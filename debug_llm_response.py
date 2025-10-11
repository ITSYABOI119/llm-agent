"""
Debug script to capture raw LLM response
"""
import requests
import yaml
from pathlib import Path

# Load config
config_path = Path(__file__).parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Call Ollama API directly
api_url = f"http://{config['ollama']['host']}:{config['ollama']['port']}"
model = "openthinker3-7b"

prompt = """You are an AI assistant with access to tools. Your workspace is: c:\\Users\\jluca\\Documents\\newfolder\\agent_workspace

Available tools:
- write_file(path, content) - Create a new file

TOOL USAGE FORMAT:
To use a tool, respond EXACTLY in this format:
TOOL: tool_name | PARAMS: {"param1": "value1"}

User: Create a file called debug_test.txt with 'Debug Test'"""

response = requests.post(
    f"{api_url}/api/generate",
    json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 8192,
            "num_predict": 2048
        }
    },
    timeout=120
)

result = response.json()
llm_response = result.get('response', '')

print("=" * 80)
print("RAW LLM RESPONSE:")
print("=" * 80)
print(llm_response)
print("=" * 80)