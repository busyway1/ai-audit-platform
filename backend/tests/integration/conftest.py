"""Pytest Configuration for Integration Tests

This module provides shared fixtures and mocking setup for all integration tests.
Patches are applied BEFORE app initialization to prevent lifespan startup errors.
"""

import pytest
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# ============================================================================
# GLOBAL PATCHES - Applied Before App Import
# ============================================================================

# Create mock for get_checkpointer function BEFORE importing app
mock_checkpointer = MagicMock()
mock_checkpointer.setup = MagicMock()
mock_checkpointer.get = MagicMock(return_value=None)

# Use pytest's monkeypatch fixture hook to patch before app import
# For module-level patching, we use contextlib approach
import contextlib

@contextlib.contextmanager
def patch_checkpointer():
    """Context manager to patch get_checkpointer before app import."""
    with patch('src.db.checkpointer.get_checkpointer', return_value=mock_checkpointer):
        yield

# Apply patch and import app
# Use a simpler approach: mock at the source level
try:
    with patch_checkpointer():
        from src.main import app
except (AttributeError, ImportError):
    # If patch fails, import without patching
    from src.main import app


# ============================================================================
# CHECKPOINTER CONTEXT MANAGER MOCK
# ============================================================================

@contextlib.contextmanager
def mock_get_checkpointer():
    """
    Mock context manager for get_checkpointer that mimics PostgresSaver behavior.
    
    This prevents actual database connections during testing while allowing
    the checkpointer interface to work as expected.
    """
    mock_cp = MagicMock()
    mock_cp.setup = MagicMock()
    mock_cp.get = MagicMock(return_value=None)
    mock_cp.put = MagicMock()
    mock_cp.get_next_version = MagicMock(return_value=1)
    
    yield mock_cp


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient for integration testing."""
    return TestClient(app)


@pytest.fixture
def task_id() -> str:
    """Standard test task UUID."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def invalid_task_id() -> str:
    """Invalid task ID for error testing."""
    return "invalid-task-id"


@pytest.fixture
def task_id_2() -> str:
    """Second task UUID for multi-task testing."""
    return "660e8400-e29b-41d4-a716-446655440001"


@pytest.fixture
def sample_message(task_id: str) -> dict:
    """Sample agent message from Realtime INSERT."""
    return {
        "id": "msg-550e8400-e29b-41d4-a716-446655440001",
        "task_id": task_id,
        "agent_role": "auditor",
        "content": "Revenue transactions verified.",
        "created_at": "2024-01-06T12:00:00Z"
    }


@pytest.fixture
def realtime_payload(sample_message) -> dict:
    """Supabase Realtime INSERT payload."""
    return {
        "type": "INSERT",
        "schema": "public",
        "table": "agent_messages",
        "new": sample_message,
        "old": None
    }


@pytest.fixture
def mock_graph():
    """Create a mock LangGraph graph for testing."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock()
    mock.aupdate_state = AsyncMock()
    return mock


@pytest.fixture
def autouse_app_mocks(mock_graph):
    """Auto-apply app state mocks for all tests."""
    app.state.graph = mock_graph
    app.state.checkpointer = MagicMock()
    yield
    # Cleanup
    app.state.graph = None
    app.state.checkpointer = None


@pytest.fixture(autouse=True)
def setup_app_with_mocks(autouse_app_mocks):
    """Auto-setup app mocks for all tests."""
    yield


@pytest.fixture
def mock_checkpointer_fixture():
    """Fixture that patches get_checkpointer for E2E tests."""
    with patch('src.db.checkpointer.get_checkpointer', mock_get_checkpointer):
        yield mock_get_checkpointer
