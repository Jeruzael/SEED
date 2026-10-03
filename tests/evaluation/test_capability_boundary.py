"""Worker serialization carries assigned storage and accounting only."""
import pickle
import os
import pytest


def test_worker_launch_has_no_evaluator_root_authority(foundation_module,tmp_path):
    p=foundation_module('paths'); c=foundation_module('contracts')
    root=p.EvaluationRoot.create(tmp_path.resolve())
    fd=root.open('plan','private','create')
    with os.fdopen(fd,'wb') as f: f.write(b'PRIVATE_PLAN_SENTINEL')
    cap=root.assign_learner('run',0)
    launch=pickle.loads(pickle.dumps(c.WorkerLaunch(cap,b'{}',0,'a'*64)))
    objects=[launch]; visited=set()
    while objects:
        value=objects.pop()
        if id(value) in visited: continue
        visited.add(id(value))
        assert type(value) is not p.EvaluationRoot, 'worker receives evaluator control authority'
        if isinstance(value,dict): objects.extend(value.values())
        elif isinstance(value,(tuple,list,set)): objects.extend(value)
        elif hasattr(value,'__dict__'): objects.extend(vars(value).values())
    launch.learner.validate()
    with pytest.raises(ValueError): launch.learner.open('plan','private','read')
    assert not (root.path/'work'/'other-run').exists()


def test_serialized_capability_keeps_live_storage_admission(foundation_module,tmp_path):
    p=foundation_module('paths'); root=p.EvaluationRoot.create(tmp_path.resolve())
    cap=pickle.loads(pickle.dumps(root.assign_learner('run',0)))
    with (root.path/'grown').open('wb') as f: f.truncate(16*1024**3)
    with pytest.raises(ValueError): cap.validate()
    assert (root.path/'grown').exists()


def test_capability_tracks_parent_outstanding_reservations(foundation_module,tmp_path):
    p=foundation_module('paths'); root=p.EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('run',0)
    request=foundation_module('contracts').RunRequest('pending',1,448*1024**2)
    reservation=root.budget.reserve(request)
    cap=pickle.loads(pickle.dumps(cap))
    with (root.path/'grown').open('wb') as f: f.truncate(16*1024**3-448*1024**2)
    with pytest.raises(ValueError): cap.validate()
    reservation.release()
