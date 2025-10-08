# Cursor-Level Code Editing Test Suite

Test these commands with your agent to verify it has Cursor-level capabilities:

## Basic Multi-File Project Creation

```
Create a Python calculator project with these files:
- calculator/main.py with a Calculator class
- calculator/operations.py with add, subtract, multiply, divide functions
- calculator/__init__.py
- tests/test_calculator.py with unit tests
- README.md with project description
```

## Advanced Code Editing Tests

### Test 1: Insert After Pattern
```
In calculator/operations.py, insert a new function 'power(a, b)' after the multiply function
```

### Test 2: Insert Before Pattern
```
In calculator/main.py, add a docstring before the Calculator class definition
```

### Test 3: Replace Lines
```
In calculator/operations.py, replace lines 1-3 with updated import statements: import math and import sys
```

### Test 4: Insert at Specific Line
```
In calculator/main.py, insert 'import logging' at line 2
```

### Test 5: Find and Replace
```
In all files, replace 'Calculator' with 'AdvancedCalculator'
```

### Test 6: Add Method to Class
```
In calculator/main.py, add a new method 'get_history()' after the existing methods in the Calculator class
```

### Test 7: Multi-Line Code Addition
```
In tests/test_calculator.py, add a new test function:
def test_power():
    assert power(2, 3) == 8
    assert power(5, 2) == 25
```

## Expected Capabilities

The agent should be able to:
- ✓ Create multiple files with complete code
- ✓ Edit files without overwriting them
- ✓ Insert code at precise locations
- ✓ Work with line numbers accurately
- ✓ Handle multi-line code blocks
- ✓ Maintain proper indentation
- ✓ Use RAG to understand existing code structure
- ✓ Remember files created in the session

## What Makes It Cursor-Level

1. **Precise Editing**: Can insert/modify at exact line numbers or patterns
2. **Context Aware**: Uses RAG to understand existing code before editing
3. **Multi-File**: Handles complex projects with multiple related files
4. **Safe Operations**: Never overwrites without confirmation
5. **Session Memory**: Tracks all file operations in the session
6. **Code Intelligence**: Understands code structure (classes, functions, imports)
7. **Syntax Validation**: Validates Python code before writing to prevent syntax errors
8. **Smart Insertion**: Finds end of functions/classes, not just first matching line
