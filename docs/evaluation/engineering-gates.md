# B10 I09–I13 protocol engineering gates — 2026-10-04

Canonical branch point: `master d0a5da528611af1526723b3ec04f6a86b3d1d1c8` (local/remote verified clean before editing). Protocol branch: `seed-0.2-b10-impl-02-protocols`. Owner authority is I09–I13 only. Technical fixtures below are regression evidence, not B10 scientific experiments.

## Task record

| Task | Files / evidence | Task commit |
| --- | --- | --- |
| I09 | point_scores.py, checkpoint.py, channel.py; test_checkpoint.py: literal scores, unavailable probability, durability and terminal failures | `c2e10891043d4acc6a679f536b2a15248c7f1c1d` |
| I10 | adapters.py, worker.py; test_cycle_adapter.py: unchanged real cycle, original B3 object returned once, one prepare/select, two perceptions, original prior action effects | `f133b30b9384bf62bcda0174ca4c61f772caf411` |
| I11 | frozen.py, worker.py; test_frozen.py/test_completed_fixture.py: owned freeze, 200-row cutoff, all raw tables/schema/sequence/JSON and DB bytes, denied writes, reflect/consolidate assays | `ceb7292e1dd1c4f75531fc6d7dce06c7ca7171bb` |
| I12 | prequential.py, adapters.py, channel.py, worker.py; test_prequential.py/test_cycle_adapter.py: real online updates, every-eight maintenance, 8 consecutive / 2048 total skipped caps, exact 5s boundary, honest cleanup | `ac98676f33c88eb1d8c482301f86646f585ea90f` |
| I13 | test_adapter_equivalence.py, test_failure_fidelity.py, extra freeze guards; evaluator-only maintenance evidence repair; this record and current tracker/authority summaries | `6fb1aac95034ba04558e10b7509605fdd35b30fd`; initial review findings followed by separate repairs |

Paths above are relative to development/evaluation or tests/evaluation. Original RED/repair output and task ledger are retained in ignored `.superpowers/b10-protocols/`. Useful task/review history is not squashed.

## G3 — durability, parity and failure fidelity

Author checks demonstrate prediction/outcome → approved point score → append/flush/fsync → constant SCORE_ACK → original current-transition learning. The closed worker channel never receives the score, truth, aggregates or classifications. Failed durability is terminal and permits no current Q/B1/B4/B7 mutation; prior reflect/consolidate effects remain legitimate and captured. Brier uses genuine probability only (`brier(.75,False)==.5625`). Approved component/frame and combined detail limits remain enforced.

Parity compares independently constructed original SeedOrganism with a test-owned controlled body against the actual same cycle through SyntheticBody/CaptureSession. Both receive identical starting rows/settings/injected RNG/perceptions/logical stage schedule. Control never calls construct_core, SyntheticBody or CaptureSession. External control spies advance stages without changing algorithms. Comparisons cover all raw tables, IDs, producer JSON, action/reward/Q/B3/B4/B5/B6/B7/B8, candidate selection/history/digest, four actions, and eight-cycle declared maintenance.

Only genuine process PID fields are excluded and each exact raw JSON/column location is audited against its process's actual PID; all other raw bytes/values remain compared. No storage geometry exclusion was needed. The copied normal-source control has no development/evaluation package/config/artifacts and still constructs, cycles, persists and closes.

The actual worker failure ladder covers prediction/outcome capture, point scoring, append/partial/flush/fsync/deadline/protocol rejection/duplicate, Q/persistence/B4/B7 before and after actual commits, real swallowed B7 snapshot errors, evidence capture after commit, external test-only aggregation/index/publication faults, B6 maintenance commits/returned failed status, and cleanup. Acknowledged mutations remain; no next dispatch, rollback, replay, relearning or double counting occurs. Confirmation comes from actual rows/source IDs and producer returns, not expected control flow.

I13 found lost maintenance IDs on a post-commit error. The narrow evaluator repair reads the actual newly created consolidation_runs row, retains failed/unconfirmed status and provenance, and terminates INCOMPLETE. Raw producer JSON exceeding the per-string wire cap is preserved losslessly in <=4096-character raw_json_chunks. Producer SQL/schema/payloads remain unchanged. Cleanup requires a separate worker receipt; process death alone cannot imply cleanup success.

G3: **PASS** at repaired review head `2be1e6feb660d81f189098ef62f92631a115631f`. Initial FAIL at `6fb1aac` and all separate repairs remain recorded below; fresh complete-diff review independently validates durability, raw parity and failure fidelity.

## G4 — frozen raw immutability

Completed owned training/checkpoint validation occurs before held-out observations. Pending commands, open transactions, incomplete training and nonprogressing B4 drain are rejected. Frozen readers use immutable mode=ro, query_only and a write-denying authorizer; no mutable organism constructor, migration, recovery, Q/B1/B4/B6/B7 mutation or operational timestamp writes run during probes. Only read transactions, introspection and bounded connection-local busy_timeout are allowed.

Every table, schema, sqlite_sequence, unprojected JSON and required DB bytes remain equal before/after each probe. The 200-row training cutoff stays 200 across held-out outcomes. Forced reflect/consolidate setup occurs before freeze; probes explicitly record driver=frozen_projection_v1, assay_kind=FROZEN_SELECTION_ASSAY, internal_action_effects=suppressed_by_protocol. Write attempts latch FAILED, preserve the source checkpoint and cannot be repaired/reused.

G4: **PASS** at repaired review head `2be1e6feb660d81f189098ef62f92631a115631f`, including raw immutability, normal original-owner freeze cleanup and rejection of failed cleanup.

## Verification and review

I09: 16 focused tests, full suite 1055 passed / two existing warnings. I10: 22 focused/adjacent checks, full suite 1062 passed / two existing warnings. I11: full I01–I11 suite 1076 passed / two existing warnings (only then-unimplemented I12 excluded), plus incomplete-training guard. I12: 22 focused/adjacent checks; complete evaluation suite 204 passed. Intermediate RED and fixture failures remain in the ledger; final all-task runs use no exclusions.

I13 focused checkpoint/cycle/online/parity/failure tests: 65 passed. Three added freeze guards: PASS. All seven standalone regressions baseline/prediction_error/world_model/curiosity/semantic/self_model/decision: PASS. Final full repository: **1122 passed / two existing warnings** (119.83s); complete evaluation suite: **239 passed** (109.94s); separately selected critical adversarial protocol suite: **83 passed** (81.70s), covering checkpoint/cycle/frozen/online/parity/failure-fidelity files without exclusions. These are pre-review author counts, not final repair verification. The fresh initial complete-diff review independently passed all 239 evaluation tests in disjoint selections but reproduced four gaps; passing tests alone did not grant G3. Post-repair full suite: **1140 passed / two existing warnings** (120.63s); complete evaluation: **257 passed** (110.50s); seven standalone regressions: **PASS**. Separately selected post-repair critical suite: **101 passed** (82.36s), without exclusions. [Fresh complete-diff repaired-head review](../reviews/2026-10-04-b10-protocols-final-review.md) at `2be1e6feb660d81f189098ef62f92631a115631f`: **0 BLOCKER / 0 MAJOR / 0 MINOR / 0 unresolved**; all original R1–R4 resolved; **G1/G2/G3/G4 PASS**. Reviewer independently passed all **257 evaluation tests** (91.48s) and additional journal-ancestry, raw-PID, real pre-ACK failure and freeze-lifecycle probes. No protocols PR has been opened at this author evidence checkpoint.

## Preservation and scope

G1/G2 remain preserved within their original trusted-code storage threat model, including terminal detectable identity mismatch and one assigned writer. No native same-UID hostile-open guarantee is introduced. `seed/** NONE`; schema v7 unchanged; no evaluator DB tables, dependencies, lock/workflow changes, API/UI, registered families/scientific suite, I14–I30/I31, deployment or installed-home access. B10 overall and engineering IN PROGRESS; empirical evaluation NOT STARTED / NOT AUTHORIZED; NO B10 EXPERIMENTS EXECUTED; INSTALLED SEED UNTOUCHED.

Protocols [PR #24](https://github.com/Jeruzael/SEED/pull/24), exact PR-head CI 37155625889, normal master merge `4fce86257a4b35e1d8bd1e9c140d1a83f239a108` and distinct exact push CI 37189929244: **SUCCESS / VERIFIED**. Separate [docs/b10-protocols-closure publication](../reviews/2026-10-04-b10-protocols-closure.md) has its own pending exact PR/master CI gates. Mandatory STOP follows verified protocols closure.

## Independent findings and separate repairs

[Initial exact-head review](../reviews/2026-10-04-b10-protocols-review.md): **0 BLOCKER / 3 MAJOR / 1 MINOR / 4 unresolved** at `6fb1aac95034ba04558e10b7509605fdd35b30fd`; G3 FAIL. All repairs remain evaluator/test-only; no design amendment or core repair is required.

| Finding | Repair / RED and GREEN evidence | Commit |
| --- | --- | --- |
| R1 MAJOR: detached journal ancestry still ACKed | Pin canonical no-follow evaluation/partials/run directory identities and exact file inode before/after durability. Seven replacement RED failures plus two ancestor-preserving-run-inode RED failures; 50 checkpoint/failure checks PASS, further ancestry tests PASS in 91 affected checks. | `4c4291e82ef367562d90e9abc21c62fd668d000f`, completed in `5d5f4eee42ecf92985813071c2b13a19ff57fb2d` |
| R2 MAJOR: unacknowledged attempt/prior effects discarded | Retain one <=512-byte terminal attempt summary joined to one <=64-KiB actual worker response, including prior consolidation rows and explicitly unconfirmed updates. Missing worker response keeps ACK unknown/null and capture unavailable; no invented current stage. Real consolidate+flush RED; 35 online/failure checks plus unknown-response check PASS. | `966d2064b71beaa9d5f0661db59bafd3366a428e`; extra response regression in `5d5f4eee42ecf92985813071c2b13a19ff57fb2d` |
| R3 MINOR: PID normalization hid non-PID JSON spelling | Mask only independently validated/audited scalar PID spans in original raw text. Non-PID whitespace/key order/number spelling/escaping remain compared. Three oracle poison RED failures; 11 parity/oracle checks PASS. | `25ef765349f98564f9e857a25d9c76fb2b39b04f` |
| R4 MAJOR: freeze double-close and failed cleanup accepted | Owned fixture completion delegates original core close, which owns Memory and instance lock, then constructs manifest only after success. Freeze requires successful separate worker cleanup receipt. Two actual normal/faulted freeze RED failures; three handoff/guard checks PASS; affected completed-fixture/foundation checks PASS. | `0c89c8a0f206c710cf66b05119cc8d224f70a3f1` |

Executor ruling: every behavior explicitly declined in the initial review is accepted for the reason listed there and remains within the approved scope/test evidence; none is silently dropped. The full registered science families, native hostile same-UID SQLite race prevention and I14+ publication architecture remain outside this task. Final independent resolution: **0 BLOCKER / 0 MAJOR / 0 MINOR / 0 unresolved**, R1–R4 resolved; see the distinct repaired-head report. Exact publication evidence follows only after hosted verification; no initial verdict is rewritten or reused as approval.

## I30 engineering release qualification — 2026-10-13

Branch `seed-0.2-b10-impl-06-release` from canonical master
`f736b0feccf9bc99496bb6d9894f3a6b8ea77bf5` (PR #32 merge; post-merge
CI 38292784699, push, all three jobs SUCCESS). I30 adds bounded
suite inventory tooling and technical qualification only; it does
not execute the registered empirical suite.

- **Suite inventory (`registered_suite`)**: one `RunRequest` per
  registered member of the frozen default plan, in frozen order:
  exactly 30 (A10 / B5 / C5 / D10, seeds 0–4; family C members are
  single robustness bundles; family D random-eligible trajectories
  are individually counted). Deterministic and byte-identical
  across calls. Eight seeds expanding to 48 requests are rejected
  before work begins; the 32-run ceiling (counting re-executions
  and counterparts) admits exactly 32 and rejects 33; the seed
  ceiling binds independently. No member is dropped to fit a limit.
- **Suite reconciliation (`verify_suite`)**: evidence is supplied
  as `MemberEvidence`, the smallest compatible typed projection
  of the published immutable evidence (the contracts define no
  `RunArtifact` input type; that name exists in `integrity` as
  the publish result). Missing, duplicate, unexpected,
  digest/seed/protocol/variant-mismatched, non-terminal,
  incomplete and evidence-free members are each reported by
  identity; supplied measurement inventories must match the
  registered inventory exactly. Technical-fixture evidence is
  labeled as such and never satisfies G7.
- **Technical scenario** (`python -m tests.evaluation_scenario`):
  bounded disposable qualification of all four families and both
  protocols, artifact publication and recorded replay, and an
  honest all-skipped failure ladder; output classification
  `TECHNICAL_FIXTURE`, 17/17 checks PASS. Pytest integration in
  `tests/test_evaluation_scenario.py` exercises the same
  assertions.
- **Acceptance matrix** (`tests/evaluation/
  test_engineering_acceptance.py`): all 22 criteria mapped to
  real, identified tests and evidence records under G1–G6;
  technical portions verified, every empirical portion
  `PENDING_EMPIRICAL`; the matrix refuses full scientific
  acceptance and refuses empirical completion from technical
  fixtures.
- **Dispatch lock**: CLI `run`/`suite`/`reexecute` still return
  `EMPIRICAL_DISPATCH_DISABLED` (exit 2); the coordinator generic
  dispatch path still raises; arbitrary paths, URLs, unknown
  verbs and unregistered selectors are rejected.
- **Author verification**: focused I30 tests 12 passed;
  evaluation 641 passed; dashboard 362 passed; full repository
  1,592 passed / 2 warnings; seven pre-existing standalones exit
  0; new technical standalone exit 0; `pip check` clean;
  protected scope (`seed/**`, dependencies/lock, workflows) zero
  diff against canonical master.
- **Status**: G1–G6 PASS / PRESERVED. G7 EMPIRICAL: PENDING /
  NOT AUTHORIZED. I31 NOT AUTHORIZED. No registered B10
  experiments executed. Independent engineering review and PR
  publication gates follow this entry.

### I30 temporary fixture cleanup repair (2026-10-13, pre-merge)

- **Defect**: `tests/evaluation_scenario.py::run_all(base=None)`
  allocated its scenario directory with `tempfile.mkdtemp(...)` and
  never removed it (~6.7 MB per invocation; accumulation on a
  512 MB `/tmp` tmpfs produced disk-full fixture errors during
  the original I30 review). Test-infrastructure defect only; no
  production behavior involved.
- **Repair** (branch `seed-0.2-b10-impl-06-release`, PR #33):
  RED tests at `99ec026` (4 failed for the leak and the unreaped
  timeout worker; caller-preservation guard passed), GREEN fix at
  `be03c91`: `run_all(base=None)` owns exactly one
  `tempfile.TemporaryDirectory(prefix='seed-i30-scenario-')`
  removed on return and on exception; a caller-provided `base`
  is never deleted; `_spawn` workers are terminated and reaped
  (terminate -> bounded join -> kill -> bounded join; failure to
  reap raises) on every path before storage is removed.
- **Evidence**: focused scenario tests 7 passed; standalone
  17/17 `TECHNICAL_FIXTURE` with zero leftover directories;
  three-repeat isolated-TMPDIR cleanup audit PASS; dashboard
  362 passed; full repository 1,597 passed / 2 warnings (1,592
  pre-repair + 5 new cleanup tests); `pip check` clean.
- **Review**: fresh independent review at `be03c91` —
  BLOCKER 0 / MAJOR 0 / MINOR 0 / UNRESOLVED 0 —
  I30 TEMPORARY FIXTURE CLEANUP REPAIR: PASS (record:
  `docs/reviews/2026-10-13-b10-i30-fixture-cleanup-review.md`).
  The original I30 review record is preserved verbatim.
- **Status**: I30 implemented and qualified on the branch,
  pending owner-approved merge and post-merge closure.
  G1–G6 PASS / PRESERVED. G7 EMPIRICAL: PENDING / NOT
  AUTHORIZED. I31 NOT AUTHORIZED.


### I30 engineering post-merge qualification evidence (2026-10-13)

- Engineering [PR #33](https://github.com/Jeruzael/SEED/pull/33), accepted head `082391f82ff2221f31eb35889b2a18bb0ad50097`, normal merge `08683000aa0c3ea711c00fd993ec67461f770542`.
- Exact PR-head [CI 38314711901](https://github.com/Jeruzael/SEED/actions/runs/38314711901): three jobs SUCCESS.
- Distinct exact post-merge master push [CI 38317966927](https://github.com/Jeruzael/SEED/actions/runs/38317966927), run #65, attempt 2: Linux 3.11 1,596 passed / 1 skipped; Linux 3.13 and macOS 3.13 1,597 passed; two warnings each. All three jobs SUCCESS; deterministic standalones succeed on both Python 3.13 jobs (skipped as planned on 3.11).
- Engineering and temporary fixture cleanup independent review records remain unmodified. No empirical B10 experiments have run. G1–G6 PASS / PRESERVED; G7 PENDING; I31 NOT AUTHORIZED.
- [I30 engineering closure record](../reviews/2026-10-13-b10-i30-engineering-closure.md): drafted; documentation closure publication still requires its own independent review, exact PR-head CI, owner-approved normal merge, and distinct post-merge master CI. Do not record final closure until all pass.

### I30 closure retrospective and corrective publication (2026-10-14)

- PR #34 (closure documentation) merged at `0c477f2` before its
  independent documentation review (governance exception,
  tracked in issue #36; the closure record had disclosed the
  pending condition in advance).
- Retrospective independent review at `0c477f2`: PASS WITH
  FINDINGS — BLOCKER 0 / MAJOR 0 / MINOR 1 / INFORMATIONAL 3
  (record:
  `docs/reviews/2026-10-13-b10-i30-closure-retrospective-review.md`).
  MINOR-1: contradictory current-status wording in the
  development plan, corrected in the corrective-publication PR.
- PR #34 gates since fulfilled: exact-head CI `38323590019`
  SUCCESS; distinct post-merge master CI `38325297633` SUCCESS
  on all three jobs (fulfillment note appended to the closure
  record, Section G).
- **Status**: I30 ENGINEERING MERGED / MASTER CI VERIFIED /
  RETROSPECTIVE REVIEW COMPLETE / FINAL CORRECTIVE PUBLICATION
  PENDING. G1–G6 PASS / PRESERVED. G7 EMPIRICAL: PENDING /
  NOT AUTHORIZED. I31 NOT AUTHORIZED.
