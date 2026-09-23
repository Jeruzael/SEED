import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from dashboard.app import create_app
from dashboard.services.seed_service import SeedService
from dashboard.services.read_store import ServiceError
from seed.memory import Memory
from tests.test_curiosity_attention import store


def client(home): return TestClient(create_app(home),base_url='http://127.0.0.1:8765')


def test_recent_pagination_detail_and_rolling100_summary(home):
    m=Memory(home/'memory.sqlite3')
    for _ in range(5): store(m,score=1)
    for _ in range(98): store(m,score=.8)
    store(m,status='unavailable',score=None,level='UNAVAILABLE',prediction_surprise=None,
          uncertainty=None,novelty=None,coverage=None,reflection_eligible=False,suppression_reason='unavailable_evaluation')
    last=store(m,score=.4,level='NOTABLE',reflection_eligible=False,suppression_reason='below_threshold')
    m.db.execute('UPDATE curiosity_assessments SET reflection_claimed=1,reflection_completed=1 WHERE transition_id=10')
    m.db.execute("UPDATE curiosity_assessments SET reflection_claimed=1,failure_reason='test failure' WHERE transition_id=11")
    m.db.commit()
    before=list(m.db.iterdump())
    m.close()
    c=client(home)
    response=c.get('/api/curiosity?limit=2')
    assert response.status_code==200
    first=response.json()
    assert [r['transition_id'] for r in first['items']]==[105,104]
    next_page=c.get('/api/curiosity',params={'before':first['next_cursor'],'limit':2}).json()
    assert [r['transition_id'] for r in next_page['items']]==[103,102]
    assert c.get(f'/api/curiosity/{last}').json()==first['items'][0]
    s=c.get('/api/curiosity/summary').json()
    assert s['window_limit']==100 and s['assessment_count']==100
    assert s['counts_by_level']=={'VERY_HIGH':98,'UNAVAILABLE':1,'NOTABLE':1}
    assert s['mean_score']==pytest.approx((98*.8+.4)/99)
    assert s['mean_prediction_surprise']==pytest.approx(.8)
    assert s['mean_uncertainty']==s['mean_novelty']==1
    assert s['eligible_reflection_count']==98 and s['completed_reflection_count']==1
    assert s['claimed_reflection_count']==2 and s['failure_count']==1
    assert s['suppressed_reflection_count']==2
    assert s['suppression_reasons']=={'unavailable_evaluation':1,'below_threshold':1}
    with sqlite3.connect(home/'memory.sqlite3') as db: assert list(db.iterdump())==before


def test_legacy_reads_are_empty_without_migration(legacy_home):
    c=client(legacy_home)
    assert c.get('/api/curiosity').json()=={'available':False,'items':[],'next_cursor':None}
    s=c.get('/api/curiosity/summary').json()
    assert not s['available'] and s['assessment_count']==0 and s['mean_score'] is None
    assert c.get('/api/curiosity/1').status_code==404
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='curiosity_assessments'").fetchone()


@pytest.mark.parametrize('path',['?limit=0','?limit=101','?before=-1','?before=9223372036854775808',
                                 '/0','/-1','/9223372036854775808'])
def test_invalid_bounds(home,path):
    assert client(home).get('/api/curiosity'+path).status_code==422


def test_service_bound_and_fixed_summary_query(home,monkeypatch):
    from contextlib import contextmanager
    service=SeedService(home)
    assert hasattr(service,'curiosity_assessments'), 'Bounded curiosity inspection required'
    with pytest.raises(ServiceError):service.curiosity_assessments(limit=101)
    with pytest.raises(ServiceError):service.curiosity_assessment(2**63)
    sql=[]
    original=service.store.connection
    @contextmanager
    def connection(*args,**kw):
        with original(*args,**kw) as db:
            db.set_trace_callback(sql.append)
            yield db
    monkeypatch.setattr(service.store,'connection',connection)
    service.curiosity_summary()
    assert any('ORDER BY transition_id DESC LIMIT 100' in s for s in sql)
    assert not any('COUNT(' in s.upper() for s in sql)


def test_operator_requires_v4_tables(home):
    with sqlite3.connect(home/'memory.sqlite3') as db: db.execute('DROP TABLE curiosity_runtime')
    with pytest.raises(ServiceError,match='schema'):create_app(home,operator=True)
