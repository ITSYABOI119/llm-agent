"""
Two-Phase Executor - Combines planning (reasoning model) with execution (code model)
"""
import logging
import requests
import time
from typing import Dict, Callable, Optional, Any
from tools.event_bus import get_event_bus
from tools.execution_history import ExecutionHistory  # Phase 2


class TwoPhaseExecutor:
    """Executes complex tasks in two phases: Plan → Execute"""

    def __init__(self, api_url: str, config: Dict):
        self.api_url = api_url
        self.config = config

        # Phase 2: Execution history tracking
        history_enabled = config.get('execution_history', {}).get('enabled', True)
        self.history = ExecutionHistory() if history_enabled else None

    def execute(self, user_message: str, planning_model: str, execution_model: str,
                parse_callback: Callable, execute_callback: Callable,
                task_analysis: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Execute a task in two phases

        Args:
            user_message: Original user request
            planning_model: Model for planning phase (e.g., openthinker3-7b)
            execution_model: Model for execution phase (e.g., qwen2.5-coder:7b)
            parse_callback: Function to parse tool calls from response
            execute_callback: Function to execute tool calls

        Returns:
            {
                'success': bool,
                'plan': str,
                'execution_result': str,
                'phases': {
                    'planning': {...},
                    'execution': {...}
                }
            }
        """
        # Phase 2: Initialize execution tracking
        start_time = time.time()
        tool_calls_executed = []

        # Get event bus for streaming
        event_bus = get_event_bus()
        streaming_enabled = self.config.get('ollama', {}).get('multi_model', {}).get('streaming', {}).get('enabled', False)

        logging.info("="*80)
        logging.info("TWO-PHASE EXECUTION STARTING")
        logging.info("="*80)

        # Emit two-phase start event
        if streaming_enabled:
            event_bus.publish('status', {
                'phase': 'two_phase_start',
                'planning_model': planning_model,
                'execution_model': execution_model
            })

        # Phase 1: Planning with reasoning model
        logging.info(f"PHASE 1: Planning with {planning_model}")

        # Emit planning phase start
        if streaming_enabled:
            event_bus.publish('status', {
                'phase': 'planning',
                'model': planning_model
            })

        plan_result = self._planning_phase(user_message, planning_model)

        if not plan_result['success']:
            # Phase 2: Log failed execution (planning phase)
            if self.history and task_analysis:
                self.history.log_execution(
                    task_text=user_message,
                    task_analysis=task_analysis,
                    execution_mode='two-phase',
                    planning_model=planning_model,
                    execution_model=execution_model,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_type='PlanningPhaseError',
                    error_message=plan_result.get('error', 'Planning phase failed')
                )

            return {
                'success': False,
                'error': f"Planning phase failed: {plan_result.get('error')}",
                'phases': {'planning': plan_result}
            }

        plan = plan_result['plan']
        logging.info(f"Planning complete. Plan length: {len(plan)} chars")
        logging.info(f"Plan preview: {plan[:200]}...")

        # Phase 2: Execution with code model
        logging.info(f"PHASE 2: Execution with {execution_model}")

        # Emit execution phase start
        if streaming_enabled:
            event_bus.publish('status', {
                'phase': 'execution',
                'model': execution_model
            })

        execution_result = self._execution_phase(
            user_message, plan, execution_model, parse_callback, execute_callback, tool_calls_executed
        )

        if not execution_result['success']:
            # Phase 2: Log failed execution (execution phase)
            if self.history and task_analysis:
                self.history.log_execution(
                    task_text=user_message,
                    task_analysis=task_analysis,
                    execution_mode='two-phase',
                    planning_model=planning_model,
                    execution_model=execution_model,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_type='ExecutionPhaseError',
                    error_message=execution_result.get('error', 'Execution phase failed'),
                    tool_calls=tool_calls_executed
                )

            return {
                'success': False,
                'error': f"Execution phase failed: {execution_result.get('error')}",
                'plan': plan,
                'phases': {
                    'planning': plan_result,
                    'execution': execution_result
                }
            }

        logging.info("TWO-PHASE EXECUTION COMPLETED SUCCESSFULLY")
        logging.info("="*80)

        # Phase 2: Log successful execution to history
        if self.history and task_analysis:
            self.history.log_execution(
                task_text=user_message,
                task_analysis=task_analysis,
                execution_mode='two-phase',
                planning_model=planning_model,
                execution_model=execution_model,
                success=True,
                duration_seconds=time.time() - start_time,
                tool_calls=tool_calls_executed
            )

        return {
            'success': True,
            'plan': plan,
            'execution_result': execution_result['result'],
            'tool_calls': execution_result.get('tool_calls', []),
            'phases': {
                'planning': plan_result,
                'execution': execution_result
            }
        }

    def _planning_phase(self, user_message: str, planning_model: str) -> Dict:
        """
        Phase 1: Use reasoning model to create detailed plan

        Returns plan with file structure, content ideas, and implementation approach
        """
        planning_prompt = f"""You are an expert software architect and creative designer.

User request: {user_message}

Create a DETAILED implementation plan. Include:

1. **File Structure**: What files to create and their purpose
2. **Content Design**: Specific content, styling approaches, color schemes
3. **Implementation Details**: Key features, code structure, best practices

Be specific and creative. Provide actual content ideas, not placeholders.

Format your response as a clear, structured plan:"""

        try:
            # PHASE 1 FIX: Use longer timeout for planning phase (can be complex)
            planning_timeout = self.config.get('ollama', {}).get('planning_timeout', 180)

            # PHASE 1 FIX: Enable streaming for planning phase progress
            streaming_enabled = self.config.get('ollama', {}).get('multi_model', {}).get('streaming', {}).get('enabled', False)
            event_bus = get_event_bus()

            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": planning_model,
                    "prompt": planning_prompt,
                    "stream": streaming_enabled,  # Stream if enabled
                    "options": {
                        "temperature": 0.8,  # Higher temp for creativity
                        "num_predict": 1024,
                        "num_ctx": 8192
                    }
                },
                timeout=planning_timeout,
                stream=streaming_enabled
            )

            if response.status_code == 200:
                plan = ""

                if streaming_enabled:
                    # Stream plan generation with progress updates
                    import json
                    chunk_count = 0
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk_data = json.loads(line)
                                chunk = chunk_data.get('response', '')
                                plan += chunk

                                # Emit progress every 10 chunks
                                chunk_count += 1
                                if chunk_count % 10 == 0:
                                    event_bus.publish('planning_progress', {
                                        'length': len(plan),
                                        'preview': plan[-100:] if len(plan) > 100 else plan
                                    })

                                # Show dots for progress
                                if chunk_count % 5 == 0:
                                    print(".", end="", flush=True)

                            except json.JSONDecodeError:
                                continue

                    print()  # Newline after dots
                else:
                    # Non-streaming (fallback)
                    result = response.json()
                    plan = result.get('response', '')

                # Strip any thinking tags if present
                import re
                plan = re.sub(r'<think>.*?</think>', '', plan, flags=re.DOTALL | re.IGNORECASE).strip()

                return {
                    'success': True,
                    'plan': plan,
                    'model': planning_model
                }
            else:
                return {
                    'success': False,
                    'error': f"API error: {response.status_code}"
                }

        except requests.exceptions.Timeout:
            # PHASE 1 FIX: Graceful timeout handling
            logging.error(f"Planning phase timeout after {planning_timeout}s")
            return {
                'success': False,
                'error': f"Planning phase timed out after {planning_timeout}s. Try a simpler task or increase planning_timeout in config.",
                'timeout': True
            }
        except Exception as e:
            logging.error(f"Planning phase error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _execution_phase(self, original_request: str, plan: str, execution_model: str,
                        parse_callback: Callable, execute_callback: Callable, tool_calls_executed: list) -> Dict:
        """
        Phase 2: Use code model to execute the plan with actual tool calls

        Takes the detailed plan and generates concrete tool calls
        """
        # Check if we should pass full plan (Phase 1 Enhancement)
        validation_config = self.config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('two_phase', {}).get('validation', {})
        use_full_plan = validation_config.get('full_plan_in_execution', True)

        # Use full plan or truncated (legacy behavior)
        plan_text = plan if use_full_plan else plan[:1000]

        # Simplified, direct execution prompt
        execution_prompt = f"""Task: {original_request}

Plan to implement:
{plan_text}

Generate file creation tool calls in this format:
TOOL: write_file | PARAMS: {{"path": "filename.ext", "content": "actual code here"}}

Output tool calls only:"""

        try:
            # PHASE 1 FIX: Use longer timeout for execution phase (complex multi-file tasks)
            execution_timeout = self.config.get('ollama', {}).get('execution_timeout', 240)

            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": execution_model,
                    "prompt": execution_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temp for reliable execution
                        "num_predict": self.config['ollama'].get('num_predict', 6144),  # Use config value (Phase 1: 6144)
                        "num_ctx": self.config['ollama'].get('num_ctx', 8192)
                    }
                },
                timeout=execution_timeout
            )

            if response.status_code == 200:
                result = response.json()
                execution_response = result.get('response', '')

                # Parse tool calls
                tool_calls = parse_callback(execution_response)

                if not tool_calls:
                    return {
                        'success': False,
                        'error': 'No tool calls generated',
                        'response': execution_response[:500]
                    }

                # Execute tool calls
                logging.info(f"Executing {len(tool_calls)} tool calls from plan")
                tool_results = []

                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    params = tool_call.get('params', {})

                    logging.info(f"Executing: {tool_name}")
                    tool_start = time.time()
                    result = execute_callback(tool_name, params)
                    tool_time = time.time() - tool_start

                    tool_results.append({
                        'tool': tool_name,
                        'result': result
                    })

                    # Phase 2: Track tool execution for history
                    tool_calls_executed.append({
                        'tool': tool_name,
                        'params': params,
                        'success': result.get('success', False),
                        'duration': tool_time
                    })

                # Build result summary
                success_count = sum(1 for tr in tool_results if tr['result'].get('success'))
                total_count = len(tool_results)

                return {
                    'success': success_count == total_count,
                    'result': f"Executed {success_count}/{total_count} tool calls successfully",
                    'tool_calls': tool_calls,
                    'tool_results': tool_results,
                    'model': execution_model
                }
            else:
                return {
                    'success': False,
                    'error': f"API error: {response.status_code}"
                }

        except requests.exceptions.Timeout:
            # PHASE 1 FIX: Graceful timeout handling for execution phase
            logging.error(f"Execution phase timeout after {execution_timeout}s")
            return {
                'success': False,
                'error': f"Execution phase timed out after {execution_timeout}s. The plan may be too complex. Try breaking into smaller tasks.",
                'timeout': True,
                'partial_plan': plan[:500]  # Return partial plan for context
            }
        except Exception as e:
            logging.error(f"Execution phase error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
