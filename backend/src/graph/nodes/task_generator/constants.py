"""
Task Generator Constants and Enums

This module defines enums, constants, and mappings used throughout the task
generation system for the 3-level audit task hierarchy.

Reference: AUDIT_PLATFORM_SPECIFICATION.md Section 4.4
"""

from enum import Enum
from typing import Dict, List


class TaskLevel(str, Enum):
    """Task hierarchy level classification."""

    HIGH = "High"  # EGA level - top-level audit objectives
    MID = "Mid"    # Assertion level - financial statement assertions
    LOW = "Low"    # Procedure level - specific audit procedures


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "Pending"
    IN_PROGRESS = "In-Progress"
    REVIEW_REQUIRED = "Review-Required"
    COMPLETED = "Completed"
    FAILED = "Failed"


class RiskLevel(str, Enum):
    """Risk level classification aligned with EGA risk levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Mapping from EGA risk levels to numeric risk scores
RISK_SCORE_MAP: Dict[str, int] = {
    RiskLevel.CRITICAL: 95,
    RiskLevel.HIGH: 75,
    RiskLevel.MEDIUM: 50,
    RiskLevel.LOW: 25,
    "critical": 95,
    "high": 75,
    "medium": 50,
    "low": 25,
}

# Standard financial statement assertions for audit tasks
STANDARD_ASSERTIONS: List[Dict[str, str]] = [
    {
        "name": "Existence/Occurrence",
        "description": "Assets, liabilities, and equity interests exist; recorded transactions occurred",
        "code": "EO",
    },
    {
        "name": "Completeness",
        "description": "All transactions and accounts that should be recorded have been recorded",
        "code": "C",
    },
    {
        "name": "Valuation/Accuracy",
        "description": "Assets, liabilities, and equity interests are valued appropriately",
        "code": "VA",
    },
    {
        "name": "Rights and Obligations",
        "description": "The entity holds or controls rights to assets; liabilities are obligations",
        "code": "RO",
    },
    {
        "name": "Presentation and Disclosure",
        "description": "Financial information is appropriately presented and disclosed",
        "code": "PD",
    },
    {
        "name": "Cut-off",
        "description": "Transactions are recorded in the correct accounting period",
        "code": "CO",
    },
]

# Standard audit procedures mapped by assertion
ASSERTION_PROCEDURES: Dict[str, List[str]] = {
    "EO": [  # Existence/Occurrence
        "Physical inspection of assets",
        "Third-party confirmation",
        "Examination of supporting documentation",
        "Review of subsequent events",
    ],
    "C": [  # Completeness
        "Analytical procedures for unusual patterns",
        "Cut-off testing at period end",
        "Search for unrecorded liabilities",
        "Bank reconciliation review",
    ],
    "VA": [  # Valuation/Accuracy
        "Recalculation of amounts",
        "Review of valuation methodologies",
        "Testing of pricing accuracy",
        "Assessment of allowances and provisions",
    ],
    "RO": [  # Rights and Obligations
        "Review of contracts and agreements",
        "Verification of ownership documents",
        "Inquiry of management",
        "Legal confirmation",
    ],
    "PD": [  # Presentation and Disclosure
        "Review of financial statement presentation",
        "Assessment of disclosure completeness",
        "Verification of note accuracy",
        "Review of related party disclosures",
    ],
    "CO": [  # Cut-off
        "Testing of transactions near period end",
        "Review of subsequent period entries",
        "Examination of shipping documents",
        "Analysis of billing timing",
    ],
}
