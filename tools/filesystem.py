"""
File System Tools
Handles file and directory operations with safety checks
"""

import os
import logging
from pathlib import Path


class FileSystemTools:
    def __init__(self, config):
        self.config = config
        self.workspace = Path(config['agent']['workspace'])
        self.max_file_size = config['security']['max_file_size']

        # Initialize linter if enabled
        self.linter = None
        if config.get('linter', {}).get('enabled'):
            try:
                from tools.linter import PythonLinter
                self.linter = PythonLinter(config)
                logging.info("Python linter initialized")
            except ImportError:
                logging.warning("Linter not available (flake8 not installed)")
            except Exception as e:
                logging.warning(f"Failed to initialize linter: {e}")

        # Initialize transaction manager for multi-file operations
        from tools.transaction_manager import TransactionManager
        self.transaction_manager = TransactionManager(self.workspace)

        # Initialize diff editor (Phase 4)
        from tools.diff_editor import DiffEditor
        self.diff_editor = DiffEditor(self.workspace)
    
    def _get_safe_path(self, relative_path):
        """Convert relative path to absolute path and validate it's within workspace"""
        # Resolve the full path
        full_path = (self.workspace / relative_path).resolve()
        
        # Check if path is within workspace
        try:
            full_path.relative_to(self.workspace)
        except ValueError:
            raise PermissionError(f"Path {relative_path} is outside workspace")
        
        return full_path
    
    def create_folder(self, path):
        """Create a new folder"""
        try:
            full_path = self._get_safe_path(path)
            full_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created folder: {full_path}")
            return {
                "success": True,
                "message": f"Folder created: {path}",
                "path": str(full_path)
            }
        except Exception as e:
            logging.error(f"Error creating folder: {e}")
            return {"success": False, "error": str(e)}
    
    def write_file(self, path, content):
        """Write content to a file"""
        try:
            # Check file size
            content_size = len(content.encode('utf-8'))
            if content_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Content size ({content_size}) exceeds maximum ({self.max_file_size})"
                }

            # Validate Python syntax before writing
            warnings = []
            if path.endswith('.py'):
                validation = self._validate_python_syntax(content)
                if not validation['valid']:
                    return {
                        "success": False,
                        "error": f"Python syntax error: {validation['error']}",
                        "suggestion": "Fix syntax errors in the content before writing"
                    }

                # Run linter (non-blocking, provides quality feedback)
                lint_result = self._lint_python_code(content, path)
                if lint_result.get('has_issues'):
                    logging.warning(f"Linting issues in {path}: {lint_result['summary']}")
                    warnings.append(f"Code quality: {lint_result['summary']}")
                    if lint_result.get('suggestion'):
                        warnings.append(lint_result['suggestion'])

            full_path = self._get_safe_path(path)

            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content)
            logging.info(f"Wrote file: {full_path} ({content_size} bytes)")

            result = {
                "success": True,
                "message": f"File written: {path}",
                "path": str(full_path),
                "size": content_size
            }

            # Add warnings if any (non-blocking)
            if warnings:
                result['warnings'] = warnings

            return result
        except Exception as e:
            logging.error(f"Error writing file: {e}")
            return {"success": False, "error": str(e)}
    
    def read_file(self, path):
        """Read contents of a file"""
        try:
            full_path = self._get_safe_path(path)
            
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            if not full_path.is_file():
                return {"success": False, "error": f"Not a file: {path}"}
            
            # Check file size
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"File too large ({file_size} bytes, max: {self.max_file_size})"
                }
            
            content = full_path.read_text()
            logging.info(f"Read file: {full_path} ({file_size} bytes)")
            
            return {
                "success": True,
                "content": content,
                "path": str(full_path),
                "size": file_size
            }
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path="."):
        """List contents of a directory"""
        try:
            full_path = self._get_safe_path(path)
            
            if not full_path.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            
            if not full_path.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            logging.info(f"Listed directory: {full_path} ({len(items)} items)")
            
            return {
                "success": True,
                "path": str(full_path),
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            logging.error(f"Error listing directory: {e}")
            return {"success": False, "error": str(e)}
    
    def edit_file(self, path, mode="append", content="", search="", replace="",
                   line_number=None, start_line=None, end_line=None, insert_after="", insert_before=""):
        """
        Edit an existing file with advanced editing modes

        Modes:
        - append: Add content to the end of the file
        - prepend: Add content to the beginning of the file
        - replace: Search for text and replace it (ALL occurrences)
        - replace_once: Replace only first occurrence of search text
        - insert_at_line: Insert content at specific line number (line_number param)
        - replace_lines: Replace line range (start_line, end_line params)
        - insert_after: Insert content after first line matching pattern (insert_after param)
        - insert_before: Insert content before first line matching pattern (insert_before param)

        Parameters:
        - content: New content to add/insert
        - search: Text to search for (for replace modes)
        - replace: Replacement text (for replace modes)
        - line_number: Line number for insert_at_line mode (1-based)
        - start_line, end_line: Line range for replace_lines mode (1-based, inclusive)
        - insert_after: Pattern to search for when using insert_after mode
        - insert_before: Pattern to search for when using insert_before mode
        """
        try:
            full_path = self._get_safe_path(path)

            if not full_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            if not full_path.is_file():
                return {"success": False, "error": f"Not a file: {path}"}

            # Read existing content
            existing_content = full_path.read_text()
            lines = existing_content.split('\n')

            # Apply edit based on mode
            if mode == "append":
                new_content = existing_content + content

            elif mode == "prepend":
                new_content = content + existing_content

            elif mode == "replace":
                if not search:
                    return {"success": False, "error": "search parameter required for replace mode"}
                if search not in existing_content:
                    return {"success": False, "error": f"Search text not found: {search}"}
                new_content = existing_content.replace(search, replace)

            elif mode == "replace_once":
                if not search:
                    return {"success": False, "error": "search parameter required for replace_once mode"}
                if search not in existing_content:
                    return {"success": False, "error": f"Search text not found: {search}"}
                new_content = existing_content.replace(search, replace, 1)

            elif mode == "insert_at_line":
                if line_number is None:
                    return {"success": False, "error": "line_number parameter required for insert_at_line mode"}
                if line_number < 1 or line_number > len(lines) + 1:
                    return {"success": False, "error": f"Invalid line_number: {line_number} (file has {len(lines)} lines)"}
                # Insert at line (1-based indexing)
                lines.insert(line_number - 1, content)
                new_content = '\n'.join(lines)

            elif mode == "replace_lines":
                if start_line is None or end_line is None:
                    return {"success": False, "error": "start_line and end_line parameters required for replace_lines mode"}
                if start_line < 1 or end_line > len(lines) or start_line > end_line:
                    return {"success": False, "error": f"Invalid line range: {start_line}-{end_line} (file has {len(lines)} lines)"}
                # Replace line range (1-based indexing, inclusive)
                new_lines = lines[:start_line-1] + [content] + lines[end_line:]
                new_content = '\n'.join(new_lines)

            elif mode == "insert_after":
                if not insert_after:
                    return {"success": False, "error": "insert_after parameter required for this mode"}

                # Auto-correct multi-line patterns
                normalized_pattern, was_normalized = self._normalize_pattern(insert_after)
                if was_normalized:
                    logging.warning(f"Pattern auto-corrected. Use short patterns like '{normalized_pattern}' instead of multi-line patterns")

                # Find first line matching pattern
                found = False
                for i, line in enumerate(lines):
                    if normalized_pattern in line:
                        # For Python files, use smart insertion (after function/class end)
                        if path.endswith('.py'):
                            insert_idx = self._find_function_or_class_end(lines, normalized_pattern, i)
                            logging.info(f"Smart insert_after: Found '{normalized_pattern}' at line {i+1}, inserting at line {insert_idx+1}")
                        else:
                            insert_idx = i + 1
                        lines.insert(insert_idx, content)
                        found = True
                        break
                if not found:
                    suggestion = f"Try a shorter pattern like '{normalized_pattern.split('(')[0]}'" if '(' in normalized_pattern else ""
                    return {"success": False, "error": f"Pattern not found: {normalized_pattern}. {suggestion}"}
                new_content = '\n'.join(lines)

            elif mode == "insert_before":
                if not insert_before:
                    return {"success": False, "error": "insert_before parameter required for this mode"}

                # Auto-correct multi-line patterns
                normalized_pattern, was_normalized = self._normalize_pattern(insert_before)
                if was_normalized:
                    logging.warning(f"Pattern auto-corrected. Use short patterns like '{normalized_pattern}' instead of multi-line patterns")

                # Find first line matching pattern
                found = False
                for i, line in enumerate(lines):
                    if normalized_pattern in line:
                        lines.insert(i, content)
                        found = True
                        break
                if not found:
                    suggestion = f"Try a shorter pattern like '{normalized_pattern.split('(')[0]}'" if '(' in normalized_pattern else ""
                    return {"success": False, "error": f"Pattern not found: {normalized_pattern}. {suggestion}"}
                new_content = '\n'.join(lines)

            else:
                return {"success": False, "error": f"Invalid mode: {mode}. Valid modes: append, prepend, replace, replace_once, insert_at_line, replace_lines, insert_after, insert_before"}

            # Check file size
            content_size = len(new_content.encode('utf-8'))
            if content_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Edited content size ({content_size}) exceeds maximum ({self.max_file_size})"
                }

            # Validate Python syntax before writing
            warnings = []
            if path.endswith('.py'):
                validation = self._validate_python_syntax(new_content)
                if not validation['valid']:
                    return {
                        "success": False,
                        "error": f"Python syntax error after edit: {validation['error']}",
                        "suggestion": "The edit would create invalid Python syntax. Please fix the content."
                    }

                # Run linter (non-blocking, provides quality feedback)
                lint_result = self._lint_python_code(new_content, path)
                if lint_result.get('has_issues'):
                    logging.warning(f"Linting issues in {path}: {lint_result['summary']}")
                    warnings.append(f"Code quality: {lint_result['summary']}")
                    if lint_result.get('suggestion'):
                        warnings.append(lint_result['suggestion'])

            # Write updated content
            full_path.write_text(new_content)
            logging.info(f"Edited file ({mode}): {full_path} ({content_size} bytes)")

            result = {
                "success": True,
                "message": f"File edited ({mode}): {path}",
                "path": str(full_path),
                "size": content_size,
                "mode": mode
            }

            # Add warnings if present
            if warnings:
                result['warnings'] = warnings

            return result
        except Exception as e:
            logging.error(f"Error editing file: {e}")
            return {"success": False, "error": str(e)}

    def _normalize_pattern(self, pattern):
        """
        Normalize search pattern - extract single-line pattern from multi-line input

        This handles cases where LLM provides full function body instead of just the function name.
        Example: "def multiply(a, b):\n    return a * b" becomes "def multiply"

        Returns: (normalized_pattern, was_normalized)
        """
        if not pattern:
            return pattern, False

        # Check if pattern contains newlines (multi-line)
        if '\n' in pattern:
            # Extract first meaningful non-empty line
            lines = [l.strip() for l in pattern.split('\n') if l.strip()]
            if lines:
                normalized = lines[0]
                logging.info(f"Auto-corrected multi-line pattern: '{pattern[:50]}...' -> '{normalized}'")
                return normalized, True
            return pattern, False

        return pattern.strip(), False

    def _validate_python_syntax(self, code):
        """
        Validate Python code syntax using AST parser
        Returns: {"valid": bool, "error": str}
        """
        try:
            import ast
            ast.parse(code)
            return {"valid": True, "error": None}
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}"
            if e.offset:
                error_msg += f", Column {e.offset}"
            error_msg += f": {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.strip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return {"valid": False, "error": error_msg}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _lint_python_code(self, code, file_path="temp.py"):
        """
        Run linter on Python code (optional quality check beyond syntax)

        Returns: {"has_issues": bool, "summary": str, "suggestion": str, "issues": list}
        """
        if not self.linter:
            return {"has_issues": False, "summary": "Linter not enabled", "issues": []}

        try:
            return self.linter.lint_code(code, file_path)
        except Exception as e:
            logging.warning(f"Linting failed: {e}")
            return {"has_issues": False, "summary": f"Linting error: {e}", "issues": []}

    def _find_function_or_class_end(self, lines, pattern, match_line_idx):
        """
        Find the end of a function or class definition starting at match_line_idx
        Returns the line index after the function/class ends, or match_line_idx + 1 if not a function/class
        """
        # Check if the matched line is a function or class definition
        match_line = lines[match_line_idx].strip()
        if not (match_line.startswith('def ') or match_line.startswith('class ')):
            return match_line_idx + 1

        # Get the indentation level of the function/class
        base_indent = len(lines[match_line_idx]) - len(lines[match_line_idx].lstrip())

        # Find where the function/class ends
        for i in range(match_line_idx + 1, len(lines)):
            line = lines[i]

            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Check indentation
            current_indent = len(line) - len(line.lstrip())

            # If we find a line at the same or lower indentation, the function/class has ended
            if current_indent <= base_indent:
                return i

        # If we reach here, the function/class extends to the end of the file
        return len(lines)

    def smart_edit(self, path, instruction, llm_callback=None):
        """
        Smart code editing using natural language instructions.

        Args:
            path: File path to edit
            instruction: Natural language description of the change (e.g., "Add error handling to divide function")
            llm_callback: Function to call LLM for code generation

        Returns:
            Dict with success status and details
        """
        try:
            # Validate LLM callback is provided
            if not llm_callback:
                return {
                    "success": False,
                    "error": "smart_edit requires LLM integration (llm_callback not provided)"
                }

            # Read current file content
            full_path = self._get_safe_path(path)
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            current_content = full_path.read_text()

            # Build prompt for LLM to generate edit strategy
            prompt = f"""You are a precise code editing assistant. Analyze the code and generate an edit strategy.

Current file content:
```
{current_content}
```

Instruction: {instruction}

Generate a JSON response with this exact structure:
{{
    "analysis": "Brief explanation of what needs to change",
    "strategy": "append|prepend|replace|insert_after|insert_before",
    "pattern": "The search pattern (only for insert_after/insert_before/replace)",
    "new_code": "The exact code to add or use as replacement"
}}

Rules:
1. For insert_after/insert_before: Use SHORT single-line patterns (e.g., "def multiply" not full function)
2. For replace: Provide both pattern and new_code
3. For append/prepend: Only provide new_code
4. Keep existing code style and indentation
5. new_code should be ready to insert (proper indentation included)
6. IMPORTANT: In new_code field, use \\n for newlines, not triple quotes. Multi-line code must be a single JSON string with escaped newlines.
   Example: "new_code": "\\ndef divide(a, b):\\n    if b == 0:\\n        return 'Error'\\n    return a / b\\n"

Return ONLY the JSON, no other text."""

            # Call LLM to get edit strategy
            logging.info(f"smart_edit: Analyzing '{instruction}' for {path}")
            llm_response = llm_callback(prompt)

            # Parse LLM response
            import json
            try:
                # Extract JSON from response (handle markdown code blocks)
                response_text = llm_response.strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                edit_plan = json.loads(response_text)

                # Validate required fields
                if "strategy" not in edit_plan or "new_code" not in edit_plan:
                    return {
                        "success": False,
                        "error": f"LLM response missing required fields: {edit_plan}"
                    }

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse LLM response as JSON: {llm_response}")
                return {
                    "success": False,
                    "error": f"Could not parse LLM response: {e}",
                    "llm_response": llm_response
                }

            # Log the edit plan
            logging.info(f"smart_edit plan: {edit_plan.get('analysis', 'No analysis')}")
            logging.info(f"smart_edit strategy: {edit_plan['strategy']}")

            # Execute the edit using existing edit_file method
            strategy = edit_plan["strategy"]
            new_code = edit_plan["new_code"]
            pattern = edit_plan.get("pattern", "")

            if strategy == "append":
                result = self.edit_file(path, mode="append", content=new_code)
            elif strategy == "prepend":
                result = self.edit_file(path, mode="prepend", content=new_code)
            elif strategy == "insert_after":
                result = self.edit_file(path, mode="insert_after", insert_after=pattern, content=new_code)
            elif strategy == "insert_before":
                result = self.edit_file(path, mode="insert_before", insert_before=pattern, content=new_code)
            elif strategy == "replace":
                result = self.edit_file(path, mode="replace", search=pattern, replace=new_code)
            else:
                return {
                    "success": False,
                    "error": f"Invalid strategy from LLM: {strategy}"
                }

            # Add smart_edit metadata to result
            if result.get("success"):
                result["smart_edit"] = {
                    "instruction": instruction,
                    "analysis": edit_plan.get("analysis", ""),
                    "strategy": strategy
                }

            return result

        except Exception as e:
            logging.error(f"Error in smart_edit: {e}")
            return {"success": False, "error": str(e)}

    def diff_edit(self, path, instruction, llm_callback=None, max_iterations=3):
        """
        Diff-based code editing with self-correction loop (Phase 4).

        For complex refactoring, the LLM generates the complete modified file,
        which is then validated and potentially corrected based on linter feedback.

        Args:
            path: File path to edit
            instruction: Natural language description of changes
            llm_callback: Function to call LLM for code generation
            max_iterations: Maximum self-correction attempts (default: 3)

        Returns:
            Dict with success status, diff, and iteration details
        """
        try:
            # Validate LLM callback
            if not llm_callback:
                return {
                    "success": False,
                    "error": "diff_edit requires LLM integration (llm_callback not provided)"
                }

            # Read current file
            full_path = self._get_safe_path(path)
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            original_content = full_path.read_text()
            iteration = 0
            lint_feedback = ""

            logging.info(f"diff_edit: Starting '{instruction}' for {path} (max {max_iterations} iterations)")

            while iteration < max_iterations:
                iteration += 1

                # Build prompt for LLM
                if iteration == 1:
                    prompt = f"""You are a code refactoring assistant. Generate the COMPLETE modified file.

Current file content:
```
{original_content}
```

Instruction: {instruction}

Generate the COMPLETE modified file content with the requested changes.
Make sure to:
1. Include ALL existing code (don't omit anything)
2. Apply the requested changes accurately
3. Maintain proper formatting and indentation
4. Follow Python best practices

Return ONLY the complete modified file content, no explanations or markdown."""
                else:
                    # Self-correction iteration
                    prompt = f"""You are a code refactoring assistant. The previous modification had issues.

Original file:
```
{original_content}
```

Your previous attempt had these issues:
{lint_feedback}

Instruction: {instruction}

Generate the COMPLETE modified file content with:
1. The requested changes from the instruction
2. Fixes for the linting issues above
3. ALL existing code (don't omit anything)

Return ONLY the complete modified file content, no explanations."""

                # Call LLM
                logging.info(f"diff_edit iteration {iteration}: Generating modified file")
                new_content = llm_callback(prompt)

                if not new_content or len(new_content.strip()) == 0:
                    return {
                        "success": False,
                        "error": f"LLM returned empty content on iteration {iteration}"
                    }

                # Clean up markdown code blocks if present
                if "```python" in new_content:
                    new_content = new_content.split("```python")[1].split("```")[0].strip()
                elif "```" in new_content:
                    new_content = new_content.split("```")[1].split("```")[0].strip()

                # Validate syntax
                if path.endswith('.py'):
                    validation = self._validate_python_syntax(new_content)
                    if not validation['valid']:
                        if iteration < max_iterations:
                            lint_feedback = f"Syntax error: {validation['error']}"
                            logging.warning(f"diff_edit iteration {iteration}: Syntax error, retrying...")
                            continue
                        else:
                            return {
                                "success": False,
                                "error": f"Syntax error after {max_iterations} iterations: {validation['error']}"
                            }

                    # Run linter
                    lint_result = self._lint_python_code(new_content, path)
                    if lint_result.get('has_issues'):
                        lint_feedback = f"{lint_result['summary']}\n{lint_result.get('suggestion', '')}"
                        logging.info(f"diff_edit iteration {iteration}: Linting issues found")

                        # If this is not the last iteration, try to self-correct
                        if iteration < max_iterations:
                            logging.info(f"diff_edit: Attempting self-correction (iteration {iteration + 1})")
                            continue
                        else:
                            # Last iteration - accept with warnings
                            logging.warning(f"diff_edit: Accepting with linting issues after {max_iterations} iterations")

                # Generate diff for logging
                import difflib
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"{path} (original)",
                    tofile=f"{path} (modified)",
                    lineterm=''
                ))
                diff_text = ''.join(diff)

                # Apply changes
                full_path.write_text(new_content)
                content_size = len(new_content.encode('utf-8'))
                logging.info(f"diff_edit: Applied changes after {iteration} iteration(s)")

                result = {
                    "success": True,
                    "message": f"File edited with diff-based approach: {path}",
                    "path": str(full_path),
                    "size": content_size,
                    "iterations": iteration,
                    "diff": diff_text
                }

                if lint_result.get('has_issues'):
                    result['warnings'] = [f"Code quality: {lint_result['summary']}"]

                return result

            # Should not reach here, but just in case
            return {
                "success": False,
                "error": f"Failed to generate valid code after {max_iterations} iterations"
            }

        except Exception as e:
            logging.error(f"Error in diff_edit: {e}")
            return {"success": False, "error": str(e)}

    def delete_file(self, path):
        """Delete a file"""
        try:
            full_path = self._get_safe_path(path)

            if not full_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            if full_path.is_dir():
                return {"success": False, "error": f"Cannot delete directory with this tool: {path}"}

            full_path.unlink()
            logging.info(f"Deleted file: {full_path}")

            return {
                "success": True,
                "message": f"File deleted: {path}"
            }
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            return {"success": False, "error": str(e)}

    def multi_file_edit(self, operations: list, llm_callback=None) -> dict:
        """
        Atomic multi-file operations with rollback (Phase 5).

        Executes multiple file operations as a transaction - all succeed or all rollback.

        Args:
            operations: List of operations, each is a dict with:
                - file: File path
                - action: "edit_file", "smart_edit", "diff_edit", "write_file"
                - Additional params for the action
            llm_callback: Function to call LLM (for smart_edit/diff_edit)

        Returns:
            Dict with success status, results, and rollback info if failed

        Example:
            operations = [
                {"file": "file1.py", "action": "edit_file", "mode": "replace",
                 "search": "old_name", "replace": "new_name"},
                {"file": "file2.py", "action": "smart_edit",
                 "instruction": "Add import statement"},
            ]
        """
        try:
            # Validate operations
            if not operations or len(operations) == 0:
                return {"success": False, "error": "operations list cannot be empty"}

            # Start transaction
            self.transaction_manager.begin()
            results = []
            files_modified = []

            logging.info(f"multi_file_edit: Starting transaction with {len(operations)} operations")

            # Backup all files that will be modified
            for operation in operations:
                file_path = operation.get('file')
                if not file_path:
                    raise ValueError("Operation missing 'file' parameter")

                self.transaction_manager.backup_file(file_path)
                self.transaction_manager.add_operation(operation)

            # Execute each operation
            for i, operation in enumerate(operations):
                file_path = operation['file']
                action = operation.get('action', 'edit_file')

                logging.info(f"multi_file_edit: Executing operation {i+1}/{len(operations)}: {action} on {file_path}")

                try:
                    # Execute the appropriate action
                    if action == "write_file":
                        content = operation.get('content', '')
                        result = self.write_file(file_path, content)

                    elif action == "edit_file":
                        mode = operation.get('mode', 'append')
                        result = self.edit_file(
                            file_path,
                            mode=mode,
                            content=operation.get('content', ''),
                            search=operation.get('search', ''),
                            replace=operation.get('replace', ''),
                            line_number=operation.get('line_number'),
                            start_line=operation.get('start_line'),
                            end_line=operation.get('end_line'),
                            insert_after=operation.get('insert_after', ''),
                            insert_before=operation.get('insert_before', '')
                        )

                    elif action == "smart_edit":
                        if not llm_callback:
                            raise ValueError("smart_edit requires llm_callback")
                        instruction = operation.get('instruction', '')
                        result = self.smart_edit(file_path, instruction, llm_callback)

                    elif action == "diff_edit":
                        if not llm_callback:
                            raise ValueError("diff_edit requires llm_callback")
                        instruction = operation.get('instruction', '')
                        max_iterations = operation.get('max_iterations', 3)
                        result = self.diff_edit(file_path, instruction, llm_callback, max_iterations)

                    else:
                        raise ValueError(f"Unknown action: {action}")

                    # Check if operation succeeded
                    if not result.get('success'):
                        raise RuntimeError(f"Operation failed on {file_path}: {result.get('error')}")

                    results.append({
                        "file": file_path,
                        "action": action,
                        "success": True,
                        "result": result
                    })
                    files_modified.append(file_path)

                except Exception as e:
                    logging.error(f"multi_file_edit: Operation {i+1} failed: {e}")
                    # Rollback all changes
                    rollback_result = self.transaction_manager.rollback()
                    return {
                        "success": False,
                        "error": f"Operation {i+1} ({action} on {file_path}) failed: {e}",
                        "completed_operations": i,
                        "total_operations": len(operations),
                        "rollback": rollback_result
                    }

            # All operations succeeded - commit transaction
            commit_result = self.transaction_manager.commit()

            return {
                "success": True,
                "message": f"Multi-file transaction completed: {len(operations)} operations",
                "operations": results,
                "files_modified": files_modified,
                "transaction": commit_result
            }

        except Exception as e:
            logging.error(f"Error in multi_file_edit: {e}")
            # Attempt rollback
            if self.transaction_manager.is_active:
                rollback_result = self.transaction_manager.rollback()
                return {
                    "success": False,
                    "error": str(e),
                    "rollback": rollback_result
                }
            return {"success": False, "error": str(e)}

    # ========== PHASE 4: DIFF-BASED EDITS ==========

    def apply_diff_changes(self, path, changes):
        """
        Apply structured diff-based changes to a file (Phase 4)

        Args:
            path: File path relative to workspace
            changes: List of change dicts with start_line, end_line, new_content, reason

        Returns:
            Dict with success status and changes applied
        """
        return self.diff_editor.apply_diff(path, changes)

    def apply_single_diff(self, path, start_line, end_line, new_content, reason=""):
        """
        Apply a single diff change (Phase 4)

        Args:
            path: File path
            start_line: Starting line (1-indexed)
            end_line: Ending line (1-indexed, inclusive)
            new_content: New content
            reason: Why this change is being made

        Returns:
            Dict with success status
        """
        return self.diff_editor.apply_single_change(path, start_line, end_line, new_content, reason)

    def insert_lines_at(self, path, after_line, content, reason=""):
        """
        Insert lines after a specific line number (Phase 4)

        Args:
            path: File path
            after_line: Line number to insert after (1-indexed)
            content: Content to insert
            reason: Why insertion is being made

        Returns:
            Dict with success status
        """
        return self.diff_editor.insert_lines(path, after_line, content, reason)

    def delete_lines_range(self, path, start_line, end_line, reason=""):
        """
        Delete a range of lines (Phase 4)

        Args:
            path: File path
            start_line: Starting line (1-indexed)
            end_line: Ending line (1-indexed, inclusive)
            reason: Why lines are being deleted

        Returns:
            Dict with success status
        """
        return self.diff_editor.delete_lines(path, start_line, end_line, reason)

    def replace_function_impl(self, path, function_name, new_implementation, reason=""):
        """
        Replace entire function by name (Phase 4)

        Args:
            path: File path
            function_name: Name of function to replace
            new_implementation: New function code
            reason: Why function is being replaced

        Returns:
            Dict with success status
        """
        return self.diff_editor.replace_function(path, function_name, new_implementation, reason)

    def preview_diff_changes(self, path, changes):
        """
        Preview diff changes without applying them (Phase 4)

        Args:
            path: File path
            changes: List of changes to preview

        Returns:
            Unified diff string
        """
        return self.diff_editor.preview_diff(path, changes)