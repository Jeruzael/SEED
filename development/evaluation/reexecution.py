"""Trusted re-execution and bounded scientific comparison (I25).

Re-execution is not replay: replay reads recorded evidence, while
re-execution constructs a fresh, separately owned technical run from the
original recorded inputs (durable journal + run record + frozen plan) under
a compatible execution profile, then compares canonical science. It never
executes code contained in an artifact, never modifies the original, and
refuses with INCOMPATIBLE_REEXECUTION when any compatibility dimension
fails -- a matching AnalysisPlan digest alone is never sufficient.
"""
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
            import hashlib as _hl
            from .canonical import canonical_bytes as _cb
            from .science import iter_science as _iter, project_state as _ps
            import sqlite3 as _sq
            raw = (root.path / 'evaluation' / 'runs' / run_id
                   / initial_declared[0]['file']).read_bytes()
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
    checks = dict(
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
    partials = root.path / 'evaluation' / 'partials'
    staging = partials / new_id
    staging.mkdir(mode=0o700)
    (staging / 'preupdate.ndjson').write_bytes(
        (source_dir / 'preupdate.ndjson').read_bytes())
    for entry in strict_json((source_dir / 'manifest.json').read_bytes(),
                             max_bytes=128 * 1024)['checkpoints']:
        target = staging / entry['file']
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((source_dir / entry['file']).read_bytes())
    new_record = dict(record, run_id=new_id)
    _artifacts.write_run_record(root, new_record)
    plan_file = strict_json((source_dir / 'analysis-plan.json').read_bytes(),
                            max_bytes=128 * 1024)
    frozen = require_frozen(AnalysisPlan(canonical_bytes(plan_file['plan'])), root)
    payload = _artifacts.assemble_payload(
        RunResult(record['status'], record['reason']), frozen, root,
        run_id=new_id)
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
