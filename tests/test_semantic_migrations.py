import sqlite3
import pytest
from seed import migrations
from seed.memory import Memory
from seed.backup import read_manifest
from tests.test_transition_migrations import v1_home
from tests.test_world_migrations import v2_home
from tests.test_curiosity_migrations import v3_home,snapshot


@pytest.fixture
def v4_home(v3_home):
    with sqlite3.connect(v3_home/'memory.sqlite3') as db:
        for sql in migrations.V4_STATEMENTS: db.execute(sql)
        db.execute('UPDATE seed_schema SET version=4')
        db.execute("""INSERT INTO curiosity_assessments(transition_id,created_at,model,model_version,status,
            score,level,prediction_surprise,uncertainty,novelty,coverage,components_json,
            reflection_eligible,reflection_claimed,reflection_completed,claimed_at,completed_at)
            VALUES(3,100,'curiosity_v1',1,'evaluated',.8,'VERY_HIGH',.8,1,1,1,'{}',1,1,1,100,101)""")
        db.execute('INSERT INTO curiosity_runtime VALUES(1,3,100)')
    return v3_home


def test_v4_backup_upgrade_preserves_every_row_and_reopen(v4_home):
    path=v4_home/'memory.sqlite3'
    with sqlite3.connect(path) as db: before=snapshot(db)
    m=Memory(path)
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0]==7
        assert {t:[tuple(r) for r in m.db.execute(f'SELECT * FROM {t}')] for t in before}==before
        for table in ('semantic_memories','semantic_memory_history','consolidation_runs','consolidation_state'):
            assert m.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
    finally:m.close()
    backups=read_manifest(v4_home)
    assert len(backups)==1
    with sqlite3.connect(v4_home/'backups'/backups[0]['name']) as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==4
        assert snapshot(db)==before
    Memory(path).close()
    assert read_manifest(v4_home)==backups


@pytest.mark.parametrize('version',[0,1,2,3,4])
def test_final_step_rollback_entire_ladder(legacy_home,version,monkeypatch):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        if version:
            for sql in migrations.STATEMENTS:db.execute(sql)
            db.execute('INSERT INTO seed_schema VALUES(?)',(version,))
        for v in range(2,version+1):
            for sql in getattr(migrations,f'V{v}_STATEMENTS'):db.execute(sql)
        db.commit()
        before=list(db.iterdump())
        monkeypatch.setattr(migrations,'V5_STATEMENTS',getattr(migrations,'V5_STATEMENTS',[])+['INVALID SQL'],raising=False)
        with pytest.raises(sqlite3.Error):migrations.migrate(db)
        assert list(db.iterdump())==before


def test_v4_backup_failure_stops_upgrade(v4_home,monkeypatch):
    def fail(home):raise OSError('backup failed')
    monkeypatch.setattr('seed.backup.create_backup',fail)
    with pytest.raises(OSError,match='backup failed'):Memory(v4_home/'memory.sqlite3')
    with sqlite3.connect(v4_home/'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==4
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='semantic_memories'").fetchone()
