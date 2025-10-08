# .agentrules - Project-Specific Agent Instructions

Similar to Cursor's `.cursorrules`, this file guides the agent's behavior for your specific project.

## 📍 Where to Put It

Place `.agentrules` in the **llm-agent directory** (where `agent.py` is located).

## 🎯 What It Does

The agent reads `.agentrules` at the start of every chat and includes it in the system prompt, giving it project-specific context and guidelines.

## ✍️ How to Write Rules

### Good Rules are:
- **Specific**: "Use insert_after with SHORT patterns like 'def multiply'"
- **Example-driven**: Show good vs bad examples
- **Actionable**: Tell the agent what to DO, not just what to avoid

### Bad Rules are:
- **Vague**: "Write good code"
- **Too broad**: "Follow best practices"
- **Negative-only**: Only saying what NOT to do

## 📝 Template

```markdown
# Agent Rules for [Your Project Name]

## Code Style
- Use snake_case for Python files
- Include docstrings for all functions
- Add type hints where appropriate

## File Operations
- Create files BEFORE editing them
- Use short single-line patterns for insert_after/insert_before
  - GOOD: "def multiply"
  - BAD: "def multiply(a, b):\n    return a * b"

## Project Structure
my_project/
  ├── src/          # Main source code
  ├── tests/        # Unit tests
  └── config/       # Configuration

## Common Patterns

### Adding a New Feature
1. Create module in src/
2. Write tests in tests/
3. Update imports in __init__.py

### Examples

Good:
TOOL: edit_file | PARAMS: {"path": "calc.py", "mode": "insert_after", "insert_after": "def add", "content": "..."}

Bad:
TOOL: edit_file | PARAMS: {"path": "calc.py", "mode": "insert_after", "insert_after": "def add(a, b):\n    return a + b", "content": "..."}
```

## 🎯 Common Use Cases

### 1. Fix Recurring Mistakes
If the agent keeps making the same mistake, add a rule:

```markdown
## Common Mistakes to Avoid
- ❌ DON'T use multi-line patterns for insert_after
- ✅ DO use short patterns: "def function_name"
```

### 2. Enforce Project Conventions
```markdown
## File Naming
- Controllers: `*_controller.py`
- Models: `*_model.py`
- Tests: `test_*.py`
```

### 3. Set Default Behaviors
```markdown
## Error Handling
- Always add try/except for file operations
- Include specific error messages
- Handle edge cases (division by zero, empty lists, etc.)
```

### 4. Define Project Structure
```markdown
## Directory Layout
src/
  ├── api/         # API endpoints
  ├── models/      # Data models
  ├── utils/       # Helper functions
  └── tests/       # Test files
```

## 🔄 When to Update

Update `.agentrules` when:
- Agent makes repeated mistakes
- You start a new feature/module
- Project structure changes
- New coding patterns emerge
- You want to enforce new standards

## 💡 Pro Tips

### 1. **Show Examples**
Instead of "Use proper patterns", show:
```markdown
GOOD: insert_after: "def multiply"
BAD:  insert_after: "def multiply(a, b):\n    return a * b"
```

### 2. **Be Specific About Modes**
```markdown
## When to Use Each Mode
- append: Add to end of file (new functions)
- insert_after: Add after specific function ("def multiply")
- insert_at_line: Precise line placement (imports at line 1)
- replace_lines: Refactor specific line ranges
```

### 3. **Include Project Context**
```markdown
## This Project Uses
- Python 3.9+
- No external dependencies (standard library only)
- pytest for testing
- Type hints required
```

### 4. **Link to Examples**
```markdown
## See test_agent.py for examples of:
- Multi-file project creation
- Smart insertion patterns
- Error handling patterns
```

## 🚀 Testing Your Rules

1. Add rules to `.agentrules`
2. Restart agent: `python agent.py`
3. Test with a prompt that should trigger the rules
4. Check logs to see if agent followed the rules
5. Refine rules based on results

## 📊 Example Real-World Rules

### For a Web API Project:
```markdown
# API Project Rules

## Endpoint Structure
- All endpoints in api/endpoints/
- Use FastAPI router pattern
- Include docstrings with request/response examples

## Error Handling
- Use HTTPException for all errors
- Include status codes: 400, 404, 500
- Return JSON error messages

## File Patterns
- Create: api/endpoints/{feature}_endpoints.py
- Then: api/models/{feature}_model.py
- Then: tests/test_{feature}.py
```

### For a Data Processing Project:
```markdown
# Data Pipeline Rules

## Module Organization
data/
  ├── extractors/    # Data extraction
  ├── transformers/  # Data transformation
  ├── loaders/       # Data loading
  └── validators/    # Data validation

## Function Naming
- Extractors: extract_from_{source}()
- Transformers: transform_{what}()
- Loaders: load_to_{destination}()

## Always Include
- Input validation
- Error logging
- Type hints
- Docstrings with examples
```

## 🎓 Advanced: Dynamic Rules

You can have different `.agentrules` for different parts of your project:

```bash
# Project root
.agentrules                 # Global rules

# Feature-specific (future enhancement)
src/api/.agentrules        # API-specific rules
src/data/.agentrules       # Data pipeline rules
```

(Note: Currently only root `.agentrules` is supported)

## ❓ FAQ

**Q: Do I need .agentrules?**
A: No, it's optional. The agent works without it, but rules help reduce mistakes.

**Q: How long can .agentrules be?**
A: Keep it under 2000 words. Focus on the most important patterns.

**Q: Can I use markdown formatting?**
A: Yes! The file is included in the prompt as-is.

**Q: Will this slow down the agent?**
A: Slightly (adds to context), but the accuracy improvement is worth it.

**Q: Can I version control .agentrules?**
A: Yes! Commit it to your repo so your team's agents follow the same rules.

## 📚 See Also

- [CURSOR_LEVEL_TEST.md](CURSOR_LEVEL_TEST.md) - Testing guidelines
- [AGENT_TEST_PROMPTS.md](AGENT_TEST_PROMPTS.md) - Test prompts
- [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) - Recent improvements
