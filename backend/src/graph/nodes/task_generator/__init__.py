"""
Task Generator Module

This module implements the Task Generation Node for creating a 3-level task hierarchy
from EGAs (Expected General Activities) extracted from Assigned Workflow documents.

The 3-Level Hierarchy:
1. High Level (EGA) - Top-level tasks representing overall audit objectives
2. Mid Level (Assertion) - Mid-level tasks for financial statement assertions
3. Low Level (Procedure) - Low-level tasks for specific audit procedures

Key Features:
- Generates hierarchical tasks from EGAs
- Assigns parent_task_id for proper linking
- Sets task_level field (High/Mid/Low)
- Calculates risk scores based on EGA risk levels
- Enriches tasks with metadata for database storage

Usage:
    ```python
    from src.graph.nodes.task_generator import (
        task_generator_node,
        generate_task_hierarchy,
        TaskLevel,
        RiskLevel,
    )

    # Use as LangGraph node
    result = await task_generator_node(state)

    # Or use hierarchy generation directly
    result = generate_task_hierarchy(egas, project_id)
    ```

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

# Constants and Enums
from .constants import (
    ASSERTION_PROCEDURES,
    RISK_SCORE_MAP,
    STANDARD_ASSERTIONS,
    RiskLevel,
    TaskLevel,
    TaskStatus,
)

# Data Models
from .models import (
    GeneratedTask,
    TaskGenerationResult,
)

# Utility Functions
from .utils import (
    calculate_risk_score,
    estimate_hours,
    filter_tasks_by_level,
    filter_tasks_by_status,
    generate_task_id,
    get_procedures_for_assertion,
    get_task_children,
    get_task_summary,
    get_task_tree,
    parse_risk_level,
    select_assertions_for_ega,
    sort_tasks_by_priority,
    sort_tasks_by_risk_score,
)

# Hierarchy Builders
from .hierarchy import (
    generate_high_level_task,
    generate_low_level_tasks,
    generate_mid_level_tasks,
    generate_task_hierarchy,
)

# LangGraph Node
from .core import (
    TaskGeneratorNode,
    task_generator_node,
)

__all__ = [
    # LangGraph Node (primary export)
    "task_generator_node",
    "TaskGeneratorNode",
    # Hierarchy Generation
    "generate_task_hierarchy",
    "generate_high_level_task",
    "generate_mid_level_tasks",
    "generate_low_level_tasks",
    # Query Utilities
    "get_task_summary",
    "filter_tasks_by_level",
    "filter_tasks_by_status",
    "get_task_children",
    "get_task_tree",
    "sort_tasks_by_priority",
    "sort_tasks_by_risk_score",
    # Data Models
    "GeneratedTask",
    "TaskGenerationResult",
    # Enums
    "TaskLevel",
    "TaskStatus",
    "RiskLevel",
    # Constants (for extension)
    "STANDARD_ASSERTIONS",
    "ASSERTION_PROCEDURES",
    "RISK_SCORE_MAP",
    # Helper utilities (for extension)
    "generate_task_id",
    "parse_risk_level",
    "calculate_risk_score",
    "select_assertions_for_ega",
    "get_procedures_for_assertion",
    "estimate_hours",
]
