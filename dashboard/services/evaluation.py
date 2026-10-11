"""Optional read-only Evaluation service (B10 I26).

Delegates exclusively to the dedicated bounded EvaluationReader over a
separately enabled evaluator-owned artifact root. The service never
creates the root, never falls back to the organism home, and holds no
execution capability: when the root is absent or the reader cannot be
constructed, every method reports a clear unavailable state and no
evaluator machinery is initialized.
"""
import json
from math import ceil
from pathlib import Path

from development.evaluation.contracts import ContractError, strict_json
from development.evaluation.paths import EvaluationRoot
from development.evaluation.reader import (EvaluationReader, ReaderError)

from .read_store import ServiceError

_CHUNK = 64 * 1024


class EvaluationService:
    def __init__(self, reader: EvaluationReader | None):
        self._reader = reader

    @classmethod
    def from_root(cls, checkout) -> 'EvaluationService':
        """Open an existing evaluator root read-only; never create one."""
        if checkout is None:
            return cls(None)
        checkout = Path(checkout)
        marker = checkout / '.seed-evaluation' / '.ownership'
        if not marker.is_file():
            return cls(None)
        try:
            root = EvaluationRoot.create(checkout)
            return cls(EvaluationReader(root))
        except Exception:
            return cls(None)

    @property
    def available(self) -> bool:
        return self._reader is not None

    def _require(self) -> EvaluationReader:
        if self._reader is None:
            raise ServiceError(
                'evaluation_unavailable',
                'Evaluation unavailable: no artifact root configured.',
                503)
        return self._reader

    def _guarded(self, call):
        try:
            return call(self._require())
        except ReaderError as error:
            if error.reason in ('RECEIPT_UNAVAILABLE',
                                'ARTIFACT_NOT_PUBLISHED'):
                raise ServiceError('not_found',
                                   'Evaluation artifact not found.', 404)
            raise ServiceError('artifact_error',
                               'Stored evaluation evidence is unavailable '
                               'or invalid.', 409)
        except ContractError:
            raise ServiceError('artifact_error',
                               'Stored evaluation evidence is unavailable '
                               'or invalid.', 409)

    @staticmethod
    def _body(event) -> dict:
        return json.loads(event.body)

    def runs(self, cursor=None, limit=20) -> dict:
        def call(reader):
            page = reader.runs(cursor, limit)
            return {'available': True,
                    'items': [self._body(event) for event in page.events],
                    'next_cursor': page.cursor}
        return self._guarded(call)

    def detail(self, run_id: str) -> dict:
        def call(reader):
            detail = reader.detail(run_id)
            body = json.loads(detail.summary.body)
            body['receipt_digest'] = detail.receipt.digest
            body['receipt_files'] = [entry.identity
                                     for entry in detail.receipt.payloads]
            return body
        return self._guarded(call)

    def measurements(self, run_id: str, cursor=None, limit=20) -> dict:
        def call(reader):
            page = reader.measurements(run_id, cursor, limit)
            return {'available': True,
                    'items': [self._body(event) for event in page.events],
                    'next_cursor': page.cursor}
        return self._guarded(call)

    def events(self, run_id: str, cursor=None, limit=20) -> dict:
        def call(reader):
            page = reader.events(run_id, cursor, limit)
            return {'available': True,
                    'items': [{'key': list(event.key),
                               'body': self._body(event)}
                              for event in page.events],
                    'next_cursor': page.cursor}
        return self._guarded(call)

    def event(self, run_id: str, key: tuple) -> dict:
        def call(reader):
            event = reader.event(run_id, key)
            return {'key': list(event.key), 'body': self._body(event)}
        return self._guarded(call)

    def curve(self, run_id: str, metric: str, series: str) -> dict:
        def call(reader):
            points = reader.curve(run_id, metric, series)
            return {'metric': metric, 'series': series,
                    'points': [list(point) for point in points]}
        return self._guarded(call)

    def _stored_file(self, reader, run_id: str, name: str) -> dict:
        """Read one receipt-verified stored file through bounded chunks."""
        detail = reader.detail(run_id)
        lengths = {entry.identity: entry.byte_length
                   for entry in detail.receipt.payloads}
        if name not in lengths:
            raise ServiceError('not_found',
                               'Stored evaluation file not found.', 404)
        pieces = ceil(lengths[name] / _CHUNK)
        data = b''.join(reader.chunk(run_id, name, index)
                        for index in range(pieces))
        return strict_json(data)

    def compare(self, left_id: str, right_id: str,
                metric: str | None) -> dict:
        """Stored-evidence comparison only; no verdict is invented.

        Compatibility dimensions are read from the two receipt-verified
        manifests. Descriptive stored values for one registered metric
        may be shown side by side; the service never classifies a run
        as better, worse or equivalent.
        """
        def call(reader):
            left = self._stored_file(reader, left_id, 'manifest.json')
            right = self._stored_file(reader, right_id, 'manifest.json')
            dimensions = {}
            for name in ('experiment', 'plan_digest', 'science_digest'):
                dimensions[name] = {
                    'left': left.get(name), 'right': right.get(name),
                    'match': left.get(name) == right.get(name)}
            compatible = all(entry['match']
                             for entry in dimensions.values())
            result = {'left': left_id, 'right': right_id,
                      'compatible': compatible,
                      'dimensions': dimensions, 'metric': None}
            if metric:
                values = {}
                for label, run_id in (('left', left_id),
                                      ('right', right_id)):
                    stored = self._stored_file(reader, run_id,
                                               'metrics.json')
                    row = next((entry for entry in stored['produced']
                                if entry['metric'] == metric), None)
                    values[label] = row
                result['metric'] = {'id': metric, **values}
            return result
        return self._guarded(call)

    def chunk(self, run_id: str, file_id: str, index: int) -> bytes:
        return self._guarded(
            lambda reader: reader.chunk(run_id, file_id, index))
