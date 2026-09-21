import sqlite3
import pytest
from seed.migrations import migrate
from seed.telemetry import Telemetry
from seed.memory import Memory
from seed.paths import checked_path

def test_preserves_rows_and_is_idempotent(legacy_home):
    with sqlite3.connect(legacy_home / 'memory.sqlite3') as db:
        tables = ['meta','episodes','q_values','concepts']
        before = {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
        migrate(db)
        migrate(db)
        assert before == {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'

def test_unknown_schema_refused(home):
    with sqlite3.connect(home / 'memory.sqlite3') as db:
        db.execute('UPDATE seed_schema SET version=999')
        db.commit()
        with pytest.raises(ValueError):
            migrate(db)

def test_migration_rollback(legacy_home, monkeypatch):
    import seed.migrations as module
    monkeypatch.setattr(module, 'STATEMENTS', module.STATEMENTS + ['THIS IS INVALID SQL'])
    with sqlite3.connect(legacy_home / 'memory.sqlite3') as db:
        with pytest.raises(sqlite3.Error):
            migrate(db)
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='seed_schema'").fetchone()[0] == 0

def test_events_monotonic_and_runtime(home):
    memory = Memory(home / 'memory.sqlite3')
    try:
        t = Telemetry(memory)
        first = t.emit('SYSTEM','test','hello',{})
        second = t.emit('SYSTEM','test','world',{})
        assert second > first
        t.runtime(activity='idle')
        t.runtime(heartbeat=123)
        import json
        row = memory.db.execute('SELECT data_json FROM runtime').fetchone()
        assert json.loads(row[0]) == {'activity':'idle','heartbeat':123}
    finally:
        memory.close()

@pytest.mark.parametrize('relative',['../escape','/tmp/escape','foo/../../escape'])
def test_path_traversal_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        checked_path(tmp_path,relative)

def test_symlink_rejected(tmp_path):
    (tmp_path/'link').symlink_to('/tmp')
    with pytest.raises(ValueError):
        checked_path(tmp_path,'link/x')
