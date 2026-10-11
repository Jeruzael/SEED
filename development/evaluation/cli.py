"""Trusted local CLI for B10 evaluation artifacts (I25).

Verbs accept registered identifiers and opaque run IDs only -- never
filesystem paths, code, URLs or installer instructions. The root is the
fixed repository-owned ``.seed-evaluation`` directory. ``run``, ``suite``
and ``reexecute`` dispatch stay locked until every I30 engineering gate and
a separate owner empirical-evaluation authorization exist; that lock is not
satisfied by the I14-I30 engineering authorization.
"""
import json
import re
import sys
from pathlib import Path

from .contracts import ContractError
from .integrity import verify_receipt
from .paths import EvaluationRoot

DISPATCH_DISABLED = 'EMPIRICAL_DISPATCH_DISABLED'
_RUN_ID = re.compile(r'[0-9a-f]{32}')
_VERBS = ('validate', 'run', 'suite', 'verify', 'replay', 'reexecute')


def _checkout_root():
    checkout = Path.cwd()
    if not (checkout / '.seed-evaluation').is_dir():
        raise ContractError()
    return EvaluationRoot.create(checkout)


def _emit(value):
    print(json.dumps(value, sort_keys=True))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] not in _VERBS or not _RUN_ID.fullmatch(argv[1]):
        _emit(dict(error='INVALID_INPUT'))
        return 3
    verb, run_id = argv
    if verb in ('run', 'suite', 'reexecute'):
        _emit(dict(error=DISPATCH_DISABLED, verb=verb))
        return 2
    try:
        root = _checkout_root()
    except ContractError:
        _emit(dict(error='EVALUATION_ROOT_UNAVAILABLE'))
        return 3
    if verb == 'verify':
        _emit(dict(run_id=run_id, verified=verify_receipt(root, run_id)))
        return 0
    from .reader import EvaluationReader
    reader = EvaluationReader(root)
    try:
        if verb == 'validate':
            detail = reader.detail(run_id)
            _emit(dict(run_id=run_id, valid=True,
                       status=detail.summary.execution.status))
            return 0
        page = reader.events(run_id)
        _emit(dict(run_id=run_id,
                   events=[list(e.key) for e in page.events]))
        return 0
    except ContractError:
        _emit(dict(error='ARTIFACT_UNAVAILABLE', run_id=run_id))
        return 3
