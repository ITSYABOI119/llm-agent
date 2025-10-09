"""
Comprehensive tests for SinglePhaseExecutor and TwoPhaseExecutor
Tests task execution, model handling, and callback integration
"""

import pytest
import tempfile
import shutil
import requests
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from tools.executors.single_phase import SinglePhaseExecutor
from tools.executors.two_phase import TwoPhaseExecutor


@pytest.fixture
def temp_workspace():
    """Create temporary workspace"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    """Create test configuration"""
    return {
        'ollama': {
            'host': 'localhost',
            'port': 11435,
            'num_ctx': 8192,
            'num_predict': 2048,
            'temperature': 0.7,
            'top_p': 0.9
        },
        'agent': {
            'workspace': str(temp_workspace),
            'name': 'TestAgent'
        }
    }


@pytest.fixture
def single_executor(config):
    """Create SinglePhaseExecutor instance"""
    return SinglePhaseExecutor(config)


@pytest.fixture
def two_phase_executor(config):
    """Create TwoPhaseExecutor instance"""
    api_url = f"http://{config['ollama']['host']}:{config['ollama']['port']}"
    return TwoPhaseExecutor(api_url, config)


@pytest.fixture
def mock_callbacks():
    """Create mock callback functions"""
    return {
        'parse': Mock(return_value=[]),
        'execute': Mock(return_value={'success': True}),
        'history': Mock()
    }


class TestSinglePhaseExecutor:
    """Test SinglePhaseExecutor functionality"""

    def test_initialization(self, single_executor, config, temp_workspace):
        """Test executor initializes correctly"""
        assert single_executor.config == config
        assert single_executor.api_url == f"http://localhost:11435"
        assert single_executor.workspace == temp_workspace

    def test_is_reasoning_model_detection(self, single_executor):
        """Test reasoning model detection"""
        assert single_executor._is_reasoning_model('openthinker3-7b') is True
        assert single_executor._is_reasoning_model('deepseek-r1:14b') is True
        assert single_executor._is_reasoning_model('qwen2.5-coder:7b') is False
        assert single_executor._is_reasoning_model('llama2') is False

    @patch('requests.post')
    def test_execute_with_mock_llm(self, mock_post, single_executor, mock_callbacks):
        """Test execution with mocked LLM response"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Here is the result',
            'done': True
        }
        mock_post.return_value = mock_response

        result = single_executor.execute(
            user_message="Create test.txt",
            selected_model="qwen2.5-coder:7b",
            session_context="",
            agent_rules=None,
            tools_description="write_file: Create files",
            parse_callback=mock_callbacks['parse'],
            execute_callback=mock_callbacks['execute'],
            history_callback=mock_callbacks['history']
        )

        assert isinstance(result, str)
        assert mock_post.called
        # Verify API was called
        call_args = mock_post.call_args
        assert 'localhost:11435' in call_args[0][0]

    def test_build_system_prompt(self, single_executor):
        """Test system prompt building"""
        result = single_executor.execute(
            user_message="Test",
            selected_model="qwen2.5-coder:7b",
            session_context="Files: test.txt",
            agent_rules="Use Python 3.12",
            tools_description="Available: write_file",
            parse_callback=Mock(return_value=[]),
            execute_callback=Mock(return_value={'success': True}),
            history_callback=Mock()
        )
        # Just verify no exceptions

    @patch('requests.post')
    def test_execute_with_tool_calls(self, mock_post, single_executor):
        """Test execution that triggers tool calls"""
        # Mock LLM response with tool calls
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'TOOL: write_file | PARAMS: {"path": "test.txt", "content": "hello"}',
            'done': True
        }
        mock_post.return_value = mock_response

        # Mock parse callback to return tool calls
        parse_mock = Mock(return_value=[
            {'tool': 'write_file', 'params': {'path': 'test.txt', 'content': 'hello'}}
        ])
        execute_mock = Mock(return_value={'success': True, 'message': 'File created'})
        history_mock = Mock()

        result = single_executor.execute(
            user_message="Create test.txt with hello",
            selected_model="qwen2.5-coder:7b",
            session_context="",
            agent_rules=None,
            tools_description="write_file: Create files",
            parse_callback=parse_mock,
            execute_callback=execute_mock,
            history_callback=history_mock
        )

        assert parse_mock.called
        assert execute_mock.called

    @patch('requests.post')
    def test_execute_with_reasoning_model(self, mock_post, single_executor):
        """Test execution with reasoning model includes special instructions"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '<think>Planning...</think>\nTOOL: write_file | PARAMS: {}',
            'done': True
        }
        mock_post.return_value = mock_response

        result = single_executor.execute(
            user_message="Create file",
            selected_model="openthinker3-7b",
            session_context="",
            agent_rules=None,
            tools_description="write_file",
            parse_callback=Mock(return_value=[]),
            execute_callback=Mock(return_value={'success': True}),
            history_callback=Mock()
        )

        # Verify request included reasoning instructions
        call_args = mock_post.call_args
        request_data = call_args[1]['json']
        assert 'REASONING MODEL' in request_data['prompt'] or 'think' in request_data['prompt'].lower()

    @patch('requests.post')
    def test_execute_handles_llm_error(self, mock_post, single_executor):
        """Test execution handles LLM API errors gracefully"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        result = single_executor.execute(
            user_message="Test",
            selected_model="qwen2.5-coder:7b",
            session_context="",
            agent_rules=None,
            tools_description="tools",
            parse_callback=Mock(return_value=[]),
            execute_callback=Mock(return_value={'success': True}),
            history_callback=Mock()
        )

        assert 'error' in result.lower() or 'failed' in result.lower()

    def test_max_iterations_limit(self, single_executor):
        """Test executor respects max iteration limit"""
        # Mock parse to always return tool calls (would create infinite loop)
        parse_mock = Mock(return_value=[{'tool': 'test', 'params': {}}])
        execute_mock = Mock(return_value={'success': True})

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'response': 'TOOL: test | PARAMS: {}',
                'done': True
            }
            mock_post.return_value = mock_response

            result = single_executor.execute(
                user_message="Test",
                selected_model="qwen2.5-coder:7b",
                session_context="",
                agent_rules=None,
                tools_description="test",
                parse_callback=parse_mock,
                execute_callback=execute_mock,
                history_callback=Mock()
            )

            # Should eventually stop (max 10 iterations)
            assert parse_mock.call_count <= 10


class TestTwoPhaseExecutor:
    """Test TwoPhaseExecutor functionality"""

    def test_initialization(self, two_phase_executor, config):
        """Test two-phase executor initializes correctly"""
        assert two_phase_executor.config == config
        assert 'localhost:11435' in two_phase_executor.api_url

    @patch('requests.post')
    def test_planning_phase(self, mock_post, two_phase_executor):
        """Test planning phase execution"""
        # Mock planning response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Plan: 1. Create file 2. Write content 3. Save',
            'done': True
        }
        mock_post.return_value = mock_response

        plan_result = two_phase_executor._planning_phase(
            "Create a config file",
            "openthinker3-7b"
        )

        assert plan_result['success'] is True
        assert 'plan' in plan_result
        assert len(plan_result['plan']) > 0

    @patch('requests.post')
    def test_execution_phase(self, mock_post, two_phase_executor):
        """Test execution phase"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'TOOL: write_file | PARAMS: {"path": "config.yaml"}',
            'done': True
        }
        mock_post.return_value = mock_response

        parse_mock = Mock(return_value=[{'tool': 'write_file', 'params': {'path': 'config.yaml'}}])
        execute_mock = Mock(return_value={'success': True})

        exec_result = two_phase_executor._execution_phase(
            "Create config",
            "Plan: create file",
            "qwen2.5-coder:7b",
            parse_mock,
            execute_mock
        )

        assert exec_result['success'] is True
        assert execute_mock.called

    @patch('requests.post')
    def test_full_two_phase_execution(self, mock_post, two_phase_executor):
        """Test complete two-phase execution"""
        # Mock both planning and execution responses
        responses = [
            # Planning response
            Mock(status_code=200, json=Mock(return_value={
                'response': 'Plan: Create test file with content',
                'done': True
            })),
            # Execution response
            Mock(status_code=200, json=Mock(return_value={
                'response': 'TOOL: write_file | PARAMS: {"path": "test.txt"}',
                'done': True
            }))
        ]
        mock_post.side_effect = responses

        parse_mock = Mock(return_value=[{'tool': 'write_file', 'params': {'path': 'test.txt'}}])
        execute_mock = Mock(return_value={'success': True, 'message': 'Created'})

        result = two_phase_executor.execute(
            user_message="Create test.txt",
            planning_model="openthinker3-7b",
            execution_model="qwen2.5-coder:7b",
            parse_callback=parse_mock,
            execute_callback=execute_mock
        )

        assert result['success'] is True
        assert 'plan' in result
        assert 'execution_result' in result
        assert 'phases' in result
        assert 'planning' in result['phases']
        assert 'execution' in result['phases']

    @patch('requests.post')
    def test_planning_failure_stops_execution(self, mock_post, two_phase_executor):
        """Test that planning failure prevents execution phase"""
        # Mock planning failure
        mock_post.side_effect = requests.exceptions.RequestException("Planning failed")

        result = two_phase_executor.execute(
            user_message="Test",
            planning_model="openthinker3-7b",
            execution_model="qwen2.5-coder:7b",
            parse_callback=Mock(),
            execute_callback=Mock()
        )

        assert result['success'] is False
        assert 'Planning phase failed' in result.get('error', '')
        # Should not have execution phase
        assert 'execution' not in result.get('phases', {})

    @patch('requests.post')
    def test_execution_phase_uses_plan(self, mock_post, two_phase_executor):
        """Test that execution phase receives and uses the plan"""
        responses = [
            Mock(status_code=200, json=Mock(return_value={
                'response': 'Detailed plan here',
                'done': True
            })),
            Mock(status_code=200, json=Mock(return_value={
                'response': 'TOOL: write_file | PARAMS: {}',
                'done': True
            }))
        ]
        mock_post.side_effect = responses

        two_phase_executor.execute(
            user_message="Create file",
            planning_model="openthinker3-7b",
            execution_model="qwen2.5-coder:7b",
            parse_callback=Mock(return_value=[]),
            execute_callback=Mock(return_value={'success': True})
        )

        # Check that second call (execution) included the plan
        execution_call = mock_post.call_args_list[1]
        request_data = execution_call[1]['json']
        assert 'Detailed plan here' in request_data['prompt']


class TestExecutorEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_user_message(self, single_executor):
        """Test handling of empty user message"""
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={'response': 'No input', 'done': True})
            )

            result = single_executor.execute(
                user_message="",
                selected_model="qwen2.5-coder:7b",
                session_context="",
                agent_rules=None,
                tools_description="",
                parse_callback=Mock(return_value=[]),
                execute_callback=Mock(return_value={'success': True}),
                history_callback=Mock()
            )

            assert isinstance(result, str)

    def test_very_long_context(self, single_executor):
        """Test handling of very long session context"""
        long_context = "Files tracked:\n" + "\n".join([f"file_{i}.txt" for i in range(1000)])

        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={'response': 'OK', 'done': True})
            )

            result = single_executor.execute(
                user_message="Test",
                selected_model="qwen2.5-coder:7b",
                session_context=long_context,
                agent_rules=None,
                tools_description="tools",
                parse_callback=Mock(return_value=[]),
                execute_callback=Mock(return_value={'success': True}),
                history_callback=Mock()
            )

            # Should handle gracefully
            assert isinstance(result, str)

    def test_tool_execution_failure(self, single_executor):
        """Test handling when tool execution fails"""
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'response': 'TOOL: write_file | PARAMS: {}',
                    'done': True
                })
            )

            parse_mock = Mock(return_value=[{'tool': 'write_file', 'params': {}}])
            execute_mock = Mock(return_value={'success': False, 'error': 'Permission denied'})

            result = single_executor.execute(
                user_message="Write file",
                selected_model="qwen2.5-coder:7b",
                session_context="",
                agent_rules=None,
                tools_description="write_file",
                parse_callback=parse_mock,
                execute_callback=execute_mock,
                history_callback=Mock()
            )

            # Should include error info
            assert execute_mock.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
