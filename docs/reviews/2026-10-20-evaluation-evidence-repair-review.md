# Evaluation evidence repair: review and verification

Engineering record dated 2026-10-20. This is not empirical acceptance, owner
closure, a signature, a permit, or approval to merge or deploy.

## Scope and identities

Base commit: `7015a9f80f8640b494c9977252337a67ea4a79ca`.
Fresh reviewer inspected staged tree `7dae775934dc4ac4a557e2f59337bc8ab884614b`.
Author's repaired code and tests are captured in tree
`e113fa16e9fa4e1c53749d8d51c61d34e1ef1865`.
Subsequent documentation changes do not change that tested code.

The change repairs a raw-checkpoint/producer interface mismatch and carries
original selection, candidate and baseline evidence through bounded post-ACK
publication and supported online reexecution. Initial/unlabelled checkpoints
and legacy absent sidecars remain unavailable. Scientific digest projection,
learner code, schemas, formulas, dependencies, CI and empirical dispatch locks
are unchanged.

## Fresh agent review

The reviewer received the base and exact staged tree with the requested scope,
without the implementation conversation. This is a separate agent's code
review, not an external human review or a GitHub approval.

One substantive finding, P2: the post-ACK baseline join validated identity and
history links but accepted malformed forecast fields or a persistence value
changed to the observed outcome. Such evidence could produce a false zero MAE.
The reviewer recommended exact field/type/support checks and binding persistence
to the original pre-action observation. No other concrete regression was
reported.

Author response:

- Added 17 negative cases: 16 failed before the fix; one already-rejected
  source-count case passed.
- Audited persistence against the pure baseline calculation from recorded
  pre-action input, with no learner inference or live-state read.
- Enforced the global forecast schema, finite bounded values, methods,
  provenance order/counts, support/fallback rules and Boolean probabilities.
- Focused affected suites: **60 passed in 25.65 seconds**.

This records the author's repair evidence; it does not attribute a later
approval of the fix to the reviewer.

Reviewer coverage suggestions, deferred rather than represented as proven
defects: actual maximum-size/global-row SQLite boundaries and more truncated
SQLite cases; a 200-row capture at the combined serialized limit; mixed
sidecar presence over a multi-transition fresh replay.

## Verification

Regression evidence includes a real producer snapshot whose literal evidence
count survives assembly/publication/readback, original prior history captured
before selection, no repeated learning after a post-ACK capture failure,
literal baseline MAE, rejected misbound/future evidence, and a genuinely fresh
online reexecution preserving legacy absence.

Final local full-suite verification of tree `e113fa16...`: **1,653 passed,
2 dependency deprecation warnings in 883.57 seconds**, exit 0.
Seven required deterministic scenario modules exited 0 and produced valid JSON
on that tree:
baseline, prediction error, world model, curiosity, semantic, self model and
decision. These are disposable engineering fixtures.

Local runtime: Ubuntu/WSL Python 3.12.3, locked project dependencies, Node
22.21.1. Source is exported with `git -c core.autocrlf=false archive` into
temporary Linux-native storage; `SEED_HOME` is separately temporary.
All 353 archive files were checked against their exact Git blob identities.
`pip check` reports no broken requirements.
The initial Windows-converted archive had 1,634 passes and two saved-byte hash
failures. Its CRLF hashes differ from the original LF references. Export settings
were corrected; supplied evidence, reference hashes and source bytes were not
rewritten. That earlier run does not verify the later review fix.

Commands on the canonical archive:

```text
python -B -m pytest -q -p no:cacheprovider
python -B -m tests.<scenario_name>
```

Local logs are retained in ignored `.review-artifacts/`, including
`review-baseline-red.log`, `review-baseline-green.log`,
`final-native-full.log`, `final-source-manifest.json` and `final-scenarios.json`.
The repository's required
Linux 3.11 / Linux 3.13 / macOS 3.13 exact-PR-head CI remains a separate check.
Hosted verification is recorded separately below. No post-merge success is
asserted.

### Subsequent hosted verification of the engineering commit

[CI run 39398419123](https://github.com/Jeruzael/SEED/actions/runs/39398419123),
PR event, attempt 1, completed successfully for exact engineering commit
`042b90384e200590b076896961e7f450935a5f62`:

- Linux 3.11: 1,652 passed, 1 skipped, 2 warnings.
- Linux 3.13: 1,653 passed, 2 warnings.
- macOS 3.13: 1,653 passed, 2 warnings.

All three jobs succeeded. Deterministic scenarios succeeded on both 3.13 jobs;
the 3.11 scenario step was skipped by workflow policy. Later no-budget design
documentation does not change that source/test code, but its final exact-head
CI remains separately tracked in [PR #43](https://github.com/Jeruzael/SEED/pull/43).
The PR remains unmerged; no post-merge closure is asserted.

## Decisions and limits

Explicit `producer-source:<member-id>` labels bind declared raw snapshots to
members; they do not authenticate snapshot origin or prove terminal timing.
Missing publication histories, self-model sources and preselection Q-source
captures remain unavailable. Global-history arithmetic cannot be independently
recomputed from a sidecar that deliberately retains no raw history pool.

Online replay coverage does not implement full frozen A/C reexecution.
Canonical admission, durable one-use accounting, suite/retention admission,
target-host qualification and personal Stage A signing remain separate gates.
The [readiness worksheet](../evaluation/2026-10-20-admission-readiness.md)
records those gaps.

The infrastructure proposal received a separate read-only consistency review.
It identified missing four-domain administrator separation and durable
one-use-ledger qualification; both were added. It is a proposal for Gio, not a
deployment review or provisioned infrastructure.

Gio subsequently specified no budget and no plan to spend. The proposal now
recommends local engineering on existing resources, with the cloud design
retained only as deferred reference. Separate read-only analyses prepared the
next frozen-reexecution and retention design; they ran no experiments and do
not approve implementation or empirical admission.
