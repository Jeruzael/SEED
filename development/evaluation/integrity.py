"""Whole-byte integrity, detached receipts and atomic publication (I23).

Integrity domain ``SEED_B10_ARTIFACT_V1\\0`` hashes the exact stored payload
bytes (ASCII filename order, unsigned 64-bit big-endian length framing). It
is distinct from the canonical scientific digest (I22): incidental byte
changes break integrity without changing science, and a changed scientific
outcome changes both. A matching payload+receipt pair proves consistency
against the recorded receipt only -- never author authenticity.
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass

from . import artifacts as _artifacts
from . import indexes as _indexes
from .contracts import ContractError, Payload, Receipt, strict_json
from .paths import EvaluationRoot, _directory, _mkdir, _open_file
from .science import science_digest
from .specs import raw_bytes

DOMAIN = b'SEED_B10_ARTIFACT_V1\0'
RECEIPT_BYTES = 16 * 1024
_ALLOW = {'manifest.json', 'analysis-plan.json', 'preupdate.ndjson',
          'events.ndjson', 'metrics.json', 'truth.json', 'chunks.json',
          'index.json', 'operations.ndjson'}
_CHECKPOINT = re.compile(r'checkpoints/[a-z0-9][a-z0-9-]*\.sqlite3')


@dataclass(frozen=True)
class RunArtifact:
    run_id: str
    receipt: Receipt
    science_digest: str
    status: str


def _root(capability):
    if type(capability) is not EvaluationRoot:
        raise ContractError()
    fd = capability._validate()
    os.close(fd)
    return capability


def payload_directory(root, run_id):
    for base in ('partials', 'runs'):
        candidate = root.path / 'evaluation' / base / run_id
        if candidate.is_dir():
            return candidate
    raise ContractError()


def _payload_files(directory):
    files = {}
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if entry.is_dir(follow_symlinks=False):
            if entry.name != 'checkpoints':
                raise ContractError()
            for sub in sorted(os.scandir(entry.path), key=lambda e: e.name):
                name = f'checkpoints/{sub.name}'
                if not _CHECKPOINT.fullmatch(name) or not sub.is_file(follow_symlinks=False):
                    raise ContractError()
                files[name] = _read_file(sub.path)
        elif entry.is_file(follow_symlinks=False):
            if entry.name not in _ALLOW:
                raise ContractError()
            files[entry.name] = _read_file(entry.path)
        else:
            raise ContractError()
    return files


def _read_file(path):
    import os as _os
    size = _os.path.getsize(path)
    if size > _artifacts.ARTIFACT_BYTES:
        raise ContractError()
    with open(path, 'rb') as f:
        data = f.read(size + 1)
    if len(data) != size:
        raise ContractError()
    return data


def _digest_files(files):
    digest = hashlib.sha256(DOMAIN)
    for name in sorted(files):
        encoded = name.encode('ascii')
        data = files[name]
        digest.update(len(encoded).to_bytes(8, 'big'))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


FIXED_FILES = frozenset(_ALLOW)


def validate_file_set(directory, manifest):
    expected = set(FIXED_FILES) | {entry['file']
                                    for entry in manifest['checkpoints']}
    actual = set(_payload_files(directory))
    if actual != expected:
        raise ContractError()
    return actual


def integrity_digest(payload: Payload, capability) -> str:
    root = _root(capability)
    files = _payload_files(payload_directory(root, payload.identity))
    return _digest_files(files)


def receipt_body(payload: Payload, capability) -> dict:
    root = _root(capability)
    _artifacts._run_id(payload.identity)
    directory = payload_directory(root, payload.identity)
    manifest = strict_json(_read_file(directory / 'manifest.json'),
                           max_bytes=128 * 1024)
    validate_file_set(directory, manifest)
    files = _payload_files(directory)
    body = dict(schema='b10_receipt_v1', run_id=payload.identity,
                files={name: dict(length=len(data),
                                  sha256=hashlib.sha256(data).hexdigest())
                       for name, data in sorted(files.items())},
                digest=_digest_files(files))
    if 'chunks.json' not in body['files']:
        raise ContractError()
    if len(raw_bytes(body)) > RECEIPT_BYTES:
        raise ContractError()
    return body


def make_receipt(payload: Payload, capability) -> Receipt:
    body = receipt_body(payload, capability)
    return Receipt(tuple(Payload(name, entry['length'])
                         for name, entry in body['files'].items()),
                   body['digest'])


def finalize_payload(payload: Payload, capability) -> Payload:
    """Bind the canonical science digest into the manifest and rebuild the
    chunk inventory, returning the finalized payload handle."""
    root = _root(capability)
    directory = payload_directory(root, payload.identity)
    if directory.parent.name != 'partials':
        raise ContractError()
    manifest = strict_json((directory / 'manifest.json').read_bytes(),
                           max_bytes=128 * 1024)
    validate_file_set(directory, manifest)
    digest = science_digest(payload, root)
    manifest['science_digest'] = digest
    manifest['publication'] = 'finalized'
    _artifacts._write_payload_file(root, payload.identity, 'manifest.json',
                                   raw_bytes(manifest))
    files = _payload_files(directory)
    files['manifest.json'] = raw_bytes(manifest)
    chunks = raw_bytes(_indexes.chunk_inventory(
        {k: v for k, v in files.items()}))
    if len(chunks) > 512 * 1024:
        raise ContractError()
    _artifacts._write_payload_file(root, payload.identity, 'chunks.json', chunks)
    files['chunks.json'] = chunks
    return Payload(payload.identity, sum(len(v) for v in files.values()))


def _fsync_tree(directory):
    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            _fsync_tree(entry.path)
        else:
            fd = os.open(entry.path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _rename(source, target):
    os.rename(source, target)


def _write_receipt(root, run_id, body):
    evaluation = _directory(root.path / 'evaluation')
    try:
        receipts = _mkdir(evaluation, 'receipts')
        try:
            fd = _open_file(receipts, f'{run_id}.json', 'create')
            with os.fdopen(fd, 'wb') as f:
                f.write(raw_bytes(body))
                f.flush()
                os.fsync(f.fileno())
            os.fsync(receipts)
        finally:
            os.close(receipts)
    finally:
        os.close(evaluation)


def _update_index(root, entry):
    evaluation = root.path / 'evaluation'
    index_path = evaluation / 'runs-index.json'
    runs = []
    if index_path.exists():
        runs = strict_json(index_path.read_bytes(),
                           max_bytes=128 * 1024)['runs']
    if any(r['run_id'] == entry['run_id'] for r in runs) or len(runs) >= 60:
        raise ContractError()
    runs.append(entry)
    data = raw_bytes(dict(schema='b10_runs_index_v1', runs=runs))
    tmp = evaluation / 'runs-index.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp, index_path)
    fd = os.open(evaluation, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(payload: Payload, receipt: Receipt, capability) -> RunArtifact:
    """Atomically publish a finalized staged payload (I23 order)."""
    root = _root(capability)
    partials = root.path / 'evaluation' / 'partials'
    runs = root.path / 'evaluation' / 'runs'
    staged = partials / payload.identity
    target = runs / payload.identity
    if not staged.is_dir() or target.exists():
        raise ContractError()
    _artifacts._run_id(payload.identity)
    expected = make_receipt(payload, root)
    if receipt.digest != expected.digest or receipt.payloads != expected.payloads:
        raise ContractError()
    manifest = strict_json((staged / 'manifest.json').read_bytes(),
                           max_bytes=128 * 1024)
    validate_file_set(staged, manifest)
    if manifest.get('publication') != 'finalized' or not manifest.get('science_digest'):
        raise ContractError()
    metrics = strict_json((staged / 'metrics.json').read_bytes(),
                          max_bytes=256 * 1024)
    if {m['identity'] for m in metrics['produced']} != set(metrics['registered']):
        raise ContractError()
    _fsync_tree(staged)
    _rename(staged, target)
    body = receipt_body(payload, root)
    _write_receipt(root, payload.identity, body)
    record = partials / f'{payload.identity}.record.json'
    if record.exists():
        _rename(record, root.path / 'evaluation' / 'receipts'
                / f'{payload.identity}.record.json')
    _update_index(root, dict(run_id=payload.identity, digest=receipt.digest,
                             science_digest=manifest['science_digest'],
                             status=manifest['status']))
    return RunArtifact(payload.identity, receipt, manifest['science_digest'],
                       manifest['status'])


def verify_receipt(capability, run_id) -> bool:
    """Recompute the payload inventory against the detached receipt."""
    try:
        root = _root(capability)
        raw = (root.path / 'evaluation' / 'receipts' / f'{run_id}.json').read_bytes()
        if len(raw) > RECEIPT_BYTES:
            return False
        body = strict_json(raw, max_bytes=RECEIPT_BYTES)
        if body.get('schema') != 'b10_receipt_v1' or body.get('run_id') != run_id:
            return False
        directory = root.path / 'evaluation' / 'runs' / run_id
        if not directory.is_dir():
            return False
        files = _payload_files(directory)
        if set(files) != set(body['files']):
            return False
        for name, data in files.items():
            entry = body['files'][name]
            if entry['length'] != len(data) \
                    or entry['sha256'] != hashlib.sha256(data).hexdigest():
                return False
        return body['digest'] == _digest_files(files)
    except Exception:
        return False
