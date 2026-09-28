import json
from pathlib import Path
import pytest
from tests.decision_scenario import run_scenario


def test_literal_b8_acceptance_and_saved_comparison(tmp_path):
    result=run_scenario(tmp_path)
    c=result['cases']
    assert c['q_fallback']['selected_action']=='reflect' and c['q_fallback']['policy_basis']=='legacy_q'
    assert c['low_disk']['selected_action']=='rest' and c['low_disk']['reasons']['consolidate']==['low_disk']
    assert c['load_battery']['reasons']['reflect']==['high_load','low_battery']
    assert c['guard_equality']['reasons']['consolidate']==[] and c['charging']['reasons']['reflect']==[]
    assert c['conflict']['selected_action']=='observe'
    assert c['conflict']['utilities']==pytest.approx(dict(observe=.7425,reflect=.5175,consolidate=.6175,rest=.6175))
    assert c['partial']['utilities']['observe']==pytest.approx(.5783333333333334)
    for prefix in ('explore_','fallback_tie_'):
        assert [c[prefix+str(i)]['selected_action'] for i in (0,1)]==['observe','rest']
    assert [c['composite_tie_'+str(i)]['selected_action'] for i in (0,3)]==['observe','rest']
    assert c['epsilon_equality']['selection_mode']=='fallback'
    assert c['stale_history']['policy_basis']=='legacy_q' and c['fresh_history_boundary']['policy_basis']=='composite'
    assert c['completed']['q']==pytest.approx([.655,5]) and c['completed']['prediction_identity'] and c['completed']['digest_matches']
    assert c['owner_low_disk']==dict(status='suppressed',reason='low_disk',decision_count=1)
    assert c['restart']==dict(unchanged=True,count=1)
    assert c['age_5.0']['status']=='completed'
    assert c['age_5.001']==dict(status='skipped',delay=8,reason='stale_decision',perceptions=1,decisions=0,q_rows=0)
    artifact=Path(__file__).parents[1]/'docs/baselines/seed-0.2-b8-comparison.json'
    assert len(result['historical_artifact_sha256'])==8
    assert result==json.loads(artifact.read_text())
