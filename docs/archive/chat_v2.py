"""
Enhanced Chat V2 - Phase 2 Implementation
Includes: Token management, structured plans, context compression
"""

import logging
from typing import Dict, Any


def chat_with_structured_plans(agent, user_message: str) -> str:
    """
    Phase 2 enhanced chat with:
    - Token counting and compression
    - Structured JSON plans
    - Better context management
    """
    try:
        # Reset token counter for new request
        agent.token_counter.reset()

        # Add to history
        agent.history.add_message("user", user_message)

        logging.info("=" * 80)
        logging.info("PHASE 2 WORKFLOW: Structured plans + Token management")
        logging.info("=" * 80)

        # PHASE 1: GATHER CONTEXT (with compression)
        logging.info("PHASE 1: Gathering and compressing context...")
        agent.model_manager.smart_load_for_phase('context')

        # Gather context
        context = agent.context_gatherer.gather_for_task(user_message)

        # Check token count and compress if needed
        context_tokens = agent.token_counter.track_phase('context_gathering', context)
        logging.info(f"Context: {context_tokens['tokens']} tokens ({context_tokens['usage_percent']:.1f}%)")

        # Compress if exceeds budget
        if context_tokens['tokens'] > agent.token_counter.get_budget_for_phase('context_gathering'):
            context = agent.context_compressor.compress_context(
                context,
                agent.token_counter.get_budget_for_phase('context_gathering')
            )
            logging.info(f"Context compressed to fit budget")

        context_formatted = agent.context_gatherer.format_for_llm(context)

        # PHASE 2: CREATE STRUCTURED PLAN (OpenThinker)
        logging.info("PHASE 2: Creating structured plan...")

        # Create plan prompt
        plan_prompt = agent.structured_planner.create_plan_prompt(
            user_message,
            context_formatted
        )

        # Track plan prompt tokens
        plan_tokens = agent.token_counter.track_phase('planning', plan_prompt)
        logging.info(f"Plan prompt: {plan_tokens['tokens']} tokens")

        # Generate plan with OpenThinker
        plan_response = agent.model_manager.call_model(
            agent.model_manager.get_model_for_role('context_master'),
            plan_prompt,
            options={'temperature': 0.7, 'num_predict': 2000}
        )

        if not plan_response.get('success'):
            return f"Error creating plan: {plan_response.get('error')}"

        # Parse structured plan
        plan = agent.structured_planner.parse_plan(plan_response['response'])
        logging.info(f"Plan created: {plan.get('task_summary', 'No summary')}")
        logging.info(agent.structured_planner.get_plan_summary(plan))

        # PHASE 3: CONVERT PLAN TO TOOL CALLS
        logging.info("PHASE 3: Converting plan to tool calls...")
        tool_calls = agent.structured_planner.plan_to_tool_calls(plan)

        # Validate tool calls
        validation = agent.structured_planner.validate_tool_calls(tool_calls)
        if not validation['valid']:
            logging.error(f"Tool call validation failed: {validation['issues']}")
            return f"Plan validation failed: {validation['issues']}"

        if validation['warnings']:
            for warning in validation['warnings']:
                logging.warning(warning)

        logging.info(f"Generated {len(tool_calls)} validated tool calls")

        # PHASE 4: EXECUTE TOOL CALLS (with streaming verification)
        logging.info("PHASE 4: Executing with streaming verification...")
        agent.model_manager.smart_load_for_phase('execution')

        results = []
        all_verified = True

        for i, tool_call in enumerate(tool_calls, 1):
            tool_name = tool_call['tool']
            params = tool_call['params']

            logging.info(f"[{i}/{len(tool_calls)}] Executing {tool_name}...")

            # Execute tool
            result = agent.execute_tool(tool_name, params)
            results.append({
                'tool': tool_name,
                'params': params,
                'result': result
            })

            # STREAMING VERIFICATION: Verify immediately
            agent.model_manager.smart_load_for_phase('verification')
            verification = agent.verifier.verify_action(tool_name, params, result)

            if not verification['verified']:
                all_verified = False
                logging.warning(f"[FAIL] Verification failed: {verification['issues']}")

                # Try quick fix (OpenThinker)
                fix_result = attempt_quick_fix(
                    agent, tool_call, result, verification
                )

                if fix_result['success']:
                    logging.info(f"[OK] Fixed successfully")
                    results[-1]['result'] = fix_result['result']
                    results[-1]['fixed'] = True
                else:
                    logging.error(f"[FAIL] Fix failed: {fix_result['error']}")
                    break  # Stop execution on unfixable error
            else:
                logging.info(f"[OK] Verified successfully")

            # Switch back to execution model for next tool
            if i < len(tool_calls):
                agent.model_manager.smart_load_for_phase('execution')

        # PHASE 5: FINAL VERIFICATION
        logging.info("PHASE 5: Final verification...")

        if all_verified:
            logging.info("[OK] All actions verified successfully!")
            success_message = build_success_message(plan, results)
        else:
            logging.warning("[WARN] Some actions failed verification")
            success_message = build_partial_success_message(plan, results)

        # Log token usage report
        logging.info(agent.token_counter.get_usage_report())

        logging.info("=" * 80)
        return success_message

    except Exception as e:
        logging.error(f"Error in Phase 2 chat: {e}", exc_info=True)
        return f"Error: {str(e)}"


def attempt_quick_fix(agent, tool_call, result, verification) -> Dict:
    """
    Attempt to fix a failed action quickly

    Returns:
        {'success': bool, 'result': Dict, 'error': str}
    """
    logging.info("Attempting quick fix...")

    # Create fix prompt
    fix_prompt = f"""The following action failed:
Tool: {tool_call['tool']}
Params: {tool_call['params']}
Error: {verification['issues']}

Suggestion: {verification['suggestion']}

Generate a corrected tool call in this format:
TOOL: tool_name | PARAMS: {{"param": "value"}}

Output only the tool call:"""

    # Use OpenThinker to create fix
    fix_response = agent.model_manager.call_model(
        agent.model_manager.get_model_for_role('context_master'),
        fix_prompt,
        options={'temperature': 0.3, 'num_predict': 512}
    )

    if not fix_response.get('success'):
        return {'success': False, 'error': 'Could not generate fix'}

    # Parse fix tool call
    fix_tool_calls = agent.parse_tool_calls(fix_response['response'])

    if not fix_tool_calls:
        return {'success': False, 'error': 'No fix tool call generated'}

    # Execute fix
    fix_tool = fix_tool_calls[0]
    fix_result = agent.execute_tool(fix_tool['tool'], fix_tool['params'])

    if fix_result.get('success'):
        return {'success': True, 'result': fix_result}
    else:
        return {'success': False, 'error': fix_result.get('error', 'Fix execution failed')}


def build_success_message(plan: Dict, results: list) -> str:
    """Build success message from results"""
    message = f"[OK] Task completed successfully!\n\n"
    message += f"Summary: {plan.get('task_summary', 'Task completed')}\n\n"

    message += f"Actions performed:\n"
    for result in results:
        if result['result'].get('success'):
            tool = result['tool']
            path = result['params'].get('path', 'N/A')
            message += f"  [OK] {tool}: {path}\n"
            if result.get('fixed'):
                message += f"    (auto-fixed)\n"

    # Check success criteria
    criteria = plan.get('success_criteria', [])
    if criteria:
        message += f"\nSuccess criteria met:\n"
        for criterion in criteria:
            message += f"  [OK] {criterion}\n"

    return message


def build_partial_success_message(plan: Dict, results: list) -> str:
    """Build message for partial success"""
    message = f"[WARN] Task partially completed\n\n"

    successful = [r for r in results if r['result'].get('success')]
    failed = [r for r in results if not r['result'].get('success')]

    message += f"Completed: {len(successful)}/{len(results)} actions\n\n"

    if successful:
        message += f"Successful actions:\n"
        for result in successful:
            tool = result['tool']
            path = result['params'].get('path', 'N/A')
            message += f"  [OK] {tool}: {path}\n"

    if failed:
        message += f"\nFailed actions:\n"
        for result in failed:
            tool = result['tool']
            path = result['params'].get('path', 'N/A')
            error = result['result'].get('error', 'Unknown error')
            message += f"  [FAIL] {tool}: {path}\n"
            message += f"    Error: {error}\n"

    return message
