"""Fixed data identifiers, never plugins or import targets."""
from types import MappingProxyType

ACTIONS = ('observe', 'reflect', 'consolidate', 'rest')
PROTOCOLS = ('FROZEN_SELECTION_ASSAY', 'PREQUENTIAL')
OPERATIONS = ('observation', 'action_catalog', 'apply', 'checkpoint', 'acknowledgment')
SCENARIOS = MappingProxyType({'A': 'stationary-action-v2', 'B': 'rest-shift-v2',
                             'C': 'evidence-v1', 'D': 'constrained-v1'})
WINDOWS = MappingProxyType({'A': ((1, 40), (361, 400)),
                           'B': ((281, 320), (321, 360), (761, 800))})
METRICS = ('prediction.numeric-mae', 'prediction.numeric-normalized-mae', 'prediction.boolean-accuracy',
           'prediction.boolean-brier', 'prediction.coverage', 'prediction.support-counts',
           'prediction.window-change', 'prediction.adaptation-delay', 'world.first-belief',
           'world.evidence-count', 'world.contradictions', 'world.revision-latency', 'world.stability',
           'world.insufficient-evidence', 'curiosity.components', 'curiosity.bounds', 'curiosity.unavailable',
           'semantic.promotion-latency', 'semantic.revisions', 'semantic.status-transitions',
           'semantic.source-consistency', 'semantic.provenance', 'self.factual-fidelity',
           'self.source-traceability', 'self.freshness', 'self.unsupported-claims', 'decision.constraints',
           'decision.eligibility', 'decision.provenance', 'decision.prediction-link',
           'decision.skipped-fallback', 'decision.q-compatibility', 'decision.task-utility')
REGISTRIES = MappingProxyType({
    'operation': MappingProxyType({name: 1 for name in OPERATIONS}),
    'action': MappingProxyType({name: 1 for name in ACTIONS}),
    'protocol': MappingProxyType({name: 1 for name in PROTOCOLS}),
    'metric': MappingProxyType({name: 2 if name == 'prediction.adaptation-delay' else 1 for name in METRICS}),
    'baseline': MappingProxyType({'persistence': 1, 'global-history': 1}),
    'family': MappingProxyType({'A': 2, 'B': 2, 'C': 1, 'D': 1}),
})


def lookup(identity: str, version: int, *, kind: str) -> str:
    if type(identity) is not str or type(version) is not int or version < 1:
        raise ValueError('INVALID_CONTRACT')
    if kind not in REGISTRIES or REGISTRIES[kind].get(identity) != version:
        raise ValueError('INVALID_CONTRACT')
    return identity
