"""Read-only repository map for Atlas agents."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List


SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
}


@dataclass(slots=True)
class FileNode:
    path: str
    language: str
    imports: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    lines: int = 0

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "language": self.language,
            "imports": self.imports,
            "symbols": self.symbols,
            "lines": self.lines,
        }


@dataclass(slots=True)
class RepoMap:
    root: str
    files: List[FileNode]

    def to_dict(self) -> Dict:
        return {
            "root": self.root,
            "file_count": len(self.files),
            "files": [node.to_dict() for node in self.files],
            "top_imports": self.top_imports(),
            "modules": self.modules(),
            "mermaid": self.to_mermaid(),
        }

    def top_imports(self, limit: int = 20) -> List[Dict[str, object]]:
        counts: Dict[str, int] = {}
        for node in self.files:
            for item in node.imports:
                counts[item] = counts.get(item, 0) + 1
        return [
            {"import": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:limit]
        ]

    def modules(self) -> List[Dict[str, object]]:
        grouped: Dict[str, Dict[str, object]] = {}
        for node in self.files:
            module = node.path.split("/", 1)[0]
            item = grouped.setdefault(module, {"module": module, "files": 0, "symbols": 0, "lines": 0})
            item["files"] = int(item["files"]) + 1
            item["symbols"] = int(item["symbols"]) + len(node.symbols)
            item["lines"] = int(item["lines"]) + node.lines
        return sorted(grouped.values(), key=lambda item: str(item["module"]))

    def to_mermaid(self, limit: int = 60) -> str:
        """Render a compact module dependency graph as Mermaid flowchart text."""
        modules = {str(item["module"]) for item in self.modules()}
        edges: Dict[tuple[str, str], int] = {}

        for node in self.files:
            source = node.path.split("/", 1)[0]
            for imported in node.imports:
                target = imported.split(".", 1)[0]
                if target in modules and target != source:
                    key = (source, target)
                    edges[key] = edges.get(key, 0) + 1

        lines = ["flowchart LR"]
        if not edges:
            for module in sorted(modules)[:limit]:
                lines.append(f"  {_mermaid_id(module)}[{_mermaid_label(module)}]")
            return "\n".join(lines)

        ranked = sorted(edges.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[:limit]
        for (source, target), count in ranked:
            lines.append(
                f"  {_mermaid_id(source)}[{_mermaid_label(source)}] "
                f"-->|{count}| {_mermaid_id(target)}[{_mermaid_label(target)}]"
            )
        return "\n".join(lines)


class RepoMapBuilder:
    """Builds a lightweight code map without modifying the repository."""

    def __init__(
        self,
        root: str | Path,
        *,
        max_files: int = 1500,
        ignore_dirs: Iterable[str] | None = None,
    ):
        self.root = Path(root).resolve()
        self.max_files = max_files
        self.ignore_dirs = set(DEFAULT_IGNORE_DIRS)
        if ignore_dirs:
            self.ignore_dirs.update(ignore_dirs)

    def build(self) -> RepoMap:
        files: List[FileNode] = []
        for path in self._iter_files():
            files.append(self._analyze_file(path))
            if len(files) >= self.max_files:
                break
        return RepoMap(root=str(self.root), files=files)

    def _iter_files(self) -> Iterable[Path]:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if any(part in self.ignore_dirs for part in path.relative_to(self.root).parts):
                continue
            yield path

    def _analyze_file(self, path: Path) -> FileNode:
        rel = path.relative_to(self.root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        language = _language(path.suffix)
        if path.suffix.lower() == ".py":
            imports, symbols = _python_imports_symbols(text)
        else:
            imports, symbols = _js_imports_symbols(text)
        return FileNode(
            path=rel,
            language=language,
            imports=imports,
            symbols=symbols,
            lines=len(text.splitlines()),
        )


def build_repo_map(root: str | Path, *, max_files: int = 1500) -> RepoMap:
    return RepoMapBuilder(root, max_files=max_files).build()


def _language(ext: str) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".ts": "typescript",
        ".tsx": "typescript-react",
    }.get(ext.lower(), ext.lstrip("."))


def _python_imports_symbols(text: str) -> tuple[List[str], List[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []
    imports: List[str] = []
    symbols: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
    return _unique(imports), _unique(symbols)


_IMPORT_RE = re.compile(r"""(?:import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]|from\s+['"]([^'"]+)['"])""")
_SYMBOL_RE = re.compile(r"\b(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)")
_EXPORT_RE = re.compile(r"\bexport\s+(?:default\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)")


def _js_imports_symbols(text: str) -> tuple[List[str], List[str]]:
    imports: List[str] = []
    for match in _IMPORT_RE.finditer(text):
        raw = match.group(1) or match.group(2) or ""
        if raw:
            imports.append(raw.split("/", 1)[0] if not raw.startswith(".") else raw)
    symbols = [m.group(1) for m in _SYMBOL_RE.finditer(text)]
    symbols.extend(m.group(1) for m in _EXPORT_RE.finditer(text))
    return _unique(imports), _unique(symbols)


def _unique(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _mermaid_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not safe or safe[0].isdigit():
        safe = f"m_{safe}"
    return safe


def _mermaid_label(value: str) -> str:
    return str(value).replace("[", "(").replace("]", ")")
