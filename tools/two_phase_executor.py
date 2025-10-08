"""
Two-Phase Executor - Combines planning (reasoning model) with execution (code model)
"""
import logging
import requests
from typing import Dict, Callable


class TwoPhaseExecutor:
    """Executes complex tasks in two phases: Plan → Execute"""

    def __init__(self, api_url: str, config: Dict):
        self.api_url = api_url
        self.config = config

    def execute(self, user_message: str, planning_model: str, execution_model: str,
                parse_callback: Callable, execute_callback: Callable) -> Dict:
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
        logging.info("="*80)
        logging.info("TWO-PHASE EXECUTION STARTING")
        logging.info("="*80)

        # Phase 1: Planning with reasoning model
        logging.info(f"PHASE 1: Planning with {planning_model}")
        plan_result = self._planning_phase(user_message, planning_model)

        if not plan_result['success']:
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
        execution_result = self._execution_phase(
            user_message, plan, execution_model, parse_callback, execute_callback
        )

        if not execution_result['success']:
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
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": planning_model,
                    "prompt": planning_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,  # Higher temp for creativity
                        "num_predict": 1024,
                        "num_ctx": 8192
                    }
                },
                timeout=self.config['ollama'].get('timeout', 120)
            )

            if response.status_code == 200:
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

        except Exception as e:
            logging.error(f"Planning phase error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _execution_phase(self, original_request: str, plan: str, execution_model: str,
                        parse_callback: Callable, execute_callback: Callable) -> Dict:
        """
        Phase 2: Use code model to execute the plan with actual tool calls

        Takes the detailed plan and generates concrete tool calls
        """
        # Simplified, direct execution prompt
        execution_prompt = f"""Task: {original_request}

Plan to implement:
{plan[:1000]}

Generate file creation tool calls in this format:
TOOL: write_file | PARAMS: {{"path": "filename.ext", "content": "actual code here"}}

Output tool calls only:"""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": execution_model,
                    "prompt": execution_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temp for reliable execution
                        "num_predict": 4096,  # Much more tokens for multi-file generation
                        "num_ctx": 8192
                    }
                },
                timeout=self.config['ollama'].get('timeout', 180)
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
                    result = execute_callback(tool_name, params)
                    tool_results.append({
                        'tool': tool_name,
                        'result': result
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

        except Exception as e:
            logging.error(f"Execution phase error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
