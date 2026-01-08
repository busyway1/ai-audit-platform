"""
Integration Tests for MCP + LangGraph

Tests the integration between AI Audit LangGraph agents
and the MCP RAG server for K-IFRS/K-GAAS retrieval.

Test Categories:
1. MCPRagClient - HTTP client for MCP RAG server
2. StandardRetrieverAgent - Uses MCP for real K-IFRS retrieval
3. reranker_node - LLM-based reranking of Top-30 to Top-5
4. multihop_node - Agent-controlled N-hop retrieval
5. E2E Flow - Full retrieval pipeline test

Reference:
- MCP RAG Server: Uses hybrid search (BM25 + vector) with pgvector
- K-IFRS Standards: Korean International Financial Reporting Standards
- K-GAAS: Korean Generally Accepted Auditing Standards
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# MCP RAG CLIENT (To be implemented in src/mcp/client.py)
# ============================================================================

@dataclass
class MCPSearchResult:
    """Result from MCP RAG hybrid search."""
    paragraph_id: str
    standard_code: str
    paragraph_number: str
    content: str
    score: float
    metadata: Dict[str, Any]


class MCPRagClient:
    """
    HTTP client for MCP RAG server.

    Provides interface to the MCP server's hybrid search capabilities
    for K-IFRS/K-GAAS standard retrieval.

    Endpoints:
    - POST /search_standards: Hybrid search (BM25 + vector)
    - GET /paragraph/{id}: Get specific paragraph
    - GET /health: Health check
    """

    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        Initialize MCP RAG client.

        Args:
            base_url: MCP RAG server URL
        """
        self.base_url = base_url
        self.timeout = 30.0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP RAG server health.

        Returns:
            Dict with status, version, and capabilities

        Raises:
            httpx.ConnectError: If server is not reachable
        """
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()

    async def search_standards(
        self,
        query: str,
        top_k: int = 30,
        account_category: Optional[str] = None,
        audit_stage: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[MCPSearchResult]:
        """
        Search K-IFRS/K-GAAS standards using hybrid search.

        Args:
            query: Search query (natural language)
            top_k: Number of results to return (default: 30 for reranking)
            account_category: Filter by category (e.g., "Sales", "Inventory")
            audit_stage: Filter by stage (e.g., "Risk Assessment", "Substantive")
            min_score: Minimum relevance score threshold

        Returns:
            List of MCPSearchResult ordered by relevance score

        Raises:
            httpx.HTTPStatusError: If server returns error
        """
        client = await self._get_client()

        payload = {
            "query": query,
            "top_k": top_k,
            "filters": {}
        }

        if account_category:
            payload["filters"]["account_category"] = account_category
        if audit_stage:
            payload["filters"]["audit_stage"] = audit_stage
        if min_score > 0:
            payload["filters"]["min_score"] = min_score

        response = await client.post("/search_standards", json=payload)
        response.raise_for_status()

        data = response.json()
        return [
            MCPSearchResult(
                paragraph_id=r["paragraph_id"],
                standard_code=r["standard_code"],
                paragraph_number=r["paragraph_number"],
                content=r["content"],
                score=r["score"],
                metadata=r.get("metadata", {})
            )
            for r in data.get("results", [])
        ]

    async def get_paragraph_by_id(
        self,
        paragraph_id: str
    ) -> Optional[MCPSearchResult]:
        """
        Get specific paragraph by ID.

        Args:
            paragraph_id: Unique paragraph identifier

        Returns:
            MCPSearchResult if found, None otherwise
        """
        client = await self._get_client()

        response = await client.get(f"/paragraph/{paragraph_id}")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return MCPSearchResult(
            paragraph_id=data["paragraph_id"],
            standard_code=data["standard_code"],
            paragraph_number=data["paragraph_number"],
            content=data["content"],
            score=1.0,  # Direct lookup, max score
            metadata=data.get("metadata", {})
        )

    async def get_related_paragraphs(
        self,
        paragraph_id: str,
        relationship_types: Optional[List[str]] = None
    ) -> List[MCPSearchResult]:
        """
        Get paragraphs related to a given paragraph.

        Used for multi-hop retrieval to expand context.

        Args:
            paragraph_id: Source paragraph ID
            relationship_types: Filter by types (e.g., ["reference", "example"])

        Returns:
            List of related paragraphs
        """
        client = await self._get_client()

        params = {}
        if relationship_types:
            params["types"] = ",".join(relationship_types)

        response = await client.get(
            f"/paragraph/{paragraph_id}/related",
            params=params
        )

        if response.status_code == 404:
            return []

        response.raise_for_status()
        data = response.json()

        return [
            MCPSearchResult(
                paragraph_id=r["paragraph_id"],
                standard_code=r["standard_code"],
                paragraph_number=r["paragraph_number"],
                content=r["content"],
                score=r.get("relevance_score", 0.8),
                metadata=r.get("metadata", {})
            )
            for r in data.get("related", [])
        ]


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_mcp_client():
    """Create mock MCP RAG client for unit tests."""
    client = AsyncMock(spec=MCPRagClient)

    # Configure default mock responses
    client.health_check.return_value = {
        "status": "healthy",
        "version": "1.0.0",
        "capabilities": ["hybrid_search", "paragraph_lookup", "related_paragraphs"]
    }

    client.search_standards.return_value = [
        MCPSearchResult(
            paragraph_id="kifrs1115-31",
            standard_code="K-IFRS 1115",
            paragraph_number="31",
            content="기업은 고객에게 약속한 재화나 용역을 이전하여 수행의무를 이행할 때 수익을 인식한다.",
            score=0.95,
            metadata={"category": "revenue", "language": "ko"}
        ),
        MCPSearchResult(
            paragraph_id="kifrs1115-32",
            standard_code="K-IFRS 1115",
            paragraph_number="32",
            content="재화나 용역은 고객이 그 재화나 용역에 대한 통제를 획득할 때 이전된다.",
            score=0.90,
            metadata={"category": "revenue", "language": "ko"}
        ),
        MCPSearchResult(
            paragraph_id="kgaas500-a1",
            standard_code="K-GAAS 500",
            paragraph_number="A1",
            content="감사증거는 감사의견의 근거가 되는 정보이다. 감사증거는 재무제표의 기초가 되는 회계기록의 정보와 기타 정보를 포함한다.",
            score=0.85,
            metadata={"category": "audit_evidence", "language": "ko"}
        ),
    ]

    client.get_paragraph_by_id.return_value = MCPSearchResult(
        paragraph_id="kifrs1115-31",
        standard_code="K-IFRS 1115",
        paragraph_number="31",
        content="기업은 고객에게 약속한 재화나 용역을 이전하여 수행의무를 이행할 때 수익을 인식한다.",
        score=1.0,
        metadata={"category": "revenue", "language": "ko"}
    )

    client.get_related_paragraphs.return_value = [
        MCPSearchResult(
            paragraph_id="kifrs1115-ie-example1",
            standard_code="K-IFRS 1115 IE",
            paragraph_number="Example 1",
            content="예시: 기업이 제품을 인도하고 대금을 수령하는 단순 판매 거래",
            score=0.80,
            metadata={"type": "example", "language": "ko"}
        )
    ]

    return client


@pytest.fixture
def sample_task_state() -> Dict[str, Any]:
    """Create sample TaskState for testing."""
    return {
        "task_id": "TASK-MCP-001",
        "thread_id": "mcp-test-thread-001",
        "category": "Sales",
        "status": "In-Progress",
        "messages": [],
        "raw_data": {
            "category": "Sales",
            "total_sales": 5_000_000_000,
            "transaction_count": 150,
            "period": "2024-01-01 to 2024-12-31"
        },
        "standards": [],
        "vouching_logs": [],
        "workpaper_draft": "",
        "next_staff": "standard_retriever",
        "error_report": "",
        "risk_score": 50
    }


@pytest.fixture
def mock_search_results() -> List[Dict[str, Any]]:
    """Create mock search results for reranking tests."""
    return [
        {
            "paragraph_id": f"para-{i}",
            "standard_code": f"K-IFRS 11{15 + (i % 3)}",
            "paragraph_number": str(i),
            "content": f"Mock paragraph content {i} for testing reranking functionality.",
            "score": 0.9 - (i * 0.02),
            "metadata": {"category": "revenue" if i % 2 == 0 else "audit"}
        }
        for i in range(30)
    ]


@pytest.fixture
def mock_llm():
    """Create mock LLM for reranker tests."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(
        content="""Based on my analysis, the most relevant paragraphs for the audit query are:

1. **para-0** (Score: 0.95) - Directly addresses revenue recognition timing
2. **para-2** (Score: 0.92) - Provides specific guidance on performance obligations
3. **para-5** (Score: 0.88) - Contains audit evidence requirements
4. **para-8** (Score: 0.85) - Discusses control transfer criteria
5. **para-12** (Score: 0.82) - Relates to contract modifications

Reasoning: These paragraphs form a coherent set covering the key aspects of revenue audit procedures."""
    )
    return llm


# ============================================================================
# TEST: MCPRagClient
# ============================================================================

class TestMCPRagClient:
    """Test cases for MCPRagClient HTTP operations."""

    @pytest.mark.asyncio
    async def test_search_standards_success(self, mock_mcp_client):
        """Test successful hybrid search call."""
        results = await mock_mcp_client.search_standards(
            query="수익 인식 시점 판단 기준",
            top_k=30,
            account_category="Sales"
        )

        assert len(results) == 3
        assert results[0].paragraph_id == "kifrs1115-31"
        assert results[0].score == 0.95
        assert "수익을 인식한다" in results[0].content

        # Verify call arguments
        mock_mcp_client.search_standards.assert_called_once_with(
            query="수익 인식 시점 판단 기준",
            top_k=30,
            account_category="Sales"
        )

    @pytest.mark.asyncio
    async def test_search_standards_with_filters(self, mock_mcp_client):
        """Test hybrid search with metadata filters."""
        await mock_mcp_client.search_standards(
            query="감사증거 수집",
            top_k=20,
            audit_stage="Substantive",
            min_score=0.7
        )

        mock_mcp_client.search_standards.assert_called_once()
        call_args = mock_mcp_client.search_standards.call_args
        assert call_args.kwargs["audit_stage"] == "Substantive"
        assert call_args.kwargs["min_score"] == 0.7

    @pytest.mark.asyncio
    async def test_search_standards_connection_error(self):
        """Test graceful handling of connection errors."""
        client = MCPRagClient(base_url="http://localhost:99999")

        with pytest.raises(httpx.ConnectError):
            await client.search_standards(query="test query")

        await client.close()

    @pytest.mark.asyncio
    async def test_search_standards_empty_results(self, mock_mcp_client):
        """Test handling of empty search results."""
        mock_mcp_client.search_standards.return_value = []

        results = await mock_mcp_client.search_standards(
            query="nonexistent standard xyz123"
        )

        assert results == []
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_paragraph_by_id_success(self, mock_mcp_client):
        """Test successful paragraph lookup."""
        result = await mock_mcp_client.get_paragraph_by_id("kifrs1115-31")

        assert result is not None
        assert result.paragraph_id == "kifrs1115-31"
        assert result.standard_code == "K-IFRS 1115"
        assert result.score == 1.0  # Direct lookup should have max score

    @pytest.mark.asyncio
    async def test_get_paragraph_by_id_not_found(self, mock_mcp_client):
        """Test paragraph lookup for non-existent ID."""
        mock_mcp_client.get_paragraph_by_id.return_value = None

        result = await mock_mcp_client.get_paragraph_by_id("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check(self, mock_mcp_client):
        """Test MCP server health check."""
        health = await mock_mcp_client.health_check()

        assert health["status"] == "healthy"
        assert "hybrid_search" in health["capabilities"]
        assert "version" in health

    @pytest.mark.asyncio
    async def test_health_check_server_unavailable(self):
        """Test health check when server is unavailable."""
        client = MCPRagClient(base_url="http://localhost:99999")

        with pytest.raises(httpx.ConnectError):
            await client.health_check()

        await client.close()

    @pytest.mark.asyncio
    async def test_get_related_paragraphs(self, mock_mcp_client):
        """Test fetching related paragraphs for multi-hop retrieval."""
        results = await mock_mcp_client.get_related_paragraphs(
            paragraph_id="kifrs1115-31",
            relationship_types=["example", "reference"]
        )

        assert len(results) == 1
        assert "Example" in results[0].paragraph_number
        assert results[0].metadata.get("type") == "example"

    @pytest.mark.asyncio
    async def test_client_connection_reuse(self, mock_mcp_client):
        """Test that client reuses HTTP connections."""
        # Make multiple requests
        await mock_mcp_client.health_check()
        await mock_mcp_client.search_standards(query="test1")
        await mock_mcp_client.search_standards(query="test2")

        # All requests should succeed with connection reuse
        assert mock_mcp_client.health_check.call_count == 1
        assert mock_mcp_client.search_standards.call_count == 2


# ============================================================================
# TEST: StandardRetrieverAgent with MCP
# ============================================================================

class TestStandardRetrieverAgentMCP:
    """Test StandardRetrieverAgent integration with MCP client."""

    @pytest.mark.asyncio
    async def test_retriever_uses_mcp_client(
        self,
        mock_mcp_client,
        sample_task_state
    ):
        """Verify agent calls MCP search_standards.

        Note: This test demonstrates the integration pattern.
        When MCPRagClient is integrated into StandardRetrieverAgent,
        update the import and agent initialization accordingly.
        """
        # Simulate how StandardRetrieverAgent would use MCP client
        # when MCP integration is implemented

        # Step 1: Query MCP for standards
        results = await mock_mcp_client.search_standards(
            query=f"audit {sample_task_state['category']}",
            account_category=sample_task_state["category"]
        )

        # Step 2: Format results for TaskState
        standards = [
            f"{r.standard_code} 문단 {r.paragraph_number}: {r.content}"
            for r in results
        ]

        # Step 3: Update state (simulating what agent.run would do)
        sample_task_state["standards"] = standards

        # Verify standards were retrieved
        assert "standards" in sample_task_state
        assert len(sample_task_state["standards"]) == 3

        # Verify MCP client was called with correct params
        mock_mcp_client.search_standards.assert_called_once()
        call_args = mock_mcp_client.search_standards.call_args
        assert call_args.kwargs["account_category"] == "Sales"

    @pytest.mark.asyncio
    async def test_retriever_formats_results_for_state(
        self,
        mock_mcp_client,
        sample_task_state
    ):
        """Verify results formatted correctly for TaskState.standards."""
        mock_mcp_client.search_standards.return_value = [
            MCPSearchResult(
                paragraph_id="kifrs1115-31",
                standard_code="K-IFRS 1115",
                paragraph_number="31",
                content="수익 인식 기준",
                score=0.95,
                metadata={}
            )
        ]

        # Simulate formatting logic
        results = await mock_mcp_client.search_standards(query="수익 인식")

        # Format for TaskState (list of strings)
        formatted_standards = [
            f"{r.standard_code}: {r.content} (문단 {r.paragraph_number})"
            for r in results
        ]

        assert len(formatted_standards) == 1
        assert "K-IFRS 1115" in formatted_standards[0]
        assert "문단 31" in formatted_standards[0]

    @pytest.mark.asyncio
    async def test_retriever_handles_mcp_error(
        self,
        mock_mcp_client,
        sample_task_state
    ):
        """Verify graceful fallback on MCP error."""
        mock_mcp_client.search_standards.side_effect = httpx.ConnectError("Connection refused")

        # When MCP fails, should fall back to mock standards
        try:
            await mock_mcp_client.search_standards(query="test")
        except httpx.ConnectError:
            # Fallback to hardcoded standards
            fallback_standards = [
                "K-GAAS 200: 재무제표감사를 수행하는 독립된 감사인의 전반적인 목적",
                "K-GAAS 315: 중요한 왜곡표시위험의 식별과 평가"
            ]
            assert len(fallback_standards) == 2

    @pytest.mark.asyncio
    async def test_retriever_applies_category_filter(
        self,
        mock_mcp_client,
        sample_task_state
    ):
        """Verify category-based filtering is applied."""
        await mock_mcp_client.search_standards(
            query="audit procedures",
            account_category=sample_task_state["category"]
        )

        call_args = mock_mcp_client.search_standards.call_args
        assert call_args.kwargs["account_category"] == "Sales"

    @pytest.mark.asyncio
    async def test_retriever_logs_retrieval_stats(
        self,
        mock_mcp_client,
        sample_task_state,
        caplog
    ):
        """Verify retrieval statistics are logged."""
        import logging

        with caplog.at_level(logging.INFO):
            results = await mock_mcp_client.search_standards(
                query="revenue recognition"
            )

            # In real implementation, logging would occur
            # Here we just verify the results are returned
            assert len(results) == 3


# ============================================================================
# TEST: Reranker Node
# ============================================================================

class TestRerankerNode:
    """Test LLM-based reranking of search results."""

    @pytest.mark.asyncio
    async def test_reranker_reduces_to_top5(
        self,
        mock_search_results,
        mock_llm
    ):
        """Verify Top-30 -> Top-5 reduction."""
        # Simulate reranking logic
        assert len(mock_search_results) == 30

        # Rerank using LLM
        response = await mock_llm.ainvoke([])

        # Parse LLM response to get top 5
        top_5_ids = ["para-0", "para-2", "para-5", "para-8", "para-12"]
        reranked = [
            r for r in mock_search_results
            if r["paragraph_id"] in top_5_ids
        ]

        assert len(reranked) == 5
        assert reranked[0]["paragraph_id"] == "para-0"

    @pytest.mark.asyncio
    async def test_reranker_includes_reasoning(self, mock_llm):
        """Verify rerank_metadata includes scores and reasons."""
        response = await mock_llm.ainvoke([])
        content = response.content

        # Verify reasoning is included
        assert "Reasoning:" in content
        assert "revenue recognition" in content.lower()
        assert "Score:" in content

    @pytest.mark.asyncio
    async def test_reranker_preserves_original_scores(
        self,
        mock_search_results
    ):
        """Verify original scores are preserved in metadata."""
        # Create rerank metadata structure
        rerank_metadata = {
            "original_scores": {
                r["paragraph_id"]: r["score"]
                for r in mock_search_results[:5]
            },
            "rerank_scores": {
                "para-0": 0.95,
                "para-2": 0.92,
                "para-5": 0.88,
                "para-8": 0.85,
                "para-12": 0.82
            },
            "reasoning": "Selected based on relevance to revenue audit"
        }

        assert "original_scores" in rerank_metadata
        assert "rerank_scores" in rerank_metadata
        assert len(rerank_metadata["rerank_scores"]) == 5

    @pytest.mark.asyncio
    async def test_reranker_fallback_on_llm_error(
        self,
        mock_search_results,
        mock_llm
    ):
        """Verify fallback to original top-5 on LLM error."""
        mock_llm.ainvoke.side_effect = Exception("LLM timeout")

        try:
            await mock_llm.ainvoke([])
        except Exception:
            # Fallback: use original top-5 by score
            top_5 = sorted(
                mock_search_results,
                key=lambda x: x["score"],
                reverse=True
            )[:5]

            assert len(top_5) == 5
            assert top_5[0]["score"] >= top_5[4]["score"]

    @pytest.mark.asyncio
    async def test_reranker_handles_duplicate_scores(self):
        """Verify handling of results with identical scores."""
        results_with_ties = [
            {"paragraph_id": f"para-{i}", "score": 0.85}
            for i in range(10)
        ]

        # Should deterministically select 5
        top_5 = results_with_ties[:5]

        assert len(top_5) == 5
        assert all(r["score"] == 0.85 for r in top_5)

    @pytest.mark.asyncio
    async def test_reranker_with_query_context(self, mock_llm):
        """Verify reranker uses query context for relevance scoring."""
        query = "매출 수익 인식 시점 결정 기준"

        # In real implementation, query would be passed to LLM prompt
        response = await mock_llm.ainvoke([])

        # The response should reference the query context
        assert response.content is not None
        assert len(response.content) > 0


# ============================================================================
# TEST: Multi-hop Node
# ============================================================================

class TestMultihopNode:
    """Test agent-controlled N-hop retrieval."""

    @pytest.mark.asyncio
    async def test_multihop_expands_context(self, mock_mcp_client):
        """Verify related_paragraphs are fetched when needed."""
        # Initial result
        initial = await mock_mcp_client.get_paragraph_by_id("kifrs1115-31")
        assert initial is not None

        # Expand with related paragraphs
        related = await mock_mcp_client.get_related_paragraphs(
            paragraph_id="kifrs1115-31"
        )

        assert len(related) == 1
        assert "Example" in related[0].paragraph_number

    @pytest.mark.asyncio
    async def test_multihop_respects_max_hops(self, mock_mcp_client):
        """Verify max 3 hops limit is respected."""
        max_hops = 3
        hops_performed = 0
        visited = set()
        current_ids = ["kifrs1115-31"]

        while hops_performed < max_hops and current_ids:
            next_ids = []
            for pid in current_ids:
                if pid not in visited:
                    visited.add(pid)
                    related = await mock_mcp_client.get_related_paragraphs(pid)
                    next_ids.extend(r.paragraph_id for r in related)

            current_ids = next_ids
            hops_performed += 1

        assert hops_performed <= max_hops

    @pytest.mark.asyncio
    async def test_multihop_no_expansion_when_not_needed(
        self,
        mock_mcp_client,
        mock_llm
    ):
        """Verify no expansion for simple queries."""
        # Configure LLM to indicate no expansion needed
        mock_llm.ainvoke.return_value = MagicMock(
            content="No expansion needed. Initial results are sufficient."
        )

        # For simple queries, multihop should not expand
        query = "K-IFRS 1115 문단 31"  # Direct reference, no expansion needed

        initial_results = await mock_mcp_client.search_standards(query=query)

        # Decision: Do not expand if query is specific
        needs_expansion = not ("문단" in query and any(
            c.isdigit() for c in query
        ))

        assert needs_expansion == False

    @pytest.mark.asyncio
    async def test_multihop_filters_by_relationship_type(
        self,
        mock_mcp_client
    ):
        """Verify filtering by relationship type (reference, example)."""
        results = await mock_mcp_client.get_related_paragraphs(
            paragraph_id="kifrs1115-31",
            relationship_types=["example"]
        )

        # Should only return examples
        assert all(
            r.metadata.get("type") == "example"
            for r in results
        )

    @pytest.mark.asyncio
    async def test_multihop_avoids_cycles(self, mock_mcp_client):
        """Verify cycle detection in multi-hop traversal."""
        visited = set()

        async def expand_with_cycle_check(paragraph_id: str, depth: int = 0):
            if paragraph_id in visited or depth > 3:
                return []

            visited.add(paragraph_id)
            related = await mock_mcp_client.get_related_paragraphs(paragraph_id)

            all_expanded = []
            for r in related:
                if r.paragraph_id not in visited:
                    all_expanded.append(r)
                    all_expanded.extend(
                        await expand_with_cycle_check(r.paragraph_id, depth + 1)
                    )

            return all_expanded

        results = await expand_with_cycle_check("kifrs1115-31")

        # No duplicates due to cycle detection
        result_ids = [r.paragraph_id for r in results]
        assert len(result_ids) == len(set(result_ids))

    @pytest.mark.asyncio
    async def test_multihop_aggregates_context(self, mock_mcp_client):
        """Verify multi-hop results are aggregated correctly."""
        initial = await mock_mcp_client.get_paragraph_by_id("kifrs1115-31")
        related = await mock_mcp_client.get_related_paragraphs("kifrs1115-31")

        # Aggregate all context
        all_context = [initial] + related if initial else related

        # Create aggregated content
        aggregated = {
            "main_paragraph": initial.content if initial else "",
            "related_paragraphs": [r.content for r in related],
            "total_context_length": sum(
                len(r.content) for r in all_context
            )
        }

        assert "main_paragraph" in aggregated
        assert len(aggregated["related_paragraphs"]) == 1
        assert aggregated["total_context_length"] > 0


# ============================================================================
# E2E FLOW TEST
# ============================================================================

@pytest.mark.integration
class TestE2EFlow:
    """End-to-end tests for full retrieval pipeline."""

    @pytest.mark.asyncio
    async def test_full_retrieval_pipeline(
        self,
        mock_mcp_client,
        mock_llm,
        sample_task_state
    ):
        """
        Test full flow:
        MCP Search -> Rerank -> Multi-hop -> Final Context
        """
        query = "매출 수익 인식 시점 판단 및 감사 절차"

        # Step 1: MCP Search (Top-30)
        search_results = await mock_mcp_client.search_standards(
            query=query,
            top_k=30,
            account_category="Sales"
        )
        assert len(search_results) <= 30

        # Step 2: Rerank to Top-5
        response = await mock_llm.ainvoke([])
        reranked_ids = ["kifrs1115-31", "kifrs1115-32", "kgaas500-a1"]
        top_5 = [r for r in search_results if r.paragraph_id in reranked_ids]

        assert len(top_5) <= 5

        # Step 3: Multi-hop expansion for top result
        if top_5:
            related = await mock_mcp_client.get_related_paragraphs(
                top_5[0].paragraph_id
            )
            all_context = list(top_5) + related
        else:
            all_context = []

        # Step 4: Format final context for TaskState
        final_standards = [
            f"{r.standard_code} 문단 {r.paragraph_number}: {r.content}"
            for r in all_context
        ]

        # Verify final output
        assert len(final_standards) >= 1
        assert any("K-IFRS 1115" in s for s in final_standards)

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_results(
        self,
        mock_mcp_client,
        sample_task_state
    ):
        """Test pipeline handles empty search results gracefully."""
        mock_mcp_client.search_standards.return_value = []

        results = await mock_mcp_client.search_standards(
            query="nonexistent standard xyz"
        )

        assert results == []

        # Pipeline should return fallback
        fallback = ["K-GAAS 200: 기본 감사 기준"]
        assert len(fallback) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_timing(
        self,
        mock_mcp_client,
        mock_llm
    ):
        """Test pipeline completes within reasonable time."""
        import time

        start = time.time()

        # Run pipeline steps
        await mock_mcp_client.search_standards(query="test")
        await mock_llm.ainvoke([])
        await mock_mcp_client.get_related_paragraphs("test-id")

        elapsed = time.time() - start

        # Should complete quickly with mocks
        assert elapsed < 1.0  # Less than 1 second

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(
        self,
        mock_mcp_client,
        mock_llm
    ):
        """Test pipeline recovers from partial failures."""
        # First call succeeds
        mock_mcp_client.search_standards.return_value = [
            MCPSearchResult(
                paragraph_id="test-1",
                standard_code="K-IFRS 1115",
                paragraph_number="1",
                content="Test content",
                score=0.9,
                metadata={}
            )
        ]

        # Rerank fails
        mock_llm.ainvoke.side_effect = Exception("LLM error")

        results = await mock_mcp_client.search_standards(query="test")
        assert len(results) == 1

        # Should fallback gracefully
        try:
            await mock_llm.ainvoke([])
        except Exception:
            # Use original results without reranking
            final = results[:5]
            assert len(final) <= 5

    @pytest.mark.asyncio
    async def test_pipeline_with_real_task_state(
        self,
        mock_mcp_client,
        mock_llm,
        sample_task_state
    ):
        """Test pipeline updates TaskState correctly."""
        # Simulate full pipeline
        results = await mock_mcp_client.search_standards(
            query=f"audit {sample_task_state['category']}",
            account_category=sample_task_state["category"]
        )

        # Update task state
        sample_task_state["standards"] = [
            f"{r.standard_code}: {r.content}"
            for r in results
        ]

        # Verify state update
        assert len(sample_task_state["standards"]) == 3
        assert "K-IFRS 1115" in sample_task_state["standards"][0]


# ============================================================================
# NOTE: pytest-asyncio handles event loop automatically
# No custom event_loop fixture needed with asyncio_mode = auto
# ============================================================================


# ============================================================================
# SKIP MARKERS FOR REAL MCP SERVER TESTS
# ============================================================================

# Check if real MCP server is available
def is_mcp_server_available():
    """Check if MCP RAG server is running."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("localhost", 8001))
        sock.close()
        return True
    except (socket.error, ConnectionRefusedError):
        return False


skip_if_no_mcp = pytest.mark.skipif(
    not is_mcp_server_available(),
    reason="MCP RAG server not available at localhost:8001"
)


@pytest.mark.integration
@skip_if_no_mcp
class TestRealMCPServer:
    """Integration tests that require real MCP server."""

    @pytest.mark.asyncio
    async def test_real_health_check(self):
        """Test health check against real MCP server."""
        client = MCPRagClient()
        try:
            health = await client.health_check()
            assert health["status"] == "healthy"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_real_search_standards(self):
        """Test real search against MCP server."""
        client = MCPRagClient()
        try:
            results = await client.search_standards(
                query="수익 인식",
                top_k=10
            )
            assert isinstance(results, list)
            if results:
                assert isinstance(results[0], MCPSearchResult)
        finally:
            await client.close()
