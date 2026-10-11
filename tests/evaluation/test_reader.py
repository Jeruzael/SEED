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
