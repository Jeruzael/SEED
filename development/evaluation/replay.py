"""Recorded replay (I24): joins stored journal/post-ACK records only.

Replay presents exactly what was recorded -- the original prediction,
selected action, permitted outcome, point scores and actual update
confirmations. It imports no cognition, scoring or metric machinery and can
never reconstruct, interpolate or repair a historical fact.

Paging is windowed (remediation F3/F4): an offset index over the two
stored files is built by streaming (never by loading whole histories into
memory), page requests read only the lines they return, and the delivered
row inventory is lossless -- every journal frame and every stored event
line (all registered stages, skipped attempts, and duplicate digest rows
included) is delivered exactly once, in a deterministic order: journal
frames in journal order, then unbound event lines in file order.
"""
import hashlib
import os
import time

from .contracts import ContractError, Event, strict_json
from .integrity import payload_directory
from .paths import EvaluationRoot
from .specs import raw_bytes

MAX_DETAIL_BYTES = 64 * 1024


class BudgetError(ContractError):
    """Request byte-budget or deadline exhaustion.

    Internally typed so callers can distinguish resource exhaustion
    from invalid evidence; externally it remains a ContractError, so
    the approved error surface is unchanged."""


class RequestBudget:
    """One coherent per-request budget for replay-related reads.

    Every physical read is preflighted against the remaining allowance
    (admit/pull) before it happens and charged for the actual bytes
    read (charge) afterwards; the deadline is checked before and after
    each operation. Index state advances only for charged bytes."""

    __slots__ = ('remaining', 'deadline')

    def __init__(self, max_bytes, deadline=None):
        self.remaining = max_bytes
        self.deadline = deadline

    def check_deadline(self):
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise BudgetError()

    def admit(self, nbytes):
        """Preflight a known-length read."""
        self.check_deadline()
        if nbytes > self.remaining:
            raise BudgetError()

    def charge(self, data):
        """Account for the actual bytes of a completed read."""
        self.remaining -= len(data)
        if self.remaining < 0:
            raise BudgetError()
        self.check_deadline()

    def pull(self, want):
        """Cap a streaming read at the remaining allowance."""
        self.check_deadline()
        if self.remaining <= 0:
            raise BudgetError()
        return min(want, self.remaining)


def _root(capability):
    if type(capability) is not EvaluationRoot:
        raise ContractError()
    fd = capability._validate()
    os.close(fd)
    return capability


def _domain_hash(domain, value):
    from .channel import wire_bytes
    return hashlib.sha256(
        domain.encode('ascii') + b'\0' + wire_bytes(value)).hexdigest()


def _validate_frame(record):
    """Recompute the stored B8/evidence digests from the stored evidence
    itself; a coordinated journal+pointer tamper still fails here."""
    from seed.decision_record import prediction_digest
    header = record['header']
    evidence = record['evidence']
    try:
        ok = (
            prediction_digest(evidence['prediction']) == header['prediction_sha256']
            and _domain_hash('SEED_B10_PREUPDATE_EVIDENCE_V1', evidence) == header['evidence_sha256']
            and _domain_hash('SEED_B10_OUTCOME_V1', evidence['state_after']) == header['outcome_sha256'])
    except (ValueError, TypeError, KeyError, OverflowError):
        ok = False
    if not ok:
        raise ContractError()


class ReplayIndex:
    """Byte-offset index over one published run's journal + event files.

    The index is built incrementally (remediation B): each advance()
    pulls a bounded number of physical bytes, charges them to the
    caller's request budget, and records resumable scan state, so a
    request that exhausts its budget fails explicitly while the partial
    index retains progress for the next request. Rows are served only
    from a complete index, keeping every delivered row final.
    """

    __slots__ = ('frames', 'events', 'bound', 'unbound', 'total',
                 '_journal_offset', '_journal_pending', '_journal_done',
                 '_events_offset', '_events_pending', '_events_done',
                 '_by_digest')

    def __init__(self, frames=None, events=None, bound=None, unbound=None):
        self.frames = frames if frames is not None else []
        self.events = events if events is not None else []
        self.bound = bound if bound is not None else {}
        self.unbound = unbound if unbound is not None else []
        self.total = len(self.frames) + len(self.unbound)
        self._journal_offset = 0
        self._journal_pending = bytearray()
        self._journal_done = False
        self._events_offset = 0
        self._events_pending = bytearray()
        self._events_done = False
        self._by_digest = {}

    @classmethod
    def empty(cls):
        return cls()

    @property
    def complete(self):
        return self._journal_done and self._events_done


def _process_line(index, source, line, offset):
    if not line.strip():
        return
    if source == 'journal':
        record = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
        header = record['header']
        key = (header['phase'], header['subcase'],
               header['transition_ordinal'])
        digest = hashlib.sha256(
            line if line.endswith(b'\n') else line + b'\n').hexdigest()
        index.frames.append((offset, len(line), key, digest))
    else:
        event = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
        position = len(index.events)
        index.events.append((offset, len(line), tuple(event['key']),
                             event.get('journal_sha256')))
        digest = event.get('journal_sha256')
        if digest and digest not in index._by_digest:
            index._by_digest[digest] = position


def _drain(index, source):
    """Process every complete line held in the pending buffer."""
    pending = index._journal_pending if source == 'journal' \
        else index._events_pending
    done = index._journal_done if source == 'journal' else index._events_done
    while True:
        cut = pending.find(b'\n')
        if cut < 0:
            break
        line = bytes(pending[:cut + 1])
        offset = (index._journal_offset if source == 'journal'
                  else index._events_offset) - len(pending)
        del pending[:cut + 1]
        _process_line(index, source, line, offset)
    if done and pending:
        line = bytes(pending)
        offset = (index._journal_offset if source == 'journal'
                  else index._events_offset) - len(pending)
        del pending[:]
        _process_line(index, source, line, offset)


def _scan_some(index, path, source, budget):
    """Pull physical bytes from one file into the resumable scan state.

    Each pull is capped at the budget's remaining allowance BEFORE the
    read; the index offsets/pending buffers advance only for bytes that
    were successfully charged, so exhaustion never marks unread bytes
    as processed and never discards prior progress. Returns the number
    of physical bytes pulled."""
    done = index._journal_done if source == 'journal' else index._events_done
    if done:
        return 0
    _drain(index, source)
    pulled = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        size = os.fstat(fd).st_size
        while True:
            offset = index._journal_offset if source == 'journal' \
                else index._events_offset
            if offset >= size:
                if source == 'journal':
                    index._journal_done = True
                else:
                    index._events_done = True
                _drain(index, source)
                break
            want = budget.pull(64 * 1024) if budget is not None \
                else 64 * 1024
            data = os.pread(fd, want, offset)
            if not data:
                break
            if budget is not None:
                budget.charge(data)
            if source == 'journal':
                index._journal_pending += data
                index._journal_offset += len(data)
            else:
                index._events_pending += data
                index._events_offset += len(data)
            pulled += len(data)
            _drain(index, source)
    finally:
        os.close(fd)
    return pulled


def _finalize(index):
    bound = {}
    claimed = set()
    for i, (_off, _len, _key, digest) in enumerate(index.frames):
        position = index._by_digest.get(digest)
        if position is not None and position not in claimed:
            bound[i] = position
            claimed.add(position)
    index.bound = bound
    index.unbound = [j for j in range(len(index.events))
                     if j not in claimed]
    index.total = len(index.frames) + len(index.unbound)


def advance(capability, run_id, index, *, budget=None):
    """Advance the incremental index (journal first, then events),
    charging every pulled byte to the request budget. Returns the
    physical bytes pulled in this call."""
    root = _root(capability)
    directory = payload_directory(root, run_id)
    if directory.parent.name != 'runs':
        raise ContractError()
    pulled = 0
    if not index._journal_done:
        pulled += _scan_some(index, directory / 'preupdate.ndjson',
                             'journal', budget)
    if index._journal_done and not index._events_done:
        pulled += _scan_some(index, directory / 'events.ndjson',
                             'events', budget)
    if index.complete:
        _finalize(index)
    return pulled


def build_index(capability, run_id, budget=None, resume=None):
    """Build (or resume building) the complete index. With a budget the
    build stops by raising BudgetError; the partially built index (pass
    it back via resume) retains exactly the progress that was charged."""
    index = resume if resume is not None else ReplayIndex.empty()
    while not index.complete:
        pulled = advance(capability, run_id, index, budget=budget)
        if pulled == 0 and not index.complete:
            raise ContractError()
    return index


def _read_line(path, offset, length):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.pread(fd, length, offset)
    finally:
        os.close(fd)
    if len(data) != length:
        raise ContractError()
    return data


def _frame_row(directory, index, position, budget=None):
    offset, length, key, _digest = index.frames[position]
    event_position = index.bound.get(position)
    if budget is not None:
        # Preflight the exact stored spans before any physical read.
        spans = length
        if event_position is not None:
            spans += index.events[event_position][1]
        budget.admit(spans)
    line = _read_line(directory / 'preupdate.ndjson', offset, length)
    if budget is not None:
        budget.charge(line)
    record = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
    _validate_frame(record)
    post = None
    if event_position is not None:
        e_off, e_len, _k, _d = index.events[event_position]
        event_line = _read_line(directory / 'events.ndjson', e_off, e_len)
        if budget is not None:
            budget.charge(event_line)
        event = strict_json(event_line, max_bytes=MAX_DETAIL_BYTES)
        post = event['body']
    body = raw_bytes(dict(preupdate=record, post_ack=post,
                          confirmed=post is not None))
    if len(body) > MAX_DETAIL_BYTES:
        raise ContractError()
    return Event((key[0], key[1], key[2], 'update'), body)


def _event_row(directory, index, event_position, budget=None):
    offset, length, key, _digest = index.events[event_position]
    if budget is not None:
        budget.admit(length)
    line = _read_line(directory / 'events.ndjson', offset, length)
    if budget is not None:
        budget.charge(line)
    event = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
    return Event(key, raw_bytes(event['body']))


def read_rows(capability, run_id, index, offset, limit, budget=None):
    """Materialize rows [offset, offset+limit) of the lossless row sequence,
    reading only the stored lines those rows need. With a budget, every
    read is preflighted and charged; budget/deadline exhaustion raises
    BudgetError, while invalid evidence raises ContractError."""
    if not index.complete:
        raise ContractError()
    root = _root(capability)
    directory = payload_directory(root, run_id)
    rows = []
    frame_count = len(index.frames)
    for position in range(offset, min(offset + limit, index.total)):
        if budget is not None:
            budget.check_deadline()
        if position < frame_count:
            rows.append(_frame_row(directory, index, position, budget))
        else:
            rows.append(_event_row(directory, index,
                                   index.unbound[position - frame_count],
                                   budget))
    return rows


def join_events(capability, run_id):
    """Strict full join: every frame validated, every journal pointer
    resolved. Raises on any unresolved post-ACK pointer."""
    index = build_index(capability, run_id)
    for j in index.unbound:
        if index.events[j][3]:
            raise ContractError()
    root = _root(capability)
    directory = payload_directory(root, run_id)
    rows = [_frame_row(directory, index, i) for i in range(len(index.frames))]
    rows += [_event_row(directory, index, j) for j in index.unbound]
    rows.sort(key=lambda e: e.key)
    return rows
