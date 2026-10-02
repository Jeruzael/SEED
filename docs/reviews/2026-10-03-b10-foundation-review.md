# B10 foundation independent review and storage amendment stop — 2026-10-03

**B10 ENGINEERING IMPLEMENTATION IN PROGRESS / FOUNDATION NOT VERIFIED / DESIGN AMENDMENT REQUIRED.** This is an engineering checkpoint, not a foundation closure or technical design amendment. The approved specification and implementation plan remain unchanged. No PR or merge is authorized while the independent review has unresolved MAJOR findings.

## Starting state and task trace

The owner authorized **I01–I08 only**, from exact clean master `196631baef225fa02983f40ffca22cc26190757d`, verified by master push [run 37019823351](https://github.com/Jeruzael/SEED/actions/runs/37019823351), all three required jobs successful. Exact branch point and local master remain that SHA. Created `seed-0.2-b10-impl-01-foundation` in the owner-selected checkout. The remote branch exists at the base only; implementation commits have not been published.

Approved technical specification: `6cd7504b96dec158bbedbadec4f133150f0e80b9`. Approved technical plan: `ef82df33771661a27c6ced6db65e3aaeb4e5fba5`. The independent review examined base through exact engineering head `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3`; eight task boundaries are preserved.

| Task | Separate local commit | Implemented checkpoint; acceptance outstanding |
| --- | --- | --- |
| I01 | `ea70c41` | Inert contracts/package, fixed registries and bounded JSON; nested prediction needs closure fix R8. |
| I02 | `7e2b072` | Strict specification/AnalysisPlan, typed canonicalization, inventory and durable freeze; root admission R6 remains. |
| I03 | `6d8c446` | Owned roots/capabilities, reservations and AST dependency gate; storage R1, live capacity R6 and graph coverage R10 remain. |
| I04 | `600f0d4` | Worker-scoped pre-import clocks, UUIDs and independent RNG primitives; no production-default change. |
| I05 | `25bfae7` | Clean source/runtime capture and compatibility; declared profile admission R5 remains. |
| I06 | `7f368a0` | Disposable schema-v7 initialization, complete backup/clone and transaction proxy; R1–R4 remain. |
| I07 | `4fb144e` | Fresh spawn, capability-only launch, sanitized environment, deadlines and worker lease; R7/R9 remain. |
| I08 | `1dd7c58` | Closed public channel and parent-private truth fixture; terminal failure R7 remains. ACK/scientific dispatch disabled. |

Every task had named failing tests before implementation, focused tests, relevant regressions and a separate commit. These commits are implemented checkpoints, **not COMPLETE / VERIFIED tasks** after review.

## Independent review

Fresh read-only review: **BLOCKER 0 / MAJOR 9 / MINOR 1** at the exact engineering head. All ten findings remain unresolved in the preserved source tree. No seed/schema/dependency/workflow edits or I09+ scientific dispatcher were found. Narrow reproductions used disposable temporary roots, not installed SEED or registered experiments.

| ID / severity | Finding and demonstrated impact | Required resolution |
| --- | --- | --- |
| R1 MAJOR | `db_adapter.py:167–182`, `state.py:82–120`: safe path/descriptor checks precede a fresh SQLite pathname open. Swapping the checked DB to a symlink before CONNECT made the proxy read a foreign DB. Backup targets also discard safely created descriptors. | Bind database and sidecar opens to validated capabilities before SQLite reads/writes them; storage design decision below. |
| R2 MAJOR | Cursor fetch/close/iteration can finalize autocommit `INSERT ... RETURNING` after the execute-time growth check. Reproduction grew physical state 8192→16384 bytes without an added check or stop. | Guard writer statement finalization and all producer commit paths. |
| R3 MAJOR | Raw checkpoint/clone backup lacks combined workspace admission/enforcement. Checkpoint returned at 134234176 bytes, above 128 MiB, with no stop latch. | Admit full backup allocation and enforce workspace bounds during completion/cleanup. |
| R4 MAJOR | Independent clone monitors permit another committed write after a sibling exceeds the shared run ceiling. | Shared terminal run-budget/latch checked before each writer transaction. |
| R5 MAJOR | require_source ignores ExperimentSpec.profile_digest; all-zero requested digest is accepted. | Canonical complete profile digest comparison at scientific admission before construction; explicitly separate technical fixtures. |
| R6 MAJOR | Freeze/create can bypass an over-cap root; Coordinator reads new usage but retains the first snapshot. | Control-write admission and reconciliation of actual retained usage/outstanding reservations without double counting active runs. |
| R7 MAJOR | An action effect followed by malformed outcome leaves the channel reusable; identical retry caused two scenario calls. Worker continues after contract error. | Terminal FAILED latch, bounded termination and no further dispatch after ambiguous effects. |
| R8 MAJOR | Closed checkpoint prediction accepts an unrestricted dict including a private truth sentinel. | Strict nested public producer prediction schema; no ACK/scoring implementation. |
| R9 MAJOR | Worker always initializes fresh state and cannot launch a completed owned clone in a new spawned process. | Explicit admitted completed-owned-fixture mode, preserving all tables/settings/sequences and process-local independence; no automatic partial resume/frozen protocol. |
| R10 MINOR | Reachable helper aliases/nonliteral dynamic imports evade the dependency audit. Current checked-in graph is clean. | Propagate unresolved imports through protected reachable graphs and resolve aliases. |

A subsequent author reproduction suite confirmed eight red cases, including R2/R4/R5/R6/R7/R8/R10. Two exploratory resource corrections were tested locally but **not committed or retained in source** when the storage audit reached the design stop. Drafts/reproductions are preserved only in the ignored local work ledger. No finding is reported as fixed.

Declined review areas: I09 ACK/crash durability; I10/I13 cycle capture/parity; I11 frozen authorizer/assay; I14+ science; I23+ publication/replay/UI; hostile same-UID sandbox resistance. These exclusions cannot be counted as passed gates. Current truth tests exercise channel and initialized state; they do not establish future cognition-path protocol acceptance.

## Storage audit and design decision required

The [approved plan](../superpowers/plans/2026-10-02-b10-development-evaluation-implementation.md#2-repository-audit-and-core-touch-analysis) proposes a worker-local **SQLite connection/transaction proxy** and zero B1–B8 edits. The [approved specification](../superpowers/specs/2026-10-02-b10-development-evaluation-design.md#20-path-safety-failure-modes-and-adversarial-self-review) requires no-follow, descriptor identity and path-replacement protection. The current proxy cannot establish that guarantee at SQLite's file-open boundary.

Verified external alternatives and their limits:

1. Retain safe file descriptors, connect using the normal pathname, then compare descriptors/inodes before SQL. Rejected as a complete fix: SQLite reads the database header during connection initialization, before Python regains control. Sidecars can also be opened inside later native operations, after a Python-side check. This adds detection but does not prevent the foreign read/write interval. [SQLite B-tree initialization](https://raw.githubusercontent.com/sqlite/sqlite/master/src/btree.c), [CPython SQLite connection initialization](https://raw.githubusercontent.com/python/cpython/3.13/Modules/_sqlite/connection.c).
2. Use a retained file descriptor pathname. A local macOS disposable test confirmed `/dev/fd/N` reads the held DB inode despite original-path replacement, but WAL/writes fail with `attempt to write a readonly database`. `/dev/fd/directory-fd/db` could not open on macOS. This cannot preserve required normal writable/WAL semantics across the matrix.
3. `mode=rw` can prevent accidental creation of a replacement database but cannot prevent foreign header reads. `SQLITE_OPEN_NOFOLLOW` is a native open flag, not a Python sqlite3.connect argument; it alone also does not bind regular-file identity. [SQLite open flags](https://www.sqlite.org/c3ref/open.html), [URI options](https://www.sqlite.org/uri.html).
4. A capability-aware native VFS/open adapter may enforce identity **inside the file-open boundary**, covering main DB, WAL/journal/SHM and cleanup. Read-only inspection found version-3 Unix VFS syscall hooks in the installed macOS SQLite; coverage, lifecycle/ABI safety and Linux/macOS portability are **not verified**. Such a mechanism is a substantive change from the approved Python connection-wrapper approach. No native hook, library installation, dependency or core edit was implemented.

**DESIGN AMENDMENT REQUIRED before further implementation.** This is an implementation-agent conclusion from the verified limits above, not an owner-approved design change and not a claim that every conceivable external adapter is impossible. The reviewer identified no required core edit. Exact required production source modification: **NONE identified or authorized**. Do not alter `seed/memory.py`, migrate schema, replace cognition or weaken protection for convenience.

Recommended next owner review is a **foundation storage design amendment only**: specify and independently audit an external capability-aware file-open mechanism, its supported ABI/runtime facts, database/sidecar/cleanup coverage, fail-closed admission and portable race/WAL/backup tests. Preserve schema v7, normal producer SQL and normal production behavior. If that design cannot remain external with existing dependencies, report the exact core/dependency change and obtain separate authorization before coding. A weaker detection-only promise also needs explicit owner-approved specification amendment; none has been selected here.

Affected acceptance: I03 no-follow/path-replacement admission, I06 safe initialization/backup/clone fidelity, I07 capability-only lifecycle and the storage component of foundation isolation. A foreign DB can supply learner state, so passing the current channel sentinel test does not close storage/truth acceptance. Ordinary SEED behavior remains unchanged because no core or production default was modified.

## Local evidence and incomplete gates

- Baseline: 883 passed, two existing deprecation warnings.
- Exact engineering checkpoint: 62 foundation tests passed; full suite **945 passed, two existing warnings**. This demonstrates the existing test suite result, not review acceptance.
- Seven existing standalone scenarios completed successfully with valid JSON: baseline, prediction error, world model, curiosity, semantic memory, self model and decision. These and disposable producer/worker fixtures are technical validation, not B10 scientific experiments.
- G1 current-source AST/import test and actual ordinary temporary-home construction/cycle with evaluation absent: local tests PASS. R10 gate coverage and storage R1/R6 remain; **final G1 foundation acceptance NOT VERIFIED**.
- G2 current channel/private-sentinel all-file/all-table/settings/meta scans: local tests PASS. R7/R8/R1 and future-path limitations remain; **final G2 foundation acceptance NOT VERIFIED**.
- G3–G7: NOT ATTEMPTED. I09–I30: NOT STARTED / NOT AUTHORIZED BY THIS INSTRUCTION. Empirical evaluation: NOT STARTED / NOT AUTHORIZED. No B10 experiments executed.
- Core-touch: **NONE**. Schema: **v7 unchanged**, no evaluator tables/migration. Dependencies: **no new dependency**. Workflows/APIs/UI unchanged. Installed SEED untouched; no deployment.

## Publication and final state

Foundation PR: **NOT CREATED**. PR head/base: no PR head; intended base remains `196631baef225fa02983f40ffca22cc26190757d`. Remote feature branch is base-only. Foundation PR CI, merge SHA and post-merge master CI: **NOT RUN / NOT MERGED / NOT AVAILABLE**. Starting run 37019823351 is baseline evidence only. The documented local engineering head is preserved; a separate review/bookkeeping commit follows it. No squash or task-history rewrite.

**B10 FOUNDATION I01–I08 NOT COMPLETE / NOT VERIFIED. G1/G2 FINAL ACCEPTANCE PENDING. B10 ENGINEERING IMPLEMENTATION IN PROGRESS / DESIGN AMENDMENT REQUIRED. I09–I30 NOT STARTED / NOT AUTHORIZED BY THIS INSTRUCTION. B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED. NO B10 EXPERIMENTS EXECUTED. INSTALLED SEED UNTOUCHED.** Stop for owner review; no protocol, empirical or next engineering branch created.

## Exact changed-file inventory

The first 37 paths are the engineering diff from the canonical base to the reviewed head. The final three are review/status bookkeeping only; approved specification/plan/protected roadmap/baselines are unchanged.

- `.gitignore`
- `development/__init__.py`
- `development/evaluation/__init__.py`
- `development/evaluation/analysis.py`
- `development/evaluation/bootstrap.py`
- `development/evaluation/canonical.py`
- `development/evaluation/channel.py`
- `development/evaluation/contracts.py`
- `development/evaluation/coordinator.py`
- `development/evaluation/db_adapter.py`
- `development/evaluation/dependency.py`
- `development/evaluation/determinism.py`
- `development/evaluation/limits.py`
- `development/evaluation/paths.py`
- `development/evaluation/profile.py`
- `development/evaluation/registry.py`
- `development/evaluation/scenarios/__init__.py`
- `development/evaluation/scenarios/private.py`
- `development/evaluation/specs.py`
- `development/evaluation/state.py`
- `development/evaluation/worker.py`
- `tests/evaluation/__init__.py`
- `tests/evaluation/conftest.py`
- `tests/evaluation/test_analysis.py`
- `tests/evaluation/test_canonical.py`
- `tests/evaluation/test_channel.py`
- `tests/evaluation/test_contracts.py`
- `tests/evaluation/test_db_adapter.py`
- `tests/evaluation/test_dependency.py`
- `tests/evaluation/test_determinism.py`
- `tests/evaluation/test_leakage.py`
- `tests/evaluation/test_limits.py`
- `tests/evaluation/test_paths.py`
- `tests/evaluation/test_profile.py`
- `tests/evaluation/test_specs.py`
- `tests/evaluation/test_state.py`
- `tests/evaluation/test_workers.py`
- `docs/reviews/2026-10-03-b10-foundation-review.md`
- `docs/seed-0.2-development-plan.md`
- `docs/implementation-log.md`
