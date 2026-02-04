"""
ARIA Conversation Memory - SQLite based
"""
import sqlite3
from pathlib import Path
from typing import List, Dict

class ConversationMemory:
    def __init__(self, db_path: str = "data/aria_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                role TEXT,
                content TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def add(self, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO conversations (timestamp, role, content) VALUES (datetime('now'), ?, ?)",
            (role, content)
        )
        conn.commit()
        conn.close()
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        results = [{"role": r[0], "content": r[1]} for r in cursor.fetchall()]
        conn.close()
        return list(reversed(results))
