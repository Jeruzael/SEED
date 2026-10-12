"""Dedicated read-only artifact reader (I24).

The reader serves recorded evidence from the owned evaluation root only:
bounded pages, opaque cursors, receipt-bound chunk verification and scoped
verification labels. It never falls back to installed SEED state, never
migrates or repairs an artifact, and invalidates stored verification when a
file fingerprint (inode/length/mtime/ctime) changes.
"""
import base64
import contextvars
import functools
import hashlib
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

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


class _RequestSession:
    """One request-scoped budget, deadline and read cache (MAJOR-1).

    Every physical read performed while serving one request -- receipt,
    manifests, metrics, chunk index, chunk slices, replay index scans
    and row lines -- is preflighted and charged against this single
    session's 1 MiB / 2 s allowance, however many reader calls the
    request composes. Sessions are held in a context variable, so
    concurrent requests on one shared reader instance each own an
    independent session; no budget state lives on the reader itself.
    Receipts, parsed chunk indexes, verified file bytes and raw reads
    are memoized per session, so a byte is physically read at most
    once per request. All state is released when the session ends.
    """

    __slots__ = ('budget', 'ambient', 'receipts', 'chunks', 'files',
                 'raw')

    def __init__(self, budget, ambient):
        self.budget = budget
        self.ambient = ambient
        self.receipts = {}
        self.chunks = {}
        self.files = {}
        self.raw = {}

    def deadline_passed(self):
        return self.budget.deadline is not None \
            and time.monotonic() > self.budget.deadline


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
        self._cache_lock = threading.Lock()
        self._index_locks = {}
        self._sessions = contextvars.ContextVar(
            f'evaluation_reader_session_{id(self)}', default=None)

    # -- request sessions -------------------------------------------------
    def _new_session(self, ambient):
        # One coherent request budget (remediation R-BUDGET, extended
        # by MAJOR-1 from one reader call to one whole request).
        budget = _replay.RequestBudget(
            REQUEST_BYTES, time.monotonic() + REQUEST_SECONDS)
        return _RequestSession(budget, ambient)

    def _session(self):
        session = self._sessions.get()
        if session is None:
            session = self._new_session(False)
            self._sessions.set(session)
        return session

    @contextmanager
    def request_session(self):
        """Scope an ambient request session over composed reader calls.

        Nested entry reuses the active ambient session (never resets
        it). Standalone reader calls outside a session keep the
        historical per-call budget: each public method begins a fresh
        transient session for itself.
        """
        session = self._sessions.get()
        if session is not None and session.ambient:
            yield session
            return
        session = self._new_session(True)
        token = self._sessions.set(session)
        try:
            yield session
        finally:
            self._sessions.reset(token)

    def _public(method):
        """Public-operation lifecycle: the call that owns a
        transient session releases it (and its raw-file caches) when
        the operation completes, on success and on failure alike.
        Ambient sessions spanning composed calls are unaffected."""
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            owned = self._begin()
            try:
                return method(self, *args, **kwargs)
            finally:
                if owned:
                    self._sessions.set(None)
        return wrapper

    def _begin(self):
        """Begin one public operation, creating a transient session
        when none is active. Returns True only when this call created
        the context's first transient session and therefore owns its
        release (M-04). Ambient request sessions are never reset or
        replaced; a nested standalone call refreshes the transient
        session (the historical per-call semantics) without owning
        its release."""
        session = self._sessions.get()
        if session is not None and session.ambient:
            return False
        owned = session is None
        self._sessions.set(self._new_session(False))
        return owned

    # -- bounded IO -----------------------------------------------------
    def _tick(self, data):
        self._session().budget.charge(data)
        return data

    def _read(self, directory, name, maximum):
        session = self._session()
        key = (str(directory), name)
        if key in session.raw:
            return session.raw[key]
        path = directory / name
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            raise ContractError() from None
        try:
            # Admission uses the descriptor's own size and every
            # physical read is capped at the admitted length, so a
            # file that grows after any check can never be over-read.
            size = os.fstat(fd).st_size
            if size > maximum:
                raise ContractError()
            session.budget.admit(size)
            raw = b''
            while len(raw) < size:
                piece = os.pread(fd, size - len(raw), len(raw))
                if not piece:
                    break
                raw += piece
        finally:
            os.close(fd)
        if len(raw) != size:
            raise ContractError()
        self._tick(raw)
        session.raw[key] = raw
        return raw

    def _fingerprint(self, path):
        st = os.stat(path, follow_symlinks=False)
        return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

    def _runs_index(self):
        path = self._root.path / 'evaluation' / 'runs-index.json'
        if not path.exists():
            return []
        raw = self._read(path.parent, path.name, 128 * 1024)
        return strict_json(raw, max_bytes=128 * 1024)['runs']

    def _receipt(self, run_id):
        session = self._session()
        if run_id in session.receipts:
            return session.receipts[run_id]
        path = self._root.path / 'evaluation' / 'receipts' / f'{run_id}.json'
        if not path.exists():
            raise ReaderError('RECEIPT_UNAVAILABLE')
        raw = self._read(path.parent, path.name, 16 * 1024)
        body = strict_json(raw, max_bytes=16 * 1024)
        if body.get('schema') != 'b10_receipt_v1' or body.get('run_id') != run_id:
            raise ContractError()
        result = (body, Receipt(tuple(Payload(n, e['length'])
                                      for n, e in body['files'].items()),
                                body['digest']))
        session.receipts[run_id] = result
        return result

    @_public
    def receipt(self, run_id):
        """The receipt-verified payload inventory for one run."""
        return self._receipt(run_id)[1]

    def _chunks(self, run_id, directory):
        """The run's chunk inventory, hash-verified against its receipt
        and parsed at most once per request session."""
        session = self._session()
        if run_id in session.chunks:
            return session.chunks[run_id]
        body, _receipt_obj = self._receipt(run_id)
        raw = self._read(directory, 'chunks.json', 512 * 1024)
        if hashlib.sha256(raw).hexdigest() \
                != body['files']['chunks.json']['sha256']:
            raise ContractError()
        chunks = strict_json(raw, max_bytes=512 * 1024)
        session.chunks[run_id] = chunks
        return chunks

    @_public
    def verified_file(self, run_id, name):
        """Assemble one stored file from receipt-verified chunks.

        Every chunk hash is checked against the receipt-verified chunk
        inventory. Bytes already read earlier in this request session
        are verified in place instead of being physically re-read;
        otherwise each chunk is admitted, read with a capped pread and
        charged exactly once.
        """
        session = self._session()
        key = (run_id, name)
        if key in session.files:
            return session.files[key]
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        entry = self._chunks(run_id, directory).get(name)
        if entry is None:
            raise ContractError()
        raw = session.raw.get((str(directory), name))
        if raw is not None and len(raw) == entry['length']:
            data = raw
        else:
            path = directory / name
            if os.path.getsize(path) != entry['length']:
                raise ContractError()
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                parts = []
                for index, _digest in enumerate(entry['chunks']):
                    want = min(CHUNK_BYTES,
                               entry['length'] - index * CHUNK_BYTES)
                    session.budget.admit(want)
                    piece = os.pread(fd, want, index * CHUNK_BYTES)
                    self._tick(piece)
                    if len(piece) != want:
                        raise ContractError()
                    parts.append(piece)
            finally:
                os.close(fd)
            data = b''.join(parts)
        for index, digest in enumerate(entry['chunks']):
            piece = data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]
            if hashlib.sha256(piece).hexdigest() != digest:
                raise ContractError()
        session.files[key] = data
        return data

    def _page(self, items, cursor, limit):
        if type(limit) is not int or not 1 <= limit <= PAGE_LIMIT:
            raise ContractError()
        offset = _offset(cursor)
        page = items[offset:offset + limit]
        next_cursor = _cursor(offset + limit) if offset + limit < len(items) else None
        return ReplayPage(tuple(page), next_cursor)

    # -- API ------------------------------------------------------------
    @_public
    def runs(self, cursor=None, limit=20):
        items = []
        for i, entry in enumerate(self._runs_index()):
            body = raw_bytes(dict(run_id=entry['run_id'], digest=entry['digest'],
                                  science_digest=entry['science_digest'],
                                  status=entry['status'],
                                  verification='whole_payload_verified_at_publication'))
            items.append(Event(('runs', 'default', i + 1, 'run'), body))
        return self._page(items, cursor, limit)

    @_public
    def detail(self, run_id):
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
        with self._cache_lock:
            stale = self._fingerprints.get(key) not in (None, fingerprint)
            self._fingerprints[key] = fingerprint
            chunk_state = run_id in self._chunk_verified
        verification = 'verification_pending' if stale else \
            'whole_payload_verified_at_publication'
        summary_body = raw_bytes(dict(
            run_id=run_id, status=manifest['status'], reason=manifest['reason'],
            science_digest=manifest['science_digest'],
            counts=manifest['counts'], measurements=metrics['produced'],
            verification=verification,
            chunk_verification='chunk_verified' if chunk_state
            else 'none'))
        if len(summary_body) > DETAIL_BYTES:
            raise ContractError()
        summary = RunSummary(run_id, RunResult(manifest['status'],
                                               manifest['reason']), summary_body)
        return RunDetail(summary, receipt)

    @_public
    def measurements(self, run_id, cursor=None, limit=20):
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        metrics = strict_json(self._read(directory, 'metrics.json', 256 * 1024),
                              max_bytes=256 * 1024)
        items = [Event(('measurements', 'default', i + 1, 'measurement'),
                       raw_bytes(item))
                 for i, item in enumerate(metrics['produced'])]
        return self._page(items, cursor, limit)

    def _index_lock(self, run_id):
        with self._cache_lock:
            return self._index_locks.setdefault(run_id, threading.RLock())

    def _replay_index(self, run_id):
        # The shared resumable index cache is guarded per run: building
        # or resuming one run's index never blocks another run, and two
        # requests for the same run cannot interleave scan state. The
        # budget charged is always the caller's own session budget.
        with self._index_lock(run_id):
            directory = payload_directory(self._root, run_id)
            fingerprint = (self._fingerprint(directory / 'preupdate.ndjson'),
                           self._fingerprint(directory / 'events.ndjson'))
            cached = self._replay_indexes.get(run_id)
            if cached is not None and cached[0] == fingerprint:
                index = cached[1]
            else:
                index = _replay.ReplayIndex.empty()
            try:
                # The incremental build preflights and charges every
                # physical byte it pulls against this request's budget.
                # On a bounded failure the partially built index is
                # cached, so the next request resumes the scan instead
                # of restarting it.
                _replay.build_index(self._root, run_id,
                                    budget=self._session().budget,
                                    resume=index)
            except ContractError:
                self._replay_indexes[run_id] = (fingerprint, index)
                raise
            self._replay_indexes[run_id] = (fingerprint, index)
            return index

    @_public
    def events(self, run_id, cursor=None, limit=20):
        self._receipt(run_id)
        if type(limit) is not int or not 1 <= limit <= PAGE_LIMIT:
            raise ContractError()
        offset = _offset(cursor)
        budget = self._session().budget
        with self._index_lock(run_id):
            index = self._replay_index(run_id)
            page = []
            position = offset
            page_bytes = 0
            while position < index.total and len(page) < limit:
                try:
                    row = _replay.read_rows(
                        self._root, run_id, index, position, 1,
                        budget=budget)[0]
                except _replay.BudgetError:
                    # Resource exhaustion only. With rows already served,
                    # return the bounded partial page (its cursor points
                    # at the unserved row); on an empty page the explicit
                    # bounded error propagates -- no unmetered retry, no
                    # skipped record, no stalled successful cursor. Any
                    # other ContractError is invalid evidence and
                    # propagates untouched, even mid-page.
                    if page:
                        break
                    raise
                if page and page_bytes + len(row.body) > REQUEST_BYTES:
                    break
                page_bytes += len(row.body)
                page.append(row)
                position += 1
        next_cursor = _cursor(position) if position < index.total else None
        return ReplayPage(tuple(page), next_cursor)

    @_public
    def event(self, run_id, key):
        self._receipt(run_id)
        key = tuple(key)
        budget = self._session().budget
        with self._index_lock(run_id):
            index = self._replay_index(run_id)
            for i, (_o, _l, frame_key, _d) in enumerate(index.frames):
                if (frame_key[0], frame_key[1], frame_key[2],
                        'update') == key:
                    return _replay.read_rows(self._root, run_id, index, i,
                                             1, budget=budget)[0]
            for j, (_o, _l, event_key, _d) in enumerate(index.events):
                if event_key == key:
                    rows = _replay.read_rows(
                        self._root, run_id, index,
                        len(index.frames) + index.unbound.index(j), 1,
                        budget=budget) \
                        if j in index.unbound else None
                    if rows:
                        return rows[0]
                    # A bound event is presented through its transition
                    # row.
                    return _replay.read_rows(
                        self._root, run_id, index,
                        next(i for i, ej in index.bound.items()
                             if ej == j), 1, budget=budget)[0]
        raise ContractError()

    @_public
    def curve(self, run_id, metric, series):
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        index = strict_json(self._read(directory, 'index.json', 128 * 1024),
                            max_bytes=128 * 1024)
        entry = index['curves'].get(series)
        if entry is None:
            raise ContractError()
        points = tuple((int(p[0]), p[1]) for p in entry['points'])
        return Curve(series, points)

    @_public
    def chunk(self, run_id, file_id, chunk):
        self._receipt(run_id)
        directory = payload_directory(self._root, run_id)
        chunks = self._chunks(run_id, directory)
        entry = chunks.get(file_id)
        if entry is None or type(chunk) is not int \
                or not 0 <= chunk < len(entry['chunks']):
            raise ContractError()
        path = directory / file_id
        if os.path.getsize(path) != entry['length']:
            raise ContractError()
        expected = min(CHUNK_BYTES, entry['length'] - chunk * CHUNK_BYTES)
        self._session().budget.admit(expected)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            # The physical read is capped at the admitted length, so a
            # file that grows after the size check cannot be over-read.
            piece = os.pread(fd, expected, chunk * CHUNK_BYTES)
        finally:
            os.close(fd)
        if len(piece) != expected:
            raise ContractError()
        self._tick(piece)
        if hashlib.sha256(piece).hexdigest() != entry['chunks'][chunk]:
            raise ContractError()
        with self._cache_lock:
            self._chunk_verified.add(run_id)
        return piece

    @_public
    def snapshot_tables(self, run_id):
        """Optional read-only snapshot inspection: table names only, under a
        write-denying authorizer and a hard VM step budget."""
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
