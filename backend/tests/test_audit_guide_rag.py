"""
Tests for PWC Audit Guide RAG Service

This module provides comprehensive unit tests for the AuditGuideRAG service,
covering initialization, search functionality, assertion classification,
chunking, and result merging.

Test Classes:
    - TestAuditGuideRAG: Core RAG functionality tests
    - TestCreateAuditGuideRAG: Factory function tests
    - TestPDFIngestion: PDF ingestion workflow tests
    - TestChunkMetadata: Metadata handling tests
    - TestAssertionClassification: Assertion keyword detection tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.audit_guide_rag import (
    AuditGuideRAG,
    AuditProcedure,
    RAGSearchResult,
    SearchMode,
    TextChunk,
    ChunkMetadata,
    create_audit_guide_rag
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def rag_service():
    """Create RAG service without external dependencies."""
    return AuditGuideRAG()


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing."""
    return [
        TextChunk(
            text="은행조회서를 발송하여 금융기관 잔액을 확인한다. 존재성 테스트 절차이다.",
            metadata=ChunkMetadata(
                chunk_id="doc1_0",
                document_id="doc1",
                section_code="3.1",
                section_title="Bank Confirmations",
                page_number=15,
                chunk_index=0,
                total_chunks=10
            )
        ),
        TextChunk(
            text="매출채권 잔액조정표를 검토하여 완전성을 확인한다. 누락된 항목이 없는지 검토.",
            metadata=ChunkMetadata(
                chunk_id="doc1_1",
                document_id="doc1",
                section_code="3.2",
                section_title="AR Reconciliation",
                page_number=20,
                chunk_index=1,
                total_chunks=10
            )
        ),
        TextChunk(
            text="재고자산 실사를 수행하여 실재성을 확인한다. 표본추출 방법을 적용한다.",
            metadata=ChunkMetadata(
                chunk_id="doc1_2",
                document_id="doc1",
                section_code="4.1",
                section_title="Inventory Count",
                page_number=30,
                chunk_index=2,
                total_chunks=10
            )
        ),
    ]


@pytest.fixture
def chunk_with_valuation():
    """Chunk with valuation-related keywords."""
    return TextChunk(
        text="재고자산의 평가를 검토하여 측정의 적정성을 확인한다. 가치평가 모델 적용.",
        metadata=ChunkMetadata(
            chunk_id="doc2_0",
            document_id="doc2",
            section_code="5.1",
            section_title="Valuation Testing",
            page_number=45,
            chunk_index=0,
            total_chunks=5
        )
    )


@pytest.fixture
def chunk_with_rights():
    """Chunk with rights/obligations keywords."""
    return TextChunk(
        text="자산에 대한 권리와 의무를 확인한다. 소유권 증빙을 검토하고 법적 제한 여부 확인.",
        metadata=ChunkMetadata(
            chunk_id="doc3_0",
            document_id="doc3",
            section_code="6.1",
            section_title="Rights and Obligations",
            page_number=60,
            chunk_index=0,
            total_chunks=3
        )
    )


@pytest.fixture
def chunk_with_presentation():
    """Chunk with presentation/disclosure keywords."""
    return TextChunk(
        text="재무제표 표시와 공시가 적절한지 검토한다. 주석 분류의 적정성 확인.",
        metadata=ChunkMetadata(
            chunk_id="doc4_0",
            document_id="doc4",
            section_code="7.1",
            section_title="Presentation and Disclosure",
            page_number=75,
            chunk_index=0,
            total_chunks=2
        )
    )


# ============================================================================
# AUDITGUIDERAG CORE TESTS
# ============================================================================

class TestAuditGuideRAG:
    """Tests for AuditGuideRAG class."""

    @pytest.mark.asyncio
    async def test_initialize(self, rag_service):
        """Should initialize without errors."""
        await rag_service.initialize()
        assert rag_service._initialized

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, rag_service):
        """Should be safe to call initialize multiple times."""
        await rag_service.initialize()
        await rag_service.initialize()
        await rag_service.initialize()
        assert rag_service._initialized

    @pytest.mark.asyncio
    async def test_search_bm25(self, rag_service, sample_chunks):
        """Should find relevant chunks via BM25 search."""
        # Add sample chunks
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search(
            "은행 금융기관 잔액",
            mode=SearchMode.BM25,
            min_score=0.1  # Lower threshold for BM25 simple scoring
        )

        assert isinstance(result, RAGSearchResult)
        assert result.search_mode == SearchMode.BM25
        assert len(result.procedures) > 0
        assert "은행" in result.procedures[0].procedure_text

    @pytest.mark.asyncio
    async def test_search_returns_procedures(self, rag_service, sample_chunks):
        """Should return AuditProcedure objects."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search("매출채권 잔액", mode=SearchMode.BM25)

        assert all(isinstance(p, AuditProcedure) for p in result.procedures)
        if result.procedures:
            procedure = result.procedures[0]
            assert procedure.id
            assert procedure.section_code
            assert procedure.procedure_text

    @pytest.mark.asyncio
    async def test_assertion_classification(self, rag_service, sample_chunks):
        """Should classify assertions based on keywords."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search("은행 존재성", mode=SearchMode.BM25)

        # Should find chunk with existence assertion
        procedures_with_existence = [
            p for p in result.procedures
            if "existence" in p.related_assertions
        ]
        assert len(procedures_with_existence) > 0

    @pytest.mark.asyncio
    async def test_search_for_ega(self, rag_service, sample_chunks):
        """Should search for EGA-specific procedures."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        procedures = await rag_service.search_for_ega(
            ega_name="은행 등 금융기관과의 거래와 약정을 조회한다",
            context={"business_process": "Revenue", "fsli": "AR"}
        )

        assert isinstance(procedures, list)
        assert all(isinstance(p, AuditProcedure) for p in procedures)

    @pytest.mark.asyncio
    async def test_search_for_ega_without_context(self, rag_service, sample_chunks):
        """Should search for EGA without context."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        procedures = await rag_service.search_for_ega(
            ega_name="매출채권 확인"
        )

        assert isinstance(procedures, list)

    @pytest.mark.asyncio
    async def test_search_for_ega_with_description(self, rag_service, sample_chunks):
        """Should include description in search query."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        procedures = await rag_service.search_for_ega(
            ega_name="은행조회",
            ega_description="금융기관에 조회서를 발송하여 잔액을 확인하는 절차"
        )

        assert isinstance(procedures, list)

    @pytest.mark.asyncio
    async def test_search_with_min_score(self, rag_service, sample_chunks):
        """Should filter results by minimum score."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search(
            "은행",
            mode=SearchMode.BM25,
            min_score=0.9  # High threshold
        )

        # All returned procedures should have high score
        for procedure in result.procedures:
            assert procedure.relevance_score >= 0.9

    @pytest.mark.asyncio
    async def test_search_with_custom_top_k(self, rag_service, sample_chunks):
        """Should respect top_k parameter."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search(
            "검토",
            mode=SearchMode.BM25,
            top_k=2,
            min_score=0.0
        )

        assert len(result.procedures) <= 2

    @pytest.mark.asyncio
    async def test_search_time_recorded(self, rag_service, sample_chunks):
        """Should record search time."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search("테스트", mode=SearchMode.BM25)

        assert result.search_time_ms > 0

    @pytest.mark.asyncio
    async def test_search_empty_query(self, rag_service, sample_chunks):
        """Should handle empty query gracefully."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search("", mode=SearchMode.BM25)

        assert isinstance(result, RAGSearchResult)
        assert result.query == ""

    @pytest.mark.asyncio
    async def test_search_no_results(self, rag_service, sample_chunks):
        """Should return empty list when no matches found."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        rag_service._initialized = True

        result = await rag_service.search(
            "xyznonexistent123",
            mode=SearchMode.BM25,
            min_score=0.5
        )

        assert len(result.procedures) == 0

    @pytest.mark.asyncio
    async def test_search_auto_initializes(self, rag_service, sample_chunks):
        """Should auto-initialize if not initialized."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()
        # Note: NOT setting _initialized = True

        result = await rag_service.search("은행", mode=SearchMode.BM25)

        assert rag_service._initialized
        assert isinstance(result, RAGSearchResult)


# ============================================================================
# CHUNKING TESTS
# ============================================================================

class TestChunking:
    """Tests for text chunking functionality."""

    def test_chunk_text(self, rag_service):
        """Should split text into overlapping chunks."""
        pages = [
            {
                "page_number": 1,
                "text": "A" * 2500,  # Long text
                "section": "1.1 Test"
            }
        ]

        chunks = rag_service._chunk_text(pages, "doc1")

        assert len(chunks) > 1  # Should split into multiple chunks
        assert all(len(c.text) <= rag_service.CHUNK_SIZE for c in chunks)

        # Check overlap exists
        if len(chunks) > 1:
            end_of_first = chunks[0].text[-rag_service.CHUNK_OVERLAP:]
            start_of_second = chunks[1].text[:rag_service.CHUNK_OVERLAP]
            assert end_of_first == start_of_second

    def test_chunk_text_short_content(self, rag_service):
        """Should create single chunk for short content."""
        pages = [
            {
                "page_number": 1,
                "text": "Short text",
                "section": "1.1 Test"
            }
        ]

        chunks = rag_service._chunk_text(pages, "doc1")

        assert len(chunks) == 1
        assert chunks[0].text == "Short text"

    def test_chunk_metadata_populated(self, rag_service):
        """Should populate chunk metadata correctly."""
        pages = [
            {
                "page_number": 5,
                "text": "Test content",
                "section": "2.1 Section Title"
            }
        ]

        chunks = rag_service._chunk_text(pages, "doc123")

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.metadata.document_id == "doc123"
        assert chunk.metadata.page_number == 5
        assert chunk.metadata.section_code == "2.1"
        assert chunk.metadata.section_title == "2.1 Section Title"
        assert chunk.metadata.chunk_index == 0
        assert chunk.metadata.total_chunks == 1

    def test_chunk_text_multiple_pages(self, rag_service):
        """Should handle multiple pages."""
        pages = [
            {"page_number": 1, "text": "Page 1 content", "section": "1.1"},
            {"page_number": 2, "text": "Page 2 content", "section": "1.2"},
        ]

        chunks = rag_service._chunk_text(pages, "doc1")

        assert len(chunks) == 2
        assert chunks[0].metadata.page_number == 1
        assert chunks[1].metadata.page_number == 2

    def test_chunk_text_empty_section(self, rag_service):
        """Should handle empty section gracefully."""
        pages = [
            {"page_number": 1, "text": "Content", "section": ""}
        ]

        chunks = rag_service._chunk_text(pages, "doc1")

        assert chunks[0].metadata.section_code == ""


# ============================================================================
# CHUNK TO PROCEDURE CONVERSION TESTS
# ============================================================================

class TestChunkToProcedure:
    """Tests for chunk to procedure conversion."""

    def test_chunk_to_procedure(self, rag_service, sample_chunks):
        """Should convert chunk to procedure with assertions."""
        chunk = sample_chunks[0]  # Has "존재" keyword

        procedure = rag_service._chunk_to_procedure(chunk, 0.85)

        assert isinstance(procedure, AuditProcedure)
        assert procedure.relevance_score == 0.85
        assert procedure.section_code == "3.1"
        assert "existence" in procedure.related_assertions

    def test_chunk_to_procedure_completeness(
        self, rag_service, sample_chunks
    ):
        """Should detect completeness assertion."""
        chunk = sample_chunks[1]  # Has "완전성", "누락"

        procedure = rag_service._chunk_to_procedure(chunk, 0.75)

        assert "completeness" in procedure.related_assertions

    def test_chunk_to_procedure_valuation(
        self, rag_service, chunk_with_valuation
    ):
        """Should detect valuation assertion."""
        procedure = rag_service._chunk_to_procedure(chunk_with_valuation, 0.8)

        assert "valuation" in procedure.related_assertions

    def test_chunk_to_procedure_rights(
        self, rag_service, chunk_with_rights
    ):
        """Should detect rights/obligations assertion."""
        procedure = rag_service._chunk_to_procedure(chunk_with_rights, 0.8)

        assert "rights" in procedure.related_assertions

    def test_chunk_to_procedure_presentation(
        self, rag_service, chunk_with_presentation
    ):
        """Should detect presentation/disclosure assertion."""
        procedure = rag_service._chunk_to_procedure(chunk_with_presentation, 0.8)

        assert "presentation" in procedure.related_assertions

    def test_chunk_to_procedure_no_assertions(self, rag_service):
        """Should handle chunk with no assertion keywords."""
        chunk = TextChunk(
            text="일반적인 감사 절차를 수행한다.",
            metadata=ChunkMetadata(
                chunk_id="test_0",
                document_id="test",
                section_code="1.0",
                section_title="General",
                page_number=1,
                chunk_index=0,
                total_chunks=1
            )
        )

        procedure = rag_service._chunk_to_procedure(chunk, 0.5)

        assert procedure.related_assertions == []


# ============================================================================
# RESULT MERGING TESTS
# ============================================================================

class TestResultMerging:
    """Tests for result merging (RRF)."""

    def test_merge_results_rrf(self, rag_service, sample_chunks):
        """Should merge results using Reciprocal Rank Fusion."""
        semantic = [(sample_chunks[0], 0.9), (sample_chunks[1], 0.8)]
        bm25 = [(sample_chunks[1], 0.85), (sample_chunks[2], 0.7)]

        merged = rag_service._merge_results(semantic, bm25)

        # chunk[1] appears in both, should rank higher
        chunk_ids = [c.metadata.chunk_id for c, _ in merged]
        assert sample_chunks[1].metadata.chunk_id in chunk_ids

    def test_merge_results_preserves_all(self, rag_service, sample_chunks):
        """Should include all unique chunks."""
        semantic = [(sample_chunks[0], 0.9)]
        bm25 = [(sample_chunks[2], 0.7)]

        merged = rag_service._merge_results(semantic, bm25)

        assert len(merged) == 2

    def test_merge_results_empty_semantic(self, rag_service, sample_chunks):
        """Should handle empty semantic results."""
        semantic = []
        bm25 = [(sample_chunks[0], 0.8)]

        merged = rag_service._merge_results(semantic, bm25)

        assert len(merged) == 1

    def test_merge_results_empty_bm25(self, rag_service, sample_chunks):
        """Should handle empty BM25 results."""
        semantic = [(sample_chunks[0], 0.8)]
        bm25 = []

        merged = rag_service._merge_results(semantic, bm25)

        assert len(merged) == 1

    def test_merge_results_both_empty(self, rag_service):
        """Should handle both empty results."""
        merged = rag_service._merge_results([], [])

        assert merged == []


# ============================================================================
# BM25 SEARCH TESTS
# ============================================================================

class TestBM25Search:
    """Tests for BM25 search functionality."""

    def test_bm25_search_basic(self, rag_service, sample_chunks):
        """Should find matching chunks by keywords."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()

        results = rag_service._bm25_search("은행 금융기관", top_k=5)

        assert len(results) > 0
        # First result should contain query terms
        assert "은행" in results[0][0].text.lower() or "금융" in results[0][0].text.lower()

    def test_bm25_search_no_index(self, rag_service):
        """Should return empty list when no index."""
        results = rag_service._bm25_search("test", top_k=5)

        assert results == []

    def test_bm25_search_respects_top_k(self, rag_service, sample_chunks):
        """Should respect top_k limit."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()

        results = rag_service._bm25_search("확인", top_k=2)

        assert len(results) <= 2

    def test_bm25_scores_sorted(self, rag_service, sample_chunks):
        """Should return results sorted by score descending."""
        rag_service.chunks = sample_chunks
        rag_service._build_bm25_index()

        results = rag_service._bm25_search("확인", top_k=10)

        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================

class TestCreateAuditGuideRAG:
    """Tests for factory function."""

    def test_create_without_dependencies(self):
        """Should create RAG without external dependencies."""
        rag = create_audit_guide_rag()

        assert isinstance(rag, AuditGuideRAG)
        assert rag.embedding_model is None
        assert rag.vector_store is None

    def test_create_with_dependencies(self):
        """Should create RAG with dependencies."""
        mock_embedding = MagicMock()
        mock_store = MagicMock()

        rag = create_audit_guide_rag(
            embedding_model=mock_embedding,
            vector_store=mock_store
        )

        assert rag.embedding_model is mock_embedding
        assert rag.vector_store is mock_store


# ============================================================================
# PDF INGESTION TESTS
# ============================================================================

class TestPDFIngestion:
    """Tests for PDF ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_returns_stats(self, rag_service):
        """Should return ingestion statistics."""
        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test content", "section": "1.1"}]
        ):
            result = await rag_service.ingest_pdf("/path/to/test.pdf")

        assert "document_id" in result
        assert "pages_processed" in result
        assert "chunks_created" in result
        assert "processing_time_ms" in result
        assert result["pages_processed"] == 1

    @pytest.mark.asyncio
    async def test_ingest_with_custom_document_id(self, rag_service):
        """Should use provided document ID."""
        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test", "section": "1.1"}]
        ):
            result = await rag_service.ingest_pdf(
                "/path/to/test.pdf",
                document_id="custom-id-123"
            )

        assert result["document_id"] == "custom-id-123"

    @pytest.mark.asyncio
    async def test_ingest_generates_document_id(self, rag_service):
        """Should auto-generate document ID from path."""
        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test", "section": "1.1"}]
        ):
            result = await rag_service.ingest_pdf("/path/to/test.pdf")

        assert result["document_id"]
        assert len(result["document_id"]) == 12

    @pytest.mark.asyncio
    async def test_ingest_adds_chunks_to_cache(self, rag_service):
        """Should add chunks to local cache."""
        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test content", "section": "1.1"}]
        ):
            await rag_service.ingest_pdf("/path/to/test.pdf")

        assert len(rag_service.chunks) == 1

    @pytest.mark.asyncio
    async def test_ingest_rebuilds_bm25_index(self, rag_service):
        """Should rebuild BM25 index after ingestion."""
        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test content", "section": "1.1"}]
        ):
            await rag_service.ingest_pdf("/path/to/test.pdf")

        assert rag_service.bm25_index is not None

    @pytest.mark.asyncio
    async def test_ingest_with_embedding_model(self, rag_service):
        """Should generate embeddings when model provided."""
        mock_embedding = AsyncMock()
        mock_embedding.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        rag_service.embedding_model = mock_embedding

        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test", "section": "1.1"}]
        ):
            await rag_service.ingest_pdf("/path/to/test.pdf")

        mock_embedding.embed.assert_called()

    @pytest.mark.asyncio
    async def test_ingest_with_vector_store(self, rag_service):
        """Should store chunks when vector store provided."""
        mock_store = AsyncMock()
        mock_store.upsert = AsyncMock()
        rag_service.vector_store = mock_store

        with patch.object(
            rag_service,
            '_extract_pdf_text',
            new_callable=AsyncMock,
            return_value=[{"page_number": 1, "text": "Test", "section": "1.1"}]
        ):
            await rag_service.ingest_pdf("/path/to/test.pdf")

        mock_store.upsert.assert_called()


# ============================================================================
# ASSERTION KEYWORD TESTS
# ============================================================================

class TestAssertionClassification:
    """Tests for assertion keyword classification."""

    def test_assertion_keywords_structure(self, rag_service):
        """Should have all five assertion types."""
        expected_assertions = {
            "existence", "completeness", "valuation", "rights", "presentation"
        }

        assert set(rag_service.ASSERTION_KEYWORDS.keys()) == expected_assertions

    def test_each_assertion_has_keywords(self, rag_service):
        """Each assertion should have at least one keyword."""
        for assertion, keywords in rag_service.ASSERTION_KEYWORDS.items():
            assert len(keywords) > 0, f"{assertion} has no keywords"

    def test_assertion_keywords_are_lowercase_friendly(self, rag_service):
        """Keywords should work with lowercase matching."""
        # The search uses .lower() so keywords don't need to be lowercase
        # but they should be matchable
        for assertion, keywords in rag_service.ASSERTION_KEYWORDS.items():
            for keyword in keywords:
                assert isinstance(keyword, str)


# ============================================================================
# SEARCH MODE ENUM TESTS
# ============================================================================

class TestSearchMode:
    """Tests for SearchMode enum."""

    def test_search_mode_values(self):
        """Should have correct enum values."""
        assert SearchMode.SEMANTIC.value == "semantic"
        assert SearchMode.BM25.value == "bm25"
        assert SearchMode.HYBRID.value == "hybrid"

    def test_search_mode_count(self):
        """Should have exactly three modes."""
        assert len(SearchMode) == 3


# ============================================================================
# RAG SEARCH RESULT TESTS
# ============================================================================

class TestRAGSearchResult:
    """Tests for RAGSearchResult dataclass."""

    def test_rag_search_result_creation(self):
        """Should create result with all fields."""
        result = RAGSearchResult(
            query="test query",
            procedures=[],
            total_found=0,
            search_mode=SearchMode.HYBRID,
            search_time_ms=15.5
        )

        assert result.query == "test query"
        assert result.procedures == []
        assert result.total_found == 0
        assert result.search_mode == SearchMode.HYBRID
        assert result.search_time_ms == 15.5


# ============================================================================
# AUDIT PROCEDURE TESTS
# ============================================================================

class TestAuditProcedure:
    """Tests for AuditProcedure dataclass."""

    def test_audit_procedure_creation(self):
        """Should create procedure with all fields."""
        procedure = AuditProcedure(
            id="proc-001",
            section_code="3.1",
            section_title="Bank Confirmations",
            procedure_text="Test procedure text",
            related_assertions=["existence", "completeness"],
            risk_indicators=["High fraud risk"],
            relevance_score=0.95,
            source_page=15
        )

        assert procedure.id == "proc-001"
        assert procedure.section_code == "3.1"
        assert procedure.section_title == "Bank Confirmations"
        assert procedure.procedure_text == "Test procedure text"
        assert procedure.related_assertions == ["existence", "completeness"]
        assert procedure.risk_indicators == ["High fraud risk"]
        assert procedure.relevance_score == 0.95
        assert procedure.source_page == 15

    def test_audit_procedure_defaults(self):
        """Should have correct default values."""
        procedure = AuditProcedure(
            id="proc-001",
            section_code="3.1",
            section_title="Test",
            procedure_text="Text",
            related_assertions=[],
            risk_indicators=[]
        )

        assert procedure.relevance_score == 0.0
        assert procedure.source_page is None
