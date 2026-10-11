"""I23: whole-byte integrity, detached receipts, atomic publication."""
import hashlib
import json
import os

import pytest

from .test_artifacts import RUN, _payload_dir, _record, _stage

RUN2 = 'b' * 32


def _assembled(tmp_path, foundation_module, plan_body, record=None):
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     record=record)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    return root, frozen, payload, artifacts


def _publish(tmp_path, foundation_module, plan_body):
    root, frozen, payload, artifacts = _assembled(tmp_path, foundation_module, plan_body)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    receipt = integrity.make_receipt(finalized, root)
    artifact = integrity.publish(finalized, receipt, root)
    return root, payload, integrity, artifact


def test_integrity_distinct_from_science(tmp_path, foundation_module, plan_body):
    root, frozen, payload, artifacts = _assembled(tmp_path, foundation_module, plan_body)
    integrity = foundation_module('integrity')
    science = foundation_module('science')
    digest1 = integrity.integrity_digest(payload, root)
    science1 = science.science_digest(payload, root)
    # Operational prose is in the payload bytes but not in science.
    ops = _payload_dir(tmp_path) / 'operations.ndjson'
    ops.write_bytes(b'{"code":"run_completed","note":"raw prose changed"}\n')
    assert integrity.integrity_digest(payload, root) != digest1
    assert science.science_digest(payload, root) == science1
    # A changed scientific outcome changes both digests.
    events = _payload_dir(tmp_path) / 'events.ndjson'
    record = json.loads(events.read_bytes())
    record['body']['update'] = dict(kind='b1_transition', source_ids=['other'])
    events.write_bytes(json.dumps(record).encode() + b'\n')
    assert integrity.integrity_digest(payload, root) != digest1
    assert science.science_digest(payload, root) != science1


def test_inventory_attack_and_replacement(tmp_path, foundation_module, plan_body):
    root, payload, integrity, artifact = _publish(tmp_path, foundation_module, plan_body)
    run_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    assert artifact.run_id == RUN
    assert integrity.verify_receipt(root, RUN) is True
    original_digest = artifact.receipt.digest
    # Modified payload byte.
    events = run_dir / 'events.ndjson'
    raw = events.read_bytes()
    events.write_bytes(raw.replace(b'observe', b'obs3rve'))
    assert integrity.verify_receipt(root, RUN) is False
    events.write_bytes(raw)
    # Extra file.
    (run_dir / 'extra.txt').write_bytes(b'x')
    assert integrity.verify_receipt(root, RUN) is False
    (run_dir / 'extra.txt').unlink()
    # Missing file.
    truth = run_dir / 'truth.json'
    saved = truth.read_bytes(); truth.unlink()
    assert integrity.verify_receipt(root, RUN) is False
    truth.write_bytes(saved)
    # Symlink replacement.
    target = run_dir / 'metrics.json'
    saved = target.read_bytes(); target.unlink(); target.symlink_to('/etc/hostname')
    assert integrity.verify_receipt(root, RUN) is False
    target.unlink(); target.write_bytes(saved)
    assert integrity.verify_receipt(root, RUN) is True
    # Documented limitation: rewriting payload AND receipt together yields a
    # self-consistent forged pair with a different digest -- not authenticity.
    forged = json.loads((tmp_path / '.seed-evaluation' / 'evaluation' / 'receipts'
                         / f'{RUN}.json').read_bytes())
    assert forged['digest'] == original_digest


def test_atomic_publish_crash_ladder(tmp_path, foundation_module, plan_body, monkeypatch):
    root, frozen, payload, artifacts = _assembled(tmp_path, foundation_module, plan_body)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    receipt = integrity.make_receipt(finalized, root)
    partial_dir = _payload_dir(tmp_path)
    runs_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs'

    def boom(*args, **kwargs):
        raise OSError('injected crash')

    # Crash at rename: staged partial survives, nothing is exposed as a run.
    monkeypatch.setattr(integrity, '_rename', boom)
    with pytest.raises(Exception):
        integrity.publish(finalized, receipt, root)
    assert partial_dir.is_dir() and not (runs_dir / RUN).exists()
    monkeypatch.undo()
    # Crash at receipt write: run directory exists but is not indexed/exposed.
    monkeypatch.setattr(integrity, '_write_receipt', boom)
    with pytest.raises(Exception):
        integrity.publish(finalized, receipt, root)
    assert (runs_dir / RUN).is_dir()
    index_path = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs-index.json'
    assert not index_path.exists()
    assert integrity.verify_receipt(root, RUN) is False
    monkeypatch.undo()
    # No overwrite of the existing (unreceipted) directory identity.
    with pytest.raises(Exception):
        integrity.publish(finalized, receipt, root)


def test_undeclared_checkpoint_file_refused(tmp_path, foundation_module, plan_body):
    # Review M1: an undeclared file inside checkpoints/ must not be
    # receipted or published; the file set must equal the manifest inventory.
    from development.evaluation.contracts import ContractError
    root, frozen, payload, artifacts = _assembled(tmp_path, foundation_module,
                                                  plan_body)
    import sqlite3 as _sq
    sneak = _payload_dir(tmp_path) / 'checkpoints'
    sneak.mkdir(exist_ok=True)
    db = _sq.connect(sneak / 'undeclared.sqlite3')
    db.execute('CREATE TABLE t (id INTEGER)')
    db.commit(); db.close()
    integrity = foundation_module('integrity')
    with pytest.raises(ContractError):
        integrity.finalize_payload(payload, root)


def test_oversized_file_not_silently_truncated(tmp_path, foundation_module,
                                               plan_body, monkeypatch):
    # Review M3: reads beyond the cap must fail, never hash a prefix.
    from development.evaluation.contracts import ContractError
    root, frozen, payload, artifacts = _assembled(tmp_path, foundation_module,
                                                  plan_body)
    import development.evaluation.artifact_io as artifacts_mod
    monkeypatch.setattr(artifacts_mod, 'ARTIFACT_BYTES', 1024)
    integrity = foundation_module('integrity')
    with pytest.raises(ContractError):
        integrity.receipt_body(payload, root)
