"""Scoped read-only work limits and strict stored-data decoding for Astra."""
from contextlib import contextmanager
import json
import math
import sqlite3

from .read_store import ServiceError

MAX_ID = 2**63 - 1


def integer(value, minimum=0, maximum=MAX_ID):
    return type(value) is int and minimum <= value <= maximum


def number(value, minimum=None, maximum=None):
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and (minimum is None or value >= minimum)
                and (maximum is None or value <= maximum))
    except OverflowError:
        return False


def compact(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def capped(value, limit, error_code='invalid_evidence_response'):
    try:
        if len(compact(value)) <= limit:
            return value
    except (ValueError, TypeError, OverflowError, UnicodeError, RecursionError):
        pass
    raise ServiceError(error_code, 'Stored evidence exceeds its bounded response contract.', 503)


def strict_json(raw, limit=16384, array_limit=100, history=False):
    if type(raw) is str:
        raw = raw.encode('utf-8')
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError('invalid_json_bytes')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('invalid_number')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError('invalid_root')
    nodes = 0
    def check(item, depth=0, key=None):
        nonlocal nodes
        if depth > 8:
            raise ValueError('json_depth')
        if isinstance(item, dict):
            nodes += len(item)
            for name, child in item.items():
                if len(name.encode('utf-8')) > 128:
                    raise ValueError('json_key')
                check(child, depth+1, name if history and depth == 0 else None)
        elif isinstance(item, list):
            nodes += len(item)
            if len(item) > array_limit:
                raise ValueError('json_array')
            for child in item:
                check(child, depth+1)
        elif isinstance(item, str):
            if len(item.encode('utf-8')) > (16384 if key == 'payload_json' else 256):
                raise ValueError('json_string')
        elif item is not None and type(item) is not bool and not number(item):
            raise ValueError('json_number')
        if nodes > 512:
            raise ValueError('json_members')
    check(value)
    if len(compact(value)) > limit:
        raise ValueError('json_canonical_bytes')
    return value


@contextmanager
def bounded_read(store, error_code='evidence_read_unavailable', budget=300000):
    try:
        with store.connection() as db:
            ticks = 0
            def progress():
                nonlocal ticks
                ticks += 1000
                return ticks >= budget
            db.execute('PRAGMA busy_timeout=0')
            db.set_progress_handler(progress, 1000)
            try:
                db.execute('BEGIN')
                yield db
            except sqlite3.Error as error:
                raise ServiceError(error_code, 'Stored evidence is temporarily unavailable.', 503) from error
            finally:
                db.set_progress_handler(None, 0)
                if db.in_transaction:
                    db.rollback()
    except ServiceError as error:
        if error.code == 'database_unavailable':
            raise ServiceError(error_code, 'Stored evidence is temporarily unavailable.', 503) from error
        raise


def schema(db, tables):
    names = ('seed_schema', *tables)
    marks = ','.join('?' for _ in names)
    found = {r[0] for r in db.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({marks}) LIMIT ?", (*names, len(names)))}
    if 'seed_schema' not in found:
        return 0, found
    versions = db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall()
    if len(versions) != 1 or not integer(versions[0][0], 1, 7):
        raise ServiceError('incompatible_schema', 'Stored evidence uses an incompatible schema.', 409)
    return versions[0][0], found
