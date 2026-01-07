"""
Parent Graph Implementation (Partner Agent + Send API)

This module implements the parent graph that orchestrates the entire audit workflow:
1. Partner Agent creates audit plan
2. HITL approval checkpoint (interrupt)
3. Send API spawns parallel Manager subgraphs
4. Final aggregation of all task results

Architecture:
- State: AuditState (global project state)
- Subgraphs: Manager subgraphs (TaskState) executed in parallel
- Checkpointer: PostgresSaver for state persistence
- HITL: interrupt() for human approval

Reference:
- Specification: Section 2.2 & 4.4
- Send API: langgraph.types.Send
- HITL Pattern: LangGraph docs/tutorials/human_in_the_loop
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import logging

from ..graph.state import AuditState
from ..graph.subgraph import create_manager_subgraph
from ..graph.nodes import (
    partner_planning_node,
    wait_for_approval_node,
    manager_aggregation_node,
    continue_to_manager_subgraphs
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# CONDITIONAL ROUTING HELPERS
# ============================================================================

def route_after_approval(state: AuditState) -> Literal["manager_dispatch", "interrupt"]:
    """
    Conditional edge: Route based on approval status.

    Args:
        state: Current AuditState

    Returns:
        - "manager_dispatch" if approved → continue to Send API
        - "interrupt" if rejected → stop workflow
    """
    if state.get("is_approved"):
        return "manager_dispatch"
    else:
        return "interrupt"


# ============================================================================
# PARENT GRAPH BUILDER
# ============================================================================

def create_parent_graph(checkpointer: PostgresSaver) -> StateGraph:
    """
    Create parent graph for entire audit workflow.

    Architecture:
        START
          ↓
        Partner Planning (creates audit plan)
          ↓
        Wait for Approval (HITL checkpoint)
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
            "shared_documents": []
        }

        # Execute until HITL interrupt
        result = await graph.ainvoke(initial_state, config)

        # User approves in frontend
        await graph.aupdate_state(config, {"is_approved": True})

        # Resume workflow
        final_result = await graph.ainvoke(None, config)
        ```
    """
    # Initialize parent graph with AuditState
    parent_graph = StateGraph(AuditState)

    # Create Manager subgraph (shared across all tasks)
    manager_subgraph = create_manager_subgraph(checkpointer)

    # Add nodes (imported from nodes/ modules)
    parent_graph.add_node("partner_planning", partner_planning_node)
    parent_graph.add_node("wait_for_approval", wait_for_approval_node)
    parent_graph.add_node("manager_subgraph", manager_subgraph)
    parent_graph.add_node("final_aggregation", manager_aggregation_node)

    # Define edges
    parent_graph.add_edge("partner_planning", "wait_for_approval")

    # Conditional edge after approval
    parent_graph.add_conditional_edges(
        "wait_for_approval",
        route_after_approval,
        {
            "manager_dispatch": "manager_subgraph",  # Will be overridden by Send API
            "interrupt": END
        }
    )

    # Send API: Dispatch to parallel Manager subgraphs
    # This overrides the "manager_dispatch" edge destination
    parent_graph.add_conditional_edges(
        "wait_for_approval",
        continue_to_manager_subgraphs
    )

    parent_graph.add_edge("manager_subgraph", "final_aggregation")
    parent_graph.add_edge("final_aggregation", END)

    # Set entry point
    parent_graph.set_entry_point("partner_planning")

    # Compile with checkpointer
    compiled_graph = parent_graph.compile(checkpointer=checkpointer)
    logger.info("[Parent Graph] Compiled successfully with Send API and HITL support")

    return compiled_graph
