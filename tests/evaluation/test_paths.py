import os
from pathlib import Path
import pytest
from .test_analysis import ClosedRoot


def test_root_attack_matrix(foundation_module, tmp_path):
    p = foundation_module('paths')
    root = p.EvaluationRoot.create(tmp_path.resolve())
    for identity in ('/etc/passwd', '..', '../x', 'a/b', 'a%2fb', 'a%5cb', 'a\\b', 'a\x00b'):
        with pytest.raises(ValueError):
            root.open('plan', identity, 'create')
    for kind in ('shell', 'module', '../learner'):
        with pytest.raises(ValueError):
            root.open(kind, 'safe', 'create')
    path = root.plan_directory / 'safe.plan'
    path.symlink_to(tmp_path / 'foreign')
    with pytest.raises(ValueError):
        root.open('plan', 'safe', 'read')
    path.unlink()
    path.write_bytes(b'ok')
    os.link(path, root.plan_directory / 'linked.plan')
    with pytest.raises(ValueError):
        root.open('plan', 'safe', 'read')
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(ValueError):
        root.open('plan', 'safe', 'read')
    path.unlink()
    fd = root.open('plan', 'atomic', 'create')
    os.write(fd, b'good')
    os.close(fd)
    old = root.plan_directory
    moved = old.with_name('replaced')
    old.rename(moved)
    old.mkdir()
    (old / 'atomic.plan').write_bytes(b'foreign')
    with pytest.raises(ValueError):
        root.open('plan', 'atomic', 'read')


def test_real_root_freeze(foundation_module, plan_body, tmp_path):
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    a = foundation_module('analysis')
    p = a.validate_plan(plan_body)
    frozen = a.freeze_plan(p, root)
    assert a.require_frozen(p, root) == frozen


def test_foreign_unmarked_root_rejected(foundation_module, tmp_path):
    p = foundation_module('paths')
    foreign = tmp_path / '.seed-evaluation'
    foreign.mkdir()
    (foreign / 'owner-data').write_bytes(b'foreign')
    with pytest.raises(ValueError):
        p.EvaluationRoot.create(tmp_path.resolve())
    assert (foreign / 'owner-data').read_bytes() == b'foreign'


def test_no_inherited_home_or_secrets(foundation_module, tmp_path, monkeypatch):
    p = foundation_module('paths')
    installed = tmp_path / 'installed'
    installed.mkdir()
    monkeypatch.setenv('SEED_HOME', str(installed))
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'private-secret')
    root = p.EvaluationRoot.create(tmp_path.resolve())
    learner = root.assign_learner('run-0', 0)
    assert learner.kind == 'learner' and learner.home != installed
    with pytest.raises(ValueError):
        learner.open('plan', 'secret', 'read')
    with pytest.raises(ValueError):
        p.LearnerCapability(installed, 'forged', (0, 0)).validate()
    assert not list(installed.iterdir())
    env = p.worker_environment()
    assert 'SEED_HOME' not in env and 'AWS_SECRET_ACCESS_KEY' not in env
