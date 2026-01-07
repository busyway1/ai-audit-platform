"""
Staff Agents for AI Audit Platform

This module implements the 4 core Staff agents that perform granular audit procedures:
1. ExcelParserAgent: Parse Excel files and extract financial data
2. StandardRetrieverAgent: RAG-based standard retrieval (mock for POC)
3. VouchingAssistantAgent: Perform vouching procedures with LLM reasoning
4. WorkPaperGeneratorAgent: Generate audit workpaper drafts

Each agent follows the Blackboard pattern, filling specific fields in TaskState.

Reference:
- Specification: Section 4.3 (Agent Personas and Prompts)
- State: backend/src/graph/state.py (TaskState)
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
import logging

# Import TaskState for type hints (compatible with Dict[str, Any])
from ..graph.state import TaskState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelParserAgent:
    """
    Staff Agent: Parse Excel files and extract financial data.

    Persona: Data analysis specialist, expert in financial statement parsing.

    Mission:
    - Extract data from uploaded Excel files (trial balance, financial statements)
    - Validate data integrity and completeness
    - Fill TaskState.raw_data field for downstream Staff agents
    """

    def __init__(self, model_name: str = "gpt-5.2"):
        """
        Initialize Excel Parser agent.

        Args:
            model_name: GPT model to use for data validation and anomaly detection
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_Excel_Parser"
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse uploaded Excel file and extract financial data.

        For POC: Mock Excel parsing with realistic sample data.
        TODO: Real implementation uses openpyxl or pandas for actual file parsing.

        Args:
            state: Current TaskState containing task_id, category, etc.

        Returns:
            Updated state with:
            - raw_data: Extracted financial data
            - messages: Log message about parsing completion
        """
        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")

        logger.info(f"[{self.agent_name}] Starting Excel parsing for task {task_id} ({category})")

        # POC: Mock data extraction
        # In production, this would:
        # 1. Fetch file from Supabase Storage using task_id
        # 2. Parse Excel with openpyxl/pandas
        # 3. Validate data completeness
        # 4. Detect anomalies with LLM

        mock_data = {
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
            "parsed_at": "2026-01-06T10:30:00Z",
            "data_quality": "GOOD",
            "anomalies_detected": 0
        }

        logger.info(
            f"[{self.agent_name}] Parsed {mock_data['transaction_count']} transactions "
            f"for {category} (Total: KRW {mock_data['total_sales']:,})"
        )

        return {
            "raw_data": mock_data,
            "messages": [
                HumanMessage(
                    content=f"[{self.agent_name}] Successfully parsed {mock_data['transaction_count']} "
                            f"{category} transactions. Total amount: KRW {mock_data['total_sales']:,}. "
                            f"Data quality: {mock_data['data_quality']}. No anomalies detected.",
                    name=self.agent_name
                )
            ]
        }


class StandardRetrieverAgent:
    """
    Staff Agent: RAG-based standard retrieval from K-IFRS/K-GAAS.

    Persona: Accounting standards expert, specializing in K-IFRS and K-GAAS research.

    Mission:
    - Retrieve relevant audit standards from vector DB (pgvector + HNSW)
    - Apply metadata filters (account category, audit stage)
    - Fill TaskState.standards field with relevant regulations
    """

    def __init__(self, model_name: str = "gpt-5.2"):
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
        Retrieve relevant audit standards from vector DB.

        For POC: Mock RAG retrieval with pre-defined standards.
        TODO: Real implementation:
        1. Query embedding with OpenAI text-embedding-3-large
        2. pgvector similarity search (cosine similarity)
        3. Metadata filtering (account_category, audit_stage)
        4. Parent-Child chunk expansion

        Args:
            state: Current TaskState containing category, raw_data, etc.

        Returns:
            Updated state with:
            - standards: List of relevant K-IFRS/K-GAAS standards
            - messages: Log message about standards retrieved
        """
        task_id = state.get("task_id", "UNKNOWN")
        category = state.get("category", "Sales")
        raw_data = state.get("raw_data", {})

        logger.info(
            f"[{self.agent_name}] Retrieving standards for task {task_id} ({category})"
        )

        # POC: Mock RAG retrieval based on category
        # In production, this would:
        # 1. Use Standard_MCP server
        # 2. Query pgvector with embeddings
        # 3. Apply metadata filters
        # 4. Return Parent chunks with full context

        category_to_standards = {
            "Sales": [
                "K-IFRS 1115: 고객과의 계약에서 생기는 수익 (Revenue from Contracts with Customers) - 문단 31-35 (수익 인식 시점)",
                "K-GAAS 500: 감사증거 (Audit Evidence) - 문단 A1-A10 (충분하고 적합한 증거)",
                "K-GAAS 330: 평가된 위험에 대한 감사인의 대응 (Auditor's Responses to Assessed Risks) - 실증절차 설계"
            ],
            "Inventory": [
                "K-IFRS 1002: 재고자산 (Inventories) - 문단 9 (원가 측정)",
                "K-GAAS 501: 감사증거—특정 항목에 대한 고려사항 (Audit Evidence—Specific Considerations for Selected Items)"
            ],
            "AR": [
                "K-IFRS 1109: 금융상품 (Financial Instruments) - 문단 5.5.1 (손상 모형)",
                "K-GAAS 540: 회계추정치와 관련 공시에 대한 감사 (Auditing Accounting Estimates and Related Disclosures)"
            ]
        }

        mock_standards = category_to_standards.get(
            category,
            [
                "K-GAAS 200: 재무제표감사를 수행하는 독립된 감사인의 전반적인 목적 (Overall Objectives of the Independent Auditor)",
                "K-GAAS 315: 중요한 왜곡표시위험의 식별과 평가 (Identifying and Assessing the Risks of Material Misstatement)"
            ]
        )

        logger.info(
            f"[{self.agent_name}] Retrieved {len(mock_standards)} relevant standards for {category}"
        )

        return {
            "standards": mock_standards,
            "messages": [
                HumanMessage(
                    content=f"[{self.agent_name}] Retrieved {len(mock_standards)} relevant audit standards "
                            f"for {category} audit:\n" + "\n".join(f"  - {s}" for s in mock_standards),
                    name=self.agent_name
                )
            ]
        }


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

    def __init__(self, model_name: str = "gpt-5.2"):
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

        For POC: Mock vouching with LLM-generated reasoning.
        TODO: Real implementation:
        1. Fetch evidence documents from Supabase Storage
        2. OCR PDF/images with Doc_Parser_MCP
        3. Cross-reference with transaction data
        4. LLM analyzes discrepancies and risk

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

        # POC: Generate mock vouching logs
        # In production, this would use actual document verification
        vouching_logs = [
            {
                "transaction_id": sample_transactions[0].get("invoice_no", "INV-001"),
                "date": sample_transactions[0].get("date", "2024-01-15"),
                "amount": sample_transactions[0].get("amount", 50_000_000),
                "status": "Verified",
                "notes": "Invoice INV-2024-001 matches sales record. Contract terms verified. Payment received on 2024-02-15.",
                "risk_level": "Low"
            },
            {
                "transaction_id": sample_transactions[1].get("invoice_no", "INV-002") if len(sample_transactions) > 1 else "INV-002",
                "date": sample_transactions[1].get("date", "2024-02-20") if len(sample_transactions) > 1 else "2024-02-20",
                "amount": sample_transactions[1].get("amount", 75_000_000) if len(sample_transactions) > 1 else 75_000_000,
                "status": "Exception",
                "notes": "Missing shipping confirmation document. Customer signature present on invoice but delivery receipt not found.",
                "risk_level": "Medium",
                "follow_up_required": True
            },
            {
                "transaction_id": sample_transactions[2].get("invoice_no", "INV-003") if len(sample_transactions) > 2 else "INV-003",
                "date": sample_transactions[2].get("date", "2024-03-10") if len(sample_transactions) > 2 else "2024-03-10",
                "amount": sample_transactions[2].get("amount", 120_000_000) if len(sample_transactions) > 2 else 120_000_000,
                "status": "Verified",
                "notes": "All supporting documents present. Contract, invoice, delivery receipt, and payment confirmation verified.",
                "risk_level": "Low"
            }
        ]

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
                        f"[{self.agent_name}] Vouching procedures completed for {len(vouching_logs)} transactions.\n"
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

    def _format_transactions(self, transactions: list) -> str:
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


class WorkPaperGeneratorAgent:
    """
    Staff Agent: Generate audit workpaper drafts.

    Persona: Experienced audit staff, expert in workpaper documentation and reporting.

    Mission:
    - Synthesize all Staff agent outputs (raw_data, standards, vouching_logs)
    - Generate comprehensive workpaper following audit standards
    - Document procedures, findings, and conclusions
    - Fill TaskState.workpaper_draft field
    """

    def __init__(self, model_name: str = "gpt-5.2"):
        """
        Initialize WorkPaper Generator agent.

        Args:
            model_name: GPT model to use for workpaper synthesis and drafting
        """
        self.llm = ChatOpenAI(model=model_name)
        self.agent_name = "Staff_WorkPaper_Generator"
        logger.info(f"{self.agent_name} initialized with model {model_name}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate audit workpaper draft synthesizing all Staff outputs.

        For POC: Generate structured workpaper with LLM.
        TODO: Real implementation:
        1. Use WorkingPaper_Generator native tool
        2. Generate Excel/Word documents
        3. Upload to Supabase Storage
        4. Store file URL in audit_workpapers table

        Args:
            state: Current TaskState with all Staff agent outputs

        Returns:
            Updated state with:
            - workpaper_draft: Generated workpaper content
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

        # Use LLM to generate comprehensive workpaper
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

        workpaper_draft = response.content

        # Add metadata to workpaper
        full_workpaper = f"""
# AUDIT WORKPAPER

**Task ID:** {task_id}
**Account Category:** {category}
**Prepared By:** {self.agent_name}
**Date:** 2026-01-06
**Status:** DRAFT

---

{workpaper_draft}

---

**Attachments:**
- Excel file: {raw_data.get('transaction_count', 0)} transactions analyzed
- Vouching logs: {len(vouching_logs)} transactions verified
- Standards applied: {len(standards)} K-IFRS/K-GAAS references

**Review Status:** Pending Manager Review
"""

        logger.info(
            f"[{self.agent_name}] Workpaper draft completed for task {task_id} "
            f"({len(workpaper_draft)} characters)"
        )

        return {
            "workpaper_draft": full_workpaper,
            "messages": [
                HumanMessage(
                    content=(
                        f"[{self.agent_name}] Audit workpaper draft completed for {category} audit.\n"
                        f"Document length: {len(full_workpaper)} characters.\n"
                        f"Status: Ready for Manager review."
                    ),
                    name=self.agent_name
                )
            ]
        }

    def _format_standards(self, standards: list) -> str:
        """Format standards list for workpaper."""
        if not standards:
            return "No standards referenced."
        return "\n".join(f"  - {s}" for s in standards)

    def _format_vouching_logs(self, logs: list) -> str:
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


# Example usage (for testing)
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
