"""
RepoScoutAgent — researches patterns, libraries and external repos.

Sprint 2 agent. Model: gemini:flash (large context for research).

Input (via AgentTask):
  objective : what problem to research
  context   : {criteria: list, constraints: list}
  inputs    : {problem: str, criteria: str}

Output (AgentResult.result):
  solution_categories, repeated_patterns, copy_conceptually,
  avoid_copying, adoption_risks, proposal_for_atlas, references, summary
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class RepoScoutAgent(BaseAgent):
    """Research agent. Returns analysis — never downloads or installs anything."""

    name:    str = "repo_scout_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "solution_categories", "repeated_patterns", "copy_conceptually",
        "avoid_copying", "adoption_risks", "proposal_for_atlas",
        "references", "summary",
    ]

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    def run(self, task: AgentTask) -> AgentResult:
        criteria = task.inputs.get("criteria", "") or ", ".join(task.context.get("criteria", []))
        prompt   = self._build_prompt(task, criteria)
        raw      = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            structured = self._stub_scout(task.objective)
            errors.append("LLM not available — stub research returned")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Research complete."),
            result   = structured,
            errors   = errors,
            metadata = {"agent": self.name, "version": self.version},
        )

    def _build_prompt(self, task: AgentTask, criteria: str) -> str:
        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "repo_scout",
                    PROBLEMA=task.objective,
                    CRITERIOS=criteria or "Simplicidad, compatibilidad con Python, licencia permisiva",
                )
            except Exception:
                pass
        return (
            "Eres el Repo Scout Agent de Atlas. "
            "Investiga soluciones y devuelve SOLO JSON.\n\n"
            f"PROBLEMA:\n{task.objective}\n\n"
            f"CRITERIOS:\n{criteria}\n\n"
            "Claves requeridas: solution_categories, repeated_patterns, "
            "copy_conceptually, avoid_copying, adoption_risks, "
            "proposal_for_atlas, references, summary"
        )

    def _call_llm(self, task: AgentTask, prompt: str) -> str:
        if self._llm is None:
            return ""
        if hasattr(self._llm, "generate"):
            try:
                return self._llm.generate(prompt, agent_name=self.name, risk_level=task.risk_level).text
            except Exception:
                return ""
        return self._llm(prompt) if callable(self._llm) else ""

    def _parse_response(self, text: str) -> tuple[Dict, List[str]]:
        if not text:
            return {}, ["Empty LLM response"]
        text = text.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text), []
        except Exception:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group(0)), []
                except Exception as e:
                    return {}, [str(e)]
        return {}, ["Could not parse JSON"]

    @staticmethod
    def _stub_scout(objective: str) -> Dict:
        return {
            "solution_categories": ["[investigar con LLM real]"],
            "repeated_patterns":   [],
            "copy_conceptually":   [],
            "avoid_copying":       [],
            "adoption_risks":      ["LLM no disponible para investigación real"],
            "proposal_for_atlas":  [f"Configurar Gemini API para investigar: {objective}"],
            "references":          [],
            "summary":             f"Stub scout para '{objective}' — requiere LLM.",
        }
