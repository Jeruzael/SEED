"""R6: control admission uses current retained usage and remaining reservations."""
import os
import pytest


def test_plan_freeze_rejects_root_growth(foundation_module,tmp_path,plan_body):
    p=foundation_module('paths'); a=foundation_module('analysis')
    root=p.EvaluationRoot.create(tmp_path.resolve())
    with (root.path/'grown').open('wb') as f: f.truncate(16*1024**3)
    plan=a.validate_plan(plan_body)
    with pytest.raises(ValueError): a.freeze_plan(plan,root)
    assert not list(root.plan_directory.iterdir())
    assert (root.path/'grown').exists()


def test_coordinator_reconciles_after_first_admission(foundation_module,tmp_path,plan_body,monkeypatch):
    p=foundation_module('paths'); a=foundation_module('analysis'); c=foundation_module('coordinator')
    root=p.EvaluationRoot.create(tmp_path.resolve()); frozen=a.freeze_plan(a.validate_plan(plan_body),root)
    owner=c.Coordinator(root=root,frozen_plan=frozen)
    monkeypatch.setattr(c,'audit_dependencies',lambda *args:())
    request=foundation_module('contracts').RunRequest
    owner.admit(request('first'))
    # Below raw root ceiling but leaves insufficient room for new + outstanding reservations.
    with (root.path/'grown').open('wb') as f: f.truncate(16*1024**3-600*1024**2)
    with pytest.raises(ValueError): owner.admit(request('second'))


def test_live_run_partial_count_checked_before_control_write(foundation_module,tmp_path):
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    partials=root.path/'evaluation'/'partials'
    for i in range(61): (partials/str(i)).mkdir()
    with pytest.raises(ValueError): root.open('plan','new','create')
    assert not (root.plan_directory/'new.plan').exists()


def test_active_reservation_not_double_counted_and_release(foundation_module):
    l=foundation_module('limits'); request=foundation_module('contracts').RunRequest
    budget=l.Budget(retained_bytes=0,retained_runs=0)
    reservation=budget.reserve(request('run',1,448*1024**2))
    # Actual active bytes replace the same reserved bytes; all other retained bytes still count.
    assert hasattr(budget,'reconcile'), 'live reservation reconciliation missing'
    reservation.activate('run')
    budget.reconcile(l.Usage(16*1024**3-448*1024**2,59,(('run',448*1024**2),),('run',)))
    budget.reserve(request('last',1,448*1024**2))
    reservation.release()
    assert 'run' not in budget._reservations
