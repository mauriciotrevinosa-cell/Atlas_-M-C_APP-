import os
import shutil
from pathlib import Path

REPO_ROOT = Path(r"c:\Users\mauri\OneDrive\Desktop\Atlas")
LEGACY_DIR = REPO_ROOT / "python" / "src" / "atlas" / "lab" / "legacy" / "orphans"

# Create the legacy directory if it doesn't exist
LEGACY_DIR.mkdir(parents=True, exist_ok=True)

orphans_file = REPO_ROOT / "orphans.txt"
if not orphans_file.exists():
    print("No orphans.txt found.")
    exit(0)

with open(orphans_file, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

moved_count = 0
for line in lines:
    if not line.strip():
        continue
    
    src_path = REPO_ROOT / line
    if not src_path.exists():
        continue
    
    # Calculate relative path inside python/src/atlas/
    try:
        rel_to_atlas = src_path.relative_to(REPO_ROOT / "python" / "src" / "atlas")
    except ValueError:
        # Maybe it's not inside python/src/atlas
        rel_to_atlas = Path(src_path.name)
        
    dest_path = LEGACY_DIR / rel_to_atlas
    
    # Ensure dest dir exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        shutil.move(str(src_path), str(dest_path))
        moved_count += 1
        print(f"Moved {src_path.name} to {dest_path}")
    except Exception as e:
        print(f"Failed to move {src_path}: {e}")

# Add README
readme_path = LEGACY_DIR / "README_TEMP.md"
readme_path.write_text("# TEMP - Orphans\nThese files were automatically moved here because they were not imported or executed by any active code. Review and delete if unnecessary.\n", encoding="utf-8")

print(f"Total files moved: {moved_count}")
