"""SQLite Audit Log for Zone Coordinators.

Provides a persistent event log for all deterministic PLC-level actions,
satisfying industrial auditability requirements.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "zone_audit.db")

class ZoneAuditLogger:
    """Thread-safe SQLite logger for PLC-level Zone Coordinator events."""

    _instance: ZoneAuditLogger | None = None
    _lock = Lock()

    def __new__(cls) -> ZoneAuditLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _init_db(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS zone_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        zone_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        action_taken TEXT
                    )
                    '''
                )
                conn.commit()
            logger.info("Initialized Zone Audit Database at %s", DB_PATH)
        except Exception as e:
            logger.error("Failed to initialize audit database: %s", e)

    def log_event(
        self,
        zone_id: str,
        event_type: str,
        message: str,
        details: dict | None = None,
        action_taken: str | None = None,
    ) -> None:
        """Log a new event to the exact zone's history."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        details_str = json.dumps(details) if details else None

        try:
            with self._lock:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''
                        INSERT INTO zone_events 
                        (timestamp, zone_id, event_type, message, details, action_taken)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''',
                        (timestamp, zone_id, event_type, message, details_str, action_taken)
                    )
                    conn.commit()
        except Exception as e:
            logger.error("Failed to log audit event for %s: %s", zone_id, e)

    def get_recent_events(self, zone_id: str | None = None, limit: int = 50) -> list[dict]:
        """Retrieve recent audit events, optionally filtered by zone."""
        query = "SELECT timestamp, zone_id, event_type, message, details, action_taken FROM zone_events"
        params = []
        
        if zone_id:
            query += " WHERE zone_id = ?"
            params.append(zone_id)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    details = json.loads(row["details"]) if row["details"] else {}
                    results.append({
                        "timestamp": row["timestamp"],
                        "zone_id": row["zone_id"],
                        "event_type": row["event_type"],
                        "message": row["message"],
                        "details": details,
                        "action_taken": row["action_taken"]
                    })
                return results
        except Exception as e:
            logger.error("Failed to retrieve audit events: %s", e)
            return []
