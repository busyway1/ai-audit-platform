"""
Comprehensive Unit Tests for Urgency Calculation Node

Target Coverage:
- urgency_node() - Main urgency calculation workflow
- calculate_task_urgency_score() - Single task urgency calculation
- calculate_urgency_scores() - Batch urgency calculation
- Helper functions for urgency determination
- Utility functions for task filtering and sorting

Coverage Target: 80%+
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
from datetime import datetime

from src.graph.nodes.urgency_node import (
    urgency_node,
    calculate_task_urgency_score,
    calculate_urgency_scores,
    get_urgency_summary,
    filter_tasks_by_urgency,
    sort_tasks_by_urgency,
    get_hitl_candidates,
    _get_urgency_config,
    _parse_risk_score,
    _calculate_materiality_factor,
    _calculate_ai_confidence_factor,
    _get_urgency_level,
    UrgencyLevel,
    UrgencyCalculationResult,
    TaskUrgencyInfo,
    DEFAULT_URGENCY_CONFIG,
    RISK_SCORE_MAP,
)
from src.graph.state import AuditState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def base_audit_state() -> AuditState:
    """Create a base AuditState for testing."""
    return {
        "messages": [],
        "project_id": "PROJECT-001",
        "client_name": "테스트 회사",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0,
        "audit_plan": {},
        "tasks": [],
        "next_action": "CONTINUE",
        "is_approved": False,
        "shared_documents": [],
        "interview_complete": False,
        "interview_phase": 0,
        "interview_responses": [],
        "specification": {},
        "egas": [],
        "urgency_config": {},
    }


@pytest.fixture
def sample_tasks() -> List[Dict[str, Any]]:
    """Create sample tasks for testing."""
    return [
        {
            "id": "task-001",
            "name": "Revenue Recognition Testing",
            "risk_score": 85,
            "risk_level": "high",
            "status": "Pending",
            "metadata": {
                "amount": 800000,
                "ai_confidence": 0.6,
                "category": "Revenue",
            },
        },
        {
            "id": "task-002",
            "name": "Inventory Count",
            "risk_score": 50,
            "risk_level": "medium",
            "status": "Pending",
            "metadata": {
                "amount": 200000,
                "ai_confidence": 0.9,
                "category": "Inventory",
            },
        },
        {
            "id": "task-003",
            "name": "Accounts Payable Review",
            "risk_score": 95,
            "risk_level": "critical",
            "status": "Pending",
            "metadata": {
                "amount": 1500000,
                "ai_confidence": 0.4,
                "category": "Payables",
            },
        },
        {
            "id": "task-004",
            "name": "Cash Reconciliation",
            "risk_score": 25,
            "risk_level": "low",
            "status": "Pending",
            "metadata": {
                "amount": 50000,
                "ai_confidence": 0.95,
                "category": "Cash",
            },
        },
    ]


@pytest.fixture
def state_with_tasks(base_audit_state, sample_tasks) -> AuditState:
    """Create state with tasks."""
    base_audit_state["tasks"] = sample_tasks
    return base_audit_state


@pytest.fixture
def custom_urgency_config() -> Dict[str, Any]:
    """Create custom urgency configuration."""
    return {
        "materiality_weight": 0.50,
        "risk_weight": 0.30,
        "ai_confidence_weight": 0.20,
        "hitl_threshold": 80.0,
        "critical_threshold": 95.0,
        "high_threshold": 80.0,
        "medium_threshold": 60.0,
    }


@pytest.fixture
def tasks_with_urgency() -> List[Dict[str, Any]]:
    """Create tasks with pre-calculated urgency scores."""
    return [
        {"id": "t1", "urgency_score": 92.5, "urgency_level": "critical", "requires_hitl": True},
        {"id": "t2", "urgency_score": 78.0, "urgency_level": "high", "requires_hitl": True},
        {"id": "t3", "urgency_score": 55.0, "urgency_level": "medium", "requires_hitl": False},
        {"id": "t4", "urgency_score": 30.0, "urgency_level": "low", "requires_hitl": False},
    ]


# ============================================================================
# ENUM AND CONSTANT TESTS
# ============================================================================

class TestEnumsAndConstants:
    """Test enum classes and constants."""

    def test_urgency_level_enum_values(self):
        """Test UrgencyLevel enum has correct values."""
        assert UrgencyLevel.CRITICAL.value == "critical"
        assert UrgencyLevel.HIGH.value == "high"
        assert UrgencyLevel.MEDIUM.value == "medium"
        assert UrgencyLevel.LOW.value == "low"

    def test_default_config_weights_sum_to_one(self):
        """Test default config weights sum to 1.0."""
        config = DEFAULT_URGENCY_CONFIG
        total = (
            config["materiality_weight"] +
            config["risk_weight"] +
            config["ai_confidence_weight"]
        )
        assert abs(total - 1.0) < 0.001

    def test_default_config_thresholds(self):
        """Test default config has all thresholds."""
        config = DEFAULT_URGENCY_CONFIG
        assert "hitl_threshold" in config
        assert "critical_threshold" in config
        assert "high_threshold" in config
        assert "medium_threshold" in config
        assert config["critical_threshold"] >= config["high_threshold"]
        assert config["high_threshold"] >= config["medium_threshold"]

    def test_risk_score_map_completeness(self):
        """Test RISK_SCORE_MAP has all risk levels."""
        assert "critical" in RISK_SCORE_MAP
        assert "high" in RISK_SCORE_MAP
        assert "medium" in RISK_SCORE_MAP
        assert "low" in RISK_SCORE_MAP

    def test_risk_score_map_ordering(self):
        """Test RISK_SCORE_MAP has correct ordering."""
        assert RISK_SCORE_MAP["critical"] > RISK_SCORE_MAP["high"]
        assert RISK_SCORE_MAP["high"] > RISK_SCORE_MAP["medium"]
        assert RISK_SCORE_MAP["medium"] > RISK_SCORE_MAP["low"]


# ============================================================================
# DATA CLASS TESTS
# ============================================================================

class TestUrgencyCalculationResult:
    """Test UrgencyCalculationResult dataclass."""

    def test_result_creation(self):
        """Test UrgencyCalculationResult creation."""
        result = UrgencyCalculationResult(
            success=True,
            tasks=[],
            total_tasks=10,
            tasks_above_threshold=3,
            highest_urgency=95.5,
            average_urgency=62.3,
        )

        assert result.success is True
        assert result.total_tasks == 10
        assert result.tasks_above_threshold == 3

    def test_result_defaults(self):
        """Test UrgencyCalculationResult default values."""
        result = UrgencyCalculationResult(success=True, tasks=[])

        assert result.errors == []
        assert result.metadata == {}
        assert result.by_urgency_level == {}


class TestTaskUrgencyInfo:
    """Test TaskUrgencyInfo dataclass."""

    def test_info_creation(self):
        """Test TaskUrgencyInfo creation."""
        info = TaskUrgencyInfo(
            task_id="task-001",
            urgency_score=85.5,
            urgency_level=UrgencyLevel.HIGH,
            materiality_factor=60.0,
            risk_factor=75.0,
            ai_confidence_factor=40.0,
            requires_hitl=True,
        )

        assert info.task_id == "task-001"
        assert info.urgency_score == 85.5
        assert info.urgency_level == UrgencyLevel.HIGH
        assert info.requires_hitl is True


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestGetUrgencyConfig:
    """Test _get_urgency_config helper."""

    def test_get_config_defaults(self, base_audit_state):
        """Test getting default config."""
        config = _get_urgency_config(base_audit_state)

        assert config["materiality_weight"] == 0.40
        assert config["risk_weight"] == 0.35
        assert config["ai_confidence_weight"] == 0.25

    def test_get_config_with_state_override(self, base_audit_state):
        """Test config override from state."""
        base_audit_state["urgency_config"] = {
            "hitl_threshold": 80.0,
            "materiality_weight": 0.50,
        }

        config = _get_urgency_config(base_audit_state)

        assert config["hitl_threshold"] == 80.0
        assert config["materiality_weight"] == 0.50
        # Other defaults should remain
        assert config["risk_weight"] == 0.35


class TestParseRiskScore:
    """Test _parse_risk_score helper."""

    def test_parse_direct_score(self):
        """Test parsing direct risk_score."""
        task = {"risk_score": 75}
        assert _parse_risk_score(task) == 75.0

    def test_parse_string_score(self):
        """Test parsing string risk_score."""
        task = {"risk_score": "80"}
        assert _parse_risk_score(task) == 80.0

    def test_parse_from_risk_level(self):
        """Test parsing from risk_level mapping."""
        assert _parse_risk_score({"risk_level": "critical"}) == 95
        assert _parse_risk_score({"risk_level": "high"}) == 75
        assert _parse_risk_score({"risk_level": "medium"}) == 50
        assert _parse_risk_score({"risk_level": "low"}) == 25

    def test_parse_case_insensitive(self):
        """Test case insensitive parsing."""
        assert _parse_risk_score({"risk_level": "HIGH"}) == 75
        assert _parse_risk_score({"risk_level": "Medium"}) == 50

    def test_parse_default(self):
        """Test default when no risk info."""
        task = {}
        assert _parse_risk_score(task) == 50  # medium default


class TestCalculateMaterialityFactor:
    """Test _calculate_materiality_factor helper."""

    def test_materiality_factor_basic(self):
        """Test basic materiality factor calculation."""
        task = {"metadata": {"amount": 500000}}
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 1000000.0, config)

        # ratio = 0.5, factor = 0.5 * 50 = 25
        assert factor == 25.0

    def test_materiality_factor_high_amount(self):
        """Test materiality factor with high amount."""
        task = {"metadata": {"amount": 2000000}}
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 1000000.0, config)

        # ratio = 2.0 (capped), factor = 2.0 * 50 = 100
        assert factor == 100.0

    def test_materiality_factor_capped(self):
        """Test materiality factor is capped."""
        task = {"metadata": {"amount": 5000000}}
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 1000000.0, config)

        # Should be capped at 100
        assert factor <= 100.0

    def test_materiality_factor_zero_materiality(self):
        """Test factor with zero materiality threshold."""
        task = {"metadata": {"amount": 500000}, "risk_score": 75}
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 0.0, config)

        # Should return risk-based default
        assert factor > 0

    def test_materiality_factor_no_amount(self):
        """Test factor when task has no amount."""
        task = {"risk_score": 50}
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 1000000.0, config)

        # Should return risk-based default
        assert factor > 0

    def test_materiality_factor_alternative_amount_fields(self):
        """Test factor with alternative amount field names."""
        task = {"amount": 400000}  # Direct amount field
        config = DEFAULT_URGENCY_CONFIG

        factor = _calculate_materiality_factor(task, 1000000.0, config)

        assert factor == 20.0


class TestCalculateAiConfidenceFactor:
    """Test _calculate_ai_confidence_factor helper."""

    def test_ai_confidence_factor_basic(self):
        """Test basic AI confidence factor."""
        task = {"metadata": {"ai_confidence": 0.8}}

        factor = _calculate_ai_confidence_factor(task)

        # (1 - 0.8) * 100 = 20
        assert factor == pytest.approx(20.0)

    def test_ai_confidence_factor_low_confidence(self):
        """Test low confidence results in high factor."""
        task = {"metadata": {"ai_confidence": 0.3}}

        factor = _calculate_ai_confidence_factor(task)

        # (1 - 0.3) * 100 = 70
        assert factor == 70.0

    def test_ai_confidence_factor_high_confidence(self):
        """Test high confidence results in low factor."""
        task = {"metadata": {"ai_confidence": 0.95}}

        factor = _calculate_ai_confidence_factor(task)

        # (1 - 0.95) * 100 = 5
        assert factor == pytest.approx(5.0)

    def test_ai_confidence_factor_default(self):
        """Test default AI confidence when not provided."""
        task = {}

        factor = _calculate_ai_confidence_factor(task)

        # Default 0.8 confidence -> (1 - 0.8) * 100 = 20
        assert factor == pytest.approx(20.0)

    def test_ai_confidence_factor_percentage_format(self):
        """Test AI confidence provided as percentage."""
        task = {"metadata": {"ai_confidence": 80}}  # 80%

        factor = _calculate_ai_confidence_factor(task)

        # 80 -> 0.80 -> (1 - 0.8) * 100 = 20
        assert factor == pytest.approx(20.0)

    def test_ai_confidence_factor_alternative_fields(self):
        """Test alternative confidence field names."""
        task = {"ai_confidence": 0.7}

        factor = _calculate_ai_confidence_factor(task)

        assert factor == pytest.approx(30.0)


class TestGetUrgencyLevel:
    """Test _get_urgency_level helper."""

    def test_urgency_level_critical(self):
        """Test critical urgency level."""
        config = DEFAULT_URGENCY_CONFIG
        assert _get_urgency_level(95.0, config) == UrgencyLevel.CRITICAL
        assert _get_urgency_level(90.0, config) == UrgencyLevel.CRITICAL

    def test_urgency_level_high(self):
        """Test high urgency level."""
        config = DEFAULT_URGENCY_CONFIG
        assert _get_urgency_level(85.0, config) == UrgencyLevel.HIGH
        assert _get_urgency_level(75.0, config) == UrgencyLevel.HIGH

    def test_urgency_level_medium(self):
        """Test medium urgency level."""
        config = DEFAULT_URGENCY_CONFIG
        assert _get_urgency_level(65.0, config) == UrgencyLevel.MEDIUM
        assert _get_urgency_level(50.0, config) == UrgencyLevel.MEDIUM

    def test_urgency_level_low(self):
        """Test low urgency level."""
        config = DEFAULT_URGENCY_CONFIG
        assert _get_urgency_level(40.0, config) == UrgencyLevel.LOW
        assert _get_urgency_level(25.0, config) == UrgencyLevel.LOW
        assert _get_urgency_level(0.0, config) == UrgencyLevel.LOW

    def test_urgency_level_custom_thresholds(self, custom_urgency_config):
        """Test with custom thresholds."""
        config = custom_urgency_config

        assert _get_urgency_level(96.0, config) == UrgencyLevel.CRITICAL
        assert _get_urgency_level(90.0, config) == UrgencyLevel.HIGH
        assert _get_urgency_level(70.0, config) == UrgencyLevel.MEDIUM


# ============================================================================
# SINGLE TASK URGENCY CALCULATION TESTS
# ============================================================================

class TestCalculateTaskUrgencyScore:
    """Test calculate_task_urgency_score function."""

    def test_basic_calculation(self, sample_tasks):
        """Test basic urgency score calculation."""
        task = sample_tasks[0]  # risk=85, amount=800k, confidence=0.6

        result = calculate_task_urgency_score(task, 1000000.0)

        assert isinstance(result, TaskUrgencyInfo)
        assert result.task_id == "task-001"
        assert 0 <= result.urgency_score <= 100

    def test_high_urgency_task(self, sample_tasks):
        """Test high urgency task calculation."""
        task = sample_tasks[2]  # risk=95, amount=1.5M, confidence=0.4

        result = calculate_task_urgency_score(task, 1000000.0)

        assert result.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        assert result.requires_hitl is True

    def test_low_urgency_task(self, sample_tasks):
        """Test low urgency task calculation."""
        task = sample_tasks[3]  # risk=25, amount=50k, confidence=0.95

        result = calculate_task_urgency_score(task, 1000000.0)

        assert result.urgency_level == UrgencyLevel.LOW
        assert result.requires_hitl is False

    def test_weighted_formula_components(self):
        """Test individual components of weighted formula."""
        task = {
            "id": "test",
            "risk_score": 100,  # Max risk
            "metadata": {
                "amount": 0,  # No amount
                "ai_confidence": 1.0,  # Max confidence (0 factor)
            }
        }

        result = calculate_task_urgency_score(task, 1000000.0)

        # With max risk, no amount (risk-based default), and max confidence
        # Score should be primarily from risk factor
        assert result.risk_factor == 100

    def test_custom_config(self, sample_tasks, custom_urgency_config):
        """Test calculation with custom configuration."""
        task = sample_tasks[0]

        result = calculate_task_urgency_score(
            task, 1000000.0, custom_urgency_config
        )

        # With higher materiality weight, score should differ
        assert result.urgency_score > 0

    def test_urgency_breakdown_in_result(self, sample_tasks):
        """Test that result includes factor breakdown."""
        task = sample_tasks[0]

        result = calculate_task_urgency_score(task, 1000000.0)

        assert result.materiality_factor >= 0
        assert result.risk_factor >= 0
        assert result.ai_confidence_factor >= 0

    def test_score_clamped_to_range(self):
        """Test urgency score is clamped to 0-100."""
        task_extreme_high = {
            "id": "extreme",
            "risk_score": 150,  # Over max
            "metadata": {"amount": 10000000, "ai_confidence": 0.0}
        }

        result = calculate_task_urgency_score(task_extreme_high, 100000.0)

        assert 0 <= result.urgency_score <= 100


# ============================================================================
# BATCH URGENCY CALCULATION TESTS
# ============================================================================

class TestCalculateUrgencyScores:
    """Test calculate_urgency_scores function."""

    def test_batch_calculation(self, sample_tasks):
        """Test batch urgency calculation."""
        result = calculate_urgency_scores(sample_tasks, 1000000.0)

        assert result.success is True
        assert result.total_tasks == 4
        assert len(result.tasks) == 4

    def test_tasks_have_urgency_fields(self, sample_tasks):
        """Test that all tasks have urgency fields after calculation."""
        result = calculate_urgency_scores(sample_tasks, 1000000.0)

        for task in result.tasks:
            assert "urgency_score" in task
            assert "urgency_level" in task
            assert "requires_hitl" in task

    def test_tasks_have_urgency_breakdown(self, sample_tasks):
        """Test that tasks have urgency breakdown in metadata."""
        result = calculate_urgency_scores(sample_tasks, 1000000.0)

        for task in result.tasks:
            breakdown = task.get("metadata", {}).get("urgency_breakdown", {})
            assert "materiality_factor" in breakdown
            assert "risk_factor" in breakdown
            assert "ai_confidence_factor" in breakdown

    def test_statistics_calculated(self, sample_tasks):
        """Test that statistics are calculated correctly."""
        result = calculate_urgency_scores(sample_tasks, 1000000.0)

        assert result.highest_urgency > 0
        assert result.average_urgency > 0
        assert result.tasks_above_threshold >= 0

    def test_level_distribution(self, sample_tasks):
        """Test urgency level distribution is tracked."""
        result = calculate_urgency_scores(sample_tasks, 1000000.0)

        total_by_level = sum(result.by_urgency_level.values())
        assert total_by_level == result.total_tasks

    def test_empty_tasks(self):
        """Test calculation with empty task list."""
        result = calculate_urgency_scores([], 1000000.0)

        assert result.success is True
        assert result.total_tasks == 0
        assert len(result.errors) > 0

    def test_custom_config_applied(self, sample_tasks, custom_urgency_config):
        """Test custom configuration is applied."""
        result = calculate_urgency_scores(
            sample_tasks, 1000000.0, custom_urgency_config
        )

        assert result.metadata["hitl_threshold"] == 80.0
        assert result.metadata["config"]["materiality_weight"] == 0.50

    def test_hitl_threshold_counting(self, sample_tasks):
        """Test HITL threshold counting."""
        config = {"hitl_threshold": 50.0}
        result = calculate_urgency_scores(sample_tasks, 1000000.0, config)

        # With threshold at 50, more tasks should be above
        hitl_tasks = [t for t in result.tasks if t["requires_hitl"]]
        assert len(hitl_tasks) == result.tasks_above_threshold


# ============================================================================
# LANGGRAPH NODE TESTS
# ============================================================================

class TestUrgencyNode:
    """Test urgency_node function."""

    @pytest.mark.asyncio
    async def test_node_basic(self, state_with_tasks):
        """Test basic urgency node execution."""
        result = await urgency_node(state_with_tasks)

        assert "tasks" in result
        assert "messages" in result
        assert len(result["tasks"]) > 0

    @pytest.mark.asyncio
    async def test_node_adds_urgency_scores(self, state_with_tasks):
        """Test node adds urgency scores to tasks."""
        result = await urgency_node(state_with_tasks)

        for task in result["tasks"]:
            assert "urgency_score" in task
            assert "urgency_level" in task
            assert "requires_hitl" in task

    @pytest.mark.asyncio
    async def test_node_message_content(self, state_with_tasks):
        """Test node generates appropriate message."""
        result = await urgency_node(state_with_tasks)

        assert len(result["messages"]) == 1
        message = result["messages"][0]
        assert "Urgency Node" in message.content
        assert "긴급도" in message.content  # Korean for urgency

    @pytest.mark.asyncio
    async def test_node_no_tasks(self, base_audit_state):
        """Test node with no tasks."""
        result = await urgency_node(base_audit_state)

        assert "tasks" in result
        assert len(result["tasks"]) == 0
        assert "긴급도 계산 대상 작업이 없습니다" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_node_uses_state_config(self, state_with_tasks):
        """Test node uses urgency_config from state."""
        state_with_tasks["urgency_config"] = {
            "hitl_threshold": 80.0,
        }

        result = await urgency_node(state_with_tasks)

        # Tasks should be scored with new threshold
        assert len(result["tasks"]) > 0

    @pytest.mark.asyncio
    async def test_node_uses_overall_materiality(self, state_with_tasks):
        """Test node uses overall_materiality from state."""
        state_with_tasks["overall_materiality"] = 500000.0

        result = await urgency_node(state_with_tasks)

        # Lower materiality should result in higher urgency for same amounts
        assert len(result["tasks"]) > 0


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestGetUrgencySummary:
    """Test get_urgency_summary function."""

    def test_summary_basic(self, tasks_with_urgency):
        """Test basic summary generation."""
        summary = get_urgency_summary(tasks_with_urgency)

        assert summary["total"] == 4
        assert "by_level" in summary
        assert summary["average_score"] > 0

    def test_summary_level_counts(self, tasks_with_urgency):
        """Test level counts in summary."""
        summary = get_urgency_summary(tasks_with_urgency)

        assert summary["by_level"]["critical"] == 1
        assert summary["by_level"]["high"] == 1
        assert summary["by_level"]["medium"] == 1
        assert summary["by_level"]["low"] == 1

    def test_summary_hitl_count(self, tasks_with_urgency):
        """Test HITL count in summary."""
        summary = get_urgency_summary(tasks_with_urgency)

        assert summary["tasks_requiring_hitl"] == 2

    def test_summary_empty_tasks(self):
        """Test summary with empty list."""
        summary = get_urgency_summary([])

        assert summary["total"] == 0
        assert summary["average_score"] == 0
        assert summary["max_score"] == 0

    def test_summary_min_max_scores(self, tasks_with_urgency):
        """Test min/max scores in summary."""
        summary = get_urgency_summary(tasks_with_urgency)

        assert summary["max_score"] == 92.5
        assert summary["min_score"] == 30.0


class TestFilterTasksByUrgency:
    """Test filter_tasks_by_urgency function."""

    def test_filter_by_min_score(self, tasks_with_urgency):
        """Test filtering by minimum score."""
        result = filter_tasks_by_urgency(tasks_with_urgency, min_score=70.0)

        assert len(result) == 2
        assert all(t["urgency_score"] >= 70.0 for t in result)

    def test_filter_by_max_score(self, tasks_with_urgency):
        """Test filtering by maximum score."""
        result = filter_tasks_by_urgency(tasks_with_urgency, max_score=60.0)

        assert len(result) == 2
        assert all(t["urgency_score"] <= 60.0 for t in result)

    def test_filter_by_score_range(self, tasks_with_urgency):
        """Test filtering by score range."""
        result = filter_tasks_by_urgency(
            tasks_with_urgency, min_score=50.0, max_score=80.0
        )

        assert len(result) == 2

    def test_filter_by_levels(self, tasks_with_urgency):
        """Test filtering by urgency levels."""
        result = filter_tasks_by_urgency(
            tasks_with_urgency, levels=["critical", "high"]
        )

        assert len(result) == 2
        assert all(t["urgency_level"] in ["critical", "high"] for t in result)

    def test_filter_by_hitl_required(self, tasks_with_urgency):
        """Test filtering by HITL requirement."""
        result = filter_tasks_by_urgency(tasks_with_urgency, requires_hitl=True)

        assert len(result) == 2
        assert all(t["requires_hitl"] for t in result)

    def test_filter_combined(self, tasks_with_urgency):
        """Test combined filters."""
        result = filter_tasks_by_urgency(
            tasks_with_urgency,
            min_score=70.0,
            levels=["high"],
        )

        assert len(result) == 1
        assert result[0]["urgency_level"] == "high"


class TestSortTasksByUrgency:
    """Test sort_tasks_by_urgency function."""

    def test_sort_descending(self, tasks_with_urgency):
        """Test descending sort by urgency."""
        result = sort_tasks_by_urgency(tasks_with_urgency, descending=True)

        for i in range(len(result) - 1):
            assert result[i]["urgency_score"] >= result[i + 1]["urgency_score"]

    def test_sort_ascending(self, tasks_with_urgency):
        """Test ascending sort by urgency."""
        result = sort_tasks_by_urgency(tasks_with_urgency, descending=False)

        for i in range(len(result) - 1):
            assert result[i]["urgency_score"] <= result[i + 1]["urgency_score"]

    def test_sort_default_is_descending(self, tasks_with_urgency):
        """Test default sort is descending."""
        result = sort_tasks_by_urgency(tasks_with_urgency)

        assert result[0]["urgency_score"] == 92.5


class TestGetHitlCandidates:
    """Test get_hitl_candidates function."""

    def test_get_candidates_default(self, tasks_with_urgency):
        """Test getting HITL candidates using requires_hitl field."""
        result = get_hitl_candidates(tasks_with_urgency)

        assert len(result) == 2
        assert all(t["requires_hitl"] for t in result)

    def test_get_candidates_custom_threshold(self, tasks_with_urgency):
        """Test getting HITL candidates with custom threshold."""
        result = get_hitl_candidates(tasks_with_urgency, threshold=50.0)

        assert len(result) == 3
        assert all(t["urgency_score"] >= 50.0 for t in result)

    def test_candidates_sorted_by_urgency(self, tasks_with_urgency):
        """Test candidates are sorted by urgency."""
        result = get_hitl_candidates(tasks_with_urgency)

        # Should be sorted descending
        if len(result) > 1:
            assert result[0]["urgency_score"] >= result[1]["urgency_score"]

    def test_get_candidates_empty(self):
        """Test getting candidates from empty list."""
        result = get_hitl_candidates([])

        assert len(result) == 0


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_task_with_missing_fields(self):
        """Test task with missing optional fields."""
        task = {"id": "minimal"}

        result = calculate_task_urgency_score(task, 1000000.0)

        # Should use defaults and not crash
        assert result.urgency_score >= 0
        assert result.urgency_score <= 100

    def test_task_with_unicode_id(self):
        """Test task with Korean ID."""
        task = {
            "id": "작업-001",
            "name": "수익인식 테스트",
            "risk_score": 75,
        }

        result = calculate_task_urgency_score(task, 1000000.0)

        assert result.task_id == "작업-001"

    def test_zero_materiality(self, sample_tasks):
        """Test calculation with zero materiality."""
        result = calculate_urgency_scores(sample_tasks, 0.0)

        assert result.success is True
        # Should still calculate using risk-based defaults

    def test_negative_values(self):
        """Test handling of negative values."""
        task = {
            "id": "negative",
            "risk_score": -10,
            "metadata": {"amount": -1000, "ai_confidence": 1.5}
        }

        result = calculate_task_urgency_score(task, 1000000.0)

        # Should clamp values appropriately
        assert 0 <= result.urgency_score <= 100

    def test_large_task_list(self):
        """Test handling large number of tasks."""
        tasks = [
            {
                "id": f"task-{i}",
                "risk_score": 50,
                "metadata": {"amount": 100000}
            }
            for i in range(100)
        ]

        result = calculate_urgency_scores(tasks, 1000000.0)

        assert result.success is True
        assert result.total_tasks == 100
        assert len(result.tasks) == 100

    @pytest.mark.asyncio
    async def test_node_handles_malformed_task(self, base_audit_state):
        """Test node handles malformed task data."""
        base_audit_state["tasks"] = [
            {"id": None},  # Invalid
            {"id": "valid", "name": "Valid Task", "risk_score": 50},
        ]

        result = await urgency_node(base_audit_state)

        # Should still process what it can
        assert len(result["tasks"]) > 0

    def test_config_weight_validation(self):
        """Test handling of invalid weight configuration."""
        config = {
            "materiality_weight": 0.60,
            "risk_weight": 0.60,  # Weights > 1.0 total
            "ai_confidence_weight": 0.20,
            "hitl_threshold": 75.0,
        }

        task = {"id": "test", "risk_score": 50}
        # Should still calculate (may exceed 100, but clamped)
        result = calculate_task_urgency_score(task, 1000000.0, config)

        assert 0 <= result.urgency_score <= 100

    def test_decimal_precision(self):
        """Test decimal precision in scores."""
        task = {
            "id": "precision",
            "risk_score": 33.333,
            "metadata": {"amount": 333333.33, "ai_confidence": 0.777}
        }

        result = calculate_task_urgency_score(task, 1000000.0)

        # Score should be rounded to 2 decimal places
        assert result.urgency_score == round(result.urgency_score, 2)
