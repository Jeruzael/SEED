"""R9: explicit completed fixture launch preserves all durable producer state."""
from dataclasses import replace
import multiprocessing
import os
import sqlite3
import pytest
from contextlib import closing


def _make_fixture(pipe, cap, slot, invalid_schema=None):
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        session=install_worker_adapters(WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64))
        state=OwnedState.fresh(cap,{'epsilon':0}); state.close()
        from seed.organism import SeedOrganism
        core=SeedOrganism(cap.home); core.decisions.rng=session.learner_rng
        class PublicBody:
            def perceive(self): return dict(battery_pct=80,charging=True,load_ratio=.2,disk_free_pct=75,network=True,local_hour=12)
        core.body=PublicBody()
        for ordinal in range(1,13):
            session.clock.stage('measured',ordinal,0); assert core.cycle().status=='completed'
        core.consolidate(core.body.perceive(),provenance='owner_requested')
        state=OwnedState(cap,core.memory,state.monitor)
        clone=state.clone(slot)
        clone.memory.set_meta('fixture-marker',{'preserve':'exact'})
        if invalid_schema:
            # Deliberately construct an invalid technical fixture, bypassing FK
            # rejection so this test reaches the completion manifest boundary.
            clone.memory.db.execute('PRAGMA foreign_keys=OFF')
            sql='DROP TABLE world_beliefs' if invalid_schema in ('missing','malformed') else 'CREATE TABLE evaluator_truth(x)' if invalid_schema=='foreign_table' else "INSERT INTO annotations(episode_id,important,tags_json) VALUES(999999,0,'[]')"
            clone.memory.db.execute(sql)
            if invalid_schema=='malformed':
                clone.memory.db.execute('CREATE TABLE world_beliefs(private_truth TEXT)')
                clone.memory.db.execute("INSERT INTO world_beliefs VALUES('private sentinel')")
            clone.memory.db.commit()
            try: clone.complete_fixture()
            except ValueError: pipe.send(('rejected',None)); core.close(); return
            pipe.send(('accepted-invalid',None)); core.close(); return
        fixture=clone.complete_fixture()
        core.close()
        pipe.send(('ok',fixture))
    except BaseException as e:
        import traceback
        traceback.print_exc()
        pipe.send(('error',type(e).__name__))
    finally: pipe.close()


def make_fixture(foundation_module,tmp_path):
    s=foundation_module('state')
    assert hasattr(s.OwnedState,'complete_fixture'), 'completed owned fixture admission missing'
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('run',0); slot=root.assign_learner('run',1)
    ctx=multiprocessing.get_context('spawn'); parent,child=ctx.Pipe()
    worker=ctx.Process(target=_make_fixture,args=(child,cap,slot),name='seed-evaluation-worker')
    worker.start(); child.close()
    assert parent.poll(15)
    result=parent.recv(); worker.join(5); parent.close()
    assert result[0]=='ok',result
    return result[1]


def dump(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        return list(db.iterdump())


def _process_local_probe(pipe, request):
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.state import CompletedLearner
        session=install_worker_adapters(request)
        core=CompletedLearner(request.fixture,{'epsilon':0},session)
        try:
            core.memory.db.execute("INSERT INTO annotations(episode_id,important,tags_json) VALUES(999999,0,'[]')")
        except sqlite3.IntegrityError:
            core.memory.db.rollback()
        else:
            raise AssertionError('completed launch disabled producer foreign-key enforcement')
        assert core.decisions.rng is session.learner_rng
        assert core.learner.memory is core.memory and core.world_model.memory is core.memory
        assert core.self_model.memory is core.memory and core.consolidator.memory is core.memory
        pipe.send(('ok',os.getpid(),core.decisions.rng.random(),session.uuids.next_hex('producer')))
        core.close()
    except BaseException as e: pipe.send(('error',type(e).__name__))
    finally: pipe.close()


def test_completed_clone_spawns_without_reinitializing(foundation_module,tmp_path,monkeypatch):
    fixture=make_fixture(foundation_module,tmp_path)
    c=foundation_module('contracts'); w=foundation_module('worker')
    path=fixture.learner.home/'memory.sqlite3'; before=path.read_bytes(); tables=dump(path)
    request=c.WorkerLaunch(fixture.learner,b'{"epsilon":0}',91,'b'*64,launch_mode='COMPLETED_OWNED_FIXTURE',fixture=fixture)
    monkeypatch.setenv('SEED_HOME',str(tmp_path/'installed'))
    worker=w.WorkerHandle.start(request)
    try:
        assert worker.ready['schema']==7
        assert worker.request({'operation':'action_catalog'})['actions'][0]=='observe'
        assert dump(path)==tables
    finally: worker.stop('OWNER_CANCELLED')
    assert path.read_bytes()==before
    assert dump(path)==tables
    assert not (tmp_path/'installed').exists()


@pytest.mark.parametrize('invalid',['missing','foreign','changed','fresh_existing'])
def test_incomplete_foreign_changed_fixture_rejected(foundation_module,tmp_path,invalid):
    fixture=make_fixture(foundation_module,tmp_path)
    c=foundation_module('contracts'); w=foundation_module('worker')
    request=c.WorkerLaunch(fixture.learner,b'{"epsilon":0}',3,'a'*64,launch_mode='COMPLETED_OWNED_FIXTURE',fixture=fixture)
    if invalid=='missing': request=replace(request,fixture=None)
    elif invalid=='foreign':
        root=foundation_module('paths').EvaluationRoot.create(fixture.learner.home.parents[3]); other=root.assign_learner('foreign',0); request=replace(request,learner=other)
    elif invalid=='fresh_existing': request=replace(request,launch_mode='FRESH',fixture=None)
    else:
        with sqlite3.connect(fixture.learner.home/'memory.sqlite3') as db: db.execute('UPDATE seed_schema SET version=8')
    with pytest.raises(ValueError): w.WorkerHandle.start(request)


def test_completed_launch_has_fresh_process_objects_and_streams(foundation_module,tmp_path):
    fixture=make_fixture(foundation_module,tmp_path)
    c=foundation_module('contracts')
    request=c.WorkerLaunch(fixture.learner,b'{"epsilon":0}',91,'b'*64,launch_mode='COMPLETED_OWNED_FIXTURE',fixture=fixture)
    ctx=multiprocessing.get_context('spawn'); results=[]
    for _ in range(2):
        parent,child=ctx.Pipe(); worker=ctx.Process(target=_process_local_probe,args=(child,request),name='seed-evaluation-worker')
        worker.start(); child.close(); assert parent.poll(10)
        results.append(parent.recv()); worker.join(5); parent.close()
    assert all(result[0]=='ok' for result in results),results
    assert results[0][1]!=results[1][1]
    # First MT19937 draw for seed 91, independently derived.
    assert results[0][2]==results[1][2]==0.08352052115358566
    assert results[0][3]==results[1][3]


@pytest.mark.parametrize('invalid',['missing','foreign_table','malformed','orphan'])
def test_incomplete_v7_table_manifest_cannot_be_completed(foundation_module,tmp_path,invalid):
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('run',0); slot=root.assign_learner('run',1)
    ctx=multiprocessing.get_context('spawn'); parent,child=ctx.Pipe()
    worker=ctx.Process(target=_make_fixture,args=(child,cap,slot,invalid),name='seed-evaluation-worker')
    worker.start(); child.close(); assert parent.poll(15)
    result=parent.recv(); worker.join(5); parent.close()
    assert result[0]=='rejected',result
