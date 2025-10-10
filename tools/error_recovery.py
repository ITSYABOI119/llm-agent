"""
Error Recovery System - Automatic error recovery strategies (Phase 2)

Implements recovery strategies for common error types:
- SyntaxError: Re-prompt with error context
- FileNotFound: Create missing directories
- Timeout: Retry with smaller scope
- RateLimit: Exponential backoff
- JSONParse: Fix malformed JSON
- InvalidParams: Re-prompt with schema
"""

import time
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Callable, Optional
from tools.error_classifier import ErrorClassifier


class RecoveryStrategy:
    """Base class for recovery strategies"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_retries = config.get('error_recovery', {}).get('max_retries', 3)

    def can_recover(self, error_classification: Dict) -> bool:
        """Check if this strategy can handle the error"""
        return error_classification.get('recoverable', False)

    def execute(
        self,
        error_classification: Dict,
        original_context: Dict,
        retry_callback: Callable
    ) -> Dict[str, Any]:
        """
        Execute recovery strategy

        Returns:
            {
                'success': bool,
                'result': Any,
                'attempts': int,
                'strategy_used': str
            }
        """
        raise NotImplementedError


class SyntaxErrorRecovery(RecoveryStrategy):
    """Recover from Python syntax errors by re-prompting with error details"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        error_msg = error_classification['details']['original_message']
        tool_params = original_context.get('tool_params', {})

        logging.info(f"[RECOVERY] Attempting syntax error recovery: {error_msg[:100]}")

        # Build error context for LLM
        recovery_prompt = f"""The previous code had a syntax error:

Error: {error_msg}

Original code that failed:
{tool_params.get('content', '')[:500]}

Please fix the syntax error and provide corrected code."""

        # Retry with error context
        try:
            result = retry_callback(recovery_prompt, tool_params)
            return {
                'success': True,
                'result': result,
                'attempts': 1,
                'strategy_used': 'syntax_error_reprompt'
            }
        except Exception as e:
            logging.error(f"[RECOVERY] Syntax error recovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': 1,
                'strategy_used': 'syntax_error_reprompt'
            }


class PathErrorRecovery(RecoveryStrategy):
    """Recover from file not found errors by creating missing directories"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        tool_params = original_context.get('tool_params', {})
        file_path = tool_params.get('path', '')

        logging.info(f"[RECOVERY] Attempting path recovery for: {file_path}")

        if not file_path:
            return {
                'success': False,
                'error': 'No path in context',
                'attempts': 0,
                'strategy_used': 'path_creation'
            }

        try:
            # Get workspace root
            workspace = Path(self.config['agent']['workspace'])
            full_path = workspace / file_path
            parent_dir = full_path.parent

            # Create parent directories if they don't exist
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
                logging.info(f"[RECOVERY] Created directory: {parent_dir}")

            # Retry original operation
            result = retry_callback(original_context.get('user_message', ''), tool_params)

            return {
                'success': True,
                'result': result,
                'attempts': 1,
                'strategy_used': 'path_creation',
                'created_path': str(parent_dir)
            }

        except Exception as e:
            logging.error(f"[RECOVERY] Path recovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': 1,
                'strategy_used': 'path_creation'
            }


class TimeoutRecovery(RecoveryStrategy):
    """Recover from timeouts by retrying with reduced scope"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        user_message = original_context.get('user_message', '')

        logging.info("[RECOVERY] Attempting timeout recovery with reduced scope")

        # Simplify the request
        simplified_prompt = f"""The previous request timed out. Let's simplify:

Original request: {user_message}

Please complete this task with a simpler, more focused approach. Break into smaller steps if needed."""

        try:
            result = retry_callback(simplified_prompt, original_context.get('tool_params', {}))
            return {
                'success': True,
                'result': result,
                'attempts': 1,
                'strategy_used': 'timeout_simplification'
            }
        except Exception as e:
            logging.error(f"[RECOVERY] Timeout recovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': 1,
                'strategy_used': 'timeout_simplification'
            }


class RateLimitRecovery(RecoveryStrategy):
    """Recover from rate limiting with exponential backoff"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        logging.info("[RECOVERY] Attempting rate limit recovery with backoff")

        backoff_times = [1, 2, 5, 10]  # seconds
        max_attempts = min(len(backoff_times), self.max_retries)

        for attempt in range(max_attempts):
            wait_time = backoff_times[attempt]
            logging.info(f"[RECOVERY] Waiting {wait_time}s before retry {attempt + 1}/{max_attempts}")
            time.sleep(wait_time)

            try:
                result = retry_callback(
                    original_context.get('user_message', ''),
                    original_context.get('tool_params', {})
                )
                return {
                    'success': True,
                    'result': result,
                    'attempts': attempt + 1,
                    'strategy_used': 'exponential_backoff'
                }
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"[RECOVERY] Rate limit recovery failed after {max_attempts} attempts")
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': max_attempts,
                        'strategy_used': 'exponential_backoff'
                    }
                continue


class JSONParseRecovery(RecoveryStrategy):
    """Recover from JSON parse errors by fixing common issues"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        error_msg = error_classification['details']['original_message']

        logging.info(f"[RECOVERY] Attempting JSON parse recovery: {error_msg[:100]}")

        recovery_prompt = f"""The previous response had invalid JSON:

Error: {error_msg}

Please provide valid JSON parameters in the correct format:
TOOL: tool_name | PARAMS: {{"param": "value"}}

Ensure:
- Use double quotes for strings
- Escape special characters
- Use \\n for newlines, not literal newlines
- Valid JSON structure"""

        try:
            result = retry_callback(recovery_prompt, original_context.get('tool_params', {}))
            return {
                'success': True,
                'result': result,
                'attempts': 1,
                'strategy_used': 'json_fix_reprompt'
            }
        except Exception as e:
            logging.error(f"[RECOVERY] JSON parse recovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': 1,
                'strategy_used': 'json_fix_reprompt'
            }


class InvalidParamsRecovery(RecoveryStrategy):
    """Recover from invalid parameters by re-prompting with schema"""

    def execute(self, error_classification: Dict, original_context: Dict, retry_callback: Callable) -> Dict:
        error_msg = error_classification['details']['original_message']
        tool_name = original_context.get('tool_name', 'unknown')

        logging.info(f"[RECOVERY] Attempting invalid params recovery for tool: {tool_name}")

        recovery_prompt = f"""The previous tool call had invalid parameters:

Tool: {tool_name}
Error: {error_msg}

Please provide the correct parameters for this tool. Check the tool description for required parameters."""

        try:
            result = retry_callback(recovery_prompt, original_context.get('tool_params', {}))
            return {
                'success': True,
                'result': result,
                'attempts': 1,
                'strategy_used': 'invalid_params_reprompt'
            }
        except Exception as e:
            logging.error(f"[RECOVERY] Invalid params recovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': 1,
                'strategy_used': 'invalid_params_reprompt'
            }


class ErrorRecoveryExecutor:
    """Main executor for error recovery strategies"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.classifier = ErrorClassifier()

        # Initialize recovery strategies
        self.strategies = {
            'syntax_error': SyntaxErrorRecovery(config),
            'file_not_found': PathErrorRecovery(config),
            'timeout': TimeoutRecovery(config),
            'rate_limit': RateLimitRecovery(config),
            'json_parse_error': JSONParseRecovery(config),
            'invalid_params': InvalidParamsRecovery(config)
        }

        # Track recovery attempts
        self.recovery_history = []

    def attempt_recovery(
        self,
        error: Exception,
        context: Dict[str, Any],
        retry_callback: Callable
    ) -> Dict[str, Any]:
        """
        Attempt to recover from an error

        Args:
            error: The exception that occurred
            context: Context dict with user_message, tool_name, tool_params, etc.
            retry_callback: Function to retry the operation

        Returns:
            {
                'recovered': bool,
                'result': Any,
                'classification': dict,
                'recovery_details': dict
            }
        """
        # Classify the error
        classification = self.classifier.classify_error(
            error_message=str(error),
            error_type=type(error).__name__,
            context=context
        )

        logging.info(
            f"[RECOVERY] Error classified as: {classification['type']} "
            f"(recoverable: {classification['recoverable']})"
        )

        # Check if recoverable
        if not classification['recoverable']:
            logging.warning(f"[RECOVERY] Error not recoverable: {classification['type']}")
            return {
                'recovered': False,
                'classification': classification,
                'reason': 'not_recoverable'
            }

        # Get appropriate strategy
        error_type = classification['type']
        strategy = self.strategies.get(error_type)

        if not strategy:
            logging.warning(f"[RECOVERY] No strategy for error type: {error_type}")
            return {
                'recovered': False,
                'classification': classification,
                'reason': 'no_strategy'
            }

        # Execute recovery strategy
        logging.info(f"[RECOVERY] Executing strategy: {classification['strategy']}")
        recovery_result = strategy.execute(classification, context, retry_callback)

        # Log recovery attempt
        self.recovery_history.append({
            'error_type': error_type,
            'classification': classification,
            'recovery_result': recovery_result,
            'timestamp': time.time()
        })

        return {
            'recovered': recovery_result['success'],
            'result': recovery_result.get('result'),
            'classification': classification,
            'recovery_details': recovery_result
        }

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get statistics about recovery attempts"""
        if not self.recovery_history:
            return {
                'total_attempts': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'by_type': {}
            }

        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r['recovery_result']['success'])

        # Count by type
        by_type = {}
        for r in self.recovery_history:
            error_type = r['error_type']
            if error_type not in by_type:
                by_type[error_type] = {'attempts': 0, 'successful': 0}
            by_type[error_type]['attempts'] += 1
            if r['recovery_result']['success']:
                by_type[error_type]['successful'] += 1

        return {
            'total_attempts': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': successful / total if total > 0 else 0.0,
            'by_type': by_type
        }
