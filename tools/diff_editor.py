"""
Diff-Based Editor (Phase 4)
More reliable file editing using structured line-based diffs
"""

import os
import logging
import difflib
from pathlib import Path
from typing import List, Dict, Optional


class DiffEditor:
    """
    Applies structured diff-based edits to files
    More reliable than comment markers or string replacement
    """

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def apply_diff(self, file_path: str, changes: List[Dict]) -> Dict:
        """
        Apply multiple changes using line-based diffs

        Args:
            file_path: Path to file (relative to workspace)
            changes: List of change dictionaries with:
                - start_line: Starting line number (1-indexed)
                - end_line: Ending line number (1-indexed, inclusive)
                - new_content: New content to insert
                - reason: Why this change is being made (for logging)

        Returns:
            Dict with success status, changes applied, and any errors
        """
        try:
            full_path = self.workspace / file_path

            if not full_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}"
                }

            # Read original content
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            original_lines = lines.copy()

            # Sort changes by line number (reverse) to maintain line numbers
            # Processing from bottom to top prevents line number shifts
            sorted_changes = sorted(changes, key=lambda c: c['start_line'], reverse=True)

            applied_changes = []

            for change in sorted_changes:
                start = change['start_line'] - 1  # Convert to 0-indexed
                end = change['end_line']  # End is inclusive, so this works for slicing
                reason = change.get('reason', 'No reason provided')

                # Validate line numbers
                if start < 0 or end > len(lines):
                    logging.warning(f"Invalid line range: {start+1}-{end} (file has {len(lines)} lines)")
                    continue

                # Prepare new content
                new_content = change['new_content']
                if not new_content.endswith('\n') and new_content:
                    new_content += '\n'

                new_lines = new_content.split('\n')
                # Remove empty last element if content ended with \n
                if new_lines and new_lines[-1] == '':
                    new_lines.pop()
                # Add newlines back
                new_lines = [line + '\n' for line in new_lines]

                # Apply change
                old_content = ''.join(lines[start:end])
                lines[start:end] = new_lines

                applied_changes.append({
                    'lines': f"{start+1}-{end}",
                    'reason': reason,
                    'old_content_preview': old_content[:100],
                    'new_content_preview': new_content[:100]
                })

                logging.info(f"Applied change to lines {start+1}-{end}: {reason}")

            # Write modified content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            return {
                'success': True,
                'file': file_path,
                'changes_applied': len(applied_changes),
                'changes': applied_changes,
                'original_line_count': len(original_lines),
                'new_line_count': len(lines)
            }

        except Exception as e:
            logging.error(f"Diff edit failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_single_change(self, file_path: str, start_line: int, end_line: int,
                           new_content: str, reason: str = "") -> Dict:
        """
        Convenience method for applying a single change

        Args:
            file_path: Path to file
            start_line: Starting line (1-indexed)
            end_line: Ending line (1-indexed, inclusive)
            new_content: New content
            reason: Why this change is being made

        Returns:
            Dict with success status
        """
        change = {
            'start_line': start_line,
            'end_line': end_line,
            'new_content': new_content,
            'reason': reason
        }
        return self.apply_diff(file_path, [change])

    def insert_lines(self, file_path: str, after_line: int, content: str,
                    reason: str = "") -> Dict:
        """
        Insert new lines after a specific line number

        Args:
            file_path: Path to file
            after_line: Line number to insert after (1-indexed)
            content: Content to insert
            reason: Why this insertion is being made

        Returns:
            Dict with success status
        """
        # Insert is like replacing 0 lines
        change = {
            'start_line': after_line + 1,
            'end_line': after_line,  # Empty range for insertion
            'new_content': content,
            'reason': reason or "Inserted lines"
        }
        return self.apply_diff(file_path, [change])

    def delete_lines(self, file_path: str, start_line: int, end_line: int,
                    reason: str = "") -> Dict:
        """
        Delete lines from a file

        Args:
            file_path: Path to file
            start_line: Starting line (1-indexed)
            end_line: Ending line (1-indexed, inclusive)
            reason: Why these lines are being deleted

        Returns:
            Dict with success status
        """
        change = {
            'start_line': start_line,
            'end_line': end_line,
            'new_content': '',
            'reason': reason or "Deleted lines"
        }
        return self.apply_diff(file_path, [change])

    def replace_function(self, file_path: str, function_name: str,
                        new_implementation: str, reason: str = "") -> Dict:
        """
        Replace an entire function by finding it in the file

        Args:
            file_path: Path to file
            function_name: Name of function to replace
            new_implementation: New function implementation
            reason: Why function is being replaced

        Returns:
            Dict with success status
        """
        try:
            full_path = self.workspace / file_path

            if not full_path.exists():
                return {'success': False, 'error': f"File not found: {file_path}"}

            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Find function definition
            func_start = None
            func_end = None
            indent_level = None

            for i, line in enumerate(lines):
                # Look for function definition
                if f"def {function_name}(" in line:
                    func_start = i + 1  # 1-indexed
                    indent_level = len(line) - len(line.lstrip())
                    continue

                # Find end of function
                if func_start is not None:
                    stripped = line.lstrip()
                    current_indent = len(line) - len(stripped)

                    # Empty lines or comments continue the function
                    if not stripped or stripped.startswith('#'):
                        continue

                    # Found a line at same or lower indent level
                    if current_indent <= indent_level and stripped:
                        func_end = i  # 1-indexed, exclusive
                        break

            # If we didn't find an end, function goes to EOF
            if func_start and func_end is None:
                func_end = len(lines) + 1

            if func_start is None:
                return {
                    'success': False,
                    'error': f"Function '{function_name}' not found in {file_path}"
                }

            # Apply the change
            change = {
                'start_line': func_start,
                'end_line': func_end,
                'new_content': new_implementation,
                'reason': reason or f"Replaced function {function_name}"
            }

            return self.apply_diff(file_path, [change])

        except Exception as e:
            logging.error(f"Function replacement failed: {e}")
            return {'success': False, 'error': str(e)}

    def preview_diff(self, file_path: str, changes: List[Dict]) -> str:
        """
        Preview what changes would be made without applying them

        Args:
            file_path: Path to file
            changes: List of changes to preview

        Returns:
            Unified diff string showing changes
        """
        try:
            full_path = self.workspace / file_path

            if not full_path.exists():
                return f"Error: File not found: {file_path}"

            with open(full_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            # Apply changes to a copy
            modified_lines = original_lines.copy()
            sorted_changes = sorted(changes, key=lambda c: c['start_line'], reverse=True)

            for change in sorted_changes:
                start = change['start_line'] - 1
                end = change['end_line']
                new_content = change['new_content']

                if not new_content.endswith('\n') and new_content:
                    new_content += '\n'

                new_lines = [line + '\n' for line in new_content.split('\n') if line or new_content]
                modified_lines[start:end] = new_lines

            # Generate unified diff
            diff = difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"{file_path} (original)",
                tofile=f"{file_path} (modified)",
                lineterm=''
            )

            return '\n'.join(diff)

        except Exception as e:
            return f"Error generating preview: {e}"
