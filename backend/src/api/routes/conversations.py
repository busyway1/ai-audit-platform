"""
Conversation API Routes for Agent Dialogue Visibility

This module provides FastAPI endpoints for querying and storing agent conversations.
Enables visibility into how agents communicate during audit workflows.

Endpoints:
- GET /api/conversations: List conversations with filters
- GET /api/conversations/stats: Get conversation statistics
- GET /api/conversations/{id}: Get single conversation
- POST /api/conversations: Create conversation entry
- POST /api/conversations/bulk: Create multiple conversation entries
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ConversationMetadata(BaseModel):
    """Metadata for conversation entry."""
    tool_call: Optional[str] = None
    file_refs: Optional[List[str]] = None
    loop_attempt: Optional[int] = None
    strategy_used: Optional[str] = None
    duration: Optional[float] = None


class ConversationCreate(BaseModel):
    """Request model for creating conversation."""
    project_id: UUID
    hierarchy_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    from_agent: str = Field(..., min_length=1, max_length=100)
    to_agent: str = Field(..., min_length=1, max_length=100)
    message_type: str = Field(
        ...,
        pattern="^(instruction|response|question|answer|error|escalation|feedback|tool_use)$"
    )
    content: str = Field(..., min_length=1)
    metadata: Optional[ConversationMetadata] = None


class ConversationResponse(BaseModel):
    """Response model for conversation."""
    id: UUID
    project_id: UUID
    hierarchy_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    from_agent: str
    to_agent: str
    message_type: str
    content: str
    timestamp: datetime
    metadata: Optional[ConversationMetadata] = None


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""
    items: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ConversationStats(BaseModel):
    """Statistics about conversations."""
    total_messages: int
    by_agent: Dict[str, int]
    by_type: Dict[str, int]
    error_count: int
    escalation_count: int


# ============================================================================
# In-memory Storage (replace with DB in production)
# ============================================================================

conversations_db: List[Dict[str, Any]] = []


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_uuid_safe(value: Optional[str]) -> Optional[UUID]:
    """Safely parse a string to UUID, returning None on failure."""
    if value is None:
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def _dict_to_response(conv: Dict[str, Any]) -> ConversationResponse:
    """Convert a dictionary to ConversationResponse."""
    return ConversationResponse(
        id=UUID(conv["id"]),
        project_id=UUID(conv["project_id"]),
        hierarchy_id=_parse_uuid_safe(conv.get("hierarchy_id")),
        task_id=_parse_uuid_safe(conv.get("task_id")),
        from_agent=conv["from_agent"],
        to_agent=conv["to_agent"],
        message_type=conv["message_type"],
        content=conv["content"],
        timestamp=datetime.fromisoformat(conv["timestamp"]),
        metadata=ConversationMetadata(**conv["metadata"]) if conv.get("metadata") else None
    )


# ============================================================================
# List Endpoints
# ============================================================================

@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Conversations retrieved successfully"},
        500: {"description": "Internal server error"},
    }
)
async def list_conversations(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    hierarchy_id: Optional[UUID] = Query(None, description="Filter by hierarchy item"),
    task_id: Optional[UUID] = Query(None, description="Filter by task"),
    from_agent: Optional[str] = Query(None, description="Filter by sender agent"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    include_errors: bool = Query(True, description="Include error messages"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
) -> ConversationListResponse:
    """
    List conversations with optional filters.

    Filters can be combined for precise queries:
    - By hierarchy: Get all conversations for a Business Process, FSLI, or EGA
    - By task: Get conversations specific to a task
    - By agent: Filter by sender agent
    - By type: Filter by message type (instruction, response, error, etc.)
    """
    try:
        logger.info(f"Listing conversations (project={project_id}, task={task_id})")
        filtered = conversations_db.copy()

        # Apply filters
        if project_id:
            filtered = [c for c in filtered if c.get("project_id") == str(project_id)]

        if hierarchy_id:
            filtered = [c for c in filtered if c.get("hierarchy_id") == str(hierarchy_id)]

        if task_id:
            filtered = [c for c in filtered if c.get("task_id") == str(task_id)]

        if from_agent:
            filtered = [c for c in filtered if c.get("from_agent") == from_agent]

        if message_type:
            filtered = [c for c in filtered if c.get("message_type") == message_type]

        if not include_errors:
            filtered = [c for c in filtered if c.get("message_type") != "error"]

        if start_date:
            filtered = [
                c for c in filtered
                if c.get("timestamp", "") >= start_date.isoformat()
            ]

        if end_date:
            filtered = [
                c for c in filtered
                if c.get("timestamp", "") <= end_date.isoformat()
            ]

        # Sort by timestamp descending (newest first)
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Pagination
        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = filtered[start_idx:end_idx]

        logger.info(f"Retrieved {len(page_items)} conversations (total: {total})")

        return ConversationListResponse(
            items=[_dict_to_response(c) for c in page_items],
            total=total,
            page=page,
            page_size=page_size,
            has_more=end_idx < total
        )

    except Exception as e:
        logger.error(f"Failed to list conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=ConversationStats,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Statistics retrieved successfully"},
        500: {"description": "Internal server error"},
    }
)
async def get_conversation_stats(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    hierarchy_id: Optional[UUID] = Query(None, description="Filter by hierarchy item"),
    task_id: Optional[UUID] = Query(None, description="Filter by task")
) -> ConversationStats:
    """
    Get conversation statistics.

    Useful for dashboard displays showing:
    - Total message count
    - Messages per agent
    - Messages by type
    - Error and escalation counts
    """
    try:
        logger.info(f"Getting conversation stats (project={project_id})")
        filtered = conversations_db.copy()

        if project_id:
            filtered = [c for c in filtered if c.get("project_id") == str(project_id)]
        if hierarchy_id:
            filtered = [c for c in filtered if c.get("hierarchy_id") == str(hierarchy_id)]
        if task_id:
            filtered = [c for c in filtered if c.get("task_id") == str(task_id)]

        by_agent: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        error_count = 0
        escalation_count = 0

        for conv in filtered:
            # Count by agent
            agent = conv.get("from_agent", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1

            # Count by type
            msg_type = conv.get("message_type", "unknown")
            by_type[msg_type] = by_type.get(msg_type, 0) + 1

            # Count errors and escalations
            if msg_type == "error":
                error_count += 1
            elif msg_type == "escalation":
                escalation_count += 1

        logger.info(f"Stats calculated: {len(filtered)} total messages")

        return ConversationStats(
            total_messages=len(filtered),
            by_agent=by_agent,
            by_type=by_type,
            error_count=error_count,
            escalation_count=escalation_count
        )

    except Exception as e:
        logger.error(f"Failed to get conversation stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation stats: {str(e)}"
        )


# ============================================================================
# Detail Endpoint
# ============================================================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Conversation retrieved successfully"},
        404: {"description": "Conversation not found"},
        500: {"description": "Internal server error"},
    }
)
async def get_conversation(conversation_id: UUID) -> ConversationResponse:
    """Get a single conversation by ID."""
    try:
        logger.info(f"Getting conversation: {conversation_id}")

        for conv in conversations_db:
            if conv.get("id") == str(conversation_id):
                logger.info(f"Conversation found: {conversation_id}")
                return _dict_to_response(conv)

        logger.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


# ============================================================================
# Create Endpoints
# ============================================================================

@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversation created successfully"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    }
)
async def create_conversation(data: ConversationCreate) -> ConversationResponse:
    """
    Create a new conversation entry.

    Called by agents to log their interactions.
    Each interaction (instruction, response, error, etc.) is logged separately.
    """
    try:
        logger.info(f"Creating conversation: {data.from_agent} -> {data.to_agent}")

        conv_id = uuid4()
        timestamp = datetime.utcnow()

        conv = {
            "id": str(conv_id),
            "project_id": str(data.project_id),
            "hierarchy_id": str(data.hierarchy_id) if data.hierarchy_id else None,
            "task_id": str(data.task_id) if data.task_id else None,
            "from_agent": data.from_agent,
            "to_agent": data.to_agent,
            "message_type": data.message_type,
            "content": data.content,
            "timestamp": timestamp.isoformat(),
            "metadata": data.metadata.model_dump() if data.metadata else None
        }

        conversations_db.append(conv)

        logger.info(f"Conversation created: {conv_id}")

        return ConversationResponse(
            id=conv_id,
            project_id=data.project_id,
            hierarchy_id=data.hierarchy_id,
            task_id=data.task_id,
            from_agent=data.from_agent,
            to_agent=data.to_agent,
            message_type=data.message_type,
            content=data.content,
            timestamp=timestamp,
            metadata=data.metadata
        )

    except Exception as e:
        logger.error(f"Failed to create conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )


@router.post(
    "/bulk",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversations created successfully"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    }
)
async def create_conversations_bulk(
    data: List[ConversationCreate]
) -> List[ConversationResponse]:
    """
    Create multiple conversation entries at once.

    Useful when Ralph-wiggum loop completes and needs to save
    all conversation history in one call.
    """
    try:
        logger.info(f"Creating {len(data)} conversations in bulk")

        results = []
        for item in data:
            result = await create_conversation(item)
            results.append(result)

        logger.info(f"Bulk creation complete: {len(results)} conversations")
        return results

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create conversations in bulk: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversations in bulk: {str(e)}"
        )
