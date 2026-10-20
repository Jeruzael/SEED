"""Trusted re-execution and bounded scientific comparison (I25).

Re-execution is not replay: replay reads recorded evidence, while
re-execution constructs a fresh, separately owned technical run from the
original recorded inputs (durable journal + run record + frozen plan) under
a compatible execution profile, then compares canonical science. It never
executes code contained in an artifact, never modifies the original, and
refuses with INCOMPATIBLE_REEXECUTION when any compatibility dimension
fails -- a matching AnalysisPlan digest alone is never sufficient.
"""
import os
import secrets

from . import artifacts as _artifacts
from . import integrity as _integrity
from .analysis import expand_inventory, require_frozen
from .canonical import canonical_bytes, decode_canonical
from .contracts import (AnalysisPlan, ContractError, Payload,
                        ReexecutionResult, RunDetail, RunResult, strict_json)
from .paths import EvaluationRoot
from .profile import Profile
from .science import iter_science, science_digest
from .specs import raw_bytes

MAX_DIFFERENCES = 100
MAX_REPORT_BYTES = 64 * 1024

_last_report = None


def last_report():
    return _last_report


def _set_report(report):
    global _last_report
    _last_report = report
    return report


def compatibility_report(reader, run_id, profile: Profile) -> dict:
    """Check every compatibility dimension of a published run against a
    trusted execution profile. Returns per-dimension booleans."""
    root = reader._root
    detail = reader.detail(run_id)
    manifest = strict_json(
        (root.path / 'evaluation' / 'runs' / run_id / 'manifest.json')
        .read_bytes(), max_bytes=128 * 1024)
    plan_file = strict_json(
        (root.path / 'evaluation' / 'runs' / run_id / 'analysis-plan.json')
        .read_bytes(), max_bytes=128 * 1024)
    record = _artifacts.read_run_record(root, run_id)
    experiment = record['experiment']
    plan_body = plan_file['plan']
    from .analysis import analysis_digest
    plan = AnalysisPlan(canonical_bytes(plan_body))
    inventory_ok = True
    try:
        registered = {row.identity for row in expand_inventory(plan)}
        metrics = strict_json(
            (root.path / 'evaluation' / 'runs' / run_id / 'metrics.json')
            .read_bytes(), max_bytes=256 * 1024)
        inventory_ok = {m['identity'] for m in metrics['produced']} == registered
    except ContractError:
        inventory_ok = False
    # Plan version is bound to the freeze receipt identity, not merely
    # present: the receipt identity ends with the analysis plan version.
    receipt = plan_file.get('receipt') or {}
    version = plan_body.get('analysis_plan_version')
    plan_version_ok = (type(version) is int and version >= 1
                       and plan_body.get('schema') == 'b10_analysis_plan_v1'
                       and str(receipt.get('identity', '')).endswith(
                           f'-{version}'))
    # Initial-state identity: when an initial checkpoint is declared, its
    # producer projection must compute and match the science header's
    # projected initial state exactly.
    initial_ok = True
    initial_declared = [e for e in manifest['checkpoints']
                        if e['name'] == 'initial']
    if initial_declared:
        try:
            from .science import iter_science as _iter, project_state as _ps
            import sqlite3 as _sq
            # Descriptor-relative, digest-validated read (remediation D):
            # never a plain path read of a checkpoint file.
            raw = _initial_checkpoint(root, run_id, manifest)
            if raw is None:
                raise ContractError()
            _db = _sq.connect(':memory:')
            try:
                _db.deserialize(raw)
                projected = _ps(_db)
            finally:
                _db.close()
            header = None
            for chunk in _iter(Payload(run_id, 0), root):
                header = __import__('development.evaluation.canonical',
                                    fromlist=['decode_canonical']
                                    ).decode_canonical(chunk)
                break
            initial_ok = header is not None \
                and header.get('initial_state') == projected
        except Exception:
            initial_ok = False
    # Source availability: in a real git checkout the supplied profile must
    # equal the captured trusted profile; fixture roots have no checkout.
    source_available = True
    checkout_kind = 'non_git_fixture'
    if (root.path.parent / '.git').exists():
        checkout_kind = 'git_checkout'
        try:
            from .profile import capture_profile
            captured = capture_profile(root)
            source_available = (captured.source_commit == profile.source_commit
                                and captured.lock_digest == profile.lock_digest
                                and captured.digest == profile.digest)
        except Exception:
            source_available = False
    engine = _registered_scenario(root, run_id, record)
    execution_inputs = _execution_inputs(root, run_id, record, manifest,
                                         engine)
    checks = dict(
        scenario=engine is not None,
        execution_inputs=execution_inputs is not None,
        source_commit=experiment['source_commit'] == profile.source_commit,
        source_clean=profile.clean is True,
        lock=experiment['lock_digest'] == profile.lock_digest,
        schema=profile.schema_version == 7,
        producer_versions=experiment['adapter_version'] == profile.adapter_version,
        plan_digest=plan_file['digest'] == analysis_digest(plan)
        and manifest['plan_digest'] == plan_file['digest'],
        plan_version=plan_version_ok,
        inventory=inventory_ok,
        protocol=experiment['protocol'] == 'PREQUENTIAL'
        and plan_body.get('members') is not None,
        population=bool(plan_body.get('populations')),
        windows=bool(plan_body.get('windows')),
        baselines=bool(plan_body.get('baselines')),
        profile_digest=experiment['profile_digest'] == profile.digest,
        initial_state=initial_ok,
        source_availability=source_available)
    # Protocol recorded in the experiment identity must match the frozen
    # plan's member protocols.
    member_protocols = {m.get('protocol') for m in plan_body.get('members', [])}
    checks['protocol'] = checks['protocol'] and \
        experiment['protocol'] in member_protocols
    return dict(run_id=run_id, compatible=all(checks.values()), checks=checks,
                checkout=checkout_kind)


def _registered_scenario(root, run_id, record):
    """Resolve the run's registered scenario engine from its recorded
    truth. The recorded truth must equal the registered engine's own
    evaluator view exactly; anything else (including a missing scenario
    identity) means the original scenario definition is not established
    and genuine re-execution is impossible."""
    try:
        raw = (root.path / 'evaluation' / 'runs' / run_id
               / 'truth.json').read_bytes()
        truth = strict_json(raw, max_bytes=64 * 1024)
    except Exception:
        return None
    if type(truth) is not dict:
        return None
    identity = truth.get('scenario')
    try:
        if identity == 'stationary-action-v2':
            from .scenarios.stationary import StationaryScenario
            engine = StationaryScenario(
                protocol=record['experiment']['protocol'])
        elif identity == 'constrained-v1':
            from .scenarios.constrained import ConstrainedScenario
            engine = ConstrainedScenario()
        elif identity == 'rest-shift-v2':
            from .scenarios.shift import ShiftScenario
            engine = ShiftScenario()
        elif identity == 'evidence-v1':
            from .scenarios.evidence import EvidenceScenario
            engine = EvidenceScenario(truth.get('variant'))
        else:
            return None
        view = strict_json(engine.evaluator_view().body,
                           max_bytes=64 * 1024)
    except Exception:
        return None
    if view != truth:
        return None
    return engine


def _initial_checkpoint(root, run_id, manifest):
    """Return the validated initial-checkpoint bytes for a run, None
    when the run declares no checkpoints, or raise ContractError when a
    declared checkpoint cannot be validated. Only a single checkpoint
    named 'initial' is a reproducible starting state."""
    declared = manifest['checkpoints']
    if not declared:
        return None
    if len(declared) != 1 or declared[0]['name'] != 'initial':
        raise ContractError()
    import hashlib as _hl
    import sqlite3 as _sq
    from .paths import _directory, _open_nested
    from .science import project_state
    entry = declared[0]
    run_fd = _directory(root.path / 'evaluation' / 'runs' / run_id)
    try:
        fd = _open_nested(run_fd, entry['file'], 'read')
        with os.fdopen(fd, 'rb') as f:
            raw = f.read(128 * 1024 ** 2 + 1)
    finally:
        os.close(run_fd)
    if len(raw) > 128 * 1024 ** 2 or _hl.sha256(raw).hexdigest() != entry['sha256']:
        raise ContractError()
    db = _sq.connect(':memory:')
    try:
        db.deserialize(raw)
        project_state(db)
    except Exception:
        raise ContractError() from None
    finally:
        db.close()
    return raw


def _execution_inputs(root, run_id, record, manifest, engine=None):
    """Validate the original recorded execution inputs. Returns
    (execution, checkpoint_bytes), or None when genuine re-execution is
    not possible for this run."""
    if engine is None:
        engine = _registered_scenario(root, run_id, record)
    if engine is None:
        return None
    # The evidence assay runs under the frozen protocol with probe
    # subcases; the prequential driver cannot reproduce it.
    if getattr(engine, 'identity', None) == 'evidence-v1':
        return None
    execution = record.get('execution')
    if type(execution) is not dict or set(execution) != {
            'settings', 'rng_seed', 'uuid', 'training', 'measured',
            'maintenance'}:
        return None
    if type(execution['settings']) is not dict \
            or type(execution['rng_seed']) is not int \
            or not 0 <= execution['rng_seed'] < 2 ** 256 \
            or type(execution['uuid']) is not str \
            or len(execution['uuid']) != 64 \
            or any(c not in '0123456789abcdef' for c in execution['uuid']) \
            or type(execution['training']) is not int \
            or not 0 <= execution['training'] <= 512 \
            or type(execution['measured']) is not int \
            or not 1 <= execution['measured'] <= 1024 \
            or type(execution['maintenance']) is not bool:
        return None
    # Scenario phase support: constrained/shift engines serve the
    # measured phase only, so a training phase is not reproducible.
    if getattr(engine, 'identity', None) in ('constrained-v1',
                                             'rest-shift-v2') \
            and execution['training'] != 0:
        return None
    try:
        checkpoint_bytes = _initial_checkpoint(root, run_id, manifest)
    except ContractError:
        return None
    journal = (root.path / 'evaluation' / 'runs' / run_id
               / 'preupdate.ndjson').read_bytes()
    counts = {'training': 0, 'measured': 0}
    seen = set()
    for line in journal.splitlines():
        if not line.strip():
            continue
        header = strict_json(line, max_bytes=64 * 1024)['header']
        key = (header['phase'], header['subcase'],
               header['transition_ordinal'])
        if header['subcase'] != 'default' \
                or header['phase'] not in counts or key in seen:
            return None
        seen.add(key)
        counts[header['phase']] += 1
    for phase in counts:
        expected = execution['training'] if phase == 'training' \
            else execution['measured']
        ordinals = sorted(k[2] for k in seen if k[0] == phase)
        if ordinals != list(range(1, expected + 1)):
            return None
    return execution, checkpoint_bytes


def _execute_fresh(root, run_id, execution, new_id, engine,
                   checkpoint_bytes, *, measurement_evidence_keys=()):
    """Execute a fresh run in an evaluator-owned workspace.

    The disposable root lives inside the target root's work area (never
    an unrestricted external temp root), is admitted against the target
    root's budget, and is destroyed afterwards. The scenario is the
    registered engine resolved from the run's recorded truth, so the
    environment outcomes are computed for the actions the fresh learner
    actually selects. When the original run declared a validated initial
    checkpoint, the fresh learner starts from that owned state through
    the approved completed-fixture launch pathway.

    Retain the historical status-only update projection, with fresh
    measurement sidecars only at keys where the original recorded them.
    Legacy missing evidence is not retrofitted, and no original sidecar
    values are used to produce the fresh evidence. Richer original update
    bodies remain intact for comparison; they are not pruned to force a match.
    """
    import json as _json
    import shutil

    from .channel import ChannelRouter
    from .checkpoint import ScoreJournal
    from .contracts import RunRequest, WorkerLaunch
    from .paths import EvaluationRoot as _Root
    from .prequential import PrequentialDriver
    from .worker import WorkerHandle

    root.budget.require_capacity(bytes=0, runs=1)
    checkout = root.path / 'work' / new_id
    if checkout.exists():
        raise ContractError()
    checkout.mkdir(mode=0o700)
    try:
        droot = _Root.create(checkout)
        capability = droot.assign_learner(new_id, 0)
        settings = _json.dumps(execution['settings'], sort_keys=True,
                               separators=(',', ':')).encode('ascii')
        if checkpoint_bytes is not None:
            from .state import CompletedFixture, _fixture_facts
            fd = capability.open('state', 'db', 'create')
            with os.fdopen(fd, 'wb') as f:
                f.write(checkpoint_bytes)
                f.flush()
                os.fsync(f.fileno())
            fixture = CompletedFixture(capability,
                                       *_fixture_facts(capability))
            launch = WorkerLaunch(capability, settings,
                                  execution['rng_seed'], execution['uuid'],
                                  launch_mode='COMPLETED_OWNED_FIXTURE',
                                  fixture=fixture)
        else:
            launch = WorkerLaunch(capability, settings,
                                  execution['rng_seed'], execution['uuid'])
        journal = ScoreJournal.create(droot, new_id)
        router = ChannelRouter(engine, journal=journal)
        worker = WorkerHandle.start(launch, channel=router)
        driver = PrequentialDriver(training=execution['training'],
                                   measured=execution['measured'],
                                   maintenance=execution['maintenance'])
        result = driver.run(RunRequest(new_id), worker)
        journal.close()
        fresh = journal.path.read_bytes()
        events = []
        for item in driver.events:
            body = strict_json(item.body, max_bytes=64 * 1024)
            projected = dict(
                acked=body['acked'], execution=body['execution'],
                decision_id=body.get('decision_id'),
                updates={k: {'status': v['status']}
                         for k, v in body['updates'].items()})
            if item.key in measurement_evidence_keys \
                    and 'measurement_evidence' in body:
                projected['measurement_evidence'] = body['measurement_evidence']
            events.append(dict(key=list(item.key), body=projected))
        attempts = []
        for raw in driver.skipped:
            item = strict_json(raw, max_bytes=512)
            attempts.append(dict(key=item['key'], status='skipped',
                                 reason=item['reason']))
        return result, fresh, events, attempts
    finally:
        shutil.rmtree(checkout, ignore_errors=True)


def _first_difference(left, right, path=''):
    if type(left) is not type(right):
        return path or '$', left, right
    if type(left) is dict:
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                return f'{path}.{key}' if path else key, \
                    left.get(key), right.get(key)
            found = _first_difference(left[key], right[key],
                                      f'{path}.{key}' if path else key)
            if found:
                return found
        return None
    if type(left) is list:
        if len(left) != len(right):
            return path, f'len={len(left)}', f'len={len(right)}'
        for i, (a, b) in enumerate(zip(left, right)):
            found = _first_difference(a, b, f'{path}[{i}]')
            if found:
                return found
        return None
    if left != right:
        return path, left, right
    return None


def compare_science(reader, left_id, right_id) -> dict:
    """Compare two published runs' canonical science, earliest first."""
    root = reader._root
    left_sections = [decode_canonical(c) for c in
                     iter_science(Payload(left_id, 0), root)]
    right_sections = [decode_canonical(c) for c in
                      iter_science(Payload(right_id, 0), root)]
    differences = []
    for left, right in zip(left_sections, right_sections):
        found = _first_difference(left, right)
        if found:
            field, expected, actual = found
            entry = dict(field=field, expected=expected, actual=actual)
            if left.get('kind') == 'transition':
                entry.update(phase=left['key'][0], subcase=left['key'][1],
                             ordinal=left['key'][2])
            differences.append(entry)
            if len(differences) >= MAX_DIFFERENCES:
                break
    if len(left_sections) != len(right_sections) and not differences:
        differences.append(dict(field='section_count',
                                expected=len(left_sections),
                                actual=len(right_sections)))
    status = 'SCIENTIFIC_MATCH' if not differences else 'SCIENTIFIC_DIVERGENCE'
    report = dict(status=status, left=left_id, right=right_id,
                  differences=differences)
    if len(raw_bytes(report)) > MAX_REPORT_BYTES:
        while len(raw_bytes(report)) > MAX_REPORT_BYTES and report['differences']:
            report['differences'].pop()
        report['truncated'] = True
    return _set_report(report)


def reexecute(reader, run_id: str, profile: Profile) -> ReexecutionResult:
    """Construct a fresh owned run from the original recorded inputs and
    compare its canonical science with the original."""
    root = reader._root
    if type(root) is not EvaluationRoot or type(profile) is not Profile:
        raise ContractError()
    detail = reader.detail(run_id)
    summary = strict_json(detail.summary.body, max_bytes=912 * 1024)
    if summary['status'] != 'COMPLETED':
        _set_report(dict(status='INCOMPLETE_COMPARISON', run_id=run_id))
        return ReexecutionResult('incompatible', ('INCOMPLETE_COMPARISON',))
    report = compatibility_report(reader, run_id, profile)
    if not report['compatible']:
        failed = tuple(k for k, ok in report['checks'].items() if not ok)
        _set_report(dict(status='INCOMPATIBLE_REEXECUTION', run_id=run_id,
                         checks=report['checks']))
        return ReexecutionResult('incompatible', failed)
    record = _artifacts.read_run_record(root, run_id)
    runs = strict_json((root.path / 'evaluation' / 'runs-index.json')
                       .read_bytes(), max_bytes=128 * 1024)['runs']
    if len(runs) >= 32:
        raise ContractError()
    new_id = secrets.token_hex(16)
    source_dir = root.path / 'evaluation' / 'runs' / run_id
    manifest = strict_json((source_dir / 'manifest.json').read_bytes(),
                           max_bytes=128 * 1024)
    engine = _registered_scenario(root, run_id, record)
    inputs = _execution_inputs(root, run_id, record, manifest, engine)
    if inputs is None:
        raise ContractError()
    execution, checkpoint_bytes = inputs
    measurement_evidence_keys = frozenset(
        tuple(event['key']) for event in record['events']
        if type(event['body']) is dict and 'measurement_evidence' in event['body'])
    result, fresh, events, attempts = _execute_fresh(
        root, run_id, execution, new_id, engine, checkpoint_bytes,
        measurement_evidence_keys=measurement_evidence_keys)
    # Admission BEFORE the first staging write (remediation C): the
    # fresh journal and any checkpoint copy are charged, plus the new
    # retained-run slot, before the partial directory appears.
    root.budget.require_capacity(
        bytes=len(fresh) + (len(checkpoint_bytes)
                            if checkpoint_bytes is not None else 0),
        runs=1)
    partials = root.path / 'evaluation' / 'partials'
    staging = partials / new_id
    staging.mkdir(mode=0o700)
    (staging / 'preupdate.ndjson').write_bytes(fresh)
    if checkpoint_bytes is not None:
        # The fresh run genuinely started from the validated initial
        # checkpoint, so its artifact declares the same starting state.
        (staging / 'checkpoints').mkdir(mode=0o700)
        (staging / 'checkpoints' / 'initial.sqlite3').write_bytes(
            checkpoint_bytes)
    plan_file = strict_json((source_dir / 'analysis-plan.json').read_bytes(),
                            max_bytes=128 * 1024)
    frozen = require_frozen(AnalysisPlan(canonical_bytes(plan_file['plan'])), root)
    new_record = dict(record, run_id=new_id, status=result.status,
                      reason=result.reason, events=events, attempts=attempts,
                      planned_transitions=execution['training']
                      + execution['measured'],
                      measurements=[], findings=[], failure=None)
    if result.status != 'COMPLETED':
        _artifacts.write_run_record(root, new_record)
        try:
            _artifacts.assemble_payload(result, frozen, root, run_id=new_id)
        except ContractError:
            pass
        _set_report(dict(status='INCOMPLETE_COMPARISON', run_id=run_id,
                         new_run_id=new_id, execution_status=result.status,
                         reason=result.reason))
        return ReexecutionResult('incompatible', ('INCOMPLETE_COMPARISON',))
    frames = _artifacts._journal_frames(fresh)
    rows, findings = _artifacts.derive_scientific_outputs(
        frozen, frames, [], 'COMPLETED', post_ack_events=events)
    new_record = dict(new_record, measurements=list(rows), findings=findings)
    _artifacts.write_run_record(root, new_record)
    payload = _artifacts.assemble_payload(
        RunResult('COMPLETED', None), frozen, root, run_id=new_id)
    finalized = _integrity.finalize_payload(payload, root)
    _integrity.publish(finalized, _integrity.make_receipt(finalized, root), root)
    new_digest = science_digest(Payload(new_id, 0), root)
    old_digest = science_digest(Payload(run_id, 0), root)
    if new_digest == old_digest:
        _set_report(dict(status='SCIENTIFIC_MATCH', run_id=run_id,
                         new_run_id=new_id, science_digest=new_digest,
                         checks=report['checks']))
        return ReexecutionResult('matched', ())
    comparison = compare_science(reader, run_id, new_id)
    _set_report(dict(comparison, new_run_id=new_id))
    return ReexecutionResult(
        'divergent', tuple(d['field'] for d in comparison['differences']))


def compare(left: RunDetail, right: RunDetail, metric_id: str):
    """Descriptive side-by-side of one metric. Never a scientific
    classification: no improved/worse/equality verdict is produced."""
    def extract(detail):
        body = strict_json(detail.summary.body, max_bytes=912 * 1024)
        for item in body.get('measurements', []):
            if item['identity'] == metric_id or item['metric'] == metric_id:
                return dict(identity=item['identity'], state=item['state'],
                            value=item['value'], reason=item['reason'])
        return dict(identity=None, state='UNAVAILABLE', value=None,
                    reason='metric_not_in_detail')
    return dict(metric_id=metric_id, left=extract(left), right=extract(right),
                classification='DESCRIPTIVE_ONLY')
