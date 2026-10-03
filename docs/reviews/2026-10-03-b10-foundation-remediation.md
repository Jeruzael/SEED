# B10 foundation R1–R10 remediation — 2026-10-03

**Current authorization: B10 FOUNDATION REVIEW REMEDIATION — R1–R10 ONLY.** Canonical amendment master `1ea281f4cc968f97ca27cba8b7255a87d8798716`, exact push CI 37106546153, all three jobs SUCCESS. Original foundation `df0569a99f192a576fa2d60d0c2050500403fbc9`, engineering review `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3`, original review 0 BLOCKER / 9 MAJOR / 1 MINOR. Normal integration `358e2bd` preserves all eight task commits. Tracker/log conflicts retain canonical amendment publication plus original foundation review; all three amended technical documents match canonical master at integration.

Foundation I01–I08 LOCAL ACCEPTANCE VERIFIED / PUBLICATION AND HOSTED VERIFICATION PENDING. R1–R10 RESOLVED. G1 PASS / G2 PASS — foundation scope. B10 engineering IN PROGRESS. I09–I30 NOT STARTED / NOT AUTHORIZED BY THIS INSTRUCTION. Empirical evaluation NOT STARTED / NOT AUTHORIZED. NO B10 EXPERIMENTS EXECUTED. INSTALLED SEED UNTOUCHED. No core/schema/dependency/workflow/native VFS changes authorized.

Amended trusted-code storage contract applies: capability/path isolation remains required; adversarial concurrent same-UID mutation inside SQLite native opens is excluded. No prevention claim for that excluded race.

## Initial execution ledger (historical sequence)

Baseline after normal integration: **62 foundation tests passed**. Each finding requires an expected failing reproduction, narrow repair, focused/adjacent verification and separate commit. Full suite/seven regressions, fresh independent review and mapped G1/G2 evidence remain pending.

Pre-flight: R1 identity guard is consumed by R2 finalization and R3 backup; R3 workspace accounting is shared by R4 sibling terminal latch; R6 root reconciliation must compose with live storage checks without reservation double-counting; R7 terminal channel must propagate through worker lifecycle; R8 reuses pure producer validation; R9 completed launch must preserve R1/R4 and original full-state fidelity. No I09 protocol is introduced.

| Finding | Before | Repair/test/commit | Current |
| --- | --- | --- | --- |
| R1 | 7 expected failures (missing DB, post-connect replacement, 3 sidecars, writer lease, foreign root), plus target identity reproduction | test_storage_identity; pre/post/ongoing/backup identity + owned writer lease | RESOLVED; independent final review PASS |
| R2 | 6 expected RETURNING failures: fetchone/fetchmany/fetchall/iteration/close/reuse | test_statement_finalization; cursor finalization/GC guard plus existing commit paths | RESOLVED; independent final review PASS |
| R3 | 4 expected failures: checkpoint/clone combined capacity, one-byte-over admission, retained snapshot accounting | test_backup_admission + state/storage regressions | RESOLVED; independent final review PASS |
| R4 | 3 expected failures: sibling write, new monitor/spawn, pre-launch rejection | test_shared_budget; durable run latch shared across sibling monitors/processes | RESOLVED; independent final review PASS |
| R5 | 9 expected failures: missing/zero/mismatched digest and changed complete runtime facts | test_profile_admission + profile/spec tests, 13 passed | RESOLVED; independent final review PASS |
| R6 | 4 expected failures: post-growth freeze/admission, partial count, active reservation reconciliation | test_live_capacity + limits/paths/analysis/state/workers | RESOLVED; independent final review PASS |
| R7 | 4 expected failures: malformed/exception action retry, continuing worker, client reuse | test_terminal_channel + channel/workers/leakage, 15 passed | RESOLVED; independent final review PASS |
| R8 | 5 expected failures: wrong action, unknown top/nested/private fields, malformed forecast | test_prediction_boundary + contracts/leakage, 14 passed | RESOLVED; independent final review PASS |
| R9 | 5 expected missing completed-fixture launch failures | test_completed_fixture + workers/state/leakage/determinism | RESOLVED; independent final review PASS |
| R10 | 6 expected failures: import function/builtin/assignment aliases and unresolved reachable helper imports | test_dependency_aliases + dependency absence/direction, 11 passed | RESOLVED; independent final review PASS |

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

## Fresh complete review and follow-up repair

Independent reviewer `/root/b10_remediation_review` reviewed the complete canonical-base-to-`4042d2a5bcd3f4f69dc1a4cab45ef1248dc58242` foundation. Its own foundation rerun passed 143, but review found **0 BLOCKER / 4 MAJOR / 2 MINOR / 6 unresolved**. G1/G2 remained NOT PASS. All cases were reproduced in disposable owned storage; the excluded native-open race was not tested or claimed.

| Review ID / original finding | Expected RED | Narrow follow-up commit | Permanent regression / focused GREEN |
| --- | --- | --- | --- |
| F1 / R1 | unsafe pre-connect WAL rejected without terminal latch, 1 failed | `6a09e53754168b6533d40d44a317f1550193e2df` | `test_storage_identity::test_preconnect_mismatch_latches_run_terminal`; 39 storage/fixture/state/statement tests |
| F3 / R9 | completed connection allowed orphan insert, 1 failed | `0d3f5f92312b7de8cb8e4032066ebc2ae970956a` | completed fresh-process probe rejects orphan insert; same 39-test focused run |
| F4 / R9 | malformed same-name table and orphan fixture both admitted, 2 failed | `f0c14ab554fc91ba7836117c57397db325a7c250` | `test_completed_fixture::test_incomplete_v7_table_manifest_cannot_be_completed`; 27 fixture/state/dependency tests |
| F6 / R10 | nested shadow erased importer alias, 3 failed / 1 already passing | `d0029cbe6d87c4294a845f9aa5e05a93da4a83b2` | `test_dependency_aliases::test_nested_shadowing_cannot_erase_importer`; same 27-test run |
| F5 / R6 | 64-byte marker returned beyond root cap, 1 failed / 2 passing boundaries | `12647b6ee5c88c73a504ab6ed6b0cc16152b739a` | `test_live_capacity::test_assignment_marker_preadmitted`, active-reservation case; 13 capacity/limits/path tests |
| F2 / R1,R6 | serialized launch retained complete evaluator-root authority, 1 failed / 2 passing accounting cases | `912b95b95bf696e599ff91ec33e5be638f5a7031` | `test_capability_boundary`; 33 capability/fixture/capacity/worker/leakage/path/limits tests |

F1 separates second-writer lease contention from detected unsafe storage. Contention rejects the extra writer without invalidating the healthy first owner; capability/path/native-open/post-connect failures latch the durable terminal run. F3 restores only the ordinary connection-local producer FK setting. F4 compares actual SQLite schema objects/constraints against an in-memory reference generated from unchanged producer DDL/migrations, checks relational integrity, and never migrates or writes the admitted fixture. F6 conservatively retains possible importer bindings across scopes, with no general static-analysis completeness claim. F5 uses active reservation allowance without double-counting marker bytes.

F2 replaces the full root reference with identity/accounting-only admission. The serialized object graph contains no EvaluationRoot, evaluator plan path/file opener, or learner-slot assignment authority. Reservation registry entries no longer point back to the evaluator Budget/root. Parent capabilities share live accounting; spawn copies those accounting facts, while every validation rescans actual current retained storage. Scientific dispatch remains disabled; no concurrent protocol coordinator or I09+ behavior is introduced.

## Fresh author verification at engineering head 912b95b

Exact head: `912b95b95bf696e599ff91ec33e5be638f5a7031`. Clean source after commits. Commands exited zero:

- `python -m pytest -q tests/evaluation`: **156 passed** (32.50 s).
- `python -m pytest -q`: **1039 passed, 2 existing warnings** (43.25 s): Starlette HTTPX TestClient deprecation and AnyIO BlockingPortal alias deprecation.
- Explicit R1–R10 adversarial modules plus capability boundary: **94 passed** (24.17 s), separately executed after repairs.
- Seven existing `tests.*_scenario` modules: baseline, prediction_error, world_model, curiosity, semantic, self_model, decision — all exit 0, nonempty finite JSON, empty stderr; expected-value assertions also pass in the repository suite. These are technical regressions, not B10 experiments.
- `git diff --check`: PASS. Complete canonical-base diff: 54 authorized files. `seed/**` NONE; schema VERSION 7 unchanged; dependency lock NONE; workflows NONE. All original I01–I08, original review, and canonical amendment master remain exact ancestors.

At this author-verification checkpoint, fresh independent follow-up review/G1/G2 determination remained pending; author test results alone do not resolve the gate. Hosted foundation PR/master CI and separate closure publication have not yet occurred. Terminal Git lacks SSH/HTTPS authentication; publication must preserve original task history and requires a working Git route or explicit owner authority for metadata-only recreation of new remediation commits.


## Independent acceptance and publication gate

Final independent continuation reviewed exact engineering head `912b95b95bf696e599ff91ec33e5be638f5a7031`: **0 BLOCKER / 0 MAJOR / 0 MINOR / 0 unresolved**, R1–R10 RESOLVED, G1 PASS, G2 PASS within foundation scope. Independent suite 156 passed (28.17 s); all six prior adversarial reproductions independently rerun PASS. See [complete final review and concrete G1/G2 map](2026-10-03-b10-foundation-final-review.md). Original complete review and earlier failed/interim evidence remain historical.

| Finding | Primary remediation commit(s), with follow-ups above |
| --- | --- |
| R1 | `1e62e0718b9953ce3d184985d275b8df10e8f7d8`; `cbb3e871b96489665b02b13ecfc0dbc34b60f5af`; `6a09e53754168b6533d40d44a317f1550193e2df`; `912b95b95bf696e599ff91ec33e5be638f5a7031` |
| R2 | `f6fe969eeecd7f7e69b0d1be5093eeb00696bbca`; `ef9c130b2749f17233ff2d7b383fb089b0aadb83` |
| R3 | `9a99384ef3a0def2da9466ce2f034cf8afb8c0f1`; `cbb3e871b96489665b02b13ecfc0dbc34b60f5af` |
| R4 | `1f7901baaaf1c52b8c68141b55eeeee38bb427de` |
| R5 | `401bec4325c75c82a7566ced6cade6d533f43c68` |
| R6 | `ab67b266ed72b2bee8d5930e4cf6893f014338f5`; `12647b6ee5c88c73a504ab6ed6b0cc16152b739a`; `912b95b95bf696e599ff91ec33e5be638f5a7031` |
| R7 | `7fc3a2103820ed11c444205da1974f74eb26ac05` |
| R8 | `62dd4a13be0f15a1916a27703978463efdfa3b70` |
| R9 | `d301438969e0c62c9705ff9e992876718a4ee21b`; `3b4db1f4469ce0895c70eb269fdd5a208ccb1f5e`; `ac77bc965edce38ae9f75eb1b2463499afc8020b`; `4042d2a5bcd3f4f69dc1a4cab45ef1248dc58242`; `0d3f5f92312b7de8cb8e4032066ebc2ae970956a`; `f0c14ab554fc91ba7836117c57397db325a7c250` |
| R10 | `27a6537ccb4fa881277a47d946b30d4e4eaf0b66`; `d0029cbe6d87c4294a845f9aa5e05a93da4a83b2` |

Local acceptance is verified. Foundation publication, exact hosted PR CI, normal merge, exact master CI and separate documentation closure publication remain pending. No I09+ work is permitted.
