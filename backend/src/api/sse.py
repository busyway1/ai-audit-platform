"""Server-Sent Events (SSE) Streaming Endpoint

This module provides real-time streaming of agent messages via SSE.
Uses polling-based approach to query database for new messages.
Supports message processing through LangGraph when a message query parameter is provided.

Key Endpoint:
    GET /stream/{task_id} - Stream agent messages for specific task
    GET /stream/{task_id}?message=... - Process message through LangGraph and stream responses

SSE Event Types:
    - "message": New agent message inserted
    - "heartbeat": Keep-alive ping every 30 seconds
    - "error": Error occurred during streaming

Reference: Plan section T3.7, LangGraph SSE pattern
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, Optional, Set
from uuid import uuid4
from urllib.parse import unquote
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global message queues (exposed for testing)
# Maps task_id -> asyncio.Queue for message injection
message_queues: Dict[str, asyncio.Queue] = {}


@router.get("/{task_id}")
def stream_agent_messages(
    task_id: str,
    request: Request,
    message: Optional[str] = None
) -> EventSourceResponse:
    """Stream agent messages via SSE for specific task.

    This endpoint establishes a Server-Sent Events connection that streams
    agent messages by polling the database for new entries. If a message
    query parameter is provided, the message will be processed through
    LangGraph before starting the polling loop.

    Args:
        task_id: UUID of the audit task to stream messages for
        request: FastAPI Request object (used for disconnect detection)
        message: Optional user message to process through LangGraph

    Returns:
        EventSourceResponse: SSE stream with agent messages

    SSE Event Format:
        ```
        event: message
        data: {
            "id": "msg-uuid",
            "agent_role": "auditor",
            "content": "Analysis complete...",
            "timestamp": "2024-01-06T12:00:00Z"
        }
        ```

    Usage (Frontend):
        ```javascript
        // Simple polling (no message)
        const eventSource = new EventSource(`/api/stream/${taskId}`);

        // With message processing
        const eventSource = new EventSource(
            `/api/stream/${taskId}?message=${encodeURIComponent('Analyze revenue')}`
        );

        eventSource.addEventListener('message', (event) => {
            const message = JSON.parse(event.data);
            console.log(`[${message.agent_role}] ${message.content}`);
        });

        eventSource.addEventListener('heartbeat', () => {
            console.log('Connection alive');
        });

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            eventSource.close();
        };
        ```

    Connection Management:
        - Auto-closes when client disconnects
        - Heartbeat every 30 seconds prevents timeout
        - Polls database every 1 second for new messages
    """

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """Generate SSE events by polling database for new messages.

        Yields:
            Dict with "event" and "data" keys for SSE protocol
        """

        from ..db.supabase_client import supabase

        # Track seen message IDs to avoid duplicates
        seen_message_ids: Set[str] = set()

        # Track last message timestamp for efficient queries
        last_check_time: Optional[str] = None

        # Get or create message queue for this task (for testing injection)
        if task_id not in message_queues:
            message_queues[task_id] = asyncio.Queue()
        message_queue = message_queues[task_id]

        # Process incoming message through LangGraph if provided
        if message:
            try:
                # Decode URL-encoded message (may be double-encoded from frontend)
                decoded_message = unquote(unquote(message))
                logger.info(f"Processing user message for task {task_id}: {decoded_message[:100]}...")

                # 1. Insert user message into agent_messages table
                user_msg_id = str(uuid4())
                user_msg_timestamp = datetime.now(timezone.utc).isoformat()
                user_message_record = {
                    "id": user_msg_id,
                    "task_id": task_id,
                    "agent_role": "user",
                    "content": decoded_message,
                    "message_type": "instruction",
                    "metadata": {},
                    "created_at": user_msg_timestamp
                }

                insert_result = supabase.table("agent_messages").insert(user_message_record).execute()
                if not insert_result.data:
                    logger.error(f"Failed to insert user message for task {task_id}")
                else:
                    logger.info(f"User message inserted: {user_msg_id}")

                # 2. Get the LangGraph instance from app state and invoke it
                graph = request.app.state.graph
                if graph is not None:
                    # Prepare initial state for the graph invocation
                    # Get thread_id from the task record (if it exists)
                    thread_id = f"task-{task_id}"  # Default fallback
                    project_id = None

                    try:
                        task_result = supabase.table("audit_tasks").select("thread_id, project_id").eq("id", task_id).execute()
                        if task_result.data and len(task_result.data) > 0:
                            thread_id = task_result.data[0].get("thread_id") or thread_id
                            project_id = task_result.data[0].get("project_id")
                    except Exception as task_lookup_err:
                        logger.warning(f"Could not find task {task_id} in audit_tasks: {task_lookup_err}")
                        # Continue with default thread_id

                    if True:  # Always proceed with LangGraph invocation

                        # Create LangGraph configuration with thread ID
                        config = {
                            "configurable": {
                                "thread_id": thread_id
                            }
                        }

                        # Build state with the new user message
                        # The graph will handle the message and insert responses into agent_messages
                        from langchain_core.messages import HumanMessage

                        graph_state = {
                            # Core conversation
                            "messages": [HumanMessage(content=decoded_message)],
                            # Audit info (defaults for ad-hoc chat)
                            "project_id": str(project_id) if project_id else task_id,
                            "client_name": "Chat Session",
                            "fiscal_year": 2026,
                            "overall_materiality": 0.0,
                            "audit_plan": {},
                            # Task management
                            "tasks": [],
                            # HITL state
                            "next_action": "CONTINUE",
                            "is_approved": True,
                            # Shared knowledge
                            "shared_documents": [],
                            # Interview state
                            "interview_complete": True,  # Skip interview for ad-hoc chat
                            "interview_phase": 0,
                            "interview_responses": [],
                            "specification": {},
                            # EGA management
                            "egas": [],
                            # Urgency config
                            "urgency_config": {
                                "materiality_weight": 0.40,
                                "risk_weight": 0.35,
                                "ai_confidence_weight": 0.25,
                                "hitl_threshold": 0.7
                            },
                        }

                        logger.info(f"Invoking LangGraph for task {task_id}, thread {thread_id}")

                        # Invoke the graph (this should process the message and may insert responses)
                        try:
                            result = await graph.ainvoke(graph_state, config)
                            logger.info(f"LangGraph invocation completed for task {task_id}")

                            # If the graph returns messages in the result, store them
                            result_messages = result.get("messages", [])
                            logger.info(f"Result contains {len(result_messages)} messages")

                            from langchain_core.messages import AIMessage

                            for msg in result_messages:
                                # Check if it's an AI message using isinstance
                                is_ai_msg = isinstance(msg, AIMessage)
                                msg_type = getattr(msg, 'type', None) or msg.__class__.__name__
                                logger.info(f"Message type: {msg_type}, is AIMessage: {is_ai_msg}")

                                if is_ai_msg and hasattr(msg, 'content') and msg.content:
                                    # Insert AI response into agent_messages
                                    ai_msg_id = str(uuid4())
                                    ai_msg_timestamp = datetime.now(timezone.utc).isoformat()
                                    agent_role = getattr(msg, 'name', None) or msg.additional_kwargs.get('agent_role', 'partner')

                                    ai_message_record = {
                                        "id": ai_msg_id,
                                        "task_id": task_id,
                                        "agent_role": agent_role,
                                        "content": msg.content,
                                        "message_type": "response",
                                        "metadata": {},
                                        "created_at": ai_msg_timestamp
                                    }

                                    supabase.table("agent_messages").insert(ai_message_record).execute()
                                    logger.info(f"AI response inserted: {ai_msg_id}")

                            # If no AI messages were found, create a summary from the audit_plan
                            if not any(isinstance(m, AIMessage) for m in result_messages):
                                audit_plan = result.get("audit_plan", {})
                                tasks = result.get("tasks", [])

                                if audit_plan or tasks:
                                    summary_content = "감사 계획이 수립되었습니다.\n\n"
                                    if audit_plan.get("summary"):
                                        summary_content += f"**요약:** {audit_plan['summary']}\n\n"
                                    if tasks:
                                        summary_content += f"**생성된 감사 작업:** {len(tasks)}개\n"
                                        for i, task in enumerate(tasks[:5], 1):
                                            task_desc = task.get('description', task.get('task_name', 'N/A'))
                                            summary_content += f"  {i}. {task_desc}\n"
                                        if len(tasks) > 5:
                                            summary_content += f"  ... 외 {len(tasks) - 5}개\n"

                                    summary_msg_id = str(uuid4())
                                    summary_msg_timestamp = datetime.now(timezone.utc).isoformat()
                                    summary_record = {
                                        "id": summary_msg_id,
                                        "task_id": task_id,
                                        "agent_role": "partner",
                                        "content": summary_content,
                                        "message_type": "response",
                                        "metadata": {"auto_generated": True},
                                        "created_at": summary_msg_timestamp
                                    }
                                    supabase.table("agent_messages").insert(summary_record).execute()
                                    logger.info(f"Auto-generated summary inserted: {summary_msg_id}")

                        except Exception as graph_error:
                            import traceback
                            logger.error(f"LangGraph invocation error for task {task_id}: {graph_error}")
                            logger.error(f"Full traceback: {traceback.format_exc()}")
                            # Insert error message for user feedback
                            error_msg_id = str(uuid4())
                            error_msg_timestamp = datetime.now(timezone.utc).isoformat()
                            error_message_record = {
                                "id": error_msg_id,
                                "task_id": task_id,
                                "agent_role": "system",
                                "content": f"Error processing message: {str(graph_error)}",
                                "message_type": "response",
                                "metadata": {"error": True},
                                "created_at": error_msg_timestamp
                            }
                            supabase.table("agent_messages").insert(error_message_record).execute()
                else:
                    logger.warning("LangGraph instance not initialized in app state")

            except Exception as msg_error:
                logger.error(f"Error processing message for task {task_id}: {msg_error}")
                # Continue to polling even if message processing fails

        try:
            logger.info(f"SSE stream started for task {task_id}")

            # Stream messages and heartbeats
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 30  # seconds
            poll_interval = 1.0  # seconds

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream for task {task_id}")
                    break

                # Check for test-injected messages first (non-blocking)
                try:
                    message_event = message_queue.get_nowait()
                    yield message_event
                    continue
                except asyncio.QueueEmpty:
                    pass

                # Poll database for new messages
                try:
                    query = supabase.table("agent_messages") \
                        .select("id, agent_role, content, created_at") \
                        .eq("task_id", task_id) \
                        .order("created_at", desc=False)

                    # Filter by timestamp if we have a last check time
                    if last_check_time:
                        query = query.gt("created_at", last_check_time)

                    result = query.execute()

                    if result.data:
                        for db_msg in result.data:
                            msg_id = db_msg.get("id")

                            # Skip already-seen messages
                            if msg_id in seen_message_ids:
                                continue

                            seen_message_ids.add(msg_id)

                            # Update last check time
                            msg_timestamp = db_msg.get("created_at")
                            if msg_timestamp:
                                last_check_time = msg_timestamp

                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "id": msg_id,
                                    "agent_role": db_msg.get("agent_role"),
                                    "content": db_msg.get("content"),
                                    "timestamp": msg_timestamp
                                })
                            }

                except Exception as db_error:
                    logger.error(f"Database query error for task {task_id}: {db_error}")
                    # Continue polling, don't break the stream

                # Send heartbeat if interval exceeded
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": current_time})
                    }
                    last_heartbeat = current_time

                # Wait before next poll
                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"SSE stream error for task {task_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())
