"""
Comprehensive Unit Tests for EGA Parser Node

Target Coverage:
- ega_parser_node() - Main LangGraph node for EGA extraction
- parse_assigned_workflow() - Core parsing function
- Helper functions for data extraction and normalization
- EGA data class and enums
- Fallback behavior when MCP unavailable

Coverage Target: 80%+
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
from datetime import datetime

from src.graph.nodes.ega_parser import (
    ega_parser_node,
    parse_assigned_workflow,
    EGA,
    EGAParseResult,
    EGARiskLevel,
    EGAStatus,
    get_ega_summary,
    filter_egas_by_risk,
    sort_egas_by_priority,
    _generate_ega_id,
    _normalize_column_name,
    _parse_risk_level,
    _parse_priority,
    _extract_egas_from_data,
    _get_field_value,
    _build_ega_hierarchy,
    _get_fallback_egas,
    _generate_egas_from_plan,
    COLUMN_MAPPINGS,
)
from src.graph.state import AuditState


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def base_audit_state() -> AuditState:
    """Create a base AuditState for testing."""
    return {
        "messages": [],
        "project_id": "PROJECT-001",
        "client_name": "테스트 제조회사",
        "fiscal_year": 2024,
        "overall_materiality": 1000000.0,
        "audit_plan": {},
        "tasks": [],
        "next_action": "CONTINUE",
        "is_approved": False,
        "shared_documents": [],
        "interview_complete": False,
        "interview_phase": 1,
        "interview_responses": [],
        "specification": {},
        "egas": [],
        "urgency_config": {},
    }


@pytest.fixture
def state_with_workflow_doc(base_audit_state) -> AuditState:
    """Create state with a workflow document."""
    base_audit_state["shared_documents"] = [
        {
            "type": "assigned_workflow",
            "name": "Assigned_Workflow_2024.xlsx",
            "file_path": "/path/to/Assigned_Workflow_2024.xlsx",
            "uploaded_at": datetime.utcnow().isoformat(),
        }
    ]
    return base_audit_state


@pytest.fixture
def state_with_audit_plan(base_audit_state) -> AuditState:
    """Create state with audit plan for EGA generation."""
    base_audit_state["audit_plan"] = {
        "audit_areas": [
            {
                "name": "Revenue Recognition",
                "description": "Test revenue in accordance with K-IFRS 1115",
                "risk_level": "high",
            },
            {
                "name": "Inventory Valuation",
                "description": "Verify inventory at lower of cost or NRV",
                "risk_level": "medium",
            },
            {
                "name": "Accounts Payable",
                "description": "Test completeness of AP at year-end",
                "risk_level": "critical",
            },
        ],
        "objectives": ["Financial statement accuracy", "Compliance with K-IFRS"],
    }
    return base_audit_state


@pytest.fixture
def sample_excel_data() -> Dict[str, Any]:
    """Create sample Excel data structure."""
    return {
        "transactions": [
            {
                "EGA Name": "Revenue Testing",
                "Description": "Test revenue recognition procedures",
                "Risk Level": "High",
                "Priority": 85,
                "Category": "Revenue",
                "Assertion": "Completeness, Accuracy",
            },
            {
                "EGA Name": "Inventory Count",
                "Description": "Observe physical inventory count",
                "Risk Level": "Medium",
                "Priority": 70,
                "Category": "Inventory",
                "Assertion": "Existence, Valuation",
            },
            {
                "EGA Name": "AP Cutoff Testing",
                "Description": "Test AP cutoff procedures",
                "Risk Level": "Critical",
                "Priority": 95,
                "Category": "Payables",
                "Assertion": "Completeness, Cut-off",
            },
        ],
        "summary": {
            "total_amount": 0,
            "transaction_count": 3,
        },
    }


@pytest.fixture
def sample_ega() -> EGA:
    """Create a sample EGA for testing."""
    return EGA(
        id="ega-test123",
        project_id="PROJECT-001",
        name="Revenue Testing",
        description="Test revenue recognition procedures",
        risk_level=EGARiskLevel.HIGH,
        priority=85,
        status=EGAStatus.PENDING,
        source_row=1,
        source_sheet="Sheet1",
        metadata={"category": "Revenue", "assertion": "Completeness"},
    )


# ============================================================================
# EGA DATA CLASS TESTS
# ============================================================================


class TestEGADataClass:
    """Tests for the EGA dataclass."""

    def test_ega_creation(self, sample_ega: EGA):
        """Test EGA creation with all fields."""
        assert sample_ega.id == "ega-test123"
        assert sample_ega.project_id == "PROJECT-001"
        assert sample_ega.name == "Revenue Testing"
        assert sample_ega.risk_level == EGARiskLevel.HIGH
        assert sample_ega.priority == 85
        assert sample_ega.status == EGAStatus.PENDING

    def test_ega_to_dict(self, sample_ega: EGA):
        """Test EGA to_dict conversion."""
        ega_dict = sample_ega.to_dict()

        assert ega_dict["id"] == "ega-test123"
        assert ega_dict["name"] == "Revenue Testing"
        assert ega_dict["risk_level"] == "high"
        assert ega_dict["status"] == "pending"
        assert "created_at" in ega_dict
        assert "updated_at" in ega_dict

    def test_ega_default_values(self):
        """Test EGA creation with default values."""
        ega = EGA(
            id="ega-default",
            project_id="proj-123",
            name="Test EGA",
            description="Test description",
        )

        assert ega.risk_level == EGARiskLevel.MEDIUM
        assert ega.priority == 50
        assert ega.status == EGAStatus.PENDING
        assert ega.task_count == 0
        assert ega.progress == 0.0
        assert ega.parent_ega_id is None

    def test_ega_with_parent(self):
        """Test EGA with parent relationship."""
        parent = EGA(
            id="ega-parent",
            project_id="proj-123",
            name="Parent EGA",
            description="Parent description",
        )

        child = EGA(
            id="ega-child",
            project_id="proj-123",
            name="Child EGA",
            description="Child description",
            parent_ega_id=parent.id,
        )

        assert child.parent_ega_id == "ega-parent"


class TestEGAEnums:
    """Tests for EGA enums."""

    def test_risk_level_values(self):
        """Test EGARiskLevel enum values."""
        assert EGARiskLevel.CRITICAL.value == "critical"
        assert EGARiskLevel.HIGH.value == "high"
        assert EGARiskLevel.MEDIUM.value == "medium"
        assert EGARiskLevel.LOW.value == "low"

    def test_status_values(self):
        """Test EGAStatus enum values."""
        assert EGAStatus.PENDING.value == "pending"
        assert EGAStatus.IN_PROGRESS.value == "in_progress"
        assert EGAStatus.REVIEW_REQUIRED.value == "review_required"
        assert EGAStatus.COMPLETED.value == "completed"


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


class TestGenerateEGAId:
    """Tests for _generate_ega_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [_generate_ega_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_id_format(self):
        """Test ID format."""
        ega_id = _generate_ega_id()
        assert ega_id.startswith("ega-")
        assert len(ega_id) == 16  # "ega-" + 12 hex chars


class TestNormalizeColumnName:
    """Tests for _normalize_column_name function."""

    def test_exact_match(self):
        """Test exact column name match."""
        assert _normalize_column_name("EGA") == "name"
        assert _normalize_column_name("Description") == "description"
        assert _normalize_column_name("Risk Level") == "risk_level"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert _normalize_column_name("ega") == "name"
        assert _normalize_column_name("DESCRIPTION") == "description"
        assert _normalize_column_name("risk level") == "risk_level"

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert _normalize_column_name("  EGA  ") == "name"
        assert _normalize_column_name("\tDescription\t") == "description"

    def test_variations(self):
        """Test various column name variations."""
        # Name variations
        assert _normalize_column_name("Activity Name") == "name"
        assert _normalize_column_name("Task Name") == "name"

        # Description variations
        assert _normalize_column_name("Desc") == "description"
        assert _normalize_column_name("Details") == "description"

        # Risk variations
        assert _normalize_column_name("Risk Rating") == "risk_level"
        assert _normalize_column_name("Risk Assessment") == "risk_level"

    def test_unrecognized_column(self):
        """Test unrecognized column name."""
        assert _normalize_column_name("Unknown Column") is None
        assert _normalize_column_name("Random") is None


class TestParseRiskLevel:
    """Tests for _parse_risk_level function."""

    def test_string_values(self):
        """Test parsing string risk levels."""
        assert _parse_risk_level("critical") == EGARiskLevel.CRITICAL
        assert _parse_risk_level("high") == EGARiskLevel.HIGH
        assert _parse_risk_level("medium") == EGARiskLevel.MEDIUM
        assert _parse_risk_level("low") == EGARiskLevel.LOW

    def test_case_insensitivity(self):
        """Test case insensitivity."""
        assert _parse_risk_level("HIGH") == EGARiskLevel.HIGH
        assert _parse_risk_level("Medium") == EGARiskLevel.MEDIUM
        assert _parse_risk_level("LOW") == EGARiskLevel.LOW

    def test_alternate_names(self):
        """Test alternate risk level names."""
        assert _parse_risk_level("very high") == EGARiskLevel.CRITICAL
        assert _parse_risk_level("moderate") == EGARiskLevel.MEDIUM
        assert _parse_risk_level("minimal") == EGARiskLevel.LOW

    def test_numeric_values(self):
        """Test parsing numeric risk levels."""
        assert _parse_risk_level(4) == EGARiskLevel.CRITICAL
        assert _parse_risk_level(3) == EGARiskLevel.HIGH
        assert _parse_risk_level(2) == EGARiskLevel.MEDIUM
        assert _parse_risk_level(1) == EGARiskLevel.LOW

    def test_numeric_as_string(self):
        """Test parsing numeric values as strings."""
        assert _parse_risk_level("4") == EGARiskLevel.CRITICAL
        assert _parse_risk_level("3") == EGARiskLevel.HIGH

    def test_default_for_none(self):
        """Test default value for None."""
        assert _parse_risk_level(None) == EGARiskLevel.MEDIUM

    def test_default_for_invalid(self):
        """Test default value for invalid input."""
        assert _parse_risk_level("invalid") == EGARiskLevel.MEDIUM
        assert _parse_risk_level("") == EGARiskLevel.MEDIUM


class TestParsePriority:
    """Tests for _parse_priority function."""

    def test_valid_numeric(self):
        """Test parsing valid numeric priority."""
        assert _parse_priority(85, EGARiskLevel.HIGH) == 85
        assert _parse_priority(50, EGARiskLevel.MEDIUM) == 50

    def test_bounds_clamping(self):
        """Test priority bounds clamping."""
        assert _parse_priority(150, EGARiskLevel.HIGH) == 100
        assert _parse_priority(0, EGARiskLevel.LOW) == 1
        assert _parse_priority(-10, EGARiskLevel.LOW) == 1

    def test_string_numeric(self):
        """Test parsing string numeric priority."""
        assert _parse_priority("75", EGARiskLevel.HIGH) == 75
        assert _parse_priority("50.5", EGARiskLevel.MEDIUM) == 50

    def test_fallback_to_risk_level(self):
        """Test fallback to risk level when no value."""
        assert _parse_priority(None, EGARiskLevel.CRITICAL) == 90
        assert _parse_priority(None, EGARiskLevel.HIGH) == 70
        assert _parse_priority(None, EGARiskLevel.MEDIUM) == 50
        assert _parse_priority(None, EGARiskLevel.LOW) == 30

    def test_fallback_for_invalid(self):
        """Test fallback for invalid value."""
        assert _parse_priority("invalid", EGARiskLevel.HIGH) == 70


class TestGetFieldValue:
    """Tests for _get_field_value function."""

    def test_with_column_map(self):
        """Test field extraction with column mapping."""
        row = {"EGA Name": "Test EGA", "Description": "Test desc"}
        column_map = {"name": "EGA Name", "description": "Description"}

        assert _get_field_value(row, column_map, "name") == "Test EGA"
        assert _get_field_value(row, column_map, "description") == "Test desc"

    def test_direct_field_access(self):
        """Test direct field access without mapping."""
        row = {"name": "Direct Name", "description": "Direct desc"}
        column_map = {}

        assert _get_field_value(row, column_map, "name") == "Direct Name"

    def test_missing_field(self):
        """Test missing field returns None."""
        row = {"name": "Test"}
        column_map = {}

        assert _get_field_value(row, column_map, "description") is None


# ============================================================================
# EGA EXTRACTION TESTS
# ============================================================================


class TestExtractEGAsFromData:
    """Tests for _extract_egas_from_data function."""

    def test_successful_extraction(self, sample_excel_data: Dict[str, Any]):
        """Test successful EGA extraction."""
        result = _extract_egas_from_data(
            sample_excel_data,
            project_id="proj-123",
            sheet_name="Sheet1"
        )

        assert result.success is True
        assert len(result.egas) == 3
        assert result.total_rows_processed == 3

    def test_ega_field_mapping(self, sample_excel_data: Dict[str, Any]):
        """Test correct field mapping."""
        result = _extract_egas_from_data(
            sample_excel_data,
            project_id="proj-123"
        )

        first_ega = result.egas[0]
        assert first_ega.name == "Revenue Testing"
        assert first_ega.description == "Test revenue recognition procedures"
        assert first_ega.risk_level == EGARiskLevel.HIGH
        assert first_ega.priority == 85

    def test_metadata_extraction(self, sample_excel_data: Dict[str, Any]):
        """Test metadata extraction."""
        result = _extract_egas_from_data(
            sample_excel_data,
            project_id="proj-123"
        )

        first_ega = result.egas[0]
        assert first_ega.metadata.get("category") == "Revenue"
        assert first_ega.metadata.get("assertion") == "Completeness, Accuracy"

    def test_empty_data(self):
        """Test handling empty data."""
        result = _extract_egas_from_data(
            {"transactions": []},
            project_id="proj-123"
        )

        assert result.success is False
        assert len(result.egas) == 0
        assert len(result.errors) > 0

    def test_missing_name_warning(self):
        """Test warning for rows without name."""
        data = {
            "transactions": [
                {"Description": "No name provided", "Risk Level": "High"},
            ]
        }

        result = _extract_egas_from_data(data, project_id="proj-123")

        assert len(result.warnings) > 0
        assert "Missing EGA name" in result.warnings[0]

    def test_source_tracking(self, sample_excel_data: Dict[str, Any]):
        """Test source row and sheet tracking."""
        result = _extract_egas_from_data(
            sample_excel_data,
            project_id="proj-123",
            sheet_name="TestSheet"
        )

        first_ega = result.egas[0]
        assert first_ega.source_row == 1
        assert first_ega.source_sheet == "TestSheet"


class TestBuildEGAHierarchy:
    """Tests for _build_ega_hierarchy function."""

    def test_hierarchy_by_category(self):
        """Test hierarchy building by category."""
        egas = [
            EGA(id="ega-1", project_id="proj-123", name="EGA 1", description="", metadata={"category": "Revenue"}),
            EGA(id="ega-2", project_id="proj-123", name="EGA 2", description="", metadata={"category": "Revenue"}),
            EGA(id="ega-3", project_id="proj-123", name="EGA 3", description="", metadata={"category": "Revenue"}),
        ]

        _build_ega_hierarchy(egas)

        assert egas[0].parent_ega_id is None  # First is parent
        assert egas[1].parent_ega_id == "ega-1"
        assert egas[2].parent_ega_id == "ega-1"

    def test_no_hierarchy_for_single_item(self):
        """Test no hierarchy changes for single item categories."""
        egas = [
            EGA(id="ega-1", project_id="proj-123", name="EGA 1", description="", metadata={"category": "Revenue"}),
            EGA(id="ega-2", project_id="proj-123", name="EGA 2", description="", metadata={"category": "Inventory"}),
        ]

        _build_ega_hierarchy(egas)

        assert egas[0].parent_ega_id is None
        assert egas[1].parent_ega_id is None

    def test_preserves_existing_parent(self):
        """Test that existing parent_ega_id is preserved."""
        egas = [
            EGA(id="ega-1", project_id="proj-123", name="EGA 1", description="", metadata={"category": "Revenue"}),
            EGA(id="ega-2", project_id="proj-123", name="EGA 2", description="", parent_ega_id="existing-parent", metadata={"category": "Revenue"}),
        ]

        _build_ega_hierarchy(egas)

        assert egas[1].parent_ega_id == "existing-parent"  # Preserved


class TestGetFallbackEGAs:
    """Tests for _get_fallback_egas function."""

    def test_returns_sample_egas(self):
        """Test fallback returns sample EGAs."""
        egas = _get_fallback_egas("proj-123")

        assert len(egas) == 5
        assert all(isinstance(e, EGA) for e in egas)

    def test_project_id_assignment(self):
        """Test project ID is correctly assigned."""
        egas = _get_fallback_egas("test-project")

        assert all(e.project_id == "test-project" for e in egas)

    def test_unique_ids(self):
        """Test all EGAs have unique IDs."""
        egas = _get_fallback_egas("proj-123")
        ids = [e.id for e in egas]

        assert len(set(ids)) == len(ids)


class TestGenerateEGAsFromPlan:
    """Tests for _generate_egas_from_plan function."""

    def test_from_audit_areas(self):
        """Test EGA generation from audit areas."""
        plan = {
            "audit_areas": [
                {"name": "Revenue", "description": "Revenue testing", "risk_level": "high"},
                {"name": "Inventory", "description": "Inventory testing", "risk_level": "medium"},
            ]
        }

        egas = _generate_egas_from_plan(plan, "proj-123")

        assert len(egas) == 2
        assert egas[0].name == "Revenue"
        assert egas[0].risk_level == EGARiskLevel.HIGH

    def test_from_objectives(self):
        """Test EGA generation from objectives when no areas."""
        plan = {
            "objectives": [
                {"name": "Accuracy Testing", "description": "Test accuracy"},
                {"name": "Compliance", "description": "Test compliance"},
            ]
        }

        egas = _generate_egas_from_plan(plan, "proj-123")

        assert len(egas) == 2
        assert egas[0].name == "Accuracy Testing"

    def test_fallback_when_empty_plan(self):
        """Test fallback EGAs when plan is empty."""
        egas = _generate_egas_from_plan({}, "proj-123")

        assert len(egas) == 5  # Fallback count


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================


class TestGetEGASummary:
    """Tests for get_ega_summary function."""

    def test_summary_calculation(self):
        """Test summary statistics calculation."""
        egas = [
            {"risk_level": "high", "status": "pending", "priority": 80},
            {"risk_level": "medium", "status": "pending", "priority": 60},
            {"risk_level": "high", "status": "completed", "priority": 70},
        ]

        summary = get_ega_summary(egas)

        assert summary["total"] == 3
        assert summary["by_risk_level"]["high"] == 2
        assert summary["by_risk_level"]["medium"] == 1
        assert summary["by_status"]["pending"] == 2
        assert summary["by_status"]["completed"] == 1
        assert summary["average_priority"] == 70

    def test_empty_list(self):
        """Test summary for empty list."""
        summary = get_ega_summary([])

        assert summary["total"] == 0
        assert summary["by_risk_level"] == {}
        assert summary["average_priority"] == 0


class TestFilterEGAsByRisk:
    """Tests for filter_egas_by_risk function."""

    def test_filter_by_single_level(self):
        """Test filtering by single risk level."""
        egas = [
            {"name": "EGA 1", "risk_level": "high"},
            {"name": "EGA 2", "risk_level": "medium"},
            {"name": "EGA 3", "risk_level": "high"},
        ]

        filtered = filter_egas_by_risk(egas, ["high"])

        assert len(filtered) == 2
        assert all(e["risk_level"] == "high" for e in filtered)

    def test_filter_by_multiple_levels(self):
        """Test filtering by multiple risk levels."""
        egas = [
            {"name": "EGA 1", "risk_level": "high"},
            {"name": "EGA 2", "risk_level": "medium"},
            {"name": "EGA 3", "risk_level": "low"},
        ]

        filtered = filter_egas_by_risk(egas, ["high", "medium"])

        assert len(filtered) == 2


class TestSortEGAsByPriority:
    """Tests for sort_egas_by_priority function."""

    def test_descending_sort(self):
        """Test descending priority sort."""
        egas = [
            {"name": "EGA 1", "priority": 50},
            {"name": "EGA 2", "priority": 90},
            {"name": "EGA 3", "priority": 30},
        ]

        sorted_egas = sort_egas_by_priority(egas, descending=True)

        assert sorted_egas[0]["priority"] == 90
        assert sorted_egas[1]["priority"] == 50
        assert sorted_egas[2]["priority"] == 30

    def test_ascending_sort(self):
        """Test ascending priority sort."""
        egas = [
            {"name": "EGA 1", "priority": 50},
            {"name": "EGA 2", "priority": 90},
            {"name": "EGA 3", "priority": 30},
        ]

        sorted_egas = sort_egas_by_priority(egas, descending=False)

        assert sorted_egas[0]["priority"] == 30
        assert sorted_egas[2]["priority"] == 90


# ============================================================================
# ASYNC FUNCTION TESTS
# ============================================================================


class TestParseAssignedWorkflow:
    """Tests for parse_assigned_workflow function."""

    @pytest.mark.asyncio
    async def test_requires_file_path_or_url(self):
        """Test that file_path or file_url is required."""
        with pytest.raises(ValueError, match="Either file_path or file_url must be provided"):
            await parse_assigned_workflow(project_id="proj-123")

    @pytest.mark.asyncio
    async def test_fallback_when_server_unavailable(self):
        """Test fallback behavior when MCP server unavailable."""
        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()

        result = await parse_assigned_workflow(
            file_path="/path/to/file.xlsx",
            project_id="proj-123",
            mcp_client=mock_client,
        )

        assert result.success is True
        assert len(result.egas) == 5  # Fallback EGAs
        assert result.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_successful_parsing(self, sample_excel_data: Dict[str, Any]):
        """Test successful document parsing."""
        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=True)
        mock_client.parse_excel = AsyncMock(return_value={
            "status": "success",
            "data": sample_excel_data,
            "metadata": {"sheet_name": "Sheet1"},
        })
        mock_client.close = AsyncMock()

        result = await parse_assigned_workflow(
            file_path="/path/to/file.xlsx",
            project_id="proj-123",
            mcp_client=mock_client,
        )

        assert result.success is True
        assert len(result.egas) == 3

    @pytest.mark.asyncio
    async def test_parse_error_handling(self):
        """Test error handling during parsing."""
        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=True)
        mock_client.parse_excel = AsyncMock(return_value={
            "status": "error",
            "error": "Invalid file format",
        })
        mock_client.close = AsyncMock()

        result = await parse_assigned_workflow(
            file_path="/path/to/file.xlsx",
            project_id="proj-123",
            mcp_client=mock_client,
        )

        assert result.success is False
        assert len(result.errors) > 0


class TestEGAParserNode:
    """Tests for ega_parser_node function."""

    @pytest.mark.asyncio
    async def test_no_workflow_docs_uses_fallback(self, base_audit_state: AuditState):
        """Test fallback when no workflow documents."""
        result = await ega_parser_node(base_audit_state)

        assert "egas" in result
        assert len(result["egas"]) > 0
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_with_audit_plan(self, state_with_audit_plan: AuditState):
        """Test EGA generation from audit plan."""
        result = await ega_parser_node(state_with_audit_plan)

        assert "egas" in result
        assert len(result["egas"]) == 3  # From audit_areas

        # Verify EGA content
        ega_names = [e["name"] for e in result["egas"]]
        assert "Revenue Recognition" in ega_names
        assert "Inventory Valuation" in ega_names

    @pytest.mark.asyncio
    async def test_with_workflow_doc(self, state_with_workflow_doc: AuditState, sample_excel_data: Dict[str, Any]):
        """Test EGA extraction from workflow document."""
        with patch("src.graph.nodes.ega_parser.MCPExcelClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.health_check = AsyncMock(return_value=True)
            mock_instance.parse_excel = AsyncMock(return_value={
                "status": "success",
                "data": sample_excel_data,
                "metadata": {"sheet_name": "Sheet1"},
            })
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ega_parser_node(state_with_workflow_doc)

            assert "egas" in result
            assert len(result["egas"]) == 3

    @pytest.mark.asyncio
    async def test_message_generation(self, base_audit_state: AuditState):
        """Test status message generation."""
        result = await ega_parser_node(base_audit_state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "EGA Parser" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_multiple_documents(self, base_audit_state: AuditState, sample_excel_data: Dict[str, Any]):
        """Test parsing multiple workflow documents."""
        base_audit_state["shared_documents"] = [
            {"type": "assigned_workflow", "file_path": "/path/to/doc1.xlsx"},
            {"type": "workflow", "file_path": "/path/to/doc2.xlsx"},
        ]

        with patch("src.graph.nodes.ega_parser.MCPExcelClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.health_check = AsyncMock(return_value=True)
            mock_instance.parse_excel = AsyncMock(return_value={
                "status": "success",
                "data": sample_excel_data,
                "metadata": {},
            })
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ega_parser_node(base_audit_state)

            # Should have EGAs from both documents
            assert len(result["egas"]) == 6  # 3 from each doc

    @pytest.mark.asyncio
    async def test_document_without_path(self, base_audit_state: AuditState):
        """Test handling document without path or URL."""
        base_audit_state["shared_documents"] = [
            {"type": "assigned_workflow", "name": "doc_without_path.xlsx"},
        ]

        result = await ega_parser_node(base_audit_state)

        # Should use fallback EGAs and add warning
        assert len(result["egas"]) > 0


# ============================================================================
# INTEGRATION-STYLE TESTS
# ============================================================================


class TestEGAParserIntegration:
    """Integration-style tests for EGA parser."""

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self, sample_excel_data: Dict[str, Any]):
        """Test full EGA parsing workflow."""
        state: AuditState = {
            "messages": [],
            "project_id": "INT-PROJECT-001",
            "client_name": "Integration Test Corp",
            "fiscal_year": 2024,
            "overall_materiality": 5000000.0,
            "audit_plan": {},
            "tasks": [],
            "next_action": "CONTINUE",
            "is_approved": True,
            "shared_documents": [
                {
                    "type": "assigned_workflow",
                    "name": "Workflow_2024.xlsx",
                    "file_path": "/uploads/Workflow_2024.xlsx",
                }
            ],
            "interview_complete": True,
            "interview_phase": 5,
            "interview_responses": [],
            "specification": {},
            "egas": [],
            "urgency_config": {},
        }

        with patch("src.graph.nodes.ega_parser.MCPExcelClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.health_check = AsyncMock(return_value=True)
            mock_instance.parse_excel = AsyncMock(return_value={
                "status": "success",
                "data": sample_excel_data,
                "metadata": {"sheet_name": "EGAs"},
            })
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await ega_parser_node(state)

        # Verify results
        assert len(result["egas"]) == 3

        # Verify EGA structure
        for ega in result["egas"]:
            assert "id" in ega
            assert "name" in ega
            assert "description" in ega
            assert "risk_level" in ega
            assert "priority" in ega
            assert "project_id" in ega
            assert ega["project_id"] == "INT-PROJECT-001"

        # Verify risk levels are correct
        risk_levels = [e["risk_level"] for e in result["egas"]]
        assert "high" in risk_levels
        assert "medium" in risk_levels
        assert "critical" in risk_levels

    def test_ega_dict_serialization(self, sample_ega: EGA):
        """Test that EGA can be serialized to JSON-compatible dict."""
        import json

        ega_dict = sample_ega.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(ega_dict)
        assert json_str is not None

        # Round-trip should preserve data
        loaded = json.loads(json_str)
        assert loaded["id"] == sample_ega.id
        assert loaded["name"] == sample_ega.name


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_parse_risk_level_boundary_values(self):
        """Test boundary values for risk level parsing."""
        assert _parse_risk_level(5) == EGARiskLevel.CRITICAL  # > 4
        assert _parse_risk_level(0) == EGARiskLevel.LOW  # < 1

    def test_priority_extreme_values(self):
        """Test extreme priority values."""
        assert _parse_priority(1000, EGARiskLevel.HIGH) == 100
        assert _parse_priority(-100, EGARiskLevel.LOW) == 1

    def test_unicode_ega_names(self):
        """Test Unicode characters in EGA names."""
        ega = EGA(
            id="ega-unicode",
            project_id="proj-123",
            name="매출 수익인식 테스트",
            description="K-IFRS 1115에 따른 수익인식 검토",
        )

        ega_dict = ega.to_dict()
        assert ega_dict["name"] == "매출 수익인식 테스트"
        assert "K-IFRS" in ega_dict["description"]

    def test_empty_metadata(self):
        """Test EGA with empty metadata."""
        ega = EGA(
            id="ega-empty-meta",
            project_id="proj-123",
            name="Test",
            description="Test description",
            metadata={},
        )

        assert ega.metadata == {}
        assert ega.to_dict()["metadata"] == {}

    @pytest.mark.asyncio
    async def test_malformed_excel_data(self):
        """Test handling of malformed Excel data."""
        malformed_data = {
            "transactions": [
                {"random_field": "value"},  # No recognizable columns
            ]
        }

        result = _extract_egas_from_data(malformed_data, "proj-123")

        # Should generate warnings for missing required fields
        assert len(result.warnings) > 0

    def test_column_mapping_coverage(self):
        """Test that all expected column variations are mapped."""
        # Test all name variations
        for variation in COLUMN_MAPPINGS["name"]:
            assert _normalize_column_name(variation) == "name"

        # Test all description variations
        for variation in COLUMN_MAPPINGS["description"]:
            assert _normalize_column_name(variation) == "description"
