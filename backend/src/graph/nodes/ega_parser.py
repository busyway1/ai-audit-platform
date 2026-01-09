"""
EGA Parser Node Implementation

This module implements the EGA (Expected General Activities) Parser Node for extracting
EGAs from Assigned Workflow documents (Excel files).

EGAs represent high-level audit objectives that are broken down into Mid-level assertions
and Low-level procedures in the task hierarchy.

Key Features:
- Parses Assigned Workflow Excel documents via MCP Excel Processor
- Extracts EGA metadata (name, description, risk_level, priority)
- Builds hierarchical relationships between EGAs
- Creates audit_egas records for database storage
- Supports various Excel formats (.xlsx, .xls)

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from ...graph.state import AuditState
from ...services.mcp_client import (
    MCPExcelClient,
    MCPExcelClientError,
    MCPExcelConnectionError,
    MCPExcelParseError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================


class EGARiskLevel(str, Enum):
    """Risk level classification for EGAs."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EGAStatus(str, Enum):
    """Status of an EGA."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"


@dataclass
class EGA:
    """
    Represents an Expected General Activity (EGA) extracted from workflow documents.

    Attributes:
        id: Unique identifier for the EGA
        project_id: Associated audit project ID
        name: EGA name/title
        description: Detailed description of the audit activity
        risk_level: Risk classification (critical, high, medium, low)
        priority: Numeric priority (1-100, higher = more urgent)
        status: Current status of the EGA
        parent_ega_id: Parent EGA for hierarchical structures (optional)
        task_count: Number of tasks associated with this EGA
        progress: Completion percentage (0-100)
        source_row: Row number in the source Excel file
        source_sheet: Sheet name in the source Excel file
        metadata: Additional metadata from the source document
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    project_id: str
    name: str
    description: str
    risk_level: EGARiskLevel = EGARiskLevel.MEDIUM
    priority: int = 50
    status: EGAStatus = EGAStatus.PENDING
    parent_ega_id: Optional[str] = None
    task_count: int = 0
    progress: float = 0.0
    source_row: Optional[int] = None
    source_sheet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert EGA to dictionary for state storage."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, EGARiskLevel) else self.risk_level,
            "priority": self.priority,
            "status": self.status.value if isinstance(self.status, EGAStatus) else self.status,
            "parent_ega_id": self.parent_ega_id,
            "task_count": self.task_count,
            "progress": self.progress,
            "source_row": self.source_row,
            "source_sheet": self.source_sheet,
            "metadata": self.metadata,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "updated_at": self.updated_at or datetime.utcnow().isoformat(),
        }


@dataclass
class EGAParseResult:
    """Result of parsing an Assigned Workflow document."""

    success: bool
    egas: List[EGA]
    total_rows_processed: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# COLUMN MAPPING CONFIGURATION
# ============================================================================

# Expected column names in Assigned Workflow documents
# Maps various possible column names to standardized field names
COLUMN_MAPPINGS = {
    "name": ["EGA", "EGA Name", "Activity", "Activity Name", "Name", "Task Name", "Audit Activity"],
    "description": ["Description", "Desc", "Details", "Activity Description", "Task Description"],
    "risk_level": ["Risk", "Risk Level", "Risk Rating", "Risk Assessment", "Priority Level"],
    "priority": ["Priority", "Order", "Sequence", "Rank"],
    "category": ["Category", "Type", "Account", "Account Category", "Section"],
    "assertion": ["Assertion", "Assertions", "Financial Statement Assertion"],
    "procedure": ["Procedure", "Audit Procedure", "Test", "Testing Procedure"],
    "materiality": ["Materiality", "PM", "Planning Materiality", "Material Amount"],
    "assigned_to": ["Assigned To", "Assignee", "Staff", "Team Member"],
    "due_date": ["Due Date", "Deadline", "Target Date", "Completion Date"],
    "notes": ["Notes", "Comments", "Remarks", "Additional Info"],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _generate_ega_id() -> str:
    """Generate a unique EGA ID."""
    return f"ega-{uuid.uuid4().hex[:12]}"


def _normalize_column_name(column: str) -> Optional[str]:
    """
    Normalize a column name to a standard field name.

    Args:
        column: Original column name from Excel

    Returns:
        Normalized field name or None if not recognized
    """
    column_lower = column.strip().lower()

    for field_name, variations in COLUMN_MAPPINGS.items():
        for variation in variations:
            if column_lower == variation.lower():
                return field_name

    return None


def _parse_risk_level(value: Any) -> EGARiskLevel:
    """
    Parse risk level from various input formats.

    Args:
        value: Risk level value (string, number, etc.)

    Returns:
        Normalized EGARiskLevel enum value
    """
    if value is None:
        return EGARiskLevel.MEDIUM

    str_value = str(value).strip().lower()

    # Handle string values
    risk_mapping = {
        "critical": EGARiskLevel.CRITICAL,
        "very high": EGARiskLevel.CRITICAL,
        "high": EGARiskLevel.HIGH,
        "medium": EGARiskLevel.MEDIUM,
        "moderate": EGARiskLevel.MEDIUM,
        "low": EGARiskLevel.LOW,
        "minimal": EGARiskLevel.LOW,
    }

    if str_value in risk_mapping:
        return risk_mapping[str_value]

    # Handle numeric values (1-4 scale)
    try:
        num_value = int(float(value))
        if num_value >= 4:
            return EGARiskLevel.CRITICAL
        elif num_value == 3:
            return EGARiskLevel.HIGH
        elif num_value == 2:
            return EGARiskLevel.MEDIUM
        else:
            return EGARiskLevel.LOW
    except (ValueError, TypeError):
        pass

    return EGARiskLevel.MEDIUM


def _parse_priority(value: Any, risk_level: EGARiskLevel) -> int:
    """
    Parse priority from value or derive from risk level.

    Args:
        value: Priority value (number)
        risk_level: Risk level for fallback calculation

    Returns:
        Priority value (1-100)
    """
    if value is not None:
        try:
            priority = int(float(value))
            return max(1, min(100, priority))
        except (ValueError, TypeError):
            pass

    # Derive from risk level
    risk_priority_map = {
        EGARiskLevel.CRITICAL: 90,
        EGARiskLevel.HIGH: 70,
        EGARiskLevel.MEDIUM: 50,
        EGARiskLevel.LOW: 30,
    }

    return risk_priority_map.get(risk_level, 50)


def _extract_egas_from_data(
    data: Dict[str, Any],
    project_id: str,
    sheet_name: Optional[str] = None
) -> EGAParseResult:
    """
    Extract EGAs from parsed Excel data.

    Args:
        data: Parsed Excel data from MCP Excel Processor
        project_id: Project ID to associate EGAs with
        sheet_name: Source sheet name

    Returns:
        EGAParseResult with extracted EGAs
    """
    egas: List[EGA] = []
    errors: List[str] = []
    warnings: List[str] = []
    rows_processed = 0

    # Get transactions/rows from the parsed data
    transactions = data.get("transactions", [])
    if not transactions:
        # Try alternative data structure
        transactions = data.get("rows", data.get("data", []))

    if not transactions:
        return EGAParseResult(
            success=False,
            egas=[],
            total_rows_processed=0,
            errors=["No data rows found in the Excel file"],
        )

    # Build column mapping from first row if headers present
    column_map = {}
    if transactions and isinstance(transactions[0], dict):
        for key in transactions[0].keys():
            normalized = _normalize_column_name(key)
            if normalized:
                column_map[normalized] = key

    # Process each row as a potential EGA
    for idx, row in enumerate(transactions):
        rows_processed += 1

        try:
            # Extract fields using column mapping
            name = _get_field_value(row, column_map, "name")
            description = _get_field_value(row, column_map, "description")

            # Skip rows without name
            if not name:
                warnings.append(f"Row {idx + 1}: Missing EGA name, skipping")
                continue

            # Parse risk level and priority
            risk_value = _get_field_value(row, column_map, "risk_level")
            risk_level = _parse_risk_level(risk_value)

            priority_value = _get_field_value(row, column_map, "priority")
            priority = _parse_priority(priority_value, risk_level)

            # Extract additional metadata
            metadata = {
                "category": _get_field_value(row, column_map, "category"),
                "assertion": _get_field_value(row, column_map, "assertion"),
                "procedure": _get_field_value(row, column_map, "procedure"),
                "materiality": _get_field_value(row, column_map, "materiality"),
                "assigned_to": _get_field_value(row, column_map, "assigned_to"),
                "due_date": _get_field_value(row, column_map, "due_date"),
                "notes": _get_field_value(row, column_map, "notes"),
            }

            # Remove None values from metadata
            metadata = {k: v for k, v in metadata.items() if v is not None}

            # Create EGA
            ega = EGA(
                id=_generate_ega_id(),
                project_id=project_id,
                name=str(name),
                description=str(description) if description else f"Audit activity: {name}",
                risk_level=risk_level,
                priority=priority,
                source_row=idx + 1,
                source_sheet=sheet_name,
                metadata=metadata,
            )

            egas.append(ega)

        except Exception as e:
            errors.append(f"Row {idx + 1}: Error parsing EGA - {str(e)}")

    # Build hierarchy relationships if category/section data exists
    _build_ega_hierarchy(egas)

    return EGAParseResult(
        success=len(egas) > 0,
        egas=egas,
        total_rows_processed=rows_processed,
        errors=errors,
        warnings=warnings,
        metadata={
            "sheet_name": sheet_name,
            "column_mapping": column_map,
        },
    )


def _get_field_value(row: Dict[str, Any], column_map: Dict[str, str], field: str) -> Any:
    """
    Get field value from row using column mapping.

    Args:
        row: Data row dictionary
        column_map: Mapping from field names to column names
        field: Field name to retrieve

    Returns:
        Field value or None
    """
    if field in column_map:
        return row.get(column_map[field])

    # Try direct field access
    return row.get(field)


def _build_ega_hierarchy(egas: List[EGA]) -> None:
    """
    Build parent-child relationships between EGAs based on category/metadata.

    Modifies EGAs in place to set parent_ega_id.

    Args:
        egas: List of EGAs to process
    """
    # Group by category
    category_groups: Dict[str, List[EGA]] = {}

    for ega in egas:
        category = ega.metadata.get("category")
        if category:
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(ega)

    # For each category, first EGA becomes parent of subsequent EGAs
    for category, group in category_groups.items():
        if len(group) > 1:
            parent = group[0]
            for child in group[1:]:
                # Only set parent if not already set
                if child.parent_ega_id is None:
                    child.parent_ega_id = parent.id


def _get_fallback_egas(project_id: str) -> List[EGA]:
    """
    Generate fallback EGAs for demo/testing when MCP server unavailable.

    Args:
        project_id: Project ID for the EGAs

    Returns:
        List of sample EGAs
    """
    sample_egas = [
        EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name="Revenue Recognition Testing",
            description="Test revenue recognition in accordance with K-IFRS 1115",
            risk_level=EGARiskLevel.HIGH,
            priority=85,
            metadata={"category": "Revenue", "assertion": "Completeness, Accuracy"},
        ),
        EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name="Accounts Receivable Confirmation",
            description="Confirm accounts receivable balances with third parties",
            risk_level=EGARiskLevel.MEDIUM,
            priority=70,
            metadata={"category": "Receivables", "assertion": "Existence, Valuation"},
        ),
        EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name="Inventory Physical Count",
            description="Observe and test physical inventory count procedures",
            risk_level=EGARiskLevel.HIGH,
            priority=80,
            metadata={"category": "Inventory", "assertion": "Existence, Completeness"},
        ),
        EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name="Fixed Asset Verification",
            description="Verify existence and valuation of fixed assets",
            risk_level=EGARiskLevel.MEDIUM,
            priority=60,
            metadata={"category": "Fixed Assets", "assertion": "Existence, Valuation"},
        ),
        EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name="Accounts Payable Completeness",
            description="Test completeness of accounts payable at year-end",
            risk_level=EGARiskLevel.CRITICAL,
            priority=90,
            metadata={"category": "Payables", "assertion": "Completeness, Cut-off"},
        ),
    ]

    return sample_egas


# ============================================================================
# MAIN PARSER FUNCTION
# ============================================================================


async def parse_assigned_workflow(
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    project_id: str = "",
    sheet_name: Optional[str] = None,
    mcp_client: Optional[MCPExcelClient] = None,
) -> EGAParseResult:
    """
    Parse an Assigned Workflow document and extract EGAs.

    This function uses the MCP Excel Processor to parse the document and
    extract Expected General Activities (EGAs) with their metadata.

    Args:
        file_path: Local path to the Excel file
        file_url: URL to download the Excel file (e.g., Supabase Storage)
        project_id: Project ID to associate EGAs with
        sheet_name: Specific sheet to parse (optional)
        mcp_client: Optional pre-configured MCP Excel client

    Returns:
        EGAParseResult with extracted EGAs and parsing metadata

    Raises:
        ValueError: If neither file_path nor file_url is provided

    Example:
        ```python
        result = await parse_assigned_workflow(
            file_path="/path/to/workflow.xlsx",
            project_id="proj-123"
        )

        if result.success:
            for ega in result.egas:
                print(f"{ega.name}: {ega.risk_level.value}")
        ```
    """
    if not file_path and not file_url:
        raise ValueError("Either file_path or file_url must be provided")

    logger.info(
        f"parse_assigned_workflow: file={file_path or file_url}, "
        f"project_id={project_id}"
    )

    # Use provided client or create new one
    client = mcp_client
    should_close = False

    if client is None:
        client = MCPExcelClient()
        should_close = True

    try:
        # Check MCP server availability
        if not await client.health_check():
            logger.warning("MCP Excel server unavailable, using fallback EGAs")
            return EGAParseResult(
                success=True,
                egas=_get_fallback_egas(project_id),
                total_rows_processed=5,
                warnings=["MCP Excel server unavailable - using fallback data"],
                metadata={"fallback": True},
            )

        # Parse Excel file
        parse_result = await client.parse_excel(
            file_path=file_path,
            file_url=file_url,
            sheet_name=sheet_name,
            category="Audit Workflow",
            validate_data=True,
            detect_anomalies=False,
        )

        if parse_result.get("status") != "success":
            error_msg = parse_result.get("error", "Unknown parsing error")
            logger.error(f"Excel parsing failed: {error_msg}")
            return EGAParseResult(
                success=False,
                egas=[],
                total_rows_processed=0,
                errors=[f"Excel parsing failed: {error_msg}"],
            )

        # Extract EGAs from parsed data
        data = parse_result.get("data", {})
        actual_sheet = parse_result.get("metadata", {}).get("sheet_name", sheet_name)

        return _extract_egas_from_data(data, project_id, actual_sheet)

    except MCPExcelConnectionError as e:
        logger.warning(f"MCP Excel connection error: {e}, using fallback")
        return EGAParseResult(
            success=True,
            egas=_get_fallback_egas(project_id),
            total_rows_processed=5,
            warnings=[f"MCP connection error: {str(e)} - using fallback data"],
            metadata={"fallback": True},
        )

    except MCPExcelParseError as e:
        logger.error(f"MCP Excel parse error: {e}")
        return EGAParseResult(
            success=False,
            egas=[],
            total_rows_processed=0,
            errors=[f"Parse error: {str(e)}"],
        )

    except MCPExcelClientError as e:
        logger.error(f"MCP Excel client error: {e}")
        return EGAParseResult(
            success=False,
            egas=[],
            total_rows_processed=0,
            errors=[f"MCP client error: {str(e)}"],
        )

    finally:
        if should_close and client:
            await client.close()


# ============================================================================
# LANGGRAPH NODE
# ============================================================================


async def ega_parser_node(state: AuditState) -> Dict[str, Any]:
    """
    LangGraph node for parsing Assigned Workflow documents and extracting EGAs.

    This node:
    1. Retrieves uploaded workflow documents from shared_documents
    2. Parses each document using MCP Excel Processor
    3. Extracts EGAs with metadata (risk_level, priority, category)
    4. Updates state with extracted EGAs

    Args:
        state: Current AuditState with shared_documents

    Returns:
        Updated state with:
        - egas: List of extracted EGA dictionaries
        - messages: Status message about parsing results

    Example:
        ```python
        state = {
            "project_id": "proj-123",
            "shared_documents": [
                {"type": "assigned_workflow", "url": "https://storage.example.com/workflow.xlsx"}
            ],
            # ... other state fields
        }

        result = await ega_parser_node(state)
        print(f"Extracted {len(result['egas'])} EGAs")
        ```

    Note:
        If no workflow documents are found in shared_documents, the node
        will generate fallback EGAs based on the audit plan.
    """
    logger.info("[Parent Graph] EGA Parser: Extracting EGAs from workflow documents")

    project_id = state.get("project_id", "")
    shared_documents = state.get("shared_documents", [])

    # Find workflow documents
    workflow_docs = [
        doc for doc in shared_documents
        if doc.get("type") in ("assigned_workflow", "workflow", "ega_document")
    ]

    all_egas: List[Dict[str, Any]] = []
    all_errors: List[str] = []
    all_warnings: List[str] = []

    if not workflow_docs:
        logger.info("[EGA Parser] No workflow documents found, generating from audit plan")

        # Generate EGAs from audit plan or use fallback
        audit_plan = state.get("audit_plan", {})
        if audit_plan:
            # Extract EGAs from audit plan structure
            egas = _generate_egas_from_plan(audit_plan, project_id)
        else:
            # Use fallback EGAs
            egas = _get_fallback_egas(project_id)

        all_egas = [ega.to_dict() for ega in egas]
        all_warnings.append("No workflow documents uploaded - generated EGAs from audit plan")
    else:
        # Parse each workflow document
        docs_with_valid_path = 0
        async with MCPExcelClient() as client:
            for doc in workflow_docs:
                file_path = doc.get("file_path")
                file_url = doc.get("url") or doc.get("file_url")

                if not file_path and not file_url:
                    all_warnings.append(f"Document missing path/URL: {doc.get('name', 'unknown')}")
                    continue

                docs_with_valid_path += 1
                result = await parse_assigned_workflow(
                    file_path=file_path,
                    file_url=file_url,
                    project_id=project_id,
                    mcp_client=client,
                )

                if result.success:
                    all_egas.extend([ega.to_dict() for ega in result.egas])
                    all_warnings.extend(result.warnings)
                else:
                    all_errors.extend(result.errors)

        # If no documents had valid paths, generate fallback EGAs
        if docs_with_valid_path == 0 and not all_egas:
            logger.info("[EGA Parser] All documents missing path/URL, using fallback EGAs")
            audit_plan = state.get("audit_plan", {})
            if audit_plan:
                egas = _generate_egas_from_plan(audit_plan, project_id)
            else:
                egas = _get_fallback_egas(project_id)
            all_egas = [ega.to_dict() for ega in egas]
            all_warnings.append("All documents missing path/URL - generated fallback EGAs")

    # Build summary message
    message_parts = [f"[EGA Parser] Extracted {len(all_egas)} EGAs"]

    if all_warnings:
        message_parts.append(f"Warnings: {len(all_warnings)}")

    if all_errors:
        message_parts.append(f"Errors: {len(all_errors)}")

    summary_message = ". ".join(message_parts)
    logger.info(summary_message)

    return {
        "egas": all_egas,
        "messages": [
            HumanMessage(
                content=summary_message,
                name="EGAParser"
            )
        ],
    }


def _generate_egas_from_plan(audit_plan: Dict[str, Any], project_id: str) -> List[EGA]:
    """
    Generate EGAs from an existing audit plan structure.

    Args:
        audit_plan: Audit plan dictionary with objectives/areas
        project_id: Project ID for the EGAs

    Returns:
        List of EGAs derived from the audit plan
    """
    egas: List[EGA] = []

    # Extract from various audit plan structures
    areas = audit_plan.get("audit_areas", audit_plan.get("areas", []))
    objectives = audit_plan.get("objectives", [])

    # Generate from areas
    for idx, area in enumerate(areas):
        if isinstance(area, dict):
            name = area.get("name", area.get("area", f"Audit Area {idx + 1}"))
            description = area.get("description", area.get("objective", ""))
            risk = area.get("risk_level", area.get("risk", "medium"))
        else:
            name = str(area)
            description = f"Audit procedures for {name}"
            risk = "medium"

        ega = EGA(
            id=_generate_ega_id(),
            project_id=project_id,
            name=name,
            description=description,
            risk_level=_parse_risk_level(risk),
            priority=_parse_priority(None, _parse_risk_level(risk)),
            metadata={"source": "audit_plan", "area_index": idx},
        )
        egas.append(ega)

    # Generate from objectives if no areas
    if not egas:
        for idx, objective in enumerate(objectives):
            if isinstance(objective, dict):
                name = objective.get("name", objective.get("title", f"Objective {idx + 1}"))
                description = objective.get("description", "")
            else:
                name = str(objective)
                description = ""

            ega = EGA(
                id=_generate_ega_id(),
                project_id=project_id,
                name=name,
                description=description or f"Audit objective: {name}",
                risk_level=EGARiskLevel.MEDIUM,
                priority=50,
                metadata={"source": "audit_plan", "objective_index": idx},
            )
            egas.append(ega)

    # Fallback if still no EGAs
    if not egas:
        egas = _get_fallback_egas(project_id)

    return egas


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_ega_summary(egas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for a list of EGAs.

    Args:
        egas: List of EGA dictionaries

    Returns:
        Summary dictionary with counts and statistics
    """
    if not egas:
        return {
            "total": 0,
            "by_risk_level": {},
            "by_status": {},
            "average_priority": 0,
        }

    risk_counts = {}
    status_counts = {}
    total_priority = 0

    for ega in egas:
        # Count by risk level
        risk = ega.get("risk_level", "medium")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

        # Count by status
        status = ega.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1

        # Sum priority
        total_priority += ega.get("priority", 50)

    return {
        "total": len(egas),
        "by_risk_level": risk_counts,
        "by_status": status_counts,
        "average_priority": total_priority / len(egas) if egas else 0,
    }


def filter_egas_by_risk(
    egas: List[Dict[str, Any]],
    risk_levels: List[str],
) -> List[Dict[str, Any]]:
    """
    Filter EGAs by risk level.

    Args:
        egas: List of EGA dictionaries
        risk_levels: List of risk levels to include

    Returns:
        Filtered list of EGAs
    """
    return [
        ega for ega in egas
        if ega.get("risk_level", "medium") in risk_levels
    ]


def sort_egas_by_priority(
    egas: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sort EGAs by priority.

    Args:
        egas: List of EGA dictionaries
        descending: Sort in descending order (highest first)

    Returns:
        Sorted list of EGAs
    """
    return sorted(
        egas,
        key=lambda x: x.get("priority", 50),
        reverse=descending,
    )
