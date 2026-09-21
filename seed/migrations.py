"""Additive migrations: original episode, concept, policy and identity rows stay intact."""
import sqlite3

VERSION = 2
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

V2_STATEMENTS = [
    '''CREATE TABLE transitions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL UNIQUE REFERENCES episodes(id),
    started_at REAL NOT NULL, completed_at REAL NOT NULL,
    state_before_json TEXT NOT NULL, action TEXT NOT NULL,
    state_after_json TEXT NOT NULL, outcome_json TEXT NOT NULL,
    legacy_reward REAL NOT NULL, prediction_json TEXT, prediction_error_json TEXT)''',
]


def schema_version(db: sqlite3.Connection) -> int:
    """Return 0 for unversioned storage; refuse ambiguous/unsupported versions."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone():
        return 0
    rows = db.execute('SELECT version FROM seed_schema').fetchall()
    if len(rows) != 1 or type(rows[0][0]) is not int or rows[0][0] not in (1, VERSION):
        raise ValueError('Unsupported SEED schema version')
    return rows[0][0]


def migrate(db: sqlite3.Connection) -> None:
    db.execute('BEGIN IMMEDIATE')
    try:
        version = schema_version(db)
        if version == 0:
            for statement in STATEMENTS:
                db.execute(statement)
            db.execute('INSERT INTO seed_schema VALUES(1)')
            version = 1
        if version == 1:
            for statement in V2_STATEMENTS:
                db.execute(statement)
            db.execute('UPDATE seed_schema SET version=?', (VERSION,))
        db.commit()
    except BaseException:
        db.rollback()
        raise
