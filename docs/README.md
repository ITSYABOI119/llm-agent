# LLM Agent Documentation

This directory contains all documentation for the hybrid multi-model LLM agent system.

## 📚 Main Documentation

### **AGENTRULES_GUIDE.md**
Guide for configuring `.agentrules` files to customize Claude Code behavior in this repository.

### **IMPROVEMENTS_SUMMARY.md**
Comprehensive changelog tracking all improvements and features added to the agent system:
- Phases 1-5 file editing capabilities
- Hybrid multi-model architecture
- RAG integration
- Linter integration
- Atomic multi-file transactions

### **AGENT_TEST_PROMPTS.md**
Collection of test prompts for evaluating agent capabilities across different complexity levels.

### **OLLAMA_UPGRADE_GUIDE.md**
Guide for upgrading Ollama models and managing model configurations.

## 🗄️ Archive

The `archive/` subdirectory contains historical documentation superseded by current files:

- **LLM-Agent System-Architecture-Documentation.txt** - Original distributed Pi/PC architecture (now replaced by hybrid multi-model system)
- **CURSOR_LEVEL_TEST.md** - Cursor-specific benchmarking tests

## 📖 Additional Documentation Locations

### Root Directory
- **CLAUDE.md** - Primary context file for Claude Code instances
  - Architecture overview
  - Development commands
  - Model routing rules
  - Troubleshooting guide

### Configuration
- **config.yaml** - System configuration (multi-model settings, security, etc.)
- **requirements.txt** - Python dependencies

### Code Documentation
All tools include comprehensive docstrings:
- `tools/` - Individual tool implementations
- `safety/` - Security and validation modules
- `agent.py` - Main orchestration logic

## 🚀 Quick Start

1. **For new developers**: Start with `../CLAUDE.md`
2. **For testing**: See `../tests/README.md`
3. **For improvements history**: Read `IMPROVEMENTS_SUMMARY.md`
4. **For configuration**: Reference `AGENTRULES_GUIDE.md`

## 📝 Documentation Standards

When adding new documentation:
- Place user-facing guides in `docs/`
- Keep technical implementation details in code docstrings
- Archive outdated docs in `docs/archive/`
- Update CLAUDE.md for significant architectural changes
- Update IMPROVEMENTS_SUMMARY.md for new features
