"""Post-B6: raw synthetic pmset output reaches real sensor consumers."""
import json
from types import SimpleNamespace
import pytest
from seed import body
from seed.learner import state_key
from seed.semantic_memory import resource_suppression, Consolidator


def output(pct='15', status='discharging', power='Battery Power'):
    return f"Now drawing from '{power}'\n-InternalBattery-0 (id=123) {pct}%; {status}; 0:45 remaining present: true"


def test_discharging_reaches_the_low_battery_guard(monkeypatch):
    monkeypatch.setattr(body, '_run', lambda *args: output())
    pct, charging = body.battery_state()
    assert (pct, charging) == (15, False)
    assert resource_suppression(dict(battery_pct=pct, charging=charging,
                                    load_ratio=.1, disk_free_pct=50)) == 'low_battery'


@pytest.mark.parametrize('raw,expected', [
    (output(), (15, False)),
    (output(status='charging', power='AC Power'), (15, True)),
    (output(status='not charging', power='AC Power'), (15, False)),
    (output('100', 'charged', 'AC Power'), (100, True)),
    ('', (None, None)),
    (output(status='unrecognized'), (15, None)),
    ("Now drawing from 'AC Power'", (None, None)),
    ('diagnostic: 15%; charging', (None, None)),
    (output(status='discharging', power='AC Power'), (15, False)),
    (output(status='charging; discharging', power='AC Power'), (15, None)),
    (output(status='charging; not charging', power='AC Power'), (15, None)),
    (output(status='charging or discharging', power='AC Power'), (15, None)),
    (output(status='charging', power='Battery Power'), (15, None)),
    (output(status='charged', power='Battery Power'), (15, None)),
    (output('-1'), (None, False)),
    (output('101', 'charging', 'AC Power'), (None, True)),
    (output('unknown'), (None, False)),
    (output('15.5'), (None, False)),
    (output('15% 20'), (None, False)),
    ("NOW DRAWING FROM 'AC Power'\n  -InternalBattery-0\t15% ;  NOT   CHARGING  ;", (15, False)),
    ("Now drawing from 'AC Power'\n-InternalBattery-0 15%; ChArGiNg;", (15, True)),
    ("Now drawing from 'AC Power'\n-InternalBattery-0 15%;", (15, None)),
    (output()+"\n-InternalBattery-1 20%; charging;", (None, None)),
    ("Now drawing from 'AC Power'\nNow drawing from 'Battery Power'\n-InternalBattery-0 15%; charging;", (15, None)),
])
def test_complete_battery_fields_and_truthful_unknowns(monkeypatch, raw, expected):
    def run(*args):
        assert args == ('/usr/bin/pmset', '-g', 'batt')
        return raw
    monkeypatch.setattr(body, '_run', run)
    assert body.battery_state() == expected


def test_command_failure_keeps_existing_timeout_and_unknown(monkeypatch):
    def failed(args, **kwargs):
        assert args == ('/usr/bin/pmset', '-g', 'batt')
        assert kwargs['timeout'] == 2 and kwargs['text'] is True
        raise OSError('synthetic command failure')
    monkeypatch.setattr(body.subprocess, 'check_output', failed)
    assert body.battery_state() == (None, None)


def sensor_boundaries(monkeypatch, raw, load=.1, disk=50):
    calls = dict(battery=0, network=0)
    def run(*args):
        calls['battery'] += 1
        return raw
    def network():
        calls['network'] += 1
        return True
    monkeypatch.setattr(body, '_run', run)
    monkeypatch.setattr(body.shutil, 'disk_usage', lambda _: SimpleNamespace(total=100, free=disk))
    monkeypatch.setattr(body.os, 'getloadavg', lambda: (load, load, load))
    monkeypatch.setattr(body.os, 'cpu_count', lambda: 1)
    monkeypatch.setattr(body, 'network_reachable', network)
    monkeypatch.setattr(body.time, 'time', lambda: 1000.)
    monkeypatch.setattr(body.time, 'localtime', lambda: SimpleNamespace(tm_hour=12))
    monkeypatch.setattr(body.platform, 'node', lambda: 'synthetic-host')
    monkeypatch.setattr(body.platform, 'machine', lambda: 'synthetic-machine')
    monkeypatch.setattr(body.platform, 'mac_ver', lambda: ('synthetic-os', '', ''))
    return calls


@pytest.mark.parametrize('pct,status,power,load,disk,reason,energy', [
    ('15','discharging','Battery Power',.1,50,'low_battery','low'),
    ('19','discharging','Battery Power',.1,50,'low_battery','low'),
    ('20','discharging','Battery Power',.1,50,None,'mid'),
    ('15','charging','AC Power',.1,50,None,'charging'),
    ('15','unknown','Battery Power',.1,50,None,'low'),
    ('15','charging','AC Power',.81,50,'high_load','charging'),
    ('15','charging','AC Power',.1,9,'low_disk','charging'),
])
def test_real_perception_reaches_learner_and_both_resource_guards(home, monkeypatch,
        pct, status, power, load, disk, reason, energy):
    from seed.memory import Memory
    from seed.curiosity import assess_curiosity
    from seed.curiosity_attention import CuriosityAttention
    from tests.test_semantic_memory import source
    calls = sensor_boundaries(monkeypatch, output(pct,status,power), load, disk)
    state = body.Body(home).perceive()
    assert state_key(state).split('|')[0] == energy
    assert resource_suppression(state) == reason
    # Full-coverage high error, absent prior beliefs, enabled attention, no cooldown:
    # resource state is the only reason these otherwise eligible operations stop.
    assessment = assess_curiosity({'evaluator':'prediction_error_v1','evaluator_version':1,
        'aggregate':{'status':'evaluated','mean_normalized_error':1,'coverage':1}},
        state, 'observe', state, {})
    assert assessment['level'] == 'VERY_HIGH'
    assert assessment['suppression_reason'] == reason
    m = Memory(home/'memory.sqlite3')
    try:
        source(m)
        run = Consolidator(m).run(state)
        assert run['status'] == ('suppressed' if reason else 'completed')
        assert run['result']['reason'] == reason
        tid = m.record_transition_experience(state_before=state, action='observe', state_after=state,
            outcome={}, legacy_reward=0, started_at=1, completed_at=2, curiosity=assessment)[1]
        reflected = []
        assert CuriosityAttention(m).execute(tid, lambda: reflected.append(1), enabled=True) is (reason is None)
        assert len(reflected) == int(reason is None)
        assert calls == {'battery':1, 'network':1}
    finally:
        m.close()
