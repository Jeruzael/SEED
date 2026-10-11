"""I29: disposable Evaluation browser/test fixtures.

`build(destination, case)` publishes genuine technical-fixture
artifacts through the approved I21–I24 publication contracts into an
explicit, empty, disposable directory. It never touches installed SEED
state. Damaged cases intentionally damage the disposable copies after
publication and are labeled technical fixtures, not authentic runs.
"""
import copy
import json
from pathlib import Path

from development.evaluation import analysis, artifacts, checkpoint, integrity
from development.evaluation.canonical import canonical_bytes
from development.evaluation.contracts import (AnalysisPlan, PreUpdateEvidence,
                                              RunResult)
from development.evaluation.paths import EvaluationRoot
from tests.evaluation.test_prediction_boundary import checkpoint as _ckpt

BASE_PLAN = dict(
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

NEGATIVE_PLAN = copy.deepcopy(BASE_PLAN)
NEGATIVE_PLAN['thresholds'] = [dict(
    id='mae-floor', version=1, value=1, metric='prediction.numeric-mae',
    metric_version=1, population='all', direction='ge',
    role='classification',
    rationale='Technical fixture threshold: the fixture MAE of 0 must '
              'fail this floor of 1, producing a genuine NEGATIVE finding.',
    missing_rule='inconclusive')]
NEGATIVE_PLAN['questions'] = [dict(
    id='prediction', metrics=['prediction.numeric-mae'],
    rule='thresholds_v1', reason='PREREGISTERED_THRESHOLD_RULE',
    thresholds=['mae-floor'])]

CASES = ('empty', 'complete-negative', 'partial', 'missing-receipt',
         'malformed', 'max-ids', 'incompatible-plans', 'max-inventory',
         'truth-annotations')


def _publish(checkout: Path, run_id: str, plan_body: dict, *,
             status='COMPLETED', reason=None, planned=1,
             source_ids=('s1',), truth=None, experiment_version=1):
    root = EvaluationRoot.create(checkout)
    plan = AnalysisPlan(canonical_bytes(plan_body))
    try:
        frozen = analysis.freeze_plan(plan, root)
    except Exception:
        # The identical plan is already frozen in this root (shared by
        # the multi-run fixture cases); load the existing freeze.
        frozen = analysis.require_frozen(plan, root)
    journal = checkpoint.ScoreJournal.create(root, run_id)
    value = _ckpt()
    journal.append(journal.frame(PreUpdateEvidence(
        json.dumps(value).encode())))
    journal.close()
    partial = (checkout / '.seed-evaluation' / 'evaluation' / 'partials'
               / run_id)
    frames = artifacts._journal_frames(
        (partial / 'preupdate.ndjson').read_bytes())
    rows, findings = artifacts.derive_scientific_outputs(
        frozen, frames, [], status)
    record = dict(
        schema='b10_run_record_v1', run_id=run_id, status=status,
        reason=reason,
        experiment=dict(id='technical-fixture',
                        version=experiment_version,
                        source_commit='b' * 40, lock_digest='c' * 64,
                        profile_digest='d' * 64, protocol='PREQUENTIAL',
                        adapter_version=1),
        events=[dict(key=['measured', 'default', 1, 'update'],
                     body=dict(action='observe', confirmed=True,
                               update=dict(kind='b1_transition',
                                           source_ids=list(source_ids))))],
        attempts=[], measurements=list(rows), findings=findings,
        truth=truth if truth is not None else dict(fixture=True),
        operations=[dict(code='run_completed', note='ok')],
        checkpoints=[], planned_transitions=planned, failure=None)
    artifacts.write_run_record(root, record)
    payload = artifacts.assemble_payload(RunResult(status, reason),
                                         frozen, root)
    finalized = integrity.finalize_payload(payload, root)
    integrity.publish(finalized, integrity.make_receipt(finalized, root),
                      root)
    return run_id


def build(destination: Path, case: str) -> dict:
    """Build one registered fixture case in an empty disposable dir."""
    destination = Path(destination)
    if case not in CASES:
        raise ValueError(f'unregistered fixture case: {case}')
    if not destination.is_dir() or any(destination.iterdir()):
        raise ValueError('fixture destination must be an empty directory')
    if (destination / 'memory.sqlite3').exists() or \
            (destination / '.seed-evaluation').exists():
        raise ValueError('fixture destination looks like existing state')
    runs = []
    if case == 'empty':
        EvaluationRoot.create(destination)
    elif case == 'complete-negative':
        runs.append(_publish(destination, 'a' * 32, NEGATIVE_PLAN))
    elif case == 'partial':
        runs.append(_publish(destination, 'a' * 32, BASE_PLAN,
                             status='INCOMPLETE', reason='PLANNED_MISSING',
                             planned=2))
    elif case == 'missing-receipt':
        run = _publish(destination, 'a' * 32, BASE_PLAN)
        receipt = (destination / '.seed-evaluation' / 'evaluation'
                   / 'receipts' / f'{run}.json')
        receipt.unlink()
        runs.append(run)
    elif case == 'malformed':
        run = _publish(destination, 'a' * 32, BASE_PLAN)
        manifest = (destination / '.seed-evaluation' / 'evaluation'
                    / 'runs' / run / 'manifest.json')
        manifest.write_bytes(b'{damaged technical fixture')
        runs.append(run)
    elif case == 'max-ids':
        runs.append(_publish(
            destination, 'a' * 32, BASE_PLAN,
            source_ids=('9223372036854775807', '9007199254740993')))
    elif case == 'incompatible-plans':
        runs.append(_publish(destination, 'a' * 32, BASE_PLAN))
        plan_b = copy.deepcopy(BASE_PLAN)
        plan_b['experiment_version'] = 2
        runs.append(_publish(destination, 'b' * 32, plan_b,
                             experiment_version=2))
    elif case == 'max-inventory':
        for index in range(21):
            runs.append(_publish(destination, f'{index:032x}', BASE_PLAN))
    elif case == 'truth-annotations':
        runs.append(_publish(
            destination, 'a' * 32, BASE_PLAN,
            truth=dict(fixture=True,
                       private_boundary='TRUTH_ANNOTATION_FIXTURE')))
    return {'case': case, 'checkout': str(destination), 'runs': runs,
            'note': 'technical fixture; not an empirical B10 result'}
