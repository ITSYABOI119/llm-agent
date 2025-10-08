# Agent.py Test Prompts - Phases 1-4 Comprehensive Testing

## Test Categories

### 🟢 SIMPLE TASKS (Should use qwen only, 0s swap)

1. **Simple Function Addition**
   ```
   Create a function called add_numbers that takes two parameters and returns their sum
   ```

2. **Simple File Creation**
   ```
   Create a file called greetings.txt with the text "Hello, World!"
   ```

3. **Simple Variable Rename**
   ```
   In the file test.py, rename the variable 'old_name' to 'new_name'
   ```

4. **Simple Comment Addition**
   ```
   Add a docstring to the hello() function explaining what it does
   ```

5. **Simple Formatting**
   ```
   Format the code in utils.py to follow PEP 8 style guidelines
   ```

---

### 🟡 STANDARD TASKS (Should use qwen only, 0s swap)

6. **Build Component**
   ```
   Create a Python calculator class with methods for add, subtract, multiply, and divide operations
   ```

7. **Refactor Function**
   ```
   Refactor the process_data function to use list comprehension instead of for loops
   ```

8. **Add Error Handling**
   ```
   Add try-except blocks to all file operations in the FileReader class
   ```

9. **Write Tests**
   ```
   Write unit tests for the Calculator class using pytest
   ```

10. **Debug Error**
    ```
    Fix the IndexError in the get_item function - it's accessing list[10] when list only has 5 items
    ```

11. **Build API Endpoint**
    ```
    Create a Flask API endpoint that accepts POST requests and returns JSON responses
    ```

12. **Data Validation**
    ```
    Add input validation to the User class to ensure email addresses are valid format
    ```

---

### 🔴 COMPLEX TASKS (Should use openthinker → qwen, 2.5s swap)

13. **Design Application Architecture**
    ```
    Design a complete web scraper application with the following:
    - Multi-threaded scraping
    - Rate limiting
    - Error recovery
    - Data storage in SQLite
    - Progress tracking
    Create the full architecture with all necessary files
    ```

14. **Build Full Authentication System**
    ```
    Create a complete user authentication system with:
    - User registration with password hashing
    - Login with JWT tokens
    - Password reset functionality
    - Session management
    - Database models for users
    Include all necessary files and configurations
    ```

15. **Microservices Design**
    ```
    Design the architecture for a microservices-based e-commerce platform with:
    - User service
    - Product catalog service
    - Order processing service
    - Payment gateway integration
    - Message queue for inter-service communication
    Create the overall structure and key components
    ```

16. **Complex Algorithm**
    ```
    Design and implement a recommendation engine that:
    - Uses collaborative filtering
    - Handles sparse matrices efficiently
    - Provides real-time recommendations
    - Scales to millions of users
    Include data structures, algorithms, and optimization strategies
    ```

17. **Creative Landing Page**
    ```
    Create a beautiful, modern landing page for a tech startup with:
    - Hero section with animated gradient background
    - Feature cards with hover effects
    - Responsive design for mobile/tablet/desktop
    - Smooth scroll animations
    - Contact form with validation
    Include HTML, CSS, and JavaScript files
    ```

---

### 🔄 RETRY & RECOVERY TESTS (Tests Phase 3)

18. **Intentional Syntax Error (Should retry with enhanced prompt)**
    ```
    Create a Python function with this code:
    def broken_func()
        return "missing colon"
    ```

19. **File Operation on Non-existent File (Should retry)**
    ```
    Edit the file /path/to/nonexistent.py and add a new function
    ```

20. **Complex Fix (Should escalate if critical)**
    ```
    Fix this critical bug: The payment processing function is charging customers twice.
    The code is in payment_processor.py and involves database transactions.
    ```

---

### 📝 DIFF EDITOR TESTS (Tests Phase 4)

21. **Replace Specific Lines**
    ```
    In calculator.py, replace lines 10-15 with a new implementation that handles division by zero
    ```

22. **Insert Lines After Specific Line**
    ```
    In main.py, insert logging statements after line 25 to track function execution
    ```

23. **Delete Lines**
    ```
    In old_code.py, delete lines 50-75 which contain deprecated functions
    ```

24. **Replace Function by Name**
    ```
    In utils.py, completely replace the function called 'parse_date' with a new implementation using datetime.strptime
    ```

25. **Multiple Simultaneous Changes**
    ```
    In server.py, make these changes:
    - Update the handle_request function (lines 10-20)
    - Add error handling to send_response function (lines 45-50)
    - Fix the port configuration (line 5)
    ```

---

### 🔍 CONTEXT GATHERING TESTS (Tests Phase 1)

26. **Find and Modify**
    ```
    Find all functions that use the deprecated 'old_api' and update them to use 'new_api'
    ```

27. **Cross-file Analysis**
    ```
    Analyze all Python files in the project and create a dependency graph showing which modules import which
    ```

28. **Smart Search and Replace**
    ```
    Find all database queries that don't use parameterized statements and fix them to prevent SQL injection
    ```

---

### 📊 VERIFICATION TESTS (Tests Phase 1)

29. **Syntax Validation**
    ```
    Create a Python module with classes and functions, ensuring all syntax is valid
    ```

30. **Linting Check**
    ```
    Write a Python script and make sure it passes all PEP 8 style checks
    ```

---

### 🎯 INTEGRATION TESTS (Tests all phases together)

31. **End-to-End: Simple to Complex**
    ```
    First, create a simple hello.py file.
    Then, expand it into a full greeting system with:
    - Multiple greeting types (formal, casual, friendly)
    - Time-based greetings (morning, afternoon, evening)
    - Internationalization support
    - Configuration file
    ```

32. **Multi-step Workflow**
    ```
    1. Create a data_processor.py file with a basic function
    2. Add error handling to it
    3. Refactor it to use classes
    4. Add unit tests
    5. Create documentation
    ```

33. **Fix-and-Enhance**
    ```
    The file buggy_code.py has multiple issues:
    - Syntax errors
    - Logic bugs
    - Poor performance
    - No error handling
    Fix all issues and enhance it with better patterns
    ```

34. **Creative + Technical**
    ```
    Build a personal portfolio website with:
    - Modern, eye-catching design (creative)
    - Contact form that sends emails (technical)
    - Project showcase with filtering (technical)
    - Smooth animations (creative)
    - Responsive design (technical)
    ```

---

### 🚀 STRESS TESTS

35. **Large File Edit**
    ```
    Create a Python file with 50 functions, then modify functions 10, 20, 30, 40 simultaneously using diff edits
    ```

36. **Rapid Sequential Tasks**
    ```
    Create 10 simple Python files named file1.py through file10.py, each with a unique function
    ```

37. **Complex Refactor**
    ```
    Refactor the entire project structure:
    - Move all utility functions to utils/ directory
    - Create separate modules for different concerns
    - Update all imports
    - Ensure nothing breaks
    ```

---

### 🎨 CREATIVE TASKS (Tests openthinker routing)

38. **Design Beautiful UI**
    ```
    Design a stunning dashboard UI for a fitness app with:
    - Animated progress charts
    - Card-based layout
    - Dark/light mode toggle
    - Smooth transitions
    - Modern color scheme
    ```

39. **Create Game**
    ```
    Create a simple browser-based Snake game with:
    - Smooth animations
    - Score tracking
    - Increasing difficulty
    - Responsive controls
    - Game over screen
    ```

40. **Build Interactive Demo**
    ```
    Create an interactive demo showing how sorting algorithms work:
    - Visualize bubble sort, quick sort, merge sort
    - Animate the sorting process
    - Show comparisons and swaps
    - Allow speed control
    ```

---

## How to Test

### Sequential Testing (Recommended)
Test in order from simple to complex:
```bash
python agent.py "prompt 1"
python agent.py "prompt 6"
python agent.py "prompt 13"
```

### Category Testing
Test one category at a time:
```bash
# Test simple tasks (should be fast, 0 swaps)
python agent.py "prompt 1"
python agent.py "prompt 2"
python agent.py "prompt 3"

# Test complex tasks (should use openthinker, 2.5s swap)
python agent.py "prompt 13"
python agent.py "prompt 14"
```

### Stress Testing
Run multiple prompts in succession:
```bash
python agent.py "prompt 35"
python agent.py "prompt 36"
python agent.py "prompt 37"
```

---

## Expected Behaviors

### ✅ Simple Tasks (1-5)
- **Route:** qwen only
- **Swap time:** 0s
- **Speed:** Fast (5-15s total)
- **Log:** Should show "Task classified as: simple"

### ✅ Standard Tasks (6-12)
- **Route:** qwen only
- **Swap time:** 0s
- **Speed:** Moderate (15-30s total)
- **Log:** Should show "Task classified as: standard"

### ✅ Complex Tasks (13-17)
- **Route:** openthinker → qwen
- **Swap time:** ~2.5s
- **Speed:** Slower (30-60s total)
- **Log:** Should show "Task classified as: complex" + "Loading openthinker"

### ✅ Retry Tests (18-20)
- **First attempt:** Uses qwen
- **Retry:** Enhanced prompt with qwen (0s swap)
- **Escalation:** Only if critical (deepseek, 2.5s swap)
- **Log:** Should show "Attempt 1 failed" + "Retrying with enhanced prompt"

### ✅ Diff Editor Tests (21-25)
- **Method:** Uses diff-based edits
- **Reliability:** Should succeed on first try
- **Log:** Should show "Applying diff changes" + line numbers

---

## Success Metrics

After testing all 40 prompts, you should see:

1. **Routing Efficiency**
   - ~70-80% of tasks use qwen only (0 swaps)
   - ~20% use openthinker (2.5s swap, justified)
   - ~5% use deepseek (failures only)

2. **Speed Improvements**
   - Simple tasks: <15s average
   - Standard tasks: <30s average
   - Complex tasks: <60s average (including 2.5s swap)

3. **Reliability**
   - All file edits succeed
   - Syntax validation works
   - Retries succeed with enhanced prompts
   - Diff edits apply correctly

4. **Quality**
   - Generated code is syntactically correct
   - Complex tasks show better planning
   - Error handling is present
   - Code follows best practices

---

## Troubleshooting

### If simple tasks are swapping:
- Check task_classifier.py - may be too conservative
- Review model_router.py - routing logic

### If retries aren't working:
- Check progressive_retry.py - retry logic
- Verify error detection in verifier.py

### If diff edits fail:
- Check diff_editor.py - line number handling
- Verify file exists and is readable

### If everything is slow:
- Check model_manager.py - swap times
- Verify Ollama is running: `ollama list`
- Check if models are loaded: `ollama ps`

---

## Quick Start Commands

```bash
# Navigate to agent directory
cd llm-agent

# Test simple task (should be fast)
./venv/Scripts/python agent.py "Create a hello.py file with a print statement"

# Test standard task (should still be fast)
./venv/Scripts/python agent.py "Create a Calculator class with add and subtract methods"

# Test complex task (should use openthinker)
./venv/Scripts/python agent.py "Design a complete web scraper with threading and rate limiting"

# Test diff editor
./venv/Scripts/python agent.py "Replace function calculate in math_utils.py with a better implementation"

# Test retry
./venv/Scripts/python agent.py "Create a function with syntax: def broken(): missing body"
```

---

## Advanced Testing

### Monitor Swap Times
Watch the logs for swap time measurements:
```bash
tail -f logs/agent.log | grep -i "swap\|loading model"
```

### Track Task Classification
See how tasks are being classified:
```bash
tail -f logs/agent.log | grep -i "classified as"
```

### Monitor Retries
Watch for retry attempts:
```bash
tail -f logs/agent.log | grep -i "retry\|attempt"
```

---

## Final Validation

After running tests, verify:

1. ✅ Simple tasks completed in <15s
2. ✅ Most tasks used qwen only (check logs)
3. ✅ Complex tasks used openthinker (check logs)
4. ✅ File edits were successful and accurate
5. ✅ Retries worked when needed
6. ✅ No crashes or unhandled errors
7. ✅ Generated code is syntactically correct
8. ✅ Swap times measured accurately (~2.5s when swapping)

**If all checks pass: System is working perfectly! 🎉**
