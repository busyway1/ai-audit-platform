"""
Partner Node Implementation

This module implements the Partner Agent nodes for the parent graph:
1. partner_planning_node: Creates comprehensive audit plan
2. wait_for_approval_node: HITL checkpoint for human approval

The Partner node is the entry point for the entire audit workflow.

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.3 & 4.4
"""

from typing import Dict, Any
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage
import logging

from ...graph.state import AuditState
from ...agents.partner_agent import PartnerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Partner agent (singleton)
partner_agent = PartnerAgent()


# ============================================================================
# PARTNER PLANNING NODE
# ============================================================================

async def partner_planning_node(state: AuditState) -> Dict[str, Any]:
    """
    Node 1: Partner Agent creates audit plan and requests HITL approval.

    This node:
    1. Analyzes client information (name, fiscal year, materiality)
    2. Uses Claude Sonnet 4.5 to generate comprehensive audit plan
    3. Creates 5-8 tasks with risk levels, procedures, sampling sizes
    4. Sets next_action="WAIT_FOR_APPROVAL" to trigger interrupt()

    Args:
        state: Current AuditState with client information

    Returns:
        Updated state with:
        - audit_plan: Structured plan dictionary
        - tasks: List of task dictionaries
        - next_action: "WAIT_FOR_APPROVAL"

    Example:
        ```python
        initial_state: AuditState = {
            "messages": [],
            "project_id": "proj-123",
            "client_name": "ABC Corp",
            "fiscal_year": 2024,
            "overall_materiality": 1000000.0,
            "audit_plan": {},
            "tasks": [],
            "next_action": "CONTINUE",
            "is_approved": False,
            "shared_documents": []
        }

        result = await partner_planning_node(initial_state)
        print(len(result["tasks"]))  # 5-8 tasks
        print(result["next_action"])  # "WAIT_FOR_APPROVAL"
        ```
    """
    logger.info("[Parent Graph] Step 1: Partner Planning")

    # Call Partner Agent to create plan
    result = await partner_agent.plan_audit(state)

    # Enrich tasks with metadata for database storage
    enriched_tasks = partner_agent.enrich_tasks_with_metadata(
        tasks=result["tasks"],
        project_id=state.get("project_id", "")
    )

    logger.info(f"[Partner] Created audit plan with {len(enriched_tasks)} tasks")

    return {
        "audit_plan": result["audit_plan"],
        "tasks": enriched_tasks,
        "next_action": "WAIT_FOR_APPROVAL",
        "messages": [
            HumanMessage(
                content=f"[Partner] Created audit plan with {len(enriched_tasks)} tasks. Awaiting approval.",
                name="Partner"
            )
        ]
    }


# ============================================================================
# HITL APPROVAL NODE
# ============================================================================

async def wait_for_approval_node(state: AuditState) -> Dict[str, Any]:
    """
    Node 2: Human-in-the-loop approval checkpoint.

    This node uses interrupt() to pause workflow execution until user approves.
    The frontend must call update_state() to inject approval and resume.

    Args:
        state: Current AuditState with audit plan

    Returns:
        Updated state with next_action based on approval status

    HITL Flow:
        1. interrupt() pauses execution
        2. User reviews plan in frontend
        3. User clicks "Approve" → backend calls update_state({"is_approved": True})
        4. Workflow resumes, continues to Manager dispatch

    Example:
        ```python
        # Execute graph until interrupt
        config = {"configurable": {"thread_id": "project-123-main"}}
        result = await graph.ainvoke(initial_state, config)

        # Check for interrupt
        snapshot = await graph.aget_state(config)
        if snapshot.next == ("__interrupt__",):
            print("Workflow paused for approval")

            # User approves in frontend
            await graph.aupdate_state(config, {"is_approved": True})

            # Resume workflow
            final_result = await graph.ainvoke(None, config)
        ```

    Integration with Frontend (REST API):
        ```python
        # FastAPI endpoint
        @app.post("/api/projects/{project_id}/approve")
        async def approve_audit_plan(project_id: str, approval: ApprovalRequest):
            config = {"configurable": {"thread_id": f"project-{project_id}-main"}}

            # Update state with approval
            await graph.aupdate_state(config, {
                "is_approved": approval.is_approved
            })

            # Resume workflow
            result = await graph.ainvoke(None, config)
            return {"status": "resumed", "result": result}
        ```
    """
    logger.info("[Parent Graph] Step 2: Waiting for human approval")

    # Check if already approved (from update_state)
    if state.get("is_approved"):
        logger.info("[HITL] Approval received, continuing workflow")
        return {
            "next_action": "CONTINUE"
        }

    # Pause and wait for approval
    logger.info("[HITL] Interrupting workflow for approval")
    approval = interrupt({
        "type": "approval_required",
        "message": "Please review the audit plan and approve to continue",
        "tasks": state.get("tasks", []),
        "audit_plan": state.get("audit_plan", {})
    })

    # After resume (user provided approval)
    if approval.get("is_approved"):
        logger.info("[HITL] Workflow resumed with approval")
        return {
            "is_approved": True,
            "next_action": "CONTINUE"
        }
    else:
        logger.warning("[HITL] Workflow rejected by user")
        return {
            "is_approved": False,
            "next_action": "INTERRUPT"
        }
