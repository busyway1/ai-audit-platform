"""
Node Implementations for Parent Graph

This module provides node wrapper functions for the parent graph.
These nodes are used in the top-level audit workflow orchestration.

Available Nodes:
- partner_planning_node: Partner Agent creates comprehensive audit plan
- wait_for_approval_node: HITL checkpoint for human approval
- manager_aggregation_node: Aggregates results from all Manager subgraphs
- continue_to_manager_subgraphs: Send API dispatcher for parallel execution

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

from .partner import partner_planning_node, wait_for_approval_node
from .manager import manager_aggregation_node, continue_to_manager_subgraphs

__all__ = [
    "partner_planning_node",
    "wait_for_approval_node",
    "manager_aggregation_node",
    "continue_to_manager_subgraphs",
]
