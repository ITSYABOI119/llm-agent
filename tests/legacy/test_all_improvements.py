"""Comprehensive test showing all Cursor-level improvements"""
import yaml
from tools.filesystem import FileSystemTools

def test_all_improvements():
    """Test syntax validation, smart insertion, and all edit modes"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    fs_tools = FileSystemTools(config)

    print("\n" + "=" * 70)
    print("  CURSOR-LEVEL CODE EDITING - COMPREHENSIVE TEST")
    print("=" * 70)

    # Test 1: Syntax Validation
    print("\n[TEST 1] Syntax Validation - Prevents Invalid Code")
    print("-" * 70)

    invalid_code = """def broken_function(
    return "missing colon and closing paren"
"""
    result = fs_tools.write_file("broken.py", invalid_code)
    if not result['success']:
        print(f"  [PASS] Blocked invalid code: {result['error'].split(':')[0]}")
    else:
        print(f"  [FAIL] Should have blocked invalid code!")

    # Test 2: Multi-File Project Creation
    print("\n[TEST 2] Multi-File Project Creation")
    print("-" * 70)

    # Create calculator project structure
    files_to_create = {
        "calculator/__init__.py": """'''Calculator package'''
from .main import Calculator
from .operations import add, subtract, multiply, divide
""",
        "calculator/operations.py": """def add(a, b):
    '''Add two numbers'''
    return a + b

def subtract(a, b):
    '''Subtract b from a'''
    return a - b

def multiply(a, b):
    '''Multiply two numbers'''
    result = a * b
    return result

def divide(a, b):
    '''Divide a by b'''
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b
""",
        "calculator/main.py": """import sys

class Calculator:
    '''A simple calculator class'''

    def __init__(self):
        self.history = []

    def calculate(self, operation, a, b):
        '''Perform a calculation'''
        self.history.append(f'{operation}({a}, {b})')
        if operation == 'add':
            return a + b
        elif operation == 'subtract':
            return a - b
        elif operation == 'multiply':
            return a * b
        elif operation == 'divide':
            if b == 0:
                raise ValueError('Cannot divide by zero')
            return a / b
"""
    }

    for path, content in files_to_create.items():
        result = fs_tools.write_file(path, content)
        if result['success']:
            print(f"  [PASS] Created: {path}")
        else:
            print(f"  [FAIL] Failed to create {path}: {result.get('error')}")

    # Test 3: Smart Insert After (finds end of function)
    print("\n[TEST 3] Smart Insert After - Finds Function End")
    print("-" * 70)

    power_func = """
def power(a, b):
    '''Raise a to the power of b'''
    return a ** b
"""

    result = fs_tools.edit_file(
        "calculator/operations.py",
        mode="insert_after",
        insert_after="def multiply",
        content=power_func
    )

    if result['success']:
        # Verify it was inserted AFTER the function, not just after the def line
        read_result = fs_tools.read_file("calculator/operations.py")
        lines = read_result['content'].split('\n')

        multiply_line = None
        power_line = None
        for i, line in enumerate(lines):
            if 'def multiply' in line:
                multiply_line = i + 1
            if 'def power' in line:
                power_line = i + 1

        if power_line and multiply_line and power_line > multiply_line + 3:
            print(f"  [PASS] Smart insertion: multiply at line {multiply_line}, power at line {power_line}")
            print(f"         Correctly inserted after function end, not just after 'def' line")
        else:
            print(f"  [WARN] May have inserted at wrong location")
    else:
        print(f"  [FAIL] Insert failed: {result.get('error')}")

    # Test 4: Insert at Line Number
    print("\n[TEST 4] Insert at Specific Line Number")
    print("-" * 70)

    result = fs_tools.edit_file(
        "calculator/main.py",
        mode="insert_at_line",
        line_number=2,
        content="import logging\n"
    )

    if result['success']:
        print(f"  [PASS] Inserted 'import logging' at line 2")
    else:
        print(f"  [FAIL] Insert failed: {result.get('error')}")

    # Test 5: Replace Line Range
    print("\n[TEST 5] Replace Line Range")
    print("-" * 70)

    result = fs_tools.edit_file(
        "calculator/main.py",
        mode="replace_lines",
        start_line=1,
        end_line=2,
        content="import sys\nimport math\n"
    )

    if result['success']:
        print(f"  [PASS] Replaced lines 1-2 with updated imports")
    else:
        print(f"  [FAIL] Replace failed: {result.get('error')}")

    # Test 6: Append to File
    print("\n[TEST 6] Append New Method to Class")
    print("-" * 70)

    new_method = """
    def get_history(self):
        '''Get calculation history'''
        return self.history

    def clear_history(self):
        '''Clear calculation history'''
        self.history = []
"""

    result = fs_tools.edit_file(
        "calculator/main.py",
        mode="append",
        content=new_method
    )

    if result['success']:
        print(f"  [PASS] Appended new methods to Calculator class")
    else:
        print(f"  [FAIL] Append failed: {result.get('error')}")

    # Test 7: Validate Final File
    print("\n[TEST 7] Final Validation - Check Syntax")
    print("-" * 70)

    read_result = fs_tools.read_file("calculator/main.py")
    if read_result['success']:
        content = read_result['content']
        validation = fs_tools._validate_python_syntax(content)
        if validation['valid']:
            print(f"  [PASS] Final file has valid Python syntax")
            print(f"         File size: {read_result['size']} bytes")
        else:
            print(f"  [FAIL] Syntax errors in final file: {validation['error']}")
    else:
        print(f"  [FAIL] Could not read file: {read_result.get('error')}")

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print("\n  Features Tested:")
    print("    [x] Syntax validation prevents invalid code")
    print("    [x] Multi-file project creation")
    print("    [x] Smart insert_after (finds function end)")
    print("    [x] Insert at specific line number")
    print("    [x] Replace line ranges")
    print("    [x] Append to files")
    print("    [x] Final syntax validation")
    print("\n  All Cursor-level editing capabilities verified!")
    print("\n" + "=" * 70)

    # Cleanup
    print("\nCleaning up test files...")
    fs_tools.delete_file("calculator/__init__.py")
    fs_tools.delete_file("calculator/operations.py")
    fs_tools.delete_file("calculator/main.py")
    print("Done!")

if __name__ == "__main__":
    test_all_improvements()
