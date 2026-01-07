# LangGraph State Tests - Quick Start Guide

## File Location
```
/Users/jaewookim/Desktop/Personal Coding/AI Audit/backend/tests/unit/test_graph/test_state.py
```

## Running Tests

### 1. Run All Tests
```bash
cd /Users/jaewookim/Desktop/Personal\ Coding/AI\ Audit/backend
source venv/bin/activate
python -m pytest tests/unit/test_graph/test_state.py -v
```

### 2. Run Specific Test Class
```bash
# AuditState structure tests
python -m pytest tests/unit/test_graph/test_state.py::TestAuditStateStructure -v

# TaskState structure tests
python -m pytest tests/unit/test_graph/test_state.py::TestTaskStateStructure -v

# Message accumulation tests
python -m pytest tests/unit/test_graph/test_state.py::TestStateAddMessages -v

# Thread ID tests
python -m pytest tests/unit/test_graph/test_state.py::TestStateThreadIdUniqueness -v

# Serialization tests
python -m pytest tests/unit/test_graph/test_state.py::TestStateSerialization -v

# Edge cases
python -m pytest tests/unit/test_graph/test_state.py::TestEdgeCasesAndBoundaryConditions -v
```

### 3. Run Single Test
```bash
python -m pytest tests/unit/test_graph/test_state.py::TestAuditStateStructure::test_audit_state_field_types -v
```

### 4. Run with Coverage
```bash
python -m pytest tests/unit/test_graph/test_state.py --cov=src/graph --cov-report=html
```

### 5. Run with Detailed Output
```bash
python -m pytest tests/unit/test_graph/test_state.py -vv --tb=short
```

### 6. Run and Stop on First Failure
```bash
python -m pytest tests/unit/test_graph/test_state.py -x
```

## Quick Stats
- **Total Tests**: 53
- **Pass Rate**: 100%
- **Execution Time**: 0.02 seconds
- **Lines of Code**: 1,520

## Test Summary

| Test Class | Tests | Status |
|------------|-------|--------|
| AuditStateStructure | 10 | PASSED |
| TaskStateStructure | 11 | PASSED |
| StateAddMessages | 9 | PASSED |
| StateThreadIdUniqueness | 6 | PASSED |
| StateSerialization | 8 | PASSED |
| EdgeCasesAndBoundaryConditions | 9 | PASSED |
| **TOTAL** | **53** | **PASSED** |

## What's Being Tested

### 1. AuditState (Parent Graph State)
- All 9 required fields present and correct types
- Empty collections are valid
- Complex nested structures work
- Large values handled correctly

### 2. TaskState (Manager Subgraph State)
- All 12 required fields present and correct types
- Risk score boundaries (0-100 and beyond)
- Multiple status values supported
- Complex raw_data and vouching logs

### 3. Message Accumulation
- Add single and multiple messages
- Message order preservation
- Different message types (Human, AI, System, Tool)
- Large message batches (100+ messages)

### 4. Thread ID
- UUID format support
- Custom string formats
- Uniqueness across states
- Long string handling (1000+ chars)

### 5. Serialization
- JSON serialization/deserialization
- Roundtrip fidelity
- Special characters handled
- Unicode support (multiple languages)

### 6. Edge Cases
- Empty strings
- Very long strings
- Zero and negative values
- Extreme numeric values

## Common Patterns

### Check if all tests pass
```bash
python -m pytest tests/unit/test_graph/test_state.py -v | tail -1
# Expected output: ============================== 53 passed in 0.02s ==============================
```

### Get count of passing tests
```bash
python -m pytest tests/unit/test_graph/test_state.py -v 2>&1 | grep "PASSED" | wc -l
```

### List all tests without running
```bash
python -m pytest tests/unit/test_graph/test_state.py --collect-only -q
```

## Documentation
- **TEST_SUMMARY.md** - Comprehensive test documentation
- **test_state.py** - Source file with docstrings
- **__init__.py** - Package documentation

## Key Files
- Test file: `test_state.py` (1,520 lines)
- State definitions: `src/graph/state.py`
- Shared fixtures: `tests/conftest.py`

## Integration Notes
- Uses LangChain's `add_messages` reducer
- Tests both AuditState (parent) and TaskState (child)
- Thread_id links TaskState to LangGraph checkpoints
- Message accumulation supports conversation history

## Troubleshooting

### Import Error: No module named 'pytest'
```bash
source venv/bin/activate
```

### Test file not found
```bash
cd /Users/jaewookim/Desktop/Personal\ Coding/AI\ Audit/backend
```

### All tests pass but coverage shows 0%
This is expected for TypedDict definitions - they are static structures without executable code.

## Next Steps
1. Add tests for graph execution logic
2. Add integration tests
3. Add E2E tests for complete workflows
4. Set up CI/CD pipeline with these tests
