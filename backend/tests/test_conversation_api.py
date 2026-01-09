"""
Tests for Conversation API Routes

This module provides comprehensive tests for the conversation API endpoints:
- GET /api/conversations: List conversations with filters
- GET /api/conversations/stats: Get conversation statistics
- GET /api/conversations/{id}: Get single conversation
- POST /api/conversations: Create conversation entry
- POST /api/conversations/bulk: Create multiple entries
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from uuid import uuid4
from datetime import datetime, timedelta

from src.api.routes.conversations import router, conversations_db


# ============================================================================
# Test Setup
# ============================================================================

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    """Clear in-memory DB before and after each test."""
    conversations_db.clear()
    yield
    conversations_db.clear()


def create_test_conversation(
    project_id: str = None,
    hierarchy_id: str = None,
    task_id: str = None,
    from_agent: str = "TestAgent",
    to_agent: str = "Manager",
    message_type: str = "response",
    content: str = "Test message",
    metadata: dict = None
) -> dict:
    """Helper to create a test conversation via API."""
    payload = {
        "project_id": project_id or str(uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "content": content
    }
    if hierarchy_id:
        payload["hierarchy_id"] = hierarchy_id
    if task_id:
        payload["task_id"] = task_id
    if metadata:
        payload["metadata"] = metadata
    return payload


# ============================================================================
# Test: GET /api/conversations
# ============================================================================

class TestListConversations:
    """Tests for GET /api/conversations."""

    def test_empty_list(self):
        """Test listing when no conversations exist."""
        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["has_more"] is False

    def test_list_with_items(self):
        """Test listing with multiple conversations."""
        project_id = str(uuid4())
        for i in range(5):
            client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    content=f"Message {i}"
                )
            )

        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_filter_by_project(self):
        """Test filtering conversations by project_id."""
        project1 = str(uuid4())
        project2 = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project1,
                from_agent="Agent1",
                content="Project 1 message"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project2,
                from_agent="Agent2",
                content="Project 2 message"
            )
        )

        response = client.get(f"/api/conversations?project_id={project1}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["from_agent"] == "Agent1"

    def test_filter_by_hierarchy(self):
        """Test filtering conversations by hierarchy_id."""
        project_id = str(uuid4())
        hierarchy_id = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                hierarchy_id=hierarchy_id,
                content="Hierarchy message"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                content="General message"
            )
        )

        response = client.get(f"/api/conversations?hierarchy_id={hierarchy_id}")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["content"] == "Hierarchy message"

    def test_filter_by_task(self):
        """Test filtering conversations by task_id."""
        project_id = str(uuid4())
        task_id = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                task_id=task_id,
                from_agent="StaffAgent",
                content="Task specific message"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="OtherAgent",
                content="General message"
            )
        )

        response = client.get(f"/api/conversations?task_id={task_id}")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["from_agent"] == "StaffAgent"

    def test_filter_by_from_agent(self):
        """Test filtering conversations by from_agent."""
        project_id = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="PartnerAgent"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="StaffAgent"
            )
        )

        response = client.get("/api/conversations?from_agent=PartnerAgent")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["from_agent"] == "PartnerAgent"

    def test_filter_by_message_type(self):
        """Test filtering conversations by message_type."""
        project_id = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                message_type="instruction"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                message_type="error"
            )
        )

        response = client.get("/api/conversations?message_type=instruction")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["message_type"] == "instruction"

    def test_exclude_errors(self):
        """Test excluding error messages from results."""
        project_id = str(uuid4())

        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                message_type="response"
            )
        )
        client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                message_type="error"
            )
        )

        response = client.get("/api/conversations?include_errors=false")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["message_type"] == "response"

    def test_pagination(self):
        """Test pagination of results."""
        project_id = str(uuid4())
        for i in range(25):
            client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    content=f"Message {i}"
                )
            )

        # Page 1
        response = client.get("/api/conversations?page=1&page_size=10")
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["has_more"] is True

        # Page 2
        response = client.get("/api/conversations?page=2&page_size=10")
        data = response.json()
        assert len(data["items"]) == 10
        assert data["has_more"] is True

        # Page 3 (last page)
        response = client.get("/api/conversations?page=3&page_size=10")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["has_more"] is False

    def test_sorted_by_timestamp_descending(self):
        """Test that results are sorted by timestamp (newest first)."""
        project_id = str(uuid4())

        # Create conversations with slight delay to ensure different timestamps
        for i in range(3):
            client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    content=f"Message {i}"
                )
            )

        response = client.get("/api/conversations")
        data = response.json()

        # Verify descending order (newest first)
        timestamps = [item["timestamp"] for item in data["items"]]
        assert timestamps == sorted(timestamps, reverse=True)


# ============================================================================
# Test: POST /api/conversations
# ============================================================================

class TestCreateConversation:
    """Tests for POST /api/conversations."""

    def test_create_basic(self):
        """Test creating a basic conversation entry."""
        project_id = str(uuid4())
        response = client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="PartnerAgent",
                to_agent="ManagerAgent",
                message_type="instruction",
                content="Please analyze the revenue cycle"
            )
        )

        assert response.status_code == 201
        data = response.json()
        assert data["from_agent"] == "PartnerAgent"
        assert data["to_agent"] == "ManagerAgent"
        assert data["message_type"] == "instruction"
        assert data["content"] == "Please analyze the revenue cycle"
        assert "id" in data
        assert "timestamp" in data

    def test_create_with_hierarchy_and_task(self):
        """Test creating conversation with hierarchy and task IDs."""
        project_id = str(uuid4())
        hierarchy_id = str(uuid4())
        task_id = str(uuid4())

        response = client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                hierarchy_id=hierarchy_id,
                task_id=task_id,
                content="Task-specific message"
            )
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project_id
        assert data["hierarchy_id"] == hierarchy_id
        assert data["task_id"] == task_id

    def test_create_with_metadata(self):
        """Test creating conversation with metadata."""
        project_id = str(uuid4())
        response = client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="StaffAgent",
                to_agent="RalphLoop",
                message_type="response",
                content="Execution completed",
                metadata={
                    "loop_attempt": 2,
                    "strategy_used": "simplified",
                    "duration": 5.3
                }
            )
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["loop_attempt"] == 2
        assert data["metadata"]["strategy_used"] == "simplified"
        assert data["metadata"]["duration"] == 5.3

    def test_create_with_tool_call_metadata(self):
        """Test creating conversation with tool_call metadata."""
        project_id = str(uuid4())
        response = client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                message_type="tool_use",
                content="Calling external tool",
                metadata={
                    "tool_call": "search_documents",
                    "file_refs": ["file1.pdf", "file2.xlsx"]
                }
            )
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["tool_call"] == "search_documents"
        assert data["metadata"]["file_refs"] == ["file1.pdf", "file2.xlsx"]

    def test_create_all_message_types(self):
        """Test creating conversations with all valid message types."""
        project_id = str(uuid4())
        valid_types = [
            "instruction", "response", "question", "answer",
            "error", "escalation", "feedback", "tool_use"
        ]

        for msg_type in valid_types:
            response = client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    message_type=msg_type,
                    content=f"Message type: {msg_type}"
                )
            )
            assert response.status_code == 201, f"Failed for type: {msg_type}"

    def test_invalid_message_type(self):
        """Test validation error for invalid message type."""
        project_id = str(uuid4())
        response = client.post(
            "/api/conversations",
            json={
                "project_id": project_id,
                "from_agent": "Agent",
                "to_agent": "Manager",
                "message_type": "invalid_type",
                "content": "Test"
            }
        )
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        # Missing from_agent
        response = client.post(
            "/api/conversations",
            json={
                "project_id": str(uuid4()),
                "to_agent": "Manager",
                "message_type": "response",
                "content": "Test"
            }
        )
        assert response.status_code == 422

        # Missing content
        response = client.post(
            "/api/conversations",
            json={
                "project_id": str(uuid4()),
                "from_agent": "Agent",
                "to_agent": "Manager",
                "message_type": "response"
            }
        )
        assert response.status_code == 422

    def test_empty_content_rejected(self):
        """Test that empty content is rejected."""
        response = client.post(
            "/api/conversations",
            json={
                "project_id": str(uuid4()),
                "from_agent": "Agent",
                "to_agent": "Manager",
                "message_type": "response",
                "content": ""
            }
        )
        assert response.status_code == 422


# ============================================================================
# Test: GET /api/conversations/{id}
# ============================================================================

class TestGetConversation:
    """Tests for GET /api/conversations/{id}."""

    def test_get_existing(self):
        """Test retrieving an existing conversation."""
        project_id = str(uuid4())

        # Create a conversation
        create_response = client.post(
            "/api/conversations",
            json=create_test_conversation(
                project_id=project_id,
                from_agent="PartnerAgent",
                content="Test content"
            )
        )
        conv_id = create_response.json()["id"]

        # Retrieve it
        response = client.get(f"/api/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert data["from_agent"] == "PartnerAgent"
        assert data["content"] == "Test content"

    def test_get_not_found(self):
        """Test 404 response for non-existent conversation."""
        fake_id = str(uuid4())
        response = client.get(f"/api/conversations/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_invalid_uuid(self):
        """Test error response for invalid UUID format."""
        response = client.get("/api/conversations/invalid-uuid")
        assert response.status_code == 422


# ============================================================================
# Test: GET /api/conversations/stats
# ============================================================================

class TestConversationStats:
    """Tests for GET /api/conversations/stats."""

    def test_stats_empty(self):
        """Test stats when no conversations exist."""
        response = client.get("/api/conversations/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 0
        assert data["by_agent"] == {}
        assert data["by_type"] == {}
        assert data["error_count"] == 0
        assert data["escalation_count"] == 0

    def test_stats_with_data(self):
        """Test stats calculation with conversation data."""
        project_id = str(uuid4())

        # Create various messages
        messages = [
            ("Partner", "instruction"),
            ("Partner", "instruction"),
            ("Manager", "response"),
            ("Staff", "response"),
            ("Staff", "error"),
            ("RalphLoop", "escalation"),
        ]

        for agent, msg_type in messages:
            client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    from_agent=agent,
                    message_type=msg_type,
                    content="Test"
                )
            )

        response = client.get(f"/api/conversations/stats?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["total_messages"] == 6
        assert data["by_agent"]["Partner"] == 2
        assert data["by_agent"]["Manager"] == 1
        assert data["by_agent"]["Staff"] == 2
        assert data["by_agent"]["RalphLoop"] == 1
        assert data["by_type"]["instruction"] == 2
        assert data["by_type"]["response"] == 2
        assert data["by_type"]["error"] == 1
        assert data["by_type"]["escalation"] == 1
        assert data["error_count"] == 1
        assert data["escalation_count"] == 1

    def test_stats_filter_by_project(self):
        """Test stats filtering by project."""
        project1 = str(uuid4())
        project2 = str(uuid4())

        # Create messages in project1
        for _ in range(3):
            client.post(
                "/api/conversations",
                json=create_test_conversation(project_id=project1)
            )

        # Create messages in project2
        for _ in range(5):
            client.post(
                "/api/conversations",
                json=create_test_conversation(project_id=project2)
            )

        # Stats for project1 only
        response = client.get(f"/api/conversations/stats?project_id={project1}")
        data = response.json()
        assert data["total_messages"] == 3

        # Stats for project2 only
        response = client.get(f"/api/conversations/stats?project_id={project2}")
        data = response.json()
        assert data["total_messages"] == 5

    def test_stats_filter_by_task(self):
        """Test stats filtering by task."""
        project_id = str(uuid4())
        task_id = str(uuid4())

        # Messages with task
        for _ in range(2):
            client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    task_id=task_id
                )
            )

        # Messages without task
        for _ in range(3):
            client.post(
                "/api/conversations",
                json=create_test_conversation(project_id=project_id)
            )

        response = client.get(f"/api/conversations/stats?task_id={task_id}")
        data = response.json()
        assert data["total_messages"] == 2


# ============================================================================
# Test: POST /api/conversations/bulk
# ============================================================================

class TestBulkCreate:
    """Tests for POST /api/conversations/bulk."""

    def test_bulk_create(self):
        """Test creating multiple conversations in bulk."""
        project_id = str(uuid4())

        response = client.post(
            "/api/conversations/bulk",
            json=[
                create_test_conversation(
                    project_id=project_id,
                    from_agent="Agent1",
                    message_type="instruction",
                    content="Message 1"
                ),
                create_test_conversation(
                    project_id=project_id,
                    from_agent="Agent2",
                    message_type="response",
                    content="Message 2"
                ),
                create_test_conversation(
                    project_id=project_id,
                    from_agent="Agent3",
                    message_type="feedback",
                    content="Message 3"
                )
            ]
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        assert data[0]["from_agent"] == "Agent1"
        assert data[1]["from_agent"] == "Agent2"
        assert data[2]["from_agent"] == "Agent3"

    def test_bulk_create_empty_list(self):
        """Test bulk create with empty list."""
        response = client.post("/api/conversations/bulk", json=[])
        assert response.status_code == 201
        data = response.json()
        assert data == []

    def test_bulk_create_with_metadata(self):
        """Test bulk create with metadata on each item."""
        project_id = str(uuid4())

        response = client.post(
            "/api/conversations/bulk",
            json=[
                create_test_conversation(
                    project_id=project_id,
                    message_type="tool_use",
                    content="Tool call 1",
                    metadata={"tool_call": "search", "duration": 1.5}
                ),
                create_test_conversation(
                    project_id=project_id,
                    message_type="tool_use",
                    content="Tool call 2",
                    metadata={"tool_call": "analyze", "duration": 2.3}
                )
            ]
        )

        assert response.status_code == 201
        data = response.json()
        assert data[0]["metadata"]["tool_call"] == "search"
        assert data[1]["metadata"]["tool_call"] == "analyze"

    def test_bulk_create_validation_error(self):
        """Test bulk create fails if any item is invalid."""
        project_id = str(uuid4())

        response = client.post(
            "/api/conversations/bulk",
            json=[
                create_test_conversation(
                    project_id=project_id,
                    content="Valid message"
                ),
                {
                    "project_id": project_id,
                    "from_agent": "Agent",
                    "to_agent": "Manager",
                    "message_type": "invalid_type",  # Invalid
                    "content": "Test"
                }
            ]
        )
        assert response.status_code == 422


# ============================================================================
# Integration Tests
# ============================================================================

class TestConversationIntegration:
    """Integration tests for conversation API."""

    def test_create_and_retrieve_flow(self):
        """Test complete create -> list -> get flow."""
        project_id = str(uuid4())
        task_id = str(uuid4())

        # Create multiple conversations
        conv_ids = []
        for i in range(3):
            response = client.post(
                "/api/conversations",
                json=create_test_conversation(
                    project_id=project_id,
                    task_id=task_id,
                    from_agent=f"Agent{i}",
                    content=f"Message {i}"
                )
            )
            conv_ids.append(response.json()["id"])

        # List all for task
        list_response = client.get(f"/api/conversations?task_id={task_id}")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3

        # Get each individually
        for conv_id in conv_ids:
            get_response = client.get(f"/api/conversations/{conv_id}")
            assert get_response.status_code == 200

        # Verify stats
        stats_response = client.get(f"/api/conversations/stats?task_id={task_id}")
        assert stats_response.json()["total_messages"] == 3

    def test_ralph_wiggum_loop_scenario(self):
        """Test scenario simulating Ralph-wiggum loop conversations."""
        project_id = str(uuid4())
        task_id = str(uuid4())

        # Simulate a Ralph-wiggum loop with multiple attempts
        loop_conversations = [
            {
                "from_agent": "RalphLoop",
                "to_agent": "StaffAgent",
                "message_type": "instruction",
                "content": "Execute task with standard approach",
                "metadata": {"loop_attempt": 1, "strategy_used": "standard"}
            },
            {
                "from_agent": "StaffAgent",
                "to_agent": "RalphLoop",
                "message_type": "error",
                "content": "Execution failed: timeout",
                "metadata": {"loop_attempt": 1, "duration": 30.0}
            },
            {
                "from_agent": "RalphLoop",
                "to_agent": "StaffAgent",
                "message_type": "instruction",
                "content": "Retry with simplified approach",
                "metadata": {"loop_attempt": 2, "strategy_used": "simplified"}
            },
            {
                "from_agent": "StaffAgent",
                "to_agent": "RalphLoop",
                "message_type": "response",
                "content": "Execution successful",
                "metadata": {"loop_attempt": 2, "duration": 5.3}
            }
        ]

        # Create all conversations in bulk
        bulk_payload = [
            create_test_conversation(
                project_id=project_id,
                task_id=task_id,
                from_agent=c["from_agent"],
                to_agent=c["to_agent"],
                message_type=c["message_type"],
                content=c["content"],
                metadata=c["metadata"]
            )
            for c in loop_conversations
        ]

        response = client.post("/api/conversations/bulk", json=bulk_payload)
        assert response.status_code == 201

        # Verify stats show the error
        stats = client.get(f"/api/conversations/stats?task_id={task_id}").json()
        assert stats["total_messages"] == 4
        assert stats["error_count"] == 1
        assert stats["by_agent"]["RalphLoop"] == 2
        assert stats["by_agent"]["StaffAgent"] == 2
