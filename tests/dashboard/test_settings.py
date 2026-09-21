import pytest
from seed.config import validate_settings
from dashboard.services.settings import SettingsStore
from dashboard.services.read_store import ServiceError

@pytest.mark.parametrize('patch',[{'alpha':float('nan')},{'alpha':float('inf')},{'epsilon':1.1},{'alpha':0},{'port':80},{'observe_interval':0},{'port':True},{'theme':'evil'},{'backup_directory':'/tmp'},{'prediction_error_curiosity':True}])
def test_invalid_settings(patch):
    with pytest.raises(ValueError): validate_settings(patch)

def test_settings_revision_and_audit(home):
    store=SettingsStore(home)
    assert store.get()['values']['memory_budget']==2*1024**3
    updated=store.update({'epsilon':.2},revision=0)
    assert updated['revision']==1 and updated['values']['epsilon']==.2
    with pytest.raises(ServiceError):store.update({'alpha':.3},revision=0)
    assert store.get()['values']['alpha']==.18

def test_core_applies_revision(home,monkeypatch):
    from seed.organism import SeedOrganism
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:{'load_ratio':.1})
    core=SeedOrganism(home)
    try:
        SettingsStore(home).update({'epsilon':0,'name':'Sprout','observe_interval':30},0)
        core.memory.set_q('unknown|calm|ok|day','observe',1,1)
        assert core.cycle()==30
        assert core.identity['name']=='Sprout'
        assert core.learner.epsilon==0
    finally:core.close()
