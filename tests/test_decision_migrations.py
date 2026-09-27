import json
import sqlite3
import pytest
from seed import migrations
from seed.memory import Memory
from tests.test_decision import system, choose, STATE

@pytest.mark.parametrize('version',range(7))
def test_v7_failure_rolls_back_all_starting_versions(legacy_home,version,monkeypatch):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        if version:
            for sql in migrations.STATEMENTS: db.execute(sql)
            db.execute('INSERT INTO seed_schema VALUES(?)',(version,))
        for v in range(2,version+1):
            for sql in getattr(migrations,f'V{v}_STATEMENTS'): db.execute(sql)
        db.commit()
        before=list(db.iterdump())
        monkeypatch.setattr(migrations,'V7_STATEMENTS',getattr(migrations,'V7_STATEMENTS',[])+['INVALID SQL'],raising=False)
        with pytest.raises(sqlite3.Error): migrations.migrate(db)
        assert list(db.iterdump())==before

def store(system,selection=None):
    return system.memory.record_transition_experience(state_before=STATE,action='observe',state_after=STATE,
        outcome={},legacy_reward=.45,started_at=100,completed_at=101,
        prediction=selection.prediction if selection else None,decision=selection.record if selection else None,
        world_model_eligible=True)

def test_optional_absence_and_linked_compact_record(system):
    assert migrations.VERSION==7
    store(system)
    assert system.memory.db.execute('SELECT count(*) FROM decision_records').fetchone()[0]==0
    selection=choose(system)
    _,tid=store(system,selection)
    row=system.memory.db.execute('SELECT * FROM decision_records').fetchone()
    record=json.loads(row['data_json'])
    assert row['transition_id']==record['transition_id']==tid
    assert record['created_at']==row['created_at']
    assert record['selected_prediction_sha256']==selection.record['selected_prediction_sha256']
    assert len(row['data_json'].encode())<16384
    assert selection.record['transition_id'] is None

def test_decision_insert_failure_rolls_back_whole_experience_group(system):
    selection=choose(system)
    system.memory.db.execute("CREATE TRIGGER reject_decision BEFORE INSERT ON decision_records BEGIN SELECT RAISE(ABORT,'rejected'); END")
    with pytest.raises(sqlite3.Error): store(system,selection)
    for table in ['episodes','transitions','world_model_queue','decision_records']:
        assert system.memory.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0

def test_mutated_prediction_aborts_before_experience_writes(system):
    selection=choose(system)
    selection.prediction['signals']['battery_pct']['value']=75
    with pytest.raises(ValueError): store(system,selection)
    assert system.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==0


def test_v6_snapshot_survives_migration_and_only_real_cycle_publishes_v7(home):
    from tests.test_self_model import record,update,current
    from dashboard.services.seed_service import SeedService
    m=Memory(home/'memory.sqlite3')
    with m.db:
        m.db.execute('DROP TABLE decision_records')
        m.db.execute('UPDATE seed_schema SET version=6')
    tid=record(m)
    assert update(m,tid)=='updated'
    retained=current(m)
    assert retained['memory']['storage']['value']['schema_version']==6
    m.close()
    m=Memory(home/'memory.sqlite3')
    assert current(m)==retained
    assert SeedService(home,clock=lambda:1002).self_model()['snapshot']['memory']['storage']['value']['schema_version']==6
    assert update(m,record(m,at=1003),at=1004)=='updated'
    assert current(m)['memory']['storage']['value']['schema_version']==7
    m.close()
