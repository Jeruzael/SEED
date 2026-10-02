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
