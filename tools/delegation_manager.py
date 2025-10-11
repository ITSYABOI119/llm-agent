"""
Delegation Manager - Cursor-style model delegation
Handles when orchestrator delegates to specialist models
Optimized for RTX 2070 8GB VRAM constraints
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum


class DelegationType(Enum):
    """Types of delegation decisions"""
    ORCHESTRATOR_ONLY = "orchestrator_only"  # Orchestrator handles directly
    DELEGATE_CODE = "delegate_code"  # Delegate to code generation model
    DELEGATE_TOOLS = "delegate_tools"  # Delegate to tool formatter
    DELEGATE_ADVANCED = "delegate_advanced"  # Delegate to advanced reasoning


class DelegationDecision:
    """Represents a delegation decision"""

    def __init__(
        self,
        delegation_type: DelegationType,
        target_model: str,
        reason: str,
        confidence: float = 1.0
    ):
        self.delegation_type = delegation_type
        self.target_model = target_model
        self.reason = reason
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"DelegationDecision({self.delegation_type.value} → {self.target_model}, {self.reason})"


class DelegationManager:
    """
    Manages model delegation decisions for Cursor-style architecture

    Architecture:
        orchestrator (openthinker3-7b) -> decides -> delegates to specialists:
            ├─ code_generation (qwen2.5-coder:7b) - for code writing
            ├─ tool_formatter (phi3:mini) - for reliable tool calls
            └─ advanced_reasoning (llama3.1:8b) - for complex debugging

    VRAM Optimization:
        - Keep orchestrator + tool_formatter loaded (6.9GB)
        - Swap to code_generation when needed (~500ms with RAM caching)
        - Rarely use advanced_reasoning (model swap overhead)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cursor_config = config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('cursor_routing', {})
        self.delegation_config = self.cursor_config.get('delegation', {})

        # Model names from config
        models = config.get('ollama', {}).get('multi_model', {}).get('models', {})
        self.orchestrator_model = models.get('orchestrator', {}).get('name', 'openthinker3-7b')
        self.code_model = models.get('code_generation', {}).get('name', 'qwen2.5-coder:7b')
        self.tool_formatter_model = models.get('tool_formatter', {}).get('name', 'phi3:mini')
        self.advanced_model = models.get('advanced_reasoning', {}).get('name', 'llama3.1:8b')

        # Delegation thresholds
        self.code_generation_threshold = self.delegation_config.get('code_generation_threshold', 20)
        self.use_advanced_reasoning = self.delegation_config.get('use_advanced_reasoning', False)
        self.tool_calls_always_use_formatter = self.delegation_config.get('tool_calls_always_use_formatter', True)

        logging.info(f"DelegationManager initialized:")
        logging.info(f"  Orchestrator: {self.orchestrator_model}")
        logging.info(f"  Code specialist: {self.code_model}")
        logging.info(f"  Tool formatter: {self.tool_formatter_model}")
        logging.info(f"  Advanced reasoning: {self.advanced_model} (enabled={self.use_advanced_reasoning})")

    def should_delegate_code_generation(
        self,
        task_description: str,
        estimated_lines: Optional[int] = None
    ) -> DelegationDecision:
        """
        Determine if code generation should be delegated to specialist model

        Args:
            task_description: Description of the task
            estimated_lines: Estimated lines of code to generate

        Returns:
            DelegationDecision indicating whether to delegate
        """
        # Check if task explicitly mentions code generation
        code_keywords = [
            'write code', 'generate code', 'create function', 'create class',
            'build component', 'implement', 'refactor', 'write a', 'create a'
        ]

        task_lower = task_description.lower()
        mentions_code = any(keyword in task_lower for keyword in code_keywords)

        # Check if estimated lines exceed threshold
        if estimated_lines and estimated_lines > self.code_generation_threshold:
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_CODE,
                target_model=self.code_model,
                reason=f"Estimated {estimated_lines} lines exceeds threshold {self.code_generation_threshold}",
                confidence=0.9
            )

        # Check for multi-file code generation indicators
        multi_file_indicators = ['html', 'css', 'js', 'javascript', 'multiple files', 'several files']
        is_multi_file = any(indicator in task_lower for indicator in multi_file_indicators)

        if is_multi_file:
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_CODE,
                target_model=self.code_model,
                reason="Multi-file code generation detected",
                confidence=0.85
            )

        # Delegate if task explicitly mentions code
        if mentions_code:
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_CODE,
                target_model=self.code_model,
                reason="Code generation keywords detected",
                confidence=0.8
            )

        # Default: orchestrator handles directly
        return DelegationDecision(
            delegation_type=DelegationType.ORCHESTRATOR_ONLY,
            target_model=self.orchestrator_model,
            reason="Simple task, orchestrator can handle",
            confidence=0.9
        )

    def should_delegate_tool_formatting(self, has_tool_calls: bool) -> DelegationDecision:
        """
        Determine if tool call formatting should be delegated to phi3:mini

        Args:
            has_tool_calls: Whether the response contains tool calls

        Returns:
            DelegationDecision indicating whether to delegate

        Note:
            Always delegates tool calls to phi3:mini because "qwen isnt good for tool calls"
        """
        if not has_tool_calls:
            return DelegationDecision(
                delegation_type=DelegationType.ORCHESTRATOR_ONLY,
                target_model=self.orchestrator_model,
                reason="No tool calls needed",
                confidence=1.0
            )

        if self.tool_calls_always_use_formatter:
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_TOOLS,
                target_model=self.tool_formatter_model,
                reason="Tool calls always use phi3:mini formatter (fixes qwen reliability issues)",
                confidence=1.0
            )

        return DelegationDecision(
            delegation_type=DelegationType.ORCHESTRATOR_ONLY,
            target_model=self.orchestrator_model,
            reason="Tool formatter disabled in config",
            confidence=0.7
        )

    def should_use_advanced_reasoning(
        self,
        task_complexity: str,
        is_debugging: bool = False,
        has_errors: bool = False
    ) -> DelegationDecision:
        """
        Determine if advanced reasoning model should be used

        Args:
            task_complexity: Complexity tier (simple, standard, complex)
            is_debugging: Whether this is a debugging task
            has_errors: Whether there are errors to analyze

        Returns:
            DelegationDecision indicating whether to use advanced model

        Note:
            Only used sparingly due to model swap overhead
        """
        if not self.use_advanced_reasoning:
            return DelegationDecision(
                delegation_type=DelegationType.ORCHESTRATOR_ONLY,
                target_model=self.orchestrator_model,
                reason="Advanced reasoning disabled in config",
                confidence=1.0
            )

        # Use advanced model for debugging with errors
        if is_debugging and has_errors:
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_ADVANCED,
                target_model=self.advanced_model,
                reason="Complex debugging task with errors",
                confidence=0.85
            )

        # Use for very complex tasks
        if task_complexity == "complex" and (is_debugging or has_errors):
            return DelegationDecision(
                delegation_type=DelegationType.DELEGATE_ADVANCED,
                target_model=self.advanced_model,
                reason="Complex task requiring advanced reasoning",
                confidence=0.8
            )

        # Default: orchestrator is sufficient
        return DelegationDecision(
            delegation_type=DelegationType.ORCHESTRATOR_ONLY,
            target_model=self.orchestrator_model,
            reason="Orchestrator sufficient for this task",
            confidence=0.9
        )

    def get_delegation_strategy(
        self,
        task_description: str,
        task_classification: Dict[str, Any],
        has_tool_calls: bool = False,
        estimated_code_lines: Optional[int] = None
    ) -> Dict[str, DelegationDecision]:
        """
        Get complete delegation strategy for a task

        Args:
            task_description: Description of the task
            task_classification: Classification from TaskClassifier
            has_tool_calls: Whether tool calls are expected
            estimated_code_lines: Estimated lines of code

        Returns:
            Dictionary with delegation decisions for each aspect
        """
        complexity = task_classification.get('complexity', 'standard')
        is_debugging = 'debug' in task_description.lower() or 'fix' in task_description.lower()
        has_errors = 'error' in task_description.lower() or 'bug' in task_description.lower()

        strategy = {
            'code_generation': self.should_delegate_code_generation(
                task_description,
                estimated_code_lines
            ),
            'tool_formatting': self.should_delegate_tool_formatting(has_tool_calls),
            'advanced_reasoning': self.should_use_advanced_reasoning(
                complexity,
                is_debugging,
                has_errors
            )
        }

        # Log delegation strategy
        logging.info("Delegation strategy:")
        for aspect, decision in strategy.items():
            logging.info(f"  {aspect}: {decision}")

        return strategy

    def get_model_for_phase(
        self,
        phase: str,
        task_classification: Dict[str, Any]
    ) -> str:
        """
        Get the appropriate model for a specific execution phase

        Args:
            phase: Execution phase (planning, orchestration, code, tools)
            task_classification: Classification from TaskClassifier

        Returns:
            Model name to use
        """
        if phase == 'planning':
            return self.orchestrator_model  # openthinker plans

        elif phase == 'orchestration':
            return self.orchestrator_model  # openthinker orchestrates

        elif phase == 'code_generation':
            return self.code_model  # qwen writes code

        elif phase == 'tool_formatting':
            return self.tool_formatter_model  # phi3 formats tools

        elif phase == 'advanced_reasoning':
            if self.use_advanced_reasoning:
                return self.advanced_model  # llama3.1 for debugging
            return self.orchestrator_model

        else:
            logging.warning(f"Unknown phase '{phase}', defaulting to orchestrator")
            return self.orchestrator_model

    def get_orchestrator_model(self) -> str:
        """Get the orchestrator model name (convenience method)"""
        return self.orchestrator_model

    def get_code_model(self) -> str:
        """Get the code generation model name (convenience method)"""
        return self.code_model

    def get_tool_formatter_model(self) -> str:
        """Get the tool formatter model name (convenience method)"""
        return self.tool_formatter_model

    def get_advanced_model(self) -> str:
        """Get the advanced reasoning model name (convenience method)"""
        return self.advanced_model
