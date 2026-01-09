"""
HITL Interrupt Node Implementation

This module implements the Human-in-the-Loop (HITL) interrupt node for escalation handling.
The node pauses workflow execution when tasks exceed urgency thresholds, allowing human
judgment for critical audit decisions.

Features:
1. Trigger on urgency_score >= configurable threshold
2. interrupt() call for workflow pause
3. Resume after user response (approve/reject/escalate)
4. Integration with hitl_requests table via Supabase

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4 (LangGraph Integration)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

from langgraph.types import interrupt
from langchain_core.messages import HumanMessage

from ...graph.state import AuditState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class HITLRequestType(str, Enum):
    """Types of HITL escalation requests."""
    URGENCY_THRESHOLD = "urgency_threshold"  # High urgency task
    MATERIALITY_EXCEEDED = "materiality_exceeded"  # Materiality threshold exceeded
    PROFESSIONAL_JUDGMENT = "professional_judgment"  # Requires human judgment
    ANOMALY_DETECTED = "anomaly_detected"  # AI detected anomaly
    EXTERNAL_REVIEW = "external_review"  # Requires external expert review


class HITLRequestStatus(str, Enum):
    """Status of HITL requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class HITLUrgencyLevel(str, Enum):
    """Urgency levels for HITL requests."""
    CRITICAL = "critical"  # Score >= 90
    HIGH = "high"         # Score >= 75
    MEDIUM = "medium"     # Score >= 50
    LOW = "low"           # Score < 50


@dataclass
class HITLRequest:
    """Represents a single HITL escalation request."""
    request_id: str
    task_id: str
    project_id: str
    request_type: HITLRequestType
    urgency_score: float
    urgency_level: HITLUrgencyLevel
    title: str
    description: str
    context: Dict[str, Any]
    status: HITLRequestStatus = HITLRequestStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    response: Optional[Dict[str, Any]] = None


@dataclass
class HITLResponse:
    """User's response to an HITL request."""
    request_id: str
    action: str  # "approve", "reject", "escalate"
    comment: Optional[str] = None
    modified_values: Optional[Dict[str, Any]] = None
    responded_by: Optional[str] = None
    responded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_URGENCY_CONFIG = {
    "hitl_threshold": 75.0,  # Default threshold for HITL escalation
    "critical_threshold": 90.0,  # Critical urgency level
    "high_threshold": 75.0,  # High urgency level
    "medium_threshold": 50.0,  # Medium urgency level
    "auto_approve_below": 30.0,  # Auto-approve tasks below this
    "materiality_weight": 0.40,
    "risk_weight": 0.35,
    "ai_confidence_weight": 0.25,
}


# ============================================================================
# HITL INTERRUPT NODE
# ============================================================================

async def hitl_interrupt_node(state: AuditState) -> Dict[str, Any]:
    """
    Node for handling HITL escalations based on urgency scores.

    This node:
    1. Evaluates tasks for urgency threshold violations
    2. Creates HITL requests for high-urgency tasks
    3. Uses interrupt() to pause workflow for human review
    4. Processes human response and updates workflow state

    Args:
        state: Current AuditState with tasks and urgency_config

    Returns:
        Updated state with:
        - tasks: Updated with HITL response decisions
        - next_action: "CONTINUE" or "INTERRUPT" based on response

    Example:
        ```python
        state = {
            "tasks": [
                {"task_id": "T001", "urgency_score": 85, ...},
                {"task_id": "T002", "urgency_score": 45, ...},
            ],
            "urgency_config": {"hitl_threshold": 75.0},
            ...
        }

        result = await hitl_interrupt_node(state)
        # T001 triggers HITL, T002 proceeds automatically
        ```

    Integration with Frontend:
        ```python
        # When interrupt triggers:
        snapshot = await graph.aget_state(config)
        if snapshot.next == ("__interrupt__",):
            hitl_data = snapshot.interrupts[0]
            # Frontend displays HITL request to user
            # User provides response
            await graph.aupdate_state(config, {
                "hitl_response": {"action": "approve", "comment": "Proceed"}
            })
            # Resume workflow
            await graph.ainvoke(None, config)
        ```
    """
    logger.info("[HITL Interrupt Node] Evaluating tasks for escalation")

    # Get configuration
    urgency_config = state.get("urgency_config", DEFAULT_URGENCY_CONFIG)
    hitl_threshold = urgency_config.get("hitl_threshold", DEFAULT_URGENCY_CONFIG["hitl_threshold"])

    # Get tasks requiring HITL review
    tasks = state.get("tasks", [])
    tasks_requiring_hitl = _identify_hitl_tasks(tasks, hitl_threshold)

    if not tasks_requiring_hitl:
        logger.info("[HITL Interrupt Node] No tasks require HITL escalation")
        return {
            "next_action": "CONTINUE",
            "messages": [
                HumanMessage(
                    content="[HITL] 모든 작업이 긴급도 임계값 이하입니다. 자동 진행합니다.",
                    name="HITL"
                )
            ]
        }

    logger.info(f"[HITL Interrupt Node] {len(tasks_requiring_hitl)} tasks require HITL review")

    # Create HITL requests for each task
    hitl_requests = _create_hitl_requests(
        tasks=tasks_requiring_hitl,
        project_id=state.get("project_id", ""),
        urgency_config=urgency_config
    )

    # Pause workflow and wait for human review
    logger.info("[HITL Interrupt Node] Interrupting workflow for human review")
    response = interrupt({
        "type": "hitl_escalation",
        "message": f"{len(hitl_requests)}개 작업이 긴급도 임계값({hitl_threshold})을 초과하여 검토가 필요합니다.",
        "requests": [_request_to_dict(r) for r in hitl_requests],
        "threshold": hitl_threshold,
        "actions": ["approve_all", "reject_all", "review_individual"]
    })

    # Process human response
    return _process_hitl_response(response, tasks, hitl_requests)


async def process_individual_hitl_node(state: AuditState) -> Dict[str, Any]:
    """
    Node for individual HITL request processing.

    This node handles cases where users want to review and respond to
    HITL requests one at a time instead of batch processing.

    Args:
        state: Current AuditState with pending HITL requests

    Returns:
        Updated state with individual task decisions
    """
    logger.info("[HITL Individual] Processing individual HITL requests")

    pending_requests = state.get("pending_hitl_requests", [])

    if not pending_requests:
        logger.info("[HITL Individual] No pending HITL requests")
        return {
            "next_action": "CONTINUE",
            "pending_hitl_requests": []
        }

    # Process first pending request
    current_request = pending_requests[0]

    logger.info(f"[HITL Individual] Reviewing request: {current_request.get('request_id')}")

    response = interrupt({
        "type": "hitl_individual_review",
        "message": "개별 작업에 대한 판단을 요청합니다.",
        "request": current_request,
        "actions": ["approve", "reject", "escalate", "skip"]
    })

    action = response.get("action", "skip")

    # Update the specific task
    tasks = state.get("tasks", [])
    updated_tasks = _update_task_from_hitl_response(
        tasks=tasks,
        task_id=current_request.get("task_id"),
        action=action,
        comment=response.get("comment", "")
    )

    # Remove processed request from pending
    remaining_requests = pending_requests[1:]

    return {
        "tasks": updated_tasks,
        "pending_hitl_requests": remaining_requests,
        "next_action": "CONTINUE" if not remaining_requests else "REVIEW_NEXT",
        "messages": [
            HumanMessage(
                content=f"[HITL] 작업 {current_request.get('task_id')}: {action}. "
                        f"남은 검토 대기: {len(remaining_requests)}개",
                name="HITL"
            )
        ]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _identify_hitl_tasks(
    tasks: List[Dict[str, Any]],
    threshold: float
) -> List[Dict[str, Any]]:
    """
    Identify tasks that require HITL review based on urgency score.

    Args:
        tasks: List of task dictionaries
        threshold: Urgency threshold for HITL escalation

    Returns:
        List of tasks exceeding threshold
    """
    return [
        task for task in tasks
        if (task.get("urgency_score") or 0) >= threshold
        and task.get("status") not in ["completed", "skipped", "hitl_approved"]
    ]


def _get_urgency_level(score: float, config: Dict[str, Any]) -> HITLUrgencyLevel:
    """
    Determine urgency level based on score and configuration.

    Args:
        score: Urgency score (0-100)
        config: Urgency configuration

    Returns:
        HITLUrgencyLevel enum value
    """
    critical = config.get("critical_threshold", 90.0)
    high = config.get("high_threshold", 75.0)
    medium = config.get("medium_threshold", 50.0)

    if score >= critical:
        return HITLUrgencyLevel.CRITICAL
    elif score >= high:
        return HITLUrgencyLevel.HIGH
    elif score >= medium:
        return HITLUrgencyLevel.MEDIUM
    else:
        return HITLUrgencyLevel.LOW


def _determine_request_type(task: Dict[str, Any]) -> HITLRequestType:
    """
    Determine the type of HITL request based on task characteristics.

    Args:
        task: Task dictionary

    Returns:
        HITLRequestType enum value
    """
    # Check for specific conditions
    metadata = task.get("metadata", {})

    if metadata.get("anomaly_detected"):
        return HITLRequestType.ANOMALY_DETECTED

    if metadata.get("materiality_exceeded"):
        return HITLRequestType.MATERIALITY_EXCEEDED

    if metadata.get("requires_expert"):
        return HITLRequestType.EXTERNAL_REVIEW

    if metadata.get("requires_judgment"):
        return HITLRequestType.PROFESSIONAL_JUDGMENT

    # Default: urgency threshold exceeded
    return HITLRequestType.URGENCY_THRESHOLD


def _create_hitl_requests(
    tasks: List[Dict[str, Any]],
    project_id: str,
    urgency_config: Dict[str, Any]
) -> List[HITLRequest]:
    """
    Create HITL request objects for tasks requiring review.

    Args:
        tasks: List of tasks requiring HITL review
        project_id: Current project ID
        urgency_config: Urgency configuration

    Returns:
        List of HITLRequest objects
    """
    requests = []

    for task in tasks:
        task_id = task.get("task_id", task.get("id", "unknown"))
        urgency_score = task.get("urgency_score", 0)

        request = HITLRequest(
            request_id=f"HITL-{project_id}-{task_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            project_id=project_id,
            request_type=_determine_request_type(task),
            urgency_score=urgency_score,
            urgency_level=_get_urgency_level(urgency_score, urgency_config),
            title=task.get("name", task.get("title", f"Task {task_id}")),
            description=task.get("description", ""),
            context={
                "category": task.get("category", ""),
                "risk_level": task.get("risk_level", ""),
                "risk_score": task.get("risk_score", 0),
                "procedure": task.get("procedure", ""),
                "sampling_size": task.get("sampling_size", 0),
                "estimated_hours": task.get("estimated_hours", 0),
                "metadata": task.get("metadata", {})
            }
        )
        requests.append(request)

    # Sort by urgency score (highest first)
    requests.sort(key=lambda r: r.urgency_score, reverse=True)

    return requests


def _request_to_dict(request: HITLRequest) -> Dict[str, Any]:
    """
    Convert HITLRequest to dictionary for serialization.

    Args:
        request: HITLRequest object

    Returns:
        Dictionary representation
    """
    return {
        "request_id": request.request_id,
        "task_id": request.task_id,
        "project_id": request.project_id,
        "request_type": request.request_type.value,
        "urgency_score": request.urgency_score,
        "urgency_level": request.urgency_level.value,
        "title": request.title,
        "description": request.description,
        "context": request.context,
        "status": request.status.value,
        "created_at": request.created_at
    }


def _process_hitl_response(
    response: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    requests: List[HITLRequest]
) -> Dict[str, Any]:
    """
    Process human response to HITL escalation.

    Args:
        response: User's response from interrupt
        tasks: Original task list
        requests: HITL requests that were presented

    Returns:
        Updated state dictionary
    """
    action = response.get("action", "approve_all")
    comment = response.get("comment", "")
    individual_responses = response.get("individual_responses", {})

    request_task_ids = {r.task_id for r in requests}

    if action == "approve_all":
        logger.info("[HITL] All tasks approved by human reviewer")
        updated_tasks = [
            {**task, "hitl_status": "approved", "hitl_comment": comment}
            if task.get("task_id", task.get("id")) in request_task_ids
            else task
            for task in tasks
        ]
        return {
            "tasks": updated_tasks,
            "next_action": "CONTINUE",
            "messages": [
                HumanMessage(
                    content=f"[HITL] {len(requests)}개 작업이 승인되었습니다. 워크플로우를 계속합니다.",
                    name="HITL"
                )
            ]
        }

    elif action == "reject_all":
        logger.info("[HITL] All tasks rejected by human reviewer")
        updated_tasks = [
            {**task, "hitl_status": "rejected", "hitl_comment": comment, "status": "skipped"}
            if task.get("task_id", task.get("id")) in request_task_ids
            else task
            for task in tasks
        ]
        return {
            "tasks": updated_tasks,
            "next_action": "CONTINUE",
            "messages": [
                HumanMessage(
                    content=f"[HITL] {len(requests)}개 작업이 거부되었습니다. 해당 작업을 건너뜁니다.",
                    name="HITL"
                )
            ]
        }

    elif action == "review_individual":
        logger.info("[HITL] User requested individual review")
        return {
            "pending_hitl_requests": [_request_to_dict(r) for r in requests],
            "next_action": "REVIEW_INDIVIDUAL",
            "messages": [
                HumanMessage(
                    content="[HITL] 개별 검토 모드로 전환합니다.",
                    name="HITL"
                )
            ]
        }

    else:
        # Handle individual responses in batch
        updated_tasks = tasks.copy()
        for task_id, task_response in individual_responses.items():
            updated_tasks = _update_task_from_hitl_response(
                tasks=updated_tasks,
                task_id=task_id,
                action=task_response.get("action", "approve"),
                comment=task_response.get("comment", "")
            )

        return {
            "tasks": updated_tasks,
            "next_action": "CONTINUE",
            "messages": [
                HumanMessage(
                    content=f"[HITL] 개별 응답 처리 완료. 워크플로우를 계속합니다.",
                    name="HITL"
                )
            ]
        }


def _update_task_from_hitl_response(
    tasks: List[Dict[str, Any]],
    task_id: str,
    action: str,
    comment: str
) -> List[Dict[str, Any]]:
    """
    Update a specific task based on HITL response.

    Args:
        tasks: List of all tasks
        task_id: ID of task to update
        action: User's action (approve/reject/escalate)
        comment: User's comment

    Returns:
        Updated task list
    """
    updated = []
    for task in tasks:
        current_id = task.get("task_id", task.get("id"))
        if current_id == task_id:
            if action == "approve":
                updated.append({
                    **task,
                    "hitl_status": "approved",
                    "hitl_comment": comment
                })
            elif action == "reject":
                updated.append({
                    **task,
                    "hitl_status": "rejected",
                    "hitl_comment": comment,
                    "status": "skipped"
                })
            elif action == "escalate":
                updated.append({
                    **task,
                    "hitl_status": "escalated",
                    "hitl_comment": comment,
                    "requires_partner_review": True
                })
            else:
                updated.append(task)
        else:
            updated.append(task)

    return updated


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_hitl_summary(state: AuditState) -> Dict[str, Any]:
    """
    Get summary of HITL-related information from state.

    Args:
        state: Current AuditState

    Returns:
        Summary dictionary with HITL statistics
    """
    tasks = state.get("tasks", [])
    urgency_config = state.get("urgency_config", DEFAULT_URGENCY_CONFIG)
    threshold = urgency_config.get("hitl_threshold", DEFAULT_URGENCY_CONFIG["hitl_threshold"])

    hitl_tasks = _identify_hitl_tasks(tasks, threshold)

    approved = [t for t in tasks if t.get("hitl_status") == "approved"]
    rejected = [t for t in tasks if t.get("hitl_status") == "rejected"]
    escalated = [t for t in tasks if t.get("hitl_status") == "escalated"]
    pending = [t for t in tasks if t.get("hitl_status") == "pending"]

    return {
        "total_tasks": len(tasks),
        "hitl_threshold": threshold,
        "tasks_above_threshold": len(hitl_tasks),
        "approved": len(approved),
        "rejected": len(rejected),
        "escalated": len(escalated),
        "pending": len(pending),
        "highest_urgency": max((t.get("urgency_score", 0) for t in tasks), default=0),
        "average_urgency": sum(t.get("urgency_score", 0) for t in tasks) / max(len(tasks), 1)
    }


def should_trigger_hitl(task: Dict[str, Any], config: Dict[str, Any] = None) -> bool:
    """
    Check if a single task should trigger HITL escalation.

    Args:
        task: Task dictionary
        config: Optional urgency configuration

    Returns:
        True if task should trigger HITL
    """
    if config is None:
        config = DEFAULT_URGENCY_CONFIG

    threshold = config.get("hitl_threshold", DEFAULT_URGENCY_CONFIG["hitl_threshold"])
    urgency_score = task.get("urgency_score", 0)

    # Don't trigger for already processed tasks
    if task.get("hitl_status") in ["approved", "rejected", "escalated"]:
        return False

    # Don't trigger for completed or skipped tasks
    if task.get("status") in ["completed", "skipped"]:
        return False

    return urgency_score >= threshold


def calculate_urgency_score(
    task: Dict[str, Any],
    materiality: float,
    config: Dict[str, Any] = None
) -> float:
    """
    Calculate urgency score for a task.

    This is a utility function that can be used by other nodes
    to calculate urgency scores consistently.

    Args:
        task: Task dictionary with risk information
        materiality: Overall materiality threshold
        config: Optional urgency configuration

    Returns:
        Calculated urgency score (0-100)

    Formula:
        urgency = (materiality_factor * 0.40) + (risk_factor * 0.35) + (ai_confidence_factor * 0.25)

    Where:
        - materiality_factor: Based on task amount vs materiality threshold
        - risk_factor: Based on risk_score (0-100)
        - ai_confidence_factor: Inverse of AI confidence (lower confidence = higher urgency)
    """
    if config is None:
        config = DEFAULT_URGENCY_CONFIG

    materiality_weight = config.get("materiality_weight", 0.40)
    risk_weight = config.get("risk_weight", 0.35)
    ai_confidence_weight = config.get("ai_confidence_weight", 0.25)

    # Materiality factor
    task_amount = task.get("metadata", {}).get("amount", 0)
    if materiality > 0 and task_amount > 0:
        materiality_ratio = min(task_amount / materiality, 2.0)  # Cap at 2x
        materiality_factor = min(materiality_ratio * 50, 100)  # Scale to 0-100
    else:
        materiality_factor = 50  # Default if no amount

    # Risk factor (direct from risk_score)
    risk_factor = task.get("risk_score", 50)

    # AI confidence factor (inverse)
    ai_confidence = task.get("metadata", {}).get("ai_confidence", 0.8)
    ai_confidence_factor = (1 - ai_confidence) * 100  # Lower confidence = higher urgency

    # Calculate weighted score
    urgency_score = (
        materiality_factor * materiality_weight +
        risk_factor * risk_weight +
        ai_confidence_factor * ai_confidence_weight
    )

    return round(min(max(urgency_score, 0), 100), 2)
