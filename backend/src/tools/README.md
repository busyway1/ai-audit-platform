# Audit Tools

This directory contains LangChain tools for the AI Audit Platform, including both native audit tools and MCP (Model Context Protocol) tool wrappers that enable LangGraph agents to interact with MCP servers.

## Overview

The tools provide essential audit capabilities:

### Native Tools
- **Financial Analyzer**: Validates consistency between financial statements and trial balances
- **Workpaper Generator**: Creates standardized audit workpapers with proper formatting

### MCP Tools (via mcp_tools.py)
- **RAG Tools**: Search K-IFRS/K-GAAS standards via mcp-rag server
- **Excel Tools**: Parse and analyze Excel workpapers via mcp-excel-processor server
- **Web Research Tools**: Search company news and industry insights via mcp-web-research server

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

3. **`mcp_tools.py`** (NEW - MCP Tool Wrappers)
   - **search_standards**: Hybrid search for K-IFRS/K-GAAS standards
   - **get_paragraph_by_id**: Direct paragraph lookup for multi-hop retrieval
   - **read_excel_structure**: Analyze Excel file structure
   - **analyze_workpaper_structure**: Deep audit analysis of workpapers
   - **search_company_news**: Search company-related news and risk indicators
   - **get_industry_insights**: Get industry-specific audit guidance

4. **`__init__.py`**
   - Exports all tools for easy import
   - Provides tool collections: RAG_TOOLS, EXCEL_TOOLS, WEB_RESEARCH_TOOLS, ALL_MCP_TOOLS

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

### Native Tools with create_react_agent

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from tools import financial_analyzer, workpaper_generator

# Create agent with tools
llm = ChatOpenAI(model="gpt-4o-mini")
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

### MCP Tools with bind_tools

The MCP tools are designed to be bound to LLM instances for tool-calling:

```python
from langchain_openai import ChatOpenAI
from tools import RAG_TOOLS, EXCEL_TOOLS, WEB_RESEARCH_TOOLS

# Bind RAG tools to LLM for standard retrieval
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_rag = llm.bind_tools(RAG_TOOLS)

# Invoke with tool-calling
response = await llm_with_rag.ainvoke([
    SystemMessage(content="Search for relevant K-IFRS standards"),
    HumanMessage(content="Find standards related to revenue recognition")
])

# Process tool calls
if response.tool_calls:
    for tool_call in response.tool_calls:
        # Execute the tool
        result = await RAG_TOOLS[0].ainvoke(tool_call["args"])
```

### Agent Classes with Built-in Tool Binding

The staff agents automatically bind appropriate MCP tools:

```python
from src.agents.staff_agents import StandardRetrieverAgent, ExcelParserAgent
from src.agents.partner_agent import PartnerAgent

# Agents auto-bind tools on initialization
standard_agent = StandardRetrieverAgent(bind_tools=True)  # RAG_TOOLS
excel_agent = ExcelParserAgent(bind_tools=True)           # EXCEL_TOOLS
partner_agent = PartnerAgent(bind_tools=True)             # WEB_RESEARCH_TOOLS

# Run agent with tool-calling
result = await standard_agent.run(state)
# Agent uses search_standards tool via LLM tool-calling
```

### Tool Bindings Reference

| Agent | Tools Bound | MCP Server |
|-------|-------------|------------|
| StandardRetrieverAgent | search_standards, get_paragraph_by_id | mcp-rag (8001) |
| ExcelParserAgent | read_excel_structure, analyze_workpaper_structure | mcp-excel-processor (8003) |
| PartnerAgent | search_company_news, get_industry_insights | mcp-web-research (8002) |

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
