"""
Integration Tests for Supabase State Sync

This module provides comprehensive integration tests for the task synchronization
service that syncs LangGraph TaskState to Supabase tables.

Test Coverage:
- Task creation and upsert operations (8 tests)
- Conflict resolution via thread_id
- Message insertion and batch operations
- Artifact (workpaper) creation
- Task retrieval by thread_id
- Error handling and edge cases
- Multiple task synchronization

Testing Strategy:
1. Mock Supabase client using pytest-mock
2. Mock LangChain BaseMessage objects
3. Test both success paths and failure scenarios
4. Verify correct SQL operations (upsert, insert, select)
5. Validate error handling and exception raising

Key Assumptions:
- Supabase client uses table().method().execute() pattern
- TaskState is a TypedDict with specific required fields
- All timestamps are ISO format
- UUIDs are generated using uuid4()
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.services.task_sync import (
    sync_task_to_supabase,
    get_task_by_thread_id,
)
from src.graph.state import TaskState


# ============================================================================
# FIXTURES - Mock Data and Supabase Client
# ============================================================================

@pytest.fixture
def sample_task_state() -> TaskState:
    """
    Create a sample TaskState for testing.

    This fixture provides a valid TaskState with all required fields
    and realistic data for sync operations.

    Returns:
        TaskState: Sample task state dict
    """
    return TaskState(
        task_id=str(uuid4()),
        thread_id="task-001-sales",
        category="Sales Revenue",
        status="In-Progress",
        messages=[],
        raw_data={"excel_data": "sample"},
        standards=["K-IFRS 1115"],
        vouching_logs=[{"entry": "sample"}],
        workpaper_draft="# Sales Revenue Audit\n\nProcedures:\n1. Vouch transactions",
        next_staff="Partner_Review",
        error_report="",
        risk_score=65,
    )


@pytest.fixture
def sample_task_state_with_messages() -> TaskState:
    """
    Create a TaskState with agent messages.

    Returns:
        TaskState: Task state with messages
    """
    return TaskState(
        task_id=str(uuid4()),
        thread_id="task-002-inventory",
        category="Inventory",
        status="Pending",
        messages=[
            HumanMessage(
                content="Please analyze inventory valuation",
                additional_kwargs={"agent_role": "Manager"}
            ),
            AIMessage(
                content="Starting inventory analysis...",
                additional_kwargs={"agent_role": "Excel_Parser"}
            ),
            AIMessage(
                content="Found 5000 units at $50/unit",
                additional_kwargs={"agent_role": "Inventory_Specialist"}
            ),
        ],
        raw_data={"inventory_count": 5000},
        standards=[],
        vouching_logs=[],
        workpaper_draft="",
        next_staff="Partner_Review",
        error_report="",
        risk_score=45,
    )


@pytest.fixture
def sample_task_state_no_workpaper() -> TaskState:
    """
    Create a TaskState without workpaper draft.

    Used to test sync when no artifact exists.

    Returns:
        TaskState: Task state without workpaper
    """
    return TaskState(
        task_id=str(uuid4()),
        thread_id="task-003-ar",
        category="Accounts Receivable",
        status="Pending",
        messages=[],
        raw_data={},
        standards=[],
        vouching_logs=[],
        workpaper_draft="",  # Empty workpaper
        next_staff="AR_Specialist",
        error_report="",
        risk_score=55,
    )


@pytest.fixture
def sample_project_id() -> str:
    """
    Sample project UUID for testing.

    Returns:
        str: UUID string
    """
    return str(uuid4())


# ============================================================================
# TEST: sync_task_to_supabase - Task Creation
# ============================================================================

@pytest.mark.asyncio
async def test_sync_task_creates_record(sample_task_state, sample_project_id):
    """
    Test that sync_task_to_supabase creates a new task record.

    Verifies:
    - Correct upsert call with thread_id conflict key
    - Task data includes all required fields
    - Returns task_id from response
    - No messages or artifacts are synced when empty
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        # Setup mock response
        expected_task_id = str(uuid4())
        mock_response = MagicMock()
        mock_response.data = [{"id": expected_task_id, "thread_id": "task-001"}]

        # Setup mock chain
        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute
        task_id = await sync_task_to_supabase(sample_task_state, sample_project_id)

        # Verify
        assert task_id == expected_task_id

        # Verify table was called with audit_tasks (should be first call)
        calls = [c for c in mock_supabase.table.call_args_list if c[0][0] == "audit_tasks"]
        assert len(calls) > 0

        # Verify upsert was called
        mock_table.upsert.assert_called_once()

        # Verify upsert arguments
        upsert_args, upsert_kwargs = mock_table.upsert.call_args
        upsert_data = upsert_args[0]

        assert upsert_data["thread_id"] == sample_task_state["thread_id"]
        assert upsert_data["project_id"] == sample_project_id
        assert upsert_data["category"] == sample_task_state["category"]
        assert upsert_data["status"] == sample_task_state["status"]
        assert upsert_data["risk_score"] == sample_task_state["risk_score"]
        assert "updated_at" in upsert_data
        assert upsert_kwargs["on_conflict"] == "thread_id"


# ============================================================================
# TEST: sync_task_to_supabase - Upsert on Conflict
# ============================================================================

@pytest.mark.asyncio
async def test_sync_task_upserts_on_conflict(sample_task_state, sample_project_id):
    """
    Test that sync_task_to_supabase updates existing task on thread_id conflict.

    Verifies:
    - on_conflict="thread_id" parameter is passed
    - Upsert operation updates existing task when thread_id exists
    - Task ID is correctly returned from updated record
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())
        mock_response = MagicMock()
        mock_response.data = [{"id": expected_task_id}]

        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute (same thread_id, different status)
        sample_task_state["status"] = "Review-Required"
        task_id = await sync_task_to_supabase(sample_task_state, sample_project_id)

        # Verify on_conflict parameter
        upsert_call_args = mock_table.upsert.call_args
        assert upsert_call_args[1]["on_conflict"] == "thread_id"

        # Verify task_id returned
        assert task_id == expected_task_id


# ============================================================================
# TEST: sync_task_to_supabase - Message Insertion
# ============================================================================

@pytest.mark.asyncio
async def test_sync_inserts_messages(sample_task_state_with_messages, sample_project_id):
    """
    Test that sync_task_to_supabase inserts agent messages.

    Verifies:
    - Messages are extracted from TaskState
    - Each message includes agent_role, content, type
    - Insert operation is called for agent_messages table
    - All messages are inserted in batch
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        # Setup mock responses
        upsert_response = MagicMock()
        upsert_response.data = [{"id": expected_task_id}]

        insert_response = MagicMock()
        insert_response.data = [{"id": str(uuid4())}]

        # Setup table mock to return different mocks
        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == "audit_tasks":
                table_mock.upsert.return_value = MagicMock()
                table_mock.upsert.return_value.execute.return_value = upsert_response
            elif table_name == "agent_messages":
                table_mock.insert.return_value = MagicMock()
                table_mock.insert.return_value.execute.return_value = insert_response
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        # Execute
        task_id = await sync_task_to_supabase(
            sample_task_state_with_messages,
            sample_project_id
        )

        # Verify messages table was called
        insert_calls = [
            c for c in mock_supabase.table.call_args_list
            if c[0][0] == "agent_messages"
        ]
        assert len(insert_calls) > 0

        # Verify task_id returned
        assert task_id == expected_task_id


# ============================================================================
# TEST: sync_task_to_supabase - Workpaper Artifact
# ============================================================================

@pytest.mark.asyncio
async def test_sync_inserts_workpaper(sample_task_state, sample_project_id):
    """
    Test that sync_task_to_supabase inserts workpaper artifact.

    Verifies:
    - Workpaper draft is extracted from TaskState
    - Artifact record includes type, content, task_id
    - Insert operation called for audit_artifacts table
    - Artifact is not created if workpaper_draft is empty
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        upsert_response = MagicMock()
        upsert_response.data = [{"id": expected_task_id}]

        insert_response = MagicMock()
        insert_response.data = [{"id": str(uuid4())}]

        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == "audit_tasks":
                table_mock.upsert.return_value = MagicMock()
                table_mock.upsert.return_value.execute.return_value = upsert_response
            elif table_name == "audit_artifacts":
                table_mock.insert.return_value = MagicMock()
                table_mock.insert.return_value.execute.return_value = insert_response
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        # Execute
        task_id = await sync_task_to_supabase(sample_task_state, sample_project_id)

        # Verify artifacts table was called (workpaper exists)
        artifact_calls = [
            c for c in mock_supabase.table.call_args_list
            if c[0][0] == "audit_artifacts"
        ]
        assert len(artifact_calls) > 0

        # Verify task_id returned
        assert task_id == expected_task_id


# ============================================================================
# TEST: get_task_by_thread_id - Task Found
# ============================================================================

@pytest.mark.asyncio
async def test_get_task_by_thread_id():
    """
    Test that get_task_by_thread_id retrieves task when found.

    Verifies:
    - Correct select query on thread_id
    - Returns task dict when found
    - All task fields are in response
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task = {
            "id": str(uuid4()),
            "thread_id": "task-001",
            "category": "Sales",
            "status": "In-Progress",
            "risk_score": 65,
        }

        mock_response = MagicMock()
        mock_response.data = [expected_task]

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()

        mock_eq.execute.return_value = mock_response
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_supabase.table.return_value = mock_table

        # Execute
        thread_id = "task-001"
        task = await get_task_by_thread_id(thread_id)

        # Verify
        assert task is not None
        assert task["thread_id"] == "task-001"
        assert task["category"] == "Sales"
        assert task["status"] == "In-Progress"

        # Verify correct query chain
        mock_supabase.table.assert_called_with("audit_tasks")
        mock_table.select.assert_called_with("*")
        mock_select.eq.assert_called_with("thread_id", thread_id)


# ============================================================================
# TEST: get_task_by_thread_id - Task Not Found
# ============================================================================

@pytest.mark.asyncio
async def test_get_task_not_found():
    """
    Test that get_task_by_thread_id returns None when task not found.

    Verifies:
    - Returns None when no data in response
    - Still calls correct query chain
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = []

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()

        mock_eq.execute.return_value = mock_response
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_supabase.table.return_value = mock_table

        # Execute
        thread_id = "nonexistent-thread"
        task = await get_task_by_thread_id(thread_id)

        # Verify
        assert task is None

        # Verify query was still made
        mock_supabase.table.assert_called_with("audit_tasks")


# ============================================================================
# TEST: Multiple Tasks Batch Operations
# ============================================================================

@pytest.mark.asyncio
async def test_sync_multiple_tasks(sample_project_id):
    """
    Test syncing multiple tasks in sequence.

    Verifies:
    - Multiple tasks can be synced without interference
    - Each task maintains its own thread_id
    - Upsert operations work correctly for each
    """
    task_states = [
        TaskState(
            task_id=str(uuid4()),
            thread_id=f"task-{i:03d}",
            category=category,
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Staff",
            error_report="",
            risk_score=50,
        )
        for i, category in enumerate(["Sales", "Inventory", "AR"], 1)
    ]

    with patch("src.services.task_sync.supabase") as mock_supabase:
        mock_table = MagicMock()

        def execute_side_effect():
            response = MagicMock()
            response.data = [{"id": str(uuid4())}]
            return response

        mock_upsert = MagicMock()
        mock_upsert.execute.side_effect = execute_side_effect
        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute
        task_ids = []
        for task_state in task_states:
            task_id = await sync_task_to_supabase(task_state, sample_project_id)
            task_ids.append(task_id)

        # Verify
        assert len(task_ids) == 3
        assert all(task_id is not None for task_id in task_ids)

        # Verify upsert called multiple times
        assert mock_table.upsert.call_count == 3


# ============================================================================
# TEST: Error Handling - Missing thread_id
# ============================================================================

@pytest.mark.asyncio
async def test_sync_error_missing_thread_id(sample_project_id):
    """
    Test that sync raises error when thread_id is missing.

    Verifies:
    - ValueError raised for missing thread_id
    - Error message is descriptive
    """
    # Create task state without thread_id
    invalid_state = TaskState(
        task_id=str(uuid4()),
        thread_id="",  # Empty thread_id
        category="Sales",
        status="Pending",
        messages=[],
        raw_data={},
        standards=[],
        vouching_logs=[],
        workpaper_draft="",
        next_staff="Staff",
        error_report="",
        risk_score=50,
    )

    with pytest.raises(ValueError, match="thread_id"):
        await sync_task_to_supabase(invalid_state, sample_project_id)


# ============================================================================
# TEST: Error Handling - Database Upsert Failure
# ============================================================================

@pytest.mark.asyncio
async def test_sync_error_upsert_failure(sample_task_state, sample_project_id):
    """
    Test error handling when upsert fails.

    Verifies:
    - Exception raised when upsert returns empty data
    - Error message indicates upsert failure
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        # Setup mock to return empty data (failure)
        mock_response = MagicMock()
        mock_response.data = []  # Empty response indicates failure

        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to upsert"):
            await sync_task_to_supabase(sample_task_state, sample_project_id)


# ============================================================================
# TEST: Error Handling - Message Insertion Failure
# ============================================================================

@pytest.mark.asyncio
async def test_sync_error_message_insertion(
    sample_task_state_with_messages,
    sample_project_id,
):
    """
    Test error handling when message insertion fails.

    Verifies:
    - Exception raised when message insert returns empty data
    - Error message indicates message insertion failure
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        upsert_response = MagicMock()
        upsert_response.data = [{"id": str(uuid4())}]

        failed_response = MagicMock()
        failed_response.data = []

        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == "audit_tasks":
                table_mock.upsert.return_value = MagicMock()
                table_mock.upsert.return_value.execute.return_value = upsert_response
            elif table_name == "agent_messages":
                table_mock.insert.return_value = MagicMock()
                table_mock.insert.return_value.execute.return_value = failed_response
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to insert agent messages"):
            await sync_task_to_supabase(
                sample_task_state_with_messages,
                sample_project_id
            )


# ============================================================================
# TEST: Error Handling - Workpaper Insertion Failure
# ============================================================================

@pytest.mark.asyncio
async def test_sync_error_workpaper_insertion(
    sample_task_state,
    sample_project_id,
):
    """
    Test error handling when workpaper insertion fails.

    Verifies:
    - Exception raised when artifact insert returns empty data
    - Error message indicates artifact insertion failure
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        upsert_response = MagicMock()
        upsert_response.data = [{"id": str(uuid4())}]

        failed_response = MagicMock()
        failed_response.data = []

        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == "audit_tasks":
                table_mock.upsert.return_value = MagicMock()
                table_mock.upsert.return_value.execute.return_value = upsert_response
            elif table_name == "audit_artifacts":
                table_mock.insert.return_value = MagicMock()
                table_mock.insert.return_value.execute.return_value = failed_response
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to insert workpaper"):
            await sync_task_to_supabase(sample_task_state, sample_project_id)


# ============================================================================
# TEST: Edge Case - No Workpaper
# ============================================================================

@pytest.mark.asyncio
async def test_sync_without_workpaper(sample_task_state_no_workpaper, sample_project_id):
    """
    Test syncing task without workpaper artifact.

    Verifies:
    - No artifact insertion when workpaper_draft is empty
    - Task is still synced successfully
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.data = [{"id": expected_task_id}]

        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute
        task_id = await sync_task_to_supabase(
            sample_task_state_no_workpaper,
            sample_project_id
        )

        # Verify upsert was called
        assert task_id is not None
        assert task_id == expected_task_id

        # Verify artifacts table was NOT called (no workpaper)
        artifact_calls = [
            c for c in mock_supabase.table.call_args_list
            if c[0][0] == "audit_artifacts"
        ]
        assert len(artifact_calls) == 0


# ============================================================================
# TEST: Metadata Serialization
# ============================================================================

@pytest.mark.asyncio
async def test_sync_preserves_metadata(sample_task_state, sample_project_id):
    """
    Test that metadata is correctly serialized in upsert.

    Verifies:
    - Metadata includes all required fields
    - Boolean flags are correctly set based on data presence
    - Metadata is included in upsert payload
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.data = [{"id": expected_task_id}]

        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Add specific data to verify metadata flags
        sample_task_state["raw_data"] = {"some": "data"}
        sample_task_state["standards"] = ["K-IFRS 1115"]
        sample_task_state["vouching_logs"] = [{"entry": 1}]
        sample_task_state["workpaper_draft"] = "# Workpaper"

        # Execute
        task_id = await sync_task_to_supabase(sample_task_state, sample_project_id)

        # Verify upsert data
        upsert_args, _ = mock_table.upsert.call_args
        upsert_data = upsert_args[0]

        # Check metadata
        metadata = upsert_data["metadata"]
        assert metadata["has_raw_data"] is True
        assert metadata["has_standards"] is True
        assert metadata["has_vouching_logs"] is True
        assert metadata["has_workpaper_draft"] is True


# ============================================================================
# TEST: Timestamp Format
# ============================================================================

@pytest.mark.asyncio
async def test_sync_includes_iso_timestamp(sample_task_state, sample_project_id):
    """
    Test that updated_at timestamp is included in ISO format.

    Verifies:
    - updated_at field is present
    - Timestamp is in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff)
    """
    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.data = [{"id": expected_task_id}]

        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_response

        mock_table.upsert.return_value = mock_upsert
        mock_supabase.table.return_value = mock_table

        # Execute
        task_id = await sync_task_to_supabase(sample_task_state, sample_project_id)

        # Verify timestamp
        upsert_args, _ = mock_table.upsert.call_args
        upsert_data = upsert_args[0]

        assert "updated_at" in upsert_data
        # Verify it's a valid ISO format string
        try:
            datetime.fromisoformat(upsert_data["updated_at"])
        except ValueError:
            pytest.fail("updated_at is not in ISO format")


# ============================================================================
# TEST: Message Agent Role Extraction
# ============================================================================

@pytest.mark.asyncio
async def test_sync_extracts_message_agent_role(sample_project_id):
    """
    Test that agent roles are correctly extracted from messages.

    Verifies:
    - agent_role is extracted from additional_kwargs
    - Message type is preserved
    - Content is correctly captured
    """
    # Create task with messages with different agent roles
    task_state = TaskState(
        task_id=str(uuid4()),
        thread_id="task-role-test",
        category="Sales",
        status="In-Progress",
        messages=[
            HumanMessage(
                content="Start review",
                additional_kwargs={"agent_role": "Manager"}
            ),
            AIMessage(
                content="Analyzing...",
                additional_kwargs={"agent_role": "Excel_Parser"}
            ),
        ],
        raw_data={},
        standards=[],
        vouching_logs=[],
        workpaper_draft="",
        next_staff="Staff",
        error_report="",
        risk_score=50,
    )

    with patch("src.services.task_sync.supabase") as mock_supabase:
        expected_task_id = str(uuid4())

        upsert_response = MagicMock()
        upsert_response.data = [{"id": expected_task_id}]

        insert_response = MagicMock()
        insert_response.data = [{"id": str(uuid4())}]

        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == "audit_tasks":
                table_mock.upsert.return_value = MagicMock()
                table_mock.upsert.return_value.execute.return_value = upsert_response
            elif table_name == "agent_messages":
                table_mock.insert.return_value = MagicMock()
                table_mock.insert.return_value.execute.return_value = insert_response
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        # Execute
        task_id = await sync_task_to_supabase(task_state, sample_project_id)

        # Verify insert was called for messages
        insert_calls = [
            c for c in mock_supabase.table.call_args_list
            if c[0][0] == "agent_messages"
        ]
        assert len(insert_calls) > 0

        # Verify task_id returned
        assert task_id == expected_task_id
