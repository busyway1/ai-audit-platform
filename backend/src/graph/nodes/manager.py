"""
Manager Node Implementation

This module implements Manager-related nodes for the parent graph:
1. continue_to_manager_subgraphs: Send API dispatcher for parallel execution
2. manager_aggregation_node: Final aggregation of all Manager subgraph results

These nodes handle the distribution and collection of parallel task execution.

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 2.2 & 4.4
"""

from typing import List, Dict, Any
from langgraph.types import Send
from langchain_core.messages import HumanMessage
import logging

from ...graph.state import AuditState, TaskState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SEND API DISPATCHER
# ============================================================================

def continue_to_manager_subgraphs(state: AuditState) -> List[Send]:
    """
    Conditional edge function: Dispatch tasks to parallel Manager subgraphs via Send API.

    This is the CORE of parallel execution. For each task in state["tasks"],
    we create a Send() object that spawns an independent Manager subgraph
    with its own unique thread_id.

    Args:
        state: Current AuditState with tasks list

    Returns:
        List of Send objects, one per task

    Example:
        If state["tasks"] = [task1, task2, task3], returns:
        [
            Send("manager_subgraph", task1_state),
            Send("manager_subgraph", task2_state),
            Send("manager_subgraph", task3_state)
        ]

        All 3 Manager subgraphs execute in parallel.

    Send API Behavior:
        - Each Send spawns an independent subgraph execution
        - Each subgraph has its own thread_id → isolated checkpoints
        - Subgraphs execute in parallel (limited by system resources)
        - Parent graph waits for ALL subgraphs to complete
        - Failed subgraphs don't affect successful ones (error isolation)

    Integration:
        ```python
        # In parent graph definition
        parent_graph.add_conditional_edges(
            "wait_for_approval",
            continue_to_manager_subgraphs,
            ["manager_subgraph"]  # Target node name
        )
        ```

    State Mapping:
        AuditState (parent) → TaskState (subgraph):
        - task["id"] → task_id
        - task["thread_id"] → thread_id (CRITICAL: unique per task)
        - task["category"] → category
        - task.get("risk_level_score", 50) → risk_score

    Thread ID Strategy:
        Each task gets unique thread_id: "task-{uuid}"
        This ensures:
        1. Isolated checkpoints per task
        2. Independent recovery (one task fails, others continue)
        3. Parallel execution without state conflicts
    """
    tasks = state.get("tasks", [])
    project_id = state.get("project_id", "")

    logger.info(f"[Send API] Dispatching {len(tasks)} tasks to Manager subgraphs")

    send_list = []
    for task in tasks:
        # Create initial TaskState for each Manager subgraph
        task_state: TaskState = {
            "task_id": task["id"],
            "thread_id": task["thread_id"],  # CRITICAL: unique thread_id per task
            "category": task["category"],
            "status": "Pending",
            "messages": [],
            "raw_data": {},
            "standards": [],
            "vouching_logs": [],
            "workpaper_draft": "",
            "next_staff": "",  # Empty string instead of None for TypedDict compatibility
            "error_report": "",
            "risk_score": task.get("risk_level_score", 50)  # Convert risk level to score
        }

        # Create Send object for this task
        send_list.append(Send("manager_subgraph", task_state))

        logger.debug(
            f"[Send API] Created Send for task {task['id']} "
            f"(thread_id: {task['thread_id']}, category: {task['category']})"
        )

    logger.info(f"[Send API] Created {len(send_list)} Send objects for parallel execution")
    return send_list


# ============================================================================
# FINAL AGGREGATION NODE
# ============================================================================

async def manager_aggregation_node(state: AuditState) -> Dict[str, Any]:
    """
    Node 4: Aggregate all Manager subgraph results.

    After all Manager subgraphs complete (all tasks processed), this node:
    1. Counts completed/failed tasks
    2. Calculates overall audit completion percentage
    3. Determines if any critical issues require attention
    4. Updates global audit status

    Args:
        state: Current AuditState with all tasks completed

    Returns:
        Updated state with:
        - Final audit status
        - Summary statistics
        - Next action (workflow complete)

    Example:
        ```python
        # After all Manager subgraphs complete
        final_state = {
            "tasks": [
                {"id": "TASK-001", "status": "Completed", ...},
                {"id": "TASK-002", "status": "Completed", ...},
                {"id": "TASK-003", "status": "Failed", ...},
            ],
            ...
        }

        result = await manager_aggregation_node(final_state)
        print(result["next_action"])  # "COMPLETED"
        # Final Aggregation message in messages
        ```

    Aggregation Logic:
        1. Count tasks by status (Completed, Failed, In-Progress)
        2. Calculate completion rate (completed / total * 100)
        3. Identify high-risk tasks (risk_score >= 80)
        4. Determine overall audit status:
           - SUCCESS: All tasks completed, no failures
           - PARTIAL SUCCESS: Some tasks failed but most completed
           - FAILED: Majority of tasks failed

    Integration with Database:
        After aggregation, sync results to Supabase:
        ```python
        from src.db.sync import sync_audit_results

        # Update audit_projects table
        await sync_audit_results(
            project_id=state["project_id"],
            completion_rate=completion_rate,
            status="Completed" if all_success else "Partial",
            tasks=state["tasks"]
        )
        ```

    Next Steps:
        After this node completes:
        1. Frontend displays completion summary
        2. User can review completed workpapers
        3. User can retry failed tasks
        4. Final audit report generation can begin
    """
    tasks = state.get("tasks", [])

    # Count tasks by status
    completed = [t for t in tasks if t.get("status") == "Completed"]
    failed = [t for t in tasks if t.get("status") == "Failed"]
    in_progress = [t for t in tasks if t.get("status") == "In-Progress"]

    # Calculate completion rate
    completion_rate = len(completed) / len(tasks) * 100 if tasks else 0

    # Identify high-risk tasks
    high_risk_tasks = [t for t in tasks if t.get("risk_score", 0) >= 80]

    # Determine overall status
    if len(failed) == 0:
        overall_status = "SUCCESS"
    elif completion_rate >= 80:
        overall_status = "PARTIAL SUCCESS"
    else:
        overall_status = "FAILED"

    # Log summary
    logger.info(
        f"[Final Aggregation] Audit complete: "
        f"{len(completed)}/{len(tasks)} tasks completed ({completion_rate:.1f}%), "
        f"{len(failed)} failed, "
        f"{len(in_progress)} still in progress, "
        f"{len(high_risk_tasks)} high-risk tasks"
    )

    # Create summary message
    summary_message = (
        f"[Final Aggregation] Audit workflow complete.\n"
        f"\n"
        f"**Statistics:**\n"
        f"- Total Tasks: {len(tasks)}\n"
        f"- Completed: {len(completed)} ({completion_rate:.1f}%)\n"
        f"- Failed: {len(failed)}\n"
        f"- In Progress: {len(in_progress)}\n"
        f"- High Risk: {len(high_risk_tasks)}\n"
        f"\n"
        f"**Overall Status:** {overall_status}\n"
    )

    # Add high-risk task details if any
    if high_risk_tasks:
        summary_message += "\n**High-Risk Tasks Requiring Review:**\n"
        for task in high_risk_tasks[:5]:  # Show first 5
            summary_message += (
                f"- {task.get('id', 'UNKNOWN')}: {task.get('category', 'Unknown')} "
                f"(Risk Score: {task.get('risk_score', 0)})\n"
            )
        if len(high_risk_tasks) > 5:
            summary_message += f"... and {len(high_risk_tasks) - 5} more\n"

    # Add failed task details if any
    if failed:
        summary_message += "\n**Failed Tasks Requiring Attention:**\n"
        for task in failed[:5]:  # Show first 5
            error_report = task.get("error_report", "Unknown error")
            summary_message += (
                f"- {task.get('id', 'UNKNOWN')}: {task.get('category', 'Unknown')} "
                f"(Error: {error_report[:50]}...)\n"
            )
        if len(failed) > 5:
            summary_message += f"... and {len(failed) - 5} more\n"

    return {
        "next_action": "COMPLETED",
        "messages": [
            HumanMessage(
                content=summary_message,
                name="System"
            )
        ]
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_task_statistics(state: AuditState) -> Dict[str, Any]:
    """
    Calculate comprehensive task statistics from AuditState.

    Args:
        state: Current AuditState with tasks

    Returns:
        Dictionary with:
        - total: Total number of tasks
        - completed: Number of completed tasks
        - failed: Number of failed tasks
        - in_progress: Number of in-progress tasks
        - pending: Number of pending tasks
        - completion_rate: Percentage of completed tasks
        - high_risk_count: Number of high-risk tasks (risk_score >= 80)
        - categories: Dict of task counts by category

    Example:
        ```python
        stats = get_task_statistics(state)
        print(f"Progress: {stats['completion_rate']:.1f}%")
        print(f"High-Risk Tasks: {stats['high_risk_count']}")
        print(f"Tasks by Category: {stats['categories']}")
        ```
    """
    tasks = state.get("tasks", [])

    # Count by status
    completed = [t for t in tasks if t.get("status") == "Completed"]
    failed = [t for t in tasks if t.get("status") == "Failed"]
    in_progress = [t for t in tasks if t.get("status") == "In-Progress"]
    pending = [t for t in tasks if t.get("status") == "Pending"]

    # Count by category
    categories: Dict[str, int] = {}
    for task in tasks:
        category = task.get("category", "Unknown")
        categories[category] = categories.get(category, 0) + 1

    # Count high-risk tasks
    high_risk = [t for t in tasks if t.get("risk_score", 0) >= 80]

    return {
        "total": len(tasks),
        "completed": len(completed),
        "failed": len(failed),
        "in_progress": len(in_progress),
        "pending": len(pending),
        "completion_rate": len(completed) / len(tasks) * 100 if tasks else 0,
        "high_risk_count": len(high_risk),
        "categories": categories
    }
