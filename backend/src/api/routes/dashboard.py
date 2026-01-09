"""
Dashboard API Routes

This module provides FastAPI endpoints for dashboard metrics aggregation.
Fetches aggregated data from multiple tables to power the frontend dashboard.

Endpoints:
- GET /api/dashboard/metrics: Get aggregated dashboard metrics
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from ...db.supabase_client import supabase

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RecentActivity(BaseModel):
    """Schema for a single recent activity item."""
    id: str
    type: str
    description: str
    timestamp: str


class DashboardMetricsResponse(BaseModel):
    """
    Response schema for dashboard metrics.

    Matches the frontend mockData structure for seamless integration.
    """
    activeProjects: int = Field(..., description="Count of active projects (status='active' or 'in_progress')")
    pendingTasks: int = Field(..., description="Count of pending audit tasks")
    completedAudits: int = Field(..., description="Count of completed audit projects")
    riskAlerts: int = Field(..., description="Count of pending HITL requests (risk alerts)")
    recentActivities: List[RecentActivity] = Field(
        default_factory=list,
        description="List of recent activity entries"
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _get_active_projects_count() -> int:
    """
    Count active audit projects.

    Active status includes: 'Planning', 'Execution', 'in_progress', 'active'
    """
    try:
        # Query for projects in active states
        result = supabase.table("audit_projects").select(
            "id", count="exact"
        ).in_(
            "status", ["Planning", "Execution", "in_progress", "active"]
        ).execute()

        return result.count if result.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count active projects: {e}")
        return 0


def _get_pending_tasks_count() -> int:
    """
    Count pending audit tasks.

    Pending status includes: 'Pending', 'pending'
    """
    try:
        result = supabase.table("audit_tasks").select(
            "id", count="exact"
        ).in_(
            "status", ["Pending", "pending"]
        ).execute()

        return result.count if result.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count pending tasks: {e}")
        return 0


def _get_completed_audits_count() -> int:
    """
    Count completed audit projects.

    Completed status includes: 'Completed', 'completed', 'Review'
    """
    try:
        result = supabase.table("audit_projects").select(
            "id", count="exact"
        ).in_(
            "status", ["Completed", "completed", "Review"]
        ).execute()

        return result.count if result.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count completed audits: {e}")
        return 0


def _get_risk_alerts_count() -> int:
    """
    Count pending HITL requests (risk alerts requiring human attention).
    """
    try:
        result = supabase.table("hitl_requests").select(
            "id", count="exact"
        ).eq("status", "pending").execute()

        return result.count if result.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count risk alerts: {e}")
        return 0


def _get_recent_activities(limit: int = 10) -> List[RecentActivity]:
    """
    Get recent activities from agent_messages table.

    Maps message types to activity types:
    - 'instruction' -> 'task_started'
    - 'response' -> 'task_completed'
    - 'tool-use' -> 'tool_executed'
    - 'human-feedback' -> 'human_feedback'

    Args:
        limit: Maximum number of activities to return (default: 10)

    Returns:
        List of RecentActivity objects
    """
    try:
        result = supabase.table("agent_messages").select(
            "id, agent_role, content, message_type, created_at"
        ).order(
            "created_at", desc=True
        ).limit(limit).execute()

        activities = []
        type_mapping = {
            "instruction": "task_started",
            "response": "task_completed",
            "tool-use": "tool_executed",
            "human-feedback": "human_feedback"
        }

        for row in (result.data or []):
            activity_type = type_mapping.get(row.get("message_type", ""), "activity")

            # Create a concise description from content
            content = row.get("content", "")
            description = content[:100] + "..." if len(content) > 100 else content

            activities.append(RecentActivity(
                id=str(row.get("id", "")),
                type=activity_type,
                description=f"[{row.get('agent_role', 'System')}] {description}",
                timestamp=row.get("created_at", datetime.utcnow().isoformat())
            ))

        return activities
    except Exception as e:
        logger.error(f"Failed to get recent activities: {e}")
        return []


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Dashboard metrics retrieved successfully"},
        500: {"description": "Internal server error"},
    }
)
async def get_dashboard_metrics() -> DashboardMetricsResponse:
    """
    Get aggregated dashboard metrics.

    This endpoint aggregates data from multiple tables:
    - audit_projects: activeProjects, completedAudits
    - audit_tasks: pendingTasks
    - hitl_requests: riskAlerts
    - agent_messages: recentActivities

    Returns:
        DashboardMetricsResponse with all aggregated metrics

    Example Response:
        {
            "activeProjects": 5,
            "pendingTasks": 12,
            "completedAudits": 8,
            "riskAlerts": 3,
            "recentActivities": [
                {
                    "id": "uuid",
                    "type": "task_completed",
                    "description": "[Manager] Task completed...",
                    "timestamp": "2026-01-14T10:00:00Z"
                }
            ]
        }
    """
    try:
        logger.info("Fetching dashboard metrics")

        # Fetch all metrics (could be parallelized with asyncio.gather if needed)
        active_projects = _get_active_projects_count()
        pending_tasks = _get_pending_tasks_count()
        completed_audits = _get_completed_audits_count()
        risk_alerts = _get_risk_alerts_count()
        recent_activities = _get_recent_activities(limit=10)

        logger.info(
            f"Dashboard metrics: active={active_projects}, pending={pending_tasks}, "
            f"completed={completed_audits}, alerts={risk_alerts}, activities={len(recent_activities)}"
        )

        return DashboardMetricsResponse(
            activeProjects=active_projects,
            pendingTasks=pending_tasks,
            completedAudits=completed_audits,
            riskAlerts=risk_alerts,
            recentActivities=recent_activities
        )

    except Exception as e:
        logger.error(f"Failed to fetch dashboard metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard metrics: {str(e)}"
        )
