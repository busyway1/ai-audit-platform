"""
Shared Pydantic Models (Request/Response Schemas) for API Routes

This module contains all Pydantic models used across the API endpoints,
organized by domain for maintainability.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


# ============================================================================
# Common/Shared Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Response schema for error cases."""
    status: str = "error"
    error: str
    details: Optional[str] = None


# ============================================================================
# Project Schemas (BE-15.1)
# ============================================================================

class ProjectStatus(str, Enum):
    """Project status enum for audit projects."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"


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


class StartAuditResponse(BaseModel):
    """Response schema for successful audit start."""
    status: str = "success"
    thread_id: str
    next_action: str
    message: str


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
# Task Schemas
# ============================================================================

class ApprovalRequest(BaseModel):
    """
    Request schema for task approval.

    Attributes:
        thread_id: LangGraph thread identifier for the workflow
        approved: Boolean indicating user approval decision
    """
    thread_id: str = Field(..., min_length=1, description="Thread ID (required)")
    approved: bool = Field(..., description="Approval decision")


class ApprovalResponse(BaseModel):
    """Response schema for successful task approval."""
    status: str = "resumed"
    thread_id: str
    task_status: str
    message: str


# ============================================================================
# EGA Schemas (BE-15.2)
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
# HITL Schemas (BE-15.3)
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
