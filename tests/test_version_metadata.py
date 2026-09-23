"""Source identity must never substitute for observed runtime identity."""
import json
import os
import sqlite3
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from seed.organism import SeedOrganism
from seed.migrations import VERSION
from dashboard.app import create_app

ORIGIN = 'http://127.0.0.1:8765'


@pytest.fixture(autouse=True)
def synthetic_process(monkeypatch):
    monkeypatch.setattr('dashboard.services.process.ProcessController.status',
                        lambda _: {'state':'unknown','reason':'Synthetic test process'})


def test_running_core_reports_current_software_version(home):
    core = SeedOrganism(home)
    try:
        runtime = json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
        assert runtime['version'] == '0.2'  # Fails against the original hard-coded 0.1.
        from seed.version import CORE_VERSION
        assert runtime['version'] == CORE_VERSION
        assert runtime.get('commit') is None
    finally:
        core.close()


@pytest.mark.parametrize('operator', [False, True])
def test_bootstrap_explicit_versions_preserve_legacy_contract_and_tokens(home, operator):
    with TestClient(create_app(home, operator=operator),base_url=ORIGIN) as c:
        data = c.get('/api/bootstrap').json()
        assert data.get('core_source_version') == '0.2'
        assert data['version'] == '0.1 Observer Edition'
        assert data['dashboard_version'] == '0.1'
        assert data['dashboard_edition'] == 'Observer Edition'
        assert data['supported_schema_version'] == VERSION == 5
        assert data['operator'] is operator and data['refresh_seconds'] == 5
        assert isinstance(data['token'],str) and len(data['token']) >= 32
        assert c.get('/api/bootstrap').json()['token'] == data['token']
        assert c.post('/api/commands/observe',json={}).status_code == 403
        assert c.post('/api/commands/observe',json={},headers={'Origin':ORIGIN,'X-SEED-CSRF':'bad'}).status_code == 403
        assert data.get('commit') is None and 'core_runtime_version' not in data


def test_legacy_metadata_read_does_not_migrate_or_invent_runtime(legacy_home):
    path = legacy_home/'memory.sqlite3'
    with sqlite3.connect(path) as db: before = list(db.iterdump())
    with TestClient(create_app(legacy_home),base_url=ORIGIN) as c:
        assert c.get('/api/bootstrap').json().get('supported_schema_version') == 5
        status = c.get('/api/status').json()
        assert status['compatibility'] == 'legacy' and not status['fresh']
        assert status['runtime'] == {} and status['runtime'].get('version') is None
    with sqlite3.connect(path) as db: assert list(db.iterdump()) == before


@pytest.mark.parametrize('lifecycle,expected', [('STOPPED','STOPPED'), ('AWAKE',None)])
def test_newer_dashboard_does_not_relabel_older_stale_or_stopped_core(home,lifecycle,expected):
    runtime = {'version':'0.1','heartbeat':1,'lifecycle':lifecycle,'pid':999999,'session_id':'old'}
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('INSERT INTO runtime VALUES(1,?)',(json.dumps(runtime),))
    with TestClient(create_app(home),base_url=ORIGIN) as c:
        assert c.get('/api/bootstrap').json().get('core_source_version') == '0.2'
        status = c.get('/api/status').json()
        assert status['runtime'] == runtime
        assert status['lifecycle'] == expected and status['fresh'] is False


def test_absent_runtime_remains_absent_with_current_source(home):
    with TestClient(create_app(home),base_url=ORIGIN) as c:
        assert c.get('/api/bootstrap').json().get('core_source_version') == '0.2'
        status = c.get('/api/status').json()
        assert status['runtime'] == {} and status['fresh'] is False
        assert status['lifecycle'] is None
        asset = c.get('/static/views/overview.js').text
        assert "rt.version||'Unavailable'" in asset
        assert 'Legacy 0.1' not in asset


def test_version_import_is_lightweight_without_startup_or_io(tmp_path):
    code = """
import sys
from seed.version import CORE_VERSION
assert CORE_VERSION == '0.2'
assert not any(name in sys.modules for name in ('sqlite3','socket','subprocess','seed.memory','seed.organism'))
"""
    result = subprocess.run([sys.executable,'-S','-c',code],capture_output=True,text=True,
                            env=dict(os.environ,SEED_HOME=str(tmp_path/'uncreated')),timeout=5)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path/'uncreated').exists()


def test_overview_battery_labels_do_not_infer_power_source(home):
    # False also represents 'not charging' on AC; the asset must not say 'On battery'.
    with TestClient(create_app(home),base_url=ORIGIN) as c:
        response = c.get('/static/views/overview.js')
        assert response.status_code == 200
        asset = response.text
        assert "state.charging===true?'Charging':state.charging===false?'Not charging':'Charging state unavailable'" in asset
        assert "state.charging===false?'On battery'" not in asset
