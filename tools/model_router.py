"""
Model Router - Smart routing to minimize swaps (Phase 2)
Routes 80% of tasks to qwen-only, reserves openthinker for complex tasks
"""
import logging
from typing import Dict, Optional


class ModelRouter:
    """
    Routes tasks to minimize model swaps

    Strategy:
    - Simple/Standard tasks (80%): qwen only → 0s swap overhead
    - Complex tasks (15-20%): openthinker → qwen → 2.5s overhead (justified)
    - Failures: deepseek → 2.5s overhead (last resort)
    """

    def __init__(self, config: Dict):
        self.config = config
        self.multi_model_config = config.get('ollama', {}).get('multi_model', {})
        self.enabled = self.multi_model_config.get('enabled', False)

        # Model names
        self.models = {
            'qwen': 'qwen2.5-coder:7b',           # Primary workhorse
            'openthinker': 'openthinker3-7b',    # Planning/complex tasks
            'deepseek': 'deepseek-r1:14b'        # Emergency/debugging
        }

        # Log configuration
        if self.enabled:
            logging.info("Smart routing enabled (Phase 2)")
            logging.info(f"Strategy: Minimize swaps, qwen-first approach")
        else:
            logging.info("Multi-model routing disabled")

    def select_model_from_classification(self, classification: Dict) -> str:
        """
        Select model based on task classification (Phase 2)

        Args:
            classification: Output from TaskClassifier.classify()

        Returns:
            Model name
        """
        tier = classification.get('tier', 'standard')
        route_strategy = classification.get('route_strategy', 'qwen_only')

        # Simple and standard: Use qwen only (no swap)
        if tier in ['simple', 'standard']:
            logging.info(f"[{tier.upper()}] Using qwen only (0s swap overhead)")
            return self.models['qwen']

        # Complex: Use openthinker for planning (swap justified)
        elif tier == 'complex':
            logging.info(f"[COMPLEX] Using openthinker (2.5s swap overhead justified)")
            return self.models['openthinker']

        # Fallback
        return self.models['qwen']

    def select_model(self, task_analysis: Dict) -> str:
        """
        Legacy method for compatibility with old TaskAnalyzer

        Args:
            task_analysis: Output from TaskAnalyzer.analyze()

        Returns:
            Model name (e.g., "qwen2.5-coder:7b")
        """
        if not self.enabled:
            return self.config['ollama']['model']

        # Map old complexity to new routing
        complexity = task_analysis.get('complexity', 'medium')
        is_creative = task_analysis.get('is_creative', False)
        is_multi_file = task_analysis.get('is_multi_file', False)

        # Complex + creative + multi-file = use openthinker
        if complexity == 'complex' and (is_creative or is_multi_file):
            logging.info("[COMPLEX] Using openthinker for planning")
            return self.models['openthinker']

        # Default: use qwen (minimize swaps)
        logging.info(f"[{complexity.upper()}] Using qwen (0s swap overhead)")
        return self.models['qwen']

    def should_use_two_phase(self, task_analysis_or_classification: Dict) -> bool:
        """
        Determine if task should use two-phase execution

        Two-phase (openthinker → qwen):
        - Complex creative tasks
        - Multi-file projects requiring planning
        - Architecture/design tasks

        Args:
            task_analysis_or_classification: TaskAnalyzer or TaskClassifier output

        Returns:
            bool: True if two-phase execution recommended
        """
        if not self.enabled:
            return False

        # Check if this is TaskClassifier output (has 'tier')
        if 'tier' in task_analysis_or_classification:
            tier = task_analysis_or_classification.get('tier')
            is_creative = task_analysis_or_classification.get('characteristics', {}).get('is_creative', False)
            is_multi_file = task_analysis_or_classification.get('characteristics', {}).get('is_multi_file', False)

            # Use two-phase for complex tasks
            if tier == 'complex':
                logging.info("Two-phase execution: openthinker (plan) → qwen (execute)")
                return True

            # Also use for standard + creative + multi-file
            if tier == 'standard' and is_creative and is_multi_file:
                logging.info("Two-phase execution: creative multi-file standard task")
                return True

            return False

        # Legacy TaskAnalyzer output
        else:
            complexity = task_analysis_or_classification.get('complexity')
            is_creative = task_analysis_or_classification.get('is_creative', False)
            is_multi_file = task_analysis_or_classification.get('is_multi_file', False)
            intent = task_analysis_or_classification.get('intent')

            use_two_phase = (
                complexity in ['medium', 'complex'] and
                is_creative and
                intent == 'create' and
                is_multi_file
            )

            if use_two_phase:
                logging.info("Two-phase execution (legacy routing)")

            return use_two_phase

    def get_planning_model(self) -> str:
        """Get the model to use for planning phase"""
        return self.models['openthinker']

    def get_execution_model(self) -> str:
        """Get the model to use for execution phase"""
        return self.models['qwen']

    def get_fixer_model(self) -> str:
        """Get the model to use for fixing failures"""
        return self.models['deepseek']

    def get_routing_stats(self, classifications: list) -> Dict:
        """
        Calculate routing statistics from a list of classifications

        Args:
            classifications: List of TaskClassifier.classify() outputs

        Returns:
            Statistics dict
        """
        total = len(classifications)
        if total == 0:
            return {}

        qwen_only = sum(1 for c in classifications if c.get('tier') in ['simple', 'standard'])
        complex_tasks = sum(1 for c in classifications if c.get('tier') == 'complex')

        total_swap_overhead = sum(c.get('estimated_swap_overhead', 0) for c in classifications)
        avg_swap_overhead = total_swap_overhead / total if total > 0 else 0

        return {
            'total_tasks': total,
            'qwen_only': qwen_only,
            'qwen_only_percent': (qwen_only / total * 100) if total > 0 else 0,
            'complex_tasks': complex_tasks,
            'complex_percent': (complex_tasks / total * 100) if total > 0 else 0,
            'total_swap_overhead': f"{total_swap_overhead:.1f}s",
            'avg_swap_overhead': f"{avg_swap_overhead:.2f}s"
        }
