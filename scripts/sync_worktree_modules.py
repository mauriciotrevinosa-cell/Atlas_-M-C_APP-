from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKTREES_ROOT = ROOT / ".claude" / "worktrees"
REPORT_PATH = ROOT / "outputs" / "worktree_sync_report.json"

TRACKED_TOP_LEVELS = {
    "apps",
    "python",
    "scripts",
    "tests",
    "docs",
    "project_governance",
}

ROOT_FILES = {
    "run_atlas.py",
    "run_aria.py",
    "run_server.py",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
}

SKIP_PARTS = {
    "node_modules",
    "__pycache__",
    ".venv",
    ".git",
    "data",
    "outputs",
    "logs",
    "dist",
    "build",
}

ALLOWED_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".md", ".json"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_tracked_rel(rel: Path) -> bool:
    parts = rel.parts
    if not parts:
        return False
    if any(part in SKIP_PARTS for part in parts):
        return False
    if rel.suffix.lower() not in ALLOWED_EXTS:
        return False
    if str(rel).replace("\\", "/") in ROOT_FILES:
        return True
    return parts[0] in TRACKED_TOP_LEVELS


def _iter_worktree_files(worktree: Path) -> list[Path]:
    files: list[Path] = []
    for path in worktree.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(worktree)
        if _is_tracked_rel(rel):
            files.append(rel)
    return files


def _iter_root_files() -> set[Path]:
    files: set[Path] = set()
    for top in TRACKED_TOP_LEVELS:
        base = ROOT / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if _is_tracked_rel(rel):
                files.add(rel)
    for name in ROOT_FILES:
        path = ROOT / name
        if path.exists() and path.is_file():
            files.add(Path(name))
    return files


@dataclass
class WorktreeDiff:
    name: str
    missing_in_root: list[str]
    changed_vs_root: list[str]


def _build_report(selected_worktrees: list[str] | None = None) -> dict:
    if not WORKTREES_ROOT.exists():
        return {"error": f"worktrees root not found: {WORKTREES_ROOT}"}

    root_files = _iter_root_files()
    root_hashes = {rel: _sha256(ROOT / rel) for rel in root_files}

    diffs: list[WorktreeDiff] = []
    names = sorted(p.name for p in WORKTREES_ROOT.iterdir() if p.is_dir())
    if selected_worktrees:
        selected = set(selected_worktrees)
        names = [name for name in names if name in selected]

    for name in names:
        wt = WORKTREES_ROOT / name
        wt_files = _iter_worktree_files(wt)
        missing: list[str] = []
        changed: list[str] = []
        for rel in wt_files:
            rel_posix = rel.as_posix()
            root_path = ROOT / rel
            wt_path = wt / rel
            if rel not in root_files or not root_path.exists():
                missing.append(rel_posix)
                continue
            if _sha256(wt_path) != root_hashes[rel]:
                changed.append(rel_posix)

        diffs.append(
            WorktreeDiff(
                name=name,
                missing_in_root=sorted(missing),
                changed_vs_root=sorted(changed),
            )
        )

    report = {
        "root": str(ROOT),
        "worktrees_root": str(WORKTREES_ROOT),
        "worktrees_checked": len(diffs),
        "worktrees": [
            {
                "name": d.name,
                "missing_in_root_count": len(d.missing_in_root),
                "changed_vs_root_count": len(d.changed_vs_root),
                "missing_in_root": d.missing_in_root,
                "changed_vs_root": d.changed_vs_root,
            }
            for d in diffs
        ],
    }
    return report


def _apply_missing(worktree: str, missing_paths: list[str], overwrite: bool = False) -> int:
    wt = WORKTREES_ROOT / worktree
    copied = 0
    for rel_str in missing_paths:
        rel = Path(rel_str)
        src = wt / rel
        dst = ROOT / rel
        if not src.exists():
            continue
        if dst.exists() and not overwrite:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit files present in .claude/worktrees that are missing or different "
            "compared to this root project."
        )
    )
    parser.add_argument(
        "--worktree",
        action="append",
        help="Specific worktree name to inspect (can be used multiple times).",
    )
    parser.add_argument(
        "--apply-missing-from",
        help=(
            "Copy missing files from this worktree into root (safe: only missing by default)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwrite when using --apply-missing-from.",
    )
    args = parser.parse_args()

    report = _build_report(selected_worktrees=args.worktree)
    if "error" in report:
        print(report["error"])
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 72)
    print("ATLAS WORKTREE SYNC AUDIT")
    print("=" * 72)
    print(f"Report written: {REPORT_PATH}")
    for item in report["worktrees"]:
        print(
            f"- {item['name']}: missing={item['missing_in_root_count']}, "
            f"changed={item['changed_vs_root_count']}"
        )

    if args.apply_missing_from:
        target = args.apply_missing_from
        selected = next(
            (item for item in report["worktrees"] if item["name"] == target),
            None,
        )
        if selected is None:
            print(f"ERROR: worktree not in report: {target}")
            return 2
        copied = _apply_missing(
            worktree=target,
            missing_paths=selected["missing_in_root"],
            overwrite=args.overwrite,
        )
        print(f"Copied {copied} missing files from {target} into root.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

