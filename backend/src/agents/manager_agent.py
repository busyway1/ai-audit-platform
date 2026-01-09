"""Manager Agent Implementation

Manager Agent Persona:
- 꼼꼼하고 엄격한 감사 매니저 (Meticulous and strict audit manager)
- 스케줄링과 리뷰 전문가 (Scheduling and review expert)
- Blackboard Router: TaskState를 보며 다음 Staff agent 결정

Mission:
1. Partner의 감사 계획을 바탕으로 세부 감사 절차를 태스크로 분해
2. 각 태스크에 적합한 Staff 에이전트를 배정
3. Staff의 작업 결과를 검토하고 논리적 결함 발견 시:
   - 경미한 경우: Staff에게 재작업 지시
   - 중요한 판단 필요: interrupt()로 유저 개입 요청
4. TaskState(Blackboard)를 보며 다음 단계를 결정하는 Router 역할

Reference: Section 4.3 of AUDIT_PLATFORM_SPECIFICATION.md
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# STAFF ALLOCATION DATA STRUCTURES
# ============================================================================

class StaffType(str, Enum):
    """Staff agent types for allocation."""
    EXCEL_PARSER = "excel_parser"
    STANDARD_RETRIEVER = "standard_retriever"
    VOUCHING_ASSISTANT = "vouching_assistant"
    WORKPAPER_GENERATOR = "workpaper_generator"


class RiskLevel(str, Enum):
    """Risk levels for task allocation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StaffProfile:
    """Profile of an available Staff agent for allocation.

    Attributes:
        staff_id: Unique identifier for the staff instance
        staff_type: Type of staff agent (StaffType enum)
        skills: List of skills this staff agent possesses
        current_workload: Current workload (0-100), affects availability
        expertise_level: Expertise level (1-5), higher is more experienced
    """
    staff_id: str
    staff_type: StaffType
    skills: List[str]
    current_workload: int = 0  # 0-100
    expertise_level: int = 3  # 1-5


@dataclass
class AllocationResult:
    """Result of staff allocation decision.

    Attributes:
        staff_id: ID of assigned staff
        staff_type: Type of staff agent assigned
        priority: Priority of this assignment (1-10, higher = more urgent)
        allocation_score: Score indicating how well this staff fits the task
        reason: Human-readable reason for this allocation
    """
    staff_id: str
    staff_type: StaffType
    priority: int
    allocation_score: float
    reason: str


@dataclass
class TaskRequirements:
    """Requirements extracted from a task for staff allocation.

    Attributes:
        task_id: Task identifier
        category: Audit category (e.g., "Sales", "Inventory")
        risk_level: Risk level of the task
        required_skills: Skills required for this task
        complexity_score: Complexity score (1-10)
        deadline_urgency: Urgency level (1-10)
    """
    task_id: str
    category: str
    risk_level: RiskLevel
    required_skills: List[str]
    complexity_score: int = 5  # 1-10
    deadline_urgency: int = 5  # 1-10


# Skill definitions for each Staff type
STAFF_SKILL_MAPPING: Dict[StaffType, List[str]] = {
    StaffType.EXCEL_PARSER: [
        "data_extraction", "excel_parsing", "financial_analysis",
        "data_validation", "anomaly_detection"
    ],
    StaffType.STANDARD_RETRIEVER: [
        "k_ifrs", "k_gaas", "standard_research", "regulatory_compliance",
        "audit_standards"
    ],
    StaffType.VOUCHING_ASSISTANT: [
        "document_verification", "vouching", "evidence_analysis",
        "cross_referencing", "exception_identification"
    ],
    StaffType.WORKPAPER_GENERATOR: [
        "documentation", "workpaper_drafting", "synthesis",
        "report_writing", "audit_documentation"
    ]
}


# Category to required skills mapping
CATEGORY_SKILL_REQUIREMENTS: Dict[str, List[str]] = {
    "매출": ["data_extraction", "k_ifrs", "vouching", "documentation"],
    "Sales": ["data_extraction", "k_ifrs", "vouching", "documentation"],
    "매입": ["data_extraction", "k_ifrs", "vouching", "documentation"],
    "Purchases": ["data_extraction", "k_ifrs", "vouching", "documentation"],
    "재고": ["data_extraction", "data_validation", "vouching", "documentation"],
    "Inventory": ["data_extraction", "data_validation", "vouching", "documentation"],
    "현금": ["data_extraction", "evidence_analysis", "vouching", "documentation"],
    "Cash": ["data_extraction", "evidence_analysis", "vouching", "documentation"],
    "대손충당금": ["financial_analysis", "k_ifrs", "evidence_analysis", "documentation"],
    "Allowance": ["financial_analysis", "k_ifrs", "evidence_analysis", "documentation"]
}


class ManagerAgent:
    """Manager Agent - Orchestrates Staff agents and reviews their work.

    The Manager acts as a strict audit supervisor who:
    1. Analyzes Partner's audit plan and decomposes into granular tasks
    2. Routes tasks to appropriate Staff agents (Excel_Parser, Standard_Retriever, etc.)
    3. Reviews Staff outputs for logical errors and completeness
    4. Decides when to request human intervention (HITL)

    Usage:
        ```python
        from src.agents.manager_agent import ManagerAgent
        from src.graph.state import TaskState

        manager = ManagerAgent()
        result = manager.run(task_state)
        ```
    """

    def __init__(self, model: str = "gpt-4o"):
        """Initialize Manager Agent with LLM.

        Args:
            model: OpenAI model identifier (default: gpt-4o for reasoning)
        """
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.3,  # Low temperature for consistent scheduling
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.persona_prompt = self._create_persona_prompt()

    def _create_persona_prompt(self) -> ChatPromptTemplate:
        """Create Manager's persona and routing logic prompt.

        Returns:
            ChatPromptTemplate with Manager's persona and decision-making framework
        """
        system_message = """당신은 20년 경력의 대형 회계법인 감사 매니저입니다.

**핵심 특성**:
- 꼼꼼하고 엄격함 (Meticulous and strict)
- 스케줄링과 작업 분배 전문가
- 논리적 결함을 즉시 발견하는 리뷰 능력
- 감사 품질 > 속도 (Quality over speed)

**당신의 역할**:
1. **작업 분해 (Task Decomposition)**:
   - Partner의 감사 계획을 받아 계정과목/프로세스별 세부 태스크로 나눔
   - 각 태스크는 특정 Staff 에이전트에게 할당

2. **Staff 에이전트 배정 (Staff Routing)**:
   - TaskState의 Blackboard를 보고 다음 실행할 Staff 결정
   - 순서: Excel_Parser → Standard_Retriever → Vouching_Assistant → WorkPaper_Generator

3. **품질 검토 (Quality Review)**:
   - Staff의 작업 결과를 검토
   - 데이터 무결성, 기준서 적용 정확성, 증빙 대조 완결성 확인
   - 논리적 결함 발견 시:
     * 경미한 오류: Staff에게 재작업 지시
     * 중요한 판단 필요: interrupt()로 유저(감사인) 개입 요청

4. **진행 상황 모니터링**:
   - TaskState의 status 업데이트 ("Pending" → "In-Progress" → "Review-Required" → "Completed")
   - risk_score 평가 (0-100, 높을수록 위험)

**현재 TaskState 필드 설명**:
- raw_data: Excel_Parser가 추출한 재무 데이터
- standards: Standard_Retriever가 검색한 K-IFRS/K-GAAS 기준서
- vouching_logs: Vouching_Assistant가 대조 완료한 증빙 목록
- workpaper_draft: WorkPaper_Generator가 생성한 감사조서 초안

**중요 원칙**:
1. 모든 Staff가 작업을 완료하기 전까지는 "Completed" 상태로 전환하지 않음
2. 데이터가 불충분하면 즉시 "Review-Required" 상태로 변경하고 필요 정보 명시
3. 감사 리스크가 높은 영역(매출 인식, 대손충당금 등)은 risk_score를 80 이상으로 설정
4. 논리적 판단이 애매하면 사람(감사인)에게 질문 (interrupt)

당신의 응답은 항상:
- 명확한 다음 액션 지시 (next_staff: "Excel_Parser" 등)
- 현재 상태 평가 (status: "In-Progress" 등)
- 리스크 점수 판단 (risk_score: 0-100)
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
            ("human", """현재 TaskState:
task_id: {task_id}
category: {category}
status: {status}

Blackboard (Staff 작업 공간):
- raw_data: {raw_data_summary}
- standards: {standards_summary}
- vouching_logs: {vouching_summary}
- workpaper_draft: {workpaper_summary}

다음 Staff를 결정하고 현재 상태를 평가하세요.
응답 형식:
1. next_staff: [Staff 이름 or None]
2. status: [새로운 status]
3. risk_score: [0-100]
4. 판단 근거: [간략한 설명]
""")
        ])

        return prompt

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Manager's routing and review logic.

        Args:
            state: TaskState dict with current task information

        Returns:
            Updated state dict with:
            - next_staff: Next Staff agent to execute (or None if complete)
            - status: Updated task status
            - risk_score: AI-assessed risk score (0-100)
            - messages: Updated conversation history

        Example:
            ```python
            task_state = {
                "task_id": "TASK-001",
                "category": "매출",
                "status": "Pending",
                "raw_data": {},
                "standards": [],
                "vouching_logs": [],
                "workpaper_draft": ""
            }

            manager = ManagerAgent()
            result = manager.run(task_state)

            print(result["next_staff"])  # "Excel_Parser"
            print(result["status"])  # "In-Progress"
            print(result["risk_score"])  # 75
            ```
        """

        # Prepare Blackboard summaries for prompt
        raw_data_summary = "비어있음" if not state.get("raw_data") else "데이터 있음 (Excel 파싱 완료)"
        standards_summary = "비어있음" if not state.get("standards") else f"{len(state.get('standards', []))}개 기준서 검색됨"
        vouching_summary = "비어있음" if not state.get("vouching_logs") else f"{len(state.get('vouching_logs', []))}개 증빙 대조됨"
        workpaper_summary = "비어있음" if not state.get("workpaper_draft") else "조서 초안 생성됨"

        # Format prompt with current state
        formatted_prompt = self.persona_prompt.invoke({
            "messages": state.get("messages", []),
            "task_id": state.get("task_id", "UNKNOWN"),
            "category": state.get("category", "UNKNOWN"),
            "status": state.get("status", "Pending"),
            "raw_data_summary": raw_data_summary,
            "standards_summary": standards_summary,
            "vouching_summary": vouching_summary,
            "workpaper_summary": workpaper_summary
        })

        # Get Manager's decision
        response = self.llm.invoke(formatted_prompt)

        # Parse response (in production, use structured output with Pydantic)
        # For now, extract key information from response text
        decision = self._parse_manager_decision(response.content, state)

        # Update messages with Manager's response
        updated_messages = state.get("messages", []) + [
            AIMessage(content=response.content, name="Manager")
        ]

        return {
            **state,
            "next_staff": decision["next_staff"],
            "status": decision["status"],
            "risk_score": decision.get("risk_score", state.get("risk_score", 50)),
            "messages": updated_messages
        }

    def _parse_manager_decision(self, response_text: str, current_state: Dict) -> Dict[str, Any]:
        """Parse Manager's decision from LLM response.

        Args:
            response_text: Manager's response text
            current_state: Current TaskState

        Returns:
            Dict with next_staff, status, risk_score

        Note:
            In production, use structured output with response_model (Pydantic)
            to ensure reliable parsing. This is a simplified implementation.
        """
        # Simple heuristic-based parsing (replace with structured output in production)
        decision = {
            "next_staff": None,
            "status": current_state.get("status", "Pending"),
            "risk_score": current_state.get("risk_score", 50)
        }

        text_lower = response_text.lower()

        # Determine next_staff based on Blackboard state
        if not current_state.get("raw_data"):
            decision["next_staff"] = "excel_parser"
            decision["status"] = "In-Progress"
        elif not current_state.get("standards"):
            decision["next_staff"] = "standard_retriever"
            decision["status"] = "In-Progress"
        elif not current_state.get("vouching_logs"):
            decision["next_staff"] = "vouching_assistant"
            decision["status"] = "In-Progress"
        elif not current_state.get("workpaper_draft"):
            decision["next_staff"] = "workpaper_generator"
            decision["status"] = "In-Progress"
        else:
            # All Staff have completed their work
            decision["next_staff"] = None
            decision["status"] = "Completed"

        # Extract risk_score if mentioned
        # Look for patterns like "risk_score: 80" or "리스크 점수: 80"
        import re
        risk_pattern = r'(?:risk_score|리스크 점수)[:：]\s*(\d+)'
        risk_match = re.search(risk_pattern, response_text)
        if risk_match:
            decision["risk_score"] = int(risk_match.group(1))

        return decision

    def should_interrupt(self, state: Dict[str, Any]) -> bool:
        """Determine if human intervention is required.

        Args:
            state: Current TaskState

        Returns:
            True if HITL (Human-in-the-Loop) is needed

        Interrupt conditions:
            1. Critical data missing after 2+ retry attempts
            2. Risk score >= 90 (high-risk audit area)
            3. Conflicting information between Staff agents
            4. Error report contains "Critical" or "치명적"
        """
        # High risk requires human review
        if state.get("risk_score", 0) >= 90:
            return True

        # Critical errors
        error_report = state.get("error_report", "")
        if "Critical" in error_report or "치명적" in error_report:
            return True

        # All Staff completed but contradictory results
        has_all_data = all([
            state.get("raw_data"),
            state.get("standards"),
            state.get("vouching_logs"),
            state.get("workpaper_draft")
        ])

        if has_all_data and state.get("status") == "Review-Required":
            return True

        return False

    # ========================================================================
    # DYNAMIC STAFF ALLOCATION (BE-11.1)
    # ========================================================================

    def allocate_staff_agents(
        self,
        task: Dict[str, Any],
        available_staff: List[StaffProfile]
    ) -> List[AllocationResult]:
        """Dynamically allocate Staff agents to a task based on multiple factors.

        This method implements intelligent staff allocation considering:
        1. Risk level of the task
        2. Required skills for the task category
        3. Current workload of available staff
        4. Staff expertise and performance

        Args:
            task: Task dictionary containing task_id, category, risk_score, etc.
            available_staff: List of StaffProfile objects representing available staff

        Returns:
            List[AllocationResult]: Ordered list of staff allocations with priorities

        Example:
            ```python
            manager = ManagerAgent()

            task = {
                "task_id": "TASK-001",
                "category": "Sales",
                "risk_score": 75,
                "complexity_score": 7
            }

            available_staff = [
                StaffProfile("staff-1", StaffType.EXCEL_PARSER, [...], 20, 4),
                StaffProfile("staff-2", StaffType.STANDARD_RETRIEVER, [...], 50, 3),
            ]

            allocations = manager.allocate_staff_agents(task, available_staff)
            for alloc in allocations:
                print(f"{alloc.staff_type}: priority={alloc.priority}")
            ```
        """
        if not available_staff:
            return []

        # Extract task requirements
        task_requirements = self._extract_task_requirements(task)

        # Calculate allocation scores for each available staff
        scored_staff: List[tuple[StaffProfile, float, str]] = []

        for staff in available_staff:
            score, reason = self._calculate_allocation_score(
                staff, task_requirements
            )
            scored_staff.append((staff, score, reason))

        # Sort by score (descending) - higher score = better match
        scored_staff.sort(key=lambda x: x[1], reverse=True)

        # Create allocation results with load balancing
        allocations = self._create_balanced_allocations(
            scored_staff, task_requirements
        )

        return allocations

    def _extract_task_requirements(
        self,
        task: Dict[str, Any]
    ) -> TaskRequirements:
        """Extract requirements from a task dictionary.

        Args:
            task: Task dictionary with task details

        Returns:
            TaskRequirements object with extracted information
        """
        category = task.get("category", "Sales")
        risk_score = task.get("risk_score", 50)

        # Determine risk level from score
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Get required skills from category mapping
        required_skills = CATEGORY_SKILL_REQUIREMENTS.get(
            category,
            ["data_extraction", "documentation"]  # Default skills
        )

        # Calculate complexity from various factors
        complexity_score = task.get("complexity_score", 5)
        if complexity_score == 0:
            # Auto-calculate based on risk and category
            complexity_score = min(10, max(1, risk_score // 10))

        # Calculate urgency from deadline or default
        deadline_urgency = task.get("deadline_urgency", 5)
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            deadline_urgency = max(deadline_urgency, 7)

        return TaskRequirements(
            task_id=task.get("task_id", "UNKNOWN"),
            category=category,
            risk_level=risk_level,
            required_skills=required_skills,
            complexity_score=complexity_score,
            deadline_urgency=deadline_urgency
        )

    def _calculate_allocation_score(
        self,
        staff: StaffProfile,
        requirements: TaskRequirements
    ) -> tuple[float, str]:
        """Calculate allocation score for a staff-task pair.

        The score is based on:
        - Skill match (40% weight)
        - Workload availability (35% weight)
        - Expertise level (25% weight)

        Higher risk tasks get bonus for higher expertise.

        Args:
            staff: StaffProfile of the candidate staff
            requirements: TaskRequirements for the task

        Returns:
            Tuple of (score: float, reason: str)
        """
        reasons: List[str] = []

        # 1. Skill Match Score (0-100, 40% weight)
        staff_skills = set(staff.skills)
        required_skills = set(requirements.required_skills)
        staff_type_skills = set(STAFF_SKILL_MAPPING.get(staff.staff_type, []))

        # Combine staff's explicit skills with type-based skills
        all_staff_skills = staff_skills.union(staff_type_skills)

        if required_skills:
            skill_overlap = len(all_staff_skills.intersection(required_skills))
            skill_match_score = (skill_overlap / len(required_skills)) * 100
        else:
            skill_match_score = 50  # Neutral if no specific skills required

        if skill_match_score >= 75:
            reasons.append(f"Strong skill match ({skill_match_score:.0f}%)")
        elif skill_match_score >= 50:
            reasons.append(f"Partial skill match ({skill_match_score:.0f}%)")
        else:
            reasons.append(f"Limited skill match ({skill_match_score:.0f}%)")

        # 2. Workload Availability Score (0-100, 35% weight)
        # Lower workload = higher availability = higher score
        availability_score = 100 - staff.current_workload

        if availability_score >= 80:
            reasons.append("High availability")
        elif availability_score >= 50:
            reasons.append("Moderate availability")
        else:
            reasons.append("Limited availability")

        # 3. Expertise Score (0-100, 25% weight)
        # expertise_level is 1-5, normalize to 0-100
        expertise_score = (staff.expertise_level / 5) * 100

        # Bonus for high expertise on high-risk tasks
        if requirements.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            if staff.expertise_level >= 4:
                expertise_score = min(100, expertise_score * 1.2)
                reasons.append("Expert for high-risk task")

        # 4. Calculate weighted total score
        total_score = (
            skill_match_score * 0.40 +
            availability_score * 0.35 +
            expertise_score * 0.25
        )

        # Apply complexity adjustment
        if requirements.complexity_score >= 7:
            # Complex tasks benefit from higher expertise
            if staff.expertise_level >= 4:
                total_score *= 1.1
                reasons.append("Suited for complex work")
            elif staff.expertise_level <= 2:
                total_score *= 0.9

        reason_text = "; ".join(reasons) if reasons else "Standard allocation"

        return total_score, reason_text

    def _create_balanced_allocations(
        self,
        scored_staff: List[tuple[StaffProfile, float, str]],
        requirements: TaskRequirements
    ) -> List[AllocationResult]:
        """Create load-balanced allocation results from scored staff.

        Ensures that:
        - Staff with high workload are deprioritized
        - Each staff type needed is included
        - Priorities reflect urgency and risk

        Args:
            scored_staff: List of (StaffProfile, score, reason) tuples, sorted by score
            requirements: TaskRequirements for the task

        Returns:
            List[AllocationResult] with balanced allocations
        """
        allocations: List[AllocationResult] = []

        # Determine base priority from risk level and urgency
        base_priority = self._calculate_base_priority(requirements)

        # Track which staff types have been allocated
        allocated_types: set[StaffType] = set()

        for staff, score, reason in scored_staff:
            # Skip if this staff type already allocated (load balancing)
            # Unless score is significantly higher (>20 points difference)
            if staff.staff_type in allocated_types:
                existing_alloc = next(
                    (a for a in allocations if a.staff_type == staff.staff_type),
                    None
                )
                if existing_alloc and (existing_alloc.allocation_score - score) < 20:
                    continue

            # Calculate priority for this allocation
            priority = self._adjust_priority_for_workload(
                base_priority, staff.current_workload
            )

            allocation = AllocationResult(
                staff_id=staff.staff_id,
                staff_type=staff.staff_type,
                priority=priority,
                allocation_score=round(score, 2),
                reason=reason
            )

            allocations.append(allocation)
            allocated_types.add(staff.staff_type)

        # Sort allocations by priority (higher = more urgent)
        allocations.sort(key=lambda x: x.priority, reverse=True)

        return allocations

    def _calculate_base_priority(self, requirements: TaskRequirements) -> int:
        """Calculate base priority from task requirements.

        Args:
            requirements: TaskRequirements object

        Returns:
            Base priority (1-10)
        """
        priority = 5  # Default

        # Adjust for risk level
        risk_adjustments = {
            RiskLevel.CRITICAL: 3,
            RiskLevel.HIGH: 2,
            RiskLevel.MEDIUM: 0,
            RiskLevel.LOW: -1
        }
        priority += risk_adjustments.get(requirements.risk_level, 0)

        # Adjust for deadline urgency
        if requirements.deadline_urgency >= 8:
            priority += 2
        elif requirements.deadline_urgency >= 6:
            priority += 1

        # Clamp to valid range
        return max(1, min(10, priority))

    def _adjust_priority_for_workload(
        self,
        base_priority: int,
        current_workload: int
    ) -> int:
        """Adjust priority based on staff workload for load balancing.

        Staff with high workload get lower priority to spread work.

        Args:
            base_priority: Starting priority value
            current_workload: Staff's current workload (0-100)

        Returns:
            Adjusted priority (1-10)
        """
        # Reduce priority for overloaded staff
        if current_workload >= 80:
            return max(1, base_priority - 2)
        elif current_workload >= 60:
            return max(1, base_priority - 1)

        return base_priority

    def get_required_staff_types(
        self,
        task: Dict[str, Any]
    ) -> List[StaffType]:
        """Determine which Staff types are needed for a task.

        Based on the current state of the task's Blackboard,
        returns the Staff types that still need to run.

        Args:
            task: Task dictionary with current state

        Returns:
            List[StaffType] in execution order
        """
        required_types: List[StaffType] = []

        # Check each stage of the audit workflow
        if not task.get("raw_data"):
            required_types.append(StaffType.EXCEL_PARSER)

        if not task.get("standards"):
            required_types.append(StaffType.STANDARD_RETRIEVER)

        if not task.get("vouching_logs"):
            required_types.append(StaffType.VOUCHING_ASSISTANT)

        if not task.get("workpaper_draft"):
            required_types.append(StaffType.WORKPAPER_GENERATOR)

        return required_types


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
Usage in Manager Subgraph:

```python
from src.agents.manager_agent import ManagerAgent
from src.graph.state import TaskState

manager = ManagerAgent()

def manager_node(state: TaskState) -> TaskState:
    '''Manager node in LangGraph subgraph'''

    # Manager evaluates current state and decides next action
    result = manager.run(state)

    # Check if human intervention needed
    if manager.should_interrupt(result):
        # In LangGraph, use interrupt() to pause execution
        from langgraph.types import interrupt
        interrupt(f"Human review required: {result.get('error_report', 'High-risk area')}")

    return result

# In subgraph definition:
from langgraph.graph import StateGraph

subgraph = StateGraph(TaskState)
subgraph.add_node("manager", manager_node)
```

Integration Notes:
1. Manager runs AFTER each Staff completes their work
2. Manager's decision (next_staff) determines the next node in subgraph
3. Manager can trigger interrupt() for HITL
4. Manager updates risk_score which is synced to Supabase audit_tasks table
"""
