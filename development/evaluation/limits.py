"""Preallocation reservation accounting; never prunes retained results."""
from dataclasses import dataclass
from .contracts import ContractError, RunRequest
from .specs import CAPS, identifier, integer


@dataclass(frozen=True)
class Usage:
    bytes: int
    runs: int
    run_bytes: tuple[tuple[str,int], ...] = ()
    run_ids: tuple[str, ...] = ()


class Reservation:
    def __init__(self, budget, request):
        self._registry, self.request, self._released = budget._reservations, request, False
        self._active=set()
    def activate(self, run):
        identifier(run)
        if self._released or run in self._active or len(self._active)>=self.request.count or any(run in r._active for r in self._registry.values()):
            raise ContractError()
        self._active.add(run)

    def release(self):
        if not self._released:
            self._registry.pop(self.request.identity)
            self._released = True


class Budget:
    def __init__(self, *, retained_bytes, retained_runs, usage=None):
        integer(retained_bytes, 0, CAPS['root_bytes'])
        integer(retained_runs, 0, CAPS['retained_runs'])
        self.retained_bytes, self.retained_runs = retained_bytes, retained_runs
        self._reservations = {}
        self._usage=usage
        self._actual=Usage(retained_bytes,retained_runs)

    def reconcile(self, usage):
        integer(usage.bytes,0,CAPS['root_bytes'])
        integer(usage.runs,0,CAPS['retained_runs'])
        self._actual=usage
        self.retained_bytes,self.retained_runs=usage.bytes,usage.runs

    def require_capacity(self, *, bytes=0, runs=0):
        if self._usage is not None:
            self.reconcile(self._usage())
        actual=dict(self._actual.run_bytes)
        ids=set(self._actual.run_ids)
        reserved_bytes=reserved_runs=0
        for reservation in self._reservations.values():
            request=reservation.request
            represented=reservation._active & ids
            for identity in represented:
                if actual.get(identity,0)>request.reservation_bytes:
                    raise ContractError()
            reserved_bytes+=request.count*request.reservation_bytes-sum(actual.get(identity,0) for identity in represented)
            reserved_runs+=request.count-len(represented)
        if self.retained_bytes+reserved_bytes+bytes>CAPS['root_bytes'] or self.retained_runs+reserved_runs+runs>CAPS['retained_runs']:
            raise ContractError()

    def reserve(self, request: RunRequest):
        identifier(request.identity)
        integer(request.count, 1, 32)
        integer(request.reservation_bytes, 1, CAPS['reservation_bytes'])
        self.require_capacity(bytes=request.count*request.reservation_bytes,runs=request.count)
        if request.identity in self._reservations or request.identity in self._actual.run_ids:
            raise ContractError()
        reservation=Reservation(self,request)
        self._reservations[request.identity]=reservation
        return reservation
