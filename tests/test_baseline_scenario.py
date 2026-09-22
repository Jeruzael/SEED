import pytest
from tests.baseline_scenario import run_scenario


def test_controlled_sequence_has_hand_calculated_policy(tmp_path):
    metrics=run_scenario(tmp_path/'control')
    assert metrics['observation_count']==8
    assert metrics['transition_count']==8
    assert metrics['autonomous_perception_count']==16
    prediction=metrics['prediction_structure']
    assert prediction['available']==32 and prediction['unavailable']==0
    assert prediction['coverage_pct']==100
    assert prediction['method_groups']=={'action_specific':8,'global':16,'persistence':8}
    assert prediction['prediction_count']==8 and prediction['prediction_error_count']==8
    for counts in prediction['evidence_counts'].values():
        assert counts==[0,0,2,3,4,5,6,7]
    assert metrics['action_distribution']=={'observe':4,'reflect':1,'consolidate':1,'rest':2}
    assert metrics['context_coverage']==2 and metrics['policy_coverage']==5
    assert metrics['concept_count']==0
    assert metrics['lifecycle_counts']=={'experience':8,'sleep':1,'wake':1}
    assert metrics['action_sequence']==['observe','observe','observe','observe','reflect','consolidate','rest','rest']
    assert metrics['returned_intervals_seconds']==[8,8,8,8,12,20,35,35]
    rows={(r['state_key'],r['action']):(r['value'],r['visits']) for r in metrics['q_values']}
    assert rows[('charging|calm|ok|day','observe')]==pytest.approx((.2018844,3))
    assert rows[('low|busy|tight|night','observe')]==pytest.approx((-.216,1))
    assert rows[('low|busy|tight|night','reflect')]==pytest.approx((-.216,1))
    assert rows[('low|busy|tight|night','consolidate')]==pytest.approx((-.036,1))
    assert rows[('low|busy|tight|night','rest')]==pytest.approx((.6552,2))
    assert metrics['database_footprint']['main_bytes']==metrics['database_page_size']*metrics['database_page_count']
    assert metrics['database_footprint']['wal_bytes']==0


def test_simulation_cli_works_with_system_temporary_directory():
    import json
    import subprocess
    import sys
    result=subprocess.run([sys.executable,'-m','tests.baseline_scenario'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['observation_count']==8
