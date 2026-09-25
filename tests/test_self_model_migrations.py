"""B7 upgrade guarantees on temporary stores, never installed memory."""
import sqlite3
import pytest
from seed import migrations
from seed.memory import Memory
from seed.backup import read_manifest
from tests.test_transition_migrations import v1_home
from tests.test_world_migrations import v2_home
from tests.test_curiosity_migrations import v3_home, snapshot
from tests.test_semantic_migrations import v4_home


@pytest.fixture
def v5_home(v4_home):
    with sqlite3.connect(v4_home/'memory.sqlite3') as db:
        for sql in migrations.V5_STATEMENTS: db.execute(sql)
        db.execute('UPDATE seed_schema SET version=5')
        db.execute("INSERT INTO consolidation_runs(id,started_at,model,model_version,provenance,status,result_json) VALUES(1,10,'semantic_v1',1,'owner_requested','running','{}')")
    return v4_home


def test_upgrade_preserves_rows_backup_and_empty_snapshot(v5_home):
    path=v5_home/'memory.sqlite3'
    with sqlite3.connect(path) as db: before=snapshot(db)
    m=Memory(path)
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0]==6
        assert m.db.execute('SELECT * FROM self_model_current').fetchall()==[]
        assert {t:[tuple(r) for r in m.db.execute(f'SELECT * FROM {t}')] for t in before}==before
    finally:m.close()
    backups=read_manifest(v5_home)
    assert len(backups)==1
    with sqlite3.connect(v5_home/'backups'/backups[0]['name']) as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==5
        assert snapshot(db)==before
    Memory(path).close()
    assert read_manifest(v5_home)==backups


@pytest.mark.parametrize('version',range(6))
def test_final_step_failure_rolls_back_every_prior_version(legacy_home,version,monkeypatch):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        if version:
            for sql in migrations.STATEMENTS:db.execute(sql)
            db.execute('INSERT INTO seed_schema VALUES(?)',(version,))
        for v in range(2,version+1):
            for sql in getattr(migrations,f'V{v}_STATEMENTS'):db.execute(sql)
        db.commit()
        before=list(db.iterdump())
        monkeypatch.setattr(migrations,'V6_STATEMENTS',getattr(migrations,'V6_STATEMENTS',[])+['INVALID SQL'],raising=False)
        with pytest.raises(sqlite3.Error):migrations.migrate(db)
        assert list(db.iterdump())==before


def test_fresh_database_has_no_invented_snapshot(tmp_path):
    m=Memory(tmp_path/'fresh'/'memory.sqlite3')
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0]==6
        assert m.db.execute('SELECT count(*) FROM self_model_current').fetchone()[0]==0
    finally:m.close()


def test_failed_backup_leaves_v5_intact(v5_home,monkeypatch):
    def fail(home):raise OSError('backup failed')
    monkeypatch.setattr('seed.backup.create_backup',fail)
    with pytest.raises(OSError):Memory(v5_home/'memory.sqlite3')
    with sqlite3.connect(v5_home/'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==5
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='self_model_current'").fetchone()


@pytest.mark.parametrize('versions',[[7],[999],[],[5,5],['broken']])
def test_unsupported_schema_refused_before_mutation(v5_home,versions):
    path=v5_home/'memory.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('DELETE FROM seed_schema')
        db.executemany('INSERT INTO seed_schema VALUES(?)',[(v,) for v in versions])
        db.commit();before=list(db.iterdump())
    with pytest.raises(ValueError):Memory(path)
    with sqlite3.connect(path) as db:assert list(db.iterdump())==before
    assert read_manifest(v5_home)==[]
