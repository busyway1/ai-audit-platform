"""
Comprehensive Unit Tests for Task Generator Node

Target Coverage:
- task_generator_node() - Main task generation workflow
- generate_task_hierarchy() - Core hierarchy generation
- Helper functions for task creation
- Utility functions for task management

Coverage Target: 80%+
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
from datetime import datetime

from src.graph.nodes.task_generator import (
    task_generator_node,
    generate_task_hierarchy,
    generate_high_level_task,
    generate_mid_level_tasks,
    generate_low_level_tasks,
    get_task_summary,
    filter_tasks_by_level,
    filter_tasks_by_status,
    get_task_children,
    get_task_tree,
    sort_tasks_by_priority,
    sort_tasks_by_risk_score,
    _generate_task_id,
    _parse_risk_level,
    _calculate_risk_score,
    _select_assertions_for_ega,
    _get_procedures_for_assertion,
    _estimate_hours,
    _enrich_existing_tasks,
    _merge_tasks,
    _count_tasks_by_ega,
    GeneratedTask,
    TaskGenerationResult,
    TaskLevel,
    TaskStatus,
    RiskLevel,
    RISK_SCORE_MAP,
    STANDARD_ASSERTIONS,
    ASSERTION_PROCEDURES,
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
def sample_egas() -> List[Dict[str, Any]]:
    """Create sample EGAs for testing."""
    return [
        {
            "id": "ega-001",
            "project_id": "PROJECT-001",
            "name": "Revenue Recognition Testing",
            "description": "Test revenue recognition in accordance with K-IFRS 1115",
            "risk_level": "high",
            "priority": 85,
            "status": "pending",
            "metadata": {
                "category": "Revenue",
                "assertion": "Completeness, Accuracy",
            },
        },
        {
            "id": "ega-002",
            "project_id": "PROJECT-001",
            "name": "Inventory Physical Count",
            "description": "Observe and test physical inventory count procedures",
            "risk_level": "medium",
            "priority": 70,
            "metadata": {
                "category": "Inventory",
                "assertion": "Existence",
            },
        },
        {
            "id": "ega-003",
            "project_id": "PROJECT-001",
            "name": "Accounts Payable Completeness",
            "description": "Test completeness of accounts payable at year-end",
            "risk_level": "critical",
            "priority": 95,
            "metadata": {
                "category": "Payables",
            },
        },
    ]


@pytest.fixture
def state_with_egas(base_audit_state, sample_egas) -> AuditState:
    """Create state with EGAs."""
    base_audit_state["egas"] = sample_egas
    return base_audit_state


@pytest.fixture
def sample_generated_task() -> GeneratedTask:
    """Create a sample GeneratedTask."""
    return GeneratedTask(
        id="task-001",
        project_id="PROJECT-001",
        ega_id="ega-001",
        parent_task_id=None,
        task_level=TaskLevel.HIGH,
        name="Revenue Recognition Testing",
        description="Test revenue recognition",
        category="Revenue",
        risk_level=RiskLevel.HIGH,
        risk_score=75,
        status=TaskStatus.PENDING,
        priority=85,
    )


@pytest.fixture
def sample_task_hierarchy() -> List[Dict[str, Any]]:
    """Create a sample task hierarchy."""
    return [
        {
            "id": "task-high-001",
            "task_level": "High",
            "parent_task_id": None,
            "name": "Revenue Testing",
            "risk_score": 75,
            "priority": 85,
            "status": "Pending",
            "ega_id": "ega-001",
        },
        {
            "id": "task-mid-001",
            "task_level": "Mid",
            "parent_task_id": "task-high-001",
            "name": "Revenue Testing - Existence",
            "risk_score": 75,
            "priority": 85,
            "status": "Pending",
            "ega_id": "ega-001",
        },
        {
            "id": "task-mid-002",
            "task_level": "Mid",
            "parent_task_id": "task-high-001",
            "name": "Revenue Testing - Completeness",
            "risk_score": 75,
            "priority": 85,
            "status": "In-Progress",
            "ega_id": "ega-001",
        },
        {
            "id": "task-low-001",
            "task_level": "Low",
            "parent_task_id": "task-mid-001",
            "name": "Procedure: Physical inspection",
            "risk_score": 75,
            "priority": 84,
            "status": "Pending",
            "ega_id": "ega-001",
        },
        {
            "id": "task-low-002",
            "task_level": "Low",
            "parent_task_id": "task-mid-001",
            "name": "Procedure: Confirmation",
            "risk_score": 75,
            "priority": 83,
            "status": "Completed",
            "ega_id": "ega-001",
        },
    ]


# ============================================================================
# ENUM AND CONSTANT TESTS
# ============================================================================

class TestEnumsAndConstants:
    """Test enum classes and constants."""

    def test_task_level_enum_values(self):
        """Test TaskLevel enum has correct values."""
        assert TaskLevel.HIGH.value == "High"
        assert TaskLevel.MID.value == "Mid"
        assert TaskLevel.LOW.value == "Low"

    def test_task_status_enum_values(self):
        """Test TaskStatus enum has correct values."""
        assert TaskStatus.PENDING.value == "Pending"
        assert TaskStatus.IN_PROGRESS.value == "In-Progress"
        assert TaskStatus.REVIEW_REQUIRED.value == "Review-Required"
        assert TaskStatus.COMPLETED.value == "Completed"
        assert TaskStatus.FAILED.value == "Failed"

    def test_risk_level_enum_values(self):
        """Test RiskLevel enum has correct values."""
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"

    def test_risk_score_map_completeness(self):
        """Test RISK_SCORE_MAP has all risk levels."""
        assert RiskLevel.CRITICAL in RISK_SCORE_MAP
        assert RiskLevel.HIGH in RISK_SCORE_MAP
        assert RiskLevel.MEDIUM in RISK_SCORE_MAP
        assert RiskLevel.LOW in RISK_SCORE_MAP

    def test_risk_score_map_values(self):
        """Test RISK_SCORE_MAP has correct values."""
        assert RISK_SCORE_MAP[RiskLevel.CRITICAL] == 95
        assert RISK_SCORE_MAP[RiskLevel.HIGH] == 75
        assert RISK_SCORE_MAP[RiskLevel.MEDIUM] == 50
        assert RISK_SCORE_MAP[RiskLevel.LOW] == 25

    def test_standard_assertions_structure(self):
        """Test STANDARD_ASSERTIONS has required fields."""
        assert len(STANDARD_ASSERTIONS) == 6
        for assertion in STANDARD_ASSERTIONS:
            assert "name" in assertion
            assert "description" in assertion
            assert "code" in assertion

    def test_assertion_procedures_completeness(self):
        """Test ASSERTION_PROCEDURES has all assertion codes."""
        assertion_codes = [a["code"] for a in STANDARD_ASSERTIONS]
        for code in assertion_codes:
            assert code in ASSERTION_PROCEDURES


# ============================================================================
# DATA CLASS TESTS
# ============================================================================

class TestGeneratedTask:
    """Test GeneratedTask dataclass."""

    def test_generated_task_creation(self, sample_generated_task):
        """Test GeneratedTask creation with all fields."""
        assert sample_generated_task.id == "task-001"
        assert sample_generated_task.project_id == "PROJECT-001"
        assert sample_generated_task.task_level == TaskLevel.HIGH
        assert sample_generated_task.risk_level == RiskLevel.HIGH

    def test_generated_task_to_dict(self, sample_generated_task):
        """Test GeneratedTask.to_dict() method."""
        result = sample_generated_task.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "task-001"
        assert result["task_level"] == "High"
        assert result["risk_level"] == "high"
        assert result["status"] == "Pending"
        assert "created_at" in result
        assert "updated_at" in result

    def test_generated_task_defaults(self):
        """Test GeneratedTask default values."""
        task = GeneratedTask(id="test", project_id="proj")

        assert task.task_level == TaskLevel.HIGH
        assert task.risk_level == RiskLevel.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.priority == 50
        assert task.parent_task_id is None
        assert task.metadata == {}


class TestTaskGenerationResult:
    """Test TaskGenerationResult dataclass."""

    def test_task_generation_result_creation(self):
        """Test TaskGenerationResult creation."""
        result = TaskGenerationResult(
            success=True,
            tasks=[],
            high_level_count=5,
            mid_level_count=15,
            low_level_count=30,
        )

        assert result.success is True
        assert result.high_level_count == 5
        assert result.mid_level_count == 15
        assert result.low_level_count == 30

    def test_task_generation_result_defaults(self):
        """Test TaskGenerationResult default values."""
        result = TaskGenerationResult(success=True, tasks=[])

        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestGenerateTaskId:
    """Test _generate_task_id helper."""

    def test_generate_task_id_format(self):
        """Test generated ID has correct format."""
        task_id = _generate_task_id()
        assert task_id.startswith("task-")
        assert len(task_id) == 17  # "task-" + 12 hex chars

    def test_generate_task_id_uniqueness(self):
        """Test generated IDs are unique."""
        ids = {_generate_task_id() for _ in range(100)}
        assert len(ids) == 100


class TestParseRiskLevel:
    """Test _parse_risk_level helper."""

    def test_parse_risk_level_from_enum(self):
        """Test parsing from RiskLevel enum."""
        assert _parse_risk_level(RiskLevel.HIGH) == RiskLevel.HIGH
        assert _parse_risk_level(RiskLevel.CRITICAL) == RiskLevel.CRITICAL

    def test_parse_risk_level_from_string(self):
        """Test parsing from string values."""
        assert _parse_risk_level("high") == RiskLevel.HIGH
        assert _parse_risk_level("HIGH") == RiskLevel.HIGH
        assert _parse_risk_level("critical") == RiskLevel.CRITICAL
        assert _parse_risk_level("medium") == RiskLevel.MEDIUM
        assert _parse_risk_level("low") == RiskLevel.LOW

    def test_parse_risk_level_aliases(self):
        """Test parsing from alias strings."""
        assert _parse_risk_level("very high") == RiskLevel.CRITICAL
        assert _parse_risk_level("moderate") == RiskLevel.MEDIUM
        assert _parse_risk_level("minimal") == RiskLevel.LOW

    def test_parse_risk_level_none(self):
        """Test parsing None returns MEDIUM."""
        assert _parse_risk_level(None) == RiskLevel.MEDIUM

    def test_parse_risk_level_unknown(self):
        """Test parsing unknown value returns MEDIUM."""
        assert _parse_risk_level("unknown") == RiskLevel.MEDIUM
        assert _parse_risk_level(999) == RiskLevel.MEDIUM


class TestCalculateRiskScore:
    """Test _calculate_risk_score helper."""

    def test_calculate_risk_score_from_enum(self):
        """Test score calculation from enum."""
        assert _calculate_risk_score(RiskLevel.CRITICAL) == 95
        assert _calculate_risk_score(RiskLevel.HIGH) == 75
        assert _calculate_risk_score(RiskLevel.MEDIUM) == 50
        assert _calculate_risk_score(RiskLevel.LOW) == 25

    def test_calculate_risk_score_from_string(self):
        """Test score calculation from string."""
        assert _calculate_risk_score("critical") == 95
        assert _calculate_risk_score("high") == 75


class TestSelectAssertionsForEga:
    """Test _select_assertions_for_ega helper."""

    def test_select_assertions_revenue(self):
        """Test assertion selection for revenue EGA."""
        ega = {"name": "Revenue Recognition", "metadata": {"category": "Revenue"}}
        assertions = _select_assertions_for_ega(ega)

        assert len(assertions) > 0
        assertion_codes = [a["code"] for a in assertions]
        assert "EO" in assertion_codes  # Existence/Occurrence
        assert "C" in assertion_codes   # Completeness

    def test_select_assertions_inventory(self):
        """Test assertion selection for inventory EGA."""
        ega = {"name": "Inventory Count", "metadata": {"category": "Inventory"}}
        assertions = _select_assertions_for_ega(ega)

        assertion_codes = [a["code"] for a in assertions]
        assert "EO" in assertion_codes

    def test_select_assertions_from_metadata(self):
        """Test assertion selection from explicit metadata."""
        ega = {
            "name": "Custom Test",
            "metadata": {"assertion": "Existence/Occurrence"}
        }
        assertions = _select_assertions_for_ega(ega)

        assert len(assertions) > 0
        assert assertions[0]["code"] == "EO"

    def test_select_assertions_default(self):
        """Test default assertion selection."""
        ega = {"name": "Unknown Category", "metadata": {}}
        assertions = _select_assertions_for_ega(ega)

        # Should return default assertions
        assert len(assertions) > 0


class TestGetProceduresForAssertion:
    """Test _get_procedures_for_assertion helper."""

    def test_get_procedures_existence(self):
        """Test procedures for Existence/Occurrence assertion."""
        procedures = _get_procedures_for_assertion("EO")
        assert len(procedures) > 0
        assert "Physical inspection" in procedures[0]

    def test_get_procedures_completeness(self):
        """Test procedures for Completeness assertion."""
        procedures = _get_procedures_for_assertion("C")
        assert len(procedures) > 0

    def test_get_procedures_max_limit(self):
        """Test max procedures limit."""
        procedures = _get_procedures_for_assertion("EO", max_procedures=1)
        assert len(procedures) == 1

    def test_get_procedures_unknown(self):
        """Test procedures for unknown assertion code."""
        procedures = _get_procedures_for_assertion("UNKNOWN")
        assert procedures == []


class TestEstimateHours:
    """Test _estimate_hours helper."""

    def test_estimate_hours_high_level(self):
        """Test hours estimation for HIGH level."""
        hours = _estimate_hours(TaskLevel.HIGH, RiskLevel.MEDIUM)
        assert hours == 0.0  # Container task

    def test_estimate_hours_mid_level(self):
        """Test hours estimation for MID level."""
        hours = _estimate_hours(TaskLevel.MID, RiskLevel.MEDIUM)
        assert hours == 4.0

    def test_estimate_hours_low_level(self):
        """Test hours estimation for LOW level."""
        hours = _estimate_hours(TaskLevel.LOW, RiskLevel.MEDIUM)
        assert hours == 2.0

    def test_estimate_hours_risk_multiplier(self):
        """Test risk multiplier effect."""
        critical = _estimate_hours(TaskLevel.MID, RiskLevel.CRITICAL)
        low = _estimate_hours(TaskLevel.MID, RiskLevel.LOW)

        assert critical > low


# ============================================================================
# TASK GENERATION FUNCTION TESTS
# ============================================================================

class TestGenerateHighLevelTask:
    """Test generate_high_level_task function."""

    def test_generate_high_level_task_basic(self, sample_egas):
        """Test basic high-level task generation."""
        ega = sample_egas[0]
        task = generate_high_level_task(ega, "PROJECT-001")

        assert task.task_level == TaskLevel.HIGH
        assert task.parent_task_id is None
        assert task.name == ega["name"]
        assert task.ega_id == ega["id"]
        assert task.project_id == "PROJECT-001"

    def test_generate_high_level_task_risk(self, sample_egas):
        """Test risk level and score assignment."""
        ega = sample_egas[0]  # High risk
        task = generate_high_level_task(ega, "PROJECT-001")

        assert task.risk_level == RiskLevel.HIGH
        assert task.risk_score == 75

    def test_generate_high_level_task_metadata(self, sample_egas):
        """Test metadata assignment."""
        ega = sample_egas[0]
        task = generate_high_level_task(ega, "PROJECT-001")

        assert "source" in task.metadata
        assert task.metadata["source"] == "ega"
        assert task.metadata["ega_id"] == ega["id"]


class TestGenerateMidLevelTasks:
    """Test generate_mid_level_tasks function."""

    def test_generate_mid_level_tasks_basic(self, sample_egas):
        """Test basic mid-level task generation."""
        ega = sample_egas[0]
        high_task = generate_high_level_task(ega, "PROJECT-001")
        mid_tasks = generate_mid_level_tasks(high_task, ega)

        assert len(mid_tasks) > 0
        for task in mid_tasks:
            assert task.task_level == TaskLevel.MID
            assert task.parent_task_id == high_task.id

    def test_generate_mid_level_tasks_assertions(self, sample_egas):
        """Test assertion assignment to mid-level tasks."""
        ega = sample_egas[0]
        high_task = generate_high_level_task(ega, "PROJECT-001")
        mid_tasks = generate_mid_level_tasks(high_task, ega)

        for task in mid_tasks:
            assert task.assertion is not None
            assert task.assertion != ""

    def test_generate_mid_level_tasks_inherit_risk(self, sample_egas):
        """Test risk level inheritance from high-level task."""
        ega = sample_egas[0]
        high_task = generate_high_level_task(ega, "PROJECT-001")
        mid_tasks = generate_mid_level_tasks(high_task, ega)

        for task in mid_tasks:
            assert task.risk_level == high_task.risk_level


class TestGenerateLowLevelTasks:
    """Test generate_low_level_tasks function."""

    def test_generate_low_level_tasks_basic(self, sample_egas):
        """Test basic low-level task generation."""
        ega = sample_egas[0]
        high_task = generate_high_level_task(ega, "PROJECT-001")
        mid_tasks = generate_mid_level_tasks(high_task, ega)

        if mid_tasks:
            low_tasks = generate_low_level_tasks(mid_tasks[0])

            assert len(low_tasks) > 0
            for task in low_tasks:
                assert task.task_level == TaskLevel.LOW
                assert task.parent_task_id == mid_tasks[0].id

    def test_generate_low_level_tasks_procedures(self, sample_egas):
        """Test procedure assignment to low-level tasks."""
        ega = sample_egas[0]
        high_task = generate_high_level_task(ega, "PROJECT-001")
        mid_tasks = generate_mid_level_tasks(high_task, ega)

        if mid_tasks:
            low_tasks = generate_low_level_tasks(mid_tasks[0])

            for task in low_tasks:
                assert task.procedure_type is not None
                assert "Procedure:" in task.name


class TestGenerateTaskHierarchy:
    """Test generate_task_hierarchy function."""

    def test_generate_task_hierarchy_basic(self, sample_egas):
        """Test basic hierarchy generation."""
        result = generate_task_hierarchy(sample_egas, "PROJECT-001")

        assert result.success is True
        assert result.high_level_count == 3
        assert result.mid_level_count > 0
        assert result.low_level_count > 0
        assert len(result.tasks) > 0

    def test_generate_task_hierarchy_structure(self, sample_egas):
        """Test hierarchy structure is correct."""
        result = generate_task_hierarchy(sample_egas, "PROJECT-001")

        # Check we have all levels
        levels = {t.task_level for t in result.tasks}
        assert TaskLevel.HIGH in levels
        assert TaskLevel.MID in levels
        assert TaskLevel.LOW in levels

    def test_generate_task_hierarchy_linking(self, sample_egas):
        """Test parent-child linking."""
        result = generate_task_hierarchy(sample_egas, "PROJECT-001")

        task_ids = {t.id for t in result.tasks}

        for task in result.tasks:
            if task.parent_task_id:
                # Parent ID should exist in task list
                assert task.parent_task_id in task_ids

    def test_generate_task_hierarchy_no_low_level(self, sample_egas):
        """Test hierarchy without low-level tasks."""
        result = generate_task_hierarchy(
            sample_egas, "PROJECT-001", include_low_level=False
        )

        assert result.low_level_count == 0
        levels = {t.task_level for t in result.tasks}
        assert TaskLevel.LOW not in levels

    def test_generate_task_hierarchy_empty_egas(self):
        """Test hierarchy generation with empty EGAs."""
        result = generate_task_hierarchy([], "PROJECT-001")

        assert result.success is False
        assert len(result.errors) > 0

    def test_generate_task_hierarchy_invalid_ega(self):
        """Test hierarchy generation with invalid EGA."""
        egas = [{"id": "invalid", "metadata": {}}]  # Missing name
        result = generate_task_hierarchy(egas, "PROJECT-001")

        assert len(result.warnings) > 0


# ============================================================================
# LANGGRAPH NODE TESTS
# ============================================================================

class TestTaskGeneratorNode:
    """Test task_generator_node function."""

    @pytest.mark.asyncio
    async def test_task_generator_node_basic(self, state_with_egas):
        """Test basic task generation node execution."""
        result = await task_generator_node(state_with_egas)

        assert "tasks" in result
        assert "messages" in result
        assert len(result["tasks"]) > 0

    @pytest.mark.asyncio
    async def test_task_generator_node_message(self, state_with_egas):
        """Test node generates appropriate message."""
        result = await task_generator_node(state_with_egas)

        assert len(result["messages"]) == 1
        message = result["messages"][0]
        assert "Task Generator" in message.content
        assert "High:" in message.content
        assert "Mid:" in message.content
        assert "Low:" in message.content

    @pytest.mark.asyncio
    async def test_task_generator_node_no_egas(self, base_audit_state):
        """Test node with no EGAs."""
        result = await task_generator_node(base_audit_state)

        assert "tasks" in result
        # Should have warning message about no EGAs

    @pytest.mark.asyncio
    async def test_task_generator_node_existing_tasks(self, base_audit_state):
        """Test node enriches existing tasks when no EGAs."""
        base_audit_state["tasks"] = [
            {"id": "existing-001", "name": "Existing Task", "status": "Pending"}
        ]
        result = await task_generator_node(base_audit_state)

        assert len(result["tasks"]) > 0
        # Should have enriched task
        enriched = result["tasks"][0]
        assert "task_level" in enriched
        assert "risk_score" in enriched

    @pytest.mark.asyncio
    async def test_task_generator_node_task_dict_format(self, state_with_egas):
        """Test tasks are in dictionary format."""
        result = await task_generator_node(state_with_egas)

        for task in result["tasks"]:
            assert isinstance(task, dict)
            assert "id" in task
            assert "task_level" in task
            assert "parent_task_id" in task


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestEnrichExistingTasks:
    """Test _enrich_existing_tasks function."""

    def test_enrich_existing_tasks_adds_level(self):
        """Test enrichment adds task_level."""
        tasks = [{"id": "task-1", "name": "Test"}]
        result = _enrich_existing_tasks(tasks, "PROJECT-001")

        assert result[0]["task_level"] == "High"

    def test_enrich_existing_tasks_adds_parent_id(self):
        """Test enrichment adds parent_task_id."""
        tasks = [{"id": "task-1"}]
        result = _enrich_existing_tasks(tasks, "PROJECT-001")

        assert result[0]["parent_task_id"] is None

    def test_enrich_existing_tasks_adds_project_id(self):
        """Test enrichment adds project_id."""
        tasks = [{"id": "task-1"}]
        result = _enrich_existing_tasks(tasks, "PROJECT-001")

        assert result[0]["project_id"] == "PROJECT-001"

    def test_enrich_existing_tasks_calculates_risk_score(self):
        """Test enrichment calculates risk_score."""
        tasks = [{"id": "task-1", "risk_level": "high"}]
        result = _enrich_existing_tasks(tasks, "PROJECT-001")

        assert result[0]["risk_score"] == 75


class TestMergeTasks:
    """Test _merge_tasks function."""

    def test_merge_tasks_no_overlap(self):
        """Test merging tasks with no overlap."""
        existing = [{"id": "e-1", "ega_id": "ega-1"}]
        generated = [{"id": "g-1", "ega_id": "ega-2"}]

        result = _merge_tasks(existing, generated)
        assert len(result) == 2

    def test_merge_tasks_with_overlap(self):
        """Test merging tasks with overlap."""
        existing = [{"id": "e-1", "ega_id": "ega-1", "name": "Old"}]
        generated = [{"id": "g-1", "ega_id": "ega-1", "name": "New"}]

        result = _merge_tasks(existing, generated)
        # Should replace existing with generated
        assert len(result) == 1
        assert result[0]["name"] == "New"


class TestCountTasksByEga:
    """Test _count_tasks_by_ega function."""

    def test_count_tasks_by_ega_basic(self, sample_task_hierarchy):
        """Test basic task counting."""
        counts = _count_tasks_by_ega(sample_task_hierarchy)

        assert "ega-001" in counts
        assert counts["ega-001"] == 5


class TestGetTaskSummary:
    """Test get_task_summary function."""

    def test_get_task_summary_basic(self, sample_task_hierarchy):
        """Test basic summary generation."""
        summary = get_task_summary(sample_task_hierarchy)

        assert summary["total"] == 5
        assert "by_level" in summary
        assert "by_status" in summary

    def test_get_task_summary_levels(self, sample_task_hierarchy):
        """Test level counts in summary."""
        summary = get_task_summary(sample_task_hierarchy)

        assert summary["by_level"]["High"] == 1
        assert summary["by_level"]["Mid"] == 2
        assert summary["by_level"]["Low"] == 2

    def test_get_task_summary_empty(self):
        """Test summary with empty list."""
        summary = get_task_summary([])

        assert summary["total"] == 0
        assert summary["average_risk_score"] == 0


class TestFilterTasksByLevel:
    """Test filter_tasks_by_level function."""

    def test_filter_high_level(self, sample_task_hierarchy):
        """Test filtering high-level tasks."""
        result = filter_tasks_by_level(sample_task_hierarchy, ["High"])

        assert len(result) == 1
        assert result[0]["task_level"] == "High"

    def test_filter_multiple_levels(self, sample_task_hierarchy):
        """Test filtering multiple levels."""
        result = filter_tasks_by_level(sample_task_hierarchy, ["High", "Mid"])

        assert len(result) == 3


class TestFilterTasksByStatus:
    """Test filter_tasks_by_status function."""

    def test_filter_pending_tasks(self, sample_task_hierarchy):
        """Test filtering pending tasks."""
        result = filter_tasks_by_status(sample_task_hierarchy, ["Pending"])

        assert all(t["status"] == "Pending" for t in result)

    def test_filter_completed_tasks(self, sample_task_hierarchy):
        """Test filtering completed tasks."""
        result = filter_tasks_by_status(sample_task_hierarchy, ["Completed"])

        assert len(result) == 1


class TestGetTaskChildren:
    """Test get_task_children function."""

    def test_get_task_children_basic(self, sample_task_hierarchy):
        """Test getting children of a task."""
        children = get_task_children(sample_task_hierarchy, "task-high-001")

        assert len(children) == 2
        for child in children:
            assert child["parent_task_id"] == "task-high-001"

    def test_get_task_children_leaf(self, sample_task_hierarchy):
        """Test getting children of a leaf task."""
        children = get_task_children(sample_task_hierarchy, "task-low-001")

        assert len(children) == 0


class TestGetTaskTree:
    """Test get_task_tree function."""

    def test_get_task_tree_basic(self, sample_task_hierarchy):
        """Test building task tree."""
        tree = get_task_tree(sample_task_hierarchy)

        assert len(tree) == 1  # One root
        assert tree[0]["id"] == "task-high-001"
        assert "children" in tree[0]

    def test_get_task_tree_nested_children(self, sample_task_hierarchy):
        """Test nested children in tree."""
        tree = get_task_tree(sample_task_hierarchy)

        root = tree[0]
        assert len(root["children"]) == 2  # Two mid-level

        mid = root["children"][0]
        assert len(mid["children"]) == 2  # Two low-level


class TestSortTasksByPriority:
    """Test sort_tasks_by_priority function."""

    def test_sort_descending(self, sample_task_hierarchy):
        """Test descending sort by priority."""
        result = sort_tasks_by_priority(sample_task_hierarchy, descending=True)

        for i in range(len(result) - 1):
            assert result[i]["priority"] >= result[i + 1]["priority"]

    def test_sort_ascending(self, sample_task_hierarchy):
        """Test ascending sort by priority."""
        result = sort_tasks_by_priority(sample_task_hierarchy, descending=False)

        for i in range(len(result) - 1):
            assert result[i]["priority"] <= result[i + 1]["priority"]


class TestSortTasksByRiskScore:
    """Test sort_tasks_by_risk_score function."""

    def test_sort_by_risk_descending(self, sample_task_hierarchy):
        """Test descending sort by risk score."""
        result = sort_tasks_by_risk_score(sample_task_hierarchy, descending=True)

        for i in range(len(result) - 1):
            assert result[i]["risk_score"] >= result[i + 1]["risk_score"]


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_ega_with_no_metadata(self):
        """Test EGA without metadata."""
        ega = {"id": "test", "name": "Test EGA"}
        task = generate_high_level_task(ega, "PROJECT-001")

        assert task.category == "General"

    def test_ega_with_unicode_name(self):
        """Test EGA with Korean name."""
        ega = {
            "id": "test",
            "name": "수익인식 테스트",
            "description": "K-IFRS 1115에 따른 수익인식 테스트",
            "risk_level": "high",
            "metadata": {"category": "수익"},
        }
        task = generate_high_level_task(ega, "PROJECT-001")

        assert task.name == "수익인식 테스트"
        assert task.category == "수익"

    def test_large_ega_list(self):
        """Test handling large number of EGAs."""
        egas = [
            {
                "id": f"ega-{i}",
                "name": f"Test EGA {i}",
                "risk_level": "medium",
                "metadata": {},
            }
            for i in range(100)
        ]

        result = generate_task_hierarchy(egas, "PROJECT-001")

        assert result.success is True
        assert result.high_level_count == 100
        assert len(result.tasks) > 100  # High + Mid + Low

    def test_task_to_dict_enum_conversion(self):
        """Test enum values are converted to strings in to_dict."""
        task = GeneratedTask(
            id="test",
            project_id="proj",
            task_level=TaskLevel.MID,
            risk_level=RiskLevel.HIGH,
            status=TaskStatus.IN_PROGRESS,
        )

        result = task.to_dict()

        assert result["task_level"] == "Mid"
        assert result["risk_level"] == "high"
        assert result["status"] == "In-Progress"

    @pytest.mark.asyncio
    async def test_node_handles_malformed_ega(self, base_audit_state):
        """Test node handles malformed EGA data."""
        base_audit_state["egas"] = [
            {"name": None},  # Invalid
            {"id": "valid", "name": "Valid EGA"},
        ]

        result = await task_generator_node(base_audit_state)

        # Should still generate tasks for valid EGA
        assert len(result["tasks"]) > 0
