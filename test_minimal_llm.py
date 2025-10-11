"""
Minimal test to verify LLM is being called
"""
from agent import Agent
from pathlib import Path

# Load agent with real config
config_path = Path(__file__).parent / "config.yaml"
agent = Agent(str(config_path))

# Send a simple request
print("=" * 60)
print("SENDING: Create a file called test_llm.txt with 'LLM Test'")
print("=" * 60)

response = agent.chat("Create a file called test_llm.txt with 'LLM Test'")

print("\n" + "=" * 60)
print("AGENT RESPONSE:")
print("=" * 60)
print(response)
print("=" * 60)

# Check workspace
workspace = Path("c:/Users/jluca/Documents/newfolder/agent_workspace")
test_file = workspace / "test_llm.txt"

if test_file.exists():
    print(f"\n✓ File created: {test_file}")
    print(f"Content: {test_file.read_text()}")
else:
    print(f"\n✗ File NOT created at {test_file}")
