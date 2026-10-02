import copy
import os
from pathlib import Path
import pytest


class ClosedRoot:
    def __init__(self, path):
        self.path = path
        self.synced = []
    def open(self, kind, identity, mode):
        assert kind in ('plan', 'freeze') and mode in ('read', 'create')
        return os.open(self.path / (identity + '.' + kind), os.O_RDONLY if mode == 'read' else os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    def sync(self):
        fd = os.open(self.path, os.O_RDONLY)
        os.fsync(fd)
        os.close(fd)
        self.synced.append(True)


def test_inventory_admission(foundation_module, plan_body):
    a = foundation_module('analysis')
    p = a.validate_plan(plan_body)
    inventory = a.expand_inventory(p)
    assert [(x.identity, x.metric, x.member) for x in inventory] == [('member-0:prediction.numeric-mae:all:whole', 'prediction.numeric-mae', 'member-0')]
    for update in [{'seeds': list(range(9))}, {'members': plan_body['members'] * 33},
                   {'measured': 1025}, {'extra': 'bad'}, {'frozen_before_execution': True}]:
        bad = copy.deepcopy(plan_body)
        if 'measured' in update:
            bad['members'][0].update(update)
        else:
            bad.update(update)
        with pytest.raises(ValueError):
            a.validate_plan(bad)
    large = copy.deepcopy(plan_body)
    large['populations'] = [dict(id='p' + str(i), phase='measured', action='all', signal='load_ratio') for i in range(1000)]
    with pytest.raises(ValueError):
        a.validate_plan(large)


def test_freeze_precedes_dispatch(foundation_module, plan_body, tmp_path):
    a = foundation_module('analysis')
    p = a.validate_plan(plan_body)
    root = ClosedRoot(tmp_path)
    with pytest.raises(ValueError):
        a.require_frozen(p, root)
    f = a.freeze_plan(p, root)
    assert len(f.digest) == 64 and root.synced
    assert a.require_frozen(p, root) == f
    with pytest.raises(ValueError):
        a.freeze_plan(p, root)
    (tmp_path / (f.digest + '.plan')).write_bytes(b'{}\n')
    with pytest.raises(ValueError):
        a.require_frozen(p, root)


@pytest.mark.parametrize('field', ['experiment_version', 'analysis_plan_version', 'metrics', 'populations', 'windows',
                                  'seeds', 'baselines', 'exclusions', 'eligibility', 'coverage', 'aggregation',
                                  'standardization', 'missing_rules', 'thresholds', 'questions', 'exploratory', 'members'])
def test_every_analysis_field_is_frozen(foundation_module, plan_body, tmp_path, field):
    a = foundation_module('analysis')
    root = ClosedRoot(tmp_path)
    p = a.validate_plan(plan_body)
    a.freeze_plan(p, root)
    bad = copy.deepcopy(plan_body)
    if field in ('experiment_version', 'analysis_plan_version'):
        bad[field] += 1
    elif field == 'exploratory':
        bad[field] = False
    else:
        bad[field] = None
    with pytest.raises(ValueError):
        # Either admission fails or the original durable receipt cannot bind it.
        a.require_frozen(a.validate_plan(bad), root)


def test_inventory_limits_apply_per_member(foundation_module, plan_body):
    a = foundation_module('analysis')
    r = foundation_module('registry')
    plan_body['metrics'] = [{'id': m, 'version': 2 if m == 'prediction.adaptation-delay' else 1} for m in r.METRICS]
    plan_body['members'] = [{**plan_body['members'][0], 'id': 'member-' + str(i)} for i in range(32)]
    plan_body['populations'].append({**plan_body['populations'][0], 'id': 'second'})
    p = a.validate_plan(plan_body)
    assert len(a.expand_inventory(p)) == 32 * 33 * 2
