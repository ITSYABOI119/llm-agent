#!/usr/bin/env python3
"""Quick test to verify tool execution works"""

import yaml
from agent import Agent

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create agent
agent = Agent()

print("Testing tool parsing...")

# Test 1: Simple tool call
test_response = """I'll create that folder for you.

TOOL: create_folder | PARAMS: {"path": "test_folder"}

Done!"""

tool_calls = agent.parse_tool_calls(test_response)
print(f"Test 1 - Found {len(tool_calls)} tool calls:")
for tc in tool_calls:
    print(f"  - {tc['tool']} with params: {tc['params']}")

# Test 2: Multiple tools
test_response2 = """Let me create a file and write content.

TOOL: write_file | PARAMS: {"path": "test.txt", "content": "Hello World"}
TOOL: read_file | PARAMS: {"path": "test.txt"}
"""

tool_calls2 = agent.parse_tool_calls(test_response2)
print(f"\nTest 2 - Found {len(tool_calls2)} tool calls:")
for tc in tool_calls2:
    print(f"  - {tc['tool']} with params: {tc['params']}")

print("\n=== Test complete ===")
