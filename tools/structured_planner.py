"""
Structured Planner - Generate JSON plans for reliable execution
Ensures Qwen follows plans correctly with explicit tool calls
"""

import json
import logging
from typing import Dict, List, Any


class StructuredPlanner:
    """
    Generate structured, machine-readable plans
    Instead of freeform text, creates explicit JSON with tool calls
    """

    def __init__(self) -> None:
        self.plan_template = {
            "task_summary": "",
            "files_to_create": [],
            "files_to_edit": [],
            "execution_order": [],
            "success_criteria": [],
            "estimated_steps": 0
        }

    def create_plan_prompt(self, user_request: str, context: str) -> str:
        """
        Create prompt for OpenThinker to generate structured plan

        Returns a prompt that encourages JSON output
        """
        prompt = f"""You are a software architect creating a detailed implementation plan.

User Request: {user_request}

Available Context:
{context}

Create a STRUCTURED JSON plan with this exact format:

{{
    "task_summary": "Brief description of what we're building",
    "files_to_create": [
        {{
            "path": "relative/path/to/file.ext",
            "purpose": "What this file does",
            "content_template": "Code structure/template",
            "dependencies": ["package1", "package2"]
        }}
    ],
    "files_to_edit": [
        {{
            "path": "existing/file.py",
            "mode": "append|insert_after|replace_lines",
            "target": "Where to edit (line number or pattern)",
            "changes": "What to add/change"
        }}
    ],
    "execution_order": ["file1.py", "file2.py", "file3.py"],
    "success_criteria": [
        "All files created",
        "Syntax valid",
        "Imports work"
    ],
    "estimated_steps": 3
}}

IMPORTANT:
1. Use EXACT file paths relative to workspace
2. Include content templates with actual code structure
3. Specify explicit dependencies
4. Order files by dependency (dependencies first)
5. Make success criteria testable

Output ONLY the JSON plan, no other text:"""

        return prompt

    def parse_plan(self, plan_text: str) -> Dict:
        """
        Parse plan from LLM response

        Handles:
        - Direct JSON response
        - JSON wrapped in markdown
        - Extraction from text
        """
        # Try direct JSON parse
        try:
            plan = json.loads(plan_text)
            logging.info("✓ Parsed plan as direct JSON")
            return self._validate_plan(plan)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        if "```json" in plan_text or "```" in plan_text:
            try:
                # Extract content between ``` markers
                start = plan_text.find("```")
                end = plan_text.find("```", start + 3)
                json_text = plan_text[start + 3:end].strip()

                # Remove 'json' language marker if present
                if json_text.startswith("json"):
                    json_text = json_text[4:].strip()

                plan = json.loads(json_text)
                logging.info("✓ Extracted plan from markdown code block")
                return self._validate_plan(plan)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try finding JSON object in text
        try:
            start = plan_text.find("{")
            end = plan_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_text = plan_text[start:end]
                plan = json.loads(json_text)
                logging.info("✓ Extracted plan from text")
                return self._validate_plan(plan)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: Create basic plan from text
        logging.warning("Could not parse structured plan, creating basic plan")
        return self._create_fallback_plan(plan_text)

    def _validate_plan(self, plan: Dict) -> Dict:
        """Validate and normalize plan structure"""
        validated = self.plan_template.copy()

        # Ensure all required fields exist
        for key in self.plan_template.keys():
            if key in plan:
                validated[key] = plan[key]

        # Validate files_to_create structure
        if validated['files_to_create']:
            for file_spec in validated['files_to_create']:
                if 'path' not in file_spec:
                    logging.warning(f"File spec missing 'path': {file_spec}")
                    file_spec['path'] = 'unknown.txt'

        return validated

    def _create_fallback_plan(self, text: str) -> Dict:
        """Create basic plan from freeform text"""
        return {
            "task_summary": text[:200] if len(text) > 200 else text,
            "files_to_create": [],
            "files_to_edit": [],
            "execution_order": [],
            "success_criteria": ["Task completed"],
            "estimated_steps": 1,
            "note": "Fallback plan - structured parsing failed"
        }

    def plan_to_tool_calls(self, plan: Dict) -> List[Dict]:
        """
        Convert structured plan to explicit tool calls

        This is what Qwen will execute
        """
        tool_calls = []

        # 1. Create files
        for file_spec in plan.get('files_to_create', []):
            tool_calls.append({
                'tool': 'write_file',
                'params': {
                    'path': file_spec['path'],
                    'content': file_spec.get('content_template', '# TODO: Implement')
                },
                'purpose': file_spec.get('purpose', 'Create file'),
                'dependencies': file_spec.get('dependencies', [])
            })

        # 2. Edit files
        for edit_spec in plan.get('files_to_edit', []):
            tool_calls.append({
                'tool': 'edit_file',
                'params': {
                    'path': edit_spec['path'],
                    'mode': edit_spec.get('mode', 'append'),
                    'content': edit_spec.get('changes', ''),
                    # Add mode-specific params
                    **self._get_edit_params(edit_spec)
                },
                'purpose': f"Edit {edit_spec['path']}"
            })

        # 3. Order by dependencies
        ordered_calls = self._order_by_dependencies(tool_calls, plan.get('execution_order', []))

        logging.info(f"Generated {len(ordered_calls)} tool calls from plan")
        return ordered_calls

    def _get_edit_params(self, edit_spec: Dict) -> Dict:
        """Extract mode-specific parameters for edit operations"""
        params = {}
        mode = edit_spec.get('mode', 'append')

        if mode == 'insert_at_line':
            params['line_number'] = edit_spec.get('target', 1)
        elif mode in ['insert_after', 'insert_before']:
            params[mode] = edit_spec.get('target', '')
        elif mode == 'replace_lines':
            target = edit_spec.get('target', '1-1')
            if '-' in str(target):
                start, end = target.split('-')
                params['start_line'] = int(start)
                params['end_line'] = int(end)

        return params

    def _order_by_dependencies(self, tool_calls: List[Dict], order: List[str]) -> List[Dict]:
        """
        Order tool calls by dependencies

        Strategy:
        1. Follow explicit execution_order if provided
        2. Otherwise, dependency-first ordering
        """
        if not order:
            # No explicit order, return as-is
            return tool_calls

        # Create path to tool_call mapping
        path_map = {}
        for tc in tool_calls:
            path = tc['params'].get('path')
            if path:
                path_map[path] = tc

        # Order based on execution_order
        ordered = []
        for path in order:
            if path in path_map:
                ordered.append(path_map[path])
                del path_map[path]

        # Add any remaining tool calls
        ordered.extend(path_map.values())

        return ordered

    def validate_tool_calls(self, tool_calls: List[Dict]) -> Dict:
        """
        Validate tool calls before execution

        Returns:
            {
                'valid': bool,
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []

        for i, tc in enumerate(tool_calls):
            # Check required fields
            if 'tool' not in tc:
                issues.append(f"Tool call {i}: Missing 'tool' field")

            if 'params' not in tc:
                issues.append(f"Tool call {i}: Missing 'params' field")
            else:
                params = tc['params']

                # Check write_file params
                if tc.get('tool') == 'write_file':
                    if 'path' not in params:
                        issues.append(f"Tool call {i}: write_file missing 'path'")
                    if 'content' not in params:
                        warnings.append(f"Tool call {i}: write_file missing 'content'")

                # Check edit_file params
                elif tc.get('tool') == 'edit_file':
                    if 'path' not in params:
                        issues.append(f"Tool call {i}: edit_file missing 'path'")
                    if 'mode' not in params:
                        warnings.append(f"Tool call {i}: edit_file missing 'mode'")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    def get_plan_summary(self, plan: Dict) -> str:
        """Get human-readable summary of plan"""
        summary = f"""
Plan Summary
============
Task: {plan.get('task_summary', 'Unknown')}

Files to Create: {len(plan.get('files_to_create', []))}
Files to Edit: {len(plan.get('files_to_edit', []))}
Total Steps: {plan.get('estimated_steps', 0)}

Execution Order:
"""
        for i, file_path in enumerate(plan.get('execution_order', []), 1):
            summary += f"  {i}. {file_path}\n"

        summary += f"\nSuccess Criteria:\n"
        for criterion in plan.get('success_criteria', []):
            summary += f"  ✓ {criterion}\n"

        return summary
