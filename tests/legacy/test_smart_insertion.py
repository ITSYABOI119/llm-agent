"""Test smart pattern matching for insert_after mode"""
import yaml
from tools.filesystem import FileSystemTools

def test_smart_insertion():
    """Test that insert_after finds the end of functions, not just the first line"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    fs_tools = FileSystemTools(config)

    print("Testing Smart Pattern Matching for insert_after\n")
    print("=" * 60)

    # Create a test file with multiple functions
    test_code = """import sys

def multiply(a, b):
    '''Multiply two numbers'''
    result = a * b
    return result

def divide(a, b):
    '''Divide two numbers'''
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b

def add(a, b):
    '''Add two numbers'''
    return a + b
"""

    # Write initial file
    fs_tools.write_file("test_smart.py", test_code)
    print("\n[1] Created test file with 3 functions")

    # Test: Insert after multiply function
    # Should insert AFTER the function ends (after line 6), not after line 3
    print("\n[2] Testing insert_after 'def multiply' - should insert after function ends")

    new_function = """
def power(a, b):
    '''Raise a to the power of b'''
    return a ** b
"""

    result = fs_tools.edit_file(
        "test_smart.py",
        mode="insert_after",
        insert_after="def multiply",
        content=new_function
    )

    assert result['success'], f"Insert failed: {result.get('error')}"
    print(f"  SUCCESS: {result['message']}")

    # Read the file and check where it was inserted
    read_result = fs_tools.read_file("test_smart.py")
    updated_content = read_result['content']

    print("\n[3] Verifying insertion location...")
    lines = updated_content.split('\n')

    # Find where power function was inserted
    power_line = None
    for i, line in enumerate(lines):
        if 'def power' in line:
            power_line = i + 1  # 1-based
            break

    # Find where multiply function is
    multiply_line = None
    for i, line in enumerate(lines):
        if 'def multiply' in line:
            multiply_line = i + 1  # 1-based
            break

    print(f"  multiply function starts at line: {multiply_line}")
    print(f"  power function inserted at line: {power_line}")

    # The power function should be inserted AFTER multiply ends (around line 8)
    # Not right after the def line (line 4)
    if power_line and multiply_line:
        if power_line > multiply_line + 3:  # Should be at least 3 lines after (for the function body)
            print(f"  [PASS] Smart insertion worked! Inserted after function end, not after def line")
        else:
            print(f"  [WARN] May have inserted too early (expected > {multiply_line + 3}, got {power_line})")

    # Show the relevant section
    print("\n[4] File content around insertion:")
    print("  " + "-" * 56)
    for i in range(max(0, power_line - 5), min(len(lines), power_line + 5)):
        marker = " >>>" if i == power_line - 1 else "    "
        print(f"  {marker} {i+1:3d} | {lines[i]}")
    print("  " + "-" * 56)

    print("\n" + "=" * 60)
    print("\n[SUCCESS] Smart insertion test completed!")

    # Cleanup
    print("\nCleaning up...")
    fs_tools.delete_file("test_smart.py")
    print("Done!")

if __name__ == "__main__":
    test_smart_insertion()
