import sqlite3
import pytest


def test_transaction_proxy_parity(foundation_module, tmp_path):
    tmp_path = tmp_path / 'run' / 'learner'
    tmp_path.mkdir(parents=True)
    a = foundation_module('db_adapter')
    raw = sqlite3.connect(tmp_path/'memory.sqlite3')
    db = a.ConnectionProxy(raw, a.GrowthMonitor(tmp_path))
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE t(id INTEGER PRIMARY KEY, value TEXT)')
    with db:
        db.execute('INSERT INTO t VALUES(1,?)',('first',))
    assert db.execute('SELECT * FROM t').fetchone()['value'] == 'first'
    with pytest.raises(RuntimeError):
        with db:
            db.cursor().execute('INSERT INTO t VALUES(2,?)',('rollback',))
            raise RuntimeError('fixture')
    assert db.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 1
    db.execute('INSERT INTO t VALUES(3,?)',('pending',))
    assert db.in_transaction
    db.executescript("INSERT INTO t VALUES(4,'script'); INSERT INTO t VALUES(5,'script');")
    assert not db.in_transaction
    assert db.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 4
    db.set_progress_handler(lambda: 1,1)
    with pytest.raises(sqlite3.OperationalError):
        db.execute('SELECT * FROM t').fetchall()
    db.set_progress_handler(None,0)
    assert db.cursor().connection is db
    db.close()


@pytest.mark.parametrize('path', ['commit','context','sql','script','cursor','autocommit'])
def test_every_commit_enforces_growth(foundation_module, tmp_path, path):
    tmp_path = tmp_path / 'run' / 'learner'
    tmp_path.mkdir(parents=True)
    a = foundation_module('db_adapter')
    raw = sqlite3.connect(tmp_path/'memory.sqlite3')
    monitor = a.GrowthMonitor(tmp_path, physical_limit=8192, workspace_limit=16384)
    db = a.ConnectionProxy(raw, monitor)
    db.execute('CREATE TABLE t(value BLOB)')
    assert db.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 0
    sql = 'INSERT INTO t VALUES(zeroblob(12000))'
    with pytest.raises(a.LimitReached):
        if path == 'context':
            with db: db.execute(sql)
        elif path == 'script':
            db.executescript(sql+'; INSERT INTO t VALUES(NULL);')
        elif path == 'cursor':
            db.cursor().execute(sql)
            db.cursor().execute('COMMIT')
        elif path == 'autocommit':
            db.isolation_level = None
            db.execute(sql)
        else:
            db.execute(sql)
            db.execute('COMMIT') if path == 'sql' else db.commit()
    assert monitor.stopped
    # Committed transaction remains; a swallowed limit error cannot permit a new writer.
    assert db.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 1
    for call in (lambda: db.execute('INSERT INTO t VALUES(NULL)'), lambda: db.cursor().execute(sql),
                 lambda: db.executescript('CREATE TABLE bypass(x);'), lambda: db.execute('PRAGMA user_version=99')):
        with pytest.raises(a.LimitReached): call()
    db.close()


def test_logical_page_cap(foundation_module, tmp_path):
    tmp_path = tmp_path / 'run' / 'learner'
    tmp_path.mkdir(parents=True)
    a = foundation_module('db_adapter')
    raw = sqlite3.connect(tmp_path/'memory.sqlite3')
    db = a.ConnectionProxy(raw, a.GrowthMonitor(tmp_path))
    db.execute('CREATE TABLE t(value BLOB)')
    with db: db.execute("INSERT INTO t VALUES('retained')")
    with pytest.raises(a.LimitReached):
        with db: db.execute('INSERT INTO t VALUES(zeroblob(?))',(32*1024**2+1,))
    assert db.execute('SELECT value FROM t').fetchone()[0] == 'retained'
    assert db.execute('PRAGMA page_count').fetchone()[0] * db.execute('PRAGMA page_size').fetchone()[0] <= 32*1024**2
    db.close()


def test_literal_physical_wal_cap_and_workspace(foundation_module, tmp_path):
    a = foundation_module('db_adapter')
    home = tmp_path / 'run' / 'learner'
    home.mkdir(parents=True)
    db = a.ConnectionProxy(sqlite3.connect(home/'memory.sqlite3'),a.GrowthMonitor(home))
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA wal_autocheckpoint=0')
    db.execute('CREATE TABLE t(value BLOB)')
    with db: db.execute('INSERT INTO t VALUES(zeroblob(1048576))')
    with pytest.raises(a.LimitReached):
        for i in range(80):
            with db: db.execute('UPDATE t SET value=?',(bytes([65+i%2])*1048576,))
    physical=sum(p.stat().st_size for p in home.iterdir() if p.name.startswith('memory.sqlite3'))
    assert 64*1024**2 < physical <= (64+36)*1024**2
    assert not db.monitor.overshoot_exceeded
    db.close()
    # Separate workspace crossing charges the second clone and stops immediately.
    other=tmp_path/'other'/'learner'; other.mkdir(parents=True)
    clone=other.parent/'clone'; clone.mkdir()
    with (clone/'memory.sqlite3').open('wb') as f: f.truncate(128*1024**2)
    monitor=a.GrowthMonitor(other)
    db=a.ConnectionProxy(sqlite3.connect(other/'memory.sqlite3'),monitor)
    with pytest.raises(a.LimitReached): db.execute('CREATE TABLE t(x)')
    assert monitor.stopped and not monitor.overshoot_exceeded
    db.close()
