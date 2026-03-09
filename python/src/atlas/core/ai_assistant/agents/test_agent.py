"""
TestAgent — designs pytest test suites for Atlas modules.

Sprint 1 agent. Model: claude:haiku (all risk levels).

Input (via AgentTask):
  objective : module purpose
  inputs    : {code: str}

Output (AgentResult.result):
  functional_risks, nominal_cases, edge_cases, error_cases,
  fixtures_needed, pytest_starter_code, missing_coverage, summary
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class TestDesignAgent(BaseAgent):
    """
    Generates comprehensive pytest test designs.

    Produces: risk analysis + case list + starter pytest code.
    Never runs tests — only designs them.
    """

    __test__ = False   # prevent pytest from collecting this as a test class

    name:    str = "test_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "functional_risks", "nominal_cases", "edge_cases",
        "error_cases", "fixtures_needed", "pytest_starter_code",
        "missing_coverage", "summary",
    ]

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    # ── Core ─────────────────────────────────────────────────────────────────

    def run(self, task: AgentTask) -> AgentResult:
        code   = task.inputs.get("code", "")
        prompt = self._build_prompt(task, code)
        raw    = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            return AgentResult(
                task_id  = task.task_id,
                status   = "error",
                summary  = "TestAgent failed to parse LLM response.",
                result   = {"raw_response": raw},
                errors   = errors,
                metadata = {"agent": self.name},
            )

        missing = [k for k in self.REQUIRED_OUTPUT_KEYS if k not in structured]
        if missing:
            errors.append(f"Missing test keys: {missing}")

        # Validate pytest code contains actual tests
        starter = structured.get("pytest_starter_code", "")
        if starter and "def test_" not in starter:
            errors.append("pytest_starter_code has no test functions")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Test design complete."),
            result   = structured,
            errors   = errors,
            metadata = {
                "agent":         self.name,
                "version":       self.version,
                "n_nominal":     len(structured.get("nominal_cases", [])),
                "n_edge":        len(structured.get("edge_cases", [])),
                "n_error":       len(structured.get("error_cases", [])),
            },
        )

    # ── Prompt ───────────────────────────────────────────────────────────────

    def _build_prompt(self, task: AgentTask, code: str) -> str:
        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "test_agent",
                    OBJETIVO_DEL_MODULO=task.objective,
                    CODIGO=code or "[no code provided]",
                )
            except Exception:
                pass

        return (
            "Eres el Test Agent de Atlas. "
            "Diseña tests pytest completos y devuelve SOLO JSON.\n\n"
            f"OBJETIVO DEL MÓDULO:\n{task.objective}\n\n"
            f"CÓDIGO:\n{code or '[no code provided]'}\n\n"
            "Claves requeridas: functional_risks, nominal_cases, edge_cases, "
            "error_cases, fixtures_needed, pytest_starter_code, missing_coverage, summary"
        )

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, task: AgentTask, prompt: str) -> str:
        if self._llm is None:
            return self._stub_tests(task.objective)

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
                return self._stub_tests(task.objective, error=str(e))

        if callable(self._llm):
            return self._llm(prompt)

        return self._stub_tests(task.objective)

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
        errors.append("Could not parse JSON from test_agent response")
        return {}, errors

    # ── Stub ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _stub_tests(objective: str = "", error: str = "") -> str:
        module_name = objective.split()[0].lower().replace("-", "_") if objective else "module"
        result = {
            "functional_risks":  ["Riesgo sin LLM: tests no personalizados al código real"],
            "nominal_cases":     [{"name": f"test_{module_name}_happy_path", "description": "Input válido → output correcto"}],
            "edge_cases":        [{"name": f"test_{module_name}_empty_input", "description": "Input vacío → error controlado"}],
            "error_cases":       [{"name": f"test_{module_name}_invalid_type", "description": "Tipo incorrecto → TypeError o ValidationError"}],
            "fixtures_needed":   [f"{module_name}_mock: instancia del módulo con dependencias mockeadas"],
            "pytest_starter_code": (
                f"import pytest\n\n\n"
                f"@pytest.fixture\ndef {module_name}_instance():\n"
                f"    # TODO: instanciar el módulo\n"
                f"    pass\n\n\n"
                f"def test_{module_name}_happy_path({module_name}_instance):\n"
                f"    # TODO: implementar test nominal\n"
                f"    assert {module_name}_instance is not None\n\n\n"
                f"def test_{module_name}_empty_input({module_name}_instance):\n"
                f"    # TODO: testear input vacío\n"
                f"    pass\n"
            ),
            "missing_coverage":  ["Integración con otros módulos", "Casos de concurrencia"],
            "summary":           f"Stub test design para '{objective}'" + (f" (error LLM: {error})" if error else ""),
        }
        return json.dumps(result)
