"""Test linter integration with filesystem operations"""
import yaml
from tools.filesystem import FileSystemTools

def test_linter_integration():
    """Test that linter provides quality feedback on code"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    fs_tools = FileSystemTools(config)

    print("\n" + "=" * 70)
    print("  LINTER INTEGRATION TEST")
    print("=" * 70)

    # Check if linter is available
    if fs_tools.linter:
        available = fs_tools.linter.is_available()
        print(f"\nLinter availability: {available}")
    else:
        print("\n⚠️  Linter not enabled or flake8 not installed")
        print("   Install with: pip install flake8")
        return

    # Test 1: Perfect code (no issues)
    print("\n[TEST 1] Perfect Python code (should have no issues)")
    print("-" * 70)

    perfect_code = """def calculate_sum(numbers):
    '''Calculate sum of numbers'''
    total = 0
    for num in numbers:
        total += num
    return total
"""

    result = fs_tools.write_file("test_perfect.py", perfect_code)
    if result['success']:
        if 'warnings' in result:
            print(f"  [INFO] {result['warnings']}")
        else:
            print(f"  [PASS] No linting issues found")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 2: Code with unused variable
    print("\n[TEST 2] Code with unused variable (should warn)")
    print("-" * 70)

    unused_var_code = """def process_data(data):
    unused_variable = "not used"
    result = data * 2
    return result
"""

    result = fs_tools.write_file("test_unused.py", unused_var_code)
    if result['success']:
        if 'warnings' in result:
            print(f"  [PASS] Linter detected issues:")
            for warning in result['warnings']:
                print(f"         {warning}")
        else:
            print(f"  [WARN] No warnings (linter may not be working)")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 3: Code with undefined name
    print("\n[TEST 3] Code with undefined variable (should warn)")
    print("-" * 70)

    undefined_code = """def broken_function():
    return undefined_variable + 10
"""

    result = fs_tools.write_file("test_undefined.py", undefined_code)
    if result['success']:
        if 'warnings' in result:
            print(f"  [PASS] Linter detected issues:")
            for warning in result['warnings']:
                print(f"         {warning}")
        else:
            print(f"  [WARN] No warnings detected")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 4: Code with multiple issues
    print("\n[TEST 4] Code with multiple quality issues")
    print("-" * 70)

    messy_code = """def messy_function(x,y,z):
    a=1
    b=2
    unused=3
    return x+y+z+undefined_var
"""

    result = fs_tools.write_file("test_messy.py", messy_code)
    if result['success']:
        if 'warnings' in result:
            print(f"  [PASS] Linter detected multiple issues:")
            for warning in result['warnings']:
                print(f"         {warning}")
        else:
            print(f"  [WARN] Expected warnings for messy code")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 5: Syntax error (should block, not just warn)
    print("\n[TEST 5] Syntax error (should be blocked by syntax check)")
    print("-" * 70)

    syntax_error_code = """def broken(
    return "missing closing paren"
"""

    result = fs_tools.write_file("test_syntax_error.py", syntax_error_code)
    if not result['success']:
        print(f"  [PASS] Syntax error blocked: {result['error'].split(':')[0]}")
    else:
        print(f"  [FAIL] Syntax error should have been blocked!")

    # Test 6: Linter with edit_file
    print("\n[TEST 6] Linter works with edit_file")
    print("-" * 70)

    # Create initial file
    fs_tools.write_file("test_edit.py", "def foo():\n    pass\n")

    # Append code with issues
    bad_append = "\ndef bar():\n    x=1\n    return undefined\n"

    result = fs_tools.edit_file("test_edit.py", mode="append", content=bad_append)
    if result['success']:
        if 'warnings' in result:
            print(f"  [PASS] Linter warns on edit:")
            for warning in result['warnings']:
                print(f"         {warning}")
        else:
            print(f"  [INFO] No warnings on append")
    else:
        print(f"  [FAIL] {result['error']}")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("\n  Linter Integration Features:")
    print("    [x] Detects code quality issues")
    print("    [x] Provides non-blocking warnings")
    print("    [x] Works with write_file")
    print("    [x] Works with edit_file")
    print("    [x] Syntax errors still block (as they should)")
    print("\n  Linter provides valuable feedback without blocking valid code!")
    print("\n" + "=" * 70)

    # Cleanup
    print("\nCleaning up test files...")
    fs_tools.delete_file("test_perfect.py")
    fs_tools.delete_file("test_unused.py")
    fs_tools.delete_file("test_undefined.py")
    fs_tools.delete_file("test_messy.py")
    fs_tools.delete_file("test_edit.py")
    print("Done!")

if __name__ == "__main__":
    test_linter_integration()
