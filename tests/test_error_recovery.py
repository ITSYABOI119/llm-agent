"""
Test suite for Phase 2 Day 2: Error Classification and Recovery

Tests:
- Error classification
- Recovery strategies
- Recovery executor
- Strategy selection
- Recovery stats
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from tools.error_classifier import ErrorClassifier
from tools.error_recovery import (
    RecoveryStrategy,
    SyntaxErrorRecovery,
    PathErrorRecovery,
    TimeoutRecovery,
    RateLimitRecovery,
    JSONParseRecovery,
    InvalidParamsRecovery,
    ErrorRecoveryExecutor
)


class TestErrorClassifier:
    """Test error classification"""

    def setup_method(self):
        """Setup for each test"""
        self.classifier = ErrorClassifier()

    def test_classify_syntax_error(self):
        """Should classify syntax errors"""
        result = self.classifier.classify_error(
            error_message="SyntaxError: invalid syntax",
            error_type="SyntaxError"
        )

        assert result['type'] == 'syntax_error'
        assert result['severity'] == 'high'
        assert result['recoverable'] is True
        assert result['strategy'] == 'rewrite_with_validation'

    def test_classify_file_not_found(self):
        """Should classify file not found errors"""
        result = self.classifier.classify_error(
            error_message="FileNotFoundError: No such file or directory: 'test.py'",
            error_type="FileNotFoundError"
        )

        assert result['type'] == 'file_not_found'
        assert result['recoverable'] is True
        assert result['strategy'] == 'verify_path_and_retry'

    def test_classify_timeout_error(self):
        """Should classify timeout errors"""
        result = self.classifier.classify_error(
            error_message="TimeoutError: Request timed out after 30 seconds"
        )

        assert result['type'] == 'timeout'
        assert result['recoverable'] is True
        assert result['strategy'] == 'retry_with_longer_timeout'

    def test_classify_rate_limit_error(self):
        """Should classify rate limit errors"""
        result = self.classifier.classify_error(
            error_message="Rate limit exceeded. Please try again later."
        )

        assert result['type'] == 'rate_limit'
        assert result['severity'] == 'low'
        assert result['recoverable'] is True
        assert result['strategy'] == 'exponential_backoff'

    def test_classify_json_parse_error(self):
        """Should classify JSON parse errors"""
        result = self.classifier.classify_error(
            error_message="JSONDecodeError: Expecting property name"
        )

        assert result['type'] == 'json_parse_error'
        assert result['recoverable'] is True

    def test_classify_permission_denied(self):
        """Should classify permission errors"""
        result = self.classifier.classify_error(
            error_message="PermissionError: [Errno 13] Permission denied"
        )

        assert result['type'] == 'permission_denied'
        assert result['severity'] == 'high'
        assert result['recoverable'] is False

    def test_classify_model_error(self):
        """Should classify model errors"""
        result = self.classifier.classify_error(
            error_message="Ollama model error: Connection refused"
        )

        assert result['type'] == 'model_error'
        assert result['recoverable'] is True

    def test_classify_unknown_error(self):
        """Should handle unknown error types"""
        result = self.classifier.classify_error(
            error_message="Some random error that doesn't match patterns"
        )

        assert result['type'] == 'unknown'
        assert result['confidence'] < 1.0

    def test_get_error_stats(self):
        """Should compute error statistics"""
        error_history = [
            {'error_type': 'syntax_error', 'error_message': 'test1'},
            {'error_type': 'syntax_error', 'error_message': 'test2'},
            {'error_type': 'file_not_found', 'error_message': 'test3'},
            {'error_type': 'timeout', 'error_message': 'test4'},
        ]

        stats = self.classifier.get_error_stats(error_history)

        assert stats['total_errors'] == 4
        assert stats['by_type']['syntax_error'] == 2
        assert stats['by_type']['file_not_found'] == 1
        assert stats['recoverable_count'] == 4  # All are recoverable


class TestSyntaxErrorRecovery:
    """Test syntax error recovery strategy"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {
            'error_recovery': {'max_retries': 3}
        }
        self.strategy = SyntaxErrorRecovery(self.config)

    def test_can_recover_syntax_error(self):
        """Should identify syntax errors as recoverable"""
        classification = {
            'type': 'syntax_error',
            'recoverable': True,
            'details': {'original_message': 'IndentationError'}
        }

        assert self.strategy.can_recover(classification)

    def test_execute_recovery(self):
        """Should attempt to recover from syntax error"""
        classification = {
            'type': 'syntax_error',
            'details': {'original_message': 'IndentationError: unexpected indent'}
        }

        context = {
            'tool_params': {'content': 'def test():\nprint("hello")'}  # Missing indent
        }

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        assert result['strategy_used'] == 'syntax_error_reprompt'
        assert retry_callback.called


class TestPathErrorRecovery:
    """Test path error recovery strategy"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {
            'error_recovery': {'max_retries': 2},
            'agent': {'workspace': 'test_workspace'}
        }
        self.strategy = PathErrorRecovery(self.config)

    def test_can_recover_path_error(self):
        """Should identify file not found as recoverable"""
        classification = {
            'type': 'file_not_found',
            'recoverable': True
        }

        assert self.strategy.can_recover(classification)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_creates_missing_directories(self, mock_mkdir, mock_exists):
        """Should create missing parent directories"""
        mock_exists.return_value = False

        classification = {'type': 'file_not_found', 'details': {}}
        context = {
            'tool_params': {'path': 'nested/folder/file.py'},
            'user_message': 'Create file'
        }

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        # Should have created parent directory
        assert mock_mkdir.called
        assert result['strategy_used'] == 'path_creation'


class TestTimeoutRecovery:
    """Test timeout recovery strategy"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {'error_recovery': {'max_retries': 2}}
        self.strategy = TimeoutRecovery(self.config)

    def test_simplifies_request(self):
        """Should simplify request on timeout"""
        classification = {'type': 'timeout', 'details': {}}
        context = {
            'user_message': 'Create a complex multi-file application',
            'tool_params': {}
        }

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        assert result['strategy_used'] == 'timeout_simplification'
        # Should have called retry with simplified prompt
        assert retry_callback.called
        call_args = retry_callback.call_args[0][0]
        assert 'simplify' in call_args.lower() or 'simpler' in call_args.lower()


class TestRateLimitRecovery:
    """Test rate limit recovery strategy"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {'error_recovery': {'max_retries': 3}}
        self.strategy = RateLimitRecovery(self.config)

    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Should use exponential backoff"""
        classification = {'type': 'rate_limit', 'details': {}}
        context = {'user_message': 'Test', 'tool_params': {}}

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        # Should have waited (mocked)
        assert mock_sleep.called
        # Should succeed on retry
        assert result['success'] is True
        assert result['strategy_used'] == 'exponential_backoff'

    @patch('time.sleep')
    def test_max_retries_respected(self, mock_sleep):
        """Should respect max retries"""
        classification = {'type': 'rate_limit', 'details': {}}
        context = {'user_message': 'Test', 'tool_params': {}}

        # Always fail
        retry_callback = Mock(side_effect=Exception("Still rate limited"))

        result = self.strategy.execute(classification, context, retry_callback)

        # Should have tried multiple times
        assert retry_callback.call_count <= 3
        assert result['success'] is False


class TestJSONParseRecovery:
    """Test JSON parse error recovery"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {'error_recovery': {'max_retries': 3}}
        self.strategy = JSONParseRecovery(self.config)

    def test_prompts_for_valid_json(self):
        """Should re-prompt with JSON formatting instructions"""
        classification = {
            'type': 'json_parse_error',
            'details': {'original_message': 'Expecting property name'}
        }
        context = {'tool_params': {}}

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        assert result['strategy_used'] == 'json_fix_reprompt'
        # Should include JSON formatting instructions
        call_args = retry_callback.call_args[0][0]
        assert 'JSON' in call_args or 'json' in call_args


class TestInvalidParamsRecovery:
    """Test invalid params recovery"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {'error_recovery': {'max_retries': 3}}
        self.strategy = InvalidParamsRecovery(self.config)

    def test_includes_tool_name_in_prompt(self):
        """Should include tool name in recovery prompt"""
        classification = {
            'type': 'invalid_params',
            'details': {'original_message': 'Missing required parameter: path'}
        }
        context = {
            'tool_name': 'write_file',
            'tool_params': {}
        }

        retry_callback = Mock(return_value={'success': True})

        result = self.strategy.execute(classification, context, retry_callback)

        # Should include tool name in prompt
        call_args = retry_callback.call_args[0][0]
        assert 'write_file' in call_args


class TestErrorRecoveryExecutor:
    """Test main recovery executor"""

    def setup_method(self):
        """Setup for each test"""
        self.config = {
            'error_recovery': {
                'max_retries': 3,
                'log_recovery_attempts': True
            },
            'agent': {'workspace': 'test_workspace'}
        }
        self.executor = ErrorRecoveryExecutor(self.config)

    def test_initialization(self):
        """Should initialize all strategies"""
        assert 'syntax_error' in self.executor.strategies
        assert 'file_not_found' in self.executor.strategies
        assert 'timeout' in self.executor.strategies
        assert 'rate_limit' in self.executor.strategies
        assert 'json_parse_error' in self.executor.strategies
        assert 'invalid_params' in self.executor.strategies

    def test_attempt_recovery_success(self):
        """Should successfully recover from error"""
        error = Exception("SyntaxError: invalid syntax")
        context = {
            'tool_params': {'content': 'bad code'},
            'user_message': 'Write file'
        }

        retry_callback = Mock(return_value={'success': True})

        result = self.executor.attempt_recovery(error, context, retry_callback)

        assert result['recovered'] is True
        assert result['classification']['type'] == 'syntax_error'

    def test_attempt_recovery_not_recoverable(self):
        """Should handle unrecoverable errors"""
        error = Exception("PermissionError: Access denied")
        context = {}
        retry_callback = Mock()

        result = self.executor.attempt_recovery(error, context, retry_callback)

        assert result['recovered'] is False
        assert result['reason'] == 'not_recoverable'

    def test_attempt_recovery_no_strategy(self):
        """Should handle errors with no strategy"""
        error = Exception("Some weird error")
        context = {}
        retry_callback = Mock()

        # Mock classifier to return type with no strategy
        with patch.object(self.executor.classifier, 'classify_error') as mock_classify:
            mock_classify.return_value = {
                'type': 'nonexistent_type',
                'recoverable': True,
                'strategy': 'nonexistent_strategy'
            }

            result = self.executor.attempt_recovery(error, context, retry_callback)

            assert result['recovered'] is False
            assert result['reason'] == 'no_strategy'

    def test_get_recovery_stats_empty(self):
        """Should return empty stats when no recoveries attempted"""
        stats = self.executor.get_recovery_stats()

        assert stats['total_attempts'] == 0
        assert stats['successful'] == 0
        assert stats['success_rate'] == 0.0

    def test_get_recovery_stats_with_attempts(self):
        """Should compute recovery statistics"""
        # Simulate recovery attempts
        self.executor.recovery_history = [
            {
                'error_type': 'syntax_error',
                'recovery_result': {'success': True}
            },
            {
                'error_type': 'syntax_error',
                'recovery_result': {'success': True}
            },
            {
                'error_type': 'file_not_found',
                'recovery_result': {'success': False}
            },
            {
                'error_type': 'timeout',
                'recovery_result': {'success': True}
            }
        ]

        stats = self.executor.get_recovery_stats()

        assert stats['total_attempts'] == 4
        assert stats['successful'] == 3
        assert stats['success_rate'] == 0.75
        assert stats['by_type']['syntax_error']['attempts'] == 2
        assert stats['by_type']['syntax_error']['successful'] == 2
        assert stats['by_type']['file_not_found']['successful'] == 0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
