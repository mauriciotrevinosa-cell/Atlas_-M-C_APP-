"""
Run Atlas - Browser Edition
===========================
Launcher script for the browser-based Atlas environment.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path


# Add python/src to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

from atlas.assistants.aria import ARIA
from atlas.assistants.aria.tools import register_phase1_tools
from atlas.assistants.aria.tools.setup import register_all_tools
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


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _sample_names(items: list[str], limit: int = 8) -> str:
    if not items:
        return "-"
    if len(items) <= limit:
        return ", ".join(items)
    visible = ", ".join(items[:limit])
    return f"{visible}, ... (+{len(items) - limit} more)"


def _summarize_dir(path: Path) -> tuple[int, int, list[str]]:
    if not path.is_dir():
        return 0, 0, []
    dirs = []
    files = []
    try:
        for item in path.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                dirs.append(item.name)
            else:
                files.append(item.name)
    except Exception:
        return 0, 0, []
    return len(dirs), len(files), sorted(dirs + files, key=str.lower)


def _extract_desktop_views(index_html: Path) -> list[str]:
    content = _safe_read_text(index_html)
    if not content:
        return []
    matches = re.findall(r'id="view-([a-zA-Z0-9_-]+)"', content)
    unique = sorted(set(matches), key=str.lower)
    return unique


def _extract_fastapi_routes(server_file: Path) -> list[str]:
    content = _safe_read_text(server_file)
    if not content:
        return []
    matches = re.findall(
        r"@app\.(?:get|post|put|delete|patch|websocket)\(\s*[\"']([^\"']+)[\"']",
        content,
    )
    unique = sorted(set(matches), key=str.lower)
    return unique


def _build_project_visibility_report(root: Path) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("ATLAS PROJECT VISIBILITY REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Root: {root}")

    lines.append("\n[Section 1/7] Repository Areas")
    core_folders = [
        "apps",
        "python",
        "tests",
        "configs",
        "docs",
        "project_governance",
        "data",
        "outputs",
        "services",
        "cpp",
        "ui_web",
        "scripts",
        "legacy",
        "logs",
        "info_instructions",
        "trash",
    ]
    for name in core_folders:
        folder = root / name
        if not folder.exists():
            lines.append(f"- {name}/ -> not found")
            continue
        dir_count, file_count, sample = _summarize_dir(folder)
        lines.append(
            f"- {name}/ -> {dir_count} dirs, {file_count} files | sample: {_sample_names(sample, 6)}"
        )

    lines.append("\n[Section 2/7] Root Files")
    root_files = sorted(
        [p.name for p in root.iterdir() if p.is_file() and not p.name.startswith(".")],
        key=str.lower,
    )
    lines.append(f"- Root files ({len(root_files)}): {_sample_names(root_files, 20)}")

    lines.append("\n[Section 3/7] Python Source Visibility")
    atlas_src = root / "python" / "src" / "atlas"
    if atlas_src.is_dir():
        packages = sorted(
            [
                p.name
                for p in atlas_src.iterdir()
                if p.is_dir() and not p.name.startswith("_")
            ],
            key=str.lower,
        )
        lines.append(f"- python/src/atlas packages ({len(packages)}): {_sample_names(packages, 12)}")
    else:
        lines.append("- python/src/atlas not found")

    phase1_files = [
        root / "python" / "src" / "atlas" / "market_finance" / "data_layer.py",
        root / "python" / "src" / "atlas" / "market_finance" / "analytics_layer.py",
        root / "python" / "src" / "atlas" / "market_finance" / "simulation_layer.py",
        root / "python" / "src" / "atlas" / "market_finance" / "risk_layer.py",
        root / "python" / "src" / "atlas" / "market_finance" / "pipeline.py",
    ]
    phase1_visible = [p.relative_to(root).as_posix() for p in phase1_files if p.exists()]
    lines.append(f"- Official Phase 1 files ({len(phase1_visible)}): {_sample_names(phase1_visible, 5)}")

    recovered_modules = [
        root / "python" / "src" / "atlas" / "analytics" / "returns.py",
        root / "python" / "src" / "atlas" / "analytics" / "risk_metrics.py",
        root / "python" / "src" / "atlas" / "analytics" / "volatility.py",
        root / "python" / "src" / "atlas" / "analytics" / "correlation.py",
        root / "python" / "src" / "atlas" / "risk" / "portfolio_risk.py",
        root / "python" / "src" / "atlas" / "monte_carlo" / "multi_asset.py",
        root / "python" / "src" / "atlas" / "shared" / "finance_concepts.py",
        root / "python" / "src" / "atlas" / "assistants" / "aria" / "tools" / "explain_concept.py",
    ]
    recovered_visible = [
        p.relative_to(root).as_posix()
        for p in recovered_modules
        if p.exists()
    ]
    lines.append(
        f"- Recovered modules integrated ({len(recovered_visible)}/{len(recovered_modules)}): "
        f"{_sample_names(recovered_visible, 8)}"
    )

    lines.append("\n[Section 4/7] Frontend Sections (apps/desktop)")
    desktop_index = root / "apps" / "desktop" / "index.html"
    views = _extract_desktop_views(desktop_index)
    lines.append(f"- UI views discovered ({len(views)}): {_sample_names(views, 14)}")

    desktop_js = root / "apps" / "desktop"
    if desktop_js.is_dir():
        js_files = sorted(
            [
                p.name
                for p in desktop_js.glob("*.js")
                if p.name.lower() not in {"preload.js"}
            ],
            key=str.lower,
        )
        lines.append(f"- Desktop JS modules ({len(js_files)}): {_sample_names(js_files, 14)}")
    else:
        lines.append("- apps/desktop not found")

    lines.append("\n[Section 5/7] API Surface (apps/server/server.py)")
    routes = _extract_fastapi_routes(root / "apps" / "server" / "server.py")
    lines.append(f"- FastAPI routes discovered ({len(routes)}): {_sample_names(routes, 16)}")

    lines.append("\n[Section 6/7] Documentation and Governance")
    for doc_folder_name in ("docs", "project_governance"):
        doc_folder = root / doc_folder_name
        if not doc_folder.is_dir():
            lines.append(f"- {doc_folder_name}/ -> not found")
            continue
        md_files = sorted([p.name for p in doc_folder.glob("*.md")], key=str.lower)
        lines.append(
            f"- {doc_folder_name}/ markdown files ({len(md_files)}): {_sample_names(md_files, 10)}"
        )

    lines.append("\n[Section 7/7] Entrypoints and Execution")
    entrypoints = [
        "run_atlas.py",
        "run_aria.py",
        "run_server.py",
        "scripts/run_phase1_demo.py",
        "apps/server/start_server.bat",
        "START_ATLAS.bat",
        "run_desktop.ps1",
    ]
    for rel in entrypoints:
        path = root / rel
        status = "ok" if path.exists() else "missing"
        lines.append(f"- {rel} -> {status}")

    lines.append("\nRuntime access after launch:")
    lines.append("- Frontend: http://localhost:<port>")
    lines.append("- API docs: http://localhost:<port>/docs")
    lines.append("- Health: http://localhost:<port>/api/health")
    lines.append("=" * 60)
    return "\n".join(lines)


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


def _register_phase1_workflow_tools(aria: ARIA) -> list[str]:
    """Register official Atlas Phase 1 workflow tools for browser mode."""
    try:
        return register_phase1_tools(aria)
    except Exception as exc:
        _safe_print(f"   -> Warning: failed to register Phase 1 tools: {exc}")
        return []


def _register_recovered_aria_tools(aria: ARIA) -> list[str]:
    """Register recovered ARIA tools (education/knowledge modules)."""
    try:
        before = set(getattr(aria, "tools", {}).keys())
        register_all_tools(aria)
        after = set(getattr(aria, "tools", {}).keys())
        return sorted(after - before)
    except Exception as exc:
        _safe_print(f"   -> Warning: failed to register recovered ARIA tools: {exc}")
        return []


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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas launcher")
    parser.add_argument(
        "--project-map-only",
        action="store_true",
        help="Print a full project visibility report and exit.",
    )
    parser.add_argument(
        "--no-project-map",
        action="store_true",
        help="Skip project visibility report at startup.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the official Phase 1 market-finance demo workflow and exit.",
    )
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "SPY"])
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--n-paths", type=int, default=1500)
    parser.add_argument("--horizon-days", type=int, default=252)
    parser.add_argument("--loss-threshold", type=float, default=0.05)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def _run_phase1_demo(args: argparse.Namespace) -> int:
    from datetime import date, timedelta

    from atlas.market_finance.pipeline import Phase1Workflow

    today = date.today()
    start_date = args.start_date or (today - timedelta(days=365)).isoformat()
    end_date = args.end_date or today.isoformat()

    workflow = Phase1Workflow(output_root=str(PROJECT_ROOT / "outputs" / "runs"))
    summary = workflow.run(
        symbols=args.symbols,
        start_date=start_date,
        end_date=end_date,
        interval=args.interval,
        n_paths=args.n_paths,
        horizon_days=args.horizon_days,
        loss_threshold=args.loss_threshold,
        confidence=args.confidence,
        run_id=args.run_id,
    )

    _safe_print("=" * 60)
    _safe_print("ATLAS PHASE 1 DEMO COMPLETED")
    _safe_print("=" * 60)
    _safe_print(f"Run ID: {summary.run_id}")
    _safe_print(f"Run Dir: {summary.run_dir}")
    _safe_print(f"Manifest: {summary.manifest_path}")
    _safe_print(f"Portfolio VaR: {summary.key_metrics.get('portfolio_var'):.6f}")
    _safe_print(f"Portfolio CVaR: {summary.key_metrics.get('portfolio_cvar'):.6f}")
    _safe_print(
        "P(loss > threshold): "
        f"{summary.key_metrics.get('probability_loss_gt_threshold'):.6f}"
    )
    return 0


def main() -> None:
    _configure_stdout_utf8()
    args = _parse_args()

    show_project_map = _env_enabled("ATLAS_SHOW_PROJECT_MAP", "1") and not args.no_project_map
    if show_project_map:
        _safe_print(_build_project_visibility_report(PROJECT_ROOT))

    if args.project_map_only:
        return

    if args.demo:
        try:
            _run_phase1_demo(args)
        except Exception as exc:
            _safe_print(f"ERROR: Demo failed: {exc}")
        return

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

        if _env_enabled("ATLAS_ENABLE_PHASE1_TOOLS", "1"):
            phase1_tools = _register_phase1_workflow_tools(aria)
            if phase1_tools:
                _safe_print(
                    "   -> Phase 1 workflow tools active: "
                    + ", ".join(phase1_tools)
                )
            else:
                _safe_print("   -> Phase 1 workflow tools were requested but none were registered.")
        else:
            _safe_print("   -> Phase 1 workflow tools disabled (ATLAS_ENABLE_PHASE1_TOOLS=0).")

        if _env_enabled("ATLAS_ENABLE_RECOVERED_TOOLS", "1"):
            recovered_tools = _register_recovered_aria_tools(aria)
            if recovered_tools:
                _safe_print(
                    "   -> Recovered ARIA tools active: "
                    + ", ".join(recovered_tools)
                )
            else:
                _safe_print("   -> Recovered ARIA tools requested but none were registered.")
        else:
            _safe_print("   -> Recovered ARIA tools disabled (ATLAS_ENABLE_RECOVERED_TOOLS=0).")

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

