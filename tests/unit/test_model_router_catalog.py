from __future__ import annotations

from atlas.services.llm import ModelProviderInfo, ModelRoute, ModelRouter
from atlas.services.llm.providers.base import BaseLLMProvider, LLMResponse


class FakeProvider(BaseLLMProvider):
    provider_name = "fake"
    default_model = "fake-small"

    def __init__(self, available=True):
        self._available = available

    def generate(self, prompt, model=None, temperature=0.3, max_tokens=4096, **kwargs):
        return LLMResponse(text=prompt, model=model or self.default_model, provider=self.provider_name)

    def is_available(self):
        return self._available


def test_model_route_serializes():
    route = ModelRoute("fake", "fake-large")

    assert route.to_dict() == {"provider": "fake", "model": "fake-large"}


def test_provider_catalog_uses_local_routes_only():
    router = ModelRouter(routes={"planner_agent": {"low": ModelRoute("fake", "fake-large")}})
    router.add_provider("fake", FakeProvider(available=True))

    catalog = router.provider_catalog()
    fake = next(item for item in catalog if item.provider == "fake")

    assert isinstance(fake, ModelProviderInfo)
    assert fake.available is True
    assert fake.default_model == "fake-small"
    assert fake.configured_models == ["fake-large"]
    assert fake.routed_agents == ["planner_agent"]


def test_route_manifest_lists_agent_risk_rows():
    router = ModelRouter(
        routes={
            "planner_agent": {
                "low": ModelRoute("ollama", "qwen2.5"),
                "high": ModelRoute("openai", "gpt-4o-mini"),
            }
        }
    )

    rows = router.route_manifest()

    assert rows == [
        {
            "agent_name": "planner_agent",
            "risk_level": "high",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
        {
            "agent_name": "planner_agent",
            "risk_level": "low",
            "provider": "ollama",
            "model": "qwen2.5",
        },
    ]
