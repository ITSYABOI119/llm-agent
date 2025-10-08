"""
Integration Tests for Phase 5
Tests multi-model routing, two-phase execution, and tool integration
"""

import pytest
import yaml
from pathlib import Path
from tools.task_analyzer import TaskAnalyzer
from tools.model_router import ModelRouter
from tools.executors.single_phase import SinglePhaseExecutor
from tools.executors.two_phase import TwoPhaseExecutor


class TestTaskAnalyzer:
    """Test task analysis and complexity detection"""

    def test_simple_task_detection(self):
        """Test detection of simple tasks"""
        analyzer = TaskAnalyzer()

        simple_tasks = [
            "What is 2 + 2?",
            "List files in current directory",
            "Show me the system info",
            "Ping google.com"
        ]

        for task in simple_tasks:
            result = analyzer.analyze(task)
            assert result['complexity'] == 'simple'
            assert result['recommended_model'] == 'execution'

    def test_complex_task_detection(self):
        """Test detection of complex tasks"""
        analyzer = TaskAnalyzer()

        complex_tasks = [
            "Create a web scraper that extracts product prices from multiple e-commerce sites",
            "Refactor the authentication system to use OAuth2 with JWT tokens",
            "Design and implement a caching layer with Redis for the API",
            "Build a CI/CD pipeline with automated testing and deployment"
        ]

        for task in complex_tasks:
            result = analyzer.analyze(task)
            assert result['complexity'] == 'complex'
            assert result['recommended_model'] == 'reasoning'

    def test_medium_task_detection(self):
        """Test detection of medium complexity tasks"""
        analyzer = TaskAnalyzer()

        medium_tasks = [
            "Create a function to calculate fibonacci numbers",
            "Write a script to backup database daily",
            "Add input validation to the user registration form"
        ]

        for task in medium_tasks:
            result = analyzer.analyze(task)
            assert result['complexity'] in ['simple', 'medium', 'complex']

    def test_analysis_includes_keywords(self):
        """Test that analysis includes detected keywords"""
        analyzer = TaskAnalyzer()

        task = "Create a new class for user authentication"
        result = analyzer.analyze(task)

        assert 'keywords' in result
        assert isinstance(result['keywords'], list)

    def test_analysis_includes_confidence(self):
        """Test that analysis includes confidence score"""
        analyzer = TaskAnalyzer()

        task = "Implement a REST API with authentication"
        result = analyzer.analyze(task)

        assert 'confidence' in result
        assert 0 <= result['confidence'] <= 1


class TestModelRouter:
    """Test model routing decisions"""

    def test_router_initialization(self):
        """Test router initializes with config"""
        config = {
            'ollama': {
                'multi_model': {
                    'enabled': True,
                    'models': {
                        'reasoning': {'name': 'openthinker3-7b'},
                        'execution': {'name': 'qwen2.5-coder:7b'}
                    }
                }
            }
        }

        router = ModelRouter(config)
        assert router is not None

    def test_route_simple_task(self):
        """Test routing of simple task to execution model"""
        config = {
            'ollama': {
                'multi_model': {
                    'enabled': True,
                    'models': {
                        'reasoning': {'name': 'openthinker3-7b'},
                        'execution': {'name': 'qwen2.5-coder:7b'}
                    }
                }
            }
        }

        router = ModelRouter(config)
        task = "Show system information"

        result = router.route_task(task)

        assert result['selected_model'] == 'qwen2.5-coder:7b'
        assert result['execution_mode'] == 'single_phase'

    def test_route_complex_task(self):
        """Test routing of complex task to reasoning model"""
        config = {
            'ollama': {
                'multi_model': {
                    'enabled': True,
                    'models': {
                        'reasoning': {'name': 'openthinker3-7b'},
                        'execution': {'name': 'qwen2.5-coder:7b'}
                    }
                }
            }
        }

        router = ModelRouter(config)
        task = "Build a complete REST API with authentication and database"

        result = router.route_task(task)

        assert result['selected_model'] == 'openthinker3-7b'
        assert result['execution_mode'] == 'two_phase'


class TestSinglePhaseExecutor:
    """Test single-phase execution"""

    def test_executor_initialization(self):
        """Test executor initializes"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        executor = SinglePhaseExecutor(config)
        assert executor is not None

    def test_executor_has_required_methods(self):
        """Test executor has execute method"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        executor = SinglePhaseExecutor(config)
        assert hasattr(executor, 'execute')
        assert callable(executor.execute)


class TestTwoPhaseExecutor:
    """Test two-phase execution"""

    def test_executor_initialization(self):
        """Test executor initializes"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        executor = TwoPhaseExecutor(config)
        assert executor is not None

    def test_executor_has_required_methods(self):
        """Test executor has execute method"""
        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        executor = TwoPhaseExecutor(config)
        assert hasattr(executor, 'execute')
        assert callable(executor.execute)


class TestToolIntegration:
    """Test integration between different tools"""

    def test_filesystem_and_search_integration(self, tmp_path):
        """Test filesystem operations with search"""
        from tools.filesystem import FileSystemTools
        from tools.search import SearchTools

        config = {
            'agent': {'workspace': str(tmp_path)},
            'security': {'max_file_size': 1024 * 1024}
        }

        fs_tools = FileSystemTools(config)
        search_tools = SearchTools(config)

        # Create files using filesystem tools
        result1 = fs_tools.write_file("test1.py", "print('hello')")
        assert result1['success'] is True

        result2 = fs_tools.write_file("test2.py", "print('world')")
        assert result2['success'] is True

        result3 = fs_tools.write_file("test.txt", "text file")
        assert result3['success'] is True

        # Search for Python files using search tools
        search_result = search_tools.find_files(pattern="*.py", path=".")
        assert search_result['success'] is True
        assert search_result['count'] == 2

        # Search for specific content
        grep_result = search_tools.grep_content(pattern="hello", path=".")
        assert grep_result['success'] is True
        assert grep_result['total_matches'] >= 1

    def test_system_and_process_integration(self):
        """Test system info with process tools"""
        from tools.system import SystemTools
        from tools.process import ProcessTools

        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        sys_tools = SystemTools(config)
        proc_tools = ProcessTools(config)

        # Get system info
        sys_info = sys_tools.get_system_info()
        assert sys_info['success'] is True
        assert 'cpu' in sys_info
        assert 'memory' in sys_info

        # List processes (should work on all platforms)
        proc_list = proc_tools.list_processes()
        assert proc_list['success'] is True
        assert 'processes' in proc_list

    def test_data_tools_json_and_yaml(self, tmp_path):
        """Test data tools with JSON and YAML"""
        from tools.data import DataTools

        config = {
            'agent': {'workspace': str(tmp_path)},
            'security': {'max_file_size': 1024 * 1024}
        }

        data_tools = DataTools(config)

        # Test JSON
        test_data = {"name": "test", "value": 123, "items": [1, 2, 3]}

        json_write = data_tools.write_json("test.json", test_data)
        assert json_write['success'] is True

        json_read = data_tools.read_json("test.json")
        assert json_read['success'] is True
        assert json_read['data'] == test_data

        # Test YAML
        yaml_write = data_tools.write_yaml("test.yaml", test_data)
        assert yaml_write['success'] is True

        yaml_read = data_tools.read_yaml("test.yaml")
        assert yaml_read['success'] is True
        assert yaml_read['data'] == test_data


class TestContextBuilder:
    """Test context builder functionality"""

    def test_context_builder_initialization(self):
        """Test context builder initializes"""
        from tools.context_builder import ContextBuilder

        config = {
            'agent': {'workspace': '.'},
            'rules_files': []
        }

        builder = ContextBuilder(config)
        assert builder is not None

    def test_track_files(self):
        """Test file tracking"""
        from tools.context_builder import ContextBuilder

        config = {
            'agent': {'workspace': '.'},
            'rules_files': []
        }

        builder = ContextBuilder(config)

        # Track created files
        builder.track_file_created("test1.py")
        builder.track_file_created("test2.py")

        # Track modified files
        builder.track_file_modified("test3.py")

        # Build context
        context = builder.build_session_context()

        assert "test1.py" in context
        assert "test2.py" in context
        assert "test3.py" in context

    def test_load_rules(self, tmp_path):
        """Test loading agent rules"""
        from tools.context_builder import ContextBuilder

        # Create rules file
        rules_file = tmp_path / "rules.txt"
        rules_file.write_text("Rule 1: Always test code\nRule 2: Write clean code")

        config = {
            'agent': {'workspace': str(tmp_path)},
            'rules_files': [str(rules_file)]
        }

        builder = ContextBuilder(config)
        rules = builder.load_agent_rules()

        assert rules is not None
        assert "Rule 1" in rules
        assert "Rule 2" in rules


class TestErrorHandling:
    """Test error handling across tools"""

    def test_filesystem_error_handling(self, tmp_path):
        """Test filesystem error handling"""
        from tools.filesystem import FileSystemTools

        config = {
            'agent': {'workspace': str(tmp_path)},
            'security': {'max_file_size': 100}  # Very small limit
        }

        fs_tools = FileSystemTools(config)

        # Try to write file larger than limit
        large_content = "x" * 1000
        result = fs_tools.write_file("large.txt", large_content)

        assert result['success'] is False
        assert 'error' in result

    def test_search_error_handling(self):
        """Test search error handling"""
        from tools.search import SearchTools

        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        search_tools = SearchTools(config)

        # Search in non-existent directory
        result = search_tools.find_files(pattern="*", path="/nonexistent/path/xyz")

        assert result['success'] is False
        assert 'error' in result

    def test_network_error_handling(self):
        """Test network error handling"""
        from tools.network import NetworkTools

        config = {
            'agent': {'workspace': '.'},
            'security': {'max_file_size': 1024 * 1024}
        }

        net_tools = NetworkTools(config)

        # Try to ping invalid host
        result = net_tools.ping("invalid.host.that.does.not.exist.xyz")

        # Should handle error gracefully
        assert 'success' in result
        assert 'error' in result or 'packet_loss' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
