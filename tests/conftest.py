import json
import sqlite3
from pathlib import Path
import pytest

@pytest.fixture
def legacy_home(tmp_path):
    home = tmp_path / 'seed'
    home.mkdir()
    with sqlite3.connect(home / 'memory.sqlite3') as db:
        db.executescript((Path(__file__).parent / 'fixtures/legacy.sql').read_text())
        db.execute('INSERT INTO meta VALUES(?,?)', ('identity', json.dumps({'name':'SEED','generation':0,'born_at':1000})))
        state = json.dumps({'battery_pct':80,'charging':True,'load_ratio':0.1,'disk_free_pct':75,'local_hour':12,'wall_time':1001})
        db.execute('INSERT INTO episodes(ts,event,state_json,action,reward,note) VALUES(?,?,?,?,?,?)', (1001,'experience',state,'observe',0.45,'context=charging|calm|ok|day'))
        db.execute('INSERT INTO meta VALUES(?,?)', ('last_state', state))
        db.execute('INSERT INTO concepts VALUES(?,?,?,?,?)', ('typical_compute_pressure',.45,10,'{"mean_load_ratio":0.1}',1002))
        db.execute('INSERT INTO q_values VALUES(?,?,?,?)', ('charging|calm|ok|day','observe',.081,1))
    return home

@pytest.fixture
def home(tmp_path):
    from seed.memory import Memory
    home = tmp_path / 'seed'
    memory = Memory(home / 'memory.sqlite3')
    memory.close()
    return home
