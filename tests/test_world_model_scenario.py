import json
from pathlib import Path
import pytest


def test_controlled_belief_revision_and_unchanged_b3_results(tmp_path):
    from tests.world_model_scenario import run_scenario
    from tests.baseline_scenario import run_scenario as baseline
    from tests.prediction_error_scenario import run_scenario as evaluation
    result=run_scenario(tmp_path/'world')
    assert result['one_sample']=={'beliefs':0,'pending':8}
    assert result['established_confidence']==.95
    assert result['metrics']==dict(belief_count=8,beliefs_by_signal={'battery_pct':2,'load_ratio':2,
        'disk_free_pct':2,'network_reachable':2},beliefs_by_scope={'global':4,'action':4},
        mean_confidence=pytest.approx(.95*20/22),processed_transitions=22,valid_signal_samples=88,
        scoped_evidence_count=176,total_scoped_contradictions=16,unprocessed_eligible_transitions=0)
    for b in result['beliefs']:
        assert b['evidence_count']==22 and b['contradiction_count']==2
        assert b['confidence']==pytest.approx(.95*20/22)
        assert b['source_first_transition_id']==1 and b['source_last_transition_id']==22
        if b['signal']=='network_reachable':
            assert b['value']['true_count']==20 and b['value']['false_count']==2
        else:
            assert b['value']['mean_delta']==pytest.approx(18/22)
            assert b['value']['mean_absolute_delta']==1
    reference=json.loads((Path(__file__).parents[1]/'docs/baselines/seed-0.2-b3-evaluation.json').read_text())
    current=baseline(tmp_path/'baseline')
    for key,value in reference['control'].items():
        if key not in ('database_footprint','database_page_count'):
            assert current[key]==value
    scores=evaluation(tmp_path/'scores')
    expected=reference['evaluation_snapshot']
    assert scores['metrics']==expected['metrics']
    for name,case in scores['cases'].items():
        for key,value in expected['cases'][name].items():
            if key!='schema_version': assert case[key]==value
        assert case['schema_version']==5
