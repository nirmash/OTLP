"""SQLite-backed telemetry store."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = os.environ.get("OTLP_DB_PATH", "telemetry.db")


class TelemetryStore:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                received_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_kind
            ON telemetry (kind, id DESC)
        """)
        conn.commit()
        conn.close()

    def _add(self, kind: str, items: list[dict]):
        now = datetime.now(timezone.utc).isoformat()
        rows = [(kind, now, json.dumps(item)) for item in items]
        with self._lock:
            conn = self._conn()
            conn.executemany(
                "INSERT INTO telemetry (kind, received_at, data) VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()

    def add_traces(self, resource_spans: list[dict]):
        self._add("traces", resource_spans)

    def add_metrics(self, resource_metrics: list[dict]):
        self._add("metrics", resource_metrics)

    def add_logs(self, resource_logs: list[dict]):
        self._add("logs", resource_logs)

    def _get(self, kind: str, limit: int) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT received_at, data FROM telemetry WHERE kind = ? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
        return [
            {"received_at": r["received_at"], "data": json.loads(r["data"])}
            for r in reversed(rows)
        ]

    def get_traces(self, limit: int = 50) -> list[dict]:
        return self._get("traces", limit)

    def get_metrics(self, limit: int = 50) -> list[dict]:
        return self._get("metrics", limit)

    def get_logs(self, limit: int = 50) -> list[dict]:
        return self._get("logs", limit)

    def get_counts(self) -> dict:
        conn = self._conn()
        rows = conn.execute(
            "SELECT kind, COUNT(*) as cnt FROM telemetry GROUP BY kind"
        ).fetchall()
        counts = {"traces": 0, "metrics": 0, "logs": 0}
        for r in rows:
            counts[r["kind"]] = r["cnt"]
        return counts

    def clear(self):
        with self._lock:
            conn = self._conn()
            conn.execute("DELETE FROM telemetry")
            conn.commit()


store = TelemetryStore()
