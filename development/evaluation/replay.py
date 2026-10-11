"""Recorded replay (I24): joins stored journal/post-ACK records only.

Replay presents exactly what was recorded -- the original prediction,
selected action, permitted outcome, point scores and actual update
confirmations. It imports no cognition, scoring or metric machinery and can
never reconstruct, interpolate or repair a historical fact.
"""
import hashlib

from .contracts import ContractError, Event, strict_json
from .integrity import payload_directory
from .paths import EvaluationRoot
from .specs import raw_bytes

MAX_DETAIL_BYTES = 64 * 1024


def _root(capability):
    if type(capability) is not EvaluationRoot:
        raise ContractError()
    fd = capability._validate()
    import os
    os.close(fd)
    return capability


def join_events(capability, run_id):
    """Join every journal frame with its post-ACK record by tuple+digest."""
    root = _root(capability)
    directory = payload_directory(root, run_id)
    if directory.parent.name != 'runs':
        raise ContractError()
    journal_raw = (directory / 'preupdate.ndjson').read_bytes()
    events_raw = (directory / 'events.ndjson').read_bytes()
    by_digest = {}
    for line in events_raw.splitlines():
        if line.strip():
            event = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
            if event.get('journal_sha256'):
                by_digest[event['journal_sha256']] = event
    joined = []
    for line in journal_raw.splitlines(keepends=True):
        if not line.strip():
            continue
        record = strict_json(line, max_bytes=MAX_DETAIL_BYTES)
        header = record['header']
        digest = hashlib.sha256(
            line if line.endswith(b'\n') else line + b'\n').hexdigest()
        post = by_digest.pop(digest, None)
        body = raw_bytes(dict(preupdate=record,
                              post_ack=post['body'] if post else None,
                              confirmed=post is not None))
        if len(body) > MAX_DETAIL_BYTES:
            raise ContractError()
        joined.append(Event((header['phase'], header['subcase'],
                             header['transition_ordinal'], 'update'), body))
    if by_digest:
        raise ContractError()
    joined.sort(key=lambda e: e.key)
    return joined
