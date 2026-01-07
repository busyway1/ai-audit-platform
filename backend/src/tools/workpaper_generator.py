from langchain_core.tools import tool
from typing import Dict, List, Any
from datetime import datetime


@tool
def workpaper_generator(data: Dict[str, Any]) -> str:
    """
    Generate standard audit workpaper in text format.

    Creates a formatted audit workpaper document that follows standard
    audit documentation practices. This tool generates the initial workpaper
    structure that can be exported to Excel/Word formats.

    Args:
        data: Dictionary containing:
            - task_category (str): Account or audit area being tested
            - auditor (str, optional): Name of auditor performing the work
            - review_date (str, optional): Date of review (ISO format)
            - procedures (List[str]): List of audit procedures performed
            - findings (List[str]): List of findings and observations
            - conclusion (str): Overall conclusion from the audit work
            - risk_rating (str, optional): Risk assessment - "Low", "Medium", "High"
            - sample_size (int, optional): Number of items tested
            - population_size (int, optional): Total population size
            - materiality_threshold (float, optional): Materiality amount

    Returns:
        Formatted workpaper text suitable for documentation

    Example:
        >>> data = {
        ...     "task_category": "Accounts Receivable",
        ...     "auditor": "John Smith",
        ...     "procedures": [
        ...         "Confirmed balances with customers",
        ...         "Tested aging report accuracy"
        ...     ],
        ...     "findings": ["No exceptions noted"],
        ...     "conclusion": "AR balance is fairly stated",
        ...     "risk_rating": "Low"
        ... }
        >>> workpaper = workpaper_generator(data)
        >>> print(workpaper)
    """
    # Extract workpaper data
    task_category = data.get("task_category", "N/A")
    auditor = data.get("auditor", "Not specified")
    review_date = data.get("review_date", datetime.now().strftime("%Y-%m-%d"))
    procedures = data.get("procedures", [])
    findings = data.get("findings", [])
    conclusion = data.get("conclusion", "No conclusion provided")
    risk_rating = data.get("risk_rating", "Not assessed")
    sample_size = data.get("sample_size")
    population_size = data.get("population_size")
    materiality_threshold = data.get("materiality_threshold")

    # Build workpaper sections
    sections: List[str] = []

    # Header section
    header = f"""
{'=' * 80}
                        AUDIT WORKPAPER
{'=' * 80}

Account/Area:           {task_category}
Prepared by:            {auditor}
Date:                   {review_date}
Risk Rating:            {risk_rating}
"""
    sections.append(header.strip())

    # Scope section (if sample data provided)
    if sample_size is not None or population_size is not None:
        scope = "\n\nSCOPE OF WORK:\n" + "-" * 80
        if population_size is not None:
            scope += f"\nPopulation Size:        {population_size:,}"
        if sample_size is not None:
            scope += f"\nSample Size:            {sample_size:,}"
            if population_size is not None:
                coverage = (sample_size / population_size) * 100
                scope += f"\nCoverage:               {coverage:.1f}%"
        if materiality_threshold is not None:
            scope += f"\nMateriality Threshold:  ${materiality_threshold:,.2f}"
        sections.append(scope)

    # Procedures section
    procedures_section = "\n\nAUDIT PROCEDURES PERFORMED:\n" + "-" * 80
    if procedures:
        for idx, procedure in enumerate(procedures, 1):
            procedures_section += f"\n{idx}. {procedure}"
    else:
        procedures_section += "\nNo procedures documented"
    sections.append(procedures_section)

    # Findings section
    findings_section = "\n\nFINDINGS AND OBSERVATIONS:\n" + "-" * 80
    if findings:
        for idx, finding in enumerate(findings, 1):
            # Determine if finding indicates an exception
            is_exception = any(
                keyword in finding.lower()
                for keyword in ["exception", "error", "discrepancy", "issue", "concern"]
            )
            marker = "[!]" if is_exception else "[ ]"
            findings_section += f"\n{marker} {idx}. {finding}"
    else:
        findings_section += "\n[ ] No findings to report"
    sections.append(findings_section)

    # Exceptions summary (if any exceptions found)
    exceptions = [f for f in findings if any(
        keyword in f.lower()
        for keyword in ["exception", "error", "discrepancy", "issue", "concern"]
    )]
    if exceptions:
        exceptions_section = "\n\nEXCEPTIONS REQUIRING FOLLOW-UP:\n" + "-" * 80
        for idx, exception in enumerate(exceptions, 1):
            exceptions_section += f"\n{idx}. {exception}"
        exceptions_section += "\n\nAction Required: Review and resolve exceptions before sign-off"
        sections.append(exceptions_section)

    # Conclusion section
    conclusion_section = "\n\nCONCLUSION:\n" + "-" * 80
    conclusion_section += f"\n{conclusion}"

    # Add risk-based conclusion enhancement
    if risk_rating == "High":
        conclusion_section += "\n\nNOTE: High risk rating requires additional review and supervisor approval."
    elif risk_rating == "Medium":
        conclusion_section += "\n\nNOTE: Medium risk rating - ensure all exceptions are addressed."

    sections.append(conclusion_section)

    # Sign-off section
    signoff = f"""

{'=' * 80}
REVIEW AND APPROVAL:

Prepared by:  {auditor}          Date: {review_date}     Signature: __________

Reviewed by:  __________         Date: __________         Signature: __________
{'=' * 80}
"""
    sections.append(signoff.strip())

    # Combine all sections
    workpaper = "\n".join(sections)

    return workpaper


@tool
def workpaper_validator(workpaper_text: str) -> Dict[str, Any]:
    """
    Validate completeness and quality of audit workpaper.

    Checks whether a workpaper meets minimum documentation standards
    for audit quality control.

    Args:
        workpaper_text: The generated workpaper text to validate

    Returns:
        Dictionary containing:
            - is_valid (bool): Whether workpaper meets standards
            - missing_elements (List[str]): Required elements that are missing
            - recommendations (List[str]): Suggestions for improvement

    Example:
        >>> workpaper = workpaper_generator({...})
        >>> validation = workpaper_validator(workpaper)
        >>> print(validation["is_valid"])
        True
    """
    missing_elements: List[str] = []
    recommendations: List[str] = []

    # Check for required sections
    required_sections = {
        "Account/Area": "Account or area being audited",
        "Prepared by": "Auditor name",
        "Date": "Workpaper date",
        "AUDIT PROCEDURES": "Procedures performed section",
        "FINDINGS": "Findings section",
        "CONCLUSION": "Conclusion statement"
    }

    for section, description in required_sections.items():
        if section not in workpaper_text:
            missing_elements.append(f"Missing {description}")

    # Check for quality indicators
    if "No procedures documented" in workpaper_text:
        recommendations.append(
            "Document specific audit procedures performed"
        )

    if workpaper_text.count("\n") < 20:
        recommendations.append(
            "Workpaper appears too brief - consider adding more detail"
        )

    if "[!]" in workpaper_text and "Action Required" not in workpaper_text:
        recommendations.append(
            "Exceptions noted but no follow-up actions documented"
        )

    if "Risk Rating:            Not assessed" in workpaper_text:
        recommendations.append(
            "Consider adding risk assessment to workpaper"
        )

    # Overall validation
    is_valid = len(missing_elements) == 0

    if is_valid and not recommendations:
        recommendations.append(
            "Workpaper meets documentation standards"
        )

    return {
        "is_valid": is_valid,
        "missing_elements": missing_elements,
        "recommendations": recommendations,
        "quality_score": max(0, 100 - (len(missing_elements) * 20) - (len(recommendations) * 5))
    }
