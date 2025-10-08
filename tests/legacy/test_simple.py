"""
Simple test with improved prompts
"""
from agent import Agent

agent = Agent()
print(f"Model: {agent.config['ollama']['model']}")
print(f"Is reasoning: {agent._is_reasoning_model()}\n")

response = agent.chat('Create a file called hello.txt with content "Hello World"')
print(f"\nResponse:\n{response}")
