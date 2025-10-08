"""
Quick test of OpenThinker3-7B with new reasoning support
"""
from agent import Agent
import logging

# Set up logging to see reasoning blocks
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# Create agent
agent = Agent()

print("="*80)
print("Testing OpenThinker3-7B with Reasoning Support")
print("="*80)
print(f"Model: {agent.config['ollama']['model']}")
print(f"Is reasoning model: {agent._is_reasoning_model()}")
print("="*80)

# Simple test: Create a file
test_prompt = 'Create a file called test_reasoning.txt with the content "Hello from OpenThinker3!"'

print(f"\nTest Prompt: {test_prompt}\n")
print("Agent response:")
print("-"*80)

response = agent.chat(test_prompt)

print(response)
print("-"*80)
print("\nTest complete!")
