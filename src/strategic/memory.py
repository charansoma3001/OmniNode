"""Context memory system for the strategic agent.

SQLite-backed storage of decisions, outcomes, and sensor snapshots.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from src.common.models import AgentDecision

logger = logging.getLogger(__name__)

DB_PATH = Path("data/agent_memory.db")


class ContextMemory:
    """Persistent context memory for strategic agent decisions.

    Stores decisions, outcomes, and sensor context for continuity across sessions.
    """

    def __init__(self, db_path: Path | str = DB_PATH):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                trigger TEXT NOT NULL,
                reasoning TEXT,
                actions TEXT,
                outcome TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_context_key ON context_snapshots(key);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def store_decision(self, decision: AgentDecision) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO decisions (id, trigger, reasoning, actions, outcome, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                decision.decision_id,
                decision.trigger,
                decision.reasoning,
                json.dumps([a.model_dump(mode="json") for a in decision.actions_taken], default=str),
                decision.outcome,
                decision.timestamp.isoformat(),
            ),
        )
        self._conn.commit()

    def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_decision(self, decision_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Context snapshots
    # ------------------------------------------------------------------

    def store_context(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO context_snapshots (key, value, timestamp) VALUES (?, ?, ?)",
            (key, json.dumps(value, default=str), datetime.utcnow().isoformat()),
        )
        self._conn.commit()

    def get_latest_context(self, key: str) -> Any | None:
        row = self._conn.execute(
            "SELECT value FROM context_snapshots WHERE key = ? ORDER BY timestamp DESC LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_context_summary(self) -> str:
        """Build a context summary for the agent's system prompt."""
        count = self._conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        if count == 0:
            return "No previous decisions on record."

        recent = self.get_recent_decisions(3)
        lines = [f"Total decisions in memory: {count}"]
        for d in recent:
            lines.append(f"  - [{d['timestamp']}] {d['trigger'][:80]}")
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()
