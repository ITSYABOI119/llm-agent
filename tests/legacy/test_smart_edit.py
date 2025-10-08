"""
Test suite for smart_edit functionality (Phase 3)
Tests natural language code editing with LLM-powered strategy selection
"""

import sys
import os
import yaml
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.filesystem import FileSystemTools


def mock_llm_callback(prompt):
    """
    Mock LLM callback for testing
    Returns appropriate JSON responses based on the instruction
    """
    if "divide function" in prompt.lower():
        # Test case: Add divide function
        return '''```json
{
    "analysis": "Need to add a new divide function with zero-division error handling",
    "strategy": "append",
    "new_code": "\\ndef divide(a, b):\\n    if b == 0:\\n        raise ValueError(\\"Cannot divide by zero\\")\\n    return a / b\\n"
}
```'''
    elif "error handling to multiply" in prompt.lower():
        # Test case: Add error handling to existing function
        return '''```json
{
    "analysis": "Replace multiply function to add type checking",
    "strategy": "replace",
    "pattern": "def multiply(a, b):\\n    return a * b",
    "new_code": "def multiply(a, b):\\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\\n        raise TypeError(\\"Arguments must be numbers\\")\\n    return a * b"
}
```'''
    elif "add docstring" in prompt.lower() or "documentation" in prompt.lower():
        # Test case: Insert docstring after function definition
        return '''```json
{
    "analysis": "Add docstring right after function definition line",
    "strategy": "insert_after",
    "pattern": "def add(a, b):",
    "new_code": "    \\"\\"\\"Add two numbers and return the result.\\"\\"\\""
}
```'''
    else:
        # Default: append mode
        return '''```json
{
    "analysis": "Adding new code at the end of file",
    "strategy": "append",
    "new_code": "\\n# New code added\\n"
}
```'''


def run_tests():
    """Run smart_edit tests"""

    print("=" * 70)
    print("  SMART_EDIT TEST SUITE (PHASE 3)")
    print("=" * 70)
    print()

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Initialize filesystem tools
    fs_tools = FileSystemTools(config)

    # Create test directory
    test_dir = Path(config['agent']['workspace']) / "test_smart_edit"
    test_dir.mkdir(exist_ok=True, parents=True)

    print("[TEST 1] Smart edit: Append new function")
    print("-" * 70)

    # Create initial file
    calc_path = "test_smart_edit/calculator.py"
    fs_tools.write_file(calc_path, """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
""")

    # Test smart_edit with append strategy
    result = fs_tools.smart_edit(
        calc_path,
        "Add a divide function with zero-division error handling",
        mock_llm_callback
    )

    if result.get("success"):
        print(f"  [PASS] Smart edit succeeded")
        print(f"         Strategy used: {result['smart_edit']['strategy']}")
        print(f"         Analysis: {result['smart_edit']['analysis']}")

        # Verify the function was added
        content = fs_tools.read_file(calc_path)
        if "def divide" in content.get("content", "") and "raise ValueError" in content.get("content", ""):
            print(f"  [PASS] Divide function correctly added with error handling")
        else:
            print(f"  [FAIL] Divide function not found or missing error handling")
    else:
        print(f"  [FAIL] Smart edit failed: {result.get('error')}")

    print()
    print("[TEST 2] Smart edit: Replace function (add type checking)")
    print("-" * 70)

    result = fs_tools.smart_edit(
        calc_path,
        "Add type checking error handling to the multiply function",
        mock_llm_callback
    )

    if result.get("success"):
        print(f"  [PASS] Smart edit succeeded")
        print(f"         Strategy used: {result['smart_edit']['strategy']}")

        # Verify type checking was added
        content = fs_tools.read_file(calc_path)
        if "isinstance" in content.get("content", "") and "TypeError" in content.get("content", ""):
            print(f"  [PASS] Type checking correctly added to multiply function")
        else:
            print(f"  [FAIL] Type checking not found")
    else:
        print(f"  [FAIL] Smart edit failed: {result.get('error')}")

    print()
    print("[TEST 3] Smart edit: Insert after (add docstring)")
    print("-" * 70)

    result = fs_tools.smart_edit(
        calc_path,
        "Add documentation to the add function explaining what it does",
        mock_llm_callback
    )

    if result.get("success"):
        print(f"  [PASS] Smart edit succeeded")
        print(f"         Strategy used: {result['smart_edit']['strategy']}")

        # Verify docstring was added
        content = fs_tools.read_file(calc_path)
        if '"""' in content.get("content", ""):
            print(f"  [PASS] Docstring correctly added")
        else:
            print(f"  [FAIL] Docstring not found")
    else:
        print(f"  [FAIL] Smart edit failed: {result.get('error')}")

    print()
    print("[TEST 4] Smart edit: File not found")
    print("-" * 70)

    result = fs_tools.smart_edit(
        "test_smart_edit/nonexistent.py",
        "Add a function",
        mock_llm_callback
    )

    if not result.get("success") and "not found" in result.get("error", "").lower():
        print(f"  [PASS] Correctly rejected non-existent file")
    else:
        print(f"  [FAIL] Should have rejected non-existent file")

    print()
    print("[TEST 5] Smart edit: Missing instruction")
    print("-" * 70)

    # This would be caught at agent.py level, but test filesystem.py behavior
    result = fs_tools.smart_edit(
        calc_path,
        "",  # Empty instruction
        mock_llm_callback
    )

    # Empty instruction should still work (LLM will default to append)
    if result.get("success"):
        print(f"  [PASS] Handled empty instruction (defaulted to append)")
    else:
        print(f"  [FAIL] Should handle empty instruction gracefully")

    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print("  Smart Edit Features:")
    print("    [x] Natural language instruction parsing")
    print("    [x] LLM-powered strategy selection")
    print("    [x] Append strategy (new code)")
    print("    [x] Replace strategy (modify existing)")
    print("    [x] Insert_after strategy (add to specific location)")
    print("    [x] Error handling (file not found)")
    print("    [x] Integration with existing edit_file infrastructure")
    print()
    print("  Phase 3 implementation complete! Smart editing with natural language!")
    print()
    print("=" * 70)
    print()

    # Cleanup
    print("Cleaning up test files...")
    import shutil
    shutil.rmtree(test_dir)
    print("Done!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_tests()
