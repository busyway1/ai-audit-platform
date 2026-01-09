"""
Parent Graph Implementation (Partner Agent + Send API)

This module implements the parent graph that orchestrates the entire audit workflow:
1. Interview Node conducts audit strategy interview
2. Wait for Interview Completion (HITL checkpoint)
3. Partner Agent creates audit plan using specification
4. HITL approval checkpoint for plan
5. EGA Parser extracts EGAs from documents
6. Task Generator creates 3-level task hierarchy
7. Urgency Node calculates urgency scores
8. Send API spawns parallel Manager subgraphs
9. Final aggregation of all task results

Architecture:
- State: AuditState (global project state)
- Subgraphs: Manager subgraphs (TaskState) executed in parallel
- Checkpointer: PostgresSaver for state persistence
- HITL: interrupt() for human approval at multiple points

Reference:
- Specification: Section 2.2 & 4.4
- Send API: langgraph.types.Send
- HITL Pattern: LangGraph docs/tutorials/human_in_the_loop
"""

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import logging

from ..graph.state import AuditState
from ..graph.subgraph import create_manager_subgraph
from ..graph.nodes import (
    partner_planning_node,
    wait_for_approval_node,
    manager_aggregation_node,
    continue_to_manager_subgraphs,
    interview_node,
    wait_for_interview_completion_node,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# PLACEHOLDER NODES (To be replaced when BE-13.x nodes are implemented)
# ============================================================================

# Try to import EGA parser, task generator, and urgency nodes
# These will be created in BE-13.1, BE-13.2, BE-13.3 respectively
try:
    from ..graph.nodes.ega_parser import ega_parser_node
except ImportError:
    logger.warning(
        "[Graph] ega_parser_node not found. Using placeholder. "
        "Implement BE-13.1 to add EGA parser functionality."
    )

    async def ega_parser_node(state: AuditState) -> Dict[str, Any]:
        """Placeholder node for EGA parsing. To be implemented in BE-13.1."""
        logger.info("[EGA Parser] Placeholder - awaiting BE-13.1 implementation")
        return {
            "egas": state.get("egas", []),
            "next_action": "CONTINUE"
        }

try:
    from ..graph.nodes.task_generator import task_generator_node
except ImportError:
    logger.warning(
        "[Graph] task_generator_node not found. Using placeholder. "
        "Implement BE-13.2 to add task generation functionality."
    )

    async def task_generator_node(state: AuditState) -> Dict[str, Any]:
        """Placeholder node for task generation. To be implemented in BE-13.2."""
        logger.info("[Task Generator] Placeholder - awaiting BE-13.2 implementation")
        return {
            "tasks": state.get("tasks", []),
            "next_action": "CONTINUE"
        }

try:
    from ..graph.nodes.urgency_node import urgency_node
except ImportError:
    logger.warning(
        "[Graph] urgency_node not found. Using placeholder. "
        "Implement BE-13.3 to add urgency calculation functionality."
    )

    async def urgency_node(state: AuditState) -> Dict[str, Any]:
        """Placeholder node for urgency calculation. To be implemented in BE-13.3."""
        logger.info("[Urgency Node] Placeholder - awaiting BE-13.3 implementation")
        return {
            "tasks": state.get("tasks", []),
            "next_action": "CONTINUE"
        }

try:
    from ..graph.nodes.hitl_interrupt import hitl_interrupt_node
except ImportError:
    logger.warning(
        "[Graph] hitl_interrupt_node not found. Using placeholder. "
        "Implement BE-14.3 to add HITL interrupt functionality."
    )

    async def hitl_interrupt_node(state: AuditState) -> Dict[str, Any]:
        """Placeholder node for HITL interrupt. To be implemented in BE-14.3."""
        logger.info("[HITL Interrupt] Placeholder - awaiting BE-14.3 implementation")
        return {
            "next_action": "CONTINUE"
        }


# ============================================================================
# CONDITIONAL ROUTING HELPERS
# ============================================================================

def route_after_interview(state: AuditState) -> Literal["partner_planning", "interview"]:
    """
    Conditional edge: Route based on interview completion status.

    Args:
        state: Current AuditState

    Returns:
        - "partner_planning" if interview complete → proceed to planning
        - "interview" if interview incomplete → continue interview
    """
    if state.get("interview_complete", False):
        return "partner_planning"

    next_action = state.get("next_action", "")
    if next_action == "ENTER_PLAN_MODE":
        return "partner_planning"
    elif next_action == "RESTART_INTERVIEW":
        return "interview"

    return "partner_planning"


def route_after_interview_review(
    state: AuditState
) -> Literal["partner_planning", "interview", "end"]:
    """
    Conditional edge: Route based on interview review result.

    Args:
        state: Current AuditState

    Returns:
        - "partner_planning" if interview approved → proceed to planning
        - "interview" if restart requested → restart interview
        - "end" if user cancelled
    """
    next_action = state.get("next_action", "")

    if next_action == "ENTER_PLAN_MODE":
        return "partner_planning"
    elif next_action == "RESTART_INTERVIEW":
        return "interview"
    elif next_action == "REGENERATE_SPECIFICATION":
        return "interview"  # Re-run interview to regenerate spec

    # Default to partner planning if interview is complete
    if state.get("interview_complete", False):
        return "partner_planning"

    return "end"


def route_after_approval(
    state: AuditState
) -> Literal["ega_parser", "manager_dispatch", "end"]:
    """
    Conditional edge: Route based on approval status.

    Args:
        state: Current AuditState

    Returns:
        - "ega_parser" if approved and has shared documents → parse EGAs
        - "manager_dispatch" if approved and no documents → go to managers
        - "end" if rejected → stop workflow
    """
    if not state.get("is_approved"):
        return "end"

    # Check if there are documents to parse for EGAs
    shared_docs = state.get("shared_documents", [])
    egas = state.get("egas", [])

    # If we have documents but no EGAs yet, parse them
    if shared_docs and not egas:
        return "ega_parser"

    return "manager_dispatch"


def route_after_ega_parser(state: AuditState) -> Literal["task_generator", "end"]:
    """
    Conditional edge: Route after EGA parsing.

    Args:
        state: Current AuditState

    Returns:
        - "task_generator" if EGAs were parsed → generate tasks
        - "end" if parsing failed
    """
    egas = state.get("egas", [])

    if egas:
        return "task_generator"

    # If no EGAs but we have tasks from planning, go to manager dispatch
    if state.get("tasks", []):
        return "task_generator"

    return "end"


def route_after_task_generator(state: AuditState) -> Literal["urgency_node", "end"]:
    """
    Conditional edge: Route after task generation.

    Args:
        state: Current AuditState

    Returns:
        - "urgency_node" if tasks were generated → calculate urgency
        - "end" if generation failed
    """
    tasks = state.get("tasks", [])

    if tasks:
        return "urgency_node"

    return "end"


def route_after_urgency(
    state: AuditState
) -> Literal["hitl_interrupt", "manager_dispatch"]:
    """
    Conditional edge: Route after urgency calculation.

    Args:
        state: Current AuditState

    Returns:
        - "hitl_interrupt" if any task exceeds HITL threshold
        - "manager_dispatch" if all tasks below threshold
    """
    tasks = state.get("tasks", [])
    urgency_config = state.get("urgency_config", {})
    hitl_threshold = urgency_config.get("hitl_threshold", 80)  # Default 80%

    # Check if any task exceeds HITL threshold
    for task in tasks:
        urgency_score = task.get("urgency_score", 0)
        if urgency_score >= hitl_threshold:
            return "hitl_interrupt"

    return "manager_dispatch"


def route_after_hitl_interrupt(
    state: AuditState
) -> Literal["manager_dispatch", "end"]:
    """
    Conditional edge: Route after HITL interrupt handling.

    Args:
        state: Current AuditState

    Returns:
        - "manager_dispatch" if HITL resolved → proceed to managers
        - "end" if HITL rejected
    """
    next_action = state.get("next_action", "")

    if next_action == "CONTINUE":
        return "manager_dispatch"
    elif next_action == "INTERRUPT":
        return "end"

    # Default to manager dispatch
    return "manager_dispatch"


# ============================================================================
# PARENT GRAPH BUILDER
# ============================================================================

def create_parent_graph(checkpointer: PostgresSaver) -> StateGraph:
    """
    Create parent graph for entire audit workflow.

    Architecture:
        START
          ↓
        Interview Node (conducts audit strategy interview)
          ↓
        Wait for Interview Completion (HITL checkpoint)
          ↓ (if approved)
        Partner Planning (creates audit plan using specification)
          ↓
        Wait for Approval (HITL checkpoint for plan)
          ↓ (if approved)
        EGA Parser (extracts EGAs from documents)
          ↓
        Task Generator (creates 3-level task hierarchy)
          ↓
        Urgency Node (calculates urgency scores)
          ↓ (if any task exceeds threshold)
        HITL Interrupt (handles high-urgency escalations)
          ↓ (if approved)
        Manager Dispatch (Send API spawns parallel subgraphs)
          ↓
        [Manager Subgraph #1] ... [Manager Subgraph #N] (parallel execution)
          ↓
        Final Aggregation (collect all results)
          ↓
        END

    Args:
        checkpointer: PostgresSaver instance for state persistence

    Returns:
        Compiled StateGraph ready for execution

    Usage:
        ```python
        from src.db.checkpointer import get_checkpointer
        from src.graph.graph import create_parent_graph

        checkpointer = get_checkpointer()
        graph = create_parent_graph(checkpointer)

        # Start audit workflow
        config = {"configurable": {"thread_id": "project-123-main"}}
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
            "shared_documents": [],
            "interview_complete": False,
            "interview_phase": 1,
            "interview_responses": [],
            "specification": {},
            "egas": [],
            "urgency_config": {
                "materiality_weight": 0.40,
                "risk_weight": 0.35,
                "ai_confidence_weight": 0.25,
                "hitl_threshold": 80
            }
        }

        # Execute until first HITL interrupt (interview)
        result = await graph.ainvoke(initial_state, config)

        # User completes interview and approves
        await graph.aupdate_state(config, {"interview_complete": True})

        # Resume workflow until plan approval
        result = await graph.ainvoke(None, config)

        # User approves plan
        await graph.aupdate_state(config, {"is_approved": True})

        # Resume workflow to completion
        final_result = await graph.ainvoke(None, config)
        ```
    """
    # Initialize parent graph with AuditState
    parent_graph = StateGraph(AuditState)

    # Create Manager subgraph (shared across all tasks)
    manager_subgraph = create_manager_subgraph(checkpointer)

    # ========================================================================
    # ADD NODES
    # ========================================================================

    # Interview workflow nodes
    parent_graph.add_node("interview", interview_node)
    parent_graph.add_node("wait_for_interview", wait_for_interview_completion_node)

    # Planning workflow nodes
    parent_graph.add_node("partner_planning", partner_planning_node)
    parent_graph.add_node("wait_for_approval", wait_for_approval_node)

    # EGA and task processing nodes (placeholder or real implementations)
    parent_graph.add_node("ega_parser", ega_parser_node)
    parent_graph.add_node("task_generator", task_generator_node)
    parent_graph.add_node("urgency_node", urgency_node)
    parent_graph.add_node("hitl_interrupt", hitl_interrupt_node)

    # Execution workflow nodes
    parent_graph.add_node("manager_subgraph", manager_subgraph)
    parent_graph.add_node("final_aggregation", manager_aggregation_node)

    # ========================================================================
    # DEFINE EDGES
    # ========================================================================

    # Interview workflow edges
    parent_graph.add_edge("interview", "wait_for_interview")

    parent_graph.add_conditional_edges(
        "wait_for_interview",
        route_after_interview_review,
        {
            "partner_planning": "partner_planning",
            "interview": "interview",
            "end": END
        }
    )

    # Planning workflow edges
    parent_graph.add_edge("partner_planning", "wait_for_approval")

    parent_graph.add_conditional_edges(
        "wait_for_approval",
        route_after_approval,
        {
            "ega_parser": "ega_parser",
            "manager_dispatch": "manager_subgraph",
            "end": END
        }
    )

    # EGA and task processing edges
    parent_graph.add_conditional_edges(
        "ega_parser",
        route_after_ega_parser,
        {
            "task_generator": "task_generator",
            "end": END
        }
    )

    parent_graph.add_conditional_edges(
        "task_generator",
        route_after_task_generator,
        {
            "urgency_node": "urgency_node",
            "end": END
        }
    )

    parent_graph.add_conditional_edges(
        "urgency_node",
        route_after_urgency,
        {
            "hitl_interrupt": "hitl_interrupt",
            "manager_dispatch": "manager_subgraph"
        }
    )

    parent_graph.add_conditional_edges(
        "hitl_interrupt",
        route_after_hitl_interrupt,
        {
            "manager_dispatch": "manager_subgraph",
            "end": END
        }
    )

    # Send API: Dispatch to parallel Manager subgraphs
    # This adds an additional conditional edge for the Send API pattern
    parent_graph.add_conditional_edges(
        "urgency_node",
        continue_to_manager_subgraphs
    )

    # Execution workflow edges
    parent_graph.add_edge("manager_subgraph", "final_aggregation")
    parent_graph.add_edge("final_aggregation", END)

    # ========================================================================
    # SET ENTRY POINT
    # ========================================================================

    # Start with interview node
    parent_graph.set_entry_point("interview")

    # ========================================================================
    # COMPILE GRAPH
    # ========================================================================

    compiled_graph = parent_graph.compile(checkpointer=checkpointer)
    logger.info(
        "[Parent Graph] Compiled successfully with Interview, EGA Parser, "
        "Task Generator, Urgency Node, HITL, and Send API support"
    )

    return compiled_graph


# ============================================================================
# GRAPH INSTANCE FOR IMPORT
# ============================================================================

# Lazy-loaded graph instance
_graph_instance = None


def get_graph(checkpointer: PostgresSaver = None):
    """
    Get or create the parent graph instance.

    Args:
        checkpointer: PostgresSaver instance. If None, uses default.

    Returns:
        Compiled StateGraph instance
    """
    global _graph_instance

    if _graph_instance is None:
        if checkpointer is None:
            # Import here to avoid circular imports
            from ..db.checkpointer import get_checkpointer
            checkpointer = get_checkpointer()

        _graph_instance = create_parent_graph(checkpointer)

    return _graph_instance


# Export for backward compatibility
graph = None  # Will be initialized when get_graph() is called with checkpointer
