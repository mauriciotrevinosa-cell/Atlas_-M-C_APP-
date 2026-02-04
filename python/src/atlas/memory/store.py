import json
from pathlib import Path
from datetime import datetime

class MemoryStore:
    """
    Phase 7: Memory & Persistence.
    Stores run results and learnings.
    """
    
    def __init__(self, path: str = "data/memory.json"):
        self.path = Path(path)
        self.data = self._load()
        
    def _load(self):
        if self.path.exists():
            with open(self.path, 'r') as f:
                return json.load(f)
        return {"runs": [], "calibration": {}}
        
    def save_run(self, run_data: dict):
        """Save a backtest or live run result."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": run_data
        }
        self.data["runs"].append(entry)
        self._persist()
        
    def _persist(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)
