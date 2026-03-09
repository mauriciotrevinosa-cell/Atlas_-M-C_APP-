"""
ResultValidator — validates AgentResult outputs before they leave the orchestrator.

Each agent type has specific required keys in its result dict.
The validator checks contracts without knowing implementation details.
"""

from __future__ import annotations

from typing import Dict, List

from .task_schema import AgentResult


# Required keys per agent type
_REQUIRED_KEYS: Dict[str, List[str]] = {
    "planner_agent": [
        "expected_result", "steps", "files_to_touch",
        "tests_required", "validation_criteria",
    ],
    "reviewer_agent": [
        "verdict", "critical_findings", "important_findings",
        "merge_recommendation", "concrete_fixes",
    ],
    "test_agent": [
        "functional_risks", "nominal_cases", "edge_cases",
        "error_cases", "pytest_starter_code",
    ],
    "context_curator_agent": [
        "required_context", "optional_context",
        "compact_prompt_context",
    ],
    "code_builder_agent": [
        "approach_summary", "files_to_create", "files_to_modify",
        "tests_suggested",
    ],
    "repo_scout_agent": [
        "solution_categories", "repeated_patterns",
        "proposal_for_atlas",
    ],
    "ingestion_agent": [
        "executive_summary", "key_concepts", "actionable_data",
        "knowledge_pack",
    ],
    "docs_agent": [
        "document_type", "content",
    ],
}

# Valid verdict values for reviewer
_VALID_VERDICTS = {"approve", "changes_requested", "reject", "needs_more_info"}

# Valid merge recommendations
_VALID_MERGE_RECS = {"merge", "do_not_merge_yet", "needs_discussion", "approved"}


class ResultValidator:
    """
    Validates AgentResult.result dict against per-agent contracts.

    Returns list of error strings (empty = valid).
    """

    def validate(self, result: AgentResult) -> List[str]:
        """Main validation entry point."""
        errors: List[str] = []

        # Status must be valid
        if result.status not in ("success", "error", "partial"):
            errors.append(f"Invalid status: {result.status!r}")

        # If error, no further structural validation needed
        if result.status == "error":
            return errors

        # Summary required
        if not result.summary or not result.summary.strip():
            errors.append("AgentResult.summary is empty")

        # Agent-specific result keys
        agent_name = result.metadata.get("agent", "")
        required   = _REQUIRED_KEYS.get(agent_name, [])
        for key in required:
            if key not in result.result:
                errors.append(f"result missing required key: '{key}'")

        # Agent-specific semantic checks
        errors.extend(self._semantic_checks(agent_name, result.result))

        return errors

    def _semantic_checks(self, agent_name: str, result: dict) -> List[str]:
        errors = []

        if agent_name == "planner_agent":
            steps = result.get("steps", [])
            if not steps:
                errors.append("planner: steps list is empty")
            if len(steps) > 20:
                errors.append(f"planner: too many steps ({len(steps)}), consider splitting")

        elif agent_name == "reviewer_agent":
            verdict = result.get("verdict", "")
            if verdict and verdict not in _VALID_VERDICTS:
                errors.append(f"reviewer: invalid verdict '{verdict}'. Must be one of {_VALID_VERDICTS}")
            merge_rec = result.get("merge_recommendation", "")
            if merge_rec and merge_rec not in _VALID_MERGE_RECS:
                errors.append(f"reviewer: invalid merge_recommendation '{merge_rec}'")

        elif agent_name == "test_agent":
            code = result.get("pytest_starter_code", "")
            if code and "def test_" not in code:
                errors.append("test_agent: pytest_starter_code has no test functions (def test_)")

        return errors

    def __repr__(self) -> str:
        return f"ResultValidator(agents={list(_REQUIRED_KEYS.keys())})"
