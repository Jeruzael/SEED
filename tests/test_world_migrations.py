"""B4 migration and prospective queue boundaries, using temporary homes only."""
import sqlite3
import pytest
from seed import migrations
from seed.memory import Memory
from seed.backup import read_manifest
from tests.test_transition_migrations import v1_home, TABLES

WORLD_TABLES = {'world_beliefs', 'world_pending', 'world_model_queue', 'world_model_processed'}


def rows(db):
    return {t: [tuple(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY rowid')]
            for t in (*TABLES, 'transitions')}


@pytest.fixture
def v2_home(v1_home):
    with sqlite3.connect(v1_home/'memory.sqlite3') as db:
        for sql in migrations.V2_STATEMENTS:
            db.execute(sql)
        db.execute('UPDATE seed_schema SET version=2')
        for index, (prediction, error) in enumerate([(None,None), ('{"original":2}',None),
                                                     ('{"original":3}','{"score":0.7}')], 1):
            if index > 1:
                db.execute("INSERT INTO episodes VALUES(?,1000,'experience','{}','observe',.45,'original')", (index,))
            db.execute('INSERT INTO transitions VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (index,index,999,1000,'{"battery_pct":80}','observe','{"battery_pct":79}',
                        '{}',.45,prediction,error))
    return v1_home


def test_v2_upgrade_preserves_every_row_and_backup_then_noop(v2_home):
    path = v2_home/'memory.sqlite3'
    with sqlite3.connect(path) as db:
        before = rows(db)
    m = Memory(path)
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0] == 6
        assert rows(m.db) == before
        for table in WORLD_TABLES:
            assert m.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    finally:
        m.close()
    backups = read_manifest(v2_home)
    assert len(backups) == 1
    with sqlite3.connect(v2_home/'backups'/backups[0]['name']) as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 2
        assert rows(db) == before
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='world_beliefs'").fetchone()
    Memory(path).close()
    assert read_manifest(v2_home) == backups


@pytest.mark.parametrize('version', [0, 1, 2])
def test_final_migration_step_failure_rolls_back_entire_ladder(version, legacy_home, monkeypatch):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        if version:
            for sql in migrations.STATEMENTS:
                db.execute(sql)
            db.execute('INSERT INTO seed_schema VALUES(?)', (version,))
        if version == 2:
            for sql in migrations.V2_STATEMENTS:
                db.execute(sql)
        db.commit()
        before = list(db.iterdump())
        monkeypatch.setattr(migrations, 'V3_STATEMENTS', getattr(migrations,'V3_STATEMENTS',[]) + ['INVALID SQL'], raising=False)
        with pytest.raises(sqlite3.Error):
            migrations.migrate(db)
        assert list(db.iterdump()) == before


def test_v2_failed_backup_prevents_migration(v2_home, monkeypatch):
    def fail(home):
        raise OSError('snapshot failed')
    monkeypatch.setattr('seed.backup.create_backup', fail)
    with pytest.raises(OSError, match='snapshot failed'):
        Memory(v2_home/'memory.sqlite3')
    with sqlite3.connect(v2_home/'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 2
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='world_beliefs'").fetchone()


def test_queue_eligibility_atomic_with_new_experience(home):
    m = Memory(home/'memory.sqlite3')
    kw = dict(state_before={}, action='observe', state_after={}, outcome={},
              legacy_reward=0, started_at=1, completed_at=2)
    try:
        _, old = m.record_transition_experience(**kw)
        _, new = m.record_transition_experience(**kw, world_model_eligible=True)
        assert [r[0] for r in m.db.execute('SELECT transition_id FROM world_model_queue')] == [new]
        assert old != new
        m.db.execute("""CREATE TRIGGER fail_queue BEFORE INSERT ON world_model_queue
                        BEGIN SELECT RAISE(ABORT,'queue failed'); END""")
        with pytest.raises(sqlite3.IntegrityError, match='queue failed'):
            m.record_transition_experience(**kw, world_model_eligible=True)
        assert m.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 2
        assert m.db.execute('SELECT count(*) FROM episodes').fetchone()[0] == 2
    finally:
        m.close()
