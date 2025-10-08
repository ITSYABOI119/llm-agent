"""
Single-Phase Executor
Executes tasks using a single model for both reasoning and action
"""

import logging
import requests
import re
from typing import Dict, Any, List, Callable, Optional
from pathlib import Path


class SinglePhaseExecutor:
    """
    Execute tasks using a single model.

    The model handles both reasoning and tool generation in one pass.
    Best for: simple tasks, code generation, file operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize single-phase executor.

        Args:
            config: Agent configuration dict
        """
        self.config = config
        self.api_url = f"http://{config['ollama']['host']}:{config['ollama']['port']}"
        self.workspace = Path(config['agent']['workspace'])

    def execute(
        self,
        user_message: str,
        selected_model: str,
        session_context: str,
        agent_rules: Optional[str],
        tools_description: str,
        parse_callback: Callable[[str], List[Dict[str, Any]]],
        execute_callback: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        history_callback: Callable[[str, str], None]
    ) -> str:
        """
        Execute task using single model.

        Args:
            user_message: User's request
            selected_model: Model to use
            session_context: Session file tracking context
            agent_rules: Project-specific rules from .agentrules
            tools_description: Available tools description
            parse_callback: Function to parse tool calls from LLM response
            execute_callback: Function to execute a tool
            history_callback: Function to add message to session history

        Returns:
            Final response message
        """
        try:
            # Build reasoning instructions
            is_reasoning_model = self._is_reasoning_model(selected_model)

            if is_reasoning_model:
                reasoning_instructions = """
⚡ REASONING MODEL - IMPORTANT ⚡
You can think step-by-step using <think>...</think> tags, but you MUST also output tool calls.

Response structure:
1. <think>Your reasoning here</think> (optional)
2. TOOL: tool_name | PARAMS: {"param": "value"} (REQUIRED)

Never output ONLY thinking - always follow with actual TOOL calls.
"""
            else:
                reasoning_instructions = ""

            # Build rules section
            rules_section = f"\nPROJECT-SPECIFIC RULES:\n{agent_rules}\n" if agent_rules else ""

            # Build system prompt
            system_prompt = f"""You are {self.config['agent']['name']}, an AI assistant with access to various tools.
You can execute commands, manage files, search information, and more.
Your workspace is: {self.config['agent']['workspace']}

{session_context}
{rules_section}
{reasoning_instructions}
Available tools:
{tools_description}

TOOL USAGE FORMAT:
To use a tool, respond EXACTLY in this format:
TOOL: tool_name | PARAMS: {{"param1": "value1", "param2": "value2"}}

CRITICAL JSON FORMATTING RULES:
- Parameters MUST be valid JSON
- For multi-line strings, use \\n for newlines (e.g., "line1\\nline2")
- NEVER use triple quotes in JSON - they are invalid
- Always escape backslashes and quotes inside strings
- Example: {{"content": "def add(a, b):\\n    return a + b\\n"}}

You can call multiple tools in one response. After tool execution, you'll see the results.

FILE WRITING RULES (CRITICAL):
- Use write_file ONLY for creating NEW files that don't exist yet
- NEVER use write_file to modify existing files - it will OVERWRITE them completely
- Use edit_file to modify/add content to existing files with these modes:

  SIMPLE MODES:
  - mode="append" - add content to end of file
  - mode="prepend" - add content to beginning of file
  - mode="replace" - find and replace ALL occurrences (needs search + replace params)
  - mode="replace_once" - replace only FIRST occurrence (needs search + replace params)

  ADVANCED MODES (for precise code editing):
  - mode="insert_at_line" - insert content at specific line (needs line_number param)
  - mode="replace_lines" - replace line range (needs start_line + end_line params)
  - mode="insert_after" - insert after line matching pattern (needs insert_after param)
  - mode="insert_before" - insert before line matching pattern (needs insert_before param)

  EXAMPLES:
  - Add function to end:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "append", "content": "def new_func():\\n    pass\\n"}}

  - Insert at line 5:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_at_line", "line_number": 5, "content": "import os\\n"}}

  - Replace lines 10-15:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "replace_lines", "start_line": 10, "end_line": 15, "content": "new code\\n"}}

  - Insert after pattern (IMPORTANT - use SHORT pattern that appears in a SINGLE line):
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_after", "insert_after": "import sys", "content": "import os\\n"}}
    TOOL: edit_file | PARAMS: {{"path": "calc.py", "mode": "insert_after", "insert_after": "def multiply", "content": "\\ndef divide(a, b):\\n    return a / b\\n"}}

  - Insert before pattern (IMPORTANT - use SHORT pattern that appears in a SINGLE line):
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_before", "insert_before": "def main", "content": "# Main function\\n"}}

  - Find and replace text:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "replace", "search": "old_name", "replace": "new_name"}}

- Use RELATIVE paths (e.g., "my_app/src/main.py" NOT "c:\\Users\\...")

CODEBASE UNDERSTANDING (RAG):
- Use search_codebase to find relevant code semantically
- Run index_codebase once to index the workspace
- RAG search helps you understand existing code before making changes
- Check rag_stats to see if codebase is indexed

Respond helpfully to user requests. Execute tools when needed."""

            # Call Ollama API
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": selected_model,
                    "prompt": f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:",
                    "stream": False,
                    "options": {
                        "temperature": self.config['ollama'].get('temperature', 0.7),
                        "num_ctx": self.config['ollama'].get('num_ctx', 8192),
                        "num_predict": self.config['ollama'].get('num_predict', 2048)
                    }
                },
                timeout=self.config['ollama'].get('timeout', 120)
            )

            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logging.error(error_msg)
                return f"Error: {error_msg}"

            # Parse response
            result = response.json()
            assistant_message = result.get('response', '')

            # Log thinking if present (for reasoning models)
            if '<think>' in assistant_message.lower():
                thinks = re.findall(r'<think>(.*?)</think>', assistant_message, re.DOTALL | re.IGNORECASE)
                for i, thought in enumerate(thinks, 1):
                    thought_preview = thought.strip()[:300]
                    if len(thought.strip()) > 300:
                        thought_preview += "..."
                    logging.info(f"[REASONING BLOCK {i}]: {thought_preview}")

            # Parse and execute tool calls
            tool_calls = parse_callback(assistant_message)

            if tool_calls:
                # Execute all tools and collect results
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    params = tool_call.get('params', {})

                    logging.info(f"Executing tool: {tool_name} with params: {params}")
                    result = execute_callback(tool_name, params)
                    tool_results.append({
                        'tool': tool_name,
                        'result': result
                    })

                # Build response with tool results
                response_parts = []

                # Add any text before the tool calls
                first_tool_pos = assistant_message.find('TOOL:')
                if first_tool_pos > 0:
                    response_parts.append(assistant_message[:first_tool_pos].strip())

                # Add tool execution results
                for tr in tool_results:
                    response_parts.append(f"\n[Executed: {tr['tool']}]")
                    if tr['result'].get('success'):
                        if 'message' in tr['result']:
                            response_parts.append(tr['result']['message'])
                        elif 'results' in tr['result']:  # For search results
                            response_parts.append(f"Found {tr['result'].get('count', 0)} results")
                        elif 'files_indexed' in tr['result']:  # For indexing
                            response_parts.append(f"Indexed {tr['result']['files_indexed']} files ({tr['result']['total_chunks']} chunks)")
                        elif 'total_chunks' in tr['result']:  # For stats
                            response_parts.append(f"RAG database contains {tr['result']['total_chunks']} chunks")
                        else:
                            response_parts.append(str(tr['result']))
                    else:
                        response_parts.append(f"Error: {tr['result'].get('error', 'Unknown error')}")

                final_response = '\n'.join(response_parts)
            else:
                # No tool calls - handle reasoning model recovery if needed
                if is_reasoning_model and '<think>' in assistant_message and 'TOOL:' not in assistant_message.upper():
                    final_response = self._attempt_recovery(
                        user_message,
                        assistant_message,
                        parse_callback,
                        execute_callback
                    )
                else:
                    final_response = assistant_message

            # Add to session history
            history_callback("assistant", final_response)

            return final_response

        except Exception as e:
            logging.error(f"Error in single-phase execution: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _is_reasoning_model(self, model_name: str) -> bool:
        """Check if model is a reasoning model based on name."""
        reasoning_models = [
            'openthinker', 'deepseek-r1', 'qwen-r1', 'qwq',
            'thinking', 'reasoning', 'r1', '-r-'
        ]
        return any(rm in model_name.lower() for rm in reasoning_models)

    def _attempt_recovery(
        self,
        user_message: str,
        assistant_message: str,
        parse_callback: Callable,
        execute_callback: Callable
    ) -> str:
        """
        Attempt to recover from reasoning model stuck in thinking.

        Args:
            user_message: Original user request
            assistant_message: LLM response with thinking but no tool calls
            parse_callback: Function to parse tool calls
            execute_callback: Function to execute tools

        Returns:
            Recovery result message
        """
        logging.warning("Reasoning model output thinking but no tool calls - attempting recovery")

        # Try ONE more time with a direct prompt
        followup_prompt = f"""Request: {user_message}

Output the tool call needed to complete this request.
Format: TOOL: tool_name | PARAMS: {{"param": "value"}}
Output only the tool call:"""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.config['ollama']['model'],
                    "prompt": followup_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 512
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                recovery_response = response.json().get('response', '')
                logging.info(f"Recovery attempt response: {recovery_response[:200]}")

                # Try to parse tool calls from recovery response
                recovery_tools = parse_callback(recovery_response)

                if recovery_tools:
                    logging.info(f"Recovery successful - found {len(recovery_tools)} tool calls")
                    # Execute the recovered tool calls
                    tool_results = []
                    for tool_call in recovery_tools:
                        tool_name = tool_call.get('tool')
                        params = tool_call.get('params', {})
                        logging.info(f"Executing recovered tool: {tool_name}")
                        result = execute_callback(tool_name, params)
                        tool_results.append({'tool': tool_name, 'result': result})

                    # Build response
                    response_parts = ["[Recovered tool execution after reasoning]"]
                    for tr in tool_results:
                        response_parts.append(f"\n[Executed: {tr['tool']}]")
                        if tr['result'].get('success'):
                            response_parts.append(tr['result'].get('message', str(tr['result'])))
                        else:
                            response_parts.append(f"Error: {tr['result'].get('error')}")

                    return '\n'.join(response_parts)
                else:
                    # Recovery failed - return thinking summary
                    logging.warning("Recovery failed - no valid tool calls generated")
                    return f"I analyzed the task but couldn't generate valid tool calls.\n\nReasoning summary: {assistant_message[:500]}"
            else:
                return assistant_message
        except Exception as e:
            logging.error(f"Error in recovery attempt: {e}")
            return assistant_message
