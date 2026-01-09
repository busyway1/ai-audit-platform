"""
Node Implementations for Parent Graph

This module provides node wrapper functions for the parent graph.
These nodes are used in the top-level audit workflow orchestration.

Available Nodes:
- partner_planning_node: Partner Agent creates comprehensive audit plan
- wait_for_approval_node: HITL checkpoint for human approval
- manager_aggregation_node: Aggregates results from all Manager subgraphs
- continue_to_manager_subgraphs: Send API dispatcher for parallel execution
- rerank_node: LLM-based reranking of search candidates (Top-30 to Top-5)
- multihop_node: Multi-hop retrieval for K-IFRS RAG context expansion
- interview_node: Audit strategy interview workflow
- wait_for_interview_completion_node: HITL checkpoint for interview review
- hitl_interrupt_node: HITL escalation handling based on urgency scores
- process_individual_hitl_node: Individual HITL request processing
- ega_parser_node: EGA extraction from Assigned Workflow documents
- task_generator_node: 3-level task hierarchy generation from EGAs
- urgency_node: Task urgency score calculation for HITL escalation

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

from .partner import partner_planning_node, wait_for_approval_node
from .manager import manager_aggregation_node, continue_to_manager_subgraphs
from .reranker_node import rerank_node
from .multihop_node import multihop_node
from .interview_node import (
    interview_node,
    wait_for_interview_completion_node,
    get_interview_progress,
    validate_interview_responses,
)
from .hitl_interrupt import (
    hitl_interrupt_node,
    process_individual_hitl_node,
    get_hitl_summary,
    should_trigger_hitl,
    calculate_urgency_score,
    HITLRequestType,
    HITLRequestStatus,
    HITLUrgencyLevel,
    DEFAULT_URGENCY_CONFIG,
)
from .ega_parser import (
    ega_parser_node,
    parse_assigned_workflow,
    EGA,
    EGAParseResult,
    EGARiskLevel,
    EGAStatus,
    get_ega_summary,
    filter_egas_by_risk,
    sort_egas_by_priority,
)
from .task_generator import (
    task_generator_node,
    TaskGeneratorNode,
    generate_task_hierarchy,
    generate_high_level_task,
    generate_mid_level_tasks,
    generate_low_level_tasks,
    get_task_summary,
    filter_tasks_by_level,
    filter_tasks_by_status,
    get_task_children,
    get_task_tree,
    sort_tasks_by_priority,
    sort_tasks_by_risk_score,
    GeneratedTask,
    TaskGenerationResult,
    TaskLevel,
    TaskStatus,
    RiskLevel,
)
from .urgency_node import (
    urgency_node,
    calculate_task_urgency_score,
    calculate_urgency_scores,
    get_urgency_summary,
    filter_tasks_by_urgency,
    sort_tasks_by_urgency,
    get_hitl_candidates,
    UrgencyLevel,
    UrgencyCalculationResult,
    TaskUrgencyInfo,
    DEFAULT_URGENCY_CONFIG as URGENCY_DEFAULT_CONFIG,
)

__all__ = [
    "partner_planning_node",
    "wait_for_approval_node",
    "manager_aggregation_node",
    "continue_to_manager_subgraphs",
    "rerank_node",
    "multihop_node",
    "interview_node",
    "wait_for_interview_completion_node",
    "get_interview_progress",
    "validate_interview_responses",
    "hitl_interrupt_node",
    "process_individual_hitl_node",
    "get_hitl_summary",
    "should_trigger_hitl",
    "calculate_urgency_score",
    "HITLRequestType",
    "HITLRequestStatus",
    "HITLUrgencyLevel",
    "DEFAULT_URGENCY_CONFIG",
    "ega_parser_node",
    "parse_assigned_workflow",
    "EGA",
    "EGAParseResult",
    "EGARiskLevel",
    "EGAStatus",
    "get_ega_summary",
    "filter_egas_by_risk",
    "sort_egas_by_priority",
    "task_generator_node",
    "TaskGeneratorNode",
    "generate_task_hierarchy",
    "generate_high_level_task",
    "generate_mid_level_tasks",
    "generate_low_level_tasks",
    "get_task_summary",
    "filter_tasks_by_level",
    "filter_tasks_by_status",
    "get_task_children",
    "get_task_tree",
    "sort_tasks_by_priority",
    "sort_tasks_by_risk_score",
    "GeneratedTask",
    "TaskGenerationResult",
    "TaskLevel",
    "TaskStatus",
    "RiskLevel",
    "urgency_node",
    "calculate_task_urgency_score",
    "calculate_urgency_scores",
    "get_urgency_summary",
    "filter_tasks_by_urgency",
    "sort_tasks_by_urgency",
    "get_hitl_candidates",
    "UrgencyLevel",
    "UrgencyCalculationResult",
    "TaskUrgencyInfo",
    "URGENCY_DEFAULT_CONFIG",
]
