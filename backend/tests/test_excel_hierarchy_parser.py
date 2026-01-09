"""
Comprehensive Unit Tests for Excel Hierarchy Parser

Target Coverage:
- ExcelHierarchyParser class - Main parser for Excel workflow files
- AuditHierarchy dataclass - Hierarchy node representation
- Helper functions - Column mapping, value cleaning, metadata extraction
- Utility functions - Summary, filtering, tree conversion

Test Categories:
1. Data Class Tests - AuditHierarchy creation and serialization
2. Helper Function Tests - Column normalization, value cleaning
3. Parser Core Tests - Hierarchy building with deduplication
4. Integration Tests - Full Excel parsing workflow
5. Utility Function Tests - Summary, filtering, tree conversion
6. Edge Case Tests - Error handling, boundary conditions

Coverage Target: 80%+
Test Count: 50+ tests
"""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.graph.nodes.excel_hierarchy_parser import (
    DEFAULT_COLUMN_MAPPING,
    COLUMN_VARIATIONS,
    METADATA_COLUMNS,
    AuditHierarchy,
    ExcelHierarchyParser,
    HierarchyLevel,
    HierarchyParseResult,
    HierarchyStatus,
    _clean_value,
    _extract_metadata,
    _find_column_for_level,
    _generate_hierarchy_id,
    _normalize_column_name,
    filter_hierarchy_by_level,
    get_children,
    get_descendants,
    get_hierarchy_summary,
    hierarchy_to_tree,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_hierarchy_node() -> AuditHierarchy:
    """Create a sample AuditHierarchy node for testing."""
    return AuditHierarchy(
        id="bp-test123456",
        project_id="PROJECT-001",
        level=HierarchyLevel.HIGH,
        parent_id=None,
        name="Revenue-Collection Cycle",
        source_column="Business Process(es)",
        source_row=2,
        ref_no="REF-001",
        status="Active",
        metadata={"category": "Revenue", "priority": "High"},
    )


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample DataFrame mimicking Excel structure."""
    return pd.DataFrame({
        "Business Process(es)": [
            "Revenue-Collection Cycle",
            "Revenue-Collection Cycle",
            "Revenue-Collection Cycle",
            "Inventory Management",
            "Inventory Management",
        ],
        "Primary FSLI": [
            "Sales Revenue",
            "Sales Revenue",
            "Accounts Receivable",
            "Inventory",
            "Cost of Sales",
        ],
        "EGA Type": [
            "Revenue Recognition Testing",
            "Sales Cutoff Testing",
            "AR Confirmation",
            "Inventory Count Observation",
            "COGS Analytical Review",
        ],
        "Ref. No.": [
            "REV-001",
            "REV-002",
            "AR-001",
            "INV-001",
            "COS-001",
        ],
        "Status": [
            "Pending",
            "In Progress",
            "Completed",
            "Pending",
            "Review",
        ],
    })


@pytest.fixture
def sample_dataframe_minimal() -> pd.DataFrame:
    """Create a minimal DataFrame with only required columns."""
    return pd.DataFrame({
        "Business Process(es)": ["Process A", "Process A"],
        "Primary FSLI": ["FSLI X", "FSLI Y"],
        "EGA Type": ["EGA 1", "EGA 2"],
    })


@pytest.fixture
def sample_dataframe_missing_columns() -> pd.DataFrame:
    """Create a DataFrame missing some hierarchy columns."""
    return pd.DataFrame({
        "EGA Type": ["EGA 1", "EGA 2", "EGA 3"],
        "Ref. No.": ["R1", "R2", "R3"],
    })


@pytest.fixture
def sample_dataframe_with_nulls() -> pd.DataFrame:
    """Create a DataFrame with null values."""
    return pd.DataFrame({
        "Business Process(es)": ["Process A", None, "Process B", "Process B"],
        "Primary FSLI": ["FSLI X", "FSLI X", None, "FSLI Z"],
        "EGA Type": ["EGA 1", "EGA 2", "EGA 3", None],
        "Ref. No.": ["R1", None, "R3", "R4"],
    })


@pytest.fixture
def temp_excel_file(sample_dataframe) -> str:
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        sample_dataframe.to_excel(f.name, index=False, engine="openpyxl")
        return f.name


@pytest.fixture
def temp_excel_file_minimal(sample_dataframe_minimal) -> str:
    """Create a minimal temporary Excel file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        sample_dataframe_minimal.to_excel(f.name, index=False, engine="openpyxl")
        return f.name


@pytest.fixture
def sample_hierarchy_list() -> List[AuditHierarchy]:
    """Create a sample hierarchy list for utility function testing."""
    high1 = AuditHierarchy(
        id="bp-001",
        project_id="proj-123",
        level=HierarchyLevel.HIGH,
        parent_id=None,
        name="Revenue Cycle",
        source_column="Business Process(es)",
        source_row=2,
    )
    high2 = AuditHierarchy(
        id="bp-002",
        project_id="proj-123",
        level=HierarchyLevel.HIGH,
        parent_id=None,
        name="Inventory Cycle",
        source_column="Business Process(es)",
        source_row=5,
    )
    mid1 = AuditHierarchy(
        id="fsli-001",
        project_id="proj-123",
        level=HierarchyLevel.MID,
        parent_id="bp-001",
        name="Sales Revenue",
        source_column="Primary FSLI",
        source_row=2,
    )
    mid2 = AuditHierarchy(
        id="fsli-002",
        project_id="proj-123",
        level=HierarchyLevel.MID,
        parent_id="bp-001",
        name="Accounts Receivable",
        source_column="Primary FSLI",
        source_row=4,
    )
    low1 = AuditHierarchy(
        id="ega-001",
        project_id="proj-123",
        level=HierarchyLevel.LOW,
        parent_id="fsli-001",
        name="Revenue Testing",
        source_column="EGA Type",
        source_row=2,
    )
    low2 = AuditHierarchy(
        id="ega-002",
        project_id="proj-123",
        level=HierarchyLevel.LOW,
        parent_id="fsli-001",
        name="Cutoff Testing",
        source_column="EGA Type",
        source_row=3,
    )

    return [high1, high2, mid1, mid2, low1, low2]


# ============================================================================
# DATA CLASS TESTS
# ============================================================================


class TestAuditHierarchy:
    """Tests for the AuditHierarchy dataclass."""

    def test_hierarchy_creation(self, sample_hierarchy_node: AuditHierarchy):
        """Test AuditHierarchy creation with all fields."""
        assert sample_hierarchy_node.id == "bp-test123456"
        assert sample_hierarchy_node.project_id == "PROJECT-001"
        assert sample_hierarchy_node.level == HierarchyLevel.HIGH
        assert sample_hierarchy_node.parent_id is None
        assert sample_hierarchy_node.name == "Revenue-Collection Cycle"
        assert sample_hierarchy_node.source_column == "Business Process(es)"
        assert sample_hierarchy_node.source_row == 2
        assert sample_hierarchy_node.ref_no == "REF-001"
        assert sample_hierarchy_node.status == "Active"

    def test_hierarchy_to_dict(self, sample_hierarchy_node: AuditHierarchy):
        """Test AuditHierarchy to_dict conversion."""
        node_dict = sample_hierarchy_node.to_dict()

        assert node_dict["id"] == "bp-test123456"
        assert node_dict["level"] == "high"
        assert node_dict["parent_id"] is None
        assert node_dict["name"] == "Revenue-Collection Cycle"
        assert "created_at" in node_dict
        assert "updated_at" in node_dict

    def test_hierarchy_default_values(self):
        """Test AuditHierarchy with minimal required fields."""
        node = AuditHierarchy(
            id="bp-minimal",
            project_id="proj-123",
            level=HierarchyLevel.MID,
            parent_id="bp-001",
            name="Test Node",
            source_column="Test Column",
            source_row=5,
        )

        assert node.ref_no is None
        assert node.status is None
        assert node.metadata == {}
        assert node.created_at is None
        assert node.updated_at is None

    def test_hierarchy_with_all_levels(self):
        """Test creating nodes for all hierarchy levels."""
        high_node = AuditHierarchy(
            id="bp-001",
            project_id="proj",
            level=HierarchyLevel.HIGH,
            parent_id=None,
            name="High Level",
            source_column="Business Process(es)",
            source_row=1,
        )

        mid_node = AuditHierarchy(
            id="fsli-001",
            project_id="proj",
            level=HierarchyLevel.MID,
            parent_id="bp-001",
            name="Mid Level",
            source_column="Primary FSLI",
            source_row=1,
        )

        low_node = AuditHierarchy(
            id="ega-001",
            project_id="proj",
            level=HierarchyLevel.LOW,
            parent_id="fsli-001",
            name="Low Level",
            source_column="EGA Type",
            source_row=1,
        )

        assert high_node.level == HierarchyLevel.HIGH
        assert mid_node.level == HierarchyLevel.MID
        assert low_node.level == HierarchyLevel.LOW
        assert mid_node.parent_id == high_node.id
        assert low_node.parent_id == mid_node.id


class TestHierarchyEnums:
    """Tests for hierarchy enums."""

    def test_hierarchy_level_values(self):
        """Test HierarchyLevel enum values."""
        assert HierarchyLevel.HIGH.value == "high"
        assert HierarchyLevel.MID.value == "mid"
        assert HierarchyLevel.LOW.value == "low"

    def test_hierarchy_status_values(self):
        """Test HierarchyStatus enum values."""
        assert HierarchyStatus.PENDING.value == "pending"
        assert HierarchyStatus.IN_PROGRESS.value == "in_progress"
        assert HierarchyStatus.REVIEW_REQUIRED.value == "review_required"
        assert HierarchyStatus.COMPLETED.value == "completed"


class TestHierarchyParseResult:
    """Tests for HierarchyParseResult dataclass."""

    def test_successful_result(self, sample_hierarchy_node: AuditHierarchy):
        """Test successful parse result."""
        result = HierarchyParseResult(
            success=True,
            hierarchy=[sample_hierarchy_node],
            high_level_count=1,
            mid_level_count=0,
            low_level_count=0,
            total_rows_processed=1,
        )

        assert result.success is True
        assert len(result.hierarchy) == 1
        assert result.high_level_count == 1
        assert result.errors == []
        assert result.warnings == []

    def test_failed_result(self):
        """Test failed parse result."""
        result = HierarchyParseResult(
            success=False,
            hierarchy=[],
            errors=["File not found", "Invalid format"],
            warnings=["Missing column"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


class TestGenerateHierarchyId:
    """Tests for _generate_hierarchy_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [_generate_hierarchy_id(HierarchyLevel.HIGH) for _ in range(100)]
        assert len(set(ids)) == 100

    def test_id_prefixes_by_level(self):
        """Test ID prefixes match hierarchy level."""
        high_id = _generate_hierarchy_id(HierarchyLevel.HIGH)
        mid_id = _generate_hierarchy_id(HierarchyLevel.MID)
        low_id = _generate_hierarchy_id(HierarchyLevel.LOW)

        assert high_id.startswith("bp-")
        assert mid_id.startswith("fsli-")
        assert low_id.startswith("ega-")

    def test_id_format(self):
        """Test ID format structure."""
        id_str = _generate_hierarchy_id(HierarchyLevel.HIGH)
        parts = id_str.split("-")

        assert len(parts) == 2
        assert parts[0] == "bp"
        assert len(parts[1]) == 12  # 12 hex chars


class TestNormalizeColumnName:
    """Tests for _normalize_column_name function."""

    def test_exact_match(self):
        """Test exact column name match."""
        assert _normalize_column_name("Business Process(es)", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.HIGH
        assert _normalize_column_name("Primary FSLI", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.MID
        assert _normalize_column_name("EGA Type", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.LOW

    def test_case_insensitive_variations(self):
        """Test case insensitivity for variations."""
        assert _normalize_column_name("business process", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.HIGH
        assert _normalize_column_name("FSLI", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.MID
        assert _normalize_column_name("ega", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.LOW

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert _normalize_column_name("  Business Process(es)  ", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.HIGH
        assert _normalize_column_name("\tPrimary FSLI\t", DEFAULT_COLUMN_MAPPING) == HierarchyLevel.MID

    def test_unrecognized_column(self):
        """Test unrecognized column name."""
        assert _normalize_column_name("Unknown Column", DEFAULT_COLUMN_MAPPING) is None
        assert _normalize_column_name("Random Field", DEFAULT_COLUMN_MAPPING) is None


class TestFindColumnForLevel:
    """Tests for _find_column_for_level function."""

    def test_find_high_level_column(self):
        """Test finding HIGH level column."""
        columns = ["Business Process(es)", "Primary FSLI", "EGA Type"]
        result = _find_column_for_level(columns, HierarchyLevel.HIGH, DEFAULT_COLUMN_MAPPING)
        assert result == "Business Process(es)"

    def test_find_column_variation(self):
        """Test finding column by variation."""
        columns = ["BP", "Account", "Activity Type"]
        result = _find_column_for_level(columns, HierarchyLevel.HIGH, {})
        assert result == "BP"

    def test_column_not_found(self):
        """Test when column is not found."""
        columns = ["Random1", "Random2"]
        result = _find_column_for_level(columns, HierarchyLevel.HIGH, DEFAULT_COLUMN_MAPPING)
        assert result is None


class TestCleanValue:
    """Tests for _clean_value function."""

    def test_clean_string_value(self):
        """Test cleaning string values."""
        assert _clean_value("  Test Value  ") == "Test Value"
        assert _clean_value("Normal") == "Normal"

    def test_clean_null_values(self):
        """Test handling null/None values."""
        assert _clean_value(None) is None
        assert _clean_value(pd.NA) is None
        assert _clean_value(float("nan")) is None

    def test_clean_empty_strings(self):
        """Test handling empty strings."""
        assert _clean_value("") is None
        assert _clean_value("   ") is None
        assert _clean_value("nan") is None
        assert _clean_value("None") is None

    def test_clean_numeric_values(self):
        """Test handling numeric values."""
        assert _clean_value(123) == "123"
        assert _clean_value(45.67) == "45.67"


class TestExtractMetadata:
    """Tests for _extract_metadata function."""

    def test_extract_known_metadata_columns(self):
        """Test extraction of known metadata columns."""
        row = pd.Series({
            "Business Process(es)": "Revenue",
            "Primary FSLI": "Sales",
            "EGA Type": "Testing",
            "Ref. No.": "REF-001",
            "Status": "Active",
            "Notes": "Important note",
        })
        columns = list(row.index)
        hierarchy_columns = ["Business Process(es)", "Primary FSLI", "EGA Type"]

        metadata = _extract_metadata(row, columns, hierarchy_columns)

        assert "ref_no" in metadata
        assert "status" in metadata
        assert "notes" in metadata
        assert metadata["ref_no"] == "REF-001"

    def test_skip_hierarchy_columns(self):
        """Test that hierarchy columns are skipped."""
        row = pd.Series({
            "Business Process(es)": "Revenue",
            "Status": "Active",
        })
        columns = list(row.index)
        hierarchy_columns = ["Business Process(es)"]

        metadata = _extract_metadata(row, columns, hierarchy_columns)

        assert "business_process" not in metadata
        assert "status" in metadata


# ============================================================================
# PARSER CORE TESTS
# ============================================================================


class TestExcelHierarchyParser:
    """Tests for ExcelHierarchyParser class."""

    def test_parser_initialization(self):
        """Test parser initialization with default mapping."""
        parser = ExcelHierarchyParser()
        assert parser.column_mapping == DEFAULT_COLUMN_MAPPING

    def test_parser_custom_mapping(self):
        """Test parser initialization with custom mapping."""
        custom_mapping = {
            "Process": HierarchyLevel.HIGH,
            "Account": HierarchyLevel.MID,
            "Task": HierarchyLevel.LOW,
        }
        parser = ExcelHierarchyParser(column_mapping=custom_mapping)
        assert parser.column_mapping == custom_mapping

    @pytest.mark.asyncio
    async def test_parse_excel_file(self, temp_excel_file: str):
        """Test parsing a real Excel file."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        assert result.success is True
        assert len(result.hierarchy) > 0
        assert result.total_rows_processed == 5

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        parser = ExcelHierarchyParser()
        result = await parser.parse("/nonexistent/path.xlsx", "project-123")

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower() or "No such file" in result.errors[0]

    @pytest.mark.asyncio
    async def test_hierarchy_deduplication(self, temp_excel_file: str):
        """Test that HIGH and MID levels are deduplicated."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        # Sample data has 2 unique Business Processes and 4 unique FSLIs
        assert result.high_level_count == 2  # Revenue-Collection, Inventory Management
        assert result.mid_level_count == 4   # Sales Revenue, AR, Inventory, Cost of Sales
        assert result.low_level_count == 5   # 5 EGA Types (one per row)

    @pytest.mark.asyncio
    async def test_parent_child_relationships(self, temp_excel_file: str):
        """Test parent-child relationships are correctly established."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        # Find nodes by level
        high_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.HIGH]
        mid_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.MID]
        low_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.LOW]

        # HIGH level nodes should have no parent
        for node in high_nodes:
            assert node.parent_id is None

        # MID level nodes should have HIGH level parent
        for node in mid_nodes:
            assert node.parent_id is not None
            parent = next((n for n in high_nodes if n.id == node.parent_id), None)
            assert parent is not None

        # LOW level nodes should have MID level parent
        for node in low_nodes:
            assert node.parent_id is not None
            parent = next((n for n in mid_nodes if n.id == node.parent_id), None)
            assert parent is not None

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, temp_excel_file: str):
        """Test that metadata (Ref. No., Status) is preserved at LOW level."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        low_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.LOW]

        # Check that at least some LOW nodes have ref_no and status
        nodes_with_ref = [n for n in low_nodes if n.ref_no is not None]
        nodes_with_status = [n for n in low_nodes if n.status is not None]

        assert len(nodes_with_ref) > 0
        assert len(nodes_with_status) > 0

    @pytest.mark.asyncio
    async def test_source_row_tracking(self, temp_excel_file: str):
        """Test that source rows are correctly tracked."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        # All nodes should have valid source rows (>= 2 since row 1 is header)
        for node in result.hierarchy:
            assert node.source_row >= 2

    def test_parse_sync(self, temp_excel_file: str):
        """Test synchronous parsing."""
        parser = ExcelHierarchyParser()
        result = parser.parse_sync(temp_excel_file, "project-123")

        assert result.success is True
        assert len(result.hierarchy) > 0


class TestBuildHierarchy:
    """Tests for _build_hierarchy method."""

    @pytest.mark.asyncio
    async def test_missing_ega_column_fails(self, sample_dataframe_missing_columns: pd.DataFrame):
        """Test that missing EGA Type column causes failure."""
        # Create temp file with missing columns
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            # Create DataFrame without EGA Type
            df = pd.DataFrame({
                "Business Process(es)": ["Process A"],
                "Primary FSLI": ["FSLI X"],
                # No EGA Type column
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is False
            assert any("EGA Type column not found" in err for err in result.errors)

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_missing_high_mid_uses_defaults(self):
        """Test that missing HIGH/MID columns use defaults with warnings."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            # Create DataFrame with only EGA Type
            df = pd.DataFrame({
                "EGA Type": ["EGA 1", "EGA 2"],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is True
            assert len(result.warnings) >= 2  # Warnings for missing HIGH and MID

            # Should create default parent nodes
            high_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.HIGH]
            assert len(high_nodes) == 1
            assert "Unknown" in high_nodes[0].name

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_null_ega_values_skipped(self, sample_dataframe_with_nulls: pd.DataFrame):
        """Test that rows with null EGA Type are skipped."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            sample_dataframe_with_nulls.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            # Should have 3 LOW nodes (4th row has null EGA Type)
            low_nodes = [n for n in result.hierarchy if n.level == HierarchyLevel.LOW]
            assert result.low_level_count == 3
            assert len(result.warnings) > 0  # Warning for skipped row

        os.unlink(f.name)


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================


class TestGetHierarchySummary:
    """Tests for get_hierarchy_summary function."""

    def test_summary_calculation(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test summary statistics calculation."""
        summary = get_hierarchy_summary(sample_hierarchy_list)

        assert summary["total"] == 6
        assert summary["by_level"]["high"] == 2
        assert summary["by_level"]["mid"] == 2
        assert summary["by_level"]["low"] == 2
        assert summary["unique_business_processes"] == 2
        assert summary["unique_fslis"] == 2

    def test_empty_list_summary(self):
        """Test summary for empty list."""
        summary = get_hierarchy_summary([])

        assert summary["total"] == 0
        assert summary["by_level"] == {}
        assert summary["unique_business_processes"] == 0
        assert summary["unique_fslis"] == 0


class TestFilterHierarchyByLevel:
    """Tests for filter_hierarchy_by_level function."""

    def test_filter_high_level(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test filtering HIGH level nodes."""
        filtered = filter_hierarchy_by_level(sample_hierarchy_list, HierarchyLevel.HIGH)

        assert len(filtered) == 2
        assert all(n.level == HierarchyLevel.HIGH for n in filtered)

    def test_filter_mid_level(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test filtering MID level nodes."""
        filtered = filter_hierarchy_by_level(sample_hierarchy_list, HierarchyLevel.MID)

        assert len(filtered) == 2
        assert all(n.level == HierarchyLevel.MID for n in filtered)

    def test_filter_low_level(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test filtering LOW level nodes."""
        filtered = filter_hierarchy_by_level(sample_hierarchy_list, HierarchyLevel.LOW)

        assert len(filtered) == 2
        assert all(n.level == HierarchyLevel.LOW for n in filtered)


class TestGetChildren:
    """Tests for get_children function."""

    def test_get_high_level_children(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test getting children of HIGH level node."""
        children = get_children(sample_hierarchy_list, "bp-001")

        assert len(children) == 2  # Two MID level children
        assert all(n.level == HierarchyLevel.MID for n in children)
        assert all(n.parent_id == "bp-001" for n in children)

    def test_get_mid_level_children(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test getting children of MID level node."""
        children = get_children(sample_hierarchy_list, "fsli-001")

        assert len(children) == 2  # Two LOW level children
        assert all(n.level == HierarchyLevel.LOW for n in children)

    def test_no_children(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test node with no children."""
        children = get_children(sample_hierarchy_list, "ega-001")
        assert len(children) == 0


class TestGetDescendants:
    """Tests for get_descendants function."""

    def test_get_all_descendants(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test getting all descendants of HIGH level node."""
        descendants = get_descendants(sample_hierarchy_list, "bp-001")

        # Should include 2 MID + 2 LOW (children of fsli-001)
        assert len(descendants) == 4

    def test_leaf_node_descendants(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test descendants of leaf node (LOW level)."""
        descendants = get_descendants(sample_hierarchy_list, "ega-001")
        assert len(descendants) == 0


class TestHierarchyToTree:
    """Tests for hierarchy_to_tree function."""

    def test_convert_to_tree(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test conversion to nested tree structure."""
        tree = hierarchy_to_tree(sample_hierarchy_list)

        # Should have 2 root nodes (HIGH level)
        assert len(tree) == 2

        # First root should have children
        root1 = tree[0]
        assert "children" in root1
        assert len(root1["children"]) == 2  # Two MID level children

        # Children should have their own children
        mid1 = root1["children"][0]
        assert "children" in mid1
        assert len(mid1["children"]) == 2  # Two LOW level children

    def test_empty_hierarchy_tree(self):
        """Test tree conversion with empty hierarchy."""
        tree = hierarchy_to_tree([])
        assert tree == []

    def test_tree_preserves_data(self, sample_hierarchy_list: List[AuditHierarchy]):
        """Test that tree conversion preserves node data."""
        tree = hierarchy_to_tree(sample_hierarchy_list)

        root = tree[0]
        assert root["id"] == "bp-001"
        assert root["name"] == "Revenue Cycle"
        assert root["level"] == "high"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_unicode_values(self):
        """Test handling of Unicode values."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df = pd.DataFrame({
                "Business Process(es)": ["매출-수금 주기"],  # Korean
                "Primary FSLI": ["매출액"],
                "EGA Type": ["수익인식 테스트"],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is True
            assert result.hierarchy[0].name == "매출-수금 주기"

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_large_file_handling(self):
        """Test handling of larger files."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            # Create a larger DataFrame
            n_rows = 100
            df = pd.DataFrame({
                "Business Process(es)": [f"Process {i % 5}" for i in range(n_rows)],
                "Primary FSLI": [f"FSLI {i % 10}" for i in range(n_rows)],
                "EGA Type": [f"EGA Type {i}" for i in range(n_rows)],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is True
            assert result.total_rows_processed == 100
            assert result.low_level_count == 100  # One per row
            assert result.high_level_count == 5   # 5 unique processes
            assert result.mid_level_count <= 50   # Up to 10 per process

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_whitespace_only_values(self):
        """Test handling of whitespace-only values."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df = pd.DataFrame({
                "Business Process(es)": ["Process A", "   ", "Process B"],
                "Primary FSLI": ["FSLI X", "FSLI Y", "   "],
                "EGA Type": ["EGA 1", "EGA 2", "EGA 3"],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is True
            # Whitespace values should be treated as "Unknown"
            high_names = [n.name for n in result.hierarchy if n.level == HierarchyLevel.HIGH]
            assert "Unknown Business Process" in high_names or any("Unknown" in name for name in high_names)

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_special_characters_in_values(self):
        """Test handling of special characters."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df = pd.DataFrame({
                "Business Process(es)": ["Revenue & Collections (R/C)"],
                "Primary FSLI": ["Sales - Net of Returns"],
                "EGA Type": ["Test: Revenue Recognition <2024>"],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is True
            assert "&" in result.hierarchy[0].name
            assert "-" in result.hierarchy[1].name
            assert ":" in result.hierarchy[2].name

        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df = pd.DataFrame({
                "Business Process(es)": [],
                "Primary FSLI": [],
                "EGA Type": [],
            })
            df.to_excel(f.name, index=False, engine="openpyxl")

            parser = ExcelHierarchyParser()
            result = await parser.parse(f.name, "project-123")

            assert result.success is False
            assert "empty" in result.errors[0].lower()

        os.unlink(f.name)

    def test_hierarchy_level_string_comparison(self):
        """Test HierarchyLevel string enum behavior."""
        level = HierarchyLevel.HIGH

        # Should be comparable as string
        assert level == "high"
        assert level.value == "high"

    def test_column_variations_coverage(self):
        """Test that all column variations are properly defined."""
        for level, variations in COLUMN_VARIATIONS.items():
            assert len(variations) > 0
            assert isinstance(level, HierarchyLevel)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for full parsing workflow."""

    @pytest.mark.asyncio
    async def test_full_parsing_workflow(self, temp_excel_file: str):
        """Test complete parsing workflow from file to structured hierarchy."""
        # Parse file
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "integration-test-001")

        assert result.success is True

        # Verify structure
        hierarchy = result.hierarchy

        # Get summary
        summary = get_hierarchy_summary(hierarchy)
        assert summary["total"] == result.high_level_count + result.mid_level_count + result.low_level_count

        # Filter by levels
        high_nodes = filter_hierarchy_by_level(hierarchy, HierarchyLevel.HIGH)
        mid_nodes = filter_hierarchy_by_level(hierarchy, HierarchyLevel.MID)
        low_nodes = filter_hierarchy_by_level(hierarchy, HierarchyLevel.LOW)

        assert len(high_nodes) == result.high_level_count
        assert len(mid_nodes) == result.mid_level_count
        assert len(low_nodes) == result.low_level_count

        # Convert to tree
        tree = hierarchy_to_tree(hierarchy)
        assert len(tree) == result.high_level_count

        # Verify tree structure is traversable
        for root in tree:
            assert "children" in root
            for mid in root["children"]:
                assert "children" in mid

    @pytest.mark.asyncio
    async def test_hierarchy_dict_serialization(self, temp_excel_file: str):
        """Test that hierarchy can be serialized to JSON-compatible format."""
        import json

        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        # Convert all nodes to dicts
        node_dicts = [node.to_dict() for node in result.hierarchy]

        # Should be JSON serializable
        json_str = json.dumps(node_dicts)
        assert json_str is not None

        # Round-trip should preserve data
        loaded = json.loads(json_str)
        assert len(loaded) == len(node_dicts)

    @pytest.mark.asyncio
    async def test_result_metadata_completeness(self, temp_excel_file: str):
        """Test that result metadata is complete."""
        parser = ExcelHierarchyParser()
        result = await parser.parse(temp_excel_file, "project-123")

        assert "file_path" in result.metadata
        assert "columns" in result.metadata
        assert "column_mapping" in result.metadata

        column_mapping = result.metadata["column_mapping"]
        assert "high" in column_mapping
        assert "mid" in column_mapping
        assert "low" in column_mapping
