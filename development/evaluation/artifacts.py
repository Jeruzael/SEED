"""Lossless bounded artifact payload assembly (I21).

The coordinator-side run record is staged next to the parent-owned durable
journal in ``evaluation/partials/<run-id>/``. Assembly reuses that journal in
place (never copies or rewrites it), joins post-ACK events to journal frames
by their closed tuple and evidence digest, reconciles the produced
measurement inventory against the frozen plan, and writes the fixed
``b10_artifact_v1`` payload files into the same owned directory. The result
is untrusted/pending until I22 science validation and I23 integrity
publication.
"""
import hashlib
import json
import os
import re

from . import indexes as _indexes
from .artifact_io import (CONTROL_BYTES, DETAIL_BYTES, FILE_CAPS, MAX_ATTEMPTS,
                          MAX_FILES, MAX_TRANSITIONS, OPERATIONAL_BYTES,
                          PAYLOAD_FILES, RECORD_SCHEMA, SNAPSHOT_BYTES,
                          TOTAL_DETAIL_BYTES, ARTIFACT_BYTES, _partials_fd,
                          _read_staged, _record_path, _run_id,
                          _write_payload_file)
from .analysis import expand_inventory
from .contracts import (CompletedEvidence, ContractError, FrozenPlan, Payload,
                        Population, RootCapability, RunResult, strict_json,
                        validate_event_key)
from .paths import EvaluationRoot, _directory, _identity, _mkdir, _open_file
from .specs import raw_bytes


_CHECKPOINT = re.compile(r'checkpoints/[a-z0-9][a-z0-9-]*\.sqlite3')


def _root(capability):
    if type(capability) is not EvaluationRoot:
        raise ContractError()
    fd = capability._validate()
    os.close(fd)
    return capability


def write_run_record(capability, record):
    """Stage (or restage) the coordinator-side run record for one run."""
    root = _root(capability)
    if type(record) is not dict or record.get('schema') != RECORD_SCHEMA:
        raise ContractError()
    run_id = _run_id(record.get('run_id'))
    if (root.path / 'evaluation' / 'runs' / run_id).exists() or \
            (root.path / 'evaluation' / 'receipts'
             / f'{run_id}.record.json').exists():
        raise ContractError()
    data = raw_bytes(record)
    if len(data) > CONTROL_BYTES:
        raise ContractError()
    # Admission BEFORE the first allocation: a new run identity charges
    # one retained-run slot; the temporary record file charges its peak
    # bytes (it coexists with any previous record until the rename).
    new_run = not (root.path / 'evaluation' / 'partials' / run_id).is_dir()
    root.budget.require_capacity(bytes=len(data), runs=1 if new_run else 0)
    partials = _partials_fd(root)
    try:
        run_dir = _mkdir(partials, run_id)
        os.close(run_dir)
        tmp = _open_file(partials, f'{run_id}.record.tmp', 'create')
        try:
            with os.fdopen(tmp, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            os.unlink(f'{run_id}.record.tmp', dir_fd=partials)
            raise
        os.rename(f'{run_id}.record.tmp', f'{run_id}.record.json',
                  src_dir_fd=partials, dst_dir_fd=partials)
        os.fsync(partials)
    finally:
        os.close(partials)
    return run_id


def read_run_record(capability, run_id):
    root = _root(capability)
    _run_id(run_id)
    partials = _partials_fd(root)
    try:
        try:
            fd = _open_file(partials, f'{run_id}.record.json', 'read')
        except ContractError:
            evaluation = _directory(root.path / 'evaluation')
            try:
                receipts = _mkdir(evaluation, 'receipts')
                try:
                    fd = _open_file(receipts, f'{run_id}.record.json', 'read')
                finally:
                    os.close(receipts)
            finally:
                os.close(evaluation)
        with os.fdopen(fd, 'rb') as f:
            raw = f.read(CONTROL_BYTES + 1)
    finally:
        os.close(partials)
    if len(raw) > CONTROL_BYTES:
        raise ContractError()
    record = strict_json(raw, max_bytes=CONTROL_BYTES)
    if type(record) is not dict or record.get('schema') != RECORD_SCHEMA \
            or record.get('run_id') != run_id:
        raise ContractError()
    return record


def _journal_frames(raw):
    frames = {}
    total = 0
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            continue
        if len(line) > DETAIL_BYTES:
            raise ContractError()
        total += len(line)
        record = strict_json(line, max_bytes=DETAIL_BYTES)
        header = record['header']
        key = (header['phase'], header['subcase'], header['transition_ordinal'])
        if key in frames:
            raise ContractError()
        frames[key] = (line if line.endswith(b'\n') else line + b'\n', header)
    if len(frames) > MAX_TRANSITIONS or total > TOTAL_DETAIL_BYTES:
        raise ContractError()
    return frames


def _event_lines(record, frames):
    events = record.get('events')
    attempts = record.get('attempts')
    if type(events) is not list or type(attempts) is not list \
            or len(events) + len(attempts) > MAX_ATTEMPTS:
        raise ContractError()
    joined = {}
    lines = []
    detail_total = 0
    merged = []
    seen_keys = set()

    def scan(value):
        if type(value) is dict:
            if {'prediction', 'state_before', 'state_after'} & set(value):
                raise ContractError()
            for item in value.values():
                scan(item)
        elif type(value) is list:
            for item in value:
                scan(item)

    for event in events:
        if type(event) is not dict or set(event) != {'key', 'body'}:
            raise ContractError()
        key = validate_event_key(event['key'])
        if key in seen_keys:
            raise ContractError()
        seen_keys.add(key)
        body = event['body']
        scan(body)
        merged.append((key, body))
    for attempt in attempts:
        if type(attempt) is not dict or set(attempt) != {'key', 'status', 'reason'} \
                or attempt['status'] != 'skipped':
            raise ContractError()
        key = validate_event_key(attempt['key'])
        if key in seen_keys:
            raise ContractError()
        seen_keys.add(key)
        merged.append((key, dict(status='skipped', reason=attempt['reason'])))
    merged.sort(key=lambda item: item[0])
    for key, body in merged:
        frame_key = key[:3]
        if key[3] == 'update':
            if frame_key not in frames or frame_key in joined:
                raise ContractError()
            joined[frame_key] = True
            line_bytes, header = frames[frame_key]
            out = dict(key=list(key), journal_sha256=hashlib.sha256(line_bytes).hexdigest(),
                       evidence_sha256=header['evidence_sha256'], body=body)
            encoded = raw_bytes(out) + b'\n'
            if len(line_bytes) + len(encoded) > DETAIL_BYTES:
                raise ContractError()
            detail_total += len(line_bytes) + len(encoded)
        else:
            out = dict(key=list(key), journal_sha256=None, evidence_sha256=None, body=body)
            encoded = raw_bytes(out) + b'\n'
            if len(encoded) > DETAIL_BYTES:
                raise ContractError()
            detail_total += len(encoded)
        if detail_total > TOTAL_DETAIL_BYTES:
            raise ContractError()
        lines.append(encoded)
    return b''.join(lines), len(joined), len(attempts)


def _checkpoints(root, run_id, record):
    declared = record.get('checkpoints')
    if type(declared) is not list or len(declared) > 8:
        raise ContractError()
    entries = []
    total = 0
    run_dir_path = root.path / 'evaluation' / 'partials' / run_id
    if len({item.get('name') for item in declared if type(item) is dict}) != len(declared) \
            or len({item.get('file') for item in declared if type(item) is dict}) != len(declared):
        raise ContractError()
    for item in declared:
        if type(item) is not dict or set(item) != {'name', 'file'} \
                or type(item['file']) is not str or not _CHECKPOINT.fullmatch(item['file']):
            raise ContractError()
        name = item['file'].split('/', 1)[1]
        data = _read_staged(root, run_id, f'checkpoints/{name}', SNAPSHOT_BYTES)
        if len(data) > SNAPSHOT_BYTES or not data.startswith(b'SQLite format 3\x00'):
            raise ContractError()
        for suffix in ('-wal', '-shm'):
            if (run_dir_path / f"{item['file']}{suffix}").exists():
                raise ContractError()
        import sqlite3 as _sqlite3
        _db = _sqlite3.connect(':memory:')
        try:
            _db.deserialize(data)
            _db.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        except _sqlite3.Error:
            raise ContractError() from None
        finally:
            _db.close()
        total += len(data)
        if total > SNAPSHOT_BYTES:
            raise ContractError()
        entries.append(dict(name=item['name'], file=item['file'], bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest()))
    return entries


def derive_scientific_outputs(plan, frames, checkpoint_data, status):
    """Recompute every registered measurement and question finding from the
    recorded evidence with the original I16-I19 scientific machinery.

    This is the only derivation used both by producers (to build an honest
    run record) and by assembly (to reconcile one). A record never becomes
    scientific fact by assertion: supplied values must equal these.
    """
    from .metrics.findings import classify_questions
    from .metrics.prediction import measure_prediction
    from .metrics.producers import measure_producers
    from .metrics.registry import measurement_data
    evidence = []
    for key in sorted(frames):
        line, header = frames[key]
        record = strict_json(line, max_bytes=DETAIL_BYTES)
        evidence.append(CompletedEvidence(
            (key[0], key[1], key[2], 'checkpoint'),
            raw_bytes(record['evidence'])))
    evidence = tuple(evidence)
    registered = expand_inventory(plan.plan)
    derived = {}
    measured_objects = {}
    prediction_rows = [r for r in registered if r.metric.startswith('prediction.')]
    producer_rows = [r for r in registered if not r.metric.startswith('prediction.')]
    for registered_row in prediction_rows:
        member, metric, population, window = registered_row.identity.split(':')
        pop = Population(population, (member,),
                         window.removesuffix('~exploratory'), registered_row.role)
        m = measure_prediction(metric, evidence, pop, plan)
        measured_objects[m.identity] = m
        data = measurement_data(m)
        derived[m.identity] = dict(identity=m.identity, metric=m.metric,
                                   version=m.version, member=m.member,
                                   state=m.state, value=data.get('value'),
                                   reason=data.get('reason'))
    measurements = []
    if producer_rows:
        sources = {}
        if checkpoint_data:
            import sqlite3 as _sqlite3
            from .science import project_state
            db = _sqlite3.connect(':memory:')
            try:
                db.deserialize(checkpoint_data[-1])
                source = project_state(db)
            except Exception:
                raise ContractError() from None
            finally:
                db.close()
            for member in {r.member for r in producer_rows}:
                sources[member] = source
        for m in measure_producers(evidence, sources, plan):
            measured_objects[m.identity] = m
            data = measurement_data(m)
            derived[m.identity] = dict(identity=m.identity, metric=m.metric,
                                       version=m.version, member=m.member,
                                       state=m.state, value=data.get('value'),
                                       reason=data.get('reason'))
    ordered = tuple(derived[row.identity] for row in registered)
    findings = classify_questions(
        plan, tuple(measured_objects[row.identity] for row in registered),
        status)
    return ordered, [dict(question=f.question, status=f.status,
                           reason=f.reason, execution=f.execution)
                      for f in findings]


def _row_key(row):
    return raw_bytes(dict(metric=row['metric'], version=row['version'],
                          member=row['member'], state=row['state'],
                          value=row['value'], reason=row['reason']))


def _metrics(record, plan, status, reason, frames, checkpoint_data):
    registered_rows = expand_inventory(plan.plan)
    registered = sorted({row.identity for row in registered_rows})
    produced_in = record.get('measurements')
    if type(produced_in) is not list:
        raise ContractError()
    supplied = {}
    for item in produced_in:
        if type(item) is not dict \
                or set(item) != {'identity', 'metric', 'version', 'member', 'state', 'value', 'reason'} \
                or item['identity'] not in registered or item['identity'] in supplied \
                or item['state'] not in ('MEASURED', 'UNAVAILABLE', 'NOT_EVALUATED'):
            raise ContractError()
        supplied[item['identity']] = item
    derived_rows, derived_findings = derive_scientific_outputs(
        plan, frames, checkpoint_data, status)
    derived = {row['identity']: row for row in derived_rows}
    # Every supplied measurement must equal the scientific derivation from
    # the recorded evidence; a COMPLETED run must supply every registered
    # row. Missing rows are preserved as UNAVAILABLE only for genuinely
    # incomplete or failed runs.
    for identity, item in supplied.items():
        if _row_key(item) != _row_key(derived[identity]):
            raise ContractError()
    if status == 'COMPLETED' and set(supplied) != set(registered):
        raise ContractError()
    produced = {}
    for identity in registered:
        if identity in supplied:
            produced[identity] = supplied[identity]
        else:
            produced[identity] = dict(derived[identity], state='UNAVAILABLE',
                                      value=None, reason=reason or 'not_produced')
    findings = record.get('findings')
    if type(findings) is not list:
        raise ContractError()
    for finding in findings:
        if type(finding) is not dict \
                or set(finding) != {'question', 'status', 'reason', 'execution'}:
            raise ContractError()
    if findings:
        if sorted(raw_bytes(f) for f in findings) != \
                sorted(raw_bytes(f) for f in derived_findings):
            raise ContractError()
    elif status == 'COMPLETED':
        raise ContractError()
    else:
        findings = derived_findings
    body = dict(schema='b10_metrics_v1', plan_digest=plan.digest,
                registered=registered,
                produced=[produced[k] for k in sorted(produced)],
                findings=findings)
    data = raw_bytes(body)
    if len(data) > FILE_CAPS['metrics.json']:
        raise ContractError()
    return data


def _operations(record):
    operations = record.get('operations')
    if type(operations) is not list or len(operations) > 4096:
        raise ContractError()
    lines = []
    for item in operations:
        if type(item) is not dict or set(item) != {'code', 'note'} \
                or type(item['code']) is not str or type(item['note']) is not str \
                or len(item['note']) > 256:
            raise ContractError()
        lines.append(raw_bytes(item) + b'\n')
    data = b''.join(lines)
    if len(data) > OPERATIONAL_BYTES:
        raise ContractError()
    return data


def _check_cap(name, data):
    cap = FILE_CAPS.get(name)
    if cap is not None and len(data) > cap:
        raise ContractError()


def assemble_payload(result: RunResult, plan: FrozenPlan, capability: RootCapability,
                     run_id: str = None) -> Payload:
    """Assemble the fixed payload inventory for one staged run.

    With ``run_id`` omitted, exactly one staged run record must exist. The
    payload stays in the owned partial directory, marked pending, until I23
    publication. Assembly never writes to the journal.
    """
    root = _root(capability)
    if type(result) is not RunResult or type(plan) is not FrozenPlan:
        raise ContractError()
    if run_id is None:
        partials = root.path / 'evaluation' / 'partials'
        staged = [p.name[:-len('.record.json')] for p in partials.iterdir()
                  if p.name.endswith('.record.json')]
        if len(staged) != 1:
            raise ContractError()
        run_id = staged[0]
    _run_id(run_id)
    record = read_run_record(root, run_id)
    if record.get('status') != result.status or record.get('reason') != result.reason:
        raise ContractError()
    experiment = record.get('experiment')
    if type(experiment) is not dict or set(experiment) != {
            'id', 'version', 'source_commit', 'lock_digest', 'profile_digest',
            'protocol', 'adapter_version'}:
        raise ContractError()
    journal_raw = _read_staged(root, run_id, 'preupdate.ndjson', TOTAL_DETAIL_BYTES)
    if len(journal_raw) > TOTAL_DETAIL_BYTES:
        raise ContractError()
    frames = _journal_frames(journal_raw)
    try:
        events_data, joined, skipped = _event_lines(record, frames)
        checkpoint_entries = _checkpoints(root, run_id, record)
        checkpoint_data = [_read_staged(root, run_id, e['file'], SNAPSHOT_BYTES)
                           for e in checkpoint_entries]
        # F5: admission against the existing root budget (which reconciles
        # retained partials, workspace, staged and published bytes from
        # disk, so crash-retained state is always accounted) precedes any
        # payload write.
        estimate = len(journal_raw) + sum(e['bytes'] for e in checkpoint_entries) \
            + sum(FILE_CAPS.values()) + OPERATIONAL_BYTES + CONTROL_BYTES
        root.budget.require_capacity(bytes=estimate)
        metrics_data = _metrics(record, plan, result.status, result.reason,
                                frames, checkpoint_data)
        operations_data = _operations(record)
        truth = record.get('truth')
        if type(truth) is not dict:
            raise ContractError()
        truth_data = raw_bytes(truth)
        plan_data = raw_bytes(dict(
            schema='b10_analysis_plan_artifact_v1',
            plan=strict_json(plan.plan.body, max_bytes=128 * 1024),
            digest=plan.digest,
            receipt=strict_json(plan.receipt, max_bytes=128 * 1024)))
        _check_cap('analysis-plan.json', plan_data)
        counts = dict(planned_transitions=record.get('planned_transitions'),
                      observed_transitions=len(frames), joined_events=joined,
                      skipped_attempts=skipped)
        if type(counts['planned_transitions']) is not int or counts['planned_transitions'] < 0:
            raise ContractError()
        if result.status == 'COMPLETED' and joined != counts['planned_transitions']:
            raise ContractError()
        manifest = dict(schema='b10_artifact_v1', run_id=run_id,
                        status=result.status, reason=result.reason,
                        experiment=experiment, plan_digest=plan.digest,
                        counts=counts, checkpoints=checkpoint_entries,
                        failure=record.get('failure'), science_digest=None,
                        publication='pending')
        manifest_data = raw_bytes(manifest)
        _check_cap('manifest.json', manifest_data)
        files = {'manifest.json': manifest_data, 'analysis-plan.json': plan_data,
                 'preupdate.ndjson': journal_raw, 'events.ndjson': events_data,
                 'metrics.json': metrics_data, 'truth.json': truth_data,
                 'operations.ndjson': operations_data}
        for entry, data in zip(checkpoint_entries, checkpoint_data):
            files[entry['file']] = data
        index_data = raw_bytes(_indexes.build_indexes(
            Payload(run_id, 0), lambda name: files[name]))
        _check_cap('index.json', index_data)
        files['index.json'] = index_data
        chunks_data = raw_bytes(_indexes.chunk_inventory(files))
        _check_cap('chunks.json', chunks_data)
        files['chunks.json'] = chunks_data
        control = sum(len(files[n]) for n in
                      ('manifest.json', 'analysis-plan.json', 'metrics.json',
                       'index.json', 'chunks.json'))
        if control > CONTROL_BYTES or len(files) > MAX_FILES:
            raise ContractError()
        total = sum(len(data) for data in files.values())
        if total > ARTIFACT_BYTES:
            raise ContractError()
        for name in ('manifest.json', 'analysis-plan.json', 'events.ndjson',
                     'metrics.json', 'truth.json', 'index.json',
                     'operations.ndjson', 'chunks.json'):
            _write_payload_file(root, run_id, name, files[name])
        return Payload(run_id, total)
    except ContractError:
        try:
            partial_fd = _directory(
                root.path / 'evaluation' / 'partials' / run_id)
        except OSError:
            partial_fd = None
        if partial_fd is not None:
            try:
                for stale in ('events.ndjson', 'metrics.json', 'truth.json',
                              'index.json', 'operations.ndjson', 'chunks.json',
                              'analysis-plan.json'):
                    try:
                        os.unlink(stale, dir_fd=partial_fd)
                    except (FileNotFoundError, OSError):
                        pass
            finally:
                os.close(partial_fd)
        _write_incomplete_manifest(root, run_id, record, experiment, plan,
                                   observed=len(frames))
        raise


def _write_incomplete_manifest(root, run_id, record, experiment, plan,
                               observed=0):
    try:
        manifest = dict(schema='b10_artifact_v1', run_id=run_id,
                        status='INCOMPLETE',
                        reason=record.get('reason') or 'ASSEMBLY_FAILED',
                        experiment=experiment, plan_digest=plan.digest,
                        counts=dict(planned_transitions=record.get('planned_transitions'),
                                    observed_transitions=observed, joined_events=0,
                                    skipped_attempts=0),
                        checkpoints=[], failure=record.get('failure'),
                        science_digest=None, publication='pending')
        _write_payload_file(root, run_id, 'manifest.json', raw_bytes(manifest))
    except Exception:
        pass
