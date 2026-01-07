# Native Audit Tools

This directory contains custom LangChain tools for the AI Audit Platform, implementing core audit functionality as native tools that can be used by LangGraph agents.

## Overview

The native tools provide essential audit capabilities:
- **Financial Analyzer**: Validates consistency between financial statements and trial balances
- **Workpaper Generator**: Creates standardized audit workpapers with proper formatting

## Files

### Core Tools

1. **`financial_analyzer.py`** (151 lines)
   - Validates financial statement consistency
   - Checks balance sheet equation (Assets = Liabilities + Equity)
   - Verifies trial balance (Debits = Credits)
   - Compares balance sheet totals with trial balance
   - Returns risk assessment and specific discrepancies

2. **`workpaper_generator.py`** (229 lines)
   - Generates formatted audit workpapers
   - Includes all required sections: procedures, findings, conclusion
   - Automatically identifies exceptions requiring follow-up
   - Provides sign-off section for review and approval
   - Bonus: `workpaper_validator` tool for quality control

3. **`__init__.py`** (4 lines)
   - Exports tools for easy import
   - Makes tools available as package

### Testing

4. **`test_tools.py`** (158 lines)
   - Comprehensive test suite for all tools
   - Tests balanced and imbalanced financial data
   - Tests workpapers with and without exceptions
   - Validates workpaper quality

## Installation

1. Create virtual environment (if not exists):
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Financial Analyzer

```python
from tools import financial_analyzer

# Prepare financial data
data = {
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

# Analyze consistency
result = financial_analyzer.invoke({"data": data})

print(f"Matched: {result['is_matched']}")
print(f"Risk Level: {result['risk_level']}")
print(f"Discrepancies: {len(result['discrepancies'])}")

for disc in result['discrepancies']:
    print(f"  - {disc['type']}: {disc['description']}")
    print(f"    Severity: {disc['severity']}")
```

**Output Structure**:
```python
{
    "is_matched": bool,          # True if no discrepancies
    "discrepancies": [           # List of identified issues
        {
            "type": str,         # Type of discrepancy
            "description": str,  # Human-readable description
            "severity": str,     # "Critical", "High", or "Medium"
            # ... additional fields specific to discrepancy type
        }
    ],
    "risk_level": str,           # "Low", "Medium", or "High"
    "recommendations": [str],    # Suggested actions
    "summary": {                 # Issue count by severity
        "total_discrepancies": int,
        "critical_issues": int,
        "high_issues": int,
        "medium_issues": int
    }
}
```

### Workpaper Generator

```python
from tools import workpaper_generator, workpaper_validator

# Prepare workpaper data
data = {
    "task_category": "Accounts Receivable",
    "auditor": "John Smith, CPA",
    "procedures": [
        "Confirmed balances with top 10 customers",
        "Tested aging report accuracy",
        "Reviewed allowance for doubtful accounts"
    ],
    "findings": [
        "No exceptions noted in confirmation responses",
        "Aging report agrees to GL balance within $500"
    ],
    "conclusion": "AR balance is fairly stated in all material respects.",
    "risk_rating": "Low",
    "sample_size": 10,
    "population_size": 150,
    "materiality_threshold": 50000.00
}

# Generate workpaper
workpaper = workpaper_generator.invoke({"data": data})
print(workpaper)

# Validate workpaper quality
validation = workpaper_validator.invoke({"workpaper_text": workpaper})
print(f"Valid: {validation['is_valid']}")
print(f"Quality Score: {validation['quality_score']}/100")
```

**Workpaper Structure**:
```
================================================================================
                        AUDIT WORKPAPER
================================================================================

Account/Area:           [Category]
Prepared by:            [Auditor Name]
Date:                   [Date]
Risk Rating:            [Low/Medium/High]

SCOPE OF WORK:
--------------------------------------------------------------------------------
Population Size:        [Number]
Sample Size:            [Number]
Coverage:               [Percentage]
Materiality Threshold:  [Amount]

AUDIT PROCEDURES PERFORMED:
--------------------------------------------------------------------------------
1. [Procedure 1]
2. [Procedure 2]
...

FINDINGS AND OBSERVATIONS:
--------------------------------------------------------------------------------
[!] 1. [Exception finding]
[ ] 2. [Normal finding]
...

EXCEPTIONS REQUIRING FOLLOW-UP: (if any)
--------------------------------------------------------------------------------
1. [Exception details]
...

CONCLUSION:
--------------------------------------------------------------------------------
[Overall conclusion]

================================================================================
REVIEW AND APPROVAL:

Prepared by:  [Name]          Date: [Date]     Signature: __________

Reviewed by:  __________      Date: __________  Signature: __________
================================================================================
```

## Running Tests

```bash
cd backend/src/tools
source ../../venv/bin/activate
python test_tools.py
```

Expected output:
```
================================================================================
NATIVE TOOLS TEST SUITE
================================================================================

Testing Financial Analyzer
- Test 1 - Balanced Financials: PASS
- Test 2 - Imbalanced Financials: PASS (discrepancies detected)

Testing Workpaper Generator
- Generated workpaper: PASS
- Workpaper validation: PASS (Quality Score: 95/100)

Testing Workpaper Generator (With Exceptions)
- Exception detection: PASS
- Workpaper validation: PASS

All tests completed!
================================================================================
```

## Integration with LangGraph

These tools are designed to be used with LangGraph agents:

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from tools import financial_analyzer, workpaper_generator

# Create agent with tools
llm = ChatOpenAI(model="gpt-5.2")
agent = create_react_agent(
    llm,
    tools=[financial_analyzer, workpaper_generator]
)

# Use agent
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Analyze this balance sheet and trial balance for consistency..."
    }]
})
```

## Future Enhancements

Potential improvements for production use:

1. **Financial Analyzer**:
   - Add pandas DataFrame support for complex financial data
   - Implement detailed variance analysis
   - Add support for multi-period comparisons
   - Include ratio analysis (liquidity, profitability, etc.)

2. **Workpaper Generator**:
   - Export to Excel format using `openpyxl`
   - Export to Word format using `python-docx`
   - Add digital signature support
   - Include embedded charts and graphs
   - Template customization per audit type

3. **New Tools** (from specification):
   - Risk Assessor: ML-based risk scoring
   - Sampling Tool: Statistical sampling methods
   - Reconciliation Tool: Automated account reconciliation
   - Exception Tracker: Track and manage audit exceptions

## Tool Design Principles

All tools follow these principles:

1. **Single Responsibility**: Each tool does one thing well
2. **Type Safety**: Full type hints for all parameters and returns
3. **Comprehensive Documentation**: Detailed docstrings with examples
4. **Error Handling**: Graceful handling of edge cases
5. **Testability**: Unit tests for all functionality
6. **LangChain Integration**: Proper @tool decorator usage

## Contributing

When adding new tools:

1. Create tool in separate file (e.g., `risk_assessor.py`)
2. Add @tool decorator from `langchain_core.tools`
3. Include comprehensive docstring with:
   - Description of what the tool does
   - Args section with type information
   - Returns section with structure
   - Example usage
4. Add unit tests in `test_tools.py`
5. Export from `__init__.py`
6. Update this README

## References

- LangChain Tools Documentation: https://python.langchain.com/docs/modules/tools/
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Project Specification: `../../docs/specification.md`
