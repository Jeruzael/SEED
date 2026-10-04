"""Closed foundation data contracts. No producer imports or execution."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
from typing import Literal, Protocol, TypeAlias
from .registry import ACTIONS, OPERATIONS, PROTOCOLS

Json: TypeAlias = None | bool | int | float | str | list['Json'] | dict[str, 'Json']
Action: TypeAlias = Literal['observe', 'reflect', 'consolidate', 'rest']
Observation: TypeAlias = dict[str, None | bool | int | float]
EventKey: TypeAlias = tuple[str, str, int, str]
MESSAGE_BYTES = 64 * 1024


class ContractError(ValueError):
    def __init__(self):
        super().__init__('INVALID_CONTRACT')


def validate_json(value: Json, *, max_depth=16, max_entries=4096) -> None:
    entries = 0
    def visit(v, depth):
        nonlocal entries
        if type(v) in (list, dict):
            if depth >= max_depth:
                raise ContractError()
            entries += len(v)
            if entries > max_entries:
                raise ContractError()
            if type(v) is dict:
                for k, item in v.items():
                    if type(k) is not str:
                        raise ContractError()
                    visit(k, depth + 1)
                    visit(item, depth + 1)
            else:
                for item in v:
                    visit(item, depth + 1)
        elif v is None or type(v) is bool:
            return
        elif type(v) is int:
            if not -2**256 <= v < 2**256:
                raise ContractError()
        elif type(v) is float:
            if not math.isfinite(v):
                raise ContractError()
        elif type(v) is str:
            if not v.isascii() or len(v) > 4096:
                raise ContractError()
        else:
            raise ContractError()
    visit(value, 0)


def strict_json(raw: bytes, *, max_bytes=MESSAGE_BYTES) -> Json:
    if type(raw) is not bytes or len(raw) > max_bytes:
        raise ContractError()
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise ContractError()
            result[key] = val
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ContractError()))
        validate_json(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ContractError() from None


def fields(value, required, optional=()) -> None:
    if type(value) is not dict or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ContractError()


def validate_observation(value) -> Observation:
    fields(value, (), ('battery_pct', 'charging', 'load_ratio', 'disk_free_pct', 'network', 'local_hour'))
    for key, val in value.items():
        if key in ('charging', 'network'):
            if val is not None and type(val) is not bool:
                raise ContractError()
        elif key == 'local_hour':
            if type(val) is not int or not 0 <= val <= 23:
                raise ContractError()
        elif key == 'battery_pct' and val is None:
            continue
        elif type(val) not in (int, float) or not math.isfinite(val) or not 0 <= val <= (2 if key == 'load_ratio' else 100):
            raise ContractError()
    return dict(value)


def validate_event_key(value) -> EventKey:
    if type(value) is not list or len(value) != 4:
        raise ContractError()
    phase, subcase, ordinal, stage = value
    if phase not in ('training', 'measured', 'probe') or subcase not in ('default', 'fresh', 'stale', 'unavailable', 'contradictory'):
        raise ContractError()
    if type(ordinal) is not int or not 1 <= ordinal <= 2048 or stage not in ('pre', 'action', 'outcome', 'checkpoint', 'update'):
        raise ContractError()
    return tuple(value)


def decode_message(raw: bytes, operation: str) -> Json:
    if operation not in OPERATIONS:
        raise ContractError()
    value = strict_json(raw)
    if operation == 'observation':
        return validate_observation(value)
    if operation == 'action_catalog':
        fields(value, ('actions',))
        if value['actions'] != list(ACTIONS):
            raise ContractError()
    elif operation == 'apply':
        fields(value, ('action', 'key'))
        if value['action'] not in ACTIONS:
            raise ContractError()
        validate_event_key(value['key'])
    elif operation == 'acknowledgment':
        fields(value, ('token',))
        if value['token'] != 'SCORE_ACK':
            raise ContractError()
    else:
        fields(value, ('phase', 'subcase', 'transition_ordinal', 'history_cutoff_id', 'state_before', 'selected_action', 'prediction', 'state_after'))
        validate_event_key([value['phase'], value['subcase'], value['transition_ordinal'], 'checkpoint'])
        if value['selected_action'] not in ACTIONS or type(value['history_cutoff_id']) is not int or not 0 <= value['history_cutoff_id'] < 2**63:
            raise ContractError()
        validate_observation(value['state_before'])
        validate_observation(value['state_after'])
        if type(value['prediction']) is not dict:
            raise ContractError()
        # Lazy pure producer validator: package import remains inert/pre-adapter.
        from seed.decision_record import validate_prediction
        try:
            validate_prediction(value['prediction'],value['selected_action'])
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
            raise ContractError() from None
        for key in ('state_before', 'prediction', 'state_after'):
            if len(json.dumps(value[key], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) > 16 * 1024:
                raise ContractError()
    return value


class RootCapability(Protocol):
    def open(self, kind: str, identity: str, mode: str) -> int: ...
    def sync(self) -> None: ...


@dataclass(frozen=True)
class ExperimentSpec:
    body: bytes


@dataclass(frozen=True)
class AnalysisPlan:
    body: bytes


@dataclass(frozen=True)
class FrozenPlan:
    plan: AnalysisPlan
    digest: str
    receipt: bytes


@dataclass(frozen=True)
class RunRequest:
    identity: str
    count: int = 1
    reservation_bytes: int = 448 * 1024**2


@dataclass(frozen=True)
class WorkerLaunch:
    learner: RootCapability
    settings: bytes
    rng_seed: int
    uuid_identity: str
    training_count: int = 0
    protocol: str = 'PREQUENTIAL'
    launch_mode: str = 'FRESH'
    fixture: object = None
    read_time: float | None = None


@dataclass(frozen=True)
class PreUpdateEvidence:
    body: bytes


@dataclass(frozen=True)
class CheckpointFrame:
    header: bytes
    evidence: PreUpdateEvidence


@dataclass(frozen=True)
class CompletedEvidence:
    key: EventKey
    body: bytes


@dataclass(frozen=True)
class Attempt:
    key: EventKey
    status: Literal['completed', 'skipped']
    reason: str | None


@dataclass(frozen=True)
class RunResult:
    status: Literal['PLANNED', 'RUNNING', 'COMPLETED', 'INCOMPLETE', 'FAILED', 'INVALID']
    reason: str | None


@dataclass(frozen=True)
class Population:
    identity: str
    members: tuple[str, ...]
    window: str = 'whole'


@dataclass(frozen=True)
class Measurement:
    identity: str
    metric: str
    version: int
    member: str
    state: Literal['MEASURED', 'UNAVAILABLE', 'NOT_EVALUATED'] = 'UNAVAILABLE'
    body: bytes = b'{}'
    role: Literal['PRIMARY', 'EXPLORATORY_DIAGNOSTIC'] = 'PRIMARY'

    @property
    def value(self):
        return strict_json(self.body).get('value')

    @property
    def reason(self):
        return strict_json(self.body).get('reason')


@dataclass(frozen=True)
class QuestionFinding:
    question: str
    status: Literal['POSITIVE', 'MIXED', 'NEGATIVE', 'INCONCLUSIVE', 'NOT_EVALUATED']
    reason: str | None


@dataclass(frozen=True)
class Payload:
    identity: str
    byte_length: int


@dataclass(frozen=True)
class Receipt:
    payloads: tuple[Payload, ...]
    digest: str


@dataclass(frozen=True)
class RunSummary:
    identity: str
    execution: RunResult


@dataclass(frozen=True)
class RunDetail:
    summary: RunSummary
    receipt: Receipt


@dataclass(frozen=True)
class Event:
    key: EventKey
    body: bytes


@dataclass(frozen=True)
class Curve:
    metric: str
    points: tuple[tuple[int, float | None], ...]


@dataclass(frozen=True)
class ReplayPage:
    events: tuple[Event, ...]
    cursor: str | None


@dataclass(frozen=True)
class ReexecutionResult:
    status: Literal['matched', 'divergent', 'incompatible']
    differences: tuple[str, ...]


@dataclass(frozen=True)
class VerificationReport:
    gate: str
    passed: bool
    reasons: tuple[str, ...]
