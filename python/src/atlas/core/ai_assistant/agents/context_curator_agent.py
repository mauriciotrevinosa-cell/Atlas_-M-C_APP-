"""
ContextCuratorAgent — filters and compresses context for other agents.

Sprint 1 agent. Model: ollama:llama3.1 (low), claude:haiku (high).

Input (via AgentTask):
  objective : goal of the destination agent
  context   : {full_context: str}  OR  context dict with many keys

Output (AgentResult.result):
  required_context, optional_context, irrelevant_context,
  compact_prompt_context, context_risks, summary
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class ContextCuratorAgent(BaseAgent):
    """
    Reduces context to the minimum necessary for a target agent.

    Key contract: compact_prompt_context must be usable as-is as a
    prompt prefix for any other Atlas agent.
    """

    name:    str = "context_curator_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "required_context", "optional_context", "irrelevant_context",
        "compact_prompt_context", "context_risks", "summary",
    ]

    MAX_COMPACT_WORDS = 300

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    # ── Core ─────────────────────────────────────────────────────────────────

    def run(self, task: AgentTask) -> AgentResult:
        full_ctx = self._extract_context_string(task)
        prompt   = self._build_prompt(task, full_ctx)
        raw      = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            # Fallback: return a basic truncated context
            compact = full_ctx[:1500] + "..." if len(full_ctx) > 1500 else full_ctx
            structured = {
                "required_context":     ["[contexto completo — no se pudo curar]"],
                "optional_context":     [],
                "irrelevant_context":   [],
                "compact_prompt_context": compact,
                "context_risks":        ["LLM no disponible — contexto no fue filtrado"],
                "summary":              "Contexto retornado sin filtrar (LLM no disponible).",
            }
            errors.append("LLM not available — returned unfiltered context")

        # Enforce word limit on compact context
        structured = self._enforce_limits(structured)

        missing = [k for k in self.REQUIRED_OUTPUT_KEYS if k not in structured]
        if missing:
            errors.append(f"Missing curator keys: {missing}")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Context curated."),
            result   = structured,
            errors   = errors,
            metadata = {
                "agent":               self.name,
                "version":             self.version,
                "required_count":      len(structured.get("required_context", [])),
                "irrelevant_count":    len(structured.get("irrelevant_context", [])),
                "compact_word_count":  len(structured.get("compact_prompt_context", "").split()),
            },
        )

    # ── Prompt ───────────────────────────────────────────────────────────────

    def _build_prompt(self, task: AgentTask, full_ctx: str) -> str:
        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "context_curator",
                    OBJETIVO=task.objective,
                    CONTEXTO_TOTAL=full_ctx[:4000],
                )
            except Exception:
                pass

        return (
            "Eres el Context Curator Agent de Atlas. "
            "Filtra el contexto y devuelve SOLO JSON.\n\n"
            f"OBJETIVO DEL AGENTE DESTINO:\n{task.objective}\n\n"
            f"CONTEXTO DISPONIBLE:\n{full_ctx[:4000]}\n\n"
            "Claves requeridas: required_context, optional_context, "
            "irrelevant_context, compact_prompt_context (máx 300 palabras), "
            "context_risks, summary"
        )

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, task: AgentTask, prompt: str) -> str:
        if self._llm is None:
            return ""

        if hasattr(self._llm, "generate"):
            try:
                resp = self._llm.generate(
                    prompt     = prompt,
                    agent_name = self.name,
                    risk_level = task.risk_level,
                    model_prefs= task.model_prefs,
                )
                return resp.text
            except Exception:
                return ""

        if callable(self._llm):
            return self._llm(prompt)

        return ""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_context_string(self, task: AgentTask) -> str:
        """Flatten context dict or full_context string."""
        ctx = task.context
        if "full_context" in ctx:
            return str(ctx["full_context"])

        parts = []
        for k, v in ctx.items():
            if isinstance(v, list):
                parts.append(f"{k}:\n" + "\n".join(f"  - {i}" for i in v))
            else:
                parts.append(f"{k}: {v}")
        return "\n".join(parts)

    def _enforce_limits(self, d: Dict) -> Dict:
        """Truncate compact_prompt_context to MAX_COMPACT_WORDS words."""
        compact = d.get("compact_prompt_context", "")
        words   = compact.split()
        if len(words) > self.MAX_COMPACT_WORDS:
            d["compact_prompt_context"] = " ".join(words[:self.MAX_COMPACT_WORDS]) + " [...]"
        return d

    def _parse_response(self, text: str) -> tuple[Dict, List[str]]:
        errors = []
        if not text:
            return {}, ["Empty LLM response"]
        text  = text.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
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
        errors.append("Could not parse JSON from context_curator response")
        return {}, errors
