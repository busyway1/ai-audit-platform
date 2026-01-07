"""
Quick test script to verify native tools functionality.
Run this to ensure tools are working correctly.
"""

from financial_analyzer import financial_analyzer
from workpaper_generator import workpaper_generator, workpaper_validator


def test_financial_analyzer():
    """Test financial analyzer with sample data."""
    print("\n" + "=" * 80)
    print("Testing Financial Analyzer")
    print("=" * 80)

    # Test case 1: Balanced financials
    balanced_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "total_liabilities": 600000,
            "total_equity": 400000
        },
        "trial_balance": {
            "total_debit": 1000000,
            "total_credit": 1000000
        }
    }

    result = financial_analyzer.invoke({"data": balanced_data})
    print("\nTest 1 - Balanced Financials:")
    print(f"  Matched: {result['is_matched']}")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Discrepancies: {len(result['discrepancies'])}")

    # Test case 2: Imbalanced financials
    imbalanced_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "total_liabilities": 600000,
            "total_equity": 300000  # Should be 400000
        },
        "trial_balance": {
            "total_debit": 1000000,
            "total_credit": 950000  # Should be 1000000
        }
    }

    result = financial_analyzer.invoke({"data": imbalanced_data})
    print("\nTest 2 - Imbalanced Financials:")
    print(f"  Matched: {result['is_matched']}")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Discrepancies: {len(result['discrepancies'])}")
    for idx, disc in enumerate(result['discrepancies'], 1):
        print(f"    {idx}. {disc['type']} - {disc['severity']}")


def test_workpaper_generator():
    """Test workpaper generator with sample data."""
    print("\n" + "=" * 80)
    print("Testing Workpaper Generator")
    print("=" * 80)

    workpaper_data = {
        "task_category": "Accounts Receivable",
        "auditor": "John Smith, CPA",
        "procedures": [
            "Confirmed balances with top 10 customers representing 80% of AR",
            "Tested aging report accuracy by tracing to underlying invoices",
            "Reviewed allowance for doubtful accounts calculation",
            "Verified subsequent cash receipts for Q4 balances"
        ],
        "findings": [
            "No exceptions noted in confirmation responses (10/10 confirmed)",
            "Aging report agrees to GL balance within $500 (0.05%)",
            "Allowance methodology consistent with prior year"
        ],
        "conclusion": "Based on procedures performed, AR balance of $1,000,000 is fairly stated in all material respects.",
        "risk_rating": "Low",
        "sample_size": 10,
        "population_size": 150,
        "materiality_threshold": 50000.00
    }

    workpaper = workpaper_generator.invoke({"data": workpaper_data})
    print("\nGenerated Workpaper:")
    print(workpaper)

    # Validate the workpaper
    validation = workpaper_validator.invoke({"workpaper_text": workpaper})
    print("\n" + "=" * 80)
    print("Workpaper Validation Results:")
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Quality Score: {validation['quality_score']}/100")
    if validation['missing_elements']:
        print("  Missing Elements:")
        for element in validation['missing_elements']:
            print(f"    - {element}")
    if validation['recommendations']:
        print("  Recommendations:")
        for rec in validation['recommendations']:
            print(f"    - {rec}")


def test_workpaper_with_exceptions():
    """Test workpaper generator with exceptions."""
    print("\n" + "=" * 80)
    print("Testing Workpaper Generator (With Exceptions)")
    print("=" * 80)

    workpaper_data = {
        "task_category": "Inventory",
        "auditor": "Jane Doe, CPA",
        "procedures": [
            "Observed physical inventory count on 12/31/2025",
            "Tested inventory pricing to vendor invoices",
            "Reviewed inventory aging for obsolescence"
        ],
        "findings": [
            "Exception: Count variance of $25,000 (2.5% of total inventory)",
            "Exception: 3 items priced above most recent purchase cost",
            "Issue: $15,000 of inventory aged > 365 days with no reserve"
        ],
        "conclusion": "Material exceptions identified requiring management adjustment.",
        "risk_rating": "High",
        "sample_size": 50,
        "population_size": 500
    }

    workpaper = workpaper_generator.invoke({"data": workpaper_data})
    print("\nGenerated Workpaper (Abbreviated):")
    # Print only key sections
    lines = workpaper.split("\n")
    for i, line in enumerate(lines):
        if "EXCEPTIONS REQUIRING FOLLOW-UP" in line:
            print("\n".join(lines[i:i+10]))
            break

    validation = workpaper_validator.invoke({"workpaper_text": workpaper})
    print("\n" + "=" * 80)
    print("Validation Results:")
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Quality Score: {validation['quality_score']}/100")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NATIVE TOOLS TEST SUITE")
    print("=" * 80)

    test_financial_analyzer()
    test_workpaper_generator()
    test_workpaper_with_exceptions()

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)
