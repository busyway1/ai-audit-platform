"""Server-Sent Events (SSE) Streaming Endpoint

This module provides real-time streaming of agent messages via SSE.
Integrates with Supabase Realtime for live database change notifications.

Key Endpoint:
    GET /stream/{task_id} - Stream agent messages for specific task

SSE Event Types:
    - "message": New agent message inserted
    - "heartbeat": Keep-alive ping every 30 seconds
    - "error": Error occurred during streaming

Reference: Plan section T3.7, LangGraph SSE pattern
Supabase Realtime: https://supabase.com/docs/guides/realtime/postgres-changes
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from typing import AsyncGenerator, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global message queues (exposed for testing)
# Maps task_id -> asyncio.Queue for message injection
message_queues: Dict[str, asyncio.Queue] = {}


@router.get("/{task_id}")
def stream_agent_messages(task_id: str, request: Request) -> EventSourceResponse:
    """Stream agent messages via SSE for specific task.

    This endpoint establishes a Server-Sent Events connection that streams
    real-time agent messages as they are inserted into the database.

    Args:
        task_id: UUID of the audit task to stream messages for
        request: FastAPI Request object (used for disconnect detection)

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
        const eventSource = new EventSource(`/api/stream/${taskId}`);

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
        - Graceful cleanup of Realtime subscription
    """

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """Generate SSE events from Supabase Realtime.

        Yields:
            Dict with "event" and "data" keys for SSE protocol
        """

        from ..db.supabase_client import supabase

        # Create unique channel for this task
        channel_name = f"task-{task_id}"
        channel = None

        try:
            # Subscribe to INSERT events on agent_messages table
            channel = supabase.channel(channel_name)

            # Get or create message queue for this task (shared with tests)
            if task_id not in message_queues:
                message_queues[task_id] = asyncio.Queue()
            message_queue = message_queues[task_id]

            def on_insert(payload: Dict[str, Any]) -> None:
                """Handle new message insert from Realtime.

                Args:
                    payload: Realtime payload with "new" key containing inserted row
                """
                try:
                    message = payload.get("new", {})

                    # Only send if message belongs to this task
                    if message.get("task_id") == task_id:
                        # Put message in queue for async processing
                        asyncio.create_task(message_queue.put({
                            "event": "message",
                            "data": json.dumps({
                                "id": message.get("id"),
                                "agent_role": message.get("agent_role"),
                                "content": message.get("content"),
                                "timestamp": message.get("created_at")
                            })
                        }))
                except Exception as e:
                    logger.error(f"Error processing message insert: {e}")

            # Subscribe to Realtime changes
            channel.on("INSERT", on_insert).subscribe()

            logger.info(f"SSE stream started for task {task_id}")

            # Stream messages and heartbeats
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 30  # seconds

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream for task {task_id}")
                    break

                # Check if new message is available (non-blocking)
                try:
                    message_event = await asyncio.wait_for(
                        message_queue.get(),
                        timeout=1.0  # Check every second
                    )
                    yield message_event
                except asyncio.TimeoutError:
                    # No message received, continue to heartbeat check
                    pass

                # Send heartbeat if interval exceeded
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                    }
                    last_heartbeat = current_time

        except Exception as e:
            logger.error(f"SSE stream error for task {task_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

        finally:
            # Cleanup: Unsubscribe from Realtime channel
            if channel:
                try:
                    channel.unsubscribe()
                    logger.info(f"Unsubscribed from channel {channel_name}")
                except Exception as e:
                    logger.error(f"Error unsubscribing from channel: {e}")

    return EventSourceResponse(event_generator())
