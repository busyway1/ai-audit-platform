"""
API Routes Package

This package provides modular API route organization for the Audit Workflow system.
Routes are split by domain for maintainability (max 800 lines per file per CLAUDE.md guidelines).

Modules:
- projects: Project CRUD and workflow initiation
- tasks: Task approval endpoints
- egas: EGA CRUD and parsing
- hitl: HITL queue management
- health: Health check endpoint
- schemas: Shared Pydantic models (request/response schemas)

Usage:
    from src.api.routes import router
    app.include_router(router)
"""

from fastapi import APIRouter

# Import all domain routers
from .projects import router as projects_router
from .tasks import router as tasks_router
from .egas import router as egas_router
from .hitl import router as hitl_router
from .health import router as health_router
from .dashboard import router as dashboard_router
from .conversations import router as conversations_router

# Create main router that aggregates all domain routers
router = APIRouter(tags=["audit-workflow"])

# Include all domain routers
# Note: Each router already has /api prefix, so no additional prefix needed here
router.include_router(projects_router)
router.include_router(tasks_router)
router.include_router(egas_router)
router.include_router(hitl_router)
router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(conversations_router)

# Re-export all schemas for backward compatibility
from .schemas import (
    # Common
    ErrorResponse,
    # Project schemas
    ProjectStatus,
    StartAuditRequest,
    StartAuditResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    # Task schemas
    ApprovalRequest,
    ApprovalResponse,
    # EGA schemas
    EGARiskLevelEnum,
    EGAStatusEnum,
    EGAResponse,
    EGAListResponse,
    EGADetailResponse,
    EGAParseRequest,
    EGAParseResponse,
    CreateEGARequest,
    UpdateEGARequest,
    # HITL schemas
    HITLRequestTypeEnum,
    HITLRequestStatusEnum,
    HITLUrgencyLevelEnum,
    HITLRequestResponse,
    HITLListResponse,
    HITLDetailResponse,
    HITLRespondRequest,
    HITLRespondResponse,
)

# Export for backward compatibility
__all__ = [
    "router",
    "projects_router",
    "tasks_router",
    "egas_router",
    "hitl_router",
    "health_router",
    "dashboard_router",
    "conversations_router",
    # Common
    "ErrorResponse",
    # Project
    "ProjectStatus",
    "StartAuditRequest",
    "StartAuditResponse",
    "CreateProjectRequest",
    "UpdateProjectRequest",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectDetailResponse",
    "ProjectCreateResponse",
    "ProjectDeleteResponse",
    # Task
    "ApprovalRequest",
    "ApprovalResponse",
    # EGA
    "EGARiskLevelEnum",
    "EGAStatusEnum",
    "EGAResponse",
    "EGAListResponse",
    "EGADetailResponse",
    "EGAParseRequest",
    "EGAParseResponse",
    "CreateEGARequest",
    "UpdateEGARequest",
    # HITL
    "HITLRequestTypeEnum",
    "HITLRequestStatusEnum",
    "HITLUrgencyLevelEnum",
    "HITLRequestResponse",
    "HITLListResponse",
    "HITLDetailResponse",
    "HITLRespondRequest",
    "HITLRespondResponse",
]
