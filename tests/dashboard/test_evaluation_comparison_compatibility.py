"""MAJOR-2: scientific comparison eligibility vs result identity.

Two runs are comparable when their experimental definitions,
populations, protocols, provenance and registered analysis rules are
compatible -- NOT when their scientific outcomes happen to be equal.
Different results alone must never cause an incompatibility verdict;
``science_digest`` is result identity (provenance), not an eligibility
criterion. Missing evidence is "not established", never ``None ==
None`` proof of a match, and an ambiguous registered measurement is
never silently resolved to its first row.

All runs here are genuinely published through the approved artifact
pipeline (freeze, journal, derived scientific outputs, assembly,
receipt). Post-publication edits are rehashed with the exact
integrity algorithm where a test needs an internally consistent but
evidence-incomplete artifact, and are labeled as such.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.app import create_app
from development.evaluation import integrity
from development.evaluation.paths import EvaluationRoot
from tests.dashboard.evaluation_fixture import BASE_PLAN, NEGATIVE_PLAN

MAE = 'prediction.numeric-mae'
A, B, C, D = 'a' * 32, 'b' * 32, 'c' * 32, 'd' * 32
DEFAULT_EXPERIMENT = dict(
    id='technical-fixture', version=1, source_commit='b' * 40,
    lock_digest='c' * 64, profile_digest='d' * 64,
    protocol='PREQUENTIAL', adapter_version=1)


def _publish(checkout: Path, run_id: str, plan_body: dict, *,
             outcome=0.2, experiment=None, status='COMPLETED'):
    """Publish one genuine run; ``outcome`` is the recorded observed
    load_ratio, so different outcomes derive different measurements
    and a different science digest through the real machinery."""
    from development.evaluation import (analysis, artifacts, checkpoint)
    from development.evaluation.canonical import canonical_bytes
    from development.evaluation.contracts import (AnalysisPlan,
                                                  PreUpdateEvidence,
                                                  RunResult)
    from tests.evaluation.test_prediction_boundary import \
        checkpoint as ckpt
    root = EvaluationRoot.create(checkout)
    plan = AnalysisPlan(canonical_bytes(plan_body))
    try:
        frozen = analysis.freeze_plan(plan, root)
    except Exception:
        frozen = analysis.require_frozen(plan, root)
    journal = checkpoint.ScoreJournal.create(root, run_id)
    value = ckpt()
    value['state_after'] = {**value['state_after'],
                            'load_ratio': outcome}
    journal.append(journal.frame(
        PreUpdateEvidence(json.dumps(value).encode())))
    journal.close()
    partial = (checkout / '.seed-evaluation' / 'evaluation'
               / 'partials' / run_id)
    frames = artifacts._journal_frames(
        (partial / 'preupdate.ndjson').read_bytes())
    rows, findings = artifacts.derive_scientific_outputs(
        frozen, frames, [], status)
    record = dict(
        schema='b10_run_record_v1', run_id=run_id, status=status,
        reason=None,
        experiment=experiment or dict(DEFAULT_EXPERIMENT),
        events=[dict(key=['measured', 'default', 1, 'update'],
                     body=dict(action='observe', confirmed=True,
                               update=dict(kind='b1_transition',
                                           source_ids=['s1'])))],
        attempts=[], measurements=list(rows), findings=findings,
        truth=dict(fixture=True),
        operations=[dict(code='run_completed', note='ok')],
        checkpoints=[], planned_transitions=1, failure=None)
    artifacts.write_run_record(root, record)
    payload = artifacts.assemble_payload(RunResult(status, None),
                                         frozen, root)
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root),
                      root)
    return run_id


ORIGIN = 'http://127.0.0.1:8765'


def _client(home, checkout):
    return TestClient(create_app(Path(home), evaluation_root=checkout),
                      base_url=ORIGIN)


@pytest.fixture
def home(tmp_path, monkeypatch):
    path = tmp_path / 'home'
    path.mkdir()
    monkeypatch.setenv('SEED_HOME', str(path))
    return path


def _root(tmp_path_factory, name, builder):
    checkout = tmp_path_factory.mktemp(name) / 'checkout'
    checkout.mkdir()
    builder(checkout)
    return checkout


@pytest.fixture(scope='module')
def differing_results_root(tmp_path_factory):
    """Same frozen plan (with the preregistered MAE floor), same
    provenance; two runs whose recorded outcomes differ."""
    def build(checkout):
        _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
        _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    return _root(tmp_path_factory, 'diff-results', build)


@pytest.fixture(scope='module')
def provenance_root(tmp_path_factory):
    """Same frozen plan; the second run's source/profile provenance
    differs."""
    def build(checkout):
        _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
        other = dict(DEFAULT_EXPERIMENT, source_commit='f' * 40,
                     profile_digest='e' * 64)
        _publish(checkout, C, NEGATIVE_PLAN, outcome=0.2,
                 experiment=other)
    return _root(tmp_path_factory, 'provenance', build)


@pytest.fixture(scope='module')
def different_plan_root(tmp_path_factory):
    """Same provenance; the second run freezes a plan whose
    preregistered threshold differs."""
    def build(checkout):
        _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
        plan_b = copy.deepcopy(NEGATIVE_PLAN)
        plan_b['analysis_plan_version'] = 2
        plan_b['thresholds'][0]['value'] = 2
        _publish(checkout, D, plan_b, outcome=0.2)
    return _root(tmp_path_factory, 'diff-plan', build)


@pytest.fixture(scope='module')
def plan_variants_root(tmp_path_factory):
    """Same provenance; the second run's plan changes its
    standardization rule and a member rule version."""
    def build(checkout):
        _publish(checkout, A, BASE_PLAN, outcome=0.2)
        plan_b = copy.deepcopy(BASE_PLAN)
        plan_b['analysis_plan_version'] = 2
        plan_b['members'][0]['variant'] = 'fresh'
        _publish(checkout, D, plan_b, outcome=0.2)
    return _root(tmp_path_factory, 'plan-variants', build)


@pytest.fixture(scope='module')
def ambiguous_root(tmp_path_factory):
    """One plan registering the same metric for two populations:
    the produced inventory holds two rows for the metric per run."""
    def build(checkout):
        plan = copy.deepcopy(BASE_PLAN)
        plan['populations'] = [
            dict(id='all', phase='measured', action='all',
                 signal='load_ratio'),
            dict(id='resting', phase='measured', action='rest',
                 signal='load_ratio')]
        _publish(checkout, A, plan, outcome=0.2)
        _publish(checkout, B, plan, outcome=0.7)
    return _root(tmp_path_factory, 'ambiguous', build)


def _compare(home, checkout, left, right, metric=MAE):
    with _client(home, checkout) as client:
        return client.get('/api/evaluation/compare',
                          params={'left': left, 'right': right,
                                  'metric': metric})


def _stored(checkout, run_id, name):
    path = (Path(checkout) / '.seed-evaluation' / 'evaluation'
            / 'runs' / run_id / name)
    return json.loads(path.read_bytes())


def _rehash(checkout, run_id):
    """Recompute chunks.json and the receipt from the actual bytes
    on disk (the exact integrity algorithm), after a test edits or
    removes a payload file: the artifact stays internally consistent
    so the observer reads the evidence as published."""
    root_path = Path(checkout) / '.seed-evaluation'
    run_dir = root_path / 'evaluation' / 'runs' / run_id
    files = {p.name: p.read_bytes() for p in sorted(run_dir.iterdir())
             if p.is_file() and p.name != 'chunks.json'}
    inventory = {}
    for name, data in files.items():
        inventory[name] = {
            'length': len(data),
            'chunks': [hashlib.sha256(data[i:i + 65536]).hexdigest()
                       for i in range(0, len(data), 65536)]}
    chunks = json.dumps(inventory).encode()
    (run_dir / 'chunks.json').write_bytes(chunks)
    files['chunks.json'] = chunks
    whole = hashlib.sha256(integrity.DOMAIN)
    receipt_files = {}
    for name in sorted(files):
        data = files[name]
        receipt_files[name] = {'length': len(data),
                               'sha256': hashlib.sha256(
                                   data).hexdigest()}
        encoded = name.encode('ascii')
        whole.update(len(encoded).to_bytes(8, 'big'))
        whole.update(encoded)
        whole.update(len(data).to_bytes(8, 'big'))
        whole.update(data)
    receipt = {'schema': 'b10_receipt_v1', 'run_id': run_id,
               'files': receipt_files, 'digest': whole.hexdigest()}
    (root_path / 'evaluation' / 'receipts'
     / f'{run_id}.json').write_bytes(json.dumps(receipt).encode())


# ---------------------------------------------------------------- B1/B8

def test_compatible_definitions_different_results(
        home, differing_results_root):
    """B1 + B8: identical definitions and provenance, different
    recorded outcomes. The runs ARE compatible; their science
    digests differ as provenance; nothing is ranked."""
    left = _stored(differing_results_root, A, 'manifest.json')
    right = _stored(differing_results_root, B, 'manifest.json')
    assert left['plan_digest'] == right['plan_digest']
    assert left['science_digest'] != right['science_digest']
    response = _compare(home, differing_results_root, A, B)
    assert response.status_code == 200
    data = response.json()
    assert data['compatible'] is True
    assert data['eligibility'] == 'compatible'
    identity = data['scientific_identity']['science_digest']
    assert identity['equal'] is False
    assert identity['left'] == left['science_digest']
    assert identity['right'] == right['science_digest']
    assert 'science_digest' not in data['dimensions']
    metric = data['metric']
    assert metric['state'] == 'paired'
    assert metric['identity'] == 'member-0:prediction.numeric-mae:all:whole'
    assert metric['left']['value'] == 0.0
    assert metric['right']['value'] == pytest.approx(0.5)
    # Stored findings are carried verbatim; a completed execution is
    # not a positive result, and no ranking language appears.
    assert data['findings']['left'] == _stored(
        differing_results_root, A, 'metrics.json')['findings']
    assert data['findings']['left'][0]['status'] == 'NEGATIVE'
    assert data['findings']['right'][0]['status'] == 'NEGATIVE'
    text = response.text.lower()
    for word in ('better', 'worse', 'winner', 'verdict', 'improved',
                 'equivalent'):
        assert word not in text


# -------------------------------------------------------------------- B2

def test_same_plan_incompatible_provenance(home, provenance_root):
    """B2: the frozen plan matches, but source/profile provenance
    demonstrably differs: incompatible, with the exact dimensions
    disclosed and no ranking."""
    response = _compare(home, provenance_root, A, C)
    assert response.status_code == 200
    data = response.json()
    assert data['compatible'] is False
    assert data['eligibility'] == 'incompatible'
    dims = data['dimensions']
    assert dims['plan_digest']['status'] == 'match'
    assert dims['source_commit']['status'] == 'differs'
    assert dims['source_commit']['left'] == 'b' * 40
    assert dims['source_commit']['right'] == 'f' * 40
    assert dims['profile_digest']['status'] == 'differs'
    assert dims['experiment']['status'] == 'match'


# -------------------------------------------------------------------- B3

def test_different_frozen_plans(home, different_plan_root):
    """B3: a different frozen analysis plan is incompatible even
    with identical provenance and experiment identity; the differing
    plan fields are disclosed."""
    response = _compare(home, different_plan_root, A, D)
    data = response.json()
    assert data['compatible'] is False
    assert data['eligibility'] == 'incompatible'
    assert data['dimensions']['plan_digest']['status'] == 'differs'
    assert data['dimensions']['experiment']['status'] == 'match'
    assert 'thresholds' in data['plan_fields']


# -------------------------------------------------------------------- B4

def test_plan_definition_mismatches_disclosed(home, plan_variants_root):
    """B4: a changed member variant (a registered plan definition)
    is a plan-definition mismatch, disclosed by field. (In plan
    schema v1, eligibility/coverage/aggregation/standardization and
    missing_rules are contract-fixed constants, so they cannot
    differ between two valid plans; member definitions, thresholds,
    populations, windows and baselines are the variable fields.)"""
    response = _compare(home, plan_variants_root, A, D)
    data = response.json()
    assert data['eligibility'] == 'incompatible'
    assert data['dimensions']['plan_digest']['status'] == 'differs'
    assert 'members' in data['plan_fields']


# -------------------------------------------------------------------- B5

def test_missing_provenance_is_not_established(home, tmp_path):
    """B5: a required provenance field absent from BOTH manifests
    is not a match (the None == None trap): eligibility is
    explicitly not established, distinct from incompatible."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
    _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    for run_id in (A, B):
        run_dir = (checkout / '.seed-evaluation' / 'evaluation'
                   / 'runs' / run_id)
        manifest = json.loads((run_dir / 'manifest.json').read_bytes())
        del manifest['experiment']['profile_digest']
        (run_dir / 'manifest.json').write_bytes(
            json.dumps(manifest).encode())
        _rehash(checkout, run_id)
    response = _compare(home, checkout, A, B)
    assert response.status_code == 200
    data = response.json()
    assert data['compatible'] is False
    assert data['eligibility'] == 'not_established'
    dim = data['dimensions']['profile_digest']
    assert dim['status'] == 'not_established'
    assert dim['match'] is None
    assert any('profile_digest' in reason
               for reason in data['reasons'])


def test_missing_plan_file_is_not_established(home, tmp_path):
    """B5: without the frozen plan artifact in a run's verified
    inventory, plan binding cannot be established."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
    _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    plan_path = (checkout / '.seed-evaluation' / 'evaluation'
                 / 'runs' / B / 'analysis-plan.json')
    plan_path.unlink()
    _rehash(checkout, B)
    response = _compare(home, checkout, A, B)
    assert response.status_code == 200
    data = response.json()
    assert data['eligibility'] == 'not_established'
    assert data['dimensions']['plan_digest']['status'] == \
        'not_established'
    assert any('plan' in reason for reason in data['reasons'])


# -------------------------------------------------------------------- B6

def test_ambiguous_metric_selection(home, ambiguous_root):
    """B6: one metric ID with two registered measurement rows per
    run is never silently resolved to the first row."""
    response = _compare(home, ambiguous_root, A, B)
    assert response.status_code == 200
    metric = response.json()['metric']
    assert metric['state'] == 'ambiguous'
    assert metric['left'] is None and metric['right'] is None
    expected = {'member-0:prediction.numeric-mae:all:whole',
                'member-0:prediction.numeric-mae:resting:whole'}
    assert set(metric['candidates']['left']) == expected
    assert set(metric['candidates']['right']) == expected


def test_metric_version_mismatch_is_explicit(home, tmp_path):
    """B6: a produced row whose version is not the plan-registered
    version is not presented as the run's registered measurement."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
    _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    run_dir = (checkout / '.seed-evaluation' / 'evaluation'
               / 'runs' / B)
    metrics = json.loads((run_dir / 'metrics.json').read_bytes())
    metrics['produced'][0]['version'] = 2
    (run_dir / 'metrics.json').write_bytes(
        json.dumps(metrics).encode())
    _rehash(checkout, B)
    response = _compare(home, checkout, A, B)
    assert response.status_code == 200
    metric = response.json()['metric']
    assert metric['state'] == 'version_mismatch'
    assert metric['left'] is None and metric['right'] is None


# -------------------------------------------------------------------- B7

def test_forged_metrics_rejected(home, tmp_path):
    """B7: a post-publication edit without rehashing fails chunk
    verification: typed integrity error, never a comparison."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
    _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    path = (checkout / '.seed-evaluation' / 'evaluation' / 'runs'
            / B / 'metrics.json')
    raw = bytearray(path.read_bytes())
    raw[40] ^= 0x01
    path.write_bytes(bytes(raw))
    response = _compare(home, checkout, A, B)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


def test_forged_plan_binding_rejected(home, tmp_path):
    """B7: a plan artifact whose stated digest contradicts the
    manifest binding (rehashed so transport integrity passes) is
    invalid stored evidence, not a comparison input."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    _publish(checkout, A, NEGATIVE_PLAN, outcome=0.2)
    _publish(checkout, B, NEGATIVE_PLAN, outcome=0.7)
    run_dir = (checkout / '.seed-evaluation' / 'evaluation'
               / 'runs' / B)
    plan = json.loads((run_dir / 'analysis-plan.json').read_bytes())
    plan['digest'] = '0' * 64
    (run_dir / 'analysis-plan.json').write_bytes(
        json.dumps(plan).encode())
    _rehash(checkout, B)
    response = _compare(home, checkout, A, B)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'artifact_error'


# ------------------------------------------------------------- budget fit

def test_compare_reads_plan_within_same_budget(
        home, differing_results_root, monkeypatch):
    """Phase C/§7: frozen-plan evidence is read through the same
    request session; the whole comparison stays inside the single
    1 MiB aggregate read budget."""
    import os
    from pathlib import Path as _Path
    reads = []
    real_read_bytes = _Path.read_bytes
    real_pread = os.pread

    def spy_read_bytes(self):
        data = real_read_bytes(self)
        reads.append((str(self), len(data)))
        return data

    def spy_pread(fd, length, offset):
        data = real_pread(fd, length, offset)
        reads.append(('pread', len(data)))
        return data

    monkeypatch.setattr(_Path, 'read_bytes', spy_read_bytes)
    monkeypatch.setattr(os, 'pread', spy_pread)
    response = _compare(home, differing_results_root, A, B)
    assert response.status_code == 200
    assert any('analysis-plan.json' in name for name, _ in reads)
    assert sum(size for _, size in reads) <= 1_048_576
