"""
Test suite for Phase 2 Day 1: Execution History Database

Tests:
- Database initialization
- Execution logging
- Query operations
- Stats and analytics
- Misroute detection
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path
from tools.execution_history import ExecutionHistory


class TestExecutionHistoryInitialization:
    """Test database initialization"""

    def test_creates_database_file(self):
        """Should create database file if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test_history.db')

            history = ExecutionHistory(db_path)

            assert os.path.exists(db_path)

    def test_creates_parent_directories(self):
        """Should create parent directories if they don't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'logs', 'nested', 'history.db')

            history = ExecutionHistory(db_path)

            assert os.path.exists(db_path)
            assert os.path.exists(os.path.dirname(db_path))

    def test_creates_executions_table(self):
        """Should create executions table"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='executions'"
            )
            assert cursor.fetchone() is not None
            conn.close()

    def test_creates_tool_results_table(self):
        """Should create tool_results table"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tool_results'"
            )
            assert cursor.fetchone() is not None
            conn.close()


class TestExecutionLogging:
    """Test execution logging"""

    def test_log_successful_execution(self):
        """Should log successful execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            execution_id = history.log_execution(
                task_text="Create hello.txt",
                task_analysis={'complexity': 'simple', 'tier': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=2.5
            )

            assert execution_id is not None
            assert execution_id > 0

    def test_log_failed_execution(self):
        """Should log failed execution with error details"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            execution_id = history.log_execution(
                task_text="Write broken code",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=False,
                duration_seconds=1.2,
                error_type='syntax_error',
                error_message='IndentationError: unexpected indent'
            )

            # Verify error was logged
            recent = history.get_recent_executions(limit=1)
            assert len(recent) == 1
            assert recent[0]['error_type'] == 'syntax_error'
            assert 'IndentationError' in recent[0]['error_message']

    def test_log_two_phase_execution(self):
        """Should log two-phase execution with both models"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            execution_id = history.log_execution(
                task_text="Create a landing page",
                task_analysis={'complexity': 'complex', 'is_creative': True},
                execution_mode='two-phase',
                planning_model='openthinker3-7b',
                execution_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=8.3,
                swap_overhead=2.5
            )

            recent = history.get_recent_executions(limit=1)
            assert recent[0]['execution_mode'] == 'two-phase'
            assert recent[0]['planning_model'] == 'openthinker3-7b'
            assert recent[0]['execution_model'] == 'qwen2.5-coder:7b'
            assert recent[0]['swap_overhead'] == 2.5

    def test_log_tool_calls(self):
        """Should log individual tool calls"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            tool_calls = [
                {'tool': 'write_file', 'success': True, 'duration': 0.3},
                {'tool': 'write_file', 'success': True, 'duration': 0.4},
                {'tool': 'write_file', 'success': True, 'duration': 0.2}
            ]

            execution_id = history.log_execution(
                task_text="Create 3 files",
                task_analysis={'complexity': 'standard'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.5,
                tool_calls=tool_calls
            )

            # Verify tool calls were logged
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM tool_results WHERE execution_id = ?",
                (execution_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 3


class TestQueryOperations:
    """Test query operations"""

    def test_get_recent_executions(self):
        """Should retrieve recent executions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log multiple executions
            for i in range(5):
                history.log_execution(
                    task_text=f"Task {i}",
                    task_analysis={'complexity': 'simple'},
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=True,
                    duration_seconds=1.0
                )

            recent = history.get_recent_executions(limit=3)

            assert len(recent) == 3
            # Should be in reverse chronological order
            assert recent[0]['task_text'] == 'Task 4'

    def test_get_stats_summary(self):
        """Should compute statistics summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log mix of successes and failures
            for i in range(10):
                history.log_execution(
                    task_text=f"Task {i}",
                    task_analysis={'complexity': 'simple'},
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=(i % 3 != 0),  # Every 3rd fails
                    duration_seconds=1.0 + (i * 0.1)
                )

            stats = history.get_stats_summary()

            assert stats['total_executions'] == 10
            assert stats['successful_executions'] == 7  # 0,3,6,9 failed
            assert stats['failed_executions'] == 3
            assert stats['success_rate'] == pytest.approx(0.7, abs=0.01)
            assert 'average_duration' in stats

    def test_get_routing_stats(self):
        """Should group stats by execution mode and complexity"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log different routing scenarios
            for i in range(3):
                history.log_execution(
                    task_text=f"Simple task {i}",
                    task_analysis={'complexity': 'simple'},
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=True,
                    duration_seconds=1.0
                )

            for i in range(2):
                history.log_execution(
                    task_text=f"Complex task {i}",
                    task_analysis={'complexity': 'complex'},
                    execution_mode='two-phase',
                    planning_model='openthinker3-7b',
                    execution_model='qwen2.5-coder:7b',
                    success=True,
                    duration_seconds=8.0
                )

            routing_stats = history.get_routing_stats()

            # Should have stats for both combinations
            simple_single = None
            complex_two = None

            for key, stats in routing_stats.items():
                if stats['execution_mode'] == 'single-phase' and stats['complexity'] == 'simple':
                    simple_single = stats
                elif stats['execution_mode'] == 'two-phase' and stats['complexity'] == 'complex':
                    complex_two = stats

            assert simple_single is not None
            assert simple_single['count'] == 3
            assert simple_single['success_rate'] == 1.0

            assert complex_two is not None
            assert complex_two['count'] == 2
            assert complex_two['success_rate'] == 1.0

    def test_get_error_patterns(self):
        """Should retrieve error patterns"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log various errors
            error_types = ['syntax_error', 'syntax_error', 'file_not_found', 'timeout']

            for i, error_type in enumerate(error_types):
                history.log_execution(
                    task_text=f"Failed task {i}",
                    task_analysis={'complexity': 'simple'},
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=False,
                    duration_seconds=1.0,
                    error_type=error_type,
                    error_message=f"Error message {i}"
                )

            errors = history.get_error_patterns(limit=10)

            assert len(errors) == 4
            # Should include error_type
            syntax_errors = [e for e in errors if e['error_type'] == 'syntax_error']
            assert len(syntax_errors) == 2


class TestMisrouteDetection:
    """Test misroute detection"""

    def test_detect_simple_misroutes(self):
        """Should detect tasks that should have used two-phase"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log simple tasks that failed with single-phase
            for i in range(5):
                history.log_execution(
                    task_text=f"Complex task routed as simple {i}",
                    task_analysis={'complexity': 'simple'},  # Misclassified
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=False,  # Failed
                    duration_seconds=1.0
                )

            # Log one success
            history.log_execution(
                task_text="Correct simple task",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.0
            )

            misroutes = history.get_misroutes(threshold=0.5)

            # Should detect the failing combination
            assert len(misroutes) > 0

            simple_single_misroute = next(
                (m for m in misroutes
                 if m['execution_mode'] == 'single-phase' and m['complexity'] == 'simple'),
                None
            )

            assert simple_single_misroute is not None
            assert simple_single_misroute['total_attempts'] == 6
            assert simple_single_misroute['success_rate'] < 0.5

    def test_no_misroutes_with_good_performance(self):
        """Should not flag good performing routes as misroutes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            # Log mostly successful executions
            for i in range(10):
                history.log_execution(
                    task_text=f"Good task {i}",
                    task_analysis={'complexity': 'simple'},
                    execution_mode='single-phase',
                    selected_model='qwen2.5-coder:7b',
                    success=(i != 0),  # Only 1 failure
                    duration_seconds=1.0
                )

            misroutes = history.get_misroutes(threshold=0.5)

            # Should not flag as misroute (90% success rate)
            simple_single_misroute = next(
                (m for m in misroutes
                 if m['execution_mode'] == 'single-phase' and m['complexity'] == 'simple'),
                None
            )

            assert simple_single_misroute is None


class TestDataPersistence:
    """Test data persistence"""

    def test_data_persists_across_instances(self):
        """Data should persist when reopening database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')

            # Create history and log execution
            history1 = ExecutionHistory(db_path)
            history1.log_execution(
                task_text="Persistent task",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.0
            )

            # Create new instance pointing to same DB
            history2 = ExecutionHistory(db_path)
            recent = history2.get_recent_executions(limit=10)

            assert len(recent) == 1
            assert recent[0]['task_text'] == 'Persistent task'


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
