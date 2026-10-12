"""I30 pytest integration for the standalone technical scenario.

Exercises the same assertions as `python -m tests.evaluation_scenario`
so a green hosted run is meaningful even where the workflow does not
launch the standalone directly. Everything runs in disposable roots
with synthetic technical fixtures; nothing here is empirical
evidence and the registered suite is never dispatched.
"""
import json
import subprocess
import sys

from tests.evaluation_scenario import CLASSIFICATION, run_all

EXPECTED_CHECKS = {
    'a_prequential_completed', 'a_score_journal_durable_prefix',
    'a_actual_updates_confirmed', 'b_prequential_completed',
    'b_exposure_recorded', 'b_only_rest_changes_at_321',
    'a_frozen_assay_probes', 'frozen_state_unchanged',
    'c_robustness_subcases', 'd_guards_preserved',
    'd_task_utility_external', 'd_random_eligible_separate_trajectory',
    'artifact_published_and_read', 'recorded_replay_without_cognition',
    'interrupted_partial_evidence_retained', 'failed_run_status_honest',
    'skipped_attempts_never_samples',
}


def test_evaluation_scenario_all_families(tmp_path):
    result = run_all(base=tmp_path / 'scenario')
    assert result['classification'] == 'TECHNICAL_FIXTURE' == CLASSIFICATION
    assert result['passed'], result['checks']
    assert {check['name'] for check in result['checks']} == EXPECTED_CHECKS
    assert all(check['passed'] for check in result['checks'])
    families = result['families']
    assert families['A']['protocol'] == 'PREQUENTIAL'
    assert families['A']['frozen_probes'] == 2
    assert families['B']['status'] == 'COMPLETED'
    assert families['C'] == {'fresh': 4, 'contradictory': 4,
                             'unavailable': 4, 'stale': 4}
    assert families['D']['pairing'] == \
        'not_paired_divergent_policy_trajectories'
    # The report is bounded and JSON-serializable, with no scientific
    # verdict field of any kind.
    encoded = json.dumps(result, sort_keys=True)
    assert len(encoded) < 16384
    assert 'finding' not in encoded and 'POSITIVE' not in encoded


def test_evaluation_scenario_module_entrypoint():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [sys.executable, '-m', 'tests.evaluation_scenario'],
        capture_output=True, text=True, cwd=str(repo_root), timeout=600)
    assert completed.returncode == 0, completed.stderr[-2000:]
    result = json.loads(completed.stdout)
    assert result['classification'] == 'TECHNICAL_FIXTURE'
    assert result['passed']


# ------------------------------------------- temporary fixture cleanup (I30)
#
# run_all() with no base owns the temporary directory it creates and
# must remove it on success and on exception. A caller-provided base
# is caller-owned and must never be removed. Spawned workers must be
# terminated and reaped on the timeout path so no process can retain
# the storage being cleaned up.

import os
import tempfile
import time
from pathlib import Path

import pytest

import tests.evaluation_scenario as scenario


def _leftover_owned(scratch):
    return sorted(Path(scratch).glob('seed-i30-scenario-*'))


def test_owned_temp_directory_removed_after_success(tmp_path, monkeypatch):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))
    result = scenario.run_all()
    assert result['passed'] and len(result['checks']) == 17
    assert _leftover_owned(scratch) == []


def test_owned_temp_directory_removed_after_exception(tmp_path, monkeypatch):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))

    def explode(name):
        raise RuntimeError('injected failure')

    monkeypatch.setattr(scenario, '_load', explode)
    with pytest.raises(RuntimeError, match='injected failure'):
        scenario.run_all()
    assert _leftover_owned(scratch) == []


def test_caller_owned_base_preserved(tmp_path):
    base = tmp_path / 'scenario'
    base.mkdir()
    sentinel = base / 'caller-owned.txt'
    sentinel.write_text('keep')
    result = scenario.run_all(base=base)
    assert result['passed']
    assert base.is_dir() and sentinel.read_text() == 'keep'


def _sleeping_child(pipe):
    try:
        time.sleep(60)
    finally:
        pipe.close()


def _zombie_children():
    zombies = []
    for stat in Path('/proc').glob('[0-9]*/stat'):
        try:
            parts = stat.read_text().split()
        except OSError:
            continue
        if parts[3] == str(os.getpid()) and parts[2] == 'Z':
            zombies.append(parts[0])
    return zombies


def test_spawn_timeout_reaps_worker():
    checks = []
    outcome = scenario._spawn(_sleeping_child, (), checks,
                              'sleeping_worker', timeout=2)
    assert outcome is None
    assert any(check['name'] == 'sleeping_worker' and not check['passed']
               for check in checks)
    if Path('/proc').is_dir():  # Linux: a reaped worker leaves no zombie
        assert _zombie_children() == []
    assert scenario.multiprocessing.active_children() == []


def test_scenario_subprocess_leaves_no_owned_directories(tmp_path):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    env = dict(os.environ, TMPDIR=str(scratch), TMP=str(scratch),
               TEMP=str(scratch))
    repo_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [sys.executable, '-m', 'tests.evaluation_scenario'],
        capture_output=True, text=True, cwd=str(repo_root), env=env,
        timeout=600)
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert json.loads(completed.stdout)['passed']
    assert _leftover_owned(scratch) == []
