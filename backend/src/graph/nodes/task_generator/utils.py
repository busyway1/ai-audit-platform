"""
Task Generator Utility Functions

This module provides utility functions for task generation including:
- Risk level parsing and score calculation
- Assertion selection
- Procedure mapping
- Task filtering, sorting, and querying

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ASSERTION_PROCEDURES,
    RISK_SCORE_MAP,
    STANDARD_ASSERTIONS,
    RiskLevel,
    TaskLevel,
)


# ============================================================================
# ID GENERATION
# ============================================================================


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return f"task-{uuid.uuid4().hex[:12]}"


# ============================================================================
# RISK LEVEL HELPERS
# ============================================================================


def parse_risk_level(value: Any) -> RiskLevel:
    """
    Parse risk level from various input formats.

    Args:
        value: Risk level value (string, enum, etc.)

    Returns:
        Normalized RiskLevel enum value
    """
    if value is None:
        return RiskLevel.MEDIUM

    if isinstance(value, RiskLevel):
        return value

    str_value = str(value).strip().lower()

    risk_mapping = {
        "critical": RiskLevel.CRITICAL,
        "very high": RiskLevel.CRITICAL,
        "high": RiskLevel.HIGH,
        "medium": RiskLevel.MEDIUM,
        "moderate": RiskLevel.MEDIUM,
        "low": RiskLevel.LOW,
        "minimal": RiskLevel.LOW,
    }

    return risk_mapping.get(str_value, RiskLevel.MEDIUM)


def calculate_risk_score(risk_level: RiskLevel) -> int:
    """
    Calculate numeric risk score from risk level.

    Args:
        risk_level: Risk level enum or string

    Returns:
        Numeric risk score (0-100)
    """
    if isinstance(risk_level, RiskLevel):
        return RISK_SCORE_MAP.get(risk_level, 50)
    return RISK_SCORE_MAP.get(str(risk_level).lower(), 50)


# ============================================================================
# ASSERTION HELPERS
# ============================================================================


def select_assertions_for_ega(ega: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Select relevant assertions based on EGA characteristics.

    Args:
        ega: EGA dictionary with metadata

    Returns:
        List of assertion dictionaries relevant to the EGA
    """
    category = ega.get("metadata", {}).get("category", "").lower()
    name = ega.get("name", "").lower()
    ega_assertion = ega.get("metadata", {}).get("assertion", "")

    # If assertion specified in EGA metadata, use it
    if ega_assertion:
        # Parse comma-separated assertions
        specified = [a.strip() for a in str(ega_assertion).split(",")]
        selected = []
        for assertion in STANDARD_ASSERTIONS:
            for spec in specified:
                if spec.lower() in assertion["name"].lower() or spec.upper() == assertion["code"]:
                    selected.append(assertion)
                    break
        if selected:
            return selected

    # Select based on category/name keywords
    selected_assertions = []

    # Revenue-related EGAs
    if any(kw in name or kw in category for kw in ["revenue", "sales", "income", "수익"]):
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["EO", "C", "CO", "VA"]]

    # Inventory-related EGAs
    elif any(kw in name or kw in category for kw in ["inventory", "stock", "재고"]):
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["EO", "C", "VA"]]

    # Receivables-related EGAs
    elif any(kw in name or kw in category for kw in ["receivable", "ar", "매출채권"]):
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["EO", "VA", "RO"]]

    # Payables-related EGAs
    elif any(kw in name or kw in category for kw in ["payable", "ap", "매입채무", "부채"]):
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["C", "VA", "CO"]]

    # Fixed assets-related EGAs
    elif any(kw in name or kw in category for kw in ["fixed asset", "ppe", "property", "유형자산"]):
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["EO", "VA", "RO"]]

    # Default: select first 3 most common assertions
    if not selected_assertions:
        selected_assertions = [a for a in STANDARD_ASSERTIONS if a["code"] in ["EO", "C", "VA"]]

    return selected_assertions


def get_procedures_for_assertion(assertion_code: str, max_procedures: int = 2) -> List[str]:
    """
    Get audit procedures for a specific assertion.

    Args:
        assertion_code: Assertion code (e.g., "EO", "C")
        max_procedures: Maximum number of procedures to return

    Returns:
        List of procedure descriptions
    """
    procedures = ASSERTION_PROCEDURES.get(assertion_code, [])
    return procedures[:max_procedures]


# ============================================================================
# ESTIMATION HELPERS
# ============================================================================


def estimate_hours(task_level: TaskLevel, risk_level: RiskLevel) -> float:
    """
    Estimate hours based on task level and risk.

    Args:
        task_level: Task hierarchy level
        risk_level: Risk classification

    Returns:
        Estimated hours to complete
    """
    # Base hours by level
    level_hours = {
        TaskLevel.HIGH: 0.0,  # High level is a container, no direct work
        TaskLevel.MID: 4.0,
        TaskLevel.LOW: 2.0,
    }

    # Risk multiplier
    risk_multiplier = {
        RiskLevel.CRITICAL: 2.0,
        RiskLevel.HIGH: 1.5,
        RiskLevel.MEDIUM: 1.0,
        RiskLevel.LOW: 0.75,
    }

    base = level_hours.get(task_level, 2.0)
    multiplier = risk_multiplier.get(risk_level, 1.0)

    return round(base * multiplier, 1)


# ============================================================================
# TASK QUERY UTILITIES
# ============================================================================


def get_task_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for a list of tasks.

    Args:
        tasks: List of task dictionaries

    Returns:
        Summary dictionary with counts and statistics
    """
    if not tasks:
        return {
            "total": 0,
            "by_level": {},
            "by_status": {},
            "by_risk_level": {},
            "average_risk_score": 0,
            "total_estimated_hours": 0,
        }

    level_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    total_risk_score = 0
    total_hours = 0.0

    for task in tasks:
        # Count by level
        level = task.get("task_level", "High")
        level_counts[level] = level_counts.get(level, 0) + 1

        # Count by status
        status = task.get("status", "Pending")
        status_counts[status] = status_counts.get(status, 0) + 1

        # Count by risk level
        risk = task.get("risk_level", "medium")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

        # Sum risk scores
        total_risk_score += task.get("risk_score", 50)

        # Sum estimated hours
        total_hours += task.get("estimated_hours", 0)

    return {
        "total": len(tasks),
        "by_level": level_counts,
        "by_status": status_counts,
        "by_risk_level": risk_counts,
        "average_risk_score": total_risk_score / len(tasks) if tasks else 0,
        "total_estimated_hours": round(total_hours, 1),
    }


def filter_tasks_by_level(
    tasks: List[Dict[str, Any]],
    levels: List[str],
) -> List[Dict[str, Any]]:
    """
    Filter tasks by hierarchy level.

    Args:
        tasks: List of task dictionaries
        levels: List of levels to include ("High", "Mid", "Low")

    Returns:
        Filtered list of tasks
    """
    return [
        task for task in tasks
        if task.get("task_level", "High") in levels
    ]


def filter_tasks_by_status(
    tasks: List[Dict[str, Any]],
    statuses: List[str],
) -> List[Dict[str, Any]]:
    """
    Filter tasks by status.

    Args:
        tasks: List of task dictionaries
        statuses: List of statuses to include

    Returns:
        Filtered list of tasks
    """
    return [
        task for task in tasks
        if task.get("status", "Pending") in statuses
    ]


def get_task_children(
    tasks: List[Dict[str, Any]],
    parent_id: str,
) -> List[Dict[str, Any]]:
    """
    Get all child tasks of a parent task.

    Args:
        tasks: List of all task dictionaries
        parent_id: Parent task ID

    Returns:
        List of child tasks
    """
    return [
        task for task in tasks
        if task.get("parent_task_id") == parent_id
    ]


def get_task_tree(
    tasks: List[Dict[str, Any]],
    root_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build a tree structure from flat task list.

    Args:
        tasks: List of task dictionaries
        root_id: Optional root task ID (None for all roots)

    Returns:
        List of root tasks with nested 'children' field
    """
    # Build lookup for fast access
    task_map = {t["id"]: {**t, "children": []} for t in tasks}

    # Build tree
    roots = []

    for task in tasks:
        task_with_children = task_map[task["id"]]
        parent_id = task.get("parent_task_id")

        if parent_id and parent_id in task_map:
            # Add as child of parent
            task_map[parent_id]["children"].append(task_with_children)
        elif root_id is None or task["id"] == root_id:
            # Add as root
            roots.append(task_with_children)

    return roots


def sort_tasks_by_priority(
    tasks: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sort tasks by priority.

    Args:
        tasks: List of task dictionaries
        descending: Sort in descending order (highest first)

    Returns:
        Sorted list of tasks
    """
    return sorted(
        tasks,
        key=lambda x: x.get("priority", 50),
        reverse=descending,
    )


def sort_tasks_by_risk_score(
    tasks: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sort tasks by risk score.

    Args:
        tasks: List of task dictionaries
        descending: Sort in descending order (highest first)

    Returns:
        Sorted list of tasks
    """
    return sorted(
        tasks,
        key=lambda x: x.get("risk_score", 50),
        reverse=descending,
    )
