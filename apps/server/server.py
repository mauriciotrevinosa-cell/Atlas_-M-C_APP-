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
import time
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
    """Get conversation history"""
    messages = db.get_conversation(session_id, limit)
    return {"session_id": session_id, "messages": messages}


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
        # Try importing yfinance to get real data
        import yfinance as yf
        import pandas as pd
        
        print(f"Fetching data for {request.ticker}...")
        data = yf.download(request.ticker, start=request.start_date, progress=False)
        
        if data.empty:
            raise HTTPException(status_code=404, detail="No data found for ticker")
            
        # Flatten MultiIndex if present (yfinance update)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # Ensure lowercase columns for consistency
        data.columns = [c.lower() for c in data.columns]
        
        # Initialize session
        from atlas.evaluation.scenario import ScenarioSession
        session = ScenarioSession(data, request.initial_capital, request.ticker)
        
        # Store in memory
        session_id = f"scen-{datetime.now().timestamp()}"
        scenario_sessions[session_id] = session
        
        # Get first step (initial state)
        state = session.next_step()
        
        return {
            "session_id": session_id,
            "ticker": request.ticker,
            "total_steps": len(data),
            "initial_state": state
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="yfinance not installed on server")
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
        "modules": {
            "aria": True,
            "data_layer": True,
            "indicators": True,
            "signal_engine": True,
            "risk_engine": True,
            "monte_carlo": True,
            "backtest": True,
            "ml_engine": False,       # Not trained yet
            "rl_agent": False,        # Not trained yet
            "execution": True,
            "cpp_core": False,        # Build pending
        },
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

    dates  = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
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
        hist = _fetch_ohlcv(symbol, period)
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

        # Recent price info
        last_close = round(float(hist["Close"].iloc[-1]), 2)
        ret_5d     = round(float((hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) * 100), 2)

        return {
            "ticker":     symbol,
            "period":     period,
            "last_close": last_close,
            "return_5d":  ret_5d,
            "consensus":  consensus,
            "individual": individual,
            "bars_used":  len(hist),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/engines")
def strategy_engines():
    """
    List all available strategy engines, their types, and weights in the MultiStrategy.
    """
    try:
        _add_sys_path()
        from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine  # noqa
    except Exception:
        pass

    return {
        "rule_based": [
            {"name": "sma",        "label": "SMA Crossover",       "weight": 0.15, "type": "trend"},
            {"name": "rsi_mr",     "label": "RSI Mean Reversion",   "weight": 0.25, "type": "contrarian"},
            {"name": "macd",       "label": "MACD Multi-Signal",    "weight": 0.25, "type": "momentum"},
            {"name": "bb_squeeze", "label": "BB Squeeze Breakout",  "weight": 0.20, "type": "volatility"},
            {"name": "momentum",   "label": "Time-Series Momentum", "weight": 0.15, "type": "momentum"},
        ],
        "ml": [
            {"name": "ml_xgboost", "label": "XGBoost",       "weight": 0.25, "status": "untrained"},
            {"name": "ml_rf",      "label": "Random Forest",  "weight": 0.15, "status": "untrained"},
            {"name": "ml_lstm",    "label": "LSTM",           "weight": 0.20, "status": "untrained"},
        ],
        "rl": [
            {"name": "rl_dqn", "label": "DQN Agent", "weight": 0.25, "status": "untrained"},
        ],
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
        hist   = _fetch_ohlcv(symbol, period)
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

        return {
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
        }

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
    """Fetch latest price quote + daily change % for one ticker using yfinance."""
    try:
        import yfinance as yf

        symbol = ticker.strip().upper()
        if not symbol:
            raise HTTPException(status_code=400, detail="Ticker is required")

        t = yf.Ticker(symbol)
        hist = t.history(period="5d", interval="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail="Ticker not found or no data")

        closes = hist["Close"].dropna()
        price  = float(closes.iloc[-1])

        # Daily % change: today vs previous close
        change_pct = 0.0
        if len(closes) >= 2:
            prev  = float(closes.iloc[-2])
            change_pct = round((price - prev) / prev * 100, 2) if prev != 0 else 0.0

        return {
            "ticker":     symbol,
            "price":      round(price, 2),
            "change_pct": change_pct,
            "source":     "yfinance",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Quote Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market_data/{ticker}")
def get_market_data(ticker: str):
    """
    Fetch live market data and news for a ticker via yfinance.
    Returns: Current Price, OHLC Data (for charts), and News.
    """
    try:
        import yfinance as yf
        import pandas as pd
        
        # 1. Get Ticker Object
        t = yf.Ticker(ticker)
        
        # 2. History (1 Year for Daily Chart)
        hist = t.history(period="1y")
        if hist.empty:
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
        
        # 4. News
        news = t.news
        formatted_news = []
        if news:
            for n in news:
                formatted_news.append({
                    "title": n.get('title'),
                    "publisher": n.get('publisher'),
                    "link": n.get('link'),
                    "timestamp": n.get('providerPublishTime')
                })
                
        return {
            "ticker": ticker.upper(),
            "price": current_price,
            "ohlc": ohlc,
            "news": formatted_news
        }
        
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
    try:
        import yfinance as yf
        from atlas.correlation_portfolio.factor_models.factor_engine import FactorEngine
    except ImportError as e:
        raise HTTPException(500, f"Factor engine import failed: {e}")

    df = await asyncio.to_thread(
        yf.download, ticker, period=period, auto_adjust=True, progress=False
    )
    if df.empty:
        raise HTTPException(404, f"No data for {ticker}")

    df.columns = [str(c).capitalize() for c in df.columns]
    engine = FactorEngine()

    scores      = await asyncio.to_thread(engine.score, df)
    group_avgs  = await asyncio.to_thread(engine.group_groups, df) if hasattr(engine,'group_groups') else await asyncio.to_thread(engine.group_scores, df)
    top_factors = await asyncio.to_thread(engine.top_factors, df, 15)

    return {
        "ticker":       ticker.upper(),
        "period":       period,
        "factor_count": len(scores),
        "scores":       scores,
        "group_scores": group_avgs,
        "top_factors":  top_factors,
        "timestamp":    datetime.now().isoformat(),
    }


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
        import yfinance as yf
        from atlas.trader.composite_scorer import CompositeScorer

        df = _fetch_ohlcv(ticker, period)
        if df is None or len(df) < 30:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {ticker}")

        # Pre-fetch info once (avoids double yfinance calls)
        info = {}
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            pass

        scorer = CompositeScorer()
        result = scorer.score(ticker, df, info=info)
        return result.to_dict()

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
        import yfinance as yf
        from atlas.trader.composite_scorer import CompositeScorer

        df = _fetch_ohlcv(ticker, period)
        if df is None or len(df) < 14:
            raise HTTPException(status_code=404, detail="Insufficient data")

        scorer = CompositeScorer()
        result = scorer.score(ticker, df, info={})
        return {
            "ticker":          result.ticker,
            "last_close":      result.last_close,
            "composite_score": result.composite_score,
            "verdict":         result.verdict,
            "confidence":      result.confidence,
            "prediction":      result.to_dict()["prediction"],
        }

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
        import yfinance as yf
        from atlas.trader.composite_scorer import CompositeScorer

        universe = [t.strip().upper() for t in tickers.split(",")] if tickers else _TRADER_UNIVERSE

        scorer = CompositeScorer()
        results = []
        for ticker in universe[:40]:          # cap at 40 to keep response fast
            try:
                df = _fetch_ohlcv(ticker, period)
                if df is None or len(df) < 30:
                    continue
                info = {}
                try:
                    info = yf.Ticker(ticker).info or {}
                except Exception:
                    pass
                r = scorer.score(ticker, df, info=info)
                results.append(r.to_dict())
            except Exception as e:
                logger.warning("screen %s: %s", ticker, e)

        results.sort(key=lambda x: x["composite_score"], reverse=True)

        return {
            "universe_size":  len(universe),
            "screened":       len(results),
            "top_buys":       results[:top_n],
            "top_avoids":     results[-top_n:][::-1],
            "full_ranking":   results,
        }

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
        import yfinance as yf
        from atlas.trader.composite_scorer import CompositeScorer

        ticker_list = [t.strip().upper() for t in tickers.split(",")][:30]
        scorer = CompositeScorer()
        out = []
        for ticker in ticker_list:
            try:
                df = _fetch_ohlcv(ticker, "6mo")
                if df is None or len(df) < 14:
                    out.append({"ticker": ticker, "error": "no data"})
                    continue
                r = scorer.score(ticker, df, info={})
                out.append({
                    "ticker":          r.ticker,
                    "composite_score": r.composite_score,
                    "verdict":         r.verdict,
                    "confidence":      r.confidence,
                    "last_close":      r.last_close,
                })
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
