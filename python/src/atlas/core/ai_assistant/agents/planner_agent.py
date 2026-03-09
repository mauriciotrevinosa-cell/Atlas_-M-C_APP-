"""
PlannerAgent — converts a goal into a small, verifiable, executable plan.

Sprint 1 agent. Model: ollama:qwen2.5 (low/medium), openai:gpt-4o-mini (high).

Input (via AgentTask):
  objective  : the goal to plan
  context    : {project, module, files, constraints, ...}

Output (AgentResult.result):
  expected_result, assumptions, risks, steps, files_to_touch,
  tests_required, validation_criteria, not_now, summary
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class PlannerAgent(BaseAgent):
    """
    Converts an objective into a structured, executable plan.

    Uses a prompt template + LLM to produce a deterministic JSON plan.
    Never makes code changes — only plans.
    """

    name:    str = "planner_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "expected_result", "assumptions", "risks", "steps",
        "files_to_touch", "tests_required", "validation_criteria",
        "not_now", "summary",
    ]

    def __init__(self, llm_client=None, prompt_store=None):
        """
        Parameters
        ----------
        llm_client   : callable(prompt: str) -> str  OR  ModelRouter instance
        prompt_store : PromptStore instance (optional; uses inline template if None)
        """
        self._llm          = llm_client
        self._prompt_store = prompt_store

    # ── Core ─────────────────────────────────────────────────────────────────

    def run(self, task: AgentTask) -> AgentResult:
        prompt = self._build_prompt(task)

        # Call LLM
        raw_text = self._call_llm(task, prompt)

        # Parse + validate
        structured, parse_errors = self._parse_response(raw_text)

        if parse_errors and not structured:
            return AgentResult(
                task_id  = task.task_id,
                status   = "error",
                summary  = f"PlannerAgent failed to parse LLM response: {parse_errors[0]}",
                result   = {"raw_response": raw_text},
                errors   = parse_errors,
                metadata = {"agent": self.name, "version": self.version},
            )

        # Validate required keys
        missing = [k for k in self.REQUIRED_OUTPUT_KEYS if k not in structured]
        if missing:
            parse_errors.append(f"Missing keys in plan: {missing}")

        status = "success" if not parse_errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Plan generated."),
            result   = structured,
            errors   = parse_errors,
            metadata = {
                "agent":    self.name,
                "version":  self.version,
                "n_steps":  len(structured.get("steps", [])),
            },
        )

    # ── Prompt building ───────────────────────────────────────────────────────

    def _build_prompt(self, task: AgentTask) -> str:
        ctx = task.context
        constraints = ctx.get("constraints", [])
        if isinstance(constraints, list):
            constraints = "\n".join(f"- {c}" for c in constraints)

        context_str = (
            f"Proyecto: {ctx.get('project', 'Atlas')}\n"
            f"Módulo:   {ctx.get('module', 'unknown')}\n"
            f"Archivos relevantes: {', '.join(ctx.get('files', [])) or 'no especificados'}\n"
        )

        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "planner",
                    OBJETIVO=task.objective,
                    CONTEXTO=context_str,
                    RESTRICCIONES=constraints or "Sin restricciones adicionales.",
                )
            except Exception:
                pass

        # Inline fallback template
        return (
            "Eres el Planner Agent de Atlas. "
            "Convierte el objetivo en un plan JSON estructurado.\n\n"
            f"OBJETIVO:\n{task.objective}\n\n"
            f"CONTEXTO:\n{context_str}\n\n"
            f"RESTRICCIONES:\n{constraints or 'Sin restricciones.'}\n\n"
            "Devuelve SOLO JSON con estas claves:\n"
            "expected_result, assumptions, risks, steps, files_to_touch, "
            "tests_required, validation_criteria, not_now, summary"
        )

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, task: AgentTask, prompt: str) -> str:
        if self._llm is None:
            # No LLM configured → return stub plan
            return self._stub_plan(task.objective)

        # ModelRouter interface
        if hasattr(self._llm, "generate"):
            try:
                response = self._llm.generate(
                    prompt     = prompt,
                    agent_name = self.name,
                    risk_level = task.risk_level,
                    model_prefs= task.model_prefs,
                )
                return response.text
            except Exception as e:
                return self._stub_plan(task.objective, error=str(e))

        # Plain callable interface
        if callable(self._llm):
            return self._llm(prompt)

        return self._stub_plan(task.objective)

    # ── Response parsing ──────────────────────────────────────────────────────

    def _parse_response(self, text: str) -> tuple[Dict, List[str]]:
        """Extract and parse JSON from LLM response. Returns (dict, errors)."""
        import re
        errors = []
        text   = text.strip()

        # Strip markdown code fences
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()

        # Try direct parse
        try:
            return json.loads(text), errors
        except json.JSONDecodeError:
            pass

        # Try to find JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0)), errors
            except json.JSONDecodeError as e:
                errors.append(f"JSON parse error: {e}")

        errors.append("Could not extract valid JSON from response")
        return {}, errors

    # ── Stub (when no LLM available) ─────────────────────────────────────────

    @staticmethod
    def _stub_plan(objective: str, error: str = "") -> str:
        plan = {
            "expected_result": f"Implementar: {objective}",
            "assumptions":     ["Módulo target ya existe", "Tests pueden ejecutarse localmente"],
            "risks":           [{"level": "medium", "issue": "Scope unclear", "mitigation": "Break into smaller tasks"}],
            "steps":           ["Analizar código existente", "Definir interfaces", "Implementar", "Agregar tests", "Revisar"],
            "files_to_touch":  ["[por determinar]"],
            "tests_required":  ["test_happy_path", "test_edge_case", "test_error_case"],
            "validation_criteria": ["Tests pasan", "Sin regresiones"],
            "not_now":         ["Optimizaciones prematuras", "Refactors no relacionados"],
            "summary":         f"Plan stub para: {objective}" + (f" (LLM error: {error})" if error else ""),
        }
        return json.dumps(plan)

    # ── Input validation ──────────────────────────────────────────────────────

    def validate_input(self, task: AgentTask) -> List[str]:
        errors = super().validate_input(task)
        if len(task.objective) > 2000:
            errors.append("objective too long (>2000 chars); please be more concise")
        return errors
