"""MAJOR-1: aggregate Astra HTTP request resource budgets.

The approved contract (B10 design sections 13 and 17) allows at most
1 MiB of physical reads and 1 MiB of serialized response per HTTP
request, under one 2-second server deadline, with metadata, chunk and
index bytes charged to the SAME allowance. The EvaluationReader
enforces budgets per reader call; the Astra service composes several
reader calls per HTTP request. These tests measure the aggregate
physical bytes actually read while serving real HTTP requests and
require the whole request -- never each nested call -- to fit the
allowance, with independent budgets for concurrent requests.

Physical reads are instrumented at every mechanism the serving paths
use: ``Path.read_bytes``, ``os.pread`` and ``os.read``.
"""
import hashlib
import json
import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

import development.evaluation.reader as reader_module
import development.evaluation.replay as replay_module
from dashboard.app import create_app
from development.evaluation import integrity
from development.evaluation.paths import EvaluationRoot
from development.evaluation.reader import EvaluationReader
from tests.dashboard.evaluation_fixture import build as build_fixture

ORIGIN = 'http://127.0.0.1:8765'
MIB = 1024 * 1024
RUN = 'a' * 32
RUN_B = 'b' * 32
RUN_C = 'c' * 32
ZERO_CHUNK = hashlib.sha256(b'\x00' * 65536).hexdigest()
FINDING = {'question': 'prediction', 'finding': 'NEGATIVE',
           'reason': 'PREREGISTERED_THRESHOLD_RULE'}


# ---------------------------------------------------------------------------
# Physical-read instrumentation
# ---------------------------------------------------------------------------

@pytest.fixture
def physical(monkeypatch):
    counter = {'bytes': 0}
    real_read_bytes = Path.read_bytes
    real_pread = os.pread
    real_read = os.read

    def read_bytes(self, *args, **kwargs):
        data = real_read_bytes(self, *args, **kwargs)
        counter['bytes'] += len(data)
        return data

    def pread(fd, count, offset):
        data = real_pread(fd, count, offset)
        counter['bytes'] += len(data)
        return data

    def read(fd, count):
        data = real_read(fd, count)
        counter['bytes'] += len(data)
        return data

    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    monkeypatch.setattr(os, 'pread', pread)
    monkeypatch.setattr(os, 'read', read)
    return counter


@pytest.fixture
def budget_tracker(monkeypatch):
    """Record which RequestBudget object each charged read belongs to."""
    charges = []          # (thread_ident, budget_id)
    created = []          # budget_id
    real_charge = replay_module.RequestBudget.charge
    real_init = replay_module.RequestBudget.__init__

    def charge(self, data):
        charges.append((threading.get_ident(), id(self)))
        return real_charge(self, data)

    def init(self, max_bytes, deadline=None):
        created.append(id(self))
        return real_init(self, max_bytes, deadline)

    monkeypatch.setattr(replay_module.RequestBudget, 'charge', charge)
    monkeypatch.setattr(replay_module.RequestBudget, '__init__', init)
    return {'charges': charges, 'created': created}


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------

def _client(home, checkout):
    return TestClient(create_app(home, evaluation_root=checkout),
                      base_url=ORIGIN)


@pytest.fixture
def genuine_checkout(tmp_path):
    checkout = tmp_path / 'genuine'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    return checkout


def _metrics_bytes(target):
    """A metrics.json of exactly ``target`` bytes.

    Padding respects the artifact grammar (strings <= 4096 chars,
    bounded containers): many measurement rows with bounded pads,
    fine-tuned by one partial row and a finding note.
    """
    assert target <= 256 * 1024

    def build(full_rows, last_pad, note_pad):
        rows = [{'metric': 'prediction.numeric-mae', 'pad': 'x' * 4000}
                for _ in range(full_rows)]
        rows.append({'metric': 'prediction.numeric-mae',
                     'pad': 'x' * last_pad})
        finding = dict(FINDING, note='z' * note_pad)
        return json.dumps({'produced': rows,
                           'findings': [finding]}).encode()

    row_unit = len(json.dumps(
        {'metric': 'prediction.numeric-mae', 'pad': 'x' * 4000}))
    count = max(0, (target - len(build(0, 0, 0))) // row_unit)
    raw = build(count, 0, 0)
    while target - len(raw) < 0:
        count -= 1
        raw = build(count, 0, 0)
    while target - len(raw) > 8000:
        count += 1
        raw = build(count, 0, 0)
    delta = target - len(raw)
    last = min(delta, 4000)
    raw = build(count, last, delta - last)
    assert len(raw) == target
    return raw


def _manifest_bytes(pad=0):
    body = {'status': 'COMPLETED', 'reason': None,
            'science_digest': 'e' * 64,
            'experiment': {'id': 'technical-fixture', 'version': 1},
            'plan_digest': 'f' * 64,
            'counts': {'planned': 1, 'joined': 1, 'observed': 1,
                       'skipped': 0}}
    if pad:
        full, rest = divmod(pad, 4000)
        body['pad'] = ['y' * 4000] * full + ['y' * rest]
    return json.dumps(body).encode()


def _chunks_entry(data):
    return {'length': len(data),
            'chunks': [hashlib.sha256(data[i:i + 65536]).hexdigest()
                       for i in range(0, len(data), 65536)]}


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


_DUMMY_CACHE = {}


def _dummy_base(run_dir, dummy_bytes):
    """Create the sparse dummy checkpoint once per run directory and
    cache its inventory entries plus the whole-payload digest state
    after its segment (it sorts first among the fabricated names)."""
    key = str(run_dir)
    cached = _DUMMY_CACHE.get(key)
    if cached and cached[0] == dummy_bytes:
        return cached[1], cached[2], cached[3]
    checkpoints = run_dir / 'checkpoints'
    checkpoints.mkdir(exist_ok=True)
    dummy = checkpoints / 'pad.sqlite3'
    if not dummy.exists() or dummy.stat().st_size != dummy_bytes:
        with open(dummy, 'wb') as handle:
            handle.seek(dummy_bytes - 1)
            handle.write(b'\x00')
    count, rest = divmod(dummy_bytes, 65536)
    hashes = [ZERO_CHUNK] * count
    if rest:
        hashes.append(hashlib.sha256(b'\x00' * rest).hexdigest())
    chunks_entry = {'length': dummy_bytes, 'chunks': hashes}
    receipt_entry = {'length': dummy_bytes, 'sha256': _sha256_file(dummy)}
    base = hashlib.sha256(integrity.DOMAIN)
    encoded = b'checkpoints/pad.sqlite3'
    base.update(len(encoded).to_bytes(8, 'big'))
    base.update(encoded)
    base.update(dummy_bytes.to_bytes(8, 'big'))
    with open(dummy, 'rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            base.update(block)
    _DUMMY_CACHE[key] = (dummy_bytes, chunks_entry, receipt_entry, base)
    return chunks_entry, receipt_entry, base


def fabricate_run(checkout, run_id, *, metrics_size, dummy_bytes=0,
                  manifest_pad=0):
    """Write one published run whose every reader-verified hash is real.

    The receipt, the chunks.json inventory and every per-chunk hash are
    computed from the actual bytes on disk (the whole-payload digest
    uses the exact integrity algorithm). A sparse zero checkpoint file
    of ``dummy_bytes`` models the large chunk index of a maximum-size
    published artifact; its chunks are never requested by these tests.
    Returns the on-disk sizes of the files a detail request reads.
    """
    root_path = Path(checkout) / '.seed-evaluation'
    run_dir = root_path / 'evaluation' / 'runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = _manifest_bytes(manifest_pad)
    metrics = _metrics_bytes(metrics_size)
    (run_dir / 'manifest.json').write_bytes(manifest)
    (run_dir / 'metrics.json').write_bytes(metrics)
    inventory = {'manifest.json': _chunks_entry(manifest),
                 'metrics.json': _chunks_entry(metrics)}
    files = {'manifest.json': manifest, 'metrics.json': metrics}
    whole = hashlib.sha256(integrity.DOMAIN)
    receipt_files = {}
    if dummy_bytes:
        chunks_entry, receipt_entry, base = _dummy_base(run_dir,
                                                        dummy_bytes)
        inventory['checkpoints/pad.sqlite3'] = chunks_entry
        receipt_files['checkpoints/pad.sqlite3'] = receipt_entry
        whole = base.copy()
    chunks = json.dumps(inventory).encode()
    (run_dir / 'chunks.json').write_bytes(chunks)
    files['chunks.json'] = chunks
    for name in sorted(files):
        data = files[name]
        length, sha = len(data), hashlib.sha256(data).hexdigest()
        receipt_files[name] = {'length': length, 'sha256': sha}
        encoded = name.encode('ascii')
        whole.update(len(encoded).to_bytes(8, 'big'))
        whole.update(encoded)
        whole.update(length.to_bytes(8, 'big'))
        whole.update(data)
    receipt = {'schema': 'b10_receipt_v1', 'run_id': run_id,
               'files': receipt_files, 'digest': whole.hexdigest()}
    receipt_raw = json.dumps(receipt).encode()
    receipts = root_path / 'evaluation' / 'receipts'
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / f'{run_id}.json').write_bytes(receipt_raw)
    return {'receipt': len(receipt_raw), 'manifest': len(manifest),
            'metrics': len(metrics), 'chunks.json': len(chunks)}


@pytest.fixture
def fabricated_checkout(tmp_path):
    checkout = tmp_path / 'fabricated'
    checkout.mkdir()
    EvaluationRoot.create(checkout)
    return checkout


def _run_total(sizes):
    """Physical bytes one request reads for one fabricated run:
    receipt + chunk index + manifest + metrics, each exactly once."""
    return (sizes['receipt'] + sizes['manifest'] + sizes['metrics']
            + sizes['chunks.json'])


# ---------------------------------------------------------------------------
# Test A: detail endpoint aggregate reads
# ---------------------------------------------------------------------------

def test_detail_aggregate_budget_calibrated_genuine(
        home, genuine_checkout, physical, monkeypatch):
    """With the limit calibrated between the nested-call aggregate and
    the true per-request aggregate, the genuine fixture's detail
    request must fit: nested reader calls share one budget."""
    # Genuine fixture on disk: receipt 1123 + manifest 750 + metrics
    # 471 + chunks.json 878. One shared budget reads 3222 bytes; the
    # nested-call flow reads 7160. 5000 separates the two.
    monkeypatch.setattr(reader_module, 'REQUEST_BYTES', 5000)
    with _client(home, genuine_checkout) as client:
        physical['bytes'] = 0
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 200
    assert physical['bytes'] <= 5000, (
        f"detail request physically read {physical['bytes']} bytes "
        f"against a 5000-byte request allowance")


def test_detail_aggregate_budget_real_ceiling_large(
        home, fabricated_checkout, physical):
    """A large valid run (256 KiB metrics, maximum-scale chunk index)
    is served under the real 1 MiB ceiling with each byte read
    exactly once. (Pre-fix this also trips the stored-file parse cap
    in the service, which the remediation aligns with the artifact
    contract as part of making the ceiling testable at all.)"""
    fabricate_run(fabricated_checkout, RUN, metrics_size=256 * 1024,
                  dummy_bytes=165 * 1024 * 1024)
    with _client(home, fabricated_checkout) as client:
        physical['bytes'] = 0
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 200
    assert [row['finding'] for row in response.json()['findings']] == [
        'NEGATIVE']
    assert physical['bytes'] <= MIB, (
        f"detail request physically read {physical['bytes']} bytes "
        f"against the 1048576-byte request allowance")


# ---------------------------------------------------------------------------
# Test B: comparison endpoint aggregate reads (both runs)
# ---------------------------------------------------------------------------

def test_compare_aggregate_budget(home, fabricated_checkout, physical):
    """The comparison flow composes four stored-file reads (two
    manifests, two metrics) plus two full detail reads; at realistic
    maximum scale its nested-call aggregate passes 1 MiB while every
    individual reader call stays inside its own allowance."""
    for run_id in (RUN, RUN_B):
        fabricate_run(fabricated_checkout, run_id,
                      metrics_size=65_000,
                      dummy_bytes=200 * 1024 * 1024)
    with _client(home, fabricated_checkout) as client:
        physical['bytes'] = 0
        response = client.get(
            '/api/evaluation/compare',
            params={'left': RUN, 'right': RUN_B,
                    'metric': 'prediction.numeric-mae'})
    assert response.status_code == 200
    assert physical['bytes'] <= MIB, (
        f"compare request physically read {physical['bytes']} bytes "
        f"against the 1048576-byte request allowance")


# ---------------------------------------------------------------------------
# Test C: multi-chunk boundary -- 1 MiB - 1, exactly 1 MiB, 1 MiB + 1
#
# A two-run comparison is the multi-chunk flow that can legitimately
# approach the ceiling: two receipts, two chunk indexes, two manifests
# and two metrics files, every chunk charged to the one request.
# ---------------------------------------------------------------------------

RUN_D = 'd' * 32
BOUNDARY_DUMMY = 250 * 1024 * 1024


def _fabricate_right_for_total(checkout, run_id, left_total, target):
    metrics_size = 147_000
    sizes = fabricate_run(checkout, run_id, metrics_size=metrics_size,
                          dummy_bytes=BOUNDARY_DUMMY, manifest_pad=59_000)
    for _ in range(10):
        total = left_total + _run_total(sizes)
        if total == target:
            return sizes
        metrics_size += target - total
        assert 20_000 <= metrics_size <= 256_000, (
            f'boundary target {target} unreachable: {metrics_size}')
        sizes = fabricate_run(checkout, run_id,
                              metrics_size=metrics_size,
                              dummy_bytes=BOUNDARY_DUMMY,
                              manifest_pad=59_000)
    raise AssertionError(f'could not fabricate total {target}: {sizes}')


def test_multichunk_boundary(home, fabricated_checkout, physical):
    left = fabricate_run(fabricated_checkout, RUN, metrics_size=200_000,
                         dummy_bytes=BOUNDARY_DUMMY, manifest_pad=59_000)
    left_total = _run_total(left)
    cases = [(RUN_B, MIB - 1, 200), (RUN_C, MIB, 200),
             (RUN_D, MIB + 1, 429)]
    for run_id, target, _ in cases:
        sizes = _fabricate_right_for_total(fabricated_checkout, run_id,
                                           left_total, target)
        assert left_total + _run_total(sizes) == target
    with _client(home, fabricated_checkout) as client:
        for run_id, target, expected in cases:
            physical['bytes'] = 0
            response = client.get(
                '/api/evaluation/compare',
                params={'left': RUN, 'right': run_id,
                        'metric': 'prediction.numeric-mae'})
            assert response.status_code == expected, (
                f'aggregate {target}: got {response.status_code}')
            assert physical['bytes'] <= MIB, (
                f'aggregate {target}: physically read '
                f"{physical['bytes']} bytes, over the 1 MiB ceiling")
            if expected == 429:
                assert response.json()['error']['code'] == 'resource_limit'


# ---------------------------------------------------------------------------
# Test D: nested reader calls share one budget (no _begin reset)
# ---------------------------------------------------------------------------

def test_nested_reader_calls_share_one_budget(
        home, genuine_checkout, budget_tracker):
    with _client(home, genuine_checkout) as client:
        budget_tracker['charges'].clear()
        budget_tracker['created'].clear()
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 200
    charged = {budget for _, budget in budget_tracker['charges']}
    assert len(charged) == 1, (
        f'nested reader calls charged {len(charged)} distinct budgets')
    assert len(budget_tracker['created']) == 1, (
        f"{len(budget_tracker['created'])} budgets were created for "
        f'one HTTP request')


# ---------------------------------------------------------------------------
# Test E: file-size race -- a growing file must not be over-read
# ---------------------------------------------------------------------------

def test_file_growth_cannot_overread(home, genuine_checkout, physical,
                                     monkeypatch):
    monkeypatch.setattr(reader_module, 'REQUEST_BYTES', 4096)
    counted_read_bytes = Path.read_bytes  # the physical counter's wrap

    def growing(self, *args, **kwargs):
        data = counted_read_bytes(self, *args, **kwargs)
        if self.name == 'metrics.json':
            # The file grew after its size was checked: the physical
            # read delivers (and is charged for) the extra bytes too.
            physical['bytes'] += 100_000
            return data + b' ' * 100_000
        return data

    monkeypatch.setattr(Path, 'read_bytes', growing)
    with _client(home, genuine_checkout) as client:
        physical['bytes'] = 0
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert physical['bytes'] <= 4096, (
        f"grew to {physical['bytes']} physical bytes against a "
        f"4096-byte allowance")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Section 4: concurrent requests have independent budgets
# ---------------------------------------------------------------------------

def test_concurrent_evaluation_requests_have_independent_budgets(
        home, genuine_checkout, budget_tracker, monkeypatch):
    app = create_app(home, evaluation_root=genuine_checkout)
    service = app.state.evaluation
    entered = threading.Event()
    release = threading.Event()
    real_read = EvaluationReader._read
    threads = {}

    def pausing_read(self, directory, name, maximum):
        if threading.current_thread() is threads.get('a') \
                and name == 'metrics.json' and not entered.is_set():
            entered.set()
            release.wait(15)
        return real_read(self, directory, name, maximum)

    monkeypatch.setattr(EvaluationReader, '_read', pausing_read)
    results, errors = {}, {}

    def call(key):
        try:
            results[key] = service.detail(RUN)
        except Exception as error:  # recorded, asserted below
            errors[key] = error

    budget_tracker['charges'].clear()
    thread_a = threading.Thread(target=call, args=('a',))
    threads['a'] = thread_a
    thread_a.start()
    assert entered.wait(15), 'request A never reached its metrics read'
    thread_b = threading.Thread(target=call, args=('b',))
    threads['b'] = thread_b
    thread_b.start()
    thread_b.join(15)
    release.set()
    thread_a.join(15)
    assert not errors, f'concurrent requests failed: {errors}'
    assert results['a']['findings'] == results['b']['findings']
    by_thread = {}
    for ident, budget in budget_tracker['charges']:
        by_thread.setdefault(ident, set()).add(budget)
    assert len(by_thread[thread_a.ident]) == 1, (
        'request A charged more than one budget (contamination)')
    assert len(by_thread[thread_b.ident]) == 1, (
        'request B charged more than one budget (contamination)')
    assert by_thread[thread_a.ident] != by_thread[thread_b.ident], (
        'requests A and B shared one budget object')

    # Replay index use from parallel requests stays correct.
    expected = service.events(RUN)
    outcomes, failures = [], []

    def page():
        try:
            outcomes.append(service.events(RUN))
        except Exception as error:
            failures.append(error)

    for _ in range(5):
        pair = [threading.Thread(target=page) for _ in range(2)]
        for thread in pair:
            thread.start()
        for thread in pair:
            thread.join(15)
    assert not failures, f'parallel replay pages failed: {failures}'
    assert all(outcome == expected for outcome in outcomes)


# ---------------------------------------------------------------------------
# Section 5: one server deadline for the whole request
# ---------------------------------------------------------------------------

def test_aggregate_http_deadline_is_not_reset(
        home, genuine_checkout, monkeypatch):
    monkeypatch.setattr(reader_module, 'REQUEST_SECONDS', 0.6)
    real_read = EvaluationReader._read
    sleeps = {'count': 0}

    def slow_read(self, directory, name, maximum):
        if name in ('metrics.json', 'chunks.json') \
                and sleeps['count'] < 3:
            sleeps['count'] += 1
            time.sleep(0.35)
        return real_read(self, directory, name, maximum)

    monkeypatch.setattr(EvaluationReader, '_read', slow_read)
    with _client(home, genuine_checkout) as client:
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 429, (
        f'aggregate work past one 0.6 s deadline returned '
        f'{response.status_code}')
    assert response.json()['error']['code'] == 'deadline_exceeded'


# ---------------------------------------------------------------------------
# Section 8: serialized response ceiling
# ---------------------------------------------------------------------------

def test_serialized_response_ceiling(home, genuine_checkout, monkeypatch):
    app = create_app(home, evaluation_root=genuine_checkout)
    service = app.state.evaluation
    base = len(JSONResponse({'pad': ''}).body)
    exact = {'pad': 'x' * (MIB - base)}
    assert len(JSONResponse(exact).body) == MIB
    monkeypatch.setattr(service, 'detail', lambda run_id: exact)
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.get(f'/api/evaluation/runs/{RUN}')
        assert response.status_code == 200
        assert len(response.content) == MIB
        over = {'pad': 'x' * (MIB - base + 1)}
        monkeypatch.setattr(service, 'detail', lambda run_id: over)
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 429
    assert response.json()['error']['code'] == 'resource_limit'
    assert len(response.content) <= MIB


# ---------------------------------------------------------------------------
# Guards: the genuine fixture stays fully servable at the real ceiling
# ---------------------------------------------------------------------------

def test_genuine_fixture_servable_within_real_ceiling(
        home, genuine_checkout, physical):
    with _client(home, genuine_checkout) as client:
        for path in (f'/api/evaluation/runs/{RUN}',
                     f'/api/evaluation/runs/{RUN}/events',
                     f'/api/evaluation/runs/{RUN}/measurements'):
            physical['bytes'] = 0
            response = client.get(path)
            assert response.status_code == 200, path
            assert physical['bytes'] <= MIB, path
        physical['bytes'] = 0
        response = client.get(
            f'/api/evaluation/runs/{RUN}/files/metrics.json',
            params={'chunk': 0})
        assert response.status_code == 200
        assert physical['bytes'] <= MIB
