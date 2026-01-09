"""
Agent Implementations

This module contains the persona and logic for all audit agents:
- PartnerAgent: Strategic audit planning and risk assessment
- ManagerAgent: Task decomposition and execution coordination
- Staff Agents: Specialized workers (Excel parsing, RAG retrieval, vouching, writing)
- StaffAgentFactory: Factory for creating specialized Staff agents
- TaskProposerAgent: EGA-based audit task proposal generation
"""

from .partner_agent import PartnerAgent
from .manager_agent import ManagerAgent
from .staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent,
)
from .staff_factory import (
    StaffAgentFactory,
    StaffAgentType,
    get_factory,
    create_staff_agent,
)
from .ralph_loop import (
    RalphWiggumLoop,
    LoopResult,
    ValidationResult,
    ConversationEntry,
    create_ralph_loop,
)
from .task_proposer_agent import (
    TaskProposerAgent,
    TaskProposalSet,
    ProposedTask,
    TaskPriority,
    TaskPhase,
    HITLApprovalRequest,
    create_task_proposer,
)

__all__ = [
    # Core Agents
    "PartnerAgent",
    "ManagerAgent",
    # Staff Agents
    "ExcelParserAgent",
    "StandardRetrieverAgent",
    "VouchingAssistantAgent",
    "WorkPaperGeneratorAgent",
    # Staff Factory
    "StaffAgentFactory",
    "StaffAgentType",
    "get_factory",
    "create_staff_agent",
    # Ralph Loop
    "RalphWiggumLoop",
    "LoopResult",
    "ValidationResult",
    "ConversationEntry",
    "create_ralph_loop",
    # Task Proposer
    "TaskProposerAgent",
    "TaskProposalSet",
    "ProposedTask",
    "TaskPriority",
    "TaskPhase",
    "HITLApprovalRequest",
    "create_task_proposer",
]
