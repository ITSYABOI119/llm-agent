# Agent Test Prompts - Cursor-Level Capabilities

Test these prompts with your agent to verify all improvements are working correctly.

---

## Test 1: Multi-File Project with Smart Insertion

**Prompt:**
```
Create a Python math utilities project with these files:

1. mathutils/operations.py - with functions: add, subtract, multiply, divide
2. mathutils/advanced.py - with functions: power, sqrt, factorial
3. mathutils/__init__.py - import all functions
4. mathutils/main.py - with a Calculator class that uses these functions

After creating them, add a new function 'modulo(a, b)' after the divide function in operations.py
```

**Expected Behavior:**
- ✓ All 4 files created with valid Python code
- ✓ modulo function inserted AFTER divide function ends (not just after the def line)
- ✓ All files pass syntax validation
- ✓ RAG indexes all files

---

## Test 2: Syntax Validation Catches Errors

**Prompt:**
```
Create a file called broken.py with this code:
def test_function(
    return "missing closing paren"
```

**Expected Behavior:**
- ✗ Agent should REFUSE to create the file
- ✓ Error message should mention "Python syntax error"
- ✓ Should show line and column number of the error

---

## Test 3: Complex Multi-Step Editing

**Prompt:**
```
Create a file game.py with a simple Player class that has name and score attributes.

Then:
1. Add an import for 'typing' at line 1
2. Add a method called 'increase_score' to the Player class
3. Add a method called 'decrease_score' after increase_score
4. Replace the constructor to include a 'level' parameter
```

**Expected Behavior:**
- ✓ File created with valid syntax
- ✓ Import added at line 1
- ✓ Methods added to class
- ✓ Methods added in correct order
- ✓ All edits validated before writing

---

## Test 4: Insert After Function (Smart Mode)

**Prompt:**
```
Create a file utils.py with these functions:

def greet(name):
    message = f"Hello, {name}"
    print(message)
    return message

def farewell(name):
    return f"Goodbye, {name}"

Then add a new function 'welcome(name)' after the greet function.
```

**Expected Behavior:**
- ✓ welcome function inserted between greet and farewell
- ✓ NOT inserted in the middle of greet function
- ✓ Proper spacing maintained

---

## Test 5: Line Range Replacement

**Prompt:**
```
Create a file config.py with:
import os
import sys

def get_config():
    return {}

Then replace lines 1-2 with:
import os
import sys
import json
from pathlib import Path
```

**Expected Behavior:**
- ✓ Lines 1-2 replaced with new imports
- ✓ get_config function preserved
- ✓ Final file has valid syntax

---

## Test 6: Auto-Correction Test

**Prompt:**
```
Create data.py with a process() function.
Then insert a new function validate() after the process function.
```

**Expected Behavior:**
- ✓ Both functions created correctly
- ✓ If LLM uses wrong parameter, auto-correction fixes it
- ✓ Check logs for "auto-correcting" warning (if it happened)

---

## Test 7: Nested Functions (Advanced)

**Prompt:**
```
Create nested.py with:

def outer():
    def inner():
        return "nested"
    return inner()

def another():
    pass

Then add a new function 'middle()' after the outer function.
```

**Expected Behavior:**
- ✓ middle() inserted between outer and another
- ✓ Smart insertion handles nested function correctly
- ✓ outer function's inner function not affected

---

## Test 8: Class-Based Smart Insertion

**Prompt:**
```
Create models.py with:

class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hi, {self.name}"

class Product:
    pass

Then add a new class 'Admin' after the User class.
```

**Expected Behavior:**
- ✓ Admin class inserted between User and Product
- ✓ Smart insertion finds end of User class
- ✓ All class definitions remain valid

---

## Success Criteria

For the agent to be considered "Cursor-level":

- [ ] All files created have valid Python syntax
- [ ] Invalid syntax is rejected with clear error messages
- [ ] Smart insertion finds end of functions/classes
- [ ] insert_after works correctly for nested structures
- [ ] Line-number operations are precise
- [ ] Multi-step editing works without breaking code
- [ ] RAG system indexes all created/modified files
- [ ] Auto-correction handles LLM parameter mistakes

---

## How to Use

1. Start your agent: `python agent.py`
2. Copy one test prompt at a time
3. Paste into the agent
4. Verify the expected behavior
5. Check `logs/agent.log` for details
6. Examine `agent_workspace/` to see created files

---

## Debugging Tips

If something fails:

1. **Check logs**: `logs/agent.log` shows syntax validation results and auto-corrections
2. **Check workspace**: `agent_workspace/` contains all created files
3. **Verify syntax**: Run `python -m py_compile <file>` on any created Python file
4. **Check RAG**: Agent should mention "RAG indexed X chunks" after file operations

---

## Expected Log Messages (Success)

```
Smart insert_after: Found 'def multiply' at line 1, inserting at line 5
LLM used 'search' instead of 'insert_after' - auto-correcting
Wrote file: mathutils/operations.py (245 bytes)
RAG indexed: 4 files, 15 chunks total
```

## Expected Log Messages (Validation Blocking)

```
Error: Python syntax error: Line 1, Column 12: expected ':'
  def broken_function(
             ^
```

---

## Quick Verification

Run this single comprehensive test:

```
Create a Python project with 3 files: calculator.py with add/subtract functions,
utils.py with a helper function, and main.py that imports from both.

Then add a multiply function after the add function in calculator.py,
and add 'import sys' at line 1 of main.py.
```

This tests: multi-file creation, smart insertion, line-number insertion, syntax validation, and RAG indexing.
