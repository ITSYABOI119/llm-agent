#!/usr/bin/env python3
"""
Automated Test Runner for LLM Agent
Runs all 40 test prompts via stdin and generates comprehensive report
"""

import subprocess
import time
import json
import sys
from datetime import datetime

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# All 40 test prompts
PROMPTS = [
    "Create a function called add_numbers that takes two parameters and returns their sum",
    "Create a file called greetings.txt with the text 'Hello, World!'",
    "In the file test.py, rename the variable 'old_name' to 'new_name'",
    "Add a docstring to the hello() function explaining what it does",
    "Format the code in utils.py to follow PEP 8 style guidelines",
    "Create a Python calculator class with methods for add, subtract, multiply, and divide operations",
    "Refactor the process_data function to use list comprehension instead of for loops",
    "Add try-except blocks to all file operations in the FileReader class",
    "Write unit tests for the Calculator class using pytest",
    "Fix the IndexError in the get_item function - it's accessing list[10] when list only has 5 items",
    "Create a Flask API endpoint that accepts POST requests and returns JSON responses",
    "Add input validation to the User class to ensure email addresses are valid format",
    "Design a complete web scraper application with multi-threaded scraping, rate limiting, error recovery, data storage in SQLite, and progress tracking. Create the full architecture with all necessary files",
    "Create a complete user authentication system with user registration with password hashing, login with JWT tokens, password reset functionality, session management, and database models for users. Include all necessary files and configurations",
    "Design the architecture for a microservices-based e-commerce platform with user service, product catalog service, order processing service, payment gateway integration, and message queue for inter-service communication. Create the overall structure and key components",
    "Design and implement a recommendation engine that uses collaborative filtering, handles sparse matrices efficiently, provides real-time recommendations, and scales to millions of users. Include data structures, algorithms, and optimization strategies",
    "Create a beautiful, modern landing page for a tech startup with hero section with animated gradient background, feature cards with hover effects, responsive design for mobile/tablet/desktop, smooth scroll animations, and contact form with validation. Include HTML, CSS, and JavaScript files",
    "Create a Python function with this code: def broken_func() return 'missing colon'",
    "Edit the file /path/to/nonexistent.py and add a new function",
    "Fix this critical bug: The payment processing function is charging customers twice. The code is in payment_processor.py and involves database transactions",
    "In calculator.py, replace lines 10-15 with a new implementation that handles division by zero",
    "In main.py, insert logging statements after line 25 to track function execution",
    "In old_code.py, delete lines 50-75 which contain deprecated functions",
    "In utils.py, completely replace the function called 'parse_date' with a new implementation using datetime.strptime",
    "In server.py, make these changes: Update the handle_request function (lines 10-20), add error handling to send_response function (lines 45-50), and fix the port configuration (line 5)",
    "Find all functions that use the deprecated 'old_api' and update them to use 'new_api'",
    "Analyze all Python files in the project and create a dependency graph showing which modules import which",
    "Find all database queries that don't use parameterized statements and fix them to prevent SQL injection",
    "Create a Python module with classes and functions, ensuring all syntax is valid",
    "Write a Python script and make sure it passes all PEP 8 style checks",
    "First, create a simple hello.py file. Then, expand it into a full greeting system with multiple greeting types (formal, casual, friendly), time-based greetings (morning, afternoon, evening), internationalization support, and configuration file",
    "1. Create a data_processor.py file with a basic function. 2. Add error handling to it. 3. Refactor it to use classes. 4. Add unit tests. 5. Create documentation",
    "The file buggy_code.py has multiple issues: syntax errors, logic bugs, poor performance, and no error handling. Fix all issues and enhance it with better patterns",
    "Build a personal portfolio website with modern, eye-catching design, contact form that sends emails, project showcase with filtering, smooth animations, and responsive design",
    "Create a Python file with 50 functions, then modify functions 10, 20, 30, 40 simultaneously using diff edits",
    "Create 10 simple Python files named file1.py through file10.py, each with a unique function",
    "Refactor the entire project structure: Move all utility functions to utils/ directory, create separate modules for different concerns, update all imports, and ensure nothing breaks",
    "Design a stunning dashboard UI for a fitness app with animated progress charts, card-based layout, dark/light mode toggle, smooth transitions, and modern color scheme",
    "Create a simple browser-based Snake game with smooth animations, score tracking, increasing difficulty, responsive controls, and game over screen",
    "Create an interactive demo showing how sorting algorithms work: Visualize bubble sort, quick sort, merge sort, animate the sorting process, show comparisons and swaps, and allow speed control",
]

CATEGORIES = {
    "Simple": (0, 5), "Standard": (5, 12), "Complex": (12, 17),
    "Retry": (17, 20), "Diff": (20, 25), "Context": (25, 28),
    "Verification": (28, 30), "Integration": (30, 34),
    "Stress": (34, 37), "Creative": (37, 40),
}

# Prompts that reference non-existent files (expected to fail or report "file not found")
EXPECTED_FILE_NOT_FOUND = [3, 4, 5, 8, 10, 12, 21, 22, 23, 24, 25, 33, 37]


def run_prompt(python_path, agent_path, prompt_num, prompt_text):
    """Run single prompt via stdin"""
    print(f"\n{'='*80}\nPrompt {prompt_num}/40\n{'='*80}\n{prompt_text[:100]}...\n")

    start = time.time()
    input_text = f"{prompt_text}\nquit\n"

    try:
        result = subprocess.run(
            [python_path, agent_path],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=180
        )
        elapsed = time.time() - start

        # Check for errors (handle None values)
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        # Special case: prompts that reference non-existent files should report "file not found"
        if prompt_num in EXPECTED_FILE_NOT_FOUND:
            # Success if agent correctly reports file not found
            file_not_found = ("File not found" in stdout or "not found" in stdout.lower() or
                            "does not exist" in stdout.lower() or "doesn't exist" in stdout.lower())
            success = file_not_found
        else:
            has_error = ("Error:" in stdout or "ERROR" in stderr or
                        "Traceback" in stderr or result.returncode != 0)
            success = not has_error

        print(f"{'✅ SUCCESS' if success else '❌ FAILED'} - {elapsed:.2f}s")
        if not success and result.stderr:
            print(f"Error: {result.stderr[:200]}")

        return {
            "prompt_num": prompt_num, "prompt": prompt_text, "success": success,
            "elapsed_time": elapsed, "stdout": result.stdout, "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        print(f"⏱️  TIMEOUT - {time.time()-start:.2f}s")
        return {"prompt_num": prompt_num, "prompt": prompt_text, "success": False,
                "elapsed_time": time.time()-start, "stderr": "TIMEOUT"}
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return {"prompt_num": prompt_num, "prompt": prompt_text, "success": False,
                "elapsed_time": time.time()-start, "stderr": str(e)}


def generate_report(results, start_time, end_time):
    """Generate test report"""
    total_time = (end_time - start_time).total_seconds()
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    success_rate = (successful / total * 100) if total > 0 else 0
    avg_time = sum(r["elapsed_time"] for r in results) / total if total > 0 else 0

    # Category stats
    cat_stats = {}
    for cat_name, (start_idx, end_idx) in CATEGORIES.items():
        cat_results = [r for r in results if start_idx < r["prompt_num"] <= end_idx]
        if cat_results:
            cat_success = sum(1 for r in cat_results if r["success"])
            cat_stats[cat_name] = {
                "total": len(cat_results),
                "success": cat_success,
                "success_rate": (cat_success / len(cat_results) * 100),
                "avg_time": sum(r["elapsed_time"] for r in cat_results) / len(cat_results),
            }

    # Build report
    report = [
        "=" * 80,
        "LLM AGENT TEST REPORT",
        "=" * 80,
        f"Duration: {total_time:.2f}s ({total_time/60:.1f}min)",
        "",
        "OVERALL STATISTICS",
        "-" * 80,
        f"Total: {total} | Success: {successful} ({success_rate:.1f}%) | Failed: {failed}",
        f"Avg Time: {avg_time:.2f}s",
        "",
        "CATEGORY BREAKDOWN",
        "-" * 80,
    ]

    for cat_name, stats in cat_stats.items():
        report.append(f"{cat_name}: {stats['success']}/{stats['total']} ({stats['success_rate']:.0f}%) - {stats['avg_time']:.1f}s avg")

    failed_results = [r for r in results if not r["success"]]
    if failed_results:
        report.append("\n" + "=" * 80)
        report.append("FAILED PROMPTS")
        report.append("=" * 80)
        for r in failed_results:
            report.append(f"\n#{r['prompt_num']}: {r['prompt'][:60]}...")
            report.append(f"  Error: {r['stderr'][:150]}")
    else:
        report.append("\n🎉 All prompts passed!")

    report.append("\n" + "=" * 80)

    report_text = "\n".join(report)
    print("\n" + report_text)

    # Save files
    timestamp = start_time.strftime('%Y%m%d_%H%M%S')
    with open(f"test_report_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    with open(f"test_results_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump({"results": results, "stats": cat_stats}, f, indent=2)

    print(f"\n📄 Saved: test_report_{timestamp}.txt")
    print(f"📊 Saved: test_results_{timestamp}.json")


def clean_workspace():
    """Clean the agent workspace before tests"""
    import shutil
    import os

    workspace_path = os.path.join(os.path.dirname(__file__), "agent_workspace")
    if os.path.exists(workspace_path):
        # Remove all contents but keep the directory
        for item in os.listdir(workspace_path):
            item_path = os.path.join(workspace_path, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Warning: Could not remove {item_path}: {e}")
        print("✨ Cleaned workspace")
    else:
        os.makedirs(workspace_path)
        print("✨ Created workspace")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run LLM Agent test suite")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=40)
    parser.add_argument("--python", default="./venv/Scripts/python")
    parser.add_argument("--no-clean", action="store_true", help="Skip workspace cleanup")
    args = parser.parse_args()

    # Clean workspace unless --no-clean is specified
    if not args.no_clean:
        clean_workspace()

    print(f"🚀 Testing prompts {args.start}-{args.end}")

    start_time = datetime.now()
    results = []

    for i in range(args.start - 1, args.end):
        results.append(run_prompt(args.python, "agent.py", i + 1, PROMPTS[i]))
        time.sleep(1)

    end_time = datetime.now()
    generate_report(results, start_time, end_time)


if __name__ == "__main__":
    main()
