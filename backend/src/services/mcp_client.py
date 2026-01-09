"""MCP Server Client Infrastructure for AI Audit Platform

This module provides async HTTP clients for all 7 MCP servers in the audit-mcp-suite,
enabling dynamic tool loading and execution via HTTP JSON-RPC protocol.

MCP Servers Supported:
    | Port | Server              | Description                        |
    |------|---------------------|------------------------------------|
    | 8001 | mcp-rag             | Semantic search (K-IFRS, K-GAAS)   |
    | 8002 | mcp-processor       | Document processing                |
    | 8003 | mcp-finance         | Accounting calculations            |
    | 8004 | mcp-vision          | OCR & table extraction             |
    | 8005 | mcp-filesystem      | File management                    |
    | 8006 | mcp-web-research    | External research                  |
    | 8007 | mcp-excel-processor | Excel workpaper automation         |

Key Features:
    - Async HTTP client using httpx for non-blocking I/O
    - Circuit breaker pattern (5 failures → 60s cooldown)
    - Retry with exponential backoff (3 attempts)
    - Health check methods for all servers
    - MCPToolRegistry for unified tool management across all servers
    - Environment variable support for server URLs
    - OpenTelemetry tracing integration

Usage:
    ```python
    from src.services.mcp_client import MCPToolRegistry

    # Create registry and register servers
    registry = MCPToolRegistry()
    await registry.register_all_servers()

    # Call a tool by name (automatically routes to correct server)
    result = await registry.call_tool(
        "search_standards",
        {"query_text": "수익인식", "top_k": 30}
    )

    # Get all available tool schemas for LangChain
    tools = registry.get_tool_schemas()
    ```

Reference:
    - MCP Protocol: HTTP JSON-RPC 2.0
    - Server Suite: audit-mcp-suite/servers/*
"""

import asyncio
import os
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
from enum import Enum

import httpx

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# MCP SERVER CONFIGURATION
# ============================================================================

class MCPServerType(Enum):
    """Enumeration of available MCP servers."""
    RAG = "mcp-rag"
    PROCESSOR = "mcp-processor"
    FINANCE = "mcp-finance"
    VISION = "mcp-vision"
    FILESYSTEM = "mcp-filesystem"
    WEB_RESEARCH = "mcp-web-research"
    EXCEL_PROCESSOR = "mcp-excel-processor"


# Default server URLs and their environment variable mappings
MCP_SERVER_CONFIG = {
    MCPServerType.RAG: {
        "name": "mcp-rag",
        "env_var": "MCP_RAG_URL",
        "default_url": "http://localhost:8001",
        "description": "Semantic search for K-IFRS, K-GAAS standards",
        "timeout": 30.0,
    },
    MCPServerType.PROCESSOR: {
        "name": "mcp-processor",
        "env_var": "MCP_PROCESSOR_URL",
        "default_url": "http://localhost:8002",
        "description": "Document processing and parsing",
        "timeout": 60.0,
    },
    MCPServerType.FINANCE: {
        "name": "mcp-finance",
        "env_var": "MCP_FINANCE_URL",
        "default_url": "http://localhost:8003",
        "description": "Accounting calculations and validations",
        "timeout": 30.0,
    },
    MCPServerType.VISION: {
        "name": "mcp-vision",
        "env_var": "MCP_VISION_URL",
        "default_url": "http://localhost:8004",
        "description": "OCR and table extraction from images/PDFs",
        "timeout": 120.0,  # Longer timeout for OCR
    },
    MCPServerType.FILESYSTEM: {
        "name": "mcp-filesystem",
        "env_var": "MCP_FILESYSTEM_URL",
        "default_url": "http://localhost:8005",
        "description": "File management operations",
        "timeout": 30.0,
    },
    MCPServerType.WEB_RESEARCH: {
        "name": "mcp-web-research",
        "env_var": "MCP_WEB_RESEARCH_URL",
        "default_url": "http://localhost:8006",
        "description": "External research and web scraping",
        "timeout": 60.0,
    },
    MCPServerType.EXCEL_PROCESSOR: {
        "name": "mcp-excel-processor",
        "env_var": "MCP_EXCEL_PROCESSOR_URL",
        "default_url": "http://localhost:8007",
        "description": "Excel workpaper automation",
        "timeout": 60.0,
    },
}


def get_server_url(server_type: MCPServerType) -> str:
    """Get server URL from environment or default.

    Args:
        server_type: Type of MCP server

    Returns:
        Server URL string
    """
    config = MCP_SERVER_CONFIG[server_type]
    return os.getenv(config["env_var"], config["default_url"])


# ============================================================================
# MCP ERROR REPORTING
# ============================================================================

@dataclass
class MCPError:
    """Structured error information for MCP tool failures.

    This dataclass provides a consistent format for reporting MCP errors
    across the application, enabling proper logging, monitoring, and
    user communication.

    Attributes:
        server: MCP server name (e.g., 'mcp-rag', 'mcp-excel')
        tool: Tool name that failed (e.g., 'search_standards')
        error_type: Category of error ('connection', 'timeout', 'circuit_breaker', 'tool_error')
        message: Human-readable error description
        retries_attempted: Number of retry attempts made before failure
        fallback_used: Whether fallback to basic LLM was triggered
        original_exception: The original exception that caused the error (optional)
    """
    server: str
    tool: str
    error_type: str  # 'connection', 'timeout', 'circuit_breaker', 'tool_error'
    message: str
    retries_attempted: int = 0
    fallback_used: bool = False
    original_exception: Optional[Exception] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "server": self.server,
            "tool": self.tool,
            "error_type": self.error_type,
            "message": self.message,
            "retries_attempted": self.retries_attempted,
            "fallback_used": self.fallback_used
        }

    def __str__(self) -> str:
        return (
            f"MCPError({self.server}/{self.tool}): "
            f"[{self.error_type}] {self.message} "
            f"(retries: {self.retries_attempted}, fallback: {self.fallback_used})"
        )


# ============================================================================
# CIRCUIT BREAKER IMPLEMENTATION
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, requests pass through
    - OPEN: After fail_max failures, reject requests for reset_timeout seconds
    - HALF_OPEN: After timeout, allow one test request

    Attributes:
        fail_max: Maximum consecutive failures before opening circuit (default: 5)
        reset_timeout: Seconds to wait before attempting recovery (default: 60)
    """
    fail_max: int = 5
    reset_timeout: float = 60.0
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               (time.time() - self._last_failure_time) >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
        return self._state

    def record_success(self) -> None:
        """Record a successful call, resetting failure count."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker CLOSED after successful recovery")

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.fail_max:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self._failure_count} failures. "
                f"Will retry after {self.reset_timeout}s"
            )

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if request is allowed, False if circuit is open
        """
        current_state = self.state  # This may transition OPEN -> HALF_OPEN
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return True  # Allow test request
        else:  # OPEN
            return False

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


# ============================================================================
# UNIFIED MCP CLIENT (Generic for any MCP Server)
# ============================================================================

@dataclass
class MCPClientConfig:
    """Configuration for MCP Client.

    Attributes:
        base_url: MCP server base URL
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts for failed requests (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        retry_backoff: Exponential backoff multiplier (default: 2.0)
        circuit_breaker_fail_max: Failures before circuit opens (default: 5)
        circuit_breaker_reset_timeout: Seconds before circuit recovery (default: 60)
    """
    base_url: str = "http://localhost:8001"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    circuit_breaker_fail_max: int = 5
    circuit_breaker_reset_timeout: float = 60.0


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Raised when connection to MCP server fails."""
    pass


class MCPToolExecutionError(MCPClientError):
    """Raised when MCP tool execution fails."""
    pass


class MCPClient:
    """Generic MCP Client for communicating with any MCP server.

    This is the unified client that can connect to any MCP server in the
    audit-mcp-suite. It provides:
    - HTTP JSON-RPC communication
    - Circuit breaker protection (5 failures → 60s cooldown)
    - Retry with exponential backoff (3 attempts)
    - Health check capabilities
    - Tool listing and execution

    Example:
        ```python
        # Create client for RAG server
        client = MCPClient(
            name="mcp-rag",
            base_url="http://localhost:8001"
        )

        # List available tools
        tools = await client.list_tools()

        # Call a tool
        result = await client.call_tool(
            "search_standards",
            {"query_text": "수익인식", "top_k": 30}
        )

        # Cleanup
        await client.close()
        ```
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: float = 30.0,
        config: Optional[MCPClientConfig] = None
    ):
        """Initialize MCP client.

        Args:
            name: Server name for identification (e.g., "mcp-rag")
            base_url: Server URL (e.g., http://localhost:8001)
            timeout: Request timeout in seconds
            config: Optional full configuration
        """
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        if config:
            self.config = config
        else:
            self.config = MCPClientConfig(
                base_url=self.base_url,
                timeout=timeout
            )

        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.health_endpoint = f"{self.base_url}/health"
        self._client: Optional[httpx.AsyncClient] = None

        # Circuit breaker for this server
        self.circuit_breaker = CircuitBreaker(
            fail_max=self.config.circuit_breaker_fail_max,
            reset_timeout=self.config.circuit_breaker_reset_timeout
        )

        logger.info(f"MCPClient '{name}' initialized: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"}
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug(f"MCPClient '{self.name}' connection closed")

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.close()

    async def _execute_with_retry(
        self,
        request_func: Callable,
        *args,
        **kwargs
    ) -> httpx.Response:
        """Execute HTTP request with circuit breaker and retry logic.

        Args:
            request_func: Async function to execute
            *args: Positional arguments for request_func
            **kwargs: Keyword arguments for request_func

        Returns:
            HTTP response

        Raises:
            CircuitBreakerOpen: If circuit is open
            MCPConnectionError: If all retries fail
        """
        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerOpen(
                f"Circuit breaker is OPEN for {self.name}. "
                f"Will retry after {self.circuit_breaker.reset_timeout}s"
            )

        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                response = await request_func(*args, **kwargs)
                response.raise_for_status()
                self.circuit_breaker.record_success()
                return response

            except httpx.ConnectError as e:
                last_error = e
                self.circuit_breaker.record_failure()
                logger.warning(
                    f"[{self.name}] Connection failed "
                    f"(attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            except httpx.TimeoutException as e:
                last_error = e
                self.circuit_breaker.record_failure()
                logger.warning(
                    f"[{self.name}] Request timeout "
                    f"(attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            except httpx.HTTPStatusError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise MCPToolExecutionError(
                        f"[{self.name}] Client error {e.response.status_code}: "
                        f"{e.response.text}"
                    )
                last_error = e
                self.circuit_breaker.record_failure()
                logger.warning(
                    f"[{self.name}] Server error "
                    f"(attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (
                    self.config.retry_backoff ** attempt
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        raise MCPConnectionError(
            f"[{self.name}] Failed after {self.config.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    async def health_check(self) -> bool:
        """Check if MCP server is available.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(self.health_endpoint, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[{self.name}] Health check failed: {e}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """Check server health with detailed status.

        Returns:
            Health status dict

        Raises:
            MCPConnectionError: If health check fails
        """
        try:
            client = await self._get_client()
            response = await client.get(self.health_endpoint, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            raise MCPConnectionError(f"Health check failed: {e}") from e

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the MCP server.

        Returns:
            List of tool schemas with name, description, and input_schema

        Raises:
            MCPConnectionError: If server is unavailable
            MCPToolExecutionError: If request fails
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }

        client = await self._get_client()
        response = await self._execute_with_retry(
            client.post,
            self.mcp_endpoint,
            json=request
        )

        result = response.json()

        if "error" in result:
            error_msg = result.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            raise MCPToolExecutionError(f"[{self.name}] {error_msg}")

        tools = result.get("result", {}).get("tools", [])
        logger.info(f"[{self.name}] Loaded {len(tools)} tools")
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPConnectionError: If server is unavailable
            MCPToolExecutionError: If tool execution fails
        """
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        client = await self._get_client()
        response = await self._execute_with_retry(
            client.post,
            self.mcp_endpoint,
            json=request,
            timeout=self.timeout
        )

        result = response.json()

        if "error" in result:
            error_msg = result.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            raise MCPToolExecutionError(
                f"[{self.name}] Tool '{tool_name}' error: {error_msg}"
            )

        return result.get("result", {})


# ============================================================================
# MCP TOOL REGISTRY (Unified Management of All MCP Servers)
# ============================================================================

@dataclass
class RegisteredTool:
    """Information about a registered tool."""
    name: str
    schema: Dict[str, Any]
    server_name: str
    client: MCPClient


class MCPToolRegistry:
    """Registry for all MCP tools across multiple servers.

    The MCPToolRegistry provides unified access to all 7 MCP servers,
    automatically routing tool calls to the correct server.

    Features:
        - Server registration with automatic tool discovery
        - Health check aggregation across all servers
        - Tool routing by name
        - Circuit breaker status monitoring

    Example:
        ```python
        # Create registry
        registry = MCPToolRegistry()

        # Register all servers from environment
        await registry.register_all_servers()

        # Or register specific servers
        await registry.register_server(MCPServerType.RAG)
        await registry.register_server(MCPServerType.FINANCE)

        # Call a tool (automatically routes to correct server)
        result = await registry.call_tool(
            "search_standards",
            {"query_text": "리스 회계처리", "top_k": 20}
        )

        # Get all tool schemas for LangChain
        tools = registry.get_tool_schemas()

        # Health check all servers
        status = await registry.health_check_all()

        # Cleanup
        await registry.close_all()
        ```
    """

    def __init__(self):
        """Initialize empty registry."""
        self.servers: Dict[str, MCPClient] = {}
        self.tools: Dict[str, RegisteredTool] = {}
        self._initialized = False

    async def register_server(
        self,
        server_type: MCPServerType,
        url: Optional[str] = None,
        skip_health_check: bool = False
    ) -> bool:
        """Register an MCP server and load its tools.

        Args:
            server_type: Type of MCP server to register
            url: Optional override URL (defaults to env var or default)
            skip_health_check: Skip initial health check (for lazy loading)

        Returns:
            True if registration successful, False otherwise

        Raises:
            MCPConnectionError: If server is unavailable (when not skipping)
        """
        config = MCP_SERVER_CONFIG[server_type]
        server_name = config["name"]
        server_url = url or get_server_url(server_type)
        timeout = config["timeout"]

        logger.info(f"Registering server: {server_name} at {server_url}")

        client = MCPClient(
            name=server_name,
            base_url=server_url,
            timeout=timeout
        )

        # Health check
        if not skip_health_check:
            try:
                health = await client.check_health()
                logger.info(f"✓ {server_name} healthy: {health.get('status', 'ok')}")
            except Exception as e:
                logger.error(f"✗ {server_name} unhealthy: {e}")
                await client.close()
                raise MCPConnectionError(
                    f"Server {server_name} at {server_url} is not available"
                ) from e

        # Load tools
        try:
            tools = await client.list_tools()
        except Exception as e:
            logger.error(f"Failed to load tools from {server_name}: {e}")
            await client.close()
            raise

        self.servers[server_name] = client

        # Register each tool
        for tool in tools:
            tool_name = tool["name"]
            self.tools[tool_name] = RegisteredTool(
                name=tool_name,
                schema=tool,
                server_name=server_name,
                client=client
            )

        logger.info(f"  Registered {len(tools)} tools from {server_name}")
        return True

    async def register_all_servers(
        self,
        skip_unavailable: bool = True
    ) -> Dict[str, bool]:
        """Register all configured MCP servers.

        Args:
            skip_unavailable: If True, continue even if some servers fail

        Returns:
            Dict mapping server name to registration success status
        """
        results = {}

        for server_type in MCPServerType:
            server_name = MCP_SERVER_CONFIG[server_type]["name"]
            try:
                await self.register_server(server_type)
                results[server_name] = True
            except Exception as e:
                logger.warning(f"Failed to register {server_name}: {e}")
                results[server_name] = False
                if not skip_unavailable:
                    raise

        self._initialized = True
        successful = sum(1 for v in results.values() if v)
        logger.info(
            f"MCPToolRegistry initialized: {successful}/{len(results)} servers"
        )
        return results

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LangChain integration.

        Returns:
            List of tool schemas with name, description, and input_schema
        """
        return [tool.schema for tool in self.tools.values()]

    def get_tools_by_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tool schemas for a specific server.

        Args:
            server_name: Name of the server (e.g., "mcp-rag")

        Returns:
            List of tool schemas from that server
        """
        return [
            tool.schema for tool in self.tools.values()
            if tool.server_name == server_name
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool by name, routing to the correct server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not registered
            MCPToolExecutionError: If execution fails
        """
        if tool_name not in self.tools:
            available = ", ".join(sorted(self.tools.keys())[:10])
            raise ValueError(
                f"Unknown tool: {tool_name}. "
                f"Available tools: {available}..."
            )

        tool_info = self.tools[tool_name]
        logger.debug(
            f"Routing tool '{tool_name}' to server '{tool_info.server_name}'"
        )
        return await tool_info.client.call_tool(tool_name, arguments)

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered servers.

        Returns:
            Dict mapping server name to health status
        """
        results = {}

        for server_name, client in self.servers.items():
            try:
                is_healthy = await client.health_check()
                results[server_name] = {
                    "healthy": is_healthy,
                    "circuit_state": client.circuit_breaker.state.value,
                    "url": client.base_url
                }
            except Exception as e:
                results[server_name] = {
                    "healthy": False,
                    "error": str(e),
                    "circuit_state": client.circuit_breaker.state.value,
                    "url": client.base_url
                }

        return results

    def get_circuit_breaker_status(self) -> Dict[str, str]:
        """Get circuit breaker status for all servers.

        Returns:
            Dict mapping server name to circuit state
        """
        return {
            name: client.circuit_breaker.state.value
            for name, client in self.servers.items()
        }

    async def close_all(self) -> None:
        """Close all server connections."""
        for server_name, client in self.servers.items():
            await client.close()
            logger.debug(f"Closed connection to {server_name}")

        self.servers.clear()
        self.tools.clear()
        self._initialized = False
        logger.info("MCPToolRegistry closed all connections")

    @property
    def registered_server_count(self) -> int:
        """Number of registered servers."""
        return len(self.servers)

    @property
    def registered_tool_count(self) -> int:
        """Number of registered tools."""
        return len(self.tools)

    def __repr__(self) -> str:
        return (
            f"MCPToolRegistry("
            f"servers={self.registered_server_count}, "
            f"tools={self.registered_tool_count})"
        )


# ============================================================================
# LEGACY EXCEPTION ALIASES (for backward compatibility)
# ============================================================================

# Keep MCPRagClientError as alias for backward compatibility
MCPRagClientError = MCPClientError


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
    """Factory function to create and verify MCP RAG client.

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


async def create_mcp_registry(
    server_types: Optional[List[MCPServerType]] = None,
    skip_unavailable: bool = True
) -> MCPToolRegistry:
    """Factory function to create and initialize MCP tool registry.

    Creates a registry and registers specified servers (or all by default).
    Use this for unified access to all MCP servers.

    Args:
        server_types: List of server types to register (None = all servers)
        skip_unavailable: If True, continue even if some servers fail

    Returns:
        MCPToolRegistry: Initialized registry with registered servers

    Example:
        # Register all servers
        registry = await create_mcp_registry()

        # Register specific servers
        registry = await create_mcp_registry(
            server_types=[MCPServerType.RAG, MCPServerType.FINANCE]
        )

        # Call any tool
        result = await registry.call_tool("search_standards", {"query_text": "..."})

        # Cleanup
        await registry.close_all()
    """
    registry = MCPToolRegistry()

    if server_types is None:
        # Register all servers
        await registry.register_all_servers(skip_unavailable=skip_unavailable)
    else:
        # Register specific servers
        for server_type in server_types:
            try:
                await registry.register_server(server_type)
            except Exception as e:
                if not skip_unavailable:
                    await registry.close_all()
                    raise
                logger.warning(f"Failed to register {server_type.value}: {e}")

    return registry


async def create_generic_mcp_client(
    name: str,
    base_url: str,
    timeout: float = 30.0
) -> MCPClient:
    """Factory function to create and verify a generic MCP client.

    Creates a client for any MCP server and verifies connectivity.

    Args:
        name: Server name for identification
        base_url: Server URL
        timeout: Request timeout in seconds

    Returns:
        MCPClient: Connected and verified client

    Raises:
        MCPConnectionError: If server is not available

    Example:
        # Create client for custom MCP server
        client = await create_generic_mcp_client(
            name="my-server",
            base_url="http://localhost:9000"
        )
        tools = await client.list_tools()
        await client.close()
    """
    client = MCPClient(name=name, base_url=base_url, timeout=timeout)

    if not await client.health_check():
        await client.close()
        raise MCPConnectionError(
            f"MCP server '{name}' at {base_url} is not available."
        )

    return client


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Server configuration
    "MCPServerType",
    "MCP_SERVER_CONFIG",
    "get_server_url",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpen",
    # Error reporting
    "MCPError",
    # Base client and registry
    "MCPClient",
    "MCPClientConfig",
    "MCPToolRegistry",
    "RegisteredTool",
    # Exceptions
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolExecutionError",
    # Legacy specialized clients (backward compatibility)
    "MCPRagClient",
    "MCPRagClientError",
    "MCPExcelClient",
    "MCPExcelClientConfig",
    "MCPExcelClientError",
    "MCPExcelConnectionError",
    "MCPExcelParseError",
    "MCPDocumentClient",
    "MCPDocumentClientConfig",
    "MCPDocumentClientError",
    "MCPDocumentConnectionError",
    "MCPDocumentGenerationError",
    # Factory functions
    "create_mcp_client",
    "create_mcp_registry",
    "create_generic_mcp_client",
]
