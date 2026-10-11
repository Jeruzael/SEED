"""I25: trusted CLI verbs and the empirical dispatch lock."""
import pytest

from .test_artifacts import RUN
from .test_replay import _publish


def test_cli_verify_and_replay(tmp_path, foundation_module, plan_body,
                               monkeypatch, capsys):
    root = _publish(tmp_path, foundation_module, plan_body)
    cli = foundation_module('cli')
    monkeypatch.setattr(cli, '_checkout_root', lambda: root)
    assert cli.main(['verify', RUN]) == 0
    assert '"verified": true' in capsys.readouterr().out
    assert cli.main(['replay', RUN]) == 0
    assert 'measured' in capsys.readouterr().out
    assert cli.main(['validate', RUN]) == 0
    capsys.readouterr()


def test_cli_dispatch_locked_and_inputs_bounded(tmp_path, foundation_module,
                                                plan_body, monkeypatch, capsys):
    root = _publish(tmp_path, foundation_module, plan_body)
    cli = foundation_module('cli')
    monkeypatch.setattr(cli, '_checkout_root', lambda: root)
    # Registered empirical dispatch remains locked (I30 + separate owner
    # empirical authorization are not satisfied).
    assert cli.main(['run', RUN]) == 2
    assert cli.main(['suite', RUN]) == 2
    assert cli.main(['reexecute', RUN]) == 2
    out = capsys.readouterr().out
    assert 'EMPIRICAL_DISPATCH_DISABLED' in out
    # Arbitrary paths / code are not inputs.
    assert cli.main(['verify', '../../etc/passwd']) == 3
    assert cli.main(['verify', 'not-a-run-id']) == 3
    assert cli.main(['frobnicate', RUN]) == 3
    capsys.readouterr()
