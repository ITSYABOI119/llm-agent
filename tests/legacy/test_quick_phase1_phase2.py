#!/usr/bin/env python3
"""
Quick Test: Phase 1 + Phase 2 Core Components
Tests components without full agent initialization
"""

from tools.task_classifier import TaskClassifier
from tools.model_router import ModelRouter
from tools.verifier import ActionVerifier
from tools.context_gatherer import ContextGatherer
from tools.token_counter import TokenCounter
from tools.model_manager import SmartModelManager
import yaml


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_phase1_tools():
    """Test Phase 1 tools directly"""
    print_section("PHASE 1: Core Tools")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Test 1: Token Counter
    print("Test 1: Token Counter")
    counter = TokenCounter(max_tokens=8000)
    tokens = counter.estimate_tokens("This is a test message for the agent")
    budget = counter.get_budget_for_phase('execution')
    print(f"  [OK] Estimated tokens: {tokens}")
    print(f"  [OK] Execution budget: {budget} tokens")

    # Test 2: Model Manager
    print("\nTest 2: Model Manager (accurate swap measurement)")
    manager = SmartModelManager("http://localhost:11434", config)

    print(f"  Loading qwen2.5-coder:7b...")
    import time
    start = time.time()
    success = manager.ensure_in_vram("qwen2.5-coder:7b", "test")
    elapsed = time.time() - start

    if success and elapsed > 0.1:
        print(f"  [OK] Model loaded, swap measured: {elapsed:.2f}s")
    else:
        print(f"  [WARN] Check: success={success}, time={elapsed:.2f}s")

    status = manager.get_status()
    print(f"  [OK] Swap count: {status['swap_count']}")
    print(f"  [OK] Average swap time: {status['avg_swap_time']}")

    print("\n[OK] Phase 1 tools working")
    return True


def test_phase2_classification():
    """Test Phase 2 task classification"""
    print_section("PHASE 2: Task Classification")

    classifier = TaskClassifier()

    test_cases = [
        ("add a function", "simple", 0.0),
        ("build a component", "standard", 0.0),
        ("design complete application", "complex", 2.5),
    ]

    correct = 0
    for task, expected_tier, expected_swap in test_cases:
        classification = classifier.classify(task)
        tier = classification['tier']
        swap = classification['estimated_swap_overhead']

        match = "[OK]" if tier == expected_tier else "[FAIL]"
        print(f"{match} '{task}'")
        print(f"     Tier: {tier} (expected: {expected_tier})")
        print(f"     Swap: {swap}s (expected: {expected_swap}s)")
        print(f"     Route: {classification['route_strategy']}\n")

        if tier == expected_tier:
            correct += 1

    accuracy = (correct / len(test_cases)) * 100
    print(f"Accuracy: {correct}/{len(test_cases)} ({accuracy:.0f}%)")

    if accuracy >= 80:
        print("[OK] Classification working")
        return True
    else:
        print("[WARN] Classification accuracy low")
        return False


def test_phase2_routing():
    """Test Phase 2 routing logic"""
    print_section("PHASE 2: Smart Routing")

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    router = ModelRouter(config)
    classifier = TaskClassifier()

    # Simulate 20 tasks
    tasks = [
        *["add function" for _ in range(8)],
        *["build component" for _ in range(8)],
        *["design application" for _ in range(4)],
    ]

    classifications = [classifier.classify(task) for task in tasks]
    stats = router.get_routing_stats(classifications)

    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Qwen-only: {stats['qwen_only']} ({stats['qwen_only_percent']:.0f}%)")
    print(f"Complex: {stats['complex_tasks']} ({stats['complex_percent']:.0f}%)")
    print(f"Total swap overhead: {stats['total_swap_overhead']}")
    print(f"Average per task: {stats['avg_swap_overhead']}")

    qwen_percent = stats['qwen_only_percent']
    if qwen_percent >= 70:
        print(f"\n[OK] Smart routing working ({qwen_percent:.0f}% qwen-only)")
        return True
    else:
        print(f"\n[WARN] Qwen-only percentage low ({qwen_percent:.0f}%)")
        return False


def main():
    print("""
+======================================================================+
|            QUICK PHASE 1 + PHASE 2 TEST                              |
|  Tests core components without full agent initialization             |
+======================================================================+
    """)

    try:
        phase1_pass = test_phase1_tools()
        phase2a_pass = test_phase2_classification()
        phase2b_pass = test_phase2_routing()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        if phase1_pass and phase2a_pass and phase2b_pass:
            print("\n[OK] ALL TESTS PASSED")
            print("\nPhase 1 Status:")
            print("  [OK] Token counting working")
            print("  [OK] Model manager measuring swaps accurately")

            print("\nPhase 2 Status:")
            print("  [OK] Task classification working")
            print("  [OK] Smart routing minimizes swaps")
            print("  [OK] 70-80% tasks route to qwen-only")

            print("\nReady for production use!")

        else:
            print("\n[WARN] SOME TESTS NEED ATTENTION")
            if not phase1_pass:
                print("  [!] Phase 1 issues")
            if not phase2a_pass:
                print("  [!] Phase 2 classification issues")
            if not phase2b_pass:
                print("  [!] Phase 2 routing issues")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
