import json
import subprocess
import sys
import pytest


def test_historical_prediction_to_scoring_snapshot(tmp_path):
    from tests.prediction_error_scenario import run_scenario
    result=run_scenario(tmp_path)
    full=result['cases']['full']
    assert full['prediction']['signals']['battery_pct']['value']==73
    assert full['prediction']['signals']['load_ratio']['value']==pytest.approx(.4)
    assert full['prediction']['signals']['disk_free_pct']['value']==49
    assert full['prediction']['signals']['network_reachable']['probability_true']==.5
    assert full['evaluation']['signals']['battery_pct']['signed_error']==-2
    assert full['evaluation']['signals']['disk_free_pct']['absolute_error']==1
    assert full['evaluation']['signals']['load_ratio']['normalized_error']==pytest.approx(.2)
    assert full['evaluation']['signals']['network_reachable']['brier_error']==.25
    assert full['evaluation']['aggregate']['mean_normalized_error']==pytest.approx(.12)
    assert full['evaluation']['aggregate']['accuracy_score']==pytest.approx(.88)
    assert full['evaluation']['aggregate']['coverage']==1
    partial=result['cases']['partial']['evaluation']['aggregate']
    assert partial['coverage']==.25 and partial['accuracy_score']==1
    empty=result['cases']['unavailable']['evaluation']['aggregate']
    assert empty['coverage']==0 and empty['mean_normalized_error'] is None and empty['accuracy_score'] is None
    for case in result['cases'].values():
        assert case['delay']==8 and case['q_value']==pytest.approx(.655) and case['q_visits']==5
        assert case['perceptions']==2 and case['prediction_calls']==1
        assert case['schema_version']==6 and case['historical_errors_unchanged'] is True
    metrics=result['metrics']
    assert metrics['mean_coverage']==pytest.approx(5/12)
    assert metrics['scored_transitions']==2 and metrics['transitions']==3
    assert metrics['mean_normalized_error']==pytest.approx(.06)
    assert metrics['mean_accuracy_score']==pytest.approx(.94)
    assert metrics['numeric_mae']['battery_pct']=={'samples':2,'value':1}
    assert metrics['numeric_mae']['disk_free_pct']=={'samples':1,'value':1}
    assert metrics['numeric_mae']['load_ratio']['value']==pytest.approx(.2)
    assert metrics['network_classification_accuracy']=={'samples':1,'value':0}
    assert metrics['network_mean_brier_error']=={'samples':1,'value':.25}
    json.dumps(result,allow_nan=False)


def test_prediction_error_snapshot_cli():
    completed=subprocess.run([sys.executable,'-m','tests.prediction_error_scenario'],capture_output=True,text=True,timeout=10)
    assert completed.returncode==0,completed.stderr
    assert json.loads(completed.stdout)['metrics']['transitions']==3
