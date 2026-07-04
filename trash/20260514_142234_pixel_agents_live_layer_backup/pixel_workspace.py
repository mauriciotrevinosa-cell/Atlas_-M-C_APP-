"""Atlas-native Pixel Operations workspace.

This module recreates the useful operating ideas from pixel-agents as Atlas
data: desks, teams, agent roster, and read-only Claude transcript visibility.
It does not import or execute the VS Code extension code.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DESK_DEFINITIONS = [
    {
        "id": "atlas-os",
        "label": "Atlas OS",
        "role": "runtime",
        "paths": ["apps/server", "ui_web"],
    },
    {
        "id": "agent-gateway",
        "label": "Agent Gateway",
        "role": "agents",
        "paths": ["python/src/atlas/core/ai_assistant"],
    },
    {
        "id": "market-intel",
        "label": "Market Intel",
        "role": "signals",
        "paths": ["python/src/atlas/signal_terminal", "python/src/atlas/data_layer"],
    },
    {
        "id": "mmo-lab",
        "label": "MMO Lab",
        "role": "ontology",
        "paths": ["python/src/atlas/lab/quantum", "python/src/atlas/market_state"],
    },
    {
        "id": "info-intake",
        "label": "Info Intake",
        "role": "research",
        "paths": ["info_instructions", "docs"],
    },
    {
        "id": "pixel-agents",
        "label": "Pixel Agents",
        "role": "visual-ops",
        "paths": ["pixel-agents"],
    },
]


TEAM_DEFINITIONS = [
    {
        "id": "planning",
        "label": "Planning Desk",
        "mission": "Goal breakdown, context, and route selection.",
        "agents": ["planner_agent", "context_curator_agent"],
    },
    {
        "id": "build",
        "label": "Build Desk",
        "mission": "Code proposals, repo scouting, ingestion, and docs.",
        "agents": ["code_builder_agent", "repo_scout_agent", "ingestion_agent", "docs_agent"],
    },
    {
        "id": "quality",
        "label": "Quality Desk",
        "mission": "Review, tests, and merge readiness.",
        "agents": ["reviewer_agent", "test_agent"],
    },
    {
        "id": "market",
        "label": "Market Desk",
        "mission": "Signals, providers, and finance context.",
        "agents": ["market_intel_agent"],
    },
]


def build_pixel_workspace(
    root: str | Path,
    *,
    agents: Sequence[Mapping[str, Any]] | None = None,
    home: str | Path | None = None,
    max_sessions: int = 8,
) -> dict[str, Any]:
    """Build a read-only Pixel Operations snapshot for Atlas."""
    root_path = Path(root).resolve()
    home_path = Path(home).expanduser().resolve() if home else Path.home()
    agent_items = _normalize_agents(agents or [])
    tracked_roots = _tracked_roots(root_path)
    sessions = _recent_claude_sessions(tracked_roots, home_path, max_sessions=max_sessions)
    desks = _build_desks(root_path, agent_items)
    teams = _build_teams(agent_items)
    pixel_repo = _pixel_repo_snapshot(root_path / "pixel-agents")

    active_sessions = sum(1 for item in sessions if item["status"] == "active")
    status = "ready" if agent_items or sessions else "standby"

    return {
        "status": status,
        "read_only": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "integration_mode": "atlas_native_rebuild",
        "source_repo": "pixel-agents-atlas",
        "office": {
            "root": str(root_path),
            "desks_total": len(desks),
            "desks_ready": sum(1 for desk in desks if desk["status"] == "ready"),
            "desks": desks,
        },
        "agents_total": len(agent_items),
        "agents": agent_items,
        "teams_total": len(teams),
        "teams": teams,
        "claude": {
            "projects_root": str(home_path / ".claude" / "projects"),
            "tracked_projects": [
                {"label": label, "path": str(path), "slug": _claude_project_slug(path)}
                for label, path in tracked_roots
            ],
            "sessions_total": len(sessions),
            "active_sessions": active_sessions,
            "sessions_recent": sessions,
        },
        "pixel_agents_repo": pixel_repo,
        "links": {
            "agents": "/api/agents",
            "agent_status": "/api/agents/status",
            "agent_audit": "/api/agents/audit",
            "agent_stream": "/ws/agents/{session_id}",
        },
    }


def _normalize_agents(agents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in agents:
        name = str(raw.get("name") or raw.get("agent") or "").strip()
        if not name:
            continue
        role = _agent_role(name)
        normalized.append(
            {
                "name": name,
                "class": raw.get("class") or raw.get("type") or "AtlasAgent",
                "version": raw.get("version") or "v1",
                "role": role,
                "desk": _desk_for_role(role),
                "status": "ready",
            }
        )
    return sorted(normalized, key=lambda item: item["name"])


def _agent_role(name: str) -> str:
    lower = name.lower()
    if "planner" in lower or "curator" in lower:
        return "planning"
    if "review" in lower or "test" in lower:
        return "quality"
    if "market" in lower or "intel" in lower:
        return "market"
    if "repo" in lower or "code" in lower or "ingestion" in lower or "docs" in lower:
        return "build"
    return "general"


def _desk_for_role(role: str) -> str:
    return {
        "planning": "agent-gateway",
        "quality": "agent-gateway",
        "build": "pixel-agents",
        "market": "market-intel",
        "general": "atlas-os",
    }.get(role, "atlas-os")


def _build_teams(agents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    available = {str(item.get("name")) for item in agents}
    teams: list[dict[str, Any]] = []
    for team in TEAM_DEFINITIONS:
        members = [name for name in team["agents"] if name in available]
        teams.append(
            {
                "id": team["id"],
                "label": team["label"],
                "mission": team["mission"],
                "members": members,
                "members_total": len(members),
                "expected_total": len(team["agents"]),
                "status": "ready" if members else "waiting",
            }
        )
    return teams


def _build_desks(root: Path, agents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    agents_by_desk: dict[str, list[str]] = {}
    for agent in agents:
        agents_by_desk.setdefault(str(agent.get("desk") or "atlas-os"), []).append(str(agent["name"]))

    desks: list[dict[str, Any]] = []
    for desk in DESK_DEFINITIONS:
        path_rows = []
        ready_paths = 0
        file_count = 0
        for rel in desk["paths"]:
            path = root / rel
            exists = path.exists()
            ready_paths += 1 if exists else 0
            count = _count_direct_files(path)
            file_count += count
            path_rows.append(
                {
                    "path": rel,
                    "exists": exists,
                    "direct_files": count,
                }
            )
        desks.append(
            {
                "id": desk["id"],
                "label": desk["label"],
                "role": desk["role"],
                "status": "ready" if ready_paths else "missing",
                "paths_ready": ready_paths,
                "paths_total": len(desk["paths"]),
                "direct_files": file_count,
                "agents": sorted(agents_by_desk.get(desk["id"], [])),
                "paths": path_rows,
            }
        )
    return desks


def _count_direct_files(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(1 for item in path.iterdir() if item.is_file())
    except OSError:
        return 0


def _tracked_roots(root: Path) -> list[tuple[str, Path]]:
    rows = [
        ("Atlas", root),
        ("Atlas UI", root / "ui_web"),
        ("Agent Gateway", root / "python" / "src" / "atlas" / "core" / "ai_assistant"),
        ("Pixel Agents", root / "pixel-agents"),
        ("Info Instructions", root / "info_instructions"),
    ]
    return [(label, path.resolve()) for label, path in rows if path.exists()]


def _recent_claude_sessions(
    tracked_roots: Iterable[tuple[str, Path]],
    home: Path,
    *,
    max_sessions: int,
) -> list[dict[str, Any]]:
    projects_root = home / ".claude" / "projects"
    sessions: list[dict[str, Any]] = []
    if not projects_root.is_dir():
        return sessions

    for label, project_path in tracked_roots:
        project_dir = _resolve_claude_project_dir(projects_root, _claude_project_slug(project_path))
        if not project_dir.is_dir():
            continue
        try:
            files = sorted(project_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
        except OSError:
            continue
        for file_path in files[:max_sessions]:
            snapshot = _session_snapshot(file_path, label)
            if snapshot:
                sessions.append(snapshot)

    sessions.sort(key=lambda item: item["updated_at"], reverse=True)
    return sessions[:max_sessions]


def _session_snapshot(path: Path, label: str) -> dict[str, Any] | None:
    try:
        stat = path.stat()
    except OSError:
        return None

    now = datetime.now().timestamp()
    age_seconds = max(0, int(now - stat.st_mtime))
    if age_seconds < 10 * 60:
        status = "active"
    elif age_seconds < 24 * 60 * 60:
        status = "recent"
    else:
        status = "archived"

    lines = _read_tail_lines(path)
    last_event = "session file"
    tools: list[str] = []
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        summary, names = _summarize_record(record)
        if summary and last_event == "session file":
            last_event = summary
        for name in names:
            if name not in tools:
                tools.append(name)
        if last_event != "session file" and tools:
            break

    return {
        "session_id": path.stem,
        "project": label,
        "status": status,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "age_seconds": age_seconds,
        "size_kb": round(stat.st_size / 1024, 1),
        "last_event": last_event,
        "tools": tools[:6],
    }


def _read_tail_lines(path: Path, max_bytes: int = 65536) -> list[str]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()
            data = handle.read()
    except OSError:
        return []
    return data.decode("utf-8", errors="replace").splitlines()


def _summarize_record(record: Mapping[str, Any]) -> tuple[str, list[str]]:
    tools: list[str] = []
    record_type = str(record.get("type") or record.get("event") or "event")
    message = record.get("message")
    if isinstance(message, Mapping):
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, Mapping):
                    continue
                name = item.get("name") or item.get("tool_name")
                if name:
                    tools.append(str(name))
            if role:
                return f"{role} {record_type}", tools
        elif isinstance(content, str) and content.strip():
            return f"{role or 'message'}: {_short_text(content)}", tools
    name = record.get("tool_name") or record.get("name")
    if name:
        tools.append(str(name))
    return record_type, tools


def _short_text(text: str, limit: int = 90) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 3]}..."


def _claude_project_slug(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "-", str(path))


def _resolve_claude_project_dir(projects_root: Path, slug: str) -> Path:
    exact = projects_root / slug
    if exact.exists():
        return exact
    try:
        lower_slug = slug.lower()
        for candidate in projects_root.iterdir():
            if candidate.name.lower() == lower_slug:
                return candidate
    except OSError:
        pass
    return exact


def _pixel_repo_snapshot(repo: Path) -> dict[str, Any]:
    if not repo.exists():
        return {
            "present": False,
            "path": str(repo),
            "status": "missing",
        }

    return {
        "present": True,
        "path": str(repo),
        "status": "ready",
        "branch": _git_value(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git_value(repo, "rev-parse", "--short", "HEAD"),
        "remote": _git_remote(repo),
        "license": "MIT" if (repo / "LICENSE").exists() else "unknown",
    }


def _git_remote(repo: Path) -> str | None:
    return (
        _git_value(repo, "config", "--get", "remote.atlas.url")
        or _git_value(repo, "config", "--get", "remote.origin.url")
    )


def _git_value(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value or None
