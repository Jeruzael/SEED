"""I25: trusted re-execution compatibility and bounded divergence."""
import hashlib
import json

import pytest

from .test_artifacts import RUN, _record, _stage

RUN2 = 'b' * 32


def _profile(foundation_module, **overrides):
    profile_mod = foundation_module('profile')
    base = dict(source_commit='b' * 40, clean=True, lock_digest='c' * 64,
                schema_version=7, core_version='0.2', python_implementation='CPython',
                python_version='3.11', sqlite_version='3.40', sqlite_compile=(),
                os_name='Linux', architecture='x86_64')
    base.update(overrides)
    return profile_mod.Profile(**base)


def _record_for(profile, **overrides):
    experiment = dict(id='technical-fixture', version=1,
                      source_commit=profile.source_commit,
                      lock_digest=profile.lock_digest,
                      profile_digest=profile.digest, protocol='PREQUENTIAL',
                      adapter_version=profile.adapter_version)
    return _record(experiment=experiment, **overrides)


def _publish(tmp_path, foundation_module, plan_body, profile, record=None):
    root, frozen, artifacts = _stage(
        tmp_path, foundation_module, plan_body,
        record=record or _record_for(profile))
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    return root, payload


def test_same_profile_science_matches(tmp_path, foundation_module, plan_body):
    profile = _profile(foundation_module)
    root, payload = _publish(tmp_path, foundation_module, plan_body, profile)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    run_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in run_dir.iterdir() if p.is_file()}
    result = reexecution.reexecute(reader, RUN, profile)
    assert result.status == 'matched'
    report = reexecution.last_report()
    assert report['status'] == 'SCIENTIFIC_MATCH'
    assert report['new_run_id'] != RUN
    science = foundation_module('science')
    from development.evaluation.contracts import Payload
    assert science.science_digest(Payload(report['new_run_id'], 0), root) == \
        science.science_digest(payload, root)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in run_dir.iterdir() if p.is_file()}
    assert before == after  # original artifact immutable


def test_incompatible_reexecution_refused(tmp_path, foundation_module, plan_body):
    profile = _profile(foundation_module)
    root, _ = _publish(tmp_path, foundation_module, plan_body, profile)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    for bad in (_profile(foundation_module, source_commit='e' * 40),
                _profile(foundation_module, lock_digest='f' * 64),
                _profile(foundation_module, schema_version=6),
                _profile(foundation_module, clean=False)):
        result = reexecution.reexecute(reader, RUN, bad)
        assert result.status == 'incompatible'
        assert reexecution.last_report()['status'] == 'INCOMPATIBLE_REEXECUTION'


def test_compatibility_more_than_plan_digest(tmp_path, foundation_module,
                                             plan_body):
    # Same frozen plan, but a changed protocol in the recorded experiment
    # identity must block re-execution: a plan digest alone is not proof.
    profile = _profile(foundation_module)
    record = _record_for(profile)
    record['experiment'] = dict(record['experiment'], protocol='FROZEN')
    root, _ = _publish(tmp_path, foundation_module, plan_body, profile,
                       record=record)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, profile)
    assert result.status == 'incompatible'
    checks = reexecution.last_report()['checks']
    assert checks['plan_digest'] is True
    assert checks['protocol'] is False


def test_bounded_earliest_divergence(tmp_path, foundation_module, plan_body):
    profile = _profile(foundation_module)
    root, _ = _publish(tmp_path, foundation_module, plan_body, profile)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    # A second run whose joined post-ACK body differs scientifically.
    record = _record_for(profile, run_id=RUN2, events=[
        dict(key=['measured', 'default', 1, 'update'],
             body=dict(action='observe', confirmed=True,
                       update=dict(kind='b1_transition', source_ids=['other'])))])
    root2 = root
    from development.evaluation.contracts import RunResult
    artifacts = foundation_module('artifacts')
    journal = foundation_module('checkpoint').ScoreJournal.create(root2, RUN2)
    from .test_artifacts import _evidence
    journal.append(journal.frame(_evidence(1)))
    journal.close()
    artifacts.write_run_record(root2, record)
    from development.evaluation.analysis import require_frozen
    from development.evaluation.contracts import AnalysisPlan
    from development.evaluation.canonical import canonical_bytes
    frozen = require_frozen(AnalysisPlan(canonical_bytes(plan_body)), root2)
    payload2 = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen,
                                          root2, run_id=RUN2)
    integrity = foundation_module('integrity')
    finalized2 = integrity.finalize_payload(payload2, root2)
    integrity.publish(finalized2, integrity.make_receipt(finalized2, root2), root2)
    report = reexecution.compare_science(reader, RUN, RUN2)
    assert report['status'] == 'SCIENTIFIC_DIVERGENCE'
    first = report['differences'][0]
    assert first['ordinal'] == 1 and first['phase'] == 'measured'
    assert 'post_ack' in first['field']
    assert len(report['differences']) <= 100
    assert len(json.dumps(report).encode()) <= 64 * 1024
