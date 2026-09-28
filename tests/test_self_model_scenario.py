import json
from pathlib import Path
import subprocess
import sys
import pytest


def test_literal_self_model_acceptance_and_saved_artifact(tmp_path):
    from tests.self_model_scenario import run_scenario
    p=run_scenario(tmp_path)
    assert p['before_first_cycle']=='awaiting_first_cycle'
    assert p['insufficient_score']['status']=='insufficient_evidence'
    assert p['metrics']['coverage']==pytest.approx(5/12)
    assert p['metrics']['error']==pytest.approx(.06)
    assert p['metrics']['accuracy']==pytest.approx(.94)
    assert p['metrics']['samples']==2
    assert p['fresh_resource_status']=='available'
    assert p['stale_resource_status']=='stale'
    assert p['stale_score_status']=='stale'
    assert p['failure_count']==1
    assert p['restart_payload_equal'] and p['restart_no_update']
    assert p['new_cycle_advances'] and p['failed_write_preserves_snapshot']
    assert p['suppressed_action_selectable'] and p['suppression_reason']=='low_disk'
    assert p['policy_equal'] and p['perceptions_per_run']==4
    artifact=json.loads((Path(__file__).parents[1]/'docs/baselines/seed-0.2-b7-comparison.json').read_text())
    assert p['schema_version']==7
    artifact['self_model']['schema_version']=7
    assert p==artifact['self_model']


def test_standalone_cli_is_stable_strict_json():
    outputs=[subprocess.check_output([sys.executable,'-m','tests.self_model_scenario'],text=True) for _ in range(2)]
    assert outputs[0]==outputs[1]
    p=json.loads(outputs[0],parse_constant=lambda value:pytest.fail(value))
    assert p['policy_equal'] is True
