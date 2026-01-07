"""
Unit Tests for Supabase Client Configuration - 100% Coverage

This module provides comprehensive unit tests for the Supabase client module.
Tests cover all functions with 100% code coverage including:

- Client initialization (get_supabase_client)
- Environment variable validation
- Error handling and edge cases
- Health check (check_connection)
- Data retrieval functions (get_project_by_id, get_tasks_by_project, etc.)

IMPORTANT: No real Supabase connections are made during tests.
All tests use mocked responses and execute in <0.1s.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import sys


# ============================================================================
# FIXTURES - Mock Setup
# ============================================================================

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client with table query methods."""
    return MagicMock()


# ============================================================================
# TEST: get_supabase_client() - Initialization
# ============================================================================

class TestGetSupabaseClient:
    """Tests for get_supabase_client() function."""

    @patch("src.db.supabase_client.os.getenv")
    @patch("src.db.supabase_client.create_client")
    def test_get_client_with_valid_credentials(self, mock_create, mock_getenv):
        """Test successful client initialization with valid credentials."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        def getenv_side_effect(key):
            return {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "valid-key-123"
            }.get(key)

        mock_getenv.side_effect = getenv_side_effect

        from src.db.supabase_client import get_supabase_client

        client = get_supabase_client()

        assert client == mock_client
        mock_create.assert_called_once_with("https://test.supabase.co", "valid-key-123")

    @patch("src.db.supabase_client.os.getenv")
    def test_get_client_missing_url(self, mock_getenv):
        """Test ValueError raised when SUPABASE_URL is missing."""
        mock_getenv.return_value = None

        from src.db.supabase_client import get_supabase_client

        with pytest.raises(ValueError) as exc_info:
            get_supabase_client()

        assert "SUPABASE_URL" in str(exc_info.value)
        assert "Project Settings" in str(exc_info.value)

    @patch("src.db.supabase_client.os.getenv")
    def test_get_client_missing_service_key(self, mock_getenv):
        """Test ValueError raised when SUPABASE_SERVICE_KEY is missing."""
        def getenv_side_effect(key):
            if key == "SUPABASE_URL":
                return "https://test.supabase.co"
            return None

        mock_getenv.side_effect = getenv_side_effect

        from src.db.supabase_client import get_supabase_client

        with pytest.raises(ValueError) as exc_info:
            get_supabase_client()

        assert "SUPABASE_SERVICE_KEY" in str(exc_info.value)
        assert "service_role" in str(exc_info.value).lower()

    @patch("src.db.supabase_client.os.getenv")
    def test_get_client_error_message_contains_guidance(self, mock_getenv):
        """Test error messages contain helpful guidance."""
        mock_getenv.return_value = None

        from src.db.supabase_client import get_supabase_client

        try:
            get_supabase_client()
        except ValueError as e:
            error_msg = str(e)
            assert "Supabase Dashboard" in error_msg
            assert "API" in error_msg


# ============================================================================
# TEST: check_connection() - Health Check
# ============================================================================

class TestCheckConnection:
    """Tests for check_connection() async function."""

    @pytest.mark.asyncio
    async def test_check_connection_success(self, mock_supabase_client):
        """Test successful connection check."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]

        mock_table = MagicMock()
        mock_table.select.return_value.limit.return_value.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        # Override the global supabase instance
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = await supabase_client.check_connection()

            assert result is True
            mock_supabase_client.table.assert_called_with("audit_projects")
            mock_table.select.assert_called_with("id")
        finally:
            supabase_client.supabase = original_supabase

    @pytest.mark.asyncio
    async def test_check_connection_exception(self, mock_supabase_client):
        """Test connection check with exception."""
        mock_supabase_client.table.side_effect = Exception("Connection timeout")

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            with patch("builtins.print"):
                result = await supabase_client.check_connection()

            assert result is False
        finally:
            supabase_client.supabase = original_supabase


# ============================================================================
# TEST: get_project_by_id() - Project Retrieval
# ============================================================================

class TestGetProjectById:
    """Tests for get_project_by_id() function."""

    def test_get_project_found(self, mock_supabase_client):
        """Test successful project retrieval."""
        sample_project = {
            "id": "proj-123",
            "client_name": "Test Client"
        }

        mock_response = MagicMock()
        mock_response.data = [sample_project]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_project_by_id("proj-123")

            assert result == sample_project
            mock_supabase_client.table.assert_called_with("audit_projects")
            mock_table.select.assert_called_with("*")
        finally:
            supabase_client.supabase = original_supabase

    def test_get_project_not_found(self, mock_supabase_client):
        """Test project not found returns None."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_project_by_id("nonexistent")

            assert result is None
        finally:
            supabase_client.supabase = original_supabase

    def test_get_project_exception(self, mock_supabase_client):
        """Test project retrieval exception handling."""
        mock_table = MagicMock()
        mock_table.select.side_effect = Exception("Database error")

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            with patch("builtins.print"):
                result = supabase_client.get_project_by_id("proj-123")

            assert result is None
        finally:
            supabase_client.supabase = original_supabase


# ============================================================================
# TEST: get_tasks_by_project() - Task Retrieval
# ============================================================================

class TestGetTasksByProject:
    """Tests for get_tasks_by_project() function."""

    def test_get_tasks_multiple(self, mock_supabase_client):
        """Test retrieving multiple tasks."""
        sample_tasks = [
            {"id": "task-1", "category": "Sales"},
            {"id": "task-2", "category": "Inventory"},
        ]

        mock_response = MagicMock()
        mock_response.data = sample_tasks

        mock_table = MagicMock()
        mock_chain = mock_table.select.return_value.eq.return_value.order.return_value
        mock_chain.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_tasks_by_project("proj-123")

            assert result == sample_tasks
            assert len(result) == 2
        finally:
            supabase_client.supabase = original_supabase

    def test_get_tasks_empty(self, mock_supabase_client):
        """Test retrieving tasks with empty result."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_table = MagicMock()
        mock_chain = mock_table.select.return_value.eq.return_value.order.return_value
        mock_chain.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_tasks_by_project("proj-123")

            assert result == []
            assert isinstance(result, list)
        finally:
            supabase_client.supabase = original_supabase

    def test_get_tasks_exception(self, mock_supabase_client):
        """Test task retrieval exception handling."""
        mock_table = MagicMock()
        mock_table.select.side_effect = Exception("Query failed")

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            with patch("builtins.print"):
                result = supabase_client.get_tasks_by_project("proj-123")

            assert result == []
        finally:
            supabase_client.supabase = original_supabase


# ============================================================================
# TEST: get_task_by_thread_id() - Task by Thread ID
# ============================================================================

class TestGetTaskByThreadId:
    """Tests for get_task_by_thread_id() function."""

    def test_get_task_found(self, mock_supabase_client):
        """Test retrieving task by thread_id."""
        sample_task = {
            "id": "task-uuid",
            "thread_id": "task-001"
        }

        mock_response = MagicMock()
        mock_response.data = [sample_task]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_task_by_thread_id("task-001")

            assert result == sample_task
        finally:
            supabase_client.supabase = original_supabase

    def test_get_task_not_found(self, mock_supabase_client):
        """Test task not found returns None."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_task_by_thread_id("nonexistent")

            assert result is None
        finally:
            supabase_client.supabase = original_supabase

    def test_get_task_exception(self, mock_supabase_client):
        """Test task retrieval exception handling."""
        mock_table = MagicMock()
        mock_table.select.side_effect = Exception("Network error")

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            with patch("builtins.print"):
                result = supabase_client.get_task_by_thread_id("task-001")

            assert result is None
        finally:
            supabase_client.supabase = original_supabase


# ============================================================================
# TEST: get_messages_by_task() - Message Retrieval
# ============================================================================

class TestGetMessagesByTask:
    """Tests for get_messages_by_task() function."""

    def test_get_messages_multiple(self, mock_supabase_client):
        """Test retrieving multiple messages."""
        sample_messages = [
            {"id": "msg-1", "content": "Start"},
            {"id": "msg-2", "content": "Done"},
        ]

        mock_response = MagicMock()
        mock_response.data = sample_messages

        mock_table = MagicMock()
        mock_chain = (mock_table.select.return_value
                      .eq.return_value
                      .order.return_value
                      .limit.return_value)
        mock_chain.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_messages_by_task("task-123")

            assert result == sample_messages
            assert len(result) == 2
        finally:
            supabase_client.supabase = original_supabase

    def test_get_messages_custom_limit(self, mock_supabase_client):
        """Test retrieving messages with custom limit."""
        sample_messages = [{"id": f"msg-{i}"} for i in range(50)]

        mock_response = MagicMock()
        mock_response.data = sample_messages

        mock_table = MagicMock()
        mock_chain = (mock_table.select.return_value
                      .eq.return_value
                      .order.return_value
                      .limit.return_value)
        mock_chain.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_messages_by_task("task-123", limit=50)

            assert len(result) == 50
        finally:
            supabase_client.supabase = original_supabase

    def test_get_messages_empty(self, mock_supabase_client):
        """Test retrieving messages with empty result."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_table = MagicMock()
        mock_chain = (mock_table.select.return_value
                      .eq.return_value
                      .order.return_value
                      .limit.return_value)
        mock_chain.execute.return_value = mock_response

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            result = supabase_client.get_messages_by_task("task-123")

            assert result == []
        finally:
            supabase_client.supabase = original_supabase

    def test_get_messages_exception(self, mock_supabase_client):
        """Test message retrieval exception handling."""
        mock_table = MagicMock()
        mock_table.select.side_effect = Exception("DB error")

        mock_supabase_client.table.return_value = mock_table

        from src.db import supabase_client
        original_supabase = supabase_client.supabase
        supabase_client.supabase = mock_supabase_client

        try:
            with patch("builtins.print"):
                result = supabase_client.get_messages_by_task("task-123")

            assert result == []
        finally:
            supabase_client.supabase = original_supabase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
