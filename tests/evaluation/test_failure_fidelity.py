"""I13 actual producer fault prefixes, never fabricated completed learning."""
import json
import sqlite3
from contextlib import closing
import pytest
from .test_prediction_boundary import checkpoint


def _fault_entry(pipe,launch,mode):
    from development.evaluation import worker,adapters
    original=adapters.construct_core
    if mode=='capture_after_commit':
        capture=adapters.capture_updates
        def fail_capture(*args):
            capture(*args)
            raise OSError('injected evidence capture after commit')
        adapters.capture_updates=fail_capture
    def construct(*args):
        core=original(*args)
        from .test_adapter_equivalence import FixedRng
        core.decisions.rng=FixedRng('consolidate' if mode=='prior_consolidate' else 'observe')
        targets={'q':(core.learner,'update'),'b1':(core.memory,'record_transition_experience'),
                 'b4':(core.world_model,'recover'),'b7':(core.self_model,'update')}
        prefix,_,timing=mode.partition('_')
        if prefix in targets:
            target,name=targets[prefix];producer=getattr(target,name)
            def fault(*args,**kwargs):
                if timing=='after':producer(*args,**kwargs)
                raise OSError('injected '+mode)
            setattr(target,name,fault)
        if mode=='swallowed_b7':
            import seed.self_model as model
            def fail(*args,**kwargs):raise sqlite3.OperationalError('injected snapshot read')
            model.build_snapshot=fail
        if mode=='prediction_capture':
            prepare=adapters.CaptureSession._prepare
            def failed_prepare(self,*args,**kwargs):
                prepare(self,*args,**kwargs)
                raise ValueError('injected prediction capture')
            adapters.CaptureSession._prepare=failed_prepare
        if mode=='outcome_capture':
            perceive=core.body.perceive
            def failed_outcome():
                state=perceive()
                if core.body.perceptions==2:raise ValueError('injected outcome capture')
                return state
            core.body.perceive=failed_outcome
        if mode=='maintenance_swallowed':
            def failed_candidates():raise sqlite3.OperationalError('injected swallowed B6 read')
            core.consolidator._candidates=failed_candidates
            consolidate=core.consolidate
            def returned_failed(*args,**kwargs):
                try:return consolidate(*args,**kwargs)
                except sqlite3.Error:
                    return core.consolidator.get_run(core.memory.db.execute('SELECT MAX(id) FROM consolidation_runs').fetchone()[0])
            core.consolidate=returned_failed
        if mode=='maintenance_after':
            run=core.consolidator.run
            def failed_maintenance(state,provenance):
                result=run(state,provenance)
                if provenance=='owner_requested':raise OSError('injected maintenance after commit')
                return result
            core.consolidator.run=failed_maintenance
        return core
    adapters.construct_core=construct
    worker._worker_entry(pipe,launch)


def harness(tmp_path,foundation_module,monkeypatch,mode='normal'):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    module=foundation_module('worker')
    context=module.multiprocessing.get_context('spawn')
    class Context:
        Pipe=staticmethod(context.Pipe)
        @staticmethod
        def Process(**kwargs):
            kwargs.update(target=_fault_entry,args=kwargs['args']+(mode,))
            return context.Process(**kwargs)
    monkeypatch.setattr(module.multiprocessing,'get_context',lambda _:Context())
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('a'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'a'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=module.WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":1}',3,'a'*64),channel=ChannelRouter(Scenario(),journal=journal))
    return worker,journal,cap.home/'memory.sqlite3'


def persisted(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        return dict(transitions=db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0],
                    visits=db.execute('SELECT COALESCE(SUM(visits),0) FROM q_values').fetchone()[0],
                    b4=db.execute('SELECT COUNT(*) FROM world_model_processed').fetchone()[0],
                    b7=db.execute('SELECT COUNT(*) FROM self_model_current').fetchone()[0],
                    b6=db.execute('SELECT COUNT(*) FROM consolidation_runs').fetchone()[0])


@pytest.mark.parametrize('mode',[
    'prediction_capture','outcome_capture','point_score','append','partial','flush','fsync','deadline','malformed','duplicate','size'])
def test_pre_ack_failure_ladder_has_no_current_learning(tmp_path,foundation_module,monkeypatch,mode):
    from development.evaluation.contracts import RunRequest,ContractError
    module=foundation_module('checkpoint')
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch,mode)
    if mode=='point_score':monkeypatch.setattr(module,'point_scores',lambda _:(_ for _ in ()).throw(ContractError()))
    if mode in ('append','partial','flush'):
        original=journal._file
        class Fault:
            def write(self,raw):
                if mode=='append':raise OSError('injected append')
                return original.write(raw[:10] if mode=='partial' else raw)
            def flush(self):
                if mode=='flush':raise OSError('injected flush')
                return original.flush()
            def __getattr__(self,name):return getattr(original,name)
        journal._file=Fault()
    if mode=='fsync':monkeypatch.setattr(module.os,'fsync',lambda _:(_ for _ in ()).throw(OSError('injected fsync')))
    if mode=='deadline':monkeypatch.setattr(journal,'_clock',iter([0,11]).__next__)
    if mode in ('malformed','size'):
        monkeypatch.setattr(journal,'frame',lambda _:(_ for _ in ()).throw(ContractError()))
    if mode=='duplicate':journal.ack(foundation_module('contracts').PreUpdateEvidence(json.dumps(checkpoint()).encode()))
    driver=foundation_module('prequential').PrequentialDriver(measured=2)
    try:
        result=driver.run(RunRequest('a'*32),worker)
        assert result.status==('INCOMPLETE' if mode in ('append','partial','flush','fsync','deadline') else 'FAILED'),result
        assert not driver.events
        assert persisted(path)==dict(transitions=0,visits=0,b4=0,b7=0,b6=0)
        assert len(journal._seen)<=1
    finally:worker.stop();journal.close()


@pytest.mark.parametrize('mode,q,b1,b4,b7',[
    ('q_before',0,0,0,0),('q_after',1,0,0,0),('b1_before',1,0,0,0),('b1_after',1,1,0,0),
    ('b4_before',1,1,0,0),('b4_after',1,1,1,0),('b7_before',1,1,1,0),('b7_after',1,1,1,1),
    ('swallowed_b7',1,1,1,0),('capture_after_commit',1,1,1,1)])
def test_post_ack_failure_preserves_actual_prefix(tmp_path,foundation_module,monkeypatch,mode,q,b1,b4,b7):
    from development.evaluation.contracts import RunRequest
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch,mode)
    driver=foundation_module('prequential').PrequentialDriver(measured=3)
    try:
        result=driver.run(RunRequest('a'*32),worker)
        assert result.status=='INCOMPLETE',result
        assert len(driver.events)==1 and len(journal.path.read_bytes().splitlines())==1
        assert persisted(path)==dict(transitions=b1,visits=q,b4=b4,b7=b7,b6=0)
        updates=json.loads(driver.events[0].body)['updates']
        for name,confirmed in (('q',q),('b1',b1),('b4',b4),('b7',b7)):
            assert updates[name]['status']==('confirmed' if confirmed else 'unconfirmed'),updates
        if mode=='swallowed_b7':assert updates['b7'].get('producer_return')=='failed'
    finally:worker.stop();journal.close()


@pytest.mark.parametrize('stage',['aggregation','index','publication'])
def test_external_post_ack_failure_never_relearns(tmp_path,foundation_module,monkeypatch,stage):
    from development.evaluation.contracts import RunRequest
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch)
    driver=foundation_module('prequential').PrequentialDriver(measured=3)
    capture=driver.capture_completed
    def failure(*args):
        capture(*args)
        raise OSError('test-only '+stage+' failure after actual commit')
    driver.capture_completed=failure
    try:
        assert driver.run(RunRequest('a'*32),worker).status=='INCOMPLETE'
        assert len(driver.events)==1 and len(journal.path.read_bytes().splitlines())==1
        assert persisted(path)==dict(transitions=1,visits=1,b4=1,b7=1,b6=0)
    finally:worker.stop();journal.close()


def test_maintenance_commit_failure_preserves_all_acknowledged_cycles(tmp_path,foundation_module,monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch,'maintenance_after')
    driver=foundation_module('prequential').PrequentialDriver(measured=9,maintenance=True)
    try:
        assert driver.run(RunRequest('a'*32),worker).status=='INCOMPLETE'
        assert len(driver.events)==8 and len(journal.path.read_bytes().splitlines())==8
        assert len(driver.maintenance)==1 and driver.maintenance[0]['run_id']==1
        assert persisted(path)==dict(transitions=8,visits=8,b4=8,b7=1,b6=1)
    finally:worker.stop();journal.close()


def test_swallowed_maintenance_failure_is_incomplete(tmp_path,foundation_module,monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch,'maintenance_swallowed')
    driver=foundation_module('prequential').PrequentialDriver(measured=9,maintenance=True)
    try:
        assert driver.run(RunRequest('a'*32),worker).status=='INCOMPLETE'
        assert len(driver.events)==8 and len(driver.maintenance)==1
        assert driver.maintenance[0]['status']=='failed'
        assert persisted(path)==dict(transitions=8,visits=8,b4=8,b7=1,b6=1)
    finally:worker.stop();journal.close()


def test_failed_checkpoint_retains_attempt_and_prior_consolidation(tmp_path,foundation_module,monkeypatch):
    from development.evaluation.contracts import RunRequest
    worker,journal,path=harness(tmp_path,foundation_module,monkeypatch,'prior_consolidate')
    original=journal._file
    class FlushFailure:
        def flush(self):raise OSError('injected flush')
        def __getattr__(self,name):return getattr(original,name)
    journal._file=FlushFailure()
    driver=foundation_module('prequential').PrequentialDriver(measured=2)
    try:
        result=driver.run(RunRequest('a'*32),worker)
        assert result.status=='INCOMPLETE' and result.reason=='STORAGE_INTERRUPTED'
        assert not driver.events and not driver.skipped
        assert len(driver.failures)==1
        failure=json.loads(driver.failures[0])
        assert failure['key']==['measured','default',1,'pre'] and failure['attempt']==1
        assert failure['execution']=='INCOMPLETE' and failure['acked'] is False
        capture=json.loads(driver.failure_capture)['capture']
        assert capture['prior_action_effects']['consolidation_runs'][0]['id']==1
        assert capture['events'][-1]=='checkpoint'
        assert persisted(path)==dict(transitions=0,visits=0,b4=0,b7=0,b6=1)
        assert len(driver.failures[0])<=512 and len(driver.failure_capture)<=65536
    finally:worker.stop();journal.close()
