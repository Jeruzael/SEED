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
