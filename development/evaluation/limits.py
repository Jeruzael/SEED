"""Preallocation reservation accounting; never prunes retained results."""
from dataclasses import dataclass
from .contracts import ContractError, RunRequest
from .specs import CAPS, identifier, integer


@dataclass(frozen=True)
class Usage:
    bytes: int
    runs: int


class Reservation:
    def __init__(self, budget, request):
        self._budget, self.request, self._released = budget, request, False
    def release(self):
        if not self._released:
            self._budget._reservations.pop(self.request.identity)
            self._released = True


class Budget:
    def __init__(self, *, retained_bytes, retained_runs):
        integer(retained_bytes, 0, CAPS['root_bytes'])
        integer(retained_runs, 0, CAPS['retained_runs'])
        self.retained_bytes, self.retained_runs = retained_bytes, retained_runs
        self._reservations = {}

    def reserve(self, request: RunRequest):
        identifier(request.identity)
        integer(request.count, 1, 32)
        integer(request.reservation_bytes, 1, CAPS['reservation_bytes'])
        if request.identity in self._reservations:
            raise ContractError()
        reserved_bytes = sum(r.count*r.reservation_bytes for r in self._reservations.values())
        reserved_runs = sum(r.count for r in self._reservations.values())
        if (self.retained_runs + reserved_runs + request.count > CAPS['retained_runs']
                or self.retained_bytes + reserved_bytes + request.count*request.reservation_bytes > CAPS['root_bytes']):
            raise ContractError()
        self._reservations[request.identity] = request
        return Reservation(self, request)
