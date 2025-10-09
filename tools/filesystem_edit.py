"""
File Editing Operations
Handles file editing with 8 modes: append, prepend, replace, insert_at_line, etc.
Extracted from filesystem.py to reduce file size
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class FileEditOperations:
    """File editing with multiple modes and Python syntax validation"""

    def __init__(self, workspace: Path, max_file_size: int, linter=None):
        """
        Initialize file edit operations.

        Args:
            workspace: Workspace directory path
            max_file_size: Maximum allowed file size in bytes
            linter: Optional Python linter instance
        """
        self.workspace = workspace
        self.max_file_size = max_file_size
        self.linter = linter

    def edit_file(
        self,
        path: str,
        get_safe_path_func,
        mode: str = "append",
        content: str = "",
        search: str = "",
        replace: str = "",
        line_number: Optional[int] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        insert_after: str = "",
        insert_before: str = ""
    ) -> Dict[str, Any]:
        """
        Edit an existing file with advanced editing modes.

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
            full_path = get_safe_path_func(path)

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

    def _normalize_pattern(self, pattern: str) -> Tuple[str, bool]:
        """
        Normalize search pattern - extract single-line pattern from multi-line input.

        This handles cases where LLM provides full function body instead of just the function name.
        Example: "def multiply(a, b):\n    return a * b" becomes "def multiply"

        Returns:
            Tuple of (normalized_pattern, was_normalized)
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

    def _validate_python_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate Python code syntax using AST parser.

        Args:
            code: Python code to validate

        Returns:
            Dict with "valid" bool and "error" message
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

    def _lint_python_code(self, code: str, file_path: str = "temp.py") -> Dict[str, Any]:
        """
        Run linter on Python code (optional quality check beyond syntax).

        Args:
            code: Python code to lint
            file_path: File path for linter context

        Returns:
            Dict with "has_issues", "summary", "suggestion", "issues"
        """
        if not self.linter:
            return {"has_issues": False, "summary": "Linter not enabled", "issues": []}

        try:
            return self.linter.lint_code(code, file_path)
        except Exception as e:
            logging.warning(f"Linting failed: {e}")
            return {"has_issues": False, "summary": f"Linting error: {e}", "issues": []}

    def _find_function_or_class_end(self, lines: list, pattern: str, match_line_idx: int) -> int:
        """
        Find the end of a function or class definition starting at match_line_idx.

        Args:
            lines: List of file lines
            pattern: Pattern that was matched
            match_line_idx: Index where pattern was found

        Returns:
            Line index after the function/class ends, or match_line_idx + 1 if not a function/class
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
