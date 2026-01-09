"""
Interview Node Implementation

This module implements the Interview Node for audit strategy interview workflow.
The interview node conducts a structured interview with the user to gather
requirements for the audit engagement before planning begins.

Features:
1. Hybrid questions (checklist + dynamic LLM-generated questions)
2. Deep question generation for requirements extraction
3. Specification document generation
4. Plan mode entry after interview completion

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.3 (Partner Agent Enhancement)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import logging
from datetime import datetime

from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ...graph.state import AuditState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class QuestionCategory(str, Enum):
    """Categories for interview questions."""
    CLIENT_OVERVIEW = "client_overview"
    BUSINESS_OPERATIONS = "business_operations"
    RISK_FACTORS = "risk_factors"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    PRIOR_AUDIT_HISTORY = "prior_audit_history"
    MATERIALITY_ASSESSMENT = "materiality_assessment"
    SPECIAL_CONSIDERATIONS = "special_considerations"


class QuestionType(str, Enum):
    """Types of interview questions."""
    CHECKLIST = "checklist"  # Predefined questions
    DYNAMIC = "dynamic"  # LLM-generated follow-up questions


@dataclass
class InterviewQuestion:
    """Represents a single interview question."""
    id: str
    category: QuestionCategory
    question_type: QuestionType
    question_text: str
    is_required: bool = True
    follow_up_trigger: Optional[str] = None
    options: List[str] = field(default_factory=list)
    help_text: Optional[str] = None


@dataclass
class InterviewResponse:
    """Represents user's response to an interview question."""
    question_id: str
    response_text: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterviewSession:
    """Tracks the state of an interview session."""
    session_id: str
    project_id: str
    current_phase: int
    total_phases: int
    questions_asked: List[InterviewQuestion]
    responses: List[InterviewResponse]
    is_complete: bool = False
    specification: Optional[Dict[str, Any]] = None


# ============================================================================
# CHECKLIST QUESTIONS (Predefined)
# ============================================================================

CHECKLIST_QUESTIONS: List[InterviewQuestion] = [
    # Phase 1: Client Overview
    InterviewQuestion(
        id="Q001",
        category=QuestionCategory.CLIENT_OVERVIEW,
        question_type=QuestionType.CHECKLIST,
        question_text="업종 특성상 중점 감사 영역이 있습니까? (예: 제조업-재고자산, 건설업-공사수익 등)",
        help_text="Industry-specific focus areas for audit",
        is_required=True
    ),
    InterviewQuestion(
        id="Q002",
        category=QuestionCategory.CLIENT_OVERVIEW,
        question_type=QuestionType.CHECKLIST,
        question_text="경영진의 주요 관심사나 우려 사항이 있습니까?",
        help_text="Management's key concerns",
        is_required=True
    ),
    InterviewQuestion(
        id="Q003",
        category=QuestionCategory.CLIENT_OVERVIEW,
        question_type=QuestionType.CHECKLIST,
        question_text="관계회사 또는 특수관계자 거래가 중요한 비중을 차지합니까?",
        options=["예, 중요함", "아니오, 미미함", "해당 없음"],
        is_required=True
    ),

    # Phase 2: Business Operations
    InterviewQuestion(
        id="Q004",
        category=QuestionCategory.BUSINESS_OPERATIONS,
        question_type=QuestionType.CHECKLIST,
        question_text="주요 수익 인식 방식을 설명해 주세요. (일시점 인식, 기간 인식, 진행기준 등)",
        help_text="Revenue recognition method",
        is_required=True,
        follow_up_trigger="기간|진행기준|장기"
    ),
    InterviewQuestion(
        id="Q005",
        category=QuestionCategory.BUSINESS_OPERATIONS,
        question_type=QuestionType.CHECKLIST,
        question_text="재고자산의 주요 평가 방법은 무엇입니까? (선입선출, 가중평균 등)",
        options=["선입선출법 (FIFO)", "가중평균법", "개별법", "해당 없음"],
        is_required=False
    ),
    InterviewQuestion(
        id="Q006",
        category=QuestionCategory.BUSINESS_OPERATIONS,
        question_type=QuestionType.CHECKLIST,
        question_text="유형자산 또는 투자부동산의 공정가치 평가가 필요합니까?",
        options=["예, 필요함", "아니오", "검토 필요"],
        is_required=True
    ),

    # Phase 3: Risk Factors
    InterviewQuestion(
        id="Q007",
        category=QuestionCategory.RISK_FACTORS,
        question_type=QuestionType.CHECKLIST,
        question_text="부정위험 요소로 인식되는 사항이 있습니까? (경영진 압박, 비정상 거래 등)",
        help_text="Fraud risk factors per K-GAAS 240",
        is_required=True
    ),
    InterviewQuestion(
        id="Q008",
        category=QuestionCategory.RISK_FACTORS,
        question_type=QuestionType.CHECKLIST,
        question_text="내부통제 환경에 대한 우려사항이 있습니까?",
        options=["예, 중요한 취약점 있음", "경미한 취약점 있음", "없음"],
        is_required=True
    ),
    InterviewQuestion(
        id="Q009",
        category=QuestionCategory.RISK_FACTORS,
        question_type=QuestionType.CHECKLIST,
        question_text="IT 일반통제(ITGC)에 대한 의존도는 어느 정도입니까?",
        options=["높음 (ERP 등 핵심 시스템 의존)", "보통", "낮음"],
        is_required=True
    ),

    # Phase 4: Prior Audit History
    InterviewQuestion(
        id="Q010",
        category=QuestionCategory.PRIOR_AUDIT_HISTORY,
        question_type=QuestionType.CHECKLIST,
        question_text="전기 감사에서 발견된 주요 이슈가 있습니까?",
        is_required=True
    ),
    InterviewQuestion(
        id="Q011",
        category=QuestionCategory.PRIOR_AUDIT_HISTORY,
        question_type=QuestionType.CHECKLIST,
        question_text="수정 분개 또는 미수정 왜곡표시가 있었습니까?",
        options=["예, 중요한 수정 있음", "경미한 수정 있음", "없음", "초도감사"],
        is_required=True
    ),

    # Phase 5: Special Considerations
    InterviewQuestion(
        id="Q012",
        category=QuestionCategory.SPECIAL_CONSIDERATIONS,
        question_type=QuestionType.CHECKLIST,
        question_text="외부 전문가 활용이 필요한 영역이 있습니까? (가치평가, 연금계리 등)",
        is_required=True
    ),
    InterviewQuestion(
        id="Q013",
        category=QuestionCategory.SPECIAL_CONSIDERATIONS,
        question_type=QuestionType.CHECKLIST,
        question_text="감사 일정상 특별히 고려해야 할 사항이 있습니까? (결산 지연, 보고 기한 등)",
        is_required=False
    ),
]


# ============================================================================
# PROMPTS
# ============================================================================

DYNAMIC_QUESTION_GENERATION_PROMPT = """You are a senior audit partner conducting an interview to understand the client's audit needs.

Based on the client information and previous responses, generate 2-3 deep, insightful follow-up questions.

CLIENT INFORMATION:
- Client Name: {client_name}
- Fiscal Year: {fiscal_year}
- Overall Materiality: ${materiality:,.2f}

PREVIOUS RESPONSES:
{previous_responses}

Generate questions that:
1. Dig deeper into potential risk areas identified in responses
2. Clarify ambiguous or incomplete information
3. Uncover hidden audit risks or complexities
4. Are specific and actionable (not generic)

Output format (JSON):
```json
{{
  "follow_up_questions": [
    {{
      "question": "질문 내용...",
      "category": "risk_factors|business_operations|special_considerations",
      "rationale": "Why this question is important..."
    }}
  ]
}}
```

Generate questions in Korean for better client understanding.
"""

SPECIFICATION_GENERATION_PROMPT = """You are a senior audit partner creating a comprehensive audit specification document.

Based on the interview responses, create a detailed specification for the audit engagement.

CLIENT INFORMATION:
- Client Name: {client_name}
- Fiscal Year: {fiscal_year}
- Overall Materiality: ${materiality:,.2f}

INTERVIEW RESPONSES:
{interview_responses}

Create a specification document that includes:
1. Executive Summary (key audit considerations)
2. Risk Assessment Summary (identified risks and their levels)
3. Key Audit Areas (prioritized list with rationale)
4. Special Procedures Required (based on identified risks)
5. Resource Requirements (expertise needed)
6. Timeline Considerations

Output format (JSON):
```json
{{
  "executive_summary": "Summary of key audit considerations...",
  "risk_assessment": {{
    "high_risk_areas": ["area1", "area2"],
    "medium_risk_areas": ["area3", "area4"],
    "low_risk_areas": ["area5"]
  }},
  "key_audit_areas": [
    {{
      "area": "Revenue Recognition",
      "priority": "high",
      "rationale": "...",
      "suggested_procedures": ["procedure1", "procedure2"]
    }}
  ],
  "special_procedures": [
    {{
      "procedure": "...",
      "trigger": "Why this is needed..."
    }}
  ],
  "resource_requirements": {{
    "specialist_needed": ["valuation", "IT audit"],
    "estimated_hours": 200,
    "team_composition": "Partner, Manager, 2 Staff"
  }},
  "timeline_notes": "Any timeline considerations..."
}}
```

Provide output in Korean where appropriate for client communication.
"""


# ============================================================================
# INTERVIEW NODE IMPLEMENTATION
# ============================================================================

# Initialize LLM for dynamic question generation
interview_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3  # Slightly creative for question generation
)


async def interview_node(state: AuditState) -> Dict[str, Any]:
    """
    Node for conducting audit strategy interview with hybrid questions.

    This node orchestrates the interview workflow:
    1. Presents checklist questions by phase
    2. Generates dynamic follow-up questions based on responses
    3. Collects all responses and generates specification document
    4. Triggers plan mode entry upon completion

    Args:
        state: Current AuditState with client information

    Returns:
        Updated state with:
        - interview_responses: List of collected responses
        - specification: Generated specification document
        - interview_complete: True when interview is finished
        - next_action: "ENTER_PLAN_MODE" on completion

    Example:
        ```python
        initial_state: AuditState = {
            "messages": [],
            "project_id": "proj-123",
            "client_name": "ABC Corp",
            "fiscal_year": 2024,
            "overall_materiality": 1000000.0,
            ...
        }

        result = await interview_node(initial_state)
        print(result["interview_complete"])  # True when done
        print(result["specification"])  # Generated spec document
        ```
    """
    logger.info("[Interview Node] Starting audit strategy interview")

    # Check if interview is already complete
    if state.get("interview_complete", False):
        logger.info("[Interview Node] Interview already complete, skipping")
        return {
            "next_action": "ENTER_PLAN_MODE",
            "messages": [
                HumanMessage(
                    content="[Interview] 인터뷰가 이미 완료되었습니다. 감사계획 수립을 진행합니다.",
                    name="Interview"
                )
            ]
        }

    # Initialize or retrieve interview session
    existing_responses = state.get("interview_responses", [])
    current_phase = _determine_current_phase(existing_responses)

    # Get questions for current phase
    phase_questions = _get_phase_questions(current_phase)

    if not phase_questions:
        # All phases complete - generate specification
        logger.info("[Interview Node] All phases complete, generating specification")
        return await _generate_specification_and_complete(state, existing_responses)

    # Conduct interview for current phase
    logger.info(f"[Interview Node] Phase {current_phase}: {len(phase_questions)} questions")

    # Use interrupt to pause and collect user responses
    interview_result = interrupt({
        "type": "interview_questions",
        "phase": current_phase,
        "total_phases": 5,
        "questions": [
            {
                "id": q.id,
                "category": q.category.value,
                "question_type": q.question_type.value,
                "question_text": q.question_text,
                "options": q.options,
                "help_text": q.help_text,
                "is_required": q.is_required
            }
            for q in phase_questions
        ],
        "message": f"감사전략 인터뷰 - 단계 {current_phase}/5"
    })

    # Process responses
    new_responses = _process_interview_responses(interview_result, phase_questions)

    # Generate dynamic follow-up questions if triggers detected
    dynamic_questions = await _generate_dynamic_questions(
        state, existing_responses + new_responses
    )

    if dynamic_questions:
        # Ask dynamic follow-up questions
        logger.info(f"[Interview Node] Generated {len(dynamic_questions)} follow-up questions")
        dynamic_result = interrupt({
            "type": "interview_questions",
            "phase": f"{current_phase}_followup",
            "total_phases": 5,
            "questions": dynamic_questions,
            "message": "추가 확인 질문"
        })
        dynamic_responses = _process_dynamic_responses(dynamic_result)
        new_responses.extend(dynamic_responses)

    # Update state with new responses
    all_responses = existing_responses + new_responses

    return {
        "interview_responses": all_responses,
        "interview_phase": current_phase + 1,
        "messages": [
            HumanMessage(
                content=f"[Interview] 단계 {current_phase}/5 완료. {len(new_responses)}개 응답 수집.",
                name="Interview"
            )
        ]
    }


async def wait_for_interview_completion_node(state: AuditState) -> Dict[str, Any]:
    """
    HITL checkpoint node for interview completion review.

    This node pauses workflow execution to allow user review of:
    1. All collected interview responses
    2. Generated specification document
    3. Option to add additional information

    Args:
        state: Current AuditState with interview responses

    Returns:
        Updated state with approval status and next action

    Example:
        ```python
        # Frontend flow:
        # 1. Display all interview responses for review
        # 2. Show generated specification preview
        # 3. User confirms or requests revision
        # 4. Call update_state() to resume workflow
        ```
    """
    logger.info("[Interview Node] Waiting for interview completion review")

    interview_responses = state.get("interview_responses", [])
    specification = state.get("specification", {})

    if not interview_responses:
        logger.warning("[Interview Node] No interview responses found")
        return {
            "next_action": "CONTINUE",
            "messages": [
                HumanMessage(
                    content="[Interview] 인터뷰 응답이 없습니다. 인터뷰를 먼저 진행해주세요.",
                    name="Interview"
                )
            ]
        }

    # Pause for user review
    review_result = interrupt({
        "type": "interview_review",
        "message": "인터뷰 결과를 검토하고 승인해주세요.",
        "responses_count": len(interview_responses),
        "specification_preview": specification.get("executive_summary", ""),
        "actions": ["approve", "add_more_info", "restart"]
    })

    action = review_result.get("action", "approve")

    if action == "approve":
        logger.info("[Interview Node] Interview approved, proceeding to plan mode")
        return {
            "interview_complete": True,
            "next_action": "ENTER_PLAN_MODE",
            "messages": [
                HumanMessage(
                    content="[Interview] 인터뷰가 승인되었습니다. 감사계획 수립 단계로 진입합니다.",
                    name="Interview"
                )
            ]
        }
    elif action == "add_more_info":
        logger.info("[Interview Node] User wants to add more information")
        additional_info = review_result.get("additional_info", "")
        additional_response = InterviewResponse(
            question_id="ADDITIONAL",
            response_text=additional_info,
            metadata={"type": "user_addition"}
        )
        return {
            "interview_responses": interview_responses + [additional_response.__dict__],
            "next_action": "REGENERATE_SPECIFICATION",
            "messages": [
                HumanMessage(
                    content="[Interview] 추가 정보가 반영되었습니다. 스펙 문서를 재생성합니다.",
                    name="Interview"
                )
            ]
        }
    else:  # restart
        logger.info("[Interview Node] User requested interview restart")
        return {
            "interview_responses": [],
            "interview_phase": 1,
            "interview_complete": False,
            "specification": {},
            "next_action": "RESTART_INTERVIEW",
            "messages": [
                HumanMessage(
                    content="[Interview] 인터뷰를 처음부터 다시 시작합니다.",
                    name="Interview"
                )
            ]
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _determine_current_phase(responses: List[Dict[str, Any]]) -> int:
    """
    Determine current interview phase based on collected responses.

    Args:
        responses: List of collected interview responses

    Returns:
        Current phase number (1-5, or 6 if all complete)
    """
    if not responses:
        return 1

    answered_ids = {r.get("question_id") for r in responses}

    # Check which phases are complete
    phase_complete = {1: True, 2: True, 3: True, 4: True, 5: True}

    for q in CHECKLIST_QUESTIONS:
        if q.is_required and q.id not in answered_ids:
            phase_num = _get_question_phase(q.category)
            phase_complete[phase_num] = False

    # Return first incomplete phase
    for phase in range(1, 6):
        if not phase_complete[phase]:
            return phase

    return 6  # All phases complete


def _get_question_phase(category: QuestionCategory) -> int:
    """Map question category to phase number."""
    phase_mapping = {
        QuestionCategory.CLIENT_OVERVIEW: 1,
        QuestionCategory.BUSINESS_OPERATIONS: 2,
        QuestionCategory.RISK_FACTORS: 3,
        QuestionCategory.PRIOR_AUDIT_HISTORY: 4,
        QuestionCategory.MATERIALITY_ASSESSMENT: 4,
        QuestionCategory.REGULATORY_COMPLIANCE: 4,
        QuestionCategory.SPECIAL_CONSIDERATIONS: 5,
    }
    return phase_mapping.get(category, 5)


def _get_phase_questions(phase: int) -> List[InterviewQuestion]:
    """
    Get questions for a specific interview phase.

    Args:
        phase: Phase number (1-5)

    Returns:
        List of questions for the phase
    """
    phase_categories = {
        1: [QuestionCategory.CLIENT_OVERVIEW],
        2: [QuestionCategory.BUSINESS_OPERATIONS],
        3: [QuestionCategory.RISK_FACTORS],
        4: [QuestionCategory.PRIOR_AUDIT_HISTORY, QuestionCategory.REGULATORY_COMPLIANCE],
        5: [QuestionCategory.SPECIAL_CONSIDERATIONS, QuestionCategory.MATERIALITY_ASSESSMENT],
    }

    categories = phase_categories.get(phase, [])
    return [q for q in CHECKLIST_QUESTIONS if q.category in categories]


def _process_interview_responses(
    result: Dict[str, Any],
    questions: List[InterviewQuestion]
) -> List[Dict[str, Any]]:
    """
    Process user responses from interview interrupt.

    Args:
        result: Raw result from interrupt()
        questions: Questions that were asked

    Returns:
        List of processed response dictionaries
    """
    responses = []
    answers = result.get("answers", {})

    for q in questions:
        if q.id in answers:
            response = InterviewResponse(
                question_id=q.id,
                response_text=answers[q.id],
                metadata={
                    "category": q.category.value,
                    "question_type": q.question_type.value
                }
            )
            responses.append(response.__dict__)

    return responses


def _process_dynamic_responses(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process responses to dynamic follow-up questions.

    Args:
        result: Raw result from interrupt()

    Returns:
        List of processed response dictionaries
    """
    responses = []
    answers = result.get("answers", {})

    for q_id, answer in answers.items():
        response = InterviewResponse(
            question_id=q_id,
            response_text=answer,
            metadata={"question_type": QuestionType.DYNAMIC.value}
        )
        responses.append(response.__dict__)

    return responses


async def _generate_dynamic_questions(
    state: AuditState,
    responses: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate dynamic follow-up questions based on responses.

    Uses LLM to analyze responses and generate insightful follow-ups.

    Args:
        state: Current AuditState
        responses: Collected interview responses

    Returns:
        List of dynamic question dictionaries
    """
    if not responses:
        return []

    # Check if any triggers are activated
    triggers_activated = _check_response_triggers(responses)

    if not triggers_activated:
        return []

    # Format previous responses for LLM
    responses_text = "\n".join([
        f"Q: {r.get('question_id')} - A: {r.get('response_text', '')}"
        for r in responses[-5:]  # Last 5 responses for context
    ])

    prompt = DYNAMIC_QUESTION_GENERATION_PROMPT.format(
        client_name=state.get("client_name", "Unknown"),
        fiscal_year=state.get("fiscal_year", "Unknown"),
        materiality=state.get("overall_materiality", 0),
        previous_responses=responses_text
    )

    try:
        response = await interview_llm.ainvoke([
            SystemMessage(content="You are a senior audit partner."),
            HumanMessage(content=prompt)
        ])

        # Parse LLM response
        questions = _parse_dynamic_questions(response.content)
        return questions

    except Exception as e:
        logger.error(f"[Interview Node] Error generating dynamic questions: {e}")
        return []


def _check_response_triggers(responses: List[Dict[str, Any]]) -> bool:
    """
    Check if any response triggers warrant follow-up questions.

    Args:
        responses: Collected interview responses

    Returns:
        True if follow-up questions should be generated
    """
    trigger_keywords = [
        "중요", "높음", "위험", "우려", "복잡",
        "예, 필요", "취약점", "중요한 수정",
        "기간", "진행기준", "장기"
    ]

    for response in responses:
        response_text = response.get("response_text", "").lower()
        for keyword in trigger_keywords:
            if keyword.lower() in response_text:
                return True

    return False


def _parse_dynamic_questions(content: str) -> List[Dict[str, Any]]:
    """
    Parse LLM-generated dynamic questions from response.

    Args:
        content: Raw LLM response content

    Returns:
        List of question dictionaries
    """
    # Try to extract JSON
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)

    if json_match:
        try:
            data = json.loads(json_match.group(1))
            questions = data.get("follow_up_questions", [])

            return [
                {
                    "id": f"DYN-{i+1:03d}",
                    "category": q.get("category", "special_considerations"),
                    "question_type": "dynamic",
                    "question_text": q.get("question", ""),
                    "options": [],
                    "is_required": False,
                    "help_text": q.get("rationale", "")
                }
                for i, q in enumerate(questions)
            ]
        except json.JSONDecodeError:
            pass

    return []


async def _generate_specification_and_complete(
    state: AuditState,
    responses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate specification document and mark interview complete.

    Args:
        state: Current AuditState
        responses: All collected interview responses

    Returns:
        Updated state with specification and completion status
    """
    logger.info("[Interview Node] Generating specification document")

    # Format responses for LLM
    responses_text = "\n".join([
        f"- {r.get('question_id')}: {r.get('response_text', '')}"
        for r in responses
    ])

    prompt = SPECIFICATION_GENERATION_PROMPT.format(
        client_name=state.get("client_name", "Unknown"),
        fiscal_year=state.get("fiscal_year", "Unknown"),
        materiality=state.get("overall_materiality", 0),
        interview_responses=responses_text
    )

    try:
        response = await interview_llm.ainvoke([
            SystemMessage(content="You are a senior audit partner creating audit specifications."),
            HumanMessage(content=prompt)
        ])

        specification = _parse_specification(response.content)

    except Exception as e:
        logger.error(f"[Interview Node] Error generating specification: {e}")
        specification = _create_fallback_specification(state, responses)

    return {
        "specification": specification,
        "interview_responses": responses,
        "interview_complete": True,
        "next_action": "WAIT_FOR_REVIEW",
        "messages": [
            HumanMessage(
                content=f"[Interview] 인터뷰 완료. "
                        f"총 {len(responses)}개 응답 수집. "
                        f"감사 스펙 문서가 생성되었습니다.",
                name="Interview"
            )
        ]
    }


def _parse_specification(content: str) -> Dict[str, Any]:
    """
    Parse specification document from LLM response.

    Args:
        content: Raw LLM response content

    Returns:
        Parsed specification dictionary
    """
    # Try to extract JSON
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try plain JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Return basic structure
    return {
        "executive_summary": content[:500] if content else "Specification generation failed.",
        "risk_assessment": {
            "high_risk_areas": [],
            "medium_risk_areas": [],
            "low_risk_areas": []
        },
        "key_audit_areas": [],
        "special_procedures": [],
        "resource_requirements": {},
        "timeline_notes": "",
        "_parse_error": True
    }


def _create_fallback_specification(
    state: AuditState,
    responses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create fallback specification when LLM generation fails.

    Args:
        state: Current AuditState
        responses: Collected interview responses

    Returns:
        Basic specification dictionary
    """
    # Extract some key information from responses
    high_risk_indicators = []
    for r in responses:
        text = r.get("response_text", "").lower()
        if any(kw in text for kw in ["높음", "중요", "위험", "우려"]):
            high_risk_indicators.append(r.get("question_id"))

    return {
        "executive_summary": f"감사 대상: {state.get('client_name', 'Unknown')} "
                            f"({state.get('fiscal_year', 'Unknown')}년도). "
                            f"중요성 기준액: ${state.get('overall_materiality', 0):,.2f}",
        "risk_assessment": {
            "high_risk_areas": ["수익인식", "재고자산"] if high_risk_indicators else [],
            "medium_risk_areas": ["매출채권", "유형자산"],
            "low_risk_areas": ["현금및현금성자산"]
        },
        "key_audit_areas": [
            {
                "area": "수익인식",
                "priority": "high",
                "rationale": "K-GAAS 240 부정위험 필수 고려사항",
                "suggested_procedures": ["매출 증빙 대사", "결산일 전후 매출 검토"]
            }
        ],
        "special_procedures": [],
        "resource_requirements": {
            "specialist_needed": [],
            "estimated_hours": 150,
            "team_composition": "Partner, Manager, Staff"
        },
        "timeline_notes": "표준 감사 일정 적용",
        "_fallback": True
    }


# ============================================================================
# UTILITY FUNCTIONS FOR EXTERNAL USE
# ============================================================================

def get_interview_progress(state: AuditState) -> Dict[str, Any]:
    """
    Get current interview progress summary.

    Args:
        state: Current AuditState

    Returns:
        Progress summary dictionary
    """
    responses = state.get("interview_responses", [])
    current_phase = _determine_current_phase(responses)

    total_required = len([q for q in CHECKLIST_QUESTIONS if q.is_required])
    answered_required = len([
        r for r in responses
        if any(q.id == r.get("question_id") and q.is_required for q in CHECKLIST_QUESTIONS)
    ])

    return {
        "current_phase": current_phase,
        "total_phases": 5,
        "questions_answered": len(responses),
        "required_answered": answered_required,
        "required_total": total_required,
        "completion_percentage": round((current_phase - 1) / 5 * 100, 1),
        "is_complete": state.get("interview_complete", False)
    }


def validate_interview_responses(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate interview responses for completeness.

    Args:
        responses: List of interview responses

    Returns:
        Validation result dictionary
    """
    answered_ids = {r.get("question_id") for r in responses}
    missing_required = []

    for q in CHECKLIST_QUESTIONS:
        if q.is_required and q.id not in answered_ids:
            missing_required.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "category": q.category.value
            })

    return {
        "is_valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "total_answered": len(responses),
        "total_required": len([q for q in CHECKLIST_QUESTIONS if q.is_required])
    }
