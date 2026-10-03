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
| R3 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R4 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R5 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R6 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R7 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R8 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R9 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |
| R10 | Independent review FAIL | Pending | UNRESOLVED / REMEDIATION REQUIRED |

R1: writer ownership uses a separate owned lease file because macOS DB-file flock interferes with SQLite native locks. This is an application trusted-writer lease, not native-open race prevention. Source/target observable checks and terminal identity latch retained; 29 focused/adjacent tests passed.

R2: statement completion is checked across fetch, iteration, close, reuse and discarded cursors; explicit/context/isolation/script commit paths retain checks. No producer SQL change. Focused/adjacent result recorded in b10-r2-green.log.
