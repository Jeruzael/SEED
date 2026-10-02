"""Fixed data identifiers, never plugins or import targets."""
from types import MappingProxyType

ACTIONS = ('observe', 'reflect', 'consolidate', 'rest')
PROTOCOLS = ('FROZEN_SELECTION_ASSAY', 'PREQUENTIAL')
OPERATIONS = ('observation', 'action_catalog', 'apply', 'checkpoint', 'acknowledgment')
REGISTRIES = MappingProxyType({
    'operation': MappingProxyType({name: 1 for name in OPERATIONS}),
    'action': MappingProxyType({name: 1 for name in ACTIONS}),
    'protocol': MappingProxyType({name: 1 for name in PROTOCOLS}),
})


def lookup(identity: str, version: int, *, kind: str) -> str:
    if type(identity) is not str or type(version) is not int or version < 1:
        raise ValueError('INVALID_CONTRACT')
    if kind not in REGISTRIES or REGISTRIES[kind].get(identity) != version:
        raise ValueError('INVALID_CONTRACT')
    return identity
