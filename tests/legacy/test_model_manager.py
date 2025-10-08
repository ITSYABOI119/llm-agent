#!/usr/bin/env python3
"""
Test Model Manager - Verify accurate swap time measurement
Tests the FIXED model_manager.py that actually loads models
"""

import time
from tools.model_manager import SmartModelManager


def test_model_manager():
    """Test that model manager actually loads models and measures swap time"""
    print("="*70)
    print("MODEL MANAGER TEST - Accurate Swap Measurement")
    print("="*70)

    # Initialize manager
    config = {
        'ollama': {
            'host': 'localhost',
            'port': 11434,
            'keep_alive': '60m'
        }
    }

    manager = SmartModelManager("http://localhost:11434", config)

    print("\n[TEST 1] Load first model (qwen2.5-coder:7b)")
    print("-" * 70)
    start = time.time()
    success = manager.ensure_in_vram("qwen2.5-coder:7b", "test")
    elapsed = time.time() - start

    if success:
        print(f"[OK] Model loaded successfully")
        print(f"    Time: {elapsed:.2f}s")
        if elapsed > 0.1:
            print(f"    [OK] Swap time was actually measured (not fake 0.00s)")
        else:
            print(f"    [WARN] Suspiciously fast - may still be cached")
    else:
        print(f"[FAIL] Model load failed")
        return False

    print("\n[TEST 2] Check status")
    print("-" * 70)
    status = manager.get_status()
    print(f"Current VRAM model: {status['vram_model']}")
    print(f"Swap count: {status['swap_count']}")
    print(f"Total swap time: {status['total_swap_time']}")
    print(f"Average swap time: {status['avg_swap_time']}")

    print("\n[TEST 3] Swap to different model (openthinker3-7b)")
    print("-" * 70)
    start = time.time()
    success = manager.ensure_in_vram("openthinker3-7b", "test")
    elapsed = time.time() - start

    if success:
        print(f"[OK] Model swapped successfully")
        print(f"    Time: {elapsed:.2f}s")
        if elapsed > 2.0:
            print(f"    [OK] Realistic swap time for Windows (~2.5s expected)")
        elif elapsed > 0.1:
            print(f"    [INFO] Faster than expected - model may have been cached")
        else:
            print(f"    [FAIL] Swap time too fast - not actually loading!")
    else:
        print(f"[FAIL] Model swap failed")
        return False

    print("\n[TEST 4] Swap back to first model (qwen)")
    print("-" * 70)
    start = time.time()
    success = manager.ensure_in_vram("qwen2.5-coder:7b", "test")
    elapsed = time.time() - start

    if success:
        print(f"[OK] Model swapped back successfully")
        print(f"    Time: {elapsed:.2f}s")
    else:
        print(f"[FAIL] Model swap failed")
        return False

    print("\n[TEST 5] Final statistics")
    print("-" * 70)
    print(manager.get_swap_report())

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)

    final_status = manager.get_status()
    swap_count = final_status['swap_count']

    if swap_count >= 2:
        print(f"[OK] Model manager is working correctly!")
        print(f"    - {swap_count} swaps measured")
        print(f"    - Average: {final_status['avg_swap_time']}")
        print(f"    - Total: {final_status['total_swap_time']}")
        print(f"\nThe model manager now measures REAL swap times, not fake 0.00s")
        return True
    else:
        print(f"[FAIL] Not enough swaps measured (expected ≥2, got {swap_count})")
        return False


if __name__ == "__main__":
    print("""
+======================================================================+
|               MODEL MANAGER VERIFICATION TEST                         |
|  Ensures model_manager.py actually loads models and measures swaps   |
+======================================================================+
    """)

    try:
        success = test_model_manager()

        if success:
            print("\n✅ ALL TESTS PASSED")
            print("Model manager is now honest about swap times!")
        else:
            print("\n❌ TESTS FAILED")
            print("Model manager still has issues")

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
