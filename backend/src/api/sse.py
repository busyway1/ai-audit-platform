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
import os

logger = logging.getLogger(__name__)

# Simple chat LLM for ad-hoc messages (bypasses complex audit graph)
_chat_llm = None

def get_chat_llm():
    """Get or create a simple chat LLM for ad-hoc messages."""
    global _chat_llm
    if _chat_llm is None:
        from langchain_openai import ChatOpenAI
        _chat_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )
    return _chat_llm


CHAT_SYSTEM_PROMPT = """You are an AI audit assistant for the AI Audit Platform.
You help users with audit-related questions and tasks.

Your capabilities include:
- Explaining audit concepts and procedures
- Discussing K-IFRS (Korean International Financial Reporting Standards)
- Discussing K-GAAS (Korean Generally Accepted Auditing Standards)
- Helping with audit planning and risk assessment
- Answering general questions about accounting and auditing

Be professional, helpful, and concise in your responses.
Respond in Korean if the user's message is in Korean.
"""

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

                # 2. Use simple chat LLM for ad-hoc messages
                # NOTE: The full audit graph has HITL interrupts which block execution.
                # For ad-hoc chat, we use a simple LLM call instead.
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    # Get the chat LLM
                    chat_llm = get_chat_llm()

                    # Get recent conversation history for context
                    history_messages = []
                    try:
                        history_result = supabase.table("agent_messages") \
                            .select("agent_role, content") \
                            .eq("task_id", task_id) \
                            .order("created_at", desc=True) \
                            .limit(10) \
                            .execute()

                        if history_result.data:
                            # Reverse to get chronological order
                            for msg in reversed(history_result.data):
                                if msg.get("agent_role") == "user":
                                    history_messages.append(HumanMessage(content=msg.get("content", "")))
                                else:
                                    from langchain_core.messages import AIMessage
                                    history_messages.append(AIMessage(content=msg.get("content", "")))
                    except Exception as history_err:
                        logger.warning(f"Could not fetch message history: {history_err}")

                    # Build messages for LLM
                    llm_messages = [
                        SystemMessage(content=CHAT_SYSTEM_PROMPT),
                        *history_messages[-6:],  # Last 6 messages for context
                        HumanMessage(content=decoded_message)
                    ]

                    logger.info(f"Invoking chat LLM for task {task_id}")

                    # Invoke the LLM
                    response = await chat_llm.ainvoke(llm_messages)
                    ai_content = response.content

                    logger.info(f"Chat LLM response received for task {task_id}: {ai_content[:100]}...")

                    # Insert AI response into agent_messages
                    ai_msg_id = str(uuid4())
                    ai_msg_timestamp = datetime.now(timezone.utc).isoformat()
                    ai_message_record = {
                        "id": ai_msg_id,
                        "task_id": task_id,
                        "agent_role": "partner",
                        "content": ai_content,
                        "message_type": "response",
                        "metadata": {"source": "chat_llm"},
                        "created_at": ai_msg_timestamp
                    }

                    insert_result = supabase.table("agent_messages").insert(ai_message_record).execute()
                    if insert_result.data:
                        logger.info(f"AI response inserted: {ai_msg_id}")
                    else:
                        logger.error(f"Failed to insert AI response for task {task_id}")

                except Exception as chat_error:
                    import traceback
                    logger.error(f"Chat LLM error for task {task_id}: {chat_error}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Insert error message for user feedback
                    error_msg_id = str(uuid4())
                    error_msg_timestamp = datetime.now(timezone.utc).isoformat()
                    error_message_record = {
                        "id": error_msg_id,
                        "task_id": task_id,
                        "agent_role": "system",
                        "content": f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(chat_error)}",
                        "message_type": "response",
                        "metadata": {"error": True},
                        "created_at": error_msg_timestamp
                    }
                    supabase.table("agent_messages").insert(error_message_record).execute()

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
