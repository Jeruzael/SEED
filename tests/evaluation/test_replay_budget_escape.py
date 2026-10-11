"""Final replay-budget remediation (R-BUDGET-1 / R-BUDGET-2).

No replay read may bypass the 1 MiB / 2 s request budget -- including
the first returned record. Reads are preflighted against the remaining
budget before they happen; budget/deadline exhaustion is a typed error
distinct from invalid evidence; a corrupt record never becomes a
silently shortened page; an unaffordable record on an empty page is an
explicit bounded error, never a stalled successful cursor.
"""
import os

import pytest

from .test_artifacts import RUN, _record
from .test_replay import _publish
from .test_replay_budget import _big_root

RECEIPT = '.seed-evaluation/evaluation/receipts'


def _sizes(tmp_path):
    run = tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    receipt = tmp_path / RECEIPT / f'{RUN}.json'
    journal_line = len((run / 'preupdate.ndjson').read_bytes().splitlines(
        keepends=True)[0])
    event_line = len((run / 'events.ndjson').read_bytes().splitlines(
        keepends=True)[0])
    return receipt.stat().st_size, journal_line + event_line


def _warm_reader(tmp_path, foundation_module, plan_body, **kw):
    root = _publish(tmp_path, foundation_module, plan_body, **kw)
    reader_mod = foundation_module('reader')
    reader = reader_mod.EvaluationReader(root)
    page = reader.events(RUN, limit=1)  # builds + caches the full index
    assert len(page.events) == 1
    return root, reader_mod, reader


# --- Test A / G: the unmetered first-row retry -------------------------
def test_first_row_cannot_escape_read_budget(
        tmp_path, foundation_module, plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError
    root, reader_mod, reader = _warm_reader(
        tmp_path, foundation_module, plan_body)
    receipt_size, row_cost = _sizes(tmp_path)
    # Fits the receipt (and the manifests the reader consults) but not
    # the first replay row: the row must NOT be served unmetered.
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES',
                        receipt_size + row_cost - 1)
    with pytest.raises(ContractError):
        reader.events(RUN, limit=1)


def test_replay_insufficient_budget_never_returns_stalled_cursor(
        tmp_path, foundation_module, plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError
    root, reader_mod, reader = _warm_reader(
        tmp_path, foundation_module, plan_body)
    receipt_size, row_cost = _sizes(tmp_path)
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES',
                        receipt_size + row_cost - 1)
    for _ in range(3):  # never a successful empty page with same cursor
        with pytest.raises(ContractError):
            reader.events(RUN, limit=20)


# --- Test B: exact byte boundary ---------------------------------------
def test_replay_exact_read_budget_boundary(
        tmp_path, foundation_module, plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError
    root, reader_mod, reader = _warm_reader(
        tmp_path, foundation_module, plan_body)
    receipt_size, row_cost = _sizes(tmp_path)
    # Exactly enough: receipt + the row's two stored lines.
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES',
                        receipt_size + row_cost)
    page = reader.events(RUN, limit=1)
    assert len(page.events) == 1
    # One byte less: explicit failure, no row.
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES',
                        receipt_size + row_cost - 1)
    with pytest.raises(ContractError):
        reader.events(RUN, limit=1)
    # Zero remaining after the metadata reads: explicit failure.
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', receipt_size)
    with pytest.raises(ContractError):
        reader.events(RUN, limit=1)
    # A subsequent request with a sufficient budget serves the row.
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', 1024 * 1024)
    page = reader.events(RUN, limit=1)
    assert len(page.events) == 1


# --- Test C / E: physical byte accounting -------------------------------
class _ReadCounter:
    def __init__(self, monkeypatch):
        self.pread_bytes = 0
        self.read_bytes_calls = 0
        real_pread = os.pread
        import pathlib
        real_read = pathlib.Path.read_bytes

        def counting_pread(fd, n, offset):
            data = real_pread(fd, n, offset)
            self.pread_bytes += len(data)
            return data

        def counting_read(self_path, *a, **k):
            data = real_read(self_path, *a, **k)
            self.read_bytes_calls += len(data)
            return data

        monkeypatch.setattr(os, 'pread', counting_pread)
        monkeypatch.setattr(pathlib.Path, 'read_bytes', counting_read)

    @property
    def total(self):
        return self.pread_bytes + self.read_bytes_calls

    def reset(self):
        self.pread_bytes = 0
        self.read_bytes_calls = 0


def test_replay_pread_never_exceeds_remaining_budget(
        tmp_path, foundation_module, plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError
    root = _big_root(tmp_path, foundation_module, plan_body)
    reader_mod = foundation_module('reader')
    reader = reader_mod.EvaluationReader(root)
    counter = _ReadCounter(monkeypatch)
    with pytest.raises(ContractError):
        reader.events(RUN, limit=1)  # cold: index build exceeds budget
    assert counter.total <= 1024 * 1024, (
        f'physical reads {counter.total} exceeded the request budget')


def test_replay_partial_index_resumes_without_overread(
        tmp_path, foundation_module, plan_body, monkeypatch):
    from development.evaluation.contracts import ContractError
    root = _big_root(tmp_path, foundation_module, plan_body)
    reader_mod = foundation_module('reader')
    monkeypatch.setattr(reader_mod, 'REQUEST_BYTES', 256 * 1024)
    reader = reader_mod.EvaluationReader(root)
    counter = _ReadCounter(monkeypatch)
    seen, cursor, errors = [], None, 0
    for _ in range(200):
        counter.reset()
        try:
            page = reader.events(RUN, cursor=cursor, limit=5)
        except ContractError:
            errors += 1
            assert counter.total <= 256 * 1024, (
                f'physical reads {counter.total} exceeded the request '
                f'budget during a failed request')
            continue
        assert counter.total <= 256 * 1024
        seen.extend(e.key for e in page.events)
        if page.cursor is None:
            break
        assert page.cursor != cursor
        cursor = page.cursor
    else:
        raise AssertionError('traversal did not complete')
    assert errors >= 1
    assert seen == [('measured', 'default', i + 1, 'update')
                    for i in range(24)]


# --- Test D: corruption after a successful row --------------------------
def test_corrupt_second_row_is_not_silently_truncated(
        tmp_path, foundation_module, plan_body):
    from development.evaluation.contracts import ContractError
    root = _publish(tmp_path, foundation_module, plan_body, frames=2)
    reader_mod = foundation_module('reader')
    reader = reader_mod.EvaluationReader(root)
    assert len(reader.events(RUN, limit=2).events) == 2
    # Corrupt the second journal frame's evidence (same length, valid
    # JSON shape, digest-invalid) in the published file.
    target = (tmp_path / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
              / 'preupdate.ndjson')
    lines = target.read_bytes().splitlines(keepends=True)
    line = bytearray(lines[1])
    anchor = line.index(b'state_after')
    for i in range(anchor, len(line)):
        if 48 <= line[i] <= 57:  # first digit of the outcome state
            line[i] = 48 + (line[i] - 47) % 10
            break
    lines[1] = bytes(line)
    target.write_bytes(b''.join(lines))
    reader2 = reader_mod.EvaluationReader(root)
    with pytest.raises(ContractError):
        reader2.events(RUN, limit=2)


# --- Test F: deadline is typed and reads nothing ------------------------
def test_replay_deadline_cannot_trigger_unmetered_retry(
        tmp_path, foundation_module, plan_body, monkeypatch):
    import time
    root = _publish(tmp_path, foundation_module, plan_body)
    replay = foundation_module('replay')
    from development.evaluation.contracts import ContractError
    budget_type = getattr(replay, 'RequestBudget', None)
    assert budget_type is not None, 'no typed request budget exists'
    budget = budget_type(1024 * 1024, deadline=time.monotonic() - 1)
    index = replay.build_index(root, RUN)
    counter = _ReadCounter(monkeypatch)
    with pytest.raises(replay.BudgetError):
        replay.read_rows(root, RUN, index, 0, 1, budget=budget)
    assert counter.pread_bytes == 0  # deadline preflight precedes any read
    # And the budget error remains part of the external contract surface.
    assert issubclass(replay.BudgetError, ContractError)
