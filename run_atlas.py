"""
Run Atlas - Browser Edition
===========================
Launcher script for the browser-based Atlas environment.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


# Add python/src to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

from atlas.assistants.aria import ARIA
from atlas.assistants.aria.tools.create_file import CreateFileTool
from atlas.assistants.aria.tools.execute_code import ExecuteCodeTool
from atlas.assistants.aria.tools.read_file import ReadFileTool
from atlas.assistants.aria.tools.web_search import WebSearchTool

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8088
DEFAULT_ARIA_MODEL = "llama3.2:1b"
FAST_BROWSER_SYSTEM_PROMPT = (
    "You are ARIA, Atlas's local assistant. "
    "Answer clearly and directly in the user's language. "
    "Keep responses concise unless asked for detail."
)


def _configure_stdout_utf8() -> None:
    """Configure stdout/stderr to avoid UnicodeEncodeError on Windows."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _safe_print(message: str) -> None:
    """Print text without crashing if terminal encoding is limited."""
    try:
        print(message)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="replace").decode("ascii")
        print(fallback)


def _find_governance_dir(root: Path) -> Path | None:
    """Find the governance folder using common naming variants."""
    candidates = (
        "Project_Governance",
        "project_governance",
        "Project Governance",
        "project governance",
    )

    for candidate in candidates:
        path = root / candidate
        if path.is_dir():
            return path

    for child in root.iterdir():
        normalized = child.name.lower().replace("_", " ")
        if child.is_dir() and "governance" in normalized:
            return child
    return None


def _build_governance_prompt_context(
    root: Path,
    max_chars_per_file: int = 1200,
) -> str:
    """
    Build a compact governance digest so ARIA can answer project questions quickly.
    """
    governance_dir = _find_governance_dir(root)
    if not governance_dir:
        return ""

    markdown_files = sorted(governance_dir.glob("*.md"))
    if not markdown_files:
        return ""

    index_lines: list[str] = []
    digest_blocks: list[str] = []

    for markdown_file in markdown_files:
        size = markdown_file.stat().st_size
        index_lines.append(f"- {markdown_file.name} ({size} bytes)")

        content = markdown_file.read_text(encoding="utf-8", errors="replace").strip()
        snippet = content[:max_chars_per_file]
        if len(content) > max_chars_per_file:
            snippet += "\n...[truncated]"
        digest_blocks.append(f"### {markdown_file.name}\n{snippet}")

    return (
        "## ATLAS Project Governance Context\n"
        f"Primary folder: {governance_dir.name}\n\n"
        "Available files:\n"
        + "\n".join(index_lines)
        + "\n\n"
        "When users ask about roadmap, workflow, governance, or project status, use this context "
        "and use the read_file tool for full-file details.\n\n"
        "### Governance File Extracts\n"
        + "\n\n".join(digest_blocks)
    )


def _register_browser_tools(aria: ARIA, root: Path) -> int:
    """Register tools needed in browser mode."""
    tools = [
        WebSearchTool(),
        CreateFileTool(base_dir=str(root / "outputs")),
        ExecuteCodeTool(),
        ReadFileTool(base_dir=str(root)),
    ]

    registered = 0
    for tool in tools:
        try:
            aria.register_tool(tool)
            registered += 1
        except Exception as exc:
            _safe_print(f"   -> Warning: failed to register '{tool.name}': {exc}")
    return registered


def _env_enabled(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _is_port_available(host: str, port: int) -> bool:
    """
    Return True when the OS allows binding host:port.

    Uses exclusive bind on Windows to avoid false positives with wildcard binds.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _resolve_server_port(host: str = DEFAULT_HOST) -> int:
    """
    Resolve a usable port for the local server.

    Priority:
    1) ATLAS_PORT env var (if valid)
    2) DEFAULT_PORT (8088), or next free ports
    """
    preferred_port = DEFAULT_PORT
    env_port = os.getenv("ATLAS_PORT")
    if env_port:
        try:
            parsed = int(env_port)
            if 1 <= parsed <= 65535:
                preferred_port = parsed
            else:
                _safe_print(
                    f"WARN: ATLAS_PORT={env_port!r} out of range. Using {DEFAULT_PORT}."
                )
        except ValueError:
            _safe_print(
                f"WARN: ATLAS_PORT={env_port!r} is not a number. Using {DEFAULT_PORT}."
            )

    for offset in range(0, 50):
        candidate = preferred_port + offset
        if candidate > 65535:
            break
        if _is_port_available(host, candidate):
            if candidate != preferred_port:
                _safe_print(
                    f"   -> Port {preferred_port} is busy. Switching to {candidate}."
                )
            return candidate

    raise RuntimeError(
        f"No free port available starting from {preferred_port}. "
        "Set ATLAS_PORT to a different value."
    )


def _open_browser_delayed(port: int) -> None:
    """Open browser after the server starts."""
    time.sleep(3)
    _safe_print("\n[3/3] Opening Atlas Interface...")
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    _configure_stdout_utf8()

    _safe_print("=" * 60)
    _safe_print("ATLAS SYSTEM LAUNCHER")
    _safe_print("=" * 60)
    _safe_print("Starting Atlas in Browser Mode (Custom Build)...")

    _safe_print("\n[1/3] Checking LLM Backend (Ollama)...")
    try:
        import requests

        response = requests.get("http://localhost:11434/", timeout=3)
        if response.status_code == 200:
            _safe_print("OK: Ollama is running.")
        else:
            _safe_print("WARN: Ollama responded with an unexpected status.")
    except Exception:
        _safe_print("WARN: Ollama does not appear to be running.")
        _safe_print("   -> Attempting to start 'ollama serve' in background...")
        try:
            subprocess.Popen(
                "ollama serve",
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            _safe_print("   -> Launched Ollama. Waiting 5s...")
            time.sleep(5)
        except Exception as exc:
            _safe_print(f"ERROR: Failed to auto-start Ollama: {exc}")
            _safe_print("Please run 'ollama serve' in a separate terminal.")

    _safe_print("\n[2/3] Starting ARIA Server...")
    try:
        server_port = _resolve_server_port(DEFAULT_HOST)
    except RuntimeError as exc:
        _safe_print(f"ERROR: {exc}")
        return

    _safe_print(f"   -> Hosting Frontend at http://localhost:{server_port}")
    _safe_print(f"   -> Hosting API at http://localhost:{server_port}/query")

    threading.Thread(target=_open_browser_delayed, args=(server_port,), daemon=True).start()

    try:
        import uvicorn
        from apps.server import server

        aria_model = os.getenv("ARIA_MODEL", DEFAULT_ARIA_MODEL).strip() or DEFAULT_ARIA_MODEL
        _safe_print(f"   -> Initializing ARIA Neural Engine ({aria_model})...")
        aria = ARIA(model=aria_model)

        if _env_enabled("ATLAS_FAST_PROMPT", "1"):
            aria.system_prompt = FAST_BROWSER_SYSTEM_PROMPT
            _safe_print("   -> Fast browser prompt enabled (ATLAS_FAST_PROMPT=0 to disable).")

        if _env_enabled("ATLAS_ENABLE_ARIA_TOOLS", "0"):
            registered_tools = _register_browser_tools(aria, PROJECT_ROOT)
            _safe_print(f"   -> Registered {registered_tools} tools for browser mode.")
        else:
            registered_tools = 0
            _safe_print("   -> Tool calling disabled for fast browser chat (ATLAS_ENABLE_ARIA_TOOLS=1 to enable).")

        if _env_enabled("ATLAS_ENABLE_GOV_CONTEXT", "0"):
            governance_context = _build_governance_prompt_context(PROJECT_ROOT)
            if governance_context:
                aria.system_prompt = f"{aria.system_prompt}\n\n{governance_context}"
                _safe_print("   -> Project governance context loaded.")
            else:
                _safe_print("   -> Project governance context not found (skipped).")
        else:
            _safe_print("   -> Governance context disabled (ATLAS_ENABLE_GOV_CONTEXT=1 to enable).")

        server.aria_instance = aria
        uvicorn.run(server.app, host=DEFAULT_HOST, port=server_port, log_level="info")

    except ImportError:
        _safe_print("\nERROR: Missing dependencies.")
        _safe_print("Please run: pip install -r requirements.txt")
    except Exception as exc:
        _safe_print(f"\nERROR: Server error: {exc}")


if __name__ == "__main__":
    main()

