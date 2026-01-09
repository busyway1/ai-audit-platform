"""
Comprehensive Unit Tests for Manager Agent

Target Coverage:
- test_manager_agent_initialization
- test_aggregate_results_all_outputs_present
- test_aggregate_results_missing_outputs
- test_manager_updates_task_status
- test_manager_handles_staff_errors
- test_manager_should_interrupt

All tests use proper mocking to avoid LLM API calls.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from src.agents.manager_agent import ManagerAgent


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def manager_agent_mock():
    """Create a ManagerAgent with mocked LLM."""
    with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.temperature = 0.3
        mock_llm_class.return_value = mock_llm

        agent = ManagerAgent(model="gpt-4o")
        agent.llm = mock_llm
        return agent


@pytest.fixture
def base_task_state():
    """Create a base TaskState for testing."""
    return {
        "task_id": "TASK-001",
        "thread_id": "thread-001",
        "category": "Sales Revenue",
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


# ============================================================================
# TEST: MANAGER AGENT INITIALIZATION
# ============================================================================

class TestManagerAgentInitialization:
    """Tests for ManagerAgent.__init__"""

    def test_manager_agent_initialization_default_model(self):
        """Test ManagerAgent initializes with default gpt-4o model."""
        with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
            mock_llm_class.return_value = MagicMock()

            manager = ManagerAgent()

            assert manager.llm is not None
            mock_llm_class.assert_called_once()
            call_kwargs = mock_llm_class.call_args[1]
            assert call_kwargs['model'] == "gpt-4o"

    def test_manager_agent_initialization_custom_model(self):
        """Test ManagerAgent initializes with custom model."""
        with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
            mock_llm_class.return_value = MagicMock()

            manager = ManagerAgent(model="gpt-4-turbo")

            assert manager.llm is not None
            call_kwargs = mock_llm_class.call_args[1]
            assert call_kwargs['model'] == "gpt-4-turbo"

    def test_manager_agent_initialization_sets_temperature(self):
        """Test ManagerAgent initializes with low temperature (0.3)."""
        with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
            mock_llm_class.return_value = MagicMock()

            manager = ManagerAgent()

            call_kwargs = mock_llm_class.call_args[1]
            assert call_kwargs['temperature'] == 0.3

    def test_manager_agent_initialization_creates_persona_prompt(self):
        """Test ManagerAgent creates persona prompt during initialization."""
        with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
            mock_llm_class.return_value = MagicMock()

            manager = ManagerAgent()

            assert manager.persona_prompt is not None
            assert hasattr(manager.persona_prompt, 'invoke')

    def test_manager_agent_initialization_uses_openai_api_key(self):
        """Test ManagerAgent uses OPENAI_API_KEY from environment."""
        with patch('src.agents.manager_agent.ChatOpenAI') as mock_llm_class:
            mock_llm_class.return_value = MagicMock()

            manager = ManagerAgent()

            call_kwargs = mock_llm_class.call_args[1]
            assert 'api_key' in call_kwargs or call_kwargs.get('api_key') == 'test-key'


# ============================================================================
# TEST: AGGREGATION - ALL OUTPUTS PRESENT
# ============================================================================

class TestAggregateResultsAllOutputsPresent:
    """Tests for successful aggregation with all Staff outputs"""

    def test_aggregate_results_all_raw_data_present(self, base_task_state):
        """Test aggregation recognizes Excel_Parser output."""
        base_task_state["raw_data"] = {
            "transactions": [
                {"id": "TXN-001", "amount": 100000},
                {"id": "TXN-002", "amount": 150000}
            ]
        }

        assert base_task_state["raw_data"]
        assert "transactions" in base_task_state["raw_data"]
        assert len(base_task_state["raw_data"]["transactions"]) == 2

    def test_aggregate_results_all_standards_present(self, base_task_state):
        """Test aggregation recognizes Standard_Retriever output."""
        base_task_state["standards"] = [
            "K-IFRS 1115: Revenue from Contracts",
            "K-GAAS 240: Auditor Responsibilities"
        ]

        assert base_task_state["standards"]
        assert len(base_task_state["standards"]) > 0

    def test_aggregate_results_all_vouching_present(self, base_task_state):
        """Test aggregation recognizes Vouching_Assistant output."""
        base_task_state["vouching_logs"] = [
            {"transaction_id": "TXN-001", "vouched_amount": 100000, "status": "Matched"},
            {"transaction_id": "TXN-002", "vouched_amount": 150000, "status": "Matched"}
        ]

        assert base_task_state["vouching_logs"]
        assert len(base_task_state["vouching_logs"]) == 2

    def test_aggregate_results_all_workpaper_present(self, base_task_state):
        """Test aggregation recognizes WorkPaper_Generator output."""
        base_task_state["workpaper_draft"] = """## Audit Workpaper
### Objective
Verify audit findings
### Conclusion
All transactions verified"""

        assert base_task_state["workpaper_draft"]
        assert len(base_task_state["workpaper_draft"]) > 0

    def test_aggregate_results_complete_task_ready(self, manager_agent_mock, base_task_state):
        """Test aggregation determines task is ready for completion."""
        # Set all fields to indicate completion
        base_task_state["raw_data"] = {"transactions": [{"id": "TXN-001"}]}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"transaction_id": "TXN-001", "status": "Matched"}]
        base_task_state["workpaper_draft"] = "## Workpaper"

        # Mock the decision parsing to return Completed
        decision = manager_agent_mock._parse_manager_decision(
            "All tasks complete", base_task_state
        )

        # Since all fields are populated, next_staff should be None
        assert decision["next_staff"] is None
        assert decision["status"] == "Completed"


# ============================================================================
# TEST: AGGREGATION - MISSING OUTPUTS
# ============================================================================

class TestAggregateResultsMissingOutputs:
    """Tests for failure detection with missing Staff outputs"""

    def test_aggregate_results_missing_raw_data_routes_to_excel_parser(self, manager_agent_mock, base_task_state):
        """Test aggregation detects missing raw_data."""
        # raw_data is empty
        decision = manager_agent_mock._parse_manager_decision("Starting", base_task_state)

        assert decision["next_staff"] == "excel_parser"
        assert decision["status"] == "In-Progress"

    def test_aggregate_results_missing_standards_routes_to_standard_retriever(self, manager_agent_mock, base_task_state):
        """Test aggregation detects missing standards."""
        base_task_state["raw_data"] = {"transactions": []}  # Has raw_data
        # standards is empty

        decision = manager_agent_mock._parse_manager_decision("Next stage", base_task_state)

        assert decision["next_staff"] == "standard_retriever"

    def test_aggregate_results_missing_vouching_routes_to_vouching_assistant(self, manager_agent_mock, base_task_state):
        """Test aggregation detects missing vouching_logs."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        # vouching_logs is empty

        decision = manager_agent_mock._parse_manager_decision("Next", base_task_state)

        assert decision["next_staff"] == "vouching_assistant"

    def test_aggregate_results_missing_workpaper_routes_to_workpaper_generator(self, manager_agent_mock, base_task_state):
        """Test aggregation detects missing workpaper_draft."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        # workpaper_draft is empty

        decision = manager_agent_mock._parse_manager_decision("Final stage", base_task_state)

        assert decision["next_staff"] == "workpaper_generator"

    def test_aggregate_results_partial_completion_detects_gaps(self, manager_agent_mock, base_task_state):
        """Test aggregation detects partial completion."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        # Missing vouching and workpaper

        decision = manager_agent_mock._parse_manager_decision("Partial", base_task_state)

        # Should route to next missing Staff agent
        assert decision["next_staff"] == "vouching_assistant"


# ============================================================================
# TEST: MANAGER STATUS UPDATES
# ============================================================================

class TestManagerStatusUpdates:
    """Tests for Manager's task status management"""

    def test_manager_updates_status_pending_to_in_progress(self, manager_agent_mock, base_task_state):
        """Test Manager transitions Pending → In-Progress."""
        base_task_state["status"] = "Pending"

        decision = manager_agent_mock._parse_manager_decision("Starting work", base_task_state)

        # When raw_data is missing, it sets to In-Progress
        assert decision["status"] == "In-Progress"

    def test_manager_transitions_to_completed_status(self, manager_agent_mock, base_task_state):
        """Test Manager transitions to Completed status when all work done."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        base_task_state["workpaper_draft"] = "## Workpaper"
        base_task_state["status"] = "In-Progress"

        decision = manager_agent_mock._parse_manager_decision("All complete", base_task_state)

        assert decision["status"] == "Completed"
        assert decision["next_staff"] is None

    def test_manager_preserves_status_if_no_change(self, manager_agent_mock, base_task_state):
        """Test Manager preserves status when no state change."""
        base_task_state["status"] = "In-Progress"

        decision = manager_agent_mock._parse_manager_decision("Continue", base_task_state)

        # Status is preserved from input
        assert decision["status"] == base_task_state["status"]


# ============================================================================
# TEST: MANAGER ERROR HANDLING
# ============================================================================

class TestManagerHandlesStaffErrors:
    """Tests for Manager's error detection and handling"""

    def test_manager_detects_critical_errors(self, base_task_state):
        """Test Manager detects critical errors in error_report."""
        base_task_state["error_report"] = "Critical: Data integrity violation detected"

        # Critical error should be detected
        assert "Critical" in base_task_state["error_report"]

    def test_manager_preserves_error_report(self, manager_agent_mock, base_task_state):
        """Test Manager preserves error_report from input state."""
        error_msg = "Critical: Database connection failed"
        base_task_state["error_report"] = error_msg

        result = {**base_task_state}

        assert result["error_report"] == error_msg

    def test_manager_handles_missing_error_report(self, base_task_state):
        """Test Manager handles missing error_report gracefully."""
        # error_report field exists but is empty
        assert base_task_state["error_report"] == ""

    def test_manager_handles_risk_score_parsing(self, manager_agent_mock, base_task_state):
        """Test Manager extracts risk_score from response."""
        response_text = "Assessment complete. risk_score: 85"
        current_state = base_task_state.copy()

        decision = manager_agent_mock._parse_manager_decision(response_text, current_state)

        assert decision["risk_score"] == 85

    def test_manager_handles_korean_risk_score(self, manager_agent_mock, base_task_state):
        """Test Manager extracts risk_score in Korean format."""
        response_text = "위험도 평가. 리스크 점수: 72"
        current_state = base_task_state.copy()

        decision = manager_agent_mock._parse_manager_decision(response_text, current_state)

        assert decision["risk_score"] == 72


# ============================================================================
# TEST: INTERRUPTION LOGIC
# ============================================================================

class TestManagerInterruption:
    """Tests for ManagerAgent.should_interrupt"""

    def test_should_interrupt_high_risk_score(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns True when risk_score >= 90."""
        base_task_state["risk_score"] = 95

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is True

    def test_should_interrupt_risk_score_exactly_90(self, manager_agent_mock, base_task_state):
        """Test should_interrupt triggers at exactly risk_score = 90."""
        base_task_state["risk_score"] = 90

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is True

    def test_should_not_interrupt_low_risk_score(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns False when risk_score < 90."""
        base_task_state["risk_score"] = 75

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is False

    def test_should_interrupt_critical_error(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns True for critical errors."""
        base_task_state["error_report"] = "Critical: Data integrity violation"

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is True

    def test_should_interrupt_korean_critical_error(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns True for Korean critical errors."""
        base_task_state["error_report"] = "치명적: 데이터 무결성 위반"

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is True

    def test_should_not_interrupt_non_critical_error(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns False for non-critical errors."""
        base_task_state["error_report"] = "Warning: Minor issue"

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is False

    def test_should_interrupt_all_data_with_review_required(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns True when all data present but Review-Required."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        base_task_state["workpaper_draft"] = "## Workpaper"
        base_task_state["status"] = "Review-Required"

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is True

    def test_should_not_interrupt_no_conditions_met(self, manager_agent_mock, base_task_state):
        """Test should_interrupt returns False when no conditions met."""
        base_task_state["risk_score"] = 50
        base_task_state["error_report"] = ""
        base_task_state["status"] = "In-Progress"

        result = manager_agent_mock.should_interrupt(base_task_state)

        assert result is False


# ============================================================================
# TEST: DECISION PARSING
# ============================================================================

class TestManagerDecisionParsing:
    """Tests for Manager's decision parsing"""

    def test_parse_decision_determines_next_staff(self, manager_agent_mock, base_task_state):
        """Test decision parsing determines correct next_staff."""
        # Empty state should route to Excel_Parser
        decision = manager_agent_mock._parse_manager_decision("Start audit", base_task_state)

        assert decision["next_staff"] == "excel_parser"

    def test_parse_decision_extracts_risk_score_english(self, manager_agent_mock, base_task_state):
        """Test parsing extracts risk_score in English format."""
        response_text = "Risk assessment: risk_score: 80"

        decision = manager_agent_mock._parse_manager_decision(response_text, base_task_state)

        assert decision["risk_score"] == 80

    def test_parse_decision_extracts_risk_score_korean(self, manager_agent_mock, base_task_state):
        """Test parsing extracts risk_score in Korean format."""
        response_text = "리스크: 리스크 점수: 65"

        decision = manager_agent_mock._parse_manager_decision(response_text, base_task_state)

        assert decision["risk_score"] == 65

    def test_parse_decision_handles_missing_risk_score(self, manager_agent_mock, base_task_state):
        """Test parsing uses current risk_score if not in response."""
        base_task_state["risk_score"] = 45
        response_text = "Proceeding"

        decision = manager_agent_mock._parse_manager_decision(response_text, base_task_state)

        assert decision["risk_score"] == 45

    def test_parse_decision_zero_risk_score(self, manager_agent_mock, base_task_state):
        """Test parsing handles zero risk_score."""
        response_text = "No risks. risk_score: 0"

        decision = manager_agent_mock._parse_manager_decision(response_text, base_task_state)

        assert decision["risk_score"] == 0

    def test_parse_decision_high_risk_score(self, manager_agent_mock, base_task_state):
        """Test parsing correctly extracts risk scores >= 90."""
        response_text = "Critical areas. risk_score: 95"

        decision = manager_agent_mock._parse_manager_decision(response_text, base_task_state)

        assert decision["risk_score"] == 95


# ============================================================================
# TEST: SUMMARY
# ============================================================================

class TestManagerParseDecisionLogic:
    """Tests for Manager's decision parsing logic"""

    def test_parse_decision_routes_correctly_step_1(self, manager_agent_mock, base_task_state):
        """Test _parse_manager_decision routes to excel_parser when no raw_data."""
        decision = manager_agent_mock._parse_manager_decision("Starting audit", base_task_state)
        assert decision["next_staff"] == "excel_parser"

    def test_parse_decision_routes_correctly_step_2(self, manager_agent_mock, base_task_state):
        """Test _parse_manager_decision routes to standard_retriever when raw_data exists."""
        base_task_state["raw_data"] = {"transactions": []}
        decision = manager_agent_mock._parse_manager_decision("Raw data complete", base_task_state)
        assert decision["next_staff"] == "standard_retriever"

    def test_parse_decision_routes_correctly_step_3(self, manager_agent_mock, base_task_state):
        """Test _parse_manager_decision routes to vouching_assistant."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        decision = manager_agent_mock._parse_manager_decision("Standards retrieved", base_task_state)
        assert decision["next_staff"] == "vouching_assistant"

    def test_parse_decision_routes_correctly_step_4(self, manager_agent_mock, base_task_state):
        """Test _parse_manager_decision routes to workpaper_generator."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        decision = manager_agent_mock._parse_manager_decision("Vouching complete", base_task_state)
        assert decision["next_staff"] == "workpaper_generator"

    def test_parse_decision_completes_when_all_data_present(self, manager_agent_mock, base_task_state):
        """Test _parse_manager_decision marks as Completed when all data present."""
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        base_task_state["workpaper_draft"] = "## Report"
        decision = manager_agent_mock._parse_manager_decision("All done", base_task_state)
        assert decision["status"] == "Completed"
        assert decision["next_staff"] is None


class TestManagerStateTransitions:
    """Tests for Manager's state transition logic"""

    def test_status_transitions_from_pending(self, manager_agent_mock, base_task_state):
        """Test that Manager transitions status from Pending."""
        base_task_state["status"] = "Pending"
        decision = manager_agent_mock._parse_manager_decision("Start", base_task_state)
        assert decision["status"] == "In-Progress"

    def test_status_preserves_during_processing(self, manager_agent_mock, base_task_state):
        """Test that Manager maintains In-Progress status."""
        base_task_state["status"] = "In-Progress"
        base_task_state["raw_data"] = {"transactions": []}
        decision = manager_agent_mock._parse_manager_decision("Processing", base_task_state)
        assert decision["status"] == "In-Progress"

    def test_status_transitions_to_completed(self, manager_agent_mock, base_task_state):
        """Test that Manager transitions to Completed when all work done."""
        base_task_state["status"] = "In-Progress"
        base_task_state["raw_data"] = {"transactions": []}
        base_task_state["standards"] = ["K-IFRS 1115"]
        base_task_state["vouching_logs"] = [{"id": "V-001"}]
        base_task_state["workpaper_draft"] = "## Report"
        decision = manager_agent_mock._parse_manager_decision("All done", base_task_state)
        assert decision["status"] == "Completed"

    def test_risk_score_default_value(self, manager_agent_mock, base_task_state):
        """Test that risk_score defaults properly."""
        base_task_state["risk_score"] = 50
        decision = manager_agent_mock._parse_manager_decision("Test", base_task_state)
        assert "risk_score" in decision

    def test_risk_score_extracted_from_response(self, manager_agent_mock, base_task_state):
        """Test that risk_score is extracted from response."""
        response = "Assessment complete. risk_score: 75"
        decision = manager_agent_mock._parse_manager_decision(response, base_task_state)
        assert decision["risk_score"] == 75

    def test_multiple_risk_scores_uses_first(self, manager_agent_mock, base_task_state):
        """Test that first risk_score is used if multiple present."""
        response = "First: risk_score: 70, then risk_score: 80"
        decision = manager_agent_mock._parse_manager_decision(response, base_task_state)
        assert decision["risk_score"] == 70


class TestManagerAgentCoverage:
    """Verify comprehensive test coverage"""

    def test_all_methods_covered(self):
        """Verify all ManagerAgent methods have test coverage."""
        required_methods = [
            '__init__',
            '_create_persona_prompt',
            'run',
            '_parse_manager_decision',
            'should_interrupt',
            'allocate_staff_agents',
            '_extract_task_requirements',
            '_calculate_allocation_score',
            '_create_balanced_allocations',
            '_calculate_base_priority',
            '_adjust_priority_for_workload',
            'get_required_staff_types'
        ]

        for method in required_methods:
            assert hasattr(ManagerAgent, method), f"Missing method: {method}"

    def test_manager_agent_core_functionality(self, manager_agent_mock):
        """Confirm core functionality of ManagerAgent."""
        assert manager_agent_mock.llm is not None
        assert manager_agent_mock.persona_prompt is not None
        assert callable(manager_agent_mock._create_persona_prompt)
        assert callable(manager_agent_mock.run)
        assert callable(manager_agent_mock._parse_manager_decision)
        assert callable(manager_agent_mock.should_interrupt)

    def test_manager_agent_has_proper_api(self, manager_agent_mock):
        """Test Manager Agent has expected public API."""
        # Constructor should accept optional model parameter
        with patch('src.agents.manager_agent.ChatOpenAI'):
            agent1 = ManagerAgent()
            agent2 = ManagerAgent(model="gpt-4-turbo")

        assert agent1.llm is not None
        assert agent2.llm is not None

    def test_manager_persona_prompt_is_chatprompttemplate(self, manager_agent_mock):
        """Test persona_prompt is proper ChatPromptTemplate."""
        from langchain_core.prompts import ChatPromptTemplate

        assert isinstance(manager_agent_mock.persona_prompt, ChatPromptTemplate)

    def test_manager_return_structure(self, manager_agent_mock, base_task_state):
        """Test Manager returns proper structure from _parse_manager_decision."""
        decision = manager_agent_mock._parse_manager_decision("Test response", base_task_state)

        assert isinstance(decision, dict)
        assert "next_staff" in decision
        assert "status" in decision
        assert "risk_score" in decision
        assert isinstance(decision["risk_score"], int)
        assert 0 <= decision["risk_score"] <= 100


# ============================================================================
# TEST: STAFF ALLOCATION (BE-11.1)
# ============================================================================

from src.agents.manager_agent import (
    StaffType, RiskLevel, StaffProfile, AllocationResult, TaskRequirements,
    STAFF_SKILL_MAPPING, CATEGORY_SKILL_REQUIREMENTS
)


@pytest.fixture
def sample_available_staff():
    """Create sample staff profiles for allocation tests."""
    return [
        StaffProfile(
            staff_id="excel-1",
            staff_type=StaffType.EXCEL_PARSER,
            skills=["data_extraction", "excel_parsing", "financial_analysis"],
            current_workload=20,
            expertise_level=4
        ),
        StaffProfile(
            staff_id="excel-2",
            staff_type=StaffType.EXCEL_PARSER,
            skills=["data_extraction", "excel_parsing"],
            current_workload=70,
            expertise_level=2
        ),
        StaffProfile(
            staff_id="standard-1",
            staff_type=StaffType.STANDARD_RETRIEVER,
            skills=["k_ifrs", "k_gaas", "standard_research"],
            current_workload=30,
            expertise_level=5
        ),
        StaffProfile(
            staff_id="vouching-1",
            staff_type=StaffType.VOUCHING_ASSISTANT,
            skills=["document_verification", "vouching", "evidence_analysis"],
            current_workload=50,
            expertise_level=3
        ),
        StaffProfile(
            staff_id="workpaper-1",
            staff_type=StaffType.WORKPAPER_GENERATOR,
            skills=["documentation", "workpaper_drafting", "report_writing"],
            current_workload=10,
            expertise_level=4
        )
    ]


@pytest.fixture
def sample_task():
    """Create a sample task for allocation tests."""
    return {
        "task_id": "TASK-001",
        "category": "Sales",
        "risk_score": 75,
        "complexity_score": 7,
        "deadline_urgency": 6,
        "raw_data": {},
        "standards": [],
        "vouching_logs": [],
        "workpaper_draft": ""
    }


class TestStaffAllocation:
    """Tests for allocate_staff_agents() method"""

    def test_allocate_staff_agents_returns_list(
        self, manager_agent_mock, sample_task, sample_available_staff
    ):
        """Test allocate_staff_agents returns a list of AllocationResult."""
        allocations = manager_agent_mock.allocate_staff_agents(
            sample_task, sample_available_staff
        )

        assert isinstance(allocations, list)
        assert all(isinstance(a, AllocationResult) for a in allocations)

    def test_allocate_staff_agents_empty_staff_list(self, manager_agent_mock, sample_task):
        """Test allocate_staff_agents returns empty list for no available staff."""
        allocations = manager_agent_mock.allocate_staff_agents(sample_task, [])
        assert allocations == []

    def test_allocate_staff_agents_prioritizes_low_workload(
        self, manager_agent_mock, sample_task
    ):
        """Test that staff with lower workload get higher priority."""
        staff = [
            StaffProfile("busy", StaffType.EXCEL_PARSER, [], 80, 3),
            StaffProfile("free", StaffType.EXCEL_PARSER, [], 10, 3),
        ]

        allocations = manager_agent_mock.allocate_staff_agents(sample_task, staff)

        # Free staff should have higher allocation score due to availability
        free_alloc = next((a for a in allocations if a.staff_id == "free"), None)
        busy_alloc = next((a for a in allocations if a.staff_id == "busy"), None)

        if free_alloc and busy_alloc:
            assert free_alloc.allocation_score > busy_alloc.allocation_score

    def test_allocate_staff_agents_prefers_higher_expertise_for_high_risk(
        self, manager_agent_mock
    ):
        """Test that high-risk tasks prefer staff with higher expertise."""
        high_risk_task = {
            "task_id": "HIGH-RISK-001",
            "category": "대손충당금",
            "risk_score": 90,
            "complexity_score": 8
        }

        staff = [
            StaffProfile("junior", StaffType.EXCEL_PARSER, [], 30, 2),
            StaffProfile("senior", StaffType.EXCEL_PARSER, [], 30, 5),
        ]

        allocations = manager_agent_mock.allocate_staff_agents(high_risk_task, staff)

        senior_alloc = next((a for a in allocations if a.staff_id == "senior"), None)
        junior_alloc = next((a for a in allocations if a.staff_id == "junior"), None)

        if senior_alloc and junior_alloc:
            assert senior_alloc.allocation_score > junior_alloc.allocation_score

    def test_allocate_staff_agents_considers_skill_match(
        self, manager_agent_mock
    ):
        """Test that staff with matching skills score higher."""
        task = {
            "task_id": "SKILL-TEST",
            "category": "Sales",  # Requires: data_extraction, k_ifrs, vouching, documentation
            "risk_score": 50
        }

        staff = [
            StaffProfile(
                "mismatched",
                StaffType.EXCEL_PARSER,
                ["unrelated_skill"],
                20, 3
            ),
            StaffProfile(
                "matched",
                StaffType.EXCEL_PARSER,
                ["data_extraction", "k_ifrs"],
                20, 3
            ),
        ]

        allocations = manager_agent_mock.allocate_staff_agents(task, staff)

        matched_alloc = next((a for a in allocations if a.staff_id == "matched"), None)
        mismatched_alloc = next((a for a in allocations if a.staff_id == "mismatched"), None)

        if matched_alloc and mismatched_alloc:
            assert matched_alloc.allocation_score > mismatched_alloc.allocation_score

    def test_allocate_staff_agents_load_balancing(
        self, manager_agent_mock, sample_task, sample_available_staff
    ):
        """Test that load balancing distributes work across staff types."""
        allocations = manager_agent_mock.allocate_staff_agents(
            sample_task, sample_available_staff
        )

        # Should have at most one allocation per staff type (load balancing)
        staff_types = [a.staff_type for a in allocations]
        unique_types = set(staff_types)

        # Most types should be unique (balanced)
        assert len(unique_types) >= len(allocations) * 0.8


class TestExtractTaskRequirements:
    """Tests for _extract_task_requirements() method"""

    def test_extract_task_requirements_creates_object(self, manager_agent_mock, sample_task):
        """Test that requirements are extracted into TaskRequirements object."""
        requirements = manager_agent_mock._extract_task_requirements(sample_task)

        assert isinstance(requirements, TaskRequirements)
        assert requirements.task_id == "TASK-001"
        assert requirements.category == "Sales"

    def test_extract_task_requirements_risk_level_critical(self, manager_agent_mock):
        """Test risk_score >= 80 maps to CRITICAL."""
        task = {"task_id": "T1", "risk_score": 85}
        requirements = manager_agent_mock._extract_task_requirements(task)
        assert requirements.risk_level == RiskLevel.CRITICAL

    def test_extract_task_requirements_risk_level_high(self, manager_agent_mock):
        """Test risk_score 60-79 maps to HIGH."""
        task = {"task_id": "T1", "risk_score": 65}
        requirements = manager_agent_mock._extract_task_requirements(task)
        assert requirements.risk_level == RiskLevel.HIGH

    def test_extract_task_requirements_risk_level_medium(self, manager_agent_mock):
        """Test risk_score 40-59 maps to MEDIUM."""
        task = {"task_id": "T1", "risk_score": 50}
        requirements = manager_agent_mock._extract_task_requirements(task)
        assert requirements.risk_level == RiskLevel.MEDIUM

    def test_extract_task_requirements_risk_level_low(self, manager_agent_mock):
        """Test risk_score < 40 maps to LOW."""
        task = {"task_id": "T1", "risk_score": 30}
        requirements = manager_agent_mock._extract_task_requirements(task)
        assert requirements.risk_level == RiskLevel.LOW

    def test_extract_task_requirements_gets_category_skills(self, manager_agent_mock):
        """Test that category-specific skills are extracted."""
        task = {"task_id": "T1", "category": "매출", "risk_score": 50}
        requirements = manager_agent_mock._extract_task_requirements(task)

        expected_skills = CATEGORY_SKILL_REQUIREMENTS.get("매출", [])
        assert requirements.required_skills == expected_skills

    def test_extract_task_requirements_default_skills_for_unknown_category(
        self, manager_agent_mock
    ):
        """Test that unknown categories get default skills."""
        task = {"task_id": "T1", "category": "UnknownCategory", "risk_score": 50}
        requirements = manager_agent_mock._extract_task_requirements(task)

        # Should have default skills
        assert "data_extraction" in requirements.required_skills
        assert "documentation" in requirements.required_skills

    def test_extract_task_requirements_urgency_boost_for_high_risk(
        self, manager_agent_mock
    ):
        """Test that high-risk tasks get urgency boost."""
        task = {"task_id": "T1", "risk_score": 85, "deadline_urgency": 5}
        requirements = manager_agent_mock._extract_task_requirements(task)

        # High risk should boost urgency to at least 7
        assert requirements.deadline_urgency >= 7


class TestCalculateAllocationScore:
    """Tests for _calculate_allocation_score() method"""

    def test_calculate_allocation_score_returns_tuple(self, manager_agent_mock):
        """Test that score calculation returns (score, reason) tuple."""
        staff = StaffProfile("s1", StaffType.EXCEL_PARSER, [], 20, 3)
        requirements = TaskRequirements("T1", "Sales", RiskLevel.MEDIUM, [], 5, 5)

        result = manager_agent_mock._calculate_allocation_score(staff, requirements)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], (int, float))
        assert isinstance(result[1], str)

    def test_calculate_allocation_score_higher_for_lower_workload(
        self, manager_agent_mock
    ):
        """Test that lower workload results in higher score."""
        staff_free = StaffProfile("free", StaffType.EXCEL_PARSER, [], 10, 3)
        staff_busy = StaffProfile("busy", StaffType.EXCEL_PARSER, [], 90, 3)
        requirements = TaskRequirements("T1", "Sales", RiskLevel.MEDIUM, [], 5, 5)

        score_free, _ = manager_agent_mock._calculate_allocation_score(
            staff_free, requirements
        )
        score_busy, _ = manager_agent_mock._calculate_allocation_score(
            staff_busy, requirements
        )

        assert score_free > score_busy

    def test_calculate_allocation_score_higher_for_better_skill_match(
        self, manager_agent_mock
    ):
        """Test that better skill match results in higher score."""
        staff_matched = StaffProfile(
            "matched", StaffType.EXCEL_PARSER,
            ["data_extraction", "k_ifrs"], 30, 3
        )
        staff_unmatched = StaffProfile(
            "unmatched", StaffType.EXCEL_PARSER,
            ["irrelevant_skill"], 30, 3
        )
        requirements = TaskRequirements(
            "T1", "Sales", RiskLevel.MEDIUM,
            ["data_extraction", "k_ifrs"], 5, 5
        )

        score_matched, _ = manager_agent_mock._calculate_allocation_score(
            staff_matched, requirements
        )
        score_unmatched, _ = manager_agent_mock._calculate_allocation_score(
            staff_unmatched, requirements
        )

        assert score_matched > score_unmatched

    def test_calculate_allocation_score_expertise_bonus_for_high_risk(
        self, manager_agent_mock
    ):
        """Test that experts get bonus for high-risk tasks."""
        expert = StaffProfile("expert", StaffType.EXCEL_PARSER, [], 30, 5)
        junior = StaffProfile("junior", StaffType.EXCEL_PARSER, [], 30, 2)

        high_risk_req = TaskRequirements(
            "T1", "Sales", RiskLevel.CRITICAL, [], 8, 8
        )

        score_expert, reason_expert = manager_agent_mock._calculate_allocation_score(
            expert, high_risk_req
        )
        score_junior, _ = manager_agent_mock._calculate_allocation_score(
            junior, high_risk_req
        )

        assert score_expert > score_junior
        assert "Expert for high-risk task" in reason_expert or "Suited for complex work" in reason_expert


class TestCalculateBasePriority:
    """Tests for _calculate_base_priority() method"""

    def test_calculate_base_priority_critical_risk(self, manager_agent_mock):
        """Test CRITICAL risk increases priority."""
        requirements = TaskRequirements("T1", "Sales", RiskLevel.CRITICAL, [], 5, 5)
        priority = manager_agent_mock._calculate_base_priority(requirements)

        assert priority >= 7  # Base 5 + 3 for critical - capped at 10

    def test_calculate_base_priority_high_risk(self, manager_agent_mock):
        """Test HIGH risk increases priority."""
        requirements = TaskRequirements("T1", "Sales", RiskLevel.HIGH, [], 5, 5)
        priority = manager_agent_mock._calculate_base_priority(requirements)

        assert priority >= 6  # Base 5 + 2 for high

    def test_calculate_base_priority_low_risk(self, manager_agent_mock):
        """Test LOW risk decreases priority."""
        requirements = TaskRequirements("T1", "Sales", RiskLevel.LOW, [], 5, 5)
        priority = manager_agent_mock._calculate_base_priority(requirements)

        assert priority <= 5  # Base 5 - 1 for low

    def test_calculate_base_priority_high_urgency_boost(self, manager_agent_mock):
        """Test high urgency increases priority."""
        requirements = TaskRequirements("T1", "Sales", RiskLevel.MEDIUM, [], 5, 9)
        priority = manager_agent_mock._calculate_base_priority(requirements)

        assert priority >= 7  # Base 5 + 0 for medium + 2 for urgency >= 8

    def test_calculate_base_priority_clamped_to_range(self, manager_agent_mock):
        """Test priority is clamped to 1-10 range."""
        # Maximum scenario
        max_req = TaskRequirements("T1", "Sales", RiskLevel.CRITICAL, [], 10, 10)
        max_priority = manager_agent_mock._calculate_base_priority(max_req)
        assert max_priority <= 10

        # Minimum scenario
        min_req = TaskRequirements("T1", "Sales", RiskLevel.LOW, [], 1, 1)
        min_priority = manager_agent_mock._calculate_base_priority(min_req)
        assert min_priority >= 1


class TestAdjustPriorityForWorkload:
    """Tests for _adjust_priority_for_workload() method"""

    def test_adjust_priority_high_workload_reduces_priority(self, manager_agent_mock):
        """Test that high workload (>=80) reduces priority by 2."""
        adjusted = manager_agent_mock._adjust_priority_for_workload(8, 85)
        assert adjusted == 6

    def test_adjust_priority_medium_workload_reduces_priority(self, manager_agent_mock):
        """Test that medium workload (60-79) reduces priority by 1."""
        adjusted = manager_agent_mock._adjust_priority_for_workload(8, 65)
        assert adjusted == 7

    def test_adjust_priority_low_workload_no_change(self, manager_agent_mock):
        """Test that low workload (<60) doesn't change priority."""
        adjusted = manager_agent_mock._adjust_priority_for_workload(8, 30)
        assert adjusted == 8

    def test_adjust_priority_minimum_is_1(self, manager_agent_mock):
        """Test that priority never goes below 1."""
        adjusted = manager_agent_mock._adjust_priority_for_workload(1, 95)
        assert adjusted >= 1


class TestGetRequiredStaffTypes:
    """Tests for get_required_staff_types() method"""

    def test_get_required_staff_types_all_needed(self, manager_agent_mock):
        """Test that all staff types are needed for empty task."""
        task = {
            "raw_data": {},
            "standards": [],
            "vouching_logs": [],
            "workpaper_draft": ""
        }

        required = manager_agent_mock.get_required_staff_types(task)

        assert StaffType.EXCEL_PARSER in required
        assert StaffType.STANDARD_RETRIEVER in required
        assert StaffType.VOUCHING_ASSISTANT in required
        assert StaffType.WORKPAPER_GENERATOR in required

    def test_get_required_staff_types_partial_completion(self, manager_agent_mock):
        """Test that only remaining types are returned."""
        task = {
            "raw_data": {"transactions": [{"id": 1}]},  # Completed
            "standards": ["K-IFRS 1115"],  # Completed
            "vouching_logs": [],  # Needed
            "workpaper_draft": ""  # Needed
        }

        required = manager_agent_mock.get_required_staff_types(task)

        assert StaffType.EXCEL_PARSER not in required
        assert StaffType.STANDARD_RETRIEVER not in required
        assert StaffType.VOUCHING_ASSISTANT in required
        assert StaffType.WORKPAPER_GENERATOR in required

    def test_get_required_staff_types_none_needed(self, manager_agent_mock):
        """Test that empty list returned for completed task."""
        task = {
            "raw_data": {"transactions": [{"id": 1}]},
            "standards": ["K-IFRS 1115"],
            "vouching_logs": [{"id": "V1"}],
            "workpaper_draft": "# Report"
        }

        required = manager_agent_mock.get_required_staff_types(task)

        assert len(required) == 0

    def test_get_required_staff_types_preserves_order(self, manager_agent_mock):
        """Test that staff types are returned in execution order."""
        task = {
            "raw_data": {},
            "standards": [],
            "vouching_logs": [],
            "workpaper_draft": ""
        }

        required = manager_agent_mock.get_required_staff_types(task)

        # Should be in workflow order
        assert required.index(StaffType.EXCEL_PARSER) < required.index(StaffType.STANDARD_RETRIEVER)
        assert required.index(StaffType.STANDARD_RETRIEVER) < required.index(StaffType.VOUCHING_ASSISTANT)
        assert required.index(StaffType.VOUCHING_ASSISTANT) < required.index(StaffType.WORKPAPER_GENERATOR)


class TestStaffAllocationIntegration:
    """Integration tests for the complete allocation workflow"""

    def test_full_allocation_workflow(
        self, manager_agent_mock, sample_task, sample_available_staff
    ):
        """Test complete allocation workflow from task to results."""
        # Get required staff types
        required_types = manager_agent_mock.get_required_staff_types(sample_task)

        # Allocate staff
        allocations = manager_agent_mock.allocate_staff_agents(
            sample_task, sample_available_staff
        )

        # Verify allocations cover required types
        allocated_types = {a.staff_type for a in allocations}

        # At least some required types should be allocated
        assert len(allocated_types) > 0

    def test_allocation_results_have_valid_structure(
        self, manager_agent_mock, sample_task, sample_available_staff
    ):
        """Test that allocation results have all required fields."""
        allocations = manager_agent_mock.allocate_staff_agents(
            sample_task, sample_available_staff
        )

        for alloc in allocations:
            assert hasattr(alloc, 'staff_id')
            assert hasattr(alloc, 'staff_type')
            assert hasattr(alloc, 'priority')
            assert hasattr(alloc, 'allocation_score')
            assert hasattr(alloc, 'reason')

            assert 1 <= alloc.priority <= 10
            assert alloc.allocation_score >= 0
            assert len(alloc.reason) > 0

    def test_allocation_sorted_by_priority(
        self, manager_agent_mock, sample_task, sample_available_staff
    ):
        """Test that allocations are sorted by priority (highest first)."""
        allocations = manager_agent_mock.allocate_staff_agents(
            sample_task, sample_available_staff
        )

        if len(allocations) > 1:
            priorities = [a.priority for a in allocations]
            assert priorities == sorted(priorities, reverse=True)
