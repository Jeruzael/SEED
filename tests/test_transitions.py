import json
import sqlite3
import pytest
from seed.memory import Memory


def test_outcome_describes_changes_without_inventing_missing_values():
    from seed.transitions import describe_outcome
    before = {'battery_pct':76, 'load_ratio':.22, 'charging':False,
              'same':8, 'unknown':None, 'removed':3, 'flag':False}
    after = {'battery_pct':75, 'load_ratio':.31, 'charging':True,
             'same':8, 'unknown':None, 'added':None, 'flag':0}
    outcome = describe_outcome(before, after)
    assert list(outcome) == sorted(before.keys() | after.keys())
    assert outcome['battery_pct'] == {'before':76, 'after':75,
                                     'before_present':True, 'after_present':True, 'delta':-1}
    assert outcome['load_ratio']['delta'] == pytest.approx(.09)
    assert outcome['charging']['changed'] is True and 'delta' not in outcome['charging']
    assert outcome['flag']['changed'] is True  # bool is not numeric zero
    assert outcome['same']['delta'] == 0
    assert outcome['unknown']['changed'] is False
    assert outcome['removed'] == {'before':3, 'after':None, 'before_present':True,
                                  'after_present':False, 'changed':True}
    assert outcome['added'] == {'before':None, 'after':None, 'before_present':False,
                                'after_present':True, 'changed':True}
    assert json.loads(json.dumps(outcome, allow_nan=False)) == outcome


def test_validated_state_detaches_nested_observation():
    from seed.transitions import validated_state
    raw = {'battery_pct':None, 'charging':None, 'extra':{'values':[1,2]}}
    copied = validated_state(raw)
    raw['extra']['values'].append(3)
    assert copied == {'battery_pct':None, 'charging':None, 'extra':{'values':[1,2]}}


@pytest.mark.parametrize('state', [[], {'load_ratio':float('nan')},
                                 {'x':float('inf')}, {1:'ambiguous'}, {'x':object()}])
def test_invalid_observation_is_rejected(state):
    from seed.transitions import validated_state
    with pytest.raises((ValueError, TypeError)):
        validated_state(state)


def test_numeric_delta_overflow_remains_json_serializable():
    from seed.transitions import describe_outcome
    result = describe_outcome({'x':-1e308}, {'x':1e308})
    assert result['x']['delta'] is None
    assert result['x']['delta_unavailable'] is True
    json.dumps(result, allow_nan=False)


def record(memory):
    return memory.record_transition_experience(
        state_before={'battery_pct':76}, action='observe', state_after={'battery_pct':75},
        outcome={'battery_pct':{'before':76,'after':75,'delta':-1}}, legacy_reward=.45,
        started_at=1000, completed_at=1002, note='context=high|calm|ok|day')


def test_transition_preserves_exact_observations_and_episode_link(home):
    m = Memory(home / 'memory.sqlite3')
    try:
        episode_id, transition_id = record(m)
        row = dict(m.db.execute('SELECT * FROM transitions WHERE id=?', (transition_id,)).fetchone())
        assert row['episode_id'] == episode_id
        assert row['started_at'] == 1000 and row['completed_at'] == 1002
        assert row['action'] == 'observe' and row['legacy_reward'] == .45
        assert json.loads(row['state_before_json']) == {'battery_pct':76}
        assert json.loads(row['state_after_json']) == {'battery_pct':75}
        assert json.loads(row['outcome_json'])['battery_pct']['delta'] == -1
        assert row['prediction_json'] is None and row['prediction_error_json'] is None
        episode = m.recent_episodes(1)[0]
        assert episode['event'] == 'experience' and episode['id'] == episode_id
        assert episode['ts'] == 1002 and episode['reward'] == .45
        assert json.loads(episode['state_json']) == {'battery_pct':76}
    finally:
        m.close()


def test_transition_insert_failure_rolls_back_both_records(home):
    m = Memory(home / 'memory.sqlite3')
    try:
        m.db.execute("""CREATE TRIGGER fail_transition BEFORE INSERT ON transitions
                     BEGIN SELECT RAISE(ABORT, 'injected failure'); END""")
        with pytest.raises(sqlite3.IntegrityError, match='injected failure'):
            record(m)
        assert m.db.execute('SELECT count(*) FROM episodes').fetchone()[0] == 0
        assert m.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 0
        m.db.execute('DROP TRIGGER fail_transition')
        record(m)  # connection remains usable after rollback
    finally:
        m.close()


def test_historical_episode_loads_without_fabricated_transition(legacy_home):
    from dashboard.services.seed_service import SeedService
    m = Memory(legacy_home / 'memory.sqlite3')
    try:
        assert m.recent_episodes(1)[0]['note'] == 'context=charging|calm|ok|day'
        assert m.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 0
        assert SeedService(legacy_home).memory(1)['action'] == 'observe'
    finally:
        m.close()
