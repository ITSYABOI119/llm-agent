"""Test syntax validation for Python files"""
import os
import sys
import yaml
from tools.filesystem import FileSystemTools

def test_syntax_validation():
    """Test that syntax validation prevents writing invalid Python code"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    fs_tools = FileSystemTools(config)

    print("Testing Python Syntax Validation\n")
    print("=" * 60)

    # Test 1: Valid Python code should succeed
    print("\n[PASS] Test 1: Valid Python code")
    valid_code = """def hello():
    print("Hello, world!")
    return True
"""
    result = fs_tools.write_file("test_valid.py", valid_code)
    assert result['success'], f"Valid code was rejected: {result.get('error')}"
    print(f"  SUCCESS: {result['message']}")

    # Test 2: Invalid syntax (missing colon) should fail
    print("\n[FAIL] Test 2: Invalid syntax - missing colon")
    invalid_code1 = """def hello()
    print("Hello")
"""
    result = fs_tools.write_file("test_invalid1.py", invalid_code1)
    assert not result['success'], "Invalid code was accepted!"
    print(f"  BLOCKED: {result['error']}")

    # Test 3: Invalid syntax (unmatched parenthesis) should fail
    print("\n[FAIL] Test 3: Invalid syntax - unmatched parenthesis")
    invalid_code2 = """def calculate(a, b:
    return a + b
"""
    result = fs_tools.write_file("test_invalid2.py", invalid_code2)
    assert not result['success'], "Invalid code was accepted!"
    print(f"  BLOCKED: {result['error']}")

    # Test 4: Invalid syntax (bad indentation) should fail
    print("\n[FAIL] Test 4: Invalid syntax - indentation error")
    invalid_code3 = """def hello():
print("Missing indent")
    return True
"""
    result = fs_tools.write_file("test_invalid3.py", invalid_code3)
    assert not result['success'], "Invalid code was accepted!"
    print(f"  BLOCKED: {result['error']}")

    # Test 5: Edit mode should also validate
    print("\n[PASS] Test 5: Edit mode validates syntax")
    # First create a valid file
    fs_tools.write_file("test_edit.py", "def foo():\n    pass\n")

    # Try to append invalid code
    result = fs_tools.edit_file("test_edit.py", mode="append", content="\ndef bar(\n    return 42\n")
    assert not result['success'], "Invalid edit was accepted!"
    print(f"  BLOCKED: {result['error']}")

    # Test 6: Non-Python files should not be validated
    print("\n[PASS] Test 6: Non-Python files bypass validation")
    result = fs_tools.write_file("test.txt", "This is not Python code (")
    assert result['success'], f"Text file validation failed: {result.get('error')}"
    print(f"  SUCCESS: {result['message']}")

    print("\n" + "=" * 60)
    print("\n[SUCCESS] All syntax validation tests passed!")

    # Cleanup
    print("\nCleaning up test files...")
    fs_tools.delete_file("test_valid.py")
    fs_tools.delete_file("test_edit.py")
    fs_tools.delete_file("test.txt")
    print("Done!")

if __name__ == "__main__":
    test_syntax_validation()
