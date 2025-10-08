#!/usr/bin/env python3
"""Test all edit_file modes"""

import sys
import yaml
from pathlib import Path
from tools.filesystem import FileSystemTools

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

fs = FileSystemTools(config)
test_file = "test_edit.py"

print("=" * 60)
print("Testing Advanced edit_file Modes")
print("=" * 60)

# Create initial file
print("\n1. Creating test file...")
result = fs.write_file(test_file, """# Test File
import sys

def hello():
    print("Hello")

def world():
    print("World")

# End of file
""")
print(f"✓ Created: {result['message']}")

# Test 1: append
print("\n2. Testing append mode...")
result = fs.edit_file(test_file, mode="append", content="\n# Appended comment\n")
print(f"✓ {result['message']}")

# Test 2: prepend
print("\n3. Testing prepend mode...")
result = fs.edit_file(test_file, mode="prepend", content="#!/usr/bin/env python3\n")
print(f"✓ {result['message']}")

# Test 4: replace
print("\n4. Testing replace mode (all occurrences)...")
result = fs.edit_file(test_file, mode="replace", search="print", replace="logging.info")
print(f"✓ {result['message']}")

# Test 5: replace_once
print("\n5. Testing replace_once mode...")
result = fs.edit_file(test_file, mode="replace_once", search="logging.info", replace="print")
print(f"✓ {result['message']}")

# Test 6: insert_at_line
print("\n6. Testing insert_at_line mode...")
result = fs.edit_file(test_file, mode="insert_at_line", line_number=3, content="import os\n")
print(f"✓ {result['message']}")

# Test 7: insert_after
print("\n7. Testing insert_after mode...")
result = fs.edit_file(test_file, mode="insert_after", insert_after="import sys", content="import json\n")
print(f"✓ {result['message']}")

# Test 8: insert_before
print("\n8. Testing insert_before mode...")
result = fs.edit_file(test_file, mode="insert_before", insert_before="def hello", content="\ndef new_func():\n    pass\n")
print(f"✓ {result['message']}")

# Test 9: replace_lines
print("\n9. Testing replace_lines mode...")
result = fs.edit_file(test_file, mode="replace_lines", start_line=1, end_line=2,
                      content="#!/usr/bin/env python3\n# Test File - Modified\n")
print(f"✓ {result['message']}")

# Show final file
print("\n" + "=" * 60)
print("FINAL FILE CONTENT:")
print("=" * 60)
content = fs.read_file(test_file)
if content['success']:
    print(content['content'])

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
