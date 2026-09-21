"""Upgrade fixtures only: every pre-v2 table keeps its original rows."""
import json
import sqlite3
import pytest
from seed.memory import Memory
from seed import migrations
from seed.backup import read_manifest

TABLES = ('meta', 'episodes', 'q_values', 'concepts', 'events', 'runtime',
          'concept_evidence', 'commands', 'annotations', 'settings',
          'automations', 'automation_runs', 'audit')


def snapshot(db):
    return {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in TABLES}


@pytest.fixture
def v1_home(legacy_home):
    with sqlite3.connect(legacy_home / 'memory.sqlite3') as db:
        for statement in migrations.STATEMENTS:
            db.execute(statement)
        db.execute('INSERT INTO seed_schema VALUES(1)')
        db.execute("INSERT INTO events VALUES(7,1000,'SYSTEM','test','original','{}')")
        db.execute("INSERT INTO runtime VALUES(1,'{\"lifecycle\":\"STOPPED\"}')")
        db.execute("INSERT INTO concept_evidence VALUES('typical_compute_pressure',1000,1001,'[1]')")
        db.execute("INSERT INTO commands VALUES('c','observe','old',1000,1001,'completed','{}')")
        db.execute("INSERT INTO annotations VALUES(1,1,'[\"original\"]')")
        db.execute("INSERT INTO settings VALUES(1,3,'{\"epsilon\":0.2}')")
        db.execute("INSERT INTO automations VALUES('a',2,'{}')")
        db.execute("INSERT INTO automation_runs VALUES('a','once','completed','{}')")
        db.execute("INSERT INTO audit VALUES(4,1001,'test','{}','{}')")
    return legacy_home


@pytest.mark.parametrize('kind', ['fresh', 'legacy', 'v1'])
def test_upgrade_to_v2_preserves_all_rows_and_backup(kind, tmp_path, legacy_home, v1_home):
    # v1_home upgrades legacy_home to a known v1 fixture; use a separate legacy copy.
    if kind == 'fresh':
        target = tmp_path / 'fresh'
    elif kind == 'legacy':
        target = tmp_path / 'legacy'
        target.mkdir()
        from pathlib import Path
        with sqlite3.connect(target / 'memory.sqlite3') as db:
            db.executescript((Path(__file__).parent / 'fixtures/legacy.sql').read_text())
            db.execute("INSERT INTO meta VALUES('identity','{\"name\":\"original\"}')")
    else:
        target = v1_home
    before = None
    if kind == 'v1':
        with sqlite3.connect(target / 'memory.sqlite3') as db:
            before = snapshot(db)
    m = Memory(target / 'memory.sqlite3')
    try:
        assert m.db.execute('SELECT version FROM seed_schema').fetchone()[0] == 2
        assert m.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 0
    finally:
        m.close()
    if before:
        with sqlite3.connect(target / 'memory.sqlite3') as db:
            assert snapshot(db) == before
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    backups = read_manifest(target)
    assert len(backups) == (kind != 'fresh')
    if backups:
        with sqlite3.connect(target / 'backups' / backups[0]['name']) as db:
            assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='transitions'").fetchone()
            if before:
                assert snapshot(db) == before
                assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 1
    m = Memory(target / 'memory.sqlite3')
    m.close()
    assert read_manifest(target) == backups


def test_v1_failed_backup_leaves_version_and_rows(v1_home, monkeypatch):
    with sqlite3.connect(v1_home / 'memory.sqlite3') as db:
        before = snapshot(db)
    def fail(_home):
        raise OSError('snapshot failed')
    monkeypatch.setattr('seed.backup.create_backup', fail)
    with pytest.raises(OSError, match='snapshot failed'):
        Memory(v1_home / 'memory.sqlite3')
    with sqlite3.connect(v1_home / 'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 1
        assert snapshot(db) == before


def test_v1_failed_migration_rolls_back(v1_home, monkeypatch):
    statements = getattr(migrations, 'V2_STATEMENTS', [])
    monkeypatch.setattr(migrations, 'V2_STATEMENTS', statements + ['INVALID SQL'], raising=False)
    with sqlite3.connect(v1_home / 'memory.sqlite3') as db:
        before = snapshot(db)
        with pytest.raises(sqlite3.Error):
            migrations.migrate(db)
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0] == 1
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='transitions'").fetchone()
        assert snapshot(db) == before


@pytest.mark.parametrize('versions', [[999], [], [1, 1]])
def test_constructor_refuses_unknown_or_ambiguous_schema_before_writes(v1_home, versions):
    path = v1_home / 'memory.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('DELETE FROM seed_schema')
        db.executemany('INSERT INTO seed_schema VALUES(?)', [(v,) for v in versions])
        before = snapshot(db)
        schema = db.execute('SELECT * FROM sqlite_master').fetchall()
    with pytest.raises(ValueError, match='schema version'):
        Memory(path)
    with sqlite3.connect(path) as db:
        assert snapshot(db) == before
        assert db.execute('SELECT * FROM sqlite_master').fetchall() == schema
    assert read_manifest(v1_home) == []


def test_legacy_to_v2_failure_rolls_back_both_migration_steps(legacy_home, monkeypatch):
    monkeypatch.setattr(migrations, 'V2_STATEMENTS', migrations.V2_STATEMENTS + ['INVALID SQL'])
    with sqlite3.connect(legacy_home / 'memory.sqlite3') as db:
        before = {table:db.execute(f'SELECT * FROM {table}').fetchall()
                  for table in ('meta','episodes','q_values','concepts')}
        with pytest.raises(sqlite3.Error):
            migrations.migrate(db)
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name IN ('seed_schema','transitions','events')").fetchone()
        assert before == {table:db.execute(f'SELECT * FROM {table}').fetchall() for table in before}
