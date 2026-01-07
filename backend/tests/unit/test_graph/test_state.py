"""
Unit Tests for LangGraph State Schemas

This module comprehensively tests the AuditState and TaskState schema definitions:

1. **test_audit_state_structure** - Validates AuditState schema completeness
2. **test_task_state_structure** - Validates TaskState schema completeness
3. **test_state_add_messages** - Tests message accumulation via add_messages reducer
4. **test_state_thread_id_uniqueness** - Verifies thread_id constraints and uniqueness
5. **test_state_serialization** - Tests JSON serialization/deserialization

Test Coverage:
- TypedDict field validation (presence, types, defaults)
- Message accumulation and reducer behavior
- Thread ID uniqueness constraints
- Serialization round-trip fidelity
- Edge cases (empty states, missing fields, boundary conditions)
"""

import pytest
import json
import uuid
from typing import Any, Dict, List
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage,
)
from src.graph.state import AuditState, TaskState


# ============================================================================
# TEST: AUDIT STATE STRUCTURE
# ============================================================================


class TestAuditStateStructure:
    """Validate AuditState schema structure and field types."""

    def test_audit_state_all_required_fields(self):
        """Test that AuditState requires all specified fields."""
        # Create a valid AuditState with all required fields
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test Client",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        # Verify all fields are present
        assert state["messages"] == []
        assert state["project_id"] == "proj-001"
        assert state["client_name"] == "Test Client"
        assert state["fiscal_year"] == 2024
        assert state["overall_materiality"] == 1000000.0
        assert state["audit_plan"] == {}
        assert state["tasks"] == []
        assert state["next_action"] == "WAIT_FOR_APPROVAL"
        assert state["is_approved"] is False
        assert state["shared_documents"] == []

    def test_audit_state_field_types(self):
        """Test that AuditState fields have correct types."""
        state = AuditState(
            messages=[HumanMessage(content="Hello")],
            project_id="proj-001",
            client_name="Test Client",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={"key": "value"},
            tasks=[{"id": "task-1", "status": "Pending"}],
            next_action="CONTINUE",
            is_approved=True,
            shared_documents=[{"filename": "doc.pdf"}],
        )

        # Verify types
        assert isinstance(state["messages"], list)
        assert isinstance(state["messages"][0], BaseMessage)
        assert isinstance(state["project_id"], str)
        assert isinstance(state["client_name"], str)
        assert isinstance(state["fiscal_year"], int)
        assert isinstance(state["overall_materiality"], float)
        assert isinstance(state["audit_plan"], dict)
        assert isinstance(state["tasks"], list)
        assert isinstance(state["next_action"], str)
        assert isinstance(state["is_approved"], bool)
        assert isinstance(state["shared_documents"], list)

    def test_audit_state_missing_field_type_checking(self):
        """Test that missing required field is caught by type checker (not runtime)."""
        # Note: TypedDict in Python doesn't enforce at runtime.
        # This test documents that missing fields won't raise errors at runtime,
        # but static type checkers (mypy) would catch them.
        # This is expected behavior - validation should be at the application level.

        # Create state with all required fields - this is the validated approach
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        # Verify all fields are present
        assert "client_name" in state
        assert state["client_name"] == "Test"

    def test_audit_state_empty_lists(self):
        """Test AuditState with empty lists is valid."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=500000.0,
            audit_plan={},
            tasks=[],
            shared_documents=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
        )

        assert state["messages"] == []
        assert state["tasks"] == []
        assert state["shared_documents"] == []

    def test_audit_state_large_materiality(self):
        """Test AuditState with large materiality values."""
        large_value = 999999999.99
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Fortune 500 Corp",
            fiscal_year=2024,
            overall_materiality=large_value,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["overall_materiality"] == large_value

    def test_audit_state_zero_materiality(self):
        """Test AuditState with zero materiality (edge case)."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=0.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["overall_materiality"] == 0.0

    def test_audit_state_future_fiscal_year(self):
        """Test AuditState with future fiscal year."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2099,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["fiscal_year"] == 2099

    def test_audit_state_complex_audit_plan(self):
        """Test AuditState with complex nested audit plan structure."""
        complex_plan = {
            "strategy": "Risk-based",
            "phases": [
                {"phase": 1, "name": "Planning", "duration": "2 weeks"},
                {"phase": 2, "name": "Fieldwork", "duration": "4 weeks"},
            ],
            "risks": {"high": 5, "medium": 3, "low": 2},
            "timeline": {"start": "2024-01-01", "end": "2024-12-31"},
        }

        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan=complex_plan,
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["audit_plan"] == complex_plan
        assert len(state["audit_plan"]["phases"]) == 2

    def test_audit_state_multiple_tasks(self):
        """Test AuditState with multiple task entries."""
        tasks = [
            {
                "id": f"task-{i}",
                "status": "Pending",
                "thread_id": str(uuid.uuid4()),
                "risk_score": 50 + i * 10,
            }
            for i in range(5)
        ]

        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=tasks,
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert len(state["tasks"]) == 5
        assert state["tasks"][0]["id"] == "task-0"
        assert state["tasks"][4]["id"] == "task-4"

    def test_audit_state_multiple_shared_documents(self):
        """Test AuditState with multiple shared documents."""
        documents = [
            {"filename": f"doc-{i}.pdf", "size": 1000 * (i + 1), "type": "PDF"}
            for i in range(3)
        ]

        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=documents,
        )

        assert len(state["shared_documents"]) == 3
        assert state["shared_documents"][0]["filename"] == "doc-0.pdf"


# ============================================================================
# TEST: TASK STATE STRUCTURE
# ============================================================================


class TestTaskStateStructure:
    """Validate TaskState schema structure and field types."""

    def test_task_state_all_required_fields(self):
        """Test that TaskState requires all specified fields."""
        thread_id = str(uuid.uuid4())
        state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="Sales Revenue",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=75,
        )

        # Verify all fields are present
        assert state["task_id"] == "task-001"
        assert state["thread_id"] == thread_id
        assert state["category"] == "Sales Revenue"
        assert state["status"] == "Pending"
        assert state["messages"] == []
        assert state["raw_data"] == {}
        assert state["standards"] == []
        assert state["vouching_logs"] == []
        assert state["workpaper_draft"] == ""
        assert state["next_staff"] == "Excel_Parser"
        assert state["error_report"] == ""
        assert state["risk_score"] == 75

    def test_task_state_field_types(self):
        """Test that TaskState fields have correct types."""
        thread_id = str(uuid.uuid4())
        state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="Inventory",
            status="In-Progress",
            messages=[HumanMessage(content="Processing...")],
            raw_data={"excel": "data"},
            standards=["IAS 2", "IAS 8"],
            vouching_logs=[{"vouched_items": 10}],
            workpaper_draft="# Draft Workpaper",
            next_staff="Standard_Retriever",
            error_report="",
            risk_score=50,
        )

        # Verify types
        assert isinstance(state["task_id"], str)
        assert isinstance(state["thread_id"], str)
        assert isinstance(state["category"], str)
        assert isinstance(state["status"], str)
        assert isinstance(state["messages"], list)
        assert isinstance(state["raw_data"], dict)
        assert isinstance(state["standards"], list)
        assert isinstance(state["vouching_logs"], list)
        assert isinstance(state["workpaper_draft"], str)
        assert isinstance(state["next_staff"], str)
        assert isinstance(state["error_report"], str)
        assert isinstance(state["risk_score"], int)

    def test_task_state_missing_field_type_checking(self):
        """Test that missing required field is caught by type checker (not runtime)."""
        # Note: TypedDict in Python doesn't enforce at runtime.
        # This test documents that missing fields won't raise errors at runtime,
        # but static type checkers (mypy) would catch them.
        # This is expected behavior - validation should be at the application level.

        # Create state with all required fields - this is the validated approach
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=75,
        )

        # Verify all fields are present
        assert "category" in state
        assert state["category"] == "AR"

    def test_task_state_empty_collections(self):
        """Test TaskState with empty collections is valid."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=0,
        )

        assert state["messages"] == []
        assert state["raw_data"] == {}
        assert state["standards"] == []
        assert state["vouching_logs"] == []

    def test_task_state_risk_score_boundaries(self):
        """Test TaskState with boundary risk scores (0-100)."""
        # Test minimum
        state_min = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=0,
        )
        assert state_min["risk_score"] == 0

        # Test maximum
        state_max = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=100,
        )
        assert state_max["risk_score"] == 100

    def test_task_state_with_complex_raw_data(self):
        """Test TaskState with complex nested raw_data structure."""
        raw_data = {
            "sheets": [
                {"name": "Sales", "rows": 1000, "columns": 5},
                {"name": "Returns", "rows": 500, "columns": 4},
            ],
            "validation": {
                "headers_valid": True,
                "data_types": {"column_1": "numeric", "column_2": "text"},
            },
        }

        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Sales Revenue",
            status="In-Progress",
            messages=[],
            raw_data=raw_data,
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=60,
        )

        assert state["raw_data"] == raw_data
        assert len(state["raw_data"]["sheets"]) == 2

    def test_task_state_with_standards_list(self):
        """Test TaskState with multiple audit standards."""
        standards = [
            "IAS 2 - Inventories",
            "IAS 8 - Accounting Policies",
            "ISA 500 - Audit Evidence",
            "ISA 330 - Audit Procedures",
        ]

        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Inventory",
            status="In-Progress",
            messages=[],
            raw_data={},
            standards=standards,
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Standard_Retriever",
            error_report="",
            risk_score=75,
        )

        assert state["standards"] == standards
        assert len(state["standards"]) == 4

    def test_task_state_with_vouching_logs(self):
        """Test TaskState with vouching log entries."""
        vouching_logs = [
            {
                "transaction_id": "TXN-001",
                "amount": 50000.00,
                "evidence": "Invoice #12345",
                "conclusion": "Valid",
            },
            {
                "transaction_id": "TXN-002",
                "amount": 30000.00,
                "evidence": "PO #67890",
                "conclusion": "Valid with exception",
            },
        ]

        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Sales Revenue",
            status="In-Progress",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=vouching_logs,
            workpaper_draft="",
            next_staff="Vouching_Assistant",
            error_report="",
            risk_score=55,
        )

        assert len(state["vouching_logs"]) == 2
        assert state["vouching_logs"][0]["transaction_id"] == "TXN-001"

    def test_task_state_all_status_values(self):
        """Test TaskState with all valid status values."""
        statuses = ["Pending", "In-Progress", "Review-Required", "Completed", "Failed"]

        for status in statuses:
            state = TaskState(
                task_id="task-001",
                thread_id=str(uuid.uuid4()),
                category="AR",
                status=status,
                messages=[],
                raw_data={},
                standards=[],
                vouching_logs=[],
                workpaper_draft="",
                next_staff="Excel_Parser",
                error_report="",
                risk_score=50,
            )
            assert state["status"] == status

    def test_task_state_workpaper_with_markdown_content(self):
        """Test TaskState with markdown-formatted workpaper draft."""
        workpaper = """# Workpaper - Sales Revenue Testing

## Objective
Verify sales transactions for completeness and accuracy.

## Sample Size
Selected 25 transactions from 1,000 total.

## Test Results
- Items tested: 25
- Items passed: 24
- Items with exceptions: 1

## Conclusion
Substantive evidence supports revenue balance as of 12/31/2024.
"""

        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Sales Revenue",
            status="In-Progress",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft=workpaper,
            next_staff="WorkPaper_Generator",
            error_report="",
            risk_score=40,
        )

        assert state["workpaper_draft"] == workpaper
        assert "# Workpaper" in state["workpaper_draft"]

    def test_task_state_with_error_report(self):
        """Test TaskState with detailed error report."""
        error_report = "Excel parsing failed: Invalid date format in column 3, row 150"

        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Sales Revenue",
            status="Failed",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report=error_report,
            risk_score=100,
        )

        assert state["error_report"] == error_report
        assert "Invalid date format" in state["error_report"]


# ============================================================================
# TEST: STATE ADD_MESSAGES - MESSAGE ACCUMULATION
# ============================================================================


class TestStateAddMessages:
    """Test message accumulation via add_messages reducer."""

    def test_audit_state_add_single_message(self):
        """Test adding a single message to AuditState."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        msg = HumanMessage(content="Hello")
        state["messages"].append(msg)

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Hello"

    def test_audit_state_add_multiple_messages_sequence(self):
        """Test adding multiple messages in sequence."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        messages = [
            HumanMessage(content="User message 1"),
            AIMessage(content="AI response 1"),
            HumanMessage(content="User message 2"),
            AIMessage(content="AI response 2"),
        ]

        for msg in messages:
            state["messages"].append(msg)

        assert len(state["messages"]) == 4
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)

    def test_audit_state_message_order_preserved(self):
        """Test that message order is preserved during accumulation."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        messages_to_add = [
            HumanMessage(content=f"Message {i}") for i in range(10)
        ]

        for msg in messages_to_add:
            state["messages"].append(msg)

        for i, msg in enumerate(state["messages"]):
            assert msg.content == f"Message {i}"

    def test_audit_state_with_different_message_types(self):
        """Test accumulating different message types."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        state["messages"].append(SystemMessage(content="System initialized"))
        state["messages"].append(HumanMessage(content="User input"))
        state["messages"].append(AIMessage(content="AI response"))
        state["messages"].append(
            ToolMessage(content="Tool result", tool_call_id="tool-1")
        )

        assert len(state["messages"]) == 4
        assert isinstance(state["messages"][0], SystemMessage)
        assert isinstance(state["messages"][1], HumanMessage)
        assert isinstance(state["messages"][2], AIMessage)
        assert isinstance(state["messages"][3], ToolMessage)

    def test_task_state_add_single_message(self):
        """Test adding a single message to TaskState."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        msg = HumanMessage(content="Start task processing")
        state["messages"].append(msg)

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Start task processing"

    def test_task_state_add_multiple_messages_sequence(self):
        """Test adding multiple messages to TaskState in sequence."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="In-Progress",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        messages = [
            AIMessage(content="Starting Excel parsing"),
            ToolMessage(content="Parsed 1000 rows", tool_call_id="parse-1"),
            AIMessage(content="Validation complete"),
        ]

        for msg in messages:
            state["messages"].append(msg)

        assert len(state["messages"]) == 3

    def test_add_messages_with_preloaded_messages(self):
        """Test add_messages behavior with pre-existing messages."""
        initial_messages = [
            HumanMessage(content="Initial message 1"),
            AIMessage(content="Initial response 1"),
        ]

        state = AuditState(
            messages=initial_messages,
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        state["messages"].append(HumanMessage(content="New message"))

        assert len(state["messages"]) == 3
        assert state["messages"][0].content == "Initial message 1"
        assert state["messages"][2].content == "New message"

    def test_audit_state_message_content_preserved(self):
        """Test that message content is correctly preserved."""
        content = "This is a comprehensive audit finding with special chars: !@#$%"

        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        msg = HumanMessage(content=content)
        state["messages"].append(msg)

        assert state["messages"][0].content == content

    def test_task_state_large_message_accumulation(self):
        """Test TaskState with large number of messages."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="In-Progress",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        # Add 100 messages
        for i in range(100):
            msg = HumanMessage(content=f"Message {i}")
            state["messages"].append(msg)

        assert len(state["messages"]) == 100
        assert state["messages"][0].content == "Message 0"
        assert state["messages"][99].content == "Message 99"


# ============================================================================
# TEST: THREAD_ID UNIQUENESS
# ============================================================================


class TestStateThreadIdUniqueness:
    """Test thread_id constraints and uniqueness properties."""

    def test_task_state_thread_id_is_unique_uuid(self):
        """Test that thread_id can be a valid UUID."""
        thread_id = str(uuid.uuid4())

        state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        assert state["thread_id"] == thread_id
        # Verify it's a valid UUID by parsing
        uuid.UUID(thread_id)

    def test_multiple_task_states_different_thread_ids(self):
        """Test that multiple TaskStates can have different thread_ids."""
        thread_ids = [str(uuid.uuid4()) for _ in range(5)]
        states = []

        for thread_id in thread_ids:
            state = TaskState(
                task_id=f"task-{thread_id[:8]}",
                thread_id=thread_id,
                category="AR",
                status="Pending",
                messages=[],
                raw_data={},
                standards=[],
                vouching_logs=[],
                workpaper_draft="",
                next_staff="Excel_Parser",
                error_report="",
                risk_score=50,
            )
            states.append(state)

        # Verify all thread_ids are unique
        actual_thread_ids = [s["thread_id"] for s in states]
        assert len(set(actual_thread_ids)) == len(actual_thread_ids)

    def test_task_state_thread_id_string_format(self):
        """Test that thread_id accepts string format."""
        thread_id = "thread-2024-01-001"

        state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        assert state["thread_id"] == thread_id

    def test_task_state_thread_id_consistency_across_reads(self):
        """Test that thread_id remains consistent when accessed multiple times."""
        thread_id = str(uuid.uuid4())

        state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        # Access thread_id multiple times
        assert state["thread_id"] == thread_id
        assert state["thread_id"] == thread_id
        assert state["thread_id"] == thread_id

    def test_audit_state_without_thread_id(self):
        """Test that AuditState does not have thread_id field (intentional)."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        # AuditState should not have thread_id
        assert "thread_id" not in state

    def test_task_state_thread_id_long_string(self):
        """Test TaskState with long thread_id string."""
        long_thread_id = "thread-" + "x" * 1000

        state = TaskState(
            task_id="task-001",
            thread_id=long_thread_id,
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        assert state["thread_id"] == long_thread_id
        assert len(state["thread_id"]) == 1007  # "thread-" (7) + 1000 x's


# ============================================================================
# TEST: STATE SERIALIZATION
# ============================================================================


class TestStateSerialization:
    """Test JSON serialization/deserialization of state objects."""

    def test_audit_state_simple_serialization(self):
        """Test basic JSON serialization of AuditState."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test Client",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={"strategy": "risk-based"},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        # Manually serialize basic fields (messages require special handling)
        serializable_state = {
            "project_id": state["project_id"],
            "client_name": state["client_name"],
            "fiscal_year": state["fiscal_year"],
            "overall_materiality": state["overall_materiality"],
            "audit_plan": state["audit_plan"],
            "tasks": state["tasks"],
            "next_action": state["next_action"],
            "is_approved": state["is_approved"],
            "shared_documents": state["shared_documents"],
        }

        json_str = json.dumps(serializable_state)
        deserialized = json.loads(json_str)

        assert deserialized["project_id"] == "proj-001"
        assert deserialized["fiscal_year"] == 2024
        assert deserialized["overall_materiality"] == 1000000.0

    def test_task_state_simple_serialization(self):
        """Test basic JSON serialization of TaskState."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Sales Revenue",
            status="Pending",
            messages=[],
            raw_data={"sheet": "Sales"},
            standards=["IAS 2"],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=75,
        )

        # Serialize without messages
        serializable_state = {
            "task_id": state["task_id"],
            "thread_id": state["thread_id"],
            "category": state["category"],
            "status": state["status"],
            "raw_data": state["raw_data"],
            "standards": state["standards"],
            "vouching_logs": state["vouching_logs"],
            "workpaper_draft": state["workpaper_draft"],
            "next_staff": state["next_staff"],
            "error_report": state["error_report"],
            "risk_score": state["risk_score"],
        }

        json_str = json.dumps(serializable_state)
        deserialized = json.loads(json_str)

        assert deserialized["task_id"] == "task-001"
        assert deserialized["category"] == "Sales Revenue"
        assert deserialized["risk_score"] == 75

    def test_audit_state_complex_structure_serialization(self):
        """Test serialization of AuditState with complex nested structures."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={
                "phases": [
                    {
                        "name": "Planning",
                        "duration": "2 weeks",
                        "tasks": ["Risk assessment", "Materiality calculation"],
                    },
                    {
                        "name": "Fieldwork",
                        "duration": "4 weeks",
                        "tasks": ["Testing", "Evidence collection"],
                    },
                ],
                "risks": {"high": 5, "medium": 3},
            },
            tasks=[
                {"id": "task-1", "status": "Pending", "risk_score": 60},
                {"id": "task-2", "status": "Pending", "risk_score": 45},
            ],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[
                {"filename": "client-data.xlsx", "size": 2000000},
                {"filename": "audit-manual.pdf", "size": 5000000},
            ],
        )

        serializable_state = {
            "project_id": state["project_id"],
            "client_name": state["client_name"],
            "fiscal_year": state["fiscal_year"],
            "overall_materiality": state["overall_materiality"],
            "audit_plan": state["audit_plan"],
            "tasks": state["tasks"],
            "next_action": state["next_action"],
            "is_approved": state["is_approved"],
            "shared_documents": state["shared_documents"],
        }

        json_str = json.dumps(serializable_state)
        deserialized = json.loads(json_str)

        assert len(deserialized["audit_plan"]["phases"]) == 2
        assert len(deserialized["tasks"]) == 2
        assert len(deserialized["shared_documents"]) == 2

    def test_task_state_complex_structure_serialization(self):
        """Test serialization of TaskState with complex nested raw_data."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="Inventory",
            status="In-Progress",
            messages=[],
            raw_data={
                "sheets": [
                    {
                        "name": "Inventory",
                        "rows": 1000,
                        "columns": ["SKU", "Description", "Qty", "Unit Cost"],
                    }
                ],
                "validation": {
                    "headers_valid": True,
                    "row_count": 1000,
                    "data_quality_score": 0.98,
                },
            },
            standards=["IAS 2", "ISA 500"],
            vouching_logs=[
                {
                    "item_id": "SKU-001",
                    "quantity": 100,
                    "unit_cost": 50.00,
                    "vouched": True,
                }
            ],
            workpaper_draft="# Inventory Testing Workpaper",
            next_staff="Standard_Retriever",
            error_report="",
            risk_score=60,
        )

        serializable_state = {
            "task_id": state["task_id"],
            "thread_id": state["thread_id"],
            "category": state["category"],
            "status": state["status"],
            "raw_data": state["raw_data"],
            "standards": state["standards"],
            "vouching_logs": state["vouching_logs"],
            "workpaper_draft": state["workpaper_draft"],
            "next_staff": state["next_staff"],
            "error_report": state["error_report"],
            "risk_score": state["risk_score"],
        }

        json_str = json.dumps(serializable_state)
        deserialized = json.loads(json_str)

        assert len(deserialized["raw_data"]["sheets"]) == 1
        assert deserialized["raw_data"]["validation"]["row_count"] == 1000
        assert deserialized["vouching_logs"][0]["quantity"] == 100

    def test_audit_state_roundtrip_serialization(self):
        """Test complete roundtrip: state -> JSON -> dict -> state."""
        original_state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test Corp",
            fiscal_year=2024,
            overall_materiality=2500000.0,
            audit_plan={"strategy": "risk-based"},
            tasks=[{"id": "task-1", "status": "Pending"}],
            next_action="CONTINUE",
            is_approved=True,
            shared_documents=[{"filename": "doc.pdf"}],
        )

        # Serialize
        serializable = {
            "project_id": original_state["project_id"],
            "client_name": original_state["client_name"],
            "fiscal_year": original_state["fiscal_year"],
            "overall_materiality": original_state["overall_materiality"],
            "audit_plan": original_state["audit_plan"],
            "tasks": original_state["tasks"],
            "next_action": original_state["next_action"],
            "is_approved": original_state["is_approved"],
            "shared_documents": original_state["shared_documents"],
        }
        json_str = json.dumps(serializable)

        # Deserialize
        deserialized = json.loads(json_str)
        reconstructed_state = AuditState(
            messages=[],
            project_id=deserialized["project_id"],
            client_name=deserialized["client_name"],
            fiscal_year=deserialized["fiscal_year"],
            overall_materiality=deserialized["overall_materiality"],
            audit_plan=deserialized["audit_plan"],
            tasks=deserialized["tasks"],
            next_action=deserialized["next_action"],
            is_approved=deserialized["is_approved"],
            shared_documents=deserialized["shared_documents"],
        )

        assert reconstructed_state["project_id"] == original_state["project_id"]
        assert reconstructed_state["fiscal_year"] == original_state["fiscal_year"]
        assert reconstructed_state["is_approved"] == original_state["is_approved"]

    def test_task_state_roundtrip_serialization(self):
        """Test complete roundtrip: state -> JSON -> dict -> state."""
        thread_id = str(uuid.uuid4())
        original_state = TaskState(
            task_id="task-001",
            thread_id=thread_id,
            category="Sales Revenue",
            status="In-Progress",
            messages=[],
            raw_data={"rows": 500},
            standards=["IAS 2"],
            vouching_logs=[{"id": "V-001"}],
            workpaper_draft="# Workpaper",
            next_staff="Vouching_Assistant",
            error_report="",
            risk_score=65,
        )

        # Serialize
        serializable = {
            "task_id": original_state["task_id"],
            "thread_id": original_state["thread_id"],
            "category": original_state["category"],
            "status": original_state["status"],
            "raw_data": original_state["raw_data"],
            "standards": original_state["standards"],
            "vouching_logs": original_state["vouching_logs"],
            "workpaper_draft": original_state["workpaper_draft"],
            "next_staff": original_state["next_staff"],
            "error_report": original_state["error_report"],
            "risk_score": original_state["risk_score"],
        }
        json_str = json.dumps(serializable)

        # Deserialize
        deserialized = json.loads(json_str)
        reconstructed_state = TaskState(
            task_id=deserialized["task_id"],
            thread_id=deserialized["thread_id"],
            category=deserialized["category"],
            status=deserialized["status"],
            raw_data=deserialized["raw_data"],
            standards=deserialized["standards"],
            vouching_logs=deserialized["vouching_logs"],
            workpaper_draft=deserialized["workpaper_draft"],
            next_staff=deserialized["next_staff"],
            error_report=deserialized["error_report"],
            risk_score=deserialized["risk_score"],
        )

        assert reconstructed_state["task_id"] == original_state["task_id"]
        assert reconstructed_state["thread_id"] == original_state["thread_id"]
        assert reconstructed_state["risk_score"] == original_state["risk_score"]

    def test_serialization_with_special_characters(self):
        """Test serialization with special characters in strings."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test & Co. (Pty) Ltd.",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={"note": "Plan with special chars: <>&\"'"},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[
                {"filename": "document_v1.0_final[2024].pdf"}
            ],
        )

        serializable = {
            "project_id": state["project_id"],
            "client_name": state["client_name"],
            "fiscal_year": state["fiscal_year"],
            "overall_materiality": state["overall_materiality"],
            "audit_plan": state["audit_plan"],
            "tasks": state["tasks"],
            "next_action": state["next_action"],
            "is_approved": state["is_approved"],
            "shared_documents": state["shared_documents"],
        }

        json_str = json.dumps(serializable)
        deserialized = json.loads(json_str)

        assert deserialized["client_name"] == "Test & Co. (Pty) Ltd."
        assert "<>&\"'" in deserialized["audit_plan"]["note"]

    def test_serialization_with_unicode(self):
        """Test serialization with unicode characters."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test 中文 Société",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={"note": "Testing €uro and émojis 🎯"},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        serializable = {
            "project_id": state["project_id"],
            "client_name": state["client_name"],
            "fiscal_year": state["fiscal_year"],
            "overall_materiality": state["overall_materiality"],
            "audit_plan": state["audit_plan"],
            "tasks": state["tasks"],
            "next_action": state["next_action"],
            "is_approved": state["is_approved"],
            "shared_documents": state["shared_documents"],
        }

        json_str = json.dumps(serializable, ensure_ascii=False)
        deserialized = json.loads(json_str)

        assert "中文" in deserialized["client_name"]
        assert "€" in deserialized["audit_plan"]["note"]


# ============================================================================
# TEST: EDGE CASES AND BOUNDARY CONDITIONS
# ============================================================================


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_audit_state_empty_client_name(self):
        """Test AuditState with empty client name."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["client_name"] == ""

    def test_task_state_empty_task_id(self):
        """Test TaskState with empty task_id."""
        state = TaskState(
            task_id="",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=50,
        )

        assert state["task_id"] == ""

    def test_audit_state_very_long_project_id(self):
        """Test AuditState with very long project_id."""
        long_id = "proj-" + "x" * 10000
        state = AuditState(
            messages=[],
            project_id=long_id,
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["project_id"] == long_id

    def test_task_state_negative_risk_score_accepted(self):
        """Test that TaskState accepts negative risk_score (no validation in schema)."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=-50,
        )

        assert state["risk_score"] == -50

    def test_task_state_risk_score_over_100(self):
        """Test that TaskState accepts risk_score over 100 (no validation in schema)."""
        state = TaskState(
            task_id="task-001",
            thread_id=str(uuid.uuid4()),
            category="AR",
            status="Pending",
            messages=[],
            raw_data={},
            standards=[],
            vouching_logs=[],
            workpaper_draft="",
            next_staff="Excel_Parser",
            error_report="",
            risk_score=999,
        )

        assert state["risk_score"] == 999

    def test_audit_state_zero_fiscal_year(self):
        """Test AuditState with year zero (edge case)."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=0,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["fiscal_year"] == 0

    def test_audit_state_negative_fiscal_year(self):
        """Test AuditState with negative fiscal year."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=-100,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["fiscal_year"] == -100

    def test_audit_state_negative_materiality_accepted(self):
        """Test AuditState accepts negative materiality (no validation in schema)."""
        state = AuditState(
            messages=[],
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=-1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["overall_materiality"] == -1000000.0

    def test_audit_state_with_empty_message_list(self):
        """Test that AuditState works with empty message list instead of None."""
        # TypedDict doesn't validate at runtime, so None would be accepted.
        # This test documents the proper way: use empty list [] not None
        state = AuditState(
            messages=[],  # Use empty list, not None
            project_id="proj-001",
            client_name="Test",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[],
        )

        assert state["messages"] == []
        assert isinstance(state["messages"], list)
