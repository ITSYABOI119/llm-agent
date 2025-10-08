"""
Python Code Linter Integration
Provides quality checking beyond syntax validation
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class PythonLinter:
    """
    Integrates Python linters (pylint, flake8) for code quality checking

    Inspired by Cursor's approach: linter feedback is "extremely high signal"
    for catching errors and guiding self-correction.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.workspace = Path(config['agent']['workspace'])
        self.enabled_linters = config.get('linter', {}).get('enabled', ['flake8'])
        self.max_issues = config.get('linter', {}).get('max_issues', 10)
        self.ignore_codes = config.get('linter', {}).get('ignore', [])

    def lint_code(self, code: str, file_path: str = "temp.py") -> Dict[str, Any]:
        """
        Lint Python code and return issues

        Args:
            code: Python code to lint
            file_path: File path for context (used in error messages)

        Returns:
            {
                "has_issues": bool,
                "issues": List[dict],
                "summary": str,
                "suggestion": str
            }
        """
        issues = []

        # Try each enabled linter
        if 'flake8' in self.enabled_linters:
            flake8_issues = self._run_flake8(code, file_path)
            issues.extend(flake8_issues)

        if 'pylint' in self.enabled_linters:
            pylint_issues = self._run_pylint(code, file_path)
            issues.extend(pylint_issues)

        # Filter out ignored codes
        issues = [i for i in issues if i.get('code') not in self.ignore_codes]

        # Limit number of issues
        issues = issues[:self.max_issues]

        # Generate summary and suggestions
        summary = self._generate_summary(issues)
        suggestion = self._generate_suggestion(issues)

        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "summary": summary,
            "suggestion": suggestion
        }

    def _run_flake8(self, code: str, file_path: str) -> List[Dict]:
        """Run flake8 linter on code"""
        try:
            # Check if flake8 is installed
            result = subprocess.run(
                ['flake8', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logging.debug("flake8 not installed, skipping")
                return []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logging.debug("flake8 not available")
            return []

        issues = []

        try:
            # Run flake8 on code (via stdin)
            result = subprocess.run(
                ['flake8', '-'],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )

            # flake8 outputs errors to stderr, not stdout
            output = result.stderr if result.stderr else result.stdout
            if output:
                for line in output.split('\n'):
                    if line.strip():
                        issues.append(self._parse_flake8_line(line))

        except subprocess.TimeoutExpired:
            logging.warning("flake8 timed out")
        except Exception as e:
            logging.warning(f"flake8 error: {e}")

        return issues

    def _run_pylint(self, code: str, file_path: str) -> List[Dict]:
        """Run pylint on code"""
        try:
            # Check if pylint is installed
            result = subprocess.run(
                ['pylint', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logging.debug("pylint not installed, skipping")
                return []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logging.debug("pylint not available")
            return []

        issues = []

        try:
            # Create temp file for pylint (it doesn't support stdin well)
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run pylint
                result = subprocess.run(
                    ['pylint', '--output-format=json', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if result.stdout:
                    pylint_output = json.loads(result.stdout)
                    for item in pylint_output:
                        issues.append({
                            "line": item.get('line'),
                            "column": item.get('column'),
                            "code": item.get('message-id'),
                            "message": item.get('message'),
                            "severity": item.get('type', 'warning'),
                            "linter": "pylint"
                        })
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logging.warning("pylint timed out")
        except Exception as e:
            logging.warning(f"pylint error: {e}")

        return issues

    def _parse_flake8_line(self, line: str) -> Dict:
        """Parse flake8 text output line"""
        # Format: filename:line:col: CODE message
        try:
            parts = line.split(':', 3)
            if len(parts) >= 4:
                return {
                    "line": int(parts[1]),
                    "column": int(parts[2]),
                    "code": parts[3].split()[0],
                    "message": parts[3].split(' ', 1)[1] if ' ' in parts[3] else parts[3],
                    "severity": "warning",
                    "linter": "flake8"
                }
        except (ValueError, IndexError):
            pass

        return {
            "line": 0,
            "column": 0,
            "code": "UNKNOWN",
            "message": line,
            "severity": "info",
            "linter": "flake8"
        }

    def _generate_summary(self, issues: List[Dict]) -> str:
        """Generate human-readable summary of issues"""
        if not issues:
            return "No linting issues found"

        # Count by severity
        errors = [i for i in issues if i.get('severity') == 'error']
        warnings = [i for i in issues if i.get('severity') == 'warning']

        summary_parts = []
        if errors:
            summary_parts.append(f"{len(errors)} error(s)")
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")

        summary = f"Found {', '.join(summary_parts)}"

        # Add top issues
        if issues:
            top_issue = issues[0]
            summary += f"\nFirst issue: Line {top_issue.get('line')}: {top_issue.get('message')}"

        return summary

    def _generate_suggestion(self, issues: List[Dict]) -> str:
        """Generate actionable suggestions for fixing issues"""
        if not issues:
            return ""

        suggestions = []

        # Group by common issue types
        undefined_names = [i for i in issues if 'undefined' in i.get('message', '').lower()]
        unused_vars = [i for i in issues if 'unused' in i.get('message', '').lower()]
        line_too_long = [i for i in issues if 'line too long' in i.get('message', '').lower()]
        missing_import = [i for i in issues if 'import' in i.get('message', '').lower()]

        if undefined_names:
            suggestions.append(f"• Fix {len(undefined_names)} undefined name(s)")
        if unused_vars:
            suggestions.append(f"• Remove {len(unused_vars)} unused variable(s)")
        if line_too_long:
            suggestions.append(f"• Break {len(line_too_long)} long line(s)")
        if missing_import:
            suggestions.append(f"• Add missing import(s)")

        if suggestions:
            return "Suggestions:\n" + "\n".join(suggestions)

        return "Review and fix the reported issues"

    def is_available(self) -> Dict[str, bool]:
        """Check which linters are available"""
        available = {}

        for linter in ['flake8', 'pylint']:
            try:
                result = subprocess.run(
                    [linter, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                available[linter] = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                available[linter] = False

        return available
