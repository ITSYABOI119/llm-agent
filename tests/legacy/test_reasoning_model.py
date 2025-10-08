"""
Test script to understand OpenThinker3-7B's output format
"""
import requests

def test_reasoning_output():
    """Test what OpenThinker3-7B actually outputs"""

    # Simple prompt to understand output format
    prompt = """You are an AI assistant with access to tools.

Available tools:
- write_file: Create a new file
  Parameters: {"path": "filename", "content": "file content"}

TOOL USAGE FORMAT:
To use a tool, respond EXACTLY in this format:
TOOL: tool_name | PARAMS: {"param1": "value1"}

User request: Create a file called hello.txt with the content "Hello World"
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "openthinker3-7b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
    )

    if response.status_code == 200:
        result = response.json()
        output = result.get('response', '')

        print("="*80)
        print("OPENTHINKER3-7B OUTPUT:")
        print("="*80)
        print(output)
        print("="*80)
        print("\nANALYSIS:")
        print("- Contains <think> tags:", "<think>" in output)
        print("- Contains TOOL: format:", "TOOL:" in output)
        print("- Output length:", len(output), "characters")

        # Try to find patterns
        if "<think>" in output:
            import re
            think_pattern = r'<think>(.*?)</think>'
            thinks = re.findall(think_pattern, output, re.DOTALL)
            print(f"- Found {len(thinks)} thinking blocks")

    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    test_reasoning_output()