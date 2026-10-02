import copy
import pytest


def test_strict_spec(foundation_module, plan_body):
    s = foundation_module('specs')
    spec = dict(schema='b10_experiment_v1', experiment_id='technical-fixture', version=1, family='A',
                scenario_version=2, rule_version=2, protocol='PREQUENTIAL', driver='seed-cycle-v1',
                source_commit='1' * 40, lock_digest='2' * 64, profile_digest='3' * 64,
                fixture='fresh-v7', fixture_digest='4' * 64, seeds=[0], rng='sha256-mt19937-v1',
                training=0, measured=1, clock='staged-v1', windows=plan_body['windows'],
                metrics=plan_body['metrics'], baselines=plan_body['baselines'], variant='seed',
                maintenance='every-eight', observation_version=1, action_version=1,
                limits={'transitions': 1024, 'run_seconds': 120})
    assert s.validate_spec(spec).body
    for changes in [{'schema': 'foreign'}, {'version': True}, {'experiment_id': '../code'}, {'metrics': [{'id':'os.system','version':1}]},
                    {'limits': {'transitions': 1025}}, {'seeds': list(range(9))}, {'training':513},
                    {'measured':1025}, {'network':True}, {'protocol':'run'}, {'source_commit':'bad'}]:
        with pytest.raises(ValueError):
            s.validate_spec({**spec, **changes})
    s.require_plan(s.validate_spec(spec), foundation_module('analysis').validate_plan(plan_body))
    changed = copy.deepcopy(plan_body)
    changed['seeds'] = [1]
    with pytest.raises(ValueError):
        s.require_plan(s.validate_spec(spec), foundation_module('analysis').validate_plan(changed))
