"""
Adaptive Analyzer - Learn from execution history to improve routing (Phase 2)

Analyzes execution history to:
- Detect routing performance patterns
- Identify misroutes (tasks that failed with chosen execution mode)
- Recommend model selections based on success rates
- Suggest routing threshold adjustments

Used for continuous improvement and self-optimization.
"""

import logging
from typing import Dict, Any, List, Optional
from tools.execution_history import ExecutionHistory
from tools.error_classifier import ErrorClassifier


class AdaptiveAnalyzer:
    """Analyze execution history for adaptive learning and optimization"""

    def __init__(self, history: ExecutionHistory):
        """
        Initialize adaptive analyzer

        Args:
            history: ExecutionHistory instance to query
        """
        self.history = history
        self.error_classifier = ErrorClassifier()

    def analyze_routing_performance(self) -> Dict[str, Any]:
        """
        Analyze routing performance to identify patterns

        Returns:
            {
                'overall_stats': {...},
                'by_complexity': {...},
                'by_mode': {...},
                'recommendations': [...]
            }
        """
        logging.info("[ADAPTIVE] Analyzing routing performance...")

        # Get overall stats
        overall = self.history.get_stats_summary()

        # Get routing stats by complexity and mode
        routing_stats = self.history.get_routing_stats()

        # Analyze patterns
        patterns = self._identify_patterns(routing_stats)

        # Generate recommendations
        recommendations = self._generate_routing_recommendations(routing_stats, patterns)

        return {
            'overall_stats': overall,
            'routing_stats': routing_stats,
            'patterns': patterns,
            'recommendations': recommendations
        }

    def detect_misroutes(self, success_threshold: float = 0.5, min_samples: int = 3) -> List[Dict[str, Any]]:
        """
        Detect potential misroutes (tasks failing with current routing logic)

        Args:
            success_threshold: Success rate below which to flag as misroute
            min_samples: Minimum number of samples required

        Returns:
            List of misroute detections with recommendations
        """
        logging.info(f"[ADAPTIVE] Detecting misroutes (threshold: {success_threshold}, min samples: {min_samples})...")

        # Get misroutes from history
        raw_misroutes = self.history.get_misroutes(threshold=success_threshold)

        # Filter by minimum samples
        misroutes = [m for m in raw_misroutes if m['total_attempts'] >= min_samples]

        # Add recommendations for each misroute
        for misroute in misroutes:
            misroute['recommendation'] = self._recommend_alternative_route(misroute)

        logging.info(f"[ADAPTIVE] Found {len(misroutes)} potential misroutes")

        return misroutes

    def recommend_model_for_task(self, task_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend best model/execution mode for a task based on history

        Args:
            task_analysis: Task analysis from TaskAnalyzer

        Returns:
            {
                'recommended_mode': str,
                'recommended_model': str,
                'confidence': float,
                'reasoning': str,
                'historical_success_rate': float
            }
        """
        complexity = task_analysis.get('complexity', task_analysis.get('tier', 'simple'))
        is_multi_file = task_analysis.get('is_multi_file',
                                         task_analysis.get('characteristics', {}).get('is_multi_file', False))
        is_creative = task_analysis.get('is_creative',
                                       task_analysis.get('characteristics', {}).get('is_creative', False))

        # Query historical performance for similar tasks
        routing_stats = self.history.get_routing_stats()

        # Find best performing mode for this task type
        best_mode = None
        best_success_rate = 0.0
        reasoning_parts = []

        for key, stats in routing_stats.items():
            if stats['complexity'] == complexity:
                if stats['success_rate'] > best_success_rate and stats['count'] >= 3:
                    best_mode = stats['execution_mode']
                    best_success_rate = stats['success_rate']

        if best_mode:
            reasoning = f"Based on {complexity} tasks in history, {best_mode} has {best_success_rate:.1%} success rate"
            confidence = min(best_success_rate, 0.9)  # Cap confidence at 90%
        else:
            # No historical data - use heuristics
            if complexity in ['complex', 'very_complex'] and is_creative and is_multi_file:
                best_mode = 'two-phase'
                reasoning = "Complex creative multi-file task - two-phase recommended (no historical data)"
                confidence = 0.6
            else:
                best_mode = 'single-phase'
                reasoning = "Simple task - single-phase recommended (no historical data)"
                confidence = 0.7

        return {
            'recommended_mode': best_mode,
            'recommended_model': self._get_model_for_mode(best_mode),
            'confidence': confidence,
            'reasoning': reasoning,
            'historical_success_rate': best_success_rate if best_mode else None
        }

    def get_error_insights(self, limit: int = 50) -> Dict[str, Any]:
        """
        Analyze error patterns for insights

        Returns:
            {
                'error_stats': {...},
                'most_common_errors': [...],
                'recovery_candidates': [...]
            }
        """
        logging.info("[ADAPTIVE] Analyzing error patterns...")

        # Get recent errors
        error_history = self.history.get_error_patterns(limit=limit)

        if not error_history:
            return {
                'error_stats': {},
                'most_common_errors': [],
                'recovery_candidates': [],
                'total_errors': 0
            }

        # Use error classifier to analyze patterns
        error_stats = self.error_classifier.get_error_stats(error_history)

        # Find most common errors
        most_common = sorted(
            error_stats['by_type'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'error_stats': error_stats,
            'most_common_errors': [
                {'type': err_type, 'count': count}
                for err_type, count in most_common
            ],
            'recovery_candidates': error_stats['recovery_candidates'],
            'total_errors': error_stats['total_errors'],
            'recoverable_count': error_stats['recoverable_count']
        }

    def suggest_threshold_adjustments(self) -> List[Dict[str, Any]]:
        """
        Suggest routing threshold adjustments based on performance

        Returns:
            List of suggested threshold changes
        """
        logging.info("[ADAPTIVE] Analyzing threshold effectiveness...")

        suggestions = []

        # Analyze two-phase usage
        routing_stats = self.history.get_routing_stats()

        # Count successes/failures by mode
        single_phase_stats = {'successes': 0, 'failures': 0, 'total': 0}
        two_phase_stats = {'successes': 0, 'failures': 0, 'total': 0}

        for key, stats in routing_stats.items():
            mode = stats['execution_mode']
            count = stats['count']
            success_rate = stats['success_rate']

            if mode == 'single-phase':
                single_phase_stats['successes'] += int(count * success_rate)
                single_phase_stats['failures'] += int(count * (1 - success_rate))
                single_phase_stats['total'] += count
            elif mode == 'two-phase':
                two_phase_stats['successes'] += int(count * success_rate)
                two_phase_stats['failures'] += int(count * (1 - success_rate))
                two_phase_stats['total'] += count

        # Suggest more two-phase if it performs better
        if (two_phase_stats['total'] >= 5 and single_phase_stats['total'] >= 5):
            two_phase_rate = two_phase_stats['successes'] / two_phase_stats['total'] if two_phase_stats['total'] > 0 else 0
            single_phase_rate = single_phase_stats['successes'] / single_phase_stats['total'] if single_phase_stats['total'] > 0 else 0

            if two_phase_rate > single_phase_rate + 0.2:  # 20% better
                suggestions.append({
                    'type': 'increase_two_phase_usage',
                    'reason': f"Two-phase has {two_phase_rate:.1%} success vs single-phase {single_phase_rate:.1%}",
                    'suggested_action': 'Lower complexity threshold for two-phase routing',
                    'confidence': 0.7
                })
            elif single_phase_rate > two_phase_rate + 0.2:
                suggestions.append({
                    'type': 'decrease_two_phase_usage',
                    'reason': f"Single-phase has {single_phase_rate:.1%} success vs two-phase {two_phase_rate:.1%}",
                    'suggested_action': 'Raise complexity threshold for two-phase routing',
                    'confidence': 0.7
                })

        return suggestions

    def _identify_patterns(self, routing_stats: Dict) -> Dict[str, Any]:
        """Identify patterns in routing performance"""
        patterns = {
            'best_performing_modes': [],
            'worst_performing_modes': [],
            'underutilized_modes': []
        }

        # Sort by success rate
        sorted_stats = sorted(
            routing_stats.items(),
            key=lambda x: x[1]['success_rate'],
            reverse=True
        )

        # Best performers (>80% success, >5 samples)
        patterns['best_performing_modes'] = [
            {
                'mode': stats['execution_mode'],
                'complexity': stats['complexity'],
                'success_rate': stats['success_rate'],
                'count': stats['count']
            }
            for key, stats in sorted_stats
            if stats['success_rate'] > 0.8 and stats['count'] >= 5
        ][:3]

        # Worst performers (<50% success, >3 samples)
        patterns['worst_performing_modes'] = [
            {
                'mode': stats['execution_mode'],
                'complexity': stats['complexity'],
                'success_rate': stats['success_rate'],
                'count': stats['count']
            }
            for key, stats in sorted_stats
            if stats['success_rate'] < 0.5 and stats['count'] >= 3
        ][:3]

        return patterns

    def _generate_routing_recommendations(self, routing_stats: Dict, patterns: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Recommend avoiding worst performing combinations
        for worst in patterns['worst_performing_modes']:
            recommendations.append(
                f"Consider alternative routing for {worst['complexity']} tasks in {worst['mode']} "
                f"(only {worst['success_rate']:.1%} success rate)"
            )

        # Recommend using best performing combinations
        for best in patterns['best_performing_modes']:
            recommendations.append(
                f"Continue using {best['mode']} for {best['complexity']} tasks "
                f"({best['success_rate']:.1%} success rate)"
            )

        return recommendations

    def _recommend_alternative_route(self, misroute: Dict) -> str:
        """Recommend alternative routing for a misroute"""
        current_mode = misroute['execution_mode']
        complexity = misroute['complexity']
        success_rate = misroute['success_rate']

        if current_mode == 'single-phase':
            return f"Try two-phase execution for {complexity} tasks (currently {success_rate:.1%} with single-phase)"
        else:
            return f"Try single-phase execution for {complexity} tasks (currently {success_rate:.1%} with two-phase)"

    def _get_model_for_mode(self, mode: str) -> str:
        """Get recommended model name for execution mode"""
        if mode == 'two-phase':
            return 'openthinker3-7b + qwen2.5-coder:7b'
        else:
            return 'qwen2.5-coder:7b'
