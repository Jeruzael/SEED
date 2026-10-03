"""Parent-owned minimal durability gate, isolated from learner storage."""
import hashlib
import os
import re
import threading
import time
from .channel import wire_bytes
from .contracts import ContractError, PreUpdateEvidence, CheckpointFrame, decode_message, strict_json
from .paths import _directory, _mkdir, _open_file, _checked, _identity
from .point_scores import point_scores

REAL_CLOCK = time.monotonic


class CheckpointError(ContractError):
    def __init__(self, status='FAILED', reason='INVALID_CONTRACT'):
        super().__init__()
        self.status, self.reason = status, reason


def bounded_bytes(raw, limit):
    if type(raw) is not bytes or len(raw) > limit:
        raise ContractError()
    return raw


def _hash(domain, value):
    return hashlib.sha256(domain.encode('ascii') + b'\0' + wire_bytes(value)).hexdigest()


class ScoreJournal:
    @classmethod
    def create(cls, root, run_id):
        if type(run_id) is not str or not re.fullmatch('[0-9a-f]{32}', run_id):
            raise ContractError()
        root.admit_control(0)
        fd = root._validate()
        os.close(fd)
        evaluation = _directory(root.path / 'evaluation')
        partials = run = stream = None
        try:
            partials = _mkdir(evaluation, 'partials')
            run = _mkdir(partials, run_id)
            stream = _open_file(run, 'preupdate.ndjson', 'create')
            os.fsync(stream)
            for directory in (run, partials, evaluation):
                os.fsync(directory)
            obj = cls()
            obj.root, obj.run_id = root, run_id
            obj.path = root.path / 'evaluation' / 'partials' / run_id / 'preupdate.ndjson'
            obj._directory = run
            obj._directory_inode = _identity(os.fstat(run))
            run = None
            obj._file = os.fdopen(stream, 'wb')
            stream = None
            obj._inode = _identity(os.fstat(obj._file.fileno()))
            obj._clock = REAL_CLOCK
            obj._seen, obj._last = set(), {}
            obj._lock = threading.Lock()
            obj.failed = False
            return obj
        finally:
            if stream is not None: os.close(stream)
            if run is not None: os.close(run)
            if partials is not None: os.close(partials)
            os.close(evaluation)

    def frame(self, evidence):
        if type(evidence) is not PreUpdateEvidence:
            raise ContractError()
        value = decode_message(evidence.body, 'checkpoint')
        if value['phase'] not in ('training', 'measured') or value['transition_ordinal'] > 1024:
            raise ContractError()
        from seed.decision_record import prediction_digest
        header = dict(checkpoint_schema='b10_preupdate_checkpoint_v1', scoring_event_version=1,
            run_id=self.run_id, protocol='prequential', phase=value['phase'], subcase=value['subcase'],
            transition_ordinal=value['transition_ordinal'], selected_action=value['selected_action'],
            history_cutoff_id=value['history_cutoff_id'] or None,
            prediction_sha256=prediction_digest(value['prediction']),
            outcome_sha256=_hash('SEED_B10_OUTCOME_V1', value['state_after']),
            evidence_sha256=_hash('SEED_B10_PREUPDATE_EVIDENCE_V1', value),
            point_scores=point_scores(evidence), checkpoint_status='CHECKPOINTED',
            ordering_marker='PREUPDATE_SCORED_BEFORE_CURRENT_LEARNING')
        return CheckpointFrame(bounded_bytes(wire_bytes(header), 4096), PreUpdateEvidence(wire_bytes(value)))

    def _append(self, frame, started):
        if type(frame) is not CheckpointFrame:
            raise ContractError()
        expected = self.frame(frame.evidence)
        bounded_bytes(frame.header, 4096)
        header = strict_json(frame.header, max_bytes=4096)
        if wire_bytes(header) != expected.header:
            raise ContractError()
        evidence = decode_message(frame.evidence.body, 'checkpoint')
        for name in ('state_before', 'prediction', 'state_after'):
            bounded_bytes(wire_bytes(evidence[name]), 16384)
        key = (header['phase'], header['subcase'], header['transition_ordinal'])
        if key in self._seen or key[2] != self._last.get(key[:2], 0) + 1:
            raise ContractError()
        raw = bounded_bytes(wire_bytes(dict(header=header, evidence=evidence)) + b'\n', 65536)
        self.root.admit_control(len(raw))
        self._validate_storage()
        if os.fstat(self._file.fileno()).st_size + len(raw) > 64*1024**2:
            raise ContractError()
        if self._clock() - started > 10:
            raise CheckpointError('INCOMPLETE', 'ACK_DEADLINE')
        self._seen.add(key)
        if self._file.write(raw) != len(raw):
            raise OSError('partial write')
        self._file.flush()
        os.fsync(self._file.fileno())
        self._validate_storage()
        if self._clock() - started > 10:
            raise CheckpointError('INCOMPLETE', 'ACK_DEADLINE')
        self._last[key[:2]] = key[2]

    def _validate_storage(self):
        os.close(self.root._validate())
        # An open directory descriptor can outlive a rename/replacement. Bind
        # the declared path to the original run directory before AND after IO.
        directory=_directory(self.path.parent)
        try:
            if _identity(os.fstat(directory)) != self._directory_inode:
                raise ContractError()
            st=os.fstat(self._file.fileno())
            _checked(st)
            current=os.stat('preupdate.ndjson',dir_fd=directory,follow_symlinks=False)
            _checked(current)
            if _identity(st)!=self._inode or _identity(current)!=self._inode:
                raise ContractError()
        finally:os.close(directory)

    def _durable(self, build):
        if not self._lock.acquire(blocking=False):
            self.failed = True
            raise CheckpointError()
        try:
            if self.failed:
                raise CheckpointError()
            started = self._clock()
            self._append(build(), started)
        except CheckpointError:
            self.failed = True
            raise
        except OSError:
            self.failed = True
            raise CheckpointError('INCOMPLETE', 'STORAGE_INTERRUPTED') from None
        except (ValueError, TypeError, OverflowError, KeyError):
            self.failed = True
            raise CheckpointError() from None
        finally:
            self._lock.release()

    def append(self, frame):
        self._durable(lambda: frame)

    def ack(self, evidence):
        self._durable(lambda: self.frame(evidence))
        return 'SCORE_ACK'

    def close(self):
        if self._directory is not None:
            try: self._file.close()
            finally:
                os.close(self._directory)
                self._directory = None
