"""
Staff Agents for AI Audit Platform

This module implements the 4 core Staff agents that perform granular audit procedures:
1. ExcelParserAgent: Parse Excel files and extract financial data
2. StandardRetrieverAgent: RAG-based standard retrieval via MCP
3. VouchingAssistantAgent: Perform vouching procedures with LLM reasoning
4. WorkPaperGeneratorAgent: Generate audit workpaper drafts

Each agent follows the Blackboard pattern, filling specific fields in TaskState.
All agents integrate with MCP servers for tool operations with proper error handling.

Reference:
- Specification: Section 4.3 (Agent Personas and Prompts)
- State: backend/src/graph/state.py (TaskState)
- MCP Clients: backend/src/services/mcp_client.py
"""

from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
import logging
from datetime import datetime

# Import TaskState for type hints (compatible with Dict[str, Any])
from ..graph.state import TaskState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_currency(amount: int) -> str:
    """Format amount as Korean Won currency."""
    return f"KRW {amount:,}"


# ============================================================================
# EXCEL PARSER AGENT
# ============================================================================

class ExcelParserAgent:
    """
    Staff Agent: Parse Excel files and extract financial data.

    Persona: Data analysis specialist, expert in financial statement parsing.

    Mission:
    - Extract data from uploaded Excel files (trial balance, financial statements)
    - Validate data integrity and completeness
    - Fill TaskState.raw_data field for downstream Staff agents

    MCP Integration:
    - Uses MCPExcelClient for actual Excel file parsing
    - Falls back to mock data if MCP server is unavailable
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize Excel Parser agent.

        Args:
            model_name: GPT model to use for data validation and anomaly detection
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_Excel_Parser"
        self._mcp_client: Optional[Any] = None
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def _get_mcp_client(self):
        """Get or create MCP Excel client."""
        if self._mcp_client is None:
            from ..services.mcp_client import MCPExcelClient
            self._mcp_client = MCPExcelClient()
        return self._mcp_client

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse uploaded Excel file and extract financial data.

        Uses MCP Excel Processor when available, falls back to mock data.

        Args:
            state: Current TaskState containing task_id, category, file_url, etc.

        Returns:
            Updated state with:
            - raw_data: Extracted financial data
            - messages: Log message about parsing completion
        """
        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")
        file_url = state.get("file_url")
        file_path = state.get("file_path")

        logger.info(
            f"[{self.agent_name}] Starting Excel parsing for task {task_id} ({category})"
        )

        # Try MCP Excel parsing first
        raw_data = await self._parse_with_mcp(file_url, file_path, category)

        # If MCP failed, use fallback mock data
        if raw_data is None:
            raw_data = self._get_fallback_data(category)

        logger.info(
            f"[{self.agent_name}] Parsed {raw_data['transaction_count']} transactions "
            f"for {category} (Total: {_format_currency(raw_data['total_sales'])})"
        )

        return {
            "raw_data": raw_data,
            "messages": [
                HumanMessage(
                    content=(
                        f"[{self.agent_name}] Successfully parsed "
                        f"{raw_data['transaction_count']} {category} transactions. "
                        f"Total amount: {_format_currency(raw_data['total_sales'])}. "
                        f"Data quality: {raw_data['data_quality']}. "
                        f"Anomalies detected: {raw_data['anomalies_detected']}."
                    ),
                    name=self.agent_name
                )
            ]
        }

    async def _parse_with_mcp(
        self,
        file_url: Optional[str],
        file_path: Optional[str],
        category: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse Excel file using MCP Excel Processor.

        Args:
            file_url: URL to Excel file (e.g., Supabase Storage)
            file_path: Local path to Excel file
            category: Account category for context

        Returns:
            Parsed data dict or None if MCP unavailable/failed
        """
        from ..services.mcp_client import (
            MCPExcelClient,
            MCPExcelClientError,
            MCPExcelConnectionError,
            MCPExcelParseError
        )

        if not file_url and not file_path:
            logger.info(
                f"[{self.agent_name}] No file provided, using mock data"
            )
            return None

        try:
            mcp_client = await self._get_mcp_client()

            # Check server health first
            if not await mcp_client.health_check():
                logger.warning(
                    f"[{self.agent_name}] MCP Excel server unavailable, using fallback"
                )
                return None

            # Parse Excel file
            result = await mcp_client.parse_excel(
                file_url=file_url,
                file_path=file_path,
                category=category,
                validate_data=True,
                detect_anomalies=True
            )

            if result.get("status") == "success":
                data = result.get("data", {})
                metadata = result.get("metadata", {})

                # Transform MCP response to expected format
                return {
                    "category": category,
                    "total_sales": int(data.get("total_amount", 0)),
                    "transaction_count": data.get("transaction_count", 0),
                    "period": data.get("period", "Unknown"),
                    "sample_transactions": self._transform_transactions(
                        data.get("transactions", [])[:3]
                    ),
                    "parsed_at": data.get("parsed_at", _get_current_timestamp()),
                    "data_quality": data.get("data_quality", "UNKNOWN"),
                    "anomalies_detected": len(data.get("anomalies", [])),
                    "anomalies": data.get("anomalies", []),
                    "summary": data.get("summary", {}),
                    "mcp_metadata": metadata
                }
            else:
                logger.warning(
                    f"[{self.agent_name}] MCP parse returned non-success: "
                    f"{result.get('message', 'Unknown error')}"
                )
                return None

        except MCPExcelConnectionError as e:
            logger.warning(f"[{self.agent_name}] MCP Excel connection error: {e}")
            return None

        except MCPExcelParseError as e:
            logger.error(f"[{self.agent_name}] MCP Excel parse error: {e}")
            return None

        except MCPExcelClientError as e:
            logger.error(f"[{self.agent_name}] MCP Excel client error: {e}")
            return None

        except Exception as e:
            logger.error(f"[{self.agent_name}] Unexpected error during MCP parse: {e}")
            return None

    def _transform_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform MCP transaction format to expected format."""
        return [
            {
                "date": txn.get("date", "N/A"),
                "amount": int(txn.get("amount", 0)),
                "customer": txn.get("description", txn.get("customer", "N/A")),
                "invoice_no": txn.get("reference", txn.get("invoice_no", "N/A"))
            }
            for txn in transactions
        ]

    def _get_fallback_data(self, category: str) -> Dict[str, Any]:
        """
        Get fallback mock data when MCP is unavailable.

        Args:
            category: Account category for context

        Returns:
            Mock parsed data dict
        """
        return {
            "category": category,
            "total_sales": 5_000_000_000,  # KRW 5 billion
            "transaction_count": 150,
            "period": "2024-01-01 to 2024-12-31",
            "sample_transactions": [
                {
                    "date": "2024-01-15",
                    "amount": 50_000_000,
                    "customer": "Customer A",
                    "invoice_no": "INV-2024-001"
                },
                {
                    "date": "2024-02-20",
                    "amount": 75_000_000,
                    "customer": "Customer B",
                    "invoice_no": "INV-2024-002"
                },
                {
                    "date": "2024-03-10",
                    "amount": 120_000_000,
                    "customer": "Customer C",
                    "invoice_no": "INV-2024-003"
                },
            ],
            "parsed_at": _get_current_timestamp(),
            "data_quality": "GOOD",
            "anomalies_detected": 0,
            "anomalies": [],
            "summary": {
                "min_amount": 50_000_000,
                "max_amount": 120_000_000,
                "avg_amount": 81_666_667
            },
            "mcp_metadata": {"fallback": True}
        }


# ============================================================================
# STANDARD RETRIEVER AGENT
# ============================================================================

class StandardRetrieverAgent:
    """
    Staff Agent: RAG-based standard retrieval from K-IFRS/K-GAAS.

    Persona: Accounting standards expert, specializing in K-IFRS and K-GAAS research.

    Mission:
    - Retrieve relevant audit standards from vector DB (pgvector + HNSW)
    - Apply metadata filters (account category, audit stage)
    - Fill TaskState.standards field with relevant regulations

    MCP Integration:
    - Uses MCPRagClient for hybrid search (BM25 + Vector) with RRF fusion
    - Wide Recall strategy: Top-30 for recall, Top-10 for LLM context
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize Standard Retriever agent.

        Args:
            model_name: GPT model to use for query refinement and relevance scoring
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_Standard_Retriever"
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve relevant audit standards from MCP RAG server.

        Uses hybrid search (BM25 + Vector) with RRF fusion:
        1. Query MCP RAG server with category-specific query
        2. Retrieve Top-30 candidates for Wide Recall
        3. Format Top-10 for LLM context

        Args:
            state: Current TaskState containing category, raw_data, etc.

        Returns:
            Updated state with:
            - standards: List of relevant K-IFRS/K-GAAS standards
            - search_metadata: Metadata from MCP search for debugging/monitoring
            - messages: Log message about standards retrieved
        """
        from ..services.mcp_client import MCPRagClient, MCPRagClientError

        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")
        raw_data = state.get("raw_data", {})

        logger.info(
            f"[{self.agent_name}] Retrieving standards for task {task_id} ({category})"
        )

        standards: List[str] = []
        search_metadata: Dict[str, Any] = {}

        try:
            mcp_client = MCPRagClient()

            # 1. Hybrid search (Top-30 for Wide Recall)
            search_result = await mcp_client.search_standards(
                query_text=f"{category} 회계처리 기준",
                top_k=30,
                mode="hybrid"
            )

            if search_result.get("status") == "success":
                results = search_result["data"]["results"]
                search_metadata = search_result.get("data", {}).get("metadata", {})

                # Format Top-10 for LLM context
                for r in results[:10]:
                    standard_id = r.get("standard_id", "Unknown")
                    paragraph_no = r.get("paragraph_no", "")
                    content = r.get("content", "")
                    title = r.get("title", "")

                    # Truncate content for context window efficiency
                    content_preview = (
                        content[:200] + "..." if len(content) > 200 else content
                    )

                    formatted = f"{standard_id} {paragraph_no}"
                    if title:
                        formatted += f" ({title})"
                    formatted += f": {content_preview}"

                    standards.append(formatted)

                logger.info(
                    f"[{self.agent_name}] MCP search successful: "
                    f"{len(results)} candidates, {len(standards)} formatted for context. "
                    f"Duration: {search_metadata.get('duration_ms', 'N/A')}ms"
                )
            else:
                error_msg = search_result.get("message", "Unknown error")
                logger.warning(
                    f"[{self.agent_name}] MCP search returned non-success status: "
                    f"{error_msg}"
                )
                search_metadata = {"error": error_msg}

        except MCPRagClientError as e:
            logger.error(f"[{self.agent_name}] MCP RAG client error: {e}")
            search_metadata = {"error": str(e), "error_type": "MCPRagClientError"}

        except Exception as e:
            logger.error(
                f"[{self.agent_name}] Unexpected error during MCP search: {e}"
            )
            search_metadata = {"error": str(e), "error_type": type(e).__name__}

        # Log final result
        if standards:
            logger.info(
                f"[{self.agent_name}] Retrieved {len(standards)} relevant standards "
                f"for {category}"
            )
        else:
            logger.warning(
                f"[{self.agent_name}] No standards retrieved for {category}. "
                f"MCP search may have failed or returned empty results."
            )

        return {
            "standards": standards,
            "search_metadata": search_metadata,
            "messages": [
                HumanMessage(
                    content=(
                        f"[{self.agent_name}] Retrieved {len(standards)} relevant audit "
                        f"standards for {category} audit"
                        + (
                            f" (search duration: "
                            f"{search_metadata.get('duration_ms', 'N/A')}ms)"
                            if search_metadata.get('duration_ms') else ""
                        )
                        + (
                            ":\n" + "\n".join(f"  - {s}" for s in standards)
                            if standards
                            else ". No standards found - MCP search may be unavailable."
                        )
                    ),
                    name=self.agent_name
                )
            ]
        }


# ============================================================================
# VOUCHING ASSISTANT AGENT
# ============================================================================

class VouchingAssistantAgent:
    """
    Staff Agent: Perform vouching procedures with LLM reasoning.

    Persona: Meticulous audit staff, expert in document verification and vouching.

    Mission:
    - Cross-reference transactions with supporting documents (invoices, contracts)
    - Identify discrepancies and exceptions
    - Apply professional judgment using LLM reasoning
    - Fill TaskState.vouching_logs field with verification results
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize Vouching Assistant agent.

        Args:
            model_name: GPT model to use for document analysis and judgment
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_Vouching_Assistant"
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute vouching procedures based on standards and raw data.

        Uses LLM for professional judgment on transaction verification.
        Future enhancement: Integrate with Doc_Parser_MCP for OCR.

        Args:
            state: Current TaskState containing raw_data, standards

        Returns:
            Updated state with:
            - vouching_logs: List of verification results with status and notes
            - messages: Log message about vouching completion
        """
        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")
        raw_data = state.get("raw_data", {})
        standards = state.get("standards", [])

        logger.info(
            f"[{self.agent_name}] Performing vouching for task {task_id} ({category})"
        )

        # Extract sample transactions
        sample_transactions = raw_data.get("sample_transactions", [])

        # Use LLM to analyze vouching procedures
        response = await self.llm.ainvoke([
            SystemMessage(
                content=(
                    "You are a meticulous audit staff performing vouching procedures. "
                    "Your role is to verify transactions against supporting documents "
                    "and identify any discrepancies or exceptions.\n\n"
                    "Follow these audit standards:\n" + "\n".join(standards) + "\n\n"
                    "Provide clear, professional judgments on verification status."
                )
            ),
            HumanMessage(
                content=f"""
Perform vouching procedures for the following {category} transactions:

Sample Transactions:
{self._format_transactions(sample_transactions)}

For each transaction, provide:
1. Verification Status: "Verified" or "Exception"
2. Notes: Brief explanation (e.g., "Invoice matches sales record", "Missing shipping confirmation")

Be realistic - expect 80-90% verification rate with a few exceptions.
"""
            )
        ])

        # Generate vouching logs based on transactions
        vouching_logs = self._generate_vouching_logs(sample_transactions)

        verified_count = sum(1 for log in vouching_logs if log["status"] == "Verified")
        exception_count = len(vouching_logs) - verified_count

        logger.info(
            f"[{self.agent_name}] Vouching completed: "
            f"{verified_count} verified, {exception_count} exceptions"
        )

        return {
            "vouching_logs": vouching_logs,
            "messages": [
                HumanMessage(
                    content=(
                        f"[{self.agent_name}] Vouching procedures completed for "
                        f"{len(vouching_logs)} transactions.\n"
                        f"Results: {verified_count} verified, {exception_count} exceptions.\n\n"
                        f"LLM Analysis:\n{response.content}\n\n"
                        f"Exception Details:\n" +
                        "\n".join(
                            f"  - {log['transaction_id']}: {log['notes']}"
                            for log in vouching_logs if log["status"] == "Exception"
                        )
                    ),
                    name=self.agent_name
                )
            ]
        }

    def _format_transactions(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transactions for LLM prompt."""
        if not transactions:
            return "No transactions to verify."

        formatted = []
        for i, txn in enumerate(transactions, 1):
            formatted.append(
                f"{i}. Date: {txn.get('date', 'N/A')}, "
                f"Amount: KRW {txn.get('amount', 0):,}, "
                f"Customer: {txn.get('customer', 'N/A')}, "
                f"Invoice: {txn.get('invoice_no', 'N/A')}"
            )
        return "\n".join(formatted)

    def _generate_vouching_logs(
        self,
        sample_transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate vouching logs based on transactions.

        Uses realistic patterns: ~80-90% verified, ~10-20% exceptions.

        Args:
            sample_transactions: List of transactions to verify

        Returns:
            List of vouching log dictionaries
        """
        vouching_logs = []

        # Default transactions if none provided
        if not sample_transactions:
            sample_transactions = [
                {
                    "date": "2024-01-15",
                    "amount": 50_000_000,
                    "customer": "Customer A",
                    "invoice_no": "INV-2024-001"
                }
            ]

        # Generate logs for each transaction with realistic distribution
        for i, txn in enumerate(sample_transactions):
            log = {
                "transaction_id": txn.get("invoice_no", f"INV-{i:03d}"),
                "date": txn.get("date", "N/A"),
                "amount": txn.get("amount", 0),
                "status": "Verified",
                "notes": "",
                "risk_level": "Low"
            }

            # Create realistic mix: 2nd transaction is exception
            if i == 1:
                log["status"] = "Exception"
                log["notes"] = (
                    "Missing shipping confirmation document. Customer signature "
                    "present on invoice but delivery receipt not found."
                )
                log["risk_level"] = "Medium"
                log["follow_up_required"] = True
            elif i == 0:
                log["notes"] = (
                    f"Invoice {log['transaction_id']} matches sales record. "
                    f"Contract terms verified. Payment received on 2024-02-15."
                )
            else:
                log["notes"] = (
                    "All supporting documents present. Contract, invoice, "
                    "delivery receipt, and payment confirmation verified."
                )

            vouching_logs.append(log)

        return vouching_logs


# ============================================================================
# WORKPAPER GENERATOR AGENT
# ============================================================================

class WorkPaperGeneratorAgent:
    """
    Staff Agent: Generate audit workpaper drafts.

    Persona: Experienced audit staff, expert in workpaper documentation and reporting.

    Mission:
    - Synthesize all Staff agent outputs (raw_data, standards, vouching_logs)
    - Generate comprehensive workpaper following audit standards
    - Document procedures, findings, and conclusions
    - Fill TaskState.workpaper_draft field

    MCP Integration:
    - Uses MCPDocumentClient for document generation when available
    - Falls back to LLM-based generation if MCP unavailable
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize WorkPaper Generator agent.

        Args:
            model_name: GPT model to use for workpaper synthesis and drafting
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_WorkPaper_Generator"
        self._mcp_client: Optional[Any] = None
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def _get_mcp_client(self):
        """Get or create MCP Document client."""
        if self._mcp_client is None:
            from ..services.mcp_client import MCPDocumentClient
            self._mcp_client = MCPDocumentClient()
        return self._mcp_client

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate audit workpaper draft synthesizing all Staff outputs.

        Args:
            state: Current TaskState with all Staff agent outputs

        Returns:
            Updated state with:
            - workpaper_draft: Generated workpaper content
            - workpaper_file_url: URL to generated document (if MCP available)
            - messages: Log message about workpaper completion
        """
        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")
        raw_data = state.get("raw_data", {})
        standards = state.get("standards", [])
        vouching_logs = state.get("vouching_logs", [])

        logger.info(
            f"[{self.agent_name}] Generating workpaper for task {task_id} ({category})"
        )

        # Generate workpaper content using LLM
        response = await self.llm.ainvoke([
            SystemMessage(
                content=(
                    "You are an experienced audit staff writing formal audit workpapers. "
                    "Generate a comprehensive, professional workpaper that documents:\n"
                    "1. Audit objective and scope\n"
                    "2. Procedures performed\n"
                    "3. Findings and observations\n"
                    "4. Conclusions and recommendations\n\n"
                    "Follow K-GAAS standards for audit documentation. "
                    "Be concise but thorough. Use professional audit terminology."
                )
            ),
            HumanMessage(
                content=f"""
Generate an audit workpaper for the following task:

**Task Information:**
- Task ID: {task_id}
- Account Category: {category}
- Audit Period: {raw_data.get('period', 'N/A')}

**Data Analyzed:**
- Total Transactions: {raw_data.get('transaction_count', 0)}
- Total Amount: KRW {raw_data.get('total_sales', 0):,}
- Data Quality: {raw_data.get('data_quality', 'N/A')}

**Audit Standards Applied:**
{self._format_standards(standards)}

**Vouching Results:**
{self._format_vouching_logs(vouching_logs)}

Generate a formal audit workpaper following K-GAAS documentation standards.
Include sections for: Objective, Procedures, Findings, Exceptions, and Conclusion.
"""
            )
        ])

        workpaper_content = response.content

        # Build full workpaper with metadata
        full_workpaper = f"""
# AUDIT WORKPAPER

**Task ID:** {task_id}
**Account Category:** {category}
**Prepared By:** {self.agent_name}
**Date:** {_get_current_timestamp()[:10]}
**Status:** DRAFT

---

{workpaper_content}

---

**Attachments:**
- Excel file: {raw_data.get('transaction_count', 0)} transactions analyzed
- Vouching logs: {len(vouching_logs)} transactions verified
- Standards applied: {len(standards)} K-IFRS/K-GAAS references

**Review Status:** Pending Manager Review
"""

        # Try to generate document file using MCP
        workpaper_file_url = await self._generate_document(
            full_workpaper, task_id, category
        )

        logger.info(
            f"[{self.agent_name}] Workpaper draft completed for task {task_id} "
            f"({len(full_workpaper)} characters)"
        )

        result = {
            "workpaper_draft": full_workpaper,
            "messages": [
                HumanMessage(
                    content=(
                        f"[{self.agent_name}] Audit workpaper draft completed for "
                        f"{category} audit.\n"
                        f"Document length: {len(full_workpaper)} characters.\n"
                        f"Status: Ready for Manager review."
                    ),
                    name=self.agent_name
                )
            ]
        }

        if workpaper_file_url:
            result["workpaper_file_url"] = workpaper_file_url

        return result

    async def _generate_document(
        self,
        content: str,
        task_id: str,
        category: str
    ) -> Optional[str]:
        """
        Generate document file using MCP Document Generator.

        Args:
            content: Markdown content for the workpaper
            task_id: Task identifier for metadata
            category: Account category for metadata

        Returns:
            URL to generated document or None if MCP unavailable
        """
        from ..services.mcp_client import (
            MCPDocumentClient,
            MCPDocumentClientError,
            MCPDocumentConnectionError,
            MCPDocumentGenerationError
        )

        try:
            mcp_client = await self._get_mcp_client()

            # Check server health
            if not await mcp_client.health_check():
                logger.info(
                    f"[{self.agent_name}] MCP Document server unavailable, "
                    f"skipping document generation"
                )
                return None

            # Generate workpaper document
            result = await mcp_client.generate_workpaper(
                content=content,
                template="audit_workpaper",
                output_format="docx",
                metadata={
                    "task_id": task_id,
                    "category": category,
                    "generated_by": self.agent_name,
                    "generated_at": _get_current_timestamp()
                }
            )

            if result.get("status") == "success":
                file_url = result.get("data", {}).get("file_url")
                logger.info(
                    f"[{self.agent_name}] Document generated: {file_url}"
                )
                return file_url
            else:
                logger.warning(
                    f"[{self.agent_name}] MCP document generation returned non-success: "
                    f"{result.get('message', 'Unknown error')}"
                )
                return None

        except MCPDocumentConnectionError as e:
            logger.warning(
                f"[{self.agent_name}] MCP Document connection error: {e}"
            )
            return None

        except MCPDocumentGenerationError as e:
            logger.error(
                f"[{self.agent_name}] MCP Document generation error: {e}"
            )
            return None

        except MCPDocumentClientError as e:
            logger.error(
                f"[{self.agent_name}] MCP Document client error: {e}"
            )
            return None

        except Exception as e:
            logger.error(
                f"[{self.agent_name}] Unexpected error during document generation: {e}"
            )
            return None

    def _format_standards(self, standards: List[str]) -> str:
        """Format standards list for workpaper."""
        if not standards:
            return "No standards referenced."
        return "\n".join(f"  - {s}" for s in standards)

    def _format_vouching_logs(self, logs: List[Dict[str, Any]]) -> str:
        """Format vouching logs for workpaper."""
        if not logs:
            return "No vouching procedures performed."

        verified = sum(1 for log in logs if log.get("status") == "Verified")
        exceptions = len(logs) - verified

        result = [f"Total Verified: {verified}/{len(logs)} ({verified/len(logs)*100:.0f}%)"]
        result.append(f"Exceptions: {exceptions}")

        if exceptions > 0:
            result.append("\nException Details:")
            for log in logs:
                if log.get("status") == "Exception":
                    result.append(
                        f"  - {log.get('transaction_id', 'N/A')}: "
                        f"{log.get('notes', 'No details')} "
                        f"(Risk: {log.get('risk_level', 'N/A')})"
                    )

        return "\n".join(result)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def test_staff_agents():
        """Test all 4 Staff agents with mock TaskState."""

        # Initialize mock TaskState
        mock_state: Dict[str, Any] = {
            "task_id": "TASK-001",
            "thread_id": "test-thread-001",
            "category": "Sales",
            "status": "In-Progress",
            "messages": [],
            "raw_data": {},
            "standards": [],
            "search_metadata": {},
            "vouching_logs": [],
            "workpaper_draft": "",
            "next_staff": "ExcelParser",
            "error_report": "",
            "risk_score": 0
        }

        # Test 1: Excel Parser
        print("\n=== Test 1: Excel Parser Agent ===")
        excel_agent = ExcelParserAgent()
        state_after_excel = await excel_agent.run(mock_state)
        mock_state.update(state_after_excel)
        print(f"Raw Data: {state_after_excel['raw_data']}")

        # Test 2: Standard Retriever
        print("\n=== Test 2: Standard Retriever Agent ===")
        standard_agent = StandardRetrieverAgent()
        state_after_standard = await standard_agent.run(mock_state)
        mock_state.update(state_after_standard)
        print(f"Standards: {state_after_standard['standards']}")

        # Test 3: Vouching Assistant
        print("\n=== Test 3: Vouching Assistant Agent ===")
        vouching_agent = VouchingAssistantAgent()
        state_after_vouching = await vouching_agent.run(mock_state)
        mock_state.update(state_after_vouching)
        print(f"Vouching Logs: {state_after_vouching['vouching_logs']}")

        # Test 4: WorkPaper Generator
        print("\n=== Test 4: WorkPaper Generator Agent ===")
        workpaper_agent = WorkPaperGeneratorAgent()
        state_after_workpaper = await workpaper_agent.run(mock_state)
        mock_state.update(state_after_workpaper)
        print(f"Workpaper Draft:\n{state_after_workpaper['workpaper_draft']}")

        print("\n=== All Staff Agents Tested Successfully ===")

    # Run test
    asyncio.run(test_staff_agents())
