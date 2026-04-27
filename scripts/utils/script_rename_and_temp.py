import os
from pathlib import Path

base_dir = Path(r"c:\Users\mauri\OneDrive\Desktop\Atlas")

renames = {
    "Info instructions": "info_instructions",
    "Project_Governance": "project_governance"
}

for old, new in renames.items():
    old_path = base_dir / old
    new_path = base_dir / new
    if old_path.exists():
        try:
            old_path.rename(new_path)
            print(f"Renamed {old} to {new}")
        except Exception as e:
            print(f"Error renaming {old}: {e}")
    else:
        print(f"Path not found: {old_path}")

# Add README_TEMP.md to the relevant folders
temp_folders = ["info_instructions", "project_governance", "trash"]
temp_content = "# TEMP\nThis directory has been marked as temporary/legacy during repo audit. Action: review and delete if not needed in the future.\n"

for folder in temp_folders:
    folder_path = base_dir / folder
    if folder_path.exists():
        readme_path = folder_path / "README_TEMP.md"
        try:
            readme_path.write_text(temp_content, encoding="utf-8")
            print(f"Added README_TEMP.md to {folder}")
        except Exception as e:
            print(f"Error writing to {readme_path}: {e}")
    else:
        print(f"Folder not found for TEMP readme: {folder_path}")
