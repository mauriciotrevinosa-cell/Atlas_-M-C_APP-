import os
from pathlib import Path
import ast
from collections import defaultdict

REPO_ROOT = Path(r"c:\Users\mauri\OneDrive\Desktop\Atlas")
SRC_DIR = REPO_ROOT / "python" / "src"
EXCLUDES = {".venv", "node_modules", "trash", "legacy", "tests", ".git", ".claude", "docs"}

# Entrypoints or known roots that we shouldn't flag as orphans
KNOWN_ROOTS = {
    REPO_ROOT / "run_atlas.py",
    REPO_ROOT / "run_aria.py",
    REPO_ROOT / "run_server.py",
    REPO_ROOT / "setup.py",
}

def is_excluded(path):
    parts = path.parts
    for ex in EXCLUDES:
        if ex in parts:
            return True
    return False

def get_module_name(path):
    # Map a file path to its module space, e.g., atlas.assistant.core
    if SRC_DIR in path.parents:
        rel = path.relative_to(SRC_DIR)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return None

def extract_imports(filepath):
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module
                # Handle relative imports roughly (assume absolute for now from `atlas.`)
                if node.level > 0:
                    # simplistic approximation: ignore relative deep levels for script, 
                    # but usually they are from current package.
                    # We'll rely mainly on absolute imports from `atlas.`
                    pass
                imports.add(module)
                for alias in node.names:
                    imports.add(f"{module}.{alias.name}")
    return imports

py_files = []
for p in REPO_ROOT.rglob("*.py"):
    if not is_excluded(p):
        py_files.append(p)

module_to_file = {}
for p in py_files:
    mod = get_module_name(p)
    if mod:
        module_to_file[mod] = p

used_modules = set()
for p in py_files:
    imports = extract_imports(p)
    # Check if any import matches a known module or sub-module
    for imp in imports:
        # imp could be "atlas.assistants.aria.core"
        # We need to mark "atlas.assistants.aria.core" and all parents as used
        parts = imp.split(".")
        current = ""
        for part in parts:
            current = f"{current}.{part}" if current else part
            used_modules.add(current)

orphans = []
for mod, path in module_to_file.items():
    if mod not in used_modules:
        # It's an orphan
        orphans.append(path)

# Filter out roots and __init__.py files that might just be structural
true_orphans = []
for p in orphans:
    if p.name == "__init__.py":
        continue
    if p in KNOWN_ROOTS:
        continue
    if "test" in p.name:
        continue
    true_orphans.append(p)

# Print orphans
print(f"Total Python files scanned: {len(py_files)}")
print(f"Total modules identified in src: {len(module_to_file)}")
print(f"Found {len(true_orphans)} true orphan files inside python/src/")
for o in true_orphans:
    print(f" - {o.relative_to(REPO_ROOT)}")

with open(REPO_ROOT / "orphans.txt", "w", encoding="utf-8") as f:
    for o in true_orphans:
        f.write(str(o.relative_to(REPO_ROOT)) + "\n")
