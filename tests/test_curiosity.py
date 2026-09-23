import copy
import json
import pytest
from seed.memory import Memory
from tests.test_world_model import record, belief


def error(value=1,coverage=1):
    return dict(evaluator='prediction_error_v1',evaluator_version=1,
                aggregate=dict(status='evaluated',mean_normalized_error=value,coverage=coverage))


def prior(signal='battery_pct',n=4,confidence=.8,mean=1,probability=.8):
    return dict(belief_key='prior',signal=signal,scope='global',scope_value='',evidence_count=n,
                confidence=confidence,source_last_transition_id=7,
                value_json=json.dumps({'mean_delta':mean} if signal!='network_reachable'
                                      else {'probability_true':probability}))


def assess(e=None,before=None,after=None,beliefs=None,action='observe'):
    from seed.curiosity import assess_curiosity
    return assess_curiosity(error() if e is None else e,{'battery_pct':50} if before is None else before,
                            action,{'battery_pct':51} if after is None else after,beliefs or {})


@pytest.mark.parametrize('err,cov,p,expected',[(0,1,None,0),(1,1,None,1),
    (1,1,prior(),.3),(.8,.5,None,.4),(1,1,prior(n=2,confidence=.2),.675)])
def test_exact_formula_and_error_anchor(err,cov,p,expected):
    result=assess(error(err,cov),beliefs={'battery_pct':p} if p else {})
    assert result['model']=='curiosity_v1' and result['model_version']==1
    assert result['status']=='evaluated'
    assert result['prediction_surprise']==err*cov
    assert result['score']==pytest.approx(expected)
    assert 0<=result['score']<=1


@pytest.mark.parametrize('score,level',[(.199999,'LOW'),(.2,'NOTABLE'),(.499999,'NOTABLE'),
                                      (.5,'HIGH'),(.749999,'HIGH'),(.75,'VERY_HIGH'),(1,'VERY_HIGH')])
def test_exact_level_boundaries(score,level):
    assert assess(error(score))['level']==level


@pytest.mark.parametrize('bad',[None,True,'1',float('nan'),float('inf'),-.1,1.1])
@pytest.mark.parametrize('field',['mean_normalized_error','coverage'])
def test_invalid_aggregate_is_unavailable_without_numeric_score(field,bad):
    e=error()
    e['aggregate'][field]=bad
    result=assess(e)
    assert result['status']=='unavailable' and result['score'] is None
    assert result['level']=='UNAVAILABLE' and not result['reflection_eligible']


def test_unavailable_and_no_usable_observations():
    for e in ({}, {'aggregate':{'status':'unavailable'}}, error(1,0)):
        assert assess(e)['score'] is None
    result=assess(error(),before={},after={})
    assert result['score'] is None and result['reflection_eligible'] is False


@pytest.mark.parametrize('confidence,expected',[(.2,.8),(.8,.2)])
def test_uncertainty_is_complement_of_evidence_consistency(confidence,expected):
    assert assess(beliefs={'battery_pct':prior(confidence=confidence)})['uncertainty']==pytest.approx(expected)


@pytest.mark.parametrize('signal', ['battery_pct','network_reachable'])
@pytest.mark.parametrize('n,contradiction,expected', [(0,False,1),(2,False,.5),(3,True,.5),(4,False,0),(4,True,1)])
def test_novelty_uses_publication_age_and_canonical_contradiction(signal,n,contradiction,expected):
    numeric=signal=='battery_pct'
    p=prior(signal,n=n)
    before={'battery_pct':50} if numeric else {}
    after={'battery_pct':49 if contradiction else 51} if numeric else {'network':not contradiction}
    result=assess(before=before,after=after,beliefs={signal:p} if n else {})
    assert result['novelty']==expected
    assert result['components']['signals'][signal]['contradictory']==(n>=4 and contradiction)


def test_multi_signal_average_excludes_invalid_observations():
    result=assess(before={'battery_pct':50,'load_ratio':.1},
                  after={'battery_pct':51,'load_ratio':.2,'disk_free_pct':None,'network':False},
                  beliefs={'battery_pct':prior(confidence=.8),'load_ratio':prior('load_ratio',n=2,confidence=.2)})
    assert result['uncertainty']==pytest.approx((.2+.8+1)/3)
    assert result['novelty']==pytest.approx((0+.5+1)/3)
    assert set(result['components']['signals'])=={'battery_pct','load_ratio','network_reachable'}


def test_assessment_is_pure_and_snapshot_is_detached():
    p=prior()
    e=error()
    before={'battery_pct':50}
    after={'battery_pct':49}
    beliefs={'battery_pct':p}
    originals=copy.deepcopy((e,before,after,beliefs))
    result=assess(e,before,after,beliefs)
    assert (e,before,after,beliefs)==originals
    p['confidence']=0
    assert result['components']['signals']['battery_pct']['prior_belief']['confidence']==.8
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('action,after,reason',[
    ('reflect',{},'already_reflected'),('observe',{'load_ratio':.80001},'high_load'),
    ('observe',{'battery_pct':19.99,'charging':False},'low_battery'),
    ('observe',{'disk_free_pct':9.99},'low_disk')])
def test_static_resource_guards_do_not_change_score(action,after,reason):
    result=assess(before={'battery_pct':50},after={'battery_pct':51,**after},action=action)
    assert result['score']==1 and result['level']=='VERY_HIGH'
    assert result['suppression_reason']==reason and not result['reflection_eligible']


@pytest.mark.parametrize('after',[{}, {'load_ratio':.8,'battery_pct':20,'charging':False,'disk_free_pct':10},
    {'battery_pct':19,'charging':True},{'battery_pct':19,'charging':None},
    {'load_ratio':'9','battery_pct':-1,'charging':False,'disk_free_pct':-1},
    {'load_ratio':float('inf'),'battery_pct':None,'disk_free_pct':True}])
def test_unknown_invalid_and_boundary_resources_do_not_suppress(after):
    from seed.curiosity import attention_suppression
    assert attention_suppression(assess(),'observe',after) is None


def test_coverage_gate_independent_of_descriptive_high_level():
    from seed.curiosity import attention_suppression
    result=assess()
    result.update(score=.8,level='HIGH',coverage=.49)
    assert attention_suppression(result,'observe',{})=='insufficient_coverage'
    assert result['score']==.8 and result['level']=='HIGH'


def test_keyed_snapshot_action_then_global_and_pending_excluded(home):
    from seed.world_model import WorldModel
    m=Memory(home/'memory.sqlite3')
    w=WorldModel(m)
    try:
        for action in ['observe','observe','reflect']:
            w.observe_transition(record(m,{'battery_pct':50},{'battery_pct':51},action))
        assert hasattr(w,'applicable_beliefs'), 'B5 requires a bounded prior-belief snapshot'
        sql=[]
        m.db.set_trace_callback(sql.append)
        chosen=w.applicable_beliefs('observe')
        assert chosen['battery_pct']['scope']=='action' and chosen['battery_pct']['evidence_count']==2
        assert w.applicable_beliefs('reflect')['battery_pct']['scope']=='global'
        m.db.set_trace_callback(None)
        assert len(sql)==2 and all('belief_key IN' in s for s in sql)
        assert 'network_reachable' not in chosen
    finally:m.close()


def test_b4_update_and_curiosity_share_exact_contradiction_function(home,monkeypatch):
    import seed.world_model as world
    assert hasattr(world,'contradicts'), 'Canonical contradiction helper must be shared'
    calls=[]
    original=world.contradicts
    def spy(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(world,'contradicts',spy)
    m=Memory(home/'memory.sqlite3')
    w=world.WorldModel(m)
    try:
        for _ in range(4): w.observe_transition(record(m,{'battery_pct':50},{'battery_pct':51}))
        calls.clear()
        result=assess(before={'battery_pct':50},after={'battery_pct':49},beliefs=w.applicable_beliefs('observe'))
        assert result['novelty']==1 and len(calls)==1
        w.observe_transition(record(m,{'battery_pct':50},{'battery_pct':49}))
        assert len(calls)==3 and belief(m)['contradiction_count']==1
    finally:m.close()
