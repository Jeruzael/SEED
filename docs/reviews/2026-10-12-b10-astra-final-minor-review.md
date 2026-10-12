# B10 I26–I29 Astra Evaluation — Independent Final Review (MINOR Cleanup + Full-Branch Acceptance)

Date: 2026-10-12. Reviewer: fresh independent reviewer (not the author).
Review tree: clean clone at `/tmp/seed-review-final`, HEAD
`df6c806dbe6ce542a8b708fc38b811d5a3d42f0a`, working tree clean.
Old-head reproduction tree: `/tmp/seed-review-old` at
`9ff5ed7645c60074a33587114cfa53e2b23f33d5` with only the cleanup
test files copied in. Master: `3406e1f2d5f757032befc9b91380ea7636b827fb`.
PR #31 OPEN, unmerged; this review pushed and committed nothing.

Cleanup commits on `9ff5ed7`: `3fa0184` (RED tests), `9de1f05`
(fixes), `df6c806` (M-05 erratum, docs-only). The cleanup range
touches exactly the seven claimed files:
`dashboard/api/evaluation.py`, `dashboard/services/evaluation.py`,
`dashboard/static/evaluation_support.js`,
`development/evaluation/reader.py`,
`docs/evaluation/browser-verification.md`,
`tests/dashboard/test_evaluation_assets.py`,
`tests/dashboard/test_evaluation_minor_cleanup.py`.
No `seed/**`, workflow, or dependency path appears in the cleanup
range, nor anywhere in the full branch range
(`3406e1f..df6c806` diff over `seed/`, `.github/`,
`requirements*` is empty).

## Part A — the seven findings

### M-01 — Frozen-plan body digest not recomputed by observer: FIXED

Code verification (reviewer's own reading):

- Producer contract, `development/evaluation/analysis.py`:
  `analysis_digest(plan)` =
  `sha256(b'SEED_B10_ANALYSIS_PLAN_V1\0' + canonical_bytes(body))`,
  and `freeze_plan` writes the freeze receipt with
  `body_sha256 = sha256(canonical_bytes(body))`.
- The fix in `dashboard/services/evaluation.py::_plan_state`
  recomputes exactly that digest over the served body's canonical
  bytes and requires equality with the manifest `plan_digest`
  (mismatch → 409 `artifact_error`); it requires a present
  `body_sha256` to equal `sha256(canonical)` (mismatch → 409), and
  treats an absent `body_sha256` as a missing binding link
  (binding not established, never a match). Pre-existing cross-file
  stated-digest checks (manifest vs plan file vs receipt vs
  metrics, contradiction → 409, absence → not established) are
  retained ahead of the body verification.
- Dependency boundary: `development/evaluation/canonical.py`
  imports only `json` and `.contracts`. `canonical_bytes` is a pure
  typed projection (sorted JSON, floats as f64 hex). The dashboard
  gained no evaluator/execution dependency; the new import in the
  service is the canonical module plus `hashlib`.

Reproduction and GREEN (reviewer's own runs):

- On `9ff5ed7` with only the cleanup tests copied in, the three
  M-01 tamper tests failed, and the failure mode is the claimed
  one: `assert 200 == 409` — a threshold-tampered plan body with
  stale stated digests and regenerated transport hashes was
  ACCEPTED (HTTP 200) by the old code. Member tamper and
  `body_sha256`-field forgery likewise passed on the old head.
- On `df6c806` all three return 409, and
  `test_plan_canonical_representation_accepted` passes on both
  heads: a canonically equivalent re-serialization of a genuine
  plan body still compares compatible (HTTP 200), proving the
  check is over canonical content, not stored bytes.

### M-02 — Missing plan reported as version mismatch: FIXED

- RED independently reproduced on `9ff5ed7`: with the frozen plan
  absent, eligibility was `not_established` but the metric state
  was `'version_mismatch'` (`AssertionError: assert
  'version_mismatch' == 'not_established'`).
- Fix read in `_metric_block`: the registered version is looked up
  per side from that side's established plan; `registered is None`
  (plan absent, or metric not registered in it) now yields
  `not_established` and returns; `version_mismatch` is reached
  only when the registered version is known and the stored row's
  version disagrees.
- Precedence audited in code: `unavailable` (a side has no rows)
  → `ambiguous` (>1 row) → `not_established` (missing row
  identity) → `unpaired` (identities differ) → `not_established`
  (registration unknown) → `version_mismatch` (known registration
  disagrees) → `paired`. Structural evidence dominates version
  claims, and unknown registration can no longer masquerade as a
  mismatch. The author's missing-plan test passes on the new head.

### M-03 — Client/server event-key grammar divergence: FIXED

- Both sides now implement the identical registered contract
  (diff read in full): phases `{training, measured, probe}`,
  subcases `{default, fresh, stale, unavailable, contradictory}`,
  stages `{pre, action, outcome, checkpoint, update}`, ordinal a
  canonical decimal in 1..2048 (regex `[1-9][0-9]{0,3}` + ceiling
  check; no leading zeros, sign, or fraction). Server:
  `dashboard/api/evaluation.py::_event_key`; client:
  `dashboard/static/evaluation_support.js::parseEvaluationRoute`.
- Server table: the author's 13 parametrized cases passed in the
  reviewer's cleanup-file run (27 passed, below).
- Client: the Node route tests were updated — the two values
  previously (incorrectly) accepted as ordinals,
  `9223372036854775807` and `9007199254740993`, are now in the
  reject list alongside `0`, `2049`, `01`, and unregistered
  phase/subcase/stage; ordinals 1 and 2048 parse. The updated
  assets tests passed in the reviewer's dashboard run (362,
  below).
- Source-ID fidelity preserved, verified end-to-end by the
  reviewer's own probe against the genuine `max-ids` fixture: the
  stored event `measured:default:1:update` (ordinal 1) returns
  HTTP 200 through the API, and its body carries
  `source_ids: ["9223372036854775807", "9007199254740993"]`
  losslessly as strings; the same int64-max value used as an
  event ORDINAL is rejected (HTTP 422). The `parseEvidence`
  signed-64 tests in `test_astra_assets.py` pass. No registered
  fixture event key approaches the 2048 ceiling (the max-ids
  event's ordinal is 1; fixture journals use small sequential
  ordinals).

### M-04 — Standalone reader transient-session retention: FIXED; G6 PRESERVED

Fix read in `development/evaluation/reader.py`: `_begin()` now
returns ownership (ambient session → never owned, never reset;
no session → this call owns the transient it creates; an existing
transient from a nested standalone composition is refreshed
without ownership transfer, preserving historical per-call
semantics). A `@_public` decorator on exactly the ten public
operations (receipt, verified_file, runs, detail, measurements,
events, event, curve, chunk, snapshot_tables) releases the owned
transient session in a `finally`, on success and failure alike.
`request_session()` is untouched.

Reviewer's own characterization probe (genuine complete-negative
fixture): the session context variable is `None` after a
standalone `runs()`, after a standalone `detail()`, after a failed
`detail()` (missing run, `ReaderError`), and in a worker thread
after its own standalone call (main thread unaffected); inside
`request_session()` the ambient session object is identical across
calls and the context is `None` after exit. The author's tests
additionally cover release after budget-exhaustion failure and
per-call budgets for standalone calls (cleanup file, 27 passed).

Mandatory G6 battery (reader.py changed) — all run by the
reviewer on `df6c806`:

- `tests/evaluation` in full: **631 passed** — including
  `test_replay.py`, `test_replay_budget.py`,
  `test_replay_budget_escape.py` (resumable replay indexes,
  lossless page/cursor progression, partial-page-on-budget),
  `test_reader.py`, `test_shared_budget.py`,
  `test_reexecution.py` / `test_reexecution_fidelity.py`,
  `test_integrity.py` and `test_frozen.py` (receipt/chunk
  verification, fingerprint invalidation, corruption-vs-budget
  error typing).
- MAJOR-1 HTTP budget/deadline file: **15/15** within a combined
  targeted run (26 passed with the comparison suite) — aggregate
  per-request budgets, concurrency independence, and deadline
  behavior at the HTTP boundary are unchanged by the lifecycle
  fix.

**G6 PRESERVATION: CONFIRMED for the reader change.**

### M-05 — Historical browser-verification label: DISPOSITION VERIFIED (documentation erratum)

`git diff 9ff5ed7..df6c806` on
`docs/evaluation/browser-verification.md` is a pure append
(+14/−0): a dated erratum (2026-10-12, M-05) stating that the
quoted "Untrusted artifact preview" label never existed in the
implementation and did not appear on screen, and recording what
was actually observed (stored bytes rendered as literal text via
safe DOM text construction, with the byte count). The historical
table, the 9-of-11 tunnel record, and the 11-of-11 macOS
addendum are byte-unchanged.

### M-06 — Leaked FileNotFoundError became typed ContractError: CLOSED INFORMATIONAL (accepted)

Verified in code: `reader._read` converts any `OSError` from
`os.open` (including `FileNotFoundError`) into
`ContractError() from None`. The author's tests (in the 27) show
a missing payload file raising `ContractError` from
`verified_file` and a missing run surfacing as the typed 404
envelope at the service boundary — no unhandled exception.
Reviewer grep: no caller in `dashboard/` or
`development/evaluation/` catches `FileNotFoundError` around
reader calls (the remaining handlers are in unrelated storage /
artifact-writing paths). The change is consistent with the
documented typed-error contract; no code change required and no
reversion warranted.

### M-07 — Deadline-before-corruption precedence: CLOSED INFORMATIONAL (accepted)

Both orders verified by the author's tests, passed in the
reviewer's runs: corruption inspected before the deadline
expires → 409 `artifact_error`; deadline expiring before the
corruption-detecting read → 429 `deadline_exceeded`; never
HTTP 200 over unverified evidence. Mechanism read in code: the
API's per-route `guard.enforce()` runs only after the service
call returns successfully, so an already-established error
(404/409/422/503) is never overwritten by a later deadline
check, and no extra reads are performed after the deadline to
re-litigate the error kind. The precedence is intended behavior:
the 429 honestly reports that verification could not complete
within the approved budget rather than fabricating a corruption
finding.

## Part B — full branch vs master (`3406e1f..df6c806`)

Reviewer's own verification:

- **G1–G5 evaluator contracts:** `tests/evaluation` 631 passed
  (above); `tests/dashboard` **362 passed** (author claimed 362 —
  exact match: 335 prior + 27 cleanup).
- **Full repository:** **1,580 passed, 2 warnings** (author
  claimed 1,580 — exact match: 1,553 + 27). Standalone scenarios
  **7/7 PASS** (baseline, prediction_error, world_model,
  curiosity, semantic, self_model, decision), run individually.
- **MAJOR-1:** 15/15 budget/deadline tests; guarantees intact
  (see M-04 battery).
- **MAJOR-2:** comparison suite 11/11 within the targeted run;
  differing-outcomes-compatible and incompatible-provenance cases
  are in that suite and in the cleanup file's M-01/M-02 pairs,
  all green on the new head.
- **Observer-only / GET-only:** the evaluation API declares only
  `@router.get` routes (zero mutation-verb decorators); the
  cleanup range adds no endpoint.
- **Empirical dispatch lock:** functionally exercised by the
  reviewer — `cli.main(['run'|'suite'|'reexecute', <run-id>])`
  each emit `EMPIRICAL_DISPATCH_DISABLED` and return exit 2.
- **Protected scope:** zero diff over `seed/**`, `.github/`,
  dependencies/lock in both the cleanup range and the full
  branch range; audits `git diff --check`, `compileall`, and
  `node --check` on the changed JS are clean.
- **Installed organism:** untouched by this review and by the
  branch (no install/migration/LaunchAgent surface exists in the
  diff).

## Browser smoke test — NOT PERFORMED (environmental)

The M-03 instruction asked for a local-browser smoke test of
event navigation. It was not performed: this environment's
browser automation refuses loopback navigation, and a tunnel is
forbidden by the instruction. No screenshot or browser artifact
is claimed. Reviewer judgment: coverage is nevertheless adequate
for this change. The client grammar change narrows route
validation to the server's registered contract; both sides are
covered at the exact grammar points by the Node DOM/route tests
and the parametrized server table, event-detail retrieval of a
max-ids event was verified end-to-end through the API by the
reviewer, and real-browser Evaluation acceptance stands at 11/11
from the I29 record (unchanged by this cleanup). Residual risk
is confined to in-browser navigation behavior of a validation
narrowing, which the DOM tests exercise directly.

## Findings register (final)

| ID | Outcome | Basis |
|---|---|---|
| M-01 | FIXED | Body-digest recomputation verified against the producer formula; old-head HTTP 200 reproduction; new-head 409s; canonical re-serialization accepted |
| M-02 | FIXED | RED reproduced on old head (`version_mismatch`); new head `not_established`; precedence audited |
| M-03 | FIXED | Identical registered grammar both sides; server table + Node tests green; signed-64 source IDs lossless end-to-end; huge ordinals rejected (422) |
| M-04 | FIXED | Ownership-scoped transient release on the ten public operations; reviewer's characterization probe clean; G6 battery green |
| M-05 | CLOSED (documentation erratum) | Pure append +14/−0; historical records byte-unchanged |
| M-06 | CLOSED INFORMATIONAL | Typed `ContractError` verified in code and at the service boundary; no caller depends on the leaked exception |
| M-07 | CLOSED INFORMATIONAL | Both precedence orders tested; established errors never overwritten; no post-deadline reads |

## Verdict

- BLOCKER: 0
- MAJOR: 0
- MINOR: 0
- UNRESOLVED: 0
- G1–G6: PRESERVED (G6 explicitly re-verified for the reader
  lifecycle change: full evaluation suite, replay-budget suites,
  and the 15-test MAJOR-1 HTTP budget/deadline file)
- MAJOR-1: CLOSED
- MAJOR-2: CLOSED
- I26–I29 TECHNICAL ACCEPTANCE: PASS
- DESIGN AMENDMENT REQUIRED: NO

Disclosure: the local-browser smoke test for M-03 was NOT
PERFORMED for environmental reasons (see above); acceptance of
the client grammar change rests on the Node DOM/route tests, the
server parity table, the reviewer's API-level end-to-end probe,
and the preserved 11/11 I29 browser record. PR #31 remains OPEN
and unmerged; merging is an owner decision outside this review.
I30 not started; I31 NOT AUTHORIZED; no empirical execution
performed.
