"""
Metrics Collection System
Tracks tool execution, performance, and system health metrics
"""

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging


class MetricsCollector:
    """
    Collect and export metrics for monitoring and analysis.

    Tracks:
    - Tool execution (success/failure rates)
    - Performance (execution times)
    - Resource usage
    - Error patterns
    """

    def __init__(self, output_dir: str = "logs"):
        """
        Initialize metrics collector.

        Args:
            output_dir: Directory to store metrics files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.output_dir / "metrics.json"

        # In-memory metrics
        self.tool_executions: List[Dict[str, Any]] = []
        self.error_log: List[Dict[str, Any]] = []
        self.performance_data: Dict[str, List[float]] = defaultdict(list)

        # Aggregated statistics
        self.stats: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "tools_used": set(),
            "errors_by_tool": defaultdict(int),
            "avg_execution_time": defaultdict(list)
        }

        self.session_start = datetime.now()

    def record_tool_execution(
        self,
        tool_name: str,
        duration: float,
        success: bool,
        parameters: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Record a tool execution event.

        Args:
            tool_name: Name of the tool executed
            duration: Execution time in seconds
            success: Whether execution succeeded
            parameters: Tool parameters (optional)
            error: Error message if failed (optional)
        """
        execution = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "duration": round(duration, 3),
            "success": success,
            "parameters": parameters or {},
            "error": error
        }

        self.tool_executions.append(execution)

        # Update statistics
        self.stats["total_executions"] += 1
        if success:
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1
            self.stats["errors_by_tool"][tool_name] += 1

        self.stats["tools_used"].add(tool_name)
        self.stats["avg_execution_time"][tool_name].append(duration)

        # Track performance
        self.performance_data[tool_name].append(duration)

        # Log error if failed
        if not success and error:
            self.record_error(tool_name, error, parameters)

    def record_error(
        self,
        tool_name: str,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an error event.

        Args:
            tool_name: Tool where error occurred
            error: Error message
            context: Additional context (optional)
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "error": error,
            "context": context or {}
        }

        self.error_log.append(error_entry)

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific tool.

        Args:
            tool_name: Tool to get stats for

        Returns:
            Dict with tool statistics
        """
        executions = [e for e in self.tool_executions if e["tool"] == tool_name]

        if not executions:
            return {"error": f"No data for tool: {tool_name}"}

        successful = sum(1 for e in executions if e["success"])
        failed = len(executions) - successful

        durations = [e["duration"] for e in executions]
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        return {
            "tool": tool_name,
            "total_executions": len(executions),
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / len(executions) * 100, 2) if executions else 0,
            "avg_duration_ms": round(avg_duration * 1000, 2),
            "min_duration_ms": round(min_duration * 1000, 2),
            "max_duration_ms": round(max_duration * 1000, 2),
            "errors": self.stats["errors_by_tool"].get(tool_name, 0)
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall system statistics.

        Returns:
            Dict with overall metrics
        """
        session_duration = (datetime.now() - self.session_start).total_seconds()

        # Calculate overall success rate
        success_rate = 0
        if self.stats["total_executions"] > 0:
            success_rate = (self.stats["successful_executions"] /
                          self.stats["total_executions"] * 100)

        # Get top tools by usage
        tool_usage: Dict[str, int] = defaultdict(int)
        for execution in self.tool_executions:
            tool_usage[execution["tool"]] += 1

        top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        # Get slowest tools
        slowest_tools = []
        for tool, durations in self.stats["avg_execution_time"].items():
            avg_time = sum(durations) / len(durations) if durations else 0
            slowest_tools.append((tool, avg_time))
        slowest_tools.sort(key=lambda x: x[1], reverse=True)
        slowest_tools = slowest_tools[:5]

        return {
            "session_duration_seconds": round(session_duration, 2),
            "total_executions": self.stats["total_executions"],
            "successful": self.stats["successful_executions"],
            "failed": self.stats["failed_executions"],
            "success_rate_percent": round(success_rate, 2),
            "unique_tools_used": len(self.stats["tools_used"]),
            "total_errors": len(self.error_log),
            "top_5_tools": [{"tool": tool, "count": count} for tool, count in top_tools],
            "slowest_5_tools": [{"tool": tool, "avg_ms": round(dur * 1000, 2)}
                               for tool, dur in slowest_tools]
        }

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent errors.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent error entries
        """
        return self.error_log[-limit:]

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """
        Get operations that exceeded time threshold.

        Args:
            threshold_ms: Threshold in milliseconds

        Returns:
            List of slow operations
        """
        threshold_seconds = threshold_ms / 1000
        slow_ops = [
            {
                "timestamp": e["timestamp"],
                "tool": e["tool"],
                "duration_ms": round(e["duration"] * 1000, 2),
                "success": e["success"]
            }
            for e in self.tool_executions
            if e["duration"] > threshold_seconds
        ]
        return slow_ops

    def export_metrics(self, filepath: Optional[str] = None) -> None:
        """
        Export metrics to JSON file.

        Args:
            filepath: Output file path (optional, uses default if not specified)
        """
        output_path = Path(filepath) if filepath else self.metrics_file

        # Convert set to list for JSON serialization
        tools_used_list = list(self.stats["tools_used"])
        errors_by_tool_dict = dict(self.stats["errors_by_tool"])

        metrics_data = {
            "exported_at": datetime.now().isoformat(),
            "session_start": self.session_start.isoformat(),
            "overall_stats": self.get_overall_stats(),
            "tool_executions": self.tool_executions,
            "errors": self.error_log,
            "tools_used": tools_used_list,
            "errors_by_tool": errors_by_tool_dict
        }

        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)

        logging.info(f"Metrics exported to {output_path}")

    def generate_report(self) -> str:
        """
        Generate a human-readable metrics report.

        Returns:
            Formatted report string
        """
        overall = self.get_overall_stats()

        report = []
        report.append("=" * 60)
        report.append("METRICS REPORT")
        report.append("=" * 60)
        report.append(f"Session Duration: {overall['session_duration_seconds']}s")
        report.append(f"Total Executions: {overall['total_executions']}")
        report.append(f"Success Rate: {overall['success_rate_percent']}%")
        report.append(f"Successful: {overall['successful']}")
        report.append(f"Failed: {overall['failed']}")
        report.append(f"Total Errors: {overall['total_errors']}")
        report.append("")

        if overall["top_5_tools"]:
            report.append("Top 5 Most Used Tools:")
            for item in overall["top_5_tools"]:
                report.append(f"  - {item['tool']}: {item['count']} times")
            report.append("")

        if overall["slowest_5_tools"]:
            report.append("Top 5 Slowest Tools (avg):")
            for item in overall["slowest_5_tools"]:
                report.append(f"  - {item['tool']}: {item['avg_ms']}ms")
            report.append("")

        # Recent errors
        recent_errors = self.get_recent_errors(5)
        if recent_errors:
            report.append("Recent Errors (last 5):")
            for error in recent_errors:
                report.append(f"  - [{error['tool']}] {error['error']}")
            report.append("")

        # Slow operations
        slow_ops = self.get_slow_operations(1000)
        if slow_ops:
            report.append(f"Slow Operations (>1000ms): {len(slow_ops)}")
            for op in slow_ops[:5]:
                report.append(f"  - {op['tool']}: {op['duration_ms']}ms")

        report.append("=" * 60)

        return "\n".join(report)

    def clear_metrics(self) -> None:
        """Clear all collected metrics and reset statistics"""
        self.tool_executions.clear()
        self.error_log.clear()
        self.performance_data.clear()

        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "tools_used": set(),
            "errors_by_tool": defaultdict(int),
            "avg_execution_time": defaultdict(list)
        }

        self.session_start = datetime.now()
        logging.info("Metrics cleared")


# Global metrics collector instance
_global_metrics: Optional[MetricsCollector] = None


def get_global_metrics() -> MetricsCollector:
    """
    Get or create global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics
