"""
Explain Concept Tool — ARIA Financial Education Engine
=======================================================
Gives ARIA the ability to look up and explain any financial concept
from the Atlas Finance Knowledge Base.

ARIA uses this tool when:
  - User asks "explain [concept]"
  - User asks "how does [concept] work?"
  - User asks "show me the math for [concept]"
  - User types "expand [concept]" after a response
  - A concept is mentioned that deserves deeper explanation

Depth levels:
  "summary"  → One-liner + definition (default — inline use)
  "full"     → Complete explanation: definition + mechanics + formulas + examples + risks
  "math"     → Formulas only (useful when user asks specifically about the math)
  "list"     → List all available concepts (for discovery)

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, Optional

from atlas.assistants.aria.tools.base import Tool
from atlas.shared.finance_concepts import (
    FINANCE_KB,
    format_summary,
    format_full,
    format_math_only,
)

logger = logging.getLogger("atlas.aria.tools.explain_concept")

_DEPTH_OPTIONS = ("summary", "full", "math", "list")


class ExplainConceptTool(Tool):
    """
    Financial concept look-up and educational explainer tool.

    ARIA uses this to deliver structured, in-depth explanations of
    any financial concept — from basic (what is a buy?) to advanced
    (Kelly criterion math, liquidation price formulas).

    Parameters:
        term  (str, required): Concept to look up. Examples:
                               "short selling", "Kelly", "VaR", "drawdown",
                               "leverage", "limit order", "Sharpe ratio"
        depth (str, optional): Detail level. One of:
                               "summary" — one-line + definition (default)
                               "full"    — complete explanation with formulas
                               "math"    — formulas only
                               "list"    — list all available concepts
    """

    def __init__(self):
        super().__init__(
            name="explain_concept",
            description=(
                "Look up and explain financial concepts, trading terms, and market mechanics. "
                "Use when the user asks 'explain X', 'how does X work?', 'show me the math for X', "
                "or types 'expand X' after a response. Covers: buy/sell, long/short, options, "
                "futures, leverage, margin, Kelly criterion, VaR, drawdown, Sharpe ratio, and more."
            ),
            category="education",
        )

        self.add_parameter(
            name="term",
            param_type="string",
            description=(
                "Financial concept to explain. Examples: 'short selling', 'Kelly criterion', "
                "'max drawdown', 'leverage', 'VaR', 'Sharpe ratio', 'limit order', 'options'."
            ),
            required=True,
        )

        self.add_parameter(
            name="depth",
            param_type="string",
            description=(
                "Explanation depth. "
                "'summary' = one-line + definition (default). "
                "'full' = complete: definition + mechanics + formulas + examples + risks. "
                "'math' = formulas only. "
                "'list' = show all available concepts."
            ),
            required=False,
            default="summary",
        )

    def execute(
        self,
        term: str = "",
        depth: str = "summary",
    ) -> Dict[str, Any]:
        """
        Look up and format a financial concept explanation.

        Args:
            term:  Concept name or alias to look up.
            depth: "summary" | "full" | "math" | "list"

        Returns:
            Dict with:
                found:       bool
                term:        str (original query)
                matched_id:  str | None
                matched_name str | None
                content:     str (formatted markdown response)
                related:     List[str] (related concept IDs)
                expand_hint: str (how to go deeper)
        """
        depth = (depth or "summary").lower().strip()

        # ── "list" mode: show available concepts ──────────────────────────
        if term.lower().strip() in ("list", "all", "") or depth == "list":
            return self._list_all_concepts()

        # ── Validate depth ────────────────────────────────────────────────
        if depth not in _DEPTH_OPTIONS:
            depth = "summary"

        # ── Look up concept ───────────────────────────────────────────────
        entry = FINANCE_KB.lookup(term)

        if entry is None:
            # Try fuzzy search
            results = FINANCE_KB.search(term)
            if results:
                # Return top match at summary, suggest others
                entry = results[0]
                logger.info("Fuzzy match: '%s' → '%s'", term, entry.id)
            else:
                return self._not_found(term)

        # ── Format response ───────────────────────────────────────────────
        if depth == "full":
            content = format_full(entry, include_math=True)
        elif depth == "math":
            content = format_math_only(entry)
        else:
            # summary (default)
            content = self._format_summary_response(entry)

        related = entry.related_ids[:5]  # Limit to 5 related

        expand_hint = (
            f"> 💡 **Go deeper:** Type `explain {entry.id} full` for mechanics, "
            f"formulas, and worked examples."
        )
        if depth == "full":
            expand_hint = (
                f"> 🔗 **Related:** {', '.join(f'`{r}`' for r in related)}"
                if related else ""
            )

        return {
            "found":        True,
            "term":         term,
            "matched_id":   entry.id,
            "matched_name": entry.name,
            "content":      content,
            "related":      related,
            "expand_hint":  expand_hint,
        }

    # ------------------------------------------------------------------
    # Internal formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _format_summary_response(entry) -> str:
        """Short summary response for inline use."""
        lines = [
            f"{entry.emoji} **{entry.name}**",
            "",
            f"**Summary:** {entry.summary}",
            "",
            f"**Definition:** {entry.definition}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _list_all_concepts() -> Dict[str, Any]:
        """Return a formatted list of all available concepts."""
        categories = FINANCE_KB.categories()
        lines = ["## 📚 Available Financial Concepts\n"]

        for cat in categories:
            concepts = FINANCE_KB.by_category(cat)
            cat_label = cat.replace("_", " ").title()
            lines.append(f"### {cat_label}")
            for c in concepts:
                lines.append(f"- {c.emoji} **{c.name}** (`{c.id}`) — {c.summary}")
            lines.append("")

        lines.append("---")
        lines.append(
            f"*{len(FINANCE_KB)} concepts available. "
            f"Type `explain [concept]` or `explain [concept] full` for details.*"
        )

        return {
            "found":        True,
            "term":         "list",
            "matched_id":   None,
            "matched_name": None,
            "content":      "\n".join(lines),
            "related":      [],
            "expand_hint":  "",
        }

    @staticmethod
    def _not_found(term: str) -> Dict[str, Any]:
        """Response when concept not found."""
        # Suggest similar concepts via search
        partial = FINANCE_KB.search(term[:4]) if len(term) >= 4 else []
        suggestions = [f"`{c.id}`" for c in partial[:5]]

        content_lines = [
            f"❓ **Concept not found:** `{term}`",
            "",
            "I couldn't find a concept matching that term in my knowledge base.",
        ]

        if suggestions:
            content_lines += [
                "",
                f"**Did you mean:** {', '.join(suggestions)}?",
                "",
                "Or type `explain list` to see all available concepts.",
            ]
        else:
            content_lines += [
                "",
                "Type `explain list` to see all available concepts.",
            ]

        return {
            "found":        False,
            "term":         term,
            "matched_id":   None,
            "matched_name": None,
            "content":      "\n".join(content_lines),
            "related":      [],
            "expand_hint":  "",
        }

    def get_parameters_schema(self) -> Dict:
        """Ollama-compatible parameter schema."""
        return {
            "type": "object",
            "properties": {
                "term": {
                    "type":        "string",
                    "description": (
                        "Financial concept to explain. Examples: 'short selling', "
                        "'Kelly criterion', 'VaR', 'drawdown', 'Sharpe ratio', "
                        "'leverage', 'limit order', 'options', 'futures'."
                    ),
                },
                "depth": {
                    "type":        "string",
                    "enum":        list(_DEPTH_OPTIONS),
                    "description": (
                        "Explanation depth: 'summary' (default), 'full' (complete with math), "
                        "'math' (formulas only), 'list' (show all concepts)."
                    ),
                },
            },
            "required": ["term"],
        }
