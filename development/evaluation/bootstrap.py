"""Adapters are installed only in a fresh, named disposable spawn worker."""
from dataclasses import dataclass
import multiprocessing
import math
import os
import random
import sys
import time
import uuid
from .contracts import ContractError, WorkerLaunch, strict_json
from .determinism import Clock, UUIDStream, _seed
from .paths import LearnerCapability, worker_environment
from .specs import digest, integer


def _forbidden(*args, **kwargs):
    raise RuntimeError('LIVE_FALLBACK_FORBIDDEN')


class BlockedBody:
    def __init__(self, home):
        self.home = home
    perceive = _forbidden


class _UUIDRole:
    def __init__(self, stream, role):
        self.stream, self.role = stream, role
    def uuid4(self):
        return uuid.UUID(hex=self.stream.next_hex(self.role))


@dataclass
class CaptureSession:
    clock: Clock
    uuids: UUIDStream
    learner_rng: random.Random
    legacy_rng: random.Random


def validate_launch(launch):
    if type(launch) is not WorkerLaunch or type(launch.learner) is not LearnerCapability:
        raise ContractError()
    launch.learner.validate()
    from .db_adapter import RunBudget
    if RunBudget(launch.learner.home.parent).stopped:
        raise ContractError()
    if launch.launch_mode=='FRESH':
        if launch.fixture is not None or (launch.learner.home/'memory.sqlite3').exists():
            raise ContractError()
    elif launch.launch_mode=='COMPLETED_OWNED_FIXTURE':
        from .state import CompletedFixture
        if type(launch.fixture) is not CompletedFixture or launch.fixture.learner!=launch.learner:
            raise ContractError()
        launch.fixture.validate()
    else:
        raise ContractError()
    digest(launch.uuid_identity)
    integer(launch.rng_seed,0,2**256-1)
    integer(launch.training_count,0,512)
    if launch.protocol not in ('PREQUENTIAL','FROZEN_SELECTION_ASSAY'):
        raise ContractError()
    if launch.read_time is not None and (launch.protocol != 'FROZEN_SELECTION_ASSAY'
            or type(launch.read_time) not in (int,float) or not math.isfinite(launch.read_time) or launch.read_time<0):
        raise ContractError()
    settings = strict_json(launch.settings)
    if type(settings) is not dict or settings.keys() - {'epsilon','alpha','observe_interval','reflect_interval','rest_interval','memory_budget','prediction_error_curiosity','advanced_concept_inference'}:
        raise ContractError()
    return settings


def install_worker_adapters(launch):
    if multiprocessing.current_process().name != 'seed-evaluation-worker' or any(n == 'seed' or n.startswith('seed.') for n in sys.modules):
        raise ContractError()
    validate_launch(launch)
    # No installed home, credentials or host socket configuration survive.
    os.environ.clear()
    os.environ.update(worker_environment())
    session = CaptureSession(Clock(training_count=launch.training_count), UUIDStream(launch.uuid_identity),
                             random.Random(launch.rng_seed), random.Random(_seed('SEED_B10_LEGACY_RNG_V1',[launch.rng_seed])))
    # Before producer imports: B7 binds its default clock at import time.
    time.time, time.monotonic = session.clock.wall, session.clock.monotonic
    time.sleep = _forbidden
    uuid.uuid4 = _UUIDRole(session.uuids,'producer').uuid4
    random.random, random.choice = session.legacy_rng.random, session.legacy_rng.choice
    import socket
    import subprocess
    socket.create_connection = _forbidden
    socket.socket = _forbidden
    subprocess.Popen = _forbidden
    import seed.body as body
    body.Body = _forbidden
    import seed.organism as organism
    import seed.decision as decision
    organism.Body = BlockedBody
    organism.uuid = _UUIDRole(session.uuids,'session')
    decision.uuid = _UUIDRole(session.uuids,'decision')
    return session
