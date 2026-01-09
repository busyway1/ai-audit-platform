"""
Task API Routes

This module provides FastAPI endpoints for task management and approval.

Endpoints:
- POST /api/tasks/approve: Resume workflow with user approval decision
"""

from fastapi import APIRouter, HTTPException, Request, status
import logging

from ...services.task_sync import sync_task_to_supabase
from .schemas import (
    ApprovalRequest,
    ApprovalResponse,
    ErrorResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["tasks"])


# ============================================================================
# Task Approval Endpoints
# ============================================================================

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
