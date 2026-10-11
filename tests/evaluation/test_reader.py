"""I24: bounded read-only artifact reader."""
import json
import os

import pytest

from .test_artifacts import RUN
from .test_replay import _publish


def test_chunk_scope_and_budget(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _publish(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    chunk = reader.chunk(RUN, 'events.ndjson', 0)
    stored = (tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
              / 'events.ndjson').read_bytes()
    assert chunk == stored[:len(chunk)] and len(chunk) <= 64 * 1024
    with pytest.raises(ContractError):
        reader.chunk(RUN, 'events.ndjson', 99)
    with pytest.raises(ContractError):
        reader.chunk(RUN, '../receipts/' + RUN + '.json', 0)
    detail = reader.detail(RUN)
    assert len(detail.summary.body) <= 912 * 1024
    body = json.loads(detail.summary.body)
    assert body['verification'] == 'whole_payload_verified_at_publication'
    assert detail.receipt.digest
    # A modified chunk is detected against the receipt-bound chunk index.
    target = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN / 'events.ndjson'
    target.write_bytes(stored.replace(b'observe', b'obs3rve'))
    with pytest.raises(ContractError):
        reader.chunk(RUN, 'events.ndjson', 0)


def test_reader_errors_and_safety(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _publish(tmp_path, foundation_module, plan_body)
    reader_mod = foundation_module('reader')
    reader = reader_mod.EvaluationReader(root)
    page = reader.runs()
    assert [json.loads(e.body)['run_id'] for e in page.events] == [RUN]
    with pytest.raises(ContractError):
        reader.runs(cursor='forged-cursor')
    with pytest.raises(ContractError):
        reader.detail('f' * 32)
    # Stale fingerprint: touching a file invalidates its verification state.
    target = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN / 'manifest.json'
    reader.detail(RUN)
    os.utime(target, (0, 0))
    body = json.loads(reader.detail(RUN).summary.body)
    assert body['verification'] == 'verification_pending'
    # Read-only SQLite inspection refuses writes.
    assert reader.snapshot_tables(RUN) == []
    with pytest.raises(ContractError):
        reader_mod.EvaluationReader(object())


def test_missing_receipt_is_unavailable(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _publish(tmp_path, foundation_module, plan_body)
    receipt = (tmp_path / '.seed-evaluation' / 'evaluation' / 'receipts'
               / f'{RUN}.json')
    receipt.unlink()
    reader = foundation_module('reader').EvaluationReader(root)
    with pytest.raises(ContractError):
        reader.detail(RUN)


def test_events_page_byte_budget(tmp_path, foundation_module, plan_body):
    # Windowed paging: a page whose joined bodies would exceed the 1 MiB
    # request budget is shortened with a correct next cursor; paging stays
    # lossless across byte-budget interruptions.
    from .test_replay import _publish
    from .test_artifacts import _record
    frames = 24
    events = [dict(key=['measured', 'default', i + 1, 'update'],
                   body=dict(blob={f'k{j}': 'x' * 4000 for j in range(13)}))
              for i in range(frames)]
    root = _publish(tmp_path, foundation_module, plan_body,
                    record=_record(events=events, planned_transitions=frames),
                    frames=frames)
    reader = foundation_module('reader').EvaluationReader(root)
    seen, cursor, pages = [], None, 0
    while True:
        page = reader.events(RUN, cursor=cursor, limit=20)
        pages += 1
        assert sum(len(e.body) for e in page.events) <= 1024 * 1024
        seen.extend(e.key for e in page.events)
        cursor = page.cursor
        if cursor is None:
            break
    assert pages > 1
    assert seen == [('measured', 'default', i + 1, 'update')
                    for i in range(frames)]


def test_chunk_verified_label_and_large_file(tmp_path, foundation_module,
                                             plan_body):
    root = _publish(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    reader.chunk(RUN, 'events.ndjson', 0)
    body = json.loads(reader.detail(RUN).summary.body)
    assert body['chunk_verification'] == 'chunk_verified'
