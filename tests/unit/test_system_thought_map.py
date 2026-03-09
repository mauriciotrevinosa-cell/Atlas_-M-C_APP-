"""
System thought-map contract tests for Atlas server.
"""

from __future__ import annotations

from apps.server import server


def test_build_connectivity_checks_reports_required_wiring(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_collect_route_paths",
        lambda: {
            "/api/health",
            "/api/system/command_center",
            "/api/system/thought_map",
            "/api/aria/models",
            "/query",
            "/ws/{session_id}",
        },
    )
    monkeypatch.setattr(server, "_discover_desktop_views", lambda: ["dashboard", "thought"])
    monkeypatch.setattr(
        server,
        "_discover_desktop_js_modules",
        lambda: ["app.js", "thought_map.js"],
    )

    checks = server._build_connectivity_checks()

    assert checks["total"] >= 8
    assert checks["connected"] == checks["total"]
    assert checks["all_connected"] is True
    assert any(c["id"] == "api_thought_map" and c["connected"] for c in checks["checks"])
    assert any(c["id"] == "desktop_view_thought" and c["connected"] for c in checks["checks"])
    assert any(c["id"] == "desktop_module_thought" and c["connected"] for c in checks["checks"])


def test_build_thought_map_snapshot_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_build_command_center_snapshot",
        lambda: {
            "status": "nominal",
            "pulse_score": 87,
            "runtime": {"api_routes": 120, "modules_online": 8, "modules_total": 10},
            "project": {"desktop_views": 16, "desktop_js_modules": 21},
            "runs": {"latest_run_id": "run_abc", "latest_updated": "2026-03-07T20:00:00"},
            "aria": {"active_model": "llama3.1:8b", "installed_models": 3},
        },
    )
    monkeypatch.setattr(
        server,
        "_build_connectivity_checks",
        lambda: {"connected": 8, "total": 8, "all_connected": True, "checks": []},
    )
    monkeypatch.setattr(
        server,
        "_build_thinking_trace",
        lambda limit=16: [{"id": "audit-1", "label": "OK 120ms · llama3.1:8b", "success": True}],
    )
    monkeypatch.setattr(
        server,
        "_build_thought_graph",
        lambda command_center, connectivity: {"nodes": [{"id": "server"}], "edges": []},
    )
    monkeypatch.setattr(
        server,
        "_build_module_registry_snapshot",
        lambda: {"total": 21, "visualized": 15, "pending": 6, "entries": []},
    )

    payload = server._build_thought_map_snapshot()

    assert set(payload.keys()) == {
        "generated_at",
        "status",
        "pulse_score",
        "connectivity",
        "thinking_trace",
        "graph",
        "module_registry",
        "visibility",
        "command_center",
    }
    assert payload["status"] == "nominal"
    assert payload["pulse_score"] == 87
    assert payload["visibility"]["desktop_views"] == 16
    assert payload["visibility"]["desktop_js_modules"] == 21
    assert payload["visibility"]["latest_run_id"] == "run_abc"
    assert payload["visibility"]["module_registry_pending"] == 6
    assert payload["module_registry"]["visualized"] == 15
    assert payload["thinking_trace"][0]["success"] is True


def test_module_registry_marks_unwired_modules_as_pending(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_discover_desktop_js_modules",
        lambda: ["thought_map.js", "playroom.js", "app.js"],
    )
    monkeypatch.setattr(
        server,
        "_discover_desktop_views",
        lambda: ["dashboard", "thought"],
    )
    monkeypatch.setattr(
        server,
        "_discover_switch_targets",
        lambda: ["dashboard", "thought"],
    )

    registry = server._build_module_registry_snapshot()
    by_name = {entry["module"]: entry for entry in registry["entries"]}

    assert registry["total"] == 3
    assert by_name["thought_map.js"]["status"] == "visualized"
    assert by_name["playroom.js"]["status"] == "pending"
    assert by_name["app.js"]["status"] == "visualized"


def test_module_registry_maps_playroom_engines_to_playroom_view(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_discover_desktop_js_modules",
        lambda: ["playroom.js", "playroom_gitcity.js", "playroom_racing.js"],
    )
    monkeypatch.setattr(
        server,
        "_discover_desktop_views",
        lambda: ["dashboard", "playroom"],
    )
    monkeypatch.setattr(
        server,
        "_discover_switch_targets",
        lambda: ["dashboard", "playroom"],
    )

    registry = server._build_module_registry_snapshot()
    by_name = {entry["module"]: entry for entry in registry["entries"]}

    assert by_name["playroom.js"]["status"] == "visualized"
    assert by_name["playroom_gitcity.js"]["status"] == "visualized"
    assert by_name["playroom_racing.js"]["status"] == "visualized"
