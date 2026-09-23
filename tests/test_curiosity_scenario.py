import json
from pathlib import Path
import pytest


def test_real_b5_scenario_and_b4_compatibility(tmp_path):
    from tests.curiosity_scenario import run_scenario
    from tests.world_model_scenario import run_scenario as world
    from tests.baseline_scenario import run_scenario as baseline
    from tests.prediction_error_scenario import run_scenario as evaluation
    result=run_scenario(tmp_path/'curiosity')
    cases=result['cases']
    allowed=cases['high_allowed']
    assert allowed['assessment']['score']==pytest.approx(.925)
    assert allowed['assessment']['reflection_completed']==1
    assert allowed['reflection_provenance']==['curiosity_triggered']
    assert allowed['q_value']==pytest.approx(.502) and allowed['reward']==-.4
    for name,reason in [('high_load','high_load'),('low_battery','low_battery'),('low_disk','low_disk'),
                        ('policy_reflect','already_reflected'),('owner_disabled','disabled_by_owner')]:
        c=cases[name]['assessment']
        assert c['level']=='VERY_HIGH' and c['suppression_reason']==reason and c['reflection_completed']==0
    assert cases['zero_error']['assessment']['score']==0
    assert cases['partial']['assessment']['score']==.25
    assert cases['unavailable']['assessment']['score'] is None
    for case in cases.values():
        assert case['perceptions']==2 and case['transition_count']==1
        assert case['assessment_count']==1 and case['world_processed']==1
        assert case['delay']==(12 if case['action']=='reflect' else 8)
    reference=json.loads((Path(__file__).parents[1]/'docs/baselines/seed-0.2-b4-comparison.json').read_text())
    current_world=world(tmp_path/'world')
    for key,value in reference['world_model'].items():
        if key!='schema_version':assert current_world[key]==value
    assert current_world['schema_version']==5
    current=baseline(tmp_path/'baseline')
    for key,value in reference['control'].items():
        if key not in ('database_footprint','database_page_count'):assert current[key]==value
    scores=evaluation(tmp_path/'scores')
    assert scores['metrics']==reference['evaluation_snapshot']['metrics']
    for name,case in scores['cases'].items():
        for key,value in reference['evaluation_snapshot']['cases'][name].items():
            if key!='schema_version':assert case[key]==value
