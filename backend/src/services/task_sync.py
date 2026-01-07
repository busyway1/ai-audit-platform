"""
Task State Synchronization Service

This module provides functionality to sync LangGraph TaskState to Supabase tables.
It handles the synchronization of audit tasks, agent messages, and audit artifacts
between the in-memory graph state and the persistent database.

Key Functions:
    - sync_task_to_supabase: Upsert task state to audit_tasks and related tables
    - get_task_by_thread_id: Retrieve task data by thread_id
"""

from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from ..db.supabase_client import supabase
from ..graph.state import TaskState, AuditState


async def sync_task_to_supabase(
    task_state: TaskState,
    project_id: str
) -> str:
    """
    Synchronize TaskState to Supabase tables.

    This function performs the following operations:
    1. Upserts task data to audit_tasks table (using thread_id as unique key)
    2. Inserts agent messages to agent_messages table
    3. Inserts workpaper artifact if it exists

    Args:
        task_state: The current task state from LangGraph
        project_id: UUID of the associated project

    Returns:
        str: The task_id (UUID) of the upserted task

    Raises:
        Exception: If database operations fail

    Examples:
        >>> task_id = await sync_task_to_supabase(task_state, "proj-123")
        >>> print(f"Synced task: {task_id}")
    """
    # Extract thread_id from task_state
    thread_id = task_state.get("thread_id")
    if not thread_id:
        raise ValueError("TaskState must contain thread_id")

    # Prepare task data for upsert (match database schema from 001_initial_schema.sql)
    task_data = {
        "thread_id": thread_id,
        "project_id": project_id,
        "category": task_state.get("category", "General"),  # Account category (e.g., "Sales", "Inventory")
        "status": task_state.get("status", "Pending"),  # "Pending", "In-Progress", "Review-Required", "Completed", "Failed"
        "risk_score": task_state.get("risk_score", 50),  # 0-100
        "assignees": [],  # JSONB array - will be populated by Manager agent
        "metadata": {
            # Store additional TaskState fields in metadata JSONB
            "next_staff": task_state.get("next_staff"),
            "error_report": task_state.get("error_report"),
            "has_raw_data": bool(task_state.get("raw_data")),
            "has_standards": bool(task_state.get("standards")),
            "has_vouching_logs": bool(task_state.get("vouching_logs")),
            "has_workpaper_draft": bool(task_state.get("workpaper_draft")),
        },
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Upsert to audit_tasks table (on conflict, update existing row)
    response = (
        supabase.table("audit_tasks")
        .upsert(task_data, on_conflict="thread_id")
        .execute()
    )

    if not response.data:
        raise Exception("Failed to upsert task to audit_tasks table")

    task_id = response.data[0]["id"]

    # Sync agent messages
    await _sync_agent_messages(task_state, task_id)

    # Sync workpaper artifact if exists
    await _sync_workpaper_artifact(task_state, task_id)

    return task_id


async def get_task_by_thread_id(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve task data by thread_id.

    Args:
        thread_id: The unique thread identifier

    Returns:
        Optional[Dict[str, Any]]: Task data dict if found, None otherwise

    Examples:
        >>> task = await get_task_by_thread_id("thread-abc-123")
        >>> if task:
        ...     print(f"Found task: {task['id']}")
        ... else:
        ...     print("Task not found")
    """
    response = (
        supabase.table("audit_tasks")
        .select("*")
        .eq("thread_id", thread_id)
        .execute()
    )

    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


async def _sync_agent_messages(
    task_state: TaskState,
    task_id: str
) -> None:
    """
    Insert agent messages to agent_messages table.

    This is a private helper function that extracts messages from TaskState
    and inserts them into the agent_messages table.

    Args:
        task_state: The current task state containing messages
        task_id: UUID of the associated task

    Raises:
        Exception: If message insertion fails
    """
    messages = task_state.get("messages", [])

    if not messages:
        return  # No messages to sync

    # Prepare message records
    message_records = []
    for msg in messages:
        # Extract agent role from additional_kwargs or default to "Unknown"
        agent_role = msg.additional_kwargs.get("agent_role", "Unknown")

        message_record = {
            "id": str(uuid4()),
            "task_id": task_id,
            "agent_role": agent_role,
            "content": msg.content,
            "message_type": msg.type if hasattr(msg, "type") else "message",
            "created_at": datetime.utcnow().isoformat(),
        }
        message_records.append(message_record)

    # Insert all messages in batch
    if message_records:
        response = (
            supabase.table("agent_messages")
            .insert(message_records)
            .execute()
        )

        if not response.data:
            raise Exception("Failed to insert agent messages")


async def _sync_workpaper_artifact(
    task_state: TaskState,
    task_id: str
) -> None:
    """
    Insert workpaper artifact if it exists in TaskState.

    This is a private helper function that checks for a workpaper draft
    in the task state and inserts it as an audit artifact.

    Args:
        task_state: The current task state
        task_id: UUID of the associated task

    Raises:
        Exception: If artifact insertion fails
    """
    workpaper_draft = task_state.get("workpaper_draft")

    if not workpaper_draft:
        return  # No workpaper to sync

    # Prepare artifact record
    artifact_record = {
        "id": str(uuid4()),
        "task_id": task_id,
        "artifact_type": "workpaper",
        "content": workpaper_draft,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Insert artifact
    response = (
        supabase.table("audit_artifacts")
        .insert(artifact_record)
        .execute()
    )

    if not response.data:
        raise Exception("Failed to insert workpaper artifact")
