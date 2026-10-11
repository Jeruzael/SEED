"""Prepublished artifact indexes and chunk inventories (I21).

Indexes are visualization/navigation aids built from the lossless payload
before publication. They are never scientific authority: every entry points
back to exact payload bytes by offset and length.
"""
import hashlib
import json

from .contracts import ContractError

CHUNK_BYTES = 64 * 1024
MAX_SERIES = 4
MAX_POINTS = 200
SERIES_SIGNALS = ('battery_pct', 'load_ratio', 'disk_free_pct')


def chunk_inventory(files):
    """Map each payload file except chunks.json to its 64 KiB chunk hashes."""
    result = {}
    for name in sorted(files):
        if name == 'chunks.json':
            continue
        data = files[name]
        chunks = [hashlib.sha256(data[i:i + CHUNK_BYTES]).hexdigest()
                  for i in range(0, len(data), CHUNK_BYTES)]
        result[name] = dict(length=len(data), chunks=chunks)
    return result


def _series(journal_frames):
    series = {}
    unavailable = {}
    for key, header in journal_frames:
        ordinal = key[2]
        scores = header.get('point_scores') or {}
        for signal in SERIES_SIGNALS:
            entry = scores.get(signal)
            if not isinstance(entry, dict):
                continue
            name = f'{key[0]}.{signal}.absolute_error'
            if entry.get('status') == 'scored' and entry.get('absolute_error') is not None:
                series.setdefault(name, []).append([ordinal, entry['absolute_error']])
            elif entry.get('unavailable_reason'):
                unavailable.setdefault(name, []).append(
                    dict(ordinal=ordinal, reason=entry['unavailable_reason']))
    bounded = {}
    for name in sorted(series)[:MAX_SERIES]:
        points = series[name]
        if len(points) > MAX_POINTS:
            step = len(points) / MAX_POINTS
            points = [points[int(i * step)] for i in range(MAX_POINTS)]
        bounded[name] = dict(points=points, unavailable=unavailable.get(name, []))
    return bounded


def build_indexes(payload, read_file=None):
    """Build index.json content for an assembled payload.

    ``read_file(name) -> bytes`` supplies exact payload bytes; the payload
    identity selects the run. The index is validated against the records it
    points to, never the other way around.
    """
    if read_file is None:
        raise ContractError()
    events_raw = read_file('events.ndjson')
    journal_raw = read_file('preupdate.ndjson')
    entries = []
    offset = 0
    for line in events_raw.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            record = json.loads(stripped)
            entries.append(dict(key=record['key'], offset=offset, length=len(line)))
        offset += len(line)
    frames = []
    for line in journal_raw.splitlines():
        if line.strip():
            frames.append(json.loads(line)['header'])
    frame_keys = [(h['phase'], h['subcase'], h['transition_ordinal']) for h in frames]
    return dict(schema='b10_index_v1', run_id=payload.identity,
                events=entries,
                counts=dict(events=len(entries), journal_frames=len(frames)),
                curves=_series(list(zip(frame_keys, frames))))
