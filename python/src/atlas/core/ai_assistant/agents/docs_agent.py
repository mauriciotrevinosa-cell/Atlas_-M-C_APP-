"""
DocsAgent — generates ADRs, changelogs, module specs and documentation.

Sprint 2 agent. Model: claude:haiku (all levels).

Input (via AgentTask):
  objective : what document to generate
  context   : {module, change_description, files_changed}
  inputs    : {document_type: 'adr'|'changelog'|'module_spec'|'readme', content: str}

Output (AgentResult.result):
  document_type, content, title, metadata, summary
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


# Supported document types
DOC_TYPES = ("adr", "changelog", "module_spec", "readme", "api_doc")


class DocsAgent(BaseAgent):
    """
    Generates structured documentation for Atlas modules.

    Never commits or publishes autonomously.
    All docs are proposals — human reviews before publishing.
    """

    name:    str = "docs_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = ["document_type", "content", "title", "summary"]

    # ADR template (Architecture Decision Records)
    _ADR_TEMPLATE = """# ADR-{number}: {title}

**Date:** {date}
**Status:** Proposed
**Deciders:** Atlas Engineering

## Context

{context}

## Decision

{decision}

## Consequences

### Positive
{positive}

### Negative
{negative}

## Alternatives Considered

{alternatives}
"""

    def __init__(self, llm_client=None, prompt_store=None):
        self._llm          = llm_client
        self._prompt_store = prompt_store

    def run(self, task: AgentTask) -> AgentResult:
        doc_type = task.inputs.get("document_type", "module_spec")
        if doc_type not in DOC_TYPES:
            doc_type = "module_spec"

        prompt = self._build_prompt(task, doc_type)
        raw    = self._call_llm(task, prompt)
        structured, errors = self._parse_response(raw, doc_type, task)

        if not structured:
            structured = self._stub_doc(doc_type, task)
            errors.append("LLM not available — stub document returned")

        status = "success" if not errors else "partial"

        return AgentResult(
            task_id  = task.task_id,
            status   = status,
            summary  = structured.get("summary", f"Document generated: {doc_type}"),
            result   = structured,
            errors   = errors,
            metadata = {
                "agent":         self.name,
                "version":       self.version,
                "document_type": doc_type,
                "word_count":    len(structured.get("content", "").split()),
            },
        )

    def _build_prompt(self, task: AgentTask, doc_type: str) -> str:
        ctx      = task.context
        content  = task.inputs.get("content", "")
        doc_desc = {
            "adr":         "Architecture Decision Record (ADR) en formato Markdown estándar",
            "changelog":   "CHANGELOG entry en formato Keep a Changelog",
            "module_spec": "Module Specification con propósito, API, dependencias y ejemplos",
            "readme":      "README.md completo con instalación, uso y ejemplos",
            "api_doc":     "Documentación de API con endpoints, parámetros y ejemplos",
        }.get(doc_type, "documento técnico")

        return (
            f"Eres el Docs Agent de Atlas. Genera un {doc_desc}.\n\n"
            f"MÓDULO/CONTEXTO:\n"
            f"  Módulo: {ctx.get('module', 'Atlas')}\n"
            f"  Cambio: {ctx.get('change_description', task.objective)}\n"
            f"  Archivos: {', '.join(ctx.get('files_changed', []))}\n\n"
            + (f"CONTENIDO BASE:\n{content[:3000]}\n\n" if content else "")
            + "Devuelve SOLO JSON con: document_type, title, content (Markdown), metadata, summary"
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

    def _parse_response(self, text: str, doc_type: str, task: AgentTask) -> tuple[Dict, List[str]]:
        if not text:
            return {}, ["Empty LLM response"]
        text = text.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text), []
        except json.JSONDecodeError:
            # If response is raw markdown (not JSON), wrap it
            if text.startswith("#") or "##" in text:
                doc = {
                    "document_type": doc_type,
                    "title":         task.objective,
                    "content":       text,
                    "metadata":      {"generated_at": datetime.now(timezone.utc).isoformat()},
                    "summary":       f"{doc_type} generated for: {task.objective}",
                }
                return doc, []
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group(0)), []
                except Exception as e:
                    return {}, [str(e)]
        return {}, ["Could not parse response"]

    def _stub_doc(self, doc_type: str, task: AgentTask) -> Dict:
        module = task.context.get("module", "atlas_module")
        if doc_type == "adr":
            content = self._ADR_TEMPLATE.format(
                number=1, title=task.objective, date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                context=f"[Describir contexto de: {task.objective}]",
                decision="[Describir la decisión tomada]",
                positive="- [Beneficio 1]\n- [Beneficio 2]",
                negative="- [Tradeoff 1]",
                alternatives="- [Alternativa A]: [Por qué se descartó]",
            )
        elif doc_type == "changelog":
            content = (
                f"## [{datetime.now(timezone.utc).strftime('%Y-%m-%d')}]\n\n"
                f"### Added\n- {task.objective}\n\n"
                f"### Changed\n- [Describir cambios]\n\n"
                f"### Fixed\n- [Describir fixes]\n"
            )
        else:
            content = (
                f"# {module}\n\n"
                f"## Propósito\n{task.objective}\n\n"
                f"## API\n[Por documentar]\n\n"
                f"## Dependencias\n[Por documentar]\n\n"
                f"## Ejemplos\n```python\n# TODO\n```\n"
            )
        return {
            "document_type": doc_type,
            "title":         task.objective,
            "content":       content,
            "metadata":      {"generated_at": datetime.now(timezone.utc).isoformat(), "stub": True},
            "summary":       f"Stub {doc_type} para '{task.objective}' — completar con LLM real.",
        }
