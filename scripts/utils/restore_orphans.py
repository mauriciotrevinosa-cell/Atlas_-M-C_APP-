import os
import shutil
from pathlib import Path

REPO_ROOT = Path(r"c:\Users\mauri\OneDrive\Desktop\Atlas")
LEGACY_DIR = REPO_ROOT / "python" / "src" / "atlas" / "lab" / "legacy" / "orphans"
SRC_DIR = REPO_ROOT / "python" / "src" / "atlas"

restored_count = 0
for root, dirs, files in os.walk(LEGACY_DIR):
    for file in files:
        if file == "README_TEMP.md":
            continue
        
        src_path = Path(root) / file
        rel_path = src_path.relative_to(LEGACY_DIR)
        dest_path = SRC_DIR / rel_path
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src_path), str(dest_path))
            restored_count += 1
            print(f"Restored {rel_path}")
        except Exception as e:
            print(f"Failed to restore {rel_path}: {e}")

print(f"Total files restored: {restored_count}")
