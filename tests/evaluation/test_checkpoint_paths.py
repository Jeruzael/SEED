"""Remediation D: descriptor-relative checkpoint path safety.

The staged/published checkpoint path `checkpoints/<name>.sqlite3` must be
opened by walking validated directory descriptors; an intermediate
symlink must never be followed to a foreign file.
"""
import hashlib
import json
import os
import sqlite3

import pytest

from .test_artifacts import RUN, _honest, _payload_dir, _record, _stage


def _make_db(path, value):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)')
    db.execute('INSERT INTO t VALUES (1, ?)', (value,))
    db.commit()
    db.close()


def _stage_with_checkpoint(tmp_path, foundation_module, plan_body, value='owned'):
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    snap_dir = _payload_dir(tmp_path) / 'checkpoints'
    snap_dir.mkdir()
    _make_db(snap_dir / 'initial.sqlite3', value)
    record = _honest(artifacts, frozen, tmp_path,
                     _record(checkpoints=[dict(
                         name='initial', file='checkpoints/initial.sqlite3')]))
    artifacts.write_run_record(root, record)
    return root, frozen, artifacts, snap_dir


def test_valid_owned_checkpoint_still_reads(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    root, frozen, artifacts, snap_dir = _stage_with_checkpoint(
        tmp_path, foundation_module, plan_body)
    artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    manifest = json.loads((_payload_dir(tmp_path) / 'manifest.json').read_bytes())
    entry = manifest['checkpoints'][0]
    assert entry['sha256'] == hashlib.sha256(
        (snap_dir / 'initial.sqlite3').read_bytes()).hexdigest()


def test_intermediate_checkpoint_symlink_rejected(tmp_path, foundation_module,
                                                  plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, snap_dir = _stage_with_checkpoint(
        tmp_path, foundation_module, plan_body)
    outside = tmp_path / 'outside'
    outside.mkdir()
    _make_db(outside / 'initial.sqlite3', 'foreign')
    # Replace the owned checkpoints directory with a symlink outside.
    (snap_dir / 'initial.sqlite3').unlink()
    snap_dir.rmdir()
    os.symlink(outside, snap_dir)
    # The staged checkpoint read itself must refuse the foreign file:
    # descriptor-relative traversal never follows the intermediate link.
    from development.evaluation import artifact_io
    with pytest.raises(ContractError):
        artifact_io._read_staged(root, RUN, 'checkpoints/initial.sqlite3',
                                 128 * 1024 ** 2)
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    # The foreign bytes were never inventoried as this run's checkpoint.
    manifest_path = _payload_dir(tmp_path) / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_bytes())
        foreign = hashlib.sha256(
            (outside / 'initial.sqlite3').read_bytes()).hexdigest()
        assert all(e['sha256'] != foreign for e in manifest['checkpoints'])


def test_checkpoint_final_component_symlink_rejected(tmp_path, foundation_module,
                                                     plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, snap_dir = _stage_with_checkpoint(
        tmp_path, foundation_module, plan_body)
    outside_file = tmp_path / 'foreign.sqlite3'
    _make_db(outside_file, 'foreign')
    (snap_dir / 'initial.sqlite3').unlink()
    os.symlink(outside_file, snap_dir / 'initial.sqlite3')
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)


def test_checkpoint_directory_not_a_directory(tmp_path, foundation_module,
                                              plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, snap_dir = _stage_with_checkpoint(
        tmp_path, foundation_module, plan_body)
    (snap_dir / 'initial.sqlite3').unlink()
    snap_dir.rmdir()
    snap_dir.write_bytes(b'not a directory')
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)


def test_checkpoint_traversal_and_absolute_names_rejected(
        tmp_path, foundation_module, plan_body):
    from development.evaluation import artifact_io
    from development.evaluation.contracts import ContractError
    root, frozen, artifacts, snap_dir = _stage_with_checkpoint(
        tmp_path, foundation_module, plan_body)
    for bad in ('../initial.sqlite3', 'checkpoints/../../secret',
                '/etc/passwd', 'checkpoints//initial.sqlite3',
                'checkpoints/./initial.sqlite3', 'checkpoints/'):
        with pytest.raises(ContractError):
            artifact_io._read_staged(root, RUN, bad, 1024)


def test_published_checkpoint_symlink_rejected(tmp_path, foundation_module,
                                               plan_body):
    """The integrity file-set read of a published run must refuse an
    intermediate checkpoints symlink (descriptor-relative reads)."""
    from development.evaluation.contracts import ContractError
    integrity = foundation_module('integrity')
    run_dir = tmp_path / 'run'
    (run_dir / 'checkpoints').mkdir(parents=True)
    _make_db(run_dir / 'checkpoints' / 'initial.sqlite3', 'owned')
    for name in integrity.FIXED_FILES:
        (run_dir / name).write_bytes(b'{}')
    manifest = {'checkpoints': [dict(name='initial',
                                     file='checkpoints/initial.sqlite3')]}
    assert integrity.validate_file_set(run_dir, manifest)  # owned layout ok
    outside = tmp_path / 'outside2'
    outside.mkdir()
    _make_db(outside / 'initial.sqlite3', 'foreign')
    (run_dir / 'checkpoints' / 'initial.sqlite3').unlink()
    (run_dir / 'checkpoints').rmdir()
    os.symlink(outside, run_dir / 'checkpoints')
    with pytest.raises(ContractError):
        integrity.validate_file_set(run_dir, manifest)
