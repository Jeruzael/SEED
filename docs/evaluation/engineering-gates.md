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

Protocols PR/exact-head CI/normal merge/exact master CI and separate docs/b10-protocols-closure publication remain pending. Mandatory stop follows verified protocols closure.

## Independent findings and separate repairs

[Initial exact-head review](../reviews/2026-10-04-b10-protocols-review.md): **0 BLOCKER / 3 MAJOR / 1 MINOR / 4 unresolved** at `6fb1aac95034ba04558e10b7509605fdd35b30fd`; G3 FAIL. All repairs remain evaluator/test-only; no design amendment or core repair is required.

| Finding | Repair / RED and GREEN evidence | Commit |
| --- | --- | --- |
| R1 MAJOR: detached journal ancestry still ACKed | Pin canonical no-follow evaluation/partials/run directory identities and exact file inode before/after durability. Seven replacement RED failures plus two ancestor-preserving-run-inode RED failures; 50 checkpoint/failure checks PASS, further ancestry tests PASS in 91 affected checks. | `4c4291e82ef367562d90e9abc21c62fd668d000f`, completed in `5d5f4eee42ecf92985813071c2b13a19ff57fb2d` |
| R2 MAJOR: unacknowledged attempt/prior effects discarded | Retain one <=512-byte terminal attempt summary joined to one <=64-KiB actual worker response, including prior consolidation rows and explicitly unconfirmed updates. Missing worker response keeps ACK unknown/null and capture unavailable; no invented current stage. Real consolidate+flush RED; 35 online/failure checks plus unknown-response check PASS. | `966d2064b71beaa9d5f0661db59bafd3366a428e`; extra response regression in `5d5f4eee42ecf92985813071c2b13a19ff57fb2d` |
| R3 MINOR: PID normalization hid non-PID JSON spelling | Mask only independently validated/audited scalar PID spans in original raw text. Non-PID whitespace/key order/number spelling/escaping remain compared. Three oracle poison RED failures; 11 parity/oracle checks PASS. | `25ef765349f98564f9e857a25d9c76fb2b39b04f` |
| R4 MAJOR: freeze double-close and failed cleanup accepted | Owned fixture completion delegates original core close, which owns Memory and instance lock, then constructs manifest only after success. Freeze requires successful separate worker cleanup receipt. Two actual normal/faulted freeze RED failures; three handoff/guard checks PASS; affected completed-fixture/foundation checks PASS. | `0c89c8a0f206c710cf66b05119cc8d224f70a3f1` |

Executor ruling: every behavior explicitly declined in the initial review is accepted for the reason listed there and remains within the approved scope/test evidence; none is silently dropped. The full registered science families, native hostile same-UID SQLite race prevention and I14+ publication architecture remain outside this task. Final independent resolution: **0 BLOCKER / 0 MAJOR / 0 MINOR / 0 unresolved**, R1–R4 resolved; see the distinct repaired-head report. Exact publication evidence follows only after hosted verification; no initial verdict is rewritten or reused as approval.
