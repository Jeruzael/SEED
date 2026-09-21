import os
import subprocess
import sys
from pathlib import Path
import pytest
from dashboard.app import create_app
from fastapi.testclient import TestClient


def test_core_runs_without_site_packages(tmp_path):
    code='''
import os
from pathlib import Path
from seed.body import Body
from seed.organism import SeedOrganism
Body.perceive = lambda self: {'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75,'local_hour':12}
core = SeedOrganism(Path(os.environ['SEED_HOME']))
try:
    core.awaken()
    assert core.cycle() in (8,12,20,35)
    core.stop()
    assert core.stop_event.is_set()
    core.sleep(reason='process_stop')
finally:
    core.close()
import sys
assert 'fastapi' not in sys.modules and 'uvicorn' not in sys.modules
print('standalone core ok')
'''
    home=tmp_path/'standalone'
    result=subprocess.run([sys.executable,'-S','-c',code],cwd=Path(__file__).resolve().parents[1],
                          env=dict(os.environ,SEED_HOME=str(home)),capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='standalone core ok'
    assert (home/'memory.sqlite3').exists()


@pytest.mark.parametrize('command',['stop','restart','rotate_logs'])
def test_mutating_command_confirmations_enforced_at_http_boundary(home,command):
    origin='http://127.0.0.1:8765'
    with TestClient(create_app(home,operator=True),base_url=origin) as client:
        token=client.get('/api/bootstrap').json()['token']
        response=client.post('/api/commands/'+command,json={},headers={'Origin':origin,'X-SEED-CSRF':token})
        assert response.status_code==409
        assert response.json()['error']['code']=='confirmation_required'


def test_wrong_origin_token_and_shell_payload_cannot_record_note(home):
    origin='http://127.0.0.1:8765'
    with TestClient(create_app(home,operator=True),base_url=origin) as client:
        token=client.get('/api/bootstrap').json()['token']
        assert client.post('/api/notes',json={'text':'not allowed'},headers={'Origin':'http://evil.example','X-SEED-CSRF':token}).status_code==403
        assert client.post('/api/notes',json={'text':'not allowed'},headers={'Origin':origin,'X-SEED-CSRF':'wrong'}).status_code==403
        assert client.post('/api/commands/observe',json={'shell':'echo bad'},headers={'Origin':origin,'X-SEED-CSRF':token}).status_code==422
        assert client.get('/api/memories').json()['total']==0
