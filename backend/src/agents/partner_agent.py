"""
Partner Agent Implementation

This module implements the Partner agent for the AI Audit Platform.
The Partner agent acts as a senior audit partner with 20+ years of experience,
responsible for:
1. Understanding client's business and industry
2. Assessing audit risk based on materiality
3. Designing high-level audit plan
4. Delegating execution to Manager agents

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.3
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import re
import asyncio
import logging
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..graph.state import AuditState

# Import MCP tools for agent binding
from ..tools.mcp_tools import WEB_RESEARCH_TOOLS

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# RESEARCH DATA STRUCTURES
# ============================================================================

@dataclass
class ResearchSource:
    """Represents a single research source result."""
    source_type: str  # "rag" | "web"
    title: str
    content: str
    url: Optional[str] = None
    relevance_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeepResearchResult:
    """Aggregated result from deep research across multiple sources."""
    topic: str
    rag_results: List[ResearchSource]
    web_results: List[ResearchSource]
    synthesis: str
    key_findings: List[str]
    sources_consulted: int
    confidence_score: float
    metadata: Dict[str, Any]


# ============================================================================
# RESEARCH SYNTHESIS PROMPT
# ============================================================================

RESEARCH_SYNTHESIS_PROMPT = """You are a senior audit partner synthesizing research findings.

Given the following research results from multiple sources, create a comprehensive synthesis:

TOPIC: {topic}

RAG KNOWLEDGE BASE RESULTS (K-IFRS/K-GAAS Standards):
{rag_results}

WEB RESEARCH RESULTS:
{web_results}

Your synthesis should:
1. Identify key findings relevant to the audit topic
2. Highlight relevant regulatory requirements (K-IFRS, K-GAAS)
3. Note any best practices or industry guidance
4. Flag potential audit risks or areas requiring attention
5. Provide actionable recommendations for the audit team

Output format:
```json
{{
  "synthesis": "Comprehensive summary of all findings...",
  "key_findings": [
    "Finding 1...",
    "Finding 2...",
    "Finding 3..."
  ],
  "regulatory_requirements": [
    "K-IFRS/K-GAAS requirement 1...",
    "K-IFRS/K-GAAS requirement 2..."
  ],
  "audit_risks": [
    "Risk area 1...",
    "Risk area 2..."
  ],
  "recommendations": [
    "Recommendation 1...",
    "Recommendation 2..."
  ],
  "confidence_score": 0.85
}}
```
"""


# Partner persona system prompt (Section 4.3 from specification)
PARTNER_PERSONA = """You are a Partner with 20+ years of audit experience at a Big 4 accounting firm.
You are an expert in Risk-Based Audit methodology and K-GAAS (Korean Generally Accepted Auditing Standards).

Your role in the audit engagement:
1. Understand the client's business model, industry, and key business processes
2. Assess overall audit risk based on materiality thresholds and risk factors
3. Design a comprehensive, risk-based audit plan covering all significant accounts
4. Define audit procedures for each account based on risk assessment
5. Delegate detailed execution to Manager and Staff teams

When creating an audit plan, you must:
- Identify key financial statement accounts (e.g., Sales, Inventory, Accounts Receivable, Fixed Assets)
- Assign risk levels to each account: Low, Medium, High, or Critical
- Set materiality thresholds for each account based on overall materiality
- Determine sampling strategy (sample sizes, selection method)
- Consider fraud risk factors (revenue recognition, management override)
- Define testing approach (substantive testing, controls testing, analytical procedures)

CRITICAL INSTRUCTIONS:
- Your audit plan must be COMPREHENSIVE and cover all material accounts
- Each task should specify: category, risk_level, materiality, sampling_size, procedures
- Use professional judgment based on industry knowledge and risk factors
- Always wait for human approval before proceeding to execution
- Output your plan in valid JSON format within a markdown code block

Output format example:
```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "category": "Sales Revenue",
      "business_process": "Revenue-Collection Cycle",
      "process_stage": "Substantive Testing",
      "risk_level": "High",
      "materiality": 500000,
      "sampling_size": 25,
      "procedures": [
        "Vouch sales transactions to supporting documents",
        "Verify revenue recognition timing per K-IFRS 1115",
        "Test controls over sales order processing"
      ],
      "rationale": "Revenue is a high fraud risk area per K-GAAS 240"
    },
    {
      "id": "TASK-002",
      "category": "Inventory",
      "business_process": "Inventory Management",
      "process_stage": "Physical Observation",
      "risk_level": "Medium",
      "materiality": 300000,
      "sampling_size": 15,
      "procedures": [
        "Observe physical inventory count",
        "Test inventory valuation (FIFO/weighted average)",
        "Review obsolescence provisions"
      ],
      "rationale": "Inventory represents 15% of total assets"
    }
  ],
  "overall_strategy": "Risk-based approach focusing on high-risk areas with increased sampling",
  "key_risks": [
    "Revenue recognition timing (cutoff issues)",
    "Inventory obsolescence in slow-moving items"
  ]
}
```

Remember: You are a senior professional. Be thorough, systematic, and risk-focused.
"""


class PartnerAgent:
    """
    Partner Agent for AI Audit Platform.

    The Partner agent acts as a senior audit partner responsible for:
    1. Understanding client's business and industry
    2. Assessing audit risk based on materiality
    3. Designing high-level audit plan
    4. Delegating execution to Manager agents

    MCP Integration:
    - Uses MCP tools (search_company_news, get_industry_insights) bound to LLM
    - Enables intelligent research for audit planning and risk assessment
    - Falls back to direct HTTP calls if MCP server is unavailable

    Tool Bindings:
    - search_company_news: Search for company-related news and risk indicators
    - get_industry_insights: Get industry-specific audit guidance

    Attributes:
        llm: GPT model for strategic planning and risk assessment
        llm_with_tools: LLM with MCP web research tools bound
        temperature: Low temperature (0.2) for consistent, professional output
    """

    def __init__(
        self,
        temperature: float = 0.2,
        model_name: str = "gpt-4o-mini",
        bind_tools: bool = True
    ):
        """
        Initialize Partner Agent with GPT model and MCP tools.

        Args:
            temperature: LLM temperature (default 0.2 for consistency)
            model_name: GPT model to use (default: gpt-4o-mini)
            bind_tools: Whether to bind MCP tools to LLM (default: True)
        """
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature
        )
        self.agent_name = "Partner_Agent"

        # Bind MCP Web Research tools for tool-calling capability
        if bind_tools:
            self.llm_with_tools = self.llm.bind_tools(WEB_RESEARCH_TOOLS)
            self._tools_by_name = {tool.name: tool for tool in WEB_RESEARCH_TOOLS}
            logger.info(
                f"{self.agent_name} initialized with model {model_name} "
                f"and {len(WEB_RESEARCH_TOOLS)} MCP tools bound"
            )
        else:
            self.llm_with_tools = None
            self._tools_by_name = {}
            logger.info(
                f"{self.agent_name} initialized with model {model_name} "
                "(tools not bound)"
            )

    async def plan_audit(self, state: AuditState) -> Dict[str, Any]:
        """
        Create comprehensive audit plan based on client information.

        This is the core Partner function that:
        1. Analyzes client context (industry, materiality, fiscal year)
        2. Uses professional judgment to assess risks
        3. Designs audit procedures for each significant account
        4. Returns structured plan ready for Manager delegation

        Args:
            state: Current AuditState containing:
                - client_name: Client company name
                - fiscal_year: Fiscal year under audit
                - overall_materiality: Materiality threshold in currency
                - messages: Conversation history with user

        Returns:
            Dict containing:
                - audit_plan: Structured plan with tasks and strategy
                - tasks: List of task dictionaries for Manager agents
                - next_action: Always "WAIT_FOR_APPROVAL" (HITL)
        """
        # Build context from state
        client_context = self._build_client_context(state)

        # Invoke LLM with persona and client context
        response = await self.llm.ainvoke([
            SystemMessage(content=PARTNER_PERSONA),
            HumanMessage(content=client_context)
        ])

        # Parse LLM response into structured plan
        plan = self._parse_plan(response.content)

        # Validate plan completeness
        self._validate_plan(plan)

        # Return state updates
        return {
            "audit_plan": plan,
            "tasks": plan.get("tasks", []),
            "next_action": "WAIT_FOR_APPROVAL"  # HITL checkpoint
        }

    def _build_client_context(self, state: AuditState) -> str:
        """
        Build comprehensive client context prompt from state.

        Args:
            state: Current AuditState

        Returns:
            Formatted prompt string for LLM
        """
        context = f"""
CLIENT INFORMATION:
- Client Name: {state.get('client_name', 'Unknown')}
- Fiscal Year: {state.get('fiscal_year', 'Unknown')}
- Overall Materiality: ${state.get('overall_materiality', 0):,.2f}

CONVERSATION HISTORY:
"""
        # Add recent messages for context
        messages = state.get('messages', [])
        for msg in messages[-5:]:  # Last 5 messages for context
            role = "User" if msg.type == "human" else "Partner"
            content = msg.content[:200]  # Truncate long messages
            context += f"\n{role}: {content}"

        context += """

TASK:
Based on the client information and conversation history above, create a comprehensive audit plan.

Your audit plan should:
1. Cover all material financial statement accounts
2. Assign appropriate risk levels based on professional judgment
3. Set materiality thresholds for each account (considering overall materiality)
4. Determine sample sizes based on risk assessment
5. Define specific audit procedures for each account
6. Consider industry-specific risks and K-GAAS requirements

Generate at least 5-8 tasks covering major account categories:
- Revenue/Sales
- Accounts Receivable
- Inventory (if applicable)
- Fixed Assets
- Accounts Payable
- Accrued Expenses
- Equity
- Any other material accounts

Provide your plan in the JSON format specified in the system prompt.
"""
        return context

    def _parse_plan(self, content: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured audit plan.

        This function extracts JSON from markdown code blocks and validates structure.
        Handles both clean JSON and JSON wrapped in markdown.

        Args:
            content: Raw LLM response content

        Returns:
            Structured plan dictionary with tasks and metadata
        """
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            try:
                plan = json.loads(json_str)
                return plan
            except json.JSONDecodeError as e:
                # Fallback: return mock structure with error note
                return self._create_mock_plan(f"JSON parse error: {str(e)}")
        else:
            # No JSON block found, try to parse entire content
            try:
                plan = json.loads(content)
                return plan
            except json.JSONDecodeError:
                # Fallback: return mock structure
                return self._create_mock_plan("No valid JSON found in response")

    def _create_mock_plan(self, note: str = "") -> Dict[str, Any]:
        """
        Create mock audit plan structure for POC/fallback.

        This is used when LLM response cannot be parsed, ensuring the system
        continues to function during development/testing.

        Args:
            note: Optional note about why mock was used

        Returns:
            Mock plan with sample tasks
        """
        return {
            "tasks": [
                {
                    "id": "TASK-001",
                    "category": "Sales Revenue",
                    "business_process": "Revenue-Collection Cycle",
                    "process_stage": "Substantive Testing",
                    "risk_level": "High",
                    "materiality": 500000,
                    "sampling_size": 25,
                    "procedures": [
                        "Vouch sales transactions to supporting documents",
                        "Verify revenue recognition timing per K-IFRS 1115",
                        "Test controls over sales order processing"
                    ],
                    "rationale": "Revenue is a high fraud risk area per K-GAAS 240"
                },
                {
                    "id": "TASK-002",
                    "category": "Accounts Receivable",
                    "business_process": "Revenue-Collection Cycle",
                    "process_stage": "Substantive Testing",
                    "risk_level": "Medium",
                    "materiality": 300000,
                    "sampling_size": 20,
                    "procedures": [
                        "Confirm AR balances with customers",
                        "Test aging analysis and collectibility",
                        "Review allowance for doubtful accounts"
                    ],
                    "rationale": "AR represents significant portion of current assets"
                },
                {
                    "id": "TASK-003",
                    "category": "Inventory",
                    "business_process": "Inventory Management",
                    "process_stage": "Physical Observation",
                    "risk_level": "Medium",
                    "materiality": 300000,
                    "sampling_size": 15,
                    "procedures": [
                        "Observe physical inventory count",
                        "Test inventory valuation (FIFO/weighted average)",
                        "Review obsolescence provisions"
                    ],
                    "rationale": "Inventory valuation is subject to estimation"
                }
            ],
            "overall_strategy": "Risk-based approach focusing on high-risk areas (POC Mode)",
            "key_risks": [
                "Revenue recognition timing",
                "Inventory obsolescence"
            ],
            "_note": note
        }

    def _validate_plan(self, plan: Dict[str, Any]) -> None:
        """
        Validate audit plan structure and completeness.

        Ensures plan has required fields and reasonable values.
        Raises ValueError if critical validation fails.

        Args:
            plan: Audit plan dictionary to validate

        Raises:
            ValueError: If plan structure is invalid
        """
        # Check required top-level fields
        if "tasks" not in plan:
            raise ValueError("Audit plan must contain 'tasks' field")

        if not isinstance(plan["tasks"], list):
            raise ValueError("'tasks' must be a list")

        if len(plan["tasks"]) == 0:
            raise ValueError("Audit plan must contain at least one task")

        # Validate each task
        required_task_fields = ["id", "category", "risk_level", "materiality"]
        for i, task in enumerate(plan["tasks"]):
            for field in required_task_fields:
                if field not in task:
                    raise ValueError(f"Task {i} missing required field: {field}")

            # Validate risk_level enum
            valid_risk_levels = ["Low", "Medium", "High", "Critical"]
            if task.get("risk_level") not in valid_risk_levels:
                raise ValueError(
                    f"Task {i} has invalid risk_level: {task.get('risk_level')}. "
                    f"Must be one of {valid_risk_levels}"
                )

            # Validate materiality is positive number
            try:
                materiality = float(task.get("materiality", 0))
                if materiality <= 0:
                    raise ValueError(f"Task {i} materiality must be positive")
            except (TypeError, ValueError):
                raise ValueError(f"Task {i} materiality must be a number")

    def enrich_tasks_with_metadata(
        self,
        tasks: List[Dict[str, Any]],
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Enrich task dictionaries with additional metadata for database storage.

        Adds fields required by audit_tasks table schema:
        - project_id (foreign key)
        - thread_id (unique identifier for LangGraph checkpoint)
        - status (initial state)
        - title and description (derived from category and procedures)

        Args:
            tasks: List of task dictionaries from audit plan
            project_id: UUID of audit project

        Returns:
            Enriched task list ready for database insertion
        """
        import uuid

        enriched = []
        for task in tasks:
            enriched_task = {
                **task,  # Copy all original fields
                "project_id": project_id,
                "thread_id": f"task-{uuid.uuid4()}",  # Unique LangGraph thread
                "status": "Pending",
                "title": f"{task['category']} Audit",
                "description": f"Audit procedures for {task['category']}: " +
                              ", ".join(task.get("procedures", [])[:2])  # First 2 procedures
            }
            enriched.append(enriched_task)

        return enriched

    # ========================================================================
    # DEEP RESEARCH METHODS (BE-10.1)
    # ========================================================================

    async def deep_research(
        self,
        topic: str,
        state: AuditState,
        rag_base_url: str = "http://localhost:8001",
        web_base_url: str = "http://localhost:8002",
        timeout: float = 30.0,
        use_tools: bool = True
    ) -> DeepResearchResult:
        """
        Perform deep research on a topic using RAG and Web integration.

        This method combines multiple research sources to provide comprehensive
        audit-relevant information:
        1. RAG search on K-IFRS/K-GAAS knowledge base
        2. Web research for industry practices and recent developments
        3. LLM-based synthesis of all findings

        Strategy:
        - If tools bound and use_tools=True: Use LLM with tool-calling
        - Otherwise: Fall back to direct HTTP calls

        Args:
            topic: Research topic (e.g., "revenue recognition timing")
            state: Current AuditState for context
            rag_base_url: MCP RAG server URL (default: localhost:8001)
            web_base_url: MCP Web Research server URL (default: localhost:8002)
            timeout: Request timeout in seconds (default: 30s)
            use_tools: Whether to use bound MCP tools (default: True)

        Returns:
            DeepResearchResult containing synthesized findings from all sources

        Raises:
            TimeoutError: If research exceeds timeout
            ValueError: If topic is empty
        """
        if not topic or not topic.strip():
            raise ValueError("Research topic cannot be empty")

        # Build context from state
        client_context = self._build_research_context(topic, state)

        # Try tool-calling approach if tools are bound and enabled
        if use_tools and self.llm_with_tools and self._tools_by_name:
            web_results = await self._search_web_with_tools(
                topic, state, client_context
            )
        else:
            # Fall back to direct HTTP calls
            web_results = await self._search_web(
                topic, client_context, web_base_url, timeout
            )
            if isinstance(web_results, Exception):
                web_results = self._get_fallback_web_results(topic)

        # RAG search (always use direct client for now)
        rag_results = await self._search_rag(
            topic, client_context, rag_base_url, timeout
        )
        if isinstance(rag_results, Exception):
            rag_results = self._get_fallback_rag_results(topic)

        # Synthesize results using LLM
        synthesis_result = await self._synthesize_research(
            topic, rag_results, web_results
        )

        # Build final result
        return DeepResearchResult(
            topic=topic,
            rag_results=rag_results,
            web_results=web_results,
            synthesis=synthesis_result.get("synthesis", ""),
            key_findings=synthesis_result.get("key_findings", []),
            sources_consulted=len(rag_results) + len(web_results),
            confidence_score=synthesis_result.get("confidence_score", 0.5),
            metadata={
                "client_name": state.get("client_name", "Unknown"),
                "fiscal_year": state.get("fiscal_year", "Unknown"),
                "regulatory_requirements": synthesis_result.get(
                    "regulatory_requirements", []
                ),
                "audit_risks": synthesis_result.get("audit_risks", []),
                "recommendations": synthesis_result.get("recommendations", []),
                "method": "tool_calling" if (
                    use_tools and self.llm_with_tools
                ) else "direct_http"
            }
        )

    async def _search_web_with_tools(
        self,
        topic: str,
        state: AuditState,
        context: str
    ) -> List[ResearchSource]:
        """
        Search web using LLM with bound MCP tools.

        The LLM decides which tools to call (search_company_news,
        get_industry_insights) based on the research topic.

        Args:
            topic: Research topic
            state: Current AuditState for context
            context: Client context string

        Returns:
            List of ResearchSource results from web search
        """
        try:
            client_name = state.get("client_name", "Unknown")

            # Build prompt for LLM to decide tool usage
            system_prompt = (
                "You are a senior audit partner conducting research. "
                "Use the available tools to search for relevant information:\n"
                "- search_company_news: For company-specific news and developments\n"
                "- get_industry_insights: For industry best practices and risks\n\n"
                "Based on the research topic, call the appropriate tools."
            )

            user_prompt = (
                f"Research the following for audit planning:\n"
                f"- Topic: {topic}\n"
                f"- Client: {client_name}\n"
                f"- Context: {context}\n\n"
                f"Use the appropriate research tools to gather relevant information."
            )

            # Invoke LLM with tools
            response = await self.llm_with_tools.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            web_results: List[ResearchSource] = []

            # Process tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args", {})

                    logger.info(
                        f"[{self.agent_name}] LLM requested tool: {tool_name}"
                    )

                    if tool_name in self._tools_by_name:
                        tool = self._tools_by_name[tool_name]
                        result_str = await tool.ainvoke(tool_args)
                        result = json.loads(result_str)

                        if result.get("status") == "success":
                            # Convert tool results to ResearchSource
                            if tool_name == "search_company_news":
                                for r in result.get("results", []):
                                    web_results.append(ResearchSource(
                                        source_type="web",
                                        title=r.get("title", ""),
                                        content=r.get("snippet", ""),
                                        url=r.get("url"),
                                        relevance_score=0.7,
                                        metadata={
                                            "tool": tool_name,
                                            "source": r.get("source", "web"),
                                            "date": r.get("date")
                                        }
                                    ))
                            elif tool_name == "get_industry_insights":
                                for r in result.get("insights", []):
                                    web_results.append(ResearchSource(
                                        source_type="web",
                                        title=r.get("title", "Industry Insight"),
                                        content=r.get("content", ""),
                                        url=r.get("url"),
                                        relevance_score=r.get("relevance", 0.6),
                                        metadata={
                                            "tool": tool_name,
                                            "industry": result.get("industry"),
                                            "topic": result.get("topic")
                                        }
                                    ))

            if not web_results:
                logger.info(
                    f"[{self.agent_name}] No tool results, using fallback"
                )
                return self._get_fallback_web_results(topic)

            return web_results

        except Exception as e:
            logger.error(
                f"[{self.agent_name}] Tool-based web search failed: {e}"
            )
            return self._get_fallback_web_results(topic)

    def _build_research_context(self, topic: str, state: AuditState) -> str:
        """
        Build context string for research queries.

        Args:
            topic: Research topic
            state: Current AuditState

        Returns:
            Formatted context string
        """
        return f"""
Client: {state.get('client_name', 'Unknown')}
Fiscal Year: {state.get('fiscal_year', 'Unknown')}
Materiality: ${state.get('overall_materiality', 0):,.2f}
Research Topic: {topic}
"""

    async def _search_rag(
        self,
        topic: str,
        context: str,
        base_url: str,
        timeout: float
    ) -> List[ResearchSource]:
        """
        Search the RAG knowledge base for K-IFRS/K-GAAS standards.

        Args:
            topic: Search topic
            context: Client context for filtering
            base_url: MCP RAG server URL
            timeout: Request timeout

        Returns:
            List of ResearchSource results from RAG
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{base_url}/search_standards",
                    json={
                        "query": topic,
                        "top_k": 10,
                        "filters": {}
                    }
                )
                response.raise_for_status()
                data = response.json()

                return [
                    ResearchSource(
                        source_type="rag",
                        title=f"{r.get('standard_code', 'N/A')} 문단 {r.get('paragraph_number', 'N/A')}",
                        content=r.get("content", ""),
                        url=None,
                        relevance_score=r.get("score", 0.0),
                        metadata={
                            "paragraph_id": r.get("paragraph_id"),
                            "standard_code": r.get("standard_code"),
                            "paragraph_number": r.get("paragraph_number"),
                            **r.get("metadata", {})
                        }
                    )
                    for r in data.get("results", [])
                ]
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                # Return fallback on error
                return self._get_fallback_rag_results(topic)

    async def _search_web(
        self,
        topic: str,
        context: str,
        base_url: str,
        timeout: float
    ) -> List[ResearchSource]:
        """
        Search the web for relevant audit information.

        Args:
            topic: Search topic
            context: Client context for filtering
            base_url: MCP Web Research server URL
            timeout: Request timeout

        Returns:
            List of ResearchSource results from web search
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                # Construct audit-focused search query
                audit_query = f"audit {topic} best practices standards"

                response = await client.post(
                    f"{base_url}/search",
                    json={
                        "query": audit_query,
                        "max_results": 5,
                        "language": "ko"  # Korean language preference
                    }
                )
                response.raise_for_status()
                data = response.json()

                return [
                    ResearchSource(
                        source_type="web",
                        title=r.get("title", "Untitled"),
                        content=r.get("snippet", r.get("content", "")),
                        url=r.get("url"),
                        relevance_score=r.get("score", 0.5),
                        metadata={
                            "source": r.get("source", "web"),
                            "date": r.get("date"),
                            **r.get("metadata", {})
                        }
                    )
                    for r in data.get("results", [])
                ]
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                # Return fallback on error
                return self._get_fallback_web_results(topic)

    def _get_fallback_rag_results(self, topic: str) -> List[ResearchSource]:
        """
        Return fallback RAG results when MCP server is unavailable.

        Args:
            topic: Research topic

        Returns:
            List of fallback ResearchSource results
        """
        return [
            ResearchSource(
                source_type="rag",
                title="K-GAAS 200: 독립된 감사인의 전반적인 목적",
                content="재무제표감사를 수행하는 독립된 감사인의 전반적인 목적은 재무제표가 "
                        "중요성의 관점에서 해당 재무보고체계에 따라 작성되었는지에 대한 "
                        "합리적인 확신을 얻는 것이다.",
                relevance_score=0.7,
                metadata={"fallback": True, "standard_code": "K-GAAS 200"}
            ),
            ResearchSource(
                source_type="rag",
                title="K-GAAS 315: 중요한 왜곡표시위험의 식별과 평가",
                content="감사인은 재무제표 전체 수준과 경영진 주장 수준에서의 중요한 왜곡표시위험을 "
                        "식별하고 평가하기 위하여 기업과 기업환경 및 기업의 내부통제에 대한 이해를 해야 한다.",
                relevance_score=0.65,
                metadata={"fallback": True, "standard_code": "K-GAAS 315"}
            )
        ]

    def _get_fallback_web_results(self, topic: str) -> List[ResearchSource]:
        """
        Return fallback web results when MCP server is unavailable.

        Args:
            topic: Research topic

        Returns:
            List of fallback ResearchSource results
        """
        return [
            ResearchSource(
                source_type="web",
                title="Audit Best Practices - KICPA Guidelines",
                content="한국공인회계사회(KICPA)에서 제공하는 감사 실무 가이드라인에 따르면, "
                        "감사인은 전문가적 의구심을 유지하고 충분하고 적합한 감사증거를 수집해야 합니다.",
                url="https://www.kicpa.or.kr/audit-guidelines",
                relevance_score=0.6,
                metadata={"fallback": True, "source": "KICPA"}
            )
        ]

    async def _synthesize_research(
        self,
        topic: str,
        rag_results: List[ResearchSource],
        web_results: List[ResearchSource]
    ) -> Dict[str, Any]:
        """
        Synthesize research results using LLM.

        Args:
            topic: Research topic
            rag_results: Results from RAG knowledge base
            web_results: Results from web search

        Returns:
            Dict containing synthesis, key_findings, and confidence_score
        """
        # Format RAG results for prompt
        rag_formatted = "\n".join([
            f"- {r.title}: {r.content[:300]}..."
            if len(r.content) > 300 else f"- {r.title}: {r.content}"
            for r in rag_results
        ]) or "No RAG results available."

        # Format web results for prompt
        web_formatted = "\n".join([
            f"- [{r.title}]({r.url}): {r.content[:200]}..."
            if r.url and len(r.content) > 200
            else f"- {r.title}: {r.content}"
            for r in web_results
        ]) or "No web results available."

        # Build synthesis prompt
        prompt = RESEARCH_SYNTHESIS_PROMPT.format(
            topic=topic,
            rag_results=rag_formatted,
            web_results=web_formatted
        )

        # Invoke LLM for synthesis
        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert audit partner synthesizing research."),
            HumanMessage(content=prompt)
        ])

        # Parse LLM response
        return self._parse_synthesis_response(response.content)

    def _parse_synthesis_response(self, content: str) -> Dict[str, Any]:
        """
        Parse LLM synthesis response into structured format.

        Args:
            content: Raw LLM response content

        Returns:
            Dict with synthesis, key_findings, and other fields
        """
        # Try to extract JSON from response
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)

        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return result
            except json.JSONDecodeError:
                pass

        # Try to parse entire content as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Return fallback structure
        return {
            "synthesis": content[:500] if content else "Research synthesis unavailable.",
            "key_findings": [
                "Research completed with partial results.",
                "Manual review recommended for comprehensive analysis."
            ],
            "regulatory_requirements": [],
            "audit_risks": [],
            "recommendations": [
                "Consult with audit team for additional context."
            ],
            "confidence_score": 0.5
        }
