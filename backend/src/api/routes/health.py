"""
Health Check API Routes

This module provides health check endpoints for monitoring service availability.

Endpoints:
- GET /api/health: Service health check
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any
from datetime import datetime
import logging

from ...db.supabase_client import supabase
from .schemas import ErrorResponse

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["health"])


# ============================================================================
# Health Check Endpoint
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
