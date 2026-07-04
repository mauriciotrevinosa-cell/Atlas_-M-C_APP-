from __future__ import annotations

from atlas.assistants.aria.core.chat import ARIA
from atlas.assistants.aria.ai_layer.provider_manager import ProviderManager
from atlas.assistants.aria.ai_layer.providers.ollama_provider import OllamaProvider


def test_provider_manager_excludes_mock_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ARIA_ALLOW_MOCK", raising=False)
    monkeypatch.delenv("ATLAS_TEST_ALLOW_MOCK", raising=False)
    monkeypatch.delenv("ARIA_LLM_BACKEND", raising=False)

    manager = ProviderManager(fallback_chain=["mock"], preferred_provider=None)

    assert "mock" not in manager.fallback_chain
    assert "mock" not in manager.get_available_providers()


def test_provider_manager_allows_mock_only_when_explicit(monkeypatch) -> None:
    monkeypatch.setenv("ARIA_ALLOW_MOCK", "1")

    manager = ProviderManager(fallback_chain=["mock"], preferred_provider=None)

    assert manager.fallback_chain == ["mock"]
    assert manager.get_available_providers() == ["mock"]


def test_ollama_provider_detects_typed_sdk_model_list() -> None:
    class Model:
        model = "llama3.2:1b"

    class Response:
        models = [Model()]

    class Client:
        def list(self) -> Response:
            return Response()

    provider = OllamaProvider.__new__(OllamaProvider)
    provider._ollama = Client()
    provider.model = "llama3.2:1b"

    assert provider.is_available() is True


def test_ollama_provider_detects_legacy_dict_model_list() -> None:
    class Client:
        def list(self) -> dict:
            return {"models": [{"name": "llama3.1:8b"}]}

    provider = OllamaProvider.__new__(OllamaProvider)
    provider._ollama = Client()
    provider.model = "llama3.1"

    assert provider.is_available() is True


def test_aria_only_offers_tools_for_action_or_live_data_requests() -> None:
    aria = ARIA.__new__(ARIA)
    aria.tool_schemas = [{"type": "function"}]

    assert aria._should_offer_tools("Reply with exactly: ok") is False
    assert aria._should_offer_tools("Search the internet for current Polymarket news") is True
    assert aria._should_offer_tools("lee el roadmap y dime el estado de los agentes") is True
