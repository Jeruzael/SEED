"""Evaluator baselines; policy settings are admitted only before measurement."""
import json
from .contracts import ContractError


def configure_policy(owned, role):
    from .state import OwnedState, _worker_only
    _worker_only()
    if type(owned) is not OwnedState or owned._closed or role not in ('seed', 'random-eligible'):
        raise ContractError()
    db = owned.memory.db
    if db.in_transaction or db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]:
        raise ContractError()
    settings = json.loads(db.execute('SELECT data_json FROM settings WHERE singleton=1').fetchone()[0])
    settings.update(epsilon=.15 if role == 'seed' else 1., alpha=.18)
    from seed.config import validate_settings
    settings = validate_settings(settings)
    raw = json.dumps(settings, sort_keys=True, separators=(',', ':')).encode()
    with db:
        db.execute('UPDATE settings SET data_json=? WHERE singleton=1', (raw.decode(),))
    return raw
