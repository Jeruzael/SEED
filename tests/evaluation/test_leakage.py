import json
from pathlib import Path
import sqlite3
import pytest
from .test_workers import launch
from .test_channel import router


def test_truth_absent_in_all_learner_state(foundation_module, tmp_path, monkeypatch):
    w=foundation_module('worker')
    r=router(foundation_module,b'PRIVATE_TRUTH_SENTINEL|PLAN_REPORT_FINDING_SENTINEL')
    l=launch(foundation_module,tmp_path)
    monkeypatch.setenv('SEED_HOME','INSTALLED_HOME_SENTINEL')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','SECRET_ENV_SENTINEL')
    worker=w.WorkerHandle.start(l,channel=r)
    try:
        before=worker.request({'operation':'observation','key':['measured','default',1,'pre']})
        assert before == {'load_ratio':.2,'network':True}
        after=worker.request({'operation':'apply','key':['measured','default',1,'action'],'action':'observe'})
        assert after == {'load_ratio':.3,'network':False}
        with pytest.raises(ValueError): worker.request({'operation':'truth'})
    finally: worker.stop('OWNER_CANCELLED')
    forbidden=[b'PRIVATE_TRUTH_SENTINEL',b'PLAN_REPORT_FINDING_SENTINEL',b'SECRET_ENV_SENTINEL',b'INSTALLED_HOME_SENTINEL']
    for path in l.learner.home.iterdir():
        if path.is_file():
            data=path.read_bytes()
            assert all(x not in data for x in forbidden),path.name
    with sqlite3.connect(l.learner.home/'memory.sqlite3') as db:
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for name in tables:
            values=db.execute('SELECT * FROM "'+name.replace('"','""')+'"').fetchall()
            data=repr(values).encode()
            assert all(x not in data for x in forbidden),name
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 7


def test_exception_values_do_not_cross_boundary(foundation_module, tmp_path):
    w=foundation_module('worker')
    r=router(foundation_module)
    worker=w.WorkerHandle.start(launch(foundation_module,tmp_path),channel=r)
    try:
        with pytest.raises(ValueError) as exc:
            worker.request({'operation':'observation','key':['measured','default',999,'pre']})
        assert 'PRIVATE_TRUTH_SENTINEL' not in str(exc.value)
        assert str(exc.value) == 'INVALID_CONTRACT'
    finally: worker.stop('OWNER_CANCELLED')
