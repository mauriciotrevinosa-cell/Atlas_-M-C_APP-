import os
import shutil
from pathlib import Path

REPO_ROOT = Path(r"c:\Users\mauri\OneDrive\Desktop\Atlas")
EXPERIMENTS_DIR = REPO_ROOT / "python" / "src" / "atlas" / "lab" / "experiments" / "root_scripts"

EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

scripts_to_move = [
    "debug_data_layer.py",
    "verify_analysis.py",
    "verify_phase1_refinement.py",
    "verify_phase2.py",
    "verify_phase3.py",
    "calc_portfolio.py",
    "test_server_logic.py",
    "scaffold_atlas.py",
    "helper_scripts.py"
]

moved = 0
for s in scripts_to_move:
    src_path = REPO_ROOT / s
    if src_path.exists():
        dest_path = EXPERIMENTS_DIR / s
        try:
            shutil.move(str(src_path), str(dest_path))
            moved += 1
            print(f"Moved {s} to {dest_path}")
        except Exception as e:
            print(f"Failed to move {s}: {e}")

readme_path = EXPERIMENTS_DIR / "README_TEMP.md"
readme_path.write_text("# TEMP - Root Scripts\nThese scripts were moved from the root of the repository to keep it clean. Action: Review and convert into proper tests/tools if needed.\n", encoding="utf-8")

print(f"Total scripts moved: {moved}")
