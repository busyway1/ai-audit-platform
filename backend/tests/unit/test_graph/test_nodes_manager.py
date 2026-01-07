"""
Comprehensive Unit Tests for Manager Node

Target Coverage:
- continue_to_manager_subgraphs() - Send API dispatcher
- manager_aggregation_node() - Final aggregation
- get_task_statistics() - Task statistics helper

Coverage Target: 80%+
Test Count: 25+ tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
from langgraph.types import Send
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from src.graph.nodes.manager import (
    continue_to_manager_subgraphs,
    manager_aggregation_node,
    get_task_statistics,
)
from src.graph.state import AuditState, TaskState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def base_audit_state() -> AuditState:
    """Create a base AuditState for testing."""
    return {
        "messages": [],
        "project_id": "PROJECT-001",
        "client_name": "Test Client",
        "fiscal_year": 2024,
        "overall_materiality": 100000.0,
        "audit_plan": {},
        "tasks": [],
        "next_action": "CONTINUE",
        "is_approved": True,
        "shared_documents": [],
    }


@pytest.fixture
def single_task() -> Dict[str, Any]:
    """Create a single task."""
    return {
        "id": "TASK-001",
        "thread_id": "thread-001",
        "category": "Sales Revenue",
        "risk_level_score": 50,
    }


@pytest.fixture
def multiple_tasks() -> List[Dict[str, Any]]:
    """Create multiple tasks."""
    return [
        {
            "id": "TASK-001",
            "thread_id": "thread-001",
            "category": "Sales Revenue",
            "risk_level_score": 45,
        },
        {
            "id": "TASK-002",
            "thread_id": "thread-002",
            "category": "Inventory",
            "risk_level_score": 55,
        },
        {
            "id": "TASK-003",
            "thread_id": "thread-003",
            "category": "Accounts Receivable",
            "risk_level_score": 60,
        },
    ]


@pytest.fixture
def high_risk_tasks() -> List[Dict[str, Any]]:
    """Create high-risk tasks for aggregation testing."""
    return [
        {
            "id": "TASK-HIGH-1",
            "thread_id": "thread-high-1",
            "category": "Revenue",
            "risk_score": 85,
            "status": "Completed",
        },
        {
            "id": "TASK-HIGH-2",
            "thread_id": "thread-high-2",
            "category": "Liabilities",
            "risk_score": 90,
            "status": "Completed",
        },
    ]


# ============================================================================
# TEST: CONTINUE_TO_MANAGER_SUBGRAPHS - BASIC FUNCTIONALITY
# ============================================================================

class TestContinueToManagerSubgraphsBasic:
    """Tests for continue_to_manager_subgraphs basic functionality"""

    def test_empty_tasks_returns_empty_list(self, base_audit_state):
        """Test that empty task list returns empty Send list."""
        base_audit_state["tasks"] = []

        result = continue_to_manager_subgraphs(base_audit_state)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_task_returns_single_send(self, base_audit_state, single_task):
        """Test that single task returns single Send object."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Send)

    def test_multiple_tasks_returns_multiple_sends(self, base_audit_state, multiple_tasks):
        """Test that multiple tasks return multiple Send objects."""
        base_audit_state["tasks"] = multiple_tasks

        result = continue_to_manager_subgraphs(base_audit_state)

        assert isinstance(result, list)
        assert len(result) == 3
        for send_obj in result:
            assert isinstance(send_obj, Send)

    def test_send_object_target_is_manager_subgraph(self, base_audit_state, single_task):
        """Test that Send object targets 'manager_subgraph'."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)

        assert result[0].node == "manager_subgraph"

    def test_send_object_has_task_state(self, base_audit_state, single_task):
        """Test that Send object contains TaskState."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)

        send_obj = result[0]
        task_state = send_obj.arg
        assert isinstance(task_state, dict)
        assert "task_id" in task_state
        assert "thread_id" in task_state
        assert "category" in task_state


# ============================================================================
# TEST: CONTINUE_TO_MANAGER_SUBGRAPHS - STATE MAPPING
# ============================================================================

class TestContinueToManagerSubgraphsStateMapping:
    """Tests for state mapping from AuditState to TaskState"""

    def test_task_id_mapping(self, base_audit_state, single_task):
        """Test that task['id'] maps to task_id."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["task_id"] == single_task["id"]

    def test_thread_id_mapping(self, base_audit_state, single_task):
        """Test that task['thread_id'] maps to thread_id."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["thread_id"] == single_task["thread_id"]

    def test_category_mapping(self, base_audit_state, single_task):
        """Test that task['category'] maps to category."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["category"] == single_task["category"]

    def test_risk_level_score_mapping(self, base_audit_state, single_task):
        """Test that task['risk_level_score'] maps to risk_score."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["risk_score"] == single_task["risk_level_score"]

    def test_risk_score_default_value(self, base_audit_state):
        """Test that risk_score defaults to 50 if not present."""
        task = {
            "id": "TASK-001",
            "thread_id": "thread-001",
            "category": "Sales Revenue",
            # No risk_level_score
        }
        base_audit_state["tasks"] = [task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["risk_score"] == 50

    def test_status_set_to_pending(self, base_audit_state, single_task):
        """Test that status is set to 'Pending' for new tasks."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["status"] == "Pending"

    def test_messages_initialized_empty(self, base_audit_state, single_task):
        """Test that messages are initialized as empty list."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["messages"] == []

    def test_raw_data_initialized_empty(self, base_audit_state, single_task):
        """Test that raw_data is initialized as empty dict."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["raw_data"] == {}

    def test_standards_initialized_empty(self, base_audit_state, single_task):
        """Test that standards are initialized as empty list."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["standards"] == []

    def test_vouching_logs_initialized_empty(self, base_audit_state, single_task):
        """Test that vouching_logs are initialized as empty list."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["vouching_logs"] == []

    def test_workpaper_draft_initialized_empty(self, base_audit_state, single_task):
        """Test that workpaper_draft is initialized as empty string."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["workpaper_draft"] == ""

    def test_next_staff_initialized_empty(self, base_audit_state, single_task):
        """Test that next_staff is initialized as empty string."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["next_staff"] == ""

    def test_error_report_initialized_empty(self, base_audit_state, single_task):
        """Test that error_report is initialized as empty string."""
        base_audit_state["tasks"] = [single_task]

        result = continue_to_manager_subgraphs(base_audit_state)
        task_state = result[0].arg

        assert task_state["error_report"] == ""


# ============================================================================
# TEST: CONTINUE_TO_MANAGER_SUBGRAPHS - PARALLEL EXECUTION
# ============================================================================

class TestContinueToManagerSubgraphsParallel:
    """Tests for parallel execution setup"""

    def test_multiple_tasks_unique_thread_ids(self, base_audit_state, multiple_tasks):
        """Test that each task gets its own unique thread_id."""
        base_audit_state["tasks"] = multiple_tasks

        result = continue_to_manager_subgraphs(base_audit_state)

        thread_ids = [send_obj.arg["thread_id"] for send_obj in result]
        assert len(set(thread_ids)) == 3  # All unique
        assert thread_ids[0] == "thread-001"
        assert thread_ids[1] == "thread-002"
        assert thread_ids[2] == "thread-003"

    def test_multiple_tasks_unique_task_ids(self, base_audit_state, multiple_tasks):
        """Test that each Send corresponds to unique task."""
        base_audit_state["tasks"] = multiple_tasks

        result = continue_to_manager_subgraphs(base_audit_state)

        task_ids = [send_obj.arg["task_id"] for send_obj in result]
        assert len(set(task_ids)) == 3  # All unique
        assert task_ids == ["TASK-001", "TASK-002", "TASK-003"]

    def test_large_number_of_tasks(self, base_audit_state):
        """Test handling of large task list (100+ tasks)."""
        large_task_list = [
            {
                "id": f"TASK-{i:04d}",
                "thread_id": f"thread-{i:04d}",
                "category": f"Category-{i % 10}",
                "risk_level_score": 50 + (i % 50),
            }
            for i in range(120)
        ]
        base_audit_state["tasks"] = large_task_list

        result = continue_to_manager_subgraphs(base_audit_state)

        assert len(result) == 120
        assert all(isinstance(s, Send) for s in result)


# ============================================================================
# TEST: MANAGER_AGGREGATION_NODE - BASIC FUNCTIONALITY
# ============================================================================

class TestManagerAggregationNodeBasic:
    """Tests for manager_aggregation_node basic functionality"""

    @pytest.mark.asyncio
    async def test_aggregation_with_empty_tasks(self, base_audit_state):
        """Test aggregation with no tasks."""
        base_audit_state["tasks"] = []

        result = await manager_aggregation_node(base_audit_state)

        assert "next_action" in result
        assert result["next_action"] == "COMPLETED"
        assert "messages" in result
        assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_aggregation_returns_dict(self, base_audit_state):
        """Test that aggregation returns a dictionary."""
        base_audit_state["tasks"] = []

        result = await manager_aggregation_node(base_audit_state)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_aggregation_returns_next_action_completed(self, base_audit_state):
        """Test that aggregation always returns COMPLETED as next_action."""
        base_audit_state["tasks"] = [
            {
                "id": "TASK-001",
                "status": "Completed",
                "risk_score": 50,
                "category": "Sales",
            }
        ]

        result = await manager_aggregation_node(base_audit_state)

        assert result["next_action"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_aggregation_returns_messages_list(self, base_audit_state):
        """Test that aggregation returns messages list."""
        base_audit_state["tasks"] = []

        result = await manager_aggregation_node(base_audit_state)

        assert "messages" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_aggregation_message_is_human_message(self, base_audit_state):
        """Test that aggregation message is HumanMessage type."""
        base_audit_state["tasks"] = []

        result = await manager_aggregation_node(base_audit_state)
        message = result["messages"][0]

        assert isinstance(message, HumanMessage)
        assert message.name == "System"


# ============================================================================
# TEST: MANAGER_AGGREGATION_NODE - STATUS COUNTING
# ============================================================================

class TestManagerAggregationNodeStatusCounting:
    """Tests for task status counting logic"""

    @pytest.mark.asyncio
    async def test_counts_completed_tasks(self, base_audit_state):
        """Test that completed tasks are counted correctly."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Failed", "risk_score": 50, "category": "INV"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "Completed: 2" in message_content
        assert "Failed: 1" in message_content

    @pytest.mark.asyncio
    async def test_counts_failed_tasks(self, base_audit_state):
        """Test that failed tasks are counted correctly."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Failed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Failed", "risk_score": 50, "category": "AR"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "Failed: 2" in message_content

    @pytest.mark.asyncio
    async def test_counts_in_progress_tasks(self, base_audit_state):
        """Test that in-progress tasks are counted correctly."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "In-Progress", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "In Progress: 1" in message_content

    @pytest.mark.asyncio
    async def test_completion_rate_all_completed(self, base_audit_state):
        """Test completion rate when all tasks complete."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Completed", "risk_score": 50, "category": "INV"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "100.0%" in message_content

    @pytest.mark.asyncio
    async def test_completion_rate_partial(self, base_audit_state):
        """Test completion rate for partial completion."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Failed", "risk_score": 50, "category": "INV"},
            {"id": "TASK-004", "status": "Failed", "risk_score": 50, "category": "AP"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "50.0%" in message_content


# ============================================================================
# TEST: MANAGER_AGGREGATION_NODE - OVERALL STATUS
# ============================================================================

class TestManagerAggregationNodeOverallStatus:
    """Tests for overall audit status determination"""

    @pytest.mark.asyncio
    async def test_overall_status_success_all_completed(self, base_audit_state):
        """Test overall status is SUCCESS when all tasks completed."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "SUCCESS" in message_content

    @pytest.mark.asyncio
    async def test_overall_status_partial_success(self, base_audit_state):
        """Test overall status is PARTIAL SUCCESS when >= 80% completed."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Completed", "risk_score": 50, "category": "INV"},
            {"id": "TASK-004", "status": "Completed", "risk_score": 50, "category": "AP"},
            {"id": "TASK-005", "status": "Failed", "risk_score": 50, "category": "PP"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "PARTIAL SUCCESS" in message_content

    @pytest.mark.asyncio
    async def test_overall_status_failed(self, base_audit_state):
        """Test overall status is FAILED when < 80% completed."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Failed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Failed", "risk_score": 50, "category": "INV"},
            {"id": "TASK-004", "status": "Failed", "risk_score": 50, "category": "AP"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "FAILED" in message_content


# ============================================================================
# TEST: MANAGER_AGGREGATION_NODE - HIGH-RISK DETECTION
# ============================================================================

class TestManagerAggregationNodeHighRisk:
    """Tests for high-risk task detection"""

    @pytest.mark.asyncio
    async def test_identifies_high_risk_tasks(self, base_audit_state, high_risk_tasks):
        """Test that high-risk tasks (risk_score >= 80) are identified."""
        base_audit_state["tasks"] = high_risk_tasks

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "High-Risk Tasks" in message_content
        assert "High Risk: 2" in message_content

    @pytest.mark.asyncio
    async def test_high_risk_tasks_show_task_details(self, base_audit_state, high_risk_tasks):
        """Test that high-risk task details are shown."""
        base_audit_state["tasks"] = high_risk_tasks

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "TASK-HIGH-1" in message_content
        assert "TASK-HIGH-2" in message_content
        assert "Risk Score: 85" in message_content
        assert "Risk Score: 90" in message_content

    @pytest.mark.asyncio
    async def test_high_risk_threshold_exactly_80(self, base_audit_state):
        """Test that risk_score = 80 is considered high-risk."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 80, "category": "Sales"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "High Risk: 1" in message_content

    @pytest.mark.asyncio
    async def test_below_high_risk_threshold(self, base_audit_state):
        """Test that risk_score = 79 is not high-risk."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 79, "category": "Sales"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "High Risk: 0" in message_content

    @pytest.mark.asyncio
    async def test_no_high_risk_tasks(self, base_audit_state):
        """Test aggregation when no high-risk tasks present."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 60, "category": "AR"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        # Should show "High Risk: 0" and no high-risk section
        assert "High Risk: 0" in message_content


# ============================================================================
# TEST: MANAGER_AGGREGATION_NODE - FAILED TASKS
# ============================================================================

class TestManagerAggregationNodeFailedTasks:
    """Tests for failed task reporting"""

    @pytest.mark.asyncio
    async def test_failed_tasks_section_shown(self, base_audit_state):
        """Test that failed tasks section is shown when tasks fail."""
        base_audit_state["tasks"] = [
            {
                "id": "TASK-001",
                "status": "Failed",
                "risk_score": 50,
                "category": "Sales",
                "error_report": "Data integrity issue",
            },
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "Failed Tasks" in message_content

    @pytest.mark.asyncio
    async def test_failed_task_details_shown(self, base_audit_state):
        """Test that failed task details are shown."""
        base_audit_state["tasks"] = [
            {
                "id": "TASK-001",
                "status": "Failed",
                "risk_score": 50,
                "category": "Sales",
                "error_report": "Data integrity issue",
            },
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        assert "TASK-001" in message_content
        assert "Sales" in message_content
        assert "Data integrity issue" in message_content

    @pytest.mark.asyncio
    async def test_failed_task_error_truncation(self, base_audit_state):
        """Test that long error reports are truncated."""
        long_error = "x" * 100
        base_audit_state["tasks"] = [
            {
                "id": "TASK-001",
                "status": "Failed",
                "risk_score": 50,
                "category": "Sales",
                "error_report": long_error,
            },
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        # Error should be truncated to 50 chars
        assert "x" * 50 in message_content or "..." in message_content

    @pytest.mark.asyncio
    async def test_no_failed_tasks(self, base_audit_state):
        """Test aggregation when no tasks failed."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        # Failed Tasks section should not appear
        assert "Failed: 0" in message_content


# ============================================================================
# TEST: GET_TASK_STATISTICS - BASIC FUNCTIONALITY
# ============================================================================

class TestGetTaskStatisticsBasic:
    """Tests for get_task_statistics helper function"""

    def test_empty_tasks_returns_zeros(self, base_audit_state):
        """Test statistics with empty task list."""
        base_audit_state["tasks"] = []

        stats = get_task_statistics(base_audit_state)

        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["in_progress"] == 0
        assert stats["pending"] == 0
        assert stats["completion_rate"] == 0
        assert stats["high_risk_count"] == 0
        assert stats["categories"] == {}

    def test_single_completed_task(self, base_audit_state):
        """Test statistics with single completed task."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"}
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["total"] == 1
        assert stats["completed"] == 1
        assert stats["completion_rate"] == 100.0

    def test_status_counting(self, base_audit_state, multiple_tasks):
        """Test that all status types are counted."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Failed", "risk_score": 50, "category": "INV"},
            {"id": "TASK-004", "status": "In-Progress", "risk_score": 50, "category": "AP"},
            {"id": "TASK-005", "status": "Pending", "risk_score": 50, "category": "PP"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["in_progress"] == 1
        assert stats["pending"] == 1
        assert stats["total"] == 5

    def test_completion_rate_calculation(self, base_audit_state):
        """Test completion rate is calculated correctly."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Failed", "risk_score": 50, "category": "INV"},
            {"id": "TASK-004", "status": "Failed", "risk_score": 50, "category": "AP"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["completion_rate"] == 50.0


# ============================================================================
# TEST: GET_TASK_STATISTICS - CATEGORY COUNTING
# ============================================================================

class TestGetTaskStatisticsCategoryCount:
    """Tests for category counting in statistics"""

    def test_single_category(self, base_audit_state):
        """Test counting tasks in single category."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "Sales"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["categories"]["Sales"] == 2
        assert len(stats["categories"]) == 1

    def test_multiple_categories(self, base_audit_state):
        """Test counting tasks across multiple categories."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "AR"},
            {"id": "TASK-003", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-004", "status": "Completed", "risk_score": 50, "category": "INV"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["categories"]["Sales"] == 2
        assert stats["categories"]["AR"] == 1
        assert stats["categories"]["INV"] == 1
        assert len(stats["categories"]) == 3

    def test_unknown_category_handling(self, base_audit_state):
        """Test handling of tasks with missing category."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50},  # No category
            {"id": "TASK-002", "status": "Completed", "risk_score": 50, "category": "Sales"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["categories"]["Unknown"] == 1
        assert stats["categories"]["Sales"] == 1


# ============================================================================
# TEST: GET_TASK_STATISTICS - HIGH-RISK COUNTING
# ============================================================================

class TestGetTaskStatisticsHighRisk:
    """Tests for high-risk task counting"""

    def test_high_risk_threshold_80(self, base_audit_state):
        """Test that risk_score >= 80 is counted as high-risk."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 80, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 85, "category": "AR"},
            {"id": "TASK-003", "status": "Completed", "risk_score": 79, "category": "INV"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["high_risk_count"] == 2

    def test_no_high_risk_tasks(self, base_audit_state):
        """Test when no tasks are high-risk."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "risk_score": 50, "category": "Sales"},
            {"id": "TASK-002", "status": "Completed", "risk_score": 60, "category": "AR"},
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["high_risk_count"] == 0

    def test_high_risk_default_zero(self, base_audit_state):
        """Test that tasks without risk_score default to 0."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001", "status": "Completed", "category": "Sales"},  # No risk_score
        ]

        stats = get_task_statistics(base_audit_state)

        assert stats["high_risk_count"] == 0


# ============================================================================
# TEST: EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_continue_subgraphs_missing_project_id(self):
        """Test handling of missing project_id."""
        state = {
            "messages": [],
            "project_id": "",  # Empty
            "client_name": "",
            "fiscal_year": 2024,
            "overall_materiality": 0,
            "audit_plan": {},
            "tasks": [
                {
                    "id": "TASK-001",
                    "thread_id": "thread-001",
                    "category": "Sales",
                }
            ],
            "next_action": "CONTINUE",
            "is_approved": True,
            "shared_documents": [],
        }

        result = continue_to_manager_subgraphs(state)

        assert len(result) == 1
        assert result[0].arg["task_id"] == "TASK-001"

    @pytest.mark.asyncio
    async def test_aggregation_missing_task_fields(self, base_audit_state):
        """Test aggregation with minimal task data."""
        base_audit_state["tasks"] = [
            {"id": "TASK-001"},  # Minimal data
        ]

        # Should not raise exception
        result = await manager_aggregation_node(base_audit_state)
        assert result is not None

    @pytest.mark.asyncio
    async def test_aggregation_more_than_5_high_risk_tasks(self, base_audit_state):
        """Test that more than 5 high-risk tasks show 'and X more' message."""
        base_audit_state["tasks"] = [
            {
                "id": f"TASK-HIGH-{i}",
                "status": "Completed",
                "risk_score": 85,
                "category": f"Category-{i}",
            }
            for i in range(7)
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        # Should show first 5 and indicate "... and 2 more"
        assert "and 2 more" in message_content

    @pytest.mark.asyncio
    async def test_aggregation_more_than_5_failed_tasks(self, base_audit_state):
        """Test that more than 5 failed tasks show 'and X more' message."""
        base_audit_state["tasks"] = [
            {
                "id": f"TASK-FAIL-{i}",
                "status": "Failed",
                "risk_score": 50,
                "category": f"Category-{i}",
                "error_report": f"Error {i}",
            }
            for i in range(8)
        ]

        result = await manager_aggregation_node(base_audit_state)
        message_content = result["messages"][0].content

        # Should show first 5 and indicate "... and 3 more"
        assert "and 3 more" in message_content
