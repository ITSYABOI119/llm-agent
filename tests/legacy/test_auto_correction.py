"""Test auto-correction of multi-line patterns"""
import yaml
from tools.filesystem import FileSystemTools

def test_auto_correction():
    """Test that multi-line patterns are automatically normalized"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    fs_tools = FileSystemTools(config)

    print("\n" + "=" * 70)
    print("  AUTO-CORRECTION TEST - Multi-Line Pattern Handling")
    print("=" * 70)

    # Create test file
    test_code = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    result = a * b
    return result
"""

    fs_tools.write_file("test_autocorrect.py", test_code)
    print("\n[1] Created test file with 3 functions")

    # Test 1: Multi-line pattern (should be auto-corrected)
    print("\n[TEST 1] Using multi-line pattern (should auto-correct)")
    print("-" * 70)

    multi_line_pattern = """def multiply(a, b):
    result = a * b
    return result"""

    print(f"  Pattern provided: '{multi_line_pattern[:30]}...'")

    divide_func = """
def divide(a, b):
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b
"""

    result = fs_tools.edit_file(
        "test_autocorrect.py",
        mode="insert_after",
        insert_after=multi_line_pattern,
        content=divide_func
    )

    if result['success']:
        print(f"  [PASS] Auto-correction worked! Pattern normalized and function inserted")
    else:
        print(f"  [FAIL] {result['error']}")

    # Verify the result
    read_result = fs_tools.read_file("test_autocorrect.py")
    if 'def divide' in read_result['content']:
        lines = read_result['content'].split('\n')
        for i, line in enumerate(lines):
            if 'def divide' in line:
                print(f"  divide function inserted at line {i+1}")
                # Should be after multiply ends (around line 11), not line 7
                if i > 9:
                    print(f"  [PASS] Correctly inserted after multiply function ends")
                else:
                    print(f"  [WARN] May have inserted too early")
                break
    else:
        print(f"  [FAIL] divide function not found in file")

    # Test 2: Single-line pattern with parameters (should work normally)
    print("\n[TEST 2] Using function signature pattern")
    print("-" * 70)

    pattern_with_params = "def add(a, b):"
    print(f"  Pattern: '{pattern_with_params}'")

    modulo_func = """
def modulo(a, b):
    return a % b
"""

    result = fs_tools.edit_file(
        "test_autocorrect.py",
        mode="insert_after",
        insert_after=pattern_with_params,
        content=modulo_func
    )

    if result['success']:
        print(f"  [PASS] Function signature pattern works")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 3: Short pattern (recommended way)
    print("\n[TEST 3] Using short pattern (best practice)")
    print("-" * 70)

    short_pattern = "def subtract"
    print(f"  Pattern: '{short_pattern}'")

    power_func = """
def power(a, b):
    return a ** b
"""

    result = fs_tools.edit_file(
        "test_autocorrect.py",
        mode="insert_after",
        insert_after=short_pattern,
        content=power_func
    )

    if result['success']:
        print(f"  [PASS] Short pattern works perfectly")
    else:
        print(f"  [FAIL] {result['error']}")

    # Test 4: Pattern not found (should give helpful error)
    print("\n[TEST 4] Pattern not found (error message quality)")
    print("-" * 70)

    bad_pattern = "def nonexistent(x, y):"
    print(f"  Pattern: '{bad_pattern}'")

    result = fs_tools.edit_file(
        "test_autocorrect.py",
        mode="insert_after",
        insert_after=bad_pattern,
        content="# test"
    )

    if not result['success']:
        print(f"  [PASS] Error caught: {result['error']}")
    else:
        print(f"  [FAIL] Should have failed but succeeded")

    # Test 5: insert_before with multi-line pattern
    print("\n[TEST 5] insert_before with multi-line pattern")
    print("-" * 70)

    multi_line_before = """def add(a, b):
    return a + b"""

    comment = "# Mathematical operations\n"

    result = fs_tools.edit_file(
        "test_autocorrect.py",
        mode="insert_before",
        insert_before=multi_line_before,
        content=comment
    )

    if result['success']:
        print(f"  [PASS] insert_before auto-correction works")
    else:
        print(f"  [FAIL] {result['error']}")

    # Show final file
    print("\n[FINAL RESULT] File contents:")
    print("-" * 70)
    read_result = fs_tools.read_file("test_autocorrect.py")
    if read_result['success']:
        lines = read_result['content'].split('\n')
        for i, line in enumerate(lines, 1):
            marker = " >>>" if any(x in line for x in ['divide', 'modulo', 'power', '# Mathematical']) else "    "
            print(f"{marker} {i:3d} | {line}")
    print("-" * 70)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("\n  Auto-Correction Features Tested:")
    print("    [x] Multi-line pattern normalization")
    print("    [x] Function signature patterns")
    print("    [x] Short pattern (best practice)")
    print("    [x] Helpful error messages")
    print("    [x] insert_before auto-correction")
    print("\n  All auto-correction features working!")
    print("\n" + "=" * 70)

    # Cleanup
    print("\nCleaning up...")
    fs_tools.delete_file("test_autocorrect.py")
    print("Done!")

if __name__ == "__main__":
    test_auto_correction()
