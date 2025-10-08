#!/usr/bin/env python3
"""
Logging System Test Suite
Tests for enhanced logging features before implementation
"""

import sys
import json
import yaml
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Import the logging tools we'll create
try:
    from tools.logging_tools import LogManager, LogAnalyzer, LogQuery
    print("✓ Logging tools imports successful")
except ImportError as e:
    print(f"✗ Import failed (expected before implementation): {e}")
    sys.exit(1)


class LoggingTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        
        # Load config
        with open('config.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Create temporary test directory
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_log_file = self.test_dir / "test_agent.log"
        
        # Override config for testing
        self.test_config = self.config.copy()
        self.test_config['logging']['log_file'] = str(self.test_log_file)
        
        # Reconfigure Python's logging to use test file
        import logging
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.test_log_file),
                logging.StreamHandler()
            ]
        )
        
        # Initialize logging tools
        self.log_manager = LogManager(self.test_config)
        self.log_analyzer = LogAnalyzer(self.test_config)
        self.log_query = LogQuery(self.test_config)
    
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
    
    def test_log_manager_basics(self):
        """Test basic LogManager functionality"""
        print("\n=== Testing LogManager Basics ===")
        
        def test_log_info():
            self.log_manager.log_info("Test info message")
            return True
        
        def test_log_warning():
            self.log_manager.log_warning("Test warning message")
            return True
        
        def test_log_error():
            self.log_manager.log_error("Test error message")
            return True
        
        def test_log_debug():
            self.log_manager.log_debug("Test debug message")
            return True
        
        def test_log_exists():
            return self.test_log_file.exists()
        
        self.test("Log info message", test_log_info)
        self.test("Log warning message", test_log_warning)
        self.test("Log error message", test_log_error)
        self.test("Log debug message", test_log_debug)
        self.test("Log file created", test_log_exists)
    
    def test_structured_logging(self):
        """Test JSON structured logging"""
        print("\n=== Testing Structured Logging ===")
        
        def test_log_with_context():
            self.log_manager.log_structured(
                level="INFO",
                message="Tool executed",
                context={
                    "tool": "write_file",
                    "path": "test.txt",
                    "size": 1024
                }
            )
            return True
        
        def test_log_with_metadata():
            self.log_manager.log_structured(
                level="INFO",
                message="Agent started",
                metadata={
                    "session_id": "12345",
                    "user": "test_user"
                }
            )
            return True
        
        def test_read_structured_log():
            # Should be able to parse as JSON
            logs = self.log_manager.get_structured_logs(limit=2)
            return len(logs) >= 2 and all('level' in log for log in logs)
        
        self.test("Log with context", test_log_with_context)
        self.test("Log with metadata", test_log_with_metadata)
        self.test("Read structured logs", test_read_structured_log)
    
    def test_tool_execution_logging(self):
        """Test automatic tool execution logging with metrics"""
        print("\n=== Testing Tool Execution Logging ===")
        
        def test_log_tool_start():
            self.log_manager.log_tool_start("write_file", {"path": "test.txt"})
            return True
        
        def test_log_tool_success():
            self.log_manager.log_tool_success(
                "write_file",
                {"path": "test.txt"},
                execution_time=0.15,
                result={"success": True}
            )
            return True
        
        def test_log_tool_failure():
            self.log_manager.log_tool_failure(
                "write_file",
                {"path": "test.txt"},
                execution_time=0.05,
                error="File not found"
            )
            return True
        
        def test_get_tool_metrics():
            metrics = self.log_manager.get_tool_metrics("write_file")
            return "total_calls" in metrics and "avg_execution_time" in metrics
        
        self.test("Log tool start", test_log_tool_start)
        self.test("Log tool success", test_log_tool_success)
        self.test("Log tool failure", test_log_tool_failure)
        self.test("Get tool metrics", test_get_tool_metrics)
    
    def test_log_analyzer(self):
        """Test log analysis features"""
        print("\n=== Testing Log Analyzer ===")
        
        # Add some sample log entries
        for i in range(10):
            self.log_manager.log_info(f"Test message {i}")
        for i in range(5):
            self.log_manager.log_warning(f"Warning {i}")
        for i in range(3):
            self.log_manager.log_error(f"Error {i}")
        
        def test_count_by_level():
            counts = self.log_analyzer.count_by_level()
            return (counts.get("INFO", 0) >= 10 and 
                    counts.get("WARNING", 0) >= 5 and 
                    counts.get("ERROR", 0) >= 3)
        
        def test_get_errors():
            errors = self.log_analyzer.get_errors(limit=5)
            return len(errors) >= 3
        
        def test_get_warnings():
            warnings = self.log_analyzer.get_warnings(limit=10)
            return len(warnings) >= 5
        
        def test_get_recent_logs():
            recent = self.log_analyzer.get_recent_logs(minutes=5)
            return len(recent) >= 10
        
        def test_search_logs():
            results = self.log_analyzer.search_logs("message")
            return len(results) >= 10
        
        def test_get_statistics():
            stats = self.log_analyzer.get_statistics()
            required_keys = ["total_entries", "by_level", "time_range"]
            return all(key in stats for key in required_keys)
        
        self.test("Count logs by level", test_count_by_level)
        self.test("Get error logs", test_get_errors)
        self.test("Get warning logs", test_get_warnings)
        self.test("Get recent logs", test_get_recent_logs)
        self.test("Search logs", test_search_logs)
        self.test("Get log statistics", test_get_statistics)
    
    def test_log_query(self):
        """Test advanced log querying"""
        print("\n=== Testing Log Query ===")
        
        # Add structured logs for testing
        self.log_manager.log_structured("INFO", "Tool call", {
            "tool": "write_file",
            "success": True,
            "execution_time": 0.1
        })
        self.log_manager.log_structured("INFO", "Tool call", {
            "tool": "read_file",
            "success": False,
            "execution_time": 0.05
        })
        
        def test_query_by_tool():
            results = self.log_query.query_by_tool("write_file")
            return len(results) >= 1
        
        def test_query_by_time_range():
            now = datetime.now()
            start = now - timedelta(minutes=10)
            results = self.log_query.query_by_time_range(start, now)
            return len(results) >= 1
        
        def test_query_by_success():
            results = self.log_query.query_by_success(success=True)
            return len(results) >= 1
        
        def test_query_slow_operations():
            # Operations taking more than 0.05 seconds
            results = self.log_query.query_slow_operations(threshold=0.05)
            return len(results) >= 1
        
        def test_query_failures():
            results = self.log_query.query_failures()
            return len(results) >= 1
        
        self.test("Query by tool name", test_query_by_tool)
        self.test("Query by time range", test_query_by_time_range)
        self.test("Query by success status", test_query_by_success)
        self.test("Query slow operations", test_query_slow_operations)
        self.test("Query failures", test_query_failures)
    
    def test_log_export(self):
        """Test log export functionality"""
        print("\n=== Testing Log Export ===")
        
        def test_export_to_json():
            export_path = self.test_dir / "export.json"
            result = self.log_manager.export_logs(str(export_path), format="json")
            return result.get("success", False) and export_path.exists()
        
        def test_export_to_csv():
            export_path = self.test_dir / "export.csv"
            result = self.log_manager.export_logs(str(export_path), format="csv")
            return result.get("success", False) and export_path.exists()
        
        def test_export_filtered():
            export_path = self.test_dir / "errors.json"
            result = self.log_manager.export_logs(
                str(export_path),
                format="json",
                level="ERROR"
            )
            return result.get("success", False)
        
        self.test("Export logs to JSON", test_export_to_json)
        self.test("Export logs to CSV", test_export_to_csv)
        self.test("Export filtered logs", test_export_filtered)
    
    def test_log_rotation(self):
        """Test log rotation features"""
        print("\n=== Testing Log Rotation ===")
        
        def test_rotate_by_size():
            # Write enough to trigger rotation
            for i in range(1000):
                self.log_manager.log_info(f"Large message {i}" * 100)
            
            # Check if backup files exist
            backup_pattern = f"{self.test_log_file}.1"
            return Path(backup_pattern).exists()
        
        def test_rotate_by_date():
            result = self.log_manager.rotate_log()
            return result.get("success", False)
        
        def test_get_log_files():
            files = self.log_manager.get_log_files()
            return len(files) >= 1
        
        def test_clean_old_logs():
            result = self.log_manager.clean_old_logs(days=7)
            return result.get("success", False)
        
        self.test("Rotate by size", test_rotate_by_size)
        self.test("Rotate by date", test_rotate_by_date)
        self.test("Get log files", test_get_log_files)
        self.test("Clean old logs", test_clean_old_logs)
    
    def test_performance_metrics(self):
        """Test performance metric logging"""
        print("\n=== Testing Performance Metrics ===")
        
        def test_log_agent_stats():
            stats = {
                "uptime": 3600,
                "total_requests": 100,
                "successful_requests": 95,
                "failed_requests": 5
            }
            self.log_manager.log_performance_metrics(stats)
            return True
        
        def test_get_performance_summary():
            summary = self.log_manager.get_performance_summary()
            return "total_tool_calls" in summary
        
        def test_get_tool_usage_stats():
            stats = self.log_manager.get_tool_usage_stats()
            return isinstance(stats, dict)
        
        self.test("Log agent stats", test_log_agent_stats)
        self.test("Get performance summary", test_get_performance_summary)
        self.test("Get tool usage stats", test_get_tool_usage_stats)
    
    def cleanup(self):
        """Clean up test files"""
        print("\n=== Cleaning Up ===")
        try:
            import shutil
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)
            print("  ✓ Test files cleaned up")
        except Exception as e:
            print(f"  ✗ Cleanup failed: {e}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("=" * 60)
        print("Logging System - Comprehensive Test Suite")
        print("=" * 60)
        
        self.test_log_manager_basics()
        self.test_structured_logging()
        self.test_tool_execution_logging()
        self.test_log_analyzer()
        self.test_log_query()
        self.test_log_export()
        self.test_log_rotation()
        self.test_performance_metrics()
        
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
    runner = LoggingTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()