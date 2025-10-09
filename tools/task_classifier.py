"""
Task Classifier - Smart task classification for minimal model swaps
Implements Phase 2: Intelligent routing to minimize 2.5s swap overhead
"""

import re
import logging
from typing import Dict, List, Any


class TaskClassifier:
    """
    Classify tasks into simple/standard/complex tiers

    Goal: Route 80% of tasks to qwen-only (0s swap overhead)
    Only use openthinker when quality gain justifies 2.5s swap cost
    """

    def __init__(self) -> None:
        # SIMPLE: Single-file, straightforward operations (qwen only)
        self.simple_patterns: List[str] = [
            'add a function',
            'add function',
            'fix typo',
            'fix this typo',
            'format code',
            'format this',
            'rename variable',
            'rename this',
            'add comment',
            'add comments',
            'update docstring',
            'delete file',
            'remove file',
            'read file',
            'show file',
            'list files',
            'search for',
            'find file'
        ]

        self.simple_keywords: List[str] = [
            'typo', 'rename', 'delete', 'remove', 'read', 'show',
            'list', 'search', 'find', 'display', 'print'
        ]

        # STANDARD: Multi-step but well-defined (qwen only)
        self.standard_patterns: List[str] = [
            'build a component',
            'create a component',
            'refactor this',
            'refactor function',
            'debug this',
            'fix this error',
            'add error handling',
            'write test',
            'write tests',
            'update function',
            'modify function',
            'improve function'
        ]

        self.standard_keywords: List[str] = [
            'refactor', 'debug', 'test', 'component', 'module',
            'error handling', 'validation', 'logging'
        ]

        # COMPLEX: Requires architectural thinking (openthinker worth it)
        self.complex_patterns: List[str] = [
            'design architecture',
            'design system',
            'create application',
            'create app',
            'build application',
            'build system',
            'build complete',
            'full application',
            'full system',
            'design algorithm',
            'solve problem',
            'complex problem',
            'design pattern'
        ]

        self.complex_keywords: List[str] = [
            'architecture', 'design', 'algorithm', 'system',
            'application', 'framework', 'platform', 'solution',
            'strategy', 'approach', 'methodology', 'authentication',
            'database', 'microservices', 'api', 'backend', 'full stack'
        ]

        # Creative indicators (suggests complex)
        self.creative_keywords: List[str] = [
            'creative', 'unique', 'modern', 'beautiful', 'stylish',
            'innovative', 'custom', 'original', 'artistic', 'elegant'
        ]

        # Multi-file patterns
        self.multi_file_patterns: List[str] = [
            r'\b(?:html|css|js)\b.*\b(?:and|with|,)\b.*\b(?:html|css|js)\b',
            r'\b\d+\s+files?\b',
            r'\bwith\s+(?:html|css|js|styling|scripts?)\b',
            r'\binclude.*(?:html|css|js)\b'
        ]

    def classify(self, user_message: str) -> Dict[str, Any]:
        """
        Classify task to determine optimal routing strategy

        Returns:
            {
                'tier': 'simple' | 'standard' | 'complex',
                'route_strategy': 'qwen_only' | 'openthinker_then_qwen',
                'estimated_swap_overhead': float,  # in seconds
                'confidence': float,
                'reasoning': str,
                'characteristics': {
                    'is_multi_file': bool,
                    'is_creative': bool,
                    'file_count': int,
                    'expected_operations': int
                }
            }
        """
        message_lower = user_message.lower()

        # Analyze characteristics
        is_multi_file = self._check_multi_file(message_lower)
        is_creative = self._check_creative(message_lower)
        file_count = self._estimate_file_count(message_lower)
        expected_operations = self._estimate_operations(message_lower, file_count)

        # Classify tier
        tier = self._classify_tier(
            message_lower,
            is_multi_file,
            is_creative,
            file_count,
            expected_operations
        )

        # Determine routing strategy
        route_strategy = self._determine_route_strategy(tier)

        # Calculate swap overhead
        swap_overhead = self._calculate_swap_overhead(route_strategy)

        # Build reasoning
        reasoning = self._build_reasoning(
            tier, is_multi_file, is_creative, file_count, expected_operations
        )

        # Confidence score
        confidence = self._calculate_confidence(message_lower, tier)

        return {
            'tier': tier,
            'route_strategy': route_strategy,
            'estimated_swap_overhead': swap_overhead,
            'confidence': confidence,
            'reasoning': reasoning,
            'characteristics': {
                'is_multi_file': is_multi_file,
                'is_creative': is_creative,
                'file_count': file_count,
                'expected_operations': expected_operations
            }
        }

    def _classify_tier(
        self,
        message: str,
        is_multi_file: bool,
        is_creative: bool,
        file_count: int,
        expected_operations: int
    ) -> str:
        """Classify into simple/standard/complex tier"""

        # Check for explicit complex patterns FIRST
        if any(pattern in message for pattern in self.complex_patterns):
            return 'complex'

        # Check for complex keywords
        complex_keyword_count = sum(
            1 for kw in self.complex_keywords if kw in message
        )
        if complex_keyword_count >= 1:  # Reduced from 2 to 1 for better detection
            return 'complex'

        # Multi-file + creative = complex
        if is_multi_file and is_creative:
            return 'complex'

        # Large number of files = complex
        if file_count >= 4:
            return 'complex'

        # Many operations = complex
        if expected_operations >= 5:
            return 'complex'

        # Check for standard patterns BEFORE simple
        if any(pattern in message for pattern in self.standard_patterns):
            return 'standard'

        # Standard keywords detection
        standard_keyword_count = sum(
            1 for kw in self.standard_keywords if kw in message
        )
        if standard_keyword_count >= 1:
            return 'standard'

        # Multi-file but not creative = standard (not simple)
        if is_multi_file:
            return 'standard'

        # Multiple operations = standard
        if expected_operations >= 3:
            return 'standard'

        # Check for explicit simple patterns
        if any(pattern in message for pattern in self.simple_patterns):
            return 'simple'

        # Check for simple keywords
        simple_keyword_count = sum(
            1 for kw in self.simple_keywords if kw in message
        )
        if simple_keyword_count >= 1:
            return 'simple'

        # Very short operations = simple
        if expected_operations <= 1:
            return 'simple'

        # Default: standard (safer default than simple)
        return 'standard'

    def _check_multi_file(self, message: str) -> bool:
        """Check if task involves multiple files"""
        # Check explicit patterns
        for pattern in self.multi_file_patterns:
            if re.search(pattern, message):
                return True

        # Check for multiple file extension mentions
        file_extensions = ['html', 'css', 'js', 'py', 'txt', 'json', 'yaml', 'jsx', 'tsx']
        ext_count = sum(1 for ext in file_extensions if ext in message)

        return ext_count >= 2

    def _check_creative(self, message: str) -> bool:
        """Check if task requires creative thinking"""
        return any(kw in message for kw in self.creative_keywords)

    def _estimate_file_count(self, message: str) -> int:
        """Estimate number of files involved"""
        # Check for explicit count (e.g., "3 files")
        number_match = re.search(r'\b(\d+)\s+files?\b', message)
        if number_match:
            return int(number_match.group(1))

        # Count file extension mentions
        file_extensions = ['html', 'css', 'js', 'py', 'txt', 'json', 'yaml', 'jsx', 'tsx']
        ext_count = sum(1 for ext in file_extensions if ext in message)

        # Heuristics
        if 'application' in message or 'app' in message:
            return 3  # Typical app has ~3 main files
        elif self._check_multi_file(message):
            return 2
        else:
            return 1

    def _estimate_operations(self, message: str, file_count: int) -> int:
        """Estimate number of operations needed"""
        operation_keywords = [
            'create', 'write', 'edit', 'update', 'delete', 'modify',
            'add', 'remove', 'refactor', 'build', 'generate'
        ]

        op_count = sum(1 for kw in operation_keywords if kw in message)

        # "Build" and "create" tasks with components are multi-step
        if ('build' in message or 'create' in message) and (
            'component' in message or 'module' in message or
            'system' in message or 'page' in message
        ):
            op_count = max(op_count, 2)

        # Factor in file count
        return max(op_count, file_count)

    def _determine_route_strategy(self, tier: str) -> str:
        """Determine routing strategy based on tier"""
        if tier == 'complex':
            return 'openthinker_then_qwen'
        else:
            # Simple and standard both use qwen only
            return 'qwen_only'

    def _calculate_swap_overhead(self, route_strategy: str) -> float:
        """Calculate estimated swap overhead in seconds"""
        if route_strategy == 'qwen_only':
            return 0.0  # No swap needed
        elif route_strategy == 'openthinker_then_qwen':
            return 2.5  # One swap from openthinker to qwen
        else:
            return 0.0

    def _build_reasoning(
        self,
        tier: str,
        is_multi_file: bool,
        is_creative: bool,
        file_count: int,
        expected_operations: int
    ) -> str:
        """Build human-readable reasoning for classification"""
        reasons = []

        if tier == 'simple':
            reasons.append("Single straightforward operation")
            if file_count <= 1:
                reasons.append("involves one file")
            if not is_creative:
                reasons.append("no creative thinking needed")

        elif tier == 'standard':
            reasons.append("Multi-step but well-defined task")
            if file_count <= 2:
                reasons.append(f"involves {file_count} file(s)")
            if expected_operations <= 4:
                reasons.append(f"~{expected_operations} operations")

        elif tier == 'complex':
            if is_multi_file and is_creative:
                reasons.append("Multi-file creative project")
            elif file_count >= 4:
                reasons.append(f"Large scope ({file_count} files)")
            elif is_creative:
                reasons.append("Requires creative/architectural thinking")
            else:
                reasons.append("Complex task requiring planning")

        return " - ".join(reasons) if reasons else "Standard task"

    def _calculate_confidence(self, message: str, tier: str) -> float:
        """Calculate confidence in classification"""
        word_count = len(message.split())

        # Base confidence on message detail
        if word_count < 5:
            base_confidence = 0.7
        elif word_count < 10:
            base_confidence = 0.85
        else:
            base_confidence = 0.95

        # Adjust based on tier clarity
        # Complex tasks are easier to identify (strong keywords)
        # Simple tasks can be ambiguous
        if tier == 'complex':
            return min(base_confidence + 0.05, 1.0)
        elif tier == 'simple':
            return max(base_confidence - 0.05, 0.6)
        else:
            return base_confidence

    def get_statistics_summary(self) -> Dict[str, int]:
        """Get summary of classification patterns"""
        return {
            'simple_patterns': len(self.simple_patterns),
            'standard_patterns': len(self.standard_patterns),
            'complex_patterns': len(self.complex_patterns),
            'total_patterns': (
                len(self.simple_patterns) +
                len(self.standard_patterns) +
                len(self.complex_patterns)
            )
        }
