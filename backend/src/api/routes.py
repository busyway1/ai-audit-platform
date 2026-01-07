"""
REST API Routes for Audit Workflow Operations

This module provides FastAPI endpoints for managing audit projects and task approvals.
Endpoints integrate with LangGraph state machine and Supabase for data persistence.

Key endpoints:
- POST /api/projects/start: Initiate new audit project
- POST /api/tasks/approve: Resume workflow with user approval decision
"""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..db.supabase_client import supabase
from ..services.task_sync import sync_task_to_supabase, get_task_by_thread_id

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["audit-workflow"])


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================

class StartAuditRequest(BaseModel):
    """
    Request schema for starting a new audit project.

    Attributes:
        client_name: Name of the client being audited
        fiscal_year: Fiscal year for the audit (e.g., 2024)
        overall_materiality: Materiality threshold in currency units
    """
    client_name: str = Field(..., min_length=1, description="Client name (required)")
    fiscal_year: int = Field(..., ge=2000, le=2100, description="Fiscal year (2000-2100)")
    overall_materiality: float = Field(..., gt=0, description="Materiality threshold (must be positive)")


class ApprovalRequest(BaseModel):
    """
    Request schema for task approval.

    Attributes:
        thread_id: LangGraph thread identifier for the workflow
        approved: Boolean indicating user approval decision
    """
    thread_id: str = Field(..., min_length=1, description="Thread ID (required)")
    approved: bool = Field(..., description="Approval decision")


class StartAuditResponse(BaseModel):
    """Response schema for successful audit start."""
    status: str = "success"
    thread_id: str
    next_action: str
    message: str


class ApprovalResponse(BaseModel):
    """Response schema for successful task approval."""
    status: str = "resumed"
    thread_id: str
    task_status: str
    message: str


class ErrorResponse(BaseModel):
    """Response schema for error cases."""
    status: str = "error"
    error: str
    details: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/projects/start",
    response_model=StartAuditResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Audit project successfully created"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def start_audit(
    request_data: StartAuditRequest,
    request: Request
) -> StartAuditResponse:
    """
    Start a new audit project and invoke the Partner agent.

    This endpoint:
    1. Validates input parameters
    2. Creates initial AuditState with project metadata
    3. Generates unique thread_id for workflow tracking
    4. Invokes LangGraph workflow (Partner agent node)
    5. Returns next action for frontend to handle

    Args:
        request_data: Audit project parameters (client, year, materiality)
        request: FastAPI request object (provides access to app.state.graph)

    Returns:
        StartAuditResponse with thread_id and next_action

    Raises:
        HTTPException: If graph is not initialized or invocation fails
    """
    try:
        # Access LangGraph instance from app state
        graph = request.app.state.graph
        if graph is None:
            logger.error("LangGraph instance not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow engine not initialized"
            )

        # Generate unique thread ID for this audit project
        thread_id = f"project-{request_data.client_name.lower().replace(' ', '-')}-{request_data.fiscal_year}"
        logger.info(f"Starting audit project with thread_id: {thread_id}")

        # Create LangGraph configuration with thread ID
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # Initialize AuditState with project metadata
        initial_state = {
            "client_name": request_data.client_name,
            "fiscal_year": request_data.fiscal_year,
            "overall_materiality": request_data.overall_materiality,
            "tasks": [],  # Will be populated by Partner agent
            "is_approved": None,  # Pending user approval
            "current_task_id": None,
            "thread_id": thread_id,
            "created_at": datetime.utcnow().isoformat()
        }

        # Invoke LangGraph workflow (starts with Partner agent)
        logger.info(f"Invoking LangGraph workflow for {thread_id}")
        result = await graph.ainvoke(initial_state, config)

        # Extract next action from result
        next_action = result.get("next_action", "await_approval")
        logger.info(f"Workflow invoked successfully. Next action: {next_action}")

        return StartAuditResponse(
            status="success",
            thread_id=thread_id,
            next_action=next_action,
            message=f"Audit project created for {request_data.client_name} (FY{request_data.fiscal_year})"
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(f"Failed to start audit project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start audit project: {str(e)}"
        )


@router.post(
    "/tasks/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Task approval processed and workflow resumed"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        404: {"model": ErrorResponse, "description": "Thread or task not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def approve_task(
    request_data: ApprovalRequest,
    request: Request
) -> ApprovalResponse:
    """
    Process user approval decision and resume workflow.

    This endpoint:
    1. Validates thread_id exists in LangGraph state
    2. Updates state with approval decision (is_approved field)
    3. Resumes workflow execution (LangGraph continues from checkpoint)
    4. Syncs updated task status to Supabase
    5. Returns current task status to frontend

    Args:
        request_data: Approval decision with thread_id
        request: FastAPI request object (provides access to app.state.graph)

    Returns:
        ApprovalResponse with updated task status

    Raises:
        HTTPException: If thread not found or workflow update fails
    """
    try:
        # Access LangGraph instance from app state
        graph = request.app.state.graph
        if graph is None:
            logger.error("LangGraph instance not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow engine not initialized"
            )

        thread_id = request_data.thread_id
        logger.info(f"Processing approval for thread_id: {thread_id} (approved={request_data.approved})")

        # Create LangGraph configuration
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # Update state with approval decision
        # This sets is_approved field, allowing workflow to continue
        logger.info(f"Updating state with approval decision: {request_data.approved}")
        await graph.aupdate_state(
            config,
            {"is_approved": request_data.approved}
        )

        # Resume workflow execution from checkpoint
        # LangGraph will continue from where it left off (likely Auditor agent)
        logger.info(f"Resuming workflow for {thread_id}")
        result = await graph.ainvoke(None, config)  # None = continue from checkpoint

        # Extract task information from result
        tasks = result.get("tasks", [])
        if not tasks:
            logger.warning(f"No tasks found in workflow result for {thread_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No tasks found for thread {thread_id}"
            )

        # Get current task (first task in list)
        current_task = tasks[0]
        task_status = current_task.get("status", "unknown")

        # Sync task status to Supabase for persistence
        # Get project_id from result state
        project_id = result.get("project_id", "")
        logger.info(f"Syncing task to Supabase: {current_task.get('id', 'unknown')} (project: {project_id})")
        await sync_task_to_supabase(current_task, project_id)

        logger.info(f"Workflow resumed successfully. Task status: {task_status}")

        return ApprovalResponse(
            status="resumed",
            thread_id=thread_id,
            task_status=task_status,
            message=f"Task approval processed. Workflow resumed with status: {task_status}"
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(f"Failed to process task approval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process task approval: {str(e)}"
        )


# ============================================================================
# Health Check Endpoint (Optional but Recommended)
# ============================================================================

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Service is healthy"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    }
)
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint for monitoring service availability.

    Checks:
    - LangGraph instance is initialized
    - Supabase client is accessible

    Returns:
        Health status with component checks
    """
    try:
        # Check LangGraph initialization
        graph_healthy = request.app.state.graph is not None

        # Check Supabase connectivity (simple check - could be enhanced)
        supabase_healthy = supabase is not None

        overall_healthy = graph_healthy and supabase_healthy

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "components": {
                "langgraph": "ok" if graph_healthy else "error",
                "supabase": "ok" if supabase_healthy else "error"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )
