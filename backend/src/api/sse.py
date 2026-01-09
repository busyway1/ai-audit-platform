"""Server-Sent Events (SSE) Streaming Endpoint

This module provides real-time streaming of agent messages via SSE.
Uses polling-based approach to query database for new messages.
Supports message processing through LangGraph when a message query parameter is provided.
Integrates MCP server tools for ad-hoc tool usage (RAG, Excel, Finance calculations).

Key Endpoint:
    GET /stream/{task_id} - Stream agent messages for specific task
    GET /stream/{task_id}?message=... - Process message through LangGraph and stream responses

SSE Event Types:
    - "message": New agent message inserted
    - "heartbeat": Keep-alive ping every 30 seconds
    - "error": Error occurred during streaming

MCP Integration:
    - Detects keywords in messages to trigger appropriate MCP tools
    - Stores MCP results in audit_artifacts table
    - Includes MCP context in LLM prompt for enhanced responses

MCP Error Handling Strategy:
    Step 1: Automatic Retry (3 attempts with exponential backoff)
        - 1st retry: wait 1 second
        - 2nd retry: wait 2 seconds
        - 3rd retry: wait 4 seconds
    Step 2: Graceful Degradation
        - If all retries fail, fallback to basic LLM without MCP context
        - Continue chat with degraded capability
        - Log the failure for monitoring
    Step 3: HITL Escalation (for critical failures)
        - If circuit breaker opens, create hitl_requests entry
        - Notify user in chat about service degradation

Reference: Plan section T3.7, LangGraph SSE pattern
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, Optional, Set, Tuple, List
from uuid import uuid4
from urllib.parse import unquote
import logging
import os
import re

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

# MCP Context Template for enhanced responses
MCP_CONTEXT_TEMPLATE = """
[MCP Tool Context]
The following information was retrieved using the {tool_name} tool:
---
{mcp_result}
---
Please use this information to provide a comprehensive response to the user's question.
"""

# ============================================================================
# MCP INTEGRATION
# ============================================================================

# MCP keyword patterns for detection
# NOTE: Order matters! More specific patterns should be checked before general ones.
# Use OrderedDict-like behavior - first match wins.
MCP_KEYWORDS = {
    # Finance calculations - check BEFORE mcp-rag since "중요성 기준" contains "기준"
    "mcp-finance": {
        "patterns": [
            r"감가상각",
            r"depreciation",
            r"중요성",
            r"materiality",
            r"할인율",
            r"discount rate",
            r"현재가치",
            r"present value",
            r"이자율",
            r"interest rate",
            r"재무계산",
            r"financial calculation",
        ],
        "tool": "calculate_materiality",
        "description": "Financial calculations"
    },
    # Excel processing - check BEFORE mcp-rag since "시산표" is specific
    "mcp-excel": {
        "patterns": [
            r"엑셀",
            r"excel",
            r"스프레드시트",
            r"spreadsheet",
            r"시산표",
            r"trial balance",
            r"원장",
            r"ledger",
            r"거래내역",
            r"transaction",
        ],
        "tool": "parse_excel",
        "description": "Excel file processing"
    },
    # Document generation - check BEFORE mcp-rag since "보고서" can overlap
    "mcp-document": {
        "patterns": [
            r"조서",  # More specific - audit workpaper
            r"workpaper",
            r"pdf",
            r"워드",
            r"word",
            r"문서\s*생성",  # "document generation"
            r"문서\s*작성",  # "document creation"
        ],
        "tool": "generate_workpaper",
        "description": "Document generation"
    },
    # RAG search - most general, check LAST
    "mcp-rag": {
        "patterns": [
            r"k-?ifrs",
            r"k-?gaas",
            r"감사기준",  # More specific than just "기준"
            r"회계기준",  # More specific than just "기준"
            r"국제회계기준",
            r"수익인식",
            r"리스",
            r"금융상품",
            r"재무보고",
            r"accounting standard",
            r"audit standard",
            r"(?<!중요성\s)기준(?!\s*계산)",  # "기준" but not after "중요성" or before "계산"
        ],
        "tool": "search_standards",
        "description": "K-IFRS/K-GAAS standards search"
    },
}


async def detect_mcp_need(message: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Detect if message needs MCP tool call based on keywords.

    Analyzes the message for keywords that indicate the need for specific
    MCP server tools (RAG search, finance calculations, Excel processing, etc.)

    Args:
        message: User message to analyze

    Returns:
        Tuple of (server_name, tool_name, arguments) if MCP tool needed,
        None otherwise

    Example:
        >>> await detect_mcp_need("K-IFRS 1115에 대해 설명해주세요")
        ('mcp-rag', 'search_standards', {'query_text': '...', 'top_k': 5})
    """
    message_lower = message.lower()

    # Check each MCP server's keyword patterns
    for server_name, config in MCP_KEYWORDS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.info(f"MCP tool detected: {server_name} ({config['description']})")

                # Build tool-specific arguments
                arguments = _build_mcp_arguments(server_name, config["tool"], message)

                return (server_name, config["tool"], arguments)

    return None


def _build_mcp_arguments(server_name: str, tool_name: str, message: str) -> Dict[str, Any]:
    """Build MCP tool arguments based on server and tool type.

    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        message: Original user message

    Returns:
        Dictionary of tool arguments
    """
    if server_name == "mcp-rag":
        return {
            "query_text": message,
            "top_k": 5,
            "mode": "hybrid"
        }
    elif server_name == "mcp-finance":
        # Extract numbers from message if present for materiality calculation
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', message)
        return {
            "query": message,
            "amounts": [float(n.replace(',', '')) for n in numbers[:3]] if numbers else []
        }
    elif server_name == "mcp-excel":
        return {
            "query": message,
            "validate_data": True
        }
    elif server_name == "mcp-document":
        return {
            "content": message,
            "template": "audit_memo"
        }
    else:
        return {"query": message}


async def execute_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional["MCPError"]]:
    """Execute MCP tool with comprehensive error handling.

    Calls the appropriate MCP client based on server name and executes
    the specified tool with given arguments. Returns both the result
    and any error information for proper error handling.

    Args:
        server_name: Name of the MCP server (mcp-rag, mcp-excel, etc.)
        tool_name: Name of the tool to execute
        arguments: Tool arguments

    Returns:
        Tuple of (result, error):
        - (result, None) if successful
        - (None, MCPError) if failed
    """
    from ..services.mcp_client import (
        MCPError,
        MCPConnectionError,
        MCPToolExecutionError,
        CircuitBreakerOpen
    )

    retries_attempted = 0
    error_type = "unknown"
    error_message = ""

    try:
        if server_name == "mcp-rag":
            from ..services.mcp_client import MCPRagClient

            async with MCPRagClient() as client:
                # Check health first
                if not await client.health_check():
                    logger.warning(
                        f"MCP {server_name}/{tool_name} failed after 0 retries: "
                        "server health check failed"
                    )
                    return None, MCPError(
                        server=server_name,
                        tool=tool_name,
                        error_type="connection",
                        message="MCP RAG server unavailable (health check failed)",
                        retries_attempted=0,
                        fallback_used=False
                    )

                if tool_name == "search_standards":
                    result = await client.search_standards(
                        query_text=arguments.get("query_text", ""),
                        top_k=arguments.get("top_k", 5),
                        mode=arguments.get("mode", "hybrid")
                    )
                    return result, None
                elif tool_name == "get_paragraph_by_id":
                    result = await client.get_paragraph_by_id(
                        standard_id=arguments.get("standard_id", ""),
                        paragraph_no=arguments.get("paragraph_no", "")
                    )
                    return result, None

        elif server_name == "mcp-excel":
            from ..services.mcp_client import MCPExcelClient

            async with MCPExcelClient() as client:
                if not await client.health_check():
                    logger.warning(
                        f"MCP {server_name}/{tool_name} failed after 0 retries: "
                        "server health check failed"
                    )
                    return None, MCPError(
                        server=server_name,
                        tool=tool_name,
                        error_type="connection",
                        message="MCP Excel server unavailable (health check failed)",
                        retries_attempted=0,
                        fallback_used=False
                    )

                # Excel parsing requires file path/URL, return info message if not provided
                if tool_name == "parse_excel":
                    file_path = arguments.get("file_path")
                    file_url = arguments.get("file_url")
                    if not file_path and not file_url:
                        return {
                            "status": "info",
                            "message": "Excel 파일을 분석하려면 파일을 업로드하거나 파일 경로를 제공해주세요."
                        }, None
                    result = await client.parse_excel(
                        file_path=file_path,
                        file_url=file_url,
                        validate_data=arguments.get("validate_data", True)
                    )
                    return result, None

        elif server_name == "mcp-document":
            from ..services.mcp_client import MCPDocumentClient

            async with MCPDocumentClient() as client:
                if not await client.health_check():
                    logger.warning(
                        f"MCP {server_name}/{tool_name} failed after 0 retries: "
                        "server health check failed"
                    )
                    return None, MCPError(
                        server=server_name,
                        tool=tool_name,
                        error_type="connection",
                        message="MCP Document server unavailable (health check failed)",
                        retries_attempted=0,
                        fallback_used=False
                    )

                if tool_name == "generate_workpaper":
                    result = await client.generate_workpaper(
                        content=arguments.get("content", ""),
                        template=arguments.get("template", "audit_memo")
                    )
                    return result, None

        elif server_name == "mcp-finance":
            # Finance calculations (to be implemented when mcp-finance server exists)
            logger.info("MCP Finance server not yet implemented, returning None")
            return None, MCPError(
                server=server_name,
                tool=tool_name,
                error_type="tool_error",
                message="MCP Finance server not yet implemented",
                retries_attempted=0,
                fallback_used=False
            )

        # Unknown server
        return None, MCPError(
            server=server_name,
            tool=tool_name,
            error_type="tool_error",
            message=f"Unknown MCP server: {server_name}",
            retries_attempted=0,
            fallback_used=False
        )

    except CircuitBreakerOpen as e:
        error_type = "circuit_breaker"
        error_message = str(e)
        retries_attempted = 0  # Circuit breaker rejects immediately
        logger.warning(
            f"MCP {server_name}/{tool_name} failed after {retries_attempted} retries: "
            f"circuit breaker open"
        )

    except MCPConnectionError as e:
        error_type = "connection"
        error_message = str(e)
        # Extract retries from error message if available
        retries_attempted = 3  # Default max retries
        logger.warning(
            f"MCP {server_name}/{tool_name} failed after {retries_attempted} retries: "
            f"{error_message}"
        )

    except MCPToolExecutionError as e:
        error_type = "tool_error"
        error_message = str(e)
        retries_attempted = 0  # Tool errors don't retry
        logger.warning(
            f"MCP {server_name}/{tool_name} failed after {retries_attempted} retries: "
            f"{error_message}"
        )

    except asyncio.TimeoutError as e:
        error_type = "timeout"
        error_message = "Request timed out"
        retries_attempted = 3
        logger.warning(
            f"MCP {server_name}/{tool_name} failed after {retries_attempted} retries: "
            f"timeout"
        )

    except Exception as e:
        error_type = "unknown"
        error_message = str(e)
        retries_attempted = 0
        logger.error(
            f"MCP {server_name}/{tool_name} failed after {retries_attempted} retries: "
            f"{error_message}"
        )

    return None, MCPError(
        server=server_name,
        tool=tool_name,
        error_type=error_type,
        message=error_message,
        retries_attempted=retries_attempted,
        fallback_used=False,
        original_exception=e if 'e' in dir() else None
    )


async def escalate_to_hitl(
    task_id: str,
    mcp_error: "MCPError",
    original_message: str
) -> Optional[str]:
    """Escalate critical MCP failure to Human-in-the-Loop (HITL).

    Creates an entry in the hitl_requests table for human intervention
    when MCP tools fail critically and fallback is insufficient.

    Args:
        task_id: UUID of the audit task
        mcp_error: Structured error information
        original_message: The original user message that triggered the failure

    Returns:
        HITL request ID if created successfully, None otherwise
    """
    try:
        from ..db.supabase_client import supabase

        hitl_id = str(uuid4())
        hitl_record = {
            "id": hitl_id,
            "task_id": task_id,
            "request_type": "mcp_failure",
            "status": "pending",
            "context": {
                "original_message": original_message,
                "mcp_error": mcp_error.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "priority": "high" if mcp_error.error_type == "circuit_breaker" else "medium",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Try to insert into hitl_requests table
        insert_result = supabase.table("hitl_requests").insert(hitl_record).execute()

        if insert_result.data:
            logger.error(
                f"Critical MCP failure, escalating to HITL: {mcp_error}"
            )
            return hitl_id
        else:
            logger.warning(
                f"Failed to create HITL request for task {task_id}: no data returned"
            )
            return None

    except Exception as e:
        # HITL table might not exist yet, log but don't fail
        logger.warning(
            f"Could not escalate to HITL (table may not exist): {e}"
        )
        return None


def create_mcp_error_message(mcp_error: "MCPError", fallback_used: bool) -> Dict[str, Any]:
    """Create a user-friendly error message for MCP failures.

    Args:
        mcp_error: Structured error information
        fallback_used: Whether fallback to basic LLM was used

    Returns:
        Dictionary with message content and metadata for SSE
    """
    if fallback_used:
        content = "MCP 서버 연결에 일시적인 문제가 발생했습니다. 기본 AI로 응답합니다."
    else:
        # More specific error messages based on error type
        error_messages = {
            "connection": "MCP 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
            "timeout": "MCP 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
            "circuit_breaker": "MCP 서버가 일시적으로 비활성화되었습니다. 잠시 후 자동으로 복구됩니다.",
            "tool_error": "MCP 도구 실행 중 오류가 발생했습니다.",
        }
        content = error_messages.get(
            mcp_error.error_type,
            "MCP 서버 오류가 발생했습니다. 기본 AI로 응답합니다."
        )

    return {
        "agent_role": "system",
        "content": content,
        "metadata": {
            "mcp_error": True,
            "fallback": fallback_used,
            "error_type": mcp_error.error_type,
            "server": mcp_error.server,
            "tool": mcp_error.tool
        }
    }


async def store_mcp_result(
    task_id: str,
    server_name: str,
    tool_name: str,
    result: Dict[str, Any]
) -> Optional[str]:
    """Store MCP result in audit_artifacts table.

    Persists MCP tool results for audit trail and future reference.

    Args:
        task_id: UUID of the audit task
        server_name: Name of the MCP server used
        tool_name: Name of the tool executed
        result: Tool execution result

    Returns:
        Artifact ID if stored successfully, None otherwise
    """
    try:
        from ..db.supabase_client import supabase

        artifact_id = str(uuid4())
        artifact_record = {
            "id": artifact_id,
            "thread_id": task_id,  # Using task_id as thread_id (required NOT NULL)
            "artifact_type": "memo",  # MCP results stored as memos
            "content": json.dumps(result, ensure_ascii=False, default=str),
            "metadata": {
                "source": "mcp",
                "server": server_name,
                "tool": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        insert_result = supabase.table("audit_artifacts").insert(artifact_record).execute()

        if insert_result.data:
            logger.info(f"MCP result stored as artifact: {artifact_id}")
            return artifact_id
        else:
            logger.warning(f"Failed to store MCP result for task {task_id}")
            return None

    except Exception as e:
        logger.error(f"Error storing MCP result: {e}")
        return None


def format_mcp_result_for_context(
    server_name: str,
    tool_name: str,
    result: Dict[str, Any]
) -> str:
    """Format MCP result for inclusion in LLM context.

    Converts MCP tool results into a human-readable format suitable
    for inclusion in the LLM prompt context.

    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool executed
        result: Tool execution result

    Returns:
        Formatted string for LLM context
    """
    if not result:
        return ""

    # Handle RAG search results
    if server_name == "mcp-rag" and tool_name == "search_standards":
        data = result.get("data", {})
        results_list = data.get("results", [])

        if not results_list:
            return ""

        formatted_results = []
        for i, r in enumerate(results_list[:5], 1):  # Top 5 results
            standard_id = r.get("standard_id", "Unknown")
            paragraph_no = r.get("paragraph_no", "")
            content = r.get("content", "")[:500]  # Truncate long content

            formatted_results.append(
                f"{i}. [{standard_id} {paragraph_no}]\n{content}"
            )

        tool_display = f"{server_name}/{tool_name}"
        mcp_result_text = "\n\n".join(formatted_results)

        return MCP_CONTEXT_TEMPLATE.format(
            tool_name=tool_display,
            mcp_result=mcp_result_text
        )

    # Handle Excel parsing results
    elif server_name == "mcp-excel":
        data = result.get("data", {})
        if result.get("status") == "info":
            return f"\n[MCP Info] {result.get('message', '')}\n"

        summary = data.get("summary", {})
        if summary:
            tool_display = f"{server_name}/{tool_name}"
            summary_text = (
                f"Category: {data.get('category', 'N/A')}\n"
                f"Total Amount: {data.get('total_amount', 0):,.2f}\n"
                f"Transaction Count: {data.get('transaction_count', 0)}\n"
                f"Data Quality: {data.get('data_quality', 'N/A')}"
            )
            return MCP_CONTEXT_TEMPLATE.format(
                tool_name=tool_display,
                mcp_result=summary_text
            )

    # Handle document generation results
    elif server_name == "mcp-document":
        data = result.get("data", {})
        if data.get("file_url"):
            tool_display = f"{server_name}/{tool_name}"
            doc_info = f"Document generated: {data.get('file_name', 'document')}"
            return MCP_CONTEXT_TEMPLATE.format(
                tool_name=tool_display,
                mcp_result=doc_info
            )

    # Generic fallback formatting
    else:
        status = result.get("status", "unknown")
        if status == "success" and result.get("data"):
            tool_display = f"{server_name}/{tool_name}"
            return MCP_CONTEXT_TEMPLATE.format(
                tool_name=tool_display,
                mcp_result=json.dumps(result.get("data"), ensure_ascii=False, indent=2)[:1000]
            )

    return ""

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

                # 2. Use simple chat LLM for ad-hoc messages with MCP integration
                # NOTE: The full audit graph has HITL interrupts which block execution.
                # For ad-hoc chat, we use a simple LLM call instead.
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    # Get the chat LLM
                    chat_llm = get_chat_llm()

                    # ====================================
                    # MCP TOOL DETECTION AND EXECUTION
                    # ====================================
                    mcp_context = ""
                    mcp_result = None
                    mcp_error = None
                    fallback_used = False
                    mcp_detection = await detect_mcp_need(decoded_message)

                    if mcp_detection:
                        server_name, tool_name, arguments = mcp_detection
                        logger.info(
                            f"MCP tool needed for task {task_id}: "
                            f"{server_name}/{tool_name}"
                        )

                        # Execute MCP tool with error handling
                        mcp_result, mcp_error = await execute_mcp_tool(
                            server_name, tool_name, arguments
                        )

                        if mcp_result and not mcp_error:
                            # Success: Store MCP result in database for audit trail
                            await store_mcp_result(
                                task_id, server_name, tool_name, mcp_result
                            )

                            # Format result for LLM context
                            mcp_context = format_mcp_result_for_context(
                                server_name, tool_name, mcp_result
                            )

                            logger.info(
                                f"MCP context added for task {task_id}: "
                                f"{len(mcp_context)} chars"
                            )
                        elif mcp_error:
                            # MCP failed - apply graceful degradation
                            fallback_used = True
                            mcp_error.fallback_used = True

                            logger.info(
                                f"Falling back to basic LLM for {task_id}"
                            )

                            # Insert system message about MCP error
                            error_msg_data = create_mcp_error_message(mcp_error, fallback_used)
                            error_msg_id = str(uuid4())
                            error_msg_timestamp = datetime.now(timezone.utc).isoformat()

                            error_message_record = {
                                "id": error_msg_id,
                                "task_id": task_id,
                                "agent_role": error_msg_data["agent_role"],
                                "content": error_msg_data["content"],
                                "message_type": "system",
                                "metadata": error_msg_data["metadata"],
                                "created_at": error_msg_timestamp
                            }
                            supabase.table("agent_messages").insert(error_message_record).execute()

                            # Escalate to HITL for critical errors (circuit breaker open)
                            if mcp_error.error_type == "circuit_breaker":
                                await escalate_to_hitl(
                                    task_id, mcp_error, decoded_message
                                )
                        else:
                            logger.info(
                                f"MCP tool returned no result for task {task_id}"
                            )

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

                    # Build system prompt with MCP context if available
                    enhanced_system_prompt = CHAT_SYSTEM_PROMPT
                    if mcp_context:
                        enhanced_system_prompt = CHAT_SYSTEM_PROMPT + "\n" + mcp_context

                    # Build messages for LLM
                    llm_messages = [
                        SystemMessage(content=enhanced_system_prompt),
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

                    # Build metadata with MCP tool info if used
                    response_metadata = {"source": "chat_llm"}
                    if mcp_detection:
                        response_metadata["mcp_tool"] = {
                            "server": mcp_detection[0],
                            "tool": mcp_detection[1],
                            "used": mcp_result is not None and not mcp_error,
                            "fallback": fallback_used
                        }
                        if mcp_error:
                            response_metadata["mcp_error"] = mcp_error.to_dict()

                    ai_message_record = {
                        "id": ai_msg_id,
                        "task_id": task_id,
                        "agent_role": "partner",
                        "content": ai_content,
                        "message_type": "response",
                        "metadata": response_metadata,
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
