"""
LangGraph State Definitions

This module defines the state structures for the hierarchical multi-agent audit system:
- AuditState: Parent graph global state
- TaskState: Manager subgraph state for individual audit tasks
"""

from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AuditState(TypedDict):
    """
    Parent graph global state.

    This state is shared across the entire audit project and managed by the Partner agent.
    It coordinates the overall audit strategy and task distribution via Send API.
    """

    # 1. Conversation history (Partner ↔ User)
    messages: Annotated[list[BaseMessage], add_messages]

    # 2. Overall audit information
    project_id: str
    client_name: str
    fiscal_year: int
    overall_materiality: float
    audit_plan: Dict[str, Any]  # Partner's strategic plan

    # 3. Task management (100+ tasks)
    tasks: List[Dict[str, Any]]  # Metadata for each task (id, thread_id, status, risk_score)

    # 4. Human-in-the-loop state
    next_action: str  # "WAIT_FOR_APPROVAL" | "CONTINUE" | "INTERRUPT"
    is_approved: bool

    # 5. Shared knowledge base
    shared_documents: List[Dict[str, Any]]  # Uploaded file metadata


class TaskState(TypedDict):
    """
    Manager subgraph state (per task).

    Each Manager subgraph manages one audit task with its own independent thread_id.
    The Blackboard pattern is used for Staff agent collaboration.

    CRITICAL: thread_id is the unique identifier that connects LangGraph checkpoints
    to Supabase audit_tasks table.
    """

    # Task identification
    task_id: str
    thread_id: str  # CRITICAL: LangGraph thread_id
    category: str   # Account category (e.g., "Sales", "Inventory", "AR")

    # Task status
    status: str     # "Pending" | "In-Progress" | "Review-Required" | "Completed" | "Failed"

    # Conversation history (Manager ↔ Staff agents)
    messages: Annotated[list[BaseMessage], add_messages]

    # Staff agent workspace (Blackboard pattern)
    # Each Staff agent fills its designated field
    raw_data: Dict[str, Any]         # Excel_Parser output
    standards: List[str]             # Standard_Retriever output
    vouching_logs: List[Dict]        # Vouching_Assistant output
    workpaper_draft: str             # WorkPaper_Generator output

    # Manager control
    next_staff: str         # Next Staff agent to execute
    error_report: str       # Error details if task fails
    risk_score: int         # AI-assessed risk score (0-100)
