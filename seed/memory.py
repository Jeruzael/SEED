from __future__ import annotations
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from .migrations import migrate
from .paths import checked_path

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    event TEXT NOT NULL,
    state_json TEXT NOT NULL,
    action TEXT,
    reward REAL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS q_values (
    state_key TEXT NOT NULL,
    action TEXT NOT NULL,
    value REAL NOT NULL DEFAULT 0,
    visits INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (state_key, action)
);

CREATE TABLE IF NOT EXISTS concepts (
    name TEXT PRIMARY KEY,
    confidence REAL NOT NULL,
    evidence INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""

class Memory:
    def __init__(self, path: Path):
        self.path = checked_path(path.parent, path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('-wal', '-shm', '-journal'):
            checked_path(path.parent, path.name + suffix)
        if self.path.exists():
            with sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True) as existing:
                legacy = not existing.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone()
                has_memory = bool(existing.execute("SELECT 1 FROM sqlite_master WHERE name='episodes'").fetchone())
            if legacy and has_memory:
                from .backup import create_backup
                create_backup(path.parent)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=2)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.row_factory = sqlite3.Row
        with self._lock:
            self.db.executescript(SCHEMA)
            self.db.commit()
            migrate(self.db)

    def close(self):
        with self._lock:
            self.db.commit()
            self.db.close()

    def set_meta(self, key: str, value: Any):
        payload = json.dumps(value)
        with self._lock:
            self.db.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, payload),
            )
            self.db.commit()

    def get_meta(self, key: str, default=None):
        with self._lock:
            row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def episode(self, event: str, state: dict, action=None, reward=None, note=None):
        with self._lock:
            cursor = self.db.execute(
                "INSERT INTO episodes(ts,event,state_json,action,reward,note) VALUES(?,?,?,?,?,?)",
                (time.time(), event, json.dumps(state, sort_keys=True), action, reward, note),
            )
            self.db.commit()

            return cursor.lastrowid

    def get_q(self, state_key: str, action: str) -> tuple[float, int]:
        with self._lock:
            row = self.db.execute(
                "SELECT value,visits FROM q_values WHERE state_key=? AND action=?",
                (state_key, action),
            ).fetchone()
        return (float(row["value"]), int(row["visits"])) if row else (0.0, 0)

    def set_q(self, state_key: str, action: str, value: float, visits: int):
        with self._lock:
            self.db.execute(
                "INSERT INTO q_values(state_key,action,value,visits) VALUES(?,?,?,?) "
                "ON CONFLICT(state_key,action) DO UPDATE SET value=excluded.value,visits=excluded.visits",
                (state_key, action, value, visits),
            )
            self.db.commit()

    def upsert_concept(self, name: str, confidence: float, evidence: int, payload: dict):
        with self._lock:
            self.db.execute(
                "INSERT INTO concepts(name,confidence,evidence,payload_json,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET confidence=excluded.confidence,"
                "evidence=excluded.evidence,payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                (name, confidence, evidence, json.dumps(payload, sort_keys=True), time.time()),
            )
            self.db.commit()

    def recent_episodes(self, limit: int = 100):
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self):
        with self._lock:
            episodes = self.db.execute("SELECT COUNT(*) AS n FROM episodes").fetchone()["n"]
            concepts = self.db.execute("SELECT COUNT(*) AS n FROM concepts").fetchone()["n"]
        return {"episodes": episodes, "concepts": concepts}
