"""
Agent Implementations

This module contains the persona and logic for all audit agents:
- PartnerAgent: Strategic audit planning and risk assessment
- ManagerAgent: Task decomposition and execution coordination
- Staff Agents: Specialized workers (Excel parsing, RAG retrieval, vouching, writing)
- StaffAgentFactory: Factory for creating specialized Staff agents
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

__all__ = [
    "PartnerAgent",
    "ManagerAgent",
    "ExcelParserAgent",
    "StandardRetrieverAgent",
    "VouchingAssistantAgent",
    "WorkPaperGeneratorAgent",
    "StaffAgentFactory",
    "StaffAgentType",
    "get_factory",
    "create_staff_agent",
]
