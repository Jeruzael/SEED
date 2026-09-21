
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
