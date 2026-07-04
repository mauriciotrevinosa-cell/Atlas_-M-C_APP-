from __future__ import annotations

from pathlib import Path

from atlas.core.ai_assistant.pixel_workspace import (
    _claude_project_slug,
    _parse_session_runtime,
    build_pixel_workspace,
)


def test_pixel_workspace_maps_atlas_desks_and_agent_teams(tmp_path: Path) -> None:
    root = tmp_path / "Atlas"
    (root / "apps" / "server").mkdir(parents=True)
    (root / "ui_web").mkdir()
    (root / "python" / "src" / "atlas" / "core" / "ai_assistant").mkdir(parents=True)
    (root / "python" / "src" / "atlas" / "signal_terminal").mkdir(parents=True)
    (root / "python" / "src" / "atlas" / "data_layer").mkdir(parents=True)
    (root / "info_instructions").mkdir()
    (root / "docs").mkdir()
    (root / "pixel-agents").mkdir()
    (root / "pixel-agents" / "LICENSE").write_text("MIT\n", encoding="utf-8")

    payload = build_pixel_workspace(
        root,
        agents=[
            {"name": "planner_agent", "version": "v1", "class": "PlannerAgent"},
            {"name": "repo_scout_agent", "version": "v1", "class": "RepoScoutAgent"},
        ],
        home=tmp_path / "home",
    )

    assert payload["status"] == "ready"
    assert payload["read_only"] is True
    assert payload["agents_total"] == 2
    assert payload["office"]["desks_ready"] >= 4
    assert any(desk["id"] == "pixel-agents" for desk in payload["office"]["desks"])
    assert any(team["id"] == "planning" and team["members_total"] == 1 for team in payload["teams"])
    assert payload["pixel_agents_repo"]["present"] is True
    assert payload["pixel_agents_repo"]["license"] == "MIT"


def test_pixel_workspace_reads_recent_claude_sessions(tmp_path: Path) -> None:
    root = tmp_path / "Atlas"
    root.mkdir()
    home = tmp_path / "home"
    project_dir = home / ".claude" / "projects" / _claude_project_slug(root.resolve())
    project_dir.mkdir(parents=True)
    (project_dir / "session-1.jsonl").write_text(
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Read"}]}}\n',
        encoding="utf-8",
    )

    payload = build_pixel_workspace(root, home=home)
    sessions = payload["claude"]["sessions_recent"]

    assert payload["claude"]["sessions_total"] == 1
    assert sessions[0]["session_id"] == "session-1"
    assert sessions[0]["project"] == "Atlas"
    assert sessions[0]["tools"] == ["Read"]
    assert sessions[0]["event_count"] >= 1
    assert sessions[0]["activity"] == "running"
    assert sessions[0]["active_tools"][0]["tool_name"] == "Read"


def test_pixel_workspace_normalizes_tools_tokens_and_waiting_state() -> None:
    runtime = _parse_session_runtime(
        [
            (
                '{"type":"assistant","message":{"role":"assistant",'
                '"content":[{"type":"tool_use","id":"tool-1","name":"Read"}],'
                '"usage":{"input_tokens":10,"output_tokens":2}}}'
            ),
            (
                '{"type":"user","message":{"role":"user",'
                '"content":[{"type":"tool_result","tool_use_id":"tool-1","content":"done"}]}}'
            ),
            (
                '{"type":"assistant","message":{"role":"assistant",'
                '"content":"Waiting for permission approval.",'
                '"usage":{"input_tokens":3,"output_tokens":4}}}'
            ),
        ]
    )

    assert runtime["tools"] == ["Read"]
    assert runtime["active_tools"] == []
    assert runtime["token_usage"] == {"input_tokens": 13, "output_tokens": 6}
    assert runtime["waiting"] is True
    assert runtime["permission_required"] is True
    assert any(event["type"] == "tool_started" for event in runtime["recent_events"])
    assert any(event["type"] == "tool_finished" for event in runtime["recent_events"])
