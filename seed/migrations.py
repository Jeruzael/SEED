"""Additive migrations: original episode, concept, policy and identity rows stay intact."""
import sqlite3

VERSION = 6
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

# A single sample is durable pending evidence, not yet a published belief.
_WORLD_COLUMNS = '''(
    id INTEGER PRIMARY KEY,
    belief_key TEXT NOT NULL UNIQUE,
    signal TEXT NOT NULL CHECK(signal IN ('battery_pct','load_ratio','disk_free_pct','network_reachable')),
    scope TEXT NOT NULL, scope_value TEXT NOT NULL,
    belief_type TEXT NOT NULL CHECK(belief_type IN ('numeric_delta','boolean_frequency')),
    value_json TEXT NOT NULL,
    evidence_count INTEGER NOT NULL CHECK(evidence_count >= {minimum}),
    contradiction_count INTEGER NOT NULL CHECK(contradiction_count BETWEEN 0 AND evidence_count),
    confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 0.95),
    created_at REAL NOT NULL, updated_at REAL NOT NULL,
    source_first_transition_id INTEGER NOT NULL REFERENCES transitions(id),
    source_last_transition_id INTEGER NOT NULL REFERENCES transitions(id),
    model_version INTEGER NOT NULL CHECK(model_version=1),
    CHECK((scope='global' AND scope_value='') OR
          (scope='action' AND scope_value IN ('observe','reflect','consolidate','rest'))),
    UNIQUE(signal,scope,scope_value,belief_type,model_version))'''

V3_STATEMENTS = [
    'CREATE TABLE world_beliefs' + _WORLD_COLUMNS.format(minimum=2),
    'CREATE TABLE world_pending' + _WORLD_COLUMNS.format(minimum=1),
    '''CREATE TABLE world_model_queue(
        transition_id INTEGER PRIMARY KEY REFERENCES transitions(id))''',
    '''CREATE TABLE world_model_processed(
        transition_id INTEGER PRIMARY KEY REFERENCES transitions(id),
        processed_at REAL NOT NULL, model_version INTEGER NOT NULL CHECK(model_version=1),
        valid_signals INTEGER NOT NULL CHECK(valid_signals BETWEEN 0 AND 4))''',
]

V4_STATEMENTS = [
    '''CREATE TABLE curiosity_assessments(
        transition_id INTEGER PRIMARY KEY REFERENCES transitions(id),
        created_at REAL NOT NULL, model TEXT NOT NULL, model_version INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('evaluated','unavailable')),
        score REAL CHECK(score BETWEEN 0 AND 1), level TEXT NOT NULL,
        prediction_surprise REAL, uncertainty REAL, novelty REAL, coverage REAL,
        components_json TEXT NOT NULL,
        reflection_eligible INTEGER NOT NULL CHECK(reflection_eligible IN (0,1)),
        reflection_claimed INTEGER NOT NULL DEFAULT 0 CHECK(reflection_claimed IN (0,1)),
        reflection_completed INTEGER NOT NULL DEFAULT 0 CHECK(reflection_completed IN (0,1)),
        suppression_reason TEXT, failure_reason TEXT, claimed_at REAL, completed_at REAL,
        CHECK((status='unavailable' AND score IS NULL AND level='UNAVAILABLE') OR
              (status='evaluated' AND score IS NOT NULL AND level IN ('LOW','NOTABLE','HIGH','VERY_HIGH'))),
        CHECK(reflection_completed <= reflection_claimed))''',
    '''CREATE TABLE curiosity_runtime(
        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
        last_reflection_transition_id INTEGER NOT NULL REFERENCES transitions(id),
        last_reflection_at REAL NOT NULL)''',
]

V5_STATEMENTS = [
    '''CREATE TABLE semantic_memories(
        id INTEGER PRIMARY KEY, semantic_key TEXT NOT NULL UNIQUE,
        signal TEXT NOT NULL, scope TEXT NOT NULL, scope_value TEXT NOT NULL,
        semantic_type TEXT NOT NULL, payload_json TEXT NOT NULL,
        confidence REAL NOT NULL, evidence_count INTEGER NOT NULL, contradiction_count INTEGER NOT NULL,
        source_belief_id INTEGER NOT NULL REFERENCES world_beliefs(id),
        source_belief_model_version INTEGER NOT NULL, source_belief_updated_at REAL NOT NULL,
        source_first_transition_id INTEGER NOT NULL, source_last_transition_id INTEGER NOT NULL,
        source_fingerprint TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>=1),
        status TEXT NOT NULL CHECK(status IN ('active','weakened','source_unavailable')),
        created_at REAL NOT NULL, updated_at REAL NOT NULL,
        model TEXT NOT NULL, model_version INTEGER NOT NULL)''',
    'CREATE INDEX semantic_source ON semantic_memories(source_belief_id)',
    '''CREATE TABLE semantic_memory_history(
        semantic_memory_id INTEGER NOT NULL REFERENCES semantic_memories(id),
        revision INTEGER NOT NULL, recorded_at REAL NOT NULL, record_json TEXT NOT NULL,
        PRIMARY KEY(semantic_memory_id,revision))''',
    '''CREATE TABLE consolidation_runs(
        id INTEGER PRIMARY KEY, started_at REAL NOT NULL, completed_at REAL,
        model TEXT NOT NULL, model_version INTEGER NOT NULL, provenance TEXT NOT NULL,
        source_beliefs_examined INTEGER NOT NULL DEFAULT 0, eligible_beliefs INTEGER NOT NULL DEFAULT 0,
        created_count INTEGER NOT NULL DEFAULT 0, revised_count INTEGER NOT NULL DEFAULT 0,
        weakened_count INTEGER NOT NULL DEFAULT 0, unchanged_count INTEGER NOT NULL DEFAULT 0,
        failed_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL, result_json TEXT NOT NULL)''',
    '''CREATE TABLE consolidation_state(
        singleton INTEGER PRIMARY KEY CHECK(singleton=1), last_belief_id INTEGER NOT NULL)''',
]


V6_STATEMENTS = [
    "CREATE TABLE self_model_current (\n    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),\n    updated_at REAL NOT NULL CHECK(updated_at >= 0),\n    model TEXT NOT NULL CHECK(model = 'self_model_v1'),\n    model_version INTEGER NOT NULL CHECK(model_version = 1),\n    source_transition_id INTEGER NOT NULL REFERENCES transitions(id)\n        CHECK(source_transition_id > 0),\n    data_json TEXT NOT NULL\n        CHECK(length(CAST(data_json AS BLOB)) <= 32768)\n);"
]


def schema_version(db: sqlite3.Connection) -> int:
    """Return 0 for unversioned storage; refuse ambiguous/unsupported versions."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone():
        return 0
    rows = db.execute('SELECT version FROM seed_schema').fetchall()
    if len(rows) != 1 or type(rows[0][0]) is not int or rows[0][0] not in (1, 2, 3, 4, 5, VERSION):
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
            db.execute('UPDATE seed_schema SET version=2')
            version = 2
        if version == 2:
            for statement in V3_STATEMENTS:
                db.execute(statement)
            db.execute('UPDATE seed_schema SET version=3')
            version = 3
        if version == 3:
            for statement in V4_STATEMENTS:
                db.execute(statement)
            db.execute('UPDATE seed_schema SET version=4')
            version = 4
        if version == 4:
            for statement in V5_STATEMENTS:
                db.execute(statement)
            db.execute('UPDATE seed_schema SET version=5')
            version = 5
        if version == 5:
            for statement in V6_STATEMENTS:
                db.execute(statement)
            db.execute('UPDATE seed_schema SET version=?', (VERSION,))
        db.commit()
    except BaseException:
        db.rollback()
        raise
