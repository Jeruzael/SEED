import json
from pathlib import Path
import pytest


def test_deterministic_semantic_revision_scenario(tmp_path):
    from tests.semantic_scenario import run_scenario
    result=run_scenario(tmp_path)
    assert result['schema_version']==5
    stages=result['stages']
    assert [s['run']['created_count'] for s in stages]==[2,0,0,0]
    assert [s['run']['revised_count'] for s in stages]==[0,0,0,2]
    assert [s['run']['weakened_count'] for s in stages]==[0,0,2,0]
    assert [s['memories'][0]['revision'] for s in stages]==[1,1,2,3]
    assert [s['memories'][0]['evidence_count'] for s in stages]==[8,8,26,27]
    assert stages[0]['memories']==stages[1]['memories']
    assert stages[2]['memories'][0]['confidence']==pytest.approx(.95*8/26)
    assert stages[3]['memories'][0]['confidence']==pytest.approx(.95*9/27)
    assert [h['status'] for h in result['history']]==['active','weakened','active','weakened']
    assert result['retained']==dict(episodes=27,transitions=27,world_beliefs=2,
                                   world_model_processed=27,semantic_memories=2,semantic_memory_history=4)


def test_b5_compatibility_and_saved_b6_artifact(tmp_path):
    from tests.semantic_scenario import run_comparison
    result=run_comparison(tmp_path)
    reference=json.loads((Path(__file__).parents[1]/'docs/baselines/seed-0.2-b5-comparison.json').read_text())
    assert result['curiosity']['cases']==reference['curiosity']['cases']
    prior=json.loads((Path(__file__).parents[1]/'docs/baselines/seed-0.2-b4-comparison.json').read_text())
    assert result['world_model']['metrics']==reference['world_metrics']
    assert result['evaluation_snapshot']['metrics']==reference['prediction_error_metrics']
    for key,value in prior['world_model'].items():
        if key!='schema_version':assert result['world_model'][key]==value
    for key,value in reference['control'].items():
        if key not in ('database_footprint','database_page_count'):assert result['control'][key]==value
    assert result['evaluation_snapshot']['metrics']==prior['evaluation_snapshot']['metrics']
    for name,case in prior['evaluation_snapshot']['cases'].items():
        for key,value in case.items():
            if key!='schema_version':assert result['evaluation_snapshot']['cases'][name][key]==value
    saved=Path(__file__).parents[1]/'docs/baselines/seed-0.2-b6-comparison.json'
    assert result==json.loads(saved.read_text())
