"""R10: aliases and unresolved reachable dynamic imports fail closed."""
from pathlib import Path
import pytest


@pytest.mark.parametrize('source',[
    'from development.evaluation import private',
    'from importlib import import_module as im\nim("development.evaluation.private")',
    'import importlib as x\nx.import_module("development.evaluation.private")',
    'im=__import__\nim("development.evaluation.private")',
    'from builtins import __import__ as im\nim("development.evaluation.private")',
    'import importlib\nfn=importlib.import_module\nfn("development.evaluation.private")',
    'from importlib import import_module as im\ndef f(target): return im(target)',
    'def f(target): return __import__(target)',
])
def test_protected_reachable_helper_import_patterns(foundation_module,tmp_path,source):
    (tmp_path/'seed').mkdir(); (tmp_path/'bridge').mkdir()
    (tmp_path/'seed/__init__.py').write_text('from bridge import helper\n')
    (tmp_path/'bridge/helper.py').write_text(source+'\n')
    failures=foundation_module('dependency').audit_dependencies(tmp_path)
    assert failures, 'protected reachable alias/dynamic import escaped audit'


def test_clean_checked_in_graph_still_passes(foundation_module):
    assert foundation_module('dependency').audit_dependencies(Path.cwd())==()
