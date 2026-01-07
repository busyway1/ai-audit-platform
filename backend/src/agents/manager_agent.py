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

from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()


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
