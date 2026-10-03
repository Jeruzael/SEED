"""I12: bounded online dispatch and honest actual update prefixes."""
import json
import pytest
from .test_prediction_boundary import checkpoint


def test_online_actual_flow_and_maintenance(tmp_path,foundation_module):
    module=foundation_module('prequential')
    from development.evaluation.contracts import WorkerLaunch,RunRequest
    from development.evaluation.channel import ChannelRouter
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('d'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'d'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64),
        channel=ChannelRouter(Scenario(),journal=journal))
    driver=module.PrequentialDriver(measured=8,maintenance=True)
    try:
        result=driver.run(RunRequest('d'*32),worker)
        assert result.status=='COMPLETED'
        assert len(driver.events)==8 and not driver.skipped
        assert len(journal.path.read_bytes().splitlines())==8
        for event in driver.events:
            updates=json.loads(event.body)['updates']
            for stage in ('q','b1','b4','b5','b7','b8'):assert updates[stage]['status']=='confirmed',updates
            assert updates['b1']['transition_id']>0
        assert driver.maintenance[0]['after_completed']==8
        assert driver.maintenance[0]['provenance']=='owner_requested'
        assert driver.maintenance[0]['annotation']=='declared_maintenance'
    finally:worker.stop();journal.close()


@pytest.mark.parametrize('limit,pattern',[(8,'all_skipped'),(2048,'seven_skipped')])
def test_bounded_skipped_attempts_never_become_samples(foundation_module,monkeypatch,limit,pattern):
    module=foundation_module('prequential')
    from development.evaluation.contracts import RunRequest
    import time
    monkeypatch.setattr(time,'sleep',lambda _:(_ for _ in ()).throw(AssertionError('real retry sleep')))
    class Worker:
        def __init__(self):self.calls=0;self.retries=0;self.stopped=False
        def request(self,message):
            if message['operation']=='retry':self.retries+=1;return {'status':'retry_scheduled'}
            self.calls+=1
            if pattern=='all_skipped' or self.calls%8:
                return dict(status='skipped',acked=False,reason='stale_decision',delay_seconds=10)
            return dict(status='completed',acked=True,reason=None,delay_seconds=10,
                        updates={name:{'status':'confirmed'} for name in ('q','b1','b4','b5','b7','b8')},capture={})
        def stop(self,reason='OWNER_CANCELLED'):self.stopped=True
    worker=Worker();driver=module.PrequentialDriver(measured=1024)
    result=driver.run(RunRequest('bounded'),worker)
    assert result.status=='INCOMPLETE' and result.reason=='LIMIT_REACHED'
    assert worker.calls==limit
    assert len(driver.events)==(0 if pattern=='all_skipped' else 256)
    assert len(driver.skipped)==limit-len(driver.events)
    assert all(json.loads(item)['status']=='skipped' for item in driver.skipped)


def test_post_ack_unconfirmed_stages_stop_without_relearning(foundation_module):
    module=foundation_module('prequential')
    from development.evaluation.contracts import RunRequest
    class Worker:
        calls=0
        def request(self,message):
            self.calls+=1
            return dict(status='incomplete',acked=True,reason='CYCLE_INTERRUPTED',delay_seconds=None,
                        updates={'q':{'status':'confirmed'},'b1':{'status':'confirmed'},'b7':{'status':'unconfirmed'}},capture={})
        def stop(self,reason='OWNER_CANCELLED'):pass
    worker=Worker();driver=module.PrequentialDriver(measured=10)
    result=driver.run(RunRequest('partial'),worker)
    assert result.status=='INCOMPLETE' and worker.calls==1
    assert len(driver.events)==1
    assert json.loads(driver.events[0].body)['updates']['q']['status']=='confirmed'


def test_capture_failure_after_ack_preserves_cycle_and_never_dispatches_again(foundation_module):
    module=foundation_module('prequential')
    from development.evaluation.contracts import RunRequest
    class Worker:
        calls=0
        def request(self,message):
            self.calls+=1
            return dict(status='completed',acked=True,reason=None,delay_seconds=10,
                        updates={'q':{'status':'confirmed'}},capture={})
        def stop(self,reason='OWNER_CANCELLED'):pass
    driver=module.PrequentialDriver(measured=2);worker=Worker()
    def fail_capture(*args):raise OSError('post-ACK capture')
    driver.capture_completed=fail_capture
    result=driver.run(RunRequest('capture-failed'),worker)
    assert result.status=='INCOMPLETE' and worker.calls==1


def test_cleanup_failure_is_incomplete_without_rollback_or_retry(foundation_module):
    module=foundation_module('prequential')
    from development.evaluation.contracts import RunRequest
    class Worker:
        calls=0
        def request(self,message):
            self.calls+=1
            return dict(status='completed',acked=True,reason=None,delay_seconds=10,updates={},capture={})
        def stop(self,reason='OWNER_CANCELLED'):raise OSError('cleanup failed')
    worker=Worker();driver=module.PrequentialDriver(measured=1)
    result=driver.run(RunRequest('cleanup'),worker)
    assert result.status=='INCOMPLETE' and worker.calls==1
    assert len(driver.events)==1


def _cleanup_fault_entry(pipe,launch):
    from development.evaluation import worker,adapters
    original=adapters.construct_core
    def construct(*args):
        core=original(*args)
        close=core.close
        def failed_close():
            close()
            raise OSError('injected cleanup failure after actual close')
        core.close=failed_close
        return core
    adapters.construct_core=construct
    worker._worker_entry(pipe,launch)


def test_actual_worker_cleanup_failure_is_reported(tmp_path,foundation_module,monkeypatch):
    from development.evaluation.contracts import WorkerLaunch,RunRequest
    from development.evaluation.channel import ChannelRouter
    worker_module=foundation_module('worker')
    context=worker_module.multiprocessing.get_context('spawn')
    class Context:
        Pipe=staticmethod(context.Pipe)
        @staticmethod
        def Process(**kwargs):
            kwargs['target']=_cleanup_fault_entry
            return context.Process(**kwargs)
    monkeypatch.setattr(worker_module.multiprocessing,'get_context',lambda _:Context())
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('e'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'e'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=worker_module.WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64),
        channel=ChannelRouter(Scenario(),journal=journal))
    driver=foundation_module('prequential').PrequentialDriver(measured=2)
    try:
        result=driver.run(RunRequest('e'*32),worker)
        assert result.status=='INCOMPLETE' and result.reason=='CLEANUP_UNCONFIRMED'
        assert worker.cleanup_status=='failed'
        assert len(driver.events)==2 and len(journal.path.read_bytes().splitlines())==2
    finally:worker.stop();journal.close()


def test_action_start_metadata_uses_declared_stage_one(tmp_path,foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('f'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'f'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64),
        channel=ChannelRouter(Scenario(),journal=journal))
    try:
        value=worker.request({'operation':'cycle','key':['measured','default',1,'pre']})
        assert value['updates']['b1']['transition']['started_at']==1800000011.
        assert value['updates']['b1']['transition']['completed_at']==1800000012.
    finally:worker.stop();journal.close()
