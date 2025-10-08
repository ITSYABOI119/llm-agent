"""
Context Gatherer - Intelligently gather context using bash tools
Implements Claude Code's "gather context" phase pattern
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional


class ContextGatherer:
    """
    Gather context for tasks using smart file inspection
    (Claude Code pattern: use grep, find, tail instead of loading everything)
    """

    def __init__(self, config: Dict, search_tools, fs_tools, token_counter=None):
        self.config = config
        self.search_tools = search_tools
        self.fs_tools = fs_tools
        self.workspace = Path(config['agent']['workspace'])
        self.token_counter = token_counter

    def gather_for_task(self, user_request: str) -> Dict:
        """
        Intelligently gather context for a user request

        Returns:
            {
                'relevant_files': List[str],
                'project_structure': str,
                'dependencies': Dict,
                'patterns_found': List[str],
                'summary': str
            }
        """
        logging.info("GATHER CONTEXT phase starting...")

        context = {
            'relevant_files': [],
            'project_structure': '',
            'dependencies': {},
            'patterns_found': [],
            'summary': ''
        }

        # 1. Analyze request for keywords
        keywords = self._extract_keywords(user_request)
        logging.info(f"Keywords extracted: {keywords}")

        # 2. Search for relevant files (grep pattern)
        if keywords:
            context['relevant_files'] = self._search_relevant_files(keywords)

        # 3. Get project structure (if creating new files)
        if any(word in user_request.lower() for word in ['create', 'new', 'build', 'generate']):
            context['project_structure'] = self._get_project_structure()

        # 4. Check for dependencies (package.json, requirements.txt, etc.)
        context['dependencies'] = self._check_dependencies()

        # 5. Find similar code patterns
        context['patterns_found'] = self._find_code_patterns(keywords)

        # 6. Generate summary
        context['summary'] = self._generate_summary(context)

        logging.info(f"Context gathered: {len(context['relevant_files'])} files, "
                    f"{len(context['patterns_found'])} patterns")

        return context

    def _extract_keywords(self, request: str) -> List[str]:
        """Extract relevant keywords from user request"""
        # Common tech keywords
        tech_keywords = [
            'react', 'vue', 'angular', 'python', 'javascript', 'typescript',
            'html', 'css', 'api', 'database', 'function', 'class', 'component',
            'dashboard', 'chart', 'form', 'button', 'modal', 'table'
        ]

        request_lower = request.lower()
        found_keywords = [kw for kw in tech_keywords if kw in request_lower]

        # Also extract quoted terms
        import re
        quoted = re.findall(r'"([^"]*)"', request)
        found_keywords.extend(quoted)

        return list(set(found_keywords))[:5]  # Limit to top 5

    def _search_relevant_files(self, keywords: List[str]) -> List[str]:
        """Search for files containing keywords (grep pattern)"""
        relevant_files = []

        for keyword in keywords:
            # Use grep to find files with keyword
            result = self.search_tools.grep_content(
                keyword,
                str(self.workspace),
                "*.*",
                case_sensitive=False
            )

            if result.get('success') and result.get('files'):
                relevant_files.extend(result['files'])

        # Deduplicate and limit
        return list(set(relevant_files))[:10]

    def _get_project_structure(self) -> str:
        """Get high-level project structure (directory tree)"""
        try:
            # List top-level directories
            result = self.fs_tools.list_directory(".")

            if result.get('success'):
                entries = result.get('entries', [])
                dirs = [e['name'] for e in entries if e['type'] == 'directory']
                files = [e['name'] for e in entries if e['type'] == 'file']

                structure = "Project structure:\n"
                structure += f"Directories: {', '.join(dirs[:10])}\n"
                structure += f"Files: {', '.join(files[:10])}"
                return structure

        except Exception as e:
            logging.warning(f"Could not get project structure: {e}")

        return "Project structure: Unknown"

    def _check_dependencies(self) -> Dict:
        """Check for common dependency files"""
        deps = {}

        # Check for common dependency files
        dep_files = [
            'package.json',
            'requirements.txt',
            'Pipfile',
            'pom.xml',
            'build.gradle',
            'Cargo.toml'
        ]

        for dep_file in dep_files:
            full_path = self.workspace / dep_file
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                    deps[dep_file] = content[:500]  # First 500 chars
                except:
                    pass

        return deps

    def _find_code_patterns(self, keywords: List[str]) -> List[str]:
        """Find common code patterns in existing files"""
        patterns = []

        # Common patterns to look for
        pattern_searches = [
            ('function', 'Functions found'),
            ('class', 'Classes found'),
            ('import', 'Import patterns'),
            ('export', 'Export patterns'),
        ]

        for pattern, description in pattern_searches:
            result = self.search_tools.grep_content(
                pattern,
                str(self.workspace),
                "*.{py,js,ts,jsx,tsx}",
                case_sensitive=False
            )

            if result.get('success') and result.get('files'):
                patterns.append(f"{description}: {len(result['files'])} files")

        return patterns

    def _generate_summary(self, context: Dict) -> str:
        """Generate a summary of gathered context"""
        summary_parts = []

        if context['relevant_files']:
            summary_parts.append(
                f"Found {len(context['relevant_files'])} relevant files"
            )

        if context['dependencies']:
            summary_parts.append(
                f"Dependencies: {', '.join(context['dependencies'].keys())}"
            )

        if context['patterns_found']:
            summary_parts.append(
                f"Patterns: {', '.join(context['patterns_found'])}"
            )

        if context['project_structure']:
            summary_parts.append("Project structure analyzed")

        return " | ".join(summary_parts) if summary_parts else "No context gathered"

    def format_for_llm(self, context: Dict) -> str:
        """Format gathered context for LLM consumption"""
        formatted = "=== GATHERED CONTEXT ===\n\n"

        if context['summary']:
            formatted += f"Summary: {context['summary']}\n\n"

        if context['project_structure']:
            formatted += f"{context['project_structure']}\n\n"

        if context['dependencies']:
            formatted += "Dependencies found:\n"
            for dep_file, content in context['dependencies'].items():
                formatted += f"  - {dep_file}\n"

        if context['relevant_files']:
            formatted += f"\nRelevant files ({len(context['relevant_files'])}):\n"
            for file_path in context['relevant_files'][:5]:
                formatted += f"  - {file_path}\n"

        if context['patterns_found']:
            formatted += f"\nCode patterns:\n"
            for pattern in context['patterns_found']:
                formatted += f"  - {pattern}\n"

        formatted += "\n=== END CONTEXT ===\n"

        return formatted
