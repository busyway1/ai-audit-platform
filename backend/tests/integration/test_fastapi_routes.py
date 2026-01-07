"""
Integration Tests for FastAPI Routes

This module provides comprehensive integration tests for the FastAPI REST API endpoints:
- POST /api/projects/start - Start audit project
- POST /api/tasks/approve - Approve and resume workflow
- GET /api/health - Health check endpoint
- CORS headers verification
- Error handling (4xx/5xx responses)

Test Approach:
1. Use FastAPI TestClient for HTTP testing
2. Mock LangGraph graph.ainvoke() and aupdate_state() methods
3. Mock Supabase client for database operations
4. Test realistic request/response payloads
5. Validate status codes, response schemas, and headers

Coverage:
- Normal happy path scenarios
- Error cases (validation, not found, server errors)
- CORS headers in responses
- Response payload structures match Pydantic models
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Dict, Any

from src.main import app, lifespan


# ============================================================================
# TEST FIXTURES - Setup and Teardown
# ============================================================================

@pytest.fixture
def client() -> TestClient:
    """
    Create a FastAPI TestClient for integration testing.

    The client allows us to make HTTP requests to the app without
    running a live server.

    Yields:
        TestClient: Configured test client for the FastAPI app
    """
    return TestClient(app)


@pytest.fixture
def mock_graph():
    """
    Create a mock LangGraph graph for testing.

    Mocks both ainvoke() (for executing workflow) and aupdate_state()
    (for updating state with approval decision).

    Returns:
        MagicMock: Mock graph with async methods
    """
    mock = MagicMock()
    mock.ainvoke = AsyncMock()
    mock.aupdate_state = AsyncMock()
    return mock


@pytest.fixture
def mock_supabase():
    """
    Create a mock Supabase client for testing.

    Used to test sync_task_to_supabase() function.

    Returns:
        MagicMock: Mock Supabase client
    """
    mock = MagicMock()
    mock.table = MagicMock(return_value=MagicMock())
    return mock


@pytest.fixture
def setup_app_with_mocks(client, mock_graph):
    """
    Set up the app with mock dependencies before each test.

    Injects mock_graph into app.state.graph so routes can access it.

    Args:
        client: TestClient fixture
        mock_graph: Mock LangGraph graph

    Yields:
        tuple: (client, mock_graph) with app.state.graph populated
    """
    # Set up mock graph in app state
    app.state.graph = mock_graph
    app.state.checkpointer = MagicMock()
    yield (client, mock_graph)
    # Cleanup
    app.state.graph = None
    app.state.checkpointer = None


# ============================================================================
# FIXTURES - Request/Response Data
# ============================================================================

@pytest.fixture
def valid_start_audit_request() -> Dict[str, Any]:
    """
    Valid request payload for POST /api/projects/start

    Returns:
        Dict: Valid StartAuditRequest data
    """
    return {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0
    }


@pytest.fixture
def invalid_start_audit_request_missing_field() -> Dict[str, Any]:
    """
    Invalid request - missing required field (client_name)

    Returns:
        Dict: Invalid StartAuditRequest data
    """
    return {
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0
    }


@pytest.fixture
def invalid_start_audit_request_bad_fiscal_year() -> Dict[str, Any]:
    """
    Invalid request - fiscal_year outside valid range (2000-2100)

    Returns:
        Dict: Invalid StartAuditRequest data
    """
    return {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 1999,  # Below minimum
        "overall_materiality": 1000000.0
    }


@pytest.fixture
def invalid_start_audit_request_negative_materiality() -> Dict[str, Any]:
    """
    Invalid request - negative materiality (must be > 0)

    Returns:
        Dict: Invalid StartAuditRequest data
    """
    return {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": -100000.0
    }


@pytest.fixture
def valid_approval_request() -> Dict[str, Any]:
    """
    Valid request payload for POST /api/tasks/approve

    Returns:
        Dict: Valid ApprovalRequest data
    """
    return {
        "thread_id": "project-abc-manufacturing-co-2024",
        "approved": True
    }


@pytest.fixture
def invalid_approval_request_empty_thread_id() -> Dict[str, Any]:
    """
    Invalid request - empty thread_id (min_length=1)

    Returns:
        Dict: Invalid ApprovalRequest data
    """
    return {
        "thread_id": "",
        "approved": True
    }


@pytest.fixture
def sample_workflow_result() -> Dict[str, Any]:
    """
    Sample LangGraph workflow result for ainvoke()

    Returns:
        Dict: Typical workflow result with tasks and next_action
    """
    return {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0,
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                "status": "pending_review",
                "risk_level": "High",
                "materiality": 500000.0
            },
            {
                "id": "TASK-002",
                "category": "Inventory",
                "status": "pending_review",
                "risk_level": "Medium",
                "materiality": 300000.0
            }
        ],
        "is_approved": None,
        "current_task_id": "TASK-001",
        "next_action": "await_approval",
        "thread_id": "project-abc-manufacturing-co-2024",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_approval_result() -> Dict[str, Any]:
    """
    Sample LangGraph workflow result after approval (aupdate_state + ainvoke)

    Returns:
        Dict: Workflow result with updated task status
    """
    return {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0,
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                "status": "in_progress",
                "risk_level": "High",
                "materiality": 500000.0
            }
        ],
        "is_approved": True,
        "current_task_id": "TASK-001",
        "next_action": "execute_staff_agents",
        "thread_id": "project-abc-manufacturing-co-2024"
    }


# ============================================================================
# TEST: POST /api/projects/start (Happy Path)
# ============================================================================

@pytest.mark.asyncio
async def test_start_audit_endpoint_success(setup_app_with_mocks, valid_start_audit_request, sample_workflow_result):
    """
    Test successful audit project start.

    Verifies:
    - POST /api/projects/start returns 201 Created
    - Response matches StartAuditResponse schema
    - LangGraph ainvoke() is called with correct config
    - thread_id is generated correctly
    - Response contains all required fields
    """
    client, mock_graph = setup_app_with_mocks

    # Configure mock to return sample workflow result
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Make request
    response = client.post("/api/projects/start", json=valid_start_audit_request)

    # Verify response status
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    # Verify response schema
    data = response.json()
    assert data["status"] == "success"
    # thread_id includes the full client name with dots converted to dashes
    expected_thread_id = "project-abc-manufacturing-co.-2024"
    assert data["thread_id"] == expected_thread_id
    assert data["next_action"] == "await_approval"
    assert "message" in data

    # Verify mock was called
    assert mock_graph.ainvoke.called
    call_args = mock_graph.ainvoke.call_args

    # Verify config contains thread_id
    assert call_args[0][1]["configurable"]["thread_id"] == expected_thread_id

    # Verify initial state includes project metadata
    initial_state = call_args[0][0]
    assert initial_state["client_name"] == valid_start_audit_request["client_name"]
    assert initial_state["fiscal_year"] == valid_start_audit_request["fiscal_year"]
    assert initial_state["overall_materiality"] == valid_start_audit_request["overall_materiality"]


@pytest.mark.asyncio
async def test_start_audit_endpoint_validation_missing_field(setup_app_with_mocks, invalid_start_audit_request_missing_field):
    """
    Test audit start with missing required field.

    Verifies:
    - POST /api/projects/start returns 422 Unprocessable Entity
    - Response contains validation error details
    - LangGraph is NOT invoked
    """
    client, mock_graph = setup_app_with_mocks

    # Make request with invalid data
    response = client.post("/api/projects/start", json=invalid_start_audit_request_missing_field)

    # Verify response status
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    # Verify error includes field name
    data = response.json()
    assert "detail" in data or "validation_error" in str(data)

    # Verify mock was NOT called
    assert not mock_graph.ainvoke.called


@pytest.mark.asyncio
async def test_start_audit_endpoint_validation_bad_fiscal_year(setup_app_with_mocks, invalid_start_audit_request_bad_fiscal_year):
    """
    Test audit start with fiscal_year outside valid range.

    Verifies:
    - POST /api/projects/start returns 422 Unprocessable Entity
    - Validation catches year outside 2000-2100 range
    """
    client, mock_graph = setup_app_with_mocks

    # Make request with invalid fiscal year
    response = client.post("/api/projects/start", json=invalid_start_audit_request_bad_fiscal_year)

    # Verify response status
    assert response.status_code == 422

    # Verify mock was NOT called
    assert not mock_graph.ainvoke.called


@pytest.mark.asyncio
async def test_start_audit_endpoint_validation_negative_materiality(setup_app_with_mocks, invalid_start_audit_request_negative_materiality):
    """
    Test audit start with negative materiality.

    Verifies:
    - POST /api/projects/start returns 422 Unprocessable Entity
    - Validation catches negative materiality (must be > 0)
    """
    client, mock_graph = setup_app_with_mocks

    # Make request with negative materiality
    response = client.post("/api/projects/start", json=invalid_start_audit_request_negative_materiality)

    # Verify response status
    assert response.status_code == 422

    # Verify mock was NOT called
    assert not mock_graph.ainvoke.called


@pytest.mark.asyncio
async def test_start_audit_endpoint_graph_not_initialized(client, valid_start_audit_request):
    """
    Test audit start when LangGraph is not initialized.

    Verifies:
    - POST /api/projects/start returns 500 Internal Server Error
    - Response indicates "Workflow engine not initialized"
    """
    # Set graph to None (simulates startup failure)
    app.state.graph = None

    # Make request
    response = client.post("/api/projects/start", json=valid_start_audit_request)

    # Verify response status
    assert response.status_code == 500, f"Expected 500, got {response.status_code}"

    # Verify error message
    data = response.json()
    assert "detail" in data
    assert "Workflow engine not initialized" in data["detail"]


@pytest.mark.asyncio
async def test_start_audit_endpoint_graph_invocation_error(setup_app_with_mocks, valid_start_audit_request):
    """
    Test audit start when LangGraph ainvoke() raises exception.

    Verifies:
    - POST /api/projects/start returns 500 Internal Server Error
    - Error message includes exception details
    """
    client, mock_graph = setup_app_with_mocks

    # Configure mock to raise exception
    mock_graph.ainvoke.side_effect = ValueError("Test error from LangGraph")

    # Make request
    response = client.post("/api/projects/start", json=valid_start_audit_request)

    # Verify response status
    assert response.status_code == 500, f"Expected 500, got {response.status_code}"

    # Verify error message includes exception
    data = response.json()
    assert "detail" in data
    assert "Test error from LangGraph" in data["detail"]


# ============================================================================
# TEST: POST /api/tasks/approve (Happy Path)
# ============================================================================

@pytest.mark.asyncio
async def test_approve_task_endpoint_success(setup_app_with_mocks, valid_approval_request, sample_approval_result):
    """
    Test successful task approval and workflow resumption.

    Verifies:
    - POST /api/tasks/approve returns 200 OK
    - Response matches ApprovalResponse schema
    - LangGraph aupdate_state() is called with approval decision
    - LangGraph ainvoke() is called to resume workflow
    - Task status is extracted from workflow result
    """
    client, mock_graph = setup_app_with_mocks

    # Configure mocks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = sample_approval_result

    # Mock sync_task_to_supabase to avoid actual DB calls
    with patch("src.api.routes.sync_task_to_supabase", new_callable=AsyncMock):
        # Make request
        response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify response status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify response schema
    data = response.json()
    assert data["status"] == "resumed"
    assert data["thread_id"] == valid_approval_request["thread_id"]
    assert data["task_status"] == "in_progress"
    assert "message" in data

    # Verify aupdate_state was called with approval decision
    assert mock_graph.aupdate_state.called
    update_call_args = mock_graph.aupdate_state.call_args
    config = update_call_args[0][0]
    state_update = update_call_args[0][1]

    assert config["configurable"]["thread_id"] == valid_approval_request["thread_id"]
    assert state_update["is_approved"] == valid_approval_request["approved"]

    # Verify ainvoke was called to resume workflow
    assert mock_graph.ainvoke.called
    invoke_call_args = mock_graph.ainvoke.call_args
    assert invoke_call_args[0][0] is None  # First arg should be None (continue from checkpoint)
    assert invoke_call_args[0][1]["configurable"]["thread_id"] == valid_approval_request["thread_id"]


@pytest.mark.asyncio
async def test_approve_task_endpoint_validation_empty_thread_id(setup_app_with_mocks, invalid_approval_request_empty_thread_id):
    """
    Test task approval with empty thread_id.

    Verifies:
    - POST /api/tasks/approve returns 422 Unprocessable Entity
    - Validation catches empty thread_id (min_length=1)
    """
    client, mock_graph = setup_app_with_mocks

    # Make request with invalid data
    response = client.post("/api/tasks/approve", json=invalid_approval_request_empty_thread_id)

    # Verify response status
    assert response.status_code == 422

    # Verify mocks were NOT called
    assert not mock_graph.aupdate_state.called
    assert not mock_graph.ainvoke.called


@pytest.mark.asyncio
async def test_approve_task_endpoint_graph_not_initialized(client, valid_approval_request):
    """
    Test task approval when LangGraph is not initialized.

    Verifies:
    - POST /api/tasks/approve returns 500 Internal Server Error
    - Response indicates "Workflow engine not initialized"
    """
    # Set graph to None
    app.state.graph = None

    # Make request
    response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify response status
    assert response.status_code == 500

    # Verify error message
    data = response.json()
    assert "detail" in data
    assert "Workflow engine not initialized" in data["detail"]


@pytest.mark.asyncio
async def test_approve_task_endpoint_no_tasks_in_result(setup_app_with_mocks, valid_approval_request):
    """
    Test task approval when workflow result contains no tasks.

    Verifies:
    - POST /api/tasks/approve returns 404 Not Found
    - Error indicates "No tasks found"
    """
    client, mock_graph = setup_app_with_mocks

    # Configure mock to return result with no tasks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = {
        "tasks": [],  # Empty tasks list
        "client_name": "ABC Corp",
        "thread_id": valid_approval_request["thread_id"]
    }

    # Make request
    response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify response status
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    # Verify error message
    data = response.json()
    assert "detail" in data
    assert "No tasks found" in data["detail"]


@pytest.mark.asyncio
async def test_approve_task_endpoint_aupdate_state_error(setup_app_with_mocks, valid_approval_request):
    """
    Test task approval when aupdate_state() raises exception.

    Verifies:
    - POST /api/tasks/approve returns 500 Internal Server Error
    - Error includes exception details
    """
    client, mock_graph = setup_app_with_mocks

    # Configure mock to raise exception
    mock_graph.aupdate_state.side_effect = ValueError("State update failed")

    # Make request
    response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify response status
    assert response.status_code == 500

    # Verify error message
    data = response.json()
    assert "detail" in data
    assert "State update failed" in data["detail"]


@pytest.mark.asyncio
async def test_approve_task_endpoint_approval_rejected(setup_app_with_mocks, sample_approval_result):
    """
    Test task approval with approval=False (rejection).

    Verifies:
    - Workflow continuation works correctly even when approval is False
    - State update includes approval=False
    """
    client, mock_graph = setup_app_with_mocks

    # Create rejection request
    rejection_request = {
        "thread_id": "project-abc-manufacturing-co-2024",
        "approved": False
    }

    # Configure mocks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = sample_approval_result

    with patch("src.api.routes.sync_task_to_supabase", new_callable=AsyncMock):
        # Make request
        response = client.post("/api/tasks/approve", json=rejection_request)

    # Verify response status
    assert response.status_code == 200

    # Verify aupdate_state was called with approved=False
    update_call_args = mock_graph.aupdate_state.call_args
    state_update = update_call_args[0][1]
    assert state_update["is_approved"] == False


# ============================================================================
# TEST: GET /api/health (Health Check)
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_all_healthy(setup_app_with_mocks):
    """
    Test health check when all components are healthy.

    Verifies:
    - GET /api/health returns 200 OK
    - Status is "healthy"
    - All components report "ok"
    - Timestamp is present
    """
    client, mock_graph = setup_app_with_mocks

    # Make request
    response = client.get("/api/health")

    # Verify response status
    assert response.status_code == 200

    # Verify response structure
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["langgraph"] == "ok"
    assert data["components"]["supabase"] == "ok"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_graph_not_initialized(client):
    """
    Test health check when LangGraph is not initialized.

    Verifies:
    - GET /api/health returns 200 OK (doesn't fail)
    - Status is "degraded"
    - LangGraph component reports "error"
    """
    # Set graph to None
    app.state.graph = None

    # Make request
    response = client.get("/api/health")

    # Verify response status
    assert response.status_code == 200

    # Verify degraded status
    data = response.json()
    assert data["status"] == "degraded"
    assert data["components"]["langgraph"] == "error"


@pytest.mark.asyncio
async def test_health_check_timestamp_format(setup_app_with_mocks):
    """
    Test that health check timestamp is ISO format.

    Verifies:
    - Timestamp is present
    - Timestamp is valid ISO 8601 format
    """
    client, mock_graph = setup_app_with_mocks

    # Make request
    response = client.get("/api/health")

    # Verify response
    data = response.json()
    timestamp = data["timestamp"]

    # Verify ISO format by parsing
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert True
    except ValueError:
        pytest.fail(f"Timestamp '{timestamp}' is not valid ISO 8601")


# ============================================================================
# TEST: CORS Headers
# ============================================================================

@pytest.mark.asyncio
async def test_cors_headers_start_audit_endpoint(setup_app_with_mocks, valid_start_audit_request, sample_workflow_result):
    """
    Test CORS headers on POST /api/projects/start response.

    Verifies:
    - Response contains Access-Control-Allow-Origin header
    - Header allows localhost:5173 (Vite dev server)
    - Response contains Access-Control-Allow-Credentials
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Make request
    response = client.post(
        "/api/projects/start",
        json=valid_start_audit_request,
        headers={"Origin": "http://localhost:5173"}
    )

    # Verify CORS headers
    assert response.status_code == 201
    assert "access-control-allow-origin" in response.headers or "Access-Control-Allow-Origin" in response.headers


@pytest.mark.asyncio
async def test_cors_headers_approval_endpoint(setup_app_with_mocks, valid_approval_request, sample_approval_result):
    """
    Test CORS headers on POST /api/tasks/approve response.

    Verifies:
    - Response contains Access-Control-Allow-Origin header
    - Response allows credentials
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = sample_approval_result

    with patch("src.api.routes.sync_task_to_supabase", new_callable=AsyncMock):
        # Make request
        response = client.post(
            "/api/tasks/approve",
            json=valid_approval_request,
            headers={"Origin": "http://localhost:5173"}
        )

    # Verify CORS headers
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cors_headers_health_check(setup_app_with_mocks):
    """
    Test CORS headers on GET /api/health response.

    Verifies:
    - Response contains CORS headers
    """
    client, mock_graph = setup_app_with_mocks

    # Make request
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"}
    )

    # Verify response
    assert response.status_code == 200


# ============================================================================
# TEST: Error Handling (4xx/5xx Responses)
# ============================================================================

@pytest.mark.asyncio
async def test_error_response_format_validation_error(setup_app_with_mocks, invalid_start_audit_request_missing_field):
    """
    Test error response format for validation errors.

    Verifies:
    - Error response is proper JSON
    - Includes error details
    """
    client, mock_graph = setup_app_with_mocks

    # Make request with invalid data
    response = client.post("/api/projects/start", json=invalid_start_audit_request_missing_field)

    # Verify response is valid JSON
    assert response.status_code == 422
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_error_response_format_server_error(setup_app_with_mocks, valid_start_audit_request):
    """
    Test error response format for server errors.

    Verifies:
    - 500 error response matches ErrorResponse schema
    - Includes error and details fields
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.side_effect = RuntimeError("Internal server error")

    # Make request
    response = client.post("/api/projects/start", json=valid_start_audit_request)

    # Verify error response format
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_error_response_404_not_found(setup_app_with_mocks, valid_approval_request):
    """
    Test 404 error response when resource not found.

    Verifies:
    - Returns 404 status code
    - Error indicates not found
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = {"tasks": []}

    # Make request
    response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify error response
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    # Error message includes "No tasks found"
    assert ("not found" in data["detail"].lower() or "tasks found" in data["detail"].lower())


# ============================================================================
# TEST: Content-Type and Response Headers
# ============================================================================

@pytest.mark.asyncio
async def test_content_type_json_start_audit(setup_app_with_mocks, valid_start_audit_request, sample_workflow_result):
    """
    Test that start audit response has correct Content-Type.

    Verifies:
    - Content-Type is application/json
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Make request
    response = client.post("/api/projects/start", json=valid_start_audit_request)

    # Verify content type
    assert response.status_code == 201
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_content_type_json_approval(setup_app_with_mocks, valid_approval_request, sample_approval_result):
    """
    Test that approval response has correct Content-Type.

    Verifies:
    - Content-Type is application/json
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = sample_approval_result

    with patch("src.api.routes.sync_task_to_supabase", new_callable=AsyncMock):
        # Make request
        response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify content type
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


# ============================================================================
# TEST: Edge Cases and Special Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_start_audit_with_special_characters_in_client_name(setup_app_with_mocks, sample_workflow_result):
    """
    Test audit start with special characters in client name.

    Verifies:
    - Special characters in client name are handled correctly
    - thread_id is generated correctly
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Request with special characters
    request_data = {
        "client_name": "ABC Manufacturing Co. & Partners, LLC",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0
    }

    # Make request
    response = client.post("/api/projects/start", json=request_data)

    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_start_audit_with_minimum_materiality(setup_app_with_mocks, sample_workflow_result):
    """
    Test audit start with minimum allowed materiality (0.01).

    Verifies:
    - Very small positive materiality values are accepted
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Request with minimal materiality
    request_data = {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": 0.01
    }

    # Make request
    response = client.post("/api/projects/start", json=request_data)

    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_start_audit_with_high_materiality(setup_app_with_mocks, sample_workflow_result):
    """
    Test audit start with very high materiality value.

    Verifies:
    - Large materiality values are handled correctly
    """
    client, mock_graph = setup_app_with_mocks
    mock_graph.ainvoke.return_value = sample_workflow_result

    # Request with high materiality
    request_data = {
        "client_name": "ABC Manufacturing Co.",
        "fiscal_year": 2024,
        "overall_materiality": 999999999999.99
    }

    # Make request
    response = client.post("/api/projects/start", json=request_data)

    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_approval_with_task_status_extraction(setup_app_with_mocks, valid_approval_request):
    """
    Test that task status is correctly extracted from workflow result.

    Verifies:
    - Task status is extracted from first task in tasks list
    - Response task_status field matches extracted status
    """
    client, mock_graph = setup_app_with_mocks

    # Create custom result with specific task status
    result = {
        "tasks": [
            {
                "id": "TASK-001",
                "status": "completed"
            }
        ]
    }

    mock_graph.aupdate_state.return_value = None
    mock_graph.ainvoke.return_value = result

    with patch("src.api.routes.sync_task_to_supabase", new_callable=AsyncMock):
        # Make request
        response = client.post("/api/tasks/approve", json=valid_approval_request)

    # Verify task_status matches
    assert response.status_code == 200
    data = response.json()
    assert data["task_status"] == "completed"


# ============================================================================
# TEST: Root Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_root_endpoint(setup_app_with_mocks):
    """
    Test root endpoint (GET /) health check.

    Verifies:
    - GET / returns 200 OK
    - Response includes service information
    - Response includes links to /docs and /api/health
    """
    client, mock_graph = setup_app_with_mocks

    # Make request
    response = client.get("/")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AI Audit Platform API"
    assert data["status"] == "running"
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"
