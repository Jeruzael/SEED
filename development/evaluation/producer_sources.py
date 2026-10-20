"""Bounded raw producer facts from a standalone schema-v7 checkpoint.

This is a source projection, not the canonical science/hash projection.
JSON cells remain original strings; no PID, storage or run-ID substitutions
are made. A checkpoint cannot supply publication-time historical captures.
"""
from functools import lru_cache
import json
import math
import sqlite3

from .artifact_io import SNAPSHOT_BYTES
from .contracts import ContractError

SOURCE_BYTES = 32 * 1024 ** 2
MAX_ROWS = 100000
TABLE_ROWS = 2048
SOURCE_TABLES = (
    'world_beliefs', 'world_pending', 'curiosity_assessments',
    'semantic_memories', 'semantic_memory_history', 'consolidation_runs',
    'consolidation_state',
)
_SCHEMA_SQL = (
    'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name'
)


@lru_cache(maxsize=1)
def _reference_schema():
    from seed import memory, migrations
    reference = sqlite3.connect(':memory:')
    try:
        reference.executescript(memory.SCHEMA)
        migrations.migrate(reference)
        return tuple(reference.execute(_SCHEMA_SQL))
    finally:
        reference.close()


def checkpoint_source(raw):
    """Read exact raw table facts, without inventing histories or self evidence.

    The caller binds this source to an explicit member checkpoint declaration.
    This pure byte reader does not authenticate that declaration or infer a
    terminal/publication time from the contents of a database.
    """
    if (type(raw) is not bytes or len(raw) > SNAPSHOT_BYTES
            or not raw.startswith(b'SQLite format 3\0')):
        raise ContractError()
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(raw)
        db.execute('PRAGMA query_only=ON')
        expected = _reference_schema()
        actual = db.execute(_SCHEMA_SQL).fetchmany(len(expected) + 1)
        if tuple(actual) != expected:
            raise ContractError()
        if db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall() != [(7,)]:
            raise ContractError()
        tables = [row[1] for row in expected if row[0] == 'table']
        if len(tables) > 64:
            raise ContractError()
        total = 0
        for name in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            count = db.execute(
                f'SELECT COUNT(*) FROM (SELECT 1 FROM {quoted} LIMIT ?)',
                (MAX_ROWS + 1,)).fetchone()[0]
            total += count
            if total > MAX_ROWS:
                raise ContractError()
        if (db.execute('PRAGMA integrity_check').fetchone() != ('ok',)
                or db.execute('PRAGMA foreign_key_check').fetchone() is not None):
            raise ContractError()
        source = {'tables': {}}
        encoded_size = len(b'{"tables":{}}')
        for name in SOURCE_TABLES:
            quoted = '"' + name + '"'
            columns = db.execute(f'PRAGMA table_info({quoted})').fetchall()
            keys = [column[1] for column in columns]
            primary = [column[1] for column in
                       sorted(columns, key=lambda column: column[5]) if column[5]]
            order = ','.join('"' + key + '"' for key in (primary or keys))
            rows = []
            encoded_size += len(json.dumps(name).encode('ascii')) + 4
            cursor = db.execute(f'SELECT * FROM {quoted} ORDER BY {order}')
            for values in cursor:
                if len(rows) >= TABLE_ROWS:
                    raise ContractError()
                if any(type(value) not in (type(None), int, float, str)
                       or type(value) is float and not math.isfinite(value)
                       for value in values):
                    raise ContractError()
                row = dict(zip(keys, values))
                encoded_size += len(json.dumps(
                    row, separators=(',', ':'), allow_nan=False).encode('ascii')) + 1
                if encoded_size > SOURCE_BYTES:
                    raise ContractError()
                rows.append(row)
            source['tables'][name] = rows
        return source
    except (sqlite3.Error, ValueError, TypeError, OverflowError, UnicodeError):
        raise ContractError() from None
    finally:
        db.close()
