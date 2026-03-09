"""
IngestionAgent — converts raw documents into Atlas knowledge packs.

Sprint 2 agent. Model: ollama:llama3.1 (low), claude:haiku (high).

Input (via AgentTask):
  objective : ingestion goal
  inputs    : {source: str, source_type: 'text'|'url'|'file'}

Output (AgentResult.result):
  executive_summary, key_concepts, entities, relations,
  actionable_data, ambiguities, knowledge_pack, summary
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class IngestionAgent(BaseAgent):
    """
    Converts any text/doc into a structured knowledge pack for ARIA.
    Output is additive to knowledge base — never replaces existing facts.
    """

    name:    str = "ingestion_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "executive_summary", "key_concepts", "entities",
        "actionable_data", "ambiguities", "knowledge_pack", "summary",
    ]

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    def run(self, task: AgentTask) -> AgentResult:
        source = task.inputs.get("source", task.objective)
        prompt = self._build_prompt(task, source)
        raw    = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw)

        if not structured:
            structured = self._stub_ingest(source)
            errors.append("LLM not available — stub ingestion returned")

        # Ensure knowledge_pack has required structure
        structured = self._normalize_pack(structured, task)

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", "Ingestion complete."),
            result   = structured,
            errors   = errors,
            metadata = {
                "agent":          self.name,
                "version":        self.version,
                "n_concepts":     len(structured.get("key_concepts", [])),
                "n_entities":     len(structured.get("entities", [])),
                "n_facts":        len(structured.get("knowledge_pack", {}).get("facts", [])),
            },
        )

    def _build_prompt(self, task: AgentTask, source: str) -> str:
        if self._prompt_store:
            try:
                return self._prompt_store.render(
                    "ingestion",
                    FUENTE=source[:4000],
                    OBJETIVO=task.objective,
                )
            except Exception:
                pass
        return (
            "Eres el Knowledge Ingestion Agent de Atlas. "
            "Extrae conocimiento estructurado y devuelve SOLO JSON.\n\n"
            f"FUENTE:\n{source[:4000]}\n\n"
            f"OBJETIVO:\n{task.objective}\n\n"
            "Claves requeridas: executive_summary, key_concepts, entities, "
            "relations, actionable_data, ambiguities, knowledge_pack, summary"
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

    def _normalize_pack(self, d: Dict, task: AgentTask) -> Dict:
        """Ensure knowledge_pack has required fields."""
        pack = d.get("knowledge_pack", {})
        pack.setdefault("domain", "atlas_general")
        pack.setdefault("version", "v1")
        pack.setdefault("ingested_at", datetime.utcnow().isoformat())
        pack.setdefault("task_id", task.task_id)
        pack.setdefault("facts", [])
        d["knowledge_pack"] = pack
        return d

    @staticmethod
    def _stub_ingest(source: str) -> Dict:
        return {
            "executive_summary": f"Stub ingestion — fuente de {len(source)} chars.",
            "key_concepts":      ["[requiere LLM real]"],
            "entities":          [],
            "relations":         [],
            "actionable_data":   [],
            "ambiguities":       ["LLM no disponible"],
            "knowledge_pack":    {"domain": "atlas_general", "version": "v1", "facts": []},
            "summary":           "Stub ingestion — configurar LLM provider.",
        }
