"""I24: recorded replay reads stored facts only; it never runs cognition."""
import json

import pytest

from .test_artifacts import RUN, _record, _stage


def _publish(tmp_path, foundation_module, plan_body, record=None, frames=1):
    root, frozen, artifacts = _stage(tmp_path, foundation_module, plan_body,
                                     record=record, journal_frames=frames)
    from development.evaluation.contracts import RunResult
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    receipt = integrity.make_receipt(finalized, root)
    integrity.publish(finalized, receipt, root)
    return root


def test_replay_never_calls_cognition(tmp_path, foundation_module, plan_body,
                                      monkeypatch):
    root = _publish(tmp_path, foundation_module, plan_body)
    replay = foundation_module('replay')
    reader_mod = foundation_module('reader')

    def poison(*args, **kwargs):
        raise AssertionError('cognition executed during replay')

    import seed.decision as decision
    import seed.predictor as predictor
    import seed.world_model as world_model
    monkeypatch.setattr(predictor.Predictor, 'predict', poison)
    monkeypatch.setattr(decision.DecisionSystem, 'select', poison)
    monkeypatch.setattr(world_model.WorldModel, 'observe_transition', poison)
    reader = reader_mod.EvaluationReader(root)
    page = reader.events(RUN)
    assert len(page.events) == 1
    event = page.events[0]
    assert event.key == ('measured', 'default', 1, 'update')
    body = json.loads(event.body)
    # The stored original prediction/action/outcome are presented verbatim.
    assert body['preupdate']['evidence']['selected_action'] == 'observe'
    assert body['preupdate']['header']['prediction_sha256']
    assert body['post_ack']['confirmed'] is True
    single = reader.event(RUN, ('measured', 'default', 1, 'update'))
    assert single.body == event.body
    joined = replay.join_events(root, RUN)
    assert [e.key for e in joined] == [event.key]


def test_lossless_paging_with_reused_ordinals(tmp_path, foundation_module,
                                              plan_body):
    # The same ordinal in two phases is a distinct event; paging is lossless.
    from development.evaluation.contracts import PreUpdateEvidence, RunResult
    import json as _json
    from .test_prediction_boundary import checkpoint
    from .test_artifacts import _frozen, _root
    root = _root(tmp_path, foundation_module)
    frozen = _frozen(root, foundation_module, plan_body)
    artifacts = foundation_module('artifacts')
    journal = foundation_module('checkpoint').ScoreJournal.create
    j = journal(root, RUN)
    for phase in ('training', 'measured'):
        value = checkpoint(); value['phase'] = phase; value['transition_ordinal'] = 1
        j.append(j.frame(PreUpdateEvidence(_json.dumps(value).encode())))
    j.close()
    record = _record(events=[
        dict(key=['training', 'default', 1, 'update'], body=dict(confirmed=True)),
        dict(key=['measured', 'default', 1, 'update'], body=dict(confirmed=True))],
        planned_transitions=2)
    artifacts.write_run_record(root, record)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None), frozen, root)
    integrity = foundation_module('integrity')
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root), root)
    reader = foundation_module('reader').EvaluationReader(root)
    seen = []
    cursor = None
    while True:
        page = reader.events(RUN, cursor=cursor, limit=1)
        seen.extend(e.key for e in page.events)
        cursor = page.cursor
        if cursor is None:
            break
    assert seen == [('measured', 'default', 1, 'update'),
                    ('training', 'default', 1, 'update')] or \
           seen == [('training', 'default', 1, 'update'),
                    ('measured', 'default', 1, 'update')]
    assert len(set(seen)) == 2


def test_replay_rejects_coordinated_tamper(tmp_path, foundation_module,
                                           plan_body):
    # Review m2: tampering journal evidence AND the events digest pointer
    # together must still fail, because replay recomputes the B8 prediction
    # digest and the preupdate evidence digest from the stored evidence.
    import hashlib
    from development.evaluation.contracts import ContractError
    root = _publish(tmp_path, foundation_module, plan_body)
    run_dir = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    journal = run_dir / 'preupdate.ndjson'
    record = json.loads(journal.read_bytes())
    record['evidence']['prediction']['signals']['battery_pct']['point'] = 1
    line = json.dumps(record).encode() + b'\n'
    journal.write_bytes(line)
    events = run_dir / 'events.ndjson'
    event = json.loads(events.read_bytes())
    event['journal_sha256'] = hashlib.sha256(line).hexdigest()
    events.write_bytes(json.dumps(event).encode() + b'\n')
    replay = foundation_module('replay')
    with pytest.raises(ContractError):
        replay.join_events(root, RUN)
