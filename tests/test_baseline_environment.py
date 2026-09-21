"""Sensor characterization with every OS/network operation replaced at its boundary."""
from types import SimpleNamespace
import pytest
from seed import body

@pytest.mark.parametrize('output,expected',[
    ('',(None,None)),
    ("Now drawing from 'AC Power'\n-InternalBattery-0 80%; charging;",(80,True)),
    ("Now drawing from 'Battery Power'\n-InternalBattery-0 70%; discharging;",(70,True)),
])
def test_current_battery_parser_including_known_discharge_false_positive(monkeypatch,output,expected):
    # Current parser treats the substring 'charging' in 'discharging' as true.
    # Documented B0 limitation, not a claim that the boolean is accurate.
    monkeypatch.setattr(body,'_run',lambda *args:output)
    assert body.battery_state()==expected


def test_failed_command_and_network_return_unknown_false(monkeypatch):
    def command(*args,**kwargs):raise OSError('unavailable')
    monkeypatch.setattr(body.subprocess,'check_output',command)
    assert body.battery_state()==(None,None)
    def connect(address,timeout):
        assert address==('1.1.1.1',443) and timeout==1
        raise OSError('offline')
    monkeypatch.setattr(body.socket,'create_connection',connect)
    assert body.network_reachable() is False


def test_environment_units_and_fields(tmp_path,monkeypatch):
    monkeypatch.setattr(body,'battery_state',lambda:(80,True))
    monkeypatch.setattr(body.shutil,'disk_usage',lambda home:SimpleNamespace(total=1000,free=250))
    monkeypatch.setattr(body.os,'getloadavg',lambda:(4,2,1))
    monkeypatch.setattr(body.os,'cpu_count',lambda:8)
    monkeypatch.setattr(body,'network_reachable',lambda:False)
    monkeypatch.setattr(body.time,'time',lambda:1000)
    monkeypatch.setattr(body.time,'localtime',lambda:SimpleNamespace(tm_hour=12))
    monkeypatch.setattr(body.platform,'node',lambda:'synthetic-host')
    monkeypatch.setattr(body.platform,'machine',lambda:'synthetic-arch')
    monkeypatch.setattr(body.platform,'mac_ver',lambda:('synthetic-os','',''))
    assert body.Body(tmp_path).perceive()=={
        'wall_time':1000,'local_hour':12,'battery_pct':80,'charging':True,'disk_free_pct':25,
        'load_ratio':.5,'load_5m_ratio':.25,'network':False,'hostname':'synthetic-host',
        'machine':'synthetic-arch','macos':'synthetic-os'}


def test_disk_failure_propagates_to_lifecycle_error(tmp_path,monkeypatch):
    monkeypatch.setattr(body,'battery_state',lambda:(None,None))
    def broken(home):raise OSError('disk unavailable')
    monkeypatch.setattr(body.shutil,'disk_usage',broken)
    with pytest.raises(OSError,match='disk unavailable'):body.Body(tmp_path).perceive()
