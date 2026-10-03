"""I09: durable external evidence, never a learner score or aggregate."""
import copy
import json
import os
import pytest
from .test_prediction_boundary import checkpoint


def evidence(value=None):
    from development.evaluation.contracts import PreUpdateEvidence
    return PreUpdateEvidence(json.dumps(value or checkpoint()).encode())


def journal(tmp_path, foundation_module):
    root = foundation_module('paths').EvaluationRoot.create(tmp_path)
    return foundation_module('checkpoint').ScoreJournal.create(root, 'a'*32)


def test_point_score_literal(foundation_module):
    scores = foundation_module('point_scores')
    value = checkpoint()
    value['state_after'].update(battery_pct=73, load_ratio=.8, disk_free_pct=70, network=False)
    result = scores.point_scores(evidence(value))
    assert result['battery_pct']['absolute_error'] == 7
    assert result['load_ratio']['absolute_error'] == pytest.approx(.6)
    assert result['disk_free_pct']['absolute_error'] == 5
    assert result['network_reachable'] == dict(status='scored', correct=False, unavailable_reason=None,
        brier_status='unavailable', brier=None, brier_unavailable_reason='probability_unavailable')
    assert scores.brier(.75, False) == .5625
    signal = value['prediction']['signals']['network_reachable']
    signal.update(method='action_boolean_frequency', evidence_count=4, confidence=.2, probability_true=.75)
    assert scores.point_scores(evidence(value))['network_reachable']['brier'] == .5625


def test_missing_is_unavailable_not_zero(foundation_module):
    value = checkpoint()
    value['state_after'] = {}
    result = foundation_module('point_scores').point_scores(evidence(value))
    assert result['battery_pct'] == dict(status='unavailable', absolute_error=None, unavailable_reason='outcome_unavailable')
    assert result['network_reachable']['correct'] is None
    value = checkpoint()
    from seed.predictor import empty_history_batch
    value['state_before'] = {}
    value['prediction'] = empty_history_batch({}, ('observe',)).predictions['observe']
    result = foundation_module('point_scores').point_scores(evidence(value))
    assert all(r['status'] == 'unavailable' and r['unavailable_reason'] == 'prediction_unavailable' for r in result.values())


def test_fsync_precedes_constant_ack(tmp_path, foundation_module, monkeypatch):
    j = journal(tmp_path, foundation_module)
    trace=[]
    original=os.fsync
    def fsync(fd):
        trace.append('fsync'); original(fd)
    monkeypatch.setattr(os, 'fsync', fsync)
    assert j.ack(evidence()) == 'SCORE_ACK'
    trace.append('ACK')
    assert trace == ['fsync', 'ACK']
    j.close()
    frame=json.loads((tmp_path/'.seed-evaluation/evaluation/partials'/('a'*32)/'preupdate.ndjson').read_bytes())
    assert frame['header']['checkpoint_status']=='CHECKPOINTED'
    assert frame['header']['history_cutoff_id'] is None
    assert frame['evidence']==checkpoint()
    assert len(frame['header']['prediction_sha256'])==64
    assert frame['header']['point_scores']['battery_pct']['absolute_error']==0


@pytest.mark.parametrize('mode',['malformed','duplicate','partial','flush','fsync','deadline'])
def test_pre_ack_failure_blocks_current_updates(tmp_path, foundation_module, monkeypatch, mode):
    module=foundation_module('checkpoint'); j=journal(tmp_path, foundation_module)
    current_updates=[]
    payload=evidence()
    if mode=='malformed':
        value=checkpoint(); value['prediction']['truth']=99; payload=evidence(value)
    if mode=='duplicate': assert j.ack(payload)=='SCORE_ACK'
    if mode=='partial':
        original=j._file
        class Partial:
            def write(self, raw): return original.write(raw[:10])
            def __getattr__(self, name): return getattr(original, name)
        j._file=Partial()
    if mode=='flush':
        original=j._file
        class FlushFailure:
            def flush(self): raise OSError('flush')
            def __getattr__(self, name): return getattr(original, name)
        j._file=FlushFailure()
    if mode=='fsync': monkeypatch.setattr(os,'fsync',lambda fd: (_ for _ in ()).throw(OSError('fsync')))
    if mode=='deadline': monkeypatch.setattr(j,'_clock',iter([0,11]).__next__)
    with pytest.raises(module.CheckpointError) as exc:
        if j.ack(payload)=='SCORE_ACK': current_updates.append('learning')
    assert not current_updates
    assert exc.value.status == ('FAILED' if mode in ('malformed','duplicate') else 'INCOMPLETE')
    with pytest.raises(module.CheckpointError): j.ack(evidence())
    j.close()


@pytest.mark.parametrize('limit',[4096,16384,65536])
def test_byte_limit_exact_boundary_and_one_over(foundation_module, limit):
    bound=foundation_module('checkpoint').bounded_bytes
    assert bound(b'x'*limit,limit)==b'x'*limit
    with pytest.raises(ValueError): bound(b'x'*(limit+1),limit)


def test_tampered_frame_rejected_before_write(tmp_path, foundation_module):
    module=foundation_module('checkpoint'); j=journal(tmp_path,foundation_module)
    frame=j.frame(evidence())
    header=json.loads(frame.header); header['point_scores']['battery_pct']['absolute_error']=99
    from development.evaluation.contracts import CheckpointFrame
    with pytest.raises(module.CheckpointError): j.append(CheckpointFrame(json.dumps(header).encode(),frame.evidence))
    assert j.path.stat().st_size==0
    j.close()


def test_ack_path_calls_no_aggregates(tmp_path, foundation_module, monkeypatch):
    import sys
    from types import ModuleType
    def poison(name): raise AssertionError('aggregate on ACK path: '+name)
    for name in ('metrics','baselines','utility','artifacts','indexes','scientific_digest','integrity','dashboard'):
        module=ModuleType('development.evaluation.'+name)
        module.__getattr__=poison
        monkeypatch.setitem(sys.modules,module.__name__,module)
    j=journal(tmp_path, foundation_module)
    assert j.ack(evidence())=='SCORE_ACK'
    j.close()


def test_closed_checkpoint_transport_returns_only_ack(tmp_path, foundation_module):
    from development.evaluation.channel import ChannelRouter, LearnerClient, wire_bytes
    from development.evaluation.contracts import strict_json
    class Scenario:
        def initial_observation(self,key): return checkpoint()['state_before']
        def apply_action(self,action,key): return checkpoint()['state_after']
    j=journal(tmp_path,foundation_module)
    router=ChannelRouter(Scenario(),journal=j)
    class Pipe:
        def send_bytes(self,raw): self.reply=wire_bytes(dict(kind='response',value=router.dispatch(strict_json(raw)['request'])))
        def recv_bytes(self,limit): return self.reply
        def poll(self,timeout): return True
    client=LearnerClient(Pipe())
    client.observation('measured',1)
    client.apply('observe',1)
    assert client.send_checkpoint(evidence())=='SCORE_ACK'
    with pytest.raises(ValueError): client.send_checkpoint(evidence())
    assert j.path.stat().st_size>0
    j.close()


def test_checkpoint_truth_or_nonconstant_ack_is_terminal(foundation_module):
    from development.evaluation.channel import LearnerClient, wire_bytes
    class Pipe:
        def send_bytes(self,raw): pass
        def recv_bytes(self,limit): return wire_bytes(dict(kind='response',value=dict(token='SCORE_ACK',score=1)))
        def poll(self,timeout): return True
    client=LearnerClient(Pipe())
    with pytest.raises(ValueError): client.send_checkpoint(evidence())
    assert client.failed


@pytest.mark.parametrize('ancestor',['run','partials','evaluation','file'])
@pytest.mark.parametrize('when',['before','during_fsync'])
def test_declared_journal_path_replacement_never_receives_ack(tmp_path,foundation_module,monkeypatch,ancestor,when):
    module=foundation_module('checkpoint');j=journal(tmp_path,foundation_module)
    def replace_path():
        source={'run':j.path.parent,'partials':j.path.parent.parent,'evaluation':j.path.parent.parent.parent,'file':j.path}[ancestor]
        source.rename(source.with_name('detached-'+source.name))
        j.path.parent.mkdir(parents=True,exist_ok=True)
        j.path.write_bytes(b'')
    if when=='before':replace_path()
    else:
        original=module.os.fsync
        def fsync(fd):original(fd);replace_path()
        monkeypatch.setattr(module.os,'fsync',fsync)
    try:
        with pytest.raises(module.CheckpointError):j.ack(evidence())
        assert j.failed
        assert j.path.read_bytes()==b''
    finally:j.close()
