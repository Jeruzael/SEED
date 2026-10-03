# B10 foundation R1–R10 remediation — 2026-10-03

**Current authorization: B10 FOUNDATION REVIEW REMEDIATION — R1–R10 ONLY.** Canonical amendment master `1ea281f4cc968f97ca27cba8b7255a87d8798716`, exact push CI 37106546153, all three jobs SUCCESS. Original foundation `df0569a99f192a576fa2d60d0c2050500403fbc9`, engineering review `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3`, original review 0 BLOCKER / 9 MAJOR / 1 MINOR. Normal integration `358e2bd` preserves all eight task commits. Tracker/log conflicts retain canonical amendment publication plus original foundation review; all three amended technical documents match canonical master at integration.

Foundation I01–I08 IMPLEMENTED CHECKPOINT / REMEDIATION IN PROGRESS / NOT VERIFIED. G1 NOT VERIFIED. G2 NOT VERIFIED. B10 engineering IN PROGRESS. I09–I30 NOT STARTED / NOT AUTHORIZED BY THIS INSTRUCTION. Empirical evaluation NOT STARTED / NOT AUTHORIZED. NO B10 EXPERIMENTS EXECUTED. INSTALLED SEED UNTOUCHED. No core/schema/dependency/workflow/native VFS changes authorized.

Amended trusted-code storage contract applies: capability/path isolation remains required; adversarial concurrent same-UID mutation inside SQLite native opens is excluded. No prevention claim for that excluded race.

## Execution ledger

Baseline after normal integration: **62 foundation tests passed**. Each finding requires an expected failing reproduction, narrow repair, focused/adjacent verification and separate commit. Full suite/seven regressions, fresh independent review and mapped G1/G2 evidence remain pending.

Pre-flight: R1 identity guard is consumed by R2 finalization and R3 backup; R3 workspace accounting is shared by R4 sibling terminal latch; R6 root reconciliation must compose with live storage checks without reservation double-counting; R7 terminal channel must propagate through worker lifecycle; R8 reuses pure producer validation; R9 completed launch must preserve R1/R4 and original full-state fidelity. No I09 protocol is introduced.

| Finding | Before | Repair/test/commit | Current |
| --- | --- | --- | --- |
| R1 | 7 expected failures (missing DB, post-connect replacement, 3 sidecars, writer lease, foreign root), plus target identity reproduction | test_storage_identity; pre/post/ongoing/backup identity + owned writer lease | Author focused verification PASS; independent gate pending |
| R2 | 6 expected RETURNING failures: fetchone/fetchmany/fetchall/iteration/close/reuse | test_statement_finalization; cursor finalization/GC guard plus existing commit paths | Author focused verification PASS; independent gate pending |
| R3 | 4 expected failures: checkpoint/clone combined capacity, one-byte-over admission, retained snapshot accounting | test_backup_admission + state/storage regressions | Author focused verification PASS; independent gate pending |
| R4 | 3 expected failures: sibling write, new monitor/spawn, pre-launch rejection | test_shared_budget; durable run latch shared across sibling monitors/processes | Author focused verification PASS; independent gate pending |
| R5 | 9 expected failures: missing/zero/mismatched digest and changed complete runtime facts | test_profile_admission + profile/spec tests, 13 passed | Author focused verification PASS; independent gate pending |
| R6 | 4 expected failures: post-growth freeze/admission, partial count, active reservation reconciliation | test_live_capacity + limits/paths/analysis/state/workers | Author focused verification PASS; independent gate pending |
| R7 | 4 expected failures: malformed/exception action retry, continuing worker, client reuse | test_terminal_channel + channel/workers/leakage, 15 passed | Author focused verification PASS; independent gate pending |
| R8 | 5 expected failures: wrong action, unknown top/nested/private fields, malformed forecast | test_prediction_boundary + contracts/leakage, 14 passed | Author focused verification PASS; independent gate pending |
| R9 | 5 expected missing completed-fixture launch failures | test_completed_fixture + workers/state/leakage/determinism | Author focused verification PASS; independent gate pending |
| R10 | 6 expected failures: import function/builtin/assignment aliases and unresolved reachable helper imports | test_dependency_aliases + dependency absence/direction, 11 passed | Author focused verification PASS; independent gate pending |

R1: writer ownership uses a separate owned lease file because macOS DB-file flock interferes with SQLite native locks. This is an application trusted-writer lease, not native-open race prevention. Source/target observable checks and terminal identity latch retained; 29 focused/adjacent tests passed.

R2: statement completion is checked across fetch, iteration, close, reuse and discarded cursors; explicit/context/isolation/script commit paths retain checks. No producer SQL change. Focused/adjacent result recorded in b10-r2-green.log.

R3: pre-admits destination allocation plus a complete journal page set and 64-KiB metadata margin (conservative within existing ceilings); progress/completion checks charge every retained run file. Failed backups retain an owned incomplete prefix and return no trusted checkpoint/clone. This adds no scientific artifact publication or protocol.

R6: live retained bytes/run identities and active allocation reconcile before control/storage admission. Explicit active reservation membership replaces actual allocated bytes/count, leaving only outstanding allowance; release removes reservation. Empty partial directories count, and retained evidence is never pruned to fit. Scientific dispatch remains disabled.

R9: explicit FRESH/COMPLETED_OWNED_FIXTURE launch, completed owned schema-v7 DB identity/byte digest, no partial resume. Completed construction creates original producer objects with fresh assigned streams, avoiding Memory/organism initialization/recovery writes so tables/meta/settings/sequences/B4/B6/B7/B8 remain byte/logically unchanged. Closed-fixture validation uses immutable read-only SQLite inspection to avoid WAL/SHM creation; active state remains a normal writable producer connection. Integrity-check empty temp schema is allowed, attached DB paths still rejected. This is foundation launch plumbing only, not frozen/protocol/parity implementation.

R9 follow-up: fresh-stream probe initially requested an unsupported UUID role; corrected the technical probe to the declared producer role. R9 is not inferred from the earlier failed probe; the corrected focused run is the verification authority.

R10 resolves approved import/module/assignment alias patterns and propagates unknown dynamic-import edges through protected reachable helpers. Clean repository graph and SEED operation with evaluator absent pass; this is not general Python static-analysis completeness.

R2 acceptance completion: explicit Python 3.13 Connection.autocommit transition reproduced a missing bound check (1 expected RED); property forwarding now guards/finalizes/checks it, 20 statement/adapter tests GREEN. Python 3.11 lacks that native property and skips only that regression.

R9 manifest acceptance: two additional expected RED cases (missing B4 table and foreign evaluator table in a purported v7 fixture). Completion now binds the complete current producer table manifest without running migrations; focused launch/state/worker regressions GREEN.

Manifest fixture correction: the deliberately missing-table case needed foreign-key enforcement disabled in the test fixture to reach table-manifest admission. The earlier full run was 1 failed / 1025 passed / 2 existing warnings (fixture setup FK failure), not accepted as verification. Corrected completed-fixture tests pass; fresh full verification follows. No producer behavior was weakened.
