# LLM Agent Project Structure

Clean, organized directory structure for the hybrid multi-model LLM agent system.

## 📁 Root Directory

```
llm-agent/
├── agent.py                    # Main agent orchestration
├── config.yaml                 # System configuration
├── requirements.txt            # Python dependencies
├── CLAUDE.md                   # Primary documentation for Claude Code
├── PROJECT_STRUCTURE.md        # This file
│
├── scripts/                    # Helper scripts
│   ├── run_agent.sh            # Linux/Mac agent launcher
│   ├── run_agent.bat           # Windows agent launcher
│   ├── run_agent.ps1           # PowerShell agent launcher
│   ├── setup_files.sh          # Setup script
│   ├── cleanup_test.bat        # Test cleanup (Windows)
│   └── cleanup_test.sh         # Test cleanup (Linux/Mac)
│
├── tools/                      # Agent tools (23 modules)
│   ├── filesystem.py           # File operations with Phases 1-5 editing
│   ├── task_analyzer.py        # Multi-model task analysis
│   ├── task_classifier.py      # Smart task routing
│   ├── model_router.py         # Intelligent model routing
│   ├── model_manager.py        # Smart model management
│   ├── two_phase_executor.py   # Plan → execute workflow
│   ├── linter.py               # Code quality integration
│   ├── transaction_manager.py  # Atomic multi-file operations
│   ├── rag_indexer.py          # Semantic code search
│   ├── diff_editor.py          # Diff-based editing
│   ├── context_gatherer.py     # Context collection
│   ├── verifier.py             # Action verification
│   ├── token_counter.py        # Token counting and compression
│   ├── structured_planner.py   # Structured task planning
│   ├── progressive_retry.py    # Progressive retry system
│   ├── commands.py             # Shell command execution
│   ├── system.py               # System information
│   ├── search.py               # File finding and content search
│   ├── network.py              # Network operations
│   ├── data.py                 # JSON/CSV handling
│   ├── process.py              # Process management
│   ├── memory.py               # Long-term memory
│   ├── session_history.py      # Conversation history
│   └── logging_tools.py        # Structured logging
│
├── safety/                     # Security modules
│   ├── sandbox.py              # Path validation
│   └── validators.py           # Input sanitization
│
├── tests/                      # Test suite
│   ├── README.md               # Test documentation
│   ├── test_core_agent.py      # Core functionality (52 tests)
│   ├── test_logging.py         # Logging system (33 tests)
│   ├── test_rag.py             # RAG integration tests
│   ├── test_multimodel.py      # Multi-model routing tests
│   ├── test_complex_only.py    # Two-phase execution tests
│   ├── legacy/                 # Historical tests (25+ files)
│   └── reports/                # Test output files
│
├── docs/                       # Documentation
│   ├── README.md               # Documentation index
│   ├── IMPROVEMENTS_SUMMARY.md # Changelog and feature history
│   ├── AGENTRULES_GUIDE.md     # .agentrules configuration guide
│   ├── AGENT_TEST_PROMPTS.md   # Test prompt collection
│   ├── TEST_PROMPTS.md         # Additional test prompts
│   ├── OLLAMA_UPGRADE_GUIDE.md # Model upgrade guide
│   ├── OLLAMA_SERVE_REQUIREMENT.md # Ollama setup guide
│   └── archive/                # Outdated documentation
│       ├── LLM-Agent System-Architecture-Documentation.txt
│       ├── CURSOR_LEVEL_TEST.md
│       ├── PHASE_PLAN.md
│       ├── FIXES_APPLIED.md
│       ├── FULL_40_PROMPT_ANALYSIS.md
│       ├── chat_v2.py          # Legacy experimental code
│       └── log_config.py       # Legacy logging config
│
├── logs/                       # Runtime logs and data
│   ├── agent.log               # Text logs
│   ├── agent_structured.json   # Structured logs with metrics
│   ├── agent_memory.json       # Long-term memory storage
│   └── session_history.json    # Recent conversation history
│
└── venv/                       # Python virtual environment
```

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `agent.py` | Main orchestration with multi-model routing |
| `config.yaml` | Multi-model settings, security, linter config |
| `CLAUDE.md` | Primary documentation for Claude Code instances |
| `requirements.txt` | Python dependencies (requests, yaml, psutil, chromadb, etc.) |

## 🧰 Tool Categories

### **Multi-Model System** (New)
- `task_analyzer.py` - Analyzes complexity, intent, creativity
- `model_router.py` - Routes to optimal model
- `two_phase_executor.py` - Plan (reasoning) → Execute (code) workflow

### **File Operations**
- `filesystem.py` - 8 edit modes, Phases 1-5 capabilities
- `linter.py` - flake8 integration
- `transaction_manager.py` - Atomic multi-file transactions with rollback

### **AI Enhancement**
- `rag_indexer.py` - ChromaDB semantic search

### **Standard Tools**
- `commands.py`, `system.py`, `search.py`, `network.py`, `data.py`, `process.py`

### **Memory & Logging**
- `memory.py`, `session_history.py`, `logging_tools.py`

## 🧪 Testing

**Active tests** (5 files, 98.8% pass rate):
- Core agent functionality
- Logging system
- RAG integration
- Multi-model routing
- Two-phase execution

**Legacy tests** (25+ files) archived in `tests/legacy/` for reference.
**Test reports** stored in `tests/reports/` for historical tracking.

## 📚 Documentation

**User-facing docs** in `docs/`:
- Feature guides, test prompts, configuration reference
- OLLAMA_SERVE_REQUIREMENT.md - Critical setup information

**Technical docs**:
- `CLAUDE.md` - Architecture, commands, troubleshooting
- Code docstrings - Implementation details

**Archived docs** in `docs/archive/`:
- Historical planning documents (PHASE_PLAN.md, FIXES_APPLIED.md)
- Legacy code files (chat_v2.py, log_config.py)
- Analysis documents (FULL_40_PROMPT_ANALYSIS.md)

## 🔒 Security

**Sandboxing**: All file operations restricted to workspace
**Validation**: Input sanitization, command whitelisting
**Path restrictions**: No traversal outside allowed directories

## 🚀 Quick Start

```bash
# 1. Start Ollama server (required!)
ollama serve

# 2. Install dependencies
./venv/Scripts/pip install -r requirements.txt

# 3. Run agent (Linux/Mac)
./scripts/run_agent.sh

# 3. Run agent (Windows)
scripts\run_agent.bat

# 4. Run tests
./venv/Scripts/python -m pytest tests/ --ignore=tests/legacy/

# 5. Test multi-model system
./venv/Scripts/python tests/test_multimodel.py
```

## 📊 Statistics

- **Total Python modules**: 23 (tools) + 2 (safety) + 1 (agent) = 26
- **Active tests**: 5 test suites, 85+ test cases
- **Test coverage**: 98.8%
- **Documentation files**: 7 active + 7 archived
- **Helper scripts**: 6 platform-specific launchers
- **Lines of code**: ~6000+ (estimated)

## 🧹 Cleanup Completed (2025-01-08)

✅ Removed all `__pycache__/` directories
✅ Created `scripts/` directory for helper scripts
✅ Moved 12 legacy test files to `tests/legacy/`
✅ Created `tests/reports/` for test output files
✅ Moved 5 historical docs to `docs/archive/`
✅ Archived 2 legacy code files (chat_v2.py, log_config.py)
✅ Organized all documentation into `docs/`
✅ Updated PROJECT_STRUCTURE.md and CLAUDE.md
✅ **Root now contains only 4 essential files** (agent.py, config.yaml, requirements.txt, CLAUDE.md)
✅ Clean, professional directory structure
