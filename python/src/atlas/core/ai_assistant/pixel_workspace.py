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
    running_tools = sum(len(item.get("active_tools", [])) for item in sessions)
    total_events = sum(int(item.get("event_count") or 0) for item in sessions)
    token_usage = _aggregate_token_usage(sessions)
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
            "running_tools": running_tools,
            "event_count": total_events,
            "token_usage": token_usage,
            "sessions_recent": sessions,
        },
        "pixel_agents_repo": pixel_repo,
        "links": {
            "agents": "/api/agents",
            "agent_status": "/api/agents/status",
            "agent_audit": "/api/agents/audit",
            "agent_stream": "/ws/agents/{session_id}",
            "pixel_stream": "/ws/pixel-agents/{session_id}",
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

    runtime = _parse_session_runtime(_read_tail_lines(path))
    activity = _session_activity(runtime, status)

    return {
        "agent_id": f"claude:{path.stem}",
        "session_id": path.stem,
        "provider": "claude",
        "project": label,
        "status": status,
        "activity": activity,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "age_seconds": age_seconds,
        "size_kb": round(stat.st_size / 1024, 1),
        "last_event": runtime["last_event"],
        "tools": runtime["tools"][:8],
        "active_tools": runtime["active_tools"],
        "token_usage": runtime["token_usage"],
        "waiting": runtime["waiting"],
        "permission_required": runtime["permission_required"],
        "event_count": runtime["event_count"],
        "recent_events": runtime["recent_events"],
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


def _parse_session_runtime(lines: Sequence[str]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    tools: list[str] = []
    active_tools: dict[str, dict[str, Any]] = {}
    token_usage = {"input_tokens": 0, "output_tokens": 0}
    waiting = False
    permission_required = False

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        record_events, token_delta = _normalize_transcript_record(record, line_no=line_no)
        token_usage["input_tokens"] += token_delta["input_tokens"]
        token_usage["output_tokens"] += token_delta["output_tokens"]

        for event in record_events:
            events.append(event)
            tool_name = event.get("tool_name")
            tool_id = str(event.get("tool_id") or "")
            if tool_name and tool_name not in tools:
                tools.append(str(tool_name))

            if event["type"] == "tool_started" and tool_id:
                active_tools[tool_id] = {
                    "tool_id": tool_id,
                    "tool_name": tool_name or "tool",
                    "label": event.get("label") or tool_name or "tool",
                }
            elif event["type"] == "tool_finished" and tool_id:
                active_tools.pop(tool_id, None)
            elif event["type"] == "agent_waiting":
                waiting = True
            elif event["type"] == "permission_required":
                permission_required = True

    last_event = events[-1]["label"] if events else "session file"
    return {
        "tools": tools,
        "active_tools": list(active_tools.values())[:8],
        "token_usage": token_usage,
        "waiting": waiting,
        "permission_required": permission_required,
        "event_count": len(events),
        "last_event": last_event,
        "recent_events": events[-12:],
    }


def _normalize_transcript_record(
    record: Mapping[str, Any],
    *,
    line_no: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    events: list[dict[str, Any]] = []
    token_delta = _extract_token_usage(record)
    record_type = str(record.get("type") or record.get("event") or "event")
    message = record.get("message")

    if isinstance(message, Mapping):
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, Mapping):
                    continue
                item_type = str(item.get("type") or "")
                name = item.get("name") or item.get("tool_name")
                tool_id = item.get("id") or item.get("tool_use_id") or item.get("tool_id")
                if name:
                    events.append(
                        {
                            "type": "tool_started",
                            "line": line_no,
                            "tool_id": str(tool_id or name),
                            "tool_name": str(name),
                            "label": f"{name} started",
                        }
                    )
                elif item_type == "tool_result" or item.get("tool_use_id"):
                    events.append(
                        {
                            "type": "tool_finished",
                            "line": line_no,
                            "tool_id": str(tool_id or "tool"),
                            "tool_name": None,
                            "label": "tool finished",
                            "is_error": bool(item.get("is_error")),
                        }
                    )
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    events.extend(_text_state_events(text, line_no=line_no))
            if role and not events:
                label = f"{role} {record_type}"
                events.append({"type": "message", "line": line_no, "label": label, "role": role})
        elif isinstance(content, str) and content.strip():
            label = f"{role or 'message'}: {_short_text(content)}"
            events.append({"type": "message", "line": line_no, "label": label, "role": role})
            events.extend(_text_state_events(content, line_no=line_no))

    name = record.get("tool_name") or record.get("name")
    if name:
        tool_id = record.get("tool_id") or record.get("id") or name
        event_type = "tool_finished" if str(record_type).endswith("End") else "tool_started"
        events.append(
            {
                "type": event_type,
                "line": line_no,
                "tool_id": str(tool_id),
                "tool_name": str(name),
                "label": f"{name} {'finished' if event_type == 'tool_finished' else 'started'}",
            }
        )

    if not events:
        events.append({"type": _generic_event_type(record_type), "line": line_no, "label": record_type})

    if token_delta["input_tokens"] or token_delta["output_tokens"]:
        events.append(
            {
                "type": "tokens_updated",
                "line": line_no,
                "label": "tokens updated",
                "input_tokens": token_delta["input_tokens"],
                "output_tokens": token_delta["output_tokens"],
            }
        )

    return events, token_delta


def _text_state_events(text: str, *, line_no: int) -> list[dict[str, Any]]:
    lower = text.lower()
    events: list[dict[str, Any]] = []
    if any(term in lower for term in ("permission", "approval", "allow this", "approve")):
        events.append(
            {
                "type": "permission_required",
                "line": line_no,
                "label": "permission required",
            }
        )
    if any(term in lower for term in ("waiting", "awaiting", "needs your input", "permission")):
        events.append(
            {
                "type": "agent_waiting",
                "line": line_no,
                "label": "agent waiting",
            }
        )
    return events


def _extract_token_usage(value: Any) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0}

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key in {"input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"}:
                    totals["input_tokens"] += _safe_int(child)
                elif key == "output_tokens":
                    totals["output_tokens"] += _safe_int(child)
                else:
                    walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return totals


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _generic_event_type(record_type: str) -> str:
    lowered = record_type.lower()
    if "session" in lowered and "start" in lowered:
        return "session_started"
    if "session" in lowered and "end" in lowered:
        return "session_finished"
    if "permission" in lowered:
        return "permission_required"
    return "event"


def _session_activity(runtime: Mapping[str, Any], status: str) -> str:
    if runtime.get("permission_required"):
        return "permission"
    if runtime.get("waiting"):
        return "waiting"
    if runtime.get("active_tools"):
        return "running"
    if status == "active":
        return "watching"
    return "idle"


def _aggregate_token_usage(sessions: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    input_tokens = 0
    output_tokens = 0
    for session in sessions:
        usage = session.get("token_usage") or {}
        if isinstance(usage, Mapping):
            input_tokens += _safe_int(usage.get("input_tokens"))
            output_tokens += _safe_int(usage.get("output_tokens"))
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


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
