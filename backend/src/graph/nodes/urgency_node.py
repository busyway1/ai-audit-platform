"""
Urgency Calculation Node Implementation

This module implements the Urgency Calculation Node for calculating task urgency scores.
Urgency scores determine which tasks require human-in-the-loop (HITL) review.

Urgency Score Formula:
    urgency = (materiality_factor * 0.40) + (risk_factor * 0.35) + (ai_confidence_factor * 0.25)

Where:
    - materiality_factor: Based on task amount vs overall materiality threshold
    - risk_factor: Based on risk_score (0-100)
    - ai_confidence_factor: Inverse of AI confidence (lower confidence = higher urgency)

Key Features:
- Calculates urgency scores for all tasks
- Assigns urgency_score field to each task
- Identifies tasks exceeding HITL threshold
- Supports configurable weights and thresholds

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4 (BE-13.3)
"""

import logging
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


class UrgencyLevel(str, Enum):
    """Urgency level classification."""

    CRITICAL = "critical"  # Score >= 90
    HIGH = "high"          # Score >= 75
    MEDIUM = "medium"      # Score >= 50
    LOW = "low"            # Score < 50


# Default configuration for urgency calculation
DEFAULT_URGENCY_CONFIG = {
    # Weight factors (must sum to 1.0)
    "materiality_weight": 0.40,
    "risk_weight": 0.35,
    "ai_confidence_weight": 0.25,

    # Thresholds
    "hitl_threshold": 75.0,       # Threshold for HITL escalation
    "critical_threshold": 90.0,   # Critical urgency level
    "high_threshold": 75.0,       # High urgency level
    "medium_threshold": 50.0,     # Medium urgency level

    # Auto-processing
    "auto_approve_below": 30.0,   # Auto-approve tasks below this threshold

    # Materiality scaling
    "materiality_cap": 2.0,       # Cap materiality ratio at 2x
    "materiality_scale": 50.0,    # Scale factor for materiality
}


# Risk level to score mapping
RISK_SCORE_MAP = {
    "critical": 95,
    "high": 75,
    "medium": 50,
    "low": 25,
}


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class UrgencyCalculationResult:
    """Result of urgency calculation for all tasks."""

    success: bool
    tasks: List[Dict[str, Any]]
    total_tasks: int = 0
    tasks_above_threshold: int = 0
    highest_urgency: float = 0.0
    average_urgency: float = 0.0
    by_urgency_level: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskUrgencyInfo:
    """Urgency information for a single task."""

    task_id: str
    urgency_score: float
    urgency_level: UrgencyLevel
    materiality_factor: float
    risk_factor: float
    ai_confidence_factor: float
    requires_hitl: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_urgency_config(state: AuditState) -> Dict[str, Any]:
    """
    Get urgency configuration from state or use defaults.

    Args:
        state: Current AuditState

    Returns:
        Merged configuration dictionary
    """
    state_config = state.get("urgency_config", {})
    config = DEFAULT_URGENCY_CONFIG.copy()
    config.update(state_config)
    return config


def _parse_risk_score(task: Dict[str, Any]) -> float:
    """
    Parse risk score from task.

    Args:
        task: Task dictionary

    Returns:
        Risk score (0-100)
    """
    # Try direct risk_score field
    risk_score = task.get("risk_score")
    if risk_score is not None:
        try:
            return float(risk_score)
        except (ValueError, TypeError):
            pass

    # Fall back to risk_level mapping
    risk_level = task.get("risk_level", "medium")
    if isinstance(risk_level, str):
        risk_level = risk_level.lower()
    return RISK_SCORE_MAP.get(risk_level, 50)


def _calculate_materiality_factor(
    task: Dict[str, Any],
    overall_materiality: float,
    config: Dict[str, Any]
) -> float:
    """
    Calculate materiality factor for urgency score.

    Materiality factor is based on the ratio of task amount to overall materiality.
    Higher ratio = higher urgency (amounts close to or exceeding materiality are urgent).

    Args:
        task: Task dictionary
        overall_materiality: Overall audit materiality threshold
        config: Urgency configuration

    Returns:
        Materiality factor (0-100)
    """
    # Get task amount from various possible locations
    task_amount = (
        task.get("metadata", {}).get("amount", 0) or
        task.get("amount", 0) or
        task.get("estimated_amount", 0) or
        0
    )

    # If no materiality or amount, return default
    if overall_materiality <= 0 or task_amount <= 0:
        # No amount data - use risk-based default
        risk_score = _parse_risk_score(task)
        return risk_score * 0.6  # Moderate default based on risk

    # Calculate materiality ratio (capped)
    materiality_cap = config.get("materiality_cap", 2.0)
    materiality_ratio = min(task_amount / overall_materiality, materiality_cap)

    # Scale to 0-100
    materiality_scale = config.get("materiality_scale", 50.0)
    return min(materiality_ratio * materiality_scale, 100.0)


def _calculate_ai_confidence_factor(task: Dict[str, Any]) -> float:
    """
    Calculate AI confidence factor for urgency score.

    Lower AI confidence = higher urgency (uncertain results need review).

    Args:
        task: Task dictionary

    Returns:
        AI confidence factor (0-100)
    """
    # Get AI confidence from various possible locations
    ai_confidence = (
        task.get("metadata", {}).get("ai_confidence") or
        task.get("ai_confidence") or
        task.get("confidence") or
        0.8  # Default 80% confidence
    )

    # Ensure confidence is in [0, 1] range
    try:
        ai_confidence = float(ai_confidence)
        if ai_confidence > 1.0:
            ai_confidence = ai_confidence / 100.0  # Convert percentage
        ai_confidence = max(0.0, min(1.0, ai_confidence))
    except (ValueError, TypeError):
        ai_confidence = 0.8

    # Invert: lower confidence = higher urgency
    return (1.0 - ai_confidence) * 100.0


def calculate_task_urgency_score(
    task: Dict[str, Any],
    overall_materiality: float,
    config: Optional[Dict[str, Any]] = None
) -> TaskUrgencyInfo:
    """
    Calculate urgency score for a single task.

    Formula:
        urgency = (materiality_factor * 0.40) + (risk_factor * 0.35) + (ai_confidence_factor * 0.25)

    Args:
        task: Task dictionary with risk information
        overall_materiality: Overall audit materiality threshold
        config: Optional urgency configuration

    Returns:
        TaskUrgencyInfo with calculated urgency details

    Example:
        ```python
        task = {
            "id": "task-001",
            "risk_score": 75,
            "metadata": {"amount": 500000, "ai_confidence": 0.7}
        }

        result = calculate_task_urgency_score(task, 1000000.0)
        print(f"Urgency: {result.urgency_score}, Level: {result.urgency_level}")
        ```
    """
    if config is None:
        config = DEFAULT_URGENCY_CONFIG

    # Get weights
    materiality_weight = config.get("materiality_weight", 0.40)
    risk_weight = config.get("risk_weight", 0.35)
    ai_confidence_weight = config.get("ai_confidence_weight", 0.25)
    hitl_threshold = config.get("hitl_threshold", 75.0)

    # Calculate individual factors
    materiality_factor = _calculate_materiality_factor(task, overall_materiality, config)
    risk_factor = _parse_risk_score(task)
    ai_confidence_factor = _calculate_ai_confidence_factor(task)

    # Calculate weighted score
    urgency_score = (
        materiality_factor * materiality_weight +
        risk_factor * risk_weight +
        ai_confidence_factor * ai_confidence_weight
    )

    # Clamp to 0-100 range
    urgency_score = round(max(0.0, min(100.0, urgency_score)), 2)

    # Determine urgency level
    urgency_level = _get_urgency_level(urgency_score, config)

    # Determine if HITL is required
    requires_hitl = urgency_score >= hitl_threshold

    return TaskUrgencyInfo(
        task_id=task.get("id", task.get("task_id", "unknown")),
        urgency_score=urgency_score,
        urgency_level=urgency_level,
        materiality_factor=round(materiality_factor, 2),
        risk_factor=round(risk_factor, 2),
        ai_confidence_factor=round(ai_confidence_factor, 2),
        requires_hitl=requires_hitl,
    )


def _get_urgency_level(score: float, config: Dict[str, Any]) -> UrgencyLevel:
    """
    Determine urgency level based on score.

    Args:
        score: Urgency score (0-100)
        config: Urgency configuration

    Returns:
        UrgencyLevel enum value
    """
    critical = config.get("critical_threshold", 90.0)
    high = config.get("high_threshold", 75.0)
    medium = config.get("medium_threshold", 50.0)

    if score >= critical:
        return UrgencyLevel.CRITICAL
    elif score >= high:
        return UrgencyLevel.HIGH
    elif score >= medium:
        return UrgencyLevel.MEDIUM
    else:
        return UrgencyLevel.LOW


def calculate_urgency_scores(
    tasks: List[Dict[str, Any]],
    overall_materiality: float,
    config: Optional[Dict[str, Any]] = None
) -> UrgencyCalculationResult:
    """
    Calculate urgency scores for all tasks.

    Args:
        tasks: List of task dictionaries
        overall_materiality: Overall audit materiality threshold
        config: Optional urgency configuration

    Returns:
        UrgencyCalculationResult with updated tasks and statistics

    Example:
        ```python
        tasks = [
            {"id": "T001", "risk_score": 85, "metadata": {"amount": 800000}},
            {"id": "T002", "risk_score": 45, "metadata": {"amount": 100000}},
        ]

        result = calculate_urgency_scores(tasks, 1000000.0)
        print(f"Tasks above threshold: {result.tasks_above_threshold}")
        ```
    """
    if config is None:
        config = DEFAULT_URGENCY_CONFIG

    if not tasks:
        return UrgencyCalculationResult(
            success=True,
            tasks=[],
            total_tasks=0,
            errors=["No tasks provided for urgency calculation"],
        )

    updated_tasks: List[Dict[str, Any]] = []
    errors: List[str] = []
    urgency_scores: List[float] = []
    level_counts: Dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    hitl_threshold = config.get("hitl_threshold", 75.0)
    tasks_above_threshold = 0

    for task in tasks:
        try:
            # Calculate urgency for this task
            urgency_info = calculate_task_urgency_score(
                task, overall_materiality, config
            )

            # Create updated task with urgency fields
            updated_task = task.copy()
            updated_task["urgency_score"] = urgency_info.urgency_score
            updated_task["urgency_level"] = urgency_info.urgency_level.value
            updated_task["requires_hitl"] = urgency_info.requires_hitl

            # Add breakdown to metadata
            if "metadata" not in updated_task:
                updated_task["metadata"] = {}
            updated_task["metadata"]["urgency_breakdown"] = {
                "materiality_factor": urgency_info.materiality_factor,
                "risk_factor": urgency_info.risk_factor,
                "ai_confidence_factor": urgency_info.ai_confidence_factor,
            }

            updated_tasks.append(updated_task)
            urgency_scores.append(urgency_info.urgency_score)

            # Update statistics
            level_counts[urgency_info.urgency_level.value] += 1
            if urgency_info.requires_hitl:
                tasks_above_threshold += 1

        except Exception as e:
            task_id = task.get("id", task.get("task_id", "unknown"))
            errors.append(f"Error calculating urgency for task {task_id}: {str(e)}")
            # Keep original task without urgency score
            updated_tasks.append(task)

    # Calculate statistics
    highest_urgency = max(urgency_scores) if urgency_scores else 0.0
    average_urgency = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0.0

    return UrgencyCalculationResult(
        success=len(errors) == 0,
        tasks=updated_tasks,
        total_tasks=len(tasks),
        tasks_above_threshold=tasks_above_threshold,
        highest_urgency=round(highest_urgency, 2),
        average_urgency=round(average_urgency, 2),
        by_urgency_level=level_counts,
        errors=errors,
        metadata={
            "hitl_threshold": hitl_threshold,
            "overall_materiality": overall_materiality,
            "config": config,
        },
    )


# ============================================================================
# LANGGRAPH NODE
# ============================================================================


async def urgency_node(state: AuditState) -> Dict[str, Any]:
    """
    LangGraph node for calculating urgency scores for all tasks.

    This node:
    1. Retrieves tasks from state
    2. Calculates urgency score for each task using weighted formula
    3. Assigns urgency_score and urgency_level to each task
    4. Identifies tasks requiring HITL review
    5. Updates state with scored tasks

    Args:
        state: Current AuditState with tasks and urgency_config

    Returns:
        Updated state with:
        - tasks: Tasks updated with urgency_score and urgency_level
        - messages: Status message about urgency calculation

    Example:
        ```python
        state = {
            "project_id": "proj-123",
            "overall_materiality": 1000000.0,
            "tasks": [
                {
                    "id": "task-001",
                    "name": "Revenue Testing",
                    "risk_score": 75,
                    "metadata": {"amount": 500000, "ai_confidence": 0.7}
                }
            ],
            "urgency_config": {
                "hitl_threshold": 75.0,
                "materiality_weight": 0.40,
                "risk_weight": 0.35,
                "ai_confidence_weight": 0.25
            },
        }

        result = await urgency_node(state)
        print(f"Tasks with urgency scores: {len(result['tasks'])}")
        for task in result['tasks']:
            print(f"  {task['name']}: {task['urgency_score']} ({task['urgency_level']})")
        ```

    Note:
        If no urgency_config is provided in state, defaults are used:
        - materiality_weight: 0.40
        - risk_weight: 0.35
        - ai_confidence_weight: 0.25
        - hitl_threshold: 75.0
    """
    logger.info("[Parent Graph] Urgency Node: Calculating task urgency scores")

    # Get configuration
    config = _get_urgency_config(state)
    overall_materiality = state.get("overall_materiality", 0.0)
    tasks = state.get("tasks", [])

    if not tasks:
        logger.warning("[Urgency Node] No tasks found in state")
        return {
            "tasks": [],
            "messages": [
                HumanMessage(
                    content="[Urgency Node] 긴급도 계산 대상 작업이 없습니다.",
                    name="UrgencyNode"
                )
            ],
        }

    # Calculate urgency scores
    result = calculate_urgency_scores(tasks, overall_materiality, config)

    # Build summary message
    hitl_threshold = config.get("hitl_threshold", 75.0)
    message_parts = [
        f"[Urgency Node] {result.total_tasks}개 작업의 긴급도 계산 완료",
        f"임계값({hitl_threshold}) 초과: {result.tasks_above_threshold}개",
        f"평균 긴급도: {result.average_urgency:.1f}",
        f"최고 긴급도: {result.highest_urgency:.1f}",
    ]

    # Add level breakdown
    level_str = ", ".join([
        f"{level.upper()}: {count}"
        for level, count in result.by_urgency_level.items()
        if count > 0
    ])
    if level_str:
        message_parts.append(f"레벨별: {level_str}")

    if result.errors:
        message_parts.append(f"오류: {len(result.errors)}건")

    summary_message = " | ".join(message_parts)
    logger.info(summary_message)

    return {
        "tasks": result.tasks,
        "messages": [
            HumanMessage(
                content=summary_message,
                name="UrgencyNode"
            )
        ],
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_urgency_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for task urgency scores.

    Args:
        tasks: List of tasks with urgency_score field

    Returns:
        Summary dictionary with urgency statistics
    """
    if not tasks:
        return {
            "total": 0,
            "by_level": {},
            "average_score": 0,
            "max_score": 0,
            "min_score": 0,
            "tasks_requiring_hitl": 0,
        }

    scores = [t.get("urgency_score", 0) for t in tasks]
    level_counts: Dict[str, int] = {}

    for task in tasks:
        level = task.get("urgency_level", "low")
        level_counts[level] = level_counts.get(level, 0) + 1

    hitl_count = sum(1 for t in tasks if t.get("requires_hitl", False))

    return {
        "total": len(tasks),
        "by_level": level_counts,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "tasks_requiring_hitl": hitl_count,
    }


def filter_tasks_by_urgency(
    tasks: List[Dict[str, Any]],
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    levels: Optional[List[str]] = None,
    requires_hitl: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Filter tasks by urgency criteria.

    Args:
        tasks: List of tasks with urgency fields
        min_score: Minimum urgency score (inclusive)
        max_score: Maximum urgency score (inclusive)
        levels: List of urgency levels to include
        requires_hitl: Filter by HITL requirement

    Returns:
        Filtered list of tasks
    """
    result = tasks

    if min_score is not None:
        result = [t for t in result if t.get("urgency_score", 0) >= min_score]

    if max_score is not None:
        result = [t for t in result if t.get("urgency_score", 0) <= max_score]

    if levels is not None:
        result = [t for t in result if t.get("urgency_level", "low") in levels]

    if requires_hitl is not None:
        result = [t for t in result if t.get("requires_hitl", False) == requires_hitl]

    return result


def sort_tasks_by_urgency(
    tasks: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sort tasks by urgency score.

    Args:
        tasks: List of tasks with urgency_score field
        descending: Sort in descending order (highest first)

    Returns:
        Sorted list of tasks
    """
    return sorted(
        tasks,
        key=lambda x: x.get("urgency_score", 0),
        reverse=descending,
    )


def get_hitl_candidates(
    tasks: List[Dict[str, Any]],
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Get tasks that are candidates for HITL review.

    Args:
        tasks: List of tasks with urgency fields
        threshold: Optional custom threshold (uses task's requires_hitl if None)

    Returns:
        List of tasks requiring HITL review, sorted by urgency
    """
    if threshold is not None:
        candidates = [t for t in tasks if t.get("urgency_score", 0) >= threshold]
    else:
        candidates = [t for t in tasks if t.get("requires_hitl", False)]

    return sort_tasks_by_urgency(candidates, descending=True)
