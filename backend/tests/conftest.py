"""
Pytest Configuration and Shared Fixtures

This module provides shared fixtures for all test suites:
- Mock AuditState instances
- Mock LLM responses
- Database fixtures
- Test data factories
"""

import os
import sys
import warnings

os.environ["LANGCHAIN_VERBOSE"] = "false"

# Use LangChain's set_debug() function instead of direct attribute access
# This is the proper way to configure debug mode in LangChain 0.3.x+
from langchain_core.globals import set_debug
set_debug(False)

import pytest
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from src.graph.state import AuditState

# Suppress specific warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


# ============================================================================
# AUDITSTATE FIXTURES
# ============================================================================

@pytest.fixture
def mock_audit_state() -> AuditState:
    """
    Create a basic mock AuditState for testing.

    This fixture provides a minimal valid AuditState with sample client data.
    Use this for basic tests that don't require specific state customization.

    Returns:
        AuditState: Mock state with sample client information
    """
    return AuditState(
        messages=[],
        project_id="test-project-001",
        client_name="ABC Manufacturing Co.",
        fiscal_year=2024,
        overall_materiality=1000000.0,
        audit_plan={},
        tasks=[],
        next_action="WAIT_FOR_APPROVAL",
        is_approved=False,
        shared_documents=[]
    )


@pytest.fixture
def mock_audit_state_with_messages() -> AuditState:
    """
    Create mock AuditState with conversation history.

    This fixture includes sample messages to test context building
    and conversation-aware planning.

    Returns:
        AuditState: Mock state with conversation history
    """
    return AuditState(
        messages=[
            HumanMessage(content="We need to audit ABC Manufacturing for FY 2024"),
            AIMessage(content="Understood. I'll create a comprehensive audit plan."),
            HumanMessage(content="Focus on revenue recognition and inventory valuation"),
        ],
        project_id="test-project-002",
        client_name="ABC Manufacturing Co.",
        fiscal_year=2024,
        overall_materiality=1000000.0,
        audit_plan={},
        tasks=[],
        next_action="WAIT_FOR_APPROVAL",
        is_approved=False,
        shared_documents=[]
    )


@pytest.fixture
def mock_audit_state_high_materiality() -> AuditState:
    """
    Create mock AuditState with high materiality threshold.

    Used to test materiality-sensitive planning logic.

    Returns:
        AuditState: Mock state with high materiality ($5M)
    """
    return AuditState(
        messages=[],
        project_id="test-project-003",
        client_name="XYZ Corporation",
        fiscal_year=2024,
        overall_materiality=5000000.0,  # $5M materiality
        audit_plan={},
        tasks=[],
        next_action="WAIT_FOR_APPROVAL",
        is_approved=False,
        shared_documents=[]
    )


# ============================================================================
# AUDIT PLAN FIXTURES
# ============================================================================

@pytest.fixture
def sample_valid_plan() -> Dict[str, Any]:
    """
    Create a valid sample audit plan.

    This fixture represents a properly structured audit plan
    with all required fields and valid values.

    Returns:
        Dict: Valid audit plan structure
    """
    return {
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                "business_process": "Revenue-Collection Cycle",
                "process_stage": "Substantive Testing",
                "risk_level": "High",
                "materiality": 500000,
                "sampling_size": 25,
                "procedures": [
                    "Vouch sales transactions to supporting documents",
                    "Verify revenue recognition timing per K-IFRS 1115",
                    "Test controls over sales order processing"
                ],
                "rationale": "Revenue is a high fraud risk area per K-GAAS 240"
            },
            {
                "id": "TASK-002",
                "category": "Accounts Receivable",
                "business_process": "Revenue-Collection Cycle",
                "process_stage": "Substantive Testing",
                "risk_level": "Medium",
                "materiality": 300000,
                "sampling_size": 20,
                "procedures": [
                    "Confirm AR balances with customers",
                    "Test aging analysis and collectibility",
                    "Review allowance for doubtful accounts"
                ],
                "rationale": "AR represents significant portion of current assets"
            },
            {
                "id": "TASK-003",
                "category": "Inventory",
                "business_process": "Inventory Management",
                "process_stage": "Physical Observation",
                "risk_level": "Medium",
                "materiality": 300000,
                "sampling_size": 15,
                "procedures": [
                    "Observe physical inventory count",
                    "Test inventory valuation (FIFO/weighted average)",
                    "Review obsolescence provisions"
                ],
                "rationale": "Inventory valuation is subject to estimation"
            }
        ],
        "overall_strategy": "Risk-based approach focusing on high-risk areas",
        "key_risks": [
            "Revenue recognition timing",
            "Inventory obsolescence"
        ]
    }


@pytest.fixture
def sample_invalid_plan_no_tasks() -> Dict[str, Any]:
    """
    Create invalid audit plan missing tasks field.

    Used to test validation error handling.

    Returns:
        Dict: Invalid plan structure
    """
    return {
        "overall_strategy": "Risk-based approach",
        "key_risks": ["Revenue recognition"]
    }


@pytest.fixture
def sample_invalid_plan_empty_tasks() -> Dict[str, Any]:
    """
    Create invalid audit plan with empty tasks list.

    Used to test validation error handling.

    Returns:
        Dict: Invalid plan with empty tasks
    """
    return {
        "tasks": [],
        "overall_strategy": "Risk-based approach"
    }


@pytest.fixture
def sample_invalid_task_missing_fields() -> Dict[str, Any]:
    """
    Create invalid audit plan with task missing required fields.

    Used to test task-level validation.

    Returns:
        Dict: Plan with invalid task
    """
    return {
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                # Missing: risk_level, materiality
                "procedures": ["Vouch sales"]
            }
        ]
    }


@pytest.fixture
def sample_invalid_task_bad_risk_level() -> Dict[str, Any]:
    """
    Create invalid audit plan with invalid risk level.

    Used to test risk level enum validation.

    Returns:
        Dict: Plan with invalid risk level
    """
    return {
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                "risk_level": "Super High",  # Invalid enum value
                "materiality": 500000,
                "procedures": ["Vouch sales"]
            }
        ]
    }


@pytest.fixture
def sample_invalid_task_negative_materiality() -> Dict[str, Any]:
    """
    Create invalid audit plan with negative materiality.

    Used to test materiality validation.

    Returns:
        Dict: Plan with negative materiality
    """
    return {
        "tasks": [
            {
                "id": "TASK-001",
                "category": "Sales Revenue",
                "risk_level": "High",
                "materiality": -100000,  # Invalid negative value
                "procedures": ["Vouch sales"]
            }
        ]
    }


# ============================================================================
# LLM RESPONSE FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_response_json_block() -> str:
    """
    Create mock LLM response with JSON in markdown code block.

    Simulates typical LLM output format with markdown-wrapped JSON.

    Returns:
        str: LLM response with JSON code block
    """
    return """Based on the client information, here's the comprehensive audit plan:

```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "category": "Sales Revenue",
      "business_process": "Revenue-Collection Cycle",
      "process_stage": "Substantive Testing",
      "risk_level": "High",
      "materiality": 500000,
      "sampling_size": 25,
      "procedures": [
        "Vouch sales transactions to supporting documents",
        "Verify revenue recognition timing per K-IFRS 1115"
      ],
      "rationale": "Revenue is a high fraud risk area"
    }
  ],
  "overall_strategy": "Risk-based approach",
  "key_risks": ["Revenue recognition timing"]
}
```

This plan focuses on high-risk areas with appropriate sampling."""


@pytest.fixture
def mock_llm_response_plain_json() -> str:
    """
    Create mock LLM response with plain JSON (no markdown).

    Tests parser's ability to handle raw JSON responses.

    Returns:
        str: Plain JSON response
    """
    return """{
  "tasks": [
    {
      "id": "TASK-001",
      "category": "Sales Revenue",
      "risk_level": "High",
      "materiality": 500000,
      "procedures": ["Vouch sales"]
    }
  ],
  "overall_strategy": "Risk-based approach"
}"""


@pytest.fixture
def mock_llm_response_invalid_json() -> str:
    """
    Create mock LLM response with invalid JSON.

    Tests error handling for malformed LLM responses.

    Returns:
        str: Response with invalid JSON
    """
    return """Here's the audit plan:

```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "category": "Sales Revenue",
      "risk_level": "High"
      # Missing comma here
      "materiality": 500000
    }
  ]
}
```"""


@pytest.fixture
def mock_llm_response_no_json() -> str:
    """
    Create mock LLM response with no JSON at all.

    Tests fallback to mock plan when JSON extraction fails.

    Returns:
        str: Text-only response with no JSON
    """
    return """I'll create a comprehensive audit plan focusing on:
1. Revenue recognition
2. Inventory valuation
3. Accounts receivable confirmation

The plan will follow K-GAAS standards."""


# ============================================================================
# TASK ENRICHMENT FIXTURES
# ============================================================================

@pytest.fixture
def sample_project_id() -> str:
    """
    Sample project ID for task enrichment tests.

    Returns:
        str: UUID-format project ID
    """
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def sample_tasks_for_enrichment() -> List[Dict[str, Any]]:
    """
    Sample tasks for testing enrichment logic.

    Returns:
        List: Tasks without metadata (pre-enrichment)
    """
    return [
        {
            "id": "TASK-001",
            "category": "Sales Revenue",
            "risk_level": "High",
            "materiality": 500000,
            "procedures": ["Vouch sales", "Test cutoff"]
        },
        {
            "id": "TASK-002",
            "category": "Inventory",
            "risk_level": "Medium",
            "materiality": 300000,
            "procedures": ["Observe count", "Test valuation"]
        }
    ]
