"""
PWC Audit Guide RAG Service

This module provides Retrieval-Augmented Generation (RAG) capabilities for
searching PWC Audit Guide PDFs to generate task proposals based on EGA descriptions.

Key Features:
    - PDF text extraction and preprocessing
    - Text chunking with configurable overlap
    - Hybrid search (semantic embeddings + BM25 keyword matching)
    - EGA to audit procedure mapping with assertion classification

Key Classes:
    - AuditGuideRAG: Main RAG service for processing and searching audit guides
    - AuditProcedure: Represents a single audit procedure from PWC Guide
    - RAGSearchResult: Container for search results with metadata
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """
    Search mode options for RAG queries.

    Attributes:
        SEMANTIC: Vector similarity search using embeddings
        BM25: Traditional keyword-based BM25 ranking
        HYBRID: Combined semantic + BM25 with Reciprocal Rank Fusion
    """
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"


@dataclass
class AuditProcedure:
    """
    Represents a single audit procedure extracted from PWC Guide.

    Attributes:
        id: Unique identifier for this procedure
        section_code: Section code from the guide (e.g., "3.1", "4.2")
        section_title: Human-readable section title
        procedure_text: Full text of the audit procedure
        related_assertions: List of relevant assertions (existence, completeness, etc.)
        risk_indicators: List of identified risk indicators
        relevance_score: Search relevance score (0.0 to 1.0)
        source_page: Page number in source PDF (if available)
    """
    id: str
    section_code: str
    section_title: str
    procedure_text: str
    related_assertions: List[str]  # existence, completeness, valuation, rights, presentation
    risk_indicators: List[str]
    relevance_score: float = 0.0
    source_page: Optional[int] = None


@dataclass
class RAGSearchResult:
    """
    Container for RAG search results.

    Attributes:
        query: Original search query
        procedures: List of matching audit procedures
        total_found: Total number of matches before filtering
        search_mode: Mode used for this search
        search_time_ms: Search execution time in milliseconds
    """
    query: str
    procedures: List[AuditProcedure]
    total_found: int
    search_mode: SearchMode
    search_time_ms: float


@dataclass
class ChunkMetadata:
    """
    Metadata associated with a text chunk.

    Attributes:
        chunk_id: Unique identifier for this chunk
        document_id: ID of the source document
        section_code: Section code from the guide
        section_title: Human-readable section title
        page_number: Page number in source PDF
        chunk_index: Index of this chunk in the document
        total_chunks: Total number of chunks in the document
    """
    chunk_id: str
    document_id: str
    section_code: str
    section_title: str
    page_number: Optional[int]
    chunk_index: int
    total_chunks: int


@dataclass
class TextChunk:
    """
    A chunk of text from the audit guide with metadata.

    Attributes:
        text: The actual text content
        metadata: Associated chunk metadata
        embedding: Vector embedding (if generated)
    """
    text: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None


class AuditGuideRAG:
    """
    RAG service for PWC Audit Guide.

    Processes PDF documents and enables semantic search for audit procedures.
    Supports hybrid search combining vector similarity and BM25 keyword matching.

    Attributes:
        CHUNK_SIZE: Maximum characters per chunk (default 1000)
        CHUNK_OVERLAP: Overlap between consecutive chunks (default 200)
        TOP_K: Default number of results to return (default 10)
        MIN_RELEVANCE_SCORE: Minimum score threshold (default 0.5)

    Examples:
        >>> rag = AuditGuideRAG()
        >>> await rag.initialize()
        >>> result = await rag.search("은행 금융기관 잔액", mode=SearchMode.HYBRID)
        >>> for procedure in result.procedures:
        ...     print(f"{procedure.section_code}: {procedure.procedure_text[:100]}")
    """

    # Chunk settings
    CHUNK_SIZE = 1000  # characters
    CHUNK_OVERLAP = 200  # characters

    # Search settings
    TOP_K = 10
    MIN_RELEVANCE_SCORE = 0.5

    # Assertion keywords for classification (Korean and English)
    ASSERTION_KEYWORDS = {
        "existence": ["존재", "실재", "발생", "existence", "occurrence", "실물", "확인"],
        "completeness": ["완전", "누락", "completeness", "기록", "전체", "모든"],
        "valuation": ["평가", "측정", "가치", "valuation", "allocation", "금액", "계산"],
        "rights": ["권리", "의무", "소유", "rights", "obligations", "법적"],
        "presentation": ["표시", "공시", "분류", "presentation", "disclosure", "주석"],
    }

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        vector_store: Optional[Any] = None
    ):
        """
        Initialize RAG service.

        Args:
            embedding_model: Model for generating embeddings (e.g., OpenAI ada-002)
            vector_store: Vector database for storing/querying embeddings
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.chunks: List[TextChunk] = []
        self.bm25_index: Optional[Dict[str, Any]] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the RAG service with existing data.

        Loads chunks from vector store if available and builds BM25 index.
        Safe to call multiple times - subsequent calls are no-ops.
        """
        if self._initialized:
            return

        # Load existing chunks from vector store if available
        if self.vector_store:
            await self._load_from_vector_store()

        # Build BM25 index
        self._build_bm25_index()

        self._initialized = True
        logger.info(f"AuditGuideRAG initialized with {len(self.chunks)} chunks")

    async def ingest_pdf(
        self,
        pdf_path: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a PDF document into the RAG system.

        Extracts text from PDF, chunks it with overlap, generates embeddings,
        and stores in vector database.

        Args:
            pdf_path: Path to PDF file
            document_id: Optional ID for the document (auto-generated if not provided)

        Returns:
            Dict containing ingestion statistics:
                - document_id: ID assigned to document
                - pages_processed: Number of pages extracted
                - chunks_created: Number of chunks created
                - processing_time_ms: Processing time in milliseconds

        Examples:
            >>> result = await rag.ingest_pdf("/path/to/pwc_guide.pdf")
            >>> print(f"Created {result['chunks_created']} chunks")
        """
        import time
        start_time = time.time()

        if not document_id:
            document_id = hashlib.md5(pdf_path.encode()).hexdigest()[:12]

        # Extract text from PDF
        pages = await self._extract_pdf_text(pdf_path)

        # Chunk the text
        new_chunks = self._chunk_text(pages, document_id)

        # Generate embeddings
        if self.embedding_model:
            await self._generate_embeddings(new_chunks)

        # Store in vector database
        if self.vector_store:
            await self._store_chunks(new_chunks)

        # Add to local cache
        self.chunks.extend(new_chunks)

        # Rebuild BM25 index
        self._build_bm25_index()

        elapsed = (time.time() - start_time) * 1000

        return {
            "document_id": document_id,
            "pages_processed": len(pages),
            "chunks_created": len(new_chunks),
            "processing_time_ms": elapsed
        }

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> RAGSearchResult:
        """
        Search for relevant audit procedures.

        Performs search using specified mode and returns matching procedures
        sorted by relevance score.

        Args:
            query: Search query (e.g., EGA description)
            mode: Search mode (semantic, bm25, or hybrid)
            top_k: Number of results to return (default: TOP_K)
            min_score: Minimum relevance score threshold (default: MIN_RELEVANCE_SCORE)

        Returns:
            RAGSearchResult containing matching procedures and metadata

        Examples:
            >>> result = await rag.search("매출채권 확인", mode=SearchMode.HYBRID)
            >>> print(f"Found {len(result.procedures)} procedures in {result.search_time_ms}ms")
        """
        import time
        start_time = time.time()

        if not self._initialized:
            await self.initialize()

        top_k = top_k or self.TOP_K
        min_score = min_score or self.MIN_RELEVANCE_SCORE

        results: List[tuple] = []  # (chunk, score)

        if mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(query, top_k * 2)
        elif mode == SearchMode.BM25:
            results = self._bm25_search(query, top_k * 2)
        else:  # HYBRID
            semantic_results = await self._semantic_search(query, top_k)
            bm25_results = self._bm25_search(query, top_k)
            results = self._merge_results(semantic_results, bm25_results)

        # Convert chunks to procedures
        procedures = []
        seen_ids = set()

        for chunk, score in results:
            if score < min_score:
                continue
            if chunk.metadata.chunk_id in seen_ids:
                continue
            seen_ids.add(chunk.metadata.chunk_id)

            procedure = self._chunk_to_procedure(chunk, score)
            procedures.append(procedure)

            if len(procedures) >= top_k:
                break

        elapsed = (time.time() - start_time) * 1000

        return RAGSearchResult(
            query=query,
            procedures=procedures,
            total_found=len(results),
            search_mode=mode,
            search_time_ms=elapsed
        )

    async def search_for_ega(
        self,
        ega_name: str,
        ega_description: Optional[str] = None,
        context: Optional[Dict[str, str]] = None
    ) -> List[AuditProcedure]:
        """
        Search for audit procedures relevant to an EGA.

        Builds an enhanced query from EGA information and context,
        then performs hybrid search to find relevant procedures.

        Args:
            ega_name: Name of the EGA (e.g., "은행 등 금융기관과의 거래와 약정을 조회한다")
            ega_description: Optional detailed description
            context: Optional context dict with keys:
                - business_process: Business process name
                - fsli: Financial Statement Line Item

        Returns:
            List of relevant AuditProcedure objects sorted by relevance

        Examples:
            >>> procedures = await rag.search_for_ega(
            ...     ega_name="매출채권 잔액을 확인한다",
            ...     context={"business_process": "Revenue", "fsli": "AR"}
            ... )
        """
        # Build enhanced query
        query_parts = [ega_name]

        if ega_description:
            query_parts.append(ega_description)

        if context:
            if context.get("business_process"):
                query_parts.append(f"업무프로세스: {context['business_process']}")
            if context.get("fsli"):
                query_parts.append(f"FSLI: {context['fsli']}")

        query = " ".join(query_parts)

        # Perform hybrid search
        result = await self.search(query, mode=SearchMode.HYBRID)

        return result.procedures

    async def _extract_pdf_text(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF pages.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with page_number, text, and section keys

        Note:
            In production, use PyMuPDF (fitz) or similar library.
            Current implementation returns mock data for testing.
        """
        # In production, use PyMuPDF (fitz) or similar
        # For now, return mock structure
        logger.info(f"Extracting text from {pdf_path}")

        # Mock implementation - replace with actual PDF extraction
        return [
            {
                "page_number": 1,
                "text": "감사절차 예시 텍스트...",
                "section": "1.1 General Procedures"
            }
        ]

    def _chunk_text(
        self,
        pages: List[Dict[str, Any]],
        document_id: str
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Uses sliding window approach with configurable size and overlap.

        Args:
            pages: List of page dicts from _extract_pdf_text
            document_id: ID of the source document

        Returns:
            List of TextChunk objects with metadata
        """
        chunks = []
        chunk_index = 0

        for page in pages:
            text = page.get("text", "")
            page_num = page.get("page_number")
            section = page.get("section", "Unknown")

            # Split into chunks with overlap
            start = 0
            while start < len(text):
                end = start + self.CHUNK_SIZE
                chunk_text = text[start:end]

                # Create chunk metadata
                chunk_id = f"{document_id}_{chunk_index}"
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    section_code=section.split()[0] if section else "",
                    section_title=section,
                    page_number=page_num,
                    chunk_index=chunk_index,
                    total_chunks=-1  # Updated later
                )

                chunks.append(TextChunk(text=chunk_text, metadata=metadata))
                chunk_index += 1

                start += self.CHUNK_SIZE - self.CHUNK_OVERLAP

        # Update total_chunks
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)

        return chunks

    async def _generate_embeddings(self, chunks: List[TextChunk]) -> None:
        """
        Generate embeddings for chunks.

        Args:
            chunks: List of TextChunk objects to embed

        Note:
            In production, batch embedding calls for efficiency.
        """
        if not self.embedding_model:
            return

        for chunk in chunks:
            # In production, batch this for efficiency
            embedding = await self.embedding_model.embed(chunk.text)
            chunk.embedding = embedding

    async def _store_chunks(self, chunks: List[TextChunk]) -> None:
        """
        Store chunks in vector database.

        Args:
            chunks: List of TextChunk objects to store
        """
        if not self.vector_store:
            return

        for chunk in chunks:
            await self.vector_store.upsert(
                id=chunk.metadata.chunk_id,
                embedding=chunk.embedding,
                metadata=vars(chunk.metadata),
                text=chunk.text
            )

    async def _load_from_vector_store(self) -> None:
        """
        Load existing chunks from vector store.

        Note:
            Implementation depends on vector store API.
        """
        if not self.vector_store:
            return

        # Implementation depends on vector store API
        pass

    def _build_bm25_index(self) -> None:
        """
        Build BM25 index for keyword search.

        Creates a simple token-based index for BM25 scoring.

        Note:
            In production, use rank_bm25 library for proper BM25 implementation.
        """
        if not self.chunks:
            return

        # In production, use rank_bm25 library
        # For now, simple token-based index
        self.bm25_index = {
            "documents": [chunk.text for chunk in self.chunks],
            "chunks": self.chunks
        }

    async def _semantic_search(
        self,
        query: str,
        top_k: int
    ) -> List[tuple]:
        """
        Perform semantic search using embeddings.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples sorted by score descending
        """
        if not self.embedding_model or not self.vector_store:
            return []

        query_embedding = await self.embedding_model.embed(query)
        results = await self.vector_store.search(
            embedding=query_embedding,
            top_k=top_k
        )

        # Map back to chunks
        return [(chunk, score) for chunk, score in results]

    def _bm25_search(
        self,
        query: str,
        top_k: int
    ) -> List[tuple]:
        """
        Perform BM25 keyword search.

        Uses simple token overlap scoring (replace with proper BM25 in production).

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples sorted by score descending
        """
        if not self.bm25_index:
            return []

        # Simple keyword matching (replace with proper BM25 in production)
        query_tokens = set(query.lower().split())
        scores = []

        for i, doc in enumerate(self.bm25_index["documents"]):
            doc_tokens = set(doc.lower().split())
            overlap = len(query_tokens & doc_tokens)
            score = overlap / max(len(query_tokens), 1)
            scores.append((self.bm25_index["chunks"][i], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def _merge_results(
        self,
        semantic: List[tuple],
        bm25: List[tuple]
    ) -> List[tuple]:
        """
        Merge and re-rank results from semantic and BM25 search.

        Uses Reciprocal Rank Fusion (RRF) to combine rankings.

        Args:
            semantic: Results from semantic search
            bm25: Results from BM25 search

        Returns:
            Merged list of (chunk, score) tuples sorted by RRF score
        """
        # Reciprocal Rank Fusion (RRF)
        k = 60  # RRF constant
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, TextChunk] = {}

        for rank, (chunk, _) in enumerate(semantic):
            chunk_id = chunk.metadata.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
            chunk_map[chunk_id] = chunk

        for rank, (chunk, _) in enumerate(bm25):
            chunk_id = chunk.metadata.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
            chunk_map[chunk_id] = chunk

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [(chunk_map[id], scores[id]) for id in sorted_ids if id in chunk_map]

    def _chunk_to_procedure(
        self,
        chunk: TextChunk,
        score: float
    ) -> AuditProcedure:
        """
        Convert a text chunk to an audit procedure.

        Classifies assertions based on keyword matching.

        Args:
            chunk: TextChunk to convert
            score: Relevance score

        Returns:
            AuditProcedure with classified assertions
        """
        # Classify assertions based on keywords
        related_assertions = []
        text_lower = chunk.text.lower()

        for assertion, keywords in self.ASSERTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                related_assertions.append(assertion)

        return AuditProcedure(
            id=chunk.metadata.chunk_id,
            section_code=chunk.metadata.section_code,
            section_title=chunk.metadata.section_title,
            procedure_text=chunk.text,
            related_assertions=related_assertions,
            risk_indicators=[],  # Could extract from text
            relevance_score=score,
            source_page=chunk.metadata.page_number
        )


def create_audit_guide_rag(
    embedding_model: Optional[Any] = None,
    vector_store: Optional[Any] = None
) -> AuditGuideRAG:
    """
    Factory function to create an AuditGuideRAG instance.

    Args:
        embedding_model: Optional embedding model for semantic search
        vector_store: Optional vector database for persistent storage

    Returns:
        Configured AuditGuideRAG instance

    Examples:
        >>> rag = create_audit_guide_rag()  # Basic instance
        >>> rag = create_audit_guide_rag(
        ...     embedding_model=OpenAIEmbeddings(),
        ...     vector_store=PineconeStore()
        ... )
    """
    return AuditGuideRAG(
        embedding_model=embedding_model,
        vector_store=vector_store
    )
