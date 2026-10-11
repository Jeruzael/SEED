"""Narrow regression tests for the two MINORs from the final independent
review of remediation A-D:

MINOR-1: compatibility_report read the initial checkpoint through an
unvalidated plain path. MINOR-2: re-execution staged the fresh journal
and checkpoint copy before any budget admission covered those bytes.
"""
import os

import pytest

from .test_remediation import RUN, _produce_genuine, _profile
from .test_reexecution_fidelity import _produce_checkpointed


def test_compat_report_checkpoint_read_is_descriptor_safe(
        tmp_path, foundation_module, plan_body):
    root = _produce_checkpointed(tmp_path, foundation_module, plan_body)
    published = (tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
                 / 'checkpoints')
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'initial.sqlite3').write_bytes(
        (published / 'initial.sqlite3').read_bytes())
    (published / 'initial.sqlite3').unlink()
    published.rmdir()
    os.symlink(outside, published)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    report = reexecution.compatibility_report(
        reader, RUN, _profile(foundation_module))
    assert report['checks']['initial_state'] is False
    assert report['compatible'] is False


def test_reexecution_staging_admitted_before_writes(
        tmp_path, foundation_module, plan_body, monkeypatch):
    """Instrumented (the reviewer's C4 method): the first write into the
    fresh run's partial directory must be preceded, on the target root's
    budget, by an admission covering the staged bytes and the run slot."""
    import pathlib as _pathlib
    import development.evaluation.limits as limits
    root, frozen = _produce_genuine(tmp_path, foundation_module, plan_body)
    calls = []
    orig_require = limits.Budget.require_capacity

    def spy_require(self, *, bytes=0, runs=0):
        calls.append(('require', id(self), bytes, runs))
        return orig_require(self, bytes=bytes, runs=runs)

    orig_write = _pathlib.Path.write_bytes

    def spy_write(self, data):
        if 'partials' in self.parts:
            calls.append(('write', str(self), len(data)))
        return orig_write(self, data)

    monkeypatch.setattr(limits.Budget, 'require_capacity', spy_require)
    monkeypatch.setattr(_pathlib.Path, 'write_bytes', spy_write)
    reexecution = foundation_module('reexecution')
    reader = foundation_module('reader').EvaluationReader(root)
    result = reexecution.reexecute(reader, RUN, _profile(foundation_module))
    assert result.status == 'matched', reexecution.last_report()
    first_write = next(i for i, c in enumerate(calls) if c[0] == 'write')
    journal_write = next(c for c in calls if c[0] == 'write'
                         and c[1].endswith('preupdate.ndjson'))
    admitted = [c for c in calls[:first_write]
                if c[0] == 'require' and c[1] == id(root.budget)
                and c[2] >= journal_write[2] and c[3] >= 1]
    assert admitted, (
        f'no admission covered the staged journal before its write: '
        f'{calls[:first_write]}')
