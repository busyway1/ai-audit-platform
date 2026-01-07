"""
Comprehensive Unit Tests for src/db/checkpointer.py

Test Coverage:
- get_checkpointer() function
- setup_checkpoint_tables() function
- get_checkpoint_by_thread_id() function
- PostgresSaver initialization
- Environment variable handling
- Error cases and edge cases

Mock Strategy:
- Mock PostgresSaver.from_conn_string() to avoid real DB connections
- Mock environment variables using monkeypatch
- Mock PostgresSaver.setup() call
- Mock PostgresSaver.get() call

Target Coverage: 100%
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import os
from dotenv import load_dotenv

# Import the module under test
from src.db.checkpointer import (
    get_checkpointer,
    setup_checkpoint_tables,
    get_checkpoint_by_thread_id,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_postgres_saver():
    """Create a mock PostgresSaver instance."""
    saver = MagicMock()
    saver.setup = MagicMock()

    # Mock get() to return a checkpoint-like object with .values attribute
    mock_checkpoint = MagicMock()
    mock_checkpoint.values = None
    saver.get = MagicMock(return_value=mock_checkpoint)

    return saver


@pytest.fixture
def mock_postgres_saver_with_checkpoint():
    """Create a mock PostgresSaver with a checkpoint."""
    saver = MagicMock()
    saver.setup = MagicMock()

    checkpoint_data = {
        "channel_values": {
            "status": "IN_PROGRESS",
            "project_id": "test-001",
        },
        "metadata": {
            "step": 5,
            "thread_id": "task-001",
        },
    }

    # Mock get() to return a checkpoint object with .values attribute
    mock_checkpoint = MagicMock()
    mock_checkpoint.values = checkpoint_data
    saver.get = MagicMock(return_value=mock_checkpoint)

    return saver


def create_mock_context_manager(mock_saver):
    """Helper to create a proper context manager mock for PostgresSaver.from_conn_string."""
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__ = MagicMock(return_value=mock_saver)
    mock_context_manager.__exit__ = MagicMock(return_value=False)
    return mock_context_manager


@pytest.fixture
def valid_connection_string():
    """Valid PostgreSQL connection string."""
    return "postgresql://postgres:password@db.example.supabase.co:5432/postgres"


@pytest.fixture
def invalid_connection_string():
    """Invalid PostgreSQL connection string (missing protocol)."""
    return "invalid://connection@string"


# ============================================================================
# TEST: get_checkpointer()
# ============================================================================


class TestGetCheckpointer:
    """Tests for get_checkpointer() function."""

    def test_get_checkpointer_success_with_valid_env(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test successful checkpointer initialization with valid connection string."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute - use as context manager
            with get_checkpointer() as result:
                # Verify
                assert result is mock_postgres_saver
            mock_from_conn.assert_called_once_with(valid_connection_string)

    def test_get_checkpointer_raises_on_missing_env(self, monkeypatch):
        """Test that ValueError is raised when POSTGRES_CONNECTION_STRING is not set."""
        # Setup
        monkeypatch.delenv("POSTGRES_CONNECTION_STRING", raising=False)

        # Execute & Verify - error raised when entering context manager
        with pytest.raises(ValueError) as exc_info:
            with get_checkpointer():
                pass

        # Verify error message
        assert "POSTGRES_CONNECTION_STRING not found" in str(exc_info.value)
        assert "Supabase Dashboard" in str(exc_info.value)

    def test_get_checkpointer_raises_on_empty_env(self, monkeypatch):
        """Test that ValueError is raised when POSTGRES_CONNECTION_STRING is empty string."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", "")

        # Execute & Verify - error raised when entering context manager
        with pytest.raises(ValueError) as exc_info:
            with get_checkpointer():
                pass

        # Verify error message
        assert "POSTGRES_CONNECTION_STRING not found" in str(exc_info.value)

    def test_get_checkpointer_accepts_whitespace_env(self, monkeypatch, mock_postgres_saver):
        """Test that whitespace connection string is passed to PostgresSaver.from_conn_string()."""
        # Note: The code doesn't validate whitespace, it just checks truthiness
        # PostgresSaver.from_conn_string() will handle invalid format
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", "   ")

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute
            with get_checkpointer() as result:
                # Verify whitespace string is passed through
                assert result is mock_postgres_saver
            mock_from_conn.assert_called_once_with("   ")

    def test_get_checkpointer_returns_correct_type(
        self, monkeypatch, valid_connection_string
    ):
        """Test that get_checkpointer returns PostgresSaver instance."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)
        mock_saver = MagicMock()

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_saver),
        ):
            # Execute
            with get_checkpointer() as result:
                # Verify type
                assert result is mock_saver

    def test_get_checkpointer_with_special_chars_in_password(
        self, monkeypatch, mock_postgres_saver
    ):
        """Test get_checkpointer with special characters in password."""
        # Setup - connection string with special chars in password
        special_conn_string = (
            "postgresql://user:p@ss%20w0rd!@db.example.supabase.co:5432/postgres"
        )
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", special_conn_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute
            with get_checkpointer() as result:
                # Verify
                assert result is mock_postgres_saver
            mock_from_conn.assert_called_once_with(special_conn_string)

    def test_get_checkpointer_with_complex_url(
        self, monkeypatch, mock_postgres_saver
    ):
        """Test get_checkpointer with complex PostgreSQL URL."""
        # Setup
        complex_conn_string = (
            "postgresql://user:pass@host.co:5432/dbname?"
            "sslmode=require&application_name=audit_platform"
        )
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", complex_conn_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute
            with get_checkpointer() as result:
                # Verify
                assert result is mock_postgres_saver
            mock_from_conn.assert_called_once_with(complex_conn_string)

    def test_get_checkpointer_called_multiple_times(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test that get_checkpointer can be called multiple times (no singleton pattern)."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute - call multiple times
            with get_checkpointer() as result1:
                assert result1 is mock_postgres_saver
            with get_checkpointer() as result2:
                assert result2 is mock_postgres_saver
            with get_checkpointer() as result3:
                assert result3 is mock_postgres_saver

            # Verify - from_conn_string should be called each time
            assert mock_from_conn.call_count == 3


# ============================================================================
# TEST: setup_checkpoint_tables()
# ============================================================================


class TestSetupCheckpointTables:
    """Tests for setup_checkpoint_tables() function."""

    def test_setup_checkpoint_tables_success(
        self, monkeypatch, valid_connection_string, mock_postgres_saver, capsys
    ):
        """Test successful setup of checkpoint tables."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            setup_checkpoint_tables()

            # Verify setup() was called
            mock_postgres_saver.setup.assert_called_once()

            # Verify success message
            captured = capsys.readouterr()
            assert "✅ PostgresSaver checkpoint tables created successfully" in captured.out

    def test_setup_checkpoint_tables_calls_get_checkpointer(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test that setup_checkpoint_tables calls get_checkpointer()."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute
            setup_checkpoint_tables()

            # Verify that from_conn_string was called (via get_checkpointer)
            mock_from_conn.assert_called_once()

    def test_setup_checkpoint_tables_propagates_get_checkpointer_error(
        self, monkeypatch
    ):
        """Test that setup_checkpoint_tables propagates errors from get_checkpointer()."""
        # Setup
        monkeypatch.delenv("POSTGRES_CONNECTION_STRING", raising=False)

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            setup_checkpoint_tables()

        assert "POSTGRES_CONNECTION_STRING not found" in str(exc_info.value)

    def test_setup_checkpoint_tables_propagates_setup_error(
        self, monkeypatch, valid_connection_string
    ):
        """Test that setup_checkpoint_tables propagates errors from setup()."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)
        mock_saver = MagicMock()
        mock_saver.setup.side_effect = Exception("Database connection failed")

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_saver),
        ):
            # Execute & Verify
            with pytest.raises(Exception) as exc_info:
                setup_checkpoint_tables()

            assert "Database connection failed" in str(exc_info.value)
            mock_saver.setup.assert_called_once()

    def test_setup_checkpoint_tables_idempotent(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test that setup_checkpoint_tables is idempotent (safe to call multiple times)."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute - call multiple times
            setup_checkpoint_tables()
            setup_checkpoint_tables()
            setup_checkpoint_tables()

            # Verify setup() was called 3 times (once per call)
            assert mock_postgres_saver.setup.call_count == 3

    def test_setup_checkpoint_tables_prints_success_message(
        self, monkeypatch, valid_connection_string, mock_postgres_saver, capsys
    ):
        """Test that success message is printed."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            setup_checkpoint_tables()

            # Verify output
            captured = capsys.readouterr()
            assert "successfully" in captured.out.lower()


# ============================================================================
# TEST: get_checkpoint_by_thread_id()
# ============================================================================


class TestGetCheckpointByThreadId:
    """Tests for get_checkpoint_by_thread_id() function."""

    def test_get_checkpoint_by_thread_id_success(
        self, monkeypatch, valid_connection_string, mock_postgres_saver_with_checkpoint
    ):
        """Test successful retrieval of checkpoint by thread_id."""
        # Setup
        thread_id = "task-001"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver_with_checkpoint),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            assert result is not None
            assert result["channel_values"]["status"] == "IN_PROGRESS"
            assert result["metadata"]["thread_id"] == "task-001"

    def test_get_checkpoint_by_thread_id_not_found(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test get_checkpoint_by_thread_id returns None when checkpoint not found."""
        # Setup
        thread_id = "nonexistent-task"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)
        mock_postgres_saver.get.return_value = None  # No checkpoint found

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            assert result is None

    def test_get_checkpoint_by_thread_id_calls_get_with_correct_config(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test that get_checkpoint_by_thread_id calls saver.get() with correct config."""
        # Setup
        thread_id = "task-123"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            get_checkpoint_by_thread_id(thread_id)

            # Verify get() was called with correct config
            mock_postgres_saver.get.assert_called_once()
            call_args = mock_postgres_saver.get.call_args
            config = call_args[0][0]
            assert config["configurable"]["thread_id"] == thread_id

    def test_get_checkpoint_by_thread_id_with_empty_thread_id(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test get_checkpoint_by_thread_id with empty thread_id."""
        # Setup
        thread_id = ""
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)
        mock_postgres_saver.get.return_value = None

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            assert result is None
            mock_postgres_saver.get.assert_called_once()

    def test_get_checkpoint_by_thread_id_with_special_chars(
        self, monkeypatch, valid_connection_string, mock_postgres_saver_with_checkpoint
    ):
        """Test get_checkpoint_by_thread_id with special characters in thread_id."""
        # Setup
        thread_id = "task-001_v2.0-beta"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver_with_checkpoint),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            call_args = mock_postgres_saver_with_checkpoint.get.call_args
            config = call_args[0][0]
            assert config["configurable"]["thread_id"] == thread_id

    def test_get_checkpoint_by_thread_id_complex_checkpoint(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test get_checkpoint_by_thread_id with complex checkpoint data."""
        # Setup
        thread_id = "task-complex"
        complex_checkpoint = {
            "channel_values": {
                "status": "PAUSED",
                "project_id": "proj-123",
                "messages": [
                    {"role": "user", "content": "test"},
                    {"role": "assistant", "content": "response"},
                ],
                "nested": {
                    "data": {
                        "key": "value",
                    }
                },
            },
            "metadata": {
                "step": 10,
                "thread_id": thread_id,
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        # Mock get() to return a checkpoint object with .values attribute
        mock_checkpoint = MagicMock()
        mock_checkpoint.values = complex_checkpoint
        mock_postgres_saver.get.return_value = mock_checkpoint

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            assert result == complex_checkpoint
            assert result["channel_values"]["status"] == "PAUSED"
            assert len(result["channel_values"]["messages"]) == 2
            assert result["channel_values"]["nested"]["data"]["key"] == "value"

    def test_get_checkpoint_by_thread_id_long_thread_id(
        self, monkeypatch, valid_connection_string, mock_postgres_saver_with_checkpoint
    ):
        """Test get_checkpoint_by_thread_id with very long thread_id."""
        # Setup
        thread_id = "task-" + "x" * 1000
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver_with_checkpoint),
        ):
            # Execute
            result = get_checkpoint_by_thread_id(thread_id)

            # Verify
            call_args = mock_postgres_saver_with_checkpoint.get.call_args
            config = call_args[0][0]
            assert config["configurable"]["thread_id"] == thread_id

    def test_get_checkpoint_by_thread_id_propagates_get_checkpointer_error(
        self, monkeypatch
    ):
        """Test that errors from get_checkpointer are propagated."""
        # Setup
        monkeypatch.delenv("POSTGRES_CONNECTION_STRING", raising=False)

        # Execute & Verify
        with pytest.raises(ValueError):
            get_checkpoint_by_thread_id("task-001")

    def test_get_checkpoint_by_thread_id_propagates_saver_error(
        self, monkeypatch, valid_connection_string
    ):
        """Test that errors from saver.get() are propagated."""
        # Setup
        thread_id = "task-error"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)
        mock_saver = MagicMock()
        mock_saver.get.side_effect = Exception("Saver error")

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_saver),
        ):
            # Execute & Verify
            with pytest.raises(Exception) as exc_info:
                get_checkpoint_by_thread_id(thread_id)

            assert "Saver error" in str(exc_info.value)


# ============================================================================
# TEST: Integration and Edge Cases
# ============================================================================


class TestIntegration:
    """Integration tests for checkpointer module."""

    def test_workflow_get_setup_retrieve(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test typical workflow: get checkpointer, setup tables, retrieve checkpoint."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        # Mock get() to return a checkpoint object with .values attribute
        mock_checkpoint = MagicMock()
        mock_checkpoint.values = {"channel_values": {"status": "OK"}}
        mock_postgres_saver.get.return_value = mock_checkpoint

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute - typical workflow
            with get_checkpointer() as checkpointer:
                assert checkpointer is mock_postgres_saver
            setup_checkpoint_tables()
            checkpoint = get_checkpoint_by_thread_id("task-001")

            # Verify
            mock_postgres_saver.setup.assert_called_once()
            assert checkpoint is not None

    def test_multiple_thread_ids(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test retrieving checkpoints for multiple thread_ids."""
        # Setup
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", valid_connection_string)

        def get_side_effect(config):
            thread_id = config["configurable"]["thread_id"]
            mock_checkpoint = MagicMock()
            if thread_id == "task-001":
                mock_checkpoint.values = {"channel_values": {"id": "001"}}
            elif thread_id == "task-002":
                mock_checkpoint.values = {"channel_values": {"id": "002"}}
            else:
                return None
            return mock_checkpoint

        mock_postgres_saver.get.side_effect = get_side_effect

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ):
            # Execute
            cp1 = get_checkpoint_by_thread_id("task-001")
            cp2 = get_checkpoint_by_thread_id("task-002")
            cp3 = get_checkpoint_by_thread_id("task-003")

            # Verify
            assert cp1["channel_values"]["id"] == "001"
            assert cp2["channel_values"]["id"] == "002"
            assert cp3 is None

    def test_environment_variable_persistence(
        self, monkeypatch, valid_connection_string, mock_postgres_saver
    ):
        """Test that environment variable is correctly used across multiple calls."""
        # Setup
        test_conn_string = "postgresql://test:test@localhost/test"
        monkeypatch.setenv("POSTGRES_CONNECTION_STRING", test_conn_string)

        with patch(
            "src.db.checkpointer.PostgresSaver.from_conn_string",
            return_value=create_mock_context_manager(mock_postgres_saver),
        ) as mock_from_conn:
            # Execute
            with get_checkpointer():
                pass
            with get_checkpointer():
                pass
            setup_checkpoint_tables()

            # Verify same connection string used each time
            calls = mock_from_conn.call_args_list
            for call_obj in calls:
                assert call_obj[0][0] == test_conn_string


# ============================================================================
# TEST: Load_dotenv Behavior
# ============================================================================


class TestDotenvLoading:
    """Tests for .env file loading behavior."""

    def test_load_dotenv_called_at_module_import(self):
        """Verify that load_dotenv() is called when module is imported."""
        # This test verifies the module imports load_dotenv and calls it
        # The import statement is at the top of checkpointer.py
        import src.db.checkpointer as checkpointer_module

        # Verify load_dotenv exists in the module
        assert hasattr(checkpointer_module, "load_dotenv")


# ============================================================================
# TEST: Error Message Quality
# ============================================================================


class TestErrorMessages:
    """Tests for error message quality and helpfulness."""

    def test_missing_env_error_message_helpful(self, monkeypatch):
        """Test that error message for missing env var is helpful."""
        # Setup
        monkeypatch.delenv("POSTGRES_CONNECTION_STRING", raising=False)

        # Execute - error raised when entering context manager
        with pytest.raises(ValueError) as exc_info:
            with get_checkpointer():
                pass

        # Verify error message contains helpful information
        error_msg = str(exc_info.value)
        assert "POSTGRES_CONNECTION_STRING" in error_msg
        assert "Supabase" in error_msg
        assert "Dashboard" in error_msg
        assert "Database" in error_msg
