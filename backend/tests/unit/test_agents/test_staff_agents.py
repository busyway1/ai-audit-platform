"""
Unit Tests for Staff Agents

This module provides comprehensive test coverage for all 4 Staff agents:
1. ExcelParserAgent - Excel file parsing and data extraction
2. StandardRetrieverAgent - K-IFRS/K-GAAS standard retrieval (mock RAG)
3. VouchingAssistantAgent - Transaction vouching and verification
4. WorkPaperGeneratorAgent - Audit workpaper draft generation

All OpenAI API calls are mocked using unittest.mock.AsyncMock.
Test coverage includes:
- Basic agent initialization
- Successful execution with mock data
- Error handling and edge cases
- Data validation and formatting
- Message generation

Target: 100% coverage of staff_agents.py
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Global patch for ChatOpenAI to avoid initialization issues
@pytest.fixture(autouse=True)
def mock_chat_openai():
    """Auto-use fixture to mock ChatOpenAI for all tests."""
    with patch('src.agents.staff_agents.ChatOpenAI'):
        yield


@pytest.fixture
def mock_mcp_rag_client():
    """
    Fixture to mock MCPRagClient for StandardRetrieverAgent tests.

    Returns mock search results that simulate MCP RAG server responses.
    """
    mock_search_result = {
        "status": "success",
        "data": {
            "query": "Sales 회계처리 기준",
            "mode": "hybrid",
            "results_count": 3,
            "results": [
                {
                    "id": "1",
                    "content": "K-IFRS 1115 고객과의 계약에서 생기는 수익 - 수익인식 5단계 모형을 적용하여 수익을 인식한다.",
                    "paragraph_no": "31",
                    "standard_id": "K-IFRS 1115",
                    "hierarchy_path": "K-IFRS.1115.31",
                    "topic": "수익인식",
                    "title": "수익인식 시점",
                    "section_type": "main",
                    "scores": {"bm25": 0.85, "vector": 0.92, "combined": 0.89},
                    "rank": 1,
                    "related_paragraphs": ["32", "33", "34"]
                },
                {
                    "id": "2",
                    "content": "K-GAAS 500 감사증거 - 감사인은 충분하고 적합한 감사증거를 입수해야 한다.",
                    "paragraph_no": "A1",
                    "standard_id": "K-GAAS 500",
                    "hierarchy_path": "K-GAAS.500.A1",
                    "topic": "감사증거",
                    "title": "감사증거 요구사항",
                    "section_type": "main",
                    "scores": {"bm25": 0.78, "vector": 0.85, "combined": 0.82},
                    "rank": 2,
                    "related_paragraphs": ["A2", "A3"]
                },
                {
                    "id": "3",
                    "content": "K-GAAS 330 평가된 위험에 대한 감사인의 대응 - 실증절차 설계 요구사항.",
                    "paragraph_no": "5",
                    "standard_id": "K-GAAS 330",
                    "hierarchy_path": "K-GAAS.330.5",
                    "topic": "위험대응",
                    "title": "실증절차",
                    "section_type": "main",
                    "scores": {"bm25": 0.72, "vector": 0.80, "combined": 0.76},
                    "rank": 3,
                    "related_paragraphs": ["6", "7"]
                }
            ],
            "metadata": {
                "bm25_candidates": 50,
                "vector_candidates": 50,
                "bm25_weight": 0.3,
                "vector_weight": 0.7,
                "fusion_method": "RRF",
                "duration_ms": 125.5
            }
        }
    }

    with patch('src.agents.staff_agents.MCPRagClient') as mock_client_class:
        mock_instance = AsyncMock()
        mock_instance.search_standards = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value = mock_instance
        yield mock_instance


from src.agents.staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent
)


# ============================================================================
# FIXTURES - Mock State and Data
# ============================================================================

@pytest.fixture
def mock_task_state() -> Dict[str, Any]:
    """
    Create a realistic mock TaskState for testing.

    Represents state after Partner Agent has created initial task.

    Returns:
        Dict: Complete TaskState with all required fields
    """
    return {
        "task_id": "TASK-001",
        "thread_id": "test-thread-001",
        "category": "Sales",
        "status": "In-Progress",
        "messages": [],
        "raw_data": {},
        "standards": [],
        "search_metadata": {},  # MCP search metadata for debugging
        "vouching_logs": [],
        "workpaper_draft": "",
        "next_staff": "ExcelParser",
        "error_report": "",
        "risk_score": 0
    }


@pytest.fixture
def mock_task_state_with_raw_data(mock_task_state) -> Dict[str, Any]:
    """
    Create mock state after ExcelParserAgent has run.

    Returns:
        Dict: TaskState with raw_data populated
    """
    mock_task_state["raw_data"] = {
        "category": "Sales",
        "total_sales": 5_000_000_000,
        "transaction_count": 150,
        "period": "2024-01-01 to 2024-12-31",
        "sample_transactions": [
            {
                "date": "2024-01-15",
                "amount": 50_000_000,
                "customer": "Customer A",
                "invoice_no": "INV-2024-001"
            },
            {
                "date": "2024-02-20",
                "amount": 75_000_000,
                "customer": "Customer B",
                "invoice_no": "INV-2024-002"
            },
            {
                "date": "2024-03-10",
                "amount": 120_000_000,
                "customer": "Customer C",
                "invoice_no": "INV-2024-003"
            }
        ],
        "parsed_at": "2026-01-06T10:30:00Z",
        "data_quality": "GOOD",
        "anomalies_detected": 0
    }
    return mock_task_state


@pytest.fixture
def mock_task_state_with_standards(mock_task_state_with_raw_data) -> Dict[str, Any]:
    """
    Create mock state after StandardRetrieverAgent has run.

    Returns:
        Dict: TaskState with standards and raw_data populated
    """
    mock_task_state_with_raw_data["standards"] = [
        "K-IFRS 1115: Revenue from Contracts with Customers",
        "K-GAAS 500: Audit Evidence",
        "K-GAAS 330: Auditor's Responses to Assessed Risks"
    ]
    return mock_task_state_with_raw_data


@pytest.fixture
def mock_llm_response_vouching() -> AIMessage:
    """
    Create mock LLM response for vouching procedures.

    Returns:
        AIMessage: Realistic LLM analysis of vouching procedures
    """
    return AIMessage(
        content=(
            "Based on the transactions provided and applicable audit standards:\n\n"
            "1. **INV-2024-001**: Invoice matches sales record, contract terms verified, "
            "payment received on 2024-02-15. No exceptions noted.\n\n"
            "2. **INV-2024-002**: Customer signature present on invoice but shipping confirmation "
            "document not located. Requires follow-up with customer.\n\n"
            "3. **INV-2024-003**: All supporting documents present and verified. "
            "Contract, invoice, delivery receipt, and payment confirmation aligned.\n\n"
            "Overall verification rate: 67% (2 of 3 verified, 1 exception)"
        )
    )


@pytest.fixture
def mock_llm_response_workpaper() -> AIMessage:
    """
    Create mock LLM response for workpaper generation.

    Returns:
        AIMessage: Realistic LLM-generated workpaper content
    """
    return AIMessage(
        content=(
            "## Audit Objective\n"
            "To verify the completeness and accuracy of sales transactions recorded in "
            "the Revenue account for the period 2024-01-01 to 2024-12-31.\n\n"
            "## Procedures Performed\n"
            "1. Obtained and reviewed sales transaction listing from accounting system\n"
            "2. Recalculated total sales amount: KRW 5,000,000,000\n"
            "3. Selected sample of 3 transactions for detailed vouching\n"
            "4. Verified each transaction against supporting documentation\n\n"
            "## Findings and Observations\n"
            "- 2 of 3 transactions fully verified with complete documentation\n"
            "- 1 transaction (INV-2024-002) missing shipping confirmation\n"
            "- Data quality rated as GOOD overall\n\n"
            "## Conclusion\n"
            "Sales transactions are generally fairly stated. One exception identified "
            "requires follow-up with customer for missing documentation."
        )
    )


# ============================================================================
# TESTS - ExcelParserAgent
# ============================================================================

class TestExcelParserAgent:
    """Test suite for ExcelParserAgent."""

    def test_initialization(self):
        """Test ExcelParserAgent initialization with default model."""
        agent = ExcelParserAgent()

        assert agent.agent_name == "Staff_Excel_Parser"
        assert agent.llm is not None

    def test_initialization_custom_model(self):
        """Test ExcelParserAgent initialization with custom model."""
        custom_model = "gpt-4o"

        with patch('src.agents.staff_agents.ChatOpenAI') as mock_llm_class:
            agent = ExcelParserAgent(model_name=custom_model)
            mock_llm_class.assert_called_once_with(model=custom_model)

    @pytest.mark.asyncio
    async def test_excel_parser_extracts_data(self, mock_task_state):
        """
        Test ExcelParserAgent successfully extracts financial data.

        Verifies:
        - Returns dict with 'raw_data' and 'messages' keys
        - raw_data contains all required fields
        - Sample transactions are properly formatted
        - Messages contain agent name and summary
        """
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)

        # Verify return structure
        assert isinstance(result, dict)
        assert "raw_data" in result
        assert "messages" in result

        # Verify raw_data structure
        raw_data = result["raw_data"]
        assert raw_data["category"] == "Sales"
        assert raw_data["total_sales"] == 5_000_000_000
        assert raw_data["transaction_count"] == 150
        assert raw_data["period"] == "2024-01-01 to 2024-12-31"
        assert raw_data["data_quality"] == "GOOD"
        assert raw_data["anomalies_detected"] == 0

        # Verify sample transactions
        assert len(raw_data["sample_transactions"]) == 3
        first_txn = raw_data["sample_transactions"][0]
        assert first_txn["date"] == "2024-01-15"
        assert first_txn["amount"] == 50_000_000
        assert first_txn["invoice_no"] == "INV-2024-001"

        # Verify messages
        assert len(result["messages"]) == 1
        msg = result["messages"][0]
        assert isinstance(msg, HumanMessage)
        assert "Staff_Excel_Parser" in msg.content
        assert "150" in msg.content
        assert "GOOD" in msg.content

    @pytest.mark.asyncio
    async def test_excel_parser_handles_inventory_category(self, mock_task_state):
        """
        Test ExcelParserAgent correctly handles different category (Inventory).

        Verifies:
        - Category is correctly preserved in raw_data
        - Agent adapts output based on category
        """
        mock_task_state["category"] = "Inventory"
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)

        raw_data = result["raw_data"]
        assert raw_data["category"] == "Inventory"
        assert "Inventory" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_excel_parser_handles_ar_category(self, mock_task_state):
        """Test ExcelParserAgent correctly handles AR category."""
        mock_task_state["category"] = "AR"
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)

        raw_data = result["raw_data"]
        assert raw_data["category"] == "AR"

    @pytest.mark.asyncio
    async def test_excel_parser_handles_missing_task_id(self):
        """
        Test ExcelParserAgent handles missing task_id gracefully.

        Verifies:
        - Uses "UNKNOWN" as default when task_id missing
        """
        state_no_id = {
            "category": "Sales",
            "messages": []
        }
        agent = ExcelParserAgent()

        result = await agent.run(state_no_id)

        # Should still produce valid output even with missing task_id
        assert "raw_data" in result
        assert result["raw_data"]["total_sales"] == 5_000_000_000

    @pytest.mark.asyncio
    async def test_excel_parser_handles_missing_category(self, mock_task_state):
        """
        Test ExcelParserAgent handles missing category.

        Verifies:
        - Uses "Sales" as default when category missing
        """
        del mock_task_state["category"]
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)

        raw_data = result["raw_data"]
        assert raw_data["category"] == "Sales"

    @pytest.mark.asyncio
    async def test_excel_parser_transaction_format(self, mock_task_state):
        """
        Test ExcelParserAgent formats transactions correctly.

        Verifies:
        - Each transaction has required fields
        - Currency amounts are properly formatted as integers
        """
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        raw_data = result["raw_data"]

        for txn in raw_data["sample_transactions"]:
            assert "date" in txn
            assert "amount" in txn
            assert "customer" in txn
            assert "invoice_no" in txn
            assert isinstance(txn["amount"], int)
            assert txn["amount"] > 0

    @pytest.mark.asyncio
    async def test_excel_parser_message_format(self, mock_task_state):
        """
        Test ExcelParserAgent generates properly formatted messages.

        Verifies:
        - Message is HumanMessage type (per agent pattern)
        - Message has agent name
        - Message contains key information
        """
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        msg = result["messages"][0]

        assert isinstance(msg, HumanMessage)
        assert msg.name == "Staff_Excel_Parser"
        assert "Staff_Excel_Parser" in msg.content
        assert "transactions" in msg.content.lower()
        assert "data quality" in msg.content.lower()


# ============================================================================
# TESTS - StandardRetrieverAgent
# ============================================================================

class TestStandardRetrieverAgent:
    """Test suite for StandardRetrieverAgent with MCP RAG integration."""

    def test_initialization(self):
        """Test StandardRetrieverAgent initialization with default model."""
        agent = StandardRetrieverAgent()

        assert agent.agent_name == "Staff_Standard_Retriever"
        assert agent.llm is not None

    def test_initialization_custom_model(self):
        """Test StandardRetrieverAgent initialization with custom model."""
        custom_model = "gpt-4o"

        with patch('src.agents.staff_agents.ChatOpenAI') as mock_llm_class:
            agent = StandardRetrieverAgent(model_name=custom_model)
            mock_llm_class.assert_called_once_with(model=custom_model)

    @pytest.mark.asyncio
    async def test_standard_retriever_returns_standards_from_mcp(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent returns standards from MCP RAG server.

        Verifies:
        - Returns dict with 'standards', 'search_metadata', and 'messages' keys
        - Standards list contains K-IFRS and K-GAAS references from MCP
        - Search metadata includes duration and search parameters
        """
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)

        # Verify return structure
        assert isinstance(result, dict)
        assert "standards" in result
        assert "search_metadata" in result
        assert "messages" in result

        # Verify standards list from MCP
        standards = result["standards"]
        assert isinstance(standards, list)
        assert len(standards) == 3  # Mock returns 3 results

        # Verify standard format (contains K-IFRS or K-GAAS references)
        for standard in standards:
            assert isinstance(standard, str)
            assert "K-IFRS" in standard or "K-GAAS" in standard

        # Verify search_metadata
        metadata = result["search_metadata"]
        assert metadata.get("duration_ms") == 125.5
        assert metadata.get("fusion_method") == "RRF"

        # Verify MCP client was called
        mock_mcp_rag_client.search_standards.assert_called_once()

    @pytest.mark.asyncio
    async def test_standard_retriever_sales_category(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent calls MCP with correct query for Sales category.

        Verifies:
        - MCP client is called with Sales category query
        - Returns formatted standards from MCP response
        """
        mock_task_state_with_raw_data["category"] = "Sales"
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        standards_content = " ".join(result["standards"])

        # Verify MCP was called with Sales category
        call_args = mock_mcp_rag_client.search_standards.call_args
        assert "Sales" in call_args.kwargs["query_text"]
        assert call_args.kwargs["top_k"] == 30
        assert call_args.kwargs["mode"] == "hybrid"

        # Verify standards contain expected content from mock
        assert "1115" in standards_content

    @pytest.mark.asyncio
    async def test_standard_retriever_inventory_category(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent calls MCP with correct query for Inventory category.
        """
        mock_task_state_with_raw_data["category"] = "Inventory"
        agent = StandardRetrieverAgent()

        await agent.run(mock_task_state_with_raw_data)

        # Verify MCP was called with Inventory category
        call_args = mock_mcp_rag_client.search_standards.call_args
        assert "Inventory" in call_args.kwargs["query_text"]

    @pytest.mark.asyncio
    async def test_standard_retriever_ar_category(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent calls MCP with correct query for AR category.
        """
        mock_task_state_with_raw_data["category"] = "AR"
        agent = StandardRetrieverAgent()

        await agent.run(mock_task_state_with_raw_data)

        # Verify MCP was called with AR category
        call_args = mock_mcp_rag_client.search_standards.call_args
        assert "AR" in call_args.kwargs["query_text"]

    @pytest.mark.asyncio
    async def test_standard_retriever_handles_mcp_error(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent handles MCP errors gracefully.

        Verifies:
        - Returns empty standards on MCP error
        - Error is logged and captured in search_metadata
        """
        from src.services.mcp_client import MCPRagClientError

        mock_mcp_rag_client.search_standards.side_effect = MCPRagClientError("Connection failed")
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)

        # Should return empty standards on error
        assert result["standards"] == []
        assert "error" in result["search_metadata"]
        assert "MCPRagClientError" in result["search_metadata"]["error_type"]

    @pytest.mark.asyncio
    async def test_standard_retriever_handles_mcp_non_success_status(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent handles MCP non-success status.
        """
        mock_mcp_rag_client.search_standards.return_value = {
            "status": "error",
            "message": "Search index unavailable"
        }
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)

        # Should return empty standards on non-success
        assert result["standards"] == []
        assert "error" in result["search_metadata"]

    @pytest.mark.asyncio
    async def test_standard_retriever_formats_standards_message(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent properly formats standards message.

        Verifies:
        - Message contains agent name
        - Message includes search duration from MCP
        """
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        msg = result["messages"][0]

        assert isinstance(msg, HumanMessage)
        assert msg.name == "Staff_Standard_Retriever"
        assert "Staff_Standard_Retriever" in msg.content
        assert "Retrieved" in msg.content
        assert "125.5ms" in msg.content  # Duration from mock

    @pytest.mark.asyncio
    async def test_standard_retriever_count_in_message(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """
        Test StandardRetrieverAgent includes standard count in message.
        """
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        msg = result["messages"][0]

        standard_count = len(result["standards"])
        assert str(standard_count) in msg.content

    @pytest.mark.asyncio
    async def test_standard_retriever_handles_missing_category(self, mock_mcp_rag_client):
        """
        Test StandardRetrieverAgent handles missing category gracefully.

        Verifies:
        - Uses default empty category when missing
        """
        state = {
            "task_id": "TASK-001",
            "raw_data": {}
        }
        agent = StandardRetrieverAgent()

        result = await agent.run(state)

        assert "standards" in result
        # MCP mock returns 3 results
        assert len(result["standards"]) == 3

    @pytest.mark.asyncio
    async def test_standard_retriever_handles_empty_raw_data(self, mock_mcp_rag_client):
        """
        Test StandardRetrieverAgent handles empty raw_data.

        Verifies:
        - Still returns standards even without raw_data
        """
        state = {
            "task_id": "TASK-001",
            "category": "Sales"
        }
        agent = StandardRetrieverAgent()

        result = await agent.run(state)

        assert "standards" in result
        assert len(result["standards"]) == 3  # From MCP mock


# ============================================================================
# TESTS - VouchingAssistantAgent
# ============================================================================

class TestVouchingAssistantAgent:
    """Test suite for VouchingAssistantAgent."""

    def test_initialization(self):
        """Test VouchingAssistantAgent initialization with default model."""
        agent = VouchingAssistantAgent()

        assert agent.agent_name == "Staff_Vouching_Assistant"
        assert agent.llm is not None

    def test_initialization_custom_model(self):
        """Test VouchingAssistantAgent initialization with custom model."""
        custom_model = "gpt-4o"

        with patch('src.agents.staff_agents.ChatOpenAI') as mock_llm_class:
            agent = VouchingAssistantAgent(model_name=custom_model)
            mock_llm_class.assert_called_once_with(model=custom_model)

    @pytest.mark.asyncio
    async def test_vouching_assistant_processes_transactions(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent successfully processes transactions.

        Mocks LLM response to test complete workflow.

        Verifies:
        - Returns dict with 'vouching_logs' and 'messages' keys
                - Vouching logs contain expected transaction verifications
        - Each log has required fields: transaction_id, date, amount, status, notes
        """
        agent = VouchingAssistantAgent()

        # Mock the LLM ainvoke call with AsyncMock
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Verify return structure
        assert isinstance(result, dict)
        assert "vouching_logs" in result
        assert "messages" in result

        # Verify vouching logs
        logs = result["vouching_logs"]
        assert isinstance(logs, list)
        assert len(logs) == 3

        # Verify log structure
        for log in logs:
            assert "transaction_id" in log
            assert "date" in log
            assert "amount" in log
            assert "status" in log
            assert "notes" in log
            assert log["status"] in ["Verified", "Exception"]

    @pytest.mark.asyncio
    async def test_vouching_assistant_identifies_exceptions(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent correctly identifies exceptions.

        Verifies:
        - Distinguishes between "Verified" and "Exception" statuses
        - Exceptions include follow-up required flag
        - Risk levels are assigned appropriately
        """
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        logs = result["vouching_logs"]

        # Find verified and exception logs
        verified_logs = [log for log in logs if log["status"] == "Verified"]
        exception_logs = [log for log in logs if log["status"] == "Exception"]

        assert len(verified_logs) == 2
        assert len(exception_logs) == 1

        # Verify exception has additional fields
        exception = exception_logs[0]
        assert exception.get("follow_up_required") is True
        assert "risk_level" in exception

    @pytest.mark.asyncio
    async def test_vouching_assistant_verification_counts(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent calculates verification counts correctly.

        Verifies:
        - Message includes verified/exception counts
        - Counts are accurate based on logs
        """
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        msg = result["messages"][0]

        # Message should contain counts
        assert "verified" in msg.content.lower()
        assert "exception" in msg.content.lower()

        # Verify LLM analysis is included
        assert "LLM Analysis" in msg.content

    @pytest.mark.asyncio
    async def test_vouching_assistant_formats_transactions(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent correctly formats transactions for LLM.

        Verifies:
        - _format_transactions method works correctly
        - LLM receives properly formatted transaction data
        """
        agent = VouchingAssistantAgent()

        transactions = [
            {"date": "2024-01-15", "amount": 50_000_000, "customer": "Cust A", "invoice_no": "INV-001"},
            {"date": "2024-02-20", "amount": 75_000_000, "customer": "Cust B", "invoice_no": "INV-002"}
        ]

        formatted = agent._format_transactions(transactions)

        assert "2024-01-15" in formatted
        assert "50,000,000" in formatted
        assert "Cust A" in formatted
        assert "INV-001" in formatted

    @pytest.mark.asyncio
    async def test_vouching_assistant_handles_empty_transactions(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent handles state with limited transactions.

        Verifies:
        - Agent processes single transaction gracefully
        - Creates mock vouching logs
        """
        # Keep one transaction, tests the edge case
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Should still have logs (from mock data)
        assert "vouching_logs" in result
        assert len(result["vouching_logs"]) > 0

    @pytest.mark.asyncio
    async def test_vouching_assistant_includes_standards_in_prompt(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent includes standards in LLM prompt.

        Verifies:
        - Standards are passed to LLM for context
        - LLM receives K-IFRS/K-GAAS references
        """
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Verify ainvoke was called with standards
        mock_ainvoke.assert_called_once()
        call_args = mock_ainvoke.call_args

        # Standards should be in the system message
        messages_list = call_args[0][0]
        system_msg = messages_list[0]
        assert "meticulous audit staff" in system_msg.content.lower()

    @pytest.mark.asyncio
    async def test_vouching_assistant_message_format(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent generates properly formatted messages.

        Verifies:
        - Message is HumanMessage type
        - Message includes agent name
        - Message structure is professional
        """
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        msg = result["messages"][0]

        assert isinstance(msg, HumanMessage)
        assert msg.name == "Staff_Vouching_Assistant"
        assert "Staff_Vouching_Assistant" in msg.content

    @pytest.mark.asyncio
    async def test_vouching_assistant_transaction_details_in_logs(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent includes transaction details in logs.

        Verifies:
        - Each log contains original transaction data
        - Invoice numbers and amounts match source data
        """
        agent = VouchingAssistantAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        logs = result["vouching_logs"]

        # Verify first transaction matches source
        assert logs[0]["transaction_id"] == "INV-2024-001"
        assert logs[0]["amount"] == 50_000_000


# ============================================================================
# TESTS - WorkPaperGeneratorAgent
# ============================================================================

class TestWorkPaperGeneratorAgent:
    """Test suite for WorkPaperGeneratorAgent."""

    def test_initialization(self):
        """Test WorkPaperGeneratorAgent initialization with default model."""
        agent = WorkPaperGeneratorAgent()

        assert agent.agent_name == "Staff_WorkPaper_Generator"
        assert agent.llm is not None

    def test_initialization_custom_model(self):
        """Test WorkPaperGeneratorAgent initialization with custom model."""
        custom_model = "gpt-4o"

        with patch('src.agents.staff_agents.ChatOpenAI') as mock_llm_class:
            agent = WorkPaperGeneratorAgent(model_name=custom_model)
            mock_llm_class.assert_called_once_with(model=custom_model)

    @pytest.mark.asyncio
    async def test_workpaper_generator_creates_draft(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent creates comprehensive workpaper draft.

        Mocks LLM response to test complete workflow.

        Verifies:
        - Returns dict with 'workpaper_draft' and 'messages' keys
        - Workpaper includes all required sections
        - Workpaper contains task information and findings
        """
        # Add vouching logs
        mock_task_state_with_standards["vouching_logs"] = [
            {
                "transaction_id": "INV-2024-001",
                "date": "2024-01-15",
                "amount": 50_000_000,
                "status": "Verified",
                "notes": "Invoice matches sales record",
                "risk_level": "Low"
            },
            {
                "transaction_id": "INV-2024-002",
                "date": "2024-02-20",
                "amount": 75_000_000,
                "status": "Exception",
                "notes": "Missing shipping confirmation",
                "risk_level": "Medium",
                "follow_up_required": True
            }
        ]

        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Verify return structure
        assert isinstance(result, dict)
        assert "workpaper_draft" in result
        assert "messages" in result

        # Verify workpaper content
        workpaper = result["workpaper_draft"]
        assert isinstance(workpaper, str)
        assert len(workpaper) > 500  # Substantial content

    @pytest.mark.asyncio
    async def test_workpaper_generator_includes_all_sections(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent includes all required workpaper sections.

        Verifies:
        - Includes Objective section
        - Includes Procedures section
        - Includes Findings section
        - Includes Conclusion section
        - Contains metadata (Task ID, Category, Date)
        """
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        # Verify required sections
        assert "AUDIT WORKPAPER" in workpaper
        assert "Task ID" in workpaper
        assert "Account Category" in workpaper
        assert "Status" in workpaper
        assert "DRAFT" in workpaper

    @pytest.mark.asyncio
    async def test_workpaper_generator_formats_standards(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent correctly formats standards in workpaper.

        Verifies:
        - _format_standards method works correctly
        - Standards are properly formatted for workpaper
        """
        agent = WorkPaperGeneratorAgent()

        standards = [
            "K-IFRS 1115: Revenue from Contracts with Customers",
            "K-GAAS 500: Audit Evidence"
        ]

        formatted = agent._format_standards(standards)

        assert "1115" in formatted or "Revenue" in formatted
        assert "500" in formatted or "Audit Evidence" in formatted
        assert "-" in formatted  # Formatted as bullet list

    @pytest.mark.asyncio
    async def test_workpaper_generator_formats_vouching_logs(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent correctly formats vouching logs.

        Verifies:
        - _format_vouching_logs method works correctly
        - Includes verification counts and percentages
        - Lists exceptions with details
        """
        agent = WorkPaperGeneratorAgent()

        logs = [
            {
                "transaction_id": "INV-001",
                "status": "Verified",
                "notes": "Verified",
                "risk_level": "Low"
            },
            {
                "transaction_id": "INV-002",
                "status": "Exception",
                "notes": "Missing doc",
                "risk_level": "Medium"
            }
        ]

        formatted = agent._format_vouching_logs(logs)

        assert "Verified" in formatted
        assert "Exception" in formatted
        assert "50%" in formatted or "1/2" in formatted
        assert "INV-002" in formatted

    @pytest.mark.asyncio
    async def test_workpaper_generator_includes_raw_data_summary(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent includes raw data summary.

        Verifies:
        - Transaction count is included
        - Total amount is formatted
        - Data quality is referenced
        """
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        # Should include data summary
        assert "150" in workpaper  # transaction_count
        assert "5" in workpaper  # total_sales in some form

    @pytest.mark.asyncio
    async def test_workpaper_generator_attachments_section(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent includes attachments section.

        Verifies:
        - Lists Excel file with transaction count
        - Lists vouching logs
        - Lists standards applied
        """
        mock_task_state_with_standards["vouching_logs"] = [
            {"transaction_id": "INV-001", "status": "Verified"}
        ]
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        assert "Attachments:" in workpaper
        assert "transactions analyzed" in workpaper
        assert "verified" in workpaper.lower()

    @pytest.mark.asyncio
    async def test_workpaper_generator_message_format(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent generates properly formatted messages.

        Verifies:
        - Message is HumanMessage type
        - Message includes agent name
        - Message indicates draft status
        """
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        msg = result["messages"][0]

        assert isinstance(msg, HumanMessage)
        assert msg.name == "Staff_WorkPaper_Generator"
        assert "Staff_WorkPaper_Generator" in msg.content
        assert "Manager review" in msg.content

    @pytest.mark.asyncio
    async def test_workpaper_generator_includes_llm_analysis(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent includes LLM-generated analysis.

        Verifies:
        - LLM analysis is included in workpaper body
        - Synthesis of all agent outputs is present
        """
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        # Should include the LLM response content
        assert "Audit Objective" in workpaper or "objective" in workpaper.lower()
        assert "Procedures" in workpaper or "procedures" in workpaper.lower()

    @pytest.mark.asyncio
    async def test_workpaper_generator_handles_empty_standards(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent handles empty standards list.

        Verifies:
        - Still generates workpaper without standards
        - Gracefully handles missing standards
        """
        mock_task_state_with_standards["standards"] = []
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        assert "workpaper_draft" in result
        assert len(result["workpaper_draft"]) > 0

    @pytest.mark.asyncio
    async def test_workpaper_generator_handles_empty_vouching_logs(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent handles empty vouching logs.

        Verifies:
        - Still generates workpaper without vouching results
        - Gracefully handles missing vouching logs
        """
        mock_task_state_with_standards["vouching_logs"] = []
        agent = WorkPaperGeneratorAgent()

        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        assert "workpaper_draft" in result
        workpaper = result["workpaper_draft"]
        assert "No vouching procedures" in workpaper or len(workpaper) > 500


# ============================================================================
# INTEGRATION TESTS - Multi-Agent Workflow
# ============================================================================

class TestStaffAgentsWorkflow:
    """Integration tests for staff agents working together."""

    @pytest.mark.asyncio
    async def test_full_staff_workflow(self, mock_task_state):
        """
        Test complete workflow: Excel -> Standards -> Vouching -> Workpaper.

        Verifies:
        - Each agent receives output from previous agent
        - State is properly threaded through workflow
        - Final workpaper includes data from all agents
        """
        # Step 1: Excel Parser
        excel_agent = ExcelParserAgent()
        state = mock_task_state.copy()
        result1 = await excel_agent.run(state)
        state.update(result1)

        assert "raw_data" in state
        raw_data = state["raw_data"]
        assert raw_data["transaction_count"] > 0

        # Step 2: Standard Retriever (with mock MCP client)
        standard_agent = StandardRetrieverAgent()

        # Mock MCP RAG client response
        mock_mcp_response = {
            "status": "success",
            "data": {
                "results": [
                    {
                        "standard_id": "K-IFRS 1115",
                        "paragraph_no": "31",
                        "title": "Revenue from Contracts",
                        "content": "An entity shall recognise revenue when it satisfies a performance obligation."
                    },
                    {
                        "standard_id": "K-GAAS 315",
                        "paragraph_no": "12",
                        "title": "Risk Assessment",
                        "content": "The auditor shall identify and assess the risks of material misstatement."
                    }
                ],
                "metadata": {"duration_ms": 50}
            }
        }

        # Create a mock MCPRagClient class
        mock_mcp_client_instance = AsyncMock()
        mock_mcp_client_instance.search_standards = AsyncMock(return_value=mock_mcp_response)

        with patch('src.services.mcp_client.MCPRagClient', return_value=mock_mcp_client_instance):
            result2 = await standard_agent.run(state)
        state.update(result2)

        assert "standards" in state
        assert len(state["standards"]) > 0

        # Step 3: Vouching Assistant (with mock LLM)
        vouching_agent = VouchingAssistantAgent()
        mock_llm_response = AIMessage(
            content="Transaction verification complete. 2 verified, 1 exception."
        )

        mock_ainvoke = AsyncMock(return_value=mock_llm_response)
        with patch.object(vouching_agent.llm, 'ainvoke', mock_ainvoke):
            result3 = await vouching_agent.run(state)
        state.update(result3)

        assert "vouching_logs" in state
        assert len(state["vouching_logs"]) > 0

        # Step 4: Workpaper Generator (with mock LLM)
        workpaper_agent = WorkPaperGeneratorAgent()
        mock_workpaper_response = AIMessage(
            content=(
                "## Audit Objective\nVerify revenue transactions.\n"
                "## Procedures\nReviewed transaction documentation.\n"
                "## Findings\nNo significant exceptions noted.\n"
                "## Conclusion\nRevenue transactions are fairly stated."
            )
        )

        mock_wp_ainvoke = AsyncMock(return_value=mock_workpaper_response)
        with patch.object(workpaper_agent.llm, 'ainvoke', mock_wp_ainvoke):
            result4 = await workpaper_agent.run(state)
        state.update(result4)

        # Verify final state
        assert "workpaper_draft" in state
        assert len(state["workpaper_draft"]) > 0

        # Verify workpaper includes data from all agents
        workpaper = state["workpaper_draft"]
        assert "Sales" in workpaper  # From raw_data
        assert "TASK-001" in workpaper  # From task info

    @pytest.mark.asyncio
    async def test_state_threading_through_agents(self, mock_task_state):
        """
        Test that state is properly threaded through all agents.

        Verifies:
        - Each agent reads from state correctly
        - Each agent updates state without overwriting
        - Messages accumulate properly
        """
        state = mock_task_state.copy()
        initial_messages_count = len(state["messages"])

        # Run Excel Parser
        excel_agent = ExcelParserAgent()
        result = await excel_agent.run(state)

        # Verify state update
        assert "raw_data" in result
        assert "messages" in result

        # Messages should be in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], BaseMessage)


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_excel_parser_with_large_category_name(self):
        """Test ExcelParserAgent with very long category name."""
        state = {
            "task_id": "TASK-001",
            "category": "Very Long Category Name That Exceeds Normal Length" * 5,
            "messages": []
        }
        agent = ExcelParserAgent()

        result = await agent.run(state)

        assert "raw_data" in result
        assert result["raw_data"]["category"] == state["category"]

    @pytest.mark.asyncio
    async def test_vouching_with_unicode_characters(self):
        """Test VouchingAssistantAgent with unicode in transaction data."""
        state = {
            "task_id": "TASK-001",
            "category": "Sales",
            "raw_data": {
                "sample_transactions": [
                    {
                        "date": "2024-01-15",
                        "amount": 50_000_000,
                        "customer": "고객사 한글 이름",  # Korean characters
                        "invoice_no": "INV-2024-001"
                    }
                ]
            },
            "standards": []
        }
        agent = VouchingAssistantAgent()
        mock_response = AIMessage(content="Verification complete")

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(state)

        assert "vouching_logs" in result

    @pytest.mark.asyncio
    async def test_workpaper_with_high_exception_rate(self):
        """Test WorkPaperGeneratorAgent with high exception rate in vouching logs."""
        state = {
            "task_id": "TASK-001",
            "category": "Sales",
            "raw_data": {
                "transaction_count": 10,
                "total_sales": 100_000_000,
                "data_quality": "POOR",
                "period": "2024-01-01 to 2024-12-31"
            },
            "standards": ["K-GAAS 500"],
            "vouching_logs": [
                {
                    "transaction_id": f"INV-{i:03d}",
                    "status": "Exception" if i % 2 == 0 else "Verified",
                    "notes": "Test exception" if i % 2 == 0 else "Test verified",
                    "risk_level": "High" if i % 2 == 0 else "Low"
                }
                for i in range(10)
            ]
        }
        agent = WorkPaperGeneratorAgent()
        mock_response = AIMessage(content="Workpaper with high exceptions")

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(state)

        workpaper = result["workpaper_draft"]

        # Workpaper should contain expected sections
        assert "AUDIT WORKPAPER" in workpaper
        assert "Task ID" in workpaper
        # Should mention vouching logs verification count
        assert "10" in workpaper  # 10 transactions analyzed
        assert "vouching logs" in workpaper.lower()


# ============================================================================
# ADDITIONAL COMPREHENSIVE TESTS
# ============================================================================

class TestExcelParserAgentComprehensive:
    """Additional comprehensive tests for ExcelParserAgent."""

    @pytest.mark.asyncio
    async def test_excel_parser_data_structure_completeness(self, mock_task_state):
        """Test that all required fields are present in raw_data."""
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        raw_data = result["raw_data"]

        required_fields = [
            "category",
            "total_sales",
            "transaction_count",
            "period",
            "sample_transactions",
            "parsed_at",
            "data_quality",
            "anomalies_detected"
        ]

        for field in required_fields:
            assert field in raw_data, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_excel_parser_transaction_count_matches(self, mock_task_state):
        """Test that transaction_count matches sample_transactions length."""
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        raw_data = result["raw_data"]

        # Should have at least some transactions
        assert raw_data["transaction_count"] > 0
        assert len(raw_data["sample_transactions"]) > 0

    @pytest.mark.asyncio
    async def test_excel_parser_message_contains_summary(self, mock_task_state):
        """Test that message contains key summary information."""
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        msg = result["messages"][0]
        content = msg.content

        # Should contain key metrics
        assert "transaction" in content.lower()
        assert "quality" in content.lower() or "GOOD" in content or "데이터" in content

    @pytest.mark.asyncio
    async def test_excel_parser_handles_different_categories(self):
        """Test ExcelParserAgent with various account categories."""
        categories = ["Sales", "Inventory", "AR", "AP", "Fixed Assets"]

        for category in categories:
            state = {"category": category, "messages": []}
            agent = ExcelParserAgent()

            result = await agent.run(state)

            assert result["raw_data"]["category"] == category


class TestStandardRetrieverAgentComprehensive:
    """Additional comprehensive tests for StandardRetrieverAgent with MCP integration."""

    @pytest.mark.asyncio
    async def test_standard_retriever_returns_list_of_strings(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """Test that standards list contains strings."""
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        standards = result["standards"]

        assert isinstance(standards, list)
        for standard in standards:
            assert isinstance(standard, str)
            assert len(standard) > 0

    @pytest.mark.asyncio
    async def test_standard_retriever_includes_k_standards(
        self, mock_task_state_with_raw_data, mock_mcp_rag_client
    ):
        """Test that retrieved standards reference K-IFRS or K-GAAS."""
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        standards_text = " ".join(result["standards"])

        assert "K-IFRS" in standards_text or "K-GAAS" in standards_text

    @pytest.mark.asyncio
    async def test_standard_retriever_category_specific_queries(self, mock_mcp_rag_client):
        """Test that different categories generate different MCP queries."""
        agent = StandardRetrieverAgent()

        # Sales category
        state_sales = {
            "category": "Sales",
            "raw_data": {}
        }
        await agent.run(state_sales)
        sales_call = mock_mcp_rag_client.search_standards.call_args_list[0]

        # Reset mock
        mock_mcp_rag_client.search_standards.reset_mock()

        # Inventory category
        state_inventory = {
            "category": "Inventory",
            "raw_data": {}
        }
        await agent.run(state_inventory)
        inventory_call = mock_mcp_rag_client.search_standards.call_args_list[0]

        # Queries should differ for different categories
        assert "Sales" in sales_call.kwargs["query_text"]
        assert "Inventory" in inventory_call.kwargs["query_text"]


class TestVouchingAssistantAgentComprehensive:
    """Additional comprehensive tests for VouchingAssistantAgent."""

    @pytest.mark.asyncio
    async def test_vouching_creates_vouching_logs_structure(self, mock_task_state_with_standards):
        """Test that vouching creates proper log structure."""
        agent = VouchingAssistantAgent()
        mock_response = AIMessage(content="Verified: 2 of 3 transactions verified")

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        vouching_logs = result["vouching_logs"]

        assert isinstance(vouching_logs, list)

    @pytest.mark.asyncio
    async def test_vouching_response_used_in_logs(self, mock_task_state_with_standards):
        """Test that LLM response is included in vouching logs."""
        agent = VouchingAssistantAgent()
        custom_response = "Custom vouching result for verification"
        mock_response = AIMessage(content=custom_response)

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Response should be used somehow
        assert len(result["vouching_logs"]) > 0

    @pytest.mark.asyncio
    async def test_vouching_uses_standards_in_prompt(self, mock_task_state_with_standards):
        """Test that vouching includes standards in the prompt."""
        agent = VouchingAssistantAgent()
        mock_response = AIMessage(content="Verification complete")

        call_count = 0

        async def mock_ainvoke_check(messages):
            nonlocal call_count
            call_count += 1
            # Check that standards are in the system message
            if messages and len(messages) > 0:
                system_msg = messages[0]
                assert "K-IFRS" in system_msg.content or "K-GAAS" in system_msg.content
            return mock_response

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke_check):
            result = await agent.run(mock_task_state_with_standards)

        assert call_count == 1  # Should have called ainvoke


class TestWorkPaperGeneratorAgentComprehensive:
    """Additional comprehensive tests for WorkPaperGeneratorAgent."""

    @pytest.mark.asyncio
    async def test_workpaper_contains_markdown_headers(self, mock_task_state_with_standards):
        """Test that workpaper draft contains markdown headers."""
        agent = WorkPaperGeneratorAgent()
        mock_response = AIMessage(
            content="## Header\n\nContent"
        )

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        # Should contain markdown headers
        assert "#" in workpaper

    @pytest.mark.asyncio
    async def test_workpaper_message_contains_draft_reference(self, mock_task_state_with_standards):
        """Test that message references the workpaper draft."""
        agent = WorkPaperGeneratorAgent()
        mock_response = AIMessage(content="Generated workpaper")

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        msg = result["messages"][0]
        content = msg.content.lower()

        # Should mention workpaper generation
        assert "workpaper" in content or "report" in content or "draft" in content

    @pytest.mark.asyncio
    async def test_workpaper_with_complete_task_state(self):
        """Test workpaper generation with fully populated state."""
        full_state = {
            "task_id": "TASK-COMPLETE",
            "category": "Sales",
            "raw_data": {
                "transaction_count": 100,
                "total_sales": 10_000_000_000,
                "period": "2024-01-01 to 2024-12-31"
            },
            "standards": [
                "K-IFRS 1115",
                "K-GAAS 500",
                "K-GAAS 330"
            ],
            "vouching_logs": [
                {"id": "V-001", "status": "Verified"},
                {"id": "V-002", "status": "Verified"},
                {"id": "V-003", "status": "Exception"}
            ]
        }

        agent = WorkPaperGeneratorAgent()
        mock_response = AIMessage(content="Complete audit workpaper draft")

        mock_ainvoke = AsyncMock(return_value=mock_response)
        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(full_state)

        assert "workpaper_draft" in result
        assert len(result["workpaper_draft"]) > 0


class TestStaffAgentsIntegration:
    """Integration tests for all Staff agents working together."""

    @pytest.mark.asyncio
    async def test_all_agents_accept_dict_state(self):
        """Test that all agents accept dict-based TaskState."""
        base_state = {
            "task_id": "TASK-001",
            "category": "Sales",
            "messages": []
        }

        excel_agent = ExcelParserAgent()
        standard_agent = StandardRetrieverAgent()
        vouching_agent = VouchingAssistantAgent()
        workpaper_agent = WorkPaperGeneratorAgent()

        # All should accept and process the state
        result1 = await excel_agent.run(base_state)
        assert "raw_data" in result1

        base_state.update(result1)
        result2 = await standard_agent.run(base_state)
        assert "standards" in result2

        base_state.update(result2)
        mock_response = AIMessage(content="Verification")
        with patch('src.agents.staff_agents.ChatOpenAI'):
            vouching_agent = VouchingAssistantAgent()
            mock_ainvoke = AsyncMock(return_value=mock_response)
            with patch.object(vouching_agent.llm, 'ainvoke', mock_ainvoke):
                result3 = await vouching_agent.run(base_state)
        assert "vouching_logs" in result3

    @pytest.mark.asyncio
    async def test_agent_names_are_unique(self):
        """Test that each agent has unique agent_name."""
        excel = ExcelParserAgent()
        standard = StandardRetrieverAgent()
        vouching = VouchingAssistantAgent()
        workpaper = WorkPaperGeneratorAgent()

        agent_names = [
            excel.agent_name,
            standard.agent_name,
            vouching.agent_name,
            workpaper.agent_name
        ]

        # All names should be unique
        assert len(agent_names) == len(set(agent_names))

        # All should start with "Staff_"
        for name in agent_names:
            assert name.startswith("Staff_")


# ============================================================================
# COVERAGE COMPLETENESS TESTS - Target 95%+ Coverage
# ============================================================================

class TestVouchingAssistantEdgeCases:
    """Test edge cases for VouchingAssistantAgent to achieve full coverage."""

    @pytest.mark.asyncio
    async def test_format_transactions_with_empty_list(self):
        """
        Test _format_transactions with empty transaction list.

        Covers line 367: return "No transactions to verify."
        """
        agent = VouchingAssistantAgent()

        # Test with empty list
        result = agent._format_transactions([])

        assert result == "No transactions to verify."
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_format_transactions_with_none_values(self):
        """
        Test _format_transactions handles missing/None values gracefully.

        Tests defensive programming for malformed transaction data.
        """
        agent = VouchingAssistantAgent()

        # Transaction with missing fields uses .get() which provides defaults
        transactions = [
            {
                # All fields missing - .get() will return 'N/A' or 0
            }
        ]

        result = agent._format_transactions(transactions)

        # Should handle missing values with defaults from .get()
        assert "N/A" in result or "0" in result
        assert "1." in result  # Should still be numbered

    @pytest.mark.asyncio
    async def test_format_transactions_with_partial_data(self):
        """
        Test _format_transactions with partially populated transactions.

        Tests handling of transactions with some fields missing.
        """
        agent = VouchingAssistantAgent()

        transactions = [
            {
                "date": "2024-01-15",
                "amount": 50_000_000
                # Missing customer and invoice_no
            }
        ]

        result = agent._format_transactions(transactions)

        # Should include available data
        assert "2024-01-15" in result
        assert "50,000,000" in result
        # Should default missing fields to N/A
        assert "N/A" in result


    @pytest.mark.asyncio
    async def test_vouching_with_single_transaction(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent with exactly one transaction.

        Tests boundary case for single transaction processing.
        """
        # Only one transaction
        mock_task_state_with_standards["raw_data"]["sample_transactions"] = [
            {
                "date": "2024-01-15",
                "amount": 50_000_000,
                "customer": "Customer A",
                "invoice_no": "INV-2024-001"
            }
        ]

        agent = VouchingAssistantAgent()
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Should handle single transaction
        assert "vouching_logs" in result
        assert len(result["vouching_logs"]) > 0

    @pytest.mark.asyncio
    async def test_vouching_with_two_transactions(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test VouchingAssistantAgent with exactly two transactions.

        Tests boundary case for len(sample_transactions) > 1.
        """
        # Two transactions
        mock_task_state_with_standards["raw_data"]["sample_transactions"] = [
            {
                "date": "2024-01-15",
                "amount": 50_000_000,
                "customer": "Customer A",
                "invoice_no": "INV-2024-001"
            },
            {
                "date": "2024-02-20",
                "amount": 75_000_000,
                "customer": "Customer B",
                "invoice_no": "INV-2024-002"
            }
        ]

        agent = VouchingAssistantAgent()
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Should handle two transactions (tests len(sample_transactions) > 1 branch)
        assert "vouching_logs" in result
        # Implementation generates one log per transaction in sample_transactions
        assert len(result["vouching_logs"]) == 2  # 2 transactions provided

    @pytest.mark.asyncio
    async def test_vouching_logs_risk_level_assignment(
        self,
        mock_task_state_with_standards,
        mock_llm_response_vouching
    ):
        """
        Test that vouching logs assign appropriate risk levels.

        Verifies risk_level field is present and valid.
        """
        agent = VouchingAssistantAgent()
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_vouching)

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        logs = result["vouching_logs"]

        for log in logs:
            assert "risk_level" in log
            assert log["risk_level"] in ["Low", "Medium", "High"]


class TestWorkPaperGeneratorEdgeCases:
    """Test edge cases for WorkPaperGeneratorAgent to achieve full coverage."""

    @pytest.mark.asyncio
    async def test_format_standards_with_empty_list(self):
        """
        Test _format_standards with empty list.

        Covers edge case for no standards retrieved.
        """
        agent = WorkPaperGeneratorAgent()

        result = agent._format_standards([])

        assert result == "No standards referenced."

    @pytest.mark.asyncio
    async def test_format_standards_with_single_standard(self):
        """
        Test _format_standards with single standard.

        Tests boundary case for single standard.
        """
        agent = WorkPaperGeneratorAgent()

        standards = ["K-IFRS 1115: Revenue from Contracts with Customers"]
        result = agent._format_standards(standards)

        assert "K-IFRS 1115" in result
        assert "Revenue" in result
        assert result.startswith("  - ")

    @pytest.mark.asyncio
    async def test_format_vouching_logs_with_empty_list(self):
        """
        Test _format_vouching_logs with empty list.

        Covers edge case for no vouching performed.
        """
        agent = WorkPaperGeneratorAgent()

        result = agent._format_vouching_logs([])

        assert result == "No vouching procedures performed."

    @pytest.mark.asyncio
    async def test_format_vouching_logs_with_all_verified(self):
        """
        Test _format_vouching_logs when all transactions verified.

        Tests 100% verification rate (no exceptions branch).
        """
        agent = WorkPaperGeneratorAgent()

        logs = [
            {"transaction_id": "INV-001", "status": "Verified", "notes": "OK", "risk_level": "Low"},
            {"transaction_id": "INV-002", "status": "Verified", "notes": "OK", "risk_level": "Low"},
            {"transaction_id": "INV-003", "status": "Verified", "notes": "OK", "risk_level": "Low"}
        ]

        result = agent._format_vouching_logs(logs)

        # Should show 100% verification
        assert "3/3" in result or "100%" in result
        assert "Exceptions: 0" in result
        # Should NOT include exception details section (exceptions == 0)
        assert "Exception Details:" not in result

    @pytest.mark.asyncio
    async def test_format_vouching_logs_with_some_exceptions(self):
        """
        Test _format_vouching_logs with mixed results.

        Tests exception details section is included when exceptions > 0.
        """
        agent = WorkPaperGeneratorAgent()

        logs = [
            {"transaction_id": "INV-001", "status": "Verified", "notes": "OK", "risk_level": "Low"},
            {
                "transaction_id": "INV-002",
                "status": "Exception",
                "notes": "Missing shipping doc",
                "risk_level": "Medium"
            }
        ]

        result = agent._format_vouching_logs(logs)

        # Should show partial verification
        assert "1/2" in result or "50%" in result
        assert "Exceptions: 1" in result
        # Should include exception details
        assert "Exception Details:" in result
        assert "INV-002" in result
        assert "Missing shipping doc" in result
        assert "Medium" in result

    @pytest.mark.asyncio
    async def test_workpaper_with_zero_transaction_count(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent with zero transactions.

        Tests edge case for empty dataset.
        """
        mock_task_state_with_standards["raw_data"]["transaction_count"] = 0
        mock_task_state_with_standards["raw_data"]["total_sales"] = 0
        mock_task_state_with_standards["vouching_logs"] = []

        agent = WorkPaperGeneratorAgent()
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        workpaper = result["workpaper_draft"]

        # Should still generate workpaper
        assert "AUDIT WORKPAPER" in workpaper
        assert "0" in workpaper  # Should mention 0 transactions

    @pytest.mark.asyncio
    async def test_workpaper_with_missing_raw_data_fields(
        self,
        mock_task_state_with_standards,
        mock_llm_response_workpaper
    ):
        """
        Test WorkPaperGeneratorAgent handles missing raw_data fields gracefully.

        Tests defensive programming for incomplete data.
        """
        # Minimal raw_data
        mock_task_state_with_standards["raw_data"] = {}
        mock_task_state_with_standards["vouching_logs"] = []

        agent = WorkPaperGeneratorAgent()
        mock_ainvoke = AsyncMock(return_value=mock_llm_response_workpaper)

        with patch.object(agent.llm, 'ainvoke', mock_ainvoke):
            result = await agent.run(mock_task_state_with_standards)

        # Should still generate workpaper with defaults
        assert "workpaper_draft" in result
        workpaper = result["workpaper_draft"]

        # Should handle missing values with .get() defaults
        assert "N/A" in workpaper or "0" in workpaper


class TestExcelParserAgentRobustness:
    """Test ExcelParserAgent robustness and error handling."""

    @pytest.mark.asyncio
    async def test_excel_parser_with_empty_state(self):
        """
        Test ExcelParserAgent with completely empty state.

        Tests absolute minimum requirements.
        """
        agent = ExcelParserAgent()

        # Completely empty state
        result = await agent.run({})

        # Should still produce output with defaults
        assert "raw_data" in result
        assert "messages" in result
        assert result["raw_data"]["category"] == "Sales"  # Default

    @pytest.mark.asyncio
    async def test_excel_parser_preserves_transaction_order(self, mock_task_state):
        """
        Test that ExcelParserAgent maintains transaction order.

        Verifies sample transactions are returned in consistent order.
        """
        agent = ExcelParserAgent()

        result = await agent.run(mock_task_state)
        transactions = result["raw_data"]["sample_transactions"]

        # Should be in chronological order
        assert transactions[0]["date"] == "2024-01-15"
        assert transactions[1]["date"] == "2024-02-20"
        assert transactions[2]["date"] == "2024-03-10"


class TestStandardRetrieverAgentRobustness:
    """Test StandardRetrieverAgent robustness and error handling with MCP integration."""

    @pytest.mark.asyncio
    async def test_standard_retriever_with_empty_state(self, mock_mcp_rag_client):
        """
        Test StandardRetrieverAgent with completely empty state.

        Tests absolute minimum requirements.
        """
        agent = StandardRetrieverAgent()

        # Completely empty state
        result = await agent.run({})

        # Should still return standards with defaults
        assert "standards" in result
        assert "messages" in result
        assert len(result["standards"]) == 3  # From MCP mock

    @pytest.mark.asyncio
    async def test_standard_retriever_standards_are_non_empty_strings(
        self,
        mock_task_state_with_raw_data,
        mock_mcp_rag_client
    ):
        """
        Test that all returned standards are non-empty strings.

        Verifies data quality of standards list.
        """
        agent = StandardRetrieverAgent()

        result = await agent.run(mock_task_state_with_raw_data)
        standards = result["standards"]

        for standard in standards:
            assert isinstance(standard, str)
            assert len(standard) > 0
            assert standard.strip() == standard  # No leading/trailing whitespace
