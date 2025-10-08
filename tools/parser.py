"""
Tool Call Parser
Parses tool calls from LLM responses supporting multiple formats
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional


class ToolParser:
    """
    Parse tool calls from LLM responses.

    Supports:
    1. Direct TOOL: format (qwen2.5-coder, llama, etc.)
    2. Reasoning format with <think> tags (OpenThinker, DeepSeek-R1)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def parse(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response.

        Args:
            llm_response: Raw response from LLM

        Returns:
            List of tool calls with 'tool' and 'params' keys
        """
        # Step 1: Strip thinking tags to get action content
        cleaned_response = self._strip_thinking_tags(llm_response)

        # Step 2: Try standard TOOL: format first
        tool_calls = self._parse_standard_format(cleaned_response)

        # Step 3: If no tools found and response has thinking, try to extract intent
        if not tool_calls and '<think>' in llm_response:
            logging.info("No tool calls found after thinking - attempting to extract intent")
            # Note: For full extraction, would need LLM access
            # For now, just return empty list
            tool_calls = []

        return tool_calls

    def _strip_thinking_tags(self, response: str) -> str:
        """Remove <think>...</think> blocks to get action content"""
        # Remove all thinking blocks
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _parse_standard_format(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse TOOL: name | PARAMS: {...} format.

        Args:
            text: Text to parse

        Returns:
            List of parsed tool calls
        """
        tool_calls = []

        # Find all TOOL: positions
        tool_positions = [m.start() for m in re.finditer(r'TOOL:\s*(\w+)', text, re.IGNORECASE)]

        for i, pos in enumerate(tool_positions):
            # Extract tool name
            tool_match = re.match(r'TOOL:\s*(\w+)\s*\|\s*PARAMS:\s*', text[pos:], re.IGNORECASE)
            if not tool_match:
                continue

            tool_name = tool_match.group(1)
            json_start = pos + tool_match.end()

            # Find matching closing brace using brace counting
            brace_count = 0
            in_string = False
            escape_next = False
            json_end = -1

            for j in range(json_start, len(text)):
                char = text[j]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = j + 1
                            break

            if json_end == -1:
                logging.error(f"Could not find closing brace for tool {tool_name}")
                continue

            params_str = text[json_start:json_end]

            try:
                # Preprocess to handle common JSON issues
                # 1. Fix Windows backslashes in paths (e.g., code\file.py -> code\\file.py)
                params_str_fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrt])', r'\\\\', params_str)

                # 2. Try to handle triple-quoted strings (convert """ to ")
                params_str_fixed = params_str_fixed.replace('"""', '"')

                params = json.loads(params_str_fixed)
                tool_calls.append({
                    'tool': tool_name,
                    'params': params
                })
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse tool params for {tool_name}: {params_str[:100]}, error: {e}")
                # Try one more time without preprocessing
                try:
                    params = json.loads(params_str)
                    tool_calls.append({
                        'tool': tool_name,
                        'params': params
                    })
                except Exception:
                    continue

        return tool_calls

    def extract_thinking(self, response: str) -> List[str]:
        """
        Extract all thinking blocks from response.

        Args:
            response: LLM response

        Returns:
            List of thinking blocks
        """
        think_pattern = r'<think>(.*?)</think>'
        thinks = re.findall(think_pattern, response, re.DOTALL | re.IGNORECASE)
        return [t.strip() for t in thinks]
