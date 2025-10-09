"""
Action Verifier - Verify that tool executions succeeded
Implements Claude Code's "verify work" phase pattern
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any


class ActionVerifier:
    """
    Verify actions after execution
    (Claude Code pattern: gather → act → verify → repeat)
    """

    def __init__(self, config: Dict, fs_tools):
        self.config = config
        self.fs_tools = fs_tools
        self.workspace = Path(config['agent']['workspace'])

    def verify_action(self, tool_name: str, params: Dict, result: Dict) -> Dict:
        """
        Verify that an action succeeded

        Returns:
            {
                'verified': bool,
                'issues': List[str],
                'suggestion': str  # What to do if failed
            }
        """
        verification = {
            'verified': True,
            'issues': [],
            'suggestion': ''
        }

        # Check basic success
        if not result.get('success'):
            verification['verified'] = False
            issues: List[str] = verification['issues']  # type: ignore
            issues.append(f"Tool reported failure: {result.get('error', 'Unknown')}")
            verification['suggestion'] = "Retry with corrected parameters"
            return verification

        # Tool-specific verification
        if tool_name == 'write_file':
            return self._verify_write_file(params, result, verification)

        elif tool_name == 'edit_file':
            return self._verify_edit_file(params, result, verification)

        elif tool_name == 'create_folder':
            return self._verify_create_folder(params, result, verification)

        elif tool_name == 'delete_file':
            return self._verify_delete_file(params, result, verification)

        # Default: trust the success flag
        return verification

    def _verify_write_file(self, params: Dict, result: Dict, verification: Dict) -> Dict:
        """Verify file was actually written"""
        file_path = params.get('path')

        if not file_path:
            verification['verified'] = False
            verification['issues'].append("No file path provided")
            return verification

        # Check file exists
        full_path = self.workspace / file_path
        if not full_path.exists():
            verification['verified'] = False
            verification['issues'].append(f"File not found after write: {file_path}")
            verification['suggestion'] = "Retry write_file with same parameters"
            return verification

        # Check file is not empty (if content was provided)
        expected_content = params.get('content', '')
        if expected_content and full_path.stat().st_size == 0:
            verification['verified'] = False
            verification['issues'].append(f"File is empty: {file_path}")
            verification['suggestion'] = "Content may not have been written"
            return verification

        # Check syntax if Python file
        if file_path.endswith('.py'):
            syntax_check = self._check_python_syntax(full_path)
            if not syntax_check['valid']:
                verification['verified'] = False
                verification['issues'].append(f"Syntax error: {syntax_check['error']}")
                verification['suggestion'] = "Fix syntax and rewrite file"
                return verification

        logging.info(f"✓ Verified: {file_path} written successfully")
        return verification

    def _verify_edit_file(self, params: Dict, result: Dict, verification: Dict) -> Dict:
        """Verify file edit succeeded"""
        file_path = params.get('path')

        if not file_path:
            verification['verified'] = False
            verification['issues'].append("No file path provided")
            return verification

        # Check file exists
        full_path = self.workspace / file_path
        if not full_path.exists():
            verification['verified'] = False
            verification['issues'].append(f"File not found after edit: {file_path}")
            verification['suggestion'] = "File may have been deleted accidentally"
            return verification

        # Check syntax if Python file
        if file_path.endswith('.py'):
            syntax_check = self._check_python_syntax(full_path)
            if not syntax_check['valid']:
                verification['verified'] = False
                verification['issues'].append(f"Edit broke syntax: {syntax_check['error']}")
                verification['suggestion'] = "Revert edit or fix syntax error"
                return verification

        logging.info(f"✓ Verified: {file_path} edited successfully")
        return verification

    def _verify_create_folder(self, params: Dict, result: Dict, verification: Dict) -> Dict:
        """Verify folder was created"""
        folder_path = params.get('path')

        if not folder_path:
            verification['verified'] = False
            verification['issues'].append("No folder path provided")
            return verification

        # Check folder exists
        full_path = self.workspace / folder_path
        if not full_path.exists():
            verification['verified'] = False
            verification['issues'].append(f"Folder not found after creation: {folder_path}")
            verification['suggestion'] = "Retry create_folder"
            return verification

        if not full_path.is_dir():
            verification['verified'] = False
            verification['issues'].append(f"Path exists but is not a folder: {folder_path}")
            verification['suggestion'] = "Delete file and retry create_folder"
            return verification

        logging.info(f"✓ Verified: {folder_path} created successfully")
        return verification

    def _verify_delete_file(self, params: Dict, result: Dict, verification: Dict) -> Dict:
        """Verify file was deleted"""
        file_path = params.get('path')

        if not file_path:
            verification['verified'] = False
            verification['issues'].append("No file path provided")
            return verification

        # Check file does NOT exist
        full_path = self.workspace / file_path
        if full_path.exists():
            verification['verified'] = False
            verification['issues'].append(f"File still exists after delete: {file_path}")
            verification['suggestion'] = "Retry delete_file"
            return verification

        logging.info(f"✓ Verified: {file_path} deleted successfully")
        return verification

    def _check_python_syntax(self, file_path: Path) -> Dict:
        """Check Python file for syntax errors"""
        try:
            import ast
            content = file_path.read_text(encoding='utf-8')
            ast.parse(content)
            return {'valid': True}

        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"Line {e.lineno}: {e.msg}"
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def verify_batch(self, actions: list) -> Dict:
        """
        Verify multiple actions

        Args:
            actions: List of (tool_name, params, result) tuples

        Returns:
            {
                'all_verified': bool,
                'total': int,
                'verified': int,
                'failed': int,
                'issues': List[Dict]
            }
        """
        results = {
            'all_verified': True,
            'total': len(actions),
            'verified': 0,
            'failed': 0,
            'issues': []
        }

        for tool_name, params, result in actions:
            verification = self.verify_action(tool_name, params, result)

            if verification['verified']:
                verified_count: int = results['verified']  # type: ignore
                results['verified'] = verified_count + 1
            else:
                failed_count: int = results['failed']  # type: ignore
                results['failed'] = failed_count + 1
                results['all_verified'] = False
                issues_list: List[Dict[str, Any]] = results['issues']  # type: ignore
                issues_list.append({
                    'tool': tool_name,
                    'params': params,
                    'issues': verification['issues'],
                    'suggestion': verification['suggestion']
                })

        logging.info(f"Batch verification: {results['verified']}/{results['total']} succeeded")

        return results
