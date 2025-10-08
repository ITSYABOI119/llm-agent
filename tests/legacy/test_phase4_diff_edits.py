"""
Phase 4: Diff-Based Edits Test
Verify structured diff editing is more reliable than comment markers
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.diff_editor import DiffEditor


def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_single_change():
    """Test applying a single line-based change"""
    print_header("TEST 1: Single Change")

    # Create temp workspace
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "test.py"

    # Write test file
    original = """def hello():
    print("Hello")
    return True

def goodbye():
    print("Goodbye")
    return False
"""
    test_file.write_text(original)

    # Create editor
    editor = DiffEditor(temp_dir)

    # Apply change to hello function
    result = editor.apply_single_change(
        "test.py",
        start_line=1,
        end_line=3,
        new_content="""def hello(name):
    print(f"Hello, {name}!")
    return name""",
        reason="Added name parameter"
    )

    print(f"Result: {result['success']}")
    print(f"Changes applied: {result.get('changes_applied', 0)}")
    print(f"Lines: {result.get('original_line_count')} -> {result.get('new_line_count')}")

    # Read result
    modified = test_file.read_text()
    print(f"\nModified file:\n{modified}")

    # Verify goodbye function unchanged
    success = "def goodbye():" in modified and 'name' in modified

    # Cleanup
    shutil.rmtree(temp_dir)

    if success:
        print("\n[OK] Single change applied correctly")
        print("[OK] Other functions preserved")
        return True
    else:
        print("\n[FAIL] Change not applied correctly")
        return False


def test_multiple_changes():
    """Test applying multiple changes at once"""
    print_header("TEST 2: Multiple Changes")

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "multi.py"

    original = """# Header comment
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""
    test_file.write_text(original)

    editor = DiffEditor(temp_dir)

    # Apply multiple changes
    changes = [
        {
            'start_line': 2,
            'end_line': 3,
            'new_content': 'def func1():\n    return 10  # Modified',
            'reason': 'Updated func1 return value'
        },
        {
            'start_line': 8,
            'end_line': 9,
            'new_content': 'def func3():\n    return 30  # Modified',
            'reason': 'Updated func3 return value'
        }
    ]

    result = editor.apply_diff("multi.py", changes)

    print(f"Result: {result['success']}")
    print(f"Changes applied: {result.get('changes_applied', 0)}")

    modified = test_file.read_text()
    print(f"\nModified file:\n{modified}")

    # Verify changes
    success = (
        "return 10  # Modified" in modified and
        "return 30  # Modified" in modified and
        "return 2" in modified  # func2 unchanged
    )

    shutil.rmtree(temp_dir)

    if success:
        print("\n[OK] Multiple changes applied correctly")
        print("[OK] Unchanged functions preserved")
        return True
    else:
        print("\n[FAIL] Multiple changes failed")
        return False


def test_insert_lines():
    """Test inserting new lines"""
    print_header("TEST 3: Insert Lines")

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "insert.py"

    original = """def main():
    print("Start")
    print("End")
"""
    test_file.write_text(original)

    editor = DiffEditor(temp_dir)

    # Insert lines after line 2
    result = editor.insert_lines(
        "insert.py",
        after_line=2,
        content='    print("Middle")\n    print("Extra")',
        reason="Added middle section"
    )

    print(f"Result: {result['success']}")

    modified = test_file.read_text()
    print(f"\nModified file:\n{modified}")

    # Verify insertion
    lines = modified.split('\n')
    success = (
        len(lines) >= 5 and
        'Middle' in modified and
        'Extra' in modified and
        lines[1].strip() == 'print("Start")' and
        lines[-2].strip() == 'print("End")'
    )

    shutil.rmtree(temp_dir)

    if success:
        print("\n[OK] Lines inserted correctly")
        print("[OK] Original lines preserved in order")
        return True
    else:
        print("\n[FAIL] Insertion failed")
        return False


def test_delete_lines():
    """Test deleting lines"""
    print_header("TEST 4: Delete Lines")

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "delete.py"

    original = """def example():
    # TODO: Remove this
    # This is outdated
    print("Keep this")
    return True
"""
    test_file.write_text(original)

    editor = DiffEditor(temp_dir)

    # Delete comment lines
    result = editor.delete_lines(
        "delete.py",
        start_line=2,
        end_line=3,
        reason="Removed outdated comments"
    )

    print(f"Result: {result['success']}")

    modified = test_file.read_text()
    print(f"\nModified file:\n{modified}")

    # Verify deletion
    success = (
        "TODO" not in modified and
        "outdated" not in modified and
        'print("Keep this")' in modified
    )

    shutil.rmtree(temp_dir)

    if success:
        print("\n[OK] Lines deleted correctly")
        print("[OK] Other lines preserved")
        return True
    else:
        print("\n[FAIL] Deletion failed")
        return False


def test_replace_function():
    """Test replacing an entire function by name"""
    print_header("TEST 5: Replace Function by Name")

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "func.py"

    original = """def calculate(x):
    # Old implementation
    result = x * 2
    return result

def other_function():
    return "unchanged"
"""
    test_file.write_text(original)

    editor = DiffEditor(temp_dir)

    # Replace function by name
    result = editor.replace_function(
        "func.py",
        function_name="calculate",
        new_implementation="""def calculate(x, y=1):
    # New implementation
    result = (x * 2) + y
    return result""",
        reason="Enhanced calculate function"
    )

    print(f"Result: {result['success']}")

    modified = test_file.read_text()
    print(f"\nModified file:\n{modified}")

    # Verify replacement
    success = (
        "x, y=1" in modified and
        "New implementation" in modified and
        "Old implementation" not in modified and
        'other_function' in modified  # Other function preserved
    )

    shutil.rmtree(temp_dir)

    if success:
        print("\n[OK] Function replaced correctly")
        print("[OK] Other functions preserved")
        return True
    else:
        print("\n[FAIL] Function replacement failed")
        return False


def test_preview_diff():
    """Test preview functionality"""
    print_header("TEST 6: Preview Diff")

    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "preview.py"

    original = """def test():
    return 1
"""
    test_file.write_text(original)

    editor = DiffEditor(temp_dir)

    # Preview change without applying
    changes = [{
        'start_line': 1,
        'end_line': 2,
        'new_content': 'def test():\n    return 2',
        'reason': 'Change return value'
    }]

    preview = editor.preview_diff("preview.py", changes)

    print("Preview:")
    print(preview)

    # Verify file is unchanged
    current = test_file.read_text()
    unchanged = current == original
    has_preview = 'return 1' in preview and 'return 2' in preview

    shutil.rmtree(temp_dir)

    if unchanged and has_preview:
        print("\n[OK] Preview generated correctly")
        print("[OK] File remains unchanged")
        return True
    else:
        print("\n[FAIL] Preview test failed")
        return False


def test_error_handling():
    """Test error handling for invalid operations"""
    print_header("TEST 7: Error Handling")

    temp_dir = tempfile.mkdtemp()
    editor = DiffEditor(temp_dir)

    # Test 1: Non-existent file
    result1 = editor.apply_single_change(
        "nonexistent.py",
        start_line=1,
        end_line=1,
        new_content="",
        reason="Test"
    )

    test1_pass = not result1['success'] and 'not found' in result1.get('error', '').lower()
    print(f"[{'OK' if test1_pass else 'FAIL'}] Non-existent file handled: {result1.get('error', '')[:50]}")

    # Test 2: Replace non-existent function
    test_file = Path(temp_dir) / "test.py"
    test_file.write_text("def other(): pass")

    result2 = editor.replace_function(
        "test.py",
        function_name="nonexistent",
        new_implementation="def x(): pass",
        reason="Test"
    )

    test2_pass = not result2['success'] and 'not found' in result2.get('error', '').lower()
    print(f"[{'OK' if test2_pass else 'FAIL'}] Non-existent function handled: {result2.get('error', '')[:50]}")

    shutil.rmtree(temp_dir)

    if test1_pass and test2_pass:
        print("\n[OK] Error handling working correctly")
        return True
    else:
        print("\n[FAIL] Some error handling tests failed")
        return False


def main():
    print("+======================================================================+")
    print("|              PHASE 4: DIFF-BASED EDITS TEST                          |")
    print("|  Verify structured diff editing reliability                          |")
    print("+======================================================================+")

    tests = [
        test_single_change,
        test_multiple_changes,
        test_insert_lines,
        test_delete_lines,
        test_replace_function,
        test_preview_diff,
        test_error_handling
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n[ERROR] Test failed with exception: {e}")
            results.append(False)

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print("[OK] ALL TESTS PASSED\n")
        print("Phase 4 Status:")
        print("  [OK] Single change edits working")
        print("  [OK] Multiple simultaneous edits working")
        print("  [OK] Line insertion working")
        print("  [OK] Line deletion working")
        print("  [OK] Function replacement working")
        print("  [OK] Diff preview working")
        print("  [OK] Error handling working")
        print("\nKey Benefits:")
        print("  - More reliable than comment markers")
        print("  - Handles multiple changes atomically")
        print("  - Preview changes before applying")
        print("  - Intelligent function replacement")
    else:
        print(f"[FAIL] {total - passed}/{total} tests failed\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
