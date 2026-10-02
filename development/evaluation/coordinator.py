"""Parent-only admission scaffold. Scientific dispatch remains unauthorized."""
import time
from .analysis import require_frozen
from .contracts import ContractError, RunRequest
from .dependency import audit_dependencies
from .limits import Budget


class Coordinator:
    def __init__(self, *, root=None, frozen_plan=None, suite_seconds=1800, clock=time.monotonic):
        if type(suite_seconds) not in (int,float) or not 0<suite_seconds<=1800:
            raise ContractError()
        self.root,self.frozen_plan,self.suite_seconds=root,frozen_plan,suite_seconds
        self._clock,self._started=clock,clock()
        self._budget=None

    def admit(self, request: RunRequest):
        if self.root is None or self.frozen_plan is None or self._clock()-self._started>=self.suite_seconds:
            raise ContractError()
        if audit_dependencies(self.root.path.parent):
            raise ContractError()
        require_frozen(self.frozen_plan.plan,self.root)
        usage=self.root.usage()
        if self._budget is None:
            self._budget=Budget(retained_bytes=usage.bytes,retained_runs=usage.runs)
        self._budget.reserve(request)
        return request

    def dispatch(self, *args, **kwargs):
        # G3–G7 and I09+ are intentionally locked, even with a frozen plan.
        raise RuntimeError('FOUNDATION_ONLY_DISPATCH_DISABLED')
