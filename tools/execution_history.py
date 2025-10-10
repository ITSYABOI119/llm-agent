"""
Execution History Database - Track all task executions for learning (Phase 2)

Stores:
- Task details (complexity, intent, multi-file, etc.)
- Model routing decisions
- Execution results (success/failure, duration, errors)
- Tool calls and outcomes

Used for:
- Adaptive threshold learning
- Misroute detection
- Error pattern analysis
- Performance optimization
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class ExecutionHistory:
    """Track and query execution history for learning and analytics"""

    def __init__(self, db_path: str = "logs/execution_history.db"):
        """
        Initialize execution history database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure logs directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logging.info(f"Execution history database initialized: {db_path}")

    def _init_database(self):
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_text TEXT NOT NULL,

                -- Task analysis
                complexity TEXT,
                intent TEXT,
                is_creative BOOLEAN,
                is_multi_file BOOLEAN,
                expected_tool_calls INTEGER,

                -- Routing decision
                execution_mode TEXT,  -- 'single-phase' or 'two-phase'
                selected_model TEXT,
                planning_model TEXT,
                execution_model TEXT,

                -- Execution results
                success BOOLEAN NOT NULL,
                duration_seconds REAL,
                error_type TEXT,
                error_message TEXT,

                -- Tool execution
                tool_calls_count INTEGER,
                tool_calls_json TEXT,  -- JSON array of tool calls

                -- Performance metrics
                swap_overhead_seconds REAL,
                tokens_used INTEGER,

                -- Metadata
                session_id TEXT,
                agent_version TEXT
            )
        """)

        # Tool results table (detailed tool-by-tool tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                tool_params TEXT,  -- JSON
                success BOOLEAN NOT NULL,
                duration_seconds REAL,
                error_message TEXT,
                timestamp TEXT NOT NULL,

                FOREIGN KEY (execution_id) REFERENCES executions(id)
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON executions(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_complexity
            ON executions(complexity)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_mode
            ON executions(execution_mode)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_success
            ON executions(success)
        """)

        conn.commit()
        conn.close()

    def log_execution(
        self,
        task_text: str,
        task_analysis: Dict,
        execution_mode: str,
        selected_model: Optional[str] = None,
        planning_model: Optional[str] = None,
        execution_model: Optional[str] = None,
        success: bool = False,
        duration_seconds: float = 0.0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        swap_overhead: float = 0.0,
        tokens_used: int = 0,
        session_id: Optional[str] = None
    ) -> int:
        """
        Log a task execution to history

        Args:
            task_text: Original user request
            task_analysis: TaskAnalyzer/TaskClassifier output
            execution_mode: 'single-phase' or 'two-phase'
            selected_model: Model used (single-phase)
            planning_model: Planning model (two-phase)
            execution_model: Execution model (two-phase)
            success: Whether execution succeeded
            duration_seconds: Total execution time
            error_type: Type of error if failed
            error_message: Error details
            tool_calls: List of tool calls made
            swap_overhead: Model swap time
            tokens_used: Tokens consumed
            session_id: Session identifier

        Returns:
            Execution ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract task analysis fields
        complexity = task_analysis.get('complexity', task_analysis.get('tier'))
        intent = task_analysis.get('intent', 'unknown')
        is_creative = task_analysis.get('is_creative',
                                       task_analysis.get('characteristics', {}).get('is_creative', False))
        is_multi_file = task_analysis.get('is_multi_file',
                                         task_analysis.get('characteristics', {}).get('is_multi_file', False))
        expected_tool_calls = task_analysis.get('expected_tool_calls',
                                               task_analysis.get('characteristics', {}).get('expected_operations', 0))

        cursor.execute("""
            INSERT INTO executions (
                timestamp, task_text,
                complexity, intent, is_creative, is_multi_file, expected_tool_calls,
                execution_mode, selected_model, planning_model, execution_model,
                success, duration_seconds, error_type, error_message,
                tool_calls_count, tool_calls_json,
                swap_overhead_seconds, tokens_used,
                session_id, agent_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            task_text,
            complexity,
            intent,
            is_creative,
            is_multi_file,
            expected_tool_calls,
            execution_mode,
            selected_model,
            planning_model,
            execution_model,
            success,
            duration_seconds,
            error_type,
            error_message,
            len(tool_calls) if tool_calls else 0,
            json.dumps(tool_calls) if tool_calls else None,
            swap_overhead,
            tokens_used,
            session_id,
            "Phase2"  # Version identifier
        ))

        execution_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logging.info(f"Logged execution #{execution_id}: {execution_mode}, success={success}")

        return execution_id

    def log_tool_result(
        self,
        execution_id: int,
        tool_name: str,
        tool_params: Dict,
        success: bool,
        duration_seconds: float,
        error_message: Optional[str] = None
    ):
        """Log individual tool execution result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tool_results (
                execution_id, tool_name, tool_params,
                success, duration_seconds, error_message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_id,
            tool_name,
            json.dumps(tool_params),
            success,
            duration_seconds,
            error_message,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_recent_executions(self, limit: int = 100) -> List[Dict]:
        """Get recent executions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM executions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_error_patterns(self, limit: int = 50) -> List[Dict]:
        """Get recent errors for pattern analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT error_type, error_message, task_text, complexity, execution_mode
            FROM executions
            WHERE success = 0 AND error_type IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics for adaptive learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Overall stats
        cursor.execute("""
            SELECT
                execution_mode,
                complexity,
                COUNT(*) as count,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                AVG(duration_seconds) as avg_duration
            FROM executions
            GROUP BY execution_mode, complexity
        """)

        stats = {}
        for row in cursor.fetchall():
            mode, complexity, count, success_rate, avg_duration = row
            key = f"{mode}_{complexity}"
            stats[key] = {
                'execution_mode': mode,
                'complexity': complexity,
                'count': count,
                'success_rate': success_rate,
                'avg_duration': avg_duration
            }

        conn.close()
        return stats

    def get_misroutes(self, threshold: float = 0.5) -> List[Dict]:
        """
        Identify potential misroutes (tasks that failed with chosen route)

        Args:
            threshold: Success rate threshold below which to flag as misroute

        Returns:
            List of potential misroutes
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                complexity,
                is_multi_file,
                execution_mode,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(duration_seconds) as avg_duration
            FROM executions
            GROUP BY complexity, is_multi_file, execution_mode
            HAVING (CAST(successes AS REAL) / total) < ?
            AND total >= 3
        """, (threshold,))

        rows = cursor.fetchall()
        conn.close()

        misroutes = []
        for row in rows:
            misroutes.append({
                'complexity': row['complexity'],
                'is_multi_file': bool(row['is_multi_file']),
                'execution_mode': row['execution_mode'],
                'total_attempts': row['total'],
                'successes': row['successes'],
                'success_rate': row['successes'] / row['total'],
                'avg_duration': row['avg_duration']
            })

        return misroutes

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall statistics summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total executions
        cursor.execute("SELECT COUNT(*) FROM executions")
        total = cursor.fetchone()[0]

        # Success rate
        cursor.execute("""
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END)
            FROM executions
        """)
        success_rate = cursor.fetchone()[0] or 0.0

        # Average duration
        cursor.execute("SELECT AVG(duration_seconds) FROM executions")
        avg_duration = cursor.fetchone()[0] or 0.0

        # Mode breakdown
        cursor.execute("""
            SELECT execution_mode, COUNT(*)
            FROM executions
            GROUP BY execution_mode
        """)
        mode_counts = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            'total_executions': total,
            'success_rate': success_rate,
            'avg_duration_seconds': avg_duration,
            'execution_modes': mode_counts
        }
