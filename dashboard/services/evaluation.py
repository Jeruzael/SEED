"""Optional read-only Evaluation service (B10 I26).

Delegates exclusively to the dedicated bounded EvaluationReader over a
separately enabled evaluator-owned artifact root. The service never
creates the root, never falls back to the organism home, and holds no
execution capability: when the root is absent or the reader cannot be
constructed, every method reports a clear unavailable state and no
evaluator machinery is initialized.
"""
import json
from contextlib import contextmanager
from pathlib import Path

from development.evaluation import replay as _replay
from development.evaluation.contracts import ContractError, strict_json
from development.evaluation.paths import EvaluationRoot
from development.evaluation.reader import (EvaluationReader, ReaderError)

from .read_store import ServiceError


class _DeadlineGuard:
    """Final deadline enforcement for one Evaluation HTTP request.

    The reader session's deadline is the single authoritative time
    boundary for the request; enforce() is called after the response
    has been fully constructed and before it is returned, so CPU-only
    processing and serialization after the last physical read cannot
    return success past the deadline.
    """

    __slots__ = ('_session',)

    def __init__(self, session):
        self._session = session

    def enforce(self):
        if self._session is not None \
                and self._session.deadline_passed():
            raise ServiceError(
                'deadline_exceeded',
                'Evaluation request exceeded its approved time limit.',
                429)


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

    @contextmanager
    def request_context(self):
        """Scope one Evaluation HTTP request: the reader session (one
        budget, one deadline) spans request validation, service
        processing and final response construction. When the service
        is used without the API layer, _guarded opens the same
        session per call as before."""
        if self._reader is None:
            yield _DeadlineGuard(None)
            return
        with self._reader.request_session() as session:
            yield _DeadlineGuard(session)

    def _guarded(self, call):
        reader = self._require()
        try:
            # One request-scoped reader session per service call (one
            # HTTP request): every nested reader operation shares the
            # same 1 MiB read budget and the same 2-second deadline,
            # and concurrent requests own independent sessions.
            with reader.request_session() as session:
                try:
                    result = call(reader)
                except _replay.BudgetError:
                    # Resource exhaustion is never mislabeled as
                    # artifact corruption.
                    if session.deadline_passed():
                        raise ServiceError(
                            'deadline_exceeded',
                            'Evaluation request exceeded its approved '
                            'time limit.', 429)
                    raise ServiceError(
                        'resource_limit',
                        'Evaluation request exceeded its approved '
                        'resource limits.', 429)
                # Processing after the final physical read (stored
                # JSON decoding, response-dict construction) is inside
                # the same deadline: it cannot return success late.
                if session.deadline_passed():
                    raise ServiceError(
                        'deadline_exceeded',
                        'Evaluation request exceeded its approved '
                        'time limit.', 429)
                return result
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
            # Scientific finding details belong in the detail response
            # (plan I26 interfaces); read them from the receipt-verified
            # stored metrics file, never recomputed here.
            metrics = self._stored_file(reader, run_id, 'metrics.json',
                                        detail.receipt)
            body['findings'] = metrics['findings']
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
            curve = reader.curve(run_id, metric, series)
            return {'metric': curve.metric, 'series': series,
                    'points': [list(point) for point in curve.points]}
        return self._guarded(call)

    def _stored_file(self, reader, run_id: str, name: str,
                     receipt=None) -> dict:
        """Read one receipt-verified stored file within this request's
        session: chunk-verified by the reader, read at most once, and
        parsed against the file's own verified length (the artifact
        contract bounds these files well above the generic 64 KiB
        message cap that previously made large valid files fail)."""
        if receipt is None:
            receipt = reader.receipt(run_id)
        lengths = {entry.identity: entry.byte_length
                   for entry in receipt.payloads}
        if name not in lengths:
            raise ServiceError('not_found',
                               'Stored evaluation file not found.', 404)
        data = reader.verified_file(run_id, name)
        return strict_json(data, max_bytes=len(data))

    def _stored_file_optional(self, reader, run_id: str, name: str,
                              receipt) -> dict | None:
        """Like _stored_file, but an artifact absent from the run's
        verified inventory yields None instead of an error: absence of
        evidence is a compatibility fact, not a request failure. No
        bytes are read for an absent file."""
        names = {entry.identity for entry in receipt.payloads}
        if name not in names:
            return None
        data = reader.verified_file(run_id, name)
        return strict_json(data, max_bytes=len(data))

    @staticmethod
    def _dimension(left, right) -> dict:
        """One eligibility dimension. Missing evidence is an explicit
        not-established state, never a match by None == None."""
        if left is None or right is None:
            return {'left': left, 'right': right, 'match': None,
                    'status': 'not_established'}
        match = left == right
        return {'left': left, 'right': right, 'match': match,
                'status': 'match' if match else 'differs'}

    def _plan_state(self, run_id: str, manifest: dict,
                    plan_file: dict | None, metrics: dict):
        """Establish one run's frozen-plan binding from its own
        verified files. Returns (established, plan_body). A stored
        value that contradicts the manifest binding is invalid
        evidence (409), not a compatibility outcome; a missing link
        leaves the binding not established."""
        digest = manifest.get('plan_digest')
        if digest is None or plan_file is None:
            return False, None
        stated = plan_file.get('digest')
        receipt = plan_file.get('receipt') or {}
        if stated is not None and stated != digest \
                or receipt.get('digest') is not None \
                and receipt.get('digest') != digest:
            raise ServiceError('artifact_error',
                               'Stored evaluation evidence is '
                               'unavailable or invalid.', 409)
        metrics_digest = metrics.get('plan_digest')
        if metrics_digest is not None and metrics_digest != digest:
            raise ServiceError('artifact_error',
                               'Stored evaluation evidence is '
                               'unavailable or invalid.', 409)
        if stated is None or receipt.get('digest') is None \
                or metrics_digest is None:
            return False, None
        return True, plan_file.get('plan')

    @staticmethod
    def _metric_block(metric: str, sides: dict) -> dict:
        """Pair one registered measurement across two runs by its
        full stored identity (member:metric:population:window).

        A bare metric ID is never silently resolved to the first
        matching row: zero rows is unavailable, several rows is
        ambiguous, differing identities are unpaired, and a row whose
        version is not the plan-registered version is not presented
        as the run's registered measurement."""
        block = {'id': metric, 'state': 'unavailable', 'identity': None,
                 'left': None, 'right': None}
        rows = {label: [row for row in side['metrics'].get(
            'produced', []) if row.get('metric') == metric]
                for label, side in sides.items()}
        if not rows['left'] or not rows['right']:
            block['missing'] = [label for label in ('left', 'right')
                                if not rows[label]]
            if len(rows['left']) > 1 or len(rows['right']) > 1:
                block['candidates'] = {
                    label: sorted({row.get('identity')
                                   for row in rows[label]})
                    for label in ('left', 'right')}
            return block
        if len(rows['left']) > 1 or len(rows['right']) > 1:
            block['state'] = 'ambiguous'
            block['candidates'] = {
                label: sorted({row.get('identity')
                               for row in rows[label]})
                for label in ('left', 'right')}
            return block
        left_row, right_row = rows['left'][0], rows['right'][0]
        left_id, right_id = (left_row.get('identity'),
                             right_row.get('identity'))
        if left_id is None or right_id is None:
            block['state'] = 'not_established'
            return block
        if left_id != right_id:
            block['state'] = 'unpaired'
            block['identities'] = {'left': left_id, 'right': right_id}
            return block
        for label, row in (('left', left_row), ('right', right_row)):
            plan = sides[label]['plan']
            registered = None
            if plan is not None:
                registered = next(
                    (entry.get('version')
                     for entry in plan.get('metrics', [])
                     if entry.get('id') == metric), None)
            if registered is None or row.get('version') != registered:
                block['state'] = 'version_mismatch'
                return block
        block.update(state='paired', identity=left_id,
                     left=left_row, right=right_row)
        return block

    def compare(self, left_id: str, right_id: str,
                metric: str | None) -> dict:
        """Stored-evidence comparison only; no verdict is invented.

        Eligibility (MAJOR-2) is decided from experimental identity,
        the receipt-bound frozen plan, run protocol and
        source/lock/profile/adapter provenance -- never from
        scientific outcomes. The science digest is reported
        separately as result identity/provenance. Eligibility is
        'compatible', 'incompatible' (a required dimension
        demonstrably differs) or 'not_established' (stored evidence
        is insufficient); the boolean 'compatible' is true only for
        the first. All evidence is read through the request session
        before any decision, so near-limit comparisons fail with the
        bounded resource error instead of skipping checks.
        """
        def call(reader):
            sides = {}
            for label, run_id in (('left', left_id),
                                  ('right', right_id)):
                receipt = reader.receipt(run_id)
                manifest = self._stored_file(reader, run_id,
                                             'manifest.json', receipt)
                plan_file = self._stored_file_optional(
                    reader, run_id, 'analysis-plan.json', receipt)
                metrics = self._stored_file(reader, run_id,
                                            'metrics.json', receipt)
                established, plan = self._plan_state(
                    run_id, manifest, plan_file, metrics)
                sides[label] = {'manifest': manifest, 'plan': plan,
                                'established': established,
                                'metrics': metrics}
            left_m = sides['left']['manifest']
            right_m = sides['right']['manifest']

            def experiment_value(manifest):
                experiment = manifest.get('experiment') or {}
                if experiment.get('id') is None \
                        or experiment.get('version') is None:
                    return None
                return {'id': experiment['id'],
                        'version': experiment['version']}

            def field(manifest, name):
                return (manifest.get('experiment') or {}).get(name)

            dimensions = {
                'experiment': self._dimension(
                    experiment_value(left_m), experiment_value(right_m)),
                'plan_digest': self._dimension(
                    left_m.get('plan_digest')
                    if sides['left']['established'] else None,
                    right_m.get('plan_digest')
                    if sides['right']['established'] else None),
                'protocol': self._dimension(field(left_m, 'protocol'),
                                            field(right_m, 'protocol')),
                'source_commit': self._dimension(
                    field(left_m, 'source_commit'),
                    field(right_m, 'source_commit')),
                'lock_digest': self._dimension(
                    field(left_m, 'lock_digest'),
                    field(right_m, 'lock_digest')),
                'profile_digest': self._dimension(
                    field(left_m, 'profile_digest'),
                    field(right_m, 'profile_digest')),
                'adapter_version': self._dimension(
                    field(left_m, 'adapter_version'),
                    field(right_m, 'adapter_version')),
            }
            statuses = [entry['status']
                        for entry in dimensions.values()]
            if 'differs' in statuses:
                eligibility = 'incompatible'
            elif 'not_established' in statuses:
                eligibility = 'not_established'
            else:
                eligibility = 'compatible'
            reasons = [
                f'{name}: differs' if entry['status'] == 'differs'
                else f'{name}: not established from stored evidence'
                for name, entry in dimensions.items()
                if entry['status'] != 'match']
            plan_fields = []
            left_plan, right_plan = (sides['left']['plan'],
                                     sides['right']['plan'])
            if left_plan is not None and right_plan is not None \
                    and dimensions['plan_digest']['status'] == 'differs':
                plan_fields = sorted(
                    name for name in set(left_plan) | set(right_plan)
                    if left_plan.get(name) != right_plan.get(name))
            left_digest = left_m.get('science_digest')
            right_digest = right_m.get('science_digest')
            result = {
                'left': left_id, 'right': right_id,
                'compatible': eligibility == 'compatible',
                'eligibility': eligibility, 'reasons': reasons,
                'dimensions': dimensions, 'plan_fields': plan_fields,
                'scientific_identity': {'science_digest': {
                    'left': left_digest, 'right': right_digest,
                    'equal': (left_digest == right_digest)
                    if left_digest is not None
                    and right_digest is not None else None}},
                'findings': {
                    'left': sides['left']['metrics'].get('findings'),
                    'right': sides['right']['metrics'].get('findings')},
                'metric': None}
            if metric:
                result['metric'] = self._metric_block(metric, sides)
            return result
        return self._guarded(call)

    def chunk(self, run_id: str, file_id: str, index: int) -> bytes:
        return self._guarded(
            lambda reader: reader.chunk(run_id, file_id, index))
