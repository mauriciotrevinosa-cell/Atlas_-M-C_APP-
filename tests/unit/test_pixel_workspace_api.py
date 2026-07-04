from __future__ import annotations

from apps.server import server


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


def test_agents_pixel_workspace_endpoint_uses_existing_agent_registry(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "_ATLAS_ROOT", tmp_path)
    monkeypatch.setattr(server, "_get_agent_orchestrator", lambda: FakeOrchestrator())

    payload = server.agents_pixel_workspace()

    assert payload["status"] == "ready"
    assert payload["read_only"] is True
    assert payload["agents_total"] == 1
    assert payload["agents"][0]["name"] == "planner_agent"
    assert payload["links"]["agent_status"] == "/api/agents/status"
