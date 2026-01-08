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
