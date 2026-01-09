"""
Task Hierarchy Builders

This module provides functions for generating the 3-level task hierarchy:
- High Level (EGA) - Top-level tasks representing overall audit objectives
- Mid Level (Assertion) - Mid-level tasks for financial statement assertions
- Low Level (Procedure) - Low-level tasks for specific audit procedures

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

from typing import Any, Dict, List

from .constants import RiskLevel, TaskLevel, TaskStatus
from .models import GeneratedTask, TaskGenerationResult
from .utils import (
    calculate_risk_score,
    estimate_hours,
    generate_task_id,
    get_procedures_for_assertion,
    parse_risk_level,
    select_assertions_for_ega,
)


def generate_high_level_task(ega: Dict[str, Any], project_id: str) -> GeneratedTask:
    """
    Generate a High-level task from an EGA.

    High-level tasks represent the top-level audit objectives derived directly
    from EGAs (Expected General Activities).

    Args:
        ega: EGA dictionary with all fields
        project_id: Project ID for the task

    Returns:
        GeneratedTask at High level
    """
    risk_level = parse_risk_level(ega.get("risk_level"))
    risk_score = calculate_risk_score(risk_level)

    return GeneratedTask(
        id=generate_task_id(),
        project_id=project_id,
        ega_id=ega.get("id"),
        parent_task_id=None,  # High level has no parent
        task_level=TaskLevel.HIGH,
        name=ega.get("name", "Unnamed EGA"),
        description=ega.get("description", ""),
        category=ega.get("metadata", {}).get("category", "General"),
        risk_level=risk_level,
        risk_score=risk_score,
        status=TaskStatus.PENDING,
        priority=ega.get("priority", 50),
        estimated_hours=estimate_hours(TaskLevel.HIGH, risk_level),
        metadata={
            "source": "ega",
            "ega_id": ega.get("id"),
            "source_row": ega.get("source_row"),
            "source_sheet": ega.get("source_sheet"),
        },
    )


def generate_mid_level_tasks(
    high_task: GeneratedTask,
    ega: Dict[str, Any],
) -> List[GeneratedTask]:
    """
    Generate Mid-level tasks (assertions) from a High-level task.

    Mid-level tasks represent financial statement assertions that need to be
    tested for each EGA/High-level task.

    Args:
        high_task: Parent High-level task
        ega: Source EGA dictionary

    Returns:
        List of Mid-level GeneratedTasks
    """
    mid_tasks = []
    assertions = select_assertions_for_ega(ega)

    for assertion in assertions:
        # Adjust risk level for assertion (can be slightly different from EGA)
        risk_level = high_task.risk_level

        mid_task = GeneratedTask(
            id=generate_task_id(),
            project_id=high_task.project_id,
            ega_id=high_task.ega_id,
            parent_task_id=high_task.id,  # Link to High level
            task_level=TaskLevel.MID,
            name=f"{high_task.name} - {assertion['name']}",
            description=f"Test {assertion['name']}: {assertion['description']}",
            category=high_task.category,
            risk_level=risk_level,
            risk_score=calculate_risk_score(risk_level),
            status=TaskStatus.PENDING,
            priority=high_task.priority,
            assertion=assertion["name"],
            estimated_hours=estimate_hours(TaskLevel.MID, risk_level),
            metadata={
                "assertion_code": assertion["code"],
                "parent_ega": ega.get("name"),
            },
        )
        mid_tasks.append(mid_task)

    return mid_tasks


def generate_low_level_tasks(
    mid_task: GeneratedTask,
) -> List[GeneratedTask]:
    """
    Generate Low-level tasks (procedures) from a Mid-level task.

    Low-level tasks represent specific audit procedures to execute for
    each assertion.

    Args:
        mid_task: Parent Mid-level task

    Returns:
        List of Low-level GeneratedTasks
    """
    low_tasks = []
    assertion_code = mid_task.metadata.get("assertion_code", "EO")
    procedures = get_procedures_for_assertion(assertion_code)

    for idx, procedure in enumerate(procedures):
        low_task = GeneratedTask(
            id=generate_task_id(),
            project_id=mid_task.project_id,
            ega_id=mid_task.ega_id,
            parent_task_id=mid_task.id,  # Link to Mid level
            task_level=TaskLevel.LOW,
            name=f"Procedure: {procedure}",
            description=f"Execute audit procedure: {procedure} for {mid_task.assertion}",
            category=mid_task.category,
            risk_level=mid_task.risk_level,
            risk_score=mid_task.risk_score,
            status=TaskStatus.PENDING,
            priority=mid_task.priority - idx,  # Slightly decrease priority for order
            assertion=mid_task.assertion,
            procedure_type=procedure,
            estimated_hours=estimate_hours(TaskLevel.LOW, mid_task.risk_level),
            metadata={
                "assertion_code": assertion_code,
                "procedure_index": idx,
            },
        )
        low_tasks.append(low_task)

    return low_tasks


def generate_task_hierarchy(
    egas: List[Dict[str, Any]],
    project_id: str,
    include_low_level: bool = True,
) -> TaskGenerationResult:
    """
    Generate complete 3-level task hierarchy from EGAs.

    This is the main entry point for task generation. It creates:
    - High-level tasks from each EGA
    - Mid-level tasks for relevant assertions
    - Low-level tasks for specific procedures

    Args:
        egas: List of EGA dictionaries
        project_id: Project ID for all tasks
        include_low_level: Whether to generate Low-level tasks (default True)

    Returns:
        TaskGenerationResult with all generated tasks

    Example:
        ```python
        egas = [
            {
                "id": "ega-001",
                "name": "Revenue Recognition Testing",
                "risk_level": "high",
                "metadata": {"category": "Revenue"}
            }
        ]

        result = generate_task_hierarchy(egas, "proj-123")
        print(f"Generated {len(result.tasks)} tasks")
        ```
    """
    if not egas:
        return TaskGenerationResult(
            success=False,
            tasks=[],
            errors=["No EGAs provided for task generation"],
        )

    all_tasks: List[GeneratedTask] = []
    errors: List[str] = []
    warnings: List[str] = []

    high_count = 0
    mid_count = 0
    low_count = 0

    for ega in egas:
        try:
            # Skip invalid EGAs
            if not ega.get("name"):
                warnings.append(f"Skipping EGA without name: {ega.get('id', 'unknown')}")
                continue

            # Generate High-level task
            high_task = generate_high_level_task(ega, project_id)
            all_tasks.append(high_task)
            high_count += 1

            # Generate Mid-level tasks
            mid_tasks = generate_mid_level_tasks(high_task, ega)
            all_tasks.extend(mid_tasks)
            mid_count += len(mid_tasks)

            # Generate Low-level tasks
            if include_low_level:
                for mid_task in mid_tasks:
                    low_tasks = generate_low_level_tasks(mid_task)
                    all_tasks.extend(low_tasks)
                    low_count += len(low_tasks)

        except Exception as e:
            errors.append(f"Error generating tasks for EGA {ega.get('id', 'unknown')}: {str(e)}")

    return TaskGenerationResult(
        success=len(all_tasks) > 0,
        tasks=all_tasks,
        high_level_count=high_count,
        mid_level_count=mid_count,
        low_level_count=low_count,
        errors=errors,
        warnings=warnings,
        metadata={
            "total_egas_processed": len(egas),
            "include_low_level": include_low_level,
        },
    )
