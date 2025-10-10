"""
Error Classifier - Categorize and analyze errors for recovery (Phase 2)

Classifies errors into types with severity and recovery strategies:
- syntax_error: Python syntax errors in generated code
- file_not_found: Missing files or directories
- permission_denied: Filesystem permission issues
- timeout: LLM or operation timeouts
- rate_limit: API rate limiting
- model_error: Ollama/model failures
- json_parse_error: Invalid JSON in tool parameters
- invalid_params: Missing or invalid tool parameters
"""

import re
import logging
from typing import Dict, Optional, Any


class ErrorClassifier:
    """Classify errors and recommend recovery strategies"""

    # Error type patterns
    ERROR_PATTERNS = {
        'syntax_error': [
            r'SyntaxError',
            r'IndentationError',
            r'invalid syntax',
            r'unexpected EOF',
            r'AST.*failed'
        ],
        'file_not_found': [
            r'FileNotFoundError',
            r'No such file or directory',
            r'cannot find the path',
            r'does not exist'
        ],
        'permission_denied': [
            r'PermissionError',
            r'Permission denied',
            r'Access is denied',
            r'operation not permitted'
        ],
        'timeout': [
            r'TimeoutError',
            r'timed out',
            r'timeout after',
            r'Connection timeout',
            r'Read timeout'
        ],
        'rate_limit': [
            r'rate limit',
            r'too many requests',
            r'429',
            r'quota exceeded'
        ],
        'model_error': [
            r'model.*not found',
            r'Ollama.*error',
            r'model.*unavailable',
            r'failed to load model'
        ],
        'json_parse_error': [
            r'JSONDecodeError',
            r'invalid JSON',
            r'Expecting property name',
            r'Expecting value'
        ],
        'invalid_params': [
            r'missing required parameter',
            r'invalid parameter',
            r'KeyError',
            r'required.*not provided'
        ],
        'network_error': [
            r'ConnectionError',
            r'Connection refused',
            r'Network.*unreachable',
            r'Failed to establish'
        ]
    }

    # Severity levels
    SEVERITY_LEVELS = {
        'syntax_error': 'medium',
        'file_not_found': 'medium',
        'permission_denied': 'high',
        'timeout': 'medium',
        'rate_limit': 'low',
        'model_error': 'high',
        'json_parse_error': 'medium',
        'invalid_params': 'medium',
        'network_error': 'high'
    }

    # Recovery strategies
    RECOVERY_STRATEGIES = {
        'syntax_error': 'reprompt_with_error',
        'file_not_found': 'create_missing_path',
        'permission_denied': 'escalate',
        'timeout': 'retry_smaller_scope',
        'rate_limit': 'exponential_backoff',
        'model_error': 'switch_model',
        'json_parse_error': 'fix_json_format',
        'invalid_params': 'reprompt_with_schema',
        'network_error': 'retry_with_backoff'
    }

    def classify_error(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify an error and recommend recovery strategy

        Args:
            error_message: The error message text
            error_type: Exception type name (e.g., 'SyntaxError')
            context: Additional context (tool_name, params, etc.)

        Returns:
            {
                'type': str,           # Error category
                'severity': str,       # low, medium, high
                'recoverable': bool,   # Can auto-recover?
                'strategy': str,       # Recovery strategy name
                'confidence': float,   # 0.0-1.0
                'details': dict        # Additional info
            }
        """
        # Combine error_type and message for matching
        search_text = f"{error_type or ''} {error_message}".lower()

        # Try to match error patterns
        matched_type = self._match_error_type(search_text)

        # Determine severity
        severity = self.SEVERITY_LEVELS.get(matched_type, 'medium')

        # Determine if recoverable
        recoverable = self._is_recoverable(matched_type, severity)

        # Get recovery strategy
        strategy = self.RECOVERY_STRATEGIES.get(matched_type, 'escalate')

        # Calculate confidence (how sure we are about classification)
        confidence = self._calculate_confidence(matched_type, error_type, error_message)

        # Build result
        result = {
            'type': matched_type,
            'severity': severity,
            'recoverable': recoverable,
            'strategy': strategy,
            'confidence': confidence,
            'details': {
                'original_error_type': error_type,
                'original_message': error_message[:200],  # Truncate
                'context': context or {}
            }
        }

        logging.info(
            f"Error classified: type={matched_type}, severity={severity}, "
            f"recoverable={recoverable}, strategy={strategy}"
        )

        return result

    def _match_error_type(self, search_text: str) -> str:
        """Match error text against known patterns"""
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, search_text, re.IGNORECASE):
                    return error_type

        # Default to unknown
        return 'unknown'

    def _is_recoverable(self, error_type: str, severity: str) -> bool:
        """Determine if error is automatically recoverable"""
        # High severity errors are not auto-recoverable
        if severity == 'high':
            return False

        # Unknown errors are not recoverable
        if error_type == 'unknown':
            return False

        # These types are recoverable
        recoverable_types = [
            'syntax_error',
            'file_not_found',
            'timeout',
            'rate_limit',
            'json_parse_error',
            'invalid_params'
        ]

        return error_type in recoverable_types

    def _calculate_confidence(
        self,
        matched_type: str,
        error_type: Optional[str],
        error_message: str
    ) -> float:
        """Calculate confidence score for classification"""
        confidence = 0.5  # Base confidence

        # If we matched a pattern, increase confidence
        if matched_type != 'unknown':
            confidence = 0.7

        # If error_type matches our classification, increase confidence
        if error_type and matched_type in error_type.lower():
            confidence = min(confidence + 0.2, 1.0)

        # If multiple patterns match, increase confidence
        search_text = f"{error_type or ''} {error_message}".lower()
        pattern_matches = 0
        for pattern in self.ERROR_PATTERNS.get(matched_type, []):
            if re.search(pattern, search_text, re.IGNORECASE):
                pattern_matches += 1

        if pattern_matches > 1:
            confidence = min(confidence + 0.1, 1.0)

        return round(confidence, 2)

    def get_error_stats(self, error_history: list) -> Dict[str, Any]:
        """
        Analyze error history for patterns

        Args:
            error_history: List of error dicts from ExecutionHistory

        Returns:
            Statistics about error patterns
        """
        if not error_history:
            return {
                'total_errors': 0,
                'by_type': {},
                'most_common': None,
                'recovery_candidates': []
            }

        # Classify all errors
        classified = [
            self.classify_error(
                error.get('error_message', ''),
                error.get('error_type'),
                {'task': error.get('task_text', '')}
            )
            for error in error_history
        ]

        # Count by type
        by_type = {}
        for c in classified:
            error_type = c['type']
            by_type[error_type] = by_type.get(error_type, 0) + 1

        # Find most common
        most_common = max(by_type.items(), key=lambda x: x[1])[0] if by_type else None

        # Find recovery candidates (recoverable errors)
        recovery_candidates = [
            c for c in classified
            if c['recoverable'] and c['confidence'] >= 0.7
        ]

        return {
            'total_errors': len(error_history),
            'by_type': by_type,
            'most_common': most_common,
            'recovery_candidates': recovery_candidates,
            'recoverable_count': len(recovery_candidates)
        }
