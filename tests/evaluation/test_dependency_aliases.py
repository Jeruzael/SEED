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


@pytest.mark.parametrize('binding',[
    'import importlib as x',
    'from importlib import import_module as x',
    'from builtins import __import__ as x',
    'x=__import__',
])
def test_nested_shadowing_cannot_erase_importer(foundation_module,tmp_path,binding):
    (tmp_path/'seed').mkdir(); (tmp_path/'bridge').mkdir()
    (tmp_path/'seed/__init__.py').write_text('from bridge import helper\n')
    call='x.import_module' if binding=='import importlib as x' else 'x'
    (tmp_path/'bridge/helper.py').write_text(binding+'\n'+call+'("development.evaluation.private")\ndef unrelated():\n    import math as x\n')
    assert foundation_module('dependency').audit_dependencies(tmp_path)
