"""
Run Atlas - Browser Edition
===========================
Launcher script for the browser-based Atlas environment.
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
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


def _configure_file_logging(root: Path) -> None:
    """Set up rotating file logging so the 24/7 machine doesn't fill its disk."""
    logs_dir = root / "logs"
    logs_dir.mkdir(exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        logs_dir / "atlas.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,               # keep 5 rotations → max 50 MB
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s  %(message)s")
    )
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)


_configure_file_logging(PROJECT_ROOT)

from atlas.assistants.aria import ARIA
from atlas.assistants.aria.tools import register_phase1_tools
from atlas.assistants.aria.tools.setup import register_all_tools
from atlas.assistants.aria.tools.create_file import CreateFileTool
from atlas.assistants.aria.tools.execute_code import ExecuteCodeTool
from atlas.assistants.aria.tools.read_file import ReadFileTool
from atlas.assistants.aria.tools.web_search import WebSearchTool
from atlas.data_layer import get_provider_registry

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


# ═══════════════════════════════════════════════════════════════════════
# Premium terminal UI — Bloomberg / JetBrains aesthetic
# Palette applied color psychology for tech/finance recruiter impression:
#   • Deep navy  → trust, depth (Wall Street)
#   • Electric blue / cyan → precision, modernity
#   • Muted gold → excellence (used sparingly)
#   • Silver/white → clarity, premium product
#   • Mint green / soft amber → status signals that aren't loud
# ═══════════════════════════════════════════════════════════════════════

def _enable_ansi_on_windows() -> bool:
    """Enable 24-bit truecolor ANSI on Windows console."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        ENABLE_VT = 0x0004
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VT)
            return True
    except Exception:
        pass
    return os.getenv("NO_COLOR") is None


_ANSI_OK = _enable_ansi_on_windows() and os.getenv("NO_COLOR") is None


class _C:
    """24-bit ANSI palette. Falls back to plain text if unsupported."""
    if _ANSI_OK:
        RESET   = "\033[0m"
        BOLD    = "\033[1m"
        DIM     = "\033[2m"
        ITALIC  = "\033[3m"
        NAVY    = "\033[38;2;50;80;140m"
        BLUE    = "\033[38;2;77;163;255m"
        CYAN    = "\033[38;2;0;200;220m"
        GOLD    = "\033[38;2;210;175;115m"
        SILVER  = "\033[38;2;220;226;236m"
        MUTED   = "\033[38;2;120;135;165m"
        GREEN   = "\033[38;2;80;220;160m"
        AMBER   = "\033[38;2;240;190;100m"
        CORAL   = "\033[38;2;255;110;130m"
    else:
        RESET = BOLD = DIM = ITALIC = ""
        NAVY = BLUE = CYAN = GOLD = SILVER = MUTED = GREEN = AMBER = CORAL = ""


def _safe_print(message: str) -> None:
    """Print text without crashing if terminal encoding is limited."""
    try:
        print(message)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="replace").decode("ascii")
        print(fallback)


def _print_banner() -> None:
    """Premium ATLAS startup banner — ASCII wordmark + tagline."""
    c = _C
    rule = c.NAVY + "─" * 62 + c.RESET
    _safe_print("")
    _safe_print(rule)
    _safe_print("")
    wordmark = [
        "   █████╗ ████████╗██╗      █████╗ ███████╗",
        "  ██╔══██╗╚══██╔══╝██║     ██╔══██╗██╔════╝",
        "  ███████║   ██║   ██║     ███████║███████╗",
        "  ██╔══██║   ██║   ██║     ██╔══██║╚════██║",
        "  ██║  ██║   ██║   ███████╗██║  ██║███████║",
        "  ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝",
    ]
    for line in wordmark:
        _safe_print(c.SILVER + c.BOLD + line + c.RESET)
    _safe_print("")
    _safe_print(c.CYAN + "      Q U A N T I T A T I V E   I N T E L L I G E N C E" + c.RESET)
    _safe_print(c.MUTED + c.ITALIC + "                 Platform  ·  v1.0  ·  by M&C" + c.RESET)
    _safe_print("")
    _safe_print(rule)


def _print_section(label: str, index: int | None = None, total: int | None = None) -> None:
    """Premium section divider:  ── 01 / 03 · LLM BACKEND ────────────"""
    c = _C
    if index is not None and total is not None:
        tag = f"{c.GOLD}{index:02d}{c.MUTED} / {total:02d}{c.RESET}"
        prefix = f"{c.NAVY}──{c.RESET} {tag} {c.MUTED}·{c.RESET} "
        prefix_plain_len = 3 + 7 + 3  # '-- NN / NN . '
    else:
        prefix = f"{c.NAVY}──{c.RESET} "
        prefix_plain_len = 3
    label_styled = f"{c.SILVER}{c.BOLD}{label.upper()}{c.RESET}"
    fill = max(4, 62 - prefix_plain_len - len(label) - 1)
    _safe_print("")
    _safe_print(prefix + label_styled + " " + c.NAVY + ("─" * fill) + c.RESET)


def _ok(msg: str) -> None:
    _safe_print(f"  {_C.GREEN}●{_C.RESET} {_C.SILVER}{msg}{_C.RESET}")


def _info(msg: str) -> None:
    _safe_print(f"  {_C.BLUE}›{_C.RESET} {_C.SILVER}{msg}{_C.RESET}")


def _dim(msg: str) -> None:
    _safe_print(f"  {_C.MUTED}{msg}{_C.RESET}")


def _warn(msg: str) -> None:
    _safe_print(f"  {_C.AMBER}!{_C.RESET} {_C.SILVER}{msg}{_C.RESET}")


def _err(msg: str) -> None:
    _safe_print(f"  {_C.CORAL}✕{_C.RESET} {_C.SILVER}{msg}{_C.RESET}")


def _kv(key: str, value: str) -> None:
    """Key-value row for the 'serving at' block."""
    _safe_print(f"  {_C.MUTED}{key:<18}{_C.RESET} {_C.CYAN}{value}{_C.RESET}")


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


def _build_runtime_observability_report(aria: ARIA) -> str:
    """
    Build a concise terminal report of runtime wiring for `python run_atlas.py`.
    """
    tool_map = getattr(aria, "tools", {}) or {}
    tool_names = sorted(tool_map.keys())

    live_registry_tools = [
        name for name in (
            "atlas_market_data",
            "atlas_macro_data",
            "atlas_news",
            "atlas_filings",
            "atlas_sentiment",
        )
        if name in tool_map
    ]
    agent_tools = [name for name in ("atlas_agent_task",) if name in tool_map]
    browser_tools = [
        name for name in ("web_search", "create_file", "execute_code", "read_file")
        if name in tool_map
    ]

    registry = get_provider_registry()
    provider_info = registry.get_provider_info()

    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ATLAS RUNTIME REPORT")
    lines.append("=" * 60)
    lines.append(f"ARIA model: {getattr(aria, 'model', 'unknown')}")
    lines.append(f"Total registered tools: {len(tool_names)}")
    if browser_tools:
        lines.append(f"Browser tools: {', '.join(browser_tools)}")
    if live_registry_tools:
        lines.append(f"Live registry tools: {', '.join(live_registry_tools)}")
    if agent_tools:
        lines.append(f"Agent tools: {', '.join(agent_tools)}")

    lines.append("Provider channels:")
    if not provider_info:
        lines.append("  - none")
    else:
        for channel in sorted(provider_info.keys()):
            providers = provider_info[channel]
            if not providers:
                lines.append(f"  - {channel}: none")
                continue
            formatted = []
            for provider in providers:
                suffix = "" if provider.get("available", True) else " (unavailable)"
                formatted.append(f"{provider.get('name', 'unknown')}{suffix}")
            lines.append(f"  - {channel}: {', '.join(formatted)}")

    lines.append("=" * 60)
    return "\n".join(lines)


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
    _safe_print(f"  {_C.BLUE}›{_C.RESET} {_C.SILVER}Opening Atlas interface in default browser …{_C.RESET}")
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

    _print_banner()

    # ── 01 / 03 · LLM BACKEND -----------------------------------------
    _aria_backend = os.getenv("ARIA_LLM_BACKEND", "auto").lower()
    _cloud_keys_present = any(
        os.getenv(k) for k in (
            "GROQ_API_KEY", "OPENROUTER_API_KEY", "CEREBRAS_API_KEY",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        )
    )
    _need_ollama = (
        _aria_backend == "ollama"
        or (_aria_backend == "auto" and not _cloud_keys_present)
    )

    _print_section("LLM Backend", index=1, total=3)
    if not _need_ollama:
        _ok(f"Backend: {_aria_backend}")
        _dim("Cloud provider credentials detected — Ollama not required.")
    else:
        try:
            import requests
            response = requests.get("http://localhost:11434/", timeout=3)
            if response.status_code == 200:
                _ok("Ollama is running (localhost:11434)")
            else:
                _warn(f"Ollama responded with status {response.status_code}")
        except Exception:
            _warn("Ollama does not appear to be running")
            if os.getenv("ATLAS_AUTO_START_OLLAMA", "1") == "1":
                _dim("Attempting to start 'ollama serve' in background …")
                try:
                    subprocess.Popen(
                        "ollama serve",
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                    _dim("Launched Ollama. Waiting 5s …")
                    time.sleep(5)
                except Exception as exc:
                    _err(f"Failed to auto-start Ollama: {exc}")
                    _dim("ARIA will fall back to cloud/mock providers automatically.")
            else:
                _dim("Auto-start disabled. ARIA will use its fallback chain (cloud → mock).")

    # ── 02 / 03 · ARIA NEURAL ENGINE ---------------------------------
    _print_section("ARIA Neural Engine", index=2, total=3)
    try:
        server_port = _resolve_server_port(DEFAULT_HOST)
    except RuntimeError as exc:
        _err(str(exc))
        return

    try:
        import uvicorn
        from apps.server import server

        aria_model = os.getenv("ARIA_MODEL", DEFAULT_ARIA_MODEL).strip() or DEFAULT_ARIA_MODEL
        _info(f"Initializing ARIA ({aria_model}) …")
        aria = ARIA(model=aria_model)

        if _env_enabled("ATLAS_FAST_PROMPT", "1"):
            aria.system_prompt = FAST_BROWSER_SYSTEM_PROMPT
            _dim("Fast browser prompt enabled (ATLAS_FAST_PROMPT=0 to disable).")

        if _env_enabled("ATLAS_ENABLE_ARIA_TOOLS", "0"):
            registered_tools = _register_browser_tools(aria, PROJECT_ROOT)
            _ok(f"Registered {registered_tools} browser tools")
        else:
            registered_tools = 0
            _dim("Tool calling disabled for fast browser chat (ATLAS_ENABLE_ARIA_TOOLS=1 to enable).")

        if _env_enabled("ATLAS_ENABLE_PHASE1_TOOLS", "1"):
            phase1_tools = _register_phase1_workflow_tools(aria)
            if phase1_tools:
                _ok(f"Phase 1 workflow tools active ({len(phase1_tools)})")
                _dim(", ".join(phase1_tools))
            else:
                _warn("Phase 1 workflow tools requested but none were registered")
        else:
            _dim("Phase 1 workflow tools disabled (ATLAS_ENABLE_PHASE1_TOOLS=0).")

        if _env_enabled("ATLAS_ENABLE_RECOVERED_TOOLS", "1"):
            recovered_tools = _register_recovered_aria_tools(aria)
            if recovered_tools:
                _ok(f"Recovered ARIA tools active ({len(recovered_tools)})")
                _dim(", ".join(recovered_tools))
            else:
                _warn("Recovered ARIA tools requested but none were registered")
        else:
            _dim("Recovered ARIA tools disabled (ATLAS_ENABLE_RECOVERED_TOOLS=0).")

        if _env_enabled("ATLAS_ENABLE_GOV_CONTEXT", "0"):
            governance_context = _build_governance_prompt_context(PROJECT_ROOT)
            if governance_context:
                aria.system_prompt = f"{aria.system_prompt}\n\n{governance_context}"
                _ok("Project governance context loaded")
            else:
                _dim("Project governance context not found (skipped).")
        else:
            _dim("Governance context disabled (ATLAS_ENABLE_GOV_CONTEXT=1 to enable).")

        if _env_enabled("ATLAS_SHOW_RUNTIME_REPORT", "1"):
            _safe_print(_build_runtime_observability_report(aria))
        else:
            _dim("Runtime report disabled (ATLAS_SHOW_RUNTIME_REPORT=0).")

        # ── 03 / 03 · SERVING ----------------------------------------
        _print_section("Serving", index=3, total=3)
        _kv("Frontend",   f"http://localhost:{server_port}")
        _kv("API",        f"http://localhost:{server_port}/query")
        _kv("Health",     f"http://localhost:{server_port}/api/health")
        _kv("ARIA model", aria_model)
        _safe_print("")
        _safe_print(f"  {_C.MUTED}{_C.ITALIC}Press Ctrl+C to stop the server.{_C.RESET}")
        _safe_print(f"  {_C.NAVY}{'─' * 62}{_C.RESET}")
        _safe_print("")

        threading.Thread(target=_open_browser_delayed, args=(server_port,), daemon=True).start()

        server.aria_instance = aria
        uvicorn.run(server.app, host=DEFAULT_HOST, port=server_port, log_level="info")

    except ImportError:
        _err("Missing dependencies")
        _dim("Run: pip install -r requirements.txt")
    except Exception as exc:
        _err(f"Server error: {exc}")


if __name__ == "__main__":
    main()
