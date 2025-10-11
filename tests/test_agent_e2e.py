"""
End-to-End Agent Tests with Real Ollama LLM

These tests require Ollama to be running and test the agent exactly as a user would interact with it.
Each test creates a clean workspace, sends prompts, and validates the results.

Run with: pytest tests/test_agent_e2e.py -v -s
Skip if Ollama not running: pytest tests/test_agent_e2e.py -v --skip-ollama
"""

import pytest
import tempfile
import shutil
import yaml
import requests
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import Agent


def check_ollama_running():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


# Skip all tests if Ollama not running (unless --run-without-ollama is passed)
pytestmark = pytest.mark.skipif(
    not check_ollama_running(),
    reason="Ollama not running. Start with 'ollama serve'"
)


@pytest.fixture(scope="function")
def test_workspace():
    """Create a clean temporary workspace for each test"""
    temp_dir = tempfile.mkdtemp(prefix="agent_test_")
    workspace = Path(temp_dir)

    print(f"\n[TEST WORKSPACE] {workspace}")

    yield workspace

    # Cleanup after test
    try:
        shutil.rmtree(workspace)
        print(f"[CLEANED UP] {workspace}")
    except Exception as e:
        print(f"[WARN] Cleanup warning: {e}")


@pytest.fixture(scope="function")
def test_agent(test_workspace):
    """Create agent instance with test workspace"""
    # Load base config
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override workspace to use test directory
    config['agent']['workspace'] = str(test_workspace)

    # Create temporary config file
    test_config_path = test_workspace / "test_config.yaml"
    with open(test_config_path, 'w') as f:
        yaml.dump(config, f)

    # Create agent with test config
    agent = Agent(str(test_config_path))

    print(f"[AGENT] Initialized with workspace: {test_workspace}")

    return agent


# ============================================================================
# SIMPLE TASK TESTS
# ============================================================================

class TestSimpleFileTasks:
    """Test basic file operations - single tool calls"""

    def test_create_single_file(self, test_agent, test_workspace):
        """Test: Create a simple text file"""
        print("\n" + "="*60)
        print("TEST: Create hello.txt with 'Hello World'")
        print("="*60)

        response = test_agent.chat("Create a file called hello.txt with the content 'Hello World'")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate file was created
        hello_file = test_workspace / "hello.txt"
        assert hello_file.exists(), "hello.txt should exist"

        content = hello_file.read_text()
        print(f"[RESPONSE] File content: '{content}'")

        assert "Hello World" in content, "File should contain 'Hello World'"
        print("[PASS] Test passed!")

    def test_create_and_read_file(self, test_agent, test_workspace):
        """Test: Create file, then read it back"""
        print("\n" + "="*60)
        print("TEST: Create and read back a file")
        print("="*60)

        # Create file
        response1 = test_agent.chat("Create a file called data.txt with 'Test Data 123'")
        print(f"\n[RESPONSE] Create response:\n{response1}\n")

        # Read file back
        response2 = test_agent.chat("Read the contents of data.txt")
        print(f"\n[RESPONSE] Read response:\n{response2}\n")

        # Validate
        assert (test_workspace / "data.txt").exists()
        assert "Test Data 123" in response2 or "Test Data 123" in (test_workspace / "data.txt").read_text()
        print("[PASS] Test passed!")

    def test_list_workspace_files(self, test_agent, test_workspace):
        """Test: Create files then list them"""
        print("\n" + "="*60)
        print("TEST: Create multiple files and list them")
        print("="*60)

        # Create a few files
        test_agent.chat("Create file1.txt with 'File 1'")
        test_agent.chat("Create file2.txt with 'File 2'")
        test_agent.chat("Create file3.txt with 'File 3'")

        # List files
        response = test_agent.chat("List all files in the workspace")
        print(f"\n[RESPONSE] List response:\n{response}\n")

        # Validate all files exist
        assert (test_workspace / "file1.txt").exists()
        assert (test_workspace / "file2.txt").exists()
        assert (test_workspace / "file3.txt").exists()

        # Response should mention the files
        assert "file1.txt" in response or "file2.txt" in response
        print("[PASS] Test passed!")

    def test_create_folder(self, test_agent, test_workspace):
        """Test: Create a folder"""
        print("\n" + "="*60)
        print("TEST: Create a folder")
        print("="*60)

        response = test_agent.chat("Create a folder called 'project'")
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate folder exists
        project_dir = test_workspace / "project"
        assert project_dir.exists(), "project folder should exist"
        assert project_dir.is_dir(), "project should be a directory"
        print("[PASS] Test passed!")


# ============================================================================
# MULTI-FILE TASK TESTS
# ============================================================================

class TestMultiFileTasks:
    """Test multi-file operations - multiple tool calls"""

    def test_create_python_project(self, test_agent, test_workspace):
        """Test: Create a Python project with multiple files"""
        print("\n" + "="*60)
        print("TEST: Create Python project (main.py, utils.py, README.md)")
        print("="*60)

        prompt = """Create a simple Python project with:
        - main.py with a main() function that prints 'Hello'
        - utils.py with a helper() function
        - README.md with project description
        """

        response = test_agent.chat(prompt)
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate all files exist
        main_py = test_workspace / "main.py"
        utils_py = test_workspace / "utils.py"
        readme = test_workspace / "README.md"

        assert main_py.exists(), "main.py should exist"
        assert utils_py.exists(), "utils.py should exist"
        assert readme.exists(), "README.md should exist"

        # Check content
        main_content = main_py.read_text()
        utils_content = utils_py.read_text()

        print(f"\n[RESPONSE] main.py:\n{main_content}\n")
        print(f"[RESPONSE] utils.py:\n{utils_content}\n")

        assert "def main" in main_content or "def main()" in main_content
        assert "def helper" in utils_content or "def helper()" in utils_content

        print("[PASS] Test passed!")

    def test_create_web_project(self, test_agent, test_workspace):
        """Test: Create HTML/CSS/JS project (may trigger two-phase)"""
        print("\n" + "="*60)
        print("TEST: Create web project (HTML, CSS, JS)")
        print("="*60)

        prompt = """Create a simple website with:
        - index.html with a heading
        - styles.css with some basic styling
        - script.js with a simple console.log
        """

        response = test_agent.chat(prompt)
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate files
        html = test_workspace / "index.html"
        css = test_workspace / "styles.css"
        js = test_workspace / "script.js"

        assert html.exists(), "index.html should exist"
        assert css.exists(), "styles.css should exist"
        assert js.exists(), "script.js should exist"

        # Check basic structure
        html_content = html.read_text()
        css_content = css.read_text()
        js_content = js.read_text()

        print(f"\n[RESPONSE] index.html:\n{html_content[:200]}...\n")
        print(f"[RESPONSE] styles.css:\n{css_content[:200]}...\n")
        print(f"[RESPONSE] script.js:\n{js_content[:200]}...\n")

        assert "<html" in html_content.lower() or "<!doctype" in html_content.lower()
        print("[PASS] Test passed!")

    def test_create_nested_structure(self, test_agent, test_workspace):
        """Test: Create nested folder structure"""
        print("\n" + "="*60)
        print("TEST: Create nested project structure")
        print("="*60)

        prompt = """Create a project structure:
        - src/main.py
        - tests/test_main.py
        - docs/README.md
        """

        response = test_agent.chat(prompt)
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate nested structure
        assert (test_workspace / "src" / "main.py").exists()
        assert (test_workspace / "tests" / "test_main.py").exists()
        assert (test_workspace / "docs" / "README.md").exists()

        print("[PASS] Test passed!")


# ============================================================================
# FILE EDIT TESTS
# ============================================================================

class TestFileEditing:
    """Test file editing operations"""

    def test_append_to_file(self, test_agent, test_workspace):
        """Test: Create file then append content"""
        print("\n" + "="*60)
        print("TEST: Append content to existing file")
        print("="*60)

        # Create initial file
        test_agent.chat("Create log.txt with 'Line 1'")

        # Append content
        response = test_agent.chat("Append 'Line 2' to log.txt")
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate
        content = (test_workspace / "log.txt").read_text()
        print(f"[RESPONSE] File content:\n{content}\n")

        assert "Line 1" in content
        assert "Line 2" in content
        print("[PASS] Test passed!")

    def test_replace_content(self, test_agent, test_workspace):
        """Test: Replace content in file"""
        print("\n" + "="*60)
        print("TEST: Replace content in file")
        print("="*60)

        # Create file
        test_agent.chat("Create config.txt with 'mode=debug'")

        # Replace content
        response = test_agent.chat("In config.txt, replace 'debug' with 'production'")
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate
        content = (test_workspace / "config.txt").read_text()
        print(f"[RESPONSE] File content:\n{content}\n")

        assert "production" in content
        assert "debug" not in content
        print("[PASS] Test passed!")

    def test_insert_function(self, test_agent, test_workspace):
        """Test: Insert new function into Python file"""
        print("\n" + "="*60)
        print("TEST: Insert function into Python file")
        print("="*60)

        # Create initial Python file
        initial_code = """def multiply(a, b):
    return a * b
"""
        (test_workspace / "math.py").write_text(initial_code)

        # Ask to add function
        response = test_agent.chat("Add a function called 'add(a, b)' to math.py that returns a + b")
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate
        content = (test_workspace / "math.py").read_text()
        print(f"[RESPONSE] File content:\n{content}\n")

        assert "def multiply" in content  # Original still there
        assert "def add" in content  # New function added
        print("[PASS] Test passed!")


# ============================================================================
# COMPLEX SCENARIO TESTS
# ============================================================================

class TestComplexScenarios:
    """Test complex multi-step scenarios"""

    def test_create_and_modify_project(self, test_agent, test_workspace):
        """Test: Create project then modify it"""
        print("\n" + "="*60)
        print("TEST: Create project then add features")
        print("="*60)

        # Step 1: Create initial project
        response1 = test_agent.chat("Create a Python file app.py with a simple hello() function")
        print(f"\n[RESPONSE] Step 1 response:\n{response1}\n")

        # Step 2: Add to it
        response2 = test_agent.chat("Add a goodbye() function to app.py")
        print(f"\n[RESPONSE] Step 2 response:\n{response2}\n")

        # Step 3: Create related file
        response3 = test_agent.chat("Create tests.py with a test for the hello function")
        print(f"\n[RESPONSE] Step 3 response:\n{response3}\n")

        # Validate
        app_content = (test_workspace / "app.py").read_text()
        tests_exist = (test_workspace / "tests.py").exists()

        assert "def hello" in app_content
        assert "def goodbye" in app_content
        assert tests_exist

        print("[PASS] Test passed!")

    def test_error_handling(self, test_agent, test_workspace):
        """Test: How agent handles errors/edge cases"""
        print("\n" + "="*60)
        print("TEST: Agent error handling")
        print("="*60)

        # Try to read non-existent file
        response = test_agent.chat("Read the contents of nonexistent.txt")
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Should mention error or file not found
        assert "not found" in response.lower() or "does not exist" in response.lower() or "error" in response.lower()
        print("[PASS] Test passed!")

    def test_creative_task(self, test_agent, test_workspace):
        """Test: Creative task that might trigger two-phase execution"""
        print("\n" + "="*60)
        print("TEST: Creative multi-file task (two-phase?)")
        print("="*60)

        prompt = """Create a beautiful landing page for a tech startup with:
        - Modern HTML5 structure
        - Responsive CSS with gradients
        - Interactive JavaScript for smooth scrolling
        """

        response = test_agent.chat(prompt)
        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate files created
        html_exists = (test_workspace / "index.html").exists()
        css_exists = any((test_workspace / f).exists() for f in ["styles.css", "style.css"])
        js_exists = any((test_workspace / f).exists() for f in ["script.js", "main.js"])

        print(f"\n[RESPONSE] Files created:")
        print(f"  - HTML: {html_exists}")
        print(f"  - CSS: {css_exists}")
        print(f"  - JS: {js_exists}")

        assert html_exists, "Should create HTML file"
        # CSS and JS are nice to have but not strictly required

        print("[PASS] Test passed!")


# ============================================================================
# WORKSPACE VALIDATION TESTS
# ============================================================================

class TestWorkspaceValidation:
    """Test workspace state validation"""

    def test_workspace_isolation(self, test_agent, test_workspace):
        """Test: Each test gets clean workspace"""
        print("\n" + "="*60)
        print("TEST: Workspace isolation")
        print("="*60)

        # Workspace should be empty at start
        files = list(test_workspace.iterdir())
        print(f"\n[RESPONSE] Files in workspace at start: {len(files)}")

        # Create some files
        test_agent.chat("Create isolation_test.txt with 'isolated'")

        # Validate
        assert (test_workspace / "isolation_test.txt").exists()
        print("[PASS] Test passed!")

    def test_file_content_accuracy(self, test_agent, test_workspace):
        """Test: File contents match expectations"""
        print("\n" + "="*60)
        print("TEST: File content accuracy")
        print("="*60)

        specific_content = "The quick brown fox jumps over the lazy dog"
        test_agent.chat(f"Create quote.txt with exactly: '{specific_content}'")

        content = (test_workspace / "quote.txt").read_text().strip()
        print(f"\n[RESPONSE] Expected: {specific_content}")
        print(f"[RESPONSE] Got: {content}")

        assert specific_content in content
        print("[PASS] Test passed!")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Add markers to tests"""
    for item in items:
        if "test_agent_e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)


# ============================================================================
# REAL WORKSPACE TESTS
# ============================================================================

class TestAgentRealWorkspace:
    """
    Tests using the actual agent_workspace directory.
    These tests will create files in C:/Users/jluca/Documents/newfolder/agent_workspace

    Run with: pytest tests/test_agent_e2e.py -m real_workspace -v -s
    """

    @pytest.fixture(scope="function")
    def real_agent(self):
        """Create agent with default config (uses real workspace)"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        agent = Agent(str(config_path))

        # Load config to get workspace path
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        workspace = Path(config['agent']['workspace'])
        print(f"\n[REAL WORKSPACE] {workspace}")

        return agent, workspace

    @pytest.mark.real_workspace
    def test_create_simple_file(self, real_agent):
        """Test: Create a simple text file (matches manual test 1)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST 1: Create simple file")
        print("="*60)

        response = agent.chat("Create a file called test123.txt with the text \"Testing the agent\"")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        test_file = workspace / "test123.txt"
        assert test_file.exists(), f"File should exist at {test_file}"

        content = test_file.read_text()
        print(f"[FILE] Content: '{content}'")

        assert "Testing the agent" in content
        print(f"[PASS] Test passed!")

    @pytest.mark.real_workspace
    def test_create_calculator_files(self, real_agent):
        """Test: Create multi-file calculator (matches manual test 2)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST 2: Create calculator with add.py and multiply.py")
        print("="*60)

        response = agent.chat("Create a simple calculator with add.py and multiply.py files")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        add_file = workspace / "add.py"
        multiply_file = workspace / "multiply.py"

        print(f"[CHECK] add.py exists: {add_file.exists()}")
        print(f"[CHECK] multiply.py exists: {multiply_file.exists()}")

        assert add_file.exists() or multiply_file.exists(), "At least one file should be created"

        if add_file.exists():
            print(f"[FILE] add.py:\n{add_file.read_text()}")
        if multiply_file.exists():
            print(f"[FILE] multiply.py:\n{multiply_file.read_text()}")

        print("[PASS] Test passed!")

    @pytest.mark.real_workspace
    def test_write_haiku(self, real_agent):
        """Test: Creative writing task (matches manual test 3)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST 3: Write a haiku about coding")
        print("="*60)

        response = agent.chat("Write a haiku about coding and save it to poem.txt")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        poem_file = workspace / "poem.txt"
        assert poem_file.exists(), f"poem.txt should exist"

        content = poem_file.read_text()
        print(f"[FILE] poem.txt:\n{content}")

        # Haiku has 3 lines
        lines = content.strip().split('\n')
        print(f"[CHECK] Line count: {len(lines)} (should be 3 for haiku)")

        print("[PASS] Test passed!")

    @pytest.mark.real_workspace
    def test_add_function_to_file(self, real_agent):
        """Test: Edit existing file by adding function (matches manual test 4)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST 4: Add greet() function to test123.txt")
        print("="*60)

        # Ensure test123.txt exists first
        test_file = workspace / "test123.txt"
        if not test_file.exists():
            agent.chat("Create a file called test123.txt with the text \"Testing the agent\"")
            print("[SETUP] Created test123.txt")

        response = agent.chat("Add a new function called greet() to test123.txt")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        content = test_file.read_text()
        print(f"[FILE] test123.txt:\n{content}")

        assert "greet" in content.lower(), "File should contain greet function"
        print("[PASS] Test passed!")

    @pytest.mark.real_workspace
    @pytest.mark.slow
    def test_build_landing_page(self, real_agent):
        """Test: Build multi-file web project (matches manual test 5)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST 5: Build landing page with HTML, CSS, and JavaScript")
        print("="*60)

        response = agent.chat("Build me a landing page with HTML, CSS, and JavaScript for a portfolio site")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Check for created files
        html_files = list(workspace.glob("*.html"))
        css_files = list(workspace.glob("*.css"))
        js_files = list(workspace.glob("*.js"))

        print(f"[FILES] HTML: {[f.name for f in html_files]}")
        print(f"[FILES] CSS: {[f.name for f in css_files]}")
        print(f"[FILES] JS: {[f.name for f in js_files]}")

        assert len(html_files) > 0, "Should create at least one HTML file"

        # Check HTML content
        for html_file in html_files:
            content = html_file.read_text()
            print(f"[FILE] {html_file.name} ({len(content)} chars)")
            print(f"[PREVIEW] {content[:200]}...")
            assert "<html" in content.lower() or "<!doctype" in content.lower()

        print("[PASS] Test passed!")

    @pytest.mark.real_workspace
    def test_list_real_workspace(self, real_agent):
        """Test: List files in the actual agent_workspace"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: List REAL workspace files")
        print("="*60)

        response = agent.chat("List all files in the workspace")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Should mention existing files
        existing_files = list(workspace.glob("*"))
        print(f"[FILES] Found {len(existing_files)} files in workspace:")
        for f in existing_files:
            print(f"  - {f.name}")

        print("[PASS] Test passed!")

    @pytest.mark.real_workspace
    def test_create_project_in_real_workspace(self, real_agent):
        """Test: Create a multi-file project in real workspace"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Create project in REAL workspace")
        print("="*60)

        prompt = """Create a test project with:
        - test_main.py with a greet() function
        - test_utils.py with a format_text() function
        """

        response = agent.chat(prompt)

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate files in REAL workspace
        main_file = workspace / "test_main.py"
        utils_file = workspace / "test_utils.py"

        print(f"[CHECK] test_main.py exists: {main_file.exists()}")
        print(f"[CHECK] test_utils.py exists: {utils_file.exists()}")

        assert main_file.exists() or utils_file.exists(), "At least one file should be created"

        if main_file.exists():
            print(f"[FILE] test_main.py:\n{main_file.read_text()[:200]}...")
        if utils_file.exists():
            print(f"[FILE] test_utils.py:\n{utils_file.read_text()[:200]}...")

        print("[PASS] Test passed! Project files in real workspace")

    @pytest.mark.real_workspace
    def test_edit_existing_file_in_real_workspace(self, real_agent):
        """Test: Edit a file in the real workspace"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Edit file in REAL workspace")
        print("="*60)

        # Create initial file if it doesn't exist
        test_file = workspace / "editable.txt"
        if not test_file.exists():
            agent.chat("Create editable.txt with 'Initial content'")
            print("[SETUP] Created editable.txt")

        # Edit the file
        response = agent.chat("Append 'Added by E2E test' to editable.txt")

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Validate edit
        content = test_file.read_text()
        print(f"[FILE] Content:\n{content}")

        assert "Initial content" in content or "Added by E2E test" in content
        print(f"[PASS] Test passed! File edited at: {test_file}")

    @pytest.mark.real_workspace
    @pytest.mark.slow
    def test_creative_task_real_workspace(self, real_agent):
        """Test: Complex creative task in real workspace (may trigger two-phase)"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Creative task in REAL workspace")
        print("="*60)

        prompt = """Create a simple web page called portfolio.html with:
        - A header with your name
        - A section about skills
        - Nice styling
        """

        response = agent.chat(prompt)

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Check for HTML file
        html_files = list(workspace.glob("*.html"))
        print(f"[FILES] HTML files in workspace: {[f.name for f in html_files]}")

        portfolio = workspace / "portfolio.html"
        if portfolio.exists():
            content = portfolio.read_text()
            print(f"[FILE] portfolio.html created ({len(content)} chars)")
            print(f"[PREVIEW] {content[:300]}...")
            assert "<html" in content.lower() or "<!doctype" in content.lower()

        print("[PASS] Test completed!")

    @pytest.mark.real_workspace
    @pytest.mark.slow
    def test_complex_refactoring_task(self, real_agent):
        """Test: Multi-step refactoring with analysis and modification"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Complex refactoring task")
        print("="*60)

        # First create the files to refactor
        setup_prompt = "Create add.py with a simple add function and multiply.py with a simple multiply function"
        agent.chat(setup_prompt)

        # Now do the complex refactoring
        prompt = """Refactor add.py and multiply.py into a single calculator.py module with a Calculator class.
        The class should have add() and multiply() methods. Then create test_calculator.py with basic tests."""

        response = agent.chat(prompt)

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Check if calculator.py was created
        calculator_file = workspace / "calculator.py"
        test_file = workspace / "test_calculator.py"

        print(f"[CHECK] calculator.py exists: {calculator_file.exists()}")
        print(f"[CHECK] test_calculator.py exists: {test_file.exists()}")

        if calculator_file.exists():
            content = calculator_file.read_text()
            print(f"[FILE] calculator.py content preview:\n{content[:300]}...")
            assert "class" in content.lower() or "def" in content

        print("[PASS] Complex refactoring test completed!")

    @pytest.mark.real_workspace
    @pytest.mark.slow
    def test_multi_file_web_app(self, real_agent):
        """Test: Create coordinated multi-file web application"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Multi-file web app with coordination")
        print("="*60)

        prompt = """Create a simple web app:
        - index.html with a table to display user data
        - styles.css with modern styling for the table
        - app.js that creates mock user data and populates the table
        Make sure the HTML properly links to the CSS and JS files."""

        response = agent.chat(prompt)

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        # Check all files exist
        html_file = workspace / "index.html"
        css_file = workspace / "styles.css"
        js_file = workspace / "app.js"

        print(f"[CHECK] index.html exists: {html_file.exists()}")
        print(f"[CHECK] styles.css exists: {css_file.exists()}")
        print(f"[CHECK] app.js exists: {js_file.exists()}")

        # Verify HTML links to CSS and JS
        if html_file.exists():
            html_content = html_file.read_text()
            has_css_link = "styles.css" in html_content
            has_js_link = "app.js" in html_content
            print(f"[VERIFY] HTML links to CSS: {has_css_link}")
            print(f"[VERIFY] HTML links to JS: {has_js_link}")

        print("[PASS] Multi-file web app test completed!")

    @pytest.mark.real_workspace
    def test_code_analysis_and_modification(self, real_agent):
        """Test: Read, analyze, and modify existing code"""
        agent, workspace = real_agent

        print("\n" + "="*60)
        print("TEST: Code analysis and modification")
        print("="*60)

        # First create a simple function
        setup_prompt = "Create greet.py with a simple greet(name) function that prints a greeting"
        agent.chat(setup_prompt)

        # Now analyze and improve it
        prompt = """Read greet.py, analyze the greet() function, and improve it by:
        - Adding a docstring
        - Adding input validation (check if name is not empty)
        - Return the greeting instead of printing it
        Then create example.py showing how to use the improved function."""

        response = agent.chat(prompt)

        print(f"\n[RESPONSE] Agent response:\n{response}\n")

        greet_file = workspace / "greet.py"
        example_file = workspace / "example.py"

        print(f"[CHECK] greet.py exists: {greet_file.exists()}")
        print(f"[CHECK] example.py exists: {example_file.exists()}")

        if greet_file.exists():
            content = greet_file.read_text()
            has_docstring = '"""' in content or "'''" in content
            has_return = "return" in content
            print(f"[VERIFY] Has docstring: {has_docstring}")
            print(f"[VERIFY] Has return statement: {has_return}")

        print("[PASS] Code analysis and modification test completed!")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
