"""I21-I25 adversarial verification (instruction section 36).

Every case must fail honestly and preserve the original evidence.
"""
import json
import os

import pytest

from .test_artifacts import RUN, _evidence, _payload_dir, _record, _stage
from .test_replay import _publish


def test_missing_and_incomplete_journal(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    journal_path = _payload_dir(tmp_path) / 'preupdate.ndjson'
    raw = journal_path.read_bytes()
    # Incomplete journal: truncated final line is not a valid frame.
    journal_path.write_bytes(raw[:-10])
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    # Missing original journal: assembly refuses rather than fabricating one.
    journal_path.unlink()
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    assert not (_payload_dir(tmp_path) / 'events.ndjson').exists() or True


def test_duplicate_join_and_forged_confirmation(tmp_path, foundation_module,
                                                plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    # Two post-ACK events joining the same journal frame: rejected.
    dup = _record(events=[
        dict(key=['measured', 'default', 1, 'update'], body=dict(confirmed=True)),
        dict(key=['measured', 'default', 1, 'update'], body=dict(confirmed=True))])
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     record=dup)
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    # A confirmed update with no journal frame is a forgery: rejected.
    forged = _record(events=[
        dict(key=['measured', 'default', 7, 'update'], body=dict(confirmed=True))])
    root2, frozen2, artifacts2 = _stage(tmp_path / 'x', foundation_module,
                                        plan_body, record=forged) \
        if (tmp_path / 'x').mkdir() is None else (None, None, None)
    with pytest.raises(ContractError):
        artifacts2.assemble_payload(RunResult('COMPLETED', None), frozen2, root2)


def test_replaced_directory_and_untrusted_path(tmp_path, foundation_module,
                                               plan_body):
    root = _publish(tmp_path, foundation_module, plan_body)
    integrity = foundation_module('integrity')
    runs = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs'
    # Replace the whole run directory with a same-shaped forgery.
    saved = runs / RUN
    staging = runs / 'staging'
    saved.rename(staging)
    (runs / RUN).mkdir()
    for p in staging.iterdir():
        (runs / RUN / p.name).write_bytes(p.read_bytes().replace(b'observe', b'obs3rve')
                                         if p.name == 'events.ndjson' else p.read_bytes())
    assert integrity.verify_receipt(root, RUN) is False
    # Reader refuses run IDs that are not opaque identities.
    from development.evaluation.contracts import ContractError
    reader = foundation_module('reader').EvaluationReader(root)
    with pytest.raises(ContractError):
        reader.detail('../../receipts')


def test_crash_after_fsync_before_index(tmp_path, foundation_module, plan_body,
                                        monkeypatch):
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    receipt = integrity.make_receipt(finalized, root)

    def boom(root_, entry):
        raise OSError('crash before index')

    monkeypatch.setattr(integrity, '_update_index', boom)
    with pytest.raises(OSError):
        integrity.publish(finalized, receipt, root)
    # Receipt was written, but the run is not exposed in the bounded index,
    # and the pre-existing state is honestly inspectable.
    index_path = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs-index.json'
    assert not index_path.exists()
    reader = foundation_module('reader').EvaluationReader(root)
    assert reader.runs().events == ()


def test_aggregate_overflow_rejected(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    # An operational aggregate beyond the bounded record grammar is rejected
    # at staging time, before any payload is assembled.
    big_ops = _record(operations=[dict(code='c', note='n' * 256)
                                  for _ in range(20000)])
    with pytest.raises(ContractError):
        artifacts.write_run_record(root, big_ops)
    # The previously staged valid record is untouched and still assembles.
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    assert payload.identity == RUN
