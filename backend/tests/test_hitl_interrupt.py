"""
Comprehensive Unit Tests for HITL Interrupt Node

Target Coverage:
- hitl_interrupt_node main functionality
- process_individual_hitl_node for individual review
- Helper functions (_identify_hitl_tasks, _get_urgency_level, etc.)
- Utility functions (get_hitl_summary, should_trigger_hitl, calculate_urgency_score)

Coverage Target: 80%+
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List
from datetime import datetime

from src.graph.nodes.hitl_interrupt import (
    hitl_interrupt_node,
    process_individual_hitl_node,
    HITLRequestType,
    HITLRequestStatus,
    HITLUrgencyLevel,
    HITLRequest,
    HITLResponse,
    DEFAULT_URGENCY_CONFIG,
    _identify_hitl_tasks,
    _get_urgency_level,
    _determine_request_type,
    _create_hitl_requests,
    _request_to_dict,
    _process_hitl_response,
    _update_task_from_hitl_response,
    get_hitl_summary,
    should_trigger_hitl,
    calculate_urgency_score,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_tasks() -> List[Dict[str, Any]]:
    """Sample tasks with various urgency scores."""
    return [
        {
            "task_id": "T001",
            "name": "Revenue Recognition Test",
            "urgency_score": 85,
            "risk_score": 80,
            "status": "pending",
            "category": "revenue",
            "description": "Test revenue recognition for Q4",
            "metadata": {"amount": 500000, "ai_confidence": 0.7}
        },
        {
            "task_id": "T002",
            "name": "Inventory Count",
            "urgency_score": 45,
            "risk_score": 40,
            "status": "pending",
            "category": "inventory",
            "description": "Physical inventory count",
            "metadata": {"amount": 100000, "ai_confidence": 0.9}
        },
        {
            "task_id": "T003",
            "name": "Cash Confirmation",
            "urgency_score": 92,
            "risk_score": 90,
            "status": "pending",
            "category": "cash",
            "description": "Bank confirmation for cash accounts",
            "metadata": {"amount": 1000000, "ai_confidence": 0.5, "anomaly_detected": True}
        },
        {
            "task_id": "T004",
            "name": "AR Aging Analysis",
            "urgency_score": 78,
            "risk_score": 75,
            "status": "pending",
            "category": "receivables",
            "description": "Analyze AR aging report",
            "metadata": {"amount": 200000, "ai_confidence": 0.8}
        },
        {
            "task_id": "T005",
            "name": "Completed Task",
            "urgency_score": 95,
            "risk_score": 95,
            "status": "completed",
            "category": "other",
            "description": "Already completed task",
            "metadata": {}
        }
    ]


@pytest.fixture
def sample_state(sample_tasks) -> Dict[str, Any]:
    """Sample AuditState for testing."""
    return {
        "project_id": "proj-test-001",
        "client_name": "Test Corp",
        "fiscal_year": 2024,
        "overall_materiality": 500000.0,
        "tasks": sample_tasks,
        "urgency_config": DEFAULT_URGENCY_CONFIG,
        "messages": [],
        "audit_plan": {},
        "next_action": "CONTINUE",
        "is_approved": False,
        "shared_documents": []
    }


@pytest.fixture
def sample_hitl_requests() -> List[HITLRequest]:
    """Sample HITL requests for testing."""
    return [
        HITLRequest(
            request_id="HITL-proj-001-T001-20240115",
            task_id="T001",
            project_id="proj-001",
            request_type=HITLRequestType.URGENCY_THRESHOLD,
            urgency_score=85,
            urgency_level=HITLUrgencyLevel.HIGH,
            title="Revenue Recognition Test",
            description="Test description",
            context={"category": "revenue"}
        ),
        HITLRequest(
            request_id="HITL-proj-001-T003-20240115",
            task_id="T003",
            project_id="proj-001",
            request_type=HITLRequestType.ANOMALY_DETECTED,
            urgency_score=92,
            urgency_level=HITLUrgencyLevel.CRITICAL,
            title="Cash Confirmation",
            description="Bank confirmation",
            context={"category": "cash"}
        )
    ]


# ============================================================================
# TEST: ENUMS
# ============================================================================

class TestHITLEnums:
    """Tests for HITL-related enumerations."""

    def test_hitl_request_type_values(self):
        """Test HITLRequestType enum values."""
        assert HITLRequestType.URGENCY_THRESHOLD == "urgency_threshold"
        assert HITLRequestType.MATERIALITY_EXCEEDED == "materiality_exceeded"
        assert HITLRequestType.PROFESSIONAL_JUDGMENT == "professional_judgment"
        assert HITLRequestType.ANOMALY_DETECTED == "anomaly_detected"
        assert HITLRequestType.EXTERNAL_REVIEW == "external_review"

    def test_hitl_request_status_values(self):
        """Test HITLRequestStatus enum values."""
        assert HITLRequestStatus.PENDING == "pending"
        assert HITLRequestStatus.APPROVED == "approved"
        assert HITLRequestStatus.REJECTED == "rejected"
        assert HITLRequestStatus.ESCALATED == "escalated"
        assert HITLRequestStatus.EXPIRED == "expired"

    def test_hitl_urgency_level_values(self):
        """Test HITLUrgencyLevel enum values."""
        assert HITLUrgencyLevel.CRITICAL == "critical"
        assert HITLUrgencyLevel.HIGH == "high"
        assert HITLUrgencyLevel.MEDIUM == "medium"
        assert HITLUrgencyLevel.LOW == "low"


# ============================================================================
# TEST: DATA CLASSES
# ============================================================================

class TestHITLDataClasses:
    """Tests for HITL data classes."""

    def test_hitl_request_creation(self):
        """Test HITLRequest dataclass creation."""
        request = HITLRequest(
            request_id="HITL-001",
            task_id="T001",
            project_id="proj-001",
            request_type=HITLRequestType.URGENCY_THRESHOLD,
            urgency_score=85.0,
            urgency_level=HITLUrgencyLevel.HIGH,
            title="Test Request",
            description="Test description",
            context={"key": "value"}
        )

        assert request.request_id == "HITL-001"
        assert request.task_id == "T001"
        assert request.project_id == "proj-001"
        assert request.request_type == HITLRequestType.URGENCY_THRESHOLD
        assert request.urgency_score == 85.0
        assert request.urgency_level == HITLUrgencyLevel.HIGH
        assert request.status == HITLRequestStatus.PENDING  # Default

    def test_hitl_request_default_status(self):
        """Test HITLRequest default status is PENDING."""
        request = HITLRequest(
            request_id="HITL-002",
            task_id="T002",
            project_id="proj-001",
            request_type=HITLRequestType.URGENCY_THRESHOLD,
            urgency_score=75.0,
            urgency_level=HITLUrgencyLevel.HIGH,
            title="Test",
            description="Test",
            context={}
        )
        assert request.status == HITLRequestStatus.PENDING

    def test_hitl_response_creation(self):
        """Test HITLResponse dataclass creation."""
        response = HITLResponse(
            request_id="HITL-001",
            action="approve",
            comment="Looks good"
        )

        assert response.request_id == "HITL-001"
        assert response.action == "approve"
        assert response.comment == "Looks good"
        assert response.responded_at is not None


# ============================================================================
# TEST: HELPER FUNCTIONS
# ============================================================================

class TestIdentifyHITLTasks:
    """Tests for _identify_hitl_tasks function."""

    def test_identify_tasks_above_threshold(self, sample_tasks):
        """Test identifying tasks above threshold."""
        result = _identify_hitl_tasks(sample_tasks, threshold=75.0)

        # Should return T001 (85), T003 (92), T004 (78)
        # T005 is completed so should be excluded
        task_ids = [t["task_id"] for t in result]
        assert "T001" in task_ids
        assert "T003" in task_ids
        assert "T004" in task_ids
        assert "T002" not in task_ids  # Below threshold
        assert "T005" not in task_ids  # Completed

    def test_identify_tasks_empty_list(self):
        """Test with empty task list."""
        result = _identify_hitl_tasks([], threshold=75.0)
        assert result == []

    def test_identify_tasks_none_above_threshold(self, sample_tasks):
        """Test when no tasks are above threshold."""
        result = _identify_hitl_tasks(sample_tasks, threshold=99.0)
        assert result == []

    def test_identify_tasks_all_above_threshold(self, sample_tasks):
        """Test when all pending tasks are above threshold."""
        result = _identify_hitl_tasks(sample_tasks, threshold=10.0)
        # Should return all pending tasks (not completed/skipped)
        assert len(result) == 4  # T001, T002, T003, T004

    def test_identify_tasks_excludes_hitl_approved(self):
        """Test that hitl_approved tasks are excluded."""
        tasks = [
            {"task_id": "T001", "urgency_score": 85, "status": "hitl_approved"},
            {"task_id": "T002", "urgency_score": 90, "status": "pending"}
        ]
        result = _identify_hitl_tasks(tasks, threshold=75.0)
        assert len(result) == 1
        assert result[0]["task_id"] == "T002"

    def test_identify_tasks_excludes_skipped(self):
        """Test that skipped tasks are excluded."""
        tasks = [
            {"task_id": "T001", "urgency_score": 85, "status": "skipped"},
            {"task_id": "T002", "urgency_score": 90, "status": "pending"}
        ]
        result = _identify_hitl_tasks(tasks, threshold=75.0)
        assert len(result) == 1
        assert result[0]["task_id"] == "T002"


class TestGetUrgencyLevel:
    """Tests for _get_urgency_level function."""

    def test_critical_level(self):
        """Test critical urgency level."""
        level = _get_urgency_level(95, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.CRITICAL

    def test_high_level(self):
        """Test high urgency level."""
        level = _get_urgency_level(80, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.HIGH

    def test_medium_level(self):
        """Test medium urgency level."""
        level = _get_urgency_level(60, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.MEDIUM

    def test_low_level(self):
        """Test low urgency level."""
        level = _get_urgency_level(30, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.LOW

    def test_boundary_critical(self):
        """Test boundary at critical threshold (90)."""
        level = _get_urgency_level(90, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.CRITICAL

    def test_boundary_high(self):
        """Test boundary at high threshold (75)."""
        level = _get_urgency_level(75, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.HIGH

    def test_boundary_medium(self):
        """Test boundary at medium threshold (50)."""
        level = _get_urgency_level(50, DEFAULT_URGENCY_CONFIG)
        assert level == HITLUrgencyLevel.MEDIUM


class TestDetermineRequestType:
    """Tests for _determine_request_type function."""

    def test_anomaly_detected(self):
        """Test anomaly detected request type."""
        task = {"metadata": {"anomaly_detected": True}}
        result = _determine_request_type(task)
        assert result == HITLRequestType.ANOMALY_DETECTED

    def test_materiality_exceeded(self):
        """Test materiality exceeded request type."""
        task = {"metadata": {"materiality_exceeded": True}}
        result = _determine_request_type(task)
        assert result == HITLRequestType.MATERIALITY_EXCEEDED

    def test_external_review(self):
        """Test external review request type."""
        task = {"metadata": {"requires_expert": True}}
        result = _determine_request_type(task)
        assert result == HITLRequestType.EXTERNAL_REVIEW

    def test_professional_judgment(self):
        """Test professional judgment request type."""
        task = {"metadata": {"requires_judgment": True}}
        result = _determine_request_type(task)
        assert result == HITLRequestType.PROFESSIONAL_JUDGMENT

    def test_default_urgency_threshold(self):
        """Test default to urgency threshold."""
        task = {"metadata": {}}
        result = _determine_request_type(task)
        assert result == HITLRequestType.URGENCY_THRESHOLD

    def test_priority_anomaly_over_others(self):
        """Test that anomaly takes priority."""
        task = {"metadata": {
            "anomaly_detected": True,
            "materiality_exceeded": True,
            "requires_expert": True
        }}
        result = _determine_request_type(task)
        assert result == HITLRequestType.ANOMALY_DETECTED


class TestCreateHITLRequests:
    """Tests for _create_hitl_requests function."""

    def test_create_requests_for_tasks(self, sample_tasks):
        """Test creating HITL requests for tasks."""
        high_urgency_tasks = [t for t in sample_tasks if t["urgency_score"] >= 75]
        requests = _create_hitl_requests(
            tasks=high_urgency_tasks,
            project_id="proj-test",
            urgency_config=DEFAULT_URGENCY_CONFIG
        )

        assert len(requests) > 0
        for request in requests:
            assert isinstance(request, HITLRequest)
            assert request.project_id == "proj-test"

    def test_requests_sorted_by_urgency(self, sample_tasks):
        """Test that requests are sorted by urgency (highest first)."""
        tasks = [t for t in sample_tasks if t["urgency_score"] >= 75 and t["status"] == "pending"]
        requests = _create_hitl_requests(
            tasks=tasks,
            project_id="proj-test",
            urgency_config=DEFAULT_URGENCY_CONFIG
        )

        # Should be sorted highest first
        scores = [r.urgency_score for r in requests]
        assert scores == sorted(scores, reverse=True)

    def test_request_id_format(self, sample_tasks):
        """Test that request IDs follow expected format."""
        tasks = [sample_tasks[0]]  # Single task
        requests = _create_hitl_requests(
            tasks=tasks,
            project_id="proj-test",
            urgency_config=DEFAULT_URGENCY_CONFIG
        )

        assert requests[0].request_id.startswith("HITL-proj-test-T001-")


class TestRequestToDict:
    """Tests for _request_to_dict function."""

    def test_converts_to_dict(self, sample_hitl_requests):
        """Test conversion to dictionary."""
        request = sample_hitl_requests[0]
        result = _request_to_dict(request)

        assert isinstance(result, dict)
        assert result["request_id"] == request.request_id
        assert result["task_id"] == request.task_id
        assert result["request_type"] == request.request_type.value
        assert result["urgency_level"] == request.urgency_level.value
        assert result["status"] == request.status.value


class TestProcessHITLResponse:
    """Tests for _process_hitl_response function."""

    def test_approve_all(self, sample_tasks, sample_hitl_requests):
        """Test approve_all action."""
        response = {"action": "approve_all", "comment": "Approved by reviewer"}

        result = _process_hitl_response(response, sample_tasks, sample_hitl_requests)

        assert result["next_action"] == "CONTINUE"
        # Check that affected tasks have hitl_status updated
        for task in result["tasks"]:
            if task["task_id"] in ["T001", "T003"]:
                assert task.get("hitl_status") == "approved"

    def test_reject_all(self, sample_tasks, sample_hitl_requests):
        """Test reject_all action."""
        response = {"action": "reject_all", "comment": "Rejected by reviewer"}

        result = _process_hitl_response(response, sample_tasks, sample_hitl_requests)

        assert result["next_action"] == "CONTINUE"
        for task in result["tasks"]:
            if task["task_id"] in ["T001", "T003"]:
                assert task.get("hitl_status") == "rejected"
                assert task.get("status") == "skipped"

    def test_review_individual(self, sample_tasks, sample_hitl_requests):
        """Test review_individual action."""
        response = {"action": "review_individual"}

        result = _process_hitl_response(response, sample_tasks, sample_hitl_requests)

        assert result["next_action"] == "REVIEW_INDIVIDUAL"
        assert "pending_hitl_requests" in result


class TestUpdateTaskFromHITLResponse:
    """Tests for _update_task_from_hitl_response function."""

    def test_approve_task(self, sample_tasks):
        """Test approving a task."""
        result = _update_task_from_hitl_response(
            tasks=sample_tasks,
            task_id="T001",
            action="approve",
            comment="Approved"
        )

        t001 = next(t for t in result if t["task_id"] == "T001")
        assert t001["hitl_status"] == "approved"
        assert t001["hitl_comment"] == "Approved"

    def test_reject_task(self, sample_tasks):
        """Test rejecting a task."""
        result = _update_task_from_hitl_response(
            tasks=sample_tasks,
            task_id="T001",
            action="reject",
            comment="Rejected"
        )

        t001 = next(t for t in result if t["task_id"] == "T001")
        assert t001["hitl_status"] == "rejected"
        assert t001["status"] == "skipped"

    def test_escalate_task(self, sample_tasks):
        """Test escalating a task."""
        result = _update_task_from_hitl_response(
            tasks=sample_tasks,
            task_id="T001",
            action="escalate",
            comment="Needs partner review"
        )

        t001 = next(t for t in result if t["task_id"] == "T001")
        assert t001["hitl_status"] == "escalated"
        assert t001["requires_partner_review"] is True

    def test_unknown_action_keeps_task_unchanged(self, sample_tasks):
        """Test that unknown action doesn't change task."""
        original_t001 = next(t for t in sample_tasks if t["task_id"] == "T001").copy()

        result = _update_task_from_hitl_response(
            tasks=sample_tasks,
            task_id="T001",
            action="unknown_action",
            comment="Test"
        )

        t001 = next(t for t in result if t["task_id"] == "T001")
        assert t001.get("hitl_status") is None


# ============================================================================
# TEST: UTILITY FUNCTIONS
# ============================================================================

class TestGetHITLSummary:
    """Tests for get_hitl_summary function."""

    def test_summary_with_tasks(self, sample_state):
        """Test summary generation with tasks."""
        result = get_hitl_summary(sample_state)

        assert result["total_tasks"] == 5
        assert result["hitl_threshold"] == DEFAULT_URGENCY_CONFIG["hitl_threshold"]
        assert "tasks_above_threshold" in result
        assert "highest_urgency" in result
        assert "average_urgency" in result

    def test_summary_empty_tasks(self):
        """Test summary with no tasks."""
        state = {"tasks": [], "urgency_config": DEFAULT_URGENCY_CONFIG}
        result = get_hitl_summary(state)

        assert result["total_tasks"] == 0
        assert result["tasks_above_threshold"] == 0
        assert result["highest_urgency"] == 0

    def test_summary_counts_statuses(self):
        """Test that summary correctly counts HITL statuses."""
        state = {
            "tasks": [
                {"task_id": "T1", "urgency_score": 80, "hitl_status": "approved", "status": "pending"},
                {"task_id": "T2", "urgency_score": 85, "hitl_status": "rejected", "status": "skipped"},
                {"task_id": "T3", "urgency_score": 90, "hitl_status": "escalated", "status": "pending"},
                {"task_id": "T4", "urgency_score": 75, "hitl_status": "pending", "status": "pending"},
            ],
            "urgency_config": DEFAULT_URGENCY_CONFIG
        }

        result = get_hitl_summary(state)

        assert result["approved"] == 1
        assert result["rejected"] == 1
        assert result["escalated"] == 1
        assert result["pending"] == 1


class TestShouldTriggerHITL:
    """Tests for should_trigger_hitl function."""

    def test_trigger_above_threshold(self):
        """Test trigger for task above threshold."""
        task = {"task_id": "T1", "urgency_score": 80, "status": "pending"}
        assert should_trigger_hitl(task) is True

    def test_no_trigger_below_threshold(self):
        """Test no trigger for task below threshold."""
        task = {"task_id": "T1", "urgency_score": 50, "status": "pending"}
        assert should_trigger_hitl(task) is False

    def test_no_trigger_if_already_approved(self):
        """Test no trigger if already HITL approved."""
        task = {"task_id": "T1", "urgency_score": 90, "hitl_status": "approved"}
        assert should_trigger_hitl(task) is False

    def test_no_trigger_if_already_rejected(self):
        """Test no trigger if already HITL rejected."""
        task = {"task_id": "T1", "urgency_score": 90, "hitl_status": "rejected"}
        assert should_trigger_hitl(task) is False

    def test_no_trigger_if_completed(self):
        """Test no trigger for completed tasks."""
        task = {"task_id": "T1", "urgency_score": 90, "status": "completed"}
        assert should_trigger_hitl(task) is False

    def test_custom_threshold(self):
        """Test with custom threshold configuration."""
        task = {"task_id": "T1", "urgency_score": 60, "status": "pending"}
        config = {"hitl_threshold": 50.0}
        assert should_trigger_hitl(task, config) is True

        config = {"hitl_threshold": 70.0}
        assert should_trigger_hitl(task, config) is False


class TestCalculateUrgencyScore:
    """Tests for calculate_urgency_score function."""

    def test_basic_calculation(self):
        """Test basic urgency score calculation."""
        task = {
            "risk_score": 80,
            "metadata": {
                "amount": 500000,
                "ai_confidence": 0.8
            }
        }

        score = calculate_urgency_score(task, materiality=500000.0)

        # Score should be between 0 and 100
        assert 0 <= score <= 100

    def test_high_risk_high_score(self):
        """Test that high risk produces high urgency."""
        task = {
            "risk_score": 95,
            "metadata": {
                "amount": 1000000,
                "ai_confidence": 0.3  # Low confidence
            }
        }

        score = calculate_urgency_score(task, materiality=500000.0)
        assert score >= 70  # Should be high

    def test_low_risk_low_score(self):
        """Test that low risk produces low urgency."""
        task = {
            "risk_score": 20,
            "metadata": {
                "amount": 50000,
                "ai_confidence": 0.95
            }
        }

        score = calculate_urgency_score(task, materiality=500000.0)
        assert score < 50  # Should be relatively low

    def test_default_values(self):
        """Test with missing values uses defaults."""
        task = {"risk_score": 50, "metadata": {}}

        score = calculate_urgency_score(task, materiality=500000.0)
        assert 0 <= score <= 100

    def test_zero_materiality(self):
        """Test handling of zero materiality."""
        task = {
            "risk_score": 50,
            "metadata": {"amount": 100000}
        }

        score = calculate_urgency_score(task, materiality=0)
        assert 0 <= score <= 100


# ============================================================================
# TEST: MAIN NODES (Async)
# ============================================================================

class TestHITLInterruptNode:
    """Tests for hitl_interrupt_node async function."""

    @pytest.mark.asyncio
    async def test_no_tasks_above_threshold(self):
        """Test when no tasks exceed threshold."""
        state = {
            "project_id": "proj-001",
            "tasks": [
                {"task_id": "T1", "urgency_score": 50, "status": "pending"},
                {"task_id": "T2", "urgency_score": 60, "status": "pending"},
            ],
            "urgency_config": DEFAULT_URGENCY_CONFIG,
        }

        result = await hitl_interrupt_node(state)

        assert result["next_action"] == "CONTINUE"
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_tasks_above_threshold_triggers_interrupt(self, sample_state):
        """Test that tasks above threshold trigger interrupt."""
        with patch("src.graph.nodes.hitl_interrupt.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve_all", "comment": "OK"}

            result = await hitl_interrupt_node(sample_state)

            # Interrupt should have been called
            mock_interrupt.assert_called_once()
            call_args = mock_interrupt.call_args[0][0]
            assert call_args["type"] == "hitl_escalation"
            assert "requests" in call_args

    @pytest.mark.asyncio
    async def test_empty_tasks_list(self):
        """Test with empty tasks list."""
        state = {
            "project_id": "proj-001",
            "tasks": [],
            "urgency_config": DEFAULT_URGENCY_CONFIG,
        }

        result = await hitl_interrupt_node(state)

        assert result["next_action"] == "CONTINUE"


class TestProcessIndividualHITLNode:
    """Tests for process_individual_hitl_node async function."""

    @pytest.mark.asyncio
    async def test_no_pending_requests(self):
        """Test when no pending HITL requests."""
        state = {
            "pending_hitl_requests": [],
            "tasks": []
        }

        result = await process_individual_hitl_node(state)

        assert result["next_action"] == "CONTINUE"
        assert result["pending_hitl_requests"] == []

    @pytest.mark.asyncio
    async def test_processes_first_pending_request(self):
        """Test processing first pending request."""
        state = {
            "pending_hitl_requests": [
                {"request_id": "HITL-001", "task_id": "T001"},
                {"request_id": "HITL-002", "task_id": "T002"},
            ],
            "tasks": [
                {"task_id": "T001", "status": "pending"},
                {"task_id": "T002", "status": "pending"},
            ]
        }

        with patch("src.graph.nodes.hitl_interrupt.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "comment": "OK"}

            result = await process_individual_hitl_node(state)

            # Should have processed first request
            assert len(result["pending_hitl_requests"]) == 1
            assert result["pending_hitl_requests"][0]["request_id"] == "HITL-002"

    @pytest.mark.asyncio
    async def test_last_request_sets_continue(self):
        """Test that processing last request sets CONTINUE."""
        state = {
            "pending_hitl_requests": [
                {"request_id": "HITL-001", "task_id": "T001"},
            ],
            "tasks": [
                {"task_id": "T001", "status": "pending"},
            ]
        }

        with patch("src.graph.nodes.hitl_interrupt.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "comment": "OK"}

            result = await process_individual_hitl_node(state)

            assert result["next_action"] == "CONTINUE"
            assert result["pending_hitl_requests"] == []


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_task_with_missing_urgency_score(self):
        """Test handling task without urgency_score."""
        tasks = [
            {"task_id": "T1", "status": "pending"},  # No urgency_score
        ]
        result = _identify_hitl_tasks(tasks, threshold=75.0)
        assert result == []  # Should not crash

    def test_task_with_none_urgency_score(self):
        """Test handling task with None urgency_score."""
        tasks = [
            {"task_id": "T1", "urgency_score": None, "status": "pending"},
        ]
        # Should handle gracefully
        result = _identify_hitl_tasks(tasks, threshold=75.0)
        assert result == []

    def test_request_with_missing_context(self):
        """Test creating request for task with missing context."""
        tasks = [{"task_id": "T1", "urgency_score": 80, "status": "pending"}]
        requests = _create_hitl_requests(tasks, "proj-001", DEFAULT_URGENCY_CONFIG)

        assert len(requests) == 1
        assert requests[0].context is not None

    def test_summary_with_missing_config(self):
        """Test summary generation with missing config."""
        state = {"tasks": [{"task_id": "T1", "urgency_score": 80}]}
        result = get_hitl_summary(state)

        assert result["hitl_threshold"] == DEFAULT_URGENCY_CONFIG["hitl_threshold"]

    def test_calculate_urgency_with_negative_values(self):
        """Test urgency calculation with negative values."""
        task = {
            "risk_score": -10,  # Invalid but should handle
            "metadata": {"amount": -5000, "ai_confidence": 1.5}
        }

        score = calculate_urgency_score(task, materiality=500000.0)
        assert 0 <= score <= 100  # Should clamp to valid range


# ============================================================================
# TEST: CONFIGURATION
# ============================================================================

class TestConfiguration:
    """Tests for configuration handling."""

    def test_default_config_values(self):
        """Test default configuration values."""
        assert DEFAULT_URGENCY_CONFIG["hitl_threshold"] == 75.0
        assert DEFAULT_URGENCY_CONFIG["critical_threshold"] == 90.0
        assert DEFAULT_URGENCY_CONFIG["high_threshold"] == 75.0
        assert DEFAULT_URGENCY_CONFIG["medium_threshold"] == 50.0
        assert DEFAULT_URGENCY_CONFIG["materiality_weight"] == 0.40
        assert DEFAULT_URGENCY_CONFIG["risk_weight"] == 0.35
        assert DEFAULT_URGENCY_CONFIG["ai_confidence_weight"] == 0.25

    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        total = (
            DEFAULT_URGENCY_CONFIG["materiality_weight"] +
            DEFAULT_URGENCY_CONFIG["risk_weight"] +
            DEFAULT_URGENCY_CONFIG["ai_confidence_weight"]
        )
        assert abs(total - 1.0) < 0.001
