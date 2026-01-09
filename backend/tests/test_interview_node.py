"""
Comprehensive Unit Tests for Interview Node

Target Coverage:
- interview_node() - Main interview workflow
- wait_for_interview_completion_node() - HITL review checkpoint
- Helper functions for question management and response processing
- Dynamic question generation
- Specification document generation

Coverage Target: 80%+
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
from datetime import datetime

from src.graph.nodes.interview_node import (
    interview_node,
    wait_for_interview_completion_node,
    get_interview_progress,
    validate_interview_responses,
    _determine_current_phase,
    _get_phase_questions,
    _get_question_phase,
    _process_interview_responses,
    _process_dynamic_responses,
    _check_response_triggers,
    _parse_dynamic_questions,
    _parse_specification,
    _create_fallback_specification,
    InterviewQuestion,
    InterviewResponse,
    InterviewSession,
    QuestionCategory,
    QuestionType,
    CHECKLIST_QUESTIONS,
)
from src.graph.state import AuditState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def base_audit_state() -> AuditState:
    """Create a base AuditState for testing."""
    return {
        "messages": [],
        "project_id": "PROJECT-001",
        "client_name": "테스트 제조회사",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0,
        "audit_plan": {},
        "tasks": [],
        "next_action": "CONTINUE",
        "is_approved": False,
        "shared_documents": [],
        "interview_responses": [],
        "interview_complete": False,
    }


@pytest.fixture
def state_with_partial_responses(base_audit_state) -> AuditState:
    """Create state with some interview responses."""
    base_audit_state["interview_responses"] = [
        {
            "question_id": "Q001",
            "response_text": "제조업 특성상 재고자산 감사가 중요합니다.",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"category": "client_overview"}
        },
        {
            "question_id": "Q002",
            "response_text": "수익 인식 시점에 대한 우려가 있습니다.",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"category": "client_overview"}
        },
        {
            "question_id": "Q003",
            "response_text": "예, 중요함",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"category": "client_overview"}
        },
    ]
    return base_audit_state


@pytest.fixture
def state_with_all_responses(base_audit_state) -> AuditState:
    """Create state with all required responses."""
    responses = []
    for q in CHECKLIST_QUESTIONS:
        if q.is_required:
            responses.append({
                "question_id": q.id,
                "response_text": "테스트 응답입니다.",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"category": q.category.value}
            })
    base_audit_state["interview_responses"] = responses
    return base_audit_state


@pytest.fixture
def state_interview_complete(state_with_all_responses) -> AuditState:
    """Create state with completed interview."""
    state_with_all_responses["interview_complete"] = True
    state_with_all_responses["specification"] = {
        "executive_summary": "테스트 요약",
        "risk_assessment": {
            "high_risk_areas": ["수익인식"],
            "medium_risk_areas": ["재고자산"],
            "low_risk_areas": []
        },
        "key_audit_areas": [],
        "special_procedures": [],
        "resource_requirements": {},
        "timeline_notes": ""
    }
    return state_with_all_responses


@pytest.fixture
def sample_interview_questions() -> List[InterviewQuestion]:
    """Create sample interview questions."""
    return [
        InterviewQuestion(
            id="TEST-001",
            category=QuestionCategory.CLIENT_OVERVIEW,
            question_type=QuestionType.CHECKLIST,
            question_text="테스트 질문 1",
            is_required=True
        ),
        InterviewQuestion(
            id="TEST-002",
            category=QuestionCategory.BUSINESS_OPERATIONS,
            question_type=QuestionType.CHECKLIST,
            question_text="테스트 질문 2",
            is_required=False,
            options=["옵션1", "옵션2", "옵션3"]
        ),
    ]


@pytest.fixture
def sample_responses() -> List[Dict[str, Any]]:
    """Create sample interview responses."""
    return [
        {
            "question_id": "Q001",
            "response_text": "재고자산 중점 감사 필요",
            "timestamp": "2024-01-15T10:00:00",
            "metadata": {"category": "client_overview"}
        },
        {
            "question_id": "Q002",
            "response_text": "수익 인식 우려사항 있음",
            "timestamp": "2024-01-15T10:01:00",
            "metadata": {"category": "client_overview"}
        },
    ]


# ============================================================================
# TEST: DATA STRUCTURES
# ============================================================================

class TestDataStructures:
    """Tests for interview data structures."""

    def test_question_category_enum_values(self):
        """Test QuestionCategory enum has expected values."""
        assert QuestionCategory.CLIENT_OVERVIEW.value == "client_overview"
        assert QuestionCategory.BUSINESS_OPERATIONS.value == "business_operations"
        assert QuestionCategory.RISK_FACTORS.value == "risk_factors"

    def test_question_type_enum_values(self):
        """Test QuestionType enum has expected values."""
        assert QuestionType.CHECKLIST.value == "checklist"
        assert QuestionType.DYNAMIC.value == "dynamic"

    def test_interview_question_creation(self):
        """Test InterviewQuestion dataclass creation."""
        q = InterviewQuestion(
            id="TEST-001",
            category=QuestionCategory.CLIENT_OVERVIEW,
            question_type=QuestionType.CHECKLIST,
            question_text="Test question"
        )
        assert q.id == "TEST-001"
        assert q.is_required is True  # Default
        assert q.options == []  # Default

    def test_interview_question_with_options(self):
        """Test InterviewQuestion with options."""
        q = InterviewQuestion(
            id="TEST-002",
            category=QuestionCategory.RISK_FACTORS,
            question_type=QuestionType.CHECKLIST,
            question_text="Select risk level",
            options=["Low", "Medium", "High"]
        )
        assert len(q.options) == 3

    def test_interview_response_creation(self):
        """Test InterviewResponse dataclass creation."""
        r = InterviewResponse(
            question_id="Q001",
            response_text="Test response"
        )
        assert r.question_id == "Q001"
        assert r.response_text == "Test response"
        assert r.timestamp is not None
        assert r.metadata == {}

    def test_interview_session_creation(self):
        """Test InterviewSession dataclass creation."""
        session = InterviewSession(
            session_id="SESSION-001",
            project_id="PROJECT-001",
            current_phase=1,
            total_phases=5,
            questions_asked=[],
            responses=[]
        )
        assert session.is_complete is False
        assert session.specification is None


# ============================================================================
# TEST: CHECKLIST QUESTIONS
# ============================================================================

class TestChecklistQuestions:
    """Tests for predefined checklist questions."""

    def test_checklist_questions_not_empty(self):
        """Test that checklist questions are defined."""
        assert len(CHECKLIST_QUESTIONS) > 0

    def test_all_questions_have_required_fields(self):
        """Test that all questions have required fields."""
        for q in CHECKLIST_QUESTIONS:
            assert q.id is not None
            assert q.category is not None
            assert q.question_type is not None
            assert q.question_text is not None

    def test_questions_have_unique_ids(self):
        """Test that all question IDs are unique."""
        ids = [q.id for q in CHECKLIST_QUESTIONS]
        assert len(ids) == len(set(ids))

    def test_questions_cover_all_categories(self):
        """Test that questions cover multiple categories."""
        categories = set(q.category for q in CHECKLIST_QUESTIONS)
        assert len(categories) >= 3

    def test_required_questions_exist(self):
        """Test that there are required questions."""
        required = [q for q in CHECKLIST_QUESTIONS if q.is_required]
        assert len(required) > 0

    def test_optional_questions_exist(self):
        """Test that there are optional questions."""
        optional = [q for q in CHECKLIST_QUESTIONS if not q.is_required]
        assert len(optional) > 0


# ============================================================================
# TEST: PHASE DETERMINATION
# ============================================================================

class TestPhaseDetermination:
    """Tests for interview phase determination."""

    def test_empty_responses_returns_phase_1(self):
        """Test that empty responses return phase 1."""
        phase = _determine_current_phase([])
        assert phase == 1

    def test_partial_responses_returns_correct_phase(self, sample_responses):
        """Test phase determination with partial responses."""
        phase = _determine_current_phase(sample_responses)
        # Should return first incomplete phase
        assert phase >= 1

    def test_get_question_phase_client_overview(self):
        """Test phase mapping for CLIENT_OVERVIEW."""
        phase = _get_question_phase(QuestionCategory.CLIENT_OVERVIEW)
        assert phase == 1

    def test_get_question_phase_business_operations(self):
        """Test phase mapping for BUSINESS_OPERATIONS."""
        phase = _get_question_phase(QuestionCategory.BUSINESS_OPERATIONS)
        assert phase == 2

    def test_get_question_phase_risk_factors(self):
        """Test phase mapping for RISK_FACTORS."""
        phase = _get_question_phase(QuestionCategory.RISK_FACTORS)
        assert phase == 3

    def test_get_question_phase_special_considerations(self):
        """Test phase mapping for SPECIAL_CONSIDERATIONS."""
        phase = _get_question_phase(QuestionCategory.SPECIAL_CONSIDERATIONS)
        assert phase == 5


# ============================================================================
# TEST: PHASE QUESTIONS
# ============================================================================

class TestPhaseQuestions:
    """Tests for getting phase-specific questions."""

    def test_phase_1_returns_client_overview(self):
        """Test phase 1 returns CLIENT_OVERVIEW questions."""
        questions = _get_phase_questions(1)
        assert all(q.category == QuestionCategory.CLIENT_OVERVIEW for q in questions)

    def test_phase_2_returns_business_operations(self):
        """Test phase 2 returns BUSINESS_OPERATIONS questions."""
        questions = _get_phase_questions(2)
        assert all(q.category == QuestionCategory.BUSINESS_OPERATIONS for q in questions)

    def test_phase_3_returns_risk_factors(self):
        """Test phase 3 returns RISK_FACTORS questions."""
        questions = _get_phase_questions(3)
        assert all(q.category == QuestionCategory.RISK_FACTORS for q in questions)

    def test_phase_5_returns_special_considerations(self):
        """Test phase 5 returns SPECIAL_CONSIDERATIONS questions."""
        questions = _get_phase_questions(5)
        assert any(q.category == QuestionCategory.SPECIAL_CONSIDERATIONS for q in questions)

    def test_invalid_phase_returns_empty(self):
        """Test invalid phase returns empty list."""
        questions = _get_phase_questions(99)
        assert questions == []

    def test_phase_6_returns_empty(self):
        """Test phase 6 (completion) returns empty list."""
        questions = _get_phase_questions(6)
        assert questions == []


# ============================================================================
# TEST: RESPONSE PROCESSING
# ============================================================================

class TestResponseProcessing:
    """Tests for interview response processing."""

    def test_process_interview_responses_basic(self, sample_interview_questions):
        """Test basic response processing."""
        result = {"answers": {"TEST-001": "Answer 1", "TEST-002": "Answer 2"}}
        responses = _process_interview_responses(result, sample_interview_questions)

        assert len(responses) == 2
        assert responses[0]["question_id"] == "TEST-001"
        assert responses[0]["response_text"] == "Answer 1"

    def test_process_interview_responses_partial(self, sample_interview_questions):
        """Test processing with partial answers."""
        result = {"answers": {"TEST-001": "Answer 1"}}
        responses = _process_interview_responses(result, sample_interview_questions)

        assert len(responses) == 1

    def test_process_interview_responses_empty(self, sample_interview_questions):
        """Test processing with no answers."""
        result = {"answers": {}}
        responses = _process_interview_responses(result, sample_interview_questions)

        assert len(responses) == 0

    def test_process_interview_responses_has_metadata(self, sample_interview_questions):
        """Test that processed responses include metadata."""
        result = {"answers": {"TEST-001": "Answer 1"}}
        responses = _process_interview_responses(result, sample_interview_questions)

        assert "metadata" in responses[0]
        assert "category" in responses[0]["metadata"]

    def test_process_dynamic_responses(self):
        """Test processing dynamic question responses."""
        result = {"answers": {"DYN-001": "Dynamic answer"}}
        responses = _process_dynamic_responses(result)

        assert len(responses) == 1
        assert responses[0]["question_id"] == "DYN-001"
        assert responses[0]["metadata"]["question_type"] == "dynamic"


# ============================================================================
# TEST: RESPONSE TRIGGERS
# ============================================================================

class TestResponseTriggers:
    """Tests for follow-up question triggers."""

    def test_trigger_on_high_risk_keyword(self):
        """Test trigger activation on '위험' keyword."""
        responses = [{"response_text": "이 영역은 위험합니다."}]
        assert _check_response_triggers(responses) is True

    def test_trigger_on_important_keyword(self):
        """Test trigger activation on '중요' keyword."""
        responses = [{"response_text": "중요한 고려사항이 있습니다."}]
        assert _check_response_triggers(responses) is True

    def test_trigger_on_concern_keyword(self):
        """Test trigger activation on '우려' keyword."""
        responses = [{"response_text": "우려되는 사항입니다."}]
        assert _check_response_triggers(responses) is True

    def test_no_trigger_on_normal_response(self):
        """Test no trigger on normal response."""
        responses = [{"response_text": "특별한 사항 없음"}]
        assert _check_response_triggers(responses) is False

    def test_trigger_empty_responses(self):
        """Test trigger with empty responses."""
        assert _check_response_triggers([]) is False

    def test_trigger_case_insensitive(self):
        """Test trigger is case insensitive."""
        responses = [{"response_text": "높음"}]
        assert _check_response_triggers(responses) is True


# ============================================================================
# TEST: DYNAMIC QUESTION PARSING
# ============================================================================

class TestDynamicQuestionParsing:
    """Tests for parsing LLM-generated dynamic questions."""

    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response."""
        content = """
```json
{
  "follow_up_questions": [
    {
      "question": "추가 질문입니다.",
      "category": "risk_factors",
      "rationale": "리스크 확인 필요"
    }
  ]
}
```
        """
        questions = _parse_dynamic_questions(content)

        assert len(questions) == 1
        assert questions[0]["question_text"] == "추가 질문입니다."
        assert questions[0]["category"] == "risk_factors"

    def test_parse_multiple_questions(self):
        """Test parsing multiple dynamic questions."""
        content = """
```json
{
  "follow_up_questions": [
    {"question": "질문 1", "category": "risk_factors", "rationale": "이유 1"},
    {"question": "질문 2", "category": "business_operations", "rationale": "이유 2"}
  ]
}
```
        """
        questions = _parse_dynamic_questions(content)

        assert len(questions) == 2

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns empty list."""
        content = "This is not valid JSON"
        questions = _parse_dynamic_questions(content)

        assert questions == []

    def test_parse_empty_questions_list(self):
        """Test parsing empty questions list."""
        content = """
```json
{
  "follow_up_questions": []
}
```
        """
        questions = _parse_dynamic_questions(content)

        assert questions == []

    def test_parsed_questions_have_id(self):
        """Test parsed questions have generated IDs."""
        content = """
```json
{
  "follow_up_questions": [
    {"question": "Test", "category": "risk_factors", "rationale": "Test"}
  ]
}
```
        """
        questions = _parse_dynamic_questions(content)

        assert questions[0]["id"].startswith("DYN-")


# ============================================================================
# TEST: SPECIFICATION PARSING
# ============================================================================

class TestSpecificationParsing:
    """Tests for parsing specification documents."""

    def test_parse_valid_specification(self):
        """Test parsing valid specification JSON."""
        content = """
```json
{
  "executive_summary": "테스트 요약",
  "risk_assessment": {
    "high_risk_areas": ["수익인식"],
    "medium_risk_areas": [],
    "low_risk_areas": []
  },
  "key_audit_areas": [],
  "special_procedures": [],
  "resource_requirements": {},
  "timeline_notes": ""
}
```
        """
        spec = _parse_specification(content)

        assert spec["executive_summary"] == "테스트 요약"
        assert "수익인식" in spec["risk_assessment"]["high_risk_areas"]

    def test_parse_invalid_json_returns_basic_structure(self):
        """Test parsing invalid JSON returns basic structure."""
        content = "This is not valid JSON but contains info"
        spec = _parse_specification(content)

        assert "executive_summary" in spec
        assert "_parse_error" in spec

    def test_parse_plain_json(self):
        """Test parsing plain JSON without markdown."""
        content = '{"executive_summary": "Plain JSON test", "risk_assessment": {"high_risk_areas": [], "medium_risk_areas": [], "low_risk_areas": []}, "key_audit_areas": [], "special_procedures": [], "resource_requirements": {}, "timeline_notes": ""}'
        spec = _parse_specification(content)

        assert spec["executive_summary"] == "Plain JSON test"


# ============================================================================
# TEST: FALLBACK SPECIFICATION
# ============================================================================

class TestFallbackSpecification:
    """Tests for fallback specification generation."""

    def test_fallback_specification_basic(self, base_audit_state, sample_responses):
        """Test basic fallback specification generation."""
        spec = _create_fallback_specification(base_audit_state, sample_responses)

        assert "executive_summary" in spec
        assert "risk_assessment" in spec
        assert "key_audit_areas" in spec
        assert spec["_fallback"] is True

    def test_fallback_includes_client_info(self, base_audit_state, sample_responses):
        """Test fallback includes client information."""
        spec = _create_fallback_specification(base_audit_state, sample_responses)

        assert base_audit_state["client_name"] in spec["executive_summary"]

    def test_fallback_detects_high_risk_keywords(self, base_audit_state):
        """Test fallback detects high risk keywords in responses."""
        responses = [
            {"question_id": "Q001", "response_text": "위험한 영역입니다."}
        ]
        spec = _create_fallback_specification(base_audit_state, responses)

        # Should have some high risk areas identified
        assert len(spec["risk_assessment"]["high_risk_areas"]) > 0

    def test_fallback_with_empty_responses(self, base_audit_state):
        """Test fallback with empty responses."""
        spec = _create_fallback_specification(base_audit_state, [])

        assert spec is not None
        assert "executive_summary" in spec


# ============================================================================
# TEST: INTERVIEW PROGRESS
# ============================================================================

class TestInterviewProgress:
    """Tests for interview progress tracking."""

    def test_progress_empty_state(self, base_audit_state):
        """Test progress with no responses."""
        progress = get_interview_progress(base_audit_state)

        assert progress["current_phase"] == 1
        assert progress["questions_answered"] == 0
        assert progress["is_complete"] is False

    def test_progress_partial_responses(self, state_with_partial_responses):
        """Test progress with partial responses."""
        progress = get_interview_progress(state_with_partial_responses)

        assert progress["questions_answered"] == 3
        assert progress["completion_percentage"] >= 0

    def test_progress_complete(self, state_interview_complete):
        """Test progress when interview is complete."""
        progress = get_interview_progress(state_interview_complete)

        assert progress["is_complete"] is True


# ============================================================================
# TEST: RESPONSE VALIDATION
# ============================================================================

class TestResponseValidation:
    """Tests for interview response validation."""

    def test_validate_empty_responses(self):
        """Test validation with no responses."""
        result = validate_interview_responses([])

        assert result["is_valid"] is False
        assert len(result["missing_required"]) > 0

    def test_validate_all_required_answered(self, state_with_all_responses):
        """Test validation when all required questions answered."""
        responses = state_with_all_responses["interview_responses"]
        result = validate_interview_responses(responses)

        assert result["is_valid"] is True
        assert len(result["missing_required"]) == 0

    def test_validate_partial_responses(self, sample_responses):
        """Test validation with partial responses."""
        result = validate_interview_responses(sample_responses)

        # Should have missing required questions
        assert result["total_answered"] == 2


# ============================================================================
# TEST: INTERVIEW NODE - ASYNC
# ============================================================================

class TestInterviewNodeAsync:
    """Tests for async interview node functions."""

    @pytest.mark.asyncio
    async def test_interview_node_already_complete(self, state_interview_complete):
        """Test interview_node when interview is already complete."""
        result = await interview_node(state_interview_complete)

        assert result["next_action"] == "ENTER_PLAN_MODE"
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interrupt")
    async def test_interview_node_first_phase(self, mock_interrupt, base_audit_state):
        """Test interview_node starting first phase."""
        mock_interrupt.return_value = {
            "answers": {"Q001": "Answer 1", "Q002": "Answer 2", "Q003": "예, 중요함"}
        }

        result = await interview_node(base_audit_state)

        # interrupt is called at least once for phase questions
        # may be called additional times for dynamic follow-up questions
        # if trigger keywords (like "예, 중요함") are detected
        assert mock_interrupt.call_count >= 1
        assert "interview_responses" in result

    @pytest.mark.asyncio
    async def test_wait_for_completion_no_responses(self, base_audit_state):
        """Test wait_for_interview_completion_node with no responses."""
        result = await wait_for_interview_completion_node(base_audit_state)

        assert result["next_action"] == "CONTINUE"

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interrupt")
    async def test_wait_for_completion_approve(
        self, mock_interrupt, state_with_all_responses
    ):
        """Test wait_for_interview_completion_node with approval."""
        mock_interrupt.return_value = {"action": "approve"}

        result = await wait_for_interview_completion_node(state_with_all_responses)

        assert result["interview_complete"] is True
        assert result["next_action"] == "ENTER_PLAN_MODE"

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interrupt")
    async def test_wait_for_completion_add_more(
        self, mock_interrupt, state_with_all_responses
    ):
        """Test wait_for_interview_completion_node with add more info."""
        mock_interrupt.return_value = {
            "action": "add_more_info",
            "additional_info": "추가 정보입니다."
        }

        result = await wait_for_interview_completion_node(state_with_all_responses)

        assert result["next_action"] == "REGENERATE_SPECIFICATION"
        assert len(result["interview_responses"]) > len(
            state_with_all_responses["interview_responses"]
        )

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interrupt")
    async def test_wait_for_completion_restart(
        self, mock_interrupt, state_with_all_responses
    ):
        """Test wait_for_interview_completion_node with restart."""
        mock_interrupt.return_value = {"action": "restart"}

        result = await wait_for_interview_completion_node(state_with_all_responses)

        assert result["next_action"] == "RESTART_INTERVIEW"
        assert result["interview_responses"] == []
        assert result["interview_complete"] is False


# ============================================================================
# TEST: SPECIFICATION GENERATION
# ============================================================================

class TestSpecificationGeneration:
    """Tests for specification generation."""

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interview_llm")
    async def test_generate_specification_llm_success(
        self, mock_llm, base_audit_state, sample_responses
    ):
        """Test specification generation with successful LLM call."""
        from src.graph.nodes.interview_node import _generate_specification_and_complete

        mock_response = MagicMock()
        mock_response.content = """
```json
{
  "executive_summary": "LLM generated summary",
  "risk_assessment": {"high_risk_areas": [], "medium_risk_areas": [], "low_risk_areas": []},
  "key_audit_areas": [],
  "special_procedures": [],
  "resource_requirements": {},
  "timeline_notes": ""
}
```
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await _generate_specification_and_complete(
            base_audit_state, sample_responses
        )

        assert result["interview_complete"] is True
        assert result["next_action"] == "WAIT_FOR_REVIEW"
        assert "specification" in result

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interview_llm")
    async def test_generate_specification_llm_failure(
        self, mock_llm, base_audit_state, sample_responses
    ):
        """Test specification generation with LLM failure uses fallback."""
        from src.graph.nodes.interview_node import _generate_specification_and_complete

        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))

        result = await _generate_specification_and_complete(
            base_audit_state, sample_responses
        )

        assert result["interview_complete"] is True
        assert result["specification"]["_fallback"] is True


# ============================================================================
# TEST: DYNAMIC QUESTION GENERATION
# ============================================================================

class TestDynamicQuestionGeneration:
    """Tests for dynamic question generation."""

    @pytest.mark.asyncio
    async def test_no_dynamic_questions_without_trigger(self, base_audit_state):
        """Test no dynamic questions generated without triggers."""
        from src.graph.nodes.interview_node import _generate_dynamic_questions

        responses = [{"response_text": "일반적인 응답"}]

        questions = await _generate_dynamic_questions(base_audit_state, responses)

        # Should return empty when no triggers
        assert questions == []

    @pytest.mark.asyncio
    @patch("src.graph.nodes.interview_node.interview_llm")
    async def test_dynamic_questions_with_trigger(
        self, mock_llm, base_audit_state
    ):
        """Test dynamic questions generated with triggers."""
        from src.graph.nodes.interview_node import _generate_dynamic_questions

        mock_response = MagicMock()
        mock_response.content = """
```json
{
  "follow_up_questions": [
    {"question": "Follow up question", "category": "risk_factors", "rationale": "Test"}
  ]
}
```
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        responses = [{"response_text": "위험한 상황입니다."}]

        questions = await _generate_dynamic_questions(base_audit_state, responses)

        assert len(questions) > 0

    @pytest.mark.asyncio
    async def test_dynamic_questions_empty_responses(self, base_audit_state):
        """Test dynamic questions with empty responses."""
        from src.graph.nodes.interview_node import _generate_dynamic_questions

        questions = await _generate_dynamic_questions(base_audit_state, [])

        assert questions == []


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_determine_phase_missing_response_text(self):
        """Test phase determination with malformed responses."""
        responses = [{"question_id": "Q001"}]  # Missing response_text
        phase = _determine_current_phase(responses)
        assert phase >= 1

    def test_validate_responses_malformed_response(self):
        """Test validation with malformed response."""
        responses = [{"question_id": "Q001"}]  # Missing response_text
        result = validate_interview_responses(responses)
        assert isinstance(result, dict)

    def test_get_progress_missing_fields(self):
        """Test progress with minimal state."""
        state = {"messages": []}
        progress = get_interview_progress(state)
        assert progress["current_phase"] == 1

    def test_process_responses_missing_answers_key(self, sample_interview_questions):
        """Test response processing with missing answers key."""
        result = {}  # No 'answers' key
        responses = _process_interview_responses(result, sample_interview_questions)
        assert responses == []

    @pytest.mark.asyncio
    async def test_interview_node_missing_state_fields(self):
        """Test interview_node with minimal state."""
        minimal_state = {
            "messages": [],
            "project_id": "",
            "client_name": "",
            "fiscal_year": 0,
            "overall_materiality": 0.0,
            "audit_plan": {},
            "tasks": [],
            "next_action": "",
            "is_approved": False,
            "shared_documents": [],
        }

        # Should handle missing interview fields gracefully
        # This test verifies no exception is raised
        try:
            # Set interview_complete to skip the interrupt
            minimal_state["interview_complete"] = True
            result = await interview_node(minimal_state)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")
