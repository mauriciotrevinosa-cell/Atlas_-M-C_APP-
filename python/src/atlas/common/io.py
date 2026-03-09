import os
from pathlib import Path

def get_run_output_dir(run_id: str) -> Path:
    """
    Estandariza dónde se escriben los outputs de runs y renders.
    Returns: Path object to the directory `outputs/runs/<run_id>/`.
    """
    # Assuming this file is at `python/src/atlas/common/io.py`
    # and the repo root is 4 levels up.
    # We can also dynamically resolve from currently working directory or env var.
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    # In case it's installed as a package, fallback to current working directory
    if repo_root.name != "Atlas":
        repo_root = Path(os.getcwd())
        
    outputs_dir = repo_root / "outputs" / "runs" / run_id
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir
