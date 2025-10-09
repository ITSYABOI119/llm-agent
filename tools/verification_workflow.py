"""
Verification Workflow - Cursor/Claude Code-style verification pattern
Extracted from agent.py to reduce file size
"""

import logging
from typing import Dict, Any, List, Callable


class VerificationWorkflow:
    """
    Implements gather → execute → verify → retry workflow.

    This is the Cursor/Claude Code pattern for ensuring quality results.
    """

    def __init__(self, agent):
        """
        Initialize VerificationWorkflow.

        Args:
            agent: Reference to parent Agent instance
        """
        self.agent = agent

    def chat_with_verification(self, user_message: str) -> str:
        """
        Enhanced chat with gather → execute → verify → repeat loop.

        Args:
            user_message: User's request

        Returns:
            Final response after verification
        """
        try:
            # Add to history
            self.agent.history.add_message("user", user_message)

            logging.info("=" * 80)
            logging.info("SMART ROUTING WORKFLOW (Phase 2): Minimize swaps")
            logging.info("=" * 80)

            # PHASE 0: CLASSIFY TASK (Phase 2 smart routing)
            logging.info("PHASE 0: Classifying task...")
            classification = self.agent.task_classifier.classify(user_message)
            logging.info(f"Classification: {classification['tier']} - {classification['reasoning']}")
            logging.info(f"Route: {classification['route_strategy']} - Swap overhead: {classification['estimated_swap_overhead']}s")

            # PHASE 1: GATHER CONTEXT (minimal, only if needed)
            logging.info("PHASE 1: Gathering context...")
            context = self.agent.context_gatherer.gather_for_task(user_message)
            context_formatted = self.agent.context_gatherer.format_for_llm(context)
            logging.info(f"Context gathered: {context['summary']}")

            # PHASE 2: PLAN & EXECUTE
            logging.info("PHASE 2: Planning and execution...")

            # Execute with appropriate strategy based on classification
            use_two_phase = self.agent.model_router.should_use_two_phase(classification)

            if use_two_phase:
                logging.info("Using TWO-PHASE execution (openthinker -> qwen)")
                execution_result = self._execute_two_phase_with_context(
                    user_message, context_formatted, classification
                )
            else:
                logging.info("Using SINGLE-PHASE execution (qwen only - 0s swap)")
                selected_model = self.agent.model_router.select_model_from_classification(classification)
                self.agent.model_manager.ensure_in_vram(selected_model)
                execution_result = self._execute_single_phase_with_context(
                    user_message, context_formatted, classification
                )

            # PHASE 3: VERIFY WORK
            logging.info("PHASE 3: Verifying results...")

            # Extract tool calls that were executed
            tool_calls = execution_result.get('tool_calls', [])

            if tool_calls:
                # Verify each action
                verification_results = []
                all_verified = True

                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    params = tool_call.get('params', {})
                    result = tool_call.get('result', {})

                    verification = self.agent.verifier.verify_action(tool_name, params, result)
                    verification_results.append({
                        'tool': tool_name,
                        'verification': verification
                    })

                    if not verification['verified']:
                        all_verified = False
                        logging.warning(f"Verification failed for {tool_name}: {verification['issues']}")

                # PHASE 4: RETRY IF FAILED
                if not all_verified:
                    logging.info("PHASE 4: Verification failed, attempting retry...")
                    retry_result = self._retry_failed_actions(
                        user_message, verification_results, max_retries=2
                    )
                    return retry_result
                else:
                    logging.info("✓ All actions verified successfully!")

            logging.info("=" * 80)
            return execution_result.get('response', 'Task completed')

        except Exception as e:
            logging.error(f"Error in enhanced chat: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _execute_single_phase_with_context(
        self,
        user_message: str,
        context: str,
        task_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute single-phase with context included.

        Returns dict format for verification (unlike regular _execute_single_phase
        which returns string).
        """
        # Execute and get response string
        response_string = self.agent._execute_single_phase(user_message, task_analysis)

        # Return in dict format expected by chat_with_verification
        return {
            'success': True,
            'response': response_string,
            'tool_calls': []  # TODO: Track tool calls during execution
        }

    def _execute_two_phase_with_context(
        self,
        user_message: str,
        context: str,
        task_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute two-phase with context included.

        Returns dict format for verification.
        """
        # Execute and get response string
        response_string = self.agent._execute_two_phase(user_message, task_analysis)

        # Return in dict format expected by chat_with_verification
        return {
            'success': True,
            'response': response_string,
            'tool_calls': []  # TODO: Track tool calls during execution
        }

    def _retry_failed_actions(
        self,
        user_message: str,
        verification_results: List[Dict[str, Any]],
        max_retries: int = 2
    ) -> str:
        """
        Retry failed actions with smarter model (Cursor's reapply pattern).

        Args:
            user_message: Original user request
            verification_results: List of verification results for each action
            max_retries: Maximum retry attempts

        Returns:
            Final response after retry
        """
        logging.info(f"Retrying with smarter model (max {max_retries} attempts)...")

        # Use OpenThinker to reason about failures
        self.agent.model_manager.smart_load_for_phase('debugging')

        failed_actions = [
            vr for vr in verification_results if not vr['verification']['verified']
        ]

        retry_prompt = f"""Original request: {user_message}

Some actions failed verification:
"""
        for failed in failed_actions:
            issues = failed['verification']['issues']
            suggestion = failed['verification']['suggestion']
            retry_prompt += f"\n- {failed['tool']}: {', '.join(issues)}"
            retry_prompt += f"\n  Suggestion: {suggestion}"

        retry_prompt += "\n\nAnalyze the failures and create a fix plan."

        # Use OpenThinker to create fix plan
        fix_plan_response = self.agent.model_manager.call_model(
            self.agent.model_manager.get_model_for_role('context_master'),
            retry_prompt
        )

        if not fix_plan_response.get('success'):
            return f"Retry failed: Could not create fix plan"

        fix_plan = fix_plan_response.get('response', '')
        logging.info(f"Fix plan created: {fix_plan[:200]}...")

        # Execute fix with Qwen
        self.agent.model_manager.smart_load_for_phase('execution')

        # For now, return the fix plan
        # TODO: Actually execute the fix plan
        return f"Verification failed. Fix plan created:\n{fix_plan}"
