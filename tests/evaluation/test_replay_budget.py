"""Remediation B: the COMPLETE cost of a replay page request is charged
to the 1 MiB / 2 s request budget -- indexing scans included, not just
returned bodies. Oversized histories fail with an explicit bounded
error while the resumable index retains progress across requests.
"""
import time

import pytest

from .test_artifacts import RUN, _record
from .test_replay import _publish

FRAMES = 24


def _big_root(tmp_path, foundation_module, plan_body):
    events = [dict(key=['measured', 'default', i + 1, 'update'],
                   body=dict(blob={f'k{j}': 'x' * 4000 for j in range(13)}))
              for i in range(FRAMES)]
    return _publish(tmp_path, foundation_module, plan_body,
                    record=_record(events=events,
                                   planned_transitions=FRAMES),
                    frames=FRAMES)


def _traverse(reader, limit=20, max_requests=100):
    seen, cursor, errors = [], None, 0
    for _ in range(max_requests):
        from development.evaluation.contracts import ContractError
        try:
            page = reader.events(RUN, cursor=cursor, limit=limit)
        except ContractError:
            errors += 1
            continue
        seen.extend(e.key for e in page.events)
        if page.cursor is None:
            return seen, errors
        assert page.cursor != cursor  # a returned cursor always advances
        cursor = page.cursor
    raise AssertionError('traversal did not complete')


def test_replay_index_build_respects_full_request_budget(
        tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _big_root(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    # Journal + events exceed 1 MiB in total: a cold first page cannot be
    # served inside one request budget, however small the page is.
    with pytest.raises(ContractError):
        reader.events(RUN, limit=1)


def test_replay_cold_and_warm_index_budgets(tmp_path, foundation_module,
                                            plan_body):
    root = _big_root(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    seen, errors = _traverse(reader)
    assert errors >= 1  # cold requests exceeded the budget while indexing
    assert seen == [('measured', 'default', i + 1, 'update')
                    for i in range(FRAMES)]
    # Warm cache: a fresh traversal needs no indexing and never errors.
    seen2, errors2 = _traverse(reader)
    assert errors2 == 0
    assert seen2 == seen


def test_replay_deadline_enforced_during_indexing(
        tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _big_root(tmp_path, foundation_module, plan_body)
    replay = foundation_module('replay')
    with pytest.raises(ContractError):
        replay.build_index(root, RUN, deadline=time.monotonic() - 1)


def test_replay_budget_interruption_preserves_cursor_progress(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.reader as reader_mod
    root = _big_root(tmp_path, foundation_module, plan_body)
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', 64 * 1024)
    reader = reader_mod.EvaluationReader(root)
    seen, errors = _traverse(reader, limit=5)
    assert errors >= 1
    assert seen == [('measured', 'default', i + 1, 'update')
                    for i in range(FRAMES)]


def test_replay_tiny_budget_makes_no_progress(tmp_path, foundation_module,
                                              plan_body, monkeypatch):
    import development.evaluation.reader as reader_mod
    from development.evaluation.contracts import ContractError
    root = _big_root(tmp_path, foundation_module, plan_body)
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', 8)
    reader = reader_mod.EvaluationReader(root)
    for _ in range(3):
        with pytest.raises(ContractError):
            reader.events(RUN, limit=1)


def test_replay_advance_is_resumable_and_charged(
        tmp_path, foundation_module, plan_body):
    root = _big_root(tmp_path, foundation_module, plan_body)
    replay = foundation_module('replay')
    index = replay.ReplayIndex.empty()
    charged = []
    total = 0
    while not index.complete:
        consumed = replay.advance(root, RUN, index, max_bytes=200_000,
                                  charge=lambda data: charged.append(len(data)))
        assert 0 < consumed <= 200_000
        total += consumed
    assert sum(charged) == total
    full = replay.build_index(root, RUN)
    assert index.total == full.total == FRAMES
    directory = root.path / '.seed-evaluation'
    import os
    runs = root.path / 'evaluation' / 'runs' / RUN
    expected = (os.path.getsize(runs / 'preupdate.ndjson')
                + os.path.getsize(runs / 'events.ndjson'))
    assert total == expected  # every physical byte accounted exactly once
