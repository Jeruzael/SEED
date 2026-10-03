"""Named streams and stage clocks; no host or producer side effects."""
from dataclasses import dataclass
import hashlib
import random
from .canonical import canonical_bytes
from .contracts import ContractError, fields, validate_json
from .specs import digest, integer, identifier


def _seed(domain, value):
    return int.from_bytes(hashlib.sha256(domain.encode('ascii') + b'\0' + canonical_bytes(value)).digest(), 'big')


class Streams:
    @classmethod
    def for_identity(cls, identity):
        validate_json(identity)
        fields(identity, ('experiment_id','experiment_version','family','seed','protocol','variant','role'))
        identifier(identity['experiment_id'])
        integer(identity['experiment_version'])
        integer(identity['seed'],0,2**63-1)
        if identity['family'] not in ('A','B','C','D') or identity['protocol'] not in ('PREQUENTIAL','FROZEN_SELECTION_ASSAY') or identity['variant'] not in ('seed','random-eligible','fresh','contradictory','stale','unavailable') or identity['role'] not in ('learner','baseline','legacy'):
            raise ContractError()
        result = cls()
        result._identity = dict(identity)
        key = [identity[k] for k in ('experiment_id','experiment_version','seed','protocol','variant','role')]
        result.learner = random.Random(_seed('SEED_B10_LEARNER_RNG_V1',key))
        result.baseline = random.Random(_seed('SEED_B10_BASELINE_RNG_V1',key))
        result.legacy = random.Random(_seed('SEED_B10_LEGACY_RNG_V1',key))
        return result

    def scenario(self, phase, event_index, channel):
        if phase not in ('training','measured','probe') or channel not in ('load','battery','disk','network','context'):
            raise ContractError()
        integer(event_index,0,2048)
        i = self._identity
        key = [i['experiment_id'],i['experiment_version'],i['family'],i['seed'],phase,event_index,channel]
        raw = hashlib.sha256(b'SEED_B10_SCENARIO_RNG_V1\0'+canonical_bytes(key)).digest()
        return (int.from_bytes(raw[:7],'big') >> 3)/2**53


class Clock:
    def __init__(self, *, training_count=0):
        integer(training_count,0,512)
        self.training_count, self._offset, self._retry, self._stale = training_count, 0, 0, 0
    def stage(self, phase, ordinal, stage):
        if phase not in ('training','measured','probe'):
            raise ContractError()
        integer(ordinal,0,2048)
        integer(stage,0,4)
        value = 10*ordinal + stage + (10*self.training_count if phase != 'training' else 0) + self._retry + self._stale
        if value < self._offset:
            raise ContractError()
        self._offset = value
    def wall(self):
        return float(1800000000 + self._offset)
    def monotonic(self):
        return float(self._offset)
    def retry(self, interval):
        integer(interval,1,3600)
        self._retry += interval
        self._offset += interval
    def stale(self):
        self._stale += 301
        self._offset += 301


class UUIDStream:
    def __init__(self, identity):
        digest(identity)
        self.identity, self.counters = identity, {}
    def next_hex(self, role):
        if role not in ('session','decision','producer','fixture'):
            raise ContractError()
        count = self.counters.get(role,0)
        self.counters[role] = count+1
        return hashlib.sha256(b'SEED_B10_UUID_V1\0'+canonical_bytes([self.identity,role,count])).hexdigest()[:32]
