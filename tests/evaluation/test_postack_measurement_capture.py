"""Post-ACK evidence survives the real worker and compact driver boundary."""
import copy
import json

import pytest

from .test_prediction_boundary import checkpoint


def _measurement_entry(pipe, launch, mode):
    from development.evaluation import adapters, baselines, worker
    from .test_adapter_equivalence import FixedRng
    original = adapters.construct_core
    forecast = baselines.forecast_baselines
    core_holder = []

    def guarded_forecast(*args, **kwargs):
        # Baseline work must never gate SCORE_ACK or touch a new DB snapshot.
        assert core_holder[0]._evaluation_capture.acked
        if mode == 'unavailable_history':
            raise AssertionError('Unavailable history is not an empty history')
        if mode == 'baseline_failure':
            raise RuntimeError('Injected post-ACK measurement failure')
        return forecast(*args, **kwargs)

    def construct(*args):
        core = original(*args)
        core_holder.append(core)
        core.decisions.rng = FixedRng('observe')
        if mode == 'unavailable_history':
            snapshot = core.decisions._snapshot

            def unavailable(key):
                q, _, _ = snapshot(key)
                return q, [], dict(status='unavailable', reason='history_read_error',
                                   cutoff_transition_id=None, raw_rows_examined=0)
            core.decisions._snapshot = unavailable
        return core

    baselines.forecast_baselines = guarded_forecast
    adapters.construct_core = construct
    worker._worker_entry(pipe, launch)


def _measurement_worker(tmp_path, foundation_module, monkeypatch, mode='normal'):
    from development.evaluation.channel import ChannelRouter
    from development.evaluation.contracts import WorkerLaunch
    module = foundation_module('worker')
    context = module.multiprocessing.get_context('spawn')

    class Context:
        Pipe = staticmethod(context.Pipe)

        @staticmethod
        def Process(**kwargs):
            kwargs.update(target=_measurement_entry, args=kwargs['args'] + (mode,))
            return context.Process(**kwargs)

    monkeypatch.setattr(module.multiprocessing, 'get_context', lambda _: Context())
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner('c' * 32, 0)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, 'c' * 32)

    class Scenario:
        def initial_observation(self, key):
            return checkpoint()['state_before']

        def apply_action(self, action, key):
            return {**checkpoint()['state_after'], 'load_ratio': (.3, .5, 1.5)[key[2] - 1]}

    worker = module.WorkerHandle.start(
        WorkerLaunch(cap, b'{"epsilon":1}', 3, 'a' * 64),
        channel=ChannelRouter(Scenario(), journal=journal))
    return worker, journal


def test_real_driver_preserves_candidates_and_same_cutoff_baselines(
        tmp_path, foundation_module, monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker, journal = _measurement_worker(tmp_path, foundation_module, monkeypatch)
    driver = foundation_module('prequential').PrequentialDriver(measured=3)
    try:
        result = driver.run(RunRequest('c' * 32), worker)
        assert result.status == 'COMPLETED'
        first, _, third = [json.loads(event.body) for event in driver.events]
        assert 'measurement_evidence' in third, 'Driver discarded preselection and baseline evidence'
        sidecar = third['measurement_evidence']
        assert set(sidecar) == {
            'schema', 'selection', 'unselected_predictions',
            'baselines', 'baseline_unavailable_reason'}
        assert sidecar['schema'] == 'b10_postack_measurement_v1'
        assert sidecar['selection']['selected_action'] == 'observe'
        assert set(sidecar['unselected_predictions']) == {'reflect', 'consolidate', 'rest'}
        assert sidecar['unselected_predictions']['rest']['signals']['load_ratio']['value'] == pytest.approx(.4)
        assert sidecar['baseline_unavailable_reason'] is None
        baselines = sidecar['baselines']
        assert baselines['action'] == 'observe'
        assert baselines['history']['cutoff_transition_id'] == 2
        assert baselines['history']['raw_ids'] == [2, 1]
        assert baselines['persistence']['signals']['load_ratio']['value'] == .2
        assert baselines['global-history']['signals']['load_ratio']['value'] == pytest.approx(.4)
        assert first['measurement_evidence']['baselines']['history']['cutoff_transition_id'] is None
        assert first['measurement_evidence']['baselines']['history']['raw_ids'] == []
        frames = [json.loads(line) for line in journal.path.read_bytes().splitlines()]
        assert frames[0]['evidence']['history_cutoff_id'] == 0
        assert sidecar['selection']['selected_prediction_sha256'] == frames[2]['header']['prediction_sha256']
        assert not {'state_before', 'state_after', 'selected_prediction', 'history_rows'} & sidecar.keys()
    finally:
        worker.stop()
        journal.close()


def test_unavailable_history_remains_unavailable_after_ack(
        tmp_path, foundation_module, monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker, journal = _measurement_worker(
        tmp_path, foundation_module, monkeypatch, 'unavailable_history')
    driver = foundation_module('prequential').PrequentialDriver(measured=1)
    try:
        assert driver.run(RunRequest('c' * 32), worker).status == 'COMPLETED'
        body = json.loads(driver.events[0].body)
        assert 'measurement_evidence' in body, 'Unavailable provenance was dropped'
        sidecar = body['measurement_evidence']
        assert sidecar['baselines'] is None
        assert sidecar['baseline_unavailable_reason'] == 'history_read_error'
        assert sidecar['selection']['history']['status'] == 'unavailable'
        assert len(sidecar['unselected_predictions']) == 3
    finally:
        worker.stop()
        journal.close()


def test_acked_failure_keeps_original_measurement_evidence(
        tmp_path, foundation_module, monkeypatch):
    from development.evaluation.contracts import RunRequest
    from .test_failure_fidelity import harness
    worker, journal, _ = harness(tmp_path, foundation_module, monkeypatch, 'b1_before')
    driver = foundation_module('prequential').PrequentialDriver(measured=2)
    try:
        result = driver.run(RunRequest('a' * 32), worker)
        assert result.status == 'INCOMPLETE'
        assert len(driver.events) == 1
        body = json.loads(driver.events[0].body)
        assert body['acked'] is True
        assert body['updates']['q']['status'] == 'confirmed'
        assert 'measurement_evidence' in body, 'Post-ACK failure lost prospective evidence'
        assert body['measurement_evidence']['baselines']['history']['raw_ids'] == []
    finally:
        worker.stop()
        journal.close()


def test_post_ack_builder_refuses_work_before_ack(foundation_module):
    from development.evaluation.contracts import ContractError
    capture = foundation_module('adapters').CaptureSession(None, None)
    assert hasattr(capture, 'post_ack_measurement'), 'Post-ACK measurement builder is missing'
    with pytest.raises(ContractError):
        capture.post_ack_measurement()


def test_measurement_failure_preserves_checkpoint_and_stops_without_retry(
        tmp_path, foundation_module, monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker, journal = _measurement_worker(
        tmp_path, foundation_module, monkeypatch, 'baseline_failure')
    driver = foundation_module('prequential').PrequentialDriver(measured=2)
    try:
        result = driver.run(RunRequest('c' * 32), worker)
        assert result.status == 'INCOMPLETE'
        assert len(journal.path.read_bytes().splitlines()) == 1
        assert len(driver.events) == 1
        body = json.loads(driver.events[0].body)
        assert body['acked'] is True
        assert body['execution'] == 'incomplete'
        assert body['updates']['b1']['status'] == 'confirmed'
        assert 'measurement_evidence' not in body
        assert json.loads(driver.failure_capture)['reason'] == 'MEASUREMENT_CAPTURE_INTERRUPTED'
    finally:
        worker.stop()
        journal.close()


def test_driver_budget_counts_measurement_evidence(foundation_module):
    from types import SimpleNamespace
    driver = foundation_module('prequential').PrequentialDriver(measured=1)
    response = dict(acked=True, status='completed', updates={}, capture={},
                    measurement_evidence={'oversized': ['x' * 4096] * 15})
    with pytest.raises(OSError, match='POST_ACK_RECORD_LIMIT'):
        driver.capture_completed(response, ('measured', 'default', 1, 'pre'),
                                 SimpleNamespace(checkpoint_bytes=8192))
    assert not driver.events


def test_driver_retains_new_evidence_without_inventing_legacy_evidence(foundation_module):
    from types import SimpleNamespace
    driver = foundation_module('prequential').PrequentialDriver(measured=2)
    value = dict(acked=True, status='completed', updates={}, capture={})
    driver.capture_completed(value, ('measured', 'default', 1, 'pre'),
                             SimpleNamespace(checkpoint_bytes=0))
    assert 'measurement_evidence' not in json.loads(driver.events[0].body)
    value['measurement_evidence'] = {'schema': 'test-detachment'}
    expected = copy.deepcopy(value['measurement_evidence'])
    driver.capture_completed(value, ('measured', 'default', 2, 'pre'),
                             SimpleNamespace(checkpoint_bytes=0))
    value['measurement_evidence']['schema'] = 'changed-after-capture'
    second = json.loads(driver.events[1].body)
    assert second.get('measurement_evidence') == expected
