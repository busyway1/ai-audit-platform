"""
Project API Routes

This module provides FastAPI endpoints for managing audit projects.
Includes both CRUD operations and workflow initiation.

Endpoints:
- POST /api/projects: Create a new project (CRUD operation)
- GET /api/projects: List all projects with optional filtering
- GET /api/projects/{id}: Get project details
- PUT /api/projects/{id}: Update project
- DELETE /api/projects/{id}: Delete project
- POST /api/projects/start: Initiate new audit project with LangGraph workflow
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from ...db.supabase_client import supabase
from .schemas import (
    StartAuditRequest,
    StartAuditResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    ProjectStatus,
    ErrorResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["projects"])


# ============================================================================
# Helper Functions
# ============================================================================

def _convert_project_row_to_response(row: Dict[str, Any]) -> ProjectResponse:
    """
    Convert a Supabase row to ProjectResponse.

    Handles field name mapping and type conversion.
    """
    return ProjectResponse(
        id=str(row.get("id", "")),
        client_name=row.get("client_name", ""),
        fiscal_year=row.get("fiscal_year", 0),
        overall_materiality=row.get("overall_materiality"),
        status=row.get("status", "planning"),
        created_at=row.get("created_at", datetime.utcnow().isoformat()),
        updated_at=row.get("updated_at")
    )


# ============================================================================
# Workflow Endpoints
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


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.post(
    "/projects",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Project successfully created"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_project(request_data: CreateProjectRequest) -> ProjectCreateResponse:
    """
    Create a new audit project.

    This endpoint creates a project record in Supabase without starting
    the LangGraph workflow. Use POST /api/projects/start to create a project
    AND start the audit workflow.

    Args:
        request_data: Project creation parameters

    Returns:
        ProjectCreateResponse with created project details
    """
    try:
        # Generate UUID for the new project
        project_id = str(uuid.uuid4())

        # Prepare project data for Supabase
        project_data = {
            "id": project_id,
            "client_name": request_data.client_name,
            "fiscal_year": request_data.fiscal_year,
            "overall_materiality": request_data.overall_materiality,
            "status": request_data.status.value,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Creating project: {request_data.client_name} (FY{request_data.fiscal_year})")

        # Insert into Supabase
        result = supabase.table("audit_projects").insert(project_data).execute()

        if not result.data:
            logger.error("Failed to create project - no data returned from Supabase")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create project in database"
            )

        created_project = result.data[0]
        logger.info(f"Project created successfully: {project_id}")

        return ProjectCreateResponse(
            status="created",
            project=_convert_project_row_to_response(created_project),
            message=f"Project '{request_data.client_name}' created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Projects retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def list_projects(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> ProjectListResponse:
    """
    List all audit projects.

    Retrieves audit projects from Supabase with optional filtering.

    Args:
        status_filter: Filter by project status (planning, in_progress, review, completed)
        limit: Maximum number of projects to return (default: 100)
        offset: Number of projects to skip for pagination (default: 0)

    Returns:
        ProjectListResponse with list of projects and total count
    """
    try:
        logger.info(f"Listing projects (status={status_filter}, limit={limit}, offset={offset})")

        # Build query
        query = supabase.table("audit_projects").select("*", count="exact")

        # Apply status filter if provided
        if status_filter:
            # Validate status value
            valid_statuses = [s.value for s in ProjectStatus]
            if status_filter not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter. Valid values: {valid_statuses}"
                )
            query = query.eq("status", status_filter)

        # Apply pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        # Execute query
        result = query.execute()

        projects = [_convert_project_row_to_response(row) for row in (result.data or [])]
        total = result.count if result.count is not None else len(projects)

        logger.info(f"Retrieved {len(projects)} projects (total: {total})")

        return ProjectListResponse(
            status="success",
            projects=projects,
            total=total
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get(
    "/projects/{project_id}",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Project retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def get_project(project_id: str) -> ProjectDetailResponse:
    """
    Get a specific audit project by ID.

    Args:
        project_id: UUID of the project to retrieve

    Returns:
        ProjectDetailResponse with project details
    """
    try:
        logger.info(f"Getting project: {project_id}")

        # Query Supabase for the project
        result = supabase.table("audit_projects").select("*").eq("id", project_id).execute()

        if not result.data:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        project = result.data[0]
        logger.info(f"Project retrieved: {project_id}")

        return ProjectDetailResponse(
            status="success",
            project=_convert_project_row_to_response(project)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put(
    "/projects/{project_id}",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Project updated successfully"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def update_project(
    project_id: str,
    request_data: UpdateProjectRequest
) -> ProjectDetailResponse:
    """
    Update an existing audit project.

    Only provided fields will be updated.

    Args:
        project_id: UUID of the project to update
        request_data: Fields to update

    Returns:
        ProjectDetailResponse with updated project details
    """
    try:
        logger.info(f"Updating project: {project_id}")

        # Check if project exists
        existing = supabase.table("audit_projects").select("id").eq("id", project_id).execute()
        if not existing.data:
            logger.warning(f"Project not found for update: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Build update data (only include non-None fields)
        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if request_data.client_name is not None:
            update_data["client_name"] = request_data.client_name
        if request_data.fiscal_year is not None:
            update_data["fiscal_year"] = request_data.fiscal_year
        if request_data.overall_materiality is not None:
            update_data["overall_materiality"] = request_data.overall_materiality
        if request_data.status is not None:
            update_data["status"] = request_data.status.value

        # Update in Supabase
        result = supabase.table("audit_projects").update(update_data).eq("id", project_id).execute()

        if not result.data:
            logger.error(f"Failed to update project - no data returned: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project in database"
            )

        updated_project = result.data[0]
        logger.info(f"Project updated successfully: {project_id}")

        return ProjectDetailResponse(
            status="success",
            project=_convert_project_row_to_response(updated_project)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Project deleted successfully"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def delete_project(project_id: str) -> ProjectDeleteResponse:
    """
    Delete an audit project.

    WARNING: This will permanently delete the project and may affect
    associated EGAs, tasks, and workflow state.

    Args:
        project_id: UUID of the project to delete

    Returns:
        ProjectDeleteResponse confirming deletion
    """
    try:
        logger.info(f"Deleting project: {project_id}")

        # Check if project exists
        existing = supabase.table("audit_projects").select("id, client_name").eq("id", project_id).execute()
        if not existing.data:
            logger.warning(f"Project not found for deletion: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        client_name = existing.data[0].get("client_name", "Unknown")

        # Delete from Supabase
        supabase.table("audit_projects").delete().eq("id", project_id).execute()

        logger.info(f"Project deleted successfully: {project_id}")

        return ProjectDeleteResponse(
            status="deleted",
            project_id=project_id,
            message=f"Project '{client_name}' deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
