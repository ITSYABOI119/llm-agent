"""
Model Router - Cursor-style routing with model delegation
Routes tasks through orchestrator which delegates to specialists
Optimized for RTX 2070 8GB VRAM
"""
import logging
from typing import Dict, Optional
from tools.delegation_manager import DelegationManager


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

        # Get routing style (cursor or hybrid)
        routing_config = self.multi_model_config.get('routing', {})
        self.routing_style = routing_config.get('style', 'cursor')  # Default to Cursor-style

        # Model names from config
        models_config = self.multi_model_config.get('models', {})
        self.models = {
            # Cursor-style models
            'orchestrator': models_config.get('orchestrator', {}).get('name', 'openthinker3-7b'),
            'tool_formatter': models_config.get('tool_formatter', {}).get('name', 'phi3:mini'),
            'code_generation': models_config.get('code_generation', {}).get('name', 'qwen2.5-coder:7b'),
            'advanced_reasoning': models_config.get('advanced_reasoning', {}).get('name', 'llama3.1:8b'),

            # Legacy model names (for backward compatibility)
            'qwen': 'qwen2.5-coder:7b',
            'openthinker': 'openthinker3-7b',
            'deepseek': 'deepseek-r1:14b'
        }

        # Initialize delegation manager for Cursor-style routing
        if self.routing_style == 'cursor':
            self.delegation_manager = DelegationManager(config)
            logging.info(f"Cursor-style routing enabled (optimized for RTX 2070 8GB VRAM)")
            logging.info(f"  Orchestrator: {self.models['orchestrator']}")
            logging.info(f"  Tool Formatter: {self.models['tool_formatter']}")
            logging.info(f"  Code Specialist: {self.models['code_generation']}")
        else:
            self.delegation_manager = None
            logging.info("Hybrid routing enabled (legacy mode)")
            logging.info(f"Strategy: Minimize swaps, qwen-first approach")

        if not self.enabled:
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
            file_count = task_analysis_or_classification.get('characteristics', {}).get('file_count', 0)

            # Use two-phase for complex tasks
            if tier == 'complex':
                logging.info("Two-phase execution: openthinker (plan) -> qwen (execute)")
                return True

            # Also use for standard + creative + multi-file
            if tier == 'standard' and is_creative and is_multi_file:
                logging.info("Two-phase execution: creative multi-file standard task")
                return True

            # PHASE 1 FIX: Force two-phase for 3+ file tasks (avoid openthinker single-phase timeout)
            if is_multi_file and file_count >= 3:
                logging.info(f"Two-phase execution: {file_count} files (avoiding single-phase timeout)")
                return True

            return False

        # Legacy TaskAnalyzer output
        else:
            complexity = task_analysis_or_classification.get('complexity')
            is_creative = task_analysis_or_classification.get('is_creative', False)
            is_multi_file = task_analysis_or_classification.get('is_multi_file', False)
            intent = task_analysis_or_classification.get('intent')
            expected_tool_calls = task_analysis_or_classification.get('expected_tool_calls', 0)

            # PHASE 1 FIX: Force two-phase for 3+ file tasks (works with legacy TaskAnalyzer too)
            if is_multi_file and expected_tool_calls >= 3:
                logging.info(f"Two-phase execution: {expected_tool_calls} operations (avoiding single-phase timeout)")
                return True

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

    # ========== CURSOR-STYLE ROUTING METHODS ==========

    def should_use_simple_path(self, classification: Dict) -> bool:
        """
        Determine if task should use simple path (direct orchestration)

        Simple Path (65-70% of tasks):
            - Single or simple tasks
            - <= 2 files
            - Not creative
            - Orchestrator handles directly or delegates to specialists

        Args:
            classification: Output from TaskClassifier.classify()

        Returns:
            bool: True if simple path should be used
        """
        if self.routing_style != 'cursor':
            return False  # Not applicable for hybrid routing

        tier = classification.get('tier', 'standard')
        characteristics = classification.get('characteristics', {})
        file_count = characteristics.get('file_count', 0)
        is_creative = characteristics.get('is_creative', False)

        # Get simple path config
        cursor_config = self.multi_model_config.get('routing', {}).get('cursor_routing', {})
        simple_config = cursor_config.get('simple_path', {})
        triggers = simple_config.get('triggers', {})

        max_files = triggers.get('max_files', 2)
        max_complexity = triggers.get('max_complexity', 'standard')

        # Use simple path if:
        # 1. Simple tier, OR
        # 2. Standard tier + <= max_files + not creative
        if tier == 'simple':
            logging.info("[SIMPLE PATH] Simple tier task → direct orchestration")
            return True

        if tier == 'standard' and file_count <= max_files and not is_creative:
            logging.info(f"[SIMPLE PATH] Standard task ({file_count} files, not creative) → direct orchestration")
            return True

        logging.info(f"[COMPLEX PATH] {tier} tier, {file_count} files, creative={is_creative} → full pipeline")
        return False

    def get_orchestrator_model(self) -> str:
        """Get the main orchestrator model (openthinker3-7b)"""
        return self.models.get('orchestrator', 'openthinker3-7b')

    def get_tool_formatter_model(self) -> str:
        """Get the tool call formatter model (phi3:mini)"""
        return self.models.get('tool_formatter', 'phi3:mini')

    def get_code_generation_model(self) -> str:
        """Get the code generation specialist model (qwen2.5-coder:7b)"""
        return self.models.get('code_generation', 'qwen2.5-coder:7b')

    def get_advanced_reasoning_model(self) -> str:
        """Get the advanced reasoning model (llama3.1:8b)"""
        return self.models.get('advanced_reasoning', 'llama3.1:8b')

    def get_delegation_strategy(
        self,
        task_description: str,
        classification: Dict,
        has_tool_calls: bool = False,
        estimated_code_lines: Optional[int] = None
    ) -> Dict:
        """
        Get delegation strategy for Cursor-style execution

        Args:
            task_description: Description of the task
            classification: Output from TaskClassifier
            has_tool_calls: Whether tool calls are expected
            estimated_code_lines: Estimated lines of code

        Returns:
            Dictionary with delegation decisions
        """
        if self.routing_style != 'cursor' or not self.delegation_manager:
            return {
                'error': 'Cursor-style routing not enabled',
                'routing_style': self.routing_style
            }

        return self.delegation_manager.get_delegation_strategy(
            task_description,
            classification,
            has_tool_calls,
            estimated_code_lines
        )

    def get_execution_path(self, classification: Dict) -> str:
        """
        Determine execution path (simple or complex)

        Returns:
            'simple_path' or 'complex_path'
        """
        if self.routing_style != 'cursor':
            # Legacy routing: check two-phase
            return 'complex_path' if self.should_use_two_phase(classification) else 'simple_path'

        return 'simple_path' if self.should_use_simple_path(classification) else 'complex_path'
