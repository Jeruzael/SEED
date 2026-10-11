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
from .paths import EvaluationRoot, _directory, _identity, _open_nested
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
        self._chunk_verified = set()
        self._replay_indexes = {}
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
        metrics = strict_json(self._read(directory, 'metrics.json', 256 * 1024),
                              max_bytes=256 * 1024)
        key = ('detail', run_id)
        all_names = []
        for entry in sorted(os.scandir(directory), key=lambda e: e.name):
            if entry.is_dir(follow_symlinks=False):
                all_names.extend(f'{entry.name}/{sub.name}' for sub in
                                 sorted(os.scandir(entry.path),
                                        key=lambda e: e.name))
            else:
                all_names.append(entry.name)
        fingerprint = {name: self._fingerprint(directory / name)
                       for name in all_names}
        stale = self._fingerprints.get(key) not in (None, fingerprint)
        self._fingerprints[key] = fingerprint
        verification = 'verification_pending' if stale else \
            'whole_payload_verified_at_publication'
        summary_body = raw_bytes(dict(
            run_id=run_id, status=manifest['status'], reason=manifest['reason'],
            science_digest=manifest['science_digest'],
            counts=manifest['counts'], measurements=metrics['produced'],
            verification=verification,
            chunk_verification='chunk_verified' if run_id in self._chunk_verified
            else 'none'))
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

    def _replay_index(self, run_id):
        directory = payload_directory(self._root, run_id)
        fingerprint = (self._fingerprint(directory / 'preupdate.ndjson'),
                       self._fingerprint(directory / 'events.ndjson'))
        cached = self._replay_indexes.get(run_id)
        if cached is not None and cached[0] == fingerprint:
            index = cached[1]
        else:
            index = _replay.ReplayIndex.empty()
        try:
            # The incremental build charges every physical byte it pulls
            # to this request's budget (_tick). On a bounded failure the
            # partially built index is cached, so the next request
            # resumes the scan instead of restarting it.
            _replay.build_index(
                self._root, run_id,
                deadline=self._started + REQUEST_SECONDS,
                charge=self._tick, resume=index)
        except ContractError:
            self._replay_indexes[run_id] = (fingerprint, index)
            raise
        self._replay_indexes[run_id] = (fingerprint, index)
        return index

    def events(self, run_id, cursor=None, limit=20):
        self._begin()
        self._receipt(run_id)
        if type(limit) is not int or not 1 <= limit <= PAGE_LIMIT:
            raise ContractError()
        offset = _offset(cursor)
        index = self._replay_index(run_id)
        page = []
        position = offset
        page_bytes = 0
        while position < index.total and len(page) < limit:
            try:
                row = _replay.read_rows(
                    self._root, run_id, index, position, 1,
                    deadline=self._started + REQUEST_SECONDS,
                    charge=self._tick)[0]
            except ContractError:
                if page:
                    break  # bounded partial page; cursor still advances
                # Single-record escape: one row is always servable (its
                # line is bounded by the 64 KiB record cap), mirroring
                # the page-body rule; corruption still raises from here.
                row = _replay.read_rows(
                    self._root, run_id, index, position, 1,
                    deadline=self._started + REQUEST_SECONDS)[0]
            if page and page_bytes + len(row.body) > REQUEST_BYTES:
                break
            page_bytes += len(row.body)
            page.append(row)
            position += 1
        next_cursor = _cursor(position) if position < index.total else None
        return ReplayPage(tuple(page), next_cursor)

    def event(self, run_id, key):
        self._begin()
        self._receipt(run_id)
        key = tuple(key)
        index = self._replay_index(run_id)
        for i, (_o, _l, frame_key, _d) in enumerate(index.frames):
            if (frame_key[0], frame_key[1], frame_key[2], 'update') == key:
                return _replay.read_rows(self._root, run_id, index, i, 1,
                                         charge=self._tick)[0]
        for j, (_o, _l, event_key, _d) in enumerate(index.events):
            if event_key == key:
                rows = _replay.read_rows(
                    self._root, run_id, index,
                    len(index.frames) + index.unbound.index(j), 1,
                    charge=self._tick) \
                    if j in index.unbound else None
                if rows:
                    return rows[0]
                # A bound event is presented through its transition row.
                return _replay.read_rows(
                    self._root, run_id, index,
                    next(i for i, ej in index.bound.items() if ej == j), 1,
                    charge=self._tick)[0]
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
        path = directory / file_id
        if os.path.getsize(path) != entry['length']:
            raise ContractError()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            piece = os.pread(fd, CHUNK_BYTES, chunk * CHUNK_BYTES)
        finally:
            os.close(fd)
        self._tick(piece)
        if hashlib.sha256(piece).hexdigest() != entry['chunks'][chunk]:
            raise ContractError()
        self._chunk_verified.add(run_id)
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
            # Descriptor-relative validation before SQLite's native open
            # (Option B covers only the native-open interval): every path
            # component must be an owned directory/regular file, and the
            # file identity must be unchanged afterwards.
            run_fd = _directory(directory)
            try:
                fd = _open_nested(run_fd, entry['file'], 'read')
                try:
                    identity = _identity(os.fstat(fd))
                finally:
                    os.close(fd)
            finally:
                os.close(run_fd)
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
            run_fd = _directory(directory)
            try:
                fd = _open_nested(run_fd, entry['file'], 'read')
                try:
                    if _identity(os.fstat(fd)) != identity:
                        raise ContractError()
                finally:
                    os.close(fd)
            finally:
                os.close(run_fd)
        return names
