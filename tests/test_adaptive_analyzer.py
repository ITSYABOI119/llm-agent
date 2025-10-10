"""
Test suite for Phase 2 Day 3: Adaptive Learning System

Tests:
- Routing performance analysis
- Misroute detection
- Model recommendations
- Threshold adjustments
- Error insights
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock
from tools.execution_history import ExecutionHistory
from tools.adaptive_analyzer import AdaptiveAnalyzer


class TestAdaptiveAnalyzerInitialization:
    """Test adaptive analyzer initialization"""

    def test_initialization_with_history(self):
        """Should initialize with execution history"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'history.db')
            history = ExecutionHistory(db_path)

            analyzer = AdaptiveAnalyzer(history)

            assert analyzer.history is not None
            assert analyzer.error_classifier is not None


class TestRoutingPerformanceAnalysis:
    """Test routing performance analysis"""

    def setup_method(self):
        """Setup for each test"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'history.db')
        self.history = ExecutionHistory(self.db_path)
        self.analyzer = AdaptiveAnalyzer(self.history)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_analyze_routing_performance_empty(self):
        """Should handle empty execution history"""
        result = self.analyzer.analyze_routing_performance()

        assert 'overall_stats' in result
        assert 'routing_stats' in result
        assert 'patterns' in result
        assert 'recommendations' in result

    def test_analyze_routing_performance_with_data(self):
        """Should analyze routing performance with real data"""
        # Log mix of executions
        for i in range(10):
            self.history.log_execution(
                task_text=f"Simple task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=(i % 5 != 0),  # 80% success
                duration_seconds=1.0
            )

        for i in range(5):
            self.history.log_execution(
                task_text=f"Complex task {i}",
                task_analysis={'complexity': 'complex'},
                execution_mode='two-phase',
                planning_model='openthinker3-7b',
                execution_model='qwen2.5-coder:7b',
                success=(i % 2 == 0),  # 60% success
                duration_seconds=8.0
            )

        result = self.analyzer.analyze_routing_performance()

        # Should have overall stats
        assert result['overall_stats']['total_executions'] == 15

        # Should have routing-specific stats
        assert len(result['routing_stats']) >= 2

        # Should identify patterns
        assert 'best_performing_modes' in result['patterns']
        assert 'worst_performing_modes' in result['patterns']

        # Should provide recommendations
        assert isinstance(result['recommendations'], list)

    def test_identify_best_performing_modes(self):
        """Should identify best performing combinations"""
        # Log high-success simple tasks
        for i in range(10):
            self.history.log_execution(
                task_text=f"Simple task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,  # 100% success
                duration_seconds=1.0
            )

        result = self.analyzer.analyze_routing_performance()

        best = result['patterns']['best_performing_modes']

        # Should identify simple+single-phase as best
        assert len(best) > 0
        assert best[0]['mode'] == 'single-phase'
        assert best[0]['complexity'] == 'simple'
        assert best[0]['success_rate'] == 1.0


class TestMisrouteDetection:
    """Test misroute detection"""

    def setup_method(self):
        """Setup for each test"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'history.db')
        self.history = ExecutionHistory(self.db_path)
        self.analyzer = AdaptiveAnalyzer(self.history)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detect_misroutes_empty(self):
        """Should handle empty history"""
        misroutes = self.analyzer.detect_misroutes()

        assert isinstance(misroutes, list)
        assert len(misroutes) == 0

    def test_detect_misroutes_with_failures(self):
        """Should detect failing routing combinations"""
        # Log tasks that should have been routed differently
        for i in range(5):
            self.history.log_execution(
                task_text=f"Misrouted task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=False,  # All failed
                duration_seconds=1.0
            )

        misroutes = self.analyzer.detect_misroutes(
            success_threshold=0.5,
            min_samples=3
        )

        assert len(misroutes) > 0

        # Should include recommendation
        assert 'recommendation' in misroutes[0]
        assert 'two-phase' in misroutes[0]['recommendation'].lower()

    def test_detect_misroutes_respects_min_samples(self):
        """Should not flag misroutes with insufficient samples"""
        # Log only 2 failures (below min_samples of 3)
        for i in range(2):
            self.history.log_execution(
                task_text=f"Task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=False,
                duration_seconds=1.0
            )

        misroutes = self.analyzer.detect_misroutes(
            success_threshold=0.5,
            min_samples=3
        )

        # Should not flag with only 2 samples
        assert len(misroutes) == 0

    def test_recommend_alternative_route(self):
        """Should recommend alternative routing"""
        # Create misroute scenario
        for i in range(5):
            self.history.log_execution(
                task_text=f"Task {i}",
                task_analysis={'complexity': 'complex'},
                execution_mode='two-phase',
                planning_model='openthinker3-7b',
                execution_model='qwen2.5-coder:7b',
                success=False,
                duration_seconds=8.0
            )

        misroutes = self.analyzer.detect_misroutes(
            success_threshold=0.5,
            min_samples=3
        )

        assert len(misroutes) > 0
        # Should recommend single-phase as alternative
        assert 'single-phase' in misroutes[0]['recommendation'].lower()


class TestModelRecommendation:
    """Test model recommendation for tasks"""

    def setup_method(self):
        """Setup for each test"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'history.db')
        self.history = ExecutionHistory(self.db_path)
        self.analyzer = AdaptiveAnalyzer(self.history)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_recommend_model_no_history(self):
        """Should use heuristics when no historical data"""
        task_analysis = {
            'complexity': 'complex',
            'is_creative': True,
            'is_multi_file': True
        }

        recommendation = self.analyzer.recommend_model_for_task(task_analysis)

        assert 'recommended_mode' in recommendation
        assert 'recommended_model' in recommendation
        assert 'confidence' in recommendation
        assert 'reasoning' in recommendation

        # Should recommend two-phase for complex creative multi-file
        assert recommendation['recommended_mode'] == 'two-phase'
        assert 'no historical data' in recommendation['reasoning'].lower()

    def test_recommend_model_with_history(self):
        """Should use historical data for recommendations"""
        # Log successful simple tasks with single-phase
        for i in range(10):
            self.history.log_execution(
                task_text=f"Simple task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.0
            )

        task_analysis = {'complexity': 'simple'}

        recommendation = self.analyzer.recommend_model_for_task(task_analysis)

        # Should recommend single-phase based on history
        assert recommendation['recommended_mode'] == 'single-phase'
        assert recommendation['historical_success_rate'] == 1.0
        assert recommendation['confidence'] > 0.5
        assert 'history' in recommendation['reasoning'].lower()

    def test_recommend_model_confidence_capped(self):
        """Should cap confidence at 90%"""
        # Log perfect success rate
        for i in range(10):
            self.history.log_execution(
                task_text=f"Task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.0
            )

        task_analysis = {'complexity': 'simple'}

        recommendation = self.analyzer.recommend_model_for_task(task_analysis)

        # Confidence should be capped at 0.9
        assert recommendation['confidence'] <= 0.9

    def test_recommend_model_requires_min_samples(self):
        """Should require minimum samples before using history"""
        # Log only 2 executions (below threshold of 3)
        for i in range(2):
            self.history.log_execution(
                task_text=f"Task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,
                duration_seconds=1.0
            )

        task_analysis = {'complexity': 'simple'}

        recommendation = self.analyzer.recommend_model_for_task(task_analysis)

        # Should fall back to heuristics
        assert 'no historical data' in recommendation['reasoning'].lower()


class TestErrorInsights:
    """Test error insights analysis"""

    def setup_method(self):
        """Setup for each test"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'history.db')
        self.history = ExecutionHistory(self.db_path)
        self.analyzer = AdaptiveAnalyzer(self.history)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_error_insights_empty(self):
        """Should handle empty error history"""
        insights = self.analyzer.get_error_insights()

        assert insights['total_errors'] == 0
        assert len(insights['most_common_errors']) == 0

    def test_get_error_insights_with_errors(self):
        """Should analyze error patterns"""
        # Log various errors
        error_types = [
            'syntax_error', 'syntax_error', 'syntax_error',
            'file_not_found', 'file_not_found',
            'timeout'
        ]

        for i, error_type in enumerate(error_types):
            self.history.log_execution(
                task_text=f"Failed task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=False,
                duration_seconds=1.0,
                error_type=error_type,
                error_message=f"Error message {i}"
            )

        insights = self.analyzer.get_error_insights(limit=50)

        assert insights['total_errors'] == 6
        assert len(insights['most_common_errors']) > 0

        # syntax_error should be most common
        most_common = insights['most_common_errors'][0]
        assert most_common['type'] == 'syntax_error'
        assert most_common['count'] == 3


class TestThresholdAdjustments:
    """Test threshold adjustment suggestions"""

    def setup_method(self):
        """Setup for each test"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'history.db')
        self.history = ExecutionHistory(self.db_path)
        self.analyzer = AdaptiveAnalyzer(self.history)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_suggest_threshold_adjustments_empty(self):
        """Should handle empty history"""
        suggestions = self.analyzer.suggest_threshold_adjustments()

        assert isinstance(suggestions, list)

    def test_suggest_increase_two_phase_usage(self):
        """Should suggest increasing two-phase usage if it performs better"""
        # Log single-phase with low success
        for i in range(10):
            self.history.log_execution(
                task_text=f"Single task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=(i < 5),  # 50% success
                duration_seconds=1.0
            )

        # Log two-phase with high success
        for i in range(10):
            self.history.log_execution(
                task_text=f"Two-phase task {i}",
                task_analysis={'complexity': 'complex'},
                execution_mode='two-phase',
                planning_model='openthinker3-7b',
                execution_model='qwen2.5-coder:7b',
                success=(i < 8),  # 80% success
                duration_seconds=8.0
            )

        suggestions = self.analyzer.suggest_threshold_adjustments()

        # Should suggest increasing two-phase usage
        increase_suggestions = [s for s in suggestions if s['type'] == 'increase_two_phase_usage']
        assert len(increase_suggestions) > 0

    def test_suggest_decrease_two_phase_usage(self):
        """Should suggest decreasing two-phase if single-phase performs better"""
        # Log single-phase with high success
        for i in range(10):
            self.history.log_execution(
                task_text=f"Single task {i}",
                task_analysis={'complexity': 'simple'},
                execution_mode='single-phase',
                selected_model='qwen2.5-coder:7b',
                success=True,  # 100% success
                duration_seconds=1.0
            )

        # Log two-phase with low success
        for i in range(10):
            self.history.log_execution(
                task_text=f"Two-phase task {i}",
                task_analysis={'complexity': 'complex'},
                execution_mode='two-phase',
                planning_model='openthinker3-7b',
                execution_model='qwen2.5-coder:7b',
                success=(i < 6),  # 60% success
                duration_seconds=8.0
            )

        suggestions = self.analyzer.suggest_threshold_adjustments()

        # Should suggest decreasing two-phase usage
        decrease_suggestions = [s for s in suggestions if s['type'] == 'decrease_two_phase_usage']
        assert len(decrease_suggestions) > 0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
