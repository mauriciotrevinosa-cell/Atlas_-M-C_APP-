"""
AI Layer Logger — Audit trail for all AI operations.

Logs:
  - Every LLM call (query, response, tokens, latency)
  - Router classifications
  - Tool executions
  - Errors and exceptions
  - Permission denials

Storage: SQLite for structured logs + optional file export.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """A single audit log entry."""
    timestamp: float
    event_type: str  # "query", "response", "tool_call", "route", "error", "permission"
    data: Dict[str, Any]
    session_id: str = ""
    provider: str = ""
    model: str = ""
    tokens: int = 0
    latency_ms: float = 0.0


class AILogger:
    """
    Structured audit logger for the AI Layer.
    """

    def __init__(self, db_path: str = "data/ai_audit.db", enabled: bool = True):
        self.enabled = enabled
        self.db_path = Path(db_path)
        self._buffer: List[LogEntry] = []
        self._session_count = 0

        if enabled:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self):
        """Initialize audit database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                session_id TEXT DEFAULT '',
                provider TEXT DEFAULT '',
                model TEXT DEFAULT '',
                tokens INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0.0,
                data TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)
        """)
        conn.commit()
        conn.close()

    def log(self, event_type: str, data: Dict = None, **kwargs):
        """
        Log an event.

        Args:
            event_type: Type of event (query, response, tool_call, route, error, permission)
            data: Event data dictionary
            **kwargs: Additional fields (session_id, provider, model, tokens, latency_ms)
        """
        if not self.enabled:
            return

        entry = LogEntry(
            timestamp=time.time(),
            event_type=event_type,
            data=data or {},
            session_id=kwargs.get("session_id", ""),
            provider=kwargs.get("provider", ""),
            model=kwargs.get("model", ""),
            tokens=kwargs.get("tokens", 0),
            latency_ms=kwargs.get("latency_ms", 0.0),
        )

        self._buffer.append(entry)

        # Persist immediately
        self._persist(entry)

    def log_query(self, query: str, session_id: str = "", **kwargs):
        """Log a user query."""
        self.log("query", {"query": query[:500]}, session_id=session_id, **kwargs)

    def log_response(self, response: str, tokens: int = 0,
                     latency_ms: float = 0.0, **kwargs):
        """Log an AI response."""
        self.log("response", {
            "response": response[:500],
        }, tokens=tokens, latency_ms=latency_ms, **kwargs)

    def log_route(self, query: str, category: str, confidence: float,
                  method: str, **kwargs):
        """Log a routing decision."""
        self.log("route", {
            "query": query[:200],
            "category": category,
            "confidence": confidence,
            "method": method,
        }, **kwargs)

    def log_tool_call(self, tool_name: str, params: Dict = None,
                      result: Any = None, **kwargs):
        """Log a tool execution."""
        self.log("tool_call", {
            "tool": tool_name,
            "params": str(params)[:200] if params else "",
            "result_preview": str(result)[:200] if result else "",
        }, **kwargs)

    def log_error(self, error: str, error_type: str = "unknown", **kwargs):
        """Log an error."""
        self.log("error", {
            "error": error[:500],
            "error_type": error_type,
        }, **kwargs)

    def log_permission(self, action: str, allowed: bool, role: str, **kwargs):
        """Log a permission check."""
        self.log("permission", {
            "action": action,
            "allowed": allowed,
            "role": role,
        }, **kwargs)

    def _persist(self, entry: LogEntry):
        """Write entry to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO audit_log
                   (timestamp, event_type, session_id, provider, model, tokens, latency_ms, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry.timestamp, entry.event_type, entry.session_id,
                 entry.provider, entry.model, entry.tokens, entry.latency_ms,
                 json.dumps(entry.data))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Don't let logging failures break the app

    def get_recent(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict]:
        """Get recent log entries."""
        conn = sqlite3.connect(self.db_path)
        if event_type:
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE event_type = ? ORDER BY id DESC LIMIT ?",
                (event_type, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        columns = [d[0] for d in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get logging statistics."""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        by_type = conn.execute(
            "SELECT event_type, COUNT(*) FROM audit_log GROUP BY event_type"
        ).fetchall()
        total_tokens = conn.execute(
            "SELECT SUM(tokens) FROM audit_log WHERE tokens > 0"
        ).fetchone()[0] or 0
        avg_latency = conn.execute(
            "SELECT AVG(latency_ms) FROM audit_log WHERE latency_ms > 0"
        ).fetchone()[0] or 0
        conn.close()

        return {
            "total_entries": total,
            "by_type": dict(by_type),
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 2),
        }
