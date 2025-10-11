"""
Plan Validator - Validate planning phase output (Phase 3 Day 4-5)

Validates plans before execution to ensure they are:
- Complete and actionable
- Have specific file specifications
- Include implementation details
- Address the original request

Returns validation score (0-1) with issues and suggestions.
"""

import logging
import re
from typing import Dict, List, Any


class PlanValidator:
    """
    Validate planning phase output before execution

    Ensures plans are complete, actionable, and address the user's request.
    """

    def __init__(self):
        """Initialize plan validator"""
        self.min_plan_length = 200  # Minimum characters for comprehensive plan
        self.min_detail_indicators = 3  # Minimum detail indicators required

    def validate_plan(self, plan: str, original_request: str) -> Dict[str, Any]:
        """
        Check if plan is complete and actionable

        Args:
            plan: Generated plan from planning model
            original_request: Original user request

        Returns:
            {
                'valid': bool - True if score >= 0.7
                'score': float - Validation score (0-1)
                'issues': List[str] - List of issues found
                'suggestions': List[str] - Actionable suggestions
                'details': Dict - Detailed validation results
            }
        """
        logging.info("[PLAN_VALIDATOR] Validating plan...")

        issues = []
        score = 1.0
        details = {}

        # Check 1: Plan has file specifications
        has_file_specs, file_spec_details = self._has_file_specs(plan)
        details['file_specs'] = file_spec_details

        if not has_file_specs:
            issues.append("Plan doesn't specify which files to create/modify")
            score -= 0.3
            logging.warning("[PLAN_VALIDATOR] Missing file specifications")

        # Check 2: Plan has content details
        has_content, content_details = self._has_content_details(plan)
        details['content_details'] = content_details

        if not has_content:
            issues.append("Plan lacks specific content/implementation details")
            score -= 0.2
            logging.warning("[PLAN_VALIDATOR] Missing content details")

        # Check 3: Plan addresses request
        addresses_request, request_coverage = self._addresses_request(plan, original_request)
        details['request_coverage'] = request_coverage

        if not addresses_request:
            issues.append("Plan doesn't fully address the original request")
            score -= 0.4
            logging.warning("[PLAN_VALIDATOR] Plan doesn't address request")

        # Check 4: Plan has sufficient structure
        has_structure, structure_details = self._has_sufficient_structure(plan)
        details['structure'] = structure_details

        if not has_structure:
            issues.append("Plan is too short or lacks structure")
            score -= 0.1
            logging.warning("[PLAN_VALIDATOR] Insufficient structure")

        # Generate suggestions based on issues
        suggestions = self._generate_suggestions(issues, details)

        # Calculate final score
        final_score = max(score, 0.0)
        is_valid = final_score >= 0.7

        result = {
            'valid': is_valid,
            'score': final_score,
            'issues': issues,
            'suggestions': suggestions,
            'details': details
        }

        logging.info(f"[PLAN_VALIDATOR] Validation complete - Score: {final_score:.2f}, Valid: {is_valid}")

        return result

    def _has_file_specs(self, plan: str) -> tuple[bool, Dict]:
        """
        Check if plan specifies files to create/modify

        Args:
            plan: Plan text

        Returns:
            (has_file_specs, details_dict)
        """
        # File indicators
        file_extensions = [
            '.html', '.css', '.js', '.jsx', '.ts', '.tsx',
            '.py', '.java', '.cpp', '.c', '.go', '.rs',
            '.txt', '.md', '.json', '.yaml', '.xml'
        ]

        file_keywords = [
            'file:', 'create', 'files:', 'modify', 'update',
            'generate', 'write', 'add file', 'new file'
        ]

        plan_lower = plan.lower()

        # Check for file extensions
        extensions_found = [ext for ext in file_extensions if ext in plan_lower]

        # Check for file keywords
        keywords_found = [kw for kw in file_keywords if kw in plan_lower]

        # Look for file path patterns (e.g., src/components/Button.tsx)
        file_path_pattern = r'\b[\w/]+\.[\w]+\b'
        file_paths = re.findall(file_path_pattern, plan)

        has_specs = len(extensions_found) > 0 or len(keywords_found) > 0 or len(file_paths) > 0

        details = {
            'extensions_found': extensions_found[:5],
            'keywords_found': keywords_found[:5],
            'file_paths_detected': len(file_paths),
            'has_specs': has_specs
        }

        return has_specs, details

    def _has_content_details(self, plan: str) -> tuple[bool, Dict]:
        """
        Check if plan has implementation details

        Args:
            plan: Plan text

        Returns:
            (has_content, details_dict)
        """
        plan_lower = plan.lower()

        # Detail indicators
        detail_indicators = [
            'function', 'class', 'component', 'method',
            'section', 'header', 'footer', 'sidebar',
            'style', 'import', 'export', 'interface',
            'type', 'props', 'state', 'hook',
            'endpoint', 'route', 'api', 'database'
        ]

        # Count occurrences
        indicators_found = []
        for indicator in detail_indicators:
            if indicator in plan_lower:
                indicators_found.append(indicator)

        # Check for code-like patterns (camelCase, snake_case, PascalCase)
        camel_case_pattern = r'\b[a-z]+[A-Z][a-zA-Z]*\b'
        snake_case_pattern = r'\b[a-z]+_[a-z_]+\b'
        pascal_case_pattern = r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b'

        camel_cases = len(re.findall(camel_case_pattern, plan))
        snake_cases = len(re.findall(snake_case_pattern, plan))
        pascal_cases = len(re.findall(pascal_case_pattern, plan))

        has_content = len(indicators_found) >= self.min_detail_indicators

        details = {
            'indicators_found': indicators_found[:10],
            'indicator_count': len(indicators_found),
            'camel_case_count': camel_cases,
            'snake_case_count': snake_cases,
            'pascal_case_count': pascal_cases,
            'has_content': has_content
        }

        return has_content, details

    def _addresses_request(self, plan: str, original_request: str) -> tuple[bool, Dict]:
        """
        Check if plan addresses the original request

        Args:
            plan: Plan text
            original_request: Original user request

        Returns:
            (addresses_request, details_dict)
        """
        plan_lower = plan.lower()
        request_lower = original_request.lower()

        # Extract key terms from request (simple tokenization)
        # Remove common words
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'can', 'may', 'might', 'must',
            'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'this', 'that', 'these', 'those',
            'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
            'please', 'want', 'need', 'help', 'create', 'make', 'build'
        }

        # Extract words from request
        request_words = re.findall(r'\b\w+\b', request_lower)
        key_terms = [w for w in request_words if len(w) > 3 and w not in stop_words]

        # Check coverage of key terms in plan
        terms_covered = [term for term in key_terms if term in plan_lower]
        coverage_rate = len(terms_covered) / len(key_terms) if key_terms else 0

        # Check for quoted terms (explicit requirements)
        quoted_terms = re.findall(r'"([^"]*)"', original_request)
        quoted_covered = [term for term in quoted_terms if term.lower() in plan_lower]

        # Consider it addressing the request if coverage >= 50% and all quoted terms covered
        addresses = coverage_rate >= 0.5 and len(quoted_covered) == len(quoted_terms)

        details = {
            'key_terms_count': len(key_terms),
            'terms_covered_count': len(terms_covered),
            'coverage_rate': coverage_rate,
            'quoted_terms': quoted_terms,
            'quoted_covered': quoted_covered,
            'addresses_request': addresses
        }

        return addresses, details

    def _has_sufficient_structure(self, plan: str) -> tuple[bool, Dict]:
        """
        Check if plan has sufficient structure/length

        Args:
            plan: Plan text

        Returns:
            (has_structure, details_dict)
        """
        # Check length
        plan_length = len(plan)
        has_min_length = plan_length >= self.min_plan_length

        # Check for structure markers (lists, steps, sections)
        lines = plan.split('\n')

        # Count numbered items (1. 2. 3. or 1) 2) 3))
        numbered_items = len(re.findall(r'^\s*\d+[\.)]\s+', plan, re.MULTILINE))

        # Count bullet points
        bullet_points = len(re.findall(r'^\s*[-*•]\s+', plan, re.MULTILINE))

        # Count section headers (lines ending with :)
        section_headers = len(re.findall(r'^[A-Z][^:]*:\s*$', plan, re.MULTILINE))

        # Has structure if it has lists or sections
        has_structure = has_min_length and (numbered_items > 0 or bullet_points > 2 or section_headers > 0)

        details = {
            'plan_length': plan_length,
            'line_count': len(lines),
            'numbered_items': numbered_items,
            'bullet_points': bullet_points,
            'section_headers': section_headers,
            'has_sufficient_structure': has_structure
        }

        return has_structure, details

    def _generate_suggestions(self, issues: List[str], details: Dict) -> List[str]:
        """
        Generate actionable suggestions from issues

        Args:
            issues: List of issues found
            details: Validation details

        Returns:
            List of suggestions
        """
        suggestions = []

        # File specification suggestions
        if "Plan doesn't specify which files" in str(issues):
            suggestions.append(
                "Add specific file names and paths (e.g., 'Create src/components/Button.tsx')"
            )

        # Content detail suggestions
        if "Plan lacks specific content" in str(issues):
            suggestions.append(
                "Include specific function/class names, components, or implementation details"
            )

        # Request coverage suggestions
        if "Plan doesn't fully address" in str(issues):
            request_coverage = details.get('request_coverage', {})
            coverage_rate = request_coverage.get('coverage_rate', 0)

            if coverage_rate < 0.3:
                suggestions.append(
                    "Plan appears disconnected from request. Review the original requirements carefully."
                )
            else:
                suggestions.append(
                    "Ensure all aspects of the original request are covered in the plan"
                )

        # Structure suggestions
        if "Plan is too short" in str(issues):
            suggestions.append(
                "Expand the plan with step-by-step instructions or more detailed breakdown"
            )

        return suggestions

    def get_validation_summary(self, validation_result: Dict) -> str:
        """
        Get human-readable validation summary

        Args:
            validation_result: Result from validate_plan()

        Returns:
            Formatted summary string
        """
        score = validation_result['score']
        valid = validation_result['valid']
        issues = validation_result['issues']
        suggestions = validation_result['suggestions']

        summary = f"Plan Validation: {'✓ VALID' if valid else '✗ NEEDS IMPROVEMENT'}\n"
        summary += f"Score: {score:.2f}/1.00\n"

        if issues:
            summary += f"\nIssues ({len(issues)}):\n"
            for issue in issues:
                summary += f"  - {issue}\n"

        if suggestions:
            summary += f"\nSuggestions ({len(suggestions)}):\n"
            for suggestion in suggestions:
                summary += f"  - {suggestion}\n"

        return summary
