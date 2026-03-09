"""
ReviewerAgent — audits code diffs with strict technical review.

Sprint 1 agent. Model: openai:gpt-4o-mini (default), gpt-4o (high risk).

Input (via AgentTask):
  context : project context
  inputs  : {code: str, diff: str}  (at least one required)

Output (AgentResult.result):
  verdict, summary, critical_findings, important_findings,
  minor_findings, good_parts, merge_recommendation, concrete_fixes
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class ReviewerAgent(BaseAgent):
    """
    Code reviewer that returns structured findings and merge recommendation.

    Never modifies code — only analyzes and reports.
    """

    name:    str = "reviewer_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "verdict", "summary", "critical_findings", "important_findings",
        "minor_findings", "good_parts", "merge_recommendation", "concrete_fixes",
    ]

    VALID_VERDICTS    = {"approve", "changes_requested", "reject", "needs_more_info"}
    VALID_MERGE_RECS  = {"merge", "do_not_merge_yet", "needs_discussion", "approved"}

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    # ── Core ─────────────────────────────────────────────────────────────────

    def run(self, task: AgentTask) -> AgentResult:
        code = task.inputs.get("code", "") or task.inputs.get("diff", "")

        prompt = self._build_prompt(task, code)
        raw    = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            return AgentResult(
                task_id  = task.task_id,
                status   = "error",
                summary  = "ReviewerAgent failed to parse LLM response.",
                result   = {"raw_response": raw},
                errors   = errors,
                metadata = {"agent": self.name},
            )

        # Normalize verdict/merge_rec
        structured = self._normalize(structured)

        missing = [k for k in self.REQUIRED_OUTPUT_KEYS if k not in structured]
        if missing:
            errors.append(f"Missing review keys: {missing}")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Review complete."),
            result   = structured,
            errors   = errors,
            metadata = {
                "agent":              self.name,
                "version":            self.version,
                "verdict":            structured.get("verdict", ""),
                "merge_recommendation": structured.get("merge_recommendation", ""),
                "critical_count":     len(structured.get("critical_findings", [])),
            },
        )

    # ── Prompt building ───────────────────────────────────────────────────────

    def _build_prompt(self, task: AgentTask, code: str) -> str:
        ctx = task.context
        ctx_str = (
            f"Proyecto: {ctx.get('project', 'Atlas')}\n"
            f"Módulo: {ctx.get('module', '')}\n"
            f"Constraints: {', '.join(ctx.get('constraints', []))}\n"
        )

        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "reviewer",
                    CONTEXTO=ctx_str,
                    CODIGO=code or task.objective,
                )
            except Exception:
                pass

        return (
            "Eres el Code Reviewer Agent de Atlas. "
            "Analiza el siguiente código y devuelve SOLO JSON.\n\n"
            f"CONTEXTO:\n{ctx_str}\n\n"
            f"CÓDIGO/DIFF:\n{code or task.objective}\n\n"
            "Claves requeridas en el JSON: "
            "verdict, summary, critical_findings, important_findings, "
            "minor_findings, good_parts, merge_recommendation, concrete_fixes"
        )

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, task: AgentTask, prompt: str) -> str:
        if self._llm is None:
            return self._stub_review(task.inputs.get("code", ""))

        if hasattr(self._llm, "generate"):
            try:
                resp = self._llm.generate(
                    prompt     = prompt,
                    agent_name = self.name,
                    risk_level = task.risk_level,
                    model_prefs= task.model_prefs,
                )
                return resp.text
            except Exception as e:
                return self._stub_review(error=str(e))

        if callable(self._llm):
            return self._llm(prompt)

        return self._stub_review()

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_response(self, text: str) -> tuple[Dict, List[str]]:
        errors = []
        text   = text.strip()
        match  = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()

        try:
            return json.loads(text), errors
        except json.JSONDecodeError:
            pass

        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0)), errors
            except json.JSONDecodeError as e:
                errors.append(str(e))

        errors.append("Could not parse JSON from reviewer response")
        return {}, errors

    def _normalize(self, d: Dict) -> Dict:
        """Normalize verdict/merge_rec to valid values."""
        v = d.get("verdict", "needs_more_info").lower().replace(" ", "_")
        if v not in self.VALID_VERDICTS:
            v = "needs_more_info"
        d["verdict"] = v

        m = d.get("merge_recommendation", "needs_discussion").lower().replace(" ", "_")
        if m not in self.VALID_MERGE_RECS:
            m = "needs_discussion"
        d["merge_recommendation"] = m

        return d

    # ── Stub ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _stub_review(code: str = "", error: str = "") -> str:
        lines = len(code.splitlines()) if code else 0
        review = {
            "verdict":           "needs_more_info",
            "summary":           f"Stub review — LLM no disponible. {lines} líneas analizadas superficialmente." + (f" Error: {error}" if error else ""),
            "critical_findings": [],
            "important_findings": [{"issue": "No se pudo ejecutar revisión real", "why_it_matters": "LLM no configurado"}],
            "minor_findings":    [],
            "good_parts":        [],
            "merge_recommendation": "needs_discussion",
            "concrete_fixes":    ["Configurar LLM provider para obtener revisión real"],
        }
        return json.dumps(review)

    # ── Input validation ──────────────────────────────────────────────────────

    def validate_input(self, task: AgentTask) -> List[str]:
        errors = super().validate_input(task)
        code = task.inputs.get("code", "") or task.inputs.get("diff", "")
        if not code and not task.objective:
            errors.append("reviewer requires either inputs.code, inputs.diff, or objective")
        return errors
