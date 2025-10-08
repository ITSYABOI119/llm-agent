#!/usr/bin/env python3
"""
Comprehensive Test Suite for LLM Agent
Tests all tools and components to ensure everything is working
"""

import sys
import yaml
from pathlib import Path

# Import all tools
try:
    from tools.filesystem import FileSystemTools
    from tools.commands import CommandTools
    from tools.system import SystemTools
    from tools.search import SearchTools
    from tools.process import ProcessTools
    from tools.network import NetworkTools
    from tools.data import DataTools
    from tools.memory import MemorySystem
    from tools.session_history import SessionHistory
    from safety.sandbox import Sandbox
    from safety.validators import Validator
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

        # Load config
        with open('config.yaml', 'r') as f:
            self.config = yaml.safe_load(f)

        # Override config to use test log file
        self.config['logging']['log_file'] = 'logs/test_agent.log'

        # Reconfigure Python's logging to use test file
        import logging
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['log_file']),
                logging.StreamHandler()
            ]
        )

        # Initialize tools
        self.fs_tools = FileSystemTools(self.config)
        self.cmd_tools = CommandTools(self.config)
        self.sys_tools = SystemTools(self.config)
        self.search_tools = SearchTools(self.config)
        self.process_tools = ProcessTools(self.config)
        self.network_tools = NetworkTools(self.config)
        self.data_tools = DataTools(self.config)
        self.memory = MemorySystem(self.config)
        self.history = SessionHistory(self.config)
        self.sandbox = Sandbox(self.config)
        self.validator = Validator(self.config)

        # Ensure test workspace exists
        self.test_dir = Path(self.config['agent']['workspace']) / 'test_data'
        self.test_dir.mkdir(parents=True, exist_ok=True)
    
    def test(self, name, func):
        """Run a test and track results"""
        try:
            result = func()
            if result:
                print(f"  ✓ {name}")
                self.passed += 1
                self.tests.append((name, True, None))
            else:
                print(f"  ✗ {name}: Test returned False")
                self.failed += 1
                self.tests.append((name, False, "Returned False"))
        except Exception as e:
            print(f"  ✗ {name}: {str(e)}")
            self.failed += 1
            self.tests.append((name, False, str(e)))
    
    def test_filesystem_tools(self):
        """Test file system operations"""
        print("\n=== Testing FileSystem Tools ===")
        
        def test_create_folder():
            result = self.fs_tools.create_folder("test_data/test_folder")
            return result.get("success", False)
        
        def test_write_file():
            result = self.fs_tools.write_file("test_data/test.txt", "Hello World")
            return result.get("success", False)
        
        def test_read_file():
            result = self.fs_tools.read_file("test_data/test.txt")
            return result.get("success", False) and result.get("content") == "Hello World"
        
        def test_list_directory():
            result = self.fs_tools.list_directory("test_data")
            return result.get("success", False) and result.get("count", 0) > 0
        
        def test_delete_file():
            result = self.fs_tools.delete_file("test_data/test.txt")
            return result.get("success", False)
        
        def test_path_safety():
            # Should fail - path outside workspace
            result = self.fs_tools.create_folder("../../etc")
            return not result.get("success", True)
        
        self.test("Create folder", test_create_folder)
        self.test("Write file", test_write_file)
        self.test("Read file", test_read_file)
        self.test("List directory", test_list_directory)
        self.test("Delete file", test_delete_file)
        self.test("Path safety check", test_path_safety)
    
    def test_command_tools(self):
        """Test command execution"""
        print("\n=== Testing Command Tools ===")
        
        def test_allowed_command():
            result = self.cmd_tools.run_command("echo test")
            return result.get("success", False)
        
        def test_command_output():
            result = self.cmd_tools.run_command("pwd")
            return result.get("success", False) and "stdout" in result
        
        def test_blocked_command():
            # Should fail - not in whitelist
            result = self.cmd_tools.run_command("rm -rf /")
            return not result.get("success", True)
        
        def test_empty_command():
            result = self.cmd_tools.run_command("")
            return not result.get("success", True)
        
        self.test("Execute allowed command", test_allowed_command)
        self.test("Command output capture", test_command_output)
        self.test("Block dangerous command", test_blocked_command)
        self.test("Reject empty command", test_empty_command)
    
    def test_system_tools(self):
        """Test system information gathering"""
        print("\n=== Testing System Tools ===")
        
        def test_system_info():
            result = self.sys_tools.get_system_info()
            required_keys = ["success", "hostname", "platform", "cpu_count"]
            return all(key in result for key in required_keys)
        
        def test_memory_info():
            result = self.sys_tools.get_system_info()
            return "memory_total" in result or "memory_total_mb" in result
        
        def test_disk_info():
            result = self.sys_tools.get_system_info()
            return result.get("success", False)
        
        self.test("Get system info", test_system_info)
        self.test("Get memory info", test_memory_info)
        self.test("Get disk info", test_disk_info)
    
    def test_search_tools(self):
        """Test file search and grep"""
        print("\n=== Testing Search Tools ===")
        
        # Setup test files
        self.fs_tools.write_file("test_data/file1.py", "def hello():\n    print('hello')")
        self.fs_tools.write_file("test_data/file2.txt", "This is a test file")
        
        def test_find_files():
            result = self.search_tools.find_files("*.py", "test_data")
            return result.get("success", False) and result.get("count", 0) > 0
        
        def test_find_all_files():
            result = self.search_tools.find_files("*", "test_data")
            return result.get("success", False)
        
        def test_grep_content():
            result = self.search_tools.grep_content("hello", "test_data", "*.py")
            return result.get("success", False)
        
        def test_grep_case_sensitive():
            result = self.search_tools.grep_content("HELLO", "test_data", "*.py", case_sensitive=True)
            return result.get("success", False) and result.get("files_with_matches", 0) == 0
        
        self.test("Find Python files", test_find_files)
        self.test("Find all files", test_find_all_files)
        self.test("Grep content", test_grep_content)
        self.test("Case-sensitive grep", test_grep_case_sensitive)
    
    def test_process_tools(self):
        """Test process management"""
        print("\n=== Testing Process Tools ===")
        
        def test_list_processes():
            result = self.process_tools.list_processes()
            return result.get("success", False) and result.get("count", 0) > 0
        
        def test_filter_processes():
            result = self.process_tools.list_processes(filter_name="python")
            return result.get("success", False)
        
        def test_check_process():
            result = self.process_tools.check_process_running("python")
            return result.get("success", False)
        
        def test_process_info():
            # Get current process PID (should always work)
            import os
            result = self.process_tools.get_process_info(os.getpid())
            return result.get("success", False)
        
        self.test("List all processes", test_list_processes)
        self.test("Filter processes", test_filter_processes)
        self.test("Check if process running", test_check_process)
        self.test("Get process info", test_process_info)
    
    def test_network_tools(self):
        """Test network operations"""
        print("\n=== Testing Network Tools ===")
        
        def test_ping_localhost():
            result = self.network_tools.ping("127.0.0.1", count=2)
            return result.get("reachable", False)
        
        def test_check_port():
            # Check SSH port on localhost (should be open)
            result = self.network_tools.check_port("127.0.0.1", 22)
            return result.get("success", False)
        
        def test_get_ip_info():
            result = self.network_tools.get_ip_info()
            return result.get("success", False)
        
        def test_http_request():
            # Simple HTTP request
            result = self.network_tools.http_request("http://httpbin.org/status/200")
            return result.get("success", False) and result.get("status_code") == 200
        
        def test_invalid_url():
            result = self.network_tools.http_request("not-a-url")
            return not result.get("success", True)
        
        self.test("Ping localhost", test_ping_localhost)
        self.test("Check port", test_check_port)
        self.test("Get IP info", test_get_ip_info)
        self.test("HTTP request", test_http_request)
        self.test("Reject invalid URL", test_invalid_url)
    
    def test_data_tools(self):
        """Test data processing"""
        print("\n=== Testing Data Tools ===")
        
        def test_write_json():
            data = {"name": "test", "value": 123}
            result = self.data_tools.write_json("test_data/test.json", data)
            return result.get("success", False)
        
        def test_parse_json():
            result = self.data_tools.parse_json(file_path="test_data/test.json")
            return result.get("success", False) and result.get("data", {}).get("name") == "test"
        
        def test_parse_json_string():
            result = self.data_tools.parse_json(json_string='{"key": "value"}')
            return result.get("success", False)
        
        def test_write_csv():
            data = [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ]
            result = self.data_tools.write_csv("test_data/test.csv", data)
            return result.get("success", False)
        
        def test_parse_csv():
            result = self.data_tools.parse_csv("test_data/test.csv")
            return result.get("success", False) and result.get("row_count", 0) == 2
        
        def test_invalid_json():
            result = self.data_tools.parse_json(json_string="not valid json")
            return not result.get("success", True)
        
        self.test("Write JSON", test_write_json)
        self.test("Parse JSON from file", test_parse_json)
        self.test("Parse JSON from string", test_parse_json_string)
        self.test("Write CSV", test_write_csv)
        self.test("Parse CSV", test_parse_csv)
        self.test("Reject invalid JSON", test_invalid_json)
    
    def test_memory_system(self):
        """Test memory system"""
        print("\n=== Testing Memory System ===")
        
        def test_store_memory():
            result = self.memory.store("test_key", "test_value", "test_category")
            return result.get("success", False)
        
        def test_retrieve_memory():
            result = self.memory.retrieve("test_key", "test_category")
            return result.get("success", False) and result.get("value") == "test_value"
        
        def test_search_memory():
            result = self.memory.search("test")
            return result.get("success", False) and result.get("count", 0) > 0
        
        def test_list_memories():
            result = self.memory.list_all()
            return result.get("success", False)
        
        def test_delete_memory():
            result = self.memory.delete("test_key", "test_category")
            return result.get("success", False)
        
        def test_memory_context():
            self.memory.store("context_test", "value", "general")
            context = self.memory.get_context_summary()
            return "context_test" in context
        
        self.test("Store memory", test_store_memory)
        self.test("Retrieve memory", test_retrieve_memory)
        self.test("Search memory", test_search_memory)
        self.test("List memories", test_list_memories)
        self.test("Delete memory", test_delete_memory)
        self.test("Get context summary", test_memory_context)
    
    def test_session_history(self):
        """Test session history"""
        print("\n=== Testing Session History ===")
        
        def test_add_message():
            self.history.add_message("user", "Test message")
            return True
        
        def test_get_recent_context():
            context = self.history.get_recent_context(5)
            return len(context) > 0
        
        def test_session_summary():
            result = self.history.get_session_summary()
            return result.get("success", False)
        
        def test_list_sessions():
            result = self.history.list_sessions()
            return result.get("success", False)
        
        def test_search_history():
            result = self.history.search_history("Test")
            return result.get("success", False)
        
        def test_context_for_llm():
            context = self.history.get_context_for_llm()
            return isinstance(context, str)
        
        self.test("Add message to history", test_add_message)
        self.test("Get recent context", test_get_recent_context)
        self.test("Get session summary", test_session_summary)
        self.test("List sessions", test_list_sessions)
        self.test("Search history", test_search_history)
        self.test("Get context for LLM", test_context_for_llm)
    
    def test_safety_tools(self):
        """Test security components"""
        print("\n=== Testing Safety Tools ===")
        
        def test_sandbox_allowed_path():
            return self.sandbox.is_path_allowed("test_data/file.txt")
        
        def test_sandbox_blocked_path():
            return not self.sandbox.is_path_allowed("../../../etc/passwd")
        
        def test_sanitize_path():
            try:
                self.sandbox.sanitize_path("valid/path")
                return True
            except:
                return False
        
        def test_dangerous_path():
            try:
                self.sandbox.sanitize_path("../dangerous")
                return False
            except ValueError:
                return True
        
        def test_validate_filename():
            return self.validator.validate_filename("valid_file.txt")
        
        def test_invalid_filename():
            try:
                self.validator.validate_filename("../etc/passwd")
                return False
            except ValueError:
                return True
        
        def test_validate_command():
            return self.validator.validate_command("echo hello")
        
        def test_dangerous_command():
            try:
                self.validator.validate_command("rm -rf /")
                return False
            except ValueError:
                return True
        
        self.test("Allow safe path", test_sandbox_allowed_path)
        self.test("Block dangerous path", test_sandbox_blocked_path)
        self.test("Sanitize valid path", test_sanitize_path)
        self.test("Reject dangerous path", test_dangerous_path)
        self.test("Validate safe filename", test_validate_filename)
        self.test("Reject dangerous filename", test_invalid_filename)
        self.test("Validate safe command", test_validate_command)
        self.test("Reject dangerous command", test_dangerous_command)
    
    def cleanup(self):
        """Clean up test files"""
        print("\n=== Cleaning Up ===")
        try:
            # Remove test files
            import shutil
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)
            
            # Clean up test memory and history files
            memory_file = Path(self.config['agent'].get('memory_file', 'logs/agent_memory.json'))
            if memory_file.exists():
                memory_file.unlink()
            
            history_file = Path(self.config['agent'].get('session_history_file', 'logs/session_history.json'))
            if history_file.exists():
                history_file.unlink()
            
            print("  ✓ Test files cleaned up")
        except Exception as e:
            print(f"  ✗ Cleanup failed: {e}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("=" * 60)
        print("LLM Agent - Comprehensive Test Suite")
        print("=" * 60)
        
        self.test_filesystem_tools()
        self.test_command_tools()
        self.test_system_tools()
        self.test_search_tools()
        self.test_process_tools()
        self.test_network_tools()
        self.test_data_tools()
        self.test_memory_system()
        self.test_session_history()
        self.test_safety_tools()
        
        self.cleanup()
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        
        if self.failed > 0:
            print("\nFailed tests:")
            for name, passed, error in self.tests:
                if not passed:
                    print(f"  - {name}: {error}")
        
        return self.failed == 0


def main():
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()