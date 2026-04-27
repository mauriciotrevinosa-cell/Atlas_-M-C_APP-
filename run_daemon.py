"""
Atlas Daemon — 24/7 Watchdog
=============================
Starts run_atlas.py as a subprocess, monitors it, and auto-restarts on crash
with exponential back-off. Writes rotating logs to logs/daemon.log.

Usage:
    python run_daemon.py              # normal mode
    python run_daemon.py --no-browser # suppress browser open (headless server)
    python run_daemon.py --upgrade    # git pull + restart, then exit

Environment:
    DAEMON_MAX_RESTARTS   — give up after N crashes in MAX_WINDOW_SEC (default 10)
    DAEMON_MAX_WINDOW_SEC — window for crash counting (default 300 s)
    DAEMON_UPGRADE_CMD    — shell command run during --upgrade (default: git pull)
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE    = LOGS_DIR / "daemon.log"
PID_FILE    = ROOT / "atlas_daemon.pid"   # daemon's own PID
ATLAS_PID_FILE = ROOT / "atlas_server.pid"  # Atlas subprocess PID (for /restart)
ATLAS_SCRIPT = ROOT / "run_atlas.py"

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_RESTARTS = int(os.getenv("DAEMON_MAX_RESTARTS", "10"))
MAX_WINDOW_SEC = int(os.getenv("DAEMON_MAX_WINDOW_SEC", "300"))
UPGRADE_CMD = os.getenv("DAEMON_UPGRADE_CMD", "git pull --ff-only")

# Back-off: 2s, 4s, 8s … capped at 60s
BACKOFF_BASE = 2
BACKOFF_CAP = 60


# ── Logging ────────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [DAEMON] %(levelname)s  %(message)s")
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s [DAEMON] %(message)s"))

    logger = logging.getLogger("atlas_daemon")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(console)
    return logger


log = _setup_logging()


# ── PID management ─────────────────────────────────────────────────────────────

def _write_pid() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    for f in (PID_FILE, ATLAS_PID_FILE):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


# ── Upgrade logic ──────────────────────────────────────────────────────────────

def do_upgrade() -> bool:
    """Run the upgrade command. Returns True on success."""
    log.info("Upgrade requested — running: %s", UPGRADE_CMD)
    try:
        result = subprocess.run(
            UPGRADE_CMD,
            shell=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout.strip():
            log.info("Upgrade stdout:\n%s", result.stdout.strip())
        if result.stderr.strip():
            log.warning("Upgrade stderr:\n%s", result.stderr.strip())
        if result.returncode == 0:
            log.info("Upgrade succeeded.")
            return True
        log.error("Upgrade exited with code %d", result.returncode)
        return False
    except subprocess.TimeoutExpired:
        log.error("Upgrade timed out after 120 s.")
        return False
    except Exception as exc:
        log.error("Upgrade failed: %s", exc)
        return False


# ── Process manager ────────────────────────────────────────────────────────────

class AtlasProcess:
    """Manages a single Atlas subprocess lifecycle."""

    def __init__(self, extra_args: list[str]) -> None:
        self.extra_args = extra_args
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        cmd = [sys.executable, str(ATLAS_SCRIPT)] + self.extra_args
        log.info("Starting Atlas: %s", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )
        log.info("Atlas PID: %d", self.proc.pid)
        # Write subprocess PID so WhatsApp /restart can signal just Atlas
        try:
            ATLAS_PID_FILE.write_text(str(self.proc.pid), encoding="utf-8")
        except Exception:
            pass

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout: int = 10) -> None:
        if self.proc is None:
            return
        log.info("Stopping Atlas (PID %d)…", self.proc.pid)
        try:
            self.proc.terminate()
            self.proc.wait(timeout=timeout)
            log.info("Atlas stopped cleanly.")
        except subprocess.TimeoutExpired:
            log.warning("Atlas did not stop in %ds — killing.", timeout)
            self.proc.kill()
            self.proc.wait()
        self.proc = None

    def returncode(self) -> int | None:
        return self.proc.returncode if self.proc else None


# ── Watchdog loop ──────────────────────────────────────────────────────────────

def run_watchdog(atlas_args: list[str]) -> None:
    _write_pid()
    atlas = AtlasProcess(atlas_args)

    crash_times: list[float] = []
    restarts = 0
    backoff = BACKOFF_BASE
    shutdown_requested = False

    def _handle_signal(signum, _frame):
        nonlocal shutdown_requested
        log.info("Signal %d received — initiating shutdown.", signum)
        shutdown_requested = True
        atlas.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log.info("=" * 60)
    log.info("Atlas Daemon started — PID %d", os.getpid())
    log.info("Watching: %s", ATLAS_SCRIPT)
    log.info("Logs: %s", LOG_FILE)
    log.info("=" * 60)

    atlas.start()

    try:
        while not shutdown_requested:
            time.sleep(2)

            if atlas.is_alive():
                backoff = BACKOFF_BASE  # reset back-off while healthy
                continue

            rc = atlas.returncode()
            now = time.time()
            crash_times.append(now)

            # Prune crash times outside window
            crash_times = [t for t in crash_times if now - t <= MAX_WINDOW_SEC]

            log.warning(
                "Atlas exited (code=%s). Crashes in last %ds: %d / %d",
                rc, MAX_WINDOW_SEC, len(crash_times), MAX_RESTARTS,
            )

            if shutdown_requested:
                break

            if len(crash_times) >= MAX_RESTARTS:
                log.error(
                    "Too many crashes (%d in %ds). Daemon giving up. "
                    "Fix the error and restart run_daemon.py.",
                    MAX_RESTARTS, MAX_WINDOW_SEC,
                )
                break

            log.info("Restarting in %ds… (attempt #%d)", backoff, restarts + 1)
            time.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_CAP)
            restarts += 1
            atlas.start()

    except KeyboardInterrupt:
        log.info("KeyboardInterrupt — shutting down.")
        atlas.stop()
    finally:
        atlas.stop()
        _remove_pid()
        log.info("Daemon exited. Total restarts: %d", restarts)


# ── Entry ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Atlas 24/7 Daemon Watchdog")
    p.add_argument("--no-browser", action="store_true",
                   help="Pass --no-browser to run_atlas.py (headless mode)")
    p.add_argument("--upgrade", action="store_true",
                   help="Run git pull upgrade then restart Atlas")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.upgrade:
        ok = do_upgrade()
        if not ok:
            log.error("Upgrade failed — Atlas will NOT restart.")
            sys.exit(1)
        log.info("Upgrade complete — starting Atlas…")

    atlas_args: list[str] = []
    if args.no_browser:
        atlas_args.append("--no-project-map")

    run_watchdog(atlas_args)


if __name__ == "__main__":
    main()
