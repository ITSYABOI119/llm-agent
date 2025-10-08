"""
Task Analyzer - Analyzes user requests to determine complexity and routing strategy
"""
import re
from typing import Dict, List


class TaskAnalyzer:
    """Analyzes user tasks to determine optimal model routing"""

    def __init__(self):
        # Keywords indicating different task types
        self.reasoning_keywords = [
            'why', 'how', 'explain', 'analyze', 'understand', 'describe',
            'what is', 'compare', 'difference', 'think', 'reason'
        ]

        self.creation_keywords = [
            'create', 'build', 'make', 'generate', 'write', 'develop',
            'implement', 'design', 'add', 'new'
        ]

        self.modification_keywords = [
            'modify', 'update', 'change', 'edit', 'fix', 'refactor',
            'optimize', 'improve', 'enhance'
        ]

        self.creative_keywords = [
            'creative', 'unique', 'modern', 'beautiful', 'stylish',
            'innovative', 'artistic', 'custom', 'original'
        ]

        # Patterns indicating multi-file operations
        self.multi_file_patterns = [
            r'\b(?:and|with|include)\b.*\b(?:html|css|js|py|txt)\b',
            r'\b\d+\s+files?\b',
            r'\b(?:html|css|js|py)\b.*\b(?:and|,)\b.*\b(?:html|css|js|py)\b'
        ]

    def analyze(self, user_message: str) -> Dict:
        """
        Analyze a user message and return task characteristics

        Returns:
            {
                'complexity': 'simple' | 'medium' | 'complex',
                'intent': 'create' | 'analyze' | 'modify' | 'query',
                'expected_tool_calls': int,
                'requires_reasoning': bool,
                'is_creative': bool,
                'is_multi_file': bool,
                'confidence': float
            }
        """
        message_lower = user_message.lower()

        # Determine intent
        intent = self._determine_intent(message_lower)

        # Check if requires reasoning
        requires_reasoning = any(kw in message_lower for kw in self.reasoning_keywords)

        # Check if creative task
        is_creative = any(kw in message_lower for kw in self.creative_keywords)

        # Check if multi-file operation
        is_multi_file = any(re.search(pattern, message_lower) for pattern in self.multi_file_patterns)

        # Estimate tool calls
        expected_tool_calls = self._estimate_tool_calls(message_lower, is_multi_file)

        # Determine complexity
        complexity = self._determine_complexity(expected_tool_calls, is_multi_file, is_creative)

        # Calculate confidence
        confidence = self._calculate_confidence(message_lower)

        return {
            'complexity': complexity,
            'intent': intent,
            'expected_tool_calls': expected_tool_calls,
            'requires_reasoning': requires_reasoning,
            'is_creative': is_creative,
            'is_multi_file': is_multi_file,
            'confidence': confidence
        }

    def _determine_intent(self, message: str) -> str:
        """Determine primary intent of the message"""
        creation_score = sum(1 for kw in self.creation_keywords if kw in message)
        modification_score = sum(1 for kw in self.modification_keywords if kw in message)
        reasoning_score = sum(1 for kw in self.reasoning_keywords if kw in message)

        scores = {
            'create': creation_score,
            'modify': modification_score,
            'analyze': reasoning_score
        }

        max_score = max(scores.values())
        if max_score == 0:
            return 'query'  # Default

        return max(scores, key=scores.get)

    def _estimate_tool_calls(self, message: str, is_multi_file: bool) -> int:
        """Estimate number of tool calls needed"""
        # Count file mentions
        file_count = 0
        file_extensions = ['html', 'css', 'js', 'py', 'txt', 'json', 'yaml']
        for ext in file_extensions:
            file_count += message.count(ext)

        # Count explicit file mentions (e.g., "3 files")
        number_match = re.search(r'\b(\d+)\s+files?\b', message)
        if number_match:
            file_count = max(file_count, int(number_match.group(1)))

        # Base estimate
        if file_count >= 3:
            return file_count
        elif is_multi_file:
            return 3  # Typical multi-file project
        elif any(word in message for word in ['read', 'list', 'search', 'find']):
            return 1  # Simple query
        else:
            return 2  # Default moderate complexity

    def _determine_complexity(self, tool_calls: int, is_multi_file: bool, is_creative: bool) -> str:
        """Determine overall task complexity"""
        if tool_calls >= 4 or (is_multi_file and is_creative):
            return 'complex'
        elif tool_calls >= 2 or is_multi_file:
            return 'medium'
        else:
            return 'simple'

    def _calculate_confidence(self, message: str) -> float:
        """Calculate confidence in the analysis (0.0 to 1.0)"""
        # Simple heuristic: longer, more specific messages = higher confidence
        word_count = len(message.split())

        if word_count < 5:
            return 0.6  # Low confidence for very short messages
        elif word_count < 15:
            return 0.8  # Medium confidence
        else:
            return 0.95  # High confidence for detailed messages
