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

from typing import Dict, Any, List
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..graph.state import AuditState


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

    Attributes:
        llm: GPT-5.2 model for strategic planning and risk assessment
        temperature: Low temperature (0.2) for consistent, professional output
    """

    def __init__(self, temperature: float = 0.2):
        """
        Initialize Partner Agent with GPT-5.2.

        Args:
            temperature: LLM temperature (default 0.2 for consistency)
        """
        self.llm = ChatOpenAI(
            model="gpt-5.2",
            temperature=temperature
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
