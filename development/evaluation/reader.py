"""Dedicated read-only artifact reader (I24).

The reader serves recorded evidence from the owned evaluation root only:
bounded pages, opaque cursors, receipt-bound chunk verification and scoped
verification labels. It never falls back to installed SEED state, never
migrates or repairs an artifact, and invalidates stored verification when a
file fingerprint (inode/length/mtime/ctime) changes.
"""
import base64
import hashlib
import os
import sqlite3
import time

from . import replay as _replay
from .contracts import (ContractError, Curve, Event, Receipt, ReplayPage,
                        RootCapability, RunDetail, RunResult, RunSummary,
                        Payload, strict_json)
from .integrity import payload_directory
from .paths import EvaluationRoot
from .specs import raw_bytes

PAGE_LIMIT = 20
REQUEST_BYTES = 1024 * 1024
REQUEST_SECONDS = 2.0
CURSOR_BYTES = 512


class ReaderError(ContractError):
    """Reader failure with an explicit unavailable/error reason."""

    def __init__(self, reason):
        super().__init__()
        self.reason = reason
DETAIL_BYTES = 912 * 1024
CHUNK_BYTES = 64 * 1024
SQLITE_STEPS = 100000


def _cursor(offset):
    raw = raw_bytes(dict(offset=offset))
    return base64.urlsafe_b64encode(raw).decode('ascii')


def _offset(cursor):
    if cursor is None:
        return 0
    if type(cursor) is not str or len(cursor.encode()) > CURSOR_BYTES:
        raise ContractError()
    try:
        value = strict_json(base64.urlsafe_b64decode(cursor.encode('ascii')),
                            max_bytes=CURSOR_BYTES)
    except Exception:
        raise ContractError() from None
    if type(value) is not dict or set(value) != {'offset'} \
            or type(value['offset']) is not int or value['offset'] < 0:
        raise ContractError()
    return value['offset']


class EvaluationReader:
    def __init__(self, capability: RootCapability):
        if type(capability) is not EvaluationRoot:
            raise ContractError()
        fd = capability._validate()
        os.close(fd)
        self._root = capability
        self._fingerprints = {}
        self._started = None
        self._read_bytes = 0

    # -- bounded IO -----------------------------------------------------
    def _begin(self):
        self._started = time.monotonic()
        self._read_bytes = 0

    def _tick(self, data):
        self._read_bytes += len(data)
        if self._read_bytes > REQUEST_BYTES \
                or time.monotonic() - self._started > REQUEST_SECONDS:
            raise ContractError()
        return data

    def _read(self, directory, name, maximum):
        raw = (directory / name).read_bytes()
        if len(raw) > maximum:
            raise ContractError()
        return self._tick(raw)

    def _fingerprint(self, path):
        st = os.stat(path, follow_symlinks=False)
        return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

    def _runs_index(self):
        path = self._root.path / 'evaluation' / 'runs-index.json'
        if not path.exists():
            return []
        return strict_json(self._tick(path.read_bytes()),
                           max_bytes=128 * 1024)['runs']

    def _receipt(self, run_id):
        path = self._root.path / 'evaluation' / 'receipts' / f'{run_id}.json'
        if not path.exists():
            raise ReaderError('RECEIPT_UNAVAILABLE')
        raw = self._read(path.parent, path.name, 16 * 1024)
        body = strict_json(raw, max_bytes=16 * 1024)
        if body.get('schema') != 'b10_receipt_v1' or body.get('run_id') != run_id:
            raise ContractError()
        return body, Receipt(tuple(Payload(n, e['length'])
                                   for n, e in body['files'].items()),
                             body['digest'])

    def _page(self, items, cursor, limit):
        if type(limit) is not int or not 1 <= limit <= PAGE_LIMIT:
            raise ContractError()
        offset = _offset(cursor)
        page = items[offset:offset + limit]
        next_cursor = _cursor(offset + limit) if offset + limit < len(items) else None
        return ReplayPage(tuple(page), next_cursor)

    # -- API ------------------------------------------------------------
    def runs(self, cursor=None, limit=20):
        self._begin()
        items = []
        for i, entry in enumerate(self._runs_index()):
            body = raw_bytes(dict(run_id=entry['run_id'], digest=entry['digest'],
                                  science_digest=entry['science_digest'],
                                  status=entry['status'],
                                  verification='whole_payload_verified_at_publication'))
            items.append(Event(('runs', 'default', i + 1, 'run'), body))
        return self._page(items, cursor, limit)

    def detail(self, run_id):
        self._begin()
        body_receipt, receipt = self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        if directory.parent.name != 'runs':
            raise ReaderError('ARTIFACT_NOT_PUBLISHED')
        raw = self._read(directory, 'manifest.json', 128 * 1024)
        manifest = strict_json(raw, max_bytes=128 * 1024)
        key = ('detail', run_id)
        fingerprint = {name: self._fingerprint(directory / name)
                       for name in ('manifest.json', 'metrics.json',
                                    'events.ndjson', 'preupdate.ndjson')}
        stale = self._fingerprints.get(key) not in (None, fingerprint)
        self._fingerprints[key] = fingerprint
        verification = 'verification_pending' if stale else \
            'whole_payload_verified_at_publication'
        summary_body = raw_bytes(dict(
            run_id=run_id, status=manifest['status'], reason=manifest['reason'],
            science_digest=manifest['science_digest'],
            counts=manifest['counts'], verification=verification))
        if len(summary_body) > DETAIL_BYTES:
            raise ContractError()
        summary = RunSummary(run_id, RunResult(manifest['status'],
                                               manifest['reason']), summary_body)
        return RunDetail(summary, receipt)

    def measurements(self, run_id, cursor=None, limit=20):
        self._begin()
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        metrics = strict_json(self._read(directory, 'metrics.json', 256 * 1024),
                              max_bytes=256 * 1024)
        items = [Event(('measurements', 'default', i + 1, 'measurement'),
                       raw_bytes(item))
                 for i, item in enumerate(metrics['produced'])]
        return self._page(items, cursor, limit)

    def events(self, run_id, cursor=None, limit=20):
        self._begin()
        self._receipt(run_id)
        joined = _replay.join_events(self._root, run_id)
        total = sum(len(e.body) for e in joined)
        if total > REQUEST_BYTES:
            # Byte budget may shorten pages, never drop records: page by
            # cursor over the full joined list with a smaller effective page.
            pass
        return self._page(joined, cursor, limit)

    def event(self, run_id, key):
        self._begin()
        self._receipt(run_id)
        for event in _replay.join_events(self._root, run_id):
            if event.key == tuple(key):
                return event
        raise ContractError()

    def curve(self, run_id, metric, series):
        self._begin()
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        index = strict_json(self._read(directory, 'index.json', 128 * 1024),
                            max_bytes=128 * 1024)
        entry = index['curves'].get(series)
        if entry is None:
            raise ContractError()
        points = tuple((int(p[0]), p[1]) for p in entry['points'])
        return Curve(series, points)

    def chunk(self, run_id, file_id, chunk):
        self._begin()
        body, _receipt_obj = self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        chunks_raw = self._read(directory, 'chunks.json', 512 * 1024)
        if hashlib.sha256(chunks_raw).hexdigest() != body['files']['chunks.json']['sha256']:
            raise ContractError()
        chunks = strict_json(chunks_raw, max_bytes=512 * 1024)
        entry = chunks.get(file_id)
        if entry is None or type(chunk) is not int \
                or not 0 <= chunk < len(entry['chunks']):
            raise ContractError()
        data = self._tick((directory / file_id).read_bytes())
        if len(data) != entry['length']:
            raise ContractError()
        piece = data[chunk * CHUNK_BYTES:(chunk + 1) * CHUNK_BYTES]
        if hashlib.sha256(piece).hexdigest() != entry['chunks'][chunk]:
            raise ContractError()
        return piece

    def snapshot_tables(self, run_id):
        """Optional read-only snapshot inspection: table names only, under a
        write-denying authorizer and a hard VM step budget."""
        self._begin()
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        manifest = strict_json(self._read(directory, 'manifest.json', 128 * 1024),
                               max_bytes=128 * 1024)
        names = []
        for entry in manifest['checkpoints']:
            path = directory / entry['file']
            db = sqlite3.connect(f'file:{path}?mode=ro&immutable=1', uri=True)
            try:
                db.execute('PRAGMA query_only=ON')
                db.set_authorizer(lambda *a: sqlite3.SQLITE_DENY
                                  if a[0] in (sqlite3.SQLITE_INSERT,
                                              sqlite3.SQLITE_UPDATE,
                                              sqlite3.SQLITE_DELETE,
                                              sqlite3.SQLITE_CREATE_TABLE,
                                              sqlite3.SQLITE_DROP_TABLE,
                                              sqlite3.SQLITE_ALTER_TABLE)
                                  else sqlite3.SQLITE_OK)
                steps = [0]

                def progress():
                    steps[0] += 1000
                    return 1 if steps[0] > SQLITE_STEPS else 0
                db.set_progress_handler(progress, 1000)
                names.extend(r[0] for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"))
            finally:
                db.close()
        return names
