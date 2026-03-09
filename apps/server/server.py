"""
ARIA Multi-Device Server

FastAPI server para acceder ARIA desde mÃºltiples dispositivos
Sincroniza conversaciones entre PCs, mÃ³viles, etc.

Features:
- REST API para ARIA
- WebSocket para real-time
- Sync entre dispositivos
- Session management
- Authentication (bÃ¡sico)
"""

from fastapi import FastAPI, WebSocket, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import asyncio
import os
import re
import time
import math
import logging
from datetime import datetime
from pathlib import Path
import sqlite3
from threading import Lock

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False


# In-memory TTL cache for high-traffic API endpoints
# Prevents repeated yfinance calls for the same ticker within a short window.
_API_CACHE: Dict[str, tuple] = {}


def _cache_get(key: str) -> Any:
    """Return cached value or None if missing / expired."""
    entry = _API_CACHE.get(key)
    if not entry:
        return None
    data, expires_at = entry
    if time.time() > expires_at:
        _API_CACHE.pop(key, None)
        return None
    return data


def _cache_set(key: str, data: Any, ttl: int = 300) -> None:
    """Store value with TTL (seconds). Auto-evicts expired entries when > 400."""
    _API_CACHE[key] = (data, time.time() + ttl)
    if len(_API_CACHE) > 400:
        now = time.time()
        stale = [k for k, (_, e) in list(_API_CACHE.items()) if now > e]
        for k in stale:
            _API_CACHE.pop(k, None)


def _json_safe(value: Any) -> Any:
    """Recursively replace NaN/Inf floats to keep API responses JSON-compliant."""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


# ==================== MODELS ====================

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class QueryRequest(BaseModel):
    message: str
    device_id: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    provider: Optional[str] = None
    latency_ms: Optional[int] = None


class PortfolioRiskRequest(BaseModel):
    tickers: List[str]
    weights: Optional[Dict[str, float]] = None
    period: str = "1y"
    return_method: str = "log"
    confidence: float = 0.95
    risk_free_rate: float = 0.04
    horizon_days: int = 1
    run_stress: bool = True


class PortfolioMonteCarloRequest(BaseModel):
    tickers: List[str]
    weights: Optional[Dict[str, float]] = None
    period: str = "1y"
    return_method: str = "log"
    n_paths: int = 1200
    horizon_days: int = 252
    seed: Optional[int] = None


# ==================== DATABASE ====================

class ConversationDB:
    """SQLite database for conversation sync"""
    
    def __init__(self, db_path: str = "data/aria_multi_device.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                device_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT,
                last_seen TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def add_message(self, session_id: str, device_id: str, role: str, content: str):
        """Add message to conversation"""
        conn = sqlite3.connect(self.db_path)
        timestamp = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO conversations (session_id, device_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (session_id, device_id, role, content, timestamp)
        )
        conn.commit()
        conn.close()
    
    def get_conversation(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        )
        messages = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
        conn.close()
        return list(reversed(messages))
    
    def register_device(self, device_id: str, device_name: str):
        """Register new device"""
        conn = sqlite3.connect(self.db_path)
        timestamp = datetime.now().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO devices (device_id, device_name, last_seen) VALUES (?, ?, ?)",
            (device_id, device_name, timestamp)
        )
        conn.commit()
        conn.close()


# ==================== SERVER ====================

app = FastAPI(title="ARIA Multi-Device Server", version="1.0")

# CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
db = ConversationDB()

# ARIA instance (initialize in main)
aria_instance = None

# WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}
QUERY_TIMEOUT_SECONDS = int(os.getenv("ATLAS_QUERY_TIMEOUT_SECONDS", "45"))

# ARIA instance (initialize in main)
aria_instance = None

# WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}
logger = logging.getLogger(__name__)

# ── ARIA Local Model State ────────────────────────────────────────────────────
# 100% local — runs entirely on Ollama. No external API calls, no API keys.
# Future-proof: models are discovered at runtime from what's pulled locally.

_aria_active_model: str = os.getenv("ARIA_MODEL", "llama3.2:1b")
_aria_audit_log:    List[Dict] = []   # append-only session audit (max 500)

# Well-known Ollama model display names (label for UI)
_KNOWN_MODELS: Dict[str, str] = {
    "llama3.2:1b":          "Llama 3.2 · 1B  ⚡ Fast",
    "llama3.2:3b":          "Llama 3.2 · 3B",
    "llama3.1:8b":          "Llama 3.1 · 8B  🧠 Smart",
    "llama3.1:70b":         "Llama 3.1 · 70B 💪 Power",
    "mistral:7b":           "Mistral · 7B",
    "mistral:latest":       "Mistral · Latest",
    "deepseek-r1:7b":       "DeepSeek-R1 · 7B 🔍 Reason",
    "deepseek-r1:14b":      "DeepSeek-R1 · 14B",
    "qwen2.5:7b":           "Qwen 2.5 · 7B",
    "qwen2.5:14b":          "Qwen 2.5 · 14B",
    "phi3:mini":            "Phi-3 Mini · Fast",
    "gemma2:9b":            "Gemma 2 · 9B",
    "codellama:7b":         "Code Llama · 7B 💻",
}

_ATLAS_ROOT = Path(__file__).resolve().parents[2]
_SYSTEM_MODULE_FLAGS: Dict[str, bool] = {
    "aria": True,
    "data_layer": True,
    "analytics": True,
    "indicators": True,
    "signal_engine": True,
    "risk_engine": True,
    "portfolio_risk": True,
    "monte_carlo": True,
    "backtest": True,
    "education_kb": True,
    "ml_engine": False,   # Not trained yet
    "rl_agent": False,    # Not trained yet
    "execution": True,
    "cpp_core": False,    # Build pending
}


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _safe_iterdir(path: Path) -> List[Path]:
    if not path.is_dir():
        return []
    try:
        return list(path.iterdir())
    except Exception:
        return []


def _count_markdown(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(1 for _ in path.glob("*.md"))
    except Exception:
        return 0


def _discover_desktop_views() -> List[str]:
    index_path = _ATLAS_ROOT / "apps" / "desktop" / "index.html"
    content = _safe_read_text(index_path)
    if not content:
        return []
    matches = re.findall(r'id="view-([a-zA-Z0-9_-]+)"', content)
    return sorted(set(matches), key=str.lower)


def _discover_desktop_js_modules() -> List[str]:
    desktop_dir = _ATLAS_ROOT / "apps" / "desktop"
    if not desktop_dir.is_dir():
        return []
    modules = [
        p.name
        for p in desktop_dir.glob("*.js")
        if p.name.lower() not in {"preload.js"}
    ]
    return sorted(modules, key=str.lower)


def _latest_run_snapshot() -> Dict[str, Any]:
    runs_root = _ATLAS_ROOT / "outputs" / "runs"
    run_dirs = [d for d in _safe_iterdir(runs_root) if d.is_dir()]
    if not run_dirs:
        return {"count": 0, "latest_run_id": None, "latest_updated": None}

    latest = max(run_dirs, key=lambda d: d.stat().st_mtime)
    latest_updated = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
    return {
        "count": len(run_dirs),
        "latest_run_id": latest.name,
        "latest_updated": latest_updated,
    }


def _route_counts() -> Dict[str, int]:
    api_paths = set()
    websocket_paths = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path:
            continue
        if path.startswith("/api/"):
            api_paths.add(path)
        if path.startswith("/ws/"):
            websocket_paths += 1
    return {"api_routes": len(api_paths), "websocket_routes": websocket_paths}


def _build_command_center_snapshot() -> Dict[str, Any]:
    models = _get_local_models()
    modules = dict(_SYSTEM_MODULE_FLAGS)
    modules_online = sum(1 for is_ok in modules.values() if is_ok)
    modules_total = len(modules)
    routes = _route_counts()
    desktop_views = _discover_desktop_views()
    desktop_js = _discover_desktop_js_modules()
    run_info = _latest_run_snapshot()

    docs_md = _count_markdown(_ATLAS_ROOT / "docs")
    gov_md = _count_markdown(_ATLAS_ROOT / "project_governance")
    root_files = len([p for p in _safe_iterdir(_ATLAS_ROOT) if p.is_file()])
    core_folders = [
        "apps",
        "python",
        "tests",
        "configs",
        "docs",
        "data",
        "outputs",
        "services",
        "cpp",
        "ui_web",
        "scripts",
    ]
    core_present = sum(1 for name in core_folders if (_ATLAS_ROOT / name).exists())

    module_ratio = modules_online / modules_total if modules_total else 0.0
    model_ratio = min(len(models), 5) / 5.0
    route_ratio = min(routes["api_routes"], 80) / 80.0
    pulse_score = int((module_ratio * 0.60 + model_ratio * 0.20 + route_ratio * 0.20) * 100)

    if pulse_score >= 75:
        status = "nominal"
    elif pulse_score >= 45:
        status = "degraded"
    else:
        status = "critical"

    return {
        "status": status,
        "pulse_score": pulse_score,
        "generated_at": datetime.now().isoformat(),
        "aria": {
            "active_model": _aria_active_model,
            "installed_models": len(models),
            "audit_entries": len(_aria_audit_log),
        },
        "runtime": {
            "modules_online": modules_online,
            "modules_total": modules_total,
            "api_routes": routes["api_routes"],
            "websocket_routes": routes["websocket_routes"],
        },
        "project": {
            "core_folders_present": core_present,
            "core_folders_total": len(core_folders),
            "root_files": root_files,
            "desktop_views": len(desktop_views),
            "desktop_js_modules": len(desktop_js),
            "docs_markdown": docs_md,
            "governance_markdown": gov_md,
        },
        "runs": run_info,
        "highlights": {
            "desktop_views_sample": desktop_views[:8],
            "desktop_js_sample": desktop_js[:8],
        },
    }


def _collect_route_paths() -> set:
    return {
        path
        for route in app.routes
        for path in [getattr(route, "path", "")]
        if path
    }


def _build_connectivity_checks() -> Dict[str, Any]:
    route_paths = _collect_route_paths()
    desktop_views = set(_discover_desktop_views())
    desktop_js_modules = set(_discover_desktop_js_modules())

    checks = [
        {
            "id": "api_health",
            "label": "API health endpoint",
            "kind": "route",
            "target": "/api/health",
            "connected": "/api/health" in route_paths,
            "required": True,
        },
        {
            "id": "api_command_center",
            "label": "Command center endpoint",
            "kind": "route",
            "target": "/api/system/command_center",
            "connected": "/api/system/command_center" in route_paths,
            "required": True,
        },
        {
            "id": "api_thought_map",
            "label": "Thought map endpoint",
            "kind": "route",
            "target": "/api/system/thought_map",
            "connected": "/api/system/thought_map" in route_paths,
            "required": True,
        },
        {
            "id": "api_models",
            "label": "ARIA model inventory",
            "kind": "route",
            "target": "/api/aria/models",
            "connected": "/api/aria/models" in route_paths,
            "required": True,
        },
        {
            "id": "api_query",
            "label": "ARIA query bridge",
            "kind": "route",
            "target": "/query",
            "connected": "/query" in route_paths,
            "required": True,
        },
        {
            "id": "api_analytics_summary",
            "label": "Analytics summary endpoint",
            "kind": "route",
            "target": "/api/analytics/summary/{ticker}",
            "connected": "/api/analytics/summary/{ticker}" in route_paths,
            "required": False,
        },
        {
            "id": "api_portfolio_risk",
            "label": "Portfolio risk endpoint",
            "kind": "route",
            "target": "/api/risk/portfolio/assess",
            "connected": "/api/risk/portfolio/assess" in route_paths,
            "required": False,
        },
        {
            "id": "api_portfolio_montecarlo",
            "label": "Portfolio Monte Carlo endpoint",
            "kind": "route",
            "target": "/api/montecarlo/portfolio/simulate",
            "connected": "/api/montecarlo/portfolio/simulate" in route_paths,
            "required": False,
        },
        {
            "id": "ws_bridge",
            "label": "WebSocket bridge",
            "kind": "route",
            "target": "/ws/{session_id}",
            "connected": "/ws/{session_id}" in route_paths,
            "required": True,
        },
        {
            "id": "desktop_view_thought",
            "label": "Desktop thought-map view",
            "kind": "desktop",
            "target": "view-thought",
            "connected": "thought" in desktop_views,
            "required": True,
        },
        {
            "id": "desktop_module_thought",
            "label": "Desktop thought-map module",
            "kind": "desktop",
            "target": "thought_map.js",
            "connected": "thought_map.js" in desktop_js_modules,
            "required": True,
        },
    ]

    required_checks = [check for check in checks if check.get("required", True)]
    optional_checks = [check for check in checks if not check.get("required", True)]
    connected = sum(1 for check in required_checks if check["connected"])
    total = len(required_checks)
    optional_connected = sum(1 for check in optional_checks if check["connected"])
    optional_total = len(optional_checks)
    return {
        "connected": connected,
        "total": total,
        "all_connected": connected == total,
        "connected_total": connected + optional_connected,
        "total_checks": total + optional_total,
        "optional_connected": optional_connected,
        "optional_total": optional_total,
        "checks": checks,
    }


def _build_thinking_trace(limit: int = 14) -> List[Dict[str, Any]]:
    if not _aria_audit_log:
        return []

    rows: List[Dict[str, Any]] = []
    for idx, entry in enumerate(reversed(_aria_audit_log[-limit:]), start=1):
        success = bool(entry.get("success"))
        latency_ms = int(entry.get("latency_ms") or 0)
        model = entry.get("model") or _aria_active_model
        stage = "response_ok" if success else "response_failed"
        rows.append(
            {
                "id": f"audit-{idx}",
                "ts": entry.get("ts"),
                "model": model,
                "success": success,
                "latency_ms": latency_ms,
                "message_len": int(entry.get("message_len") or 0),
                "stage": stage,
                "label": f"{'OK' if success else 'ERR'} {latency_ms}ms · {model}",
            }
        )
    return rows


def _severity_from_ratio(ratio: float) -> str:
    if ratio >= 0.8:
        return "online"
    if ratio >= 0.45:
        return "degraded"
    return "critical"


def _build_thought_graph(
    command_center: Dict[str, Any],
    connectivity: Dict[str, Any],
) -> Dict[str, Any]:
    runtime = command_center.get("runtime", {})
    project = command_center.get("project", {})
    runs = command_center.get("runs", {})
    aria = command_center.get("aria", {})

    modules_online = int(runtime.get("modules_online") or 0)
    modules_total = int(runtime.get("modules_total") or 0)
    module_ratio = modules_online / modules_total if modules_total else 0.0
    modules_state = _severity_from_ratio(module_ratio)

    models_installed = int(aria.get("installed_models") or 0)
    aria_state = "online" if models_installed > 0 else "degraded"

    runs_count = int(runs.get("count") or 0)
    runs_state = "online" if runs_count > 0 else "degraded"

    docs_total = int(project.get("docs_markdown") or 0) + int(project.get("governance_markdown") or 0)
    docs_state = "online" if docs_total > 0 else "critical"

    bridge_state = "online" if connectivity.get("all_connected") else "degraded"
    route_count = int(runtime.get("api_routes") or 0)
    api_state = "online" if route_count >= 1 else "critical"

    nodes = [
        {
            "id": "desktop",
            "label": "Desktop UI",
            "status": "online",
            "x": 8,
            "y": 50,
            "meta": f"{project.get('desktop_views', 0)} views",
        },
        {
            "id": "server",
            "label": "FastAPI Core",
            "status": api_state,
            "x": 30,
            "y": 50,
            "meta": f"{route_count} API routes",
        },
        {
            "id": "aria",
            "label": "ARIA Runtime",
            "status": aria_state,
            "x": 52,
            "y": 28,
            "meta": str(aria.get("active_model") or "unknown"),
        },
        {
            "id": "engines",
            "label": "Atlas Engines",
            "status": modules_state,
            "x": 52,
            "y": 72,
            "meta": f"{modules_online}/{modules_total} online",
        },
        {
            "id": "governance",
            "label": "Governance",
            "status": docs_state,
            "x": 74,
            "y": 28,
            "meta": f"{docs_total} docs",
        },
        {
            "id": "artifacts",
            "label": "Run Artifacts",
            "status": runs_state,
            "x": 74,
            "y": 72,
            "meta": str(runs.get("latest_run_id") or "none"),
        },
        {
            "id": "bridge",
            "label": "System Bridge",
            "status": bridge_state,
            "x": 74,
            "y": 50,
            "meta": f"{connectivity.get('connected', 0)}/{connectivity.get('total', 0)} links",
        },
    ]

    edges = [
        {"source": "desktop", "target": "server", "status": "online", "label": "UI REST"},
        {"source": "server", "target": "aria", "status": aria_state, "label": "inference"},
        {"source": "server", "target": "engines", "status": modules_state, "label": "module calls"},
        {"source": "server", "target": "governance", "status": docs_state, "label": "docs context"},
        {"source": "server", "target": "artifacts", "status": runs_state, "label": "run outputs"},
        {"source": "server", "target": "bridge", "status": bridge_state, "label": "wiring"},
        {"source": "bridge", "target": "aria", "status": bridge_state, "label": "prompt path"},
    ]

    return {"nodes": nodes, "edges": edges}


def _discover_switch_targets() -> List[str]:
    index_path = _ATLAS_ROOT / "apps" / "desktop" / "index.html"
    content = _safe_read_text(index_path)
    if not content:
        return []
    matches = re.findall(r"switchView\('([a-zA-Z0-9_-]+)'\)", content)
    return sorted(set(matches), key=str.lower)


def _build_module_registry_snapshot() -> Dict[str, Any]:
    modules = _discover_desktop_js_modules()
    views = _discover_desktop_views()
    view_set = set(views)
    switch_targets = set(_discover_switch_targets())

    view_hints = {
        "analysis": "analysis",
        "app": "dashboard",
        "aria_core": "chat",
        "decision": "decision",
        "derivatives": "derivatives",
        "finance": "finance",
        "indicator_terminal": "indicators",
        "info": "info",
        "main": "dashboard",
        "mmo": "mmo",
        "paper_trading": "paper",
        "playroom": "playroom",
        "playroom_gitcity": "playroom",
        "playroom_racing": "playroom",
        "real_estate": "realestate",
        "rl_lab": "rl",
        "scenario": "practice",
        "sim_dashboard": "practice",
        "strategy": "finance",
        "terminal": "chat",
        "thought_map": "thought",
        "trader": "trader",
        "viz_lab": "vizlab",
        "viz_mmo": "mmo",
    }

    entries: List[Dict[str, Any]] = []
    visualized = 0
    for module_name in modules:
        stem = Path(module_name).stem.lower()
        suggested_view = view_hints.get(stem)
        if not suggested_view and stem in view_set:
            suggested_view = stem
        if not suggested_view:
            normalized = stem.replace("_", "")
            if normalized in view_set:
                suggested_view = normalized

        view_exists = bool(suggested_view and suggested_view in view_set)
        linked = bool(suggested_view and suggested_view in switch_targets)
        if view_exists and linked:
            status = "visualized"
            visualized += 1
            note = "View exists and is linked in switchView."
        elif view_exists or linked:
            status = "partial"
            note = "Partially wired. Keep this module but finish wiring."
        else:
            status = "pending"
            note = "No visible view yet. Keep module and add UI wiring later."

        entries.append(
            {
                "module": module_name,
                "suggested_view": suggested_view,
                "view_exists": view_exists,
                "linked": linked,
                "status": status,
                "note": note,
            }
        )

    total = len(entries)
    pending = sum(1 for entry in entries if entry["status"] != "visualized")
    return {
        "total": total,
        "visualized": visualized,
        "pending": pending,
        "views_discovered": len(views),
        "switch_targets": sorted(switch_targets),
        "entries": entries,
    }


def _build_thought_map_snapshot() -> Dict[str, Any]:
    command_center = _build_command_center_snapshot()
    connectivity = _build_connectivity_checks()
    trace = _build_thinking_trace(limit=16)
    graph = _build_thought_graph(command_center, connectivity)
    module_registry = _build_module_registry_snapshot()

    project = command_center.get("project", {})
    runs = command_center.get("runs", {})

    return {
        "generated_at": datetime.now().isoformat(),
        "status": command_center.get("status", "degraded"),
        "pulse_score": int(command_center.get("pulse_score") or 0),
        "connectivity": connectivity,
        "thinking_trace": trace,
        "graph": graph,
        "module_registry": module_registry,
        "visibility": {
            "desktop_views": int(project.get("desktop_views") or 0),
            "desktop_js_modules": int(project.get("desktop_js_modules") or 0),
            "latest_run_id": runs.get("latest_run_id"),
            "latest_run_updated": runs.get("latest_updated"),
            "module_registry_pending": int(module_registry.get("pending") or 0),
        },
        "command_center": command_center,
    }


def _get_local_models() -> List[Dict]:
    """
    Query Ollama for locally installed models.
    Returns a list of {id, label, active, size_gb} dicts.
    Falls back to [active_model] if Ollama is unreachable.
    """
    try:
        import ollama as _ollama
        raw = _ollama.list()
        # ollama.list() returns a dict with 'models' key (list of model dicts)
        models_raw = raw.get("models", []) if isinstance(raw, dict) else []
        # Each item has 'name', 'size', etc.
        result = []
        for m in models_raw:
            name = m.get("name", "") or m.get("model", "")
            if not name:
                continue
            size_bytes = m.get("size", 0) or 0
            size_gb    = round(size_bytes / 1e9, 1)
            label = _KNOWN_MODELS.get(name, name)
            result.append({
                "id":      name,
                "label":   label,
                "active":  name == _aria_active_model,
                "size_gb": size_gb,
            })
        if not result:
            # No models pulled yet — return the configured default
            result = [{
                "id":      _aria_active_model,
                "label":   _KNOWN_MODELS.get(_aria_active_model, _aria_active_model),
                "active":  True,
                "size_gb": 0,
            }]
        return result
    except Exception as e:
        logger.warning("Could not list Ollama models: %s", e)
        return [{
            "id":      _aria_active_model,
            "label":   _KNOWN_MODELS.get(_aria_active_model, _aria_active_model),
            "active":  True,
            "size_gb": 0,
        }]


async def _ask_local(user_message: str) -> tuple:
    """
    Ask ARIA via local Ollama. 100% offline — no external calls.
    Returns (response: str, model_used: str, latency_ms: int).
    """
    global _aria_audit_log
    t0 = time.time()

    if not aria_instance:
        raise RuntimeError("ARIA not initialised")

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(aria_instance.ask, user_message),
            timeout=QUERY_TIMEOUT_SECONDS,
        )
        latency_ms = int((time.time() - t0) * 1000)
        _aria_audit_log.append({
            "ts":          datetime.now().isoformat(),
            "model":       _aria_active_model,
            "latency_ms":  latency_ms,
            "success":     True,
            "message_len": len(user_message),
        })
        if len(_aria_audit_log) > 500:
            _aria_audit_log.pop(0)
        return response, _aria_active_model, latency_ms
    except Exception as e:
        _aria_audit_log.append({
            "ts":          datetime.now().isoformat(),
            "model":       _aria_active_model,
            "latency_ms":  int((time.time() - t0) * 1000),
            "success":     False,
            "message_len": len(user_message),
        })
        if len(_aria_audit_log) > 500:
            _aria_audit_log.pop(0)
        raise


# _ask_with_provider: routes to local Ollama OR cloud provider based on selection
async def _ask_with_provider(user_message: str, preferred: str = "auto") -> tuple:
    """
    Route to the correct backend:
      - local models  → Ollama
      - cloud:groq    → Groq API (free tier, OpenAI-compatible)
      - cloud:openrouter → OpenRouter API
      - cloud:gemini  → Google Gemini API
    """
    if preferred.startswith("cloud:"):
        pid = preferred[6:]   # strip "cloud:" prefix
        try:
            return await _ask_cloud(user_message, pid)
        except Exception as e:
            logger.warning("Cloud provider %s failed: %s — falling back to Ollama", pid, e)
            # Fall through to local
    return await _ask_local(user_message)

# Keep _PROVIDER_FALLBACK_ORDER for code that references it
_PROVIDER_FALLBACK_ORDER = ["ollama"]


def _slash_models() -> str:
    """Format /models slash command response."""
    models = _get_local_models()
    lines = ["**ARIA — Local Models (Ollama)**\n"]
    for m in models:
        icon  = "●" if m["active"] else "○"
        size  = f" · {m['size_gb']} GB" if m["size_gb"] else ""
        lines.append(f"{icon} **{m['id']}** — {m['label']}{size}")
    lines.append(f"\n**Active:** `{_aria_active_model}`")
    lines.append("\nSwitch with `/model <name>` — all models run 100% locally via Ollama.")
    return "\n".join(lines)


def _slash_audit(n: int = 10) -> str:
    """Format /audit slash command response."""
    if not _aria_audit_log:
        return "No audit entries yet."
    entries = _aria_audit_log[-n:]
    lines = [f"**Last {len(entries)} ARIA Requests**\n"]
    for e in reversed(entries):
        icon = "✅" if e["success"] else "❌"
        lines.append(
            f"{icon} `{e['ts'][-8:]}` **{e['model']}** · {e['latency_ms']}ms"
        )
    total   = len(_aria_audit_log)
    ok      = sum(1 for x in _aria_audit_log if x["success"])
    avg_lat = int(sum(x["latency_ms"] for x in _aria_audit_log) / total) if total else 0
    lines.append(f"\n*{ok}/{total} successful · avg {avg_lat}ms*")
    return "\n".join(lines)


# ==================== REST API ====================

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Silence browser favicon 404s in logs."""
    return Response(status_code=204, media_type="image/x-icon")


@app.get("/api/health")
def root():
    """Health check"""
    return {
        "status": "online",
        "service": "ARIA Multi-Device Server",
        "version": "1.0"
    }


@app.get("/api/monitor/tick")
async def monitor_tick(tickers: str = "AAPL,MSFT,NVDA,BTC-USD,SPY,QQQ"):
    """
    Live Monitor snapshot — parallel quote fetch for multiple tickers.
    Designed for the Viz Lab Live Monitor panel (auto-polls every 15s).
    Returns: per-ticker price, change_pct, volume + server_ms + timestamp.
    All fetches run concurrently so 6 tickers ≈ same latency as 1.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:8]
    t0 = time.time()

    async def _fetch_one(sym: str) -> dict:
        try:
            import yfinance as yf
            hist = await asyncio.to_thread(
                lambda: yf.Ticker(sym).history(period="5d", interval="1d", auto_adjust=True)
            )
            if hist is None or hist.empty:
                return {"symbol": sym, "price": None, "change_pct": None, "volume": None}
            closes = hist["Close"].dropna()
            price = float(closes.iloc[-1])
            change_pct = 0.0
            if len(closes) >= 2:
                prev = float(closes.iloc[-2])
                change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
            volume = int(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist.columns else None
            return {
                "symbol": sym,
                "price": round(price, 4),
                "change_pct": change_pct,
                "volume": volume,
            }
        except Exception as exc:
            return {"symbol": sym, "price": None, "change_pct": None, "volume": None, "error": str(exc)[:60]}

    results = await asyncio.gather(*[_fetch_one(sym) for sym in ticker_list])
    return {
        "tickers": list(results),
        "count": len(results),
        "server_ms": round((time.time() - t0) * 1000),
        "timestamp": datetime.now().isoformat(),
        "status": "ok",
    }


@app.get("/api/system/verify")
async def system_verify(ticker: str = "AAPL"):
    """
    Full-loop diagnostic: Data -> Signal -> Result.
    Tests that the complete Atlas pipeline works end-to-end for a given ticker.
    Returns a structured health report with timing for each stage.
    """
    import time as _t
    report = {"ticker": ticker.upper(), "stages": {}, "ok": True, "ts": datetime.now().isoformat()}

    # Stage 1: Data fetch (real first, deterministic local fallback)
    t0 = _t.time()
    try:
        hist, is_synthetic = _fetch_ohlcv_local(ticker.upper(), period="1mo")
        if hist is None or hist.empty:
            raise ValueError("Empty response from data layer")
        price = float(hist["Close"].dropna().iloc[-1])
        report["stages"]["data"] = {
            "ok": True,
            "price": round(price, 2),
            "synthetic": bool(is_synthetic),
            "ms": round((_t.time() - t0) * 1000),
        }
    except Exception as e:
        report["stages"]["data"] = {"ok": False, "error": str(e)[:120], "ms": round((_t.time()-t0)*1000)}
        report["ok"] = False

    # Stage 2: Cache layer
    t0 = _t.time()
    try:
        _cache_set(f"__verify_{ticker}", {"test": True}, ttl=10)
        hit = _cache_get(f"__verify_{ticker}")
        report["stages"]["cache"] = {"ok": hit is not None, "ms": round((_t.time()-t0)*1000)}
        if not hit:
            report["ok"] = False
    except Exception as e:
        report["stages"]["cache"] = {"ok": False, "error": str(e)[:80]}
        report["ok"] = False

    # Stage 3: Signal engine
    t0 = _t.time()
    try:
        from atlas.trader.composite_scorer import CompositeScorer
        hist2, is_synthetic_sig = _fetch_ohlcv_local(ticker.upper(), period="6mo")
        scorer = CompositeScorer()
        score_result = await asyncio.to_thread(scorer.score, ticker.upper(), hist2)
        action = getattr(score_result, "action", None) or score_result.get("action", "?") if isinstance(score_result, dict) else str(score_result)[:40]
        report["stages"]["signal"] = {
            "ok": True,
            "action": str(action)[:20],
            "synthetic": bool(is_synthetic_sig),
            "ms": round((_t.time() - t0) * 1000),
        }
    except Exception as e:
        report["stages"]["signal"] = {"ok": False, "error": str(e)[:120], "ms": round((_t.time()-t0)*1000)}
        report["stages"]["signal"]["warning"] = "signal engine degraded"

    # Stage 4: ARIA health
    t0 = _t.time()
    aria_ok = aria_instance is not None
    report["stages"]["aria"] = {
        "ok": aria_ok,
        "model": _aria_active_model,
        "initialized": aria_ok,
        "ms": round((_t.time()-t0)*1000),
    }

    # Summary
    stages_ok = sum(1 for s in report["stages"].values() if s.get("ok"))
    report["summary"] = f"{stages_ok}/{len(report["stages"])} stages passing"
    return report


@app.get("/api/system/command_center")
def command_center_snapshot():
    """Aggregated snapshot for the Atlas dashboard Command Center."""
    return _build_command_center_snapshot()


@app.get("/api/system/thought_map")
def thought_map_snapshot():
    """System-wide visibility graph + high-level ARIA reasoning trace."""
    return _build_thought_map_snapshot()


@app.post("/query", response_model=QueryResponse)
async def query_aria(request: QueryRequest):
    """
    Query ARIA — routes through the active provider with automatic fallback.

    Request:
        {
            "message": "What's AAPL price?",
            "device_id": "pc-1",
            "session_id": "session-123" (optional)
        }

    Slash commands (handled server-side, no LLM call):
        /providers       — list configured providers + status
        /audit [n]       — show last n audit entries (default 10)
        /model <name>    — switch active provider
        /debug <topic>   — structured debug protocol
        /review <ticker> — strategy review template
    """
    # Generate session ID if not provided
    session_id = request.session_id or f"session-{datetime.now().timestamp()}"

    # Save user message
    db.add_message(session_id, request.device_id, "user", request.message)

    msg = request.message.strip()
    provider_used = "system"
    latency_ms = 0

    # ── Slash-command fast path ────────────────────────────────────────────────
    if msg.startswith("/"):
        global _aria_active_provider
        parts = msg.split(None, 1)
        cmd  = parts[0].lower()
        arg  = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/providers", "/models"):
            response = _slash_models()

        elif cmd == "/audit":
            n = int(arg) if arg.isdigit() else 10
            response = _slash_audit(n)

        elif cmd == "/project":
            snap = _build_command_center_snapshot()
            runtime = snap.get("runtime", {})
            project = snap.get("project", {})
            runs = snap.get("runs", {})
            aria = snap.get("aria", {})
            response = (
                "**Atlas Command Center**\n\n"
                f"- Status: **{snap.get('status', 'unknown').upper()}** "
                f"(pulse {snap.get('pulse_score', 0)}/100)\n"
                f"- Runtime: {runtime.get('modules_online', 0)}/{runtime.get('modules_total', 0)} modules online, "
                f"{runtime.get('api_routes', 0)} API routes\n"
                f"- Project: {project.get('desktop_views', 0)} UI views, "
                f"{project.get('docs_markdown', 0)} docs, "
                f"{project.get('governance_markdown', 0)} governance docs\n"
                f"- Runs: {runs.get('count', 0)} total, latest `{runs.get('latest_run_id') or 'none'}`\n"
                f"- ARIA: model `{aria.get('active_model', 'unknown')}`, "
                f"{aria.get('installed_models', 0)} local model(s)\n\n"
                "Live endpoint: `/api/system/command_center`"
            )

        elif cmd == "/model":
            global _aria_active_model
            if arg:
                _aria_active_model = arg
                # Also switch the live ARIA instance model
                if aria_instance:
                    aria_instance.model = arg
                response = (
                    f"✅ Switched to **{arg}** — running locally on Ollama.\n"
                    f"Use `/models` to see all installed models."
                )
            else:
                response = (
                    f"Current model: `{_aria_active_model}`\n"
                    f"Usage: `/model <name>` — e.g. `/model llama3.1:8b`\n"
                    f"List models: `/models`"
                )

        elif cmd == "/debug":
            topic = arg or "current issue"
            response = (
                f"🔍 **Debug Protocol — {topic}**\n\n"
                "**Step 1: Reproduce**\n- Describe exact steps to trigger the issue\n\n"
                "**Step 2: Isolate**\n- Check server logs: `tail -f atlas.log`\n"
                "- Check browser console (F12 → Console)\n"
                "- Verify API health: `GET /api/health`\n\n"
                "**Step 3: Inspect**\n- Provider status: `/providers`\n"
                "- Recent calls: `/audit 5`\n"
                "- Strategy engines: `GET /api/strategy/engines`\n\n"
                "**Step 4: Fix & Verify**\n- Apply fix → restart server → retest\n\n"
                f"What specifically is happening with **{topic}**? Paste the error or describe it."
            )

        elif cmd == "/review":
            ticker = arg.upper() or "TARGET"
            response = (
                f"📋 **Strategy Review — {ticker}**\n\n"
                f"**1. Signal Consensus** → `GET /api/strategy/analyze/{ticker}`\n"
                f"**2. Backtest** → `GET /api/strategy/backtest/{ticker}`\n"
                f"**3. Regime** → `GET /api/vizlab/regime/{ticker}`\n"
                f"**4. Similar Patterns** — check `PatternMemory` for analogous states\n"
                f"**5. Correlation** → `GET /api/correlation/pairs`\n\n"
                f"**Checklist:**\n"
                f"- [ ] Sharpe > 1.0\n- [ ] Max drawdown < 20%\n"
                f"- [ ] Win rate > 50%\n- [ ] Signal agreement ≥ 3/5 engines\n"
                f"- [ ] Regime = trending (avoid volatile)\n\n"
                f"Want me to run the full analysis for **{ticker}**?"
            )

        elif cmd == "/help":
            response = (
                "**ARIA Slash Commands**\n\n"
                "| Command | Description |\n"
                "|---------|-------------|\n"
                "| `/models` | List locally installed Ollama models |\n"
                "| `/model <name>` | Switch to a different local model |\n"
                "| `/audit [n]` | Show last n request logs |\n"
                "| `/project` | Show Atlas command-center snapshot |\n"
                "| `/debug <topic>` | Structured debug protocol |\n"
                "| `/review <ticker>` | Strategy review checklist |\n"
                "| `/help` | This help message |\n\n"
                "*All models run 100% locally via Ollama — no internet required.*"
            )

        else:
            # Unknown slash command → pass to LLM
            response = None

        if response is not None:
            timestamp = datetime.now().isoformat()
            db.add_message(session_id, request.device_id, "assistant", response)
            await broadcast_message(session_id, {
                "type": "new_message", "role": "assistant",
                "content": response, "timestamp": timestamp,
            })
            return QueryResponse(
                response=response, session_id=session_id,
                timestamp=timestamp, provider="system", latency_ms=0,
            )

    # ── LLM path ──────────────────────────────────────────────────────────────
    # Cloud models bypass local Ollama check entirely
    is_cloud = _aria_active_model.startswith("cloud:")
    if not aria_instance and not is_cloud:
        raise HTTPException(status_code=500, detail="ARIA not initialized. Start Ollama or select a cloud model.")

    # Restore session history so ARIA has multi-turn context from previous exchanges.
    # We load the last 20 messages from SQLite and inject them before the current ask().
    if aria_instance:
        prior = db.get_conversation(session_id, limit=20)
        # Exclude the current user message we just saved (last item) to avoid duplicate
        history_msgs = [{"role": m["role"], "content": m["content"]} for m in prior[:-1]]
        aria_instance.history = history_msgs

    try:
        response, provider_used, latency_ms = await _ask_with_provider(
            msg, preferred=_aria_active_model
        )
    except asyncio.TimeoutError:
        response = (
            "⏱ Request timed out. "
            "Try `/model groq` for a faster cloud provider, or simplify your prompt."
        )
        provider_used = "timeout"
        latency_ms = QUERY_TIMEOUT_SECONDS * 1000
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save & broadcast
    timestamp = datetime.now().isoformat()
    db.add_message(session_id, request.device_id, "assistant", response)
    await broadcast_message(session_id, {
        "type": "new_message", "role": "assistant",
        "content": response, "timestamp": timestamp,
        "provider": provider_used, "latency_ms": latency_ms,
    })

    return QueryResponse(
        response=response,
        session_id=session_id,
        timestamp=timestamp,
        provider=provider_used,
        latency_ms=latency_ms,
    )


@app.get("/conversation/{session_id}")
def get_conversation(session_id: str, limit: int = 50):
    """Get conversation history for a session (used by frontend to restore context)."""
    messages = db.get_conversation(session_id, limit)
    return {"session_id": session_id, "messages": messages}


@app.post("/api/device/register")
def register_device(device_id: str, device_name: str = "unknown"):
    """Register a device for multi-device sync."""
    db.register_device(device_id, device_name)
    return {"status": "registered", "device_id": device_id}


# ==================== SCENARIO MODE API ====================

# Global session store for scenarios (simple in-memory for now)
scenario_sessions: Dict[str, Any] = {}

class ScenarioStartRequest(BaseModel):
    ticker: str = "SPY"
    initial_capital: float = 10000.0
    start_date: str = "2020-01-01"

@app.post("/api/scenario/start")
def start_scenario(request: ScenarioStartRequest):
    """Start a new interactive scenario session."""
    try:
        symbol = request.ticker.strip().upper()
        print(f"Fetching data for {symbol}...")

        data, is_synthetic = _fetch_ohlcv_local(symbol, period="5y")
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail="No data found for ticker")

        data = data.copy()
        data.columns = [c.lower() for c in data.columns]
        data["date"] = data.index
        
        # Initialize session
        from atlas.evaluation.scenario import ScenarioSession
        session = ScenarioSession(data, request.initial_capital, symbol)
        
        # Store in memory
        session_id = f"scen-{datetime.now().timestamp()}"
        scenario_sessions[session_id] = session
        
        # Get first step (initial state)
        state = session.next_step()
        
        return {
            "session_id": session_id,
            "ticker": symbol,
            "total_steps": len(data),
            "initial_state": state,
            "synthetic": bool(is_synthetic),
        }

    except Exception as e:
        print(f"Scenario error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scenario/{session_id}/next")
def next_scenario_step(session_id: str):
    """Advance simulation by one step."""
    if session_id not in scenario_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = scenario_sessions[session_id]
    state = session.next_step()
    
    if state is None:
        return {"status": "finished", "history": session.get_full_history()}
        
    return {"status": "active", "state": state}

class SwitchTickerRequest(BaseModel):
    session_id: str
    ticker: str

@app.post("/api/scenario/switch_ticker")
def switch_ticker(request: SwitchTickerRequest):
    """Switch active ticker in scenario."""
    if request.session_id not in scenario_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = scenario_sessions[request.session_id]
    success = session.switch_ticker(request.ticker)
    
    if not success:
         raise HTTPException(status_code=400, detail="Failed to switch ticker (no data?)")
         
    return {"status": "ok", "ticker": request.ticker}


# --- Portfolio API ---

last_active_session_id = None
PORTFOLIO_UPLOAD_PATH = Path("data") / "portfolio_uploaded.json"

@app.get("/api/portfolio")
def get_portfolio():
    """Get portfolio state from active session."""
    # Find most recent session
    if not scenario_sessions:
        return {
            "source": "none",
            "has_active_session": False,
            "capital": 0,
            "total_equity": 0,
            "positions": [],
        }
        
    # Just take the last one created
    session = list(scenario_sessions.values())[-1]
    
    positions_data = []
    total_equity = session.capital
    
    for symbol, pos in session.positions.items():
        market_val = pos['qty'] * pos['last_price']
        cost_basis = pos['qty'] * pos['avg_price']
        pnl = market_val - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        positions_data.append({
            "symbol": symbol,
            "qty": pos['qty'],
            "avg_price": pos['avg_price'],
            "current_price": pos['last_price'],
            "market_value": market_val,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        })
        total_equity += market_val
        
    return {
        "source": "scenario",
        "has_active_session": True,
        "capital": session.capital,
        "total_equity": total_equity,
        "positions": positions_data
    }

@app.get("/api/portfolio/uploaded")
def get_uploaded_portfolio():
    """Return last uploaded portfolio package if it exists."""
    if not PORTFOLIO_UPLOAD_PATH.exists():
        return {"source": "uploaded", "has_uploaded_portfolio": False, "positions": []}
    try:
        data = json.loads(PORTFOLIO_UPLOAD_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"source": "uploaded", "has_uploaded_portfolio": False, "positions": []}

    positions = data.get("positions") if isinstance(data, dict) else None
    if not isinstance(positions, list):
        return {"source": "uploaded", "has_uploaded_portfolio": False, "positions": []}

    return {
        "source": "uploaded",
        "has_uploaded_portfolio": True,
        "as_of": data.get("as_of"),
        "total_equity": data.get("total_equity"),
        "positions": positions,
    }

@app.post("/api/portfolio/upload")
async def upload_portfolio(file: UploadFile = File(...)):
    """Upload a portfolio package JSON and persist it server-side."""
    try:
        raw = await file.read()
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not isinstance(payload, dict) or not isinstance(payload.get("positions"), list):
        raise HTTPException(status_code=400, detail="Invalid portfolio schema.")

    PORTFOLIO_UPLOAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_UPLOAD_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    return {"status": "ok", "saved_to": str(PORTFOLIO_UPLOAD_PATH)}


# ==================== SIMULATION DASHBOARD API ====================

def _coerce_dashboard_positions(raw_positions: Any) -> List[Dict[str, float | str]]:
    if not isinstance(raw_positions, list):
        return []
    positions: List[Dict[str, float | str]] = []
    for item in raw_positions:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        qty = float(item.get("qty", 0) or 0)
        avg_price = float(item.get("avg_price", 0) or 0)
        current_price = float(item.get("current_price", avg_price) or avg_price)
        if qty <= 0 or current_price <= 0:
            continue
        positions.append(
            {
                "symbol": symbol,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
            }
        )
    return positions


def _positions_from_active_scenario() -> List[Dict[str, float | str]]:
    if not scenario_sessions:
        return []
    session = list(scenario_sessions.values())[-1]
    positions: List[Dict[str, float | str]] = []
    for symbol, pos in session.positions.items():
        qty = float(pos.get("qty", 0) or 0)
        avg_price = float(pos.get("avg_price", 0) or 0)
        current_price = float(pos.get("last_price", avg_price) or avg_price)
        if qty <= 0 or current_price <= 0:
            continue
        positions.append(
            {
                "symbol": str(symbol).upper(),
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
            }
        )
    return positions


def _positions_from_uploaded_portfolio() -> List[Dict[str, float | str]]:
    if not PORTFOLIO_UPLOAD_PATH.exists():
        return []
    try:
        payload = json.loads(PORTFOLIO_UPLOAD_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return _coerce_dashboard_positions(payload.get("positions"))


def _resolve_portfolio_positions() -> List[Dict[str, float | str]]:
    scenario_positions = _positions_from_active_scenario()
    if scenario_positions:
        return scenario_positions
    uploaded_positions = _positions_from_uploaded_portfolio()
    if uploaded_positions:
        return uploaded_positions
    return []


def _resolve_seed_price(ticker: str, fallback: float = 100.0) -> float:
    symbol = str(ticker).strip().upper() or "SPY"
    try:
        import yfinance as yf

        hist = yf.Ticker(symbol).history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return fallback


def _load_stock_candles(symbol: str, period: str = "1y", interval: str = "1d") -> List[Dict[str, Any]]:
    try:
        import yfinance as yf
        import pandas as pd

        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if data is None or data.empty:
            return []

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.columns = [str(column).lower() for column in data.columns]
        required = {"open", "high", "low", "close"}
        if not required.issubset(set(data.columns)):
            return []

        candles: List[Dict[str, Any]] = []
        for index, row in data.iterrows():
            try:
                open_price = float(row["open"])
                high_price = float(row["high"])
                low_price = float(row["low"])
                close_price = float(row["close"])
                volume = float(row["volume"]) if "volume" in data.columns else 0.0
            except Exception:
                continue

            if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                continue

            candles.append(
                {
                    "time": index.strftime("%Y-%m-%d"),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )

        return candles[-365:]
    except Exception:
        return []


def _candles_fingerprint(symbol: str, candles: List[Dict[str, Any]]) -> str:
    if not candles:
        return f"{symbol}:empty"
    first = candles[0].get("time", "")
    last = candles[-1].get("time", "")
    return f"{symbol}:{len(candles)}:{first}:{last}"


class SimDashboardStartRequest(BaseModel):
    mode: str = "stock"  # stock | portfolio
    ticker: str = "SPY"
    tick_interval_seconds: float = 1.0
    use_portfolio: bool = False
    positions: Optional[List[Dict[str, Any]]] = None
    active_modules: Optional[List[str]] = None


class SimDashboardConfigRequest(BaseModel):
    mode: Optional[str] = None
    ticker: Optional[str] = None
    tick_interval_seconds: Optional[float] = None
    use_portfolio: bool = False
    positions: Optional[List[Dict[str, Any]]] = None
    active_modules: Optional[List[str]] = None


class DesktopSimulationRuntime:
    def __init__(self) -> None:
        self._lock = Lock()
        self._initialized = False
        self._runner = None
        self._registry = None
        self._module_meta: List[Dict[str, str]] = []
        self._config: Dict[str, Any] = {
            "mode": "stock",
            "ticker": "SPY",
            "tick_interval_seconds": 1.0,
        }
        self._stock_candle_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            from atlas.core.analytics.modules import (
                CommodityConcentrationMonitorModule,
                MarketStateModule,
                PortfolioStockSimulationModule,
            )
            from atlas.core.engine import ArtifactRegistry, EventBus, SimulationRunner
            from atlas.services.storage import SQLiteArtifactStore

            store = SQLiteArtifactStore(db_path=Path("data") / "desktop_sim_artifacts.db")
            registry = ArtifactRegistry(cache_size=8000, store=store)
            event_bus = EventBus(registry=registry)
            modules = [
                MarketStateModule(seed=7),
                CommodityConcentrationMonitorModule(seed=13),
                PortfolioStockSimulationModule(seed=41),
            ]
            runner = SimulationRunner(
                event_bus=event_bus,
                modules=modules,
                tick_interval_seconds=1.0,
                runner_id="desktop_sim_api",
            )

            self._registry = registry
            self._runner = runner
            self._module_meta = [
                {
                    "module_id": module.module_id,
                    "title": module.title,
                    "description": module.description,
                }
                for module in modules
            ]
            self._initialized = True

    def _validate_mode(self, mode: str) -> str:
        normalized = str(mode).strip().lower() or "stock"
        if normalized not in {"stock", "portfolio"}:
            raise HTTPException(status_code=400, detail="mode must be 'stock' or 'portfolio'")
        return normalized

    def _build_inputs(
        self,
        mode: str,
        ticker: str,
        use_portfolio: bool,
        positions: Optional[List[Dict[str, Any]]],
        previous_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        inputs = dict(previous_inputs or {})
        symbol = str(ticker).strip().upper() or "SPY"
        inputs["mode"] = mode
        inputs["ticker"] = symbol
        inputs["seed_price"] = _resolve_seed_price(symbol, fallback=float(inputs.get("seed_price", 100.0)))
        inputs.pop("stock_candles", None)
        inputs.pop("stock_candles_fingerprint", None)

        if mode == "stock":
            candles = self._stock_candle_cache.get(symbol)
            if not candles:
                candles = _load_stock_candles(symbol, period="1y", interval="1d")
                self._stock_candle_cache[symbol] = candles
            inputs["stock_candles"] = candles
            inputs["stock_candles_fingerprint"] = _candles_fingerprint(symbol, candles)

        if positions is not None:
            inputs["positions"] = _coerce_dashboard_positions(positions)
        elif use_portfolio or mode == "portfolio":
            inputs["positions"] = _resolve_portfolio_positions()

        return inputs

    def state(self) -> Dict[str, Any]:
        self._ensure_initialized()
        runner = self._runner
        registry = self._registry
        assert runner is not None
        assert registry is not None
        raw_inputs = runner.get_inputs()
        safe_inputs = dict(raw_inputs)
        if "stock_candles" in safe_inputs:
            try:
                safe_inputs["stock_candles_count"] = len(safe_inputs["stock_candles"])
            except Exception:
                safe_inputs["stock_candles_count"] = 0
            del safe_inputs["stock_candles"]

        return {
            "running": runner.is_running(),
            "tick": runner.tick_count,
            "tick_interval_seconds": runner.tick_interval_seconds,
            "last_sequence": registry.get_last_sequence(),
            "artifacts_cached": registry.total_artifacts(),
            "warning_error_events": len(registry.get_error_events(limit=200)),
            "last_update": registry.get_last_update().isoformat() if registry.get_last_update() else None,
            "config": dict(self._config),
            "inputs": safe_inputs,
            "modules": [
                {
                    **meta,
                    "active": meta["module_id"] in runner.active_module_ids(),
                }
                for meta in self._module_meta
            ],
        }

    def start(self, request: SimDashboardStartRequest) -> Dict[str, Any]:
        self._ensure_initialized()
        runner = self._runner
        assert runner is not None

        mode = self._validate_mode(request.mode)
        ticker = str(request.ticker).strip().upper() or "SPY"
        if request.tick_interval_seconds <= 0:
            raise HTTPException(status_code=400, detail="tick_interval_seconds must be > 0")

        runner.set_tick_interval_seconds(float(request.tick_interval_seconds))
        inputs = self._build_inputs(
            mode=mode,
            ticker=ticker,
            use_portfolio=bool(request.use_portfolio),
            positions=request.positions,
            previous_inputs=runner.get_inputs(),
        )
        runner.set_inputs(inputs)

        if request.active_modules:
            runner.set_active_modules(request.active_modules)

        self._config = {
            "mode": mode,
            "ticker": ticker,
            "tick_interval_seconds": float(request.tick_interval_seconds),
        }
        runner.start()
        return self.state()

    def stop(self) -> Dict[str, Any]:
        self._ensure_initialized()
        runner = self._runner
        assert runner is not None
        runner.stop()
        return self.state()

    def update(self, request: SimDashboardConfigRequest) -> Dict[str, Any]:
        self._ensure_initialized()
        runner = self._runner
        assert runner is not None

        current_mode = self._config.get("mode", "stock")
        current_ticker = self._config.get("ticker", "SPY")

        if request.mode is not None:
            current_mode = self._validate_mode(request.mode)
        if request.ticker is not None:
            current_ticker = str(request.ticker).strip().upper() or "SPY"

        if request.tick_interval_seconds is not None:
            if request.tick_interval_seconds <= 0:
                raise HTTPException(status_code=400, detail="tick_interval_seconds must be > 0")
            runner.set_tick_interval_seconds(float(request.tick_interval_seconds))
            self._config["tick_interval_seconds"] = float(request.tick_interval_seconds)

        inputs = self._build_inputs(
            mode=current_mode,
            ticker=current_ticker,
            use_portfolio=bool(request.use_portfolio),
            positions=request.positions,
            previous_inputs=runner.get_inputs(),
        )
        runner.set_inputs(inputs)

        if request.active_modules is not None:
            runner.set_active_modules(request.active_modules)

        self._config["mode"] = current_mode
        self._config["ticker"] = current_ticker

        return self.state()

    def artifacts(
        self,
        *,
        since_sequence: int = 0,
        module_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        limit: int = 400,
    ) -> Dict[str, Any]:
        self._ensure_initialized()
        registry = self._registry
        assert registry is not None

        artifact_type_filter = None
        if artifact_type:
            from atlas.core.analytics.artifacts import ArtifactType

            artifact_type_filter = ArtifactType(str(artifact_type).upper())

        artifacts = registry.get_history(
            module_id=module_id,
            artifact_type=artifact_type_filter,
            since_sequence=max(0, since_sequence),
            limit=max(1, min(limit, 2000)),
        )
        return {
            "artifacts": [artifact.to_record() for artifact in artifacts],
            "last_sequence": registry.get_last_sequence(),
        }

    def snapshot(self) -> Dict[str, Any]:
        self._ensure_initialized()
        registry = self._registry
        runner = self._runner
        assert registry is not None
        assert runner is not None

        modules_snapshot: List[Dict[str, Any]] = []
        for meta in self._module_meta:
            module_id = meta["module_id"]
            history = registry.get_history(module_id=module_id, limit=240)
            latest_by_type: Dict[str, Dict[str, Any]] = {}
            recent_events: List[Dict[str, Any]] = []
            recent_logs: List[Dict[str, Any]] = []

            for artifact in history:
                key = artifact.artifact_type.value
                if key in {"EVENT", "LOG"}:
                    if key == "EVENT":
                        recent_events.append(artifact.to_record())
                    else:
                        recent_logs.append(artifact.to_record())
                else:
                    latest_by_type[key] = artifact.to_record()

            modules_snapshot.append(
                {
                    **meta,
                    "active": module_id in runner.active_module_ids(),
                    "latest_artifacts": latest_by_type,
                    "recent_events": recent_events[-5:],
                    "recent_logs": recent_logs[-5:],
                }
            )

        return {
            "state": self.state(),
            "modules": modules_snapshot,
            "errors": [event.to_record() for event in registry.get_error_events(limit=20)],
            "audit": [
                {
                    "sequence": audit.sequence,
                    "artifact_id": audit.artifact_id,
                    "module_id": audit.module_id,
                    "artifact_type": audit.artifact_type.value,
                    "title": audit.title,
                    "published_by": audit.published_by,
                    "created_at": audit.created_at.isoformat(),
                }
                for audit in registry.get_audit_trail(limit=60)
            ],
        }


desktop_sim_runtime = DesktopSimulationRuntime()


@app.get("/api/sim/dashboard/state")
def sim_dashboard_state():
    return desktop_sim_runtime.state()


@app.post("/api/sim/dashboard/start")
def sim_dashboard_start(request: SimDashboardStartRequest):
    return desktop_sim_runtime.start(request)


@app.post("/api/sim/dashboard/stop")
def sim_dashboard_stop():
    return desktop_sim_runtime.stop()


@app.post("/api/sim/dashboard/config")
def sim_dashboard_config(request: SimDashboardConfigRequest):
    return desktop_sim_runtime.update(request)


@app.get("/api/sim/dashboard/artifacts")
def sim_dashboard_artifacts(
    since_sequence: int = 0,
    module_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    limit: int = 400,
):
    return desktop_sim_runtime.artifacts(
        since_sequence=since_sequence,
        module_id=module_id,
        artifact_type=artifact_type,
        limit=limit,
    )


@app.get("/api/sim/dashboard/snapshot")
def sim_dashboard_snapshot():
    return desktop_sim_runtime.snapshot()

# --- 3D Visualization API ---

@app.get("/api/viz/3d/{viz_type}")
def generate_3d_viz(viz_type: str):
    """Generate 3D render."""
    try:
        from atlas.visualization.renderer_3d import Atlas3DRenderer
        import numpy as np
        import pandas as pd
        
        renderer = Atlas3DRenderer(output_dir="apps/desktop/assets/3d") # Save to public folder
        
        path = ""
        
        if viz_type == "vol_surface":
            # Generate Synthetic Vol Surface
            strikes = np.linspace(100, 200, 20)
            expiries = np.linspace(7, 90, 20)
            iv = np.zeros((20, 20))
            for i in range(20):
                for j in range(20):
                    # Vol smile + term structure
                    iv[i, j] = 0.2 + 0.001 * (strikes[j] - 150)**2 + 0.05 * np.exp(-expiries[i]/100)
            
            path = renderer.volatility_surface(strikes, expiries, iv, title="Synthetic Volatility Surface (Atlas Engine)")
            
        elif viz_type == "correlation":
            # Synthetic Corr Matrix
            data = {
                "SPY": np.random.normal(0, 1, 100),
                "QQQ": np.random.normal(0, 1, 100),
                "IWM": np.random.normal(0, 1, 100),
                "GLD": np.random.normal(0, 1, 100),
                "USO": np.random.normal(0, 1, 100)
            }
            df = pd.DataFrame(data)
            # Add some correlation
            df['QQQ'] += df['SPY'] * 0.8
            df['IWM'] += df['SPY'] * 0.6
            
            path = renderer.correlation_mountain(df.corr(), title="Portfolio Correlation Mountain")
            
        elif viz_type == "risk":
             # Synthetic Risk Landscape
            allocs = np.linspace(0, 1, 30)
            returns = np.linspace(-0.1, 0.1, 30)
            risk = np.zeros((30, 30))
            for i, a in enumerate(allocs):
                for j, r in enumerate(returns):
                    risk[i, j] = 1000 * a * abs(r) * np.random.normal(1, 0.1) # VaR proxy
            
            path = renderer.risk_landscape(allocs, returns, risk, title="VAR Landscape (Allocation vs Vol)")
            
        else:
            raise HTTPException(status_code=400, detail="Unknown viz type")
            
        # Convert absolute path to URL relative to server root
        # Assuming we mount 'apps/desktop' as static root
        import os
        filename = os.path.basename(path)
        url = f"assets/3d/{filename}" # Check static mount
        
        return {"status": "ok", "path": path, "url": url}
        
    except Exception as e:
        print(f"3D Render Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────
# VIZ LAB API ROUTES
# ─────────────────────────────────────────────────────────

@app.get("/api/vizlab/brain")
def vizlab_brain():
    """
    Return ARIA module graph (nodes + edges) for the neural brain visualization.
    Includes live status booleans so the frontend can highlight active modules.
    """
    nodes = [
        {"id": "data",       "label": "Data Layer",    "type": "data",      "active": True},
        {"id": "indicators", "label": "Indicators",    "type": "analytics", "active": True},
        {"id": "market",     "label": "Market State",  "type": "analytics", "active": True},
        {"id": "features",   "label": "Features",      "type": "analytics", "active": True},
        {"id": "signal",     "label": "Signal Engine", "type": "engine",    "active": True},
        {"id": "ml",         "label": "ML Engine",     "type": "engine",    "active": False},
        {"id": "rl",         "label": "RL Agent",      "type": "engine",    "active": False},
        {"id": "risk",       "label": "Risk Engine",   "type": "risk",      "active": True},
        {"id": "mc",         "label": "Monte Carlo",   "type": "sim",       "active": True},
        {"id": "backtest",   "label": "Backtest",      "type": "eval",      "active": True},
        {"id": "exec",       "label": "Execution",     "type": "exec",      "active": True},
        {"id": "aria",       "label": "ARIA",          "type": "ai",        "active": True},
    ]
    edges = [
        {"from": "data",     "to": "indicators"}, {"from": "data",   "to": "market"},
        {"from": "data",     "to": "features"},   {"from": "indicators","to": "signal"},
        {"from": "market",   "to": "signal"},     {"from": "features", "to": "signal"},
        {"from": "signal",   "to": "ml"},         {"from": "signal",   "to": "rl"},
        {"from": "signal",   "to": "aria"},       {"from": "ml",       "to": "aria"},
        {"from": "rl",       "to": "aria"},       {"from": "risk",     "to": "aria"},
        {"from": "signal",   "to": "risk"},       {"from": "mc",       "to": "signal"},
        {"from": "mc",       "to": "aria"},       {"from": "backtest", "to": "aria"},
        {"from": "exec",     "to": "aria"},       {"from": "exec",     "to": "backtest"},
    ]
    return {"nodes": nodes, "edges": edges, "version": "Atlas v0.6.0-alpha"}


@app.get("/api/vizlab/regime/{ticker}")
def vizlab_regime(ticker: str):
    """
    Return current market regime + stats for a ticker.
    Used by particle viz to select shape (BULL/BEAR/SIDEWAYS/VOLATILE/TRENDING).
    """
    try:
        import yfinance as yf
        import numpy as np
        ticker = ticker.upper().strip()
        hist = yf.Ticker(ticker).history(period="3mo", auto_adjust=True)
        if hist.empty:
            raise ValueError("No data")
        closes = hist["Close"].values
        returns = np.diff(closes) / closes[:-1]
        vol     = float(np.std(returns) * np.sqrt(252))
        trend   = float((closes[-1] - closes[0]) / closes[0])
        adx_proxy = abs(trend) / (vol + 1e-6)

        if vol > 0.40:
            regime = "VOLATILE"
        elif adx_proxy > 0.7 and trend > 0:
            regime = "TRENDING"
        elif adx_proxy > 0.7 and trend < 0:
            regime = "BEAR"
        elif abs(trend) < 0.03:
            regime = "SIDEWAYS"
        else:
            regime = "BULL" if trend > 0 else "BEAR"

        return {
            "ticker": ticker,
            "regime": regime,
            "trend_pct": round(trend * 100, 2),
            "annual_vol_pct": round(vol * 100, 2),
            "adx_proxy": round(adx_proxy, 3),
            "last_price": round(float(closes[-1]), 2),
        }
    except Exception as e:
        return {"ticker": ticker, "regime": "SIDEWAYS", "error": str(e)}


@app.get("/api/vizlab/market_graph")
def vizlab_market_graph():
    """
    Return correlation-based market graph for the Force Graph visualization.
    Nodes = tickers, edges = correlation pairs above threshold.
    """
    try:
        import yfinance as yf
        import numpy as np
        import pandas as pd

        tickers = ["SPY","QQQ","AAPL","MSFT","NVDA","JPM","GS","XOM","GLD","BTC-USD"]
        data = {}
        for t in tickers:
            try:
                hist = yf.Ticker(t).history(period="3mo", auto_adjust=True)
                if not hist.empty:
                    data[t.replace("-USD","")] = hist["Close"].pct_change().dropna()
            except Exception:
                pass

        if not data:
            raise ValueError("No data")

        df = pd.DataFrame(data).dropna()
        corr = df.corr()

        nodes = []
        sector_map = {
            "SPY":"ETF","QQQ":"ETF","AAPL":"Tech","MSFT":"Tech",
            "NVDA":"Tech","JPM":"Finance","GS":"Finance",
            "XOM":"Energy","GLD":"Commodity","BTC":"Crypto"
        }
        colors = {"ETF":"#00ff88","Tech":"#4488ff","Finance":"#ff8800","Energy":"#ff4444","Commodity":"#ffdd44","Crypto":"#ffaa00"}
        for t in corr.columns:
            s = sector_map.get(t, "Other")
            nodes.append({"id": t, "sector": s, "color": colors.get(s,"#aaa")})

        edges = []
        threshold = 0.35
        for i, a in enumerate(corr.columns):
            for j, b in enumerate(corr.columns):
                if j <= i: continue
                c = float(corr.loc[a, b])
                if abs(c) >= threshold:
                    edges.append({"from": a, "to": b, "corr": round(c, 3)})

        return {"nodes": nodes, "edges": edges, "n_days": len(df)}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


@app.get("/api/vizlab/montecarlo/{ticker}")
def vizlab_montecarlo(ticker: str, paths: int = 200, horizon: int = 252):
    """
    Run a GBM Monte Carlo for the given ticker.
    Returns path data for the animated Monte Carlo visualization.
    """
    try:
        import yfinance as yf
        import numpy as np

        ticker = ticker.upper().strip()
        hist = yf.Ticker(ticker).history(period="2y", auto_adjust=True)
        if hist.empty:
            raise ValueError("No data")

        closes = hist["Close"].values
        returns = np.diff(np.log(closes))
        mu    = float(np.mean(returns))
        sigma = float(np.std(returns))
        S0    = float(closes[-1])

        # GBM paths (downsampled to 60 points for transfer efficiency)
        STEPS = min(horizon, 252)
        SAMPLE = 60
        out_paths = []
        for _ in range(min(paths, 300)):
            path = [S0]
            price = S0
            for _ in range(STEPS):
                dW = np.random.normal(0, 1)
                price *= np.exp((mu - 0.5 * sigma**2) + sigma * dW)
                path.append(round(float(price), 2))
            # Downsample
            step = max(1, STEPS // SAMPLE)
            out_paths.append(path[::step][:SAMPLE])

        return {
            "ticker": ticker, "S0": S0, "mu_annual": round(mu*252*100, 2),
            "sigma_annual": round(sigma*np.sqrt(252)*100, 2),
            "paths": out_paths,
        }
    except Exception as e:
        return {"error": str(e), "paths": []}


@app.get("/api/vizlab/system_status")
def vizlab_system_status():
    """
    Return live system status for the ARIA brain + system pulse viz.
    """
    import time
    return {
        "timestamp": time.time(),
        "modules": dict(_SYSTEM_MODULE_FLAGS),
        "aria_model": os.getenv("ARIA_MODEL", "llama3.2:1b"),
        "uptime_note": "Atlas v0.6.0-alpha — Viz Lab online",
    }


# ==================== STRATEGY ANALYSIS API ====================

def _fetch_ohlcv(ticker: str, period: str = "6mo"):
    """Fetch OHLCV data from yfinance and return a capitalized-column DataFrame."""
    import yfinance as yf
    hist = yf.Ticker(ticker.upper()).history(period=period, auto_adjust=True)
    if hist.empty:
        return None
    # Ensure standard capitalized column names required by rule-based engines
    hist = hist[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return hist


def _add_sys_path():
    """Ensure the atlas Python package is importable inside server routes."""
    import sys
    from pathlib import Path
    pkg = str(Path(__file__).parent.parent.parent / "python" / "src")
    if pkg not in sys.path:
        sys.path.insert(0, pkg)


def _generate_synthetic_ohlcv(ticker: str = "SYN", n: int = 252, seed: int = None):
    """
    Generate a realistic synthetic OHLCV DataFrame locally (no internet required).
    Uses a GBM price process + realistic OHLC spreads + volume.
    Returns a DataFrame with capitalized columns matching _fetch_ohlcv output.
    """
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed if seed is not None else abs(hash(ticker)) % (2**31))

    # GBM parameters — vary slightly by ticker name hash for diversity
    mu    = 0.0003 + (abs(hash(ticker)) % 20) * 0.00001
    sigma = 0.015  + (abs(hash(ticker)) % 10) * 0.001
    price = 100.0  + (abs(hash(ticker)) % 400)

    # Normalize timestamp to midnight so synthetic series from different tickers align on index.
    dates  = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="B")
    closes = [price]
    for _ in range(n - 1):
        ret = rng.normal(mu - 0.5 * sigma**2, sigma)
        closes.append(closes[-1] * np.exp(ret))

    closes = np.array(closes)
    # OHLC spread: high/low are ±(0.3..1.5%) from close, open ≈ prev close + noise
    spread = rng.uniform(0.003, 0.015, n)
    highs  = closes * (1 + spread)
    lows   = closes * (1 - spread)
    opens  = np.concatenate([[closes[0]], closes[:-1]]) * rng.uniform(0.997, 1.003, n)
    opens  = np.clip(opens, lows, highs)
    vols   = (rng.lognormal(12, 0.8, n)).astype(int)

    df = pd.DataFrame({
        "Open":   opens,
        "High":   highs,
        "Low":    lows,
        "Close":  closes,
        "Volume": vols,
    }, index=dates)
    return df


def _fetch_ohlcv_local(ticker: str, period: str = "1y"):
    """
    Fetch OHLCV data — tries yfinance first, falls back to local synthetic data.
    Always returns a capitalized-column DataFrame (never None).
    """
    # Map period string to approximate bar count
    period_bars = {
        "1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260,
    }
    n_bars = period_bars.get(period, 252)

    # Try yfinance (network optional)
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker.upper()).history(period=period, auto_adjust=True)
        if not hist.empty:
            return hist[["Open", "High", "Low", "Close", "Volume"]].dropna(), False
    except Exception:
        pass

    # Local fallback — deterministic synthetic data seeded by ticker name
    return _generate_synthetic_ohlcv(ticker, n=n_bars, seed=abs(hash(ticker)) % (2**31)), True


def _parse_ticker_list(tickers: List[str] | str) -> List[str]:
    """Normalize ticker input and keep first-seen order."""
    if isinstance(tickers, str):
        raw = [part.strip().upper() for part in tickers.replace(";", ",").split(",")]
    else:
        raw = [str(part).strip().upper() for part in tickers]

    cleaned: List[str] = []
    seen: set[str] = set()
    for symbol in raw:
        if not symbol or symbol in seen:
            continue
        cleaned.append(symbol)
        seen.add(symbol)
    return cleaned


def _to_lower_ohlcv(df):
    """Convert Open/High/Low/Close/Volume columns to lowercase equivalents."""
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    return df.rename(columns=rename_map).copy()


def _load_ohlcv_bundle(tickers: List[str], period: str = "1y") -> tuple[Dict[str, Any], Dict[str, bool]]:
    """Fetch OHLCV for multiple tickers with local synthetic fallback."""
    ohlcv_map: Dict[str, Any] = {}
    synthetic_map: Dict[str, bool] = {}
    for symbol in tickers:
        hist, is_synthetic = _fetch_ohlcv_local(symbol, period=period)
        if hist is None or hist.empty:
            continue
        ohlcv_map[symbol] = _to_lower_ohlcv(hist)
        synthetic_map[symbol] = bool(is_synthetic)
    return ohlcv_map, synthetic_map


def _resolve_weights(tickers: List[str], weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Build validated, normalized weights aligned to ticker order."""
    if not tickers:
        raise ValueError("No tickers provided")

    if not weights:
        equal = 1.0 / len(tickers)
        return {symbol: equal for symbol in tickers}

    mapped = {str(k).strip().upper(): float(v) for k, v in weights.items()}
    aligned: Dict[str, float] = {}
    for symbol in tickers:
        value = float(mapped.get(symbol, 0.0))
        if value < 0:
            raise ValueError(f"Negative weight not allowed for {symbol}: {value}")
        aligned[symbol] = value

    total = float(sum(aligned.values()))
    if total <= 0:
        raise ValueError("Weight sum must be positive")
    return {symbol: value / total for symbol, value in aligned.items()}


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _downsample_series(values: List[float], max_points: int = 120) -> List[float]:
    """Downsample a long series for API payload efficiency."""
    if not values:
        return []
    if len(values) <= max_points:
        return [float(v) for v in values]
    step = max(1, len(values) // max_points)
    return [float(values[i]) for i in range(0, len(values), step)]


@app.get("/api/market-state/{ticker}")
def api_market_state(ticker: str, period: str = "1y", adx_threshold: float = 25.0):
    """
    Compute market-state snapshot for a ticker:
    - regime detection
    - volatility regime/forecast
    - market internals
    - sentiment score
    """
    try:
        _add_sys_path()
        import numpy as np

        from atlas.market_state import (
            MarketInternals,
            RegimeDetector,
            SentimentAnalyzer,
            VolatilityRegime,
        )

        symbol = ticker.strip().upper()
        ohlcv, is_synthetic = _fetch_ohlcv_local(symbol, period=period)
        if ohlcv is None or ohlcv.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        if len(ohlcv) < 20:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 20 bars for market-state analysis, got {len(ohlcv)}",
            )

        def _safe_float(value):
            if value is None:
                return None
            try:
                if np.isnan(value):
                    return None
            except Exception:
                pass
            try:
                return float(value)
            except Exception:
                return None

        regime = RegimeDetector(adx_threshold=adx_threshold, lookback=min(20, len(ohlcv))).detect(ohlcv)
        vol_detector = VolatilityRegime(lookback=max(20, min(252, len(ohlcv))))
        vol_regime = vol_detector.classify(ohlcv)
        vol_forecast = vol_detector.get_volatility_forecast(ohlcv, horizon=5)
        internals = MarketInternals().calculate(ohlcv)
        sentiment = SentimentAnalyzer().analyze(ohlcv)

        return {
            "ticker": symbol,
            "period": period,
            "n_bars": int(len(ohlcv)),
            "synthetic": bool(is_synthetic),
            "regime": {
                "name": regime.regime,
                "confidence": _safe_float(regime.confidence),
                "timestamp": regime.timestamp.isoformat() if hasattr(regime.timestamp, "isoformat") else str(regime.timestamp),
                "metrics": {k: _safe_float(v) for k, v in regime.metrics.items()},
            },
            "volatility": {
                "regime": vol_regime,
                "forecast_annualized": _safe_float(vol_forecast),
            },
            "internals": {k: _safe_float(v) for k, v in internals.items()},
            "sentiment": {
                "score": _safe_float(sentiment.score),
                "confidence": _safe_float(sentiment.confidence),
                "source": sentiment.source,
                "components": {k: _safe_float(v) for k, v in sentiment.components.items()},
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Market-state API error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/summary/{ticker}")
def analytics_summary(ticker: str, period: str = "1y", window: int = 21):
    """
    Single-ticker analytics snapshot using recovered analytics modules.

    Returns:
    - return statistics (log + simple)
    - annualized volatility
    - drawdown summary
    - Sharpe / Sortino / Calmar
    - historical VaR/CVaR
    """
    try:
        _add_sys_path()
        import numpy as np

        from atlas.analytics.returns import log_returns, simple_returns
        from atlas.analytics.risk_metrics import (
            calmar_ratio,
            drawdown_summary,
            historical_var,
            sharpe_ratio,
            sortino_ratio,
        )
        from atlas.analytics.volatility import historical_volatility, rolling_volatility

        symbol = ticker.strip().upper()
        cache_key = f"analytics:summary:{symbol}:{period}:{window}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        hist, is_synthetic = _fetch_ohlcv_local(symbol, period=period)
        if hist is None or hist.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if len(hist) < 40:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 40 bars for analytics summary, got {len(hist)}",
            )

        df = _to_lower_ohlcv(hist)
        effective_window = _clamp_int(window, 5, max(5, len(df) - 1))

        log_ret = log_returns(df, column="close")
        simple_ret = simple_returns(df, column="close")
        rolling_vol = rolling_volatility(df, window=effective_window, column="close")

        latest_vol = None
        rolling_non_null = rolling_vol.dropna()
        if not rolling_non_null.empty:
            latest_vol = float(rolling_non_null.iloc[-1])

        daily_risk_free = 0.04 / 252.0
        result = {
            "ticker": symbol,
            "period": period,
            "n_bars": int(len(df)),
            "synthetic": bool(is_synthetic),
            "price": {
                "last": float(df["close"].iloc[-1]),
                "change_pct": float((df["close"].iloc[-1] / df["close"].iloc[0] - 1.0) * 100.0),
            },
            "returns": {
                "log": {
                    "mean": float(log_ret.mean()),
                    "std": float(log_ret.std()),
                    "last": float(log_ret.iloc[-1]),
                },
                "simple": {
                    "mean": float(simple_ret.mean()),
                    "std": float(simple_ret.std()),
                    "last": float(simple_ret.iloc[-1]),
                },
            },
            "volatility": {
                "historical_annualized": float(historical_volatility(df, column="close", annualize=True)),
                "rolling_window": int(effective_window),
                "rolling_latest": latest_vol,
            },
            "risk": {
                "drawdown": drawdown_summary(simple_ret),
                "sharpe": float(sharpe_ratio(simple_ret, risk_free_rate=daily_risk_free)),
                "sortino": float(sortino_ratio(simple_ret, risk_free_rate=daily_risk_free)),
                "calmar": float(calmar_ratio(simple_ret)),
                "historical_var": historical_var(simple_ret, confidence=0.95, horizon_days=1),
            },
        }

        result = _json_safe(result)
        _cache_set(cache_key, result, ttl=120)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analytics summary error [%s]: %s", ticker, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/correlation")
def analytics_correlation(
    tickers: str = "AAPL,MSFT,SPY",
    period: str = "1y",
    return_method: str = "log",
    window: int = 63,
):
    """
    Multi-asset correlation endpoint powered by recovered analytics modules.
    """
    try:
        _add_sys_path()
        import pandas as pd

        from atlas.analytics.correlation import heatmap_data, rolling_correlation, static_correlation
        from atlas.analytics.returns import returns_matrix

        symbols = _parse_ticker_list(tickers)
        if len(symbols) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers")
        symbols = symbols[:20]

        method = return_method.strip().lower()
        if method not in {"log", "simple"}:
            raise HTTPException(status_code=400, detail="return_method must be 'log' or 'simple'")

        cache_key = f"analytics:corr:{','.join(symbols)}:{period}:{method}:{window}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        ohlcv_map, synthetic_map = _load_ohlcv_bundle(symbols, period=period)
        if len(ohlcv_map) < 2:
            raise HTTPException(status_code=404, detail="Not enough ticker data for correlation analysis")

        returns_df = returns_matrix(ohlcv_map, method=method)
        if returns_df.empty or len(returns_df) < 20:
            raise HTTPException(status_code=400, detail="Need at least 20 aligned return observations")

        corr_matrix = static_correlation(
            returns_df,
            method="pearson",
            min_periods=min(30, max(10, len(returns_df))),
        )
        rolling_window = _clamp_int(window, 10, max(10, len(returns_df)))
        rolling_df = rolling_correlation(returns_df, window=rolling_window)

        rolling_latest: Dict[str, float] = {}
        if not rolling_df.empty:
            for col in rolling_df.columns:
                ser = rolling_df[col].dropna()
                if not ser.empty:
                    rolling_latest[str(col)] = float(ser.iloc[-1])

        pair_strength: List[Dict[str, float]] = []
        cols = list(corr_matrix.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                val = corr_matrix.loc[a, b]
                if pd.notna(val):
                    pair_strength.append(
                        {
                            "pair": f"{a}/{b}",
                            "correlation": float(val),
                            "abs_correlation": float(abs(val)),
                        }
                    )
        pair_strength.sort(key=lambda x: x["abs_correlation"], reverse=True)

        result = {
            "tickers_requested": symbols,
            "tickers_used": list(returns_df.columns),
            "period": period,
            "return_method": method,
            "observations": int(len(returns_df)),
            "synthetic": synthetic_map,
            "matrix": corr_matrix.round(4).to_dict(),
            "heatmap": heatmap_data(corr_matrix),
            "rolling_window": int(rolling_window),
            "rolling_latest": rolling_latest,
            "top_pairs": pair_strength[:12],
        }

        result = _json_safe(result)
        _cache_set(cache_key, result, ttl=180)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analytics correlation error [%s]: %s", tickers, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/portfolio/assess")
def portfolio_risk_assess(req: PortfolioRiskRequest):
    """
    Portfolio risk endpoint backed by atlas.risk.portfolio_risk.PortfolioRiskManager.
    """
    try:
        _add_sys_path()
        from atlas.analytics.returns import returns_matrix
        from atlas.risk.portfolio_risk import PortfolioRiskManager

        symbols = _parse_ticker_list(req.tickers)
        if len(symbols) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers")

        method = (req.return_method or "log").strip().lower()
        if method not in {"log", "simple"}:
            raise HTTPException(status_code=400, detail="return_method must be 'log' or 'simple'")

        key_payload = {
            "tickers": symbols,
            "weights": req.weights or {},
            "period": req.period,
            "return_method": method,
            "confidence": float(req.confidence),
            "risk_free_rate": float(req.risk_free_rate),
            "horizon_days": int(req.horizon_days),
            "run_stress": bool(req.run_stress),
        }
        cache_key = "risk:portfolio:" + json.dumps(key_payload, sort_keys=True)
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        ohlcv_map, synthetic_map = _load_ohlcv_bundle(symbols, period=req.period)
        if len(ohlcv_map) < 2:
            raise HTTPException(status_code=404, detail="Not enough ticker data for portfolio risk")

        ret_df = returns_matrix(ohlcv_map, method=method)
        if ret_df.empty or len(ret_df) < 20:
            raise HTTPException(status_code=400, detail="Need at least 20 aligned return observations")

        aligned_tickers = [symbol for symbol in symbols if symbol in ret_df.columns]
        weights = _resolve_weights(aligned_tickers, req.weights)

        manager = PortfolioRiskManager()
        result_obj = manager.assess(
            returns_df=ret_df[aligned_tickers],
            weights=weights,
            confidence=float(req.confidence),
            risk_free_rate=float(req.risk_free_rate) / 252.0,
            horizon_days=_clamp_int(req.horizon_days, 1, 252),
            run_stress=bool(req.run_stress),
        )

        payload = {
            "tickers": aligned_tickers,
            "period": req.period,
            "return_method": method,
            "observations": int(len(ret_df)),
            "synthetic": synthetic_map,
            "weights": weights,
            "risk": result_obj.to_dict(),
        }
        payload = _json_safe(payload)
        _cache_set(cache_key, payload, ttl=180)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Portfolio risk error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/montecarlo/portfolio/simulate")
def portfolio_montecarlo_simulate(req: PortfolioMonteCarloRequest):
    """
    Correlated multi-asset Monte Carlo simulation endpoint.
    """
    try:
        _add_sys_path()
        import numpy as np

        from atlas.analytics.returns import returns_matrix
        from atlas.monte_carlo.multi_asset import MultiAssetSimulator, PortfolioSimConfig
        from atlas.monte_carlo.simulator import VarianceReduction

        symbols = _parse_ticker_list(req.tickers)
        if len(symbols) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers")

        method = (req.return_method or "log").strip().lower()
        if method not in {"log", "simple"}:
            raise HTTPException(status_code=400, detail="return_method must be 'log' or 'simple'")

        n_paths = _clamp_int(req.n_paths, 200, 20000)
        n_steps = _clamp_int(req.horizon_days, 20, 756)

        key_payload = {
            "tickers": symbols,
            "weights": req.weights or {},
            "period": req.period,
            "return_method": method,
            "n_paths": n_paths,
            "horizon_days": n_steps,
            "seed": req.seed,
        }
        cache_key = "mc:portfolio:" + json.dumps(key_payload, sort_keys=True)
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        ohlcv_map, synthetic_map = _load_ohlcv_bundle(symbols, period=req.period)
        if len(ohlcv_map) < 2:
            raise HTTPException(status_code=404, detail="Not enough ticker data for simulation")

        ret_df = returns_matrix(ohlcv_map, method=method)
        if ret_df.empty or len(ret_df) < 20:
            raise HTTPException(status_code=400, detail="Need at least 20 aligned return observations")

        aligned_tickers = [symbol for symbol in symbols if symbol in ret_df.columns]
        weights = _resolve_weights(aligned_tickers, req.weights)

        config = PortfolioSimConfig(
            n_paths=n_paths,
            n_steps=n_steps,
            dt=1.0 / 252.0,
            variance_reduction=VarianceReduction.ANTITHETIC,
            seed=req.seed,
        )

        simulator = MultiAssetSimulator()
        results = simulator.simulate_from_returns(ret_df[aligned_tickers], weights, config)

        final_values = results.portfolio_paths[:, -1]
        p05 = results.percentiles.get(0.05)
        p50 = results.percentiles.get(0.50)
        p95 = results.percentiles.get(0.95)

        payload = {
            "tickers": results.tickers,
            "period": req.period,
            "return_method": method,
            "observations": int(len(ret_df)),
            "synthetic": synthetic_map,
            "weights": results.weights,
            "config": {
                "n_paths": int(results.config.n_paths),
                "n_steps": int(results.config.n_steps),
                "dt": float(results.config.dt),
                "variance_reduction": results.config.variance_reduction.value,
                "seed": results.config.seed,
            },
            "terminal_distribution": {
                "mean_final_value": float(np.mean(final_values)),
                "median_final_value": float(np.median(final_values)),
                "p05_final_value": float(np.percentile(final_values, 5)),
                "p95_final_value": float(np.percentile(final_values, 95)),
                "expected_return": float(np.mean(final_values - 1.0)),
                "probability_of_loss": float((final_values < 1.0).mean()),
            },
            "risk_metrics": results.risk_metrics,
            "correlation_matrix": results.corr_matrix.round(4).to_dict(),
            "summary_table": results.summary().to_dict(orient="records"),
            "percentile_paths": {
                "p05": _downsample_series(p05.tolist() if p05 is not None else [], max_points=140),
                "p50": _downsample_series(p50.tolist() if p50 is not None else [], max_points=140),
                "p95": _downsample_series(p95.tolist() if p95 is not None else [], max_points=140),
            },
        }
        payload = _json_safe(payload)
        _cache_set(cache_key, payload, ttl=180)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Portfolio Monte Carlo error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/analyze/{ticker}")
def strategy_analyze(ticker: str, period: str = "6mo"):
    """
    Run the MultiStrategy consensus engine on a ticker and return per-engine signals
    plus the overall consensus, confidence score, and recommendation.

    Query params:
        period  — yfinance period string (default '6mo')
    """
    try:
        _add_sys_path()
        from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine

        symbol = ticker.strip().upper()
        cache_key = f"strategy:analyze:{symbol}:{period}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        hist, is_synthetic = _fetch_ohlcv_local(symbol, period)
        if hist is None or len(hist) < 60:
            raise HTTPException(status_code=404, detail=f"Not enough data for {symbol}")

        engine = MultiStrategyEngine(min_confidence=0.40, require_agreement=2)
        ctx    = {"symbol": symbol}

        # Consensus signal
        consensus_sigs = engine.analyze(hist, ctx)

        # Per-engine individual signals
        ind = engine.get_individual_signals(hist, ctx)
        individual = {}
        for key, sigs in ind.items():
            if sigs:
                s = sigs[0]
                individual[key] = {
                    "action":     s.action,
                    "confidence": round(s.confidence, 3),
                    "reason":     s.metadata.get("reason", ""),
                }
            else:
                individual[key] = {"action": "HOLD", "confidence": 0.50, "reason": "No signal"}

        consensus = None
        if consensus_sigs:
            cs = consensus_sigs[0]
            consensus = {
                "action":     cs.action,
                "confidence": round(cs.confidence, 3),
                "reason":     cs.metadata.get("reason", ""),
                "engines":    cs.metadata.get("engines", {}),
                "buy_weight":  cs.metadata.get("buy_weight", 0),
                "sell_weight": cs.metadata.get("sell_weight", 0),
                "net_score":   cs.metadata.get("net_score", 0),
                "agreement":   cs.metadata.get("agreement", 0),
            }
        else:
            consensus = {
                "action": "HOLD", "confidence": 0.50,
                "reason": "No consensus — engines disagree or confidence too low",
                "engines": {k: v.get("action", "HOLD") for k, v in individual.items()},
                "buy_weight": 0, "sell_weight": 0, "net_score": 0, "agreement": 0,
            }

        # ── ML Engine Signals (injected when trained models exist) ─────────
        ml_individual: Dict[str, Any] = {}
        try:
            import pickle
            from atlas.core_intelligence.engines.ml.ml_suite import FeaturePipeline

            hist_norm = hist.copy()
            hist_norm.columns = [c.lower() for c in hist_norm.columns]
            pipeline   = FeaturePipeline(lookback=20, forecast_horizon=5)
            X_ml, _, _ = pipeline.prepare(hist_norm, label_method="direction")

            for ml_key in ("ml_xgboost", "ml_rf"):
                mpath = _ml_model_path(symbol, ml_key)
                if mpath.exists():
                    try:
                        with open(mpath, "rb") as f:
                            ml_eng = pickle.load(f)
                        proba = ml_eng.predict_proba(X_ml[-1:])   # last row
                        # proba shape: (1, n_classes) — class 0=SELL, 1=HOLD, 2=BUY (direction)
                        if proba is not None and len(proba) > 0:
                            p = proba[0]
                            if len(p) == 3:
                                sell_p, hold_p, buy_p = float(p[0]), float(p[1]), float(p[2])
                            elif len(p) == 2:
                                sell_p, buy_p = float(p[0]), float(p[1])
                                hold_p = 0.0
                            else:
                                sell_p, hold_p, buy_p = 0.0, 1.0, 0.0

                            if buy_p >= max(sell_p, hold_p) and buy_p > 0.45:
                                ml_action, ml_conf = "BUY",  round(buy_p, 3)
                            elif sell_p >= max(buy_p, hold_p) and sell_p > 0.45:
                                ml_action, ml_conf = "SELL", round(sell_p, 3)
                            else:
                                ml_action, ml_conf = "HOLD", round(hold_p if hold_p else 0.5, 3)

                            ml_individual[ml_key] = {
                                "action":     ml_action,
                                "confidence": ml_conf,
                                "reason":     f"ML {ml_key.split('_')[-1].upper()} (p_buy={buy_p:.2f}, p_sell={sell_p:.2f})",
                            }
                    except Exception as ml_e:
                        logger.debug("ML inference %s: %s", ml_key, ml_e)
        except Exception as ml_import_e:
            logger.debug("ML pipeline unavailable: %s", ml_import_e)

        # Merge ML signals into individual (ML signals don't override rule-based)
        individual.update(ml_individual)

        # Recent price info
        last_close = round(float(hist["Close"].iloc[-1]), 2)
        ret_5d     = round(float((hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) * 100), 2)

        # ── Indicator diagnostics (always computed, shows state even on HOLD) ──
        closes = hist["Close"]
        try:
            # RSI-14
            delta  = closes.diff()
            gain   = delta.clip(lower=0).rolling(14).mean()
            loss   = (-delta.clip(upper=0)).rolling(14).mean()
            rs     = gain / (loss + 1e-10)
            rsi_14 = round(float(100 - 100 / (1 + rs.iloc[-1])), 1)
        except Exception:
            rsi_14 = None

        try:
            # MACD histogram
            ema12 = closes.ewm(span=12, adjust=False).mean()
            ema26 = closes.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_l  = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist_val = round(float(macd_line.iloc[-1] - signal_l.iloc[-1]), 4)
            macd_val      = round(float(macd_line.iloc[-1]), 4)
        except Exception:
            macd_hist_val = None
            macd_val      = None

        try:
            # SMA spread: (SMA20 - SMA50) / SMA50 * 100
            sma20 = closes.rolling(20).mean()
            sma50 = closes.rolling(50).mean()
            sma_spread_pct = round(float((sma20.iloc[-1] - sma50.iloc[-1]) / (sma50.iloc[-1] + 1e-10) * 100), 2)
        except Exception:
            sma_spread_pct = None

        try:
            # ATR-14 as % of price
            hi, lo, cl = hist["High"], hist["Low"], closes
            tr  = (hi - lo).combine(abs(hi - cl.shift()), max).combine(abs(lo - cl.shift()), max)
            atr = tr.rolling(14).mean()
            atr_pct = round(float(atr.iloc[-1] / (last_close + 1e-10) * 100), 2)
        except Exception:
            atr_pct = None

        diagnostics = {
            "rsi_14":        rsi_14,
            "macd":          macd_val,
            "macd_hist":     macd_hist_val,
            "sma_spread_pct": sma_spread_pct,
            "atr_pct":       atr_pct,
            "rsi_zone":      ("oversold" if rsi_14 and rsi_14 < 35 else
                              "overbought" if rsi_14 and rsi_14 > 65 else "neutral"),
            "macd_bias":     ("bullish" if macd_hist_val and macd_hist_val > 0 else
                              "bearish" if macd_hist_val and macd_hist_val < 0 else "flat"),
            "sma_bias":      ("bullish" if sma_spread_pct and sma_spread_pct > 0 else
                              "bearish" if sma_spread_pct and sma_spread_pct < 0 else "flat"),
        }

        result = {
            "ticker":      symbol,
            "period":      period,
            "last_close":  last_close,
            "return_5d":   ret_5d,
            "signal":      consensus["action"],      # top-level shortcut
            "confidence":  consensus["confidence"],  # top-level shortcut
            "consensus":   consensus,
            "individual":  individual,
            "diagnostics": diagnostics,
            "ml_signals":  len(ml_individual),       # how many ML engines contributed
            "bars_used":   len(hist),
            "synthetic":   bool(is_synthetic),
        }
        result = _json_safe(result)
        _cache_set(cache_key, result, ttl=120)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/engines")
def strategy_engines(ticker: str = "AAPL"):
    """
    List all available strategy engines, their types, weights, and training status.
    Pass ?ticker=AAPL to check ML model status for a specific ticker.
    """
    symbol = ticker.strip().upper()
    ml_stat = _ml_model_status(symbol)

    return {
        "ticker": symbol,
        "rule_based": [
            {"name": "sma",        "label": "SMA Crossover",       "weight": 0.15, "type": "trend",       "status": "active"},
            {"name": "rsi_mr",     "label": "RSI Mean Reversion",   "weight": 0.25, "type": "contrarian",  "status": "active"},
            {"name": "macd",       "label": "MACD Multi-Signal",    "weight": 0.25, "type": "momentum",    "status": "active"},
            {"name": "bb_squeeze", "label": "BB Squeeze Breakout",  "weight": 0.20, "type": "volatility",  "status": "active"},
            {"name": "momentum",   "label": "Time-Series Momentum", "weight": 0.15, "type": "momentum",    "status": "active"},
        ],
        "ml": [
            {**{"name": k, **v}} for k, v in ml_stat.items()
        ] + [
            {"name": "ml_lstm", "label": "LSTM", "weight": 0.20, "status": "untrained", "note": "requires PyTorch"},
        ],
        "rl": [
            {"name": "rl_dqn", "label": "DQN Agent", "weight": 0.25, "status": "untrained"},
        ],
        "train_endpoint": f"/api/ml/train/{symbol}",
    }


# ==================== ML ENGINE TRAINING ====================

_ML_MODEL_DIR = Path("data/models")
_ML_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _ml_model_path(ticker: str, engine: str) -> Path:
    return _ML_MODEL_DIR / f"{ticker.upper()}_{engine}.pkl"


def _ml_model_status(ticker: str) -> Dict[str, Any]:
    """Return training status for each ML engine for a given ticker."""
    engines = {
        "ml_xgboost": {"label": "XGBoost",      "weight": 0.25},
        "ml_rf":      {"label": "Random Forest", "weight": 0.15},
    }
    result = {}
    for key, meta in engines.items():
        path = _ml_model_path(ticker, key)
        if path.exists():
            age_s = int(time.time() - path.stat().st_mtime)
            result[key] = {**meta, "status": "trained", "age_seconds": age_s,
                           "model_path": str(path)}
        else:
            result[key] = {**meta, "status": "untrained", "model_path": str(path)}
    return result


@app.post("/api/ml/train/{ticker}")
async def ml_train(ticker: str, period: str = "2y"):
    """
    Train XGBoost and RandomForest ML signal engines for a ticker.
    Models saved to data/models/{TICKER}_{engine}.pkl.
    Returns per-engine training metrics.
    """
    try:
        _add_sys_path()
        import pickle
        from atlas.core_intelligence.engines.ml.ml_suite import (
            XGBoostEngine, RandomForestEngine, FeaturePipeline,
        )

        symbol = ticker.strip().upper()
        hist, is_synthetic = _fetch_ohlcv_local(symbol, period=period)
        if hist is None or len(hist) < 80:
            raise HTTPException(status_code=404,
                detail=f"Need ≥80 bars to train ML engines; got {len(hist) if hist is not None else 0}")

        # Normalise column names for FeaturePipeline
        hist_norm = hist.copy()
        hist_norm.columns = [c.lower() for c in hist_norm.columns]
        hist_norm.index.name = "date"

        pipeline = FeaturePipeline(lookback=20, forecast_horizon=5)
        X, y, _ = pipeline.prepare(hist_norm, label_method="direction")
        if len(X) < 40:
            raise HTTPException(status_code=422,
                detail=f"Feature pipeline produced only {len(X)} samples; need ≥40")

        metrics: Dict[str, Any] = {}

        # ── XGBoost ─────────────────────────────────────────────────────
        try:
            xgb_engine = XGBoostEngine()
            xgb_engine.name = "ml_xgboost"
            xgb_engine.model_dir = _ML_MODEL_DIR
            m = xgb_engine.train(X, y)
            xgb_engine.is_trained = True
            path = _ml_model_path(symbol, "ml_xgboost")
            with open(path, "wb") as f:
                pickle.dump(xgb_engine, f)
            metrics["ml_xgboost"] = {**m, "status": "trained", "saved_to": str(path)}
        except Exception as e:
            metrics["ml_xgboost"] = {"status": "error", "error": str(e)}

        # ── Random Forest ────────────────────────────────────────────────
        try:
            rf_engine = RandomForestEngine()
            rf_engine.name = "ml_rf"
            rf_engine.model_dir = _ML_MODEL_DIR
            m = rf_engine.train(X, y)
            rf_engine.is_trained = True
            path = _ml_model_path(symbol, "ml_rf")
            with open(path, "wb") as f:
                pickle.dump(rf_engine, f)
            metrics["ml_rf"] = {**m, "status": "trained", "saved_to": str(path)}
        except Exception as e:
            metrics["ml_rf"] = {"status": "error", "error": str(e)}

        return {
            "ticker":    symbol,
            "period":    period,
            "n_samples": int(len(X)),
            "n_features": int(X.shape[1] if len(X.shape) > 1 else 1),
            "synthetic": bool(is_synthetic),
            "engines":   metrics,
            "label_method": "direction",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ML train error [%s]: %s", ticker, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/status")
async def ml_status(ticker: str = "AAPL"):
    """
    Return training status of all ML engines for a given ticker.
    Lists which models are saved, their age, and their paths.
    """
    symbol = ticker.strip().upper()
    status = _ml_model_status(symbol)
    trained_count = sum(1 for v in status.values() if v.get("status") == "trained")
    return {
        "ticker":        symbol,
        "model_dir":     str(_ML_MODEL_DIR),
        "engines":       status,
        "trained_count": trained_count,
        "total":         len(status),
        "summary":       f"{trained_count}/{len(status)} ML engines trained",
    }


@app.get("/api/strategy/backtest/{ticker}")
def strategy_backtest(ticker: str, period: str = "1y", initial_cash: float = 10000.0):
    """
    Quick walk-forward backtest of MultiStrategy on a ticker.
    Uses a simple signal-to-position rule:
      BUY → full long, SELL → flat, HOLD → keep position.
    Returns equity curve (sampled to 100 pts), total return, and Sharpe.
    """
    try:
        _add_sys_path()
        import numpy as np
        from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine

        symbol = ticker.strip().upper()
        cache_key = f"strategy:backtest:{symbol}:{period}:{round(float(initial_cash), 2)}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        hist, is_synthetic = _fetch_ohlcv_local(symbol, period)
        if hist is None or len(hist) < 80:
            raise HTTPException(status_code=404, detail=f"Not enough data for {symbol}")

        engine = MultiStrategyEngine(min_confidence=0.40, require_agreement=2)
        ctx    = {"symbol": symbol}

        # Walk-forward: start after 60-bar warm-up
        cash       = initial_cash
        shares     = 0.0
        equity_log = []
        trade_log  = []
        warm_up    = 60

        for i in range(warm_up, len(hist)):
            window = hist.iloc[:i]
            sigs   = engine.analyze(window, ctx)
            price  = float(hist["Close"].iloc[i])

            if sigs:
                action = sigs[0].action
                if action == "BUY" and shares == 0 and cash > 0:
                    shares = cash / price
                    cash   = 0.0
                    trade_log.append({"bar": i, "action": "BUY",  "price": round(price, 2)})
                elif action == "SELL" and shares > 0:
                    cash   = shares * price
                    shares = 0.0
                    trade_log.append({"bar": i, "action": "SELL", "price": round(price, 2)})

            equity = cash + shares * price
            equity_log.append(round(equity, 2))

        # Metrics
        eq_arr  = np.array(equity_log)
        ret     = round(float((eq_arr[-1] - initial_cash) / initial_cash * 100), 2)
        rets    = np.diff(eq_arr) / eq_arr[:-1]
        sharpe  = round(float(rets.mean() / (rets.std() + 1e-10) * np.sqrt(252)), 3)
        max_dd  = round(float(np.max((np.maximum.accumulate(eq_arr) - eq_arr) /
                               (np.maximum.accumulate(eq_arr) + 1e-10)) * 100), 2)

        # Downsample equity curve to ≤100 points
        step = max(1, len(equity_log) // 100)
        dates = [hist.index[warm_up + i * step].strftime("%Y-%m-%d")
                 for i in range(len(equity_log[::step]))]
        sampled = equity_log[::step]

        result = {
            "ticker":        symbol,
            "period":        period,
            "initial_cash":  initial_cash,
            "final_equity":  round(float(eq_arr[-1]), 2),
            "total_return":  ret,
            "sharpe":        sharpe,
            "max_drawdown":  max_dd,
            "n_trades":      len(trade_log),
            "equity_curve":  [{"date": d, "equity": e} for d, e in zip(dates, sampled)],
            "trades":        trade_log[-20:],   # last 20 trades
            "synthetic":     bool(is_synthetic),
        }
        result = _json_safe(result)
        _cache_set(cache_key, result, ttl=180)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CORRELATION PORTFOLIO API ====================

@app.get("/api/correlation/cluster")
def correlation_cluster(
    tickers: str = "AAPL,MSFT,GOOG,AMZN,NVDA,META,TSLA,JPM,GLD,TLT",
    n_clusters: int = 4,
    method: str = "hierarchical",
    period: str = "6mo",
):
    """
    Cluster a list of assets by return similarity.

    Query params:
        tickers     — comma-separated list of tickers
        n_clusters  — number of clusters (default 4)
        method      — 'hierarchical' or 'kmeans'
        period      — yfinance period (default '6mo')
    """
    try:
        _add_sys_path()
        import yfinance as yf
        import pandas as pd
        from atlas.correlation_portfolio.clustering.regime_clustering import RegimeClusterer

        syms = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if len(syms) < 3:
            raise HTTPException(status_code=400, detail="Need at least 3 tickers")

        # Fetch close prices
        raw = yf.download(syms, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"].dropna(how="all")
        else:
            prices = raw[["Close"]].dropna()

        prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8)).dropna()
        if prices.shape[1] < 2:
            raise HTTPException(status_code=404, detail="Not enough ticker data")

        clusterer = RegimeClusterer(n_clusters=n_clusters, method=method)
        result    = clusterer.cluster(prices)

        return {
            "n_clusters":        result.n_clusters,
            "labels":            result.labels,
            "cluster_members":   result.cluster_members,
            "intra_cluster_corr": result.intra_cluster_corr,
            "inter_cluster_corr": result.inter_cluster_corr,
            "silhouette_score":   result.silhouette_score,
            "pca_coords":        result.pca_coords,
            "tickers_used":      list(prices.columns),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/correlation/pairs")
def correlation_pairs(
    tickers: str = "AAPL,MSFT,GOOG,AMZN,NVDA",
    period: str = "2y",
    max_pairs: int = 10,
):
    """
    Find cointegrated pairs and return current z-score trading signals.

    Query params:
        tickers   — comma-separated
        period    — yfinance period (default '2y' — ADF needs long history)
        max_pairs — return at most this many pairs (default 10)
    """
    try:
        _add_sys_path()
        import yfinance as yf
        import pandas as pd
        from atlas.correlation_portfolio.pairs_trading.pairs_engine import PairsEngine

        syms = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if len(syms) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers")

        raw = yf.download(syms, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"].dropna(how="all")
        else:
            prices = raw.dropna()

        prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8)).dropna()

        engine = PairsEngine()
        pairs  = engine.find_pairs(prices)

        output = []
        for p in pairs[:max_pairs]:
            sigs = engine.generate_signals(prices, p)
            current_sig = sigs[-1] if sigs else None
            output.append({
                "ticker_a":    p.ticker_a,
                "ticker_b":    p.ticker_b,
                "correlation": round(p.correlation, 3),
                "half_life":   round(p.half_life, 1),
                "z_score":     round(p.current_zscore, 2) if hasattr(p, "current_zscore") else None,
                "signal": {
                    "type":       current_sig.signal_type if current_sig else "NONE",
                    "z_score":    round(current_sig.z_score, 2) if current_sig else None,
                    "confidence": round(current_sig.confidence, 3) if current_sig else None,
                } if current_sig else None,
            })

        return {
            "tickers_analyzed": list(prices.columns),
            "pairs_found":      len(pairs),
            "pairs":            output,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/correlation/structure")
def correlation_structure(
    tickers: str = "SPY,QQQ,IWM,GLD,TLT,VXX,USO,HYG,EEM,XLF",
    period: str = "1y",
    lookback: int = 60,
):
    """
    Analyze market structure: rolling correlation regime, diversification score,
    most central assets, and most correlated pairs.

    Query params:
        tickers   — comma-separated (default 10 diversified ETFs)
        period    — yfinance period (default '1y')
        lookback  — rolling window for regime detection (default 60 days)
    """
    try:
        _add_sys_path()
        import yfinance as yf
        import pandas as pd
        from atlas.correlation_portfolio.correlation.market_structure import MarketStructureAnalyzer

        syms = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if len(syms) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 tickers")

        raw = yf.download(syms, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"].dropna(how="all")
        else:
            prices = raw.dropna()

        prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8)).dropna()

        analyzer = MarketStructureAnalyzer(lookback=lookback)
        struct   = analyzer.analyze(prices)

        top_pairs = analyzer.top_correlated_pairs(prices, n=8)

        return {
            "tickers_used":       list(prices.columns),
            "current_regime":     struct.current_regime,
            "avg_correlation":    struct.avg_correlation,
            "diversification":    struct.diversification_score,
            "regime_history":     struct.regime_history[-30:],  # last 30 data points
            "centrality_rank":    struct.centrality_rank,
            "correlation_change": struct.correlation_change,
            "breakdown_detected": struct.breakdown_detected,
            "top_correlated_pairs": [
                {"a": a, "b": b, "corr": round(c, 3)} for a, b, c in top_pairs
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scenario/{session_id}/history")
def get_scenario_history(session_id: str):
    """Get full history of the session."""
    if session_id not in scenario_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = scenario_sessions[session_id]
    return {"history": session.get_full_history()}


# ==================== LIVE MARKET DATA & NEWS ====================

@app.get("/api/quote/{ticker}")
def get_quote(ticker: str):
    """
    Fetch latest quote for one ticker.
    Uses real Yahoo data first; falls back to deterministic local data if unavailable.
    Cached for 15 minutes.
    """
    try:
        symbol = ticker.strip().upper()
        if not symbol:
            raise HTTPException(status_code=400, detail="Ticker is required")

        # Cache check - 15-minute TTL
        _ck = f"quote:{symbol}"
        _hit = _cache_get(_ck)
        if _hit:
            return {**_hit, "_cached": True}

        is_synthetic = False
        hist = None

        try:
            import yfinance as yf

            t = yf.Ticker(symbol)
            hist = t.history(period="5d", interval="1d", auto_adjust=True)
            if hist is not None and not hist.empty:
                hist = hist[["Open", "High", "Low", "Close", "Volume"]].dropna()
        except Exception:
            hist = None

        if hist is None or hist.empty:
            hist, is_synthetic = _fetch_ohlcv_local(symbol, period="1mo")

        if hist is None or hist.empty:
            raise HTTPException(status_code=404, detail="Ticker not found or no data")

        closes = hist["Close"].dropna()
        price  = float(closes.iloc[-1])

        # Daily % change: today vs previous close
        change_pct = 0.0
        if len(closes) >= 2:
            prev  = float(closes.iloc[-2])
            change_pct = round((price - prev) / prev * 100, 2) if prev != 0 else 0.0

        result = {
            "ticker":     symbol,
            "price":      round(price, 2),
            "change_pct": change_pct,
            "source":     "synthetic_local" if is_synthetic else "yfinance",
            "synthetic":  bool(is_synthetic),
            "_cached":    False,
        }
        _cache_set(_ck, result, ttl=900)   # 15-min cache
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Quote Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market_data/{ticker}")
def get_market_data(ticker: str):
    """
    Fetch live market data and news for a ticker via yfinance. Cached 60 min.
    Returns: Current Price, OHLC Data (for charts), and News.
    """
    try:
        symbol = ticker.upper().strip()
        if not symbol:
            raise HTTPException(status_code=400, detail="Ticker is required")

        # Cache check - 60-minute TTL (OHLC history changes slowly)
        _ck = f"market_data:{symbol}"
        _hit = _cache_get(_ck)
        if _hit:
            return {**_hit, "_cached": True}

        is_synthetic = False
        hist = None
        t = None

        try:
            import yfinance as yf

            t = yf.Ticker(symbol)
            hist = t.history(period="1y", auto_adjust=True)
            if hist is not None and not hist.empty:
                hist = hist[["Open", "High", "Low", "Close", "Volume"]].dropna()
        except Exception:
            hist = None

        if hist is None or hist.empty:
            hist, is_synthetic = _fetch_ohlcv_local(symbol, period="1y")

        if hist is None or hist.empty:
            raise HTTPException(status_code=404, detail="Ticker not found or no data")

        # Format OHLC for Lightweight Charts
        # Needs: { time: '2023-01-01', open: 100, high: 105, low: 99, close: 102 }
        ohlc = []
        for date, row in hist.iterrows():
            ohlc.append({
                "time": date.strftime('%Y-%m-%d'),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
            
        # 3. Current Price
        current_price = float(hist['Close'].iloc[-1])
        
        formatted_news = []
        if not is_synthetic and t is not None:
            try:
                news = t.news
                if news:
                    for n in news:
                        formatted_news.append({
                            "title": n.get('title'),
                            "publisher": n.get('publisher'),
                            "link": n.get('link'),
                            "timestamp": n.get('providerPublishTime')
                        })
            except Exception:
                formatted_news = []
                
        result = {
            "ticker": symbol,
            "price": current_price,
            "ohlc": ohlc,
            "news": formatted_news,
            "source": "synthetic_local" if is_synthetic else "yfinance",
            "synthetic": bool(is_synthetic),
            "_cached": False,
        }
        _cache_set(_ck, result, ttl=3600)  # 60-min cache
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Market Data Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CHAOS / ENTROPY / VOL ADVANCED / FACTORS API ====================

@app.get("/api/chaos/{ticker}")
def get_chaos_features(ticker: str, period: str = "1y"):
    """
    Compute chaos & nonlinear features for a ticker (Fase 3.5).
    Works fully locally — falls back to synthetic data if network unavailable.
    Returns: Hurst, DFA, fractal dim, Lyapunov proxy, entropy metrics,
             vol metrics, regime label.
    """
    _add_sys_path()
    try:
        from atlas.core_intelligence.features.chaos import ChaosFeatureExtractor
        from atlas.core_intelligence.features.entropy import MarketEntropyAnalyzer
        from atlas.core_intelligence.features.volatility_advanced import RollingVolatilityEngine

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, period=period)
        if ohlcv is None or len(ohlcv) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {ticker}")

        prices = ohlcv["Close"]
        returns = prices.pct_change().dropna()

        # Chaos features
        chaos = ChaosFeatureExtractor()
        chaos_feats = chaos.compute(prices)
        chaos_regime = chaos.regime_label(chaos_feats)

        # Entropy features
        entropy_analyzer = MarketEntropyAnalyzer()
        entropy_feats = entropy_analyzer.analyze(prices)

        # Advanced volatility
        vol_engine = RollingVolatilityEngine()
        vol_feats = vol_engine.analyze(ohlcv)

        return {
            "ticker": ticker.upper(),
            "period": period,
            "n_bars": len(ohlcv),
            "synthetic": is_synthetic,
            "chaos": {k: round(float(v), 5) if isinstance(v, float) else v
                      for k, v in chaos_feats.items()},
            "chaos_regime": chaos_regime,
            "entropy": {k: round(float(v), 5) if isinstance(v, (float, int)) else v
                        for k, v in entropy_feats.items()},
            "volatility": {k: round(float(v), 5) if isinstance(v, (float, int)) else v
                           for k, v in vol_feats.items()},
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chaos API error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/volatility/{ticker}")
def get_advanced_volatility(ticker: str, period: str = "1y"):
    """
    Advanced volatility metrics: Yang-Zhang, Garman-Klass, Vol-of-Vol,
    vol regime, synthetic IV surface parameters.
    Works fully locally — falls back to synthetic data if network unavailable.
    """
    _add_sys_path()
    try:
        from atlas.core_intelligence.features.volatility_advanced import (
            RollingVolatilityEngine, garman_klass_vol, yang_zhang_vol, vol_regime_state,
        )

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, period=period)
        if ohlcv is None or len(ohlcv) < 30:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        engine = RollingVolatilityEngine()
        summary = engine.analyze(ohlcv)

        # Rolling panel (last 20 rows for chart sparkline)
        panel = engine.rolling_panel(ohlcv).tail(20)
        panel_dict = {col: [round(float(v), 5) for v in panel[col].fillna(0)]
                      for col in panel.columns}

        returns = ohlcv["Close"].pct_change().dropna()
        regime_series = vol_regime_state(returns)

        return {
            "ticker": ticker.upper(),
            "period": period,
            "n_bars": len(ohlcv),
            "synthetic": is_synthetic,
            "summary": {k: round(float(v), 5) if isinstance(v, (float, int)) else v
                        for k, v in summary.items()},
            "rolling_20d": panel_dict,
            "regime_latest": str(regime_series.iloc[-1]) if len(regime_series) > 0 else "UNKNOWN",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Volatility API error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factors/decompose")
def get_factor_decomposition(tickers: str = "AAPL,MSFT,NVDA,AMZN,JPM,XOM,GLD,SPY", period: str = "1y", n_factors: int = 5):
    """
    PCA factor decomposition for a portfolio of tickers.
    Works fully locally — builds synthetic returns matrix if network unavailable.
    Returns: factor loadings, explained variance, attribution per asset,
             factor timing signals.

    Query params:
        tickers   : comma-separated list (default 8 assets)
        period    : yfinance period string (default '1y')
        n_factors : number of PCA factors (1-10, default 5)
    """
    _add_sys_path()
    try:
        import pandas as pd
        from atlas.correlation_portfolio.factor_models import FactorModelEngine

        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if len(ticker_list) < 3:
            raise HTTPException(status_code=400, detail="Need at least 3 tickers")

        n_factors = max(1, min(n_factors, 10))
        is_synthetic = False

        # Try yfinance first for all tickers
        try:
            import yfinance as yf
            raw = yf.download(ticker_list, period=period, auto_adjust=True, progress=False)["Close"]
            if raw is None or (hasattr(raw, "empty") and raw.empty):
                raise ValueError("empty")
            if isinstance(raw, pd.Series):
                raw = raw.to_frame()
            returns = raw.pct_change().dropna()
            if len(returns) < 30:
                raise ValueError("too short")
        except Exception:
            # Full local fallback — build synthetic return matrix
            is_synthetic = True
            period_bars = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504}
            n_bars = period_bars.get(period, 252)
            frames = {}
            for tk in ticker_list:
                ohlcv = _generate_synthetic_ohlcv(tk, n=n_bars)
                frames[tk] = ohlcv["Close"].pct_change().dropna()
            returns = pd.DataFrame(frames).dropna()

        engine = FactorModelEngine(n_factors=n_factors)
        engine.fit(returns)
        summary = engine.summary()

        def _safe(obj):
            if isinstance(obj, float):
                return round(obj, 5)
            if isinstance(obj, dict):
                return {k: _safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_safe(v) for v in obj]
            return obj

        return {
            "tickers": ticker_list,
            "period": period,
            "n_bars": len(returns),
            "synthetic": is_synthetic,
            "decomposition": _safe(summary),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Factor decompose error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factors/attribution/{ticker}")
def get_factor_attribution(ticker: str, universe: str = "AAPL,MSFT,NVDA,AMZN,JPM,XOM,GLD,SPY", period: str = "1y"):
    """
    Factor attribution for a single ticker vs a universe.
    Works fully locally — uses synthetic data fallback when offline.
    Returns r², systematic vol, idiosyncratic vol, alpha, factor betas.
    """
    _add_sys_path()
    try:
        import pandas as pd
        from atlas.correlation_portfolio.factor_models import FactorModelEngine, factor_attribution

        tickers = list({t.strip().upper() for t in universe.split(",") if t.strip()} | {ticker.upper()})
        is_synthetic = False

        try:
            import yfinance as yf
            raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
            if isinstance(raw, pd.Series):
                raw = raw.to_frame()
            returns = raw.pct_change().dropna()
            if len(returns) < 30:
                raise ValueError("too short")
        except Exception:
            is_synthetic = True
            period_bars = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504}
            n_bars = period_bars.get(period, 252)
            frames = {}
            for tk in tickers:
                ohlcv = _generate_synthetic_ohlcv(tk, n=n_bars)
                frames[tk] = ohlcv["Close"].pct_change().dropna()
            returns = pd.DataFrame(frames).dropna()

        engine = FactorModelEngine(n_factors=5)
        result = engine.fit(returns)
        attr = engine.attribute(ticker.upper())

        return {
            "ticker": ticker.upper(),
            "period": period,
            "synthetic": is_synthetic,
            "attribution": {k: round(float(v), 5) if isinstance(v, (float, int)) else v
                            for k, v in attr.items() if k != "factor_betas"},
            "factor_betas": {k: round(float(v), 5) for k, v in attr.get("factor_betas", {}).items()},
            "timing_signals": result.get("timing", {}),
            "cumulative_var_explained": result.get("cumulative_var", 0.0),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Factor attribution error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discrepancy/{ticker}")
def get_discrepancy_analysis(ticker: str, period: str = "6mo"):
    """
    Enhanced discrepancy analysis: runs all 5 strategy engines and
    computes signal disagreement score, outlier engines, and recommended action.
    Works fully locally — falls back to synthetic data when offline.
    """
    _add_sys_path()
    try:
        from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine
        from atlas.discrepancy_analysis.discrepancy_analyzer import DiscrepancyAnalyzer

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, period=period)
        if ohlcv is None or len(ohlcv) < 60:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {ticker}")

        # Get signals from multi-strategy
        ms = MultiStrategyEngine()
        context = {"ticker": ticker, "capital": 100000}
        signals = ms.analyze(ohlcv, context)

        # Discrepancy analysis
        analyzer = DiscrepancyAnalyzer()
        engine_outputs = {sig.strategy_id: sig.action for sig in signals if hasattr(sig, 'strategy_id')}

        # Fallback: build from consensus result if strategy_id not set
        if not engine_outputs:
            consensus = ms.consensus(ohlcv, context)
            engine_outputs = consensus.get("per_engine", {})

        result = analyzer.analyze(engine_outputs) if engine_outputs else {
            "discrepancy_score": 0.0, "level": "LOW", "recommended_action": "HOLD", "outliers": []
        }

        # Also get the consensus
        consensus = ms.consensus(ohlcv, context)

        return {
            "ticker": ticker.upper(),
            "period": period,
            "n_bars": len(ohlcv),
            "synthetic": is_synthetic,
            "discrepancy": result,
            "consensus": {k: (round(float(v), 4) if isinstance(v, float) else v)
                          for k, v in consensus.items()
                          if k not in ("signals", "equity_curve")},
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Discrepancy API error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FASE 5 — SIGNAL COMPOSITOR ====================

@app.get("/api/signal/compose/{ticker}")
async def api_signal_compose(
    ticker:     str,
    capital:    float = 100_000.0,
    confidence: float = Query(0.65, ge=0.0, le=1.0),
):
    """
    Compose signals from all strategy engines into a single OrderProposal.
    Uses Kelly criterion + vol-scaling for position sizing.
    """
    try:
        _add_sys_path()
        from atlas.core_intelligence.signal_composition import (
            SignalCompositor, Signal, consensus_action, volatility_scalar,
        )
        from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, "6mo")

        # Gather individual signals from each sub-engine
        engine = MultiStrategyEngine()
        per_engine = engine.get_individual_signals(ohlcv, {"ticker": ticker})
        signals = []
        for name, sig_list in per_engine.items():
            if sig_list:
                s = sig_list[0]
                # Map BUY→LONG, SELL→SHORT, else HOLD
                action_map = {"BUY": "LONG", "SELL": "SHORT"}
                action = action_map.get(s.action, "HOLD")
                signals.append(Signal(
                    engine_id=name,
                    action=action,
                    confidence=float(getattr(s, "confidence", confidence)),
                    weight=1.0,
                ))
            else:
                signals.append(Signal(
                    engine_id=name,
                    action="HOLD",
                    confidence=0.3,
                    weight=1.0,
                ))

        compositor = SignalCompositor(capital=capital)
        proposal   = compositor.compose(signals, ohlcv=ohlcv)

        result = proposal.to_dict()
        result["ticker"]     = ticker
        result["synthetic"]  = is_synthetic
        result["scenarios"]  = compositor.size_scenarios(ohlcv=ohlcv)

        return result

    except Exception as e:
        logger.error(f"Signal compose error [{ticker}]: {e}")
        # Fallback: return a minimal HOLD proposal
        return {
            "ticker":        ticker,
            "action":        "HOLD",
            "size_pct":      0.0,
            "dollar_amount": 0.0,
            "confidence":    0.0,
            "kelly_fraction":0.0,
            "vol_scalar":    1.0,
            "engine_votes":  {},
            "reasoning":     f"Error during composition: {e}",
            "blocked":       False,
            "block_reason":  "",
            "scenarios":     [],
            "synthetic":     True,
        }


@app.get("/api/signal/scenarios")
async def api_signal_scenarios(
    ticker:   str   = Query("SPY"),
    capital:  float = Query(100_000.0),
):
    """Position sizing scenarios across confidence levels."""
    try:
        _add_sys_path()
        from atlas.core_intelligence.signal_composition import SignalCompositor

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, "3mo")
        compositor = SignalCompositor(capital=capital)
        return {
            "ticker":    ticker,
            "capital":   capital,
            "synthetic": is_synthetic,
            "scenarios": compositor.size_scenarios(ohlcv=ohlcv),
        }
    except Exception as e:
        return {"error": str(e), "scenarios": []}


# ==================== FASE 11 — ENHANCED BACKTEST ====================

@app.get("/api/backtest/enhanced/{ticker}")
async def api_backtest_enhanced(
    ticker:  str,
    capital: float = Query(10_000.0),
    walkforward: bool = Query(False),
):
    """
    Enhanced backtest with Sortino, Calmar, CAGR, trade log, and optional walk-forward.
    """
    try:
        _add_sys_path()
        from atlas.backtesting.runner import BacktestRunner

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, "2y")
        runner  = BacktestRunner(initial_capital=capital)

        # Generate signals from SMA fallback
        signals = runner._sma_signals(ohlcv)

        if walkforward:
            result = runner.walk_forward(ohlcv, signals, strategy="sma_crossover")
        else:
            result = runner.run(ohlcv, signals, strategy="sma_crossover")

        result["ticker"]    = ticker
        result["synthetic"] = is_synthetic
        return result

    except Exception as e:
        logger.error(f"Enhanced backtest error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FASE 12.4 — OPTIONS / DERIVATIVES ====================

@app.get("/api/options/chain/{ticker}")
async def api_options_chain(
    ticker:   str,
    expiry_days: int   = Query(30, ge=1, le=730),
    n_strikes:   int   = Query(11, ge=3, le=21),
):
    """
    Synthetic options chain using Black-Scholes with vol smile.
    Fully offline — derives sigma from realised vol of OHLCV data.
    """
    try:
        _add_sys_path()
        from atlas.derivatives.options.black_scholes import options_chain

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, "6mo")
        close   = ohlcv["Close"]
        S       = float(close.iloc[-1])
        rets    = close.pct_change().dropna()
        sigma   = float(rets.tail(30).std() * (252 ** 0.5))
        sigma   = max(sigma, 0.10)      # floor at 10% IV

        T = expiry_days / 365.0
        r = 0.05                         # assume 5% risk-free

        chain = options_chain(S, T, r, sigma, n_strikes=n_strikes)
        chain["ticker"]    = ticker
        chain["synthetic"] = is_synthetic
        return chain

    except Exception as e:
        logger.error(f"Options chain error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/options/greeks")
async def api_options_greeks(
    S:     float = Query(..., description="Spot price"),
    K:     float = Query(..., description="Strike"),
    T:     float = Query(..., description="Time to expiry (years)"),
    sigma: float = Query(0.20, description="Implied vol (annualised decimal)"),
    r:     float = Query(0.05, description="Risk-free rate"),
    option_type: str = Query("call"),
):
    """Black-Scholes Greeks calculator — all inputs manual, fully offline."""
    try:
        _add_sys_path()
        from atlas.derivatives.options.black_scholes import bs_greeks, synthetic_positions
        greeks  = bs_greeks(S, K, T, r, sigma, option_type)
        synths  = synthetic_positions(S, K, T, r, sigma)
        return {
            "inputs": {"S": S, "K": K, "T": T, "sigma": sigma, "r": r, "type": option_type},
            "greeks": greeks,
            "synthetics": synths,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/options/surface/{ticker}")
async def api_options_surface(
    ticker: str,
):
    """
    Full IV surface across expiries and strikes.
    Fully offline — realised vol proxy.
    """
    try:
        _add_sys_path()
        from atlas.derivatives.options.black_scholes import iv_surface

        ohlcv, is_synthetic = _fetch_ohlcv_local(ticker, "1y")
        close   = ohlcv["Close"]
        S       = float(close.iloc[-1])
        rets    = close.pct_change().dropna()
        sigma   = float(rets.tail(30).std() * (252 ** 0.5))
        sigma   = max(sigma, 0.10)

        surface = iv_surface(S, r=0.05, sigma=sigma)
        surface["ticker"]    = ticker
        surface["synthetic"] = is_synthetic
        return surface

    except Exception as e:
        logger.error(f"IV surface error [{ticker}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FASE 15 — POST-TRADE ====================

@app.post("/api/posttrade/report")
async def api_posttrade_report(payload: dict):
    """
    Full post-trade report from a submitted trade list.

    Body
    ----
    {
      "trades": [ {trade_id, ticker, action, entry_price, exit_price,
                   size, entry_time, exit_time, engine_id, signal_conf, regime} ],
      "horizons": [1, 3, 5, 10, 20]   (optional)
    }
    """
    try:
        _add_sys_path()
        from atlas.post_trade.post_trade import (
            PostTradeAnalyzer, TradeRecord,
        )

        raw_trades = payload.get("trades", [])
        horizons   = payload.get("horizons", [1, 3, 5, 10, 20])

        analyzer = PostTradeAnalyzer()
        for t in raw_trades:
            analyzer.add_trade(TradeRecord(
                trade_id    = str(t.get("trade_id", "")),
                ticker      = str(t.get("ticker", "")),
                action      = str(t.get("action", "BUY")),
                entry_price = float(t.get("entry_price", 0)),
                exit_price  = float(t.get("exit_price", 0)),
                size        = float(t.get("size", 1)),
                entry_time  = str(t.get("entry_time", "")),
                exit_time   = str(t.get("exit_time", "")),
                engine_id   = str(t.get("engine_id", "")),
                signal_conf = float(t.get("signal_conf", 0)),
                regime      = str(t.get("regime", "")),
            ))

        # Fetch OHLCV for each unique ticker
        tickers  = list({t.ticker for t in analyzer.trades})
        ohlcv_map = {}
        for tkr in tickers:
            try:
                df, _ = _fetch_ohlcv_local(tkr, "2y")
                ohlcv_map[tkr] = df
            except Exception:
                pass

        report = analyzer.full_report(ohlcv_map, horizons=horizons)
        report["leaderboard"] = analyzer.engine_leaderboard()
        return report

    except Exception as e:
        logger.error(f"Post-trade report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FASE 10 — MEMORY ====================

@app.get("/api/memory/summary")
async def api_memory_summary():
    """Return summary of the enhanced pattern/regime memory."""
    try:
        _add_sys_path()
        from atlas.memory.pattern_memory import EnhancedMemoryStore
        store = EnhancedMemoryStore(path="data/memory_enhanced.json")
        return store.memory_summary()
    except Exception as e:
        return {"error": str(e), "n_runs": 0, "n_patterns": 0}


@app.post("/api/memory/snapshot")
async def api_memory_snapshot(payload: dict):
    """
    Add a market snapshot to pattern memory.

    Body
    ----
    { ticker, trend_score, vol_percentile, rsi, momentum_5d,
      momentum_20d, regime_code, confidence, label }
    """
    try:
        _add_sys_path()
        from atlas.memory.pattern_memory import EnhancedMemoryStore, MarketSnapshot
        from datetime import datetime

        store = EnhancedMemoryStore(path="data/memory_enhanced.json")
        snap  = MarketSnapshot(
            timestamp     = datetime.now().isoformat(),
            ticker        = payload.get("ticker", ""),
            trend_score   = float(payload.get("trend_score", 0)),
            vol_percentile= float(payload.get("vol_percentile", 0.5)),
            rsi           = float(payload.get("rsi", 0.5)),
            momentum_5d   = float(payload.get("momentum_5d", 0)),
            momentum_20d  = float(payload.get("momentum_20d", 0)),
            regime_code   = float(payload.get("regime_code", 0)),
            confidence    = float(payload.get("confidence", 0)),
            label         = payload.get("label", ""),
        )
        store.add_snapshot(snap, auto_save=True)
        return {"status": "ok", "n_patterns": len(store.pattern_memory)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ARIA LOCAL MODEL API ====================

@app.get("/api/aria/models")
def get_aria_models():
    """
    List all locally installed Ollama models.
    100% offline — queries Ollama daemon, no external calls.
    """
    models = _get_local_models()
    return {
        "models":       models,
        "active_model": _aria_active_model,
        "backend":      "ollama",
        "local_only":   True,
    }


# Keep /api/aria/providers as alias for backwards-compat
@app.get("/api/aria/providers")
def get_aria_providers():
    """Alias for /api/aria/models — local models only."""
    return get_aria_models()


class SetModelRequest(BaseModel):
    model: str


@app.post("/api/aria/set_model")
def set_aria_model(req: SetModelRequest):
    """
    Switch ARIA to a different locally installed Ollama model.
    No restart required — takes effect on the next query.
    """
    global _aria_active_model
    _aria_active_model = req.model
    is_cloud = req.model.startswith("cloud:")
    if not is_cloud and aria_instance:
        aria_instance.model = req.model
    backend  = "cloud" if is_cloud else "ollama"
    provider = req.model[6:] if is_cloud else req.model
    return {
        "status":       "ok",
        "active_model": _aria_active_model,
        "backend":      backend,
        "message":      f"ARIA now uses: {provider} ({backend})",
    }


# Keep /api/aria/set_provider as alias
@app.post("/api/aria/set_provider")
def set_aria_provider_compat(req: SetModelRequest):
    """Alias for /api/aria/set_model — local models only."""
    return set_aria_model(req)


@app.get("/api/aria/audit")
def get_aria_audit(limit: int = 20):
    """
    Return the last N ARIA request audit entries.
    Each entry: ts, model, latency_ms, success, message_len
    """
    entries = _aria_audit_log[-limit:] if limit > 0 else list(_aria_audit_log)
    total   = len(_aria_audit_log)
    ok      = sum(1 for e in _aria_audit_log if e.get("success"))
    avg_lat = int(sum(e.get("latency_ms", 0) for e in _aria_audit_log) / total) if total else 0
    return {
        "total_requests": total,
        "successful":     ok,
        "success_rate":   round(ok / total, 3) if total else 1.0,
        "avg_latency_ms": avg_lat,
        "active_model":   _aria_active_model,
        "backend":        "ollama",
        "local_only":     True,
        "entries":        list(reversed(entries)),
    }


@app.get("/api/aria/status")
def get_aria_status():
    """Quick ARIA health check — model, latency stats, fully local."""
    total = len(_aria_audit_log)
    ok    = sum(1 for e in _aria_audit_log if e.get("success"))
    return {
        "active_model":     _aria_active_model,
        "backend":          "ollama",
        "local_only":       True,
        "aria_initialised": aria_instance is not None,
        "total_requests":   total,
        "success_rate":     round(ok / total, 3) if total else 1.0,
    }


# ==================== FACTOR ENGINE ====================

@app.get("/api/factors/{ticker}")
async def get_factors(ticker: str, period: str = "1y"):
    """
    Compute qlib Alpha158-inspired factor scores for a ticker.
    Returns normalized factor scores, group averages, and top signals.
    Inspired by Microsoft qlib Alpha158 / Alpha360 feature pipeline.
    """
    _add_sys_path()
    symbol = ticker.strip().upper()
    cache_key = f"factors:{symbol}:{period}"
    cache_hit = _cache_get(cache_key)
    if cache_hit:
        return cache_hit

    try:
        from atlas.correlation_portfolio.factor_models.factor_engine import FactorEngine
    except ImportError as e:
        raise HTTPException(500, f"Factor engine import failed: {e}")

    df, is_synthetic = _fetch_ohlcv_local(symbol, period=period)
    if df is None or df.empty:
        raise HTTPException(404, f"No data for {symbol}")

    # Keep only OHLCV in capitalized form expected by FactorEngine.
    ohlcv_cols = [c for c in df.columns if c.lower() in ("open", "high", "low", "close", "volume")]
    df = df[ohlcv_cols].copy()
    engine = FactorEngine()

    scores      = await asyncio.to_thread(engine.score, df)
    group_avgs  = await asyncio.to_thread(engine.group_groups, df) if hasattr(engine,'group_groups') else await asyncio.to_thread(engine.group_scores, df)
    top_factors = await asyncio.to_thread(engine.top_factors, df, 15)

    payload = _json_safe({
        "ticker":       symbol,
        "period":       period,
        "factor_count": len(scores),
        "scores":       scores,
        "group_scores": group_avgs,
        "top_factors":  top_factors,
        "source":       "synthetic_local" if is_synthetic else "yfinance",
        "synthetic":    bool(is_synthetic),
        "timestamp":    datetime.now().isoformat(),
    })
    _cache_set(cache_key, payload, ttl=120)
    return payload


# ==================== FUNDAMENTAL ANALYSIS (Dexter-inspired) ====================

@app.get("/api/fundamental/{ticker}")
async def get_fundamentals(ticker: str):
    """
    Fetch key fundamental metrics for a ticker.
    Inspired by Dexter's financial tool schemas (income statement, ratios, DCF).
    Uses yfinance — no API key required.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise HTTPException(500, "yfinance not installed")

    def _fetch():
        t = yf.Ticker(ticker)
        info = t.info or {}
        # Build a curated fundamental snapshot
        return {
            "ticker":           ticker.upper(),
            "name":             info.get("longName", ticker),
            "sector":           info.get("sector", "N/A"),
            "industry":         info.get("industry", "N/A"),
            "market_cap":       info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            # Valuation
            "pe_ratio":         info.get("trailingPE"),
            "forward_pe":       info.get("forwardPE"),
            "peg_ratio":        info.get("pegRatio"),
            "pb_ratio":         info.get("priceToBook"),
            "ps_ratio":         info.get("priceToSalesTrailing12Months"),
            "ev_ebitda":        info.get("enterpriseToEbitda"),
            # Profitability
            "profit_margin":    info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe":              info.get("returnOnEquity"),
            "roa":              info.get("returnOnAssets"),
            # Growth
            "revenue_growth":   info.get("revenueGrowth"),
            "earnings_growth":  info.get("earningsGrowth"),
            "revenue_ttm":      info.get("totalRevenue"),
            "ebitda":           info.get("ebitda"),
            "free_cash_flow":   info.get("freeCashflow"),
            # Debt & liquidity
            "debt_to_equity":   info.get("debtToEquity"),
            "current_ratio":    info.get("currentRatio"),
            "quick_ratio":      info.get("quickRatio"),
            # Dividends
            "dividend_yield":   info.get("dividendYield"),
            "payout_ratio":     info.get("payoutRatio"),
            # Price
            "current_price":    info.get("currentPrice") or info.get("regularMarketPrice"),
            "52w_high":         info.get("fiftyTwoWeekHigh"),
            "52w_low":          info.get("fiftyTwoWeekLow"),
            "beta":             info.get("beta"),
            "shares_outstanding": info.get("sharesOutstanding"),
            # Analyst
            "target_price":     info.get("targetMeanPrice"),
            "recommendation":   info.get("recommendationKey"),
            "analyst_count":    info.get("numberOfAnalystOpinions"),
        }

    data = await asyncio.to_thread(_fetch)
    return data


@app.get("/api/dcf/{ticker}")
async def get_dcf(ticker: str, wacc: float = 0.10, terminal_growth: float = 0.025, years: int = 10):
    """
    Simple DCF (Discounted Cash Flow) valuation.
    Inspired by Dexter's DCF SKILL.md — 8-step Buffett/Munger framework.

    Steps:
      1. Fetch trailing free cash flow
      2. Apply analyst revenue growth rate (or historical avg)
      3. Estimate FCF margin stability
      4. Discount back at WACC
      5. Add terminal value (Gordon Growth Model)
      6. Compare to market cap → margin of safety
    """
    try:
        import yfinance as yf
    except ImportError:
        raise HTTPException(500, "yfinance not installed")

    def _dcf():
        t    = yf.Ticker(ticker)
        info = t.info or {}

        fcf   = info.get("freeCashflow")
        mcap  = info.get("marketCap")
        shares = info.get("sharesOutstanding") or 1
        price  = info.get("currentPrice") or info.get("regularMarketPrice") or 0

        if not fcf or not mcap:
            return {"error": "Insufficient fundamental data", "ticker": ticker.upper()}

        # Growth rate: use analyst earnings growth or default to 8%
        growth = float(info.get("earningsGrowth") or info.get("revenueGrowth") or 0.08)
        # Taper growth after 5 years
        growth = min(max(growth, -0.20), 0.40)   # clamp to [-20%, 40%]

        # Project FCF for `years` years
        projected_fcf = []
        current_fcf = float(fcf)
        for yr in range(1, years + 1):
            g = growth if yr <= 5 else max(terminal_growth, growth * 0.5)
            current_fcf *= (1 + g)
            pv = current_fcf / ((1 + wacc) ** yr)
            projected_fcf.append({
                "year": yr,
                "fcf": round(current_fcf),
                "pv":  round(pv),
                "growth_rate": round(g, 4),
            })

        total_pv_fcf = sum(p["pv"] for p in projected_fcf)

        # Terminal value (Gordon Growth Model)
        last_fcf  = projected_fcf[-1]["fcf"]
        tv        = last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        tv_pv     = tv / ((1 + wacc) ** years)

        # Intrinsic value
        iv_total      = total_pv_fcf + tv_pv
        iv_per_share  = iv_total / shares if shares > 0 else 0

        # Margin of safety
        mos = (iv_per_share - price) / price if price > 0 else None

        # Sensitivity: ±1% WACC
        sensitivity = {}
        for delta_w in [-0.02, -0.01, 0, 0.01, 0.02]:
            w2 = wacc + delta_w
            if w2 <= terminal_growth:
                sensitivity[f"wacc_{round((wacc+delta_w)*100)}pct"] = None
                continue
            pv_fcf2 = sum(
                projected_fcf[i]["fcf"] / ((1+w2)**(i+1))
                for i in range(len(projected_fcf))
            )
            tv2    = projected_fcf[-1]["fcf"] * (1+terminal_growth) / (w2 - terminal_growth)
            tv_pv2 = tv2 / ((1+w2)**years)
            iv2    = (pv_fcf2 + tv_pv2) / shares if shares > 0 else 0
            sensitivity[f"wacc_{round(w2*100)}pct"] = round(iv2, 2)

        return {
            "ticker":           ticker.upper(),
            "current_price":    round(price, 2),
            "intrinsic_value":  round(iv_per_share, 2),
            "margin_of_safety": round(mos, 4) if mos is not None else None,
            "assessment":       (
                "UNDERVALUED"  if mos and mos > 0.20 else
                "FAIRLY VALUED" if mos and mos > -0.10 else
                "OVERVALUED"
            ) if mos is not None else "INSUFFICIENT DATA",
            "inputs": {
                "trailing_fcf":    fcf,
                "wacc":            wacc,
                "terminal_growth": terminal_growth,
                "growth_rate_y1_5":round(growth, 4),
                "projection_years": years,
                "shares_outstanding": shares,
            },
            "pv_of_fcf":          round(total_pv_fcf),
            "terminal_value_pv":  round(tv_pv),
            "intrinsic_value_total": round(iv_total),
            "projected_fcf":      projected_fcf,
            "sensitivity":        sensitivity,
            "methodology":        "Gordon Growth Model (Buffett/Munger framework)",
            "timestamp":          datetime.now().isoformat(),
        }

    result = await asyncio.to_thread(_dcf)
    return result


# ==================== CLOUD LLM PROVIDERS (free-llm-api-resources inspired) ====================

# Cloud provider registry — checks env vars at runtime (no keys = provider hidden)
_CLOUD_PROVIDERS = {
    "groq": {
        "label":    "Groq · Llama 3.3 70B ⚡ Fast",
        "base_url": "https://api.groq.com/openai/v1",
        "model":    "llama-3.3-70b-versatile",
        "env_key":  "GROQ_API_KEY",
        "free":     True,
        "rpm":      30,   # free tier: 30 req/min
    },
    "groq-fast": {
        "label":    "Groq · Llama 3.1 8B ⚡⚡ Ultra Fast",
        "base_url": "https://api.groq.com/openai/v1",
        "model":    "llama-3.1-8b-instant",
        "env_key":  "GROQ_API_KEY",
        "free":     True,
        "rpm":      30,
    },
    "openrouter": {
        "label":    "OpenRouter · Llama 3.3 70B (free)",
        "base_url": "https://openrouter.ai/api/v1",
        "model":    "meta-llama/llama-3.3-70b-instruct:free",
        "env_key":  "OPENROUTER_API_KEY",
        "free":     True,
        "rpm":      10,
    },
    "gemini": {
        "label":    "Gemini 2.0 Flash (free tier)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model":    "gemini-2.0-flash",
        "env_key":  "GEMINI_API_KEY",
        "free":     True,
        "rpm":      15,
    },
}


async def _ask_cloud(user_message: str, provider_id: str) -> tuple:
    """
    Query a cloud LLM provider (Groq / OpenRouter / Gemini) using
    their OpenAI-compatible API. Returns (response, provider_id, latency_ms).
    Requires the provider's API key in the corresponding env var.
    """
    import httpx
    cfg   = _CLOUD_PROVIDERS[provider_id]
    key   = os.getenv(cfg["env_key"])
    if not key:
        raise RuntimeError(f"No API key for {provider_id} (set {cfg['env_key']})")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    if provider_id == "openrouter":
        headers["HTTP-Referer"] = "https://atlas.local"
        headers["X-Title"]      = "Atlas Trading Platform"

    payload = {
        "model":    cfg["model"],
        "messages": [{"role":"user","content":user_message}],
        "max_tokens": 2048,
        "temperature": 0.7,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            json=payload, headers=headers
        )
    resp.raise_for_status()
    data   = resp.json()
    answer = data["choices"][0]["message"]["content"]
    latency_ms = int((time.time() - t0) * 1000)
    return answer, provider_id, latency_ms


@app.get("/api/aria/cloud-providers")
def get_cloud_providers():
    """
    List available free cloud LLM providers.
    Only returns providers where an API key env var is set.
    """
    available = []
    for pid, cfg in _CLOUD_PROVIDERS.items():
        has_key = bool(os.getenv(cfg["env_key"]))
        available.append({
            "id":        pid,
            "label":     cfg["label"],
            "model":     cfg["model"],
            "free":      cfg["free"],
            "available": has_key,
            "env_key":   cfg["env_key"],
        })
    return {"providers": available}


# Update get_aria_models to include cloud providers when keys are set
@app.get("/api/aria/all-models")
def get_all_models():
    """
    Combined list: local Ollama models + available cloud providers.
    Use this for the full model picker in the UI.
    """
    local   = _get_local_models()
    cloud_p = []
    for pid, cfg in _CLOUD_PROVIDERS.items():
        has_key = bool(os.getenv(cfg["env_key"]))
        if has_key:
            cloud_p.append({
                "id":       f"cloud:{pid}",
                "label":    cfg["label"],
                "active":   _aria_active_model == f"cloud:{pid}",
                "size_gb":  0,
                "backend":  "cloud",
                "provider": pid,
                "free":     cfg["free"],
            })
    return {
        "models":       local + cloud_p,
        "active_model": _aria_active_model,
        "local_count":  len(local),
        "cloud_count":  len(cloud_p),
    }


# ==================== ARIA TRADER ====================

# Default universe for screener
_TRADER_UNIVERSE = [
    "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","MA",
    "UNH","JNJ","WMT","HD","BAC","XOM","CVX","ABBV","LLY","PG",
    "AVGO","ORCL","AMD","ADBE","CRM","NFLX","COST","DIS","PFE","KO",
]

@app.get("/api/trader/analyze/{ticker}")
async def trader_analyze(ticker: str, period: str = Query("1y")):
    """
    Full composite score for a single ticker.
    Fuses: technical (35%) + factor (25%) + fundamental (20%) + momentum (10%) + regime (10%)
    Returns: composite_score, verdict, confidence, components, prediction, insights, risk_flags
    """
    try:
        _add_sys_path()
        from atlas.trader.composite_scorer import CompositeScorer

        symbol = ticker.strip().upper()
        cache_key = f"trader:analyze:{symbol}:{period}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        df, is_synthetic = _fetch_ohlcv_local(symbol, period)
        if df is None or len(df) < 30:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        # Pre-fetch info once (avoids double yfinance calls)
        info = {}
        if not is_synthetic:
            try:
                import yfinance as yf
                info = yf.Ticker(symbol).info or {}
            except Exception:
                info = {}

        scorer = CompositeScorer()
        result = scorer.score(symbol, df, info=info).to_dict()
        # Add top-level 'signal' key (alias for verdict) for uniform API
        result["signal"] = result.get("verdict") or (
            "BUY"  if (result.get("composite_score") or 0) > 25  else
            "SELL" if (result.get("composite_score") or 0) < -15 else "HOLD"
        )
        result["synthetic"] = bool(is_synthetic)
        result["source"] = "synthetic_local" if is_synthetic else "yfinance"
        result = _json_safe(result)
        _cache_set(cache_key, result, ttl=120)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("trader_analyze error %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trader/predict/{ticker}")
async def trader_predict(ticker: str, period: str = Query("6mo")):
    """
    Fast price prediction only — entry / stop / target / R:R ratio.
    Uses ATR-based setup scaled by composite conviction.
    """
    try:
        _add_sys_path()
        from atlas.trader.composite_scorer import CompositeScorer

        symbol = ticker.strip().upper()
        cache_key = f"trader:predict:{symbol}:{period}"
        cache_hit = _cache_get(cache_key)
        if cache_hit:
            return cache_hit

        df, is_synthetic = _fetch_ohlcv_local(symbol, period)
        if df is None or len(df) < 14:
            raise HTTPException(status_code=404, detail="Insufficient data")

        scorer = CompositeScorer()
        result = scorer.score(symbol, df, info={})
        _verdict_str = result.verdict or (
            "BUY"  if result.composite_score > 25  else
            "SELL" if result.composite_score < -15 else "HOLD"
        )
        payload = {
            "ticker":          result.ticker,
            "last_close":      result.last_close,
            "composite_score": result.composite_score,
            "signal":          _verdict_str,   # top-level shortcut (BUY/SELL/HOLD)
            "verdict":         _verdict_str,
            "confidence":      result.confidence,
            "prediction":      result.to_dict()["prediction"],
            "synthetic":       bool(is_synthetic),
            "source":          "synthetic_local" if is_synthetic else "yfinance",
        }
        payload = _json_safe(payload)
        _cache_set(cache_key, payload, ttl=120)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trader/screen")
async def trader_screen(
    tickers: str = Query(None, description="Comma-separated tickers; omit for default universe"),
    period:  str = Query("1y"),
    top_n:   int = Query(10),
):
    """
    Screen a universe of tickers, rank by composite score.
    Returns sorted list: top BUYs first, worst AVOIDs last.
    """
    try:
        _add_sys_path()
        from atlas.trader.composite_scorer import CompositeScorer

        universe = [t.strip().upper() for t in tickers.split(",")] if tickers else _TRADER_UNIVERSE

        scorer = CompositeScorer()
        results = []
        for ticker in universe[:40]:          # cap at 40 to keep response fast
            try:
                df, is_synthetic = _fetch_ohlcv_local(ticker, period)
                if df is None or len(df) < 30:
                    continue
                info = {}
                if not is_synthetic:
                    try:
                        import yfinance as yf
                        info = yf.Ticker(ticker).info or {}
                    except Exception:
                        info = {}
                r = scorer.score(ticker, df, info=info)
                row = _json_safe(r.to_dict())
                row["synthetic"] = bool(is_synthetic)
                results.append(row)
            except Exception as e:
                logger.warning("screen %s: %s", ticker, e)

        results.sort(key=lambda x: x["composite_score"], reverse=True)

        return _json_safe({
            "universe_size":  len(universe),
            "screened":       len(results),
            "top_buys":       results[:top_n],
            "top_avoids":     results[-top_n:][::-1],
            "full_ranking":   results,
        })

    except Exception as e:
        logger.error("trader_screen: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trader/batch")
async def trader_batch(
    tickers: str = Query(..., description="Comma-separated tickers"),
    period:  str = Query("1y"),
):
    """
    Lightweight batch scorer — returns just composite_score + verdict for each ticker.
    Fast endpoint for dashboard cards.
    """
    try:
        _add_sys_path()
        from atlas.trader.composite_scorer import CompositeScorer

        ticker_list = [t.strip().upper() for t in tickers.split(",")][:30]
        scorer = CompositeScorer()
        out = []
        for ticker in ticker_list:
            try:
                df, is_synthetic = _fetch_ohlcv_local(ticker, "6mo")
                if df is None or len(df) < 14:
                    out.append({"ticker": ticker, "error": "no data"})
                    continue
                r = scorer.score(ticker, df, info={})
                out.append(_json_safe({
                    "ticker":          r.ticker,
                    "composite_score": r.composite_score,
                    "verdict":         r.verdict,
                    "confidence":      r.confidence,
                    "last_close":      r.last_close,
                    "synthetic":       bool(is_synthetic),
                }))
            except Exception as e:
                out.append({"ticker": ticker, "error": str(e)[:60]})
        return {"results": out}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MMO — MAU'S MARKET ONTOLOGY ====================

@app.get("/api/mmo/quantum_state/{ticker}")
def mmo_quantum_state(ticker: str):
    """
    Mau's Market Ontology — Full physics-layer analysis.
    Returns quantum amplitudes (Born rule), string theory metrics,
    energy/entropy, thermal state, geology, and 4-layer ecosystem data.
    """
    import yfinance as yf
    import numpy as np
    ticker = ticker.upper().strip()

    result = {
        "ticker": ticker,
        "amplitudes": {"BULL": 0.2, "BEAR": 0.2, "SIDEWAYS": 0.2, "VOLATILE": 0.2, "TRENDING": 0.2},
        "collapse_prob": 0.2,
        "collapsed_state": None,
        "entropy": 1.0,
        "quantum_verdict": "SUPERPOSED",
        "tunneling_risk": 0.05,
        "string": {"amplitude": 0.5, "frequency": 0.5, "vertices_30d": 0, "nodes": []},
        "energy": {"score": 0.5, "fatigue": 0.0, "bubble_risk": 0.0, "cooling_adequacy": 0.5},
        "thermal": {"temperature": 0.5, "overheating": False, "phase": "NEUTRAL"},
        "ontology": {"being": "UNKNOWN", "essence": "UNDEFINED", "entanglement": "MODERATE", "structural_stability": 0.5},
        "layers": [
            {"id": "structure", "label": "GEOLOGY",     "metric": "Structural Stability", "value": 0.5, "health": "STABLE"},
            {"id": "energy",    "label": "SUBSURFACE",  "metric": "Capital Flow Energy",  "value": 0.5, "health": "NEUTRAL"},
            {"id": "thermal",   "label": "STATE",       "metric": "Market Temperature",   "value": 0.5, "health": "NEUTRAL"},
            {"id": "surface",   "label": "OBSERVABLE",  "metric": "Price Momentum",       "value": 0.5, "health": "STABLE"},
        ],
        "confidence": 0.0,
        "last_close": 0.0,
        "trend_pct": 0.0,
        "trend_1mo_pct": 0.0,
        "annual_vol_pct": 0.0,
        "error": None,
    }

    try:
        _add_sys_path()

        # ── Strategy signals (best-effort) ───────────────────────────────
        strat = None
        try:
            df = _fetch_ohlcv(ticker, period="6mo")
            if not df.empty:
                from atlas.multi_strategy import MultiStrategyEngine
                engine = MultiStrategyEngine()
                sr = engine.analyze(ticker, df)
                if sr:
                    strat = sr
        except Exception:
            pass

        # ── Market data ──────────────────────────────────────────────────
        hist = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
        if hist.empty:
            result["error"] = "No market data"
            return result

        closes  = hist["Close"].values
        volumes = hist["Volume"].values if "Volume" in hist.columns else np.ones(len(closes))

        returns   = np.diff(closes) / (closes[:-1] + 1e-10)
        vol_3mo   = float(np.std(returns[-63:]) * np.sqrt(252)) if len(returns) >= 63 else float(np.std(returns) * np.sqrt(252))
        vol_6mo   = float(np.std(returns) * np.sqrt(252))
        trend     = float((closes[-1] - closes[0]) / (closes[0] + 1e-10))
        trend_1mo = float((closes[-1] - closes[-21]) / (closes[-21] + 1e-10)) if len(closes) >= 21 else trend
        adx_proxy = abs(trend) / (vol_3mo + 1e-6)

        buy_w    = getattr(strat, "buy_weight",  0.5 if trend > 0 else 0.3) if strat else (0.5 if trend > 0 else 0.3)
        sell_w   = getattr(strat, "sell_weight", 0.5 if trend < 0 else 0.3) if strat else (0.5 if trend < 0 else 0.3)
        conf     = getattr(strat, "confidence",  0.5) if strat else 0.5
        disagree = abs(buy_w - sell_w)

        # ── QUANTUM LAYER ────────────────────────────────────────────────
        a_bull     = max(0.0, buy_w  * (1 + adx_proxy * 0.3))
        a_bear     = max(0.0, sell_w * (1 + adx_proxy * 0.3))
        a_sideways = max(0.0, (1 - disagree) * (1 - min(vol_3mo / 0.3, 1)) * 0.8)
        a_volatile = max(0.0, min(vol_3mo / 0.3, 1) * (1 - disagree * 0.5))
        a_trending = max(0.0, adx_proxy * disagree * 0.9)

        raw  = np.maximum(np.array([a_bull, a_bear, a_sideways, a_volatile, a_trending]), 0.01)
        norm = raw / np.linalg.norm(raw)
        probs = norm ** 2  # Born rule: P_i = |α_i|²

        states     = ["BULL", "BEAR", "SIDEWAYS", "VOLATILE", "TRENDING"]
        amplitudes = {s: float(probs[i]) for i, s in enumerate(states)}
        max_prob   = float(np.max(probs))
        dominant   = states[int(np.argmax(probs))]
        entropy    = float(-np.sum(probs * np.log(probs + 1e-10)) / np.log(5))

        # Tunneling risk: tail-event probability (rare discontinuous transition)
        sigma_5d      = vol_3mo / max(np.sqrt(52), 1e-6)
        tunneling_risk = round(float(min(2.0 * np.exp(-4.5 * sigma_5d), 0.25)), 4)

        collapsed_state = dominant if max_prob > 0.50 else None
        if   collapsed_state == "BULL":     quantum_verdict = "BUY"
        elif collapsed_state == "BEAR":     quantum_verdict = "SELL"
        elif collapsed_state == "TRENDING": quantum_verdict = "FOLLOW TREND"
        elif collapsed_state == "VOLATILE": quantum_verdict = "HEDGE / REDUCE"
        else:                               quantum_verdict = "SUPERPOSED — WAIT"

        # ── STRING THEORY LAYER ──────────────────────────────────────────
        # Amplitude = trend strength (how hard the string is plucked)
        string_amplitude = float(min(abs(trend) * 2.5, 1.0))
        # Frequency = vol normalized (how fast states switch)
        string_frequency = float(min(vol_3mo / 0.25, 1.0))
        # Vertices = significant moves >1.5σ in last 30d (energy transfer events)
        vertices_30d = 0
        if len(returns) >= 30:
            r30 = returns[-30:]
            sig = float(np.std(r30)) + 1e-10
            vertices_30d = int(np.sum(np.abs(r30) > 1.5 * sig))
        # Nodes = most-visited price levels (standing waves / structural boundaries)
        price_nodes = []
        if len(closes) >= 20:
            counts, edges = np.histogram(closes, bins=10)
            top_bins = np.argsort(counts)[-3:][::-1]
            for b in top_bins:
                level = float((edges[b] + edges[b + 1]) / 2)
                node_type = "SUPPORT" if level < closes[-1] else "RESISTANCE"
                price_nodes.append({"level": round(level, 2), "type": node_type, "strength": int(counts[b])})

        # ── ENERGY LAYER ─────────────────────────────────────────────────
        r20   = returns[-20:] if len(returns) >= 20 else returns
        v20   = volumes[-20:] if len(volumes) >= 20 else volumes
        raw_e = float(np.mean(np.abs(r20) * v20 / (np.mean(v20) + 1e-10)))
        energy_score = float(min(raw_e * 10, 1.0))

        fatigue = 0.0
        if len(returns) >= 40:
            ev = float(np.std(returns[-40:-20]) * np.sqrt(252))
            rv = float(np.std(returns[-20:])    * np.sqrt(252))
            fatigue = float(max(0.0, (ev - rv) / (ev + 1e-6)))

        sma_6mo     = float(np.mean(closes))
        bubble_risk = float(min(abs(closes[-1] - sma_6mo) / (sma_6mo * 0.2 + 1e-6), 1.0))

        cooling = 0.5
        if len(returns) >= 40:
            cooling = float(max(0.0, min(1.0, (vol_6mo - vol_3mo) / (vol_6mo + 1e-6))))

        # ── THERMAL LAYER ────────────────────────────────────────────────
        temperature = float(min(vol_3mo / 0.40, 1.0))
        overheating = bool(temperature > 0.75 and trend > 0.05)
        if   temperature < 0.25:  thermal_phase = "COLD"
        elif temperature < 0.50:  thermal_phase = "WARM"
        elif temperature < 0.75:  thermal_phase = "HOT"
        elif overheating:         thermal_phase = "OVERHEATING"
        else:                     thermal_phase = "TURBULENT"

        # ── GEOLOGY LAYER ────────────────────────────────────────────────
        if   trend > 0.05  and vol_3mo < 0.25: being = "EXPANSION"
        elif trend < -0.05 and vol_3mo < 0.25: being = "CONTRACTION"
        elif vol_3mo > 0.35:                    being = "TURBULENCE"
        elif abs(trend) < 0.02:                 being = "STASIS"
        else:                                   being = "TRANSITION"

        if   adx_proxy > 0.8:  essence = "MOMENTUM-DRIVEN"
        elif vol_3mo > 0.30:   essence = "VOLATILITY-DRIVEN"
        elif buy_w > 0.6:      essence = "DEMAND-LED"
        elif sell_w > 0.6:     essence = "SUPPLY-PRESSURED"
        else:                  essence = "MEAN-REVERTING"

        ent_s = (vol_3mo * 2 + adx_proxy) / 3
        if   ent_s > 0.7:  entanglement = "MAXIMAL"
        elif ent_s > 0.4:  entanglement = "HIGH"
        elif ent_s > 0.2:  entanglement = "MODERATE"
        else:              entanglement = "LOW"

        structural_stability = round(float(min(max(0.0, 1 - vol_3mo * 1.5 + abs(trend) * 0.3), 1.0)), 3)

        # ── 4-LAYER ECOSYSTEM ────────────────────────────────────────────
        def _health(v):
            if v > 0.7: return "STRONG"
            if v > 0.4: return "STABLE"
            if v > 0.2: return "WEAK"
            return "FRAGILE"

        layers = [
            {"id": "structure", "label": "GEOLOGY",    "metric": "Structural Stability",
             "value": structural_stability,         "health": _health(structural_stability)},
            {"id": "energy",    "label": "SUBSURFACE", "metric": "Capital Flow Energy",
             "value": round(energy_score, 3),       "health": _health(energy_score)},
            {"id": "thermal",   "label": "STATE",      "metric": "Market Temperature",
             "value": round(temperature, 3),        "health": thermal_phase},
            {"id": "surface",   "label": "OBSERVABLE", "metric": "Price Momentum",
             "value": round(max_prob, 3),           "health": _health(max_prob)},
        ]

        result.update({
            "amplitudes":       amplitudes,
            "collapse_prob":    round(max_prob, 3),
            "collapsed_state":  collapsed_state,
            "entropy":          round(entropy, 3),
            "quantum_verdict":  quantum_verdict,
            "tunneling_risk":   tunneling_risk,
            "string": {
                "amplitude":    round(string_amplitude, 3),
                "frequency":    round(string_frequency, 3),
                "vertices_30d": vertices_30d,
                "nodes":        price_nodes,
            },
            "energy": {
                "score":            round(energy_score, 3),
                "fatigue":          round(fatigue, 3),
                "bubble_risk":      round(bubble_risk, 3),
                "cooling_adequacy": round(cooling, 3),
            },
            "thermal": {
                "temperature": round(temperature, 3),
                "overheating": overheating,
                "phase":       thermal_phase,
            },
            "ontology": {
                "being":                being,
                "essence":              essence,
                "entanglement":         entanglement,
                "structural_stability": structural_stability,
            },
            "layers":        layers,
            "confidence":    round(conf, 3),
            "last_close":    round(float(closes[-1]), 2),
            "trend_pct":     round(trend * 100, 2),
            "trend_1mo_pct": round(trend_1mo * 100, 2),
            "annual_vol_pct": round(vol_3mo * 100, 2),
        })

    except Exception as e:
        result["error"] = str(e)

    return result


# ==================== AI AGENT SYSTEM ====================

# Lazy-init orchestrator (built once on first request)
_agent_orchestrator = None

def _get_agent_orchestrator():
    global _agent_orchestrator
    if _agent_orchestrator is None:
        try:
            import sys
            from pathlib import Path
            _root = Path(__file__).resolve().parents[2]
            if str(_root / "python" / "src") not in sys.path:
                sys.path.insert(0, str(_root / "python" / "src"))
            from atlas.core.ai_assistant import build_system
            _agent_orchestrator = build_system()
        except Exception as e:
            logging.warning(f"Agent system init failed: {e}")
            _agent_orchestrator = None
    return _agent_orchestrator


@app.get("/api/agents")
def list_agents():
    """List all registered agents and their metadata."""
    orch = _get_agent_orchestrator()
    if orch is None:
        return {"error": "Agent system not available", "agents": []}

    agents_info = []
    try:
        for name in orch.registry.list_agents():
            agent = orch.registry.get(name)
            agents_info.append({
                "name":    agent.name,
                "version": agent.version,
                "class":   type(agent).__name__,
            })
    except Exception as e:
        return {"error": str(e), "agents": []}

    return {
        "total":  len(agents_info),
        "agents": agents_info,
        "status": "ok",
    }


class AgentRunRequest(BaseModel):
    agent_name:  str
    objective:   str
    context:     Optional[Dict[str, Any]] = {}
    inputs:      Optional[Dict[str, Any]] = {}
    risk_level:  Optional[str] = "low"


@app.post("/api/agents/run")
def run_agent(req: AgentRunRequest):
    """Execute an agent task and return the result."""
    orch = _get_agent_orchestrator()
    if orch is None:
        return {"status": "error", "errors": ["Agent system not available"], "result": {}}

    try:
        from atlas.core.ai_assistant.task_schema import AgentTask
        task = AgentTask(
            objective  = req.objective,
            agent_name = req.agent_name,
            context    = req.context or {},
            inputs     = req.inputs or {},
            risk_level = req.risk_level or "low",
        )
        result = orch.execute(task)
        return {
            "task_id":  result.task_id,
            "status":   result.status,
            "summary":  result.summary,
            "result":   result.result,
            "errors":   result.errors,
            "metadata": result.metadata,
        }
    except Exception as e:
        return {"status": "error", "errors": [str(e)], "result": {}}


@app.get("/api/agents/status")
def agents_status():
    """Quick status check for the agent system."""
    orch = _get_agent_orchestrator()
    if orch is None:
        return {"available": False, "agents_count": 0, "reason": "Import error or build failed"}

    try:
        count = len(orch.registry.list_agents())
        return {
            "available":    True,
            "agents_count": count,
            "agents":       orch.registry.list_agents(),
        }
    except Exception as e:
        return {"available": False, "agents_count": 0, "reason": str(e)}


# ==================== WEBSOCKET ====================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket for real-time sync
    
    Connect: ws://server:8000/ws/session-123
    
    Messages:
        Client -> Server: {"type": "message", "content": "Hello"}
        Server -> Client: {"type": "new_message", "role": "assistant", "content": "Hi!"}
    """
    await websocket.accept()
    
    # Add to active connections
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "message":
                # Process with ARIA
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(aria_instance.ask, message["content"]),
                        timeout=QUERY_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    response = (
                        "Request timed out while waiting for ARIA. "
                        "Try a shorter prompt or switch to a faster model."
                    )
                
                # Save to DB
                db.add_message(session_id, "websocket", "user", message["content"])
                db.add_message(session_id, "websocket", "assistant", response)
                
                # Broadcast response
                await broadcast_message(session_id, {
                    "type": "new_message",
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        # Remove from active connections
        active_connections[session_id].remove(websocket)


async def broadcast_message(session_id: str, message: dict):
    """Broadcast message to all devices in session"""
    if session_id in active_connections:
        for connection in active_connections[session_id]:
            try:
                await connection.send_json(message)
            except:
                pass


# ==================== STATIC FILES (Catch-All) ====================

# Serve Static Files (Frontend)
# Must be last to avoid hiding API routes
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_path = Path(__file__).parent.parent / "desktop"

if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")

# ==================== STARTUP ====================

def run_server(aria, host: str = "0.0.0.0", port: int = 8000):
    """
    Run multi-device server
    
    Args:
        aria: ARIA instance
        host: Server host (0.0.0.0 = accessible from network)
        port: Server port
    
    Example:
        from atlas.assistants.aria import ARIA
        from aria.server import run_server
        
        aria = ARIA()
        run_server(aria, host="0.0.0.0", port=8000)
    
    Access:
        - From same PC: http://localhost:8000
        - From other PC: http://192.168.1.X:8000
        - API docs: http://localhost:8000/docs
    """
    global aria_instance
    aria_instance = aria
    
    import uvicorn
    
    print("=" * 60)
    print("ðŸŒ ARIA Multi-Device Server")
    print("=" * 60)
    print(f"Server: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print(f"WebSocket: ws://{host}:{port}/ws/{{session_id}}")
    print("\nAccess from other devices:")
    print("1. Find your IP: ipconfig (Windows) or ifconfig (Linux/Mac)")
    print("2. Connect: http://YOUR_IP:8000")
    print("=" * 60)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("""
    ðŸŒ ARIA Multi-Device Server
    
    Installation:
        pip install fastapi uvicorn websockets
    
    Usage:
        from atlas.assistants.aria import ARIA
        from aria.server import run_server
        
        aria = ARIA()
        run_server(aria, host="0.0.0.0", port=8000)
    
    Features:
        âœ… REST API for queries
        âœ… WebSocket for real-time
        âœ… Conversation sync
        âœ… Multi-device support
    
    Access:
        PC 1: http://localhost:8000
        PC 2: http://192.168.1.X:8000 (replace X with your IP)
        Mobile: http://192.168.1.X:8000
    
    API Endpoints:
        POST /query - Query ARIA
        GET /conversation/{session_id} - Get history
        POST /device/register - Register device
        WS /ws/{session_id} - WebSocket connection
    
    âœ… Ready for multi-device access!
    """)
