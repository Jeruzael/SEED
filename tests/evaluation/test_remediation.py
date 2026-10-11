"""Remediation RED/GREEN: independent-review findings F1-F5 for I21-I25.

F1 re-execution must genuinely re-execute in a disposable worker, not copy
evidence. F2 assembly must reconcile measurements/findings against the
original scientific derivation. F3 replay paging must be windowed/bounded.
F4 the event inventory must be lossless (all stages, attempts, duplicates).
F5 assembly/publication must use the existing root budget admission.
"""
import hashlib
import json

import pytest

from .test_prediction_boundary import checkpoint

RUN = 'a' * 32
_fm = None


def _set_fm(foundation_module):
    global _fm
    _fm = foundation_module
    return foundation_module
EXECUTION = dict(settings={'epsilon': 0}, rng_seed=3, uuid='a' * 64,
                 training=0, measured=1, maintenance=False)


def _root(tmp_path, foundation_module):
    _set_fm(foundation_module)
    return foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())


def _frozen(root, foundation_module, plan_body):
    from development.evaluation.contracts import AnalysisPlan
    from development.evaluation.canonical import canonical_bytes
    plan = AnalysisPlan(canonical_bytes(plan_body))
    return foundation_module('analysis').freeze_plan(plan, root)


def _evidence_rows(journal_raw):
    from development.evaluation.contracts import CompletedEvidence
    rows = []
    for line in journal_raw.splitlines():
        if line.strip():
            record = json.loads(line)
            h = record['header']
            rows.append(CompletedEvidence(
                (h['phase'], h['subcase'], h['transition_ordinal'], 'checkpoint'),
                json.dumps(record['evidence']).encode()))
    return tuple(rows)


def _derive(frozen, journal_raw, status='COMPLETED'):
    """Producer-side scientific derivation, independent of artifacts.py."""
    from development.evaluation.analysis import expand_inventory
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from development.evaluation.metrics.registry import measurement_data
    from development.evaluation.metrics.findings import classify_questions
    evidence = _evidence_rows(journal_raw)
    rows = []
    for registered in expand_inventory(frozen.plan):
        member, metric, population, window = registered.identity.split(':')
        window = window.removesuffix('~exploratory')
        pop = Population(population, (member,), window, registered.role)
        if metric.startswith('prediction.'):
            m = measure_prediction(metric, evidence, pop, frozen)
        else:
            raise AssertionError('fixture plan has only prediction metrics')
        data = measurement_data(m)
        rows.append(dict(identity=m.identity, metric=m.metric,
                         version=m.version, member=m.member, state=m.state,
                         value=data.get('value'), reason=data.get('reason')))
    findings = [dict(question=f.question, status=f.status, reason=f.reason,
                     execution=f.execution)
                for f in classify_questions(frozen, tuple(
                    _to_measurement(r) for r in rows), status)]
    return rows, findings


def _to_measurement(row):
    from development.evaluation.contracts import Measurement
    from development.evaluation.specs import raw_bytes
    body = raw_bytes(dict(value=row['value'], reason=row['reason'],
                          plan_digest='x', dimensions={}, non_inferential=False))
    return Measurement(row['identity'], row['metric'], row['version'],
                       row['member'], row['state'], body)


def _profile(foundation_module):
    profile_mod = foundation_module('profile')
    return profile_mod.Profile(
        source_commit='b' * 40, clean=True, lock_digest='c' * 64,
        schema_version=7, core_version='0.2', python_implementation='CPython',
        python_version='3.11', sqlite_version='3.40', sqlite_compile=(),
        os_name='Linux', architecture='x86_64')


def _record(journal_raw, **overrides):
    frozen = overrides.pop('frozen')
    rows, findings = _derive(frozen, journal_raw,
                             overrides.get('status', 'COMPLETED'))
    profile = _profile(_fm)
    record = dict(
        schema='b10_run_record_v1', run_id=RUN, status='COMPLETED', reason=None,
        experiment=dict(id='technical-fixture', version=1,
                        source_commit=profile.source_commit,
                        lock_digest=profile.lock_digest,
                        profile_digest=profile.digest,
                        protocol='PREQUENTIAL', adapter_version=1),
        events=[dict(key=['measured', 'default', 1, 'update'],
                     body=dict(acked=True, execution='completed',
                               updates={'b1': {'status': 'confirmed'}}))],
        attempts=[], measurements=rows, findings=findings,
        truth=dict(fixture=True),
        operations=[dict(code='run_completed', note='ok')],
        checkpoints=[], planned_transitions=1, failure=None,
        execution=EXECUTION)
    record.update(overrides)
    return record


def _stage(tmp_path, foundation_module, plan_body, record=None, frames=1):
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    from development.evaluation.contracts import PreUpdateEvidence
    for ordinal in range(1, frames + 1):
        value = checkpoint()
        value['transition_ordinal'] = ordinal
        journal.append(journal.frame(PreUpdateEvidence(json.dumps(value).encode())))
    journal.close()
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    artifacts = foundation_module('artifacts')
    artifacts.write_run_record(root, record or _record(journal_raw, frozen=frozen))
    return root, frozen, artifacts, journal_raw


def _publish(tmp_path, foundation_module, plan_body, **kw):
    from development.evaluation.contracts import RunResult
    root, frozen, artifacts, journal_raw = _stage(
        tmp_path, foundation_module, plan_body, **kw)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    return root, frozen


# ---------------------------------------------------------------- F2
def test_f2_fabricated_measurement_rejected(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, journal_raw = _stage(tmp_path, foundation_module, plan_body)
    rows, findings = _derive(frozen, journal_raw)
    rows[0] = dict(rows[0], value=999.0)
    artifacts.write_run_record(root, _record(journal_raw, frozen=frozen,
                                             measurements=rows))
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)


def test_f2_missing_measurements_rejected_for_completed(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, journal_raw = _stage(tmp_path, foundation_module, plan_body)
    artifacts.write_run_record(root, _record(journal_raw, frozen=frozen,
                                             measurements=[], findings=[]))
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)


def test_f2_fabricated_finding_rejected(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError, RunResult
    root, frozen, artifacts, journal_raw = _stage(tmp_path, foundation_module, plan_body)
    rows, findings = _derive(frozen, journal_raw)
    findings[0] = dict(findings[0], status='POSITIVE')
    artifacts.write_run_record(root, _record(journal_raw, frozen=frozen,
                                             findings=findings))
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)


def test_f2_partial_run_keeps_unavailable_rows(tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    record_kw = dict(status='INCOMPLETE', reason='STORAGE_INTERRUPTED',
                     measurements=[], findings=[],
                     failure=dict(phase='measured', ordinal=2, completed=1,
                                  attempted=2, confirmed_updates=1,
                                  unconfirmed_updates=0, missing=[]))
    root, frozen, artifacts, journal_raw = _stage(
        tmp_path, foundation_module, plan_body)
    artifacts.write_run_record(root, _record(journal_raw, frozen=frozen, **record_kw))
    payload = artifacts.assemble_payload(
        RunResult('INCOMPLETE', 'STORAGE_INTERRUPTED'), frozen, root)
    metrics = json.loads((tmp_path / '.seed-evaluation' / 'evaluation'
                          / 'partials' / RUN / 'metrics.json').read_bytes())
    assert metrics['produced'] and all(
        m['state'] == 'UNAVAILABLE' for m in metrics['produced'])


# ---------------------------------------------------------------- F5
def test_f5_budget_admission_blocks_assembly(tmp_path, foundation_module,
                                             plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError, RunResult
    import development.evaluation.specs as specs
    root, frozen, artifacts, journal_raw = _stage(tmp_path, foundation_module, plan_body)
    usage = root.usage()
    monkeypatch.setitem(specs.CAPS, 'root_bytes', usage.bytes + 8)
    with pytest.raises(ContractError):
        artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    assert not (partial / 'metrics.json').exists()


# ---------------------------------------------------------------- F3/F4
def _publish_varied2(tmp_path, foundation_module, plan_body):
    root, frozen, artifacts, journal_raw = _stage(tmp_path, foundation_module, plan_body)
    rows, findings = _derive(frozen, journal_raw)
    record = _record(journal_raw, frozen=frozen, measurements=rows, findings=findings,
                     events=[
                         dict(key=['measured', 'default', 1, 'pre'], body=dict(n='pre')),
                         dict(key=['measured', 'default', 1, 'update'],
                              body=dict(acked=True, execution='completed',
                                        updates={'b1': {'status': 'confirmed'}})),
                         dict(key=['measured', 'default', 1, 'checkpoint'], body=dict(n='cp')),
                         dict(key=['training', 'default', 1, 'outcome'], body=dict(n='reuse'))],
                     attempts=[dict(key=['training', 'default', 1, 'pre'],
                                    status='skipped', reason='stale_decision')])
    artifacts.write_run_record(root, record)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    return root


def test_f4_all_stages_and_attempts_paged(tmp_path, foundation_module, plan_body):
    root = _publish_varied2(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    seen, cursor = [], None
    while True:
        page = reader.events(RUN, cursor=cursor, limit=2)
        seen.extend(e.key for e in page.events)
        cursor = page.cursor
        if cursor is None:
            break
    assert ('measured', 'default', 1, 'update') in seen
    assert ('measured', 'default', 1, 'pre') in seen
    assert ('measured', 'default', 1, 'checkpoint') in seen
    assert ('training', 'default', 1, 'outcome') in seen
    assert ('training', 'default', 1, 'pre') in seen  # skipped attempt row
    assert len(seen) == len(set(seen)) == 5


def test_f4_duplicate_digest_rows_not_dropped(tmp_path, foundation_module, plan_body):
    import shutil
    root = _publish_varied2(tmp_path, foundation_module, plan_body)
    run_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    events = (run_dir / 'events.ndjson').read_bytes().splitlines()
    update_line = next(l for l in events if b'"update"' in l)
    with open(run_dir / 'events.ndjson', 'ab') as f:
        f.write(update_line + b'\n')
    reader = foundation_module('reader').EvaluationReader(root)
    seen, cursor = [], None
    while True:
        page = reader.events(RUN, cursor=cursor, limit=2)
        seen.extend(page.events)
        cursor = page.cursor
        if cursor is None:
            break
    # 5 stored event rows + 1 transition row set: the duplicate update line
    # is a stored row and must be delivered, not silently dropped.
    assert len(seen) == 6


def test_f3_events_do_not_use_whole_history_join(tmp_path, foundation_module,
                                                 plan_body, monkeypatch):
    root = _publish_varied2(tmp_path, foundation_module, plan_body)
    replay = foundation_module('replay')
    def boom(*a, **k):
        raise AssertionError('whole-history join used for a page request')
    monkeypatch.setattr(replay, 'join_events', boom)
    reader = foundation_module('reader').EvaluationReader(root)
    page = reader.events(RUN, limit=2)
    assert len(page.events) == 2


def test_f3_byte_budget_interruptions_lossless(tmp_path, foundation_module,
                                               plan_body, monkeypatch):
    root = _publish_varied2(tmp_path, foundation_module, plan_body)
    reader_mod = foundation_module('reader')
    receipt_size = (tmp_path / '.seed-evaluation' / 'evaluation' / 'receipts'
                    / f'{RUN}.json').stat().st_size
    budget = receipt_size + 1200
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', budget)
    reader = reader_mod.EvaluationReader(root)
    seen, cursor, pages = [], None, 0
    while True:
        page = reader.events(RUN, cursor=cursor, limit=20)
        pages += 1
        assert sum(len(e.body) for e in page.events) <= 1200 + max(
            (len(e.body) for e in page.events), default=0)
        seen.extend(e.key for e in page.events)
        cursor = page.cursor
        if cursor is None:
            break
    assert pages > 1
    assert len(seen) == len(set(seen)) == 5


# ---------------------------------------------------------------- F1
def _produce_genuine(tmp_path, foundation_module, plan_body, *,
                     tamper_prediction=False):
    """Produce a genuine run with the PrequentialDriver + real worker."""
    from development.evaluation.contracts import (
        PreUpdateEvidence, RunRequest, RunResult, WorkerLaunch)
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    base = checkpoint()
    frames = {(base['phase'], base['transition_ordinal']): base}

    class Scenario:
        def initial_observation(self, key):
            return dict(frames[(key[0], key[2])]['state_before'])

        def apply_action(self, action, key):
            return dict(frames[(key[0], key[2])]['state_after'])

    cap = root.assign_learner(RUN, 0)
    launch = WorkerLaunch(cap, json.dumps(EXECUTION['settings']).encode(),
                          EXECUTION['rng_seed'], EXECUTION['uuid'])
    router = foundation_module('channel').ChannelRouter(Scenario(), journal=journal)
    worker = foundation_module('worker').WorkerHandle.start(launch, channel=router)
    driver = foundation_module('prequential').PrequentialDriver(
        training=0, measured=1)
    result = driver.run(RunRequest(RUN), worker)
    journal.close()
    assert result.status == 'COMPLETED', result
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    events = []
    for ev in driver.events:
        body = json.loads(ev.body)
        events.append(dict(key=list(ev.key), body=dict(
            acked=body['acked'], execution=body['execution'],
            decision_id=body.get('decision_id'),
            updates={k: {'status': v['status']} for k, v in body['updates'].items()})))
    attempts = []
    for raw in driver.skipped:
        item = json.loads(raw)
        attempts.append(dict(key=item['key'], status='skipped',
                             reason=item['reason']))
    rows, findings = _derive(frozen, journal_raw)
    record = _record(journal_raw, frozen=frozen, measurements=rows,
                     findings=findings, events=events, attempts=attempts)
    artifacts = foundation_module('artifacts')
    artifacts.write_run_record(root, record)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    return root, frozen


def test_f1_genuine_run_reexecutes_to_match(tmp_path, foundation_module, plan_body):
    root, frozen = _produce_genuine(tmp_path, foundation_module, plan_body)
    reader = foundation_module('reader').EvaluationReader(root)
    reexecution = foundation_module('reexecution')
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()


def test_f1_tampered_stored_prediction_diverges(tmp_path, foundation_module, plan_body):
    # The stored journal's prediction is altered before assembly (headers
    # recomputed so the journal is internally consistent, and measurements
    # derived from the tampered evidence). Copy-based re-execution would
    # match; genuine execution must diverge.
    from development.evaluation.contracts import (
        PreUpdateEvidence, RunResult)
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, RUN)
    value = checkpoint()
    value['prediction']['signals']['battery_pct']['value'] = 55
    journal.append(journal.frame(PreUpdateEvidence(json.dumps(value).encode())))
    journal.close()
    partial = tmp_path / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    rows, findings = _derive(frozen, journal_raw)
    artifacts = foundation_module('artifacts')
    artifacts.write_run_record(root, _record(journal_raw, frozen=frozen,
                                             measurements=rows, findings=findings))
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    reader = foundation_module('reader').EvaluationReader(root)
    reexecution = foundation_module('reexecution')
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'divergent', reexecution.last_report()
