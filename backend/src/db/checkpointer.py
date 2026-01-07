"""LangGraph PostgresSaver Integration

This module configures PostgresSaver to persist LangGraph workflow checkpoints
in Supabase's PostgreSQL database. Critical for:
1. Workflow resumption after interrupts (HITL)
2. Multi-session workflow continuity
3. Debugging and state inspection

PostgresSaver automatically creates:
- checkpoints table (stores full state snapshots)
- checkpoint_writes table (stores individual state updates)

Reference: /libs/checkpoint-postgres/langgraph/checkpoint/postgres/__init__.py
"""

from langgraph.checkpoint.postgres import PostgresSaver
import os
from dotenv import load_dotenv
from typing import Optional, ContextManager
from contextlib import contextmanager

load_dotenv()


@contextmanager
def get_checkpointer() -> ContextManager[PostgresSaver]:
    """Initialize PostgresSaver with Supabase Postgres connection.

    Returns:
        ContextManager[PostgresSaver]: Context manager for checkpointer instance

    Raises:
        ValueError: If POSTGRES_CONNECTION_STRING is not set

    Usage:
        ```python
        from src.db.checkpointer import get_checkpointer
        from src.graph.graph import create_audit_graph

        with get_checkpointer() as checkpointer:
            graph = create_audit_graph(checkpointer)

            # Execute with thread_id for checkpoint tracking
            config = {"configurable": {"thread_id": "task-001"}}
            result = await graph.ainvoke(state, config)
        ```

    Connection String Format:
        postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

    Environment Variables Required:
        - POSTGRES_CONNECTION_STRING: Direct Postgres connection (NOT Supabase API URL)
    """

    connection_string = os.getenv("POSTGRES_CONNECTION_STRING")

    if not connection_string:
        raise ValueError(
            "POSTGRES_CONNECTION_STRING not found in environment. "
            "Get it from Supabase Dashboard → Project Settings → Database → Connection string (Direct)"
        )

    # PostgresSaver.from_conn_string returns a context manager
    # Yield the checkpointer from the context manager
    with PostgresSaver.from_conn_string(connection_string) as checkpointer:
        yield checkpointer


def setup_checkpoint_tables() -> None:
    """Setup PostgresSaver checkpoint tables (run once on deployment).

    Creates:
        - checkpoints: Stores full state snapshots with thread_id
        - checkpoint_writes: Stores incremental state updates

    This is idempotent - safe to run multiple times.

    Usage:
        ```bash
        # From backend/ directory
        python -c "from src.db.checkpointer import setup_checkpoint_tables; setup_checkpoint_tables()"
        ```
    """
    with get_checkpointer() as checkpointer:
        # PostgresSaver.setup() creates required tables if they don't exist
        checkpointer.setup()

    print("✅ PostgresSaver checkpoint tables created successfully")


def get_checkpoint_by_thread_id(thread_id: str) -> Optional[dict]:
    """Retrieve latest checkpoint for a given thread_id (for debugging).

    Args:
        thread_id: LangGraph thread identifier (e.g., "task-001")

    Returns:
        Latest checkpoint dict or None if not found

    Usage:
        ```python
        from src.db.checkpointer import get_checkpoint_by_thread_id

        checkpoint = get_checkpoint_by_thread_id("task-001")
        if checkpoint:
            print(f"State: {checkpoint['values']}")
        ```
    """
    with get_checkpointer() as checkpointer:
        checkpoint_data = checkpointer.get({"configurable": {"thread_id": thread_id}})
        if checkpoint_data:
            return checkpoint_data.values
        return None
