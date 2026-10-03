"""R7: potentially applied actions cannot be retried after ambiguous outcomes."""
import json
import pytest
from .test_workers import launch


class AmbiguousScenario:
    def __init__(self, outcome='malformed'): self.calls=0; self.outcome=outcome
    def initial_observation(self,key): return {'load_ratio':.2}
    def apply_action(self,action,key):
        self.calls+=1
        if self.outcome=='exception': raise RuntimeError('PRIVATE_SENTINEL')
        return {'load_ratio':.3,'private':'PRIVATE_SENTINEL'}


@pytest.mark.parametrize('outcome',['malformed','exception'])
def test_ambiguous_action_latches_terminal_router(foundation_module,outcome):
    c=foundation_module('channel'); scenario=AmbiguousScenario(outcome); router=c.ChannelRouter(scenario)
    router.dispatch({'operation':'observation','key':['measured','default',1,'pre']})
    request={'operation':'apply','key':['measured','default',1,'action'],'action':'observe'}
    for _ in range(2):
        with pytest.raises(ValueError): router.dispatch(request)
    assert scenario.calls==1
    with pytest.raises(ValueError): router.dispatch({'operation':'action_catalog'})


def test_pre_action_error_has_no_effect(foundation_module):
    scenario=AmbiguousScenario(); router=foundation_module('channel').ChannelRouter(scenario)
    with pytest.raises(ValueError): router.dispatch({'operation':'apply','key':['measured','default',1,'action'],'action':'observe'})
    assert scenario.calls==0


def test_worker_contract_failure_terminates_dispatch(foundation_module,tmp_path):
    c=foundation_module('channel'); w=foundation_module('worker'); scenario=AmbiguousScenario()
    worker=w.WorkerHandle.start(launch(foundation_module,tmp_path),channel=c.ChannelRouter(scenario),cleanup_seconds=.1)
    worker.request({'operation':'observation','key':['measured','default',1,'pre']})
    try:
        with pytest.raises(ValueError): worker.request({'operation':'apply','key':['measured','default',1,'action'],'action':'observe'})
        worker.process.join(1)
        assert not worker.process.is_alive()
        with pytest.raises(ValueError): worker.request({'operation':'action_catalog'})
        assert scenario.calls==1
    finally: worker.stop('WORKER_DIED')


def test_client_invalid_response_after_apply_cannot_retry(foundation_module):
    class Pipe:
        calls=0
        def send_bytes(self,body): self.calls+=1
        def recv_bytes(self,*args):
            return json.dumps({'kind':'response','value':{'load_ratio':.2} if self.calls==1 else {'private':'sentinel'}}).encode()
    pipe=Pipe(); client=foundation_module('channel').LearnerClient(pipe)
    client.observation('measured',1)
    for _ in range(2):
        with pytest.raises(ValueError): client.apply('observe',1)
    assert pipe.calls==2
