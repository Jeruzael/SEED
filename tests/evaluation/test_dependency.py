import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest


def test_dependency_direction(foundation_module, tmp_path):
    d = foundation_module('dependency')
    assert d.audit_dependencies(Path.cwd()) == ()
    # Synthetic indirect and dynamic edges prove this is more than text grep.
    (tmp_path / 'seed').mkdir()
    (tmp_path / 'bridge').mkdir()
    (tmp_path / 'development/evaluation').mkdir(parents=True)
    (tmp_path / 'seed/__init__.py').write_text('from bridge import helper\n')
    (tmp_path / 'bridge/helper.py').write_text('from development.evaluation import contracts\n')
    assert d.audit_dependencies(tmp_path)
    (tmp_path / 'bridge/helper.py').write_text('import importlib\nx=importlib.import_module("development.evaluation.contracts")\n')
    assert d.audit_dependencies(tmp_path)


def test_seed_operates_without_evaluator(foundation_module, tmp_path):
    foundation_module('dependency')
    shutil.copytree('seed', tmp_path / 'seed', ignore=shutil.ignore_patterns('__pycache__'))
    code = '''
from pathlib import Path
import sys
import seed.organism as o
class Body:
    def __init__(self, home): pass
    def perceive(self):
        return dict(battery_pct=80,charging=True,load_ratio=.2,disk_free_pct=75,network=True,local_hour=12)
o.Body=Body
core=o.SeedOrganism(Path('home'))
try:
    assert core.cycle().status == 'completed'
    from seed.migrations import schema_version
    assert schema_version(core.memory.db) == 7
    assert not any(n.startswith('development') for n in sys.modules)
finally: core.close()
'''
    env = {'PATH': os.environ.get('PATH','')}
    subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env=env, check=True, timeout=10)
