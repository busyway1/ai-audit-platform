from langchain_core.tools import tool
from typing import Dict, List, Any, Literal


@tool
def financial_analyzer(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    재무제표와 시산표의 정합성을 검증.

    Validates the consistency between financial statements and trial balance.
    This is a critical audit procedure to ensure the accuracy of financial data.

    Args:
        data: Dictionary containing:
            - balance_sheet (Dict): Balance sheet data with total_assets, total_liabilities, total_equity
            - trial_balance (Dict): Trial balance data with total_debit, total_credit
            - income_statement (Dict, optional): Income statement data for additional validation

    Returns:
        Dictionary containing:
            - is_matched (bool): Whether the financial data is consistent
            - discrepancies (List[Dict]): List of identified discrepancies
            - risk_level (str): Risk assessment - "Low", "Medium", or "High"
            - recommendations (List[str]): Suggested actions based on findings

    Example:
        >>> data = {
        ...     "balance_sheet": {
        ...         "total_assets": 1000000,
        ...         "total_liabilities": 600000,
        ...         "total_equity": 400000
        ...     },
        ...     "trial_balance": {
        ...         "total_debit": 1000000,
        ...         "total_credit": 1000000
        ...     }
        ... }
        >>> result = financial_analyzer(data)
        >>> print(result["is_matched"])
        True
    """
    # Extract financial data
    balance_sheet = data.get("balance_sheet", {})
    trial_balance = data.get("trial_balance", {})
    income_statement = data.get("income_statement", {})

    # Initialize result structure
    discrepancies: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    # Validation 1: Balance Sheet equation (Assets = Liabilities + Equity)
    total_assets = balance_sheet.get("total_assets", 0)
    total_liabilities = balance_sheet.get("total_liabilities", 0)
    total_equity = balance_sheet.get("total_equity", 0)

    bs_equation_diff = total_assets - (total_liabilities + total_equity)
    if abs(bs_equation_diff) > 0.01:  # Allow for minor rounding differences
        discrepancies.append({
            "type": "Balance Sheet Equation Violation",
            "description": "Assets ≠ Liabilities + Equity",
            "assets": total_assets,
            "liabilities_plus_equity": total_liabilities + total_equity,
            "difference": bs_equation_diff,
            "severity": "Critical"
        })
        recommendations.append(
            "Review balance sheet accounts for posting errors or missing entries"
        )

    # Validation 2: Trial Balance consistency (Debits = Credits)
    total_debit = trial_balance.get("total_debit", 0)
    total_credit = trial_balance.get("total_credit", 0)

    tb_diff = total_debit - total_credit
    if abs(tb_diff) > 0.01:
        discrepancies.append({
            "type": "Trial Balance Imbalance",
            "description": "Total debits do not equal total credits",
            "total_debit": total_debit,
            "total_credit": total_credit,
            "difference": tb_diff,
            "severity": "Critical"
        })
        recommendations.append(
            "Investigate journal entries for incorrect debit/credit postings"
        )

    # Validation 3: Balance Sheet total matches Trial Balance total
    if total_assets > 0 and total_debit > 0:
        bs_tb_diff = total_assets - total_debit
        if abs(bs_tb_diff) > 0.01:
            discrepancies.append({
                "type": "Balance Sheet - Trial Balance Mismatch",
                "description": "Total assets do not match trial balance total debits",
                "balance_sheet_total": total_assets,
                "trial_balance_total": total_debit,
                "difference": bs_tb_diff,
                "severity": "High"
            })
            recommendations.append(
                "Reconcile balance sheet accounts with trial balance GL accounts"
            )

    # Validation 4: Income Statement validation (if provided)
    if income_statement:
        net_income = income_statement.get("net_income", 0)
        retained_earnings_change = balance_sheet.get("retained_earnings_change", 0)

        # Check if net income ties to retained earnings (simplified check)
        if abs(net_income - retained_earnings_change) > 0.01:
            discrepancies.append({
                "type": "Income Statement - Balance Sheet Link",
                "description": "Net income does not tie to retained earnings change",
                "net_income": net_income,
                "retained_earnings_change": retained_earnings_change,
                "difference": net_income - retained_earnings_change,
                "severity": "Medium"
            })
            recommendations.append(
                "Verify dividend payments and other retained earnings adjustments"
            )

    # Determine risk level based on discrepancies
    risk_level: Literal["Low", "Medium", "High"]
    if not discrepancies:
        risk_level = "Low"
    elif any(d.get("severity") == "Critical" for d in discrepancies):
        risk_level = "High"
    elif any(d.get("severity") == "High" for d in discrepancies):
        risk_level = "High"
    else:
        risk_level = "Medium"

    # Add general recommendation if no issues found
    if not discrepancies:
        recommendations.append(
            "Financial data appears consistent. Proceed with substantive testing."
        )

    return {
        "is_matched": len(discrepancies) == 0,
        "discrepancies": discrepancies,
        "risk_level": risk_level,
        "recommendations": recommendations,
        "summary": {
            "total_discrepancies": len(discrepancies),
            "critical_issues": len([d for d in discrepancies if d.get("severity") == "Critical"]),
            "high_issues": len([d for d in discrepancies if d.get("severity") == "High"]),
            "medium_issues": len([d for d in discrepancies if d.get("severity") == "Medium"])
        }
    }
