"""
HITL (Human-in-the-Loop) API Routes

This module provides FastAPI endpoints for managing HITL queue and requests.

Endpoints (BE-15.3):
- GET /api/hitl/pending: List all pending HITL requests
- GET /api/hitl: List all HITL requests with filtering
- GET /api/hitl/{id}: Get specific HITL request details
- POST /api/hitl/{id}/respond: Submit response (approve/reject/escalate)
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ...db.supabase_client import supabase
from .schemas import (
    HITLRequestResponse,
    HITLListResponse,
    HITLDetailResponse,
    HITLRespondRequest,
    HITLRespondResponse,
    HITLRequestTypeEnum,
    HITLRequestStatusEnum,
    HITLUrgencyLevelEnum,
    ErrorResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["hitl"])


# ============================================================================
# Helper Functions
# ============================================================================

def _convert_hitl_row_to_response(row: Dict[str, Any]) -> HITLRequestResponse:
    """
    Convert a Supabase row to HITLRequestResponse.

    Handles field name mapping and type conversion.
    """
    return HITLRequestResponse(
        id=str(row.get("id", "")),
        task_id=str(row.get("task_id", "")),
        project_id=str(row.get("project_id", "")),
        request_type=row.get("request_type", "urgency_threshold"),
        urgency_score=float(row.get("urgency_score", 0)),
        urgency_level=row.get("urgency_level", "medium"),
        title=row.get("title", ""),
        description=row.get("description", ""),
        context=row.get("context"),
        status=row.get("status", "pending"),
        response=row.get("response"),
        responded_by=row.get("responded_by"),
        responded_at=row.get("responded_at"),
        created_at=row.get("created_at", datetime.utcnow().isoformat()),
        updated_at=row.get("updated_at")
    )


def _get_hitl_summary(requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for HITL requests.

    Args:
        requests: List of HITL request dictionaries

    Returns:
        Summary with counts by status, urgency level, and type
    """
    if not requests:
        return {
            "by_status": {},
            "by_urgency_level": {},
            "by_type": {},
            "average_urgency_score": 0,
            "highest_urgency_score": 0
        }

    # Count by status
    by_status: Dict[str, int] = {}
    for req in requests:
        req_status = req.get("status", "pending")
        by_status[req_status] = by_status.get(req_status, 0) + 1

    # Count by urgency level
    by_urgency_level: Dict[str, int] = {}
    for req in requests:
        level = req.get("urgency_level", "medium")
        by_urgency_level[level] = by_urgency_level.get(level, 0) + 1

    # Count by type
    by_type: Dict[str, int] = {}
    for req in requests:
        req_type = req.get("request_type", "urgency_threshold")
        by_type[req_type] = by_type.get(req_type, 0) + 1

    # Calculate urgency statistics
    urgency_scores = [float(req.get("urgency_score", 0)) for req in requests]
    avg_score = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0
    max_score = max(urgency_scores) if urgency_scores else 0

    return {
        "by_status": by_status,
        "by_urgency_level": by_urgency_level,
        "by_type": by_type,
        "average_urgency_score": round(avg_score, 2),
        "highest_urgency_score": round(max_score, 2)
    }


# ============================================================================
# HITL List Endpoints
# ============================================================================

@router.get(
    "/hitl/pending",
    response_model=HITLListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Pending HITL requests retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def list_pending_hitl_requests(
    project_id: Optional[str] = None,
    urgency_level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    include_summary: bool = True
) -> HITLListResponse:
    """
    List all pending HITL requests.

    Retrieves pending HITL requests from Supabase, sorted by urgency score (highest first).

    Args:
        project_id: Optional filter by project ID
        urgency_level: Optional filter by urgency level (critical, high, medium, low)
        limit: Maximum number of requests to return (default: 100)
        offset: Number of requests to skip for pagination (default: 0)
        include_summary: Include summary statistics (default: True)

    Returns:
        HITLListResponse with list of pending requests and optional summary
    """
    try:
        logger.info(f"Listing pending HITL requests (project={project_id}, urgency={urgency_level})")

        # Build query for pending requests only
        query = supabase.table("hitl_requests").select("*", count="exact").eq("status", "pending")

        # Apply filters
        if project_id:
            query = query.eq("project_id", project_id)

        if urgency_level:
            valid_levels = [level.value for level in HITLUrgencyLevelEnum]
            if urgency_level not in valid_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid urgency_level. Valid values: {valid_levels}"
                )
            query = query.eq("urgency_level", urgency_level)

        # Sort by urgency score (highest first), then by created_at
        query = query.order("urgency_score", desc=True).order("created_at", desc=False)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        # Execute query
        result = query.execute()

        requests = [_convert_hitl_row_to_response(row) for row in (result.data or [])]
        total = result.count if result.count is not None else len(requests)

        # Build summary if requested
        summary = None
        if include_summary and result.data:
            summary = _get_hitl_summary(result.data)

        logger.info(f"Retrieved {len(requests)} pending HITL requests (total: {total})")

        return HITLListResponse(
            status="success",
            requests=requests,
            total=total,
            summary=summary
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list pending HITL requests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pending HITL requests: {str(e)}"
        )


@router.get(
    "/hitl",
    response_model=HITLListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "HITL requests retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def list_hitl_requests(
    project_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    request_type: Optional[str] = None,
    urgency_level: Optional[str] = None,
    sort_by: str = "urgency_score",
    descending: bool = True,
    limit: int = 100,
    offset: int = 0,
    include_summary: bool = True
) -> HITLListResponse:
    """
    List all HITL requests with filtering options.

    Retrieves HITL requests from Supabase with optional filtering and sorting.

    Args:
        project_id: Optional filter by project ID
        status_filter: Optional filter by status (pending, approved, rejected, escalated, expired)
        request_type: Optional filter by request type
        urgency_level: Optional filter by urgency level (critical, high, medium, low)
        sort_by: Field to sort by (urgency_score, created_at, status)
        descending: Sort in descending order (default: True)
        limit: Maximum number of requests to return (default: 100)
        offset: Number of requests to skip for pagination (default: 0)
        include_summary: Include summary statistics (default: True)

    Returns:
        HITLListResponse with list of requests and optional summary
    """
    try:
        logger.info(f"Listing HITL requests (status={status_filter}, type={request_type})")

        # Build query
        query = supabase.table("hitl_requests").select("*", count="exact")

        # Apply filters
        if project_id:
            query = query.eq("project_id", project_id)

        if status_filter:
            valid_statuses = [s.value for s in HITLRequestStatusEnum]
            if status_filter not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status_filter. Valid values: {valid_statuses}"
                )
            query = query.eq("status", status_filter)

        if request_type:
            valid_types = [t.value for t in HITLRequestTypeEnum]
            if request_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request_type. Valid values: {valid_types}"
                )
            query = query.eq("request_type", request_type)

        if urgency_level:
            valid_levels = [level.value for level in HITLUrgencyLevelEnum]
            if urgency_level not in valid_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid urgency_level. Valid values: {valid_levels}"
                )
            query = query.eq("urgency_level", urgency_level)

        # Apply sorting
        valid_sort_fields = ["urgency_score", "created_at", "status", "urgency_level"]
        if sort_by not in valid_sort_fields:
            sort_by = "urgency_score"

        query = query.order(sort_by, desc=descending)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        # Execute query
        result = query.execute()

        requests = [_convert_hitl_row_to_response(row) for row in (result.data or [])]
        total = result.count if result.count is not None else len(requests)

        # Build summary if requested
        summary = None
        if include_summary and result.data:
            summary = _get_hitl_summary(result.data)

        logger.info(f"Retrieved {len(requests)} HITL requests (total: {total})")

        return HITLListResponse(
            status="success",
            requests=requests,
            total=total,
            summary=summary
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list HITL requests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list HITL requests: {str(e)}"
        )


# ============================================================================
# HITL Detail and Response Endpoints
# ============================================================================

@router.get(
    "/hitl/{request_id}",
    response_model=HITLDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "HITL request retrieved successfully"},
        404: {"model": ErrorResponse, "description": "HITL request not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def get_hitl_request(request_id: str) -> HITLDetailResponse:
    """
    Get a specific HITL request by ID.

    Args:
        request_id: ID of the HITL request

    Returns:
        HITLDetailResponse with request details
    """
    try:
        logger.info(f"Getting HITL request: {request_id}")

        # Query Supabase for the request
        result = supabase.table("hitl_requests").select("*").eq("id", request_id).execute()

        if not result.data:
            logger.warning(f"HITL request not found: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HITL request not found: {request_id}"
            )

        hitl_request = result.data[0]
        logger.info(f"HITL request retrieved: {request_id}")

        return HITLDetailResponse(
            status="success",
            request=_convert_hitl_row_to_response(hitl_request)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get HITL request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get HITL request: {str(e)}"
        )


@router.post(
    "/hitl/{request_id}/respond",
    response_model=HITLRespondResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Response submitted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        404: {"model": ErrorResponse, "description": "HITL request not found"},
        409: {"model": ErrorResponse, "description": "Request already processed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def respond_to_hitl_request(
    request_id: str,
    request_data: HITLRespondRequest,
    request: Request
) -> HITLRespondResponse:
    """
    Submit a response to an HITL request.

    This endpoint:
    1. Validates the HITL request exists and is pending
    2. Records the response (approve/reject/escalate)
    3. Updates the task status based on the response
    4. Resumes the LangGraph workflow with the response

    Args:
        request_id: ID of the HITL request
        request_data: Response details (action, comment, modified_values)
        request: FastAPI request object (provides access to app.state.graph)

    Returns:
        HITLRespondResponse with submission status and workflow state
    """
    try:
        logger.info(f"Processing HITL response for request: {request_id} (action={request_data.action})")

        # Get the HITL request
        hitl_result = supabase.table("hitl_requests").select("*").eq("id", request_id).execute()

        if not hitl_result.data:
            logger.warning(f"HITL request not found: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HITL request not found: {request_id}"
            )

        hitl_request = hitl_result.data[0]

        # Check if request is still pending
        if hitl_request.get("status") != "pending":
            logger.warning(f"HITL request already processed: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"HITL request has already been processed (status: {hitl_request.get('status')})"
            )

        # Map action to status
        action_to_status = {
            "approve": HITLRequestStatusEnum.APPROVED.value,
            "reject": HITLRequestStatusEnum.REJECTED.value,
            "escalate": HITLRequestStatusEnum.ESCALATED.value
        }

        new_status = action_to_status.get(request_data.action, HITLRequestStatusEnum.PENDING.value)

        # Update HITL request in database
        update_data = {
            "status": new_status,
            "response": {
                "action": request_data.action,
                "comment": request_data.comment,
                "modified_values": request_data.modified_values
            },
            "responded_by": request_data.responded_by,
            "responded_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        update_result = supabase.table("hitl_requests").update(update_data).eq("id", request_id).execute()

        if not update_result.data:
            logger.error(f"Failed to update HITL request: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update HITL request in database"
            )

        logger.info(f"HITL request updated: {request_id} -> {new_status}")

        # Update the associated task status
        task_id = hitl_request.get("task_id")
        task_status = None

        if task_id:
            task_update = {
                "hitl_status": new_status,
                "hitl_comment": request_data.comment,
                "updated_at": datetime.utcnow().isoformat()
            }

            # If rejected, also set task status to skipped
            if request_data.action == "reject":
                task_update["status"] = "skipped"
                task_status = "skipped"
            elif request_data.action == "approve":
                task_status = "hitl_approved"

            try:
                supabase.table("audit_tasks").update(task_update).eq("id", task_id).execute()
                logger.info(f"Task {task_id} updated with HITL response")
            except Exception as task_error:
                logger.warning(f"Failed to update task {task_id}: {task_error}")

        # Resume LangGraph workflow if available
        workflow_resumed = False

        try:
            graph = request.app.state.graph
            if graph is not None:
                thread_id = hitl_request.get("thread_id")

                if thread_id:
                    config = {"configurable": {"thread_id": thread_id}}

                    # Update graph state with HITL response
                    await graph.aupdate_state(
                        config,
                        {
                            "hitl_response": {
                                "request_id": request_id,
                                "action": request_data.action,
                                "comment": request_data.comment,
                                "modified_values": request_data.modified_values
                            }
                        }
                    )

                    # Resume workflow
                    await graph.ainvoke(None, config)
                    workflow_resumed = True
                    logger.info(f"Workflow resumed for thread: {thread_id}")
                else:
                    logger.info("No thread_id found, skipping workflow resume")
            else:
                logger.info("Graph not available, skipping workflow resume")
        except Exception as graph_error:
            logger.warning(f"Failed to resume workflow: {graph_error}")
            # Don't fail the request if workflow resume fails

        return HITLRespondResponse(
            status="success",
            request_id=request_id,
            action=request_data.action,
            workflow_resumed=workflow_resumed,
            task_status=task_status,
            message=f"HITL request {request_data.action}d successfully"
            + (" and workflow resumed" if workflow_resumed else "")
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to process HITL response: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process HITL response: {str(e)}"
        )
