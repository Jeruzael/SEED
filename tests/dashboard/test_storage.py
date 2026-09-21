import sqlite3
import threading
import pytest
from seed.backup import create_backup
from dashboard.services.backups import BackupStore
from seed.memory import Memory

def test_backup_consistent_and_retention_safe(home):
    m=Memory(home/'memory.sqlite3');m.episode('experience',{},action='observe');m.close()
    store=BackupStore(home)
    first=store.create()
    path=home/'backups'/first['name']
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT count(*) FROM episodes').fetchone()[0]==1
    unrelated=home/'backups'/'my-own.sqlite3';unrelated.write_bytes(b'keep')
    store.create();store.prune(1)
    assert unrelated.read_bytes()==b'keep'
    assert len(list((home/'backups').glob('memory-*.sqlite3')))==1

def test_backup_while_writing(home):
    done=threading.Event()
    def write():
        with sqlite3.connect(home/'memory.sqlite3') as db:
            for i in range(50):
                db.execute('INSERT INTO episodes(ts,event,state_json) VALUES(?,?,?)',(i,'experience','{}'));db.commit()
        done.set()
    thread=threading.Thread(target=write);thread.start()
    result=create_backup(home)
    thread.join(5)
    assert done.is_set()
    with sqlite3.connect(home/'backups'/result['name']) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_backup_symlink_rejected(home,tmp_path):
    outside=tmp_path/'outside';outside.mkdir()
    (home/'backups').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError): create_backup(home)
    assert list(outside.iterdir())==[]

def test_legacy_upgrade_backed_up_before_schema(legacy_home):
    m=Memory(legacy_home/'memory.sqlite3');m.close()
    files=list((legacy_home/'backups').glob('memory-*.sqlite3'))
    assert len(files)==1
    with sqlite3.connect(files[0]) as db:
        assert db.execute('SELECT count(*) FROM episodes').fetchone()[0]==1
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone()

def test_failed_backup_does_not_migrate(legacy_home,monkeypatch):
    def fail(home): raise OSError('disk full')
    monkeypatch.setattr('seed.backup.create_backup',fail)
    with pytest.raises(OSError): Memory(legacy_home/'memory.sqlite3')
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='seed_schema'").fetchone()

def test_logs_rotate_and_reject_symlink(home,tmp_path):
    from seed.logging_setup import configure_logging
    logger=configure_logging(home,'seed',128,2)
    for i in range(50): logger.info('record %s %s',i,'x'*80)
    for h in list(logger.handlers): h.close();logger.removeHandler(h)
    assert len(list(home.glob('seed.log*')))<=3
    outside=tmp_path/'outside-log';outside.write_text('untouched')
    (home/'bad.log').symlink_to(outside)
    with pytest.raises(ValueError):configure_logging(home,'bad',128,2)
    assert outside.read_text()=='untouched'
