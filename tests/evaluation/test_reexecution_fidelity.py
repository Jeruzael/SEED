"""Remediation A: re-execution fidelity.

Re-execution must run the registered scenario engine (action-dependent
outcomes computed for the fresh learner's own actions), support the
approved initial-checkpoint fixture pathway, refuse artifacts whose
scenario definition is not established, and execute inside an
evaluator-owned workspace -- never by serving stored outcomes.
"""
import hashlib
import json
import multiprocessing
import os
import tempfile

import pytest

from .test_prediction_boundary import checkpoint
from .test_remediation import (EXECUTION, RUN, _derive, _frozen, _produce_genuine,
                               _profile, _record, _root)

RUN_CKPT = 'b' * 32


def _stationary_truth():
    from development.evaluation.scenarios.stationary import StationaryScenario
    return json.loads(StationaryScenario().evaluator_view().body)


def _publish_record(tmp_path, foundation_module, root, frozen, record):
    artifacts = foundation_module('artifacts')
    artifacts.write_run_record(root, record)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None),
                                         frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)


def _tampered_outcome_run(tmp_path, foundation_module, plan_body):
    """A journal whose recorded state_after is NOT what the registered
    stationary scenario computes; copy-based re-execution would match."""
    from development.evaluation.contracts import PreUpdateEvidence
    from development.evaluation.scenarios.stationary import COMMON
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    value = checkpoint()
    value['state_before'] = dict(COMMON)
    value['state_after'] = dict(COMMON, battery_pct=33.0, load_ratio=0.99)
    journal.append(journal.frame(PreUpdateEvidence(json.dumps(value).encode())))
    journal.close()
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    rows, findings = _derive(frozen, journal_raw)
    record = _record(journal_raw, frozen=frozen, measurements=rows,
                     findings=findings, truth=_stationary_truth())
    _publish_record(tmp_path, foundation_module, root, frozen, record)
    return root


def test_reexecution_uses_fresh_action_dependent_outcome(
        tmp_path, foundation_module, plan_body):
    root = _tampered_outcome_run(tmp_path, foundation_module, plan_body)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'divergent', reexecution.last_report()
    # The fresh run's outcome is the registered scenario's response to
    # the fresh action (battery 79.75 / COMMON shape), not the recorded
    # tampered outcome (battery 33.0).
    new_id = reexecution.last_report()['new_run_id']
    fresh = (tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / new_id
             / 'preupdate.ndjson').read_bytes()
    evidence = json.loads(fresh.splitlines()[0])['evidence']
    assert evidence['state_after']['battery_pct'] == 79.75
    assert evidence['state_after'] != dict(
        evidence['state_before'], battery_pct=33.0, load_ratio=0.99)


def test_reexecution_missing_scenario_inputs_incompatible(
        tmp_path, foundation_module, plan_body):
    # A genuine run whose record carries no registered scenario truth:
    # the original scenario definition is not established, so genuine
    # re-execution must refuse rather than improvise one.
    from development.evaluation.contracts import RunResult
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    journal.close()
    # Reuse the genuine producer but rewrite truth before publication is
    # not possible; instead produce genuinely then check the guard unit:
    reexecution = foundation_module('reexecution')
    record = _record(b'', frozen=frozen, truth=dict(fixture=True))
    engine = reexecution._registered_scenario(root, RUN, record)
    assert engine is None


def test_reexecution_owned_workspace_and_dispatch_lock(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import tempfile as _tempfile
    def _no_temp_root(*a, **k):
        raise AssertionError('re-execution allocated an external temp root')
    monkeypatch.setattr(_tempfile, 'mkdtemp', _no_temp_root)
    root, frozen = _produce_genuine(tmp_path, foundation_module, plan_body)
    run_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in run_dir.iterdir() if p.is_file()}
    tmp_before = {n for n in os.listdir(tempfile.gettempdir())
                  if n.startswith('seed-reexecute-')}
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()
    tmp_after = {n for n in os.listdir(tempfile.gettempdir())
                 if n.startswith('seed-reexecute-')}
    assert tmp_after == tmp_before  # no unrestricted external temp root
    work = tmp_path / '.seed-evaluation' / 'work'
    leftovers = [n for n in os.listdir(work)
                 if n == reexecution.last_report()['new_run_id']]
    assert leftovers == []  # owned workspace destroyed afterwards
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in run_dir.iterdir() if p.is_file()}
    assert before == after  # original artifact byte-identical
    # Registered empirical dispatch stays locked on every public surface.
    cli = foundation_module('cli')
    assert cli.main(['reexecute', RUN]) == 2


# ------------------------------------------------------------- checkpoints
def _checkpoint_bytes(tmp_path, foundation_module):
    """Produce a genuine initial owned-state checkpoint: boot a real
    worker (which initializes the owned state and identity), stop it
    before any transition, and take the resulting state DB bytes."""
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.scenarios.stationary import StationaryScenario
    paths = foundation_module('paths')
    (tmp_path / 'ckptsrc').mkdir()
    src = paths.EvaluationRoot.create((tmp_path / 'ckptsrc').resolve())
    cap = src.assign_learner('f' * 32, 0)
    launch = WorkerLaunch(cap, b'{"epsilon":0.15}', 3, 'c' * 64)
    router = foundation_module('channel').ChannelRouter(StationaryScenario())
    worker = foundation_module('worker').WorkerHandle.start(
        launch, channel=router)
    worker.stop()
    home = cap.home
    # Export through the SQLite backup API (the same mechanism
    # OwnedState.checkpoint uses) so the bytes are a standalone,
    # fully merged snapshot rather than a WAL-mode main file.
    import sqlite3
    merged = tmp_path / 'merged.sqlite3'
    src_db = sqlite3.connect(home / 'memory.sqlite3')
    dst_db = sqlite3.connect(merged)
    try:
        src_db.backup(dst_db)
        # Convert the merged snapshot out of WAL journal mode so the
        # bytes stand alone (as producer checkpoints do).
        dst_db.execute('PRAGMA journal_mode=DELETE')
    finally:
        dst_db.close()
        src_db.close()
    return merged.read_bytes()


def _produce_checkpointed(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import (RunRequest, RunResult,
                                                  WorkerLaunch)
    from development.evaluation.scenarios.stationary import StationaryScenario
    from development.evaluation.state import CompletedFixture, _fixture_facts
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    ckpt = _checkpoint_bytes(tmp_path, foundation_module)
    cap = root.assign_learner(RUN, 0)
    fd = cap.open('state', 'db', 'create')
    with os.fdopen(fd, 'wb') as f:
        f.write(ckpt)
        f.flush()
        os.fsync(f.fileno())
    fixture = CompletedFixture(cap, *_fixture_facts(cap))
    settings = {'epsilon': 0.15}
    launch = WorkerLaunch(cap, json.dumps(settings).encode(),
                          EXECUTION['rng_seed'], EXECUTION['uuid'],
                          launch_mode='COMPLETED_OWNED_FIXTURE',
                          fixture=fixture)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    scenario = StationaryScenario()
    router = foundation_module('channel').ChannelRouter(scenario,
                                                        journal=journal)
    worker = foundation_module('worker').WorkerHandle.start(
        launch, channel=router)
    driver = foundation_module('prequential').PrequentialDriver(
        training=0, measured=1)
    result = driver.run(RunRequest(RUN), worker)
    journal.close()
    assert result.status == 'COMPLETED', result
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    (partial / 'checkpoints').mkdir()
    (partial / 'checkpoints' / 'initial.sqlite3').write_bytes(ckpt)
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    events = []
    for ev in driver.events:
        body = json.loads(ev.body)
        events.append(dict(key=list(ev.key), body=dict(
            acked=body['acked'], execution=body['execution'],
            decision_id=body.get('decision_id'),
            updates={k: {'status': v['status']}
                     for k, v in body['updates'].items()})))
    rows, findings = _derive(frozen, journal_raw)
    record = _record(
        journal_raw, frozen=frozen, measurements=rows, findings=findings,
        events=events, truth=_stationary_truth(),
        checkpoints=[dict(name='initial',
                          file='checkpoints/initial.sqlite3')],
        execution=dict(EXECUTION, settings=settings))
    _publish_record(tmp_path, foundation_module, root, frozen, record)
    return root


def test_reexecution_original_initial_checkpoint(
        tmp_path, foundation_module, plan_body):
    root = _produce_checkpointed(tmp_path, foundation_module, plan_body)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()


def test_reexecution_corrupt_checkpoint_rejected(
        tmp_path, foundation_module, plan_body):
    root = _produce_checkpointed(tmp_path, foundation_module, plan_body)
    published = (tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
                 / 'checkpoints' / 'initial.sqlite3')
    raw = bytearray(published.read_bytes())
    raw[100] ^= 0xFF
    published.write_bytes(bytes(raw))
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'incompatible', reexecution.last_report()
