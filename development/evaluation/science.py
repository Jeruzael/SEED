"""Canonical scientific projection and digest (I22).

Science identity is the typed canonical content of a run: experiment, frozen
plan, private truth, initial logical state, joined journal/post-ACK
transitions, measurements and findings, and terminal status. It deliberately
excludes only the approved incidental information (storage run IDs, real
execution times, worker PID, paths, operational prose, SQLite physical
geometry, B7 physical storage-allocation values). Stored-byte integrity is a
separate contract (I23); this module never hashes raw payload files.
"""
import hashlib
import json
import sqlite3

from .canonical import canonical_bytes, canonical_stream
from .contracts import ContractError, Payload, strict_json
from .paths import EvaluationRoot

DOMAIN = b'SEED_B10_SCIENCE_V1\0'
MAX_TABLES = 64
MAX_ROWS = 100000
MAX_TRANSITIONS = 1024
MAX_ATTEMPTS = 2048
_STORAGE_KEYS = ('page_size', 'page_count', 'logical_allocated_bytes')
_MANIFEST_FIELDS = {'schema', 'run_id', 'status', 'reason', 'experiment',
                    'plan_digest', 'counts', 'checkpoints', 'failure',
                    'science_digest', 'publication'}

_reference_tables = None


def _reference():
    global _reference_tables
    if _reference_tables is None:
        import seed.memory as producer
        from seed import migrations
        db = sqlite3.connect(':memory:')
        try:
            db.executescript(producer.SCHEMA)
            migrations.migrate(db)
            _reference_tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            db.close()
    return _reference_tables


def _project_json(value, in_storage=False):
    if type(value) is dict:
        out = {}
        for key, item in value.items():
            if key == 'pid':
                out[key] = 'incidental_pid'
            elif key == 'run_id':
                out[key] = 'incidental_run_id'
            elif in_storage and key in _STORAGE_KEYS:
                out[key] = 'incidental_storage'
            else:
                out[key] = _project_json(item, in_storage or key == 'storage')
        return out
    if type(value) is list:
        return [_project_json(item, in_storage) for item in value]
    return value


def _typed(value):
    if value is None or type(value) in (bool, int, float):
        return value
    if isinstance(value, bytes):
        return {'utf8_bytes': value.hex()}
    if type(value) is str:
        if value[:1] in ('{', '['):
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = None
            if type(parsed) in (dict, list):
                return _project_json(parsed)
        try:
            value.encode('ascii')
            if len(value) <= 4096:
                return value
        except UnicodeEncodeError:
            pass
        return {'utf8_bytes': value.encode('utf-8').hex()}
    raise ContractError()


def project_state(snapshot) -> dict:
    """Project every table of a producer-shaped SQLite state, typed and
    deterministically ordered, with only approved incidental exclusions."""
    if hasattr(snapshot, 'memory'):  # OwnedState
        db = snapshot.memory.db
        owned = False
    elif isinstance(snapshot, sqlite3.Connection):
        db, owned = snapshot, False
    else:  # path to a closed snapshot file
        db = sqlite3.connect(f'file:{snapshot}?mode=ro&immutable=1', uri=True)
        owned = True
    try:
        names = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if len(names) > MAX_TABLES or set(names) != _reference():
            raise ContractError()
        tables = []
        total = 0
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            info = db.execute(f'PRAGMA table_info({quoted})').fetchall()
            columns = [dict(name=c[1], type=c[2], pk=c[5]) for c in info]
            pk = [c[1] for c in info if c[5]]
            order_cols = pk if pk else [c[1] for c in info]
            order = ','.join('"' + c.replace('"', '""') + '"' for c in order_cols)
            rows = []
            for row in db.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
                total += 1
                if total > MAX_ROWS:
                    raise ContractError()
                projected = []
                for column, value in zip(columns, row):
                    if column['name'] == 'run_id':
                        projected.append('incidental_run_id')
                    else:
                        projected.append(_typed(value))
                rows.append(projected)
            tables.append(dict(name=name, columns=columns, rows=rows))
        return dict(schema='b10_state_projection_v1', tables=tables)
    finally:
        if owned:
            db.close()


def _payload_dir(root, run_id):
    if type(root) is not EvaluationRoot:
        raise ContractError()
    from pathlib import Path
    for base in ('partials', 'runs'):
        candidate = root.path / 'evaluation' / base / run_id
        if candidate.is_dir():
            return candidate
    raise ContractError()


def _read_json(directory, name, maximum=4 * 1024 ** 2):
    raw = (directory / name).read_bytes()
    if len(raw) > maximum:
        raise ContractError()
    return strict_json(raw, max_bytes=maximum)


def _sections(payload, capability):
    if type(payload) is not Payload:
        raise ContractError()
    directory = _payload_dir(capability, payload.identity)
    manifest = _read_json(directory, 'manifest.json', 128 * 1024)
    if set(manifest) != _MANIFEST_FIELDS or manifest['schema'] != 'b10_artifact_v1':
        raise ContractError()
    plan_file = _read_json(directory, 'analysis-plan.json', 128 * 1024)
    plan_body = plan_file['plan']
    receipt = plan_file['receipt']
    if receipt.get('frozen_before_execution') is not True:
        raise ContractError()
    truth = _read_json(directory, 'truth.json')
    metrics = _read_json(directory, 'metrics.json', 256 * 1024)
    initial = None
    for entry in manifest['checkpoints']:
        if entry['name'] == 'initial':
            raw = (directory / entry['file']).read_bytes()
            db = sqlite3.connect(':memory:')
            try:
                db.deserialize(raw)
                initial = project_state(db)
            finally:
                db.close()
    header = dict(schema='b10_science_v1', kind='header',
                  experiment=manifest['experiment'],
                  plan=dict(body=plan_body, digest=plan_file['digest'],
                            frozen_before_execution=True,
                            first_members=receipt['first_members']),
                  truth=truth, initial_state=initial,
                  terminal=dict(status=manifest['status'],
                                reason=manifest['reason'],
                                failure=manifest['failure']))
    yield header
    journal_raw = (directory / 'preupdate.ndjson').read_bytes()
    frames = {}
    for line in journal_raw.splitlines(keepends=True):
        if line.strip():
            record = strict_json(line, max_bytes=64 * 1024)
            h = record['header']
            frames[(h['phase'], h['subcase'], h['transition_ordinal'])] = (
                line if line.endswith(b'\n') else line + b'\n', h)
    if len(frames) > MAX_TRANSITIONS:
        raise ContractError()
    events = {}
    others = []
    attempts = []
    events_raw = (directory / 'events.ndjson').read_bytes()
    for line in events_raw.splitlines():
        if not line.strip():
            continue
        event = strict_json(line, max_bytes=64 * 1024)
        if event.get('journal_sha256'):
            events[event['journal_sha256']] = event
        elif type(event.get('body')) is dict and event['body'].get('status') == 'skipped':
            attempts.append(event)
        else:
            others.append(event)
    if len(events) + len(others) + len(attempts) > MAX_ATTEMPTS:
        raise ContractError()
    for key in sorted(frames):
        line, h = frames[key]
        digest = hashlib.sha256(line).hexdigest()
        event = events.pop(digest, None)
        yield dict(kind='transition', key=list(key),
                   action=h['selected_action'], cutoff=h['history_cutoff_id'],
                   prediction_sha256=h['prediction_sha256'],
                   outcome_sha256=h['outcome_sha256'],
                   evidence_sha256=h['evidence_sha256'],
                   point_scores=h['point_scores'],
                   post_ack=event['body'] if event else None,
                   confirmed=event is not None)
    if events:
        raise ContractError()  # joined digest with no journal frame
    for event in others:
        yield dict(kind='event', key=event['key'], body=event['body'])
    for event in attempts:
        yield dict(kind='attempt', key=event['key'],
                   reason=event['body'].get('reason'))
    yield dict(kind='trailer', measurements=metrics['produced'],
               findings=metrics['findings'], counts=manifest['counts'])


def iter_science(payload: Payload, capability) -> 'iter':
    """Stream canonical science sections for one assembled payload."""
    return canonical_stream(_sections(payload, capability))


def science_digest(payload: Payload, capability) -> str:
    digest = hashlib.sha256(DOMAIN)
    for chunk in iter_science(payload, capability):
        digest.update(chunk)
    return digest.hexdigest()
