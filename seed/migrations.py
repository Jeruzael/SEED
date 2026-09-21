"""Additive migrations: original episode, concept, policy and identity rows stay intact."""
import sqlite3

VERSION = 1
STATEMENTS = [
    'CREATE TABLE seed_schema(version INTEGER NOT NULL)',
    '''CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
    category TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL, data_json TEXT NOT NULL)''',
    'CREATE INDEX events_category_id ON events(category,id)',
    'CREATE INDEX events_ts ON events(ts)',
    'CREATE INDEX IF NOT EXISTS episodes_event_ts ON episodes(event,ts)',
    'CREATE TABLE runtime(singleton INTEGER PRIMARY KEY CHECK(singleton=1),data_json TEXT NOT NULL)',
    '''CREATE TABLE concept_evidence(name TEXT PRIMARY KEY, created_at REAL,
    updated_at REAL NOT NULL,episode_ids_json TEXT NOT NULL)''',
    '''CREATE TABLE commands(id TEXT PRIMARY KEY,name TEXT NOT NULL,session_id TEXT NOT NULL,
    created_at REAL NOT NULL,expires_at REAL NOT NULL,status TEXT NOT NULL,result_json TEXT)''',
    '''CREATE TABLE annotations(episode_id INTEGER PRIMARY KEY REFERENCES episodes(id),
    important INTEGER NOT NULL DEFAULT 0,tags_json TEXT NOT NULL DEFAULT '[]')''',
    '''CREATE TABLE settings(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    revision INTEGER NOT NULL,data_json TEXT NOT NULL)''',
    'CREATE TABLE automations(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,data_json TEXT NOT NULL)',
    '''CREATE TABLE automation_runs(rule_id TEXT NOT NULL,occurrence TEXT NOT NULL,
    status TEXT NOT NULL,result_json TEXT,PRIMARY KEY(rule_id,occurrence))''',
    '''CREATE TABLE audit(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL NOT NULL,
    action TEXT NOT NULL,parameters_json TEXT NOT NULL,result_json TEXT NOT NULL)''',
]


def migrate(db: sqlite3.Connection) -> None:
    db.execute('BEGIN IMMEDIATE')
    try:
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone()
        if exists:
            row = db.execute('SELECT version FROM seed_schema').fetchone()
            if not row or row[0] != VERSION:
                raise ValueError('Unsupported SEED schema version')
        else:
            for statement in STATEMENTS:
                db.execute(statement)
            db.execute('INSERT INTO seed_schema VALUES(?)', (VERSION,))
        db.commit()
    except BaseException:
        db.rollback()
        raise
