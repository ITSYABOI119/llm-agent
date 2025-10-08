# LLM Agent Test Suite

This directory contains all test files for the LLM agent system.

## Active Test Files

### Core Tests
- **test_core_agent.py** - Main agent functionality tests (52 tests)
  - File operations, command execution, system tools
  - Security features (sandboxing, validation)
  - Tool execution and parsing

- **test_logging.py** - Logging system tests (33 tests)
  - Log manager, analyzer, query functionality
  - Structured logging and metrics

### Advanced Features
- **test_rag.py** - RAG (Retrieval-Augmented Generation) tests
  - ChromaDB indexing and semantic search
  - Embedding generation and codebase queries

- **test_multimodel.py** - Hybrid multi-model system tests
  - Task analysis and model routing
  - Single-phase vs two-phase execution
  - Integration of reasoning and execution models

- **test_complex_only.py** - Two-phase execution tests
  - Planning (OpenThinker3-7B) → Execution (qwen2.5-coder) workflow
  - Creative multi-file generation

## Running Tests

```bash
# Run all active tests
cd /c/Users/jluca/Documents/newfolder/llm-agent
./venv/Scripts/python -m pytest tests/ --ignore=tests/legacy/

# Run specific test suite
./venv/Scripts/python tests/test_core_agent.py
./venv/Scripts/python tests/test_multimodel.py
./venv/Scripts/python tests/test_complex_only.py

# Run with verbose output
./venv/Scripts/python -m pytest tests/ -v
```

## Legacy Tests (tests/legacy/)

Historical tests for specific features, kept for reference:
- File editing mode tests (append, prepend, replace, insert, etc.)
- Auto-correction and linter integration tests
- Smart edit and diff edit tests
- Syntax validation tests
- Individual reasoning model tests

These are superseded by the active test suite but preserved for historical reference and specific debugging scenarios.

## Test Coverage

Current coverage: **98.8%** (84/85 tests passing)
- Core agent: 100%
- Logging system: 97%
- Security features: 100%
- Multi-model routing: Successfully tested

## Adding New Tests

When adding new test files:
1. Place in `tests/` root directory
2. Name with `test_` prefix (e.g., `test_new_feature.py`)
3. Update this README with description
4. Ensure tests pass before committing
