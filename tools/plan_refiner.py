"""
Plan Refiner - Iteratively improve plans based on validation (Phase 3 Day 4-5)

Re-prompts the planning model with validation feedback to improve low-scoring plans.
Maximum 2 refinement iterations to avoid infinite loops.
"""

import logging
from typing import Dict, Any, Callable, Optional


class PlanRefiner:
    """
    Iteratively improve plans based on validation feedback

    Uses validation results to generate refinement prompts for the planning model.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plan refiner

        Args:
            config: Configuration dict
        """
        self.config = config
        self.max_refinement_iterations = config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('two_phase', {}).get('validation', {}).get('max_refinement_iterations', 2)

    def refine_plan(
        self,
        original_plan: str,
        validation_result: Dict[str, Any],
        original_request: str,
        call_model_callback: Callable[[str, str], str]
    ) -> Dict[str, Any]:
        """
        Refine plan based on validation issues

        Args:
            original_plan: Plan that failed validation
            validation_result: Result from PlanValidator
            original_request: Original user request
            call_model_callback: Function to call planning model (prompt, model_name) -> response

        Returns:
            {
                'success': bool,
                'refined_plan': str,
                'refinement_applied': bool,
                'error': str (if failed)
            }
        """
        logging.info("[PLAN_REFINER] Refining plan...")

        # If plan is already valid, no refinement needed
        if validation_result['valid']:
            logging.info("[PLAN_REFINER] Plan already valid, no refinement needed")
            return {
                'success': True,
                'refined_plan': original_plan,
                'refinement_applied': False
            }

        # Build refinement prompt
        refinement_prompt = self._build_refinement_prompt(
            original_plan,
            validation_result,
            original_request
        )

        try:
            # Get planning model name from config
            planning_model = self.config.get('ollama', {}).get('multi_model', {}).get('routing', {}).get('two_phase', {}).get('planning_model', 'openthinker3-7b')

            # Call model with refinement prompt
            logging.info(f"[PLAN_REFINER] Calling {planning_model} for plan refinement")
            refined_plan = call_model_callback(refinement_prompt, planning_model)

            if not refined_plan or len(refined_plan) < 50:
                logging.error("[PLAN_REFINER] Refined plan is too short or empty")
                return {
                    'success': False,
                    'refined_plan': original_plan,
                    'refinement_applied': False,
                    'error': 'Refinement produced invalid plan'
                }

            logging.info(f"[PLAN_REFINER] Plan refined successfully ({len(refined_plan)} chars)")

            return {
                'success': True,
                'refined_plan': refined_plan,
                'refinement_applied': True
            }

        except Exception as e:
            logging.error(f"[PLAN_REFINER] Error refining plan: {e}")
            return {
                'success': False,
                'refined_plan': original_plan,
                'refinement_applied': False,
                'error': str(e)
            }

    def _build_refinement_prompt(
        self,
        original_plan: str,
        validation_result: Dict[str, Any],
        original_request: str
    ) -> str:
        """
        Build refinement prompt with validation feedback

        Args:
            original_plan: Plan that needs improvement
            validation_result: Validation result with issues/suggestions
            original_request: Original user request

        Returns:
            Refinement prompt for planning model
        """
        issues = validation_result.get('issues', [])
        suggestions = validation_result.get('suggestions', [])
        score = validation_result.get('score', 0)
        details = validation_result.get('details', {})

        # Build issues section
        issues_str = '\n'.join(f"  - {issue}" for issue in issues) if issues else "  (none)"

        # Build suggestions section
        suggestions_str = '\n'.join(f"  - {sug}" for sug in suggestions) if suggestions else "  (none)"

        # Build specific feedback based on validation details
        specific_feedback = self._build_specific_feedback(details)

        # Construct refinement prompt
        prompt = f"""You previously created a plan that scored {score:.2f}/1.00 in validation.

Original User Request:
{original_request}

Your Previous Plan:
{original_plan}

Issues Found:
{issues_str}

Suggestions for Improvement:
{suggestions_str}

{specific_feedback}

Please create an IMPROVED plan that addresses all the issues above. Make sure to:
1. Specify exact file names and paths
2. Include specific implementation details (function names, components, classes)
3. Address all aspects of the original request
4. Provide a structured, step-by-step breakdown

Improved Plan:"""

        return prompt

    def _build_specific_feedback(self, details: Dict[str, Any]) -> str:
        """
        Build specific feedback based on validation details

        Args:
            details: Validation details from PlanValidator

        Returns:
            Specific feedback string
        """
        feedback_parts = []

        # File specification feedback
        file_specs = details.get('file_specs', {})
        if not file_specs.get('has_specs'):
            feedback_parts.append(
                "Specific Issue: No file specifications found. "
                "Please specify exactly which files to create or modify (e.g., 'Create src/App.tsx' or 'Modify components/Header.jsx')."
            )

        # Content detail feedback
        content_details = details.get('content_details', {})
        if not content_details.get('has_content'):
            indicator_count = content_details.get('indicator_count', 0)
            feedback_parts.append(
                f"Specific Issue: Insufficient implementation details (only {indicator_count} detail indicators found). "
                "Include specific function names, class names, component names, or implementation details."
            )

        # Request coverage feedback
        request_coverage = details.get('request_coverage', {})
        if not request_coverage.get('addresses_request'):
            coverage_rate = request_coverage.get('coverage_rate', 0)
            terms_covered = request_coverage.get('terms_covered_count', 0)
            terms_total = request_coverage.get('key_terms_count', 0)

            feedback_parts.append(
                f"Specific Issue: Plan only covers {coverage_rate*100:.0f}% of the request "
                f"({terms_covered}/{terms_total} key terms). "
                "Make sure to address all requirements from the original request."
            )

        # Structure feedback
        structure = details.get('structure', {})
        if not structure.get('has_sufficient_structure'):
            plan_length = structure.get('plan_length', 0)
            feedback_parts.append(
                f"Specific Issue: Plan is too brief ({plan_length} characters). "
                "Expand with step-by-step instructions, file structure, or detailed breakdown."
            )

        return '\n\n'.join(feedback_parts) if feedback_parts else ""

    def should_refine(self, validation_result: Dict[str, Any]) -> bool:
        """
        Determine if plan should be refined

        Args:
            validation_result: Result from PlanValidator

        Returns:
            True if plan should be refined
        """
        return not validation_result.get('valid', False)

    def get_refinement_stats(self, refinement_history: list) -> Dict[str, Any]:
        """
        Get statistics from refinement history

        Args:
            refinement_history: List of refinement attempts

        Returns:
            Statistics dict
        """
        if not refinement_history:
            return {
                'total_refinements': 0,
                'average_score_improvement': 0,
                'success_rate': 0
            }

        total_refinements = len(refinement_history)
        successful_refinements = sum(1 for r in refinement_history if r.get('refinement_applied', False))

        # Calculate score improvements
        score_improvements = []
        for refinement in refinement_history:
            before = refinement.get('score_before', 0)
            after = refinement.get('score_after', 0)
            if after > before:
                score_improvements.append(after - before)

        avg_improvement = sum(score_improvements) / len(score_improvements) if score_improvements else 0

        return {
            'total_refinements': total_refinements,
            'successful_refinements': successful_refinements,
            'success_rate': successful_refinements / total_refinements if total_refinements > 0 else 0,
            'average_score_improvement': avg_improvement,
            'score_improvements': score_improvements
        }
