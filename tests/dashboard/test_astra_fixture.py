import sqlite3
import pytest
from dashboard.services.seed_service import SeedService


def test_fixture_requires_disposable_destination(tmp_path):
    from tests.dashboard.astra_fixture import build
    with pytest.raises(ValueError):build(tmp_path.parent/'not-empty', 'unknown')
    with pytest.raises(ValueError):build(__import__('pathlib').Path.home()/'.seed','empty')


@pytest.mark.parametrize('case',['empty','predictions','models','self','decisions','boundary','legacy','legacy1','legacy2','counts','combined'])
def test_deterministic_fixture_is_inspectable_and_readonly(tmp_path,case):
    from tests.dashboard.astra_fixture import build
    home=tmp_path/case;manifest=build(home,case);s=SeedService(home,clock=lambda:1700000000)
    with sqlite3.connect(home/'memory.sqlite3') as db:before=list(db.iterdump())
    for read in (s.predictions,s.world_beliefs,s.curiosity_assessments,s.semantic_memories,s.consolidation_runs,s.self_model,s.decisions):read()
    if case in ('predictions','combined'):
        full=s.prediction(manifest['full'])
        assert full['evaluation']['data']['aggregate']['accuracy_score']==.791875
        assert s.prediction(manifest['zero'])['evaluation']['data']['aggregate']['mean_normalized_error']==0
    if case=='decisions':
        assert s.decisions(limit=2)['next_cursor']==122
        assert s.decision(124)['reason']=='invalid_decision'
        assert s.decision(121)['record']['selected_action']=='observe'
        assert s.decision(123)['record']['selected_action']=='rest'
    if case=='boundary':assert s.predictions(limit=1)['items'][0]['transition_id']==2**63-1
    if case=='models':
        assert s.semantic_memory(manifest['semantic'])['revision']==3
        assert s.semantic_history(manifest['semantic'])['items'][0]['revision']==2
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before
