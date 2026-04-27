"""
ARIA WhatsApp Command Station — 24/7

Run Atlas on a dedicated machine and control it remotely via WhatsApp.
Supports slash commands (real data from Atlas API) + free-form chat (Anthropic API).

Setup:
  1. pip install twilio flask requests anthropic
  2. Set env vars: TWILIO_SID, TWILIO_TOKEN, TWILIO_WA_NUMBER, ANTHROPIC_API_KEY
  3. Expose this server: ngrok http 5001  (or point your VPS)
  4. Set Twilio sandbox webhook → https://your-url/whatsapp
  5. python -m atlas.assistants.aria.integrations.whatsapp_bot

Commands Mau can send:
  /help              — command list
  /status            — Atlas server health
  /analyze AAPL      — MMO quantum analysis
  /signal            — latest signals from Signal Terminal
  /market            — quick market snapshot (SPY, QQQ, BTC, GLD)
  /portfolio         — portfolio summary
  /whale             — recent whale alerts
  /scan              — quantum scanner top movers
  /ping              — latency test
  Anything else      — free-form chat with ARIA via Claude API
"""

from __future__ import annotations

import os
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from flask import Flask, request

logger = logging.getLogger(__name__)


# ── Config from env ────────────────────────────────────────────────────────────
ATLAS_API_URL   = os.getenv("ATLAS_API_URL",  "http://localhost:8088")
TWILIO_SID      = os.getenv("TWILIO_SID",     "")
TWILIO_TOKEN    = os.getenv("TWILIO_TOKEN",   "")
TWILIO_WA_FROM  = os.getenv("TWILIO_WA_NUMBER", "whatsapp:+14155238886")
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
AUTHORIZED_NUMBERS = set(
    n.strip() for n in os.getenv("WHATSAPP_AUTHORIZED", "").split(",") if n.strip()
)
PORT = int(os.getenv("WHATSAPP_PORT", "5001"))


# ── Atlas API helpers ──────────────────────────────────────────────────────────

def _get(path: str, timeout: int = 10) -> dict:
    try:
        r = requests.get(f"{ATLAS_API_URL}{path}", timeout=timeout)
        return r.json() if r.ok else {"error": r.status_code}
    except Exception as e:
        return {"error": str(e)}


# ── Command handlers ───────────────────────────────────────────────────────────

def cmd_help(_args: str) -> str:
    return (
        "🤖 *ARIA Command Station*\n\n"
        "*Market*\n"
        "/analyze TICK — Quantum state analysis\n"
        "/signal       — Latest signals feed\n"
        "/market       — SPY · QQQ · BTC · GLD snapshot\n"
        "/portfolio    — Portfolio summary\n"
        "/whale        — Recent whale alerts\n"
        "/scan         — Quantum scanner movers\n\n"
        "*System*\n"
        "/status       — Atlas server health\n"
        "/ping         — Latency check\n"
        "/sysinfo      — CPU · RAM · Disk · Uptime\n"
        "/restart      — Restart Atlas server\n"
        "/upgrade      — git pull + restart\n\n"
        "Or just talk to me — I'll answer as ARIA 💬"
    )


def cmd_ping(_args: str) -> str:
    import time
    t0 = time.time()
    data = _get("/api/health") or _get("/api/status")
    ms = int((time.time() - t0) * 1000)
    if "error" in data:
        return f"⚠️ Atlas unreachable ({ms}ms)\n`{data['error']}`"
    return f"✅ Atlas online — {ms}ms\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"


def cmd_status(_args: str) -> str:
    data = _get("/api/agents/status")
    if "error" in data:
        return f"⚠️ Could not reach Atlas\n`{data['error']}`"
    agents = data.get("agents_count", 0)
    avail  = data.get("available", False)
    icon   = "✅" if avail else "⚠️"
    lines  = [f"{icon} *Atlas Status*"]
    lines.append(f"Agents: {agents} {'ready' if avail else '(stub mode)'}")
    lines.append(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    return "\n".join(lines)


def cmd_analyze(ticker: str) -> str:
    ticker = (ticker.strip().upper() or "SPY")[:10]
    data = _get(f"/api/mmo/quantum_state/{ticker}", timeout=20)
    if "error" in data and data.get("last_close", 0) == 0:
        return f"⚠️ Could not analyze {ticker}: {data.get('error', 'no data')}"

    verdict  = data.get("quantum_verdict", "?")
    entropy  = data.get("entropy", 0)
    collapse = data.get("collapse_prob", 0)
    close    = data.get("last_close", 0)
    trend    = data.get("trend_pct", 0)
    vol      = data.get("annual_vol_pct", 0)
    thermal  = data.get("thermal", {}).get("phase", "?")
    berry    = data.get("berry_phase", {}).get("regime_cycle", "?")
    tau      = data.get("decoherence_tau", 0)

    amps = data.get("amplitudes", {})
    amp_lines = "  ".join(
        f"{k[:4]}:{v:.0%}" for k, v in sorted(amps.items(), key=lambda x: -x[1])
    )

    return (
        f"⟨ψ⟩ *{ticker} Quantum Analysis*\n\n"
        f"Verdict: *{verdict}*\n"
        f"Close: ${close:,.2f}  ({trend:+.1f}% 6mo)\n"
        f"Vol: {vol:.1f}%  τ: {tau:.2f}d\n"
        f"Thermal: {thermal}  Berry: {berry}\n"
        f"Collapse prob: {collapse:.0%}  Entropy: {entropy:.2f}\n"
        f"Amplitudes: {amp_lines}"
    )


def cmd_signal(_args: str) -> str:
    data = _get("/api/signals/?limit=5")
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ Signal Terminal error: {data['error']}"
    if not data:
        return "📭 No signals yet — collector may be warming up."

    signals = data if isinstance(data, list) else data.get("signals", [])[:5]
    if not signals:
        return "📭 No signals in feed."

    lines = ["📡 *Latest Signals*\n"]
    for s in signals[:5]:
        score  = s.get("composite_score", 0)
        source = s.get("source_type", "?").upper()
        title  = s.get("title", "?")[:60]
        lines.append(f"[{score:.2f}] [{source}] {title}")
    return "\n".join(lines)


def cmd_market(_args: str) -> str:
    tickers = ["SPY", "QQQ", "BTC-USD", "GLD"]
    lines   = ["📊 *Market Snapshot*\n"]
    for t in tickers:
        d = _get(f"/api/mmo/quantum_state/{t}", timeout=15)
        close   = d.get("last_close", 0)
        trend   = d.get("trend_pct", 0)
        verdict = d.get("quantum_verdict", "?")
        icon    = "🟢" if trend > 0 else "🔴"
        lines.append(f"{icon} *{t}* ${close:,.2f} ({trend:+.1f}%) — {verdict}")
    return "\n".join(lines)


def cmd_whale(_args: str) -> str:
    data = _get("/api/signals/whale?limit=5")
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ Whale data error: {data['error']}"
    alerts = data if isinstance(data, list) else data.get("alerts", [])
    if not alerts:
        return "🐋 No whale alerts in recent window."
    lines = ["🐋 *Whale Alerts*\n"]
    for a in alerts[:5]:
        ticker = a.get("ticker", "?")
        vol    = a.get("volume", 0)
        action = a.get("action", "?").upper()
        lines.append(f"• {ticker} — {action} — Vol: {vol:,.0f}")
    return "\n".join(lines)


def cmd_scan(_args: str) -> str:
    data = _get("/api/mmo/quantum_state/SPY")
    # Scanner hits individual tickers — summarize top signals from scanner cache
    tickers = ["AAPL", "TSLA", "NVDA", "META", "AMZN"]
    lines   = ["🔭 *Quantum Scanner*\n"]
    for t in tickers:
        d      = _get(f"/api/mmo/quantum_state/{t}", timeout=12)
        verdict = d.get("quantum_verdict", "?")
        entropy = d.get("entropy", 1.0)
        bar     = "█" * int((1 - entropy) * 5) + "░" * int(entropy * 5)
        lines.append(f"*{t}* [{bar}] {verdict}")
    return "\n".join(lines)


def cmd_portfolio(_args: str) -> str:
    data = _get("/api/portfolio/summary")
    if isinstance(data, dict) and "error" in data:
        return "⚠️ Portfolio summary not available — open Atlas in browser."
    total = data.get("total_value", 0)
    pnl   = data.get("total_pnl", 0)
    count = data.get("positions", 0)
    icon  = "🟢" if pnl >= 0 else "🔴"
    return (
        f"{icon} *Portfolio*\n\n"
        f"Value: ${total:,.2f}\n"
        f"P&L: {'+' if pnl >= 0 else ''}{pnl:,.2f}\n"
        f"Positions: {count}"
    )


def cmd_sysinfo(_args: str) -> str:
    """Return basic machine stats for the dedicated 24/7 machine."""
    try:
        import psutil
        cpu     = psutil.cpu_percent(interval=1)
        mem     = psutil.virtual_memory()
        disk    = psutil.disk_usage(str(ROOT_PATH))
        uptime  = time.time() - psutil.boot_time()
        hours   = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return (
            f"💻 *Atlas Machine*\n\n"
            f"CPU:    {cpu:.0f}%\n"
            f"RAM:    {mem.used / 1e9:.1f} / {mem.total / 1e9:.1f} GB  ({mem.percent:.0f}%)\n"
            f"Disk:   {disk.used / 1e9:.1f} / {disk.total / 1e9:.1f} GB  ({disk.percent:.0f}%)\n"
            f"Uptime: {hours}h {minutes}m\n"
            f"Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except ImportError:
        return (
            f"💻 Atlas time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "(install psutil for full stats: pip install psutil)"
        )
    except Exception as e:
        return f"⚠️ sysinfo error: {e}"


def cmd_restart(_args: str) -> str:
    """
    Kill the Atlas server subprocess — the daemon auto-restarts it.
    Sends SIGTERM to the Atlas process (atlas_server.pid), NOT the daemon.
    """
    import os, signal as _sig
    pid_file = ROOT_PATH / "atlas_server.pid"
    if not pid_file.exists():
        return (
            "⚠️ atlas_server.pid not found.\n"
            "Atlas may not be running under run_daemon.py.\n"
            "Start it with: python run_daemon.py"
        )
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, _sig.SIGTERM)
        return (
            f"🔄 Atlas restart triggered (PID {pid} → SIGTERM).\n"
            "Daemon will restart it in ~5 seconds.\n"
            "Check with /ping"
        )
    except ProcessLookupError:
        return "⚠️ Atlas process not found — it may have already stopped. Daemon will restart it."
    except Exception as e:
        return f"⚠️ Restart failed: {e}"


def cmd_upgrade(_args: str) -> str:
    """Trigger a git pull + restart via the daemon's --upgrade path."""
    import subprocess, sys
    from pathlib import Path
    try:
        # Run upgrade script non-blocking — daemon will handle restart
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(ROOT_PATH),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return f"⚠️ git pull failed:\n{result.stderr.strip()[:300]}"

        changed = result.stdout.strip()
        if "Already up to date" in changed:
            return "✅ Already up to date — no restart needed."

        # Pull succeeded — now restart
        restart_msg = cmd_restart("")
        return f"✅ Code updated:\n{changed[:200]}\n\n{restart_msg}"
    except subprocess.TimeoutExpired:
        return "⚠️ git pull timed out (60s). Check network."
    except Exception as e:
        return f"⚠️ Upgrade error: {e}"


# Resolve Atlas root for daemon ops (2 levels up from this file)
ROOT_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent


# ── Command router ─────────────────────────────────────────────────────────────

COMMANDS: dict[str, callable] = {
    "/help":      lambda a: cmd_help(a),
    "/status":    lambda a: cmd_status(a),
    "/ping":      lambda a: cmd_ping(a),
    "/analyze":   lambda a: cmd_analyze(a),
    "/signal":    lambda a: cmd_signal(a),
    "/signals":   lambda a: cmd_signal(a),
    "/market":    lambda a: cmd_market(a),
    "/whale":     lambda a: cmd_whale(a),
    "/scan":      lambda a: cmd_scan(a),
    "/portfolio": lambda a: cmd_portfolio(a),
    # Remote machine management
    "/sysinfo":   lambda a: cmd_sysinfo(a),
    "/restart":   lambda a: cmd_restart(a),
    "/upgrade":   lambda a: cmd_upgrade(a),
    # Placeholder stubs — noted for future work
    "/tasks":     lambda _: "📋 ClickUp integration coming soon. Tasks tracked in Atlas Signal Terminal.",
    "/note":      lambda a: f"📝 Notion integration coming soon. Noted locally: {a[:100] if a else '(empty)'}",
}


def route_command(text: str) -> Optional[str]:
    """Route /command [args] to its handler. Returns None if not a command."""
    if not text.startswith("/"):
        return None
    parts = text.split(None, 1)
    cmd   = parts[0].lower()
    args  = parts[1] if len(parts) > 1 else ""
    handler = COMMANDS.get(cmd)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            logger.exception("Command %s failed", cmd)
            return f"⚠️ {cmd} failed: {e}"
    return f"❓ Unknown command `{cmd}`. Type /help."


# ── Free-form chat via Anthropic API ──────────────────────────────────────────

_chat_history: list[dict] = []  # simple in-memory conversation buffer (last 10 turns)
_history_lock = threading.Lock()

ARIA_SYSTEM = (
    "You are ARIA — Atlas's AI assistant. You are concise, intelligent, and professional. "
    "You help Mau (the owner) monitor markets, analyze data, and manage his Atlas platform remotely via WhatsApp. "
    "Keep answers SHORT — WhatsApp messages, not essays. "
    "If asked about specific live data you can't access, remind Mau he can use slash commands like /analyze or /market."
)


def chat_with_aria(user_message: str) -> str:
    if not ANTHROPIC_KEY:
        return "⚠️ ARIA chat unavailable — ANTHROPIC_API_KEY not set."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        with _history_lock:
            _chat_history.append({"role": "user", "content": user_message})
            # Keep last 10 messages (5 turns)
            messages = _chat_history[-10:]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=ARIA_SYSTEM,
            messages=messages,
        )
        reply = response.content[0].text.strip()

        with _history_lock:
            _chat_history.append({"role": "assistant", "content": reply})
            # Trim history
            while len(_chat_history) > 20:
                _chat_history.pop(0)

        return f"🤖 {reply}"
    except Exception as e:
        logger.exception("Anthropic chat failed")
        return f"⚠️ ARIA unavailable: {e}"


# ── Flask webhook ──────────────────────────────────────────────────────────────

flask_app = Flask(__name__)


@flask_app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number  = request.form.get("From", "")
    message_body = request.form.get("Body", "").strip()

    logger.info("WA incoming from=%s body=%r", from_number, message_body[:80])

    # Authorization check — if list configured, only allow listed numbers
    if AUTHORIZED_NUMBERS and from_number not in AUTHORIZED_NUMBERS:
        logger.warning("Rejected unauthorized sender: %s", from_number)
        return _twiml_response("🔒 Unauthorized.")

    if not message_body:
        return _twiml_response("(empty message)")

    # Route: command or chat
    reply = route_command(message_body)
    if reply is None:
        reply = chat_with_aria(message_body)

    return _twiml_response(reply)


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "online", "service": "ARIA WhatsApp Command Station", "time": datetime.utcnow().isoformat()}


def _twiml_response(text: str):
    """Wrap text in a Twilio MessagingResponse."""
    try:
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(text)
        return str(resp), 200, {"Content-Type": "text/xml"}
    except ImportError:
        # Twilio not installed — return plain text (for testing without Twilio)
        return text, 200, {"Content-Type": "text/plain"}


# ── Outbound helper (send a message proactively) ───────────────────────────────

def send_whatsapp(to: str, message: str) -> Optional[str]:
    """
    Send a proactive WhatsApp message from Atlas to Mau.
    Useful for alerts: call this from signal_terminal or any monitor.

    Args:
        to: Full WhatsApp number e.g. 'whatsapp:+521234567890'
        message: Message text

    Returns:
        Twilio message SID or None on failure.
    """
    if not TWILIO_SID or not TWILIO_TOKEN:
        logger.warning("send_whatsapp: credentials not configured")
        return None
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WA_FROM,
            to=to if to.startswith("whatsapp:") else f"whatsapp:{to}",
        )
        return msg.sid
    except Exception as e:
        logger.error("send_whatsapp failed: %s", e)
        return None


# ── Entry point ────────────────────────────────────────────────────────────────

def run(port: int = PORT, use_ngrok: bool = False):
    """
    Start the ARIA WhatsApp Command Station.

    Usage:
        from atlas.assistants.aria.integrations.whatsapp_bot import run
        run()

    Or from CLI:
        python -m atlas.assistants.aria.integrations.whatsapp_bot
        python -m atlas.assistants.aria.integrations.whatsapp_bot --ngrok
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [WA] %(message)s")

    if use_ngrok:
        try:
            from pyngrok import ngrok
            tunnel = ngrok.connect(port)
            public_url = tunnel.public_url
            print(f"\n🌐 Ngrok tunnel: {public_url}")
            print(f"   Webhook URL:  {public_url}/whatsapp")
            print("   → Paste this URL in Twilio sandbox settings\n")
        except ImportError:
            print("⚠️  pyngrok not installed: pip install pyngrok")

    print("=" * 60)
    print("🤖 ARIA WhatsApp Command Station")
    print("=" * 60)
    print(f"Atlas API:  {ATLAS_API_URL}")
    print(f"Port:       {port}")
    print(f"Auth nums:  {AUTHORIZED_NUMBERS or 'open (set WHATSAPP_AUTHORIZED)'}")
    print(f"Anthropic:  {'✅ configured' if ANTHROPIC_KEY else '❌ not set'}")
    print(f"Twilio:     {'✅ configured' if TWILIO_SID else '❌ not set'}")
    print("=" * 60)
    print("Commands available: " + "  ".join(COMMANDS.keys()))
    print("=" * 60)

    flask_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    import sys
    run(use_ngrok="--ngrok" in sys.argv)
