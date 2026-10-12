"""Final MINOR cleanup: M-01 plan-body binding, M-02 metric-state
accuracy, M-03 event-key grammar (server side), M-04 reader session
lifecycle, M-06 typed missing-file errors, M-07 deadline/corruption
precedence.

Fixtures are genuinely published through the approved artifact
pipeline; adversarial copies are clearly labeled and rehashed only
at the transport layer where a test needs internally consistent
transport metadata.
"""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import dashboard.services.evaluation as service_module
import development.evaluation.reader as reader_module
import development.evaluation.replay as replay_module
from dashboard.app import create_app
from development.evaluation.contracts import ContractError
from development.evaluation.paths import EvaluationRoot
from development.evaluation.reader import EvaluationReader
from tests.dashboard.evaluation_fixture import (
    NEGATIVE_PLAN, build as build_fixture)
from tests.dashboard.test_evaluation_comparison_compatibility import (
    _publish, _rehash)

RUN = 'a' * 32
B = 'b' * 32
ORIGIN = 'http://127.0.0.1:8765'


@pytest.fixture
def home(tmp_path, monkeypatch):
    path = tmp_path / 'home'
    path.mkdir()
    monkeypatch.setenv('SEED_HOME', str(path))
    return path


def _client(home, checkout):
    return TestClient(create_app(Path(home), evaluation_root=checkout),
                      base_url=ORIGIN)


def _pair(tmp_path, plan=NEGATIVE_PLAN):
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, RUN, plan, outcome=0.2)
    _publish(checkout, B, plan, outcome=0.7)
    return checkout


def _edit_plan(checkout, run_id, mutate):
    run_dir = (Path(checkout) / '.seed-evaluation' / 'evaluation'
               / 'runs' / run_id)
    plan = json.loads((run_dir / 'analysis-plan.json').read_bytes())
    mutate(plan)
    (run_dir / 'analysis-plan.json').write_bytes(
        json.dumps(plan).encode())
    _rehash(checkout, run_id)


def _compare(home, checkout, left=RUN, right=B, metric='prediction.numeric-mae'):
    with _client(home, checkout) as client:
        return client.get('/api/evaluation/compare',
                          params={'left': left, 'right': right,
                                  'metric': metric})


# ------------------------------------------------------------------ M-01

def test_plan_body_threshold_tamper_rejected(home, tmp_path):
    """M-01: a plan body whose threshold was changed, with the
    stated digest and freeze receipt left stale and only transport
    integrity regenerated, is invalid evidence: 409, never a
    compatible comparison."""
    checkout = _pair(tmp_path)
    _edit_plan(checkout, B, lambda plan:
               plan['plan']['thresholds'][0].update(value=5))
    response = _compare(home, checkout)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


def test_plan_body_member_tamper_rejected(home, tmp_path):
    """M-01: same for a member definition change in the body."""
    checkout = _pair(tmp_path)
    _edit_plan(checkout, B, lambda plan:
               plan['plan']['members'][0].update(variant='fresh'))
    response = _compare(home, checkout)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


def test_plan_body_hash_field_forgery_rejected(home, tmp_path):
    """M-01: a freeze receipt whose body_sha256 does not match the
    served body is rejected even when every stated digest agrees."""
    checkout = _pair(tmp_path)
    _edit_plan(checkout, B, lambda plan:
               plan['receipt'].update(body_sha256='0' * 64))
    response = _compare(home, checkout)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


def test_plan_canonical_representation_accepted(home, tmp_path):
    """M-01: a canonically equivalent re-serialization of the same
    plan body (different key order and whitespace, transport
    rehashed) still verifies: the check is over canonical bytes,
    not raw file bytes."""
    checkout = _pair(tmp_path)
    run_dir = (checkout / '.seed-evaluation' / 'evaluation' / 'runs'
               / B)
    plan = json.loads((run_dir / 'analysis-plan.json').read_bytes())
    (run_dir / 'analysis-plan.json').write_bytes(
        json.dumps(plan, indent=3, sort_keys=False).encode())
    _rehash(checkout, B)
    response = _compare(home, checkout)
    assert response.status_code == 200
    assert response.json()['eligibility'] == 'compatible'


# ------------------------------------------------------------------ M-02

def test_missing_plan_metric_state_not_established(home, tmp_path):
    """M-02: when one run's frozen plan is absent, the metric's
    registered version is UNKNOWN -- the metric state must be
    not_established, never version_mismatch."""
    checkout = _pair(tmp_path)
    plan_path = (checkout / '.seed-evaluation' / 'evaluation'
                 / 'runs' / B / 'analysis-plan.json')
    plan_path.unlink()
    _rehash(checkout, B)
    response = _compare(home, checkout)
    assert response.status_code == 200
    data = response.json()
    assert data['eligibility'] == 'not_established'
    assert data['metric']['state'] == 'not_established'


# ------------------------------------------------------------------ M-03

@pytest.mark.parametrize('key,expected', [
    ('measured:default:1:update', 200),
    ('measured:default:2048:update', 'grammar-ok'),
    ('measured:default:0:update', 422),
    ('measured:default:01:update', 422),
    ('measured:default:2049:update', 422),
    ('measured:default:-1:update', 422),
    ('measured:default:1.0:update', 422),
    ('measured:default:9223372036854775807:update', 422),
    ('bogus:default:1:update', 422),
    ('measured:bogus:1:update', 422),
    ('measured:default:1:bogus', 422),
    ('training:fresh:12:pre', 'grammar-ok'),
    ('probe:contradictory:2048:checkpoint', 'grammar-ok'),
])
def test_event_key_grammar(home, tmp_path, key, expected):
    """M-03: the server enforces the registered event-key contract:
    registered phase/subcase/stage sets and a canonical ordinal in
    1..2048. Grammar-valid keys for absent events surface the
    reader's typed 404/409, never a grammar 422."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    encoded = key.replace(':', '%3A')
    with _client(home, checkout) as client:
        response = client.get(
            f'/api/evaluation/runs/{RUN}/events/{encoded}')
    if expected == 'grammar-ok':
        assert response.status_code in (404, 409), response.status_code
    else:
        assert response.status_code == expected, (
            key, response.status_code)


# ------------------------------------------------------------------ M-04

def _reader(tmp_path):
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    return EvaluationReader(EvaluationRoot.create(checkout))


def test_transient_session_released_after_standalone_calls(tmp_path):
    """M-04: a standalone (non-ambient) reader call must not leave
    its transient session -- with its raw-file caches -- retained in
    the calling context after the operation completes."""
    reader = _reader(tmp_path)
    reader.detail(RUN)
    assert reader._sessions.get() is None
    reader.runs()
    assert reader._sessions.get() is None
    reader.verified_file(RUN, 'manifest.json')
    assert reader._sessions.get() is None


def test_transient_session_released_after_failures(tmp_path):
    """M-04: failures (missing run, exhausted budget) also release
    the transient session; nothing stale leaks into the next call."""
    reader = _reader(tmp_path)
    with pytest.raises(Exception):
        reader.detail('f' * 32)
    assert reader._sessions.get() is None
    reader.detail(RUN)  # a later call still works normally
    assert reader._sessions.get() is None


def test_ambient_session_unaffected_by_transient_cleanup(tmp_path):
    """M-04: inside an explicit request_session, calls share the
    ambient session and the context is clean after exit."""
    reader = _reader(tmp_path)
    with reader.request_session() as session:
        reader.detail(RUN)
        assert reader._sessions.get() is session
    assert reader._sessions.get() is None


def test_transient_sessions_are_per_thread(tmp_path):
    """M-04: standalone calls in another thread retain nothing in
    that thread's context once complete."""
    reader = _reader(tmp_path)
    observed = {}

    def work():
        reader.detail(RUN)
        observed['after'] = reader._sessions.get()

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    assert observed['after'] is None
    assert reader._sessions.get() is None


def test_standalone_calls_keep_per_call_budgets(tmp_path):
    """M-04 guard: standalone calls keep their historical per-call
    budget semantics (each call admits its own session)."""
    reader = _reader(tmp_path)
    first = reader.verified_file(RUN, 'metrics.json')
    second = reader.verified_file(RUN, 'metrics.json')
    assert first == second


# ------------------------------------------------------------------ M-06

def test_missing_payload_file_is_typed_contract_error(tmp_path):
    """M-06: reading a published run whose payload file was removed
    raises the typed ContractError, never a leaked
    FileNotFoundError."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    target = (checkout / '.seed-evaluation' / 'evaluation' / 'runs'
              / RUN / 'metrics.json')
    target.unlink()
    reader = EvaluationReader(EvaluationRoot.create(checkout))
    with pytest.raises(ContractError):
        reader.verified_file(RUN, 'metrics.json')


def test_service_missing_run_is_404_not_unhandled(home, tmp_path):
    """M-06: at the service boundary a missing run is the typed
    404 envelope; no unhandled exception escapes."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    with _client(home, checkout) as client:
        response = client.get(f'/api/evaluation/runs/{"f" * 32}')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'not_found'


# ------------------------------------------------------------------ M-07

class _FakeTime:
    def __init__(self):
        self.now = time.monotonic()

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds

    def __getattr__(self, name):
        return getattr(time, name)


@pytest.fixture
def fake_clock(monkeypatch):
    fake = _FakeTime()
    monkeypatch.setattr(reader_module, 'time', fake)
    monkeypatch.setattr(replay_module, 'time', fake)
    return fake


def _corrupted_checkout(tmp_path):
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    build_fixture(checkout, 'complete-negative')
    path = (checkout / '.seed-evaluation' / 'evaluation' / 'runs'
            / RUN / 'metrics.json')
    raw = bytearray(path.read_bytes())
    raw[40] ^= 0x01
    path.write_bytes(bytes(raw))
    return checkout


def test_corruption_established_before_deadline_is_409(
        home, tmp_path, fake_clock):
    """M-07: corruption the reader actually inspects before the
    deadline is the established error: 409 artifact_error."""
    checkout = _corrupted_checkout(tmp_path)
    with _client(home, checkout) as client:
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


def test_deadline_before_corruption_inspection_is_429(
        home, tmp_path, fake_clock, monkeypatch):
    """M-07: when the deadline expires before the corrupting file
    can be inspected, the established error is the deadline: 429
    deadline_exceeded, and never a 200 over unverified evidence.
    No extra reads are performed after the deadline to reclassify
    it."""
    checkout = _corrupted_checkout(tmp_path)
    real_strict_json = reader_module.strict_json

    def advancing(data, **kwargs):
        result = real_strict_json(data, **kwargs)
        fake_clock.advance(3.0)  # deadline passes during early reads
        return result

    monkeypatch.setattr(reader_module, 'strict_json', advancing)
    with _client(home, checkout) as client:
        response = client.get(f'/api/evaluation/runs/{RUN}')
    assert response.status_code == 429
    assert response.json()['error']['code'] == 'deadline_exceeded'
