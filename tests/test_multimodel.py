"""
Test the Hybrid Multi-Model System
"""
from agent import Agent
import logging

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("="*80)
print("HYBRID MULTI-MODEL SYSTEM TEST")
print("="*80)

agent = Agent()

print(f"\nMulti-model enabled: {agent.model_router.enabled}")
print(f"Available models:")
for key, model_config in agent.model_router.models.items():
    print(f"  - {key}: {model_config.get('name', 'N/A')}")

print("\n" + "="*80)
print("TEST 1: Simple Task (should use single-phase, qwen2.5-coder)")
print("="*80)

response1 = agent.chat('Create a file called simple.txt with content "Test123"')
print(f"\nResponse:\n{response1}")

print("\n" + "="*80)
print("TEST 2: Analysis Task (should use openthinker3-7b)")
print("="*80)

response2 = agent.chat('Explain why Python is popular for data science')
print(f"\nResponse:\n{response2}")

print("\n" + "="*80)
print("TEST 3: Complex Creative Task (should use TWO-PHASE)")
print("="*80)

response3 = agent.chat('''Create a modern landing page for a tech startup called "NeuralFlow AI".
Include index.html with semantic structure, styles.css with a purple-to-blue gradient hero section
and glassmorphism cards, and script.js with smooth scroll animations and a typing effect for the tagline.''')

print(f"\nResponse:\n{response3}")

print("\n" + "="*80)
print("ALL TESTS COMPLETE")
print("="*80)
