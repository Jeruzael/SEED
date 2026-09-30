"""Stored prediction evidence: bounded reads, exact identity, no recomputation."""
import json
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from dashboard.app import create_app
from dashboard.services.seed_service import SeedService
from dashboard.services.read_store import ServiceError
from seed.memory import Memory

MAX_ID = 2**63 - 1


def client(home):
    return TestClient(create_app(home), base_url='http://127.0.0.1:8765')


def prediction():
    support = dict(evidence_count=4, confidence=.2, confidence_kind='evidence_support')
    signals = {name: dict(status='predicted', value=value, method='action_mean_delta',
                         clamped=False, **support)
               for name, value in [('battery_pct',80),('load_ratio',.5),('disk_free_pct',50)]}
    signals['network_reachable'] = dict(status='predicted', value=True,
        method='action_boolean_frequency', probability_true=.75, **support)
    return dict(action='observe', signals=signals, model='transition_delta_v1',
                model_version=1, horizon='next_post_action_observation')


def transition(home, pred=None, evaluation=None):
    memory=Memory(home/'memory.sqlite3')
    try:
        _, tid = memory.record_transition_experience(state_before={}, action='observe',
            state_after={}, outcome={}, legacy_reward=.25, started_at=100, completed_at=101)
        memory.db.execute('UPDATE transitions SET prediction_json=?,prediction_error_json=? WHERE id=?',
                          (pred, evaluation, tid))
        memory.db.commit()
    finally:
        memory.close()
    return tid


def test_empty_missing_home_and_missing_record(home, tmp_path):
    c=client(home)
    r=c.get('/api/predictions')
    assert r.status_code==200
    assert r.json()==dict(available=True,status='stored',reason=None,items=[],next_cursor=None)
    assert c.get('/api/predictions/1').status_code==404
    missing=tmp_path/'missing'
    assert client(missing).get('/api/predictions').json()['reason']=='missing_home'
    assert not missing.exists()


def test_presence_is_not_validity_and_corrupt_slot_is_not_refilled(home):
    ids=[transition(home),transition(home,'bad'),transition(home,json.dumps(prediction()))]
    c=client(home)
    first=c.get('/api/predictions?limit=2').json()
    assert [r['transition_id'] for r in first['items']]==[3,2]
    assert first['items'][1]['prediction_present'] is True
    assert first['next_cursor']==1
    assert 'prediction' not in first['items'][0]
    last=c.get('/api/predictions?limit=2&before=1').json()
    assert [r['transition_id'] for r in last['items']]==[1]
    assert last['next_cursor'] is None
    assert c.get('/api/predictions/2').json()['prediction']==dict(status='corrupt',reason='invalid_prediction',data=None)
    assert c.get('/api/predictions/1').json()['prediction']['status']=='absent'


@pytest.mark.parametrize('suffix', ['?limit=0','?limit=51','?limit=01','?limit=+1','?limit=1&limit=2',
    '?before=0','?before=-1','?before=01','?before=1.0','?before=1e2','?before=9223372036854775808',
    '?before=１２','?unknown=1','/01','/0','/-1','/1?limit=1','/1?x=y','/99999999999999999999'])
def test_strict_http_query(home,suffix):
    r=client(home).get('/api/predictions'+suffix)
    assert r.status_code==422
    assert r.json()['error']['code']=='invalid_query'


def test_supported_prediction_evaluation_and_no_recompute(home,monkeypatch):
    from seed.prediction_error import evaluate_prediction
    p=prediction()
    e=evaluate_prediction(p,dict(battery_pct=79,load_ratio=.75,disk_free_pct=49,network=False)).to_dict()
    # Freeze a different but in-domain score: readers validate types, not formulas.
    e['aggregate']['accuracy_score']=.123
    tid=transition(home,json.dumps(p),json.dumps(e))
    with sqlite3.connect(home/'memory.sqlite3') as db: before=list(db.iterdump())
    def forbidden(*a,**kw): raise AssertionError('read invoked a producer')
    monkeypatch.setattr('seed.predictor.Predictor.__init__',forbidden)
    monkeypatch.setattr('seed.prediction_error.evaluate_prediction',forbidden)
    monkeypatch.setattr(Memory,'__init__',forbidden)
    r=client(home).get(f'/api/predictions/{tid}')
    assert r.status_code==200
    d=r.json()
    assert d['prediction']['data']==p and d['evaluation']['data']==e
    assert d['evaluation']['data']['aggregate']['accuracy_score']==.123
    assert len(r.content)<=35840 and d['transition']['legacy_reward']==.25
    with sqlite3.connect(home/'memory.sqlite3') as db: assert list(db.iterdump())==before


@pytest.mark.parametrize('bad', ['{','{}','[]','null','{"x":NaN}', '{"x":1,"x":2}',
                                 ' '*16385, '{"x":1e999}', b'{}'])
def test_invalid_payloads_preserve_valid_sibling(home,bad):
    tid=transition(home,json.dumps(prediction()),bad)
    d=client(home).get(f'/api/predictions/{tid}').json()
    assert d['available'] is True
    assert d['prediction']['status']=='stored'
    assert d['evaluation']['status']=='corrupt' and d['evaluation']['data'] is None


def test_source_boundary_supported_unknown_and_shape_validation(home):
    raw=json.dumps(prediction())
    tid=transition(home,raw+' '*(16384-len(raw)))
    c=client(home)
    assert c.get(f'/api/predictions/{tid}').json()['prediction']['status']=='stored'
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('UPDATE transitions SET prediction_json=? WHERE id=?',(raw+' '*(16385-len(raw)),tid))
    assert c.get(f'/api/predictions/{tid}').json()['prediction']['status']=='corrupt'
    for change,want in [({'model_version':2},'unsupported'),({'model_version':True},'corrupt'),({'action':'rest'},'corrupt'),({'extra':1},'corrupt')]:
        p=prediction();p.update(change)
        with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('UPDATE transitions SET prediction_json=? WHERE id=?',(json.dumps(p),tid))
        assert c.get(f'/api/predictions/{tid}').json()['prediction']['status']==want


def test_max_id_missing_cursor_and_metadata_damage(home):
    transition(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('UPDATE transitions SET id=?',(MAX_ID,))
    c=client(home)
    assert c.get(f'/api/predictions?before={MAX_ID}').json()['items'][0]['transition_id']==MAX_ID
    assert c.get(f'/api/predictions/{MAX_ID}').json()['transition_id']==MAX_ID
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute("UPDATE transitions SET completed_at='invalid'")
    r=c.get('/api/predictions').json()['items'][0]
    assert r==dict(available=False,status='error',reason='invalid_transition',transition_id=MAX_ID)
    d=c.get(f'/api/predictions/{MAX_ID}').json()
    assert d['transition'] is d['prediction'] is d['evaluation'] is None


@pytest.mark.parametrize('version', [0,8,'broken'])
def test_incompatible_schema(home,version):
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('UPDATE seed_schema SET version=?',(version,))
    assert client(home).get('/api/predictions').status_code==409


def test_missing_feature_table_is_not_legacy(home):
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('DROP TABLE transitions')
    r=client(home).get('/api/predictions').json()
    assert r['status']=='error' and r['reason']=='missing_transition_table'


def test_select_budget_readonly_list_projection_and_busy(home,monkeypatch):
    transition(home,json.dumps(prediction()))
    service=SeedService(home);sql=[];original=service.store.connection
    @contextmanager
    def tracked(*a,**kw):
        with original(*a,**kw) as db:
            db.set_trace_callback(sql.append)
            yield db
    monkeypatch.setattr(service.store,'connection',tracked)
    service.predictions();selects=[s for s in sql if s.lstrip().upper().startswith('SELECT')]
    assert len(selects)<=4
    assert not any('substr(' in s.lower() for s in selects)
    assert any('prediction_json IS NOT NULL' in s for s in selects)
    sql.clear();service.prediction(1)
    assert len([s for s in sql if s.lstrip().upper().startswith('SELECT')])<=3
    assert any('ROLLBACK' in s for s in sql)
    # A rollback-journal fixture is required: WAL writers do not block readers.
    locked=home.parent/'locked';locked.mkdir()
    with sqlite3.connect(locked/'memory.sqlite3') as db:
        db.execute('CREATE TABLE seed_schema(version INTEGER)');db.commit()
        db.execute('BEGIN EXCLUSIVE')
        with pytest.raises(ServiceError) as error:SeedService(locked).predictions()
        assert error.value.code=='prediction_read_unavailable' and error.value.status==503


def test_progress_budget_and_recovery(home,monkeypatch):
    from dashboard.services import predictions
    for _ in range(30):transition(home)
    monkeypatch.setattr(predictions,'READ_BUDGET',1)
    service=SeedService(home)
    with pytest.raises(ServiceError) as error:service.predictions(limit=50)
    assert error.value.code=='prediction_read_unavailable'
    monkeypatch.setattr(predictions,'READ_BUDGET',300000)
    assert len(service.predictions(limit=50)['items'])==30


@pytest.mark.parametrize('value',[True,0,-1,1.5,'1',MAX_ID+1])
def test_direct_service_validation(home,value):
    service=SeedService(home)
    with pytest.raises(ServiceError):service.prediction(value)
    with pytest.raises(ServiceError):service.predictions(before=value)


def test_legacy_prediction_schema(legacy_home):
    assert client(legacy_home).get("/api/predictions").json()["reason"]=="legacy_schema"
