from __future__ import annotations

from pathlib import Path

from apps.server import server
from atlas.assistants.aria.tools import web_search


def test_info_catalog_uses_live_api_and_agent_registry(monkeypatch) -> None:
    class FakeAgent:
        name = "planner_agent"
        version = "v1"

    class FakeRegistry:
        def list_agents(self):
            return ["planner_agent"]

        def get(self, name):
            assert name == "planner_agent"
            return FakeAgent()

    class FakeOrchestrator:
        registry = FakeRegistry()

    monkeypatch.setattr(server, "_get_agent_orchestrator", lambda: FakeOrchestrator())

    payload = server.info_catalog(query="planner", include_web=False, limit=20)

    assert payload["status"] == "ok"
    assert payload["source"] == "atlas_api"
    assert payload["include_web"] is False
    assert any(item["id"] == "agent:planner_agent" for item in payload["items"])


def test_info_catalog_can_filter_live_routes() -> None:
    payload = server.info_catalog(query="providers", include_web=False, limit=40)

    assert payload["count"] > 0
    assert any("/api/providers/health" == item.get("api") for item in payload["items"])


def test_web_info_returns_empty_state_when_search_has_no_results(monkeypatch) -> None:
    class EmptySearch:
        def execute(self, query: str, max_results: int = 5) -> dict:
            return {"success": True, "query": query, "results": [], "count": 0}

    monkeypatch.setattr(web_search, "WebSearchTool", EmptySearch)

    entries = server._build_web_info_entries("no hits", limit=5)

    assert entries[0]["name"] == "Internet Search Returned No Results"
    assert entries[0]["category"] == "data"


def test_desktop_info_panel_has_no_local_static_catalog() -> None:
    info_js = Path("apps/desktop/info.js").read_text(encoding="utf-8")

    assert "const ITEMS" not in info_js
    assert "Synthetic GBM Data" not in info_js
    assert "local fallback" not in info_js.lower()
