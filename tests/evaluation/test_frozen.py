"""I11: held-out selection cannot write even operational state."""
import json
import multiprocessing
import pytest
from .test_completed_fixture import make_fixture, dump
from .test_prediction_boundary import checkpoint


def _frozen_child(pipe, launch, operation):
    frozen=None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.frozen import FrozenWorker
        streams=install_worker_adapters(launch)
        if operation=='probes':
            # Mutable producers must never run in the frozen path, even when
            # they could return without touching storage.
            from seed.world_model import WorldModel
            from seed.self_model import SelfModel
            from seed.organism import SeedOrganism
            def forbidden(*args,**kwargs):raise AssertionError('mutable producer in frozen worker')
            WorldModel.recover=SelfModel.update=SeedOrganism.__init__=forbidden
        frozen=FrozenWorker(launch.fixture,streams)
        before=frozen.raw_state()
        if operation=='probes':
            class Client:
                def observation(self,phase,ordinal,subcase='default'):return checkpoint()['state_before']
                def apply(self,action,ordinal):return checkpoint()['state_after']
            # Every held-out observation uses fixed stored history, not online rows.
            records=[]
            for ordinal in range(1,4):
                result=frozen.probe(checkpoint()['state_before'],('probe','default',ordinal,'pre'),Client())
                records.append(json.loads(result.body))
                assert frozen.raw_state()==before
            pipe.send(('ok',records,before==frozen.raw_state()))
        else:
            try:
                if operation=='publication':
                    from seed.self_model import SelfModel
                    import threading
                    SelfModel(frozen.memory,clock=streams.clock.wall).update(13,'a'*32,threading.Event())
                    frozen.assert_unchanged()
                else:frozen.memory.db.execute(operation)
            except (ValueError,RuntimeError,__import__('sqlite3').DatabaseError):
                pipe.send(('denied',before==frozen.raw_state(),frozen.failed))
            else:pipe.send(('allowed',operation))
    except BaseException:
        import traceback;traceback.print_exc();pipe.send(('error',None))
    finally:
        if frozen:frozen.close()
        pipe.close()


def probe(tmp_path,foundation_module,operation,*,count=12,selected_action=None):
    foundation_module('frozen')
    fixture=make_fixture(foundation_module,tmp_path,count=count,selected_action=selected_action)
    from development.evaluation.contracts import WorkerLaunch
    launch=WorkerLaunch(fixture.learner,b'{"epsilon":0}',3,'a'*64,training_count=count,
        protocol='FROZEN_SELECTION_ASSAY',launch_mode='COMPLETED_OWNED_FIXTURE',fixture=fixture)
    path=fixture.learner.home/'memory.sqlite3';before=path.read_bytes();raw=dump(path)
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe()
    worker=ctx.Process(target=_frozen_child,args=(child,launch,operation),name='seed-evaluation-worker')
    worker.start();child.close()
    try:
        assert parent.poll(15);result=parent.recv();worker.join(5)
        assert result[0]!='error',result
        assert path.read_bytes()==before and dump(path)==raw
        return result
    finally:
        if worker.is_alive():worker.terminate();worker.join(5)
        parent.close()


def test_all_frozen_tables_and_db_bytes_equal(tmp_path,foundation_module):
    result=probe(tmp_path,foundation_module,'probes',count=200)
    assert result[0]=='ok' and result[2]
    for record in result[1]:
        assert record['driver']=='frozen_projection_v1'
        assert record['assay_kind']=='FROZEN_SELECTION_ASSAY'
        assert record['internal_action_effects']=='suppressed_by_protocol'
        assert record['selection']['history']['cutoff_transition_id']==200
        assert record['selection']['history']['raw_rows_examined']==200


@pytest.mark.parametrize('action',['reflect','consolidate'])
def test_reflect_consolidate_are_assays(tmp_path,foundation_module,action):
    result=probe(tmp_path,foundation_module,'probes',selected_action=action)
    assert all(r['selection']['selected_action']==action for r in result[1])
    assert all(r['internal_action_effects']=='suppressed_by_protocol' for r in result[1])


def test_freeze_worker_prepares_owned_checkpoint_before_read_worker(tmp_path,foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('c'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'c'*32)
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64,training_count=1),
        channel=ChannelRouter(Scenario(),journal=journal))
    try:
        assert worker.request({'operation':'cycle','key':['training','default',1,'pre']})['status']=='completed'
        assert hasattr(worker,'freeze'),'owned freeze preparation transport missing'
        fixture=worker.freeze()
        assert fixture.validate() is fixture
        assert (cap.home/'checkpoint.sqlite3').is_file()
    finally:worker.stop();journal.close()


def test_incomplete_training_cannot_be_frozen(tmp_path,foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('unfinished',0)
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64,training_count=1))
    try:
        with pytest.raises(ValueError):worker.freeze()
        assert not (cap.home/'checkpoint.sqlite3').exists()
    finally:worker.stop()


@pytest.mark.parametrize('operation',[
    "INSERT INTO meta VALUES('heldout','1')", "UPDATE q_values SET value=99",'DELETE FROM episodes',
    'CREATE TABLE private_truth(x)', 'DROP TABLE transitions', 'PRAGMA user_version=1',
    'PRAGMA journal_mode=DELETE', 'PRAGMA query_only=OFF','publication'])
def test_frozen_write_attempt_is_failed_not_repaired(tmp_path,foundation_module,operation):
    result=probe(tmp_path,foundation_module,operation)
    assert result==('denied',True,True)


def test_frozen_worker_handle_never_constructs_mutable_organism(tmp_path,foundation_module):
    foundation_module('frozen')
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    fixture=make_fixture(foundation_module,tmp_path)
    path=fixture.learner.home/'memory.sqlite3';before=path.read_bytes()
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    launch=WorkerLaunch(fixture.learner,b'{"epsilon":0}',3,'a'*64,training_count=12,
        protocol='FROZEN_SELECTION_ASSAY',launch_mode='COMPLETED_OWNED_FIXTURE',fixture=fixture)
    worker=foundation_module('worker').WorkerHandle.start(launch,channel=ChannelRouter(Scenario()))
    try:
        result=worker.request({'operation':'probe','key':['probe','default',1,'pre']})
        assert result['assay_kind']=='FROZEN_SELECTION_ASSAY'
    finally:worker.stop()
    assert path.read_bytes()==before


def _freeze_guard_child(pipe,launch,mode):
    state=None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.state import OwnedState
        from development.evaluation.frozen import freeze_state
        install_worker_adapters(launch)
        state=OwnedState.fresh(launch.learner,{'epsilon':0})
        if mode=='pending_command':
            with state.memory.db:state.memory.db.execute("INSERT INTO commands VALUES('fixture','reflect','session',1,2,'pending',NULL)")
        elif mode=='transaction':state.memory.db.execute('BEGIN')
        elif mode=='b4_no_progress':
            state.close()
            from seed.organism import SeedOrganism
            core=SeedOrganism(launch.learner.home)
            class Body:
                def perceive(self):return checkpoint()['state_before']
            core.body=Body();core.cycle()
            state.close()
            state=OwnedState(launch.learner,core.memory,core.memory.db.monitor)
            with state.memory.db:
                state.memory.db.execute('DELETE FROM world_model_processed')
                state.memory.db.execute('INSERT INTO world_model_queue VALUES(1)')
            from seed.world_model import WorldModel
            WorldModel.recover=lambda self:0
        try:freeze_state(state)
        except ValueError:pipe.send(('rejected',not (launch.learner.home/'checkpoint.sqlite3').exists()))
        else:pipe.send(('incorrectly_accepted',))
    except BaseException:
        import traceback;traceback.print_exc();pipe.send(('error',))
    finally:
        if state:state.close()
        pipe.close()


@pytest.mark.parametrize('mode',['pending_command','transaction','b4_no_progress'])
def test_freeze_rejects_pending_or_incomplete_work(tmp_path,foundation_module,mode):
    from development.evaluation.contracts import WorkerLaunch
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve());cap=root.assign_learner('guard',0)
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe()
    worker=ctx.Process(target=_freeze_guard_child,args=(child,WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64),mode),name='seed-evaluation-worker')
    worker.start();child.close()
    try:
        assert parent.poll(15);result=parent.recv();worker.join(5)
        assert result==('rejected',True),result
    finally:
        if worker.is_alive():worker.terminate();worker.join(5)
        parent.close()
