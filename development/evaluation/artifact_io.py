"""Leaf-level artifact IO: caps, run-record staging paths and payload
file writes shared by assembly (artifacts) and publication (integrity).

This module deliberately imports nothing beyond contracts/paths/specs so
the read path (reader -> replay -> integrity) never transitively reaches
the scientific derivation or scenario machinery.
"""
import os
import re

from .contracts import ContractError
from .paths import _directory, _mkdir, _open_nested, _unlink_nested

DETAIL_BYTES = 64 * 1024
TOTAL_DETAIL_BYTES = 64 * 1024 ** 2
SNAPSHOT_BYTES = 128 * 1024 ** 2
ARTIFACT_BYTES = 224 * 1024 ** 2
CONTROL_BYTES = 4 * 1024 ** 2
OPERATIONAL_BYTES = 4 * 1024 ** 2
MAX_FILES = 32
MAX_TRANSITIONS = 1024
MAX_ATTEMPTS = 2048
FILE_CAPS = {'manifest.json': 128 * 1024, 'analysis-plan.json': 128 * 1024,
             'index.json': 128 * 1024, 'metrics.json': 256 * 1024,
             'chunks.json': 512 * 1024}
PAYLOAD_FILES = ('manifest.json', 'analysis-plan.json', 'preupdate.ndjson',
                 'events.ndjson', 'metrics.json', 'truth.json', 'index.json',
                 'operations.ndjson')
RECORD_SCHEMA = 'b10_run_record_v1'
_RUN_ID = re.compile(r'[0-9a-f]{32}')


def _run_id(value):
    if type(value) is not str or not _RUN_ID.fullmatch(value):
        raise ContractError()
    return value


def _partials_fd(root):
    evaluation = _directory(root.path / 'evaluation')
    try:
        return _mkdir(evaluation, 'partials')
    finally:
        os.close(evaluation)


def _record_path(root, run_id):
    return root.path / 'evaluation' / 'partials' / f'{run_id}.record.json'


def _read_staged(root, run_id, name, maximum):
    run_dir = _directory(root.path / 'evaluation' / 'partials' / run_id)
    try:
        fd = _open_nested(run_dir, name, 'read')
        with os.fdopen(fd, 'rb') as f:
            return f.read(maximum + 1)
    finally:
        os.close(run_dir)


def _write_payload_file(root, run_id, name, data):
    # Admission before replacing/writing any payload file: the new bytes
    # are charged against current on-disk usage (which already includes
    # any previous version), so nothing is double counted.
    root.budget.require_capacity(bytes=len(data))
    run_dir = _directory(root.path / 'evaluation' / 'partials' / run_id)
    try:
        try:
            _unlink_nested(run_dir, name)
        except FileNotFoundError:
            pass
        fd = _open_nested(run_dir, name, 'create')
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.fsync(run_dir)
    finally:
        os.close(run_dir)


