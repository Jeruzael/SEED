"""Remediation C: capacity admission before the first artifact allocation.

write_run_record, journal creation, payload-file writes, the detached
receipt and the runs index must all pass the existing Budget check
BEFORE any directory or file appears; a rename must not be charged as a
second payload copy; crash-retained partials count against the root.
"""
import json

import pytest

from .test_artifacts import RUN, _record, _stage

RUN_B = 'b' * 32


def _usage(root):
    return root.usage()


def _partials(tmp_path):
    return tmp_path / '.seed-evaluation' / 'evaluation' / 'partials'


def test_staging_admission_before_directory_creation(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation.contracts import ContractError
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     journal_frames=0)
    # Remove the staged run entirely: this is about a NEW run identity.
    import shutil
    shutil.rmtree(_partials(tmp_path) / RUN)
    monkeypatch.setitem(specs.CAPS, 'root_bytes', _usage(root).bytes)
    with pytest.raises(ContractError):
        artifacts.write_run_record(root, _record(run_id=RUN_B))
    assert not (_partials(tmp_path) / RUN_B).exists()
    assert not (_partials(tmp_path) / f'{RUN_B}.record.json').exists()
    assert not (_partials(tmp_path) / f'{RUN_B}.record.tmp').exists()


def test_retained_run_61_rejected_before_write(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation.contracts import ContractError
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    monkeypatch.setitem(specs.CAPS, 'retained_runs', _usage(root).runs)
    with pytest.raises(ContractError):
        artifacts.write_run_record(root, _record(run_id=RUN_B))
    assert not (_partials(tmp_path) / RUN_B).exists()
    # Journal creation for a new identity is likewise refused up front.
    checkpoint = foundation_module('checkpoint')
    with pytest.raises(ContractError):
        checkpoint.ScoreJournal.create(root, RUN_B)
    assert not (_partials(tmp_path) / RUN_B).exists()


def test_restaging_record_respects_remaining_capacity(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation.contracts import ContractError
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    record_file = _partials(tmp_path) / f'{RUN}.record.json'
    before = record_file.read_bytes()
    monkeypatch.setitem(specs.CAPS, 'root_bytes', _usage(root).bytes + 16)
    big = _record(operations=[dict(code='run_completed', note='x' * 4096)])
    with pytest.raises(ContractError):
        artifacts.write_run_record(root, big)
    assert record_file.read_bytes() == before  # original record untouched


def test_crash_retained_partial_counts_against_root(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation.contracts import ContractError
    # Run A staged then "crashed": its partial journal stays on disk.
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     journal_frames=3)
    monkeypatch.setitem(specs.CAPS, 'root_bytes', _usage(root).bytes + 32)
    with pytest.raises(ContractError):
        artifacts.write_run_record(root, _record(run_id=RUN_B))
    assert not (_partials(tmp_path) / RUN_B).exists()


def test_payload_file_write_admission(tmp_path, foundation_module, plan_body,
                                      monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation import artifact_io
    from development.evaluation.contracts import ContractError
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    monkeypatch.setitem(specs.CAPS, 'root_bytes', _usage(root).bytes + 8)
    with pytest.raises(ContractError):
        artifact_io._write_payload_file(root, RUN, 'metrics.json',
                                        b'x' * 1024)
    assert not (_partials(tmp_path) / RUN / 'metrics.json').exists()


def test_publication_rename_does_not_double_reserve(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import development.evaluation.specs as specs
    from development.evaluation.contracts import RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None),
                                         frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    # Room for the receipt + index only: if publish charged the payload
    # a second time for the rename, this would be refused.
    monkeypatch.setitem(specs.CAPS, 'root_bytes',
                        _usage(root).bytes + 256 * 1024)
    receipt = integrity.make_receipt(finalized, root)
    integrity.publish(finalized, receipt, root)
    runs_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    assert (runs_dir / 'manifest.json').exists()
    assert (tmp_path / '.seed-evaluation' / 'evaluation' / 'receipts'
            / f'{RUN}.json').exists()
