"""
REST API Routes for Audit Workflow Operations

This module provides FastAPI endpoints for managing audit projects, EGAs, and task approvals.
Endpoints integrate with LangGraph state machine and Supabase for data persistence.

Key endpoints:

Project Endpoints:
- POST /api/projects: Create a new project (CRUD operation)
- GET /api/projects: List all projects with optional filtering
- GET /api/projects/{id}: Get project details
- PUT /api/projects/{id}: Update project
- DELETE /api/projects/{id}: Delete project
- POST /api/projects/start: Initiate new audit project with LangGraph workflow

EGA Endpoints (BE-15.2):
- GET /api/projects/{id}/egas: List EGAs for a project
- GET /api/projects/{id}/egas/{ega_id}: Get specific EGA details
- POST /api/projects/{id}/egas: Create EGA manually
- PUT /api/projects/{id}/egas/{ega_id}: Update EGA
- DELETE /api/projects/{id}/egas/{ega_id}: Delete EGA
- POST /api/projects/{id}/egas/parse: Parse Assigned Workflow document and extract EGAs

HITL Endpoints (BE-15.3):
- GET /api/hitl/pending: List all pending HITL requests
- GET /api/hitl: List all HITL requests with filtering
- GET /api/hitl/{id}: Get specific HITL request details
- POST /api/hitl/{id}/respond: Submit response (approve/reject/escalate)

Task Endpoints:
- POST /api/tasks/approve: Resume workflow with user approval decision
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import logging
import uuid
import tempfile
import os

from ..db.supabase_client import supabase
from ..services.task_sync import sync_task_to_supabase, get_task_by_thread_id
from ..graph.nodes.ega_parser import (
    parse_assigned_workflow,
    EGARiskLevel,
    EGAStatus,
    get_ega_summary,
    filter_egas_by_risk,
    sort_egas_by_priority,
)

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
# Project CRUD Pydantic Models (BE-15.1)
# ============================================================================

class ProjectStatus(str, Enum):
    """Project status enum for audit projects."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"


class CreateProjectRequest(BaseModel):
    """
    Request schema for creating a new audit project.

    Attributes:
        client_name: Name of the client being audited
        fiscal_year: Fiscal year for the audit (e.g., 2024)
        overall_materiality: Materiality threshold in currency units (optional)
        status: Initial project status (defaults to 'planning')
    """
    client_name: str = Field(..., min_length=1, max_length=255, description="Client name (required)")
    fiscal_year: int = Field(..., ge=2000, le=2100, description="Fiscal year (2000-2100)")
    overall_materiality: Optional[float] = Field(None, ge=0, description="Materiality threshold")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING, description="Project status")


class UpdateProjectRequest(BaseModel):
    """
    Request schema for updating an existing audit project.

    All fields are optional - only provided fields will be updated.
    """
    client_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Client name")
    fiscal_year: Optional[int] = Field(None, ge=2000, le=2100, description="Fiscal year (2000-2100)")
    overall_materiality: Optional[float] = Field(None, ge=0, description="Materiality threshold")
    status: Optional[ProjectStatus] = Field(None, description="Project status")


class ProjectResponse(BaseModel):
    """Response schema for a single project."""
    id: str
    client_name: str
    fiscal_year: int
    overall_materiality: Optional[float] = None
    status: str
    created_at: str
    updated_at: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Response schema for listing projects."""
    status: str = "success"
    projects: List[ProjectResponse]
    total: int


class ProjectDetailResponse(BaseModel):
    """Response schema for project detail with success status."""
    status: str = "success"
    project: ProjectResponse


class ProjectCreateResponse(BaseModel):
    """Response schema for successful project creation."""
    status: str = "created"
    project: ProjectResponse
    message: str


class ProjectDeleteResponse(BaseModel):
    """Response schema for successful project deletion."""
    status: str = "deleted"
    project_id: str
    message: str


# ============================================================================
# EGA Pydantic Models (BE-15.2)
# ============================================================================

class EGARiskLevelEnum(str, Enum):
    """Risk level enum for EGAs."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EGAStatusEnum(str, Enum):
    """Status enum for EGAs."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"


class EGAResponse(BaseModel):
    """Response schema for a single EGA."""
    id: str
    project_id: str
    name: str
    description: str
    risk_level: str
    priority: int
    status: str
    parent_ega_id: Optional[str] = None
    task_count: int = 0
    progress: float = 0.0
    source_row: Optional[int] = None
    source_sheet: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None


class EGAListResponse(BaseModel):
    """Response schema for listing EGAs."""
    status: str = "success"
    egas: List[EGAResponse]
    total: int
    summary: Optional[Dict[str, Any]] = None


class EGADetailResponse(BaseModel):
    """Response schema for EGA detail with success status."""
    status: str = "success"
    ega: EGAResponse


class EGAParseRequest(BaseModel):
    """
    Request schema for parsing EGA from URL.

    Use this when the file is already uploaded to Supabase Storage.
    """
    file_url: Optional[str] = Field(None, description="URL to the Excel file in Supabase Storage")
    sheet_name: Optional[str] = Field(None, description="Specific sheet to parse (optional)")


class EGAParseResponse(BaseModel):
    """Response schema for EGA parsing operation."""
    status: str
    project_id: str
    egas_created: int
    egas: List[EGAResponse]
    warnings: List[str] = []
    errors: List[str] = []
    message: str


class CreateEGARequest(BaseModel):
    """Request schema for creating a single EGA manually."""
    name: str = Field(..., min_length=1, max_length=500, description="EGA name/title")
    description: str = Field(..., min_length=1, description="EGA description")
    risk_level: EGARiskLevelEnum = Field(default=EGARiskLevelEnum.MEDIUM, description="Risk level")
    priority: int = Field(default=50, ge=1, le=100, description="Priority (1-100)")
    status: EGAStatusEnum = Field(default=EGAStatusEnum.PENDING, description="Initial status")
    parent_ega_id: Optional[str] = Field(None, description="Parent EGA ID for hierarchy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UpdateEGARequest(BaseModel):
    """Request schema for updating an EGA."""
    name: Optional[str] = Field(None, min_length=1, max_length=500, description="EGA name/title")
    description: Optional[str] = Field(None, min_length=1, description="EGA description")
    risk_level: Optional[EGARiskLevelEnum] = Field(None, description="Risk level")
    priority: Optional[int] = Field(None, ge=1, le=100, description="Priority (1-100)")
    status: Optional[EGAStatusEnum] = Field(None, description="Status")
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# ============================================================================
# HITL Pydantic Models (BE-15.3)
# ============================================================================

class HITLRequestTypeEnum(str, Enum):
    """Types of HITL escalation requests."""
    URGENCY_THRESHOLD = "urgency_threshold"
    MATERIALITY_EXCEEDED = "materiality_exceeded"
    PROFESSIONAL_JUDGMENT = "professional_judgment"
    ANOMALY_DETECTED = "anomaly_detected"
    EXTERNAL_REVIEW = "external_review"


class HITLRequestStatusEnum(str, Enum):
    """Status of HITL requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class HITLUrgencyLevelEnum(str, Enum):
    """Urgency levels for HITL requests."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HITLRequestResponse(BaseModel):
    """Response schema for a single HITL request."""
    id: str
    task_id: str
    project_id: str
    request_type: str
    urgency_score: float
    urgency_level: str
    title: str
    description: str
    context: Optional[Dict[str, Any]] = None
    status: str
    response: Optional[Dict[str, Any]] = None
    responded_by: Optional[str] = None
    responded_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class HITLListResponse(BaseModel):
    """Response schema for listing HITL requests."""
    status: str = "success"
    requests: List[HITLRequestResponse]
    total: int
    summary: Optional[Dict[str, Any]] = None


class HITLDetailResponse(BaseModel):
    """Response schema for HITL request detail."""
    status: str = "success"
    request: HITLRequestResponse


class HITLRespondRequest(BaseModel):
    """
    Request schema for responding to an HITL request.

    Attributes:
        action: Response action (approve, reject, escalate)
        comment: Optional comment explaining the decision
        modified_values: Optional modified task values (for partial approvals)
        responded_by: User identifier who responded
    """
    action: str = Field(
        ...,
        pattern="^(approve|reject|escalate)$",
        description="Response action (approve, reject, or escalate)"
    )
    comment: Optional[str] = Field(None, max_length=2000, description="Optional response comment")
    modified_values: Optional[Dict[str, Any]] = Field(None, description="Optional modified task values")
    responded_by: Optional[str] = Field(None, max_length=255, description="User identifier")


class HITLRespondResponse(BaseModel):
    """Response schema for HITL response submission."""
    status: str
    request_id: str
    action: str
    workflow_resumed: bool
    task_status: Optional[str] = None
    message: str


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
# Project CRUD Endpoints (BE-15.1)
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


# ============================================================================
# EGA Endpoints (BE-15.2)
# ============================================================================

def _convert_ega_row_to_response(row: Dict[str, Any]) -> EGAResponse:
    """
    Convert a Supabase row to EGAResponse.

    Handles field name mapping and type conversion.
    """
    return EGAResponse(
        id=str(row.get("id", "")),
        project_id=str(row.get("project_id", "")),
        name=row.get("name", ""),
        description=row.get("description", ""),
        risk_level=row.get("risk_level", "medium"),
        priority=row.get("priority", 50),
        status=row.get("status", "pending"),
        parent_ega_id=row.get("parent_ega_id"),
        task_count=row.get("task_count", 0),
        progress=row.get("progress", 0.0),
        source_row=row.get("source_row"),
        source_sheet=row.get("source_sheet"),
        metadata=row.get("metadata"),
        created_at=row.get("created_at", datetime.utcnow().isoformat()),
        updated_at=row.get("updated_at")
    )


@router.get(
    "/projects/{project_id}/egas",
    response_model=EGAListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "EGAs retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def list_egas(
    project_id: str,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: Optional[str] = "priority",
    descending: bool = True,
    limit: int = 100,
    offset: int = 0,
    include_summary: bool = True
) -> EGAListResponse:
    """
    List all EGAs for a specific project.

    Retrieves EGAs from Supabase with optional filtering and sorting.

    Args:
        project_id: UUID of the project
        risk_level: Filter by risk level (critical, high, medium, low)
        status_filter: Filter by status (pending, in_progress, review_required, completed)
        sort_by: Field to sort by (priority, created_at, name, risk_level)
        descending: Sort in descending order (default: True)
        limit: Maximum number of EGAs to return (default: 100)
        offset: Number of EGAs to skip for pagination (default: 0)
        include_summary: Include summary statistics (default: True)

    Returns:
        EGAListResponse with list of EGAs and optional summary
    """
    try:
        logger.info(f"Listing EGAs for project: {project_id}")

        # Verify project exists
        project_check = supabase.table("audit_projects").select("id").eq("id", project_id).execute()
        if not project_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Build query
        query = supabase.table("audit_egas").select("*", count="exact").eq("project_id", project_id)

        # Apply filters
        if risk_level:
            valid_risk_levels = [r.value for r in EGARiskLevelEnum]
            if risk_level not in valid_risk_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid risk_level. Valid values: {valid_risk_levels}"
                )
            query = query.eq("risk_level", risk_level)

        if status_filter:
            valid_statuses = [s.value for s in EGAStatusEnum]
            if status_filter not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status_filter. Valid values: {valid_statuses}"
                )
            query = query.eq("status", status_filter)

        # Apply sorting
        valid_sort_fields = ["priority", "created_at", "name", "risk_level", "status"]
        if sort_by not in valid_sort_fields:
            sort_by = "priority"

        query = query.order(sort_by, desc=descending)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        # Execute query
        result = query.execute()

        egas = [_convert_ega_row_to_response(row) for row in (result.data or [])]
        total = result.count if result.count is not None else len(egas)

        # Build summary if requested
        summary = None
        if include_summary and egas:
            ega_dicts = [row for row in (result.data or [])]
            summary = get_ega_summary(ega_dicts)

        logger.info(f"Retrieved {len(egas)} EGAs for project {project_id} (total: {total})")

        return EGAListResponse(
            status="success",
            egas=egas,
            total=total,
            summary=summary
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list EGAs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list EGAs: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/egas/{ega_id}",
    response_model=EGADetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "EGA retrieved successfully"},
        404: {"model": ErrorResponse, "description": "EGA or project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def get_ega(project_id: str, ega_id: str) -> EGADetailResponse:
    """
    Get a specific EGA by ID.

    Args:
        project_id: UUID of the project
        ega_id: UUID of the EGA

    Returns:
        EGADetailResponse with EGA details
    """
    try:
        logger.info(f"Getting EGA: {ega_id} for project: {project_id}")

        # Query for the EGA
        result = supabase.table("audit_egas").select("*").eq("id", ega_id).eq("project_id", project_id).execute()

        if not result.data:
            logger.warning(f"EGA not found: {ega_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EGA not found: {ega_id}"
            )

        ega = result.data[0]
        logger.info(f"EGA retrieved: {ega_id}")

        return EGADetailResponse(
            status="success",
            ega=_convert_ega_row_to_response(ega)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get EGA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get EGA: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/egas",
    response_model=EGADetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "EGA created successfully"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_ega(
    project_id: str,
    request_data: CreateEGARequest
) -> EGADetailResponse:
    """
    Create a new EGA manually.

    Args:
        project_id: UUID of the project
        request_data: EGA creation parameters

    Returns:
        EGADetailResponse with created EGA details
    """
    try:
        logger.info(f"Creating EGA for project: {project_id}")

        # Verify project exists
        project_check = supabase.table("audit_projects").select("id").eq("id", project_id).execute()
        if not project_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Generate EGA ID
        ega_id = f"ega-{uuid.uuid4().hex[:12]}"

        # Prepare EGA data
        ega_data = {
            "id": ega_id,
            "project_id": project_id,
            "name": request_data.name,
            "description": request_data.description,
            "risk_level": request_data.risk_level.value,
            "priority": request_data.priority,
            "status": request_data.status.value,
            "parent_ega_id": request_data.parent_ega_id,
            "task_count": 0,
            "progress": 0.0,
            "metadata": request_data.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        # Insert into Supabase
        result = supabase.table("audit_egas").insert(ega_data).execute()

        if not result.data:
            logger.error("Failed to create EGA - no data returned from Supabase")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create EGA in database"
            )

        created_ega = result.data[0]
        logger.info(f"EGA created successfully: {ega_id}")

        return EGADetailResponse(
            status="success",
            ega=_convert_ega_row_to_response(created_ega)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create EGA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create EGA: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/egas/{ega_id}",
    response_model=EGADetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "EGA updated successfully"},
        404: {"model": ErrorResponse, "description": "EGA or project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def update_ega(
    project_id: str,
    ega_id: str,
    request_data: UpdateEGARequest
) -> EGADetailResponse:
    """
    Update an existing EGA.

    Only provided fields will be updated.

    Args:
        project_id: UUID of the project
        ega_id: UUID of the EGA to update
        request_data: Fields to update

    Returns:
        EGADetailResponse with updated EGA details
    """
    try:
        logger.info(f"Updating EGA: {ega_id}")

        # Check if EGA exists
        existing = supabase.table("audit_egas").select("id").eq("id", ega_id).eq("project_id", project_id).execute()
        if not existing.data:
            logger.warning(f"EGA not found for update: {ega_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EGA not found: {ega_id}"
            )

        # Build update data (only include non-None fields)
        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if request_data.name is not None:
            update_data["name"] = request_data.name
        if request_data.description is not None:
            update_data["description"] = request_data.description
        if request_data.risk_level is not None:
            update_data["risk_level"] = request_data.risk_level.value
        if request_data.priority is not None:
            update_data["priority"] = request_data.priority
        if request_data.status is not None:
            update_data["status"] = request_data.status.value
        if request_data.progress is not None:
            update_data["progress"] = request_data.progress
        if request_data.metadata is not None:
            update_data["metadata"] = request_data.metadata

        # Update in Supabase
        result = supabase.table("audit_egas").update(update_data).eq("id", ega_id).execute()

        if not result.data:
            logger.error(f"Failed to update EGA - no data returned: {ega_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update EGA in database"
            )

        updated_ega = result.data[0]
        logger.info(f"EGA updated successfully: {ega_id}")

        return EGADetailResponse(
            status="success",
            ega=_convert_ega_row_to_response(updated_ega)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update EGA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update EGA: {str(e)}"
        )


@router.delete(
    "/projects/{project_id}/egas/{ega_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "EGA deleted successfully"},
        404: {"model": ErrorResponse, "description": "EGA not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def delete_ega(project_id: str, ega_id: str) -> Dict[str, Any]:
    """
    Delete an EGA.

    Args:
        project_id: UUID of the project
        ega_id: UUID of the EGA to delete

    Returns:
        Confirmation of deletion
    """
    try:
        logger.info(f"Deleting EGA: {ega_id}")

        # Check if EGA exists
        existing = supabase.table("audit_egas").select("id, name").eq("id", ega_id).eq("project_id", project_id).execute()
        if not existing.data:
            logger.warning(f"EGA not found for deletion: {ega_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EGA not found: {ega_id}"
            )

        ega_name = existing.data[0].get("name", "Unknown")

        # Delete from Supabase
        supabase.table("audit_egas").delete().eq("id", ega_id).execute()

        logger.info(f"EGA deleted successfully: {ega_id}")

        return {
            "status": "deleted",
            "ega_id": ega_id,
            "message": f"EGA '{ega_name}' deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete EGA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete EGA: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/egas/parse",
    response_model=EGAParseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "EGAs parsed and created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or request"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def parse_egas(
    project_id: str,
    file: Optional[UploadFile] = File(None, description="Excel file to parse (.xlsx, .xls)"),
    file_url: Optional[str] = Form(None, description="URL to Excel file in Supabase Storage"),
    sheet_name: Optional[str] = Form(None, description="Specific sheet to parse")
) -> EGAParseResponse:
    """
    Parse an Assigned Workflow document and extract EGAs.

    Accepts either a file upload or a URL to a file in Supabase Storage.

    This endpoint:
    1. Validates the project exists
    2. Parses the Excel file using MCP Excel Processor
    3. Extracts EGAs with metadata (risk_level, priority, category)
    4. Creates EGA records in Supabase
    5. Returns created EGAs with parsing statistics

    Args:
        project_id: UUID of the project
        file: Uploaded Excel file (.xlsx, .xls)
        file_url: URL to Excel file in Supabase Storage
        sheet_name: Specific sheet to parse (optional)

    Returns:
        EGAParseResponse with created EGAs and parsing metadata
    """
    temp_file_path = None

    try:
        logger.info(f"Parsing EGAs for project: {project_id}")

        # Verify project exists
        project_check = supabase.table("audit_projects").select("id, client_name").eq("id", project_id).execute()
        if not project_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )

        # Validate input - need either file or file_url
        if not file and not file_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either file or file_url must be provided"
            )

        # Handle file upload
        if file:
            # Validate file type
            if file.filename:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in (".xlsx", ".xls"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid file type: {file_ext}. Only .xlsx and .xls files are supported"
                    )

            # Save to temp file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(file.filename)[1] if file.filename else ".xlsx"
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            logger.info(f"Saved uploaded file to: {temp_file_path}")

        # Parse the workflow document
        parse_result = await parse_assigned_workflow(
            file_path=temp_file_path,
            file_url=file_url,
            project_id=project_id,
            sheet_name=sheet_name
        )

        if not parse_result.success and not parse_result.egas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse document: {'; '.join(parse_result.errors)}"
            )

        # Insert EGAs into Supabase
        created_egas: List[EGAResponse] = []

        for ega in parse_result.egas:
            ega_dict = ega.to_dict()

            try:
                result = supabase.table("audit_egas").insert(ega_dict).execute()

                if result.data:
                    created_egas.append(_convert_ega_row_to_response(result.data[0]))
                else:
                    parse_result.warnings.append(f"Failed to insert EGA: {ega.name}")

            except Exception as insert_error:
                parse_result.warnings.append(f"Error inserting EGA '{ega.name}': {str(insert_error)}")

        logger.info(
            f"Parsed and created {len(created_egas)} EGAs for project {project_id} "
            f"(warnings: {len(parse_result.warnings)}, errors: {len(parse_result.errors)})"
        )

        client_name = project_check.data[0].get("client_name", "Unknown")

        return EGAParseResponse(
            status="success" if created_egas else "partial",
            project_id=project_id,
            egas_created=len(created_egas),
            egas=created_egas,
            warnings=parse_result.warnings,
            errors=parse_result.errors,
            message=f"Parsed and created {len(created_egas)} EGAs for project '{client_name}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to parse EGAs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse EGAs: {str(e)}"
        )

    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file: {cleanup_error}")


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


# ============================================================================
# HITL Queue Management Endpoints (BE-15.3)
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
                project_id = hitl_request.get("project_id")
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
