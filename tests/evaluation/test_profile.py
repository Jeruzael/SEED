import json
from pathlib import Path
import shutil
import subprocess
import pytest


def checkout(tmp_path):
    root = tmp_path / 'checkout'
    root.mkdir()
    shutil.copytree('seed', root/'seed', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile('requirements-lock.txt', root/'requirements-lock.txt')
    (root/'.gitignore').write_text('.seed-evaluation/\n')
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    'commit','-qm','technical fixture'],check=True)
    return root


def test_dirty_or_changed_source_rejected(foundation_module, tmp_path):
    p = foundation_module('profile')
    root = checkout(tmp_path)
    cap = foundation_module('paths').EvaluationRoot.create(root.resolve())
    profile = p.capture_profile(cap)
    assert profile.clean and profile.schema_version == 7
    assert profile.lock_digest and len(profile.source_commit) == 40
    (root/'seed/version.py').write_text("CORE_VERSION='bad'\n")
    dirty = p.capture_profile(cap)
    assert not dirty.clean
    with pytest.raises(ValueError):
        p.require_source({'source_commit': profile.source_commit,'lock_digest':profile.lock_digest},dirty)
    subprocess.run(['git','-C',str(root),'restore','seed/version.py'],check=True)
    (root/'untracked.py').write_text('secret=1\n')
    assert not p.capture_profile(cap).clean
    (root/'untracked.py').unlink()
    (root/'requirements-lock.txt').write_text('changed\n')
    assert not p.capture_profile(cap).clean


def test_profile_compatibility(foundation_module, tmp_path, monkeypatch):
    p = foundation_module('profile')
    root = checkout(tmp_path)
    cap = foundation_module('paths').EvaluationRoot.create(root.resolve())
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','PRIVATE_SECRET_SENTINEL')
    profile = p.capture_profile(cap)
    report = json.dumps(profile.as_dict())
    assert 'PRIVATE_SECRET_SENTINEL' not in report and str(root) not in report
    p.require_source({'source_commit':profile.source_commit,'lock_digest':profile.lock_digest},profile)
    assert p.compatible(profile, profile)
    from dataclasses import replace
    for field, value in [('schema_version',8),('source_commit','f'*40),('lock_digest','a'*64),
                         ('python_version','0'),('adapter_version',2),('sqlite_version','0')]:
        assert not p.compatible(profile,replace(profile,**{field:value}))
    with pytest.raises(ValueError):
        p.require_source({'source_commit':'f'*40,'lock_digest':profile.lock_digest},profile)
