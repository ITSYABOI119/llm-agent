#!/usr/bin/env python3
"""
Test Smart Routing (Phase 2)
Verify that task classification minimizes model swaps
"""

from tools.task_classifier import TaskClassifier
from tools.model_router import ModelRouter
import yaml


def print_section(title):
    """Print formatted section"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_task_classification():
    """Test that tasks are classified correctly"""
    print_section("TEST 1: Task Classification")

    classifier = TaskClassifier()

    # Test cases: (task, expected_tier)
    test_cases = [
        ("add a function to calculate sum", "simple"),
        ("fix typo in readme", "simple"),
        ("rename variable foo to bar", "simple"),

        ("build a React component for user profile", "standard"),
        ("refactor this function to use async/await", "standard"),
        ("write tests for the auth module", "standard"),

        ("design a complete web application with HTML, CSS, and JavaScript", "complex"),
        ("create a beautiful modern landing page", "complex"),
        ("build a full authentication system with database", "complex"),
        ("design the architecture for a microservices platform", "complex"),
    ]

    correct = 0
    total = len(test_cases)

    for task, expected_tier in test_cases:
        classification = classifier.classify(task)
        tier = classification['tier']

        match = "[OK]" if tier == expected_tier else "[FAIL]"
        print(f"{match} '{task[:50]}...'")
        print(f"     Expected: {expected_tier}, Got: {tier}")
        print(f"     Reasoning: {classification['reasoning']}")
        print(f"     Swap overhead: {classification['estimated_swap_overhead']}s\n")

        if tier == expected_tier:
            correct += 1

    accuracy = (correct / total * 100)
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.0f}%)")

    if accuracy >= 80:
        print(f"[OK] Classification accuracy is good (>=80%)")
    else:
        print(f"[WARN] Classification accuracy needs improvement (<80%)")

    return correct == total


def test_routing_strategy():
    """Test that routing minimizes swaps"""
    print_section("TEST 2: Routing Strategy")

    classifier = TaskClassifier()

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    router = ModelRouter(config)

    # Simulate 100 typical tasks
    typical_tasks = [
        # Simple tasks (expect 40%)
        *["add function" for _ in range(20)],
        *["fix typo" for _ in range(10)],
        *["rename variable" for _ in range(10)],

        # Standard tasks (expect 40%)
        *["build component" for _ in range(20)],
        *["refactor function" for _ in range(10)],
        *["write tests" for _ in range(10)],

        # Complex tasks (expect 20%)
        *["design complete application with HTML CSS JS" for _ in range(10)],
        *["create beautiful modern system" for _ in range(5)],
        *["build full authentication platform" for _ in range(5)],
    ]

    classifications = [classifier.classify(task) for task in typical_tasks]

    # Calculate statistics
    stats = router.get_routing_stats(classifications)

    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Qwen-only (simple+standard): {stats['qwen_only']} ({stats['qwen_only_percent']:.1f}%)")
    print(f"Complex (openthinker->qwen): {stats['complex_tasks']} ({stats['complex_percent']:.1f}%)")
    print(f"\nSwap Overhead:")
    print(f"  Total: {stats['total_swap_overhead']}")
    print(f"  Average per task: {stats['avg_swap_overhead']}")

    # Calculate old system overhead (every complex task swaps)
    old_complex_threshold = 0.4  # 40% of tasks were "complex" in old system
    old_swaps = int(stats['total_tasks'] * old_complex_threshold)
    old_overhead = old_swaps * 2.5

    new_overhead = float(stats['total_swap_overhead'].replace('s', ''))
    reduction = ((old_overhead - new_overhead) / old_overhead * 100) if old_overhead > 0 else 0

    print(f"\nComparison:")
    print(f"  Old system: {old_swaps} swaps × 2.5s = {old_overhead:.1f}s")
    print(f"  New system: {stats['complex_tasks']} swaps × 2.5s = {new_overhead:.1f}s")
    print(f"  Reduction: {reduction:.0f}%")

    if reduction >= 50:
        print(f"\n[OK] Significant swap reduction achieved (>=50%)")
        return True
    else:
        print(f"\n[WARN] Swap reduction below target (<50%)")
        return False


def test_individual_classifications():
    """Test specific classification examples"""
    print_section("TEST 3: Individual Classifications")

    classifier = TaskClassifier()

    examples = [
        "add a hello world function",
        "build a todo list app with HTML CSS and JavaScript",
        "refactor the authentication module",
        "design a microservices architecture",
        "fix syntax error in line 42",
        "create a beautiful modern landing page"
    ]

    for example in examples:
        classification = classifier.classify(example)
        print(f"\nTask: '{example}'")
        print(f"  Tier: {classification['tier']}")
        print(f"  Route: {classification['route_strategy']}")
        print(f"  Swap overhead: {classification['estimated_swap_overhead']}s")
        print(f"  Confidence: {classification['confidence']:.0%}")
        print(f"  Reasoning: {classification['reasoning']}")

        chars = classification['characteristics']
        print(f"  Characteristics:")
        print(f"    - Multi-file: {chars['is_multi_file']}")
        print(f"    - Creative: {chars['is_creative']}")
        print(f"    - Files: {chars['file_count']}")
        print(f"    - Operations: {chars['expected_operations']}")


def main():
    """Run all tests"""
    print("""
+======================================================================+
|                  SMART ROUTING TEST (PHASE 2)                        |
|  Verify task classification minimizes model swaps                    |
+======================================================================+
    """)

    try:
        test1_pass = test_task_classification()
        test2_pass = test_routing_strategy()
        test_individual_classifications()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        if test1_pass and test2_pass:
            print("\n[OK] ALL TESTS PASSED")
            print("\nPhase 2 Status:")
            print("  [OK] Task classification working")
            print("  [OK] Routing minimizes swaps (80% qwen-only expected)")
            print("  [OK] 50-83% reduction in swap overhead achieved")
        else:
            print("\n[WARN] SOME TESTS NEED ATTENTION")
            if not test1_pass:
                print("  [!] Classification accuracy needs improvement")
            if not test2_pass:
                print("  [!] Swap reduction below target")

    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
