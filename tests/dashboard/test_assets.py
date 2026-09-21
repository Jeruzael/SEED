from fastapi.testclient import TestClient
from dashboard.app import create_app

def test_accessible_local_shell(legacy_home):
    with TestClient(create_app(legacy_home),base_url='http://127.0.0.1:8765') as c:
        response=c.get('/')
        assert response.status_code==200
        assert '<main id="main"' in response.text
        assert 'href="#main"' in response.text
        for asset in ['app.js','api.js','styles.css','charts.js','views/overview.js','views/activity.js','views/environment.js','views/memory.js','views/concepts.js','views/learning.js']:
            assert c.get('/static/'+asset).status_code==200
