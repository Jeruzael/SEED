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
    """Byte-offset index over one published run's journal + event files."""

    __slots__ = ('frames', 'events', 'bound', 'unbound', 'total')

    def __init__(self, frames, events, bound, unbound):
        self.frames = frames      # [(offset, length, key, digest)]
        self.events = events      # [(offset, length, key, journal_sha256)]
        self.bound = bound        # frame position -> event position
        self.unbound = unbound    # [event position] in file order
        self.total = len(frames) + len(unbound)


def _check_deadline(deadline, counter):
    if deadline is not None and counter % 64 == 0 \
            and time.monotonic() > deadline:
        raise ContractError()


def build_index(capability, run_id, deadline=None):
    root = _root(capability)
    directory = payload_directory(root, run_id)
    if directory.parent.name != 'runs':
        raise ContractError()
    frames = []
    counter = 0
    with open(directory / 'preupdate.ndjson', 'rb') as f:
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            counter += 1
            _check_deadline(deadline, counter)
            if not line.strip():
                continue
            record = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
            header = record['header']
            key = (header['phase'], header['subcase'],
                   header['transition_ordinal'])
            digest = hashlib.sha256(
                line if line.endswith(b'\n') else line + b'\n').hexdigest()
            frames.append((offset, len(line), key, digest))
    events = []
    by_digest = {}
    with open(directory / 'events.ndjson', 'rb') as f:
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            counter += 1
            _check_deadline(deadline, counter)
            if not line.strip():
                continue
            event = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
            position = len(events)
            events.append((offset, len(line), tuple(event['key']),
                           event.get('journal_sha256')))
            digest = event.get('journal_sha256')
            if digest and digest not in by_digest:
                by_digest[digest] = position
    bound = {}
    claimed = set()
    for i, (_off, _len, _key, digest) in enumerate(frames):
        position = by_digest.get(digest)
        if position is not None and position not in claimed:
            bound[i] = position
            claimed.add(position)
    unbound = [j for j in range(len(events)) if j not in claimed]
    return ReplayIndex(frames, events, bound, unbound)


def _read_line(path, offset, length):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.pread(fd, length, offset)
    finally:
        os.close(fd)
    if len(data) != length:
        raise ContractError()
    return data


def _frame_row(directory, index, position):
    offset, length, key, _digest = index.frames[position]
    line = _read_line(directory / 'preupdate.ndjson', offset, length)
    record = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
    _validate_frame(record)
    post = None
    event_position = index.bound.get(position)
    if event_position is not None:
        e_off, e_len, _k, _d = index.events[event_position]
        event = strict_json(
            _read_line(directory / 'events.ndjson', e_off, e_len),
            max_bytes=MAX_DETAIL_BYTES)
        post = event['body']
    body = raw_bytes(dict(preupdate=record, post_ack=post,
                          confirmed=post is not None))
    if len(body) > MAX_DETAIL_BYTES:
        raise ContractError()
    return Event((key[0], key[1], key[2], 'update'), body)


def _event_row(directory, index, event_position):
    offset, length, key, _digest = index.events[event_position]
    event = strict_json(
        _read_line(directory / 'events.ndjson', offset, length),
        max_bytes=MAX_DETAIL_BYTES)
    return Event(key, raw_bytes(event['body']))


def read_rows(capability, run_id, index, offset, limit, deadline=None):
    """Materialize rows [offset, offset+limit) of the lossless row sequence,
    reading only the stored lines those rows need."""
    root = _root(capability)
    directory = payload_directory(root, run_id)
    rows = []
    frame_count = len(index.frames)
    for position in range(offset, min(offset + limit, index.total)):
        _check_deadline(deadline, position)
        if position < frame_count:
            rows.append(_frame_row(directory, index, position))
        else:
            rows.append(_event_row(directory, index,
                                   index.unbound[position - frame_count]))
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
