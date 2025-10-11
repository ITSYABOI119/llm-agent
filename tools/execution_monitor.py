"""
Execution Monitor - Monitor execution and provide feedback (Phase 3 Day 4-5)

Analyzes execution results to determine if replanning is needed.
Detects:
- Cascading failures
- Low success rates
- Critical errors
- Early termination conditions

Provides feedback for adaptive replanning.
"""

import logging
from typing import Dict, List, Any, Optional


class ExecutionMonitor:
    """
    Monitor execution phase and provide feedback for replanning

    Tracks tool execution results and determines if the plan needs adjustment.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize execution monitor

        Args:
            config: Configuration dict
        """
        self.config = config

        # Get thresholds from config
        feedback_config = config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('two_phase', {}).get('feedback_loop', {})

        self.replan_threshold = feedback_config.get('replan_on_failure_rate', 0.5)
        self.max_replan_attempts = feedback_config.get('max_replan_attempts', 1)

        # Early termination config
        execution_config = config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('two_phase', {}).get('execution', {})
        self.early_termination = execution_config.get('early_termination_on_critical_failure', True)

        # Tracking
        self.execution_history = []

    def monitor_execution(
        self,
        plan: str,
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze execution results and determine if replanning is needed

        Args:
            plan: Original plan
            execution_results: List of tool execution results

        Returns:
            {
                'status': str - 'success', 'partial_success', 'failure', 'critical_failure'
                'success_rate': float - Percentage of successful tool calls
                'replan_needed': bool - Whether replanning is needed
                'replan_reason': str - Reason for replanning (if needed)
                'failed_tools': List[Dict] - List of failed tools
                'cascading_failure': bool - Whether cascading failures detected
                'early_termination': bool - Whether to terminate early
            }
        """
        logging.info(f"[EXEC_MONITOR] Monitoring execution: {len(execution_results)} tool calls")

        if not execution_results:
            logging.warning("[EXEC_MONITOR] No execution results to monitor")
            return {
                'status': 'unknown',
                'success_rate': 0,
                'replan_needed': False,
                'replan_reason': '',
                'failed_tools': [],
                'cascading_failure': False,
                'early_termination': False
            }

        # Calculate success rate
        successful = sum(1 for r in execution_results if r.get('success', False))
        success_rate = successful / len(execution_results)

        # Identify failed tools
        failed_tools = [
            {
                'tool': r.get('tool', 'unknown'),
                'error': r.get('error', 'Unknown error'),
                'index': i
            }
            for i, r in enumerate(execution_results)
            if not r.get('success', False)
        ]

        # Detect cascading failures
        cascading = self._has_cascading_failures(execution_results, failed_tools)

        # Detect critical failures
        critical_failure = self._has_critical_failure(failed_tools)

        # Determine status
        if success_rate == 1.0:
            status = 'success'
        elif success_rate >= 0.7:
            status = 'partial_success'
        elif critical_failure:
            status = 'critical_failure'
        else:
            status = 'failure'

        # Determine if replanning is needed
        replan_needed = False
        replan_reason = ''

        if success_rate < self.replan_threshold:
            replan_needed = True
            replan_reason = f"Low success rate ({success_rate*100:.0f}%), below threshold ({self.replan_threshold*100:.0f}%)"

        if cascading:
            replan_needed = True
            replan_reason = "Cascading failures detected - early failures blocking later steps"

        if critical_failure:
            replan_needed = True
            replan_reason = "Critical failure encountered - plan execution blocked"

        # Determine if early termination is needed
        early_termination_needed = (
            self.early_termination and
            (critical_failure or (cascading and success_rate < 0.3))
        )

        result = {
            'status': status,
            'success_rate': success_rate,
            'successful_count': successful,
            'failed_count': len(failed_tools),
            'total_count': len(execution_results),
            'replan_needed': replan_needed,
            'replan_reason': replan_reason,
            'failed_tools': failed_tools,
            'cascading_failure': cascading,
            'critical_failure': critical_failure,
            'early_termination': early_termination_needed
        }

        # Log to history
        self.execution_history.append({
            'plan_snippet': plan[:100],
            'result': result
        })

        logging.info(f"[EXEC_MONITOR] Status: {status}, Success rate: {success_rate*100:.0f}%, "
                    f"Replan needed: {replan_needed}")

        if early_termination_needed:
            logging.warning("[EXEC_MONITOR] Early termination recommended")

        return result

    def _has_cascading_failures(
        self,
        execution_results: List[Dict[str, Any]],
        failed_tools: List[Dict[str, Any]]
    ) -> bool:
        """
        Detect if failures are cascading (early failures causing later ones)

        Args:
            execution_results: All execution results
            failed_tools: Failed tool results

        Returns:
            True if cascading failures detected
        """
        if len(failed_tools) < 2:
            return False

        # Check if failures are consecutive
        failed_indices = [f['index'] for f in failed_tools]
        consecutive_failures = 0
        max_consecutive = 0

        for i in range(len(failed_indices) - 1):
            if failed_indices[i+1] - failed_indices[i] == 1:
                consecutive_failures += 1
                max_consecutive = max(max_consecutive, consecutive_failures + 1)
            else:
                consecutive_failures = 0

        # Cascading if 3+ consecutive failures
        if max_consecutive >= 3:
            return True

        # Also check if early failures (first 3 tools) affect later ones
        early_failures = [f for f in failed_tools if f['index'] < 3]
        if early_failures and len(failed_tools) > len(early_failures):
            # Likely cascading if early failures exist and more failures follow
            return True

        return False

    def _has_critical_failure(self, failed_tools: List[Dict[str, Any]]) -> bool:
        """
        Detect if any failures are critical (blocking execution)

        Args:
            failed_tools: List of failed tools

        Returns:
            True if critical failure detected
        """
        # Critical error indicators
        critical_keywords = [
            'permission denied',
            'access denied',
            'authentication failed',
            'authorization failed',
            'cannot connect',
            'connection refused',
            'fatal error',
            'critical error',
            'system error'
        ]

        for failed in failed_tools:
            error_msg = failed.get('error', '').lower()
            if any(keyword in error_msg for keyword in critical_keywords):
                return True

        return False

    def generate_execution_report(
        self,
        monitor_result: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable execution report

        Args:
            monitor_result: Result from monitor_execution()

        Returns:
            Formatted report string
        """
        status = monitor_result['status']
        success_rate = monitor_result['success_rate']
        successful = monitor_result['successful_count']
        failed = monitor_result['failed_count']
        total = monitor_result['total_count']

        # Status emoji
        status_emoji = {
            'success': '✓',
            'partial_success': '⚠',
            'failure': '✗',
            'critical_failure': '✗✗'
        }.get(status, '?')

        report = f"{status_emoji} Execution Status: {status.upper()}\n"
        report += f"Success Rate: {success_rate*100:.0f}% ({successful}/{total} tools succeeded)\n"

        # Failed tools
        if monitor_result['failed_tools']:
            report += f"\nFailed Tools ({failed}):\n"
            for failed_tool in monitor_result['failed_tools'][:5]:  # Show first 5
                report += f"  - {failed_tool['tool']}: {failed_tool['error'][:100]}\n"

        # Warnings
        if monitor_result['cascading_failure']:
            report += "\n⚠ WARNING: Cascading failures detected\n"

        if monitor_result['critical_failure']:
            report += "\n✗ CRITICAL: Critical failure encountered\n"

        if monitor_result['early_termination']:
            report += "\n⚠ Recommending early termination\n"

        # Replanning
        if monitor_result['replan_needed']:
            report += f"\n↻ Replanning recommended: {monitor_result['replan_reason']}\n"

        return report

    def should_replan(self, monitor_result: Dict[str, Any]) -> bool:
        """
        Determine if replanning should occur

        Args:
            monitor_result: Result from monitor_execution()

        Returns:
            True if replanning should occur
        """
        return monitor_result.get('replan_needed', False)

    def should_terminate_early(self, monitor_result: Dict[str, Any]) -> bool:
        """
        Determine if execution should terminate early

        Args:
            monitor_result: Result from monitor_execution()

        Returns:
            True if early termination recommended
        """
        return monitor_result.get('early_termination', False)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get statistics from monitoring history

        Returns:
            Statistics dict
        """
        if not self.execution_history:
            return {
                'total_monitored': 0,
                'average_success_rate': 0,
                'replan_rate': 0,
                'critical_failure_rate': 0
            }

        total = len(self.execution_history)
        replans = sum(1 for h in self.execution_history if h['result']['replan_needed'])
        critical = sum(1 for h in self.execution_history if h['result']['critical_failure'])

        success_rates = [h['result']['success_rate'] for h in self.execution_history]
        avg_success = sum(success_rates) / len(success_rates) if success_rates else 0

        return {
            'total_monitored': total,
            'average_success_rate': avg_success,
            'replan_rate': replans / total if total > 0 else 0,
            'critical_failure_rate': critical / total if total > 0 else 0,
            'replans_triggered': replans,
            'critical_failures': critical
        }
