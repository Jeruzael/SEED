import json
import multiprocessing
import pytest

from development.evaluation.fixtures import admit_c_workspace, build_fixture
from development.evaluation.scenarios.evidence import EvidenceScenario
from development.evaluation.contracts import ContractError


def _fixture_child(pipe, cap, variant):
    owned = frozen = None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        from development.evaluation.frozen import freeze_state, FrozenWorker
        streams = install_worker_adapters(WorkerLaunch(cap, b'{"epsilon":0.15}', 3, 'c'*64))
        owned = OwnedState.fresh(cap, {'epsilon': .15})
        if variant != 'cold':
            build_fixture('conflict', owned)
        before_variant = owned.raw_tables()
        if variant != 'conflict':
            build_fixture(variant, owned)
        provenance = owned.fixture_provenance
        raw = owned.raw_tables()
        fixture = freeze_state(owned)
        frozen = FrozenWorker(fixture, streams)
        before = frozen.raw_state()
        scenario = EvidenceScenario(variant)
        class Client:
            def apply(self, action, ordinal):
                return scenario.apply_action(action, ('probe', scenario.subcase, ordinal, 'outcome'))
        for ordinal in range(1, 17):
            key = ('probe', scenario.subcase, ordinal, 'pre')
            record = frozen.probe(scenario.initial_observation(key), key, Client(),
                                  read_time=provenance['read_time'])
            assert json.loads(record.body)['assay_kind'] == 'FROZEN_SELECTION_ASSAY'
        assert frozen.raw_state() == before
        final_record = json.loads(record.body)
        statuses = [signal['status'] for candidate in final_record['selection']['candidates'].values()
                    for signal in candidate['resource_forecasts'].values()]
        projection = None
        row = frozen.memory.db.execute('SELECT data_json FROM self_model_current').fetchone()
        if row:
            from seed.self_model import project_snapshot
            projection = project_snapshot(json.loads(row[0]), provenance['read_time'])
        frozen.assert_unchanged()
        pipe.send(('ok', raw, before_variant == raw, provenance, fixture.sha256, statuses, projection, fixture))
    except BaseException:
        import traceback
        traceback.print_exc()
        pipe.send(('error',))
    finally:
        if frozen: frozen.close()
        if owned: owned.close()
        pipe.close()


@pytest.fixture(scope='module')
def variants(tmp_path_factory):
    from development.evaluation.paths import EvaluationRoot
    root = EvaluationRoot.create(tmp_path_factory.mktemp('c').resolve())
    results = {}
    context = multiprocessing.get_context('spawn')
    for variant in ('cold', 'conflict', 'unavailable', 'stale'):
        cap = root.assign_learner('c-' + variant, 0)
        parent, child = context.Pipe()
        process = context.Process(target=_fixture_child, args=(child, cap, variant), name='seed-evaluation-worker')
        process.start(); child.close()
        try:
            assert parent.poll(30)
            result = parent.recv(); process.join(5)
            assert result[0] == 'ok', result
            results[variant] = result
        finally:
            if process.is_alive(): process.terminate(); process.join(5)
            parent.close()
    return results


def test_c_cold_does_not_publish(variants):
    tables = variants['cold'][1]
    for table in ('transitions', 'world_beliefs', 'semantic_memories', 'self_model_current', 'decision_records'):
        assert tables[table] == []


def test_c_conflict_is_producer_owned_not_forged_policy(variants):
    tables = variants['conflict'][1]
    assert len(tables['transitions']) == 128
    assert len(tables['world_model_processed']) == 128
    assert tables['decision_records'] == []
    assert tables['semantic_memories'] and tables['self_model_current']
    provenance = variants['conflict'][3]
    assert provenance['driver'] == 'producer_fixture_v1'
    assert provenance['transition_ids'] == list(range(1, 129))
    assert provenance['before_freeze'] is True
    rows = tables['transitions']
    assert [row[5] for row in rows[:8]] == ['observe', 'reflect', 'consolidate', 'rest'] * 2
    assert json.loads(rows[63][6])['load_ratio'] == .6
    assert json.loads(rows[64][6])['load_ratio'] == .4
    assert len(provenance['final_digest']) == 64


def test_unavailable_keeps_candidate_source_and_history(variants):
    result = variants['unavailable']
    provenance = result[3]
    assert provenance['reason'] == 'declared_invalid_typed_source_payload'
    assert len(provenance['modification_digest']) == 64
    source_id = provenance['source_identity']
    rows = result[1]['world_beliefs']
    assert any(row[0] == source_id for row in rows)
    assert result[1]['semantic_memory_history']
    # Inspect schema-independent literal status in the real producer row.
    assert any('source_unavailable' in row for row in result[1]['semantic_memories'])


def test_stale_uses_301_seconds_without_mutation(variants):
    result = variants['stale']
    assert result[2] is True
    assert result[3]['read_time'] - result[3]['last_evidence_time'] == 301
    assert set(result[5]) == {'stale'}
    assert result[6]['observations']['load_ratio']['status'] == 'stale'


def test_c_missing_inputs_and_workspace_bounds():
    scenario = EvidenceScenario('unavailable')
    observation = scenario.initial_observation(('probe', 'unavailable', 1, 'pre'))
    assert 'load_ratio' not in observation and 'disk_free_pct' not in observation
    assert observation['battery_pct'] is None and observation['network'] is None
    with pytest.raises(ContractError):
        scenario.initial_observation(('probe', 'unavailable', 17, 'pre'))
    admit_c_workspace((1, 2, 3, 4), generating_bytes=5)
    with pytest.raises(ContractError):
        admit_c_workspace((32*1024**2,)*4, generating_bytes=1)
    with pytest.raises(ContractError):
        admit_c_workspace((33*1024**2, 1, 1, 1), generating_bytes=0)


def test_stale_read_time_crosses_closed_worker_control(variants, foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    from dataclasses import replace
    stale = variants['stale']; fixture = stale[7]
    launch = WorkerLaunch(fixture.learner, b'{"epsilon":0.15}', 3, 'c'*64,
        protocol='FROZEN_SELECTION_ASSAY', launch_mode='COMPLETED_OWNED_FIXTURE', fixture=fixture,
        read_time=stale[3]['read_time'])
    worker = foundation_module('worker').WorkerHandle.start(launch, channel=ChannelRouter(EvidenceScenario('stale')))
    before = (fixture.learner.home/'memory.sqlite3').read_bytes()
    try:
        result = worker.request({'operation':'probe','key':['probe','stale',1,'pre']})
        assert result['read_time'] == stale[3]['last_evidence_time'] + 301
        assert all(s['status']=='stale' for c in result['selection']['candidates'].values() for s in c['resource_forecasts'].values())
    finally: worker.stop()
    assert (fixture.learner.home/'memory.sqlite3').read_bytes() == before
    for value in (True,float('nan'),-1):
        with pytest.raises(ValueError): foundation_module('worker').WorkerHandle.start(replace(launch,read_time=value))
    with pytest.raises(ValueError): foundation_module('worker').WorkerHandle.start(replace(launch,protocol='PREQUENTIAL'))
