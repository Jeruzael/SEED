from dataclasses import replace
import time
import pytest


def launch(foundation_module, tmp_path, run='run'):
    c = foundation_module('contracts')
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner(run,0)
    return c.WorkerLaunch(cap,b'{"epsilon":0}',3,'a'*64)


def test_repeated_workers_are_independent(foundation_module, tmp_path):
    w = foundation_module('worker')
    a = launch(foundation_module,tmp_path,'first')
    b = launch(foundation_module,tmp_path,'second')
    first = w.WorkerHandle.start(a)
    try:
        assert first.ready['schema'] == 7
        assert first.request({'operation':'action_catalog'}) == {'actions':['observe','reflect','consolidate','rest']}
    finally: first.stop('OWNER_CANCELLED')
    second = w.WorkerHandle.start(b)
    try:
        assert second.ready['schema'] == 7
        assert second.request({'operation':'action_catalog'}) == {'actions':['observe','reflect','consolidate','rest']}
    finally: second.stop('OWNER_CANCELLED')
    import sqlite3
    with sqlite3.connect(a.learner.home/'memory.sqlite3') as da, sqlite3.connect(b.learner.home/'memory.sqlite3') as db:
        assert da.execute("SELECT value FROM meta WHERE key='identity'").fetchone() == db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
        assert da.execute('SELECT COUNT(*) FROM transitions').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0] == 0


def test_worker_timeout_and_cleanup(foundation_module, tmp_path):
    w = foundation_module('worker')
    worker = w.WorkerHandle.start(launch(foundation_module,tmp_path),run_seconds=.8,cleanup_seconds=.1)
    pid = worker.process.pid
    time.sleep(.9)
    with pytest.raises(w.WorkerError):
        worker.request({'operation':'action_catalog'})
    result = worker.stop('LIMIT_REACHED')
    assert result.status == 'INCOMPLETE'
    assert not worker.process.is_alive() and worker.process.pid == pid
    coordinator = foundation_module('coordinator').Coordinator
    with pytest.raises(ValueError): coordinator(suite_seconds=1801)


def test_one_worker_and_two_clone_slots(foundation_module, tmp_path):
    w = foundation_module('worker')
    a = launch(foundation_module,tmp_path,'one')
    b = launch(foundation_module,tmp_path,'two')
    worker = w.WorkerHandle.start(a)
    try:
        with pytest.raises(w.WorkerError): w.WorkerHandle.start(b)
        with pytest.raises(w.WorkerError): worker.request({'operation':'run'})
        with pytest.raises(w.WorkerError): worker.request({'operation':'cycle'})
    finally: worker.stop('OWNER_CANCELLED')


def test_invalid_launch_never_constructs(foundation_module, tmp_path, monkeypatch):
    w = foundation_module('worker')
    valid = launch(foundation_module,tmp_path)
    monkeypatch.setenv('SEED_HOME',str(tmp_path/'installed'))
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','SECRET_SENTINEL')
    for bad in [None, replace(valid,settings=b'{"truth":"SECRET_SENTINEL"}'),replace(valid,rng_seed=-1),
                replace(valid,uuid_identity='SECRET_SENTINEL')]:
        with pytest.raises(ValueError): w.WorkerHandle.start(bad)
    assert not (valid.learner.home/'memory.sqlite3').exists()
    worker=w.WorkerHandle.start(valid)
    try:
        assert 'SECRET_SENTINEL' not in str(worker.ready)
    finally: worker.stop('OWNER_CANCELLED')
    assert not (tmp_path/'installed').exists()


def test_idle_worker_deadline_is_enforced(foundation_module, tmp_path):
    w = foundation_module('worker')
    worker=w.WorkerHandle.start(launch(foundation_module,tmp_path),run_seconds=.8,cleanup_seconds=.1)
    time.sleep(1.1)
    assert not worker.process.is_alive()
    assert worker.stop('LIMIT_REACHED').reason == 'LIMIT_REACHED'
