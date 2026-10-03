"""R4: run terminal state survives sibling monitors and spawn admission."""
import multiprocessing
import sqlite3
import pytest


def _terminal_probe(pipe, home):
    from development.evaluation.db_adapter import GrowthMonitor
    pipe.send(GrowthMonitor(home).stopped)
    pipe.close()


def test_sibling_latch_blocks_write_before_commit(foundation_module, tmp_path):
    a=foundation_module('db_adapter')
    home=tmp_path/'run'/'learner'; home.mkdir(parents=True)
    sibling=home.parent/'clone'; sibling.mkdir()
    first=a.GrowthMonitor(home,workspace_limit=16384)
    second=a.GrowthMonitor(sibling)
    db=a.ConnectionProxy(sqlite3.connect(sibling/'memory.sqlite3'),second)
    db.execute('CREATE TABLE t(x)')
    (home/'memory.sqlite3').write_bytes(bytes(16384))
    with sqlite3.connect(':memory:') as fixture:
        with pytest.raises(a.LimitReached): first.check(fixture)
    try:
        with pytest.raises(a.LimitReached):
            db.execute('INSERT INTO t VALUES(1)')
        assert db.execute('SELECT COUNT(*) FROM t').fetchone()[0]==0
        assert a.GrowthMonitor(sibling).stopped
        other=tmp_path/'unrelated'/'learner'; other.mkdir(parents=True)
        assert not a.GrowthMonitor(other).stopped
    finally: db.close()


def test_terminal_latch_survives_spawn(foundation_module,tmp_path):
    a=foundation_module('db_adapter')
    home=tmp_path/'run'/'learner'; home.mkdir(parents=True)
    a.GrowthMonitor(home).stopped=True
    ctx=multiprocessing.get_context('spawn'); parent,child=ctx.Pipe()
    process=ctx.Process(target=_terminal_probe,args=(child,home))
    process.start(); child.close()
    try:
        assert parent.poll(5)
        assert parent.recv() is True
    finally: process.join(5); parent.close()


def test_terminal_run_rejected_before_worker_launch(foundation_module,tmp_path,monkeypatch):
    from .test_workers import launch
    w=foundation_module('worker'); request=launch(foundation_module,tmp_path)
    foundation_module('db_adapter').GrowthMonitor(request.learner.home).stopped=True
    reached=[]
    monkeypatch.setattr(w.multiprocessing,'get_context',lambda *args: reached.append(True))
    with pytest.raises(ValueError): w.WorkerHandle.start(request)
    assert reached==[]
