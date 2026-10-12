# B10 Evaluation Tooling — Usage

This page describes the evaluator-owned B10 tooling as of I30
(engineering release qualification). Everything here is
engineering infrastructure: it builds inventories, verifies
recorded evidence and runs disposable technical fixtures. The
registered empirical evaluation (I31) is a separate, later,
separately authorized activity; nothing on this page dispatches
it.

## Roots and isolation

All evaluation state lives under an evaluator-owned
`EvaluationRoot` (the `.seed-evaluation` directory of a checkout,
created explicitly). Evaluation artifacts are isolated from
learner state: the learner never reads evaluator truth, and the
evaluation root is never the installed SEED home. Disposable
fixtures and tests create roots only in temporary directories.

## Trusted CLI

```text
python -m development.evaluation <verb> <run-id>
```

Verbs accept registered identifiers and opaque run IDs only —
never filesystem paths, code, URLs or installer instructions.

| Verb | Behavior |
|---|---|
| `validate` | Read-only: report a published run's recorded execution status. |
| `verify` | Read-only: verify a published run's receipt integrity. |
| `replay` | Read-only: list a published run's recorded event keys (replay never invokes cognition). |
| `run` | **Locked.** Prints `EMPIRICAL_DISPATCH_DISABLED`, exit 2. |
| `suite` | **Locked.** Prints `EMPIRICAL_DISPATCH_DISABLED`, exit 2. |
| `reexecute` | **Locked.** Prints `EMPIRICAL_DISPATCH_DISABLED`, exit 2. |

The lock is deliberate and survives I30: the coordinator's generic
dispatch path raises `FOUNDATION_ONLY_DISPATCH_DISABLED` as well.
No other execution endpoint exists, and the Astra dashboard is
GET-only. Unlocking requires the separate owner empirical
authorization described in the implementation plan (Phase P); I30
engineering authorization does not satisfy it.

## Suite inventory tooling (I30)

`development.evaluation.coordinator` provides two pure planning /
verification operations. Neither launches workers, creates
learner state, executes scenarios or writes artifacts.

### `registered_suite(plan) -> tuple[RunRequest, ...]`

Given a validated `FrozenPlan`, returns one `RunRequest` per
registered member, in frozen member order, using the plan's own
member identities — nothing is inferred, substituted or dropped.
The default registered plan yields exactly 30 requests
(A10 / B5 / C5 / D10, seeds 0–4; each family C member is one
robustness bundle, and family D's random-eligible trajectory is
its own counted member). Inventories beyond the approved
ceilings (8 seeds, 32 runs per suite, counting counterparts and
re-executions) are rejected with `ContractError` before any work
begins.

### `verify_suite(plan, members) -> VerificationReport`

Reconciles supplied member evidence against the registered
suite. The plan text names a `RunArtifact` input; the contracts
define no such type, so evidence is supplied as
`MemberEvidence` — the smallest compatible typed projection of
the immutable published evidence (member identity, terminal
status, plan-digest binding, seed/protocol/variant, published
run and receipt identities, and, when available, the produced
registered-measurement inventory). (A `RunArtifact` type does
exist in `development.evaluation.integrity` as the result of
publishing a payload; it is not an input contract.)

Every planned member stays in the denominator. Missing,
duplicated, unexpected, digest-mismatched, seed/protocol/variant
-mismatched, non-terminal, incomplete, or evidence-free members
are each reported by identity in the report's reasons; a supplied
measurement inventory must match the member's registered
inventory exactly. The report verifies reconciliation of recorded
evidence — it is not scientific proof, it fabricates no finding,
and technical-fixture evidence never satisfies the empirical
gate G7.

## Technical scenario

```text
python -m tests.evaluation_scenario
```

Runs a bounded, disposable technical qualification across all
four families and both protocols (prequential runs with durable
score-before-learning, frozen selection assays, family C
robustness subcases, family D constrained policy preparation),
publishes and replays one technical artifact, and accounts for a
failed all-skipped run honestly. It prints one JSON object whose
`classification` is `TECHNICAL_FIXTURE`. It is not an empirical
result and never runs the registered 30-member suite.

## Engineering acceptance matrix

`tests/evaluation/test_engineering_acceptance.py` maps all 22
B10 acceptance criteria to the real tests that enforce them, the
governing evidence records, and gates G1–G6, with technical and
empirical status kept separate. During I30 every criterion's
technical portion is verified and every empirical portion remains
`PENDING_EMPIRICAL`; the matrix structurally refuses full
scientific acceptance (an empirical portion can only complete
against the I31 results record, which does not exist yet).

## Boundaries

- No cognition, schema, dependency or workflow changes belong to
  this tooling.
- Empirical dispatch stays locked during and after I30.
- The installed SEED organism is outside this work: never point
  an evaluation root at an installed home.
