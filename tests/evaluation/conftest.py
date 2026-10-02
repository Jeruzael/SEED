import importlib
from pathlib import Path
import pytest


@pytest.fixture
def foundation_module():
    def load(name):
        # Fail as an assertion on the missing approved behavior, before import.
        assert Path('development/evaluation', name + '.py').is_file(), 'foundation behavior missing: ' + name
        return importlib.import_module('development.evaluation.' + name)
    return load


@pytest.fixture
def plan_body():
    return dict(schema='b10_analysis_plan_v1', experiment_id='technical-fixture', experiment_version=1,
                analysis_plan_version=1, members=[dict(id='member-0', family='A', scenario_version=2,
                rule_version=2, protocol='PREQUENTIAL', variant='seed', seed=0, training=0, measured=1)],
                metrics=[dict(id='prediction.numeric-mae', version=1)], seeds=[0],
                populations=[dict(id='all', phase='measured', action='all', signal='load_ratio')],
                windows=[dict(id='whole', start=1, end=1, unit='ordinal')],
                baselines=[dict(id='persistence', version=1)], exclusions=[],
                eligibility='registered_support', coverage='all_opportunities', aggregation='ordered_fsum',
                standardization='equal_qualifying_actions', missing_rules='unavailable_with_reason',
                thresholds=[], questions=[dict(id='prediction', metrics=['prediction.numeric-mae'],
                rule='descriptive_only', reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE')], exploratory=True)
