"""
Progressive Retry System - Smart escalation on failures (Phase 3)
Retries with increasing sophistication before escalating to heavier models
"""

import logging
from typing import Dict, List, Any, Optional


class ProgressiveRetrySystem:
    """
    Progressive retry with smart escalation

    Strategy:
    1. Attempt with primary model (qwen) + standard prompt
    2. Retry with primary model (qwen) + enhanced prompt (0s overhead)
    3. Escalate to emergency model (deepseek) if critical (2.5s swap)

    Benefits:
    - 0s overhead for most retries (same model, better prompt)
    - Only swap to deepseek when absolutely necessary
    - Maintains high success rate without excessive swaps
    """

    def __init__(self, model_manager, model_router):
        """
        Initialize retry system

        Args:
            model_manager: SmartModelManager instance
            model_router: ModelRouter instance
        """
        self.model_manager = model_manager
        self.model_router = model_router
        self.max_retries = 3

    def execute_with_retry(
        self,
        task: str,
        execute_fn,
        context: Optional[Dict] = None,
        classification: Optional[Dict] = None
    ) -> Dict:
        """
        Execute task with progressive retry

        Args:
            task: User request
            execute_fn: Function to execute (takes prompt, returns result dict)
            context: Optional context gathered
            classification: Optional task classification

        Returns:
            Result dict with 'success', 'response', 'attempts', 'final_model'
        """
        attempts = []
        current_model = self.model_router.get_execution_model()  # qwen

        # Attempt 1: Standard execution with primary model
        logging.info("Attempt 1: Standard execution (qwen)")
        prompt = self._build_standard_prompt(task, context)

        result = self._execute_attempt(
            model=current_model,
            prompt=prompt,
            execute_fn=execute_fn,
            attempt_num=1
        )

        attempts.append(result)

        if result['success']:
            logging.info("[OK] Task succeeded on first attempt")
            return {
                'success': True,
                'response': result['response'],
                'attempts': 1,
                'final_model': current_model,
                'retry_history': attempts
            }

        # Attempt 2: Enhanced prompt with same model (0s swap overhead)
        logging.warning(f"Attempt 1 failed: {result.get('error', 'Unknown error')}")
        logging.info("Attempt 2: Enhanced prompt (qwen, 0s swap)")

        enhanced_prompt = self._build_enhanced_prompt(task, context, attempts)

        result = self._execute_attempt(
            model=current_model,
            prompt=enhanced_prompt,
            execute_fn=execute_fn,
            attempt_num=2
        )

        attempts.append(result)

        if result['success']:
            logging.info("[OK] Task succeeded with enhanced prompt")
            return {
                'success': True,
                'response': result['response'],
                'attempts': 2,
                'final_model': current_model,
                'retry_history': attempts
            }

        # Attempt 3: Emergency model (deepseek) - only if critical
        is_critical = self._is_critical_task(task, classification, attempts)

        if not is_critical:
            logging.warning("Task failed but not critical - giving up")
            return {
                'success': False,
                'error': 'Max retries exceeded (non-critical task)',
                'attempts': 2,
                'final_model': current_model,
                'retry_history': attempts
            }

        # Escalate to emergency model
        logging.warning("Attempt 2 failed - escalating to deepseek (2.5s swap)")
        emergency_model = self.model_router.get_fixer_model()

        # Load emergency model (2.5s swap)
        self.model_manager.ensure_in_vram(emergency_model, 'emergency_retry')

        debugging_prompt = self._build_debugging_prompt(task, context, attempts)

        result = self._execute_attempt(
            model=emergency_model,
            prompt=debugging_prompt,
            execute_fn=execute_fn,
            attempt_num=3
        )

        attempts.append(result)

        if result['success']:
            logging.info("[OK] Task succeeded with emergency model (deepseek)")
            return {
                'success': True,
                'response': result['response'],
                'attempts': 3,
                'final_model': emergency_model,
                'retry_history': attempts
            }
        else:
            logging.error("All retry attempts exhausted")
            return {
                'success': False,
                'error': 'All retry attempts failed',
                'attempts': 3,
                'final_model': emergency_model,
                'retry_history': attempts
            }

    def _execute_attempt(
        self,
        model: str,
        prompt: str,
        execute_fn,
        attempt_num: int
    ) -> Dict:
        """Execute a single attempt"""
        try:
            result = execute_fn(prompt, model)

            # Normalize result format
            if isinstance(result, str):
                result = {'response': result, 'success': True}

            return {
                'success': result.get('success', True),
                'response': result.get('response', ''),
                'error': result.get('error'),
                'model': model,
                'attempt': attempt_num
            }

        except Exception as e:
            logging.error(f"Attempt {attempt_num} exception: {e}")
            return {
                'success': False,
                'response': '',
                'error': str(e),
                'model': model,
                'attempt': attempt_num
            }

    def _build_standard_prompt(self, task: str, context: Optional[Dict]) -> str:
        """Build standard prompt for first attempt"""
        prompt = f"Task: {task}\n\n"

        if context:
            prompt += "Context:\n"
            if context.get('summary'):
                prompt += f"{context['summary']}\n"

        return prompt

    def _build_enhanced_prompt(
        self,
        task: str,
        context: Optional[Dict],
        previous_attempts: List[Dict]
    ) -> str:
        """
        Build enhanced prompt with failure analysis

        Same model (0s swap overhead), better instructions
        """
        prompt = f"RETRY ATTEMPT - Previous attempt failed\n\n"
        prompt += f"Original Task: {task}\n\n"

        # Add failure context
        if previous_attempts:
            last_attempt = previous_attempts[-1]
            error = last_attempt.get('error', 'Unknown error')
            prompt += f"Previous Error: {error}\n\n"

        prompt += "INSTRUCTIONS:\n"
        prompt += "1. Carefully analyze why the previous attempt failed\n"
        prompt += "2. Use a different approach to solve the task\n"
        prompt += "3. Double-check your work before responding\n"
        prompt += "4. If the task requires file operations, verify paths exist\n\n"

        if context:
            prompt += f"Context: {context.get('summary', '')}\n\n"

        prompt += "Please retry the task with these improvements:\n"

        return prompt

    def _build_debugging_prompt(
        self,
        task: str,
        context: Optional[Dict],
        previous_attempts: List[Dict]
    ) -> str:
        """
        Build detailed debugging prompt for emergency model

        Emergency model (2.5s swap), deep analysis
        """
        prompt = f"EMERGENCY RETRY - Multiple failures detected\n\n"
        prompt += f"Original Task: {task}\n\n"

        # Detailed failure history
        prompt += "FAILURE HISTORY:\n"
        for i, attempt in enumerate(previous_attempts, 1):
            prompt += f"\nAttempt {i} ({attempt['model']}):\n"
            prompt += f"  Error: {attempt.get('error', 'Failed')}\n"
            if attempt.get('response'):
                response_preview = attempt['response'][:200]
                prompt += f"  Response: {response_preview}...\n"

        prompt += "\nDEEP ANALYSIS REQUIRED:\n"
        prompt += "1. Analyze all previous failure modes\n"
        prompt += "2. Identify root cause of failures\n"
        prompt += "3. Design a completely different approach\n"
        prompt += "4. Consider edge cases and potential issues\n"
        prompt += "5. Provide detailed reasoning for your solution\n\n"

        if context:
            prompt += f"Context: {context.get('summary', '')}\n\n"

        prompt += "Use your advanced reasoning capabilities to solve this task:\n"

        return prompt

    def _is_critical_task(
        self,
        task: str,
        classification: Optional[Dict],
        attempts: List[Dict]
    ) -> bool:
        """
        Determine if task is critical enough to warrant emergency model swap

        Critical if:
        - Task is complex (already invested time)
        - Multiple files involved (high impact)
        - User explicitly requested (contains "important", "critical")
        - Previous attempts had partial success
        """
        # Check task urgency keywords
        urgency_keywords = ['important', 'critical', 'urgent', 'must', 'required']
        if any(kw in task.lower() for kw in urgency_keywords):
            logging.info("Task marked as critical (urgency keywords)")
            return True

        # Check if task is complex (worth emergency retry)
        if classification and classification.get('tier') == 'complex':
            logging.info("Task marked as critical (complex tier)")
            return True

        # Check if previous attempts had partial success
        if attempts:
            for attempt in attempts:
                if attempt.get('response') and len(attempt['response']) > 100:
                    logging.info("Task marked as critical (partial success detected)")
                    return True

        # Default: not critical
        logging.info("Task not critical - won't escalate to emergency model")
        return False

    def get_retry_statistics(self, retry_history: List[Dict]) -> Dict:
        """Get statistics from retry history"""
        if not retry_history:
            return {}

        total_attempts = len(retry_history)
        models_used = list(set(a['model'] for a in retry_history))

        return {
            'total_attempts': total_attempts,
            'models_used': models_used,
            'swap_count': len(models_used) - 1,  # Swaps = models - 1
            'final_success': retry_history[-1].get('success', False)
        }
