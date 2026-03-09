from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_ROOTS = [
    PROJECT_ROOT / "apps",
    PROJECT_ROOT / "configs",
    PROJECT_ROOT / "cpp",
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "python",
    PROJECT_ROOT / "services",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "ui_web",
]

EXCLUDED_PARTS = {
    "node_modules",
    ".git",
    ".venv",
    "trash",
    "info_instructions",
    ".claude",
    ".clone",
}


def has_excluded_part(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def collect_paths_with_spaces() -> list[Path]:
    offenders: list[Path] = []
    for root in CORE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if has_excluded_part(path):
                continue
            if " " in path.name:
                offenders.append(path)
    return sorted(offenders)


def main() -> int:
    offenders = collect_paths_with_spaces()
    if not offenders:
        print("OK: no spaces in core repo paths")
        return 0

    print("ERROR: found paths with spaces in core repo:")
    for path in offenders:
        print(path)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
