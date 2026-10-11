"""I21: lossless bounded payload assembly over the parent-owned journal."""
import hashlib
import json
import sqlite3

import pytest

from .test_prediction_boundary import checkpoint

RUN = 'a' * 32


def _root(tmp_path, foundation_module):
    return foundation_module('paths').EvaluationRoot.create(tmp_path)


def _frozen(root, foundation_module, plan_body):
    from development.evaluation.contracts import AnalysisPlan
    from development.evaluation.canonical import canonical_bytes
    plan = AnalysisPlan(canonical_bytes(plan_body))
    return foundation_module('analysis').freeze_plan(plan, root)


def _evidence(ordinal, phase='measured'):
    from development.evaluation.contracts import PreUpdateEvidence
    value = checkpoint()
    value['phase'] = phase
    value['transition_ordinal'] = ordinal
    return PreUpdateEvidence(json.dumps(value).encode())


def _record(**overrides):
    record = dict(
        schema='b10_run_record_v1', run_id=RUN, status='COMPLETED', reason=None,
        experiment=dict(id='technical-fixture', version=1, source_commit='b' * 40,
                        lock_digest='c' * 64, profile_digest='d' * 64,
                        protocol='PREQUENTIAL', adapter_version=1),
        events=[dict(key=['measured', 'default', 1, 'update'],
                     body=dict(action='observe', confirmed=True,
                               update=dict(kind='b1_transition', source_ids=['s1'])))],
        attempts=[], measurements=[], findings=[], truth=dict(fixture=True),
        operations=[dict(code='run_completed', note='ok')],
        checkpoints=[], planned_transitions=1,
        failure=None)
    record.update(overrides)
    return record


def _stage(tmp_path, foundation_module, plan_body, record=None, journal_frames=1):
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    for ordinal in range(1, journal_frames + 1):
        journal.append(journal.frame(_evidence(ordinal)))
    journal.close()
    artifacts = foundation_module('artifacts')
    artifacts.write_run_record(root, record or _record())
    return root, frozen, artifacts


def _payload_dir(tmp_path):
    return tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN


def test_journal_reused_and_detail_reconciled(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    journal_before = (_payload_dir(tmp_path) / 'preupdate.ndjson').read_bytes()
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    assert payload.identity == RUN and payload.byte_length > 0
    # Journal is reused in place, never copied or rewritten.
    assert (_payload_dir(tmp_path) / 'preupdate.ndjson').read_bytes() == journal_before
    names = sorted(p.name for p in _payload_dir(tmp_path).iterdir() if p.is_file())
    assert names == ['analysis-plan.json', 'chunks.json', 'events.ndjson', 'index.json',
                     'manifest.json', 'metrics.json', 'operations.ndjson',
                     'preupdate.ndjson', 'truth.json']
    event = json.loads((_payload_dir(tmp_path) / 'events.ndjson').read_bytes())
    line = journal_before.splitlines()[0]
    assert event['journal_sha256'] == hashlib.sha256(line + b'\n').hexdigest()
    assert event['evidence_sha256'] == json.loads(line)['header']['evidence_sha256']
    # Post-ACK event must not duplicate the raw prediction/outcome payloads.
    assert 'prediction' not in json.dumps(event['body'])
    assert 'state_after' not in json.dumps(event['body'])
    manifest = json.loads((_payload_dir(tmp_path) / 'manifest.json').read_bytes())
    assert manifest['schema'] == 'b10_artifact_v1'
    assert manifest['status'] == 'COMPLETED'
    assert manifest['counts'] == dict(planned_transitions=1, observed_transitions=1,
                                      joined_events=1, skipped_attempts=0)
    assert manifest['publication'] == 'pending'
    index = json.loads((_payload_dir(tmp_path) / 'index.json').read_bytes())
    assert index['events'][0]['key'] == ['measured', 'default', 1, 'update']
    assert index['events'][0]['offset'] == 0


def test_bound_every_file_and_snapshot(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    # One event whose body pushes the combined journal+event detail over 64 KiB.
    big = _record(events=[dict(key=['measured', 'default', 1, 'update'],
                               body=dict(blob={f'k{i}': 'x' * 4000 for i in range(20)}))])
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body, record=big)
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    # Oversized metrics content is rejected, not truncated.
    fat = _record(measurements=[dict(identity='member-0:prediction.numeric-mae:all:whole',
                                     metric='prediction.numeric-mae',
                                     version=1, member='member-0', state='MEASURED',
                                     value={f'k{i}': 'y' * 4000 for i in range(80)},
                                     reason=None)])
    (tmp_path / 'b').mkdir()
    root2, frozen2, artifacts2 = _stage(tmp_path / 'b', foundation_module, plan_body, record=fat)
    with pytest.raises(ContractError):
        artifacts2.assemble_payload(RunResult('COMPLETED', None), frozen2, root2)


def test_post_ack_detail_failure_preserves_state(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    big = _record(events=[dict(key=['measured', 'default', 1, 'update'],
                               body=dict(blob={f'k{i}': 'x' * 4000 for i in range(20)}))])
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body, record=big)
    journal_before = (_payload_dir(tmp_path) / 'preupdate.ndjson').read_bytes()
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    # Actual learning evidence (the durable journal) is untouched; no retry.
    assert (_payload_dir(tmp_path) / 'preupdate.ndjson').read_bytes() == journal_before
    manifest = json.loads((_payload_dir(tmp_path) / 'manifest.json').read_bytes())
    assert manifest['status'] == 'INCOMPLETE'
    assert manifest['publication'] == 'pending'


def test_partial_inventory_preserved(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    record = _record(status='INCOMPLETE', reason='STORAGE_INTERRUPTED',
                     failure=dict(phase='measured', ordinal=2, completed=1, attempted=2,
                                  confirmed_updates=1, unconfirmed_updates=0,
                                  missing=[dict(identity='member-0:prediction.numeric-mae:whole',
                                                reason='run_incomplete')]))
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body, record=record)
    payload = artifacts.assemble_payload(RunResult('INCOMPLETE', 'STORAGE_INTERRUPTED'),
                                         frozen, root)
    assert payload.identity == RUN
    manifest = json.loads((_payload_dir(tmp_path) / 'manifest.json').read_bytes())
    assert manifest['status'] == 'INCOMPLETE'
    assert manifest['failure']['confirmed_updates'] == 1
    assert manifest['failure']['missing'][0]['reason'] == 'run_incomplete'
    metrics = json.loads((_payload_dir(tmp_path) / 'metrics.json').read_bytes())
    assert metrics['registered']  # full registered inventory retained for partials
    assert all(m['state'] == 'UNAVAILABLE' for m in metrics['produced'])


def test_checkpoint_snapshots_bounded_and_inventoried(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body)
    snap_dir = _payload_dir(tmp_path) / 'checkpoints'
    snap_dir.mkdir()
    db = sqlite3.connect(snap_dir / 'initial.sqlite3')
    db.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)')
    db.execute("INSERT INTO t VALUES (1, 'x')")
    db.commit(); db.close()
    record = _record(checkpoints=[dict(name='initial', file='checkpoints/initial.sqlite3')])
    artifacts.write_run_record(root, record)
    artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    manifest = json.loads((_payload_dir(tmp_path) / 'manifest.json').read_bytes())
    entry = manifest['checkpoints'][0]
    assert entry['file'] == 'checkpoints/initial.sqlite3'
    assert entry['sha256'] == hashlib.sha256(
        (snap_dir / 'initial.sqlite3').read_bytes()).hexdigest()
    assert not (snap_dir / 'initial.sqlite3-wal').exists()
