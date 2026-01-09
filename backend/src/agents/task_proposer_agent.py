"""
Task Proposer Agent

Generates audit task proposals based on EGA descriptions and PWC Audit Guide.
Uses RAG for procedure suggestions and creates HITL requests for approval.

Reference:
- Specification: Section 4.3 (Agent Personas and Prompts)
- EGA Processing: backend/src/graph/nodes/ega_parser.py
- HITL Integration: backend/src/api/routes/hitl.py
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskPhase(str, Enum):
    """Audit task phases aligned with K-GAAS methodology."""
    PLANNING = "planning"
    RISK_ASSESSMENT = "risk-assessment"
    CONTROLS_TESTING = "controls-testing"
    SUBSTANTIVE_PROCEDURES = "substantive-procedures"
    COMPLETION = "completion"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ProposedTask:
    """
    A proposed audit task generated from EGA analysis.

    Attributes:
        id: Unique identifier for the task
        title: Task name/title
        description: Detailed description of the task
        phase: Audit phase this task belongs to
        priority: Task priority level
        estimated_hours: Estimated time to complete
        required_skills: Skills needed for this task
        related_assertions: Financial statement assertions (existence, completeness, etc.)
        source_procedures: IDs of source audit procedures from RAG
        suggested_approach: Recommended approach for completing the task
        risk_considerations: Risk factors to consider
        ega_id: Source EGA ID
        ega_name: Source EGA name/description
        confidence_score: Confidence in this proposal (0-1)
    """
    id: str
    title: str
    description: str
    phase: TaskPhase
    priority: TaskPriority
    estimated_hours: float
    required_skills: List[str]
    related_assertions: List[str]
    source_procedures: List[str]
    suggested_approach: str
    risk_considerations: List[str]
    ega_id: str
    ega_name: str
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "phase": self.phase.value if isinstance(self.phase, TaskPhase) else self.phase,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "estimated_hours": self.estimated_hours,
            "required_skills": self.required_skills,
            "related_assertions": self.related_assertions,
            "source_procedures": self.source_procedures,
            "suggested_approach": self.suggested_approach,
            "risk_considerations": self.risk_considerations,
            "ega_id": self.ega_id,
            "ega_name": self.ega_name,
            "confidence_score": self.confidence_score,
        }


@dataclass
class TaskProposalSet:
    """
    Set of proposed tasks for an EGA.

    Attributes:
        ega_id: Source EGA ID
        ega_name: Source EGA name
        hierarchy_context: Business process and FSLI context
        proposed_tasks: List of proposed tasks
        rag_sources: PWC Guide references used
        generated_at: Timestamp of generation
        requires_hitl_approval: Whether HITL approval is needed
    """
    ega_id: str
    ega_name: str
    hierarchy_context: Dict[str, str]
    proposed_tasks: List[ProposedTask]
    rag_sources: List[Dict[str, Any]]
    generated_at: str
    requires_hitl_approval: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ega_id": self.ega_id,
            "ega_name": self.ega_name,
            "hierarchy_context": self.hierarchy_context,
            "proposed_tasks": [t.to_dict() for t in self.proposed_tasks],
            "rag_sources": self.rag_sources,
            "generated_at": self.generated_at,
            "requires_hitl_approval": self.requires_hitl_approval,
        }


@dataclass
class HITLApprovalRequest:
    """
    HITL request for task proposal approval.

    Attributes:
        id: Unique request ID
        request_type: Type of request (task_proposal)
        ega_id: Source EGA ID
        ega_name: Source EGA name
        proposed_tasks: List of proposed tasks
        rag_sources: PWC Guide references
        context: Additional context information
        created_at: Creation timestamp
        priority: Request priority
        suggested_actions: Available actions for the user
    """
    id: str
    ega_id: str
    ega_name: str
    proposed_tasks: List[ProposedTask]
    rag_sources: List[Dict[str, Any]]
    context: Dict[str, Any]
    created_at: str
    request_type: str = "task_proposal"
    priority: str = "medium"
    suggested_actions: List[str] = field(default_factory=lambda: [
        "approve_all",
        "approve_selected",
        "modify_and_approve",
        "reject_all"
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "request_type": self.request_type,
            "ega_id": self.ega_id,
            "ega_name": self.ega_name,
            "proposed_tasks": [t.to_dict() for t in self.proposed_tasks],
            "rag_sources": self.rag_sources,
            "context": self.context,
            "created_at": self.created_at,
            "priority": self.priority,
            "suggested_actions": self.suggested_actions,
        }


# ============================================================================
# TASK PROPOSER AGENT
# ============================================================================

class TaskProposerAgent:
    """
    Agent that proposes audit tasks based on EGA descriptions.

    Uses PWC Audit Guide RAG for procedure suggestions and creates
    HITL requests for human approval of generated tasks.

    Persona: Experienced audit planning specialist with deep knowledge
    of K-GAAS and audit methodology.

    Mission:
    - Analyze EGA descriptions to identify required audit procedures
    - Use RAG to retrieve relevant procedures from PWC Audit Guide
    - Generate structured task proposals with proper assertions
    - Create HITL requests for human review and approval
    """

    # Default task templates per EGA pattern (Korean audit terminology)
    TASK_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
        "조회": [  # Inquiry/Confirmation procedures
            {
                "title_pattern": "{entity} 조회서 발송대상 완전성 체크",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["completeness"],
                "estimated_hours": 2.0,
            },
            {
                "title_pattern": "{entity} 조회서 발송 및 회신 관리",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["existence"],
                "estimated_hours": 4.0,
            },
            {
                "title_pattern": "{entity} 조회 결과 Recon",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["valuation"],
                "estimated_hours": 3.0,
            },
            {
                "title_pattern": "{entity} 조회 차이 분석 및 후속 절차",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["existence", "valuation"],
                "estimated_hours": 4.0,
            },
        ],
        "실사": [  # Physical inspection procedures
            {
                "title_pattern": "{entity} 실사 계획 수립",
                "phase": TaskPhase.PLANNING,
                "assertions": ["existence"],
                "estimated_hours": 2.0,
            },
            {
                "title_pattern": "{entity} 실사 수행",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["existence", "completeness"],
                "estimated_hours": 8.0,
            },
            {
                "title_pattern": "{entity} 실사 결과 검토",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["existence", "valuation"],
                "estimated_hours": 3.0,
            },
        ],
        "검토": [  # Review/Analysis procedures
            {
                "title_pattern": "{entity} 문서 검토",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["existence", "rights"],
                "estimated_hours": 4.0,
            },
            {
                "title_pattern": "{entity} 분석적 검토",
                "phase": TaskPhase.SUBSTANTIVE_PROCEDURES,
                "assertions": ["valuation", "completeness"],
                "estimated_hours": 3.0,
            },
        ],
        "통제": [  # Controls testing
            {
                "title_pattern": "{entity} 통제 설계 평가",
                "phase": TaskPhase.CONTROLS_TESTING,
                "assertions": ["existence", "completeness"],
                "estimated_hours": 3.0,
            },
            {
                "title_pattern": "{entity} 통제 운영 효과성 테스트",
                "phase": TaskPhase.CONTROLS_TESTING,
                "assertions": ["existence", "valuation"],
                "estimated_hours": 6.0,
            },
        ],
    }

    # Entity extraction patterns (Korean)
    ENTITY_PATTERNS: Dict[str, str] = {
        "금융기관": "금융기관",
        "매출채권": "매출채권",
        "재고": "재고자산",
        "은행": "은행",
        "투자": "투자자산",
        "유형자산": "유형자산",
        "무형자산": "무형자산",
        "부채": "부채",
        "충당": "충당부채",
        "자본": "자본",
    }

    def __init__(
        self,
        rag_client: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        hitl_service: Optional[Any] = None
    ):
        """
        Initialize Task Proposer Agent.

        Args:
            rag_client: AuditGuideRAG instance for procedure lookup
            llm_client: LLM client for enhanced task generation
            hitl_service: Service for creating HITL requests
        """
        self.rag_client = rag_client
        self.llm_client = llm_client
        self.hitl_service = hitl_service
        self.name = "TaskProposer"

        logger.info(
            f"{self.name} initialized "
            f"(RAG: {'enabled' if rag_client else 'disabled'}, "
            f"LLM: {'enabled' if llm_client else 'disabled'}, "
            f"HITL: {'enabled' if hitl_service else 'disabled'})"
        )

    async def propose_tasks(
        self,
        ega_id: str,
        ega_name: str,
        hierarchy_context: Optional[Dict[str, str]] = None,
        auto_create_hitl: bool = True
    ) -> TaskProposalSet:
        """
        Generate task proposals for an EGA.

        This is the main entry point for task proposal generation.

        Args:
            ega_id: ID of the EGA
            ega_name: Name/description of the EGA
            hierarchy_context: Business Process and FSLI context
            auto_create_hitl: Whether to automatically create HITL request

        Returns:
            TaskProposalSet with proposed tasks and metadata
        """
        logger.info(f"[{self.name}] Generating task proposals for EGA: {ega_name}")

        hierarchy_context = hierarchy_context or {}

        # Step 1: Search RAG for relevant procedures
        rag_sources = await self._search_rag_sources(ega_name, hierarchy_context)

        # Step 2: Generate tasks using templates and/or LLM
        proposed_tasks = await self._generate_tasks(
            ega_id=ega_id,
            ega_name=ega_name,
            rag_sources=rag_sources,
            hierarchy_context=hierarchy_context
        )

        # Step 3: Create proposal set
        proposal_set = TaskProposalSet(
            ega_id=ega_id,
            ega_name=ega_name,
            hierarchy_context=hierarchy_context,
            proposed_tasks=proposed_tasks,
            rag_sources=rag_sources,
            generated_at=datetime.utcnow().isoformat(),
            requires_hitl_approval=True
        )

        # Step 4: Create HITL request if enabled
        if auto_create_hitl and self.hitl_service:
            await self._create_hitl_request(proposal_set)

        logger.info(
            f"[{self.name}] Generated {len(proposed_tasks)} task proposals "
            f"for EGA {ega_id} using {len(rag_sources)} RAG sources"
        )

        return proposal_set

    async def _search_rag_sources(
        self,
        ega_name: str,
        hierarchy_context: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Search RAG for relevant audit procedures.

        Args:
            ega_name: EGA name for search query
            hierarchy_context: Context for filtering results

        Returns:
            List of relevant procedure references
        """
        if not self.rag_client:
            logger.info(f"[{self.name}] RAG client not available, skipping search")
            return []

        try:
            procedures = await self.rag_client.search_for_ega(
                ega_name=ega_name,
                context=hierarchy_context
            )

            rag_sources = [
                {
                    "id": getattr(p, 'id', str(uuid.uuid4())[:8]),
                    "section_code": getattr(p, 'section_code', ''),
                    "section_title": getattr(p, 'section_title', ''),
                    "procedure_text": getattr(p, 'procedure_text', '')[:500],
                    "relevance_score": getattr(p, 'relevance_score', 0.0),
                    "related_assertions": getattr(p, 'related_assertions', [])
                }
                for p in procedures
            ]

            logger.info(
                f"[{self.name}] RAG search returned {len(rag_sources)} procedures"
            )

            return rag_sources

        except Exception as e:
            logger.warning(f"[{self.name}] RAG search failed: {e}")
            return []

    async def _generate_tasks(
        self,
        ega_id: str,
        ega_name: str,
        rag_sources: List[Dict[str, Any]],
        hierarchy_context: Dict[str, str]
    ) -> List[ProposedTask]:
        """
        Generate proposed tasks from EGA and RAG results.

        Args:
            ega_id: EGA identifier
            ega_name: EGA name/description
            rag_sources: RAG search results
            hierarchy_context: Business context

        Returns:
            List of proposed tasks
        """
        tasks: List[ProposedTask] = []

        # Identify EGA pattern and entity
        pattern = self._identify_ega_pattern(ega_name)
        entity = self._extract_entity(ega_name)

        logger.debug(
            f"[{self.name}] EGA pattern: {pattern}, entity: {entity}"
        )

        # Get templates for this pattern
        templates = self.TASK_TEMPLATES.get(pattern, self.TASK_TEMPLATES.get("검토", []))

        # Generate tasks from templates
        for i, template in enumerate(templates):
            task_id = f"{ega_id[:8]}-{i+1:02d}"
            title = template["title_pattern"].format(entity=entity)

            # Find related RAG sources based on assertions
            task_assertions = template.get("assertions", [])
            related_sources = self._find_related_sources(
                task_assertions, rag_sources
            )

            # Calculate confidence score
            confidence = self._calculate_confidence(
                has_rag_sources=len(related_sources) > 0,
                pattern_match=pattern in self.TASK_TEMPLATES,
                template_count=len(templates)
            )

            task = ProposedTask(
                id=task_id,
                title=title,
                description=self._generate_description(
                    ega_name, title, template
                ),
                phase=template["phase"],
                priority=self._determine_priority(hierarchy_context),
                estimated_hours=template.get("estimated_hours", 4.0),
                required_skills=["audit", "accounting"],
                related_assertions=task_assertions,
                source_procedures=related_sources[:3],
                suggested_approach=self._generate_approach(template, rag_sources),
                risk_considerations=self._identify_risks(ega_name, hierarchy_context),
                ega_id=ega_id,
                ega_name=ega_name,
                confidence_score=confidence
            )
            tasks.append(task)

        # If LLM available, enhance with additional tasks
        if self.llm_client and rag_sources:
            additional_tasks = await self._llm_generate_tasks(
                ega_id=ega_id,
                ega_name=ega_name,
                rag_sources=rag_sources,
                existing_tasks=tasks
            )
            tasks.extend(additional_tasks)

        return tasks

    def _identify_ega_pattern(self, ega_name: str) -> str:
        """
        Identify the pattern type of an EGA based on keywords.

        Args:
            ega_name: EGA name/description

        Returns:
            Pattern key (조회, 실사, 검토, 통제)
        """
        ega_lower = ega_name.lower()

        # Check for pattern keywords
        if "조회" in ega_lower or "확인" in ega_lower:
            return "조회"
        elif "실사" in ega_lower or "관찰" in ega_lower:
            return "실사"
        elif "통제" in ega_lower or "내부통제" in ega_lower:
            return "통제"
        elif "검토" in ega_lower or "분석" in ega_lower:
            return "검토"
        else:
            return "검토"  # Default pattern

    def _extract_entity(self, ega_name: str) -> str:
        """
        Extract the main entity from EGA name.

        Args:
            ega_name: EGA name/description

        Returns:
            Entity name (e.g., 금융기관, 매출채권)
        """
        # Check for known entity patterns
        for keyword, entity in self.ENTITY_PATTERNS.items():
            if keyword in ega_name:
                return entity

        # Fallback: extract first significant noun phrase
        words = ega_name.split()
        if words:
            # Return first non-connector word
            for word in words:
                if len(word) > 1 and word not in ["을", "를", "의", "와", "과", "에", "에서"]:
                    return word

        return "대상"

    def _find_related_sources(
        self,
        assertions: List[str],
        rag_sources: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Find RAG sources related to given assertions.

        Args:
            assertions: List of assertion codes
            rag_sources: Available RAG sources

        Returns:
            List of source IDs
        """
        related = []
        for source in rag_sources:
            source_assertions = source.get("related_assertions", [])
            if any(a in source_assertions for a in assertions):
                related.append(source["id"])
        return related

    def _calculate_confidence(
        self,
        has_rag_sources: bool,
        pattern_match: bool,
        template_count: int
    ) -> float:
        """
        Calculate confidence score for task proposal.

        Args:
            has_rag_sources: Whether RAG sources support this task
            pattern_match: Whether EGA matches a known pattern
            template_count: Number of templates matched

        Returns:
            Confidence score (0-1)
        """
        score = 0.5  # Base score

        if has_rag_sources:
            score += 0.2
        if pattern_match:
            score += 0.2
        if template_count >= 2:
            score += 0.1

        return min(score, 1.0)

    def _generate_description(
        self,
        ega_name: str,
        title: str,
        template: Dict[str, Any]
    ) -> str:
        """
        Generate task description.

        Args:
            ega_name: Source EGA name
            title: Task title
            template: Task template

        Returns:
            Task description
        """
        phase_names = {
            TaskPhase.PLANNING: "감사계획",
            TaskPhase.RISK_ASSESSMENT: "위험평가",
            TaskPhase.CONTROLS_TESTING: "통제테스트",
            TaskPhase.SUBSTANTIVE_PROCEDURES: "실증절차",
            TaskPhase.COMPLETION: "감사완료",
        }

        phase_name = phase_names.get(template["phase"], "감사절차")
        assertions = ", ".join(template.get("assertions", []))

        return (
            f"EGA '{ega_name}'에 대한 {phase_name}: {title}. "
            f"관련 주장(assertions): {assertions}. "
            f"예상 소요시간: {template.get('estimated_hours', 4.0)}시간."
        )

    def _determine_priority(
        self,
        hierarchy_context: Dict[str, str]
    ) -> TaskPriority:
        """
        Determine task priority based on context.

        Args:
            hierarchy_context: Business context

        Returns:
            TaskPriority enum value
        """
        fsli = hierarchy_context.get("fsli", "").upper()

        # High priority for significant FSLIs
        high_priority_fslis = [
            "REVENUE", "AR", "RECEIVABLE", "INVENTORY", "CASH",
            "TRADE", "매출", "매출채권", "재고", "현금"
        ]
        if any(hp.upper() in fsli for hp in high_priority_fslis):
            return TaskPriority.HIGH

        return TaskPriority.MEDIUM

    def _generate_approach(
        self,
        template: Dict[str, Any],
        rag_sources: List[Dict[str, Any]]
    ) -> str:
        """
        Generate suggested approach for task.

        Args:
            template: Task template
            rag_sources: RAG sources for reference

        Returns:
            Approach description
        """
        approaches = []

        # Add phase context
        phase = template.get("phase", TaskPhase.SUBSTANTIVE_PROCEDURES)
        phase_str = phase.value if isinstance(phase, TaskPhase) else phase
        approaches.append(f"감사단계: {phase_str}")

        # Add assertion context
        assertions = template.get("assertions", [])
        if assertions:
            approaches.append(f"검증 주장: {', '.join(assertions)}")

        # Add procedure hints from RAG
        for source in rag_sources[:2]:
            procedure_text = source.get("procedure_text", "")
            if procedure_text:
                approaches.append(
                    f"참고절차: {procedure_text[:200]}..."
                    if len(procedure_text) > 200 else
                    f"참고절차: {procedure_text}"
                )

        return "\n".join(approaches) if approaches else "표준 감사절차에 따라 수행"

    def _identify_risks(
        self,
        ega_name: str,
        hierarchy_context: Dict[str, str]
    ) -> List[str]:
        """
        Identify risk considerations for the EGA.

        Args:
            ega_name: EGA name/description
            hierarchy_context: Business context

        Returns:
            List of risk considerations
        """
        risks = []

        # Pattern-based risks
        if "조회" in ega_name:
            risks.append("조회 회신 지연 위험")
            risks.append("조회 결과와 장부 차이 발생 가능성")
        elif "실사" in ega_name:
            risks.append("실사 일정 조율 필요")
            risks.append("표본추출 적정성 검토 필요")
        elif "통제" in ega_name:
            risks.append("통제 미비점 식별 시 추가 절차 필요")

        # Context-based risks
        fsli = hierarchy_context.get("fsli", "").upper()
        if fsli in ["AR", "RECEIVABLE", "매출채권"]:
            risks.append("매출채권 대손충당금 추정 검토 필요")
        elif fsli in ["INVENTORY", "재고"]:
            risks.append("재고자산 평가 및 진부화 검토 필요")
        elif fsli in ["REVENUE", "매출"]:
            risks.append("수익인식 기준 적용의 적정성 검토 필요")

        return risks if risks else ["표준 감사위험 고려사항 적용"]

    async def _llm_generate_tasks(
        self,
        ega_id: str,
        ega_name: str,
        rag_sources: List[Dict[str, Any]],
        existing_tasks: List[ProposedTask]
    ) -> List[ProposedTask]:
        """
        Use LLM to generate additional task suggestions.

        Args:
            ega_id: EGA identifier
            ega_name: EGA name/description
            rag_sources: RAG search results
            existing_tasks: Already generated tasks

        Returns:
            List of additional proposed tasks
        """
        if not self.llm_client:
            return []

        try:
            # Build context for LLM
            existing_titles = [t.title for t in existing_tasks]
            source_texts = [
                s.get("procedure_text", "")[:200]
                for s in rag_sources[:3]
            ]

            # Note: In production, this would call the LLM
            # For now, we return empty list as LLM integration is optional
            logger.debug(
                f"[{self.name}] LLM generation skipped "
                f"(would analyze {len(source_texts)} sources)"
            )

            return []

        except Exception as e:
            logger.warning(f"[{self.name}] LLM task generation failed: {e}")
            return []

    async def _create_hitl_request(
        self,
        proposal_set: TaskProposalSet
    ) -> str:
        """
        Create HITL approval request for task proposals.

        Args:
            proposal_set: The task proposal set to approve

        Returns:
            HITL request ID
        """
        if not self.hitl_service:
            logger.warning(f"[{self.name}] HITL service not available")
            return ""

        try:
            request = HITLApprovalRequest(
                id=str(uuid.uuid4()),
                ega_id=proposal_set.ega_id,
                ega_name=proposal_set.ega_name,
                proposed_tasks=proposal_set.proposed_tasks,
                rag_sources=proposal_set.rag_sources,
                context={
                    "hierarchy_context": proposal_set.hierarchy_context,
                    "generated_at": proposal_set.generated_at,
                    "task_count": len(proposal_set.proposed_tasks),
                },
                created_at=datetime.utcnow().isoformat()
            )

            await self.hitl_service.create_request(request)

            logger.info(
                f"[{self.name}] Created HITL request {request.id} "
                f"for {len(request.proposed_tasks)} tasks"
            )

            return request.id

        except Exception as e:
            logger.error(f"[{self.name}] Failed to create HITL request: {e}")
            return ""

    async def handle_hitl_response(
        self,
        request_id: str,
        action: str,
        approved_task_ids: Optional[List[str]] = None,
        modifications: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Handle HITL approval response.

        Args:
            request_id: ID of the HITL request
            action: approve_all, approve_selected, modify_and_approve, reject_all
            approved_task_ids: IDs of approved tasks (for approve_selected)
            modifications: Task modifications (for modify_and_approve)

        Returns:
            List of finalized task definitions
        """
        logger.info(
            f"[{self.name}] Processing HITL response for request {request_id}: {action}"
        )

        if action == "reject_all":
            logger.info(f"[{self.name}] All tasks rejected for request {request_id}")
            return []

        # In production, this would:
        # 1. Retrieve original proposal from storage
        # 2. Apply modifications if any
        # 3. Return finalized tasks for creation

        # Placeholder implementation
        logger.info(
            f"[{self.name}] HITL response processed for request {request_id}"
        )

        return []


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_task_proposer(
    rag_client: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    hitl_service: Optional[Any] = None
) -> TaskProposerAgent:
    """
    Create a TaskProposerAgent instance.

    Factory function for creating TaskProposerAgent with optional dependencies.

    Args:
        rag_client: AuditGuideRAG instance for procedure lookup
        llm_client: LLM client for enhanced task generation
        hitl_service: Service for creating HITL requests

    Returns:
        Configured TaskProposerAgent instance
    """
    return TaskProposerAgent(
        rag_client=rag_client,
        llm_client=llm_client,
        hitl_service=hitl_service
    )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_task_proposer():
        """Test TaskProposerAgent with sample EGA."""

        # Create agent without external dependencies
        proposer = create_task_proposer()

        # Test with sample EGA
        result = await proposer.propose_tasks(
            ega_id="ega-001",
            ega_name="은행 등 금융기관과의 거래와 약정을 조회한다",
            hierarchy_context={
                "business_process": "Revenue-Collection Cycle",
                "fsli": "Trade Receivables"
            },
            auto_create_hitl=False
        )

        print(f"\n=== Task Proposals for EGA: {result.ega_name} ===")
        print(f"Generated at: {result.generated_at}")
        print(f"Total tasks: {len(result.proposed_tasks)}")

        for task in result.proposed_tasks:
            print(f"\n--- Task: {task.title} ---")
            print(f"  Phase: {task.phase.value}")
            print(f"  Priority: {task.priority.value}")
            print(f"  Assertions: {task.related_assertions}")
            print(f"  Estimated hours: {task.estimated_hours}")
            print(f"  Confidence: {task.confidence_score:.2f}")

        print("\n=== Test Complete ===")

    asyncio.run(test_task_proposer())
