"""Supabase Client Configuration

This module provides authenticated Supabase client for backend operations.
Uses service_role key for admin-level access (bypasses RLS).

CRITICAL: Never expose service_role key to frontend - frontend uses anon key.

Reference: https://supabase.com/docs/reference/python/initializing
"""

from supabase import create_client, Client  # type: ignore[attr-defined]
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


def get_supabase_client() -> Client:
    """Get authenticated Supabase client with service_role key.

    Returns:
        Client: Supabase client with admin privileges

    Raises:
        ValueError: If required environment variables are not set

    Usage:
        ```python
        from src.db.supabase_client import supabase

        # Insert task
        result = supabase.table("audit_tasks").insert({
            "project_id": "uuid-here",
            "thread_id": "task-001",
            "category": "Sales",
            "status": "In-Progress"
        }).execute()

        # Query tasks
        tasks = supabase.table("audit_tasks") \\
            .select("*") \\
            .eq("project_id", project_id) \\
            .execute()
        ```

    Environment Variables Required:
        - SUPABASE_URL: Project URL (https://xxx.supabase.co)
        - SUPABASE_SERVICE_KEY: Service role key (starts with "eyJhbG...")
    """

    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url:
        raise ValueError(
            "SUPABASE_URL not found in environment. "
            "Get it from Supabase Dashboard → Project Settings → API → Project URL"
        )

    if not service_key:
        raise ValueError(
            "SUPABASE_SERVICE_KEY not found in environment. "
            "Get it from Supabase Dashboard → Project Settings → API → service_role (secret)"
        )

    # Create client with service_role key
    # This bypasses Row Level Security (RLS) - use with caution
    return create_client(url, service_key)


# Global client instance (singleton pattern)
# Import this in other modules: from src.db.supabase_client import supabase
supabase: Client = get_supabase_client()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_connection() -> bool:
    """Health check for Supabase connection.

    Returns:
        bool: True if connection successful, False otherwise

    Usage:
        ```python
        from src.db.supabase_client import check_connection

        if await check_connection():
            print("✅ Supabase connected")
        else:
            print("❌ Supabase connection failed")
        ```
    """
    try:
        # Simple query to test connection
        result = supabase.table("audit_projects").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase connection error: {e}")
        return False


def get_project_by_id(project_id: str) -> Optional[dict]:
    """Retrieve audit project by ID.

    Args:
        project_id: UUID of the project

    Returns:
        Project dict or None if not found

    Example:
        ```python
        project = get_project_by_id("123e4567-e89b-12d3-a456-426614174000")
        if project:
            print(f"Client: {project['client_name']}")
        ```
    """
    try:
        result = supabase.table("audit_projects") \
            .select("*") \
            .eq("id", project_id) \
            .execute()

        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error fetching project: {e}")
        return None


def get_tasks_by_project(project_id: str) -> list[dict]:
    """Retrieve all tasks for a project.

    Args:
        project_id: UUID of the project

    Returns:
        List of task dicts

    Example:
        ```python
        tasks = get_tasks_by_project("123e4567-e89b-12d3-a456-426614174000")
        for task in tasks:
            print(f"{task['category']}: {task['status']}")
        ```
    """
    try:
        result = supabase.table("audit_tasks") \
            .select("*") \
            .eq("project_id", project_id) \
            .order("created_at", desc=False) \
            .execute()

        return result.data or []
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []


def get_task_by_thread_id(thread_id: str) -> Optional[dict]:
    """Retrieve task by LangGraph thread_id.

    Args:
        thread_id: LangGraph thread identifier (e.g., "task-001")

    Returns:
        Task dict or None if not found

    Example:
        ```python
        task = get_task_by_thread_id("task-sales-001")
        if task:
            print(f"Status: {task['status']}")
        ```
    """
    try:
        result = supabase.table("audit_tasks") \
            .select("*") \
            .eq("thread_id", thread_id) \
            .execute()

        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error fetching task by thread_id: {e}")
        return None


def get_messages_by_task(task_id: str, limit: int = 100) -> list[dict]:
    """Retrieve agent messages for a task.

    Args:
        task_id: UUID of the task
        limit: Maximum number of messages to retrieve (default: 100)

    Returns:
        List of message dicts sorted by creation time

    Example:
        ```python
        messages = get_messages_by_task("task-uuid", limit=50)
        for msg in messages:
            print(f"[{msg['agent_role']}] {msg['content']}")
        ```
    """
    try:
        result = supabase.table("agent_messages") \
            .select("*") \
            .eq("task_id", task_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()

        return result.data or []
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []


# ============================================================================
# CRITICAL NOTES
# ============================================================================

"""
Service Role vs. Anon Key:

1. Service Role Key (Backend):
   - Admin privileges - bypasses all RLS policies
   - Can read/write any data regardless of user permissions
   - NEVER expose to frontend or client-side code
   - Use for backend operations, agent automation, admin tasks

2. Anon Key (Frontend):
   - Limited by RLS policies (auth.uid() checks)
   - Users can only access their own projects/tasks
   - Safe to expose in client-side code
   - Used in frontend for user-facing operations

Environment Setup:
    # .env file
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJhbG...   # Backend only
    SUPABASE_ANON_KEY=eyJhbG...       # Frontend only

RLS Policy Behavior:
    - With service_role: All queries succeed (admin mode)
    - With anon key: Queries filtered by RLS policies

      # This query with anon key only returns user's projects
      projects = supabase.table("audit_projects").select("*").execute()

      # This query with service_role returns ALL projects
      projects = supabase.table("audit_projects").select("*").execute()

Best Practices:
    1. Always use service_role in backend for agent operations
    2. Never log service_role key (even in error messages)
    3. Implement additional auth checks in FastAPI routes if needed
    4. Use RLS policies as defense-in-depth (even with service_role)

Performance:
    - Connection pooling handled by supabase-py library
    - Safe to import global 'supabase' instance across modules
    - For 100+ concurrent operations, consider connection pool tuning
"""
