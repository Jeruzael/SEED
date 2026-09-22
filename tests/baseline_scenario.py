"""B0 policy control with paired B1 observations. No sensors or installed data.

Run: .venv/bin/python -m tests.baseline_scenario
All filesystem writes are confined to a TemporaryDirectory.
"""
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from seed.organism import SeedOrganism

STATE_A = {'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75,'local_hour':12}
STATE_B = {'battery_pct':10,'charging':False,'load_ratio':1,'disk_free_pct':5,'local_hour':2}
SEQUENCE = ['A','A','B','A','B','B','B','B']


def prediction_structure(db):
    """Structural support/availability counts only; never compare with outcomes."""
    predictions = [json.loads(row[0]) for row in db.execute(
        'SELECT prediction_json FROM transitions WHERE prediction_json IS NOT NULL ORDER BY id')]
    available = unavailable = 0
    groups = {'action_specific':0, 'global':0, 'persistence':0}
    evidence = {}
    for prediction in predictions:
        for name, signal in prediction['signals'].items():
            evidence.setdefault(name, []).append(signal['evidence_count'])
            if signal['status'] == 'unavailable':
                unavailable += 1
                continue
            available += 1
            method = signal['method']
            group = 'action_specific' if method.startswith('action_') else 'global' if method.startswith('global_') else 'persistence'
            groups[group] += 1
    total = available + unavailable
    return {'prediction_count':len(predictions), 'available':available, 'unavailable':unavailable,
            'coverage_pct':100 * available / total if total else None,
            'method_groups':groups, 'evidence_counts':evidence,
            'prediction_error_count':db.execute('SELECT count(*) FROM transitions WHERE prediction_error_json IS NOT NULL').fetchone()[0]}


def run_scenario(home: Path) -> dict:
    now = [1_000_000_000.0]
    # Same decision contexts as B0, repeated for immediate post-action observation.
    pending = [STATE_A, *[STATE_A if label == 'A' else STATE_B for label in SEQUENCE for _ in range(2)]]
    def perceive(_body):
        return {**pending.pop(0), 'wall_time':now[0], 'load_5m_ratio':0,
                'network':False, 'hostname':'synthetic-host', 'machine':'synthetic-arch', 'macos':'synthetic-os'}
    with patch('seed.body.Body.perceive',perceive), patch('seed.learner.random.random',return_value=.5), \
            patch('seed.learner.random.choice',side_effect=lambda choices:choices[0]), \
            patch('seed.organism.time.time',side_effect=lambda:now[0]):
        core = SeedOrganism(home)
        try:
            core.learner.epsilon = 0  # Fixed exploitation control; default remains .15.
            core.awaken()
            delays = []
            for _ in SEQUENCE:
                now[0] += 1
                delays.append(core.cycle())
            core.sleep(reason='process_stop')
            db = core.memory.db
            counts = dict(db.execute('SELECT event,COUNT(*) FROM episodes GROUP BY event').fetchall())
            distribution = dict(db.execute("SELECT action,COUNT(*) FROM episodes WHERE event='experience' GROUP BY action").fetchall())
            values = [dict(row) for row in db.execute('SELECT * FROM q_values ORDER BY state_key,action')]
            action_sequence = [row[0] for row in db.execute("SELECT action FROM episodes WHERE event='experience' ORDER BY id")]
            metrics = {
                'observation_count':counts['experience'], 'action_distribution':distribution,
                'context_coverage':len({row['state_key'] for row in values}),
                'policy_coverage':len(values), 'concept_count':core.memory.stats()['concepts'],
                'lifecycle_counts':counts, 'q_values':values, 'action_sequence':action_sequence,
                'returned_intervals_seconds':delays,
                'transition_count':db.execute('SELECT count(*) FROM transitions').fetchone()[0],
                'autonomous_perception_count':db.execute("SELECT count(*) FROM events WHERE category='PERCEPTION'").fetchone()[0],
                'prediction_structure':prediction_structure(db),
                'database_page_size':db.execute('PRAGMA page_size').fetchone()[0],
                'database_page_count':db.execute('PRAGMA page_count').fetchone()[0],
            }
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall()
        finally:
            core.close()
    metrics['database_footprint'] = {
        label:(home / name).stat().st_size if (home / name).exists() else 0
        for label,name in [('main_bytes','memory.sqlite3'),('wal_bytes','memory.sqlite3-wal'),('shm_bytes','memory.sqlite3-shm')]
    }
    return metrics


def main():
    with tempfile.TemporaryDirectory(prefix='seed-b0-') as directory:
        result=run_scenario(Path(directory).resolve())
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__ == '__main__':
    main()
