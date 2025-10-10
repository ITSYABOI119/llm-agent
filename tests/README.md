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

### Phase 1: Streaming Execution (Enhancement Plan)
- **test_streaming.py** - Streaming & progress feedback tests
  - Event bus publish/subscribe system
  - Progress indicator updates
  - Real-time execution visibility
  - Streaming executor integration

### Phase 2: Execution History & Error Recovery (Enhancement Plan)
- **test_execution_history.py** - Execution history database tests
  - Database initialization and schema
  - Execution logging (single-phase and two-phase)
  - Query operations (recent, stats, routing)
  - Misroute detection
  - Data persistence

- **test_error_recovery.py** - Error recovery system tests
  - Error classification (9 error types)
  - Recovery strategies (syntax, path, timeout, rate limit, JSON, params)
  - Recovery executor orchestration
  - Recovery statistics and success rates

- **test_adaptive_analyzer.py** - Adaptive learning tests
  - Routing performance analysis
  - Pattern identification (best/worst performing modes)
  - Model recommendations based on history
  - Threshold adjustment suggestions
  - Error insights and trends

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

### Overall Coverage
Current coverage: **98.8%** (84/85 tests passing)
- Core agent: 100%
- Logging system: 97%
- Security features: 100%
- Multi-model routing: Successfully tested

### Phase 1-2 Test Coverage (New)
**Phase 1: Streaming Execution**
- Event bus: 6 tests
- Progress indicator: 6 tests
- Streaming integration: 2 tests
- Configuration: 2 tests
- **Total: ~16 tests**

**Phase 2: Execution History & Error Recovery**
- Execution history database: 11 tests
- Error classification: 8 tests
- Recovery strategies: 18 tests
- Adaptive analysis: 15 tests
- **Total: ~52 tests**

**Combined Phase 1-2: ~68 new tests**

**Estimated Total Test Suite: 150+ tests**

## Adding New Tests

When adding new test files:
1. Place in `tests/` root directory
2. Name with `test_` prefix (e.g., `test_new_feature.py`)
3. Update this README with description
4. Ensure tests pass before committing
