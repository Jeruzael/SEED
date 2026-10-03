"""R2: delayed autocommit RETURNING finalization must charge actual growth."""
import sqlite3
import pytest


@pytest.mark.parametrize('finish', ['fetchone','fetchmany','fetchall','iteration','close','reuse'])
def test_returning_finalization_enforces_growth(foundation_module, tmp_path, finish):
    a = foundation_module('db_adapter')
    home = tmp_path/'run'/'learner'
    home.mkdir(parents=True)
    raw = sqlite3.connect(home/'memory.sqlite3', isolation_level=None)
    monitor = a.GrowthMonitor(home, physical_limit=8192)
    db = a.ConnectionProxy(raw, monitor)
    db.execute('CREATE TABLE t(x)')
    cursor = db.execute('INSERT INTO t VALUES(zeroblob(12000)) RETURNING length(x)')
    before = monitor.commits
    try:
        with pytest.raises(a.LimitReached):
            if finish=='fetchone':
                while cursor.fetchone() is not None: pass
            elif finish=='fetchmany':
                while cursor.fetchmany(1): pass
            elif finish=='fetchall': cursor.fetchall()
            elif finish=='iteration': list(cursor)
            elif finish=='reuse': cursor.execute('SELECT 1')
            else: cursor.close()
        assert monitor.commits>before and monitor.stopped
        with pytest.raises(a.LimitReached): db.execute('INSERT INTO t VALUES(NULL)')
    finally: db.close()


@pytest.mark.parametrize('finish', ['commit','context','isolation','script'])
def test_transaction_finalization_paths_still_guarded(foundation_module, tmp_path, finish):
    a=foundation_module('db_adapter')
    home=tmp_path/'run'/'learner'; home.mkdir(parents=True)
    db=a.ConnectionProxy(sqlite3.connect(home/'memory.sqlite3'),a.GrowthMonitor(home,physical_limit=8192))
    db.execute('CREATE TABLE t(x)')
    db.execute('INSERT INTO t VALUES(zeroblob(12000)) RETURNING x').fetchall()
    try:
        with pytest.raises(a.LimitReached):
            if finish=='context': db.__exit__(None,None,None)
            elif finish=='isolation': db.isolation_level=None
            elif finish=='script': db.executescript('SELECT 1;')
            else: db.commit()
        assert db.monitor.stopped
    finally: db.close()
