# B10 Astra Evaluation — Final MINOR Findings Register (I26–I29)

Date: 2026-10-12. Branch: `seed-0.2-b10-impl-05-astra` (PR #31).
Cleanup starting head: `9ff5ed7645c60074a33587114cfa53e2b23f33d5`.
Engineering head under review: `df6c806dbe6ce542a8b708fc38b811d5a3d42f0a`.
Commits: `3fa0184` (RED tests), `9de1f05` (fixes), `df6c806`
(M-05 erratum). Independent final review:
`docs/reviews/2026-10-12-b10-astra-final-minor-review.md` —
**BLOCKER 0 / MAJOR 0 / MINOR 0 / UNRESOLVED 0 — G1–G6 PRESERVED —
MAJOR-1: CLOSED — MAJOR-2: CLOSED — I26–I29 TECHNICAL ACCEPTANCE:
PASS — DESIGN AMENDMENT REQUIRED: NO.**

Six findings were documented before this cleanup; M-02 entered
as a source-level candidate and was confirmed by reproduction
before being counted as a defect. Historical findings remain
visible below after closure.

| ID | Finding | Source / reviewed SHA | Disposition | Status |
|---|---|---|---|---|
| M-01 | Observer never recomputed the frozen-plan body digest | MAJOR-2 review MINOR at `01e6d28` | FIXED | CLOSED |
| M-02 | Missing plan could be reported as metric version mismatch | Source candidate in `_metric_block` at `9ff5ed7`; RED-confirmed | FIXED | CLOSED |
| M-03 | Client/server event-key grammar divergence | I26–I29 review MINOR-1 at `fd7c064` | FIXED | CLOSED |
| M-04 | Standalone transient reader session retained in thread context | MAJOR-1 review observation (b) at `afc936e` | FIXED | CLOSED |
| M-05 | Browser checklist quoted a label that never existed | I26–I29 review MINOR-2 at `fd7c064` | Documentation erratum | CLOSED |
| M-06 | Missing-file path leaked `FileNotFoundError` (pre-MAJOR-1 observation (a); the MAJOR-1 change made it a typed `ContractError`) | MAJOR-1 review at `afc936e` | CLOSED INFORMATIONAL | CLOSED |
| M-07 | Deadline expiring before corruption-inspecting read yields 429 ahead of a not-yet-established 409 | Deadline review MINOR at `fefce84` | CLOSED INFORMATIONAL (intended precedence) | CLOSED |

## M-01 — Frozen-plan body digest (FIXED, `9de1f05`)

Reproduction (`3fa0184` on `9ff5ed7`): genuinely published run
pairs whose plan body was edited (threshold value; member variant)
or whose freeze receipt `body_sha256` was forged, with stated
digests kept and only transport integrity regenerated, compared
with HTTP 200. Fix (`dashboard/services/evaluation.py`,
`_plan_state`): the served body is verified by recomputing, over
its canonical bytes (`development.evaluation.canonical`, a pure
projection importing only contracts — no evaluator/execution
dependency), the producer's own definitions from
`development/evaluation/analysis.py`:
`sha256(SEED_B10_ANALYSIS_PLAN_V1\0 + canonical)` must equal the
manifest plan digest, and `sha256(canonical)` must equal the
receipt `body_sha256` when present (absence downgrades the binding
to not-established; contradiction is 409 `artifact_error`). A
canonically equivalent re-serialization of the same body still
verifies (representation-independent). Tests:
`tests/dashboard/test_evaluation_minor_cleanup.py` (4 cases);
reviewer reproduced the RED pattern (`assert 200 == 409` ×3) and
the GREEN behavior independently. This verifies internal plan
binding; it is not a claim of authentication against an attacker
who controls every trust anchor.

## M-02 — Missing plan vs version mismatch (FIXED, `9de1f05`)

Reproduction: the MAJOR-2 missing-plan fixture (plan file removed,
transport rehashed) returned metric state `version_mismatch`
although the registered version was unknowable. Fix
(`_metric_block`): unknown registration yields `not_established`;
`version_mismatch` is reported only when the registered version is
known and demonstrably disagrees. Fact-based states keep
precedence: `unavailable` (row absent), `ambiguous` (multiple
rows) and `unpaired` (identities differ) are determinable from the
stored rows alone and are decided before any registration
question.

## M-03 — Event-key grammar (FIXED, `9de1f05`)

Both sides now enforce the registered contract identically
(`dashboard/api/evaluation.py::_event_key`;
`dashboard/static/evaluation_support.js`): phase ∈ {training,
measured, probe}, subcase ∈ {default, fresh, stale, unavailable,
contradictory}, stage ∈ {pre, action, outcome, checkpoint,
update}, ordinal a canonical decimal integer in 1..2048 (leading
zeros, signs, fractions and out-of-range values rejected).
Server table (13 cases) and updated Node route tests are green.
Earlier client tests that used `9223372036854775807` /
`9007199254740993` as event ORDINALS were corrected: those values
are evidence source IDs, valid and lossless inside event bodies
(parseEvidence tests and the max-ids fixture unchanged; the
reviewer's API probe fetched a max-ids event detail with both IDs
intact while an int64-max ordinal was rejected with 422). A
local-browser smoke test of event navigation at this head is
recorded separately below; the historical I29 11/11 acceptance is
unchanged.

## M-04 — Reader transient session lifecycle (FIXED, `9de1f05`)

Characterization: standalone `EvaluationReader` calls installed a
fresh transient session via `_begin()` and never removed it, so
the calling thread's context retained the session (and its
raw-file caches) after the operation completed; HTTP requests were
unaffected (the API's scoped `request_session()` resets via its
token). Fix (`development/evaluation/reader.py`): `_begin()` now
reports ownership and a `_public` decorator on the ten public
operations releases the transient session on completion, success
or failure. Nested standalone calls refresh the transient session
without owning its release (historical per-call budget semantics
preserved); ambient sessions are never reset or replaced. Tests:
five lifecycle cases (release after success/failure, ambient
unaffected, per-thread release, per-call budgets). The
reviewer's mandatory G6 battery passed: tests/evaluation 631
(incl. replay-budget, resumable-index, fingerprint and
corruption-typing suites) and the MAJOR-1 budget/deadline file
15/15.

## M-05 — Browser-verification erratum (CLOSED, `df6c806`)

A dated erratum was appended to
`docs/evaluation/browser-verification.md` explaining that the
quoted "Untrusted artifact preview" label never existed in the
implementation or on screen; the observed behavior (stored bytes
rendered as literal text via safe DOM construction) was and is
accurate. The historical table, the 9/11 tunnel record and the
11/11 local Mac addendum are byte-unchanged (append-only, +14/−0,
verified by the reviewer).

## M-06 — Typed missing-file exception (CLOSED INFORMATIONAL)

Verified: the reader's `_read` converts `OSError` to the typed
`ContractError`; a missing published run is the typed 404 envelope
at the service boundary; a missing chunk-inventory file raises
`ContractError` from `verified_file` (cleanup tests); no caller
depends on the previously leaked `FileNotFoundError` (reviewer's
grep). The typed behavior is consistent with the documented
reader/service contracts. No code change required; the leaked
exception is not restored.

## M-07 — Deadline/corruption precedence (CLOSED INFORMATIONAL)

Both orders are now pinned by tests
(`test_evaluation_minor_cleanup.py`): corruption the reader
inspects before the deadline → 409 `artifact_error`; the deadline
expiring before the corrupting file can be inspected → 429
`deadline_exceeded`. The service never returns 200 over unverified
evidence, established errors are never overwritten by a later
deadline check (final enforcement runs only on the success path),
and no extra reads are performed after the deadline to reclassify
an error. This precedence is intended behavior.

## Verification summary (author, at `df6c806`)

Cleanup file 27 passed; dashboard 362 passed; evaluation 631
passed; full repository 1,580 passed / 2 warnings; 7/7 standalone
scenarios; JS syntax, compileall and `git diff --check` clean;
cleanup range touches exactly seven files with zero protected
scope. The independent review reproduced every count exactly.

## Browser smoke test (M-03, at `df6c806`)

Performed 2026-10-12 on the owner's Mac (Chrome, macOS) against
engineering head `df6c806`, in a fresh isolated checkout
(`~/SEED-astra-smoke`), with a disposable synthetic fixture
(`complete-negative`, built under `/private/tmp`) and an
observer-only dashboard on `127.0.0.1:8971` -- no tunnel, no
`--operator`, the installed organism never accessed. Steps: (1)
the Evaluation run list rendered the published run; (2) the run
detail rendered with separate Execution and Scientific findings
sections (finding NEGATIVE, preregistered threshold rule); (3)
Replay events rendered the recorded-events table; (4) the event
`measured:default:1:update` opened its Recorded event detail
(phase/subcase/ordinal/stage shown; "Recorded replay only; no
cognition is invoked"); (5) Back returned to the events list;
(6) a directly loaded invalid route with ordinal 0
(`event=measured:default:0:update`) was rejected safely with an
"Invalid view link" notice -- no event detail, no broken page.
All six steps PASS. This smoke test is identified separately from
the historical I29 acceptance: it does not alter the preserved
11/11 record.

PR #31 remains OPEN and unmerged. I30 not started; I31 NOT
AUTHORIZED; no empirical execution performed; the installed SEED
organism was never accessed or modified.
