# LLM Agent

Advanced hybrid multi-model LLM agent system with intelligent task routing, two-phase execution, and comprehensive tooling.

## Features

- **Hybrid Multi-Model Architecture** - Intelligent routing between reasoning and code generation models
- **Two-Phase Execution** - Planning (openthinker3-7b) → Execution (qwen2.5-coder:7b) workflow
- **RAG Integration** - Semantic code search with ChromaDB
- **Advanced File Editing** - 8 edit modes with syntax validation and linter integration
- **23 Tool Modules** - Comprehensive functionality for file ops, system info, network, data processing
- **Security Layer** - Sandboxing and input validation
- **98.8% Test Coverage** - Comprehensive test suite with 85+ test cases

## Quick Start

### Prerequisites

**Ollama server must be running:**
```bash
ollama serve
```

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd llm-agent

# Install dependencies
./venv/Scripts/pip install -r requirements.txt

# Run agent
./venv/Scripts/python agent.py
```

### Usage

```bash
# Interactive mode
./venv/Scripts/python agent.py

# With prompt
./venv/Scripts/python agent.py "Create a web app with HTML, CSS, and JS"

# Run tests
./venv/Scripts/python -m pytest tests/ --ignore=tests/legacy/
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Architecture, commands, troubleshooting
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Directory organization
- **[docs/COMPREHENSIVE_IMPROVEMENT_PLAN.md](docs/COMPREHENSIVE_IMPROVEMENT_PLAN.md)** - Roadmap for enhancements
- **[docs/IMPROVEMENTS_SUMMARY.md](docs/IMPROVEMENTS_SUMMARY.md)** - Feature changelog

## Architecture

```
User Request → Task Analysis → Model Selection → Execution
                    ↓
         ┌──────────┴──────────┐
    Single-Phase          Two-Phase
         ↓                     ↓
   One Model          Plan → Execute
```

**Models:**
- `qwen2.5-coder:7b` - Fast code generation
- `openthinker3-7b` - Reasoning and planning
- `deepseek-r1:14b` - Complex reasoning (optional)

## License

MIT
