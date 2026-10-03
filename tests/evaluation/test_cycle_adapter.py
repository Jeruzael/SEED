"""I10: actual cycle delegation with an external durable B3 barrier."""
import json
import multiprocessing
import sqlite3
import pytest
from .test_prediction_boundary import checkpoint


def _cycle_child(pipe, launch, mode):
    core=None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.channel import LearnerClient, wire_bytes
        from development.evaluation.adapters import CaptureSession, construct_core
        streams=install_worker_adapters(launch)
        client=LearnerClient(pipe,streams.clock)
        core=construct_core(launch,streams,client)
        capture=CaptureSession(client,streams.clock)
        capture.attach(core)
        # Original B3 must retain identity, not merely an equivalent dictionary.
        import seed.organism as organism
        original=capture.original_b3
        seen=[]
        def b3(prediction,outcome):
            result=original(prediction,outcome);seen.append(result);return result
        capture.original_b3=b3
        if mode=='reflect':
            for i in range(8):core.memory.episode('experience',checkpoint()['state_before'],action='observe')
            core.decisions.rng=type('Rng',(),dict(random=lambda s:0.,choice=lambda s,p:'reflect'))()
        if mode=='consolidate':
            core.decisions.rng=type('Rng',(),dict(random=lambda s:0.,choice=lambda s,p:'consolidate'))()
        capture.begin(('measured','default',1,'pre'))
        try:
            result=core.cycle()
            status=result.status
        except ValueError:
            status='failed'
        tables={name:core.memory.db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                for name in ('transitions','episodes','q_values','concepts','consolidation_runs','self_model_current')}
        pipe.send_bytes(wire_bytes(dict(kind='final',status=status,record=capture.record,
              b3_calls=len(seen),same_b3=bool(seen) and capture.b3_result is seen[0],tables=tables)))
    except BaseException:
        import traceback;traceback.print_exc()
        try: pipe.send_bytes(b'{"kind":"child_error"}')
        except BaseException:pass
    finally:
        if core is not None:core.close()
        pipe.close()


def run_cycle(tmp_path, foundation_module, *, fail_ack=False, mode='normal'):
    # Assert the intended missing boundary before spawning/importing.
    foundation_module('adapters')
    from development.evaluation.contracts import WorkerLaunch, strict_json
    from development.evaluation.channel import ChannelRouter, wire_bytes
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('a'*32,0)
    launch=WorkerLaunch(cap,b'{"epsilon":1}',3,'a'*64)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'a'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return {**checkpoint()['state_after'],'battery_pct':73}
    router=ChannelRouter(Scenario(),journal=journal)
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe()
    process=ctx.Process(target=_cycle_child,args=(child,launch,mode),name='seed-evaluation-worker')
    process.start();child.close();trace=[];final=None
    try:
        while parent.poll(15):
            message=strict_json(parent.recv_bytes(65536))
            if message['kind']!='request':final=message;break
            request=message['request'];trace.append(request['operation'])
            if request['operation']=='checkpoint' and fail_ack:
                parent.send_bytes(b'{"kind":"error","code":"INVALID_CONTRACT"}')
            else:
                value=router.dispatch(request)
                parent.send_bytes(wire_bytes(dict(kind='response',value=value)))
        process.join(5)
        assert final and final['kind']=='final',final
        return final,trace,journal.path.read_bytes()
    finally:
        if process.is_alive():process.terminate();process.join(5)
        parent.close();journal.close()


def test_prediction_precedes_selection_and_outcome(tmp_path,foundation_module):
    result,trace,raw=run_cycle(tmp_path,foundation_module)
    assert result['status']=='completed'
    assert trace==['observation','apply','checkpoint']
    record=result['record']
    assert record['events']==['perception_before','prepare','select','action','perception_after','b3','checkpoint','ack']
    assert set(record['candidate_predictions'])=={'observe','reflect','consolidate','rest'}
    assert record['history']['cutoff_transition_id'] is None
    assert record['q_snapshot'][record['selected_action']]['visits']==0
    frame=json.loads(raw)
    assert frame['header']['prediction_sha256']==record['selection']['selected_prediction_sha256']
    assert result['tables']['transitions']==1
    assert result['tables']['q_values']==1


def test_original_b3_result_returned_unchanged(tmp_path,foundation_module):
    result,_,_=run_cycle(tmp_path,foundation_module)
    assert result['b3_calls']==1 and result['same_b3']
    assert result['record']['b3_result']['signals']['battery_pct']['absolute_error']==7


@pytest.mark.parametrize('mode',['normal','reflect','consolidate'])
def test_prior_action_effects_remain_without_ack(tmp_path,foundation_module,mode):
    result,trace,raw=run_cycle(tmp_path,foundation_module,fail_ack=True,mode=mode)
    assert result['status']=='failed'
    assert result['tables']['transitions']==0 and result['tables']['q_values']==0
    assert result['tables']['self_model_current']==0
    assert 'ack' not in result['record']['events']
    assert not raw
    if mode=='reflect':assert result['tables']['concepts']==2
    if mode=='consolidate':assert result['tables']['consolidation_runs']==1


def test_synthetic_body_installed_before_constructor(tmp_path,foundation_module):
    # Bootstrap poisons Body and all socket/subprocess host sensing paths. A
    # successful real cycle proves construction/perception use synthetic input.
    result,_,raw=run_cycle(tmp_path,foundation_module)
    assert result['status']=='completed'
    frame=json.loads(raw)
    assert 'wall_time' not in frame['evidence']['state_before']
    assert 'wall_time' not in frame['evidence']['state_after']


def test_worker_handle_delegates_cycle_through_parent_journal(tmp_path,foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('b'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'b'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64),
        channel=ChannelRouter(Scenario(),journal=journal))
    try:
        result=worker.request({'operation':'cycle','key':['measured','default',1,'pre']})
        assert result['status']=='completed' and result['acked'] is True
        assert result['capture']['selected_action'] in ('observe','reflect','consolidate','rest')
        assert 'point_scores' not in result
        assert len(journal.path.read_bytes().splitlines())==1
    finally:worker.stop();journal.close()
