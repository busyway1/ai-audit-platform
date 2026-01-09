"""
Task Generator Core - LangGraph Node Implementation

This module implements the LangGraph node for generating a 3-level task hierarchy
from EGAs (Expected General Activities) extracted from Assigned Workflow documents.

The 3-Level Hierarchy:
1. High Level (EGA) - Top-level tasks representing overall audit objectives
2. Mid Level (Assertion) - Mid-level tasks for financial statement assertions
3. Low Level (Procedure) - Low-level tasks for specific audit procedures

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from ....graph.state import AuditState
from .constants import TaskLevel
from .hierarchy import generate_task_hierarchy
from .utils import calculate_risk_score, parse_risk_level

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def task_generator_node(state: AuditState) -> Dict[str, Any]:
    """
    LangGraph node for generating 3-level task hierarchy from EGAs.

    This node:
    1. Retrieves EGAs from state
    2. Generates High-level tasks (EGA level)
    3. Generates Mid-level tasks (Assertion level)
    4. Generates Low-level tasks (Procedure level)
    5. Updates state with generated tasks

    Args:
        state: Current AuditState with egas field

    Returns:
        Updated state with:
        - tasks: List of generated task dictionaries with hierarchy
        - messages: Status message about generation results

    Example:
        ```python
        state = {
            "project_id": "proj-123",
            "egas": [
                {
                    "id": "ega-001",
                    "name": "Revenue Testing",
                    "risk_level": "high",
                    "metadata": {"category": "Revenue"}
                }
            ],
            # ... other state fields
        }

        result = await task_generator_node(state)
        print(f"Generated {len(result['tasks'])} tasks")
        ```

    Note:
        If no EGAs are found in state, the node will generate tasks from
        existing audit_plan tasks or return empty list.
    """
    logger.info("[Parent Graph] Task Generator: Creating 3-level task hierarchy from EGAs")

    project_id = state.get("project_id", "")
    egas = state.get("egas", [])
    existing_tasks = state.get("tasks", [])

    # If no EGAs, try to use existing tasks or return early
    if not egas:
        logger.warning("[Task Generator] No EGAs found in state")

        # Check if we have existing tasks to enrich
        if existing_tasks:
            enriched = _enrich_existing_tasks(existing_tasks, project_id)
            return {
                "tasks": enriched,
                "messages": [
                    HumanMessage(
                        content=f"[Task Generator] Enriched {len(enriched)} existing tasks with hierarchy metadata",
                        name="TaskGenerator"
                    )
                ],
            }

        return {
            "tasks": [],
            "messages": [
                HumanMessage(
                    content="[Task Generator] No EGAs found - cannot generate task hierarchy",
                    name="TaskGenerator"
                )
            ],
        }

    # Generate task hierarchy
    result = generate_task_hierarchy(egas, project_id, include_low_level=True)

    if not result.success:
        logger.error(f"[Task Generator] Failed to generate tasks: {result.errors}")
        return {
            "tasks": existing_tasks,  # Keep existing tasks
            "messages": [
                HumanMessage(
                    content=f"[Task Generator] Error: {'; '.join(result.errors)}",
                    name="TaskGenerator"
                )
            ],
        }

    # Convert tasks to dictionaries
    generated_tasks = [task.to_dict() for task in result.tasks]

    # Merge with existing tasks (avoiding duplicates by EGA ID)
    merged_tasks = _merge_tasks(existing_tasks, generated_tasks)

    # Update task_count in EGAs
    ega_task_counts = _count_tasks_by_ega(generated_tasks)

    # Build summary message
    summary_parts = [
        f"[Task Generator] Generated {len(generated_tasks)} tasks from {len(egas)} EGAs",
        f"High: {result.high_level_count}",
        f"Mid: {result.mid_level_count}",
        f"Low: {result.low_level_count}",
    ]

    if result.warnings:
        summary_parts.append(f"Warnings: {len(result.warnings)}")

    summary_message = " | ".join(summary_parts)
    logger.info(summary_message)

    return {
        "tasks": merged_tasks,
        "messages": [
            HumanMessage(
                content=summary_message,
                name="TaskGenerator"
            )
        ],
    }


def _enrich_existing_tasks(
    tasks: List[Dict[str, Any]],
    project_id: str,
) -> List[Dict[str, Any]]:
    """
    Enrich existing tasks with hierarchy metadata if missing.

    Args:
        tasks: List of existing task dictionaries
        project_id: Project ID

    Returns:
        Enriched task list
    """
    enriched = []

    for task in tasks:
        enriched_task = task.copy()

        # Add missing fields
        if "task_level" not in enriched_task:
            enriched_task["task_level"] = TaskLevel.HIGH.value

        if "parent_task_id" not in enriched_task:
            enriched_task["parent_task_id"] = None

        if "project_id" not in enriched_task or not enriched_task["project_id"]:
            enriched_task["project_id"] = project_id

        if "risk_score" not in enriched_task:
            risk_level = parse_risk_level(enriched_task.get("risk_level"))
            enriched_task["risk_score"] = calculate_risk_score(risk_level)

        enriched.append(enriched_task)

    return enriched


def _merge_tasks(
    existing: List[Dict[str, Any]],
    generated: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge existing and generated tasks, avoiding duplicates.

    Args:
        existing: Existing task list
        generated: Newly generated task list

    Returns:
        Merged task list
    """
    # Build set of existing EGA IDs that have generated tasks
    generated_ega_ids = {t.get("ega_id") for t in generated if t.get("ega_id")}

    # Keep existing tasks that don't have generated replacements
    merged = [t for t in existing if t.get("ega_id") not in generated_ega_ids]

    # Add all generated tasks
    merged.extend(generated)

    return merged


def _count_tasks_by_ega(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count tasks per EGA.

    Args:
        tasks: List of task dictionaries

    Returns:
        Dictionary mapping EGA ID to task count
    """
    counts: Dict[str, int] = {}

    for task in tasks:
        ega_id = task.get("ega_id")
        if ega_id:
            counts[ega_id] = counts.get(ega_id, 0) + 1

    return counts


# Create an alias for backward compatibility
TaskGeneratorNode = task_generator_node
