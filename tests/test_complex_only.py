"""
Test just the complex creative task with two-phase execution
"""
from agent import Agent
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("="*80)
print("TWO-PHASE EXECUTION TEST: Complex Creative Task")
print("="*80)

agent = Agent()

prompt = '''Create a modern landing page for a tech startup called "NeuralFlow AI".
Include index.html with semantic structure, styles.css with a purple-to-blue gradient hero section
and glassmorphism cards, and script.js with smooth scroll animations.'''

print(f"\nPrompt: {prompt}\n")
print("Executing...\n")

response = agent.chat(prompt)

print("="*80)
print("RESPONSE:")
print("="*80)
print(response)
print("="*80)
