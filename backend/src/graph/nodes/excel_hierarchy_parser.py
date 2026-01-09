"""
Excel Hierarchy Parser for Audit Workflow Documents

This module parses Excel files with "Assigned Workflow by Business Process" format
into a 3-level task hierarchy:
- HIGH level: Business Process(es)
- MID level: Primary FSLI (Financial Statement Line Item)
- LOW level: EGA Type (Expected General Activity Type)

The parser handles deduplication of parent nodes and maintains proper parent-child
relationships across the hierarchy.

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================


class HierarchyLevel(str, Enum):
    """Hierarchy level classification for audit tasks."""

    HIGH = "high"    # Business Process
    MID = "mid"      # Primary FSLI
    LOW = "low"      # EGA Type


class HierarchyStatus(str, Enum):
    """Status of a hierarchy node."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"


@dataclass
class AuditHierarchy:
    """
    Represents a node in the 3-level audit hierarchy.

    Attributes:
        id: Unique identifier for the hierarchy node
        project_id: Associated audit project ID
        level: Hierarchy level (high/mid/low)
        parent_id: Parent node ID for hierarchy linking
        name: Node name/title
        source_column: Column name in the source Excel file
        source_row: Row number in the source Excel file
        ref_no: Reference number from Excel (optional)
        status: Status from Excel (optional)
        metadata: Additional metadata from the source document
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    project_id: str
    level: HierarchyLevel
    parent_id: Optional[str]
    name: str
    source_column: str
    source_row: int
    ref_no: Optional[str] = None
    status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert hierarchy node to dictionary for state storage."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "level": self.level.value if isinstance(self.level, HierarchyLevel) else self.level,
            "parent_id": self.parent_id,
            "name": self.name,
            "source_column": self.source_column,
            "source_row": self.source_row,
            "ref_no": self.ref_no,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "updated_at": self.updated_at or datetime.utcnow().isoformat(),
        }


@dataclass
class HierarchyParseResult:
    """Result of parsing an Excel file into hierarchy."""

    success: bool
    hierarchy: List[AuditHierarchy]
    high_level_count: int = 0
    mid_level_count: int = 0
    low_level_count: int = 0
    total_rows_processed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# COLUMN MAPPING CONFIGURATION
# ============================================================================


# Default column mapping for Assigned Workflow documents
DEFAULT_COLUMN_MAPPING = {
    "Business Process(es)": HierarchyLevel.HIGH,
    "Primary FSLI": HierarchyLevel.MID,
    "EGA Type": HierarchyLevel.LOW,
}

# Alternative column name variations
COLUMN_VARIATIONS = {
    HierarchyLevel.HIGH: [
        "Business Process(es)",
        "Business Process",
        "Business Processes",
        "Process",
        "BP",
    ],
    HierarchyLevel.MID: [
        "Primary FSLI",
        "FSLI",
        "Financial Statement Line Item",
        "Account",
        "Account Category",
    ],
    HierarchyLevel.LOW: [
        "EGA Type",
        "EGA",
        "Activity Type",
        "Expected General Activity",
        "Task Type",
    ],
}

# Metadata column names to preserve
METADATA_COLUMNS = ["Ref. No.", "Ref No", "Reference", "Status", "Notes", "Comments"]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _generate_hierarchy_id(level: HierarchyLevel) -> str:
    """Generate a unique hierarchy node ID with level prefix."""
    prefix_map = {
        HierarchyLevel.HIGH: "bp",    # Business Process
        HierarchyLevel.MID: "fsli",   # FSLI
        HierarchyLevel.LOW: "ega",    # EGA Type
    }
    prefix = prefix_map.get(level, "node")
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _normalize_column_name(column: str, column_mapping: Dict[str, HierarchyLevel]) -> Optional[HierarchyLevel]:
    """
    Normalize a column name to its hierarchy level.

    Args:
        column: Original column name from Excel
        column_mapping: Mapping from column names to hierarchy levels

    Returns:
        HierarchyLevel or None if not recognized
    """
    column_clean = column.strip()

    # Check direct mapping first
    if column_clean in column_mapping:
        return column_mapping[column_clean]

    # Check variations
    column_lower = column_clean.lower()
    for level, variations in COLUMN_VARIATIONS.items():
        for variation in variations:
            if column_lower == variation.lower():
                return level

    return None


def _find_column_for_level(
    columns: List[str],
    level: HierarchyLevel,
    column_mapping: Dict[str, HierarchyLevel],
) -> Optional[str]:
    """
    Find the column name for a specific hierarchy level.

    Args:
        columns: List of column names from DataFrame
        level: Target hierarchy level
        column_mapping: Mapping from column names to hierarchy levels

    Returns:
        Column name or None if not found
    """
    # Check direct mapping
    for col_name, col_level in column_mapping.items():
        if col_level == level and col_name in columns:
            return col_name

    # Check variations
    for variation in COLUMN_VARIATIONS.get(level, []):
        for col in columns:
            if col.strip().lower() == variation.lower():
                return col

    return None


def _clean_value(value: Any) -> Optional[str]:
    """
    Clean and normalize a cell value.

    Args:
        value: Raw cell value

    Returns:
        Cleaned string value or None
    """
    if pd.isna(value):
        return None

    str_value = str(value).strip()
    if not str_value or str_value.lower() in ("nan", "none", "null", ""):
        return None

    return str_value


def _extract_metadata(
    row: pd.Series,
    columns: List[str],
    hierarchy_columns: List[str],
) -> Dict[str, Any]:
    """
    Extract metadata from non-hierarchy columns.

    Args:
        row: DataFrame row
        columns: All column names
        hierarchy_columns: Column names used for hierarchy

    Returns:
        Dictionary of metadata
    """
    metadata = {}

    for col in columns:
        if col in hierarchy_columns:
            continue

        # Check if it's a known metadata column
        col_lower = col.strip().lower()
        is_metadata = any(
            meta.lower() in col_lower or col_lower in meta.lower()
            for meta in METADATA_COLUMNS
        )

        if is_metadata:
            value = _clean_value(row.get(col))
            if value:
                # Normalize key name
                key = col.strip().replace(" ", "_").replace(".", "").lower()
                metadata[key] = value

    return metadata


# ============================================================================
# EXCEL HIERARCHY PARSER
# ============================================================================


class ExcelHierarchyParser:
    """
    Parse Excel files with "Assigned Workflow by Business Process" format
    into a 3-level audit task hierarchy.

    The parser:
    1. Reads Excel files using pandas
    2. Maps columns to hierarchy levels (HIGH/MID/LOW)
    3. Builds parent-child relationships with deduplication
    4. Preserves metadata (Ref. No., Status) at the LOW level

    Example:
        ```python
        parser = ExcelHierarchyParser()
        result = await parser.parse("/path/to/workflow.xlsx", "project-123")

        if result.success:
            for node in result.hierarchy:
                print(f"{node.level.value}: {node.name}")
        ```
    """

    def __init__(
        self,
        column_mapping: Optional[Dict[str, HierarchyLevel]] = None,
    ):
        """
        Initialize the parser with optional custom column mapping.

        Args:
            column_mapping: Custom mapping from column names to hierarchy levels
        """
        self.column_mapping = column_mapping or DEFAULT_COLUMN_MAPPING.copy()

    async def parse(
        self,
        file_path: str,
        project_id: str,
        sheet_name: Optional[str] = None,
    ) -> HierarchyParseResult:
        """
        Parse Excel file and return 3-level hierarchy.

        Args:
            file_path: Path to the Excel file
            project_id: Project ID to associate hierarchy nodes with
            sheet_name: Specific sheet to parse (optional, uses first sheet if not specified)

        Returns:
            HierarchyParseResult with parsed hierarchy and metadata

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file format is invalid
        """
        logger.info(f"Parsing Excel file: {file_path} for project: {project_id}")

        try:
            # Read Excel file
            df = self._read_excel(file_path, sheet_name)

            if df.empty:
                return HierarchyParseResult(
                    success=False,
                    hierarchy=[],
                    errors=["Excel file is empty or contains no data"],
                )

            # Build hierarchy from DataFrame
            result = self._build_hierarchy(df, project_id)

            # Add file metadata
            result.metadata["file_path"] = file_path
            result.metadata["sheet_name"] = sheet_name
            result.metadata["columns"] = list(df.columns)

            logger.info(
                f"Parsed hierarchy: {result.high_level_count} HIGH, "
                f"{result.mid_level_count} MID, {result.low_level_count} LOW"
            )

            return result

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return HierarchyParseResult(
                success=False,
                hierarchy=[],
                errors=[f"File not found: {file_path}"],
            )

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            return HierarchyParseResult(
                success=False,
                hierarchy=[],
                errors=[f"Parse error: {str(e)}"],
            )

    def _read_excel(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read Excel file into DataFrame.

        Args:
            file_path: Path to the Excel file
            sheet_name: Sheet name to read (optional)

        Returns:
            pandas DataFrame
        """
        read_kwargs = {"engine": "openpyxl"}

        if sheet_name:
            read_kwargs["sheet_name"] = sheet_name
        else:
            read_kwargs["sheet_name"] = 0  # First sheet

        df = pd.read_excel(file_path, **read_kwargs)

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]

        return df

    def _build_hierarchy(
        self,
        df: pd.DataFrame,
        project_id: str,
    ) -> HierarchyParseResult:
        """
        Build 3-level hierarchy from DataFrame with deduplication.

        Args:
            df: Source DataFrame
            project_id: Project ID for hierarchy nodes

        Returns:
            HierarchyParseResult with complete hierarchy
        """
        hierarchy: List[AuditHierarchy] = []
        errors: List[str] = []
        warnings: List[str] = []

        columns = list(df.columns)

        # Find columns for each hierarchy level
        high_col = _find_column_for_level(columns, HierarchyLevel.HIGH, self.column_mapping)
        mid_col = _find_column_for_level(columns, HierarchyLevel.MID, self.column_mapping)
        low_col = _find_column_for_level(columns, HierarchyLevel.LOW, self.column_mapping)

        if not high_col:
            warnings.append("Business Process column not found, using 'Unknown' as default")
        if not mid_col:
            warnings.append("Primary FSLI column not found, using 'Unknown' as default")
        if not low_col:
            errors.append("EGA Type column not found - cannot build hierarchy")
            return HierarchyParseResult(
                success=False,
                hierarchy=[],
                errors=errors,
                warnings=warnings,
            )

        hierarchy_columns = [c for c in [high_col, mid_col, low_col] if c]

        # Find metadata columns (Ref. No., Status)
        ref_col = None
        status_col = None
        for col in columns:
            col_lower = col.lower()
            if "ref" in col_lower and ref_col is None:
                ref_col = col
            elif "status" in col_lower and status_col is None:
                status_col = col

        # Track unique nodes for deduplication
        # Key: (level, parent_id, name) -> node_id
        node_registry: Dict[Tuple[HierarchyLevel, Optional[str], str], str] = {}

        high_count = 0
        mid_count = 0
        low_count = 0

        for row_idx, row in df.iterrows():
            row_num = int(row_idx) + 2  # Excel row number (1-indexed + header)

            try:
                # Extract values
                high_value = _clean_value(row.get(high_col)) if high_col else "Unknown"
                mid_value = _clean_value(row.get(mid_col)) if mid_col else "Unknown"
                low_value = _clean_value(row.get(low_col)) if low_col else None

                # Skip rows without EGA Type (LOW level is required)
                if not low_value:
                    warnings.append(f"Row {row_num}: Missing EGA Type, skipping")
                    continue

                # Use defaults for missing HIGH/MID
                if not high_value:
                    high_value = "Unknown Business Process"
                if not mid_value:
                    mid_value = "Unknown FSLI"

                # Extract metadata
                ref_no = _clean_value(row.get(ref_col)) if ref_col else None
                status = _clean_value(row.get(status_col)) if status_col else None
                metadata = _extract_metadata(row, columns, hierarchy_columns)

                # Create/get HIGH level node (Business Process)
                high_key = (HierarchyLevel.HIGH, None, high_value)
                if high_key not in node_registry:
                    high_node = AuditHierarchy(
                        id=_generate_hierarchy_id(HierarchyLevel.HIGH),
                        project_id=project_id,
                        level=HierarchyLevel.HIGH,
                        parent_id=None,
                        name=high_value,
                        source_column=high_col or "Unknown",
                        source_row=row_num,
                        metadata={"first_occurrence": row_num},
                    )
                    hierarchy.append(high_node)
                    node_registry[high_key] = high_node.id
                    high_count += 1

                high_id = node_registry[high_key]

                # Create/get MID level node (Primary FSLI)
                mid_key = (HierarchyLevel.MID, high_id, mid_value)
                if mid_key not in node_registry:
                    mid_node = AuditHierarchy(
                        id=_generate_hierarchy_id(HierarchyLevel.MID),
                        project_id=project_id,
                        level=HierarchyLevel.MID,
                        parent_id=high_id,
                        name=mid_value,
                        source_column=mid_col or "Unknown",
                        source_row=row_num,
                        metadata={"first_occurrence": row_num, "business_process": high_value},
                    )
                    hierarchy.append(mid_node)
                    node_registry[mid_key] = mid_node.id
                    mid_count += 1

                mid_id = node_registry[mid_key]

                # Create LOW level node (EGA Type) - always create, no deduplication
                low_node = AuditHierarchy(
                    id=_generate_hierarchy_id(HierarchyLevel.LOW),
                    project_id=project_id,
                    level=HierarchyLevel.LOW,
                    parent_id=mid_id,
                    name=low_value,
                    source_column=low_col,
                    source_row=row_num,
                    ref_no=ref_no,
                    status=status,
                    metadata={
                        **metadata,
                        "business_process": high_value,
                        "primary_fsli": mid_value,
                    },
                )
                hierarchy.append(low_node)
                low_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: Error processing - {str(e)}")

        return HierarchyParseResult(
            success=len(hierarchy) > 0,
            hierarchy=hierarchy,
            high_level_count=high_count,
            mid_level_count=mid_count,
            low_level_count=low_count,
            total_rows_processed=len(df),
            errors=errors,
            warnings=warnings,
            metadata={
                "column_mapping": {
                    "high": high_col,
                    "mid": mid_col,
                    "low": low_col,
                    "ref_no": ref_col,
                    "status": status_col,
                },
            },
        )

    def parse_sync(
        self,
        file_path: str,
        project_id: str,
        sheet_name: Optional[str] = None,
    ) -> HierarchyParseResult:
        """
        Synchronous version of parse for non-async contexts.

        Args:
            file_path: Path to the Excel file
            project_id: Project ID to associate hierarchy nodes with
            sheet_name: Specific sheet to parse (optional)

        Returns:
            HierarchyParseResult with parsed hierarchy
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.parse(file_path, project_id, sheet_name)
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_hierarchy_summary(hierarchy: List[AuditHierarchy]) -> Dict[str, Any]:
    """
    Get summary statistics for a hierarchy.

    Args:
        hierarchy: List of AuditHierarchy nodes

    Returns:
        Summary dictionary with counts and statistics
    """
    if not hierarchy:
        return {
            "total": 0,
            "by_level": {},
            "unique_business_processes": 0,
            "unique_fslis": 0,
        }

    level_counts = {}
    business_processes = set()
    fslis = set()

    for node in hierarchy:
        level = node.level.value if isinstance(node.level, HierarchyLevel) else node.level
        level_counts[level] = level_counts.get(level, 0) + 1

        if node.level == HierarchyLevel.HIGH:
            business_processes.add(node.name)
        elif node.level == HierarchyLevel.MID:
            fslis.add(node.name)

    return {
        "total": len(hierarchy),
        "by_level": level_counts,
        "unique_business_processes": len(business_processes),
        "unique_fslis": len(fslis),
    }


def filter_hierarchy_by_level(
    hierarchy: List[AuditHierarchy],
    level: HierarchyLevel,
) -> List[AuditHierarchy]:
    """
    Filter hierarchy nodes by level.

    Args:
        hierarchy: List of AuditHierarchy nodes
        level: Target hierarchy level

    Returns:
        Filtered list of nodes
    """
    return [node for node in hierarchy if node.level == level]


def get_children(
    hierarchy: List[AuditHierarchy],
    parent_id: str,
) -> List[AuditHierarchy]:
    """
    Get all direct children of a parent node.

    Args:
        hierarchy: List of AuditHierarchy nodes
        parent_id: Parent node ID

    Returns:
        List of child nodes
    """
    return [node for node in hierarchy if node.parent_id == parent_id]


def get_descendants(
    hierarchy: List[AuditHierarchy],
    parent_id: str,
) -> List[AuditHierarchy]:
    """
    Get all descendants (children, grandchildren, etc.) of a parent node.

    Args:
        hierarchy: List of AuditHierarchy nodes
        parent_id: Parent node ID

    Returns:
        List of all descendant nodes
    """
    descendants = []
    children = get_children(hierarchy, parent_id)
    descendants.extend(children)

    for child in children:
        descendants.extend(get_descendants(hierarchy, child.id))

    return descendants


def hierarchy_to_tree(hierarchy: List[AuditHierarchy]) -> List[Dict[str, Any]]:
    """
    Convert flat hierarchy list to nested tree structure.

    Args:
        hierarchy: List of AuditHierarchy nodes

    Returns:
        Nested tree structure with children arrays
    """
    # Create lookup by ID
    node_map = {node.id: {**node.to_dict(), "children": []} for node in hierarchy}

    # Build tree
    roots = []
    for node in hierarchy:
        node_dict = node_map[node.id]
        if node.parent_id is None:
            roots.append(node_dict)
        elif node.parent_id in node_map:
            node_map[node.parent_id]["children"].append(node_dict)

    return roots
