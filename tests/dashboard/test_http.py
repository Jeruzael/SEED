import asyncio
import pytest
from fastapi.testclient import TestClient
from dashboard.app import create_app
from dashboard.__main__ import server_options
from dashboard.api.stream import encode_event, StreamSlots

ORIGIN='http://127.0.0.1:8765'

def test_routes_and_local_binding(legacy_home):
    with TestClient(create_app(legacy_home),base_url=ORIGIN) as c:
        for route in ['status','environment','memories','concepts','learning','development','storage','history','health','events','settings','commands','automations']:
            assert c.get('/api/'+route).status_code==200,route
        assert c.get('/api/memories/99').status_code==404
        assert c.get('/api/memories?page_size=101').status_code==422
        assert c.get('/api/events?after=-1').status_code==422
    assert server_options(8765)['host']=='127.0.0.1'
    with pytest.raises(ValueError): server_options(80)

@pytest.mark.parametrize('headers',[{'host':'evil.example'},{'origin':'https://evil.example'},{'host':'127.0.0.1:8765.evil'}])
def test_host_and_origin_guard(legacy_home,headers):
    with TestClient(create_app(legacy_home),base_url=ORIGIN) as c:
        assert c.get('/api/status',headers=headers).status_code==403

def test_csrf_and_readonly_mode(home):
    with TestClient(create_app(home),base_url=ORIGIN) as c:
        assert c.post('/api/commands/observe',json={}).status_code==403
        token=c.get('/api/bootstrap').json()['token']
        headers={'Origin':ORIGIN,'X-SEED-CSRF':token}
        assert c.post('/api/commands/observe',json={},headers=headers).status_code==403
        response=c.get('/api/status')
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        assert 'access-control-allow-origin' not in response.headers

def test_request_body_limit(home):
    with TestClient(create_app(home,operator=True),base_url=ORIGIN) as c:
        token=c.get('/api/bootstrap').json()['token']
        headers={'Origin':ORIGIN,'X-SEED-CSRF':token,'Content-Type':'application/json'}
        assert c.post('/api/commands/observe',content='x'*17000,headers=headers).status_code==413

def test_sse_encodes_newlines_and_limits_clients():
    wire=encode_event({'id':7,'message':'a\nb'})
    assert 'id: 7\n' in wire and 'a\\nb' in wire
    async def exercise():
        slots=StreamSlots(2)
        assert slots.acquire() and slots.acquire()
        assert not slots.acquire()
        slots.release()
        assert slots.acquire()
    asyncio.run(exercise())
