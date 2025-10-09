"""
Test Metrics Collection System (Phase 6)
"""

import pytest
import time
from tools.metrics import MetricsCollector, get_global_metrics


class TestMetricsCollector:
    """Test metrics collection functionality"""

    def test_initialization(self, tmp_path):
        """Test metrics collector initializes correctly"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        assert metrics.stats["total_executions"] == 0
        assert metrics.stats["successful_executions"] == 0
        assert metrics.stats["failed_executions"] == 0
        assert len(metrics.tool_executions) == 0
        assert len(metrics.error_log) == 0

    def test_record_successful_execution(self, tmp_path):
        """Test recording successful tool execution"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        metrics.record_tool_execution(
            tool_name="test_tool",
            duration=0.5,
            success=True,
            parameters={"param1": "value1"}
        )

        assert metrics.stats["total_executions"] == 1
        assert metrics.stats["successful_executions"] == 1
        assert metrics.stats["failed_executions"] == 0
        assert len(metrics.tool_executions) == 1
        assert "test_tool" in metrics.stats["tools_used"]

    def test_record_failed_execution(self, tmp_path):
        """Test recording failed tool execution"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        metrics.record_tool_execution(
            tool_name="test_tool",
            duration=0.3,
            success=False,
            parameters={"param1": "value1"},
            error="Test error message"
        )

        assert metrics.stats["total_executions"] == 1
        assert metrics.stats["successful_executions"] == 0
        assert metrics.stats["failed_executions"] == 1
        assert len(metrics.error_log) == 1
        assert metrics.stats["errors_by_tool"]["test_tool"] == 1

    def test_get_tool_stats(self, tmp_path):
        """Test getting statistics for specific tool"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record multiple executions
        metrics.record_tool_execution("write_file", 0.5, True)
        metrics.record_tool_execution("write_file", 0.3, True)
        metrics.record_tool_execution("write_file", 0.7, False, error="Failed")

        stats = metrics.get_tool_stats("write_file")

        assert stats["tool"] == "write_file"
        assert stats["total_executions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] == 66.67
        assert stats["errors"] == 1

    def test_get_overall_stats(self, tmp_path):
        """Test getting overall statistics"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record various executions
        metrics.record_tool_execution("write_file", 0.5, True)
        metrics.record_tool_execution("read_file", 0.2, True)
        metrics.record_tool_execution("list_directory", 0.8, False, error="Error")

        stats = metrics.get_overall_stats()

        assert stats["total_executions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate_percent"] == 66.67
        assert stats["unique_tools_used"] == 3
        assert stats["total_errors"] == 1

    def test_get_recent_errors(self, tmp_path):
        """Test getting recent errors"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record errors
        metrics.record_error("tool1", "Error 1")
        metrics.record_error("tool2", "Error 2")
        metrics.record_error("tool3", "Error 3")

        recent = metrics.get_recent_errors(limit=2)

        assert len(recent) == 2
        assert recent[0]["error"] == "Error 2"
        assert recent[1]["error"] == "Error 3"

    def test_get_slow_operations(self, tmp_path):
        """Test identifying slow operations"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record operations with various durations
        metrics.record_tool_execution("fast_tool", 0.1, True)
        metrics.record_tool_execution("slow_tool", 1.5, True)
        metrics.record_tool_execution("slower_tool", 2.0, True)

        # Get operations slower than 1 second
        slow_ops = metrics.get_slow_operations(threshold_ms=1000)

        assert len(slow_ops) == 2
        assert slow_ops[0]["tool"] == "slow_tool"
        assert slow_ops[1]["tool"] == "slower_tool"

    def test_export_metrics(self, tmp_path):
        """Test exporting metrics to JSON"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record some data
        metrics.record_tool_execution("test_tool", 0.5, True)

        # Export
        export_file = tmp_path / "test_metrics.json"
        metrics.export_metrics(str(export_file))

        # Verify file exists
        assert export_file.exists()

        # Verify JSON content
        import json
        with open(export_file) as f:
            data = json.load(f)

        assert "overall_stats" in data
        assert "tool_executions" in data
        assert len(data["tool_executions"]) == 1

    def test_generate_report(self, tmp_path):
        """Test generating human-readable report"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record data
        metrics.record_tool_execution("write_file", 0.5, True)
        metrics.record_tool_execution("read_file", 0.2, True)
        metrics.record_tool_execution("read_file", 0.3, False, error="Not found")

        report = metrics.generate_report()

        assert "METRICS REPORT" in report
        assert "Total Executions: 3" in report
        assert "Success Rate:" in report
        assert "Top 5 Most Used Tools:" in report

    def test_clear_metrics(self, tmp_path):
        """Test clearing all metrics"""
        metrics = MetricsCollector(output_dir=str(tmp_path))

        # Record data
        metrics.record_tool_execution("test_tool", 0.5, True)
        metrics.record_error("test_tool", "Error")

        # Clear
        metrics.clear_metrics()

        assert metrics.stats["total_executions"] == 0
        assert len(metrics.tool_executions) == 0
        assert len(metrics.error_log) == 0

    def test_global_metrics_singleton(self):
        """Test global metrics instance is singleton"""
        metrics1 = get_global_metrics()
        metrics2 = get_global_metrics()

        assert metrics1 is metrics2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
