"""
Tests for Task Proposer Agent

This module tests the TaskProposerAgent functionality including:
- Task proposal generation from EGA descriptions
- RAG integration for procedure lookup
- HITL request creation
- Pattern identification and entity extraction
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.task_proposer_agent import (
    TaskProposerAgent,
    TaskProposalSet,
    ProposedTask,
    TaskPriority,
    TaskPhase,
    HITLApprovalRequest,
    create_task_proposer,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def proposer():
    """Create proposer without external dependencies."""
    return TaskProposerAgent()


@pytest.fixture
def mock_rag_client():
    """Mock RAG client with sample responses."""
    client = AsyncMock()
    client.search_for_ega = AsyncMock(return_value=[
        MagicMock(
            id="proc1",
            section_code="3.1",
            section_title="Bank Confirmations",
            procedure_text="은행조회서를 발송하여 잔액을 확인한다.",
            relevance_score=0.9,
            related_assertions=["existence"]
        ),
        MagicMock(
            id="proc2",
            section_code="3.2",
            section_title="AR Recon",
            procedure_text="매출채권 잔액을 조정한다.",
            relevance_score=0.85,
            related_assertions=["completeness", "valuation"]
        ),
        MagicMock(
            id="proc3",
            section_code="3.3",
            section_title="Follow-up Procedures",
            procedure_text="조회 차이에 대해 후속 절차를 수행한다.",
            relevance_score=0.75,
            related_assertions=["existence", "valuation"]
        ),
    ])
    return client


@pytest.fixture
def mock_hitl_service():
    """Mock HITL service."""
    service = AsyncMock()
    service.create_request = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = AsyncMock()
    return client


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

class TestTaskProposerAgent:
    """Tests for basic TaskProposerAgent functionality."""

    @pytest.mark.asyncio
    async def test_propose_tasks_basic(self, proposer):
        """Should generate task proposals for an EGA without dependencies."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="은행 등 금융기관과의 거래와 약정을 조회한다",
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)
        assert result.ega_id == "ega-1"
        assert len(result.proposed_tasks) > 0
        assert result.requires_hitl_approval is True
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_propose_tasks_returns_proposal_set(self, proposer):
        """Should return properly structured TaskProposalSet."""
        result = await proposer.propose_tasks(
            ega_id="ega-test",
            ega_name="재고자산 실사",
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)
        assert result.ega_id == "ega-test"
        assert result.ega_name == "재고자산 실사"
        assert isinstance(result.proposed_tasks, list)
        assert isinstance(result.rag_sources, list)
        assert isinstance(result.hierarchy_context, dict)

    @pytest.mark.asyncio
    async def test_proposed_task_structure(self, proposer):
        """Should generate properly structured ProposedTask objects."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="금융기관 조회",
            auto_create_hitl=False
        )

        for task in result.proposed_tasks:
            assert isinstance(task, ProposedTask)
            assert task.id is not None
            assert task.title is not None
            assert task.description is not None
            assert isinstance(task.phase, TaskPhase)
            assert isinstance(task.priority, TaskPriority)
            assert task.ega_id == "ega-1"
            assert 0 <= task.confidence_score <= 1
            assert isinstance(task.related_assertions, list)
            assert isinstance(task.risk_considerations, list)

    @pytest.mark.asyncio
    async def test_propose_tasks_with_hierarchy_context(self, proposer):
        """Should use hierarchy context in task generation."""
        context = {
            "business_process": "Revenue-Collection Cycle",
            "fsli": "Trade Receivables"
        }

        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="매출채권 조회",
            hierarchy_context=context,
            auto_create_hitl=False
        )

        assert result.hierarchy_context == context
        # High priority FSLI should result in HIGH priority tasks
        high_priority_tasks = [
            t for t in result.proposed_tasks
            if t.priority == TaskPriority.HIGH
        ]
        assert len(high_priority_tasks) > 0


# ============================================================================
# RAG INTEGRATION TESTS
# ============================================================================

class TestRAGIntegration:
    """Tests for RAG client integration."""

    @pytest.mark.asyncio
    async def test_propose_tasks_with_rag(self, mock_rag_client):
        """Should use RAG sources in task generation."""
        proposer = TaskProposerAgent(rag_client=mock_rag_client)

        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="은행 금융기관 조회",
            hierarchy_context={"business_process": "Revenue", "fsli": "AR"},
            auto_create_hitl=False
        )

        # RAG should have been called
        mock_rag_client.search_for_ega.assert_called_once()

        # RAG sources should be included
        assert len(result.rag_sources) > 0
        assert result.rag_sources[0]["id"] == "proc1"

    @pytest.mark.asyncio
    async def test_rag_sources_formatted_correctly(self, mock_rag_client):
        """Should format RAG sources with proper fields."""
        proposer = TaskProposerAgent(rag_client=mock_rag_client)

        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=False
        )

        for source in result.rag_sources:
            assert "id" in source
            assert "section_code" in source
            assert "section_title" in source
            assert "procedure_text" in source
            assert "relevance_score" in source
            assert "related_assertions" in source

    @pytest.mark.asyncio
    async def test_rag_failure_graceful_handling(self):
        """Should handle RAG client failures gracefully."""
        mock_rag = AsyncMock()
        mock_rag.search_for_ega = AsyncMock(side_effect=Exception("RAG error"))

        proposer = TaskProposerAgent(rag_client=mock_rag)

        # Should not raise, just log warning
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)
        assert result.rag_sources == []  # Empty due to failure
        assert len(result.proposed_tasks) > 0  # Tasks still generated

    @pytest.mark.asyncio
    async def test_confidence_score_with_rag(self, mock_rag_client):
        """Should have higher confidence when RAG sources available."""
        proposer = TaskProposerAgent(rag_client=mock_rag_client)

        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="금융기관 조회",
            auto_create_hitl=False
        )

        # With RAG sources, confidence should be higher
        for task in result.proposed_tasks:
            assert task.confidence_score >= 0.5


# ============================================================================
# HITL INTEGRATION TESTS
# ============================================================================

class TestHITLIntegration:
    """Tests for HITL service integration."""

    @pytest.mark.asyncio
    async def test_propose_tasks_creates_hitl(self, mock_hitl_service):
        """Should create HITL request when enabled."""
        proposer = TaskProposerAgent(hitl_service=mock_hitl_service)

        await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=True
        )

        mock_hitl_service.create_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_tasks_skips_hitl_when_disabled(self, mock_hitl_service):
        """Should not create HITL request when disabled."""
        proposer = TaskProposerAgent(hitl_service=mock_hitl_service)

        await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=False
        )

        mock_hitl_service.create_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_hitl_request_structure(self, mock_hitl_service):
        """Should create properly structured HITL request."""
        proposer = TaskProposerAgent(hitl_service=mock_hitl_service)

        await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=True
        )

        call_args = mock_hitl_service.create_request.call_args
        request = call_args[0][0]

        assert isinstance(request, HITLApprovalRequest)
        assert request.ega_id == "ega-1"
        assert request.request_type == "task_proposal"
        assert len(request.proposed_tasks) > 0
        assert "approve_all" in request.suggested_actions

    @pytest.mark.asyncio
    async def test_handle_hitl_response_reject(self, proposer):
        """Should handle rejection response."""
        result = await proposer.handle_hitl_response(
            request_id="req-1",
            action="reject_all"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_handle_hitl_response_approve(self, proposer):
        """Should handle approval response."""
        result = await proposer.handle_hitl_response(
            request_id="req-1",
            action="approve_all"
        )

        # Currently returns empty, but should not raise
        assert isinstance(result, list)


# ============================================================================
# PATTERN IDENTIFICATION TESTS
# ============================================================================

class TestPatternIdentification:
    """Tests for EGA pattern identification."""

    def test_identify_ega_pattern_inquiry(self, proposer):
        """Should identify inquiry pattern (조회)."""
        pattern = proposer._identify_ega_pattern("은행 등 금융기관과의 거래와 약정을 조회한다")
        assert pattern == "조회"

        pattern = proposer._identify_ega_pattern("매출채권 잔액 확인")
        assert pattern == "조회"

    def test_identify_ega_pattern_inspection(self, proposer):
        """Should identify inspection pattern (실사)."""
        pattern = proposer._identify_ega_pattern("재고자산 실사를 수행한다")
        assert pattern == "실사"

        pattern = proposer._identify_ega_pattern("현금 관찰 절차")
        assert pattern == "실사"

    def test_identify_ega_pattern_review(self, proposer):
        """Should identify review pattern (검토)."""
        pattern = proposer._identify_ega_pattern("계약서를 검토한다")
        assert pattern == "검토"

        pattern = proposer._identify_ega_pattern("변동 분석 수행")
        assert pattern == "검토"

    def test_identify_ega_pattern_controls(self, proposer):
        """Should identify controls pattern (통제)."""
        pattern = proposer._identify_ega_pattern("내부통제 테스트")
        assert pattern == "통제"

        pattern = proposer._identify_ega_pattern("통제 운영 효과성 평가")
        assert pattern == "통제"

    def test_identify_ega_pattern_default(self, proposer):
        """Should default to review pattern for unknown patterns."""
        pattern = proposer._identify_ega_pattern("알 수 없는 절차")
        assert pattern == "검토"


# ============================================================================
# ENTITY EXTRACTION TESTS
# ============================================================================

class TestEntityExtraction:
    """Tests for entity extraction from EGA names."""

    def test_extract_entity_financial_institution(self, proposer):
        """Should extract financial institution entity."""
        entity = proposer._extract_entity("금융기관과의 거래를 조회한다")
        assert entity == "금융기관"

    def test_extract_entity_receivables(self, proposer):
        """Should extract receivables entity."""
        entity = proposer._extract_entity("매출채권 잔액을 확인한다")
        assert entity == "매출채권"

    def test_extract_entity_inventory(self, proposer):
        """Should extract inventory entity."""
        entity = proposer._extract_entity("재고자산 실사")
        assert entity == "재고자산"

    def test_extract_entity_bank(self, proposer):
        """Should extract bank entity."""
        entity = proposer._extract_entity("은행 조회서 발송")
        assert entity == "은행"

    def test_extract_entity_fallback(self, proposer):
        """Should fallback to first significant word."""
        entity = proposer._extract_entity("특별한 절차 수행")
        assert entity == "특별한"


# ============================================================================
# RISK IDENTIFICATION TESTS
# ============================================================================

class TestRiskIdentification:
    """Tests for risk consideration identification."""

    def test_identify_risks_inquiry(self, proposer):
        """Should identify inquiry-specific risks."""
        risks = proposer._identify_risks(
            "금융기관 조회",
            {"fsli": "Cash"}
        )

        assert len(risks) > 0
        assert any("조회" in r for r in risks)

    def test_identify_risks_inspection(self, proposer):
        """Should identify inspection-specific risks."""
        risks = proposer._identify_risks(
            "재고 실사",
            {"fsli": "Inventory"}
        )

        assert len(risks) > 0
        assert any("실사" in r or "재고" in r for r in risks)

    def test_identify_risks_ar_context(self, proposer):
        """Should identify AR-specific risks."""
        risks = proposer._identify_risks(
            "매출채권 검토",
            {"fsli": "AR"}
        )

        assert any("대손충당금" in r for r in risks)

    def test_identify_risks_inventory_context(self, proposer):
        """Should identify inventory-specific risks."""
        risks = proposer._identify_risks(
            "재고 검토",
            {"fsli": "Inventory"}
        )

        assert any("재고" in r or "평가" in r for r in risks)

    def test_identify_risks_default(self, proposer):
        """Should provide default risks when none identified."""
        risks = proposer._identify_risks(
            "일반 절차",
            {}
        )

        assert len(risks) > 0


# ============================================================================
# TASK TEMPLATE TESTS
# ============================================================================

class TestTaskTemplates:
    """Tests for task template matching."""

    @pytest.mark.asyncio
    async def test_inquiry_templates(self, proposer):
        """Should use inquiry templates for inquiry EGAs."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="금융기관 잔액 조회",
            auto_create_hitl=False
        )

        titles = [t.title for t in result.proposed_tasks]
        # Should have inquiry-specific tasks
        assert any("완전성 체크" in t for t in titles)
        assert any("Recon" in t for t in titles)

    @pytest.mark.asyncio
    async def test_inspection_templates(self, proposer):
        """Should use inspection templates for inspection EGAs."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="재고자산 실사",
            auto_create_hitl=False
        )

        titles = [t.title for t in result.proposed_tasks]
        # Should have inspection-specific tasks
        assert any("실사" in t for t in titles)

    @pytest.mark.asyncio
    async def test_controls_templates(self, proposer):
        """Should use controls templates for controls EGAs."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="내부통제 테스트",
            auto_create_hitl=False
        )

        titles = [t.title for t in result.proposed_tasks]
        # Should have controls-specific tasks
        assert any("통제" in t for t in titles)

    @pytest.mark.asyncio
    async def test_task_phases_correct(self, proposer):
        """Should assign correct phases to tasks."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="내부통제 평가",
            auto_create_hitl=False
        )

        # Controls tasks should be in controls testing phase
        for task in result.proposed_tasks:
            if "통제" in task.title:
                assert task.phase == TaskPhase.CONTROLS_TESTING


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    """Tests for data class serialization."""

    @pytest.mark.asyncio
    async def test_proposed_task_to_dict(self, proposer):
        """Should serialize ProposedTask correctly."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=False
        )

        for task in result.proposed_tasks:
            task_dict = task.to_dict()
            assert isinstance(task_dict, dict)
            assert "id" in task_dict
            assert "title" in task_dict
            assert "phase" in task_dict
            assert isinstance(task_dict["phase"], str)
            assert isinstance(task_dict["priority"], str)

    @pytest.mark.asyncio
    async def test_task_proposal_set_to_dict(self, proposer):
        """Should serialize TaskProposalSet correctly."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            auto_create_hitl=False
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "ega_id" in result_dict
        assert "proposed_tasks" in result_dict
        assert isinstance(result_dict["proposed_tasks"], list)

    def test_hitl_approval_request_to_dict(self):
        """Should serialize HITLApprovalRequest correctly."""
        task = ProposedTask(
            id="task-1",
            title="Test Task",
            description="Test Description",
            phase=TaskPhase.PLANNING,
            priority=TaskPriority.MEDIUM,
            estimated_hours=4.0,
            required_skills=["audit"],
            related_assertions=["existence"],
            source_procedures=[],
            suggested_approach="Test approach",
            risk_considerations=["Test risk"],
            ega_id="ega-1",
            ega_name="Test EGA",
            confidence_score=0.8
        )

        request = HITLApprovalRequest(
            id="req-1",
            ega_id="ega-1",
            ega_name="Test EGA",
            proposed_tasks=[task],
            rag_sources=[],
            context={},
            created_at=datetime.utcnow().isoformat()
        )

        request_dict = request.to_dict()
        assert isinstance(request_dict, dict)
        assert request_dict["id"] == "req-1"
        assert request_dict["request_type"] == "task_proposal"
        assert len(request_dict["proposed_tasks"]) == 1


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================

class TestCreateTaskProposer:
    """Tests for factory function."""

    def test_create_without_dependencies(self):
        """Should create proposer without dependencies."""
        proposer = create_task_proposer()
        assert isinstance(proposer, TaskProposerAgent)
        assert proposer.rag_client is None
        assert proposer.llm_client is None
        assert proposer.hitl_service is None

    def test_create_with_all_dependencies(self):
        """Should create proposer with all dependencies."""
        mock_rag = MagicMock()
        mock_llm = MagicMock()
        mock_hitl = MagicMock()

        proposer = create_task_proposer(
            rag_client=mock_rag,
            llm_client=mock_llm,
            hitl_service=mock_hitl
        )

        assert proposer.rag_client is mock_rag
        assert proposer.llm_client is mock_llm
        assert proposer.hitl_service is mock_hitl

    def test_create_with_partial_dependencies(self):
        """Should create proposer with partial dependencies."""
        mock_rag = MagicMock()

        proposer = create_task_proposer(rag_client=mock_rag)

        assert proposer.rag_client is mock_rag
        assert proposer.llm_client is None
        assert proposer.hitl_service is None


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_ega_name(self, proposer):
        """Should handle empty EGA name gracefully."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="",
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)
        # Should still generate tasks with default pattern

    @pytest.mark.asyncio
    async def test_none_hierarchy_context(self, proposer):
        """Should handle None hierarchy context."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="조회 절차",
            hierarchy_context=None,
            auto_create_hitl=False
        )

        assert result.hierarchy_context == {}

    @pytest.mark.asyncio
    async def test_long_ega_name(self, proposer):
        """Should handle very long EGA names."""
        long_name = "은행 등 금융기관과의 거래와 약정을 조회한다 " * 10

        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name=long_name,
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)
        assert len(result.proposed_tasks) > 0

    @pytest.mark.asyncio
    async def test_special_characters_in_ega_name(self, proposer):
        """Should handle special characters in EGA name."""
        result = await proposer.propose_tasks(
            ega_id="ega-1",
            ega_name="금융기관 (은행/증권) 조회 [2024]",
            auto_create_hitl=False
        )

        assert isinstance(result, TaskProposalSet)

    @pytest.mark.asyncio
    async def test_concurrent_proposals(self, proposer):
        """Should handle concurrent proposal generation."""
        import asyncio

        async def generate_proposal(ega_id: str, ega_name: str):
            return await proposer.propose_tasks(
                ega_id=ega_id,
                ega_name=ega_name,
                auto_create_hitl=False
            )

        results = await asyncio.gather(
            generate_proposal("ega-1", "조회 절차"),
            generate_proposal("ega-2", "실사 절차"),
            generate_proposal("ega-3", "검토 절차"),
        )

        assert len(results) == 3
        for result in results:
            assert isinstance(result, TaskProposalSet)
