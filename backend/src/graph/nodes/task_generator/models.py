"""
Task Generator Data Models

This module defines the data classes used for representing generated tasks
and task generation results in the 3-level audit task hierarchy.

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constants import RiskLevel, TaskLevel, TaskStatus


@dataclass
class GeneratedTask:
    """
    Represents a generated audit task in the 3-level hierarchy.

    Attributes:
        id: Unique identifier for the task
        project_id: Associated audit project ID
        ega_id: Source EGA ID (for traceability)
        parent_task_id: Parent task ID for hierarchy linking
        task_level: Hierarchy level (High/Mid/Low)
        name: Task name/title
        description: Detailed description
        category: Account category (e.g., "Revenue", "Inventory")
        risk_level: Risk classification
        risk_score: Numeric risk score (0-100)
        status: Current task status
        priority: Task priority (1-100)
        assertion: Financial statement assertion (for Mid/Low level)
        procedure_type: Type of audit procedure (for Low level)
        estimated_hours: Estimated time to complete
        assigned_to: Staff assignment (optional)
        due_date: Target completion date (optional)
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    project_id: str
    ega_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    task_level: TaskLevel = TaskLevel.HIGH
    name: str = ""
    description: str = ""
    category: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: int = 50
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 50
    assertion: Optional[str] = None
    procedure_type: Optional[str] = None
    estimated_hours: float = 0.0
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for state storage and database."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "ega_id": self.ega_id,
            "parent_task_id": self.parent_task_id,
            "task_level": self.task_level.value if isinstance(self.task_level, TaskLevel) else self.task_level,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else self.risk_level,
            "risk_score": self.risk_score,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "assertion": self.assertion,
            "procedure_type": self.procedure_type,
            "estimated_hours": self.estimated_hours,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "metadata": self.metadata,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "updated_at": self.updated_at or datetime.utcnow().isoformat(),
        }


@dataclass
class TaskGenerationResult:
    """Result of task generation from EGAs."""

    success: bool
    tasks: List[GeneratedTask]
    high_level_count: int = 0
    mid_level_count: int = 0
    low_level_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
