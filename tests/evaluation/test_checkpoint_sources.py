"""Checkpoint source integration; no registered scientific execution."""
import copy
import hashlib
import json
import sqlite3

import pytest

from development.evaluation import artifacts
from development.evaluation.analysis import freeze_plan, validate_plan
from development.evaluation.contracts import ContractError
from .test_analysis import ClosedRoot


def _plan(tmp_path, plan_body, metrics=('world.evidence-count',), members=1):
    body = copy.deepcopy(plan_body)
    body['metrics'] = [dict(id=metric, version=1) for metric in metrics]
    body['questions'][0]['metrics'] = list(metrics)
    body['populations'][0]['signal'] = 'all'
    body['members'] = [
        dict(body['members'][0], id=f'member-{index}', seed=index)
        for index in range(members)
    ]
    body['seeds'] = list(range(members))
    directory = tmp_path / 'plan'
    directory.mkdir()
    return freeze_plan(validate_plan(body), ClosedRoot(directory))


def _checkpoint(tmp_path, count=2, name='state.sqlite3'):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    memory = Memory(tmp_path / name)
    try:
        world = WorldModel(memory)
        for ordinal in range(1, count + 1):
            _, tid = memory.record_transition_experience(
                state_before={'load_ratio': .5}, action='rest',
                state_after={'load_ratio': .4}, outcome={}, legacy_reward=0,
                started_at=ordinal - 1, completed_at=ordinal,
                world_model_eligible=True)
            world.observe_transition(tid)
        snapshot = tmp_path / (name + '.checkpoint')
        destination = sqlite3.connect(snapshot)
        try:
            memory.db.backup(destination)
            destination.execute('PRAGMA journal_mode=DELETE')
        finally:
            destination.close()
        return snapshot.read_bytes()
    finally:
        memory.close()


def _entry(member='member-0'):
    return dict(name='producer-source:' + member,
                file='checkpoints/' + member + '.sqlite3')


def _expected_world(member, count):
    return dict(
        identity=f'{member}:world.evidence-count:all:whole',
        metric='world.evidence-count', version=1, member=member,
        state='MEASURED', reason=None,
        value=dict(beliefs={
            '1:load_ratio:action:rest:numeric_delta': count,
            '1:load_ratio:global::numeric_delta': count,
        }, published=2, pending=0))


def test_bound_checkpoint_publishes_literal_world_counts(tmp_path, plan_body):
    """The publication path must consume raw rows rather than hash projection."""
    plan = _plan(tmp_path, plan_body)
    raw = _checkpoint(tmp_path)
    before = hashlib.sha256(raw).hexdigest()
    record = dict(checkpoints=[_entry()],
                  measurements=[_expected_world('member-0', 2)],
                  findings=[dict(question='prediction', status='NOT_EVALUATED',
                                 reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE',
                                 execution='COMPLETED')])
    encoded = artifacts._metrics(record, plan, 'COMPLETED', None, {}, [raw])
    produced = json.loads(encoded)['produced']
    assert produced == [_expected_world('member-0', 2)]
    assert hashlib.sha256(raw).hexdigest() == before


def test_bound_source_survives_artifact_publication_and_readback(
        tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import RunResult
    from .test_artifacts import RUN, _payload_dir, _record, _stage
    body = copy.deepcopy(plan_body)
    body['metrics'] = [dict(id='world.evidence-count', version=1)]
    body['questions'][0]['metrics'] = ['world.evidence-count']
    body['populations'][0]['signal'] = 'all'
    raw = _checkpoint(tmp_path)
    record = _record(
        checkpoints=[_entry()],
        measurements=[_expected_world('member-0', 2)],
        findings=[dict(question='prediction', status='NOT_EVALUATED',
                       reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE',
                       execution='COMPLETED')])
    root, plan, _ = _stage(tmp_path, foundation_module, body, record=record)
    directory = _payload_dir(tmp_path)
    (directory / 'checkpoints').mkdir()
    (directory / _entry()['file']).write_bytes(raw)
    payload = artifacts.assemble_payload(
        RunResult('COMPLETED', None), plan, root)
    integrity = foundation_module('integrity')
    final = integrity.finalize_payload(payload, root)
    integrity.publish(final, integrity.make_receipt(final, root), root)
    reader = foundation_module('reader').EvaluationReader(root)
    detail = json.loads(reader.detail(RUN).summary.body)
    assert detail['measurements'] == [_expected_world('member-0', 2)]
    stored = root.path / 'evaluation' / 'runs' / RUN / _entry()['file']
    assert stored.read_bytes() == raw
    assert len(reader.events(RUN).events) == 1


@pytest.mark.parametrize('entries', [None, [dict(
    name='initial', file='checkpoints/initial.sqlite3')]])
def test_unlabelled_or_initial_checkpoint_cannot_supply_measured_source(
        tmp_path, plan_body, entries):
    plan = _plan(tmp_path, plan_body)
    raw = _checkpoint(tmp_path)
    kwargs = {} if entries is None else dict(checkpoint_entries=entries)
    rows, _ = artifacts.derive_scientific_outputs(
        plan, {}, [raw], 'COMPLETED', **kwargs)
    assert rows[0]['state'] == 'UNAVAILABLE'
    assert rows[0]['reason'] == 'MISSING_WORLD_SOURCE'


def test_member_binding_does_not_reuse_the_last_snapshot(tmp_path, plan_body):
    plan = _plan(tmp_path, plan_body, members=2)
    first = _checkpoint(tmp_path, count=2, name='first.sqlite3')
    second = _checkpoint(tmp_path, count=4, name='second.sqlite3')
    rows, _ = artifacts.derive_scientific_outputs(
        plan, {}, [second, first], 'COMPLETED',
        checkpoint_entries=[_entry('member-1'), _entry('member-0')])
    assert rows == (_expected_world('member-0', 2),
                    _expected_world('member-1', 4))


@pytest.mark.parametrize('entries', [
    [_entry('unknown')],
    [_entry(), _entry()],
    [],
])
def test_ambiguous_checkpoint_bindings_fail_closed(
        tmp_path, plan_body, entries):
    plan = _plan(tmp_path, plan_body)
    raw = _checkpoint(tmp_path)
    snapshots = [raw] * (len(entries) or 1)
    with pytest.raises(ContractError):
        artifacts.derive_scientific_outputs(
            plan, {}, snapshots, 'COMPLETED',
            checkpoint_entries=entries)


@pytest.mark.parametrize('field,value', [('bytes', 1), ('sha256', '0' * 64)])
def test_source_binding_checks_supplied_byte_identity(
        tmp_path, plan_body, field, value):
    plan = _plan(tmp_path, plan_body)
    with pytest.raises(ContractError):
        artifacts.derive_scientific_outputs(
            plan, {}, [_checkpoint(tmp_path)], 'COMPLETED',
            checkpoint_entries=[dict(_entry(), **{field: value})])


def test_checkpoint_does_not_invent_historical_source_evidence(
        tmp_path, plan_body):
    plan = _plan(tmp_path, plan_body, metrics=(
        'world.first-belief', 'semantic.promotion-latency',
        'self.factual-fidelity'))
    rows, _ = artifacts.derive_scientific_outputs(
        plan, {}, [_checkpoint(tmp_path)], 'COMPLETED',
        checkpoint_entries=[_entry()])
    reasons = {row['metric']: (row['state'], row['reason']) for row in rows}
    assert reasons == {
        'world.first-belief': ('UNAVAILABLE', 'MISSING_PUBLICATION_HISTORY'),
        'semantic.promotion-latency': ('UNAVAILABLE',
                                       'NO_CONSOLIDATION_OPPORTUNITY'),
        'self.factual-fidelity': ('UNAVAILABLE', 'MISSING_SELF_SOURCE_EVIDENCE'),
    }


def test_source_adapter_preserves_raw_json_and_native_cells(tmp_path):
    from development.evaluation.producer_sources import checkpoint_source
    raw = _checkpoint(tmp_path)
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(raw)
        literal = ('{ "mean_delta": -0.1, "pid": 123, "run_id": "original",'
                   ' "storage": {"page_count": 17}, "label": "é" }')
        db.execute('UPDATE world_beliefs SET value_json=?', (literal,))
        db.commit()
        snapshot = db.serialize()
        source = checkpoint_source(snapshot)
        assert len(source['tables']['world_beliefs']) == 2
        for row in source['tables']['world_beliefs']:
            assert row['value_json'] == literal
            assert type(row['value_json']) is str
            assert type(row['evidence_count']) is int
            assert type(row['confidence']) is float
        assert db.serialize() == snapshot
        assert 'self_evidence' not in source
        assert 'world_revisions' not in source
    finally:
        db.close()


@pytest.mark.parametrize('defect', ['schema', 'version', 'blob', 'rows'])
def test_source_adapter_rejects_invalid_or_oversized_sources(tmp_path, defect):
    from development.evaluation.producer_sources import checkpoint_source
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(_checkpoint(tmp_path))
        if defect == 'schema':
            db.execute('ALTER TABLE world_beliefs ADD COLUMN unregistered TEXT')
        elif defect == 'version':
            db.execute('UPDATE seed_schema SET version=6')
        elif defect == 'blob':
            db.execute('UPDATE world_beliefs SET value_json=?', (b'{}',))
        else:
            db.executemany(
                'INSERT INTO consolidation_runs '
                '(id,started_at,model,model_version,provenance,status,result_json)'
                " VALUES(?,0,'semantic_v1',1,'fixture','completed','{}')",
                [(index,) for index in range(1, 2050)])
        db.commit()
        with pytest.raises(ContractError):
            checkpoint_source(db.serialize())
    finally:
        db.close()
