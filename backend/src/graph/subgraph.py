"""Manager Subgraph Implementation

Manager Subgraph Architecture:
- Orchestrates 4 Staff agents sequentially
- Each Staff fills its designated field in TaskState (Blackboard pattern)
- Manager reviews after each Staff and decides next action
- Uses PostgresSaver for checkpoint persistence
- Aggregates all Staff results at the end

Sequential Flow:
    START → Excel_Parser → Standard_Retriever → Vouching_Assistant
    → WorkPaper_Generator → Manager_Aggregator → END

Reference: Section 4.3 & 4.4 of AUDIT_PLATFORM_SPECIFICATION.md
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from ..graph.state import TaskState
from ..agents.manager_agent import ManagerAgent


# ============================================================================
# IMPORT REAL STAFF AGENTS
# ============================================================================
from ..agents.staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent
)


# ============================================================================
# AGGREGATOR FUNCTION
# ============================================================================

def aggregate_results(state: TaskState) -> Dict[str, Any]:
    """Manager reviews all Staff outputs and updates task status.

    This is the final node in the Manager Subgraph. It validates that all
    Staff agents have completed their work and updates the task status accordingly.

    Validation checks:
    1. raw_data is populated (Excel_Parser completed)
    2. standards is populated (Standard_Retriever completed)
    3. vouching_logs is populated (Vouching_Assistant completed)
    4. workpaper_draft is populated (WorkPaper_Generator completed)

    Args:
        state: TaskState after all Staff have executed

    Returns:
        Updated state with final status and next_staff set to None

    Success Criteria:
        All 4 fields populated → status="Completed", next_staff=None
        Any field missing → status="Failed", error_report with details
    """
    from langchain_core.messages import HumanMessage

    has_data = bool(state.get("raw_data"))
    has_standards = bool(state.get("standards"))
    has_vouching = bool(state.get("vouching_logs"))
    has_workpaper = bool(state.get("workpaper_draft"))

    # Calculate risk score based on vouching results
    vouching_logs = state.get("vouching_logs", [])
    total_transactions = len(vouching_logs)
    exceptions = sum(1 for log in vouching_logs if log.get("status") == "Exception")

    if total_transactions > 0:
        exception_rate = exceptions / total_transactions
        if exception_rate > 0.3:
            risk_score = 80  # High risk
        elif exception_rate > 0.1:
            risk_score = 50  # Medium risk
        else:
            risk_score = 20  # Low risk
    else:
        risk_score = 0

    if all([has_data, has_standards, has_vouching, has_workpaper]):
        # All Staff completed successfully
        return {
            "status": "Completed",
            "next_staff": None,
            "risk_score": risk_score,
            "messages": [
                HumanMessage(
                    content=f"[Manager] Task {state.get('task_id', 'UNKNOWN')} completed. "
                            f"Risk score: {risk_score}/100. "
                            f"Vouching: {total_transactions - exceptions}/{total_transactions} verified.",
                    name="Manager"
                )
            ]
        }
    else:
        # Missing required outputs
        missing_fields = []
        if not has_data:
            missing_fields.append("raw_data (Excel_Parser)")
        if not has_standards:
            missing_fields.append("standards (Standard_Retriever)")
        if not has_vouching:
            missing_fields.append("vouching_logs (Vouching_Assistant)")
        if not has_workpaper:
            missing_fields.append("workpaper_draft (WorkPaper_Generator)")

        error_message = f"Missing required outputs: {', '.join(missing_fields)}"

        return {
            "status": "Failed",
            "error_report": error_message,
            "next_staff": None,
            "messages": [
                HumanMessage(
                    content=f"[Manager] Task failed: {error_message}",
                    name="Manager"
                )
            ]
        }


# ============================================================================
# SUBGRAPH BUILDER
# ============================================================================

def create_manager_subgraph(checkpointer: PostgresSaver) -> StateGraph:
    """Create Manager subgraph that orchestrates 4 Staff agents.

    Architecture:
        START
          ↓
        Excel_Parser (fills raw_data)
          ↓
        Standard_Retriever (fills standards)
          ↓
        Vouching_Assistant (fills vouching_logs)
          ↓
        WorkPaper_Generator (fills workpaper_draft)
          ↓
        Manager_Aggregator (validates all outputs)
          ↓
        END

    Args:
        checkpointer: PostgresSaver instance for state persistence

    Returns:
        Compiled StateGraph ready for execution

    Usage:
        ```python
        from src.db.checkpointer import get_checkpointer
        from src.graph.subgraph import create_manager_subgraph

        checkpointer = get_checkpointer()
        subgraph = create_manager_subgraph(checkpointer)

        # Execute subgraph for a specific task
        config = {"configurable": {"thread_id": "task-001"}}
        initial_state = {
            "task_id": "TASK-001",
            "thread_id": "task-001",
            "category": "매출",
            "status": "Pending",
            "messages": [],
            "raw_data": {},
            "standards": [],
            "vouching_logs": [],
            "workpaper_draft": "",
            "next_staff": None,
            "error_report": "",
            "risk_score": 50
        }

        result = await subgraph.ainvoke(initial_state, config)
        print(result["status"])  # "Completed" or "Failed"
        ```

    Checkpoint Behavior:
        - State is saved after EACH node execution
        - thread_id must match audit_tasks.thread_id in Supabase
        - Can resume from any checkpoint using same thread_id
        - Parallel execution: Each task has unique thread_id → isolated checkpoints

    Error Handling:
        - Each Staff node should catch exceptions and update error_report
        - Manager_Aggregator validates all required fields
        - If critical error: state.status = "Failed", error_report populated
        - Parent graph can check state.status to handle failures

    Integration with Parent Graph (Send API):
        ```python
        from langgraph.graph import Send

        def continue_to_subgraphs(state: AuditState):
            return [
                Send("manager_subgraph", {
                    "task": task,
                    "global_info": {
                        "project_id": state["project_id"],
                        "materiality": state["overall_materiality"]
                    }
                })
                for task in state["tasks"]
            ]

        parent_graph.add_conditional_edges("partner_planning", continue_to_subgraphs)
        ```
    """

    # Initialize StateGraph with TaskState
    subgraph = StateGraph(TaskState)

    # Initialize Staff agents
    excel_parser = ExcelParserAgent()
    standard_retriever = StandardRetrieverAgent()
    vouching_assistant = VouchingAssistantAgent()
    workpaper_generator = WorkPaperGeneratorAgent()

    # Define async wrapper nodes
    # Note: TaskState is TypedDict, compatible with Dict[str, Any] at runtime
    async def excel_parser_node(state: TaskState) -> Dict[str, Any]:
        """Wrapper node for Excel Parser Staff agent."""
        return await excel_parser.run(state)  # type: ignore[arg-type]

    async def standard_retriever_node(state: TaskState) -> Dict[str, Any]:
        """Wrapper node for Standard Retriever Staff agent."""
        return await standard_retriever.run(state)  # type: ignore[arg-type]

    async def vouching_assistant_node(state: TaskState) -> Dict[str, Any]:
        """Wrapper node for Vouching Assistant Staff agent."""
        return await vouching_assistant.run(state)  # type: ignore[arg-type]

    async def workpaper_generator_node(state: TaskState) -> Dict[str, Any]:
        """Wrapper node for WorkPaper Generator Staff agent."""
        return await workpaper_generator.run(state)  # type: ignore[arg-type]

    # Add Staff nodes
    subgraph.add_node("excel_parser", excel_parser_node)
    subgraph.add_node("standard_retriever", standard_retriever_node)
    subgraph.add_node("vouching_assistant", vouching_assistant_node)
    subgraph.add_node("workpaper_generator", workpaper_generator_node)

    # Add Manager aggregator node
    subgraph.add_node("manager_aggregator", aggregate_results)

    # Define sequential flow
    # START → Excel Parser → Standard Retriever → Vouching → WorkPaper → Aggregator → END
    subgraph.add_edge(START, "excel_parser")
    subgraph.add_edge("excel_parser", "standard_retriever")
    subgraph.add_edge("standard_retriever", "vouching_assistant")
    subgraph.add_edge("vouching_assistant", "workpaper_generator")
    subgraph.add_edge("workpaper_generator", "manager_aggregator")
    subgraph.add_edge("manager_aggregator", END)

    # Compile with checkpointer for state persistence
    return subgraph.compile(checkpointer=checkpointer)


# ============================================================================
# ADVANCED ROUTING (OPTIONAL)
# ============================================================================

def create_manager_subgraph_with_routing(checkpointer: PostgresSaver) -> StateGraph:
    """Create Manager subgraph with dynamic routing based on Manager decisions.

    This is an ADVANCED version where Manager Agent actively routes between Staff
    instead of using a fixed sequential flow. Use this if:
    1. Some Staff agents can be skipped based on task type
    2. Staff execution order varies by category
    3. Manager needs to re-run Staff for corrections

    Flow:
        START → Manager_Router → [Staff based on next_staff] → Manager_Router → ...
        Manager_Router decides: "excel_parser" | "standard_retriever" | ... | END

    Args:
        checkpointer: PostgresSaver instance

    Returns:
        Compiled StateGraph with dynamic routing

    Note:
        This is more flexible but complex. Start with create_manager_subgraph()
        (sequential) and migrate to this when routing logic is needed.
    """

    subgraph = StateGraph(TaskState)

    # Initialize agents
    manager = ManagerAgent()
    excel_parser = ExcelParserAgent()
    standard_retriever = StandardRetrieverAgent()
    vouching_assistant = VouchingAssistantAgent()
    workpaper_generator = WorkPaperGeneratorAgent()

    # Add Manager router node
    def manager_router(state: TaskState) -> Dict[str, Any]:
        """Manager evaluates current state and decides next Staff."""
        return manager.run(state)  # type: ignore[arg-type, return-value]

    subgraph.add_node("manager_router", manager_router)

    # Add Staff nodes
    subgraph.add_node("excel_parser", excel_parser.run)
    subgraph.add_node("standard_retriever", standard_retriever.run)
    subgraph.add_node("vouching_assistant", vouching_assistant.run)
    subgraph.add_node("workpaper_generator", workpaper_generator.run)

    # Conditional routing based on Manager's decision
    def route_to_staff(state: TaskState) -> str:
        """Route to next Staff based on Manager's next_staff field."""
        next_staff = state.get("next_staff")

        if next_staff is None:
            return END  # All work completed
        else:
            return next_staff  # Route to specific Staff node

    # START → Manager Router
    subgraph.add_edge(START, "manager_router")

    # Manager Router → [Staff or END]
    subgraph.add_conditional_edges(
        "manager_router",
        route_to_staff,
        {
            "excel_parser": "excel_parser",
            "standard_retriever": "standard_retriever",
            "vouching_assistant": "vouching_assistant",
            "workpaper_generator": "workpaper_generator",
            END: END
        }
    )

    # Each Staff → Manager Router (loop back for next decision)
    subgraph.add_edge("excel_parser", "manager_router")
    subgraph.add_edge("standard_retriever", "manager_router")
    subgraph.add_edge("vouching_assistant", "manager_router")
    subgraph.add_edge("workpaper_generator", "manager_router")

    return subgraph.compile(checkpointer=checkpointer)


# ============================================================================
# TESTING UTILITIES
# ============================================================================

async def test_manager_subgraph():
    """Test Manager subgraph with mock data.

    This is a standalone test function to verify subgraph execution without
    dependencies on Supabase or MCP servers.

    Usage:
        ```bash
        # From backend/ directory
        python -c "import asyncio; from src.graph.subgraph import test_manager_subgraph; asyncio.run(test_manager_subgraph())"
        ```
    """
    from src.db.checkpointer import get_checkpointer

    print("=== Manager Subgraph Test ===\n")

    # Initialize checkpointer
    checkpointer = get_checkpointer()
    subgraph = create_manager_subgraph(checkpointer)

    # Create test task
    test_state: TaskState = {
        "task_id": "TEST-001",
        "thread_id": "test-thread-001",
        "category": "매출",
        "status": "Pending",
        "messages": [],
        "raw_data": {},
        "standards": [],
        "vouching_logs": [],
        "workpaper_draft": "",
        "next_staff": "",  # Empty string instead of None for TypedDict compatibility
        "error_report": "",
        "risk_score": 50
    }

    # Execute subgraph
    config = {"configurable": {"thread_id": "test-thread-001"}}

    print("Starting subgraph execution...")
    result = await subgraph.ainvoke(test_state, config)

    # Print results
    print("\n=== Execution Results ===")
    print(f"Task ID: {result['task_id']}")
    print(f"Status: {result['status']}")
    print(f"Risk Score: {result['risk_score']}")
    print(f"Has raw_data: {bool(result['raw_data'])}")
    print(f"Has standards: {bool(result['standards'])}")
    print(f"Has vouching_logs: {bool(result['vouching_logs'])}")
    print(f"Has workpaper_draft: {bool(result['workpaper_draft'])}")
    print(f"\nWorkpaper Preview:\n{result['workpaper_draft'][:200]}...")

    print("\n=== Test Completed ===")


# ============================================================================
# INTEGRATION NOTES
# ============================================================================

"""
Manager Subgraph Integration Checklist:

1. **Parent Graph Integration (Send API)**:
   ```python
   from langgraph.graph import Send
   from src.graph.subgraph import create_manager_subgraph

   # In parent graph
   manager_subgraph = create_manager_subgraph(checkpointer)

   def continue_to_tasks(state: AuditState):
       return [
           Send("manager_subgraph", {"task_id": task["id"], ...})
           for task in state["tasks"]
       ]

   parent_graph.add_conditional_edges("partner_planning", continue_to_tasks)
   ```

2. **State Synchronization**:
   - TaskState.thread_id MUST match audit_tasks.thread_id in Supabase
   - After subgraph completes, sync state to Supabase:
     ```python
     await sync_task_to_supabase(result["task_id"], result)
     ```

3. **Checkpoint Management**:
   - Each task has unique thread_id → isolated checkpoints
   - 100 parallel tasks = 100 checkpoint records in PostgreSQL
   - Use thread_id to resume interrupted tasks

4. **Error Handling**:
   - Staff agents should catch exceptions and update error_report
   - Manager_Aggregator validates required fields
   - Parent graph can filter failed tasks: [t for t in tasks if t["status"] == "Failed"]

5. **Real Staff Agents (Future)**:
   - Replace placeholder Staff classes with actual implementations
   - Use MCP tools: Standard_MCP, Vouching_MCP, Doc_Parser_MCP
   - Use native tools: Financial_Analyzer, WorkingPaper_Generator
   - Add retry logic for transient errors (API timeouts, file parsing failures)

6. **HITL Integration**:
   - Manager can call interrupt() for critical decisions
   - Use LangGraph's update_state() to inject user feedback
   - Resume execution from checkpoint after approval

7. **Performance Monitoring**:
   - Track subgraph execution time per task
   - Monitor checkpoint size (state serialization overhead)
   - Use LangSmith for tracing Staff → Manager interactions

8. **Testing Strategy**:
   - Unit test: Each Staff agent independently
   - Integration test: Full subgraph execution with mock data
   - E2E test: Parent graph → 100 tasks → Supabase sync
   - Evaluation: LangSmith with Golden Dataset (correct outputs)
"""
