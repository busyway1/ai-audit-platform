"""
Agent Implementations

This module contains the persona and logic for all audit agents:
- PartnerAgent: Strategic audit planning and risk assessment
- ManagerAgent: Task decomposition and execution coordination
- Staff Agents: Specialized workers (Excel parsing, RAG retrieval, vouching, writing)
"""

from .partner_agent import PartnerAgent
from .manager_agent import ManagerAgent
from .staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent,
)

__all__ = [
    "PartnerAgent",
    "ManagerAgent",
    "ExcelParserAgent",
    "StandardRetrieverAgent",
    "VouchingAssistantAgent",
    "WorkPaperGeneratorAgent",
]
