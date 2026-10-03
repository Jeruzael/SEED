import json
import pytest


def router(foundation_module, truth=b'PRIVATE_TRUTH_SENTINEL'):
    p=foundation_module('scenarios/private')
    c=foundation_module('channel')
    engine=p.ScenarioEngine({'load_ratio':.2,'network':True},[{'load_ratio':.3,'network':False}],p.PrivateTruthView(truth))
    return c.ChannelRouter(engine)


def test_all_forbidden_dispatch_and_sentinels(foundation_module):
    channel=foundation_module('channel')
    r=router(foundation_module)
    for op in ('truth','score','expected_result','getattr','__dict__','config','findings','evaluation_root','checkpoint'):
        with pytest.raises(ValueError): r.dispatch({'operation':op})
    for field in ('truth','score','expected_result','finding','wall_time','settings'):
        with pytest.raises(ValueError):
            r.dispatch({'operation':'observation','key':['measured','default',1,'pre'],field:'PRIVATE_TRUTH_SENTINEL'})
    before=r.dispatch({'operation':'observation','key':['measured','default',1,'pre']})
    assert before == {'load_ratio':.2,'network':True}
    before['truth']='PRIVATE_TRUTH_SENTINEL'
    after=r.dispatch({'operation':'apply','key':['measured','default',1,'action'],'action':'observe'})
    assert after == {'load_ratio':.3,'network':False}
    assert b'PRIVATE_TRUTH_SENTINEL' not in json.dumps(after).encode()


def test_protocol_tuple_identity(foundation_module):
    r=router(foundation_module)
    with pytest.raises(ValueError):
        r.dispatch({'operation':'apply','key':['measured','default',1,'action'],'action':'observe'})
    r.dispatch({'operation':'observation','key':['training','default',1,'pre']})
    with pytest.raises(ValueError):
        r.dispatch({'operation':'observation','key':['training','default',1,'pre']})
    r.dispatch({'operation':'apply','key':['training','default',1,'action'],'action':'rest'})
    r.dispatch({'operation':'observation','key':['measured','stale',1,'pre']})
    with pytest.raises(ValueError):
        r.dispatch({'operation':'apply','key':['measured','fresh',1,'action'],'action':'rest'})
    with pytest.raises(ValueError):
        r.dispatch({'operation':'acknowledgment','key':['measured','stale',1,'checkpoint'],'token':'SCORE_ACK'})


def test_checkpoint_transport_remains_locked(foundation_module):
    c=foundation_module('channel')
    client=c.LearnerClient(None)
    with pytest.raises(ValueError):
        client.send_checkpoint(b'{}')
