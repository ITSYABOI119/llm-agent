"""
Token Counter - Manage context window limits
Prevents context overflow for OpenThinker (8K tokens)
"""

import logging
from typing import Dict, Any, List


class TokenCounter:
    """
    Track and manage token usage to prevent context overflow
    Uses conservative estimation: ~4 chars per token
    """

    def __init__(self, max_tokens: int = 8000) -> None:
        """
        Initialize token counter

        Args:
            max_tokens: Maximum context window (default: 8000 for OpenThinker)
        """
        self.max_tokens = max_tokens
        self.current_usage = {
            'context_gathering': 0,
            'planning': 0,
            'execution': 0,
            'verification': 0,
            'system_prompt': 0,
            'total': 0
        }

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text
        Conservative estimate: ~4 characters per token
        """
        if not text:
            return 0

        # Handle different input types
        if isinstance(text, dict):
            text = str(text)
        elif isinstance(text, list):
            text = str(text)

        # Estimate: 4 chars per token (conservative)
        return len(text) // 4

    def count_context(self, context: Dict) -> int:
        """Count tokens in gathered context"""
        total = 0

        for key, value in context.items():
            if isinstance(value, str):
                total += self.estimate_tokens(value)
            elif isinstance(value, list):
                for item in value:
                    total += self.estimate_tokens(str(item))
            elif isinstance(value, dict):
                total += self.estimate_tokens(str(value))

        return total

    def track_phase(self, phase: str, content: Any) -> Dict:
        """
        Track token usage for a phase

        Returns:
            {
                'tokens': int,
                'phase': str,
                'within_budget': bool,
                'remaining': int
            }
        """
        tokens = self.estimate_tokens(str(content))
        self.current_usage[phase] = tokens
        self.current_usage['total'] = sum([
            v for k, v in self.current_usage.items() if k != 'total'
        ])

        remaining = self.max_tokens - self.current_usage['total']

        result = {
            'tokens': tokens,
            'phase': phase,
            'within_budget': self.current_usage['total'] < self.max_tokens,
            'remaining': remaining,
            'usage_percent': (self.current_usage['total'] / self.max_tokens) * 100
        }

        if not result['within_budget']:
            logging.warning(
                f"Context budget exceeded! "
                f"{self.current_usage['total']}/{self.max_tokens} tokens used"
            )

        return result

    def check_budget(self, additional_tokens: int) -> bool:
        """Check if we can add more tokens"""
        return (self.current_usage['total'] + additional_tokens) < self.max_tokens

    def get_budget_for_phase(self, phase: str) -> int:
        """
        Get recommended token budget for a phase

        Phase budgets (for 8K total):
        - context_gathering: 2000 tokens (25%)
        - planning: 2000 tokens (25%)
        - execution: 2500 tokens (31%)
        - verification: 1000 tokens (12%)
        - system_prompt: 500 tokens (6%)
        """
        budgets = {
            'context_gathering': 2000,
            'planning': 2000,
            'execution': 2500,
            'verification': 1000,
            'system_prompt': 500
        }

        return budgets.get(phase, 1000)

    def compress_if_needed(self, content: Any, phase: str, compressor) -> Any:
        """
        Automatically compress content if it exceeds phase budget

        Args:
            content: Content to potentially compress
            phase: Current phase
            compressor: Compression function
        """
        budget = self.get_budget_for_phase(phase)
        current_tokens = self.estimate_tokens(str(content))

        if current_tokens > budget:
            logging.info(
                f"Content too large for {phase}: {current_tokens} > {budget} tokens"
            )
            logging.info("Compressing content...")

            compressed = compressor(content, budget)
            new_tokens = self.estimate_tokens(str(compressed))

            logging.info(
                f"Compressed {current_tokens} → {new_tokens} tokens "
                f"({((current_tokens - new_tokens) / current_tokens * 100):.1f}% reduction)"
            )

            return compressed

        return content

    def get_usage_report(self) -> str:
        """Get detailed usage report"""
        report = f"""
Token Usage Report
==================
Max tokens: {self.max_tokens}
Total used: {self.current_usage['total']} ({self.current_usage['total'] / self.max_tokens * 100:.1f}%)
Remaining: {self.max_tokens - self.current_usage['total']}

Phase Breakdown:
  Context gathering: {self.current_usage['context_gathering']} tokens
  Planning:         {self.current_usage['planning']} tokens
  Execution:        {self.current_usage['execution']} tokens
  Verification:     {self.current_usage['verification']} tokens
  System prompt:    {self.current_usage['system_prompt']} tokens

Status: {'✓ Within budget' if self.current_usage['total'] < self.max_tokens else '✗ OVER BUDGET'}
"""
        return report

    def reset(self) -> None:
        """Reset token counter for new request"""
        self.current_usage = {
            'context_gathering': 0,
            'planning': 0,
            'execution': 0,
            'verification': 0,
            'system_prompt': 0,
            'total': 0
        }


class ContextCompressor:
    """
    Compress context to fit within token budgets
    """

    @staticmethod
    def compress_context(context: Dict, max_tokens: int) -> Dict:
        """
        Compress gathered context to fit within token budget

        Strategy:
        1. Keep structure and dependencies (essential)
        2. Summarize file lists (keep only top N)
        3. Shorten patterns (keep only descriptions)
        4. Truncate long strings
        """
        compressed = {}

        # 1. Always keep structure (small)
        if 'project_structure' in context:
            # Truncate if too long
            structure = context['project_structure']
            if len(structure) > 500:
                compressed['project_structure'] = structure[:500] + "..."
            else:
                compressed['project_structure'] = structure

        # 2. Keep dependencies (important)
        if 'dependencies' in context:
            deps = context['dependencies']
            compressed['dependencies'] = {}
            for dep_file, content in list(deps.items())[:3]:  # Max 3 dep files
                # Keep only first 200 chars of each
                compressed['dependencies'][dep_file] = content[:200]

        # 3. Compress file list (keep only top 5)
        if 'relevant_files' in context:
            files = context['relevant_files']
            if len(files) > 5:
                compressed['relevant_files'] = files[:5]
                compressed['file_count'] = len(files)
                compressed['note'] = f"Showing 5 of {len(files)} relevant files"
            else:
                compressed['relevant_files'] = files

        # 4. Compress patterns (keep only counts/descriptions)
        if 'patterns_found' in context:
            patterns = context['patterns_found']
            compressed['patterns_found'] = patterns[:3]  # Top 3 patterns only

        # 5. Keep summary (already compressed)
        if 'summary' in context:
            compressed['summary'] = context['summary']

        return compressed

    @staticmethod
    def compress_plan(plan: str, max_tokens: int) -> str:
        """
        Compress plan text to fit within budget

        Strategy:
        1. Remove verbose explanations
        2. Keep action items
        3. Shorten descriptions
        """
        lines = plan.split('\n')
        compressed_lines = []
        token_count = 0

        for line in lines:
            line_tokens = len(line) // 4

            if token_count + line_tokens > max_tokens:
                break

            # Keep important lines (action items, file names, structure)
            if any(keyword in line.lower() for keyword in [
                'file:', 'create', 'function', 'class', 'import', '1.', '2.', '3.'
            ]):
                compressed_lines.append(line)
                token_count += line_tokens

        return '\n'.join(compressed_lines)

    @staticmethod
    def compress_results(results: List[Dict], max_tokens: int) -> List[Dict]:
        """
        Compress execution results

        Strategy:
        1. Keep success/failure status
        2. Keep file paths
        3. Truncate detailed messages
        """
        compressed = []
        token_count = 0

        for result in results:
            summary = {
                'tool': result.get('tool'),
                'success': result.get('result', {}).get('success'),
                'path': result.get('params', {}).get('path', 'unknown')
            }

            # Add brief error if failed
            if not summary['success']:
                error = result.get('result', {}).get('error', '')
                summary['error'] = error[:100]  # First 100 chars

            result_tokens = len(str(summary)) // 4
            if token_count + result_tokens > max_tokens:
                break

            compressed.append(summary)
            token_count += result_tokens

        return compressed
