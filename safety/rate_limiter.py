"""
Rate Limiter
Prevents abuse by limiting tool execution frequency
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import logging


class RateLimiter:
    """Rate limit tool executions to prevent abuse"""

    def __init__(self, config: Dict):
        self.config = config
        self.limits = config.get('security', {}).get('rate_limits', {})

        # Track executions: {tool_name: [timestamp1, timestamp2, ...]}
        self._executions: Dict[str, List[datetime]] = defaultdict(list)

        # Default limits
        self.default_limit = self.limits.get('default_per_minute', 60)

    def check_rate_limit(self, tool_name: str) -> bool:
        """
        Check if tool execution is within rate limits.

        Args:
            tool_name: Name of tool to check

        Returns:
            True if within limits, False if exceeded
        """
        # Get limit for this tool (default: 60 per minute)
        limit_key = f"{tool_name}_per_minute"
        limit = self.limits.get(limit_key, self.default_limit)

        # Clean old executions (older than 1 minute)
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        self._executions[tool_name] = [
            ts for ts in self._executions[tool_name]
            if ts > cutoff
        ]

        # Check if limit exceeded
        if len(self._executions[tool_name]) >= limit:
            logging.warning(
                f"Rate limit exceeded for {tool_name}: "
                f"{len(self._executions[tool_name])}/{limit} per minute"
            )
            return False

        # Record this execution
        self._executions[tool_name].append(now)
        return True

    def get_stats(self) -> Dict[str, int]:
        """Get current rate limit statistics"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        stats = {}
        for tool_name, timestamps in self._executions.items():
            recent = [ts for ts in timestamps if ts > cutoff]
            stats[tool_name] = len(recent)

        return stats

    def reset(self, tool_name: str = None) -> None:
        """
        Reset rate limit counters.

        Args:
            tool_name: Specific tool to reset, or None to reset all
        """
        if tool_name:
            self._executions[tool_name] = []
        else:
            self._executions.clear()
