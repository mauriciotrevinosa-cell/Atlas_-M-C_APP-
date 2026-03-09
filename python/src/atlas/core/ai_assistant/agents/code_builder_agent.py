"""
CodeBuilderAgent — proposes clean, modular, testable implementations.

Sprint 2 agent. Model: claude:haiku / claude:sonnet (high risk).

Input (via AgentTask):
  objective : what to build
  context   : {project, module, files, existing_code}
  inputs    : {task: str, existing_code: str}

Output (AgentResult.result):
  approach_summary, files_to_create, files_to_modify,
  proposed_code, risks, tests_suggested, next_step
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class CodeBuilderAgent(BaseAgent):
    """
    Proposes clean code implementations. Never deploys or merges autonomously.
    All output is proposals — human must review before applying.
    """

    name:    str = "code_builder_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "approach_summary", "files_to_create", "files_to_modify",
        "proposed_code", "risks", "tests_suggested", "next_step",
    ]

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    def run(self, task: AgentTask) -> AgentResult:
        existing = task.inputs.get("existing_code", "") or task.context.get("existing_code", "")
        prompt   = self._build_prompt(task, existing)
        raw      = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            structured = self._stub_build(task.objective)
            errors.append("LLM not available — stub proposal returned")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("approach_summary", "Build proposal generated."),
            result   = structured,
            errors   = errors,
            metadata = {"agent": self.name, "version": self.version},
        )

    def _build_prompt(self, task: AgentTask, existing: str) -> str:
        ctx = task.context
        return (
            "Eres el Code Builder Agent de Atlas.\n"
            "Propone implementación limpia, modular y testeable. Devuelve SOLO JSON.\n\n"
            f"TAREA:\n{task.objective}\n\n"
            f"CONTEXTO:\n"
            f"  Módulo: {ctx.get('module', '')}\n"
            f"  Archivos relevantes: {', '.join(ctx.get('files', []))}\n\n"
            + (f"CÓDIGO EXISTENTE:\n{existing[:3000]}\n\n" if existing else "")
            + "Claves requeridas: approach_summary, files_to_create, "
              "files_to_modify, proposed_code, risks, tests_suggested, next_step"
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
        text  = text.strip()
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
        return {}, ["Could not parse JSON from code_builder response"]

    @staticmethod
    def _stub_build(objective: str) -> Dict:
        return {
            "approach_summary":  f"Propuesta stub para: {objective}",
            "files_to_create":   ["[por determinar]"],
            "files_to_modify":   [],
            "proposed_code":     "# TODO: implementar con LLM configurado",
            "risks":             [{"level": "low", "issue": "LLM no disponible"}],
            "tests_suggested":   ["test_happy_path", "test_edge_case"],
            "next_step":         "Configurar LLM provider y re-ejecutar",
        }
