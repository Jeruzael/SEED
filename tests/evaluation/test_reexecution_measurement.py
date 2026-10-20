"""One online transition carries captured baselines through publication/reexecution."""
import copy
import hashlib
import json

from development.evaluation.analysis import expand_inventory
from development.evaluation.contracts import CompletedEvidence, Population
from development.evaluation.metrics.prediction import measure_prediction
from development.evaluation.metrics.registry import measurement_data
from development.evaluation.postack import join_checkpoint
from development.evaluation.specs import raw_bytes

from .test_remediation import RUN, _produce_genuine, _profile


def test_captured_baseline_survives_publication_and_fresh_reexecution(
        tmp_path, foundation_module, plan_body):
    plan_body = copy.deepcopy(plan_body)
    plan_body['populations'][0].update(
        signal='battery_pct', method='seed', comparison='persistence')
    root, frozen = _produce_genuine(
        tmp_path, foundation_module, plan_body, measurement_evidence=True)
    reader = foundation_module('reader').EvaluationReader(root)
    artifacts = foundation_module('artifacts')
    original_record = artifacts.read_run_record(root, RUN)
    original_event = original_record['events'][0]
    sidecar = original_event['body']['measurement_evidence']
    assert sidecar['schema'] == 'b10_postack_measurement_v1'
    assert sidecar['baselines']['persistence']['signals']['battery_pct']['value'] == 80
    assert sidecar['selection']['history']['cutoff_transition_id'] is None
    assert sidecar['baselines']['history']['raw_ids'] == []

    joined = json.loads(reader.event(RUN, tuple(original_event['key'])).body)
    assert joined['post_ack']['measurement_evidence'] == sidecar
    checkpoint = joined['preupdate']['evidence']
    assert checkpoint['history_cutoff_id'] == 0
    assert checkpoint['state_after']['battery_pct'] == 79.75
    evidence = (CompletedEvidence(
        ('measured', 'default', 1, 'checkpoint'),
        raw_bytes(join_checkpoint(checkpoint, joined['post_ack']))),)
    measured = measure_prediction(
        'prediction.numeric-mae', evidence,
        Population('all', ('member-0',), 'whole',
                   expand_inventory(frozen.plan)[0].role),
        frozen)
    detail = measurement_data(measured)
    # Independent literal oracle: both first-cycle forecasts are 80, while
    # the real stationary scenario reports 79.75; one paired opportunity.
    assert detail['value'] == .25
    assert detail['baseline_value'] == .25
    assert detail['numerator'] == detail['baseline_numerator'] == .25
    assert detail['denominator'] == detail['opportunities'] == 1
    original_row = original_record['measurements'][0]
    assert original_row['state'] == 'MEASURED'
    assert original_row['value'] == .25
    assert original_row['reason'] is None

    run_dir = root.path / 'evaluation' / 'runs' / RUN
    original_files = list(run_dir.rglob('*'))
    original_files += list((root.path / 'evaluation' / 'receipts').glob(RUN + '*'))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in original_files if p.is_file()}
    reexecution = foundation_module('reexecution')
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()
    new_id = reexecution.last_report()['new_run_id']
    assert new_id != RUN
    fresh_record = artifacts.read_run_record(root, new_id)
    assert fresh_record['measurements'] == original_record['measurements']
    fresh_event = reader.event(new_id, tuple(original_event['key']))
    assert json.loads(fresh_event.body)['post_ack']['measurement_evidence'] == sidecar
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before} == before


def test_legacy_missing_baseline_is_not_retrofitted_during_reexecution(
        tmp_path, foundation_module, plan_body):
    plan_body = copy.deepcopy(plan_body)
    plan_body['populations'][0].update(
        signal='battery_pct', method='seed', comparison='persistence')
    root, _ = _produce_genuine(tmp_path, foundation_module, plan_body)
    artifacts = foundation_module('artifacts')
    original = artifacts.read_run_record(root, RUN)
    assert 'measurement_evidence' not in original['events'][0]['body']
    assert original['measurements'][0]['state'] == 'UNAVAILABLE'
    assert original['measurements'][0]['reason'] == 'INSUFFICIENT_EVIDENCE'
    reader = foundation_module('reader').EvaluationReader(root)
    reexecution = foundation_module('reexecution')
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()
    fresh = artifacts.read_run_record(
        root, reexecution.last_report()['new_run_id'])
    assert 'measurement_evidence' not in fresh['events'][0]['body']
    assert fresh['measurements'] == original['measurements']
