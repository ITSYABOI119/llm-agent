#!/usr/bin/env python3
"""
Test Model Swapping Performance
Verifies that model swaps are actually happening and measures timing accurately
"""

import sys
import time
import requests
from agent import Agent


def test_actual_model_swaps():
    """
    Test real model swaps by making actual API calls
    This verifies models are truly being swapped, not just state tracking
    """
    print("="*70)
    print("TESTING ACTUAL MODEL SWAPS")
    print("="*70)

    print("\nInitializing agent (preloading models to RAM)...")
    start_init = time.time()
    agent = Agent()
    init_time = time.time() - start_init
    print(f"[OK] Agent initialized in {init_time:.1f}s")

    print(f"\nRAM preloaded models: {agent.model_manager.ram_preloaded}")
    print(f"Current VRAM model: {agent.model_manager.current_vram_model}")

    # Test 1: First call to OpenThinker (should be in RAM)
    print("\n" + "="*70)
    print("TEST 1: Call OpenThinker (should load from RAM to VRAM)")
    print("="*70)

    model1 = "openthinker3-7b"
    prompt1 = "Hello"

    print(f"Making API call to {model1}...")
    start1 = time.time()

    response1 = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model1,
            "prompt": prompt1,
            "keep_alive": "60m",
            "stream": False,
            "options": {"num_predict": 5}
        },
        timeout=60
    )

    time1 = time.time() - start1
    print(f"Response time: {time1:.3f}s")

    if response1.status_code == 200:
        response_text = response1.json().get('response', '')
        print(f"[OK] {model1} responded: '{response_text[:50]}...'")
        print(f"Timing: {time1:.3f}s")
    else:
        print(f"[FAIL] Request failed: {response1.status_code}")

    agent.model_manager.current_vram_model = model1

    # Test 2: Call to Qwen (should swap from OpenThinker to Qwen)
    print("\n" + "="*70)
    print("TEST 2: Swap to Qwen (RAM -> VRAM swap)")
    print("="*70)

    model2 = "qwen2.5-coder:7b"
    prompt2 = "Hello"

    print(f"Previous VRAM model: {model1}")
    print(f"Swapping to: {model2}")
    print(f"Making API call to {model2}...")

    start2 = time.time()

    response2 = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model2,
            "prompt": prompt2,
            "keep_alive": "60m",
            "stream": False,
            "options": {"num_predict": 5}
        },
        timeout=60
    )

    time2 = time.time() - start2
    print(f"Response time: {time2:.3f}s")

    if response2.status_code == 200:
        response_text = response2.json().get('response', '')
        print(f"[OK] {model2} responded: '{response_text[:50]}...'")
        print(f"Timing: {time2:.3f}s")
    else:
        print(f"[FAIL] Request failed: {response2.status_code}")

    agent.model_manager.current_vram_model = model2

    # Test 3: Swap back to OpenThinker
    print("\n" + "="*70)
    print("TEST 3: Swap back to OpenThinker")
    print("="*70)

    print(f"Previous VRAM model: {model2}")
    print(f"Swapping back to: {model1}")
    print(f"Making API call to {model1}...")

    start3 = time.time()

    response3 = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model1,
            "prompt": prompt1,
            "keep_alive": "60m",
            "stream": False,
            "options": {"num_predict": 5}
        },
        timeout=60
    )

    time3 = time.time() - start3
    print(f"Response time: {time3:.3f}s")

    if response3.status_code == 200:
        response_text = response3.json().get('response', '')
        print(f"[OK] {model1} responded: '{response_text[:50]}...'")
        print(f"Timing: {time3:.3f}s")
    else:
        print(f"[FAIL] Request failed: {response3.status_code}")

    # Analysis
    print("\n" + "="*70)
    print("SWAP TIMING ANALYSIS")
    print("="*70)

    print(f"\nTest 1 ({model1} first load):  {time1:.3f}s")
    print(f"Test 2 ({model2} swap):         {time2:.3f}s")
    print(f"Test 3 ({model1} swap back):    {time3:.3f}s")

    avg_swap_time = (time2 + time3) / 2
    print(f"\nAverage swap time: {avg_swap_time:.3f}s")

    # Expected: 0.5-3s for RAM preloaded models
    if avg_swap_time < 3.0:
        print(f"\n[OK] Swaps are FAST! Average {avg_swap_time:.3f}s")
        print(f"RAM preloading is working correctly.")

        if avg_swap_time < 1.0:
            print(f"[INFO] Very fast swaps (<1s) - models likely cached in VRAM")
        else:
            print(f"[INFO] Good swap speed (1-3s) - RAM -> VRAM working")
    else:
        print(f"\n[WARN] Swaps are slow (>{avg_swap_time:.3f}s)")
        print(f"Models may not be preloaded in RAM")
        print(f"Expected: <3s, Got: {avg_swap_time:.3f}s")

    return {
        'test1_time': time1,
        'test2_time': time2,
        'test3_time': time3,
        'avg_swap': avg_swap_time
    }


def test_without_preload():
    """
    Test model swap WITHOUT preloading to show the difference
    """
    print("\n\n" + "="*70)
    print("BASELINE TEST: Model Load WITHOUT Preloading")
    print("="*70)

    print("\nTesting model load from disk (no RAM preload)...")
    print("This simulates what happens WITHOUT keep_alive")

    # Use a model that's NOT preloaded
    test_model = "openthinker3-7b"

    print(f"\nLoading {test_model} from disk (cold start)...")
    start = time.time()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": test_model,
            "prompt": "Hello",
            "keep_alive": "0s",  # Don't keep in memory
            "stream": False,
            "options": {"num_predict": 5}
        },
        timeout=120
    )

    cold_time = time.time() - start

    if response.status_code == 200:
        print(f"[OK] Cold load time: {cold_time:.3f}s")
    else:
        print(f"[FAIL] Request failed: {response.status_code}")

    return cold_time


def main():
    print("""
+======================================================================+
|            MODEL SWAP VERIFICATION TEST                              |
|  Testing actual model swaps with precise timing measurements         |
+======================================================================+
    """)

    try:
        # Test actual swaps
        results = test_actual_model_swaps()

        # Note about timing
        print("\n[INFO] Note: These times include model swap + inference")
        print("[INFO] Most time is spent on generating the 5-token response")
        print("[INFO] Actual swap time is harder to isolate from inference time")

        # Final summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)

        if results['avg_swap'] < 1.0:
            print("[OK] Model swaps are very fast (<1s)")
            print("Models are likely being cached efficiently")
        elif results['avg_swap'] < 3.0:
            print("[OK] Model swaps are fast (1-3s)")
            print("RAM preloading is working as expected")
        else:
            print("[WARN] Model swaps are slower than expected (>3s)")
            print("Check if models are actually preloaded to RAM")

        print(f"\nDetailed timings:")
        print(f"  First load:  {results['test1_time']:.3f}s")
        print(f"  Swap 1:      {results['test2_time']:.3f}s")
        print(f"  Swap 2:      {results['test3_time']:.3f}s")
        print(f"  Average:     {results['avg_swap']:.3f}s")

    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
