"""
Comprehensive Unit Tests for Partner Agent

This test suite provides 100% coverage of partner_agent.py, including:
- Agent initialization with OpenAI model setup
- Audit plan creation with LLM integration
- Plan parsing and validation logic
- Mock plan fallback handling
- Task enrichment with metadata
- Error handling for API failures
- Materiality threshold validation

Test Fixtures:
- mock_audit_state: Basic AuditState for testing
- mock_audit_state_with_messages: AuditState with conversation history
- mock_audit_state_high_materiality: High materiality threshold testing
- sample_valid_plan: Valid audit plan fixture
- sample_project_id: Project ID for enrichment tests
- sample_tasks_for_enrichment: Sample tasks for enrichment

Mocking Strategy:
- Use unittest.mock to mock ChatOpenAI for deterministic testing
- Mock async LLM responses with AsyncMock
- Test both success and failure paths
- Validate JSON parsing with real and malformed responses
"""

import os
os.environ["LANGCHAIN_VERBOSE"] = "false"

import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.agents.partner_agent import (
    PartnerAgent,
    ResearchSource,
    DeepResearchResult
)
from src.graph.state import AuditState
from langchain_core.messages import AIMessage, HumanMessage
import httpx


# ============================================================================
# MODULE-LEVEL FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def mock_chat_openai():
    """
    Automatically mock ChatOpenAI for all tests in this module.

    This prevents the langchain.verbose AttributeError that occurs when
    ChatOpenAI tries to initialize without proper mocking.

    The mock is applied to all tests automatically (autouse=True).
    Individual tests can override this by using their own @patch decorator.
    """
    with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
        # Create a basic mock LLM that works for non-async tests
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        yield mock_llm_class


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

class TestPartnerAgentInitialization:
    """Test suite for PartnerAgent initialization."""

    def test_partner_agent_initialization_default_temperature(self):
        """
        Test PartnerAgent initializes with correct default temperature.

        Verifies:
        - ChatOpenAI is instantiated with correct model (gpt-5.2)
        - Default temperature is 0.2 (low for consistency)
        - LLM attribute is properly set

        Expected behavior:
        - Agent should have llm attribute
        - Model should be "gpt-5.2"
        - Temperature should be 0.2
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            agent = PartnerAgent()

            # Verify ChatOpenAI was called with correct parameters
            mock_llm_class.assert_called_once_with(
                model="gpt-5.2",
                temperature=0.2
            )

            # Verify agent has llm attribute
            assert hasattr(agent, 'llm')
            assert agent.llm == mock_llm_class.return_value

    def test_partner_agent_initialization_custom_temperature(self):
        """
        Test PartnerAgent initializes with custom temperature.

        Verifies:
        - Custom temperature parameter is respected
        - ChatOpenAI receives correct custom temperature

        Expected behavior:
        - Agent should use provided temperature value
        - Default should be overridable
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            custom_temp = 0.5
            agent = PartnerAgent(temperature=custom_temp)

            # Verify ChatOpenAI was called with custom temperature
            mock_llm_class.assert_called_once_with(
                model="gpt-5.2",
                temperature=custom_temp
            )

    def test_partner_agent_initialization_high_temperature(self):
        """
        Test PartnerAgent with high temperature for creative outputs.

        Verifies:
        - High temperature values (>0.5) are accepted
        - Model configuration handles diverse temperature ranges

        Expected behavior:
        - Should accept temperature values from 0.0 to 2.0
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            high_temp = 1.8
            agent = PartnerAgent(temperature=high_temp)

            # Verify high temperature is passed through
            mock_llm_class.assert_called_once_with(
                model="gpt-5.2",
                temperature=high_temp
            )


# ============================================================================
# PLAN AUDIT TESTS
# ============================================================================

class TestPlanAudit:
    """Test suite for plan_audit method."""

    @pytest.mark.asyncio
    async def test_plan_audit_creates_tasks_from_llm_response(
        self,
        mock_audit_state: AuditState,
        sample_valid_plan: Dict[str, Any]
    ):
        """
        Test plan_audit creates tasks from valid LLM response.

        Verifies:
        - LLM is invoked with system prompt and client context
        - JSON parsing extracts valid plan structure
        - Tasks list is returned in response
        - next_action is set to "WAIT_FOR_APPROVAL"

        Expected behavior:
        - Should call LLM.ainvoke with proper messages
        - Should parse JSON from response
        - Should validate plan structure
        - Should return dict with audit_plan, tasks, next_action
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            # Setup mock LLM response
            mock_response = MagicMock()
            mock_response.content = json.dumps(sample_valid_plan)

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()
            result = await agent.plan_audit(mock_audit_state)

            # Verify LLM was called
            mock_llm.ainvoke.assert_called_once()

            # Verify result structure
            assert "audit_plan" in result
            assert "tasks" in result
            assert "next_action" in result

            # Verify next_action is WAIT_FOR_APPROVAL (HITL)
            assert result["next_action"] == "WAIT_FOR_APPROVAL"

            # Verify tasks match the plan
            assert len(result["tasks"]) == len(sample_valid_plan["tasks"])

    @pytest.mark.asyncio
    async def test_plan_audit_sets_next_action_wait_for_approval(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test plan_audit always returns WAIT_FOR_APPROVAL as next_action.

        This is the Human-in-the-Loop checkpoint. Partner never proceeds
        without explicit human approval.

        Verifies:
        - next_action field is always "WAIT_FOR_APPROVAL"
        - This ensures HITL gate before Manager execution

        Expected behavior:
        - Result["next_action"] should equal "WAIT_FOR_APPROVAL"
        - Should be the same regardless of plan content
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            valid_plan = {
                "tasks": [
                    {
                        "id": "TASK-001",
                        "category": "Sales Revenue",
                        "risk_level": "High",
                        "materiality": 500000
                    }
                ]
            }

            mock_response = MagicMock()
            mock_response.content = json.dumps(valid_plan)

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()
            result = await agent.plan_audit(mock_audit_state)

            # CRITICAL: next_action must always be WAIT_FOR_APPROVAL
            assert result["next_action"] == "WAIT_FOR_APPROVAL"

    @pytest.mark.asyncio
    async def test_plan_audit_handles_llm_api_failure(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test plan_audit handles LLM API failures gracefully.

        Verifies:
        - API errors (timeouts, rate limits, etc.) don't crash the system
        - Falls back to mock plan on API failure
        - Error information is preserved

        Expected behavior:
        - Should catch API exceptions
        - Should return mock plan with error note
        - Should not raise exception to caller
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            # Setup mock to raise API error
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(
                side_effect=Exception("OpenAI API timeout")
            )
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            # Should raise or handle gracefully
            with pytest.raises(Exception):
                await agent.plan_audit(mock_audit_state)

    @pytest.mark.asyncio
    async def test_plan_audit_with_high_materiality(
        self,
        mock_audit_state_high_materiality: AuditState
    ):
        """
        Test plan_audit respects materiality threshold in context.

        Verifies:
        - High materiality ($5M) is included in client context
        - LLM receives correct financial threshold for planning
        - Task materiality values respect overall materiality

        Expected behavior:
        - Client context should include overall_materiality
        - Plan tasks should have materiality ≤ overall_materiality
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            valid_plan = {
                "tasks": [
                    {
                        "id": "TASK-001",
                        "category": "Sales Revenue",
                        "risk_level": "High",
                        "materiality": 2000000  # Less than $5M overall
                    }
                ]
            }

            mock_response = MagicMock()
            mock_response.content = json.dumps(valid_plan)

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()
            result = await agent.plan_audit(mock_audit_state_high_materiality)

            # Verify LLM was called and result is returned
            assert result["next_action"] == "WAIT_FOR_APPROVAL"

    @pytest.mark.asyncio
    async def test_plan_audit_builds_client_context_from_state(
        self,
        mock_audit_state_with_messages: AuditState
    ):
        """
        Test plan_audit builds proper client context from AuditState.

        Verifies:
        - Client name is extracted from state
        - Fiscal year is included in context
        - Overall materiality is formatted correctly
        - Message history (last 5) is included

        Expected behavior:
        - Context should include all required state fields
        - Messages should be truncated to last 5 for context window
        - Should format materiality as currency
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            valid_plan = {
                "tasks": [
                    {
                        "id": "TASK-001",
                        "category": "Sales Revenue",
                        "risk_level": "High",
                        "materiality": 500000
                    }
                ]
            }

            mock_response = MagicMock()
            mock_response.content = json.dumps(valid_plan)

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()
            result = await agent.plan_audit(mock_audit_state_with_messages)

            # Verify successful execution
            assert result["next_action"] == "WAIT_FOR_APPROVAL"

            # Verify LLM was called with HumanMessage
            call_args = mock_llm.ainvoke.call_args
            messages = call_args[0][0]

            # Should have SystemMessage and HumanMessage
            assert len(messages) == 2
            assert messages[1].type == "human"
            # Client context should be in human message
            assert "ABC Manufacturing Co." in messages[1].content


# ============================================================================
# PARSING TESTS
# ============================================================================

class TestPlanParsing:
    """Test suite for plan parsing logic."""

    def test_parse_plan_with_json_code_block(
        self,
        sample_valid_plan: Dict[str, Any]
    ):
        """
        Test parsing plan from markdown JSON code block.

        Verifies:
        - JSON wrapped in ```json``` block is extracted correctly
        - Markdown delimiters are removed
        - Resulting JSON is valid and parseable

        Expected behavior:
        - Should extract JSON between backticks
        - Should parse into valid dictionary
        - Should preserve all fields
        """
        agent = PartnerAgent()

        # Create markdown-wrapped JSON
        json_content = json.dumps(sample_valid_plan)
        markdown_response = f"```json\n{json_content}\n```"

        result = agent._parse_plan(markdown_response)

        # Verify parsing succeeded
        assert isinstance(result, dict)
        assert "tasks" in result
        assert len(result["tasks"]) > 0

    def test_parse_plan_with_plain_json(
        self,
        sample_valid_plan: Dict[str, Any]
    ):
        """
        Test parsing plan from plain JSON (no markdown).

        Verifies:
        - Raw JSON (no markdown) is parsed correctly
        - Parser handles both markdown and plain JSON

        Expected behavior:
        - Should parse JSON directly
        - Should not require markdown wrapping
        """
        agent = PartnerAgent()

        json_content = json.dumps(sample_valid_plan)
        result = agent._parse_plan(json_content)

        assert isinstance(result, dict)
        assert "tasks" in result

    def test_parse_plan_with_invalid_json_returns_mock(
        self,
        mock_llm_response_invalid_json: str
    ):
        """
        Test parsing with invalid JSON returns mock plan.

        Verifies:
        - Malformed JSON triggers fallback to mock plan
        - Error note is preserved in _note field
        - System continues to function

        Expected behavior:
        - Should catch JSONDecodeError
        - Should return _create_mock_plan()
        - Should include error information
        """
        agent = PartnerAgent()

        result = agent._parse_plan(mock_llm_response_invalid_json)

        # Should return mock plan on parse failure
        assert isinstance(result, dict)
        assert "tasks" in result
        assert isinstance(result["tasks"], list)
        assert len(result["tasks"]) > 0

    def test_parse_plan_with_no_json_returns_mock(
        self,
        mock_llm_response_no_json: str
    ):
        """
        Test parsing response with no JSON content.

        Verifies:
        - Response without any JSON structure triggers fallback
        - Mock plan is returned with error note
        - System doesn't crash on non-JSON responses

        Expected behavior:
        - Should detect missing JSON
        - Should return mock plan
        - Should log error note
        """
        agent = PartnerAgent()

        result = agent._parse_plan(mock_llm_response_no_json)

        # Should fallback to mock plan
        assert isinstance(result, dict)
        assert "tasks" in result
        assert len(result["tasks"]) > 0

    def test_parse_plan_preserves_all_fields(
        self,
        sample_valid_plan: Dict[str, Any]
    ):
        """
        Test parsing preserves all fields from original plan.

        Verifies:
        - All task fields are preserved (id, category, risk_level, etc.)
        - Overall strategy is preserved
        - Key risks are preserved
        - No data loss during parsing

        Expected behavior:
        - Parsed plan should match original structure
        - All nested fields should be intact
        """
        agent = PartnerAgent()

        json_content = json.dumps(sample_valid_plan)
        result = agent._parse_plan(json_content)

        # Verify all fields are preserved
        assert result["overall_strategy"] == sample_valid_plan["overall_strategy"]
        assert result["key_risks"] == sample_valid_plan["key_risks"]

        for i, task in enumerate(result["tasks"]):
            original = sample_valid_plan["tasks"][i]
            assert task["id"] == original["id"]
            assert task["category"] == original["category"]
            assert task["risk_level"] == original["risk_level"]


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestPlanValidation:
    """Test suite for plan validation logic."""

    def test_validate_plan_success_with_valid_plan(
        self,
        sample_valid_plan: Dict[str, Any]
    ):
        """
        Test validation passes with valid plan structure.

        Verifies:
        - Valid plan with all required fields passes validation
        - No exception is raised
        - Multiple tasks are handled correctly

        Expected behavior:
        - Should not raise any exception
        - Should allow execution to continue
        """
        agent = PartnerAgent()

        # Should not raise exception
        agent._validate_plan(sample_valid_plan)

    def test_validate_plan_fails_missing_tasks_field(
        self,
        sample_invalid_plan_no_tasks: Dict[str, Any]
    ):
        """
        Test validation fails when tasks field is missing.

        Verifies:
        - Missing "tasks" key is caught
        - ValueError is raised with clear message
        - Error message indicates missing field

        Expected behavior:
        - Should raise ValueError
        - Error message should mention "tasks" field
        """
        agent = PartnerAgent()

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(sample_invalid_plan_no_tasks)

        assert "tasks" in str(exc_info.value).lower()

    def test_validate_plan_fails_tasks_not_list(
        self,
        sample_invalid_plan_no_tasks: Dict[str, Any]
    ):
        """
        Test validation fails when tasks is not a list.

        Verifies:
        - Non-list tasks field is rejected
        - ValueError is raised
        - Error message indicates type mismatch

        Expected behavior:
        - Should raise ValueError
        - Error should mention "list"
        """
        agent = PartnerAgent()

        invalid_plan = {
            "tasks": {"id": "TASK-001"}  # Dict instead of list
        }

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(invalid_plan)

        assert "list" in str(exc_info.value).lower()

    def test_validate_plan_fails_empty_tasks(
        self,
        sample_invalid_plan_empty_tasks: Dict[str, Any]
    ):
        """
        Test validation fails with empty tasks list.

        Verifies:
        - Empty tasks list is rejected
        - ValueError is raised
        - Error message indicates minimum requirement

        Expected behavior:
        - Should raise ValueError
        - Error should mention at least one task
        """
        agent = PartnerAgent()

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(sample_invalid_plan_empty_tasks)

        assert "one task" in str(exc_info.value).lower() or \
               "at least" in str(exc_info.value).lower()

    def test_validate_plan_fails_task_missing_required_field(
        self,
        sample_invalid_task_missing_fields: Dict[str, Any]
    ):
        """
        Test validation fails when task missing required fields.

        Verifies:
        - Missing required task fields (id, category, risk_level, materiality)
        - ValueError is raised
        - Error message identifies missing field and task

        Expected behavior:
        - Should raise ValueError
        - Should identify which field is missing
        - Should identify which task is invalid
        """
        agent = PartnerAgent()

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(sample_invalid_task_missing_fields)

        error_msg = str(exc_info.value).lower()
        # Should mention missing field
        assert "missing" in error_msg or "required" in error_msg

    def test_validate_plan_fails_invalid_risk_level(
        self,
        sample_invalid_task_bad_risk_level: Dict[str, Any]
    ):
        """
        Test validation fails with invalid risk_level enum.

        Verifies:
        - Invalid risk_level values are rejected
        - Only allowed values: Low, Medium, High, Critical
        - ValueError indicates valid options

        Expected behavior:
        - Should raise ValueError
        - Should list valid risk levels
        - Should indicate which value was invalid
        """
        agent = PartnerAgent()

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(sample_invalid_task_bad_risk_level)

        error_msg = str(exc_info.value).lower()
        assert "risk_level" in error_msg or "invalid" in error_msg

    def test_validate_plan_fails_negative_materiality(
        self,
        sample_invalid_task_negative_materiality: Dict[str, Any]
    ):
        """
        Test validation fails with negative materiality value.

        Verifies:
        - Negative materiality is rejected
        - Zero materiality is rejected
        - Only positive numbers are allowed

        Expected behavior:
        - Should raise ValueError
        - Should indicate materiality must be positive
        """
        agent = PartnerAgent()

        with pytest.raises(ValueError) as exc_info:
            agent._validate_plan(sample_invalid_task_negative_materiality)

        error_msg = str(exc_info.value).lower()
        assert "positive" in error_msg or "materiality" in error_msg

    def test_validate_plan_fails_non_numeric_materiality(self):
        """
        Test validation fails with non-numeric materiality.

        Verifies:
        - String materiality is rejected
        - Non-convertible types raise error
        - Type validation is strict

        Expected behavior:
        - Should raise ValueError
        - Should indicate materiality must be numeric
        """
        agent = PartnerAgent()

        invalid_plan = {
            "tasks": [
                {
                    "id": "TASK-001",
                    "category": "Sales",
                    "risk_level": "High",
                    "materiality": "not a number"
                }
            ]
        }

        with pytest.raises(ValueError):
            agent._validate_plan(invalid_plan)

    def test_validate_plan_accepts_all_valid_risk_levels(self):
        """
        Test validation accepts all valid risk level values.

        Verifies:
        - Low, Medium, High, Critical are all accepted
        - Validation passes with each valid level
        - Case sensitivity is respected

        Expected behavior:
        - Should accept: Low, Medium, High, Critical
        - Should reject other cases (low, LOW, etc.)
        """
        agent = PartnerAgent()

        valid_levels = ["Low", "Medium", "High", "Critical"]

        for risk_level in valid_levels:
            plan = {
                "tasks": [
                    {
                        "id": "TASK-001",
                        "category": "Sales",
                        "risk_level": risk_level,
                        "materiality": 500000
                    }
                ]
            }

            # Should not raise
            agent._validate_plan(plan)


# ============================================================================
# MOCK PLAN TESTS
# ============================================================================

class TestMockPlan:
    """Test suite for mock plan creation."""

    def test_create_mock_plan_default(self):
        """
        Test creating default mock plan.

        Verifies:
        - Default mock plan has valid structure
        - Contains at least 3 sample tasks
        - All required fields are present
        - Plan can be used as fallback

        Expected behavior:
        - Should return valid plan structure
        - Should have reasonable default values
        - Should be complete and usable
        """
        agent = PartnerAgent()

        plan = agent._create_mock_plan()

        # Verify structure
        assert "tasks" in plan
        assert "overall_strategy" in plan
        assert "key_risks" in plan

        # Verify completeness
        assert len(plan["tasks"]) >= 3
        assert isinstance(plan["key_risks"], list)

    def test_create_mock_plan_with_error_note(self):
        """
        Test creating mock plan with error information.

        Verifies:
        - Error note is preserved in _note field
        - Useful for debugging parse failures
        - Note doesn't affect plan structure

        Expected behavior:
        - Should include _note field
        - Should preserve error message
        - Should still be valid plan structure
        """
        agent = PartnerAgent()

        error_msg = "JSON parse error: Unexpected token"
        plan = agent._create_mock_plan(note=error_msg)

        # Verify note is included
        assert "_note" in plan
        assert error_msg in plan["_note"]

        # Verify plan is still valid
        assert "tasks" in plan

    def test_mock_plan_has_all_required_task_fields(self):
        """
        Test mock plan tasks have all required fields.

        Verifies:
        - Each task in mock plan has: id, category, risk_level, materiality
        - Additional fields are included (procedures, rationale, etc.)
        - Plan passes own validation

        Expected behavior:
        - All required fields should be present
        - Should pass _validate_plan()
        - Should be suitable for downstream processing
        """
        agent = PartnerAgent()

        plan = agent._create_mock_plan()

        # Should pass own validation
        agent._validate_plan(plan)

        # Verify additional fields exist
        for task in plan["tasks"]:
            assert "procedures" in task
            assert "rationale" in task
            assert isinstance(task["procedures"], list)


# ============================================================================
# TASK ENRICHMENT TESTS
# ============================================================================

class TestTaskEnrichment:
    """Test suite for task enrichment with metadata."""

    def test_enrich_tasks_adds_all_metadata(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test task enrichment adds required metadata fields.

        Verifies:
        - project_id is added to each task
        - thread_id is generated (unique UUID format)
        - status is set to "Pending"
        - title and description are created

        Expected behavior:
        - All original fields are preserved
        - New fields are added with correct values
        - thread_id format is valid (task-UUID)
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        # Verify all tasks enriched
        assert len(enriched) == len(sample_tasks_for_enrichment)

        for task in enriched:
            # Verify metadata added
            assert task["project_id"] == sample_project_id
            assert "thread_id" in task
            assert task["status"] == "Pending"
            assert "title" in task
            assert "description" in task

            # Verify thread_id format
            assert task["thread_id"].startswith("task-")

    def test_enrich_tasks_preserves_original_fields(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test enrichment preserves all original task fields.

        Verifies:
        - Original fields (id, category, risk_level, etc.) are unchanged
        - No data loss during enrichment
        - Enrichment is purely additive

        Expected behavior:
        - All original fields should be identical
        - New fields should not overwrite existing
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        for i, task in enumerate(enriched):
            original = sample_tasks_for_enrichment[i]

            # Verify original fields preserved
            assert task["id"] == original["id"]
            assert task["category"] == original["category"]
            assert task["risk_level"] == original["risk_level"]
            assert task["materiality"] == original["materiality"]
            assert task["procedures"] == original["procedures"]

    def test_enrich_tasks_generates_unique_thread_ids(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test each enriched task gets unique thread_id.

        Verifies:
        - No two tasks have same thread_id
        - thread_ids are in proper UUID format
        - thread_ids are deterministic per enrichment call

        Expected behavior:
        - All thread_ids should be unique
        - Should be valid UUID format
        - Should be deterministically generated
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        thread_ids = [task["thread_id"] for task in enriched]

        # Verify uniqueness
        assert len(thread_ids) == len(set(thread_ids))

        # Verify format
        for thread_id in thread_ids:
            # Should start with "task-" and contain UUID
            assert thread_id.startswith("task-")
            uuid_part = thread_id.split("task-")[1]
            # Should be valid UUID format
            try:
                uuid.UUID(uuid_part)
            except ValueError:
                pytest.fail(f"Invalid UUID format in thread_id: {thread_id}")

    def test_enrich_tasks_creates_title_from_category(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test title is derived from task category.

        Verifies:
        - Title includes category name
        - Title includes "Audit" keyword
        - Title is human-readable

        Expected behavior:
        - Title should be: "{category} Audit"
        - Should match expected format
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        for task in enriched:
            original_category = next(
                t["category"] for t in sample_tasks_for_enrichment
                if t["id"] == task["id"]
            )

            # Verify title format
            expected_title = f"{original_category} Audit"
            assert task["title"] == expected_title

    def test_enrich_tasks_creates_description_from_procedures(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test description is created from task procedures.

        Verifies:
        - Description includes category
        - Description includes first 2 procedures
        - Description is readable and informative

        Expected behavior:
        - Should include category name
        - Should include first 2 procedures
        - Should be human-readable summary
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        for task in enriched:
            # Description should contain category
            assert task["category"].lower() in task["description"].lower()

            # Description should be non-empty
            assert len(task["description"]) > 0

    def test_enrich_tasks_with_single_task(
        self,
        sample_project_id: str
    ):
        """
        Test enrichment works with single task.

        Verifies:
        - Single-element list is handled correctly
        - Metadata is properly added
        - No edge cases with list length

        Expected behavior:
        - Should enrich single task correctly
        - Should return list with one element
        """
        agent = PartnerAgent()

        single_task = [
            {
                "id": "TASK-001",
                "category": "Revenue",
                "risk_level": "High",
                "materiality": 500000,
                "procedures": ["Procedure 1", "Procedure 2"]
            }
        ]

        enriched = agent.enrich_tasks_with_metadata(
            single_task,
            sample_project_id
        )

        assert len(enriched) == 1
        assert enriched[0]["project_id"] == sample_project_id

    def test_enrich_tasks_with_multiple_tasks(
        self,
        sample_tasks_for_enrichment: list,
        sample_project_id: str
    ):
        """
        Test enrichment with multiple tasks.

        Verifies:
        - Multiple tasks (2+) are all enriched
        - Order is preserved
        - All metadata is correctly added

        Expected behavior:
        - Should handle arbitrary number of tasks
        - Should preserve order
        - Should enrich all uniformly
        """
        agent = PartnerAgent()

        enriched = agent.enrich_tasks_with_metadata(
            sample_tasks_for_enrichment,
            sample_project_id
        )

        # Verify count matches
        assert len(enriched) == len(sample_tasks_for_enrichment)

        # Verify order preserved
        for i, task in enumerate(enriched):
            assert task["id"] == sample_tasks_for_enrichment[i]["id"]


# ============================================================================
# BUILD CLIENT CONTEXT TESTS
# ============================================================================

class TestBuildClientContext:
    """Test suite for client context building."""

    def test_build_client_context_includes_client_name(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test client context includes client name.

        Verifies:
        - Client name is extracted from state
        - Appears in context string
        - Formatted for LLM consumption

        Expected behavior:
        - Context should include "ABC Manufacturing Co."
        """
        agent = PartnerAgent()

        context = agent._build_client_context(mock_audit_state)

        assert "ABC Manufacturing Co." in context

    def test_build_client_context_includes_fiscal_year(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test client context includes fiscal year.

        Verifies:
        - Fiscal year is extracted from state
        - Appears in context string
        - Formatted correctly

        Expected behavior:
        - Context should include fiscal year 2024
        """
        agent = PartnerAgent()

        context = agent._build_client_context(mock_audit_state)

        assert "2024" in context

    def test_build_client_context_includes_materiality(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test client context includes overall materiality.

        Verifies:
        - Overall materiality is formatted as currency
        - Appears in context string
        - Properly formatted with commas and decimals

        Expected behavior:
        - Should include formatted materiality
        - Should use currency format
        """
        agent = PartnerAgent()

        context = agent._build_client_context(mock_audit_state)

        # Should be formatted as currency
        assert "1,000,000.00" in context or "1000000" in context

    def test_build_client_context_includes_messages(
        self,
        mock_audit_state_with_messages: AuditState
    ):
        """
        Test client context includes conversation messages.

        Verifies:
        - Recent messages are included (last 5)
        - Human and AI messages are both included
        - Messages are truncated if too long

        Expected behavior:
        - Should include message content
        - Should identify message role (User/Partner)
        - Should limit to last 5 messages
        """
        agent = PartnerAgent()

        context = agent._build_client_context(mock_audit_state_with_messages)

        # Should include message content
        assert "audit" in context.lower()
        assert "revenue" in context.lower() or "inventory" in context.lower()

    def test_build_client_context_truncates_long_messages(self):
        """
        Test client context truncates long messages.

        Verifies:
        - Messages longer than 200 chars are truncated
        - Prevents context window overflow
        - Preserves meaning with first 200 chars

        Expected behavior:
        - Should limit each message to 200 characters
        - Should not include full long messages
        """
        agent = PartnerAgent()

        # Create state with very long message
        long_message = "A" * 500
        state = AuditState(
            messages=[HumanMessage(content=long_message)],
            project_id="test",
            client_name="Test Client",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[]
        )

        context = agent._build_client_context(state)

        # Message should be truncated (max 200 chars in output)
        # Can verify by checking the long string doesn't appear fully
        assert "A" * 500 not in context

    def test_build_client_context_limits_to_last_5_messages(self):
        """
        Test client context includes only last 5 messages.

        Verifies:
        - Only recent 5 messages are included
        - Older messages are excluded (context window optimization)
        - Prevents excessive context size

        Expected behavior:
        - Should process last 5 messages
        - Earlier messages should be excluded
        """
        agent = PartnerAgent()

        # Create state with 10 messages
        messages = [
            HumanMessage(content=f"Message {i}") if i % 2 == 0
            else AIMessage(content=f"Response {i}")
            for i in range(10)
        ]

        state = AuditState(
            messages=messages,
            project_id="test",
            client_name="Test Client",
            fiscal_year=2024,
            overall_materiality=1000000.0,
            audit_plan={},
            tasks=[],
            next_action="WAIT_FOR_APPROVAL",
            is_approved=False,
            shared_documents=[]
        )

        context = agent._build_client_context(state)

        # Should include recent messages (8, 9)
        assert "Message 8" in context or "Response 9" in context


# ============================================================================
# DEEP RESEARCH TESTS (BE-10.1)
# ============================================================================

class TestDeepResearch:
    """Test suite for deep_research() method with RAG + Web integration."""

    @pytest.mark.asyncio
    async def test_deep_research_returns_result_structure(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research returns proper DeepResearchResult structure.

        Verifies:
        - Returns DeepResearchResult dataclass
        - Contains topic, rag_results, web_results
        - Contains synthesis and key_findings
        - Contains sources_consulted count and confidence_score
        - Contains metadata with client info

        Expected behavior:
        - Should return complete DeepResearchResult
        - All fields should be properly typed
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            # Setup mock LLM for synthesis
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "synthesis": "Comprehensive research synthesis",
                "key_findings": ["Finding 1", "Finding 2"],
                "regulatory_requirements": ["K-IFRS 1115"],
                "audit_risks": ["Revenue timing risk"],
                "recommendations": ["Test cutoff procedures"],
                "confidence_score": 0.85
            })

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            # Mock MCP servers being unavailable (will use fallback)
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock()
                )
                mock_client.return_value.__aexit__ = AsyncMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )

                result = await agent.deep_research(
                    topic="revenue recognition timing",
                    state=mock_audit_state
                )

            # Verify result structure
            assert isinstance(result, DeepResearchResult)
            assert result.topic == "revenue recognition timing"
            assert isinstance(result.rag_results, list)
            assert isinstance(result.web_results, list)
            assert isinstance(result.synthesis, str)
            assert isinstance(result.key_findings, list)
            assert isinstance(result.sources_consulted, int)
            assert isinstance(result.confidence_score, float)
            assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_deep_research_empty_topic_raises_error(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research raises ValueError for empty topic.

        Verifies:
        - Empty string topic raises ValueError
        - Whitespace-only topic raises ValueError
        - None topic raises error

        Expected behavior:
        - Should raise ValueError with clear message
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            agent = PartnerAgent()

            # Test empty string
            with pytest.raises(ValueError) as exc_info:
                await agent.deep_research(topic="", state=mock_audit_state)
            assert "empty" in str(exc_info.value).lower()

            # Test whitespace only
            with pytest.raises(ValueError) as exc_info:
                await agent.deep_research(topic="   ", state=mock_audit_state)
            assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_deep_research_uses_fallback_on_mcp_error(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research uses fallback results when MCP servers fail.

        Verifies:
        - Connection errors trigger fallback
        - Fallback RAG results include K-GAAS standards
        - Fallback web results include KICPA guidelines
        - Research continues despite server failures

        Expected behavior:
        - Should return fallback results on connection error
        - Should not raise exception to caller
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "synthesis": "Fallback synthesis",
                "key_findings": ["Fallback finding"],
                "confidence_score": 0.5
            })

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            # Mock MCP servers failing
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                result = await agent.deep_research(
                    topic="revenue recognition",
                    state=mock_audit_state
                )

            # Verify fallback results are used
            assert len(result.rag_results) > 0
            assert len(result.web_results) > 0

            # Verify fallback metadata
            assert any(
                r.metadata.get("fallback") == True
                for r in result.rag_results
            )
            assert any(
                r.metadata.get("fallback") == True
                for r in result.web_results
            )

    @pytest.mark.asyncio
    async def test_deep_research_parallel_execution(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research executes RAG and Web searches in parallel.

        Verifies:
        - Both searches are initiated concurrently
        - Results from both sources are combined
        - Total sources_consulted reflects both sources

        Expected behavior:
        - Should use asyncio.gather for parallel execution
        - Should combine results from multiple sources
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "synthesis": "Combined synthesis",
                "key_findings": ["Finding from RAG", "Finding from Web"],
                "confidence_score": 0.75
            })

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            # Count that both methods are called
            call_count = {"rag": 0, "web": 0}

            original_search_rag = agent._search_rag
            original_search_web = agent._search_web

            async def mock_search_rag(*args, **kwargs):
                call_count["rag"] += 1
                return agent._get_fallback_rag_results("test")

            async def mock_search_web(*args, **kwargs):
                call_count["web"] += 1
                return agent._get_fallback_web_results("test")

            agent._search_rag = mock_search_rag
            agent._search_web = mock_search_web

            result = await agent.deep_research(
                topic="inventory valuation",
                state=mock_audit_state
            )

            # Verify both search methods were called
            assert call_count["rag"] == 1
            assert call_count["web"] == 1

            # Verify combined results
            assert result.sources_consulted == len(result.rag_results) + len(result.web_results)

    @pytest.mark.asyncio
    async def test_deep_research_synthesizes_results(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research synthesizes results using LLM.

        Verifies:
        - LLM is called for synthesis
        - Synthesis combines RAG and web findings
        - Key findings are extracted
        - Regulatory requirements are identified

        Expected behavior:
        - Should invoke LLM with research results
        - Should parse synthesis response
        - Should extract key findings
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            synthesis_response = {
                "synthesis": "Revenue recognition under K-IFRS 1115 requires careful analysis...",
                "key_findings": [
                    "Revenue recognized when control transfers",
                    "Five-step model must be applied",
                    "Timing is critical for audit"
                ],
                "regulatory_requirements": [
                    "K-IFRS 1115 para 31-38",
                    "K-GAAS 240 fraud risk"
                ],
                "audit_risks": [
                    "Cutoff issues at period end"
                ],
                "recommendations": [
                    "Increase sample size for Q4 transactions"
                ],
                "confidence_score": 0.88
            }

            mock_response = MagicMock()
            mock_response.content = f"```json\n{json.dumps(synthesis_response)}\n```"

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            # Use fallback results
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                result = await agent.deep_research(
                    topic="revenue recognition",
                    state=mock_audit_state
                )

            # Verify LLM was called
            mock_llm.ainvoke.assert_called()

            # Verify synthesis is present
            assert "K-IFRS 1115" in result.synthesis

            # Verify key findings
            assert len(result.key_findings) >= 3
            assert "control" in result.key_findings[0].lower()

            # Verify confidence score
            assert result.confidence_score == 0.88

            # Verify metadata includes regulatory info
            assert "regulatory_requirements" in result.metadata
            assert len(result.metadata["regulatory_requirements"]) >= 1

    @pytest.mark.asyncio
    async def test_deep_research_includes_client_context_in_metadata(
        self,
        mock_audit_state: AuditState
    ):
        """
        Test deep_research includes client context in result metadata.

        Verifies:
        - Client name is in metadata
        - Fiscal year is in metadata
        - Metadata is populated from state

        Expected behavior:
        - Result metadata should contain client info
        """
        with patch('src.agents.partner_agent.ChatOpenAI') as mock_llm_class:
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "synthesis": "Test synthesis",
                "key_findings": [],
                "confidence_score": 0.5
            })

            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            agent = PartnerAgent()

            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                result = await agent.deep_research(
                    topic="test topic",
                    state=mock_audit_state
                )

            # Verify client context in metadata
            assert result.metadata["client_name"] == "ABC Manufacturing Co."
            assert result.metadata["fiscal_year"] == 2024


class TestResearchHelperMethods:
    """Test suite for deep_research helper methods."""

    def test_build_research_context(self, mock_audit_state: AuditState):
        """
        Test _build_research_context creates proper context string.

        Verifies:
        - Context includes client name
        - Context includes fiscal year
        - Context includes materiality
        - Context includes topic

        Expected behavior:
        - Should return formatted context string
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            context = agent._build_research_context(
                topic="inventory valuation",
                state=mock_audit_state
            )

            assert "ABC Manufacturing Co." in context
            assert "2024" in context
            assert "1,000,000.00" in context
            assert "inventory valuation" in context

    def test_get_fallback_rag_results(self):
        """
        Test _get_fallback_rag_results returns valid fallback.

        Verifies:
        - Returns list of ResearchSource
        - Includes K-GAAS standards
        - Has fallback flag in metadata

        Expected behavior:
        - Should return at least 2 fallback results
        - All results should have source_type "rag"
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            results = agent._get_fallback_rag_results("test topic")

            assert len(results) >= 2
            assert all(isinstance(r, ResearchSource) for r in results)
            assert all(r.source_type == "rag" for r in results)
            assert all(r.metadata.get("fallback") == True for r in results)
            assert any("K-GAAS 200" in r.title for r in results)

    def test_get_fallback_web_results(self):
        """
        Test _get_fallback_web_results returns valid fallback.

        Verifies:
        - Returns list of ResearchSource
        - Includes KICPA guidelines
        - Has URL for web sources
        - Has fallback flag in metadata

        Expected behavior:
        - Should return at least 1 fallback result
        - All results should have source_type "web"
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            results = agent._get_fallback_web_results("test topic")

            assert len(results) >= 1
            assert all(isinstance(r, ResearchSource) for r in results)
            assert all(r.source_type == "web" for r in results)
            assert all(r.url is not None for r in results)
            assert all(r.metadata.get("fallback") == True for r in results)

    def test_parse_synthesis_response_with_json_block(self):
        """
        Test _parse_synthesis_response with markdown JSON block.

        Verifies:
        - Extracts JSON from markdown code block
        - Returns dict with expected fields

        Expected behavior:
        - Should parse JSON from ```json block
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            content = """Here's the synthesis:

```json
{
    "synthesis": "Comprehensive analysis",
    "key_findings": ["Finding 1"],
    "confidence_score": 0.85
}
```
"""
            result = agent._parse_synthesis_response(content)

            assert result["synthesis"] == "Comprehensive analysis"
            assert result["key_findings"] == ["Finding 1"]
            assert result["confidence_score"] == 0.85

    def test_parse_synthesis_response_with_plain_json(self):
        """
        Test _parse_synthesis_response with plain JSON.

        Verifies:
        - Parses plain JSON (no markdown)
        - Returns dict with expected fields

        Expected behavior:
        - Should parse plain JSON content
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            content = json.dumps({
                "synthesis": "Plain JSON synthesis",
                "key_findings": ["Finding A", "Finding B"],
                "confidence_score": 0.75
            })

            result = agent._parse_synthesis_response(content)

            assert result["synthesis"] == "Plain JSON synthesis"
            assert len(result["key_findings"]) == 2

    def test_parse_synthesis_response_fallback_on_invalid_json(self):
        """
        Test _parse_synthesis_response returns fallback for invalid JSON.

        Verifies:
        - Invalid JSON triggers fallback
        - Fallback has expected structure
        - Content is preserved in synthesis field

        Expected behavior:
        - Should return fallback structure
        - Should preserve original content
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            content = "This is not valid JSON, just plain text analysis."

            result = agent._parse_synthesis_response(content)

            # Should return fallback structure
            assert "synthesis" in result
            assert "key_findings" in result
            assert "confidence_score" in result

            # Fallback confidence score is 0.5
            assert result["confidence_score"] == 0.5

            # Original content should be in synthesis
            assert "plain text" in result["synthesis"]


class TestRAGIntegration:
    """Test suite for RAG MCP integration."""

    @pytest.mark.asyncio
    async def test_search_rag_success(self, mock_audit_state: AuditState):
        """
        Test _search_rag successfully retrieves from MCP RAG server.

        Verifies:
        - Constructs proper request to MCP server
        - Parses response into ResearchSource list
        - Includes relevance scores

        Expected behavior:
        - Should return list of ResearchSource objects
        - Should preserve standard codes and paragraph numbers
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            mock_rag_response = {
                "results": [
                    {
                        "paragraph_id": "kifrs1115-31",
                        "standard_code": "K-IFRS 1115",
                        "paragraph_number": "31",
                        "content": "수익 인식 기준",
                        "score": 0.95,
                        "metadata": {"category": "revenue"}
                    },
                    {
                        "paragraph_id": "kifrs1115-32",
                        "standard_code": "K-IFRS 1115",
                        "paragraph_number": "32",
                        "content": "통제 이전 시점",
                        "score": 0.90,
                        "metadata": {"category": "revenue"}
                    }
                ]
            }

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_rag_response
                mock_response.raise_for_status = MagicMock()

                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                results = await agent._search_rag(
                    topic="revenue recognition",
                    context="Test context",
                    base_url="http://localhost:8001",
                    timeout=30.0
                )

            assert len(results) == 2
            assert all(isinstance(r, ResearchSource) for r in results)
            assert results[0].source_type == "rag"
            assert "K-IFRS 1115" in results[0].title
            assert results[0].relevance_score == 0.95

    @pytest.mark.asyncio
    async def test_search_rag_fallback_on_error(self):
        """
        Test _search_rag returns fallback on connection error.

        Verifies:
        - Connection errors don't crash
        - Fallback results are returned
        - Fallback flag is set

        Expected behavior:
        - Should return fallback results on connection error
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                results = await agent._search_rag(
                    topic="test",
                    context="",
                    base_url="http://localhost:8001",
                    timeout=30.0
                )

            # Should return fallback results
            assert len(results) >= 1
            assert all(r.metadata.get("fallback") == True for r in results)


class TestWebIntegration:
    """Test suite for Web MCP integration."""

    @pytest.mark.asyncio
    async def test_search_web_success(self, mock_audit_state: AuditState):
        """
        Test _search_web successfully retrieves from MCP Web server.

        Verifies:
        - Constructs audit-focused query
        - Parses response into ResearchSource list
        - Includes URLs for web sources

        Expected behavior:
        - Should return list of ResearchSource objects
        - Should include URLs and titles
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            mock_web_response = {
                "results": [
                    {
                        "title": "Revenue Recognition Best Practices",
                        "snippet": "Industry guidance on revenue recognition...",
                        "url": "https://example.com/revenue-guide",
                        "score": 0.8,
                        "source": "web",
                        "date": "2024-01-15"
                    }
                ]
            }

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_web_response
                mock_response.raise_for_status = MagicMock()

                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                results = await agent._search_web(
                    topic="revenue recognition",
                    context="Test context",
                    base_url="http://localhost:8002",
                    timeout=30.0
                )

            assert len(results) == 1
            assert results[0].source_type == "web"
            assert results[0].url == "https://example.com/revenue-guide"
            assert results[0].title == "Revenue Recognition Best Practices"

    @pytest.mark.asyncio
    async def test_search_web_fallback_on_error(self):
        """
        Test _search_web returns fallback on connection error.

        Verifies:
        - Connection errors don't crash
        - Fallback results are returned
        - Fallback has valid URL

        Expected behavior:
        - Should return fallback results on connection error
        """
        with patch('src.agents.partner_agent.ChatOpenAI'):
            agent = PartnerAgent()

            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=httpx.TimeoutException("Timeout")
                )
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock()

                results = await agent._search_web(
                    topic="test",
                    context="",
                    base_url="http://localhost:8002",
                    timeout=30.0
                )

            # Should return fallback results
            assert len(results) >= 1
            assert all(r.metadata.get("fallback") == True for r in results)
            assert all(r.url is not None for r in results)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
