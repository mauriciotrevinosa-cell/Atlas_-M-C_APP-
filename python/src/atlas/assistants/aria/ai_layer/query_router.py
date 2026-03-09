"""
Query Router — Classifies user intent and dispatches to the right handler.

Flow:
  1. User sends query
  2. Router classifies intent (using LLM or rules)
  3. Routes to correct prompt + tools
  4. Returns classification result

Supports both:
  - Rule-based (fast, no LLM call) for common patterns
  - LLM-based (accurate, slower) for ambiguous queries
"""

import re
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .prompt_store import PromptStore


@dataclass
class RouteResult:
    """Result of query classification."""
    category: str
    confidence: float
    reasoning: str
    prompt_name: str  # Which prompt to use
    tools_needed: list  # Which tools to attach
    use_context: bool  # Whether to inject project context


# Rule-based patterns for fast classification (no LLM call needed)
RULE_PATTERNS = {
    "project_data": {
        "patterns": [
            r"\b(ctc|costo total|precio m2|terreno|unidades|cajones|amenidades)\b",
            r"\b(kin towers|bonampak|cancun|torre residencial|torre hotelera)\b",
            r"\b(fideicomiso|invex|mid4|masterbroker|ceron)\b",
            r"\b(superficie|m2 vendible|cos|cus|densidad)\b",
            r"\b(mauricio|carlos pickering|azyadeh|trevino)\b",
        ],
        "prompt": "system",
        "tools": [],
        "context": True,
    },
    "financial_analysis": {
        "patterns": [
            r"\b(simulador|escenario|what.if|que pasa si)\b",
            r"\b(tipo de cambio|tc|contingencia|comision|fees)\b",
            r"\b(roi|rendimiento|rentabilidad|flujo|inversi[oó]n)\b",
            r"\b(calcul|estim|proyect|presupuest)\w*",
        ],
        "prompt": "system",
        "tools": ["execute_code"],
        "context": True,
    },
    "market_data": {
        "patterns": [
            r"\b(spy|aapl|tsla|msft|stock|market|portfolio)\b",
            r"\b(precio|price|buy|sell|trade|posicion)\b",
            r"\b(backtest|signal|strategy|indicator)\b",
        ],
        "prompt": "system",
        "tools": ["get_data", "execute_code"],
        "context": False,
    },
    "code_execution": {
        "patterns": [
            r"\b(python|javascript|code|script|programa)\b",
            r"\b(create file|crear archivo|write|ejecuta)\b",
            r"\b(function|class|import|def |print\()\b",
        ],
        "prompt": "system",
        "tools": ["execute_code", "create_file", "read_file"],
        "context": False,
    },
    "web_search": {
        "patterns": [
            r"\b(search|busca|news|noticias|latest|recent)\b",
            r"\b(google|web|internet|online)\b",
            r"\b(que es|what is|how to|como)\b",
        ],
        "prompt": "system",
        "tools": ["web_search"],
        "context": False,
    },
    "document_query": {
        "patterns": [
            r"\b(documento|excel|presentacion|pptx|xlsx)\b",
            r"\b(segun|according to|dice|says)\b",
            r"\b(slide|hoja|sheet|pagina)\b",
        ],
        "prompt": "system",
        "tools": ["read_file"],
        "context": True,
    },
    "conversation": {
        "patterns": [
            r"^(hola|hello|hi|hey|buenos?\s+d[ií]as?|buenas?\s+tardes?|buenas?\s+noches?)",
            r"\b(quien eres|who are you|que puedes|what can you)\b",
            r"\b(ayuda|help|gracias|thanks)\b",
        ],
        "prompt": "system",
        "tools": [],
        "context": False,
    },
}


class QueryRouter:
    """
    Classifies user queries and routes to appropriate handlers.

    Two modes:
      1. Rule-based: Fast regex matching for common patterns
      2. LLM-based: Uses the router_classify prompt for complex queries
    """

    def __init__(self, prompt_store: PromptStore, provider=None):
        """
        Args:
            prompt_store: PromptStore instance for loading prompts
            provider: LLM provider for LLM-based classification (optional)
        """
        self.prompt_store = prompt_store
        self.provider = provider
        self._classification_log = []

    def classify(self, query: str) -> RouteResult:
        """
        Classify a user query.

        First tries rule-based matching. If no confident match,
        falls back to LLM classification.

        Args:
            query: User's input text

        Returns:
            RouteResult with category, confidence, and routing info
        """
        # Step 1: Try rule-based classification
        result = self._rule_classify(query)

        if result and result.confidence >= 0.7:
            self._log(query, result, method="rules")
            return result

        # Step 2: Try LLM classification if provider available
        if self.provider:
            llm_result = self._llm_classify(query)
            if llm_result:
                self._log(query, llm_result, method="llm")
                return llm_result

        # Step 3: Default to conversation
        default = RouteResult(
            category="conversation",
            confidence=0.3,
            reasoning="No confident match — defaulting to conversation",
            prompt_name="system",
            tools_needed=[],
            use_context=False,
        )
        self._log(query, default, method="default")
        return default

    def _rule_classify(self, query: str) -> Optional[RouteResult]:
        """Rule-based classification using regex patterns."""
        query_lower = query.lower().strip()
        best_category = None
        best_score = 0
        best_matches = 0

        for category, config in RULE_PATTERNS.items():
            matches = 0
            for pattern in config["patterns"]:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    matches += 1

            # Score based on number of pattern matches
            if matches > 0:
                score = min(1.0, matches * 0.3 + 0.4)  # 1 match = 0.7, 2 = 1.0
                if score > best_score:
                    best_score = score
                    best_category = category
                    best_matches = matches

        if best_category:
            config = RULE_PATTERNS[best_category]
            return RouteResult(
                category=best_category,
                confidence=best_score,
                reasoning=f"Matched {best_matches} rule patterns for '{best_category}'",
                prompt_name=config["prompt"],
                tools_needed=config["tools"],
                use_context=config["context"],
            )
        return None

    def _llm_classify(self, query: str) -> Optional[RouteResult]:
        """LLM-based classification using router_classify prompt."""
        try:
            classify_prompt = self.prompt_store.get("router_classify")
            messages = [
                {"role": "system", "content": classify_prompt},
                {"role": "user", "content": query},
            ]

            response = self.provider.chat(messages, temperature=0.1)

            # Parse JSON response
            content = response.content.strip()
            # Extract JSON from potential markdown code block
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                category = data.get("category", "conversation")
                confidence = float(data.get("confidence", 0.5))
                reasoning = data.get("reasoning", "LLM classification")

                # Look up routing config
                config = RULE_PATTERNS.get(category, {
                    "prompt": "system",
                    "tools": [],
                    "context": False,
                })

                return RouteResult(
                    category=category,
                    confidence=confidence,
                    reasoning=reasoning,
                    prompt_name=config.get("prompt", "system"),
                    tools_needed=config.get("tools", []),
                    use_context=config.get("context", False),
                )
        except Exception as e:
            pass  # Fall through to default

        return None

    def _log(self, query: str, result: RouteResult, method: str):
        """Log classification for audit trail."""
        self._classification_log.append({
            "query": query[:200],
            "category": result.category,
            "confidence": result.confidence,
            "method": method,
            "reasoning": result.reasoning,
        })

    def get_log(self) -> list:
        """Get classification audit log."""
        return self._classification_log

    def get_stats(self) -> Dict:
        """Get routing statistics."""
        if not self._classification_log:
            return {"total": 0}

        categories = {}
        methods = {}
        for entry in self._classification_log:
            cat = entry["category"]
            categories[cat] = categories.get(cat, 0) + 1
            method = entry["method"]
            methods[method] = methods.get(method, 0) + 1

        return {
            "total": len(self._classification_log),
            "categories": categories,
            "methods": methods,
            "avg_confidence": sum(
                e["confidence"] for e in self._classification_log
            ) / len(self._classification_log),
        }
