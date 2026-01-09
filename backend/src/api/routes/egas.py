"""
EGA (Engagement Area) API Routes

This module provides FastAPI endpoints for managing EGAs within audit projects.

Endpoints (BE-15.2):
- GET /api/projects/{id}/egas: List EGAs for a project
- GET /api/projects/{id}/egas/{ega_id}: Get specific EGA details
- POST /api/projects/{id}/egas: Create EGA manually
- PUT /api/projects/{id}/egas/{ega_id}: Update EGA
- DELETE /api/projects/{id}/egas/{ega_id}: Delete EGA
- POST /api/projects/{id}/egas/parse: Parse Assigned Workflow document and extract EGAs
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid
import tempfile
import os

from ...db.supabase_client import supabase
from ...graph.nodes.ega_parser import (
    parse_assigned_workflow,
    get_ega_summary,
)
from .schemas import (
    EGAResponse,
    EGAListResponse,
    EGADetailResponse,
    EGAParseResponse,
    CreateEGARequest,
    UpdateEGARequest,
    EGARiskLevelEnum,
    EGAStatusEnum,
    ErrorResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["egas"])


# ============================================================================
# Helper Functions
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


# ============================================================================
# EGA CRUD Endpoints
# ============================================================================

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


# ============================================================================
# EGA Parsing Endpoint
# ============================================================================

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
