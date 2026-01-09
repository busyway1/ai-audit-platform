"""MCP RAG Server Client for K-IFRS Standards Retrieval

This module provides an async HTTP client for the MCP RAG server that enables
hybrid search (BM25 + Vector) with Reciprocal Rank Fusion for K-IFRS standards.

The MCP RAG server provides two primary tools:
1. search_standards: Hybrid search for finding relevant K-IFRS paragraphs
2. get_paragraph_by_id: Direct lookup for Multi-hop retrieval workflows

Key Features:
    - Async HTTP client using httpx for non-blocking I/O
    - Configurable retry logic with exponential backoff
    - Connection health checks
    - Graceful error handling with structured error responses
    - Async context manager support for proper resource cleanup

Usage:
    ```python
    from src.services.mcp_client import MCPRagClient

    # Using context manager (recommended)
    async with MCPRagClient() as client:
        results = await client.search_standards(
            query_text="수익인식 기준",
            top_k=30,
            mode="hybrid"
        )

    # Or manual lifecycle
    client = MCPRagClient()
    try:
        paragraph = await client.get_paragraph_by_id(
            standard_id="K-IFRS1115",
            paragraph_no="35"
        )
    finally:
        await client.close()
    ```

Reference:
    - MCP RAG Server: audit-mcp-suite/servers/mcp-rag/main.py
    - Tools: search_standards, get_paragraph_by_id, get_standard_context
"""

import asyncio
import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

import httpx

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MCPClientConfig:
    """Configuration for MCP RAG Client.

    Attributes:
        base_url: MCP RAG server base URL
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts for failed requests (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        retry_backoff: Exponential backoff multiplier (default: 2.0)
    """
    base_url: str = "http://localhost:8001"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0


class MCPRagClientError(Exception):
    """Base exception for MCP RAG client errors."""
    pass


class MCPConnectionError(MCPRagClientError):
    """Raised when connection to MCP server fails."""
    pass


class MCPToolExecutionError(MCPRagClientError):
    """Raised when MCP tool execution fails."""
    pass


class MCPRagClient:
    """MCP RAG Server Client for K-IFRS standards retrieval.

    This client provides access to the MCP RAG server's hybrid search capabilities,
    combining BM25 lexical search with vector semantic search using Reciprocal
    Rank Fusion (RRF) for optimal retrieval of K-IFRS accounting standards.

    The client is designed for use in the Standard_Retriever agent within the
    AI Audit platform's multi-agent architecture.

    Attributes:
        base_url: MCP RAG server base URL
        timeout: Request timeout in seconds
        config: Full client configuration (optional)

    Example:
        ```python
        # Simple initialization
        client = MCPRagClient()

        # With custom config
        config = MCPClientConfig(
            base_url="http://localhost:8001",
            timeout=60.0,
            max_retries=5
        )
        client = MCPRagClient(config=config)

        # Execute hybrid search
        result = await client.search_standards(
            query_text="매출채권 손상차손 인식",
            top_k=30,
            mode="hybrid",
            standard_filter="K-IFRS1109"
        )
        ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        config: Optional[MCPClientConfig] = None
    ):
        """Initialize MCP RAG client.

        Args:
            base_url: MCP RAG server URL. Defaults to MCP_RAG_SERVER_URL env var
                     or http://localhost:8001
            timeout: Request timeout in seconds (default: 30s)
            config: Optional MCPClientConfig for advanced settings.
                   If provided, base_url and timeout parameters are ignored.
        """
        if config:
            self.config = config
        else:
            resolved_url = base_url or os.getenv(
                "MCP_RAG_SERVER_URL",
                "http://localhost:8001"
            )
            self.config = MCPClientConfig(
                base_url=resolved_url.rstrip('/'),
                timeout=timeout
            )

        self.base_url = self.config.base_url
        self.timeout = self.config.timeout
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.health_endpoint = f"{self.base_url}/health"
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"MCPRagClient initialized with server: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            httpx.AsyncClient: Configured async HTTP client

        Note:
            The client is lazily initialized and reused for connection pooling.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"}
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection.

        Call this method when done using the client to release resources.

        Example:
            ```python
            client = MCPRagClient()
            try:
                results = await client.search_standards("query")
            finally:
                await client.close()
            ```
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MCPRagClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry logic.

        Args:
            method: HTTP method (POST, GET, etc.)
            endpoint: API endpoint path
            payload: Request payload (JSON body for POST, params for GET)

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            MCPConnectionError: If all retry attempts fail
            MCPToolExecutionError: If server returns error status
        """
        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "POST":
                    response = await client.post(endpoint, json=payload)
                elif method.upper() == "GET":
                    response = await client.get(endpoint, params=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                result = response.json()

                # Check for JSON-RPC error
                if "error" in result:
                    error_msg = result.get("error", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    raise MCPToolExecutionError(f"MCP tool error: {error_msg}")

                return result

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Connection failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Request timeout (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )
            except httpx.HTTPStatusError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise MCPToolExecutionError(
                        f"Client error {e.response.status_code}: {e.response.text}"
                    )
                last_error = e
                logger.warning(
                    f"Server error (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )
            except MCPToolExecutionError:
                # Don't retry on MCP tool errors
                raise

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        raise MCPConnectionError(
            f"Failed to connect to MCP server after {self.config.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    async def health_check(self) -> bool:
        """Check if MCP RAG server is available.

        Performs a lightweight health check to verify server connectivity.
        This is useful for:
        - Pre-flight checks before batch operations
        - Monitoring and alerting
        - Graceful degradation in case of server unavailability

        Returns:
            bool: True if server is healthy and responding, False otherwise

        Example:
            ```python
            client = MCPRagClient()

            if await client.health_check():
                print("MCP RAG server is available")
                results = await client.search_standards("query")
            else:
                print("MCP RAG server is unavailable - using fallback")
            ```
        """
        try:
            client = await self._get_client()
            response = await client.get(self.health_endpoint, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP health check failed: {e}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """Check MCP RAG server health (returns detailed status).

        Returns:
            Health status dict with server info and component status

        Raises:
            MCPRagClientError: If health check fails

        Example:
            ```python
            status = await client.check_health()
            print(f"Server status: {status.get('status')}")
            print(f"Components: {status.get('components')}")
            ```
        """
        try:
            client = await self._get_client()
            response = await client.get(
                self.health_endpoint,
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP RAG health check failed: {e}")
            raise MCPRagClientError(f"Health check failed: {e}") from e

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool via JSON-RPC protocol with retry logic.

        This method constructs a JSON-RPC 2.0 request and sends it to the
        MCP endpoint. It includes automatic retry with exponential backoff
        for transient failures.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments dict

        Returns:
            Tool result dict from the JSON-RPC response

        Raises:
            MCPConnectionError: If connection fails after retries
            MCPToolExecutionError: If tool execution fails
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        result = await self._execute_with_retry("POST", self.mcp_endpoint, request)
        return result.get("result", {})

    async def search_standards(
        self,
        query_text: str,
        top_k: int = 30,
        mode: str = "hybrid",
        standard_filter: Optional[str] = None,
        section_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search K-IFRS audit standards using hybrid search.

        This method implements the "Wide Recall -> High Precision" strategy:
        - Returns Top-K candidates (default: 30) for LLM reranking
        - Uses RRF (Reciprocal Rank Fusion) for combining BM25 and vector scores

        Args:
            query_text: Search query in Korean or English
                       (e.g., "리스 식별", "수익인식 5단계")
            top_k: Maximum results to return (default: 30 for Wide Recall)
            mode: Search mode - "hybrid", "vector", "bm25", or "auto"
                 (default: "hybrid" for best results)
            standard_filter: Filter by specific standard (e.g., "K-IFRS 1115")
            section_filter: Filter by section type - "main", "appendix", "example"

        Returns:
            Dict with search results:
            {
                "status": "success" | "error",
                "data": {
                    "query": str,
                    "mode": str,
                    "results_count": int,
                    "results": [
                        {
                            "id": str,
                            "content": str,
                            "paragraph_no": str,
                            "standard_id": str,
                            "hierarchy_path": str,
                            "topic": str,
                            "title": str,
                            "section_type": str,
                            "scores": {"bm25": float, "vector": float, "combined": float},
                            "rank": int,
                            "related_paragraphs": [str]
                        }
                    ],
                    "metadata": {
                        "bm25_candidates": int,
                        "vector_candidates": int,
                        "bm25_weight": float,
                        "vector_weight": float,
                        "fusion_method": str,
                        "duration_ms": float
                    }
                }
            }

        Raises:
            MCPRagClientError: If search fails

        Example:
            ```python
            result = await client.search_standards(
                query_text="매출 수익인식 기준",
                top_k=30,
                mode="hybrid"
            )
            for r in result["data"]["results"][:10]:
                print(f"{r['standard_id']} {r['paragraph_no']}: {r['content'][:100]}...")
            ```
        """
        logger.info(
            f"search_standards: query='{query_text}', top_k={top_k}, "
            f"mode={mode}, standard={standard_filter}"
        )

        arguments = {
            "query_text": query_text,
            "top_k": top_k,
            "mode": mode
        }

        if standard_filter:
            arguments["standard_filter"] = standard_filter

        if section_filter:
            arguments["section_filter"] = section_filter

        return await self._call_tool("search_standards", arguments)

    async def get_paragraph_by_id(
        self,
        standard_id: str,
        paragraph_no: str,
        include_related: bool = True
    ) -> Dict[str, Any]:
        """
        Direct lookup of a specific paragraph for Multi-hop retrieval.

        Use this method to follow related_paragraphs references for
        comprehensive context.

        Args:
            standard_id: Standard identifier (e.g., "K-IFRS 1115")
            paragraph_no: Paragraph number (e.g., "B34", "9", "IE5")
            include_related: Include preview of related paragraphs (default: True)

        Returns:
            Dict with paragraph data:
            {
                "status": "success" | "not_found" | "error",
                "data": {
                    "id": str,
                    "content": str,
                    "paragraph_no": str,
                    "standard_id": str,
                    "hierarchy_path": str,
                    "topic": str,
                    "title": str,
                    "section_type": str,
                    "related_paragraphs": [str]  # if include_related=True
                }
            }

        Raises:
            MCPRagClientError: If lookup fails
        """
        logger.info(f"get_paragraph_by_id: {standard_id}.{paragraph_no}")

        arguments = {
            "standard_id": standard_id,
            "paragraph_no": paragraph_no,
            "include_related": include_related
        }

        return await self._call_tool("get_paragraph_by_id", arguments)

    async def get_standard_context(
        self,
        hierarchy_path: str,
        include_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve hierarchical context for an audit standard (legacy support).

        Args:
            hierarchy_path: Hierarchical path (e.g., "K-IFRS.1115.9")
            include_parents: Include parent sections (default: True)

        Returns:
            Dict with hierarchical context data

        Raises:
            MCPRagClientError: If context retrieval fails
        """
        logger.info(f"get_standard_context: path='{hierarchy_path}'")

        arguments = {
            "hierarchy_path": hierarchy_path,
            "include_parents": include_parents
        }

        return await self._call_tool("get_standard_context", arguments)


# ============================================================================
# MCP EXCEL PROCESSOR CLIENT
# ============================================================================

@dataclass
class MCPExcelClientConfig:
    """Configuration for MCP Excel Processor Client.

    Attributes:
        base_url: MCP Excel Processor server base URL
        timeout: Request timeout in seconds (default: 60 for large files)
        max_retries: Maximum retry attempts for failed requests (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        retry_backoff: Exponential backoff multiplier (default: 2.0)
    """
    base_url: str = "http://localhost:8003"
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0


class MCPExcelClientError(Exception):
    """Base exception for MCP Excel client errors."""
    pass


class MCPExcelConnectionError(MCPExcelClientError):
    """Raised when connection to MCP Excel server fails."""
    pass


class MCPExcelParseError(MCPExcelClientError):
    """Raised when Excel parsing fails."""
    pass


class MCPExcelClient:
    """MCP Excel Processor Client for financial data extraction.

    This client provides access to the MCP Excel Processor server for:
    - Parsing Excel files (trial balance, financial statements)
    - Extracting transaction data with validation
    - Detecting anomalies in financial data
    - Supporting multiple Excel formats (.xlsx, .xls)

    The client is designed for use in the Excel_Parser Staff agent within
    the AI Audit platform's multi-agent architecture.

    Example:
        ```python
        async with MCPExcelClient() as client:
            result = await client.parse_excel(
                file_path="/path/to/trial_balance.xlsx",
                sheet_name="TB",
                category="Sales"
            )
        ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        config: Optional[MCPExcelClientConfig] = None
    ):
        """Initialize MCP Excel client.

        Args:
            base_url: MCP Excel server URL. Defaults to MCP_EXCEL_SERVER_URL env var
                     or http://localhost:8003
            timeout: Request timeout in seconds (default: 60s for large files)
            config: Optional MCPExcelClientConfig for advanced settings.
        """
        if config:
            self.config = config
        else:
            resolved_url = base_url or os.getenv(
                "MCP_EXCEL_SERVER_URL",
                "http://localhost:8003"
            )
            self.config = MCPExcelClientConfig(
                base_url=resolved_url.rstrip('/'),
                timeout=timeout
            )

        self.base_url = self.config.base_url
        self.timeout = self.config.timeout
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.health_endpoint = f"{self.base_url}/health"
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"MCPExcelClient initialized with server: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"}
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MCPExcelClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry logic."""
        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "POST":
                    response = await client.post(endpoint, json=payload)
                elif method.upper() == "GET":
                    response = await client.get(endpoint, params=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    error_msg = result.get("error", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    raise MCPExcelParseError(f"MCP Excel error: {error_msg}")

                return result

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Excel server connection failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Excel server timeout (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    raise MCPExcelParseError(
                        f"Client error {e.response.status_code}: {e.response.text}"
                    )
                last_error = e
            except MCPExcelParseError:
                raise

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                await asyncio.sleep(delay)

        raise MCPExcelConnectionError(
            f"Failed to connect to MCP Excel server after {self.config.max_retries} "
            f"attempts. Last error: {last_error}"
        )

    async def health_check(self) -> bool:
        """Check if MCP Excel server is available."""
        try:
            client = await self._get_client()
            response = await client.get(self.health_endpoint, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP Excel health check failed: {e}")
            return False

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool via JSON-RPC protocol."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        result = await self._execute_with_retry("POST", self.mcp_endpoint, request)
        return result.get("result", {})

    async def parse_excel(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        sheet_name: Optional[str] = None,
        category: str = "General",
        validate_data: bool = True,
        detect_anomalies: bool = True
    ) -> Dict[str, Any]:
        """
        Parse Excel file and extract financial data.

        Args:
            file_path: Local path to Excel file
            file_url: URL to download Excel file (e.g., Supabase Storage URL)
            sheet_name: Specific sheet to parse (default: first sheet)
            category: Account category for context (Sales, Inventory, AR, etc.)
            validate_data: Perform data validation checks (default: True)
            detect_anomalies: Run anomaly detection (default: True)

        Returns:
            Dict with parsed data:
            {
                "status": "success" | "error",
                "data": {
                    "category": str,
                    "total_amount": float,
                    "transaction_count": int,
                    "period": str,
                    "transactions": [
                        {
                            "date": str,
                            "amount": float,
                            "description": str,
                            "account_code": str,
                            "reference": str
                        }
                    ],
                    "summary": {
                        "min_amount": float,
                        "max_amount": float,
                        "avg_amount": float,
                        "std_dev": float
                    },
                    "data_quality": "GOOD" | "WARNING" | "POOR",
                    "anomalies": [
                        {
                            "type": str,
                            "description": str,
                            "row": int,
                            "severity": str
                        }
                    ],
                    "parsed_at": str
                },
                "metadata": {
                    "file_name": str,
                    "sheet_name": str,
                    "row_count": int,
                    "column_count": int,
                    "processing_time_ms": float
                }
            }

        Raises:
            MCPExcelParseError: If parsing fails
            MCPExcelConnectionError: If server is unavailable
        """
        if not file_path and not file_url:
            raise ValueError("Either file_path or file_url must be provided")

        logger.info(
            f"parse_excel: file={file_path or file_url}, "
            f"category={category}, sheet={sheet_name}"
        )

        arguments = {
            "category": category,
            "validate_data": validate_data,
            "detect_anomalies": detect_anomalies
        }

        if file_path:
            arguments["file_path"] = file_path
        if file_url:
            arguments["file_url"] = file_url
        if sheet_name:
            arguments["sheet_name"] = sheet_name

        return await self._call_tool("parse_excel", arguments)

    async def extract_trial_balance(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        fiscal_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract trial balance data from Excel file.

        Specialized method for trial balance extraction with:
        - Account code recognition
        - Debit/credit validation
        - Balance reconciliation

        Args:
            file_path: Local path to Excel file
            file_url: URL to download Excel file
            fiscal_year: Fiscal year for context

        Returns:
            Dict with trial balance data
        """
        if not file_path and not file_url:
            raise ValueError("Either file_path or file_url must be provided")

        logger.info(f"extract_trial_balance: file={file_path or file_url}")

        arguments = {}
        if file_path:
            arguments["file_path"] = file_path
        if file_url:
            arguments["file_url"] = file_url
        if fiscal_year:
            arguments["fiscal_year"] = fiscal_year

        return await self._call_tool("extract_trial_balance", arguments)

    async def validate_financial_data(
        self,
        data: Dict[str, Any],
        validation_rules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate financial data against audit rules.

        Args:
            data: Financial data dictionary to validate
            validation_rules: Specific rules to apply (default: all)

        Returns:
            Dict with validation results
        """
        arguments = {
            "data": data
        }
        if validation_rules:
            arguments["validation_rules"] = validation_rules

        return await self._call_tool("validate_financial_data", arguments)


# ============================================================================
# MCP DOCUMENT GENERATOR CLIENT
# ============================================================================

@dataclass
class MCPDocumentClientConfig:
    """Configuration for MCP Document Generator Client."""
    base_url: str = "http://localhost:8004"
    timeout: float = 120.0  # Longer timeout for document generation
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0


class MCPDocumentClientError(Exception):
    """Base exception for MCP Document client errors."""
    pass


class MCPDocumentConnectionError(MCPDocumentClientError):
    """Raised when connection to MCP Document server fails."""
    pass


class MCPDocumentGenerationError(MCPDocumentClientError):
    """Raised when document generation fails."""
    pass


class MCPDocumentClient:
    """MCP Document Generator Client for workpaper generation.

    This client provides access to the MCP Document Generator server for:
    - Generating audit workpapers (Word/PDF)
    - Creating structured reports
    - Applying audit document templates

    Example:
        ```python
        async with MCPDocumentClient() as client:
            result = await client.generate_workpaper(
                content=workpaper_draft,
                template="audit_workpaper",
                output_format="docx"
            )
        ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        config: Optional[MCPDocumentClientConfig] = None
    ):
        """Initialize MCP Document client."""
        if config:
            self.config = config
        else:
            resolved_url = base_url or os.getenv(
                "MCP_DOCUMENT_SERVER_URL",
                "http://localhost:8004"
            )
            self.config = MCPDocumentClientConfig(
                base_url=resolved_url.rstrip('/'),
                timeout=timeout
            )

        self.base_url = self.config.base_url
        self.timeout = self.config.timeout
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.health_endpoint = f"{self.base_url}/health"
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"MCPDocumentClient initialized with server: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"}
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MCPDocumentClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry logic."""
        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "POST":
                    response = await client.post(endpoint, json=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    error_msg = result.get("error", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    raise MCPDocumentGenerationError(f"MCP Document error: {error_msg}")

                return result

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Document server connection failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Document server timeout (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    raise MCPDocumentGenerationError(
                        f"Client error {e.response.status_code}: {e.response.text}"
                    )
                last_error = e
            except MCPDocumentGenerationError:
                raise

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                await asyncio.sleep(delay)

        raise MCPDocumentConnectionError(
            f"Failed to connect to MCP Document server after {self.config.max_retries} "
            f"attempts. Last error: {last_error}"
        )

    async def health_check(self) -> bool:
        """Check if MCP Document server is available."""
        try:
            client = await self._get_client()
            response = await client.get(self.health_endpoint, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP Document health check failed: {e}")
            return False

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool via JSON-RPC protocol."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        result = await self._execute_with_retry("POST", self.mcp_endpoint, request)
        return result.get("result", {})

    async def generate_workpaper(
        self,
        content: str,
        template: str = "audit_workpaper",
        output_format: str = "docx",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate audit workpaper document.

        Args:
            content: Markdown content for the workpaper
            template: Template name (audit_workpaper, summary_report, etc.)
            output_format: Output format (docx, pdf, xlsx)
            metadata: Document metadata (task_id, client, fiscal_year, etc.)

        Returns:
            Dict with generation results:
            {
                "status": "success" | "error",
                "data": {
                    "file_url": str,  # URL to download generated file
                    "file_name": str,
                    "file_size": int,
                    "format": str,
                    "generated_at": str
                }
            }
        """
        logger.info(f"generate_workpaper: template={template}, format={output_format}")

        arguments = {
            "content": content,
            "template": template,
            "output_format": output_format
        }
        if metadata:
            arguments["metadata"] = metadata

        return await self._call_tool("generate_workpaper", arguments)

    async def create_audit_report(
        self,
        sections: List[Dict[str, Any]],
        report_type: str = "standard",
        output_format: str = "docx"
    ) -> Dict[str, Any]:
        """
        Create structured audit report from sections.

        Args:
            sections: List of section dictionaries
            report_type: Report type (standard, summary, management_letter)
            output_format: Output format

        Returns:
            Dict with report generation results
        """
        arguments = {
            "sections": sections,
            "report_type": report_type,
            "output_format": output_format
        }

        return await self._call_tool("create_audit_report", arguments)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_mcp_client(
    base_url: str = "http://localhost:8001"
) -> MCPRagClient:
    """Factory function to create and verify MCP client.

    Creates an MCP client and verifies connectivity before returning.
    Use this for guaranteed working client instances.

    Args:
        base_url: MCP RAG server URL

    Returns:
        MCPRagClient: Connected and verified client instance

    Raises:
        MCPConnectionError: If server is not available

    Example:
        client = await create_mcp_client()
        # Client is guaranteed to be connected
        results = await client.search_standards("query")
        await client.close()
    """
    client = MCPRagClient(base_url=base_url)

    if not await client.health_check():
        await client.close()
        raise MCPConnectionError(
            f"MCP RAG server at {base_url} is not available. "
            "Ensure the server is running."
        )

    return client
