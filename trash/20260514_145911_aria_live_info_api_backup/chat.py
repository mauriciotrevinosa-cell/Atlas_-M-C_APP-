"""
ARIA Chat Engine — v3.0 (Provider-Agnostic)

Previously this file hard-imported `ollama` at the top and called
`ollama.chat()` directly. That made Ollama a hard dependency and crashed
the whole app if the Ollama daemon wasn't running.

v3.0 change: route every chat call through `ProviderManager`, which
already handles fallback across Ollama / Groq / OpenRouter / Cerebras /
OpenAI / Mock. Ollama is now ONE option in a chain, not a requirement.

Enhancements preserved from v2:
- Professional system prompt v2.0
- Parameter validation
- Robust error handling
- Tool calling
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

from .validation import validate_tool_params, ValidationError
from .system_prompt import get_system_prompt

# Lazy-import the provider manager so this module doesn't explode if one
# of the optional provider SDKs isn't installed.
try:
    from ..ai_layer.provider_manager import ProviderManager
    from ..ai_layer.providers.base import LLMResponse
    _PROVIDER_MANAGER_AVAILABLE = True
except Exception as _pm_exc:  # pragma: no cover - defensive
    ProviderManager = None  # type: ignore
    LLMResponse = None       # type: ignore
    _PROVIDER_MANAGER_AVAILABLE = False
    logging.getLogger("atlas.aria").warning(
        "ProviderManager unavailable (%s); ARIA will fall back to direct Ollama if present.",
        _pm_exc,
    )

logger = logging.getLogger("atlas.aria")


class ARIA:
    """
    ARIA (Atlas Reasoning & Intelligence Assistant) — v3.0

    Backend is selected automatically:
      1. ProviderManager picks the first available provider in the fallback
         chain based on env vars (GROQ_API_KEY, OPENROUTER_API_KEY, etc.)
      2. If none are configured, it falls back to MockProvider so the app
         still boots and the UI stays responsive.
      3. Ollama is supported but no longer required.
    """

    def __init__(self,
                 model: Optional[str] = None,
                 host: Optional[str] = None,
                 temperature: float = 0.7,
                 preferred_provider: Optional[str] = None,
                 fallback_chain: Optional[List[str]] = None):
        """
        Initialize ARIA with a provider-agnostic backend.

        Args:
            model: Optional model override (used only if the preferred provider
                   needs one). Defaults per-provider.
            host:  Kept for backward compatibility (Ollama host).
            temperature: Sampling temperature.
            preferred_provider: e.g. "groq", "openrouter", "ollama", "anthropic".
                                Falls back automatically if unavailable.
            fallback_chain: Override the default provider priority order.
        """
        self.model = model or os.getenv("ARIA_DEFAULT_MODEL", "llama3.1:8b")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.temperature = temperature

        # Conversation history
        self.history: List[Dict[str, str]] = []

        # Tool registry
        self.tools: Dict[str, Any] = {}
        self.tool_schemas: List[Dict] = []

        # System prompt v2.0
        self.system_prompt = get_system_prompt(version="2.0")

        # Version
        self.__version__ = "3.0.0"

        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "tools_called": 0,
            "validation_errors": 0
        }

        # Structured tool-call audit trail
        self.tool_event_log_path = Path("outputs") / "runs" / "aria_tool_calls.jsonl"
        self.tool_event_log_path.parent.mkdir(parents=True, exist_ok=True)

        # --- Provider setup (the actual v3 change) -----------------------
        # Preferred provider defaults to the env var, else None (=> manager
        # picks the first available in the chain).
        self.preferred_provider = (
            preferred_provider
            or os.getenv("ARIA_LLM_BACKEND")
            or None
        )
        self.backend = self.preferred_provider or "auto"

        self._provider_manager = None
        if _PROVIDER_MANAGER_AVAILABLE:
            try:
                self._provider_manager = ProviderManager(
                    fallback_chain=fallback_chain,
                    preferred_provider=self.preferred_provider,
                )
            except Exception as exc:
                logger.warning("ProviderManager init failed: %s", exc)
                self._provider_manager = None

        # Print welcome banner (no hard Ollama dependency)
        self.print_banner()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _safe_print(message: str) -> None:
        """Print safely across Windows console encodings."""
        try:
            print(message)
        except UnicodeEncodeError:
            fallback = message.encode("ascii", errors="replace").decode("ascii")
            print(fallback)
        except Exception:
            try:
                print(str(message))
            except Exception:
                pass

    def print_banner(self):
        """Print startup banner."""
        available = self._available_providers_summary()
        banner = (
            "\n"
            + "=" * 60
            + "\nARIA - Atlas Reasoning & Intelligence Assistant\n"
            + "v3.0 - Provider-Agnostic Edition\n"
            + f"Backends available: {available}\n"
            + f"Preferred: {self.preferred_provider or 'auto (first available)'}\n"
            + "Status: Ready\n"
            + "=" * 60
        )
        self._safe_print(banner)

    def _available_providers_summary(self) -> str:
        if not self._provider_manager:
            return "direct-ollama (legacy fallback)"
        try:
            providers = self._provider_manager.get_available_providers()
            return ", ".join(providers) if providers else "mock only"
        except Exception:
            return "unknown"

    # ----------------------------------------------------------- tool registry
    def register_tool(self, tool):
        """Register a tool for ARIA to use."""
        self.tools[tool.name] = tool
        tool_schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_parameters_schema()
            }
        }
        self.tool_schemas.append(tool_schema)
        self._safe_print(f"🔧 Registered tool: {tool.name}")

    # -------------------------------------------------------------- main loop
    def ask(self,
            user_message: str,
            max_iterations: int = 5) -> str:
        """Ask ARIA a question (supports multi-step tool calling)."""
        self.stats["total_queries"] += 1

        try:
            # Add user message to history
            self.history.append({"role": "user", "content": user_message})

            # Fast path: self-description commands
            triggers = ["who are you", "what are you", "describe yourself", "/intro", "/info"]
            if any(trigger in user_message.lower() for trigger in triggers):
                description = (
                    "🤖 **I am ARIA (Atlas Reasoning & Intelligence Assistant).**\n\n"
                    "I am Atlas's autonomous reasoning co-pilot. I route through whichever LLM "
                    "backend is available — local (Ollama), free cloud (Groq, OpenRouter, Cerebras), "
                    "or premium (OpenAI, Anthropic) — and fall back automatically if one goes down.\n\n"
                    "**My Key Capabilities:**\n"
                    "- 🧠 **Reasoning:** I use Llama 3, DeepSeek, Claude, or GPT depending on what's available.\n"
                    "- 🛠️ **Tools:** Files, web search, schedule (ClickUp/Notion), market data.\n"
                    "- 👁️ **Vision:** I can see and analyze images you share.\n"
                    "- 🗣️ **Voice:** I can speak and listen via my Voice Terminal.\n"
                    "- 🔌 **Integration:** WhatsApp, Discord, and your local apps.\n\n"
                    "I am built to be precise, helpful, and secure. How can I assist you today?"
                )
                self.history.append({"role": "assistant", "content": description})
                return description

            # Prepare messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.history
            ]

            # Multi-step reasoning with tools
            iterations = 0
            while iterations < max_iterations:
                iterations += 1

                # Route through provider manager (or direct ollama as legacy fallback)
                response, provider_used = self._call_backend(messages)

                # provider_used is a string. Response may be LLMResponse OR a raw dict
                # from legacy ollama (kept for backward compat).
                assistant_message = self._normalize_response(response)

                # Check if ARIA wants to call tools
                tool_calls = assistant_message.get("tool_calls") or []
                if tool_calls:
                    tool_results = self._execute_tools(tool_calls)
                    messages.append(assistant_message)
                    for tool_result in tool_results:
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result)
                        })
                    continue
                else:
                    final_response = assistant_message.get("content", "") or ""
                    self.history.append({"role": "assistant", "content": final_response})
                    self.stats["successful_queries"] += 1
                    return final_response

            return ("I apologize, but I'm having trouble completing this request. "
                    "Could you try rephrasing or breaking it into smaller questions?")

        except Exception as e:
            self.stats["failed_queries"] += 1
            return self._handle_error(e)

    # ------------------------------------------------------------- backends
    def _call_backend(self, messages: List[Dict[str, str]]):
        """
        Route the chat call through ProviderManager if available, otherwise
        fall back to direct Ollama (legacy path) for environments that still
        rely on it.

        Returns:
            (response_obj, provider_name)  — response may be LLMResponse OR raw dict.
        """
        # Preferred path: provider manager
        if self._provider_manager is not None:
            response, provider_name = self._provider_manager.chat_with_fallback(
                messages=messages,
                tools=self.tool_schemas if self.tool_schemas else None,
                max_retries=3,
            )
            return response, provider_name

        # Legacy fallback: direct Ollama (only if the package actually exists)
        try:
            import ollama  # lazy import
        except ImportError:
            raise RuntimeError(
                "No LLM backend available: ProviderManager failed to initialize and "
                "'ollama' package is not installed. Install one of: "
                "ollama / groq / openai / anthropic, or set an API key."
            )

        raw = ollama.chat(
            model=self.model,
            messages=messages,
            tools=self.tool_schemas if self.tool_schemas else None,
            options={"temperature": self.temperature},
        )
        return raw, "ollama-direct"

    @staticmethod
    def _normalize_response(response) -> Dict[str, Any]:
        """
        Normalize LLMResponse / raw-ollama-dict into a common shape:
            {"role": "assistant", "content": str, "tool_calls": list}
        """
        # LLMResponse case
        if LLMResponse is not None and isinstance(response, LLMResponse):
            tc = []
            for call in (response.tool_calls or []):
                tc.append({
                    "function": {
                        "name": call.get("name", ""),
                        "arguments": call.get("arguments", {}),
                    }
                })
            return {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": tc,
            }

        # Raw dict from ollama.chat()
        if isinstance(response, dict) and "message" in response:
            return response["message"]

        # Fallback: try best-effort attribute access
        return {
            "role": "assistant",
            "content": getattr(response, "content", str(response)),
            "tool_calls": getattr(response, "tool_calls", []) or [],
        }

    # ---------------------------------------------------------------- tools
    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls with validation."""
        results = []
        for tool_call in tool_calls:
            function = tool_call.get('function', {})
            tool_name = function.get('name')
            tool_params = function.get('arguments', {})

            if isinstance(tool_params, str):
                try:
                    tool_params = json.loads(tool_params)
                except json.JSONDecodeError:
                    tool_params = {}

            try:
                validated_params = validate_tool_params(tool_name, tool_params)
                tool = self.tools.get(tool_name)
                if not tool:
                    result = {"success": False, "error": f"Tool '{tool_name}' not found"}
                else:
                    self._safe_print(f"🔧 Executing: {tool_name}({validated_params})")
                    result = tool.execute(**validated_params)
                    self.stats["tools_called"] += 1
            except ValidationError as e:
                self.stats["validation_errors"] += 1
                result = {"success": False, "error": str(e), "error_type": "validation"}
            except Exception as e:
                result = {"success": False, "error": str(e), "error_type": "execution"}

            self._log_tool_event(
                tool_name=tool_name or "unknown",
                params=tool_params,
                result=result,
            )
            results.append({"tool": tool_name, "result": result})
        return results

    def _log_tool_event(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Append a structured JSONL record for each tool call."""
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "params": params,
            "result": result,
        }
        try:
            with self.tool_event_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to write tool event log: %s", exc)

    # ---------------------------------------------------------------- error
    def _handle_error(self, error: Exception) -> str:
        """Handle errors with user-friendly messages."""
        error_type = type(error).__name__
        error_msg = str(error)

        if isinstance(error, ConnectionError):
            return (
                "I'm having trouble connecting to my language model. "
                "All configured backends appear to be offline. "
                "Check your API keys (.env) or start Ollama if you use it locally."
            )
        elif isinstance(error, ValidationError):
            return f"I need some clarification: {error_msg}"
        elif "timeout" in error_msg.lower():
            return (
                "This request is taking longer than expected. Could you try:\n"
                "1. Simplifying the query\n"
                "2. Breaking it into smaller questions\n"
                "3. Trying again in a moment"
            )
        else:
            return (
                f"I encountered an unexpected issue: {error_msg}\n\n"
                "Could you try rephrasing your question or asking something else?"
            )

    # -------------------------------------------------------------- misc api
    def reset(self):
        """Reset conversation history."""
        self.history = []
        self._safe_print("🔄 Conversation history cleared")

    def get_stats(self) -> Dict:
        """Get usage statistics."""
        base = {
            **self.stats,
            "success_rate": (
                self.stats["successful_queries"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0 else 0
            )
        }
        if self._provider_manager is not None:
            try:
                base["provider_stats"] = self._provider_manager.get_stats()
            except Exception:
                pass
        return base

    def export_conversation(self, filepath: str):
        """Export conversation history to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "model": self.model,
                "backend": self.backend,
                "history": self.history,
                "stats": self.get_stats()
            }, f, indent=2)
        self._safe_print(f"💾 Conversation exported to {filepath}")


# Convenience function
def create_aria(model: Optional[str] = None,
                preferred_provider: Optional[str] = None) -> ARIA:
    """
    Create ARIA instance with default settings.

    Args:
        model: Optional model override.
        preferred_provider: e.g. "groq", "ollama", "openrouter". If None,
                            ARIA auto-selects the first available backend.

    Returns:
        ARIA instance
    """
    return ARIA(model=model, preferred_provider=preferred_provider)


if __name__ == "__main__":
    print("🧪 Testing ARIA v3.0 (Provider-Agnostic Edition)")
    print("=" * 60)
    try:
        aria = create_aria()
        print("\nTest 1: Simple question")
        print("-" * 60)
        response = aria.ask("Hello! Who are you?")
        print(f"ARIA: {response}\n")

        print("Test 2: Capabilities")
        print("-" * 60)
        response = aria.ask("What can you help me with?")
        print(f"ARIA: {response}\n")

        print("=" * 60)
        print("📊 Statistics:")
        stats = aria.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✅ ARIA v3.0 is working!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
