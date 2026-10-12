# B10-I30 Engineering Release Qualification — Independent Review

Reviewer: fresh independent reviewer (did not author this work).
Reviewed from a clean clone (`/tmp/seed-review-i30`,
`git clone --no-hardlinks`), author's tree never modified.
Nothing pushed, committed, or PR'd by the reviewer.

- Canonical base: `f736b0feccf9bc99496bb6d9894f3a6b8ea77bf5` (verified
  equal to `origin/master`).
- Head under review: `da4b65e6990ae24fcb17beab588bc0cf6769b365`
  (branch `seed-0.2-b10-impl-06-release`; 5 commits: RED tests,
  feat, scenario tests, matrix tests, docs).
- Method: 67 reviewer-written probe checks against the production
  code (probe 1), 34 reviewer checks against the acceptance matrix
  (probe 2), plus full suite reproductions in the clone. Author
  claims were treated as claims and reproduced, not trusted.

## Diff scope (mechanical, obligation 13)

`git diff f736b0f..da4b65e --stat`: exactly 9 files, 1,366
insertions / 6 deletions — `development/evaluation/coordinator.py`
(the only production file), new `docs/evaluation/usage.md`,
append-only `docs/evaluation/engineering-gates.md`, status
updates in `docs/implementation-log.md` and
`docs/seed-0.2-development-plan.md`, and the four new test files.
`seed/**`, `dashboard/**`, `pyproject.toml`, lockfiles and
`.github/` diffs: **0 lines**. `git diff --check` clean.
`pip check`: no broken requirements. No new published artifact
schema: `contracts.py` and `integrity.py` are untouched.

## Per-obligation evidence

**1. Default suite structure (30 members, A10/B5/C5/D10).**
From `analysis.default_plan()` frozen via `freeze_plan` in my
clone: seeds exactly `[0,1,2,3,4]`; 30 members, unique ids;
family counts A=10, B=5, C=5, D=10. A = 5 PREQUENTIAL + 5
FROZEN_SELECTION_ASSAY, one of each per seed. B = 5 PREQUENTIAL,
one per seed. C = exactly one member per seed
(`c-contradictory-0..4`, profile `c-frozen`); the four robustness
subcases (fresh / contradictory / unavailable / stale) exist as
populations inside the single bundle profile and inside the one
member's expanded inventory (172 rows for `c-contradictory-0`,
including `c-fresh-*` and `c-stale-*` identities) — they are NOT
separate suite runs. D = 10 members, variants `seed` ×5 and
`random-eligible` ×5, two per seed; the random-eligible
counterpart is its own counted member and no 11th baseline member
exists. Training/measured counts are taken verbatim from the
frozen body (e.g. A-frozen training 320 / measured 80).

**2. Determinism and ordering.** Two `registered_suite` calls
return equal tuples with byte-identical serialization; order
equals frozen member order; every element is a `RunRequest` with
`count == 1` and the plan's own identities. Ordering derives from
the frozen body list, so it is host-independent.

**3. Eight-seed rejection; independent seed ceiling.** A
synthetic 8-seed body expanding the default families (48 members)
raises `ContractError` before any work. A 9-seed body with only 9
members (well under the run ceiling) also raises `ContractError`
— the `CAPS['seeds'] == 8` ceiling binds independently of runs.

**4. 32-run ceiling, exact.** A 32-member body is admitted
(exactly 32 requests); 33 members raise `ContractError`; no
member is dropped to fit. Duplicated member identities in the
body are refused, not silently deduplicated. Counterparts count:
all 10 D members (both variants) are inside the 30. Re-execution
accounting: the author's admission test, which I read and which
passes in the reproduced suites, shows all 30 members admitted
through `Coordinator.admit` and a second admission of the same
member rejected; `RunRequest` reservations are charged against
the retained-runs ceiling by the pre-existing `Budget` machinery
(exact-cap and one-over probes in `test_suite.py` use small mock
reservations — no large disk allocation).

**5. Frozen-plan bindings.** A fully valid 30-member evidence
tuple reconciles (`passed`, no reasons). Per-member digest
mismatch is reported by identity (`plan digest mismatch:
a-seed-0`). A `FrozenPlan` whose digest does not match its body
(forged digest `f…f`) does NOT reconcile evidence bound to the
true body digest: all 30 members report digest mismatch and the
report fails. Non-`FrozenPlan` inputs and non-tuple member inputs
raise `ContractError`.

**6. Reconciliation classifications.** Each probed independently
and reported by member identity: missing, duplicate, unexpected
extra, wrong seed, wrong variant, wrong protocol, non-terminal
status (`RUNNING` → `invalid terminal status`), `COMPLETED`
without `run_id` or without `receipt_digest` (`missing published
evidence` — a bare COMPLETED label is never accepted as proof),
measurement omission, invented measurement (`unregistered
measurement`), duplicated measurement identity. The returned
`VerificationReport` has exactly the contract fields
(`gate`, `passed`, `reasons`); `gate == 'suite'` (never a
G-gate); no findings field exists and no scientific verdict,
finding, or PASS beyond reconciliation is produced.

**7. Partial / failed / missing accounting.** 29 of 30 supplied →
exactly the one missing member named, suite fails. 17 of 30 →
exactly 13 missing members named. Empty evidence → 30 named
missing members, `passed=False`. One honest `FAILED` member and
one honest `INCOMPLETE` member each keep the suite failed with
`member did not complete: <id>: <status>`; no member ever leaves
the denominator.

**8. Technical scenario.** `python -m tests.evaluation_scenario`
in my clone: exit 0, single JSON object, `classification:
TECHNICAL_FIXTURE`, **17/17 checks passed**. Coverage: A
prequential (durable score journal prefix, actual learning-stage
updates confirmed) and A frozen assay (2 probes, worker-asserted
raw-state equality — frozen mode does not mutate); B prequential
with recorded exposure (rest .4 → .55 at ordinal 321 only); C
robustness subcases fresh/contradictory/unavailable/stale ×4;
D guard matrix over 8 contexts, literal task utilities, and the
random-eligible trajectory as a distinct role from one equal-start
digest; artifact published and read back; recorded replay without
cognition; interrupted run retains partial evidence (6,427 bytes);
failed run honestly `INCOMPLETE/LIMIT_REACHED`; skipped attempts
never become samples. Roots are `tempfile.mkdtemp` disposable
only; the module contains no reference to `registered_suite`,
`dispatch`, or any installed home, and does not run the
registered 30-member suite. `tests/test_evaluation_scenario.py`
asserts the identical 17 check names (`EXPECTED_CHECKS`) plus the
absence of any finding/verdict field in the output.

**9. 22-criterion acceptance matrix.** Verified independently of
the file's own self-checks, using my own scan of the tests tree:
all 22 criteria numbered 1–22 in order; **every cited test name
exists** (zero missing); **every cited evidence path exists**;
gates are exactly G1–G6, all six used; all technical statuses
`TECHNICAL_PASS`; **every empirical status is
`PENDING_EMPIRICAL`**. Criteria descriptions and cited tests match
the approved plan's section 7 traceability table, which I read
directly. The five documented name correspondences are real and
accurately disclosed in the criterion notes: plan
`test_all_c_mutations_precede_freeze` → criterion 3's
producer-owned C fixture tests; plan
`test_every_failure_stage_is_accounted` → criterion 4's
failure-ladder tests; plan
`test_all_registered_measurements_accounted` and
`test_suite_counts_failed_seeds` → criterion 15's
preregistered-inventory / failed-seed tests in `test_reporting.py`;
plan `test_execution_and_findings_independent` → implemented
`test_execution_and_finding_states_independent` (criterion 16).
All correspondence targets exist. `validate_matrix` refusals,
each reproduced with my own mutations: forged empirical
completion on technical evidence; empirical completion pointing
at the (absent) results file; missing criterion; 23 rows;
reordered criteria; ghost test citation; missing evidence path;
empty test list; `G7` gate; unknown gate; non-canonical status
strings. `claim_full_acceptance` refuses during I30.

**10. G7 pending.** `docs/evaluation/b10-v1-results.md` does not
exist. Grep of `development/` and `dashboard/`: the only
empirical/G7 mentions in production code are the CLI lock
constant `EMPIRICAL_DISPATCH_DISABLED` and the pre-existing lock
comment in `Coordinator.dispatch`. No code path claims empirical
completion; `EMPIRICAL_COMPLETE` appears only as an unused status
constant inside the matrix test file.

**11. Dispatch-lock bypass attempts.** CLI (via `cli.main` in my
clone): `run` / `suite` / `reexecute` with a valid 32-hex id →
exit 2 with `EMPIRICAL_DISPATCH_DISABLED` in the emitted JSON.
`suite` with `b10-shared-suite`, a filesystem path, or a URL →
exit 3; unknown verb, missing argument, extra argument, malformed
id → exit 3. Python interface: `Coordinator.dispatch(...)` raises
`RuntimeError` both with no plan and with a genuine frozen plan
attached — the generic path is not an alternate entry point.
Purity: calling `registered_suite` and `verify_suite` in an empty
working directory created no files, and the freeze root contents
were unchanged — the tooling executes nothing.

**12. G1–G6 / MAJOR-1 / MAJOR-2 preservation.** Reproduced in my
clone: `tests/evaluation` **641 passed**; `tests/dashboard`
**362 passed** (2 warnings) — the dashboard tree is byte-unchanged
and carries the MAJOR-1/MAJOR-2 regression suites. The coordinator
diff is purely additive in behavior: `git diff -U0` shows the only
removed lines are the two import lines (extended for the new
names); `Coordinator.__init__` / `admit` / `dispatch` /
`prepare_policy_pair` bodies are untouched.

**13. Protected scope.** See diff-scope section above: zero-line
diff for `seed/**`, dashboard, dependencies/lock, workflows,
schema and contracts. Installed organism never referenced by any
new code path (disposable temp roots only).

**14. Full-suite / standalone / resource-bound evidence.**
Reproduced in my clone: focused I30 tests **12 passed**
(`test_suite.py` 8, `test_engineering_acceptance.py` 2,
`test_evaluation_scenario.py` 2); full repository **1,592
passed, 2 warnings**; seven pre-existing standalone scenarios
each exit 0 with JSON output; new technical standalone exit 0.
Boundary tests use `Budget` arithmetic and synthetic bodies —
no large real allocation (my own probes likewise). All counts
match the author's reported numbers exactly.

**15. MemberEvidence design judgment.** The plan names a
`RunArtifact` input that `contracts.py` does not define.
`integrity.RunArtifact` exists only as a publish RESULT
(`run_id`, `receipt`, `science_digest`, `status`); it lacks the
member identity, seed, protocol, variant and plan-digest binding
that reconciliation must check, so it cannot serve as the input
contract. `MemberEvidence` is the smallest compatible typed
projection: exactly the fields reconciliation verifies, projected
from published immutable evidence, frozen and type-checked at the
`verify_suite` boundary (non-`MemberEvidence` elements raise
`ContractError`). The choice is documented in three places I
verified: the `MemberEvidence` docstring in `coordinator.py`,
`docs/evaluation/usage.md` (which explicitly distinguishes the
integrity publish result), and the I30 entry in
`docs/evaluation/engineering-gates.md`. No new published artifact
schema was introduced (contracts/integrity untouched). Sound;
no design amendment required.

**16. Documentation accuracy.** `usage.md` claims match the code
I exercised: CLI lock table (exit 2 + `EMPIRICAL_DISPATCH_DISABLED`
for run/suite/reexecute; read-only validate/verify/replay),
ceilings (8 seeds / 32 runs counting counterparts and
re-executions, `ContractError` before work), scenario
classification `TECHNICAL_FIXTURE` and its non-empirical status.
The engineering-gates I30 entry's counts (12 / 641 / 362 /
1,592, 17/17 scenario checks) match my reproduced counts exactly,
and it labels them author verification with independent review
following. Tracker and log wording: I30 is described as
"ENGINEERING IMPLEMENTED / QUALIFICATION IN PROGRESS", explicitly
"subject to independent engineering review, exact PR-head CI,
owner-approved merge and separate post-merge master CI" — never
as complete, closed, or merged. I26–I29 correctly advanced to
COMPLETE / VERIFIED / CLOSED (PR #32 merge `f736b0f` is the
branch base). Both documents state I31 NOT AUTHORIZED and NO
REGISTERED B10 EXPERIMENTS EXECUTED.

## Observation (not a finding)

`verify_suite` compares each member's `plan_digest` against
`plan.digest` but does not recompute `analysis_digest(plan.plan)`
internally. This matches the codebase's established trust model:
`FrozenPlan` instances are minted only by the freeze machinery
(`freeze_plan` / `require_frozen`, which verify receipt, body
hash and digest against a capability-checked root), and every
other consumer likewise trusts the constructed object. Obligation
5's specified behavior — evidence bound to a different digest
must not reconcile — is fully satisfied. Recorded for
transparency; it does not affect the verdict.

(Reviewer-probe note: an early sanity threshold in my own probe 2
expected >1,000 literal `def test_` functions; the tree defines
752, the suite's 1,592 tests arising substantially from
parametrization. A probe artifact, not a defect.)

## Addendum — evaluation-suite count discrepancy, resolved

Two completion reports reached the reviewer for the first
`tests/evaluation` run in the clone: one stating 641 passed, a
later one stating 627 passed with 14 setup ERRORs, all in
`test_semantic_inventory.py::test_missing_actual_semantic_source_
cannot_shrink_complete_inventory[...]` (627 + 14 = 641 collected).
Resolution, established before this report was finalized:

- The implicated file alone in the same clone: **28 passed**.
- At the time, the VM's 512 MB `/tmp` tmpfs was at 83% capacity,
  filled largely by accumulated `seed-i30-scenario-*` disposable
  roots (~6.7 MB each, left by repeated scenario executions)
  plus pytest scratch — the known tmpfs-exhaustion failure mode
  for long suite runs on this VM; the 14 errors were fixture
  setup errors under that pressure, not test failures.
- After cleaning `/tmp` (16% used), the complete
  `tests/evaluation` suite was re-run in the clone end-to-end:
  **641 passed, 0 errors** (202.37s, exit 0).
- The same semantic-inventory tests also passed inside the full
  repository run (1,592 passed).

The 641-passed figure used throughout this report is the
clean-run result and stands.

## Verdict

```text
BLOCKER 0
MAJOR 0
MINOR 0
UNRESOLVED 0

G1-G6: PASS / PRESERVED

I30 ENGINEERING QUALIFICATION: PASS
G7 EMPIRICAL: PENDING / NOT AUTHORIZED

DESIGN AMENDMENT REQUIRED: NO
```
