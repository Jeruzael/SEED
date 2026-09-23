import json
import sqlite3
import pytest
from seed import migrations
from seed.memory import Memory
from seed.backup import read_manifest
from tests.test_transition_migrations import v1_home
from tests.test_world_migrations import v2_home


def assessment():
    return dict(model='curiosity_v1',model_version=1,status='evaluated',score=.8,level='VERY_HIGH',
                prediction_surprise=.8,uncertainty=1.,novelty=1.,coverage=1.,components={'signals':{}},
                reflection_eligible=True,suppression_reason=None)


@pytest.fixture
def v3_home(v2_home):
    with sqlite3.connect(v2_home/'memory.sqlite3') as db:
        for sql in migrations.V3_STATEMENTS: db.execute(sql)
        db.execute('UPDATE seed_schema SET version=3')
        for table,n,signal in [('world_beliefs',2,'battery_pct'),('world_pending',1,'load_ratio')]:
            db.execute(f'''INSERT INTO {table} VALUES(1,? ,?,'global','','numeric_delta',?, ?,0,.1,1,2,1,2,1)''',
                       (f'1:{signal}:global::numeric_delta',signal,
                        '{"mean_delta":-1,"mean_absolute_delta":1,"min_delta":-1,"max_delta":-1}',n))
        db.execute('INSERT INTO world_model_queue VALUES(3)')
        db.execute('INSERT INTO world_model_processed VALUES(1,2,1,1)')
    return v2_home


def snapshot(db):
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='seed_schema'")]
    return {t:[tuple(r) for r in db.execute(f'SELECT * FROM {t}')] for t in tables}


def test_v3_backup_upgrade_preserves_all_prior_rows_and_no_backfill(v3_home):
    path=v3_home/'memory.sqlite3'
    with sqlite3.connect(path) as db: before=snapshot(db)
    m=Memory(path)
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0]==5
        assert {t:[tuple(r) for r in m.db.execute(f'SELECT * FROM {t}')] for t in before}==before
        assert m.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==0
        assert m.db.execute('SELECT count(*) FROM curiosity_runtime').fetchone()[0]==0
    finally: m.close()
    backups=read_manifest(v3_home)
    assert len(backups)==1
    with sqlite3.connect(v3_home/'backups'/backups[0]['name']) as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==3
        assert snapshot(db)==before
    Memory(path).close()
    assert read_manifest(v3_home)==backups


@pytest.mark.parametrize('version',[0,1,2,3])
def test_failed_final_v4_step_rolls_back_all_prior_steps(legacy_home,version,monkeypatch):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        if version:
            for sql in migrations.STATEMENTS: db.execute(sql)
            db.execute('INSERT INTO seed_schema VALUES(?)',(version,))
        if version>=2:
            for sql in migrations.V2_STATEMENTS: db.execute(sql)
        if version>=3:
            for sql in migrations.V3_STATEMENTS: db.execute(sql)
        db.commit()
        before=list(db.iterdump())
        monkeypatch.setattr(migrations,'V4_STATEMENTS',getattr(migrations,'V4_STATEMENTS',[])+['INVALID SQL'],raising=False)
        with pytest.raises(sqlite3.Error): migrations.migrate(db)
        assert list(db.iterdump())==before


def test_v3_backup_failure_stops_upgrade(v3_home,monkeypatch):
    def fail(home): raise OSError('backup failed')
    monkeypatch.setattr('seed.backup.create_backup',fail)
    with pytest.raises(OSError,match='backup failed'): Memory(v3_home/'memory.sqlite3')
    with sqlite3.connect(v3_home/'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==3
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='curiosity_assessments'").fetchone()


def test_exact_assessment_atomic_with_episode_transition_and_world_queue(home):
    m=Memory(home/'memory.sqlite3')
    kw=dict(state_before={},state_after={},action='observe',outcome={},legacy_reward=0,
            started_at=1,completed_at=2,world_model_eligible=True)
    expected=assessment()
    try:
        _,tid=m.record_transition_experience(**kw,curiosity=expected)
        row=dict(m.db.execute('SELECT * FROM curiosity_assessments').fetchone())
        for key,value in expected.items():
            if key=='components': assert json.loads(row['components_json'])==value
            else: assert row[key]==value
        assert row['transition_id']==tid and row['created_at']==2
        assert row['reflection_claimed']==row['reflection_completed']==0
        m.db.execute("""CREATE TRIGGER fail_assessment BEFORE INSERT ON curiosity_assessments
                        BEGIN SELECT RAISE(ABORT,'assessment failed'); END""")
        before=list(m.db.iterdump())
        with pytest.raises(sqlite3.IntegrityError,match='assessment failed'):
            m.record_transition_experience(**kw,curiosity=expected)
        assert list(m.db.iterdump())==before
        m.db.execute('DROP TRIGGER fail_assessment')
        m.record_transition_experience(**kw)  # Historical/default callers stay absent.
        assert m.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==1
    finally: m.close()
