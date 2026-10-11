"""I26: optional read-only Evaluation service and GET-only API.

The dashboard observes immutable B10 artifacts through the dedicated
EvaluationReader only. It never acquires an execution capability, never
falls back to the organism home, and reports a clear unavailable state
when the optional evaluation root is absent or disabled.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.app import create_app

ORIGIN = 'http://127.0.0.1:8765'
RUN = 'a' * 32

PLAN_BODY = dict(
    schema='b10_analysis_plan_v1', experiment_id='technical-fixture',
    experiment_version=1, analysis_plan_version=1,
    members=[dict(id='member-0', family='A', scenario_version=2,
                  rule_version=2, protocol='PREQUENTIAL', variant='seed',
                  seed=0, training=0, measured=1)],
    metrics=[dict(id='prediction.numeric-mae', version=1)], seeds=[0],
    populations=[dict(id='all', phase='measured', action='all',
                      signal='load_ratio')],
    windows=[dict(id='whole', start=1, end=1, unit='ordinal')],
    baselines=[dict(id='persistence', version=1)], exclusions=[],
    eligibility='registered_support', coverage='all_opportunities',
    aggregation='ordered_fsum', standardization='equal_qualifying_actions',
    missing_rules='unavailable_with_reason', thresholds=[],
    questions=[dict(id='prediction', metrics=['prediction.numeric-mae'],
                    rule='descriptive_only',
                    reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE')],
    exploratory=True)


def _publish(checkout: Path):
    """Publish one genuine technical-fixture run into an evaluator root."""
    from development.evaluation import (analysis, artifacts, checkpoint,
                                         integrity)
    from development.evaluation.canonical import canonical_bytes
    from development.evaluation.contracts import (AnalysisPlan,
                                                  PreUpdateEvidence,
                                                  RunResult)
    from development.evaluation.paths import EvaluationRoot
    from tests.evaluation.test_prediction_boundary import checkpoint as ckpt
    root = EvaluationRoot.create(checkout)
    plan = AnalysisPlan(canonical_bytes(PLAN_BODY))
    frozen = analysis.freeze_plan(plan, root)
    journal = checkpoint.ScoreJournal.create(root, RUN)
    value = ckpt()
    journal.append(journal.frame(PreUpdateEvidence(json.dumps(value).encode())))
    journal.close()
    partial = checkout / '.seed-evaluation' / 'evaluation' / 'partials' / RUN
    journal_raw = (partial / 'preupdate.ndjson').read_bytes()
    frames = artifacts._journal_frames(journal_raw)
    rows, findings = artifacts.derive_scientific_outputs(
        frozen, frames, [], 'COMPLETED')
    record = dict(
        schema='b10_run_record_v1', run_id=RUN, status='COMPLETED',
        reason=None,
        experiment=dict(id='technical-fixture', version=1,
                        source_commit='b' * 40, lock_digest='c' * 64,
                        profile_digest='d' * 64, protocol='PREQUENTIAL',
                        adapter_version=1),
        events=[dict(key=['measured', 'default', 1, 'update'],
                     body=dict(action='observe', confirmed=True,
                               update=dict(kind='b1_transition',
                                           source_ids=['s1'])))],
        attempts=[], measurements=list(rows), findings=findings,
        truth=dict(fixture=True),
        operations=[dict(code='run_completed', note='ok')],
        checkpoints=[], planned_transitions=1, failure=None)
    artifacts.write_run_record(root, record)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None),
                                         frozen, root)
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root),
                      root)
    return root


@pytest.fixture
def eval_checkout(tmp_path):
    checkout = tmp_path / 'evalroot'
    checkout.mkdir()
    _publish(checkout)
    return checkout


@pytest.fixture
def client(home, eval_checkout):
    return TestClient(create_app(home, evaluation_root=eval_checkout),
                      base_url=ORIGIN)


def test_get_only_even_operator(home, eval_checkout):
    with TestClient(create_app(home, operator=True,
                               evaluation_root=eval_checkout),
                    base_url=ORIGIN) as c:
        token = c.get('/api/bootstrap').json()['token']
        headers = {'Origin': ORIGIN, 'X-SEED-CSRF': token}
        assert c.get('/api/evaluation/runs').status_code == 200
        for method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            for path in ('/api/evaluation/runs',
                         f'/api/evaluation/runs/{RUN}',
                         '/api/evaluation/run',
                         '/api/evaluation/reexecute'):
                response = c.request(method, path, json={},
                                     headers=headers)
                assert response.status_code in (403, 404, 405), (
                    method, path, response.status_code)


def test_optional_reader_absence_and_no_home_fallback(home, tmp_path):
    # Disabled (no root configured): clear unavailable state, other
    # views keep working.
    with TestClient(create_app(home), base_url=ORIGIN) as c:
        response = c.get('/api/evaluation/runs')
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'evaluation_unavailable'
        assert c.get('/api/status').status_code == 200
    # Missing root directory: unavailable, and nothing is created.
    missing = tmp_path / 'nope'
    with TestClient(create_app(home, evaluation_root=missing),
                    base_url=ORIGIN) as c:
        assert c.get('/api/evaluation/runs').status_code == 503
    assert not missing.exists()
    # The organism home is never a fallback evaluation root.
    with TestClient(create_app(home, evaluation_root=home),
                    base_url=ORIGIN) as c:
        assert c.get('/api/evaluation/runs').status_code == 503
    assert not (home / '.seed-evaluation').exists()


def test_all_route_bounds(client, eval_checkout):
    c = client
    runs = c.get('/api/evaluation/runs')
    assert runs.status_code == 200
    body = runs.json()
    assert body['available'] is True
    assert [item['run_id'] for item in body['items']] == [RUN]
    assert body['next_cursor'] is None
    # Bounds on the list route.
    assert c.get('/api/evaluation/runs?limit=21').status_code == 422
    assert c.get('/api/evaluation/runs?limit=0').status_code == 422
    assert c.get('/api/evaluation/runs?limit=1&limit=2').status_code == 422
    assert c.get('/api/evaluation/runs?bogus=1').status_code == 422
    # Detail + run ID validation.
    detail = c.get(f'/api/evaluation/runs/{RUN}')
    assert detail.status_code == 200
    assert detail.json()['status'] == 'COMPLETED'
    assert detail.json()['receipt_digest']
    for bad in ('xyz', 'A' * 32, 'a' * 31, 'a' * 33, 'g' * 32):
        assert c.get(f'/api/evaluation/runs/{bad}').status_code == 422, bad
    assert c.get(f"/api/evaluation/runs/{'f' * 32}").status_code == 404
    # Measurements + events pages.
    measurements = c.get(f'/api/evaluation/runs/{RUN}/measurements')
    assert measurements.status_code == 200
    assert len(measurements.json()['items']) >= 1
    events = c.get(f'/api/evaluation/runs/{RUN}/events')
    assert events.status_code == 200
    items = events.json()['items']
    assert [i['key'] for i in items] == [['measured', 'default', 1, 'update']]
    # Forged cursors are rejected, never treated as paths or queries.
    assert c.get(f'/api/evaluation/runs/{RUN}/events?cursor=forged'
                 ).status_code in (409, 422)
    assert c.get(f'/api/evaluation/runs/{RUN}/events?cursor='
                 + 'A' * 600).status_code == 422
    # Event detail by exact tuple.
    single = c.get(f'/api/evaluation/runs/{RUN}/events/measured:default:1:update')
    assert single.status_code == 200
    assert single.json()['key'] == ['measured', 'default', 1, 'update']
    for bad in ('a:b:c', 'measured:default:x:update',
                'measured:default:1', 'measured:default:-1:update',
                '../../etc:passwd:1:update'):
        assert c.get(f'/api/evaluation/runs/{RUN}/events/{bad}'
                     ).status_code == 422, bad
    # Curve: registered series only, metric + series required.
    run_dir = eval_checkout / '.seed-evaluation' / 'evaluation' / 'runs' / RUN
    index = json.loads((run_dir / 'index.json').read_text())
    series = sorted(index['curves'])[0]
    curve = c.get(f'/api/evaluation/runs/{RUN}/curve',
                  params={'metric': 'prediction.numeric-mae',
                          'series': series})
    assert curve.status_code == 200
    assert len(curve.json()['points']) <= 200
    assert c.get(f'/api/evaluation/runs/{RUN}/curve',
                 params={'series': series}).status_code == 422
    assert c.get(f'/api/evaluation/runs/{RUN}/curve',
                 params={'metric': 'prediction.numeric-mae',
                         'series': 'nope'}).status_code in (409, 422)
    # Compare: same run is dimension-compatible; missing run is 404.
    compare = c.get('/api/evaluation/compare',
                    params={'left': RUN, 'right': RUN,
                            'metric': 'prediction.numeric-mae'})
    assert compare.status_code == 200
    assert compare.json()['compatible'] is True
    assert c.get('/api/evaluation/compare',
                 params={'left': RUN, 'right': 'f' * 32}).status_code == 404
    assert c.get('/api/evaluation/compare',
                 params={'left': RUN}).status_code == 422
    # Files: allowlisted IDs, bounded chunk integers, binary attachment.
    chunk = c.get(f'/api/evaluation/runs/{RUN}/files/manifest.json?chunk=0')
    assert chunk.status_code == 200
    assert chunk.headers['content-type'] == 'application/octet-stream'
    assert 'attachment' in chunk.headers['content-disposition']
    assert len(chunk.content) <= 64 * 1024
    for bad_id in ('../secret', 'evil.exe', 'manifest.json/extra', ''):
        if bad_id:
            assert c.get(f'/api/evaluation/runs/{RUN}/files/{bad_id}'
                         ).status_code in (404, 422), bad_id
    assert c.get(f'/api/evaluation/runs/{RUN}/files/manifest.json?chunk=-1'
                 ).status_code == 422
    assert c.get(f'/api/evaluation/runs/{RUN}/files/manifest.json?chunk=x'
                 ).status_code == 422
    assert c.get(f'/api/evaluation/runs/{RUN}/files/manifest.json?chunk=9999'
                 ).status_code in (404, 409, 422)


def test_corrupt_receipt_is_typed_error_not_empty_success(
        home, eval_checkout):
    receipt = (eval_checkout / '.seed-evaluation' / 'evaluation'
               / 'receipts' / f'{RUN}.json')
    receipt.write_bytes(b'{"schema":"b10_receipt_v1","run_id":"x"}')
    with TestClient(create_app(home, evaluation_root=eval_checkout),
                    base_url=ORIGIN) as c:
        response = c.get(f'/api/evaluation/runs/{RUN}')
        assert response.status_code in (404, 409)
        assert response.json()['error']['code'] != 'evaluation_unavailable'


def test_no_executor_or_scorer_imports():
    import dashboard.services.evaluation as service_mod
    import dashboard.api.evaluation as api_mod
    import inspect
    for mod in (service_mod, api_mod):
        source = inspect.getsource(mod)
        for banned in ('evaluation.coordinator', 'evaluation.worker',
                       'evaluation.scenarios', 'evaluation.metrics',
                       'evaluation.reexecution', 'from seed',
                       'import seed.', 'SeedService', 'mutate('):
            assert banned not in source, (mod.__name__, banned)
