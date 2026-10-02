import json
import multiprocessing
import sqlite3
import pytest


def _state_probe(pipe, first, second):
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        session = install_worker_adapters(WorkerLaunch(first,b'{"epsilon":0}',3,'a'*64))
        from development.evaluation.state import OwnedState
        state = OwnedState.fresh(first, {'epsilon':0})
        state.close()
        # Technical producer fixture only: original cycles populate actual B1–B8.
        from seed.organism import SeedOrganism
        core = SeedOrganism(first.home)
        core.decisions.rng = session.learner_rng
        class PublicBody:
            def perceive(self):
                return dict(battery_pct=80,charging=True,load_ratio=.2,disk_free_pct=75,network=True,local_hour=12)
        core.body = PublicBody()
        for ordinal in range(1,13):
            session.clock.stage('measured',ordinal,0)
            assert core.cycle().status == 'completed'
        core.consolidate(core.body.perceive(),provenance='owner_requested')
        state = OwnedState(first,core.memory,state.monitor)
        state.memory.set_meta('semantic_cursor',123)
        before = state.raw_tables()
        snapshot = state.checkpoint()
        clone = state.clone(second)
        assert clone.raw_tables() == before
        clone.memory.set_meta('independent','clone')
        assert state.memory.get_meta('independent') is None
        assert state.raw_tables()['seed_schema'] == [[7]]
        assert 'sqlite_sequence' in before and 'decision_records' in before and 'transitions' in before
        assert before['transitions'] and before['decision_records'] and before['q_values']
        assert before['self_model_current'] and before['consolidation_runs']
        assert not any('evaluation' in n for n in before)
        clone.close()
        core.close()
        pipe.send({'ok':True,'tables':len(before),'checkpoint':snapshot.name})
    except BaseException as e:
        pipe.send({'ok':False,'error':type(e).__name__})
    finally: pipe.close()


def test_clone_preserves_all_tables(foundation_module, tmp_path):
    foundation_module('state')
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    first, second = root.assign_learner('run',0), root.assign_learner('run',1)
    ctx=multiprocessing.get_context('spawn')
    parent,child=ctx.Pipe()
    worker=ctx.Process(target=_state_probe,args=(child,first,second),name='seed-evaluation-worker')
    worker.start(); child.close()
    assert parent.poll(15)
    result=parent.recv(); worker.join(5)
    assert result['ok'],result
    assert result['tables'] > 20 and result['checkpoint'] == 'checkpoint.sqlite3'
    with sqlite3.connect(first.home/'checkpoint.sqlite3') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_foreign_or_installed_clone_rejected(foundation_module, tmp_path, monkeypatch):
    s = foundation_module('state')
    p = foundation_module('paths')
    monkeypatch.setenv('SEED_HOME',str(tmp_path/'installed'))
    with pytest.raises(ValueError):
        s.OwnedState.fresh(p.LearnerCapability(tmp_path/'installed','forged',(0,0)),{})
    assert not (tmp_path/'installed').exists()
