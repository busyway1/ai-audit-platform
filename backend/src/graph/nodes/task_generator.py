"""
Task Generator Node Implementation

This module implements the Task Generation Node for creating a 3-level task hierarchy
from EGAs (Expected General Activities) extracted from Assigned Workflow documents.

The 3-Level Hierarchy:
1. High Level (EGA) - Top-level tasks representing overall audit objectives
2. Mid Level (Assertion) - Mid-level tasks for financial statement assertions
3. Low Level (Procedure) - Low-level tasks for specific audit procedures

Key Features:
- Generates hierarchical tasks from EGAs
- Assigns parent_task_id for proper linking
- Sets task_level field (High/Mid/Low)
- Calculates risk scores based on EGA risk levels
- Enriches tasks with metadata for database storage

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from ...graph.state import AuditState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class TaskLevel(str, Enum):
    """Task hierarchy level classification."""

    HIGH = "High"  # EGA level - top-level audit objectives
    MID = "Mid"    # Assertion level - financial statement assertions
    LOW = "Low"    # Procedure level - specific audit procedures


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "Pending"
    IN_PROGRESS = "In-Progress"
    REVIEW_REQUIRED = "Review-Required"
    COMPLETED = "Completed"
    FAILED = "Failed"


class RiskLevel(str, Enum):
    """Risk level classification aligned with EGA risk levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Mapping from EGA risk levels to numeric risk scores
RISK_SCORE_MAP = {
    RiskLevel.CRITICAL: 95,
    RiskLevel.HIGH: 75,
    RiskLevel.MEDIUM: 50,
    RiskLevel.LOW: 25,
    "critical": 95,
    "high": 75,
    "medium": 50,
    "low": 25,
}

# Standard financial statement assertions for audit tasks
STANDARD_ASSERTIONS = [
    {
        "name": "Existence/Occurrence",
        "description": "Assets, liabilities, and equity interests exist; recorded transactions occurred",
        "code": "EO",
    },
    {
        "name": "Completeness",
        "description": "All transactions and accounts that should be recorded have been recorded",
        "code": "C",
    },
    {
        "name": "Valuation/Accuracy",
        "description": "Assets, liabilities, and equity interests are valued appropriately",
        "code": "VA",
    },
    {
        "name": "Rights and Obligations",
        "description": "The entity holds or controls rights to assets; liabilities are obligations",
        "code": "RO",
    },
    {
        "name": "Presentation and Disclosure",
        "description": "Financial information is appropriately presented and disclosed",
        "code": "PD",
    },
    {
        "name": "Cut-off",
        "description": "Transactions are recorded in the correct accounting period",
        "code": "CO",
    },
]

# Standard audit procedures mapped by assertion
ASSERTION_PROCEDURES = {
    "EO": [  # Existence/Occurrence
        "Physical inspection of assets",
        "Third-party confirmation",
        "Examination of supporting documentation",
        "Review of subsequent events",
    ],
    "C": [  # Completeness
        "Analytical procedures for unusual patterns",
        "Cut-off testing at period end",
        "Search for unrecorded liabilities",
        "Bank reconciliation review",
    ],
    "VA": [  # Valuation/Accuracy
        "Recalculation of amounts",
        "Review of valuation methodologies",
        "Testing of pricing accuracy",
        "Assessment of allowances and provisions",
    ],
    "RO": [  # Rights and Obligations
        "Review of contracts and agreements",
        "Verification of ownership documents",
        "Inquiry of management",
        "Legal confirmation",
    ],
    "PD": [  # Presentation and Disclosure
        "Review of financial statement presentation",
        "Assessment of disclosure completeness",
        "Verification of note accuracy",
        "Review of related party disclosures",
    ],
    "CO": [  # Cut-off
        "Testing of transactions near period end",
        "Review of subsequent period entries",
        "Examination of shipping documents",
        "Analysis of billing timing",
    ],
}


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class GeneratedTask:
    """
    Represents a generated audit task in the 3-level hierarchy.

    Attributes:
        id: Unique identifier for the task
        project_id: Associated audit project ID
        ega_id: Source EGA ID (for traceability)
        parent_task_id: Parent task ID for hierarchy linking
        task_level: Hierarchy level (High/Mid/Low)
        name: Task name/title
        description: Detailed description
        category: Account category (e.g., "Revenue", "Inventory")
        risk_level: Risk classification
        risk_score: Numeric risk score (0-100)
        status: Current task status
        priority: Task priority (1-100)
        assertion: Financial statement assertion (for Mid/Low level)
        procedure_type: Type of audit procedure (for Low level)
        estimated_hours: Estimated time to complete
        assigned_to: Staff assignment (optional)
        due_date: Target completion date (optional)
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    project_id: str
    ega_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    task_level: TaskLevel = TaskLevel.HIGH
    name: str = ""
    description: str = ""
    category: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: int = 50
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 50
    assertion: Optional[str] = None
    procedure_type: Optional[str] = None
    estimated_hours: float = 0.0
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for state storage and database."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "ega_id": self.ega_id,
            "parent_task_id": self.parent_task_id,
            "task_level": self.task_level.value if isinstance(self.task_level, TaskLevel) else self.task_level,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else self.risk_level,
            "risk_score": self.risk_score,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "assertion": self.assertion,
            "procedure_type": self.procedure_type,
            "estimated_hours": self.estimated_hours,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "metadata": self.metadata,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "updated_at": self.updated_at or datetime.utcnow().isoformat(),
        }


@dataclass
class TaskGenerationResult:
    """Result of task generation from EGAs."""

    success: bool
    tasks: List[GeneratedTask]
    high_level_count: int = 0
    mid_level_count: int = 0
    low_level_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _generate_task_id() -> str:
    """Generate a unique task ID."""
    return f"task-{uuid.uuid4().hex[:12]}"


def _parse_risk_level(value: Any) -> RiskLevel:
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


def _calculate_risk_score(risk_level: RiskLevel) -> int:
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


def _select_assertions_for_ega(ega: Dict[str, Any]) -> List[Dict[str, str]]:
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


def _get_procedures_for_assertion(assertion_code: str, max_procedures: int = 2) -> List[str]:
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


def _estimate_hours(task_level: TaskLevel, risk_level: RiskLevel) -> float:
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
# TASK GENERATION FUNCTIONS
# ============================================================================


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
    risk_level = _parse_risk_level(ega.get("risk_level"))
    risk_score = _calculate_risk_score(risk_level)

    return GeneratedTask(
        id=_generate_task_id(),
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
        estimated_hours=_estimate_hours(TaskLevel.HIGH, risk_level),
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
    assertions = _select_assertions_for_ega(ega)

    for assertion in assertions:
        # Adjust risk level for assertion (can be slightly different from EGA)
        risk_level = high_task.risk_level

        mid_task = GeneratedTask(
            id=_generate_task_id(),
            project_id=high_task.project_id,
            ega_id=high_task.ega_id,
            parent_task_id=high_task.id,  # Link to High level
            task_level=TaskLevel.MID,
            name=f"{high_task.name} - {assertion['name']}",
            description=f"Test {assertion['name']}: {assertion['description']}",
            category=high_task.category,
            risk_level=risk_level,
            risk_score=_calculate_risk_score(risk_level),
            status=TaskStatus.PENDING,
            priority=high_task.priority,
            assertion=assertion["name"],
            estimated_hours=_estimate_hours(TaskLevel.MID, risk_level),
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
    procedures = _get_procedures_for_assertion(assertion_code)

    for idx, procedure in enumerate(procedures):
        low_task = GeneratedTask(
            id=_generate_task_id(),
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
            estimated_hours=_estimate_hours(TaskLevel.LOW, mid_task.risk_level),
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


# ============================================================================
# LANGGRAPH NODE
# ============================================================================


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
            risk_level = _parse_risk_level(enriched_task.get("risk_level"))
            enriched_task["risk_score"] = _calculate_risk_score(risk_level)

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


# ============================================================================
# UTILITY FUNCTIONS
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
