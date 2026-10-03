# Independent complete-diff review — B10 I09–I13

Reviewed exact head **6fb1aac95034ba04558e10b7509605fdd35b30fd**, branch `seed-0.2-b10-impl-02-protocols`, against exact canonical base **d0a5da528611af1526723b3ec04f6a86b3d1d1c8**. Initial checkout was clean at that head. Review covered all 19 changed code/test/document files, the authoritative owner instruction, the approved specification/plan, and the owner-selected Option B amendment. A Git archive of the exact head at `/private/tmp/b10-review-head` kept subsequent reproductions independent of author repairs. No source, index, HEAD, branches, installed SEED, or registered experiment was modified/accessed/executed by this reviewer.

## Findings

### R1 — MAJOR — Journal directory replacement still receives SCORE_ACK

**Location:** `development/evaluation/checkpoint.py:100–105` (primary line 104); directory identity is not retained/validated at creation, lines 39–55.

**Trigger:** After journal creation, rename `evaluation/partials/<run_id>` and recreate the original directory with an empty `preupdate.ndjson`. Then ACK a valid first checkpoint. This requires no SQLite interaction or concurrency: the replacement is complete before the next append.

**Observed:** `SCORE_ACK`; `journal.failed == False`; declared journal path remains **0 bytes**, while the renamed directory's original journal receives **2193 bytes**. The file/child checks at line 104 are relative to the retained, now-detached directory descriptor; root validation checks only the evaluation root identity. Thus the application-visible artifact path no longer identifies the acknowledged checkpoint. Replacing evaluation/partials ancestors or replacing a component during durability also needs coverage.

**Impact:** Current-transition learning can proceed after an undetected ordinary artifact identity mismatch, and later publication/inspection of the declared journal path finds no scored evidence. This regresses the application-controlled ordinary-file portion of G1 and invalidates the claimed G3 durability guarantee. This is explicitly within Option B; it is not the excluded hostile same-UID SQLite native-open race.

**Fix:** Retain the expected identities for the entire journal ancestry and validate the live descriptor-relative/no-follow path against them, including the journal inode, before writing and again after flush/fsync before ACK. Any detected mismatch must latch terminal failure; retain the original prefix and do not ACK or reopen a replacement. Add replacement-before-append and replacement-during-fsync regressions for file and each ancestor. No core/schema/native-VFS change is needed.

**Independent evidence:** `/private/tmp/b10-review-journal-repro.py` and `/private/tmp/b10-review-journal-repro.log`.

### R2 — MAJOR — Pre-ACK failure discards the captured attempt and prior action effects

**Location:** `development/evaluation/prequential.py:49–53` (primary line 51); retained collections initialized at line 12.

**Trigger:** A real policy-selected `consolidate` action completes, the actual outcome/B3/checkpoint capture occurs, and the journal flush fails before ACK.

**Observed:** The worker returns `status='failed', acked=False`, its capture contains the actual events through `checkpoint`, and `prior_action_effects.consolidation_runs` contains actual producer **ID 1**, status `completed`, provenance `policy_selected`. The driver returns `INCOMPLETE/STORAGE_INTERRUPTED` but retains **events=[], skipped=[], maintenance=[]** and has no terminal attempt/capture record. It drops the current tuple/attempt, capture boundary, and prior-effect evidence. Only an external test spy retained the worker response in the reproduction.

**Impact:** The driver cannot account for the failed/incomplete checkpoint attempt required by owner instruction §34, or honestly preserve the prior-action evidence required by I10/I12. Keeping the learner DB and a possibly partial journal does not preserve this returned evaluator capture or its join to the attempted transition. Failure classification/no-retry behavior is correct, but failure fidelity is incomplete.

**Fix:** Retain a bounded evaluator-side terminal-attempt record before returning from the unacked failure path, including event key/attempt, actual worker status, channel failure classification, ACK fact, available capture/prior effects, and explicit unconfirmed current updates. Preserve the same terminal record on transport/capture failures where the available facts are narrower, without inventing successful stages. This is a small driver evidence record, not I14+ publication architecture. Add a real prior-action-plus-pre-ACK-failure assertion that the evidence survives `run()`.

**Independent evidence:** `/private/tmp/b10-review-preack-repro.py` and `/private/tmp/b10-review-preack-repro.log`.

### R3 — MINOR — PID scrubbing also hides non-PID raw JSON differences

**Location:** `tests/evaluation/test_adapter_equivalence.py:156`; corresponding overclaim in `docs/evaluation/engineering-gates.md` paragraph beginning “Only genuine process PID fields”.

**Trigger:** Compare raw JSON `{"pid":123,"other":1}` with `{ "other": 1, "pid": 456 }`, using each process's correct PID.

**Observed:** `incidental_pid()` produces equal tables and equal location audits because it reparses and reserializes the entire PID-bearing cell. Whitespace, key order, numeric lexical spelling, and escaping outside the PID value can therefore disappear from the raw comparison.

**Impact:** This is a concrete hole in the exact all-table/raw-JSON parity proof and contradicts the assertion that every other raw byte remains compared. The reproduction does not demonstrate a core semantic mismatch; its severity is MINOR because ordinary values and non-PID-bearing cells remain compared. Nevertheless it must be resolved before claiming the owner-required complete raw-fidelity proof.

**Fix:** Replace only independently validated/audited PID scalar byte spans in the original JSON, preserving all other original bytes. Add oracle poison tests showing that non-PID whitespace/order/number/escape differences remain visible, while only the actual PID difference is admitted. Do not broaden incidental exclusions.

**Independent evidence:** `/private/tmp/b10-review-pid-repro.py` and `/private/tmp/b10-review-pid-repro.log`.

### R4 — MAJOR — Freeze returns a valid fixture despite failed worker cleanup

**Location:** `development/evaluation/worker.py:327–331` (primary line 327); lifecycle interaction at lines 111–113 and 165–167, and `development/evaluation/frozen.py:30`.

**Trigger:** Perform one normal acknowledged training cycle using a launch with `training_count=1`, then call `WorkerHandle.freeze()`.

**Observed:** `freeze()` returns a successfully validated `CompletedFixture`, while `handle.cleanup_status == 'failed'`. `freeze_state()` calls `OwnedState.complete_fixture()`, which closes the shared Memory; the worker's final `core.close()` then calls the original Memory.close(), whose commit fails on that already-closed connection. The finally block reports failed cleanup, but `freeze()` ignores it and accepts the fixture. A real injected cleanup failure could be accepted by the same path.

**Impact:** The I11 mutable-to-frozen handoff falsely accepts a lifecycle that the worker itself classifies as failed, despite the explicit requirement that cleanup failure be accounted for. This is also a normal-path double-close defect, not merely a fault injection. Raw frozen probe immutability remains intact, but protocol lifecycle/failure fidelity is not established.

**Fix:** Resolve evaluator ownership so mutable memory and the organism instance lock close exactly once, then require the worker's successful cleanup receipt before returning a trusted frozen fixture. A failed/unconfirmed close must retain state as incomplete evidence and reject the handoff. Add normal-freeze receipt and genuinely failed-cleanup-during-freeze regressions. Preserve original SeedOrganism/Memory behavior.

**Independent evidence:** `/private/tmp/b10-review-freeze-cleanup-repro.py` and `/private/tmp/b10-review-freeze-cleanup-repro.log`.

## Fresh independent checks

- Exact-base/head `git diff --check`: PASS.
- Critical six-file checkpoint/cycle/frozen/prequential/parity/failure-fidelity suite: **83 passed in 65.66s**, exit 0; `/private/tmp/b10-independent-review-pytest.log`.
- All remaining evaluation tests on the exact-head archive: **156 passed in 23.82s**, exit 0; `/private/tmp/b10-review-preservation-pytest.log`. These two disjoint selections cover all **239** evaluation tests; no individual evaluation test was excluded from the union.
- Exact-head dependency audit: `audit_dependencies(...) == ()`.
- Exact-head `seed.migrations.VERSION == 7`.
- Changed-file inspection confirms no `seed/**`, migrations, dependency/lock files, workflows, API/UI, registered science families, or I14+ infrastructure changes.
- Four independent adversarial reproductions above confirm the findings despite the passing suite.
- Author full-suite/seven-regression logs were inspected, including 1122 tests/two warnings and 239 evaluation tests. Those author runs are corroborating history, not independently rerun full-repository or standalone evidence from this reviewer.
- All reviewer tests/reproductions were technical fixtures in disposable temporary storage. No installed-home access or registered B10 experiment execution occurred.

## Behaviors considered and declined as findings

The following records the reviewed behaviors and why each was not judged defective; it precedes the verdict intentionally.

| Considered behavior | Reason declined |
| --- | --- |
| Native SQLite same-UID open races/custom VFS absence | Owner-approved Option B explicitly excludes that prevention guarantee; R1 is instead an observable ordinary-file directory mismatch. |
| Core cognition/schema/SQL/order changes | Complete changed-file diff contains no `seed/**` change; adapters delegate original methods. No discovered repair requires producer changes or a design amendment. |
| Dependency/workflow additions | None appear in the exact diff; dependency audit reports no prohibited path. |
| Point scoring/unavailable/Brier handling | Exactly four approved point signals, literal numeric absolute errors and Boolean correctness; Brier only genuine probability; explicit unavailable reasons; no invented zero. Validation bounds numeric domains. |
| Constant ACK/truth leakage | Closed acknowledgment validator accepts only the constant token; scores remain parent-side. Dependency/leakage suites pass. No observed evaluator truth reaches learner tables/settings/cognition. |
| Aggregate work on ACK path | Minimal journal uses permitted small identity hashes/point scores; poison checks pass. Final aggregate/digest/index/UI operations are absent from the path. |
| File write/flush/fsync/deadline failures and duplicate frames | Terminal journal latch, no ACK, no current learning, storage/deadline versus protocol classifications pass. The separate ancestry hole is R1. |
| Point-score recomputation during frame verification | Bounded deterministic validation, not aggregation or learner feedback; original B3 is still called once. |
| Original B3 identity and cycle delegation | Retained original B3 reference is called once; the exact original result is returned. Original cycle remains unchanged. |
| Synthetic sensor/wall-time behavior | Synthetic body is installed before constructor; real body/network/subprocess fallback is poisoned. Permitted payload excludes wall_time; controlled logical metadata is local. |
| Candidate/history/Q capture and logical stages | Detached prepare/select evidence is captured before outcome; digest/cutoff and stage 0–4 metadata tests pass. No post-outcome reconstruction was found. |
| Prior reflection/consolidation mutations before ACK | Explicitly allowed original prior-evidence action effects; no current Q/B1/B4/B7 learning without ACK. Losing returned failure evidence is separately R2. |
| Frozen constructor/migrations/recovery/publication | FrozenWorker uses a separate minimal read facade and original pure/read producers; mutable paths are poisoned or denied. No mutable SeedOrganism construction in frozen worker. |
| Frozen SQL authorizer allowances | Read transactions/introspection and bounded connection-local busy_timeout are required by original read paths; no observed stored write bypass. SQL writes/DDL/persistent PRAGMA/publication attempts latch failure. |
| Frozen raw equality/history/actions | Every table, schema, sequence, operational/raw JSON state and required DB bytes remain equal; 200-row cutoff stays fixed; reflect/consolidate are labelled assays with internal effects suppressed. |
| Freeze queue/command/transaction admission | Bounded B4 drain with progress, pending commands/open transaction/incomplete training guards pass. Cleanup handoff is separately R4. |
| Absence of complete registered C/science family execution | I14+ is expressly unauthorized. Technical pre-freeze setup and write prevention are in scope; registered families/scientific conclusions are not required here. |
| Skipped-cycle retry limits and exact 5-second boundary | Core stale rule preserved, no score/current update/second perception when not reached; separate skipped evidence, logical retries and 8/2048 caps pass. |
| Q/B1/B4/B5/B7/B8 confirmation | Actual source IDs/stored rows and producer returns are inspected. Post-commit failures preserve prefixes and do not retry. Prediction/evaluation payloads are stored on transition rows, not separate invented IDs. |
| B6 maintenance suppression and swallowed failures | Every-eight-completed schedule is outside ACK; real owner_requested producer row/status is retained, including resource suppression/failed post-commit maintenance. No unrelated attention behavior is newly enabled. |
| Raw JSON chunk transport | Lossless per-string chunks preserve producer payload bytes without altering source SQL/schema. No aggregate/publication implementation is smuggled into this mechanism. |
| Post-ACK aggregation/index/publication fault fixtures | Explicitly allowed technical fault points; no production I14+ systems or science runs are introduced. Mutations remain and no next cycle/relearning occurs. |
| Parity control shares foundation bootstrap/channel | Required deterministic/isolation scaffolding only; independent body plus original constructor/cycle form the control. It does not call construct_core/SyntheticBody/CaptureSession. |
| Parity forced actions/exploration fixtures | Controlled permitted RNG choices exercise four original actions and maintenance; no copied decision/cognition algorithm. No actual selector semantic mismatch was found. Raw normalization proof gap is R3. |
| PID incidental exclusion | Actual process PID locations are audited on both sides; PID itself is approved incidental. Rewriting other bytes is separately R3. No storage-geometry exclusion is used. |
| Normal SEED evaluation-absent behavior | Copied original source constructs/cycles/persists/closes without evaluation package; no reverse dependency appears. |
| Document status/“I13 commit pending” | Snapshot records author verification and pending independent publication gates rather than claiming completed protocols. Self-referential task commit bookkeeping can be finalized with the gate update/closure. Technical design scope is unchanged. |
| Existing warnings, author historical logs, future CI | Existing warnings are unrelated; author logs are not independent proof; exact PR/master CI remains a later required publication gate. No gate is granted from those counts alone. |

## Gate rulings and verdict

**Counts: 0 BLOCKER / 3 MAJOR / 1 MINOR / 4 UNRESOLVED.**

- **G1 preservation: NOT ESTABLISHED for the protocols diff** until R1 is resolved. Existing foundation application/storage tests pass, but the new ordinary journal path lacks required identity protection.
- **G2 preservation: PASS** within the owner-approved trusted-code contract, based on complete diff, dependency audit and boundary/leakage regressions.
- **G3: FAIL** at this exact head. R1 breaks journal-path durability; R2 loses failed-attempt evidence; R3 weakens the raw parity oracle; R4 accepts failed freeze cleanup. Passing current tests does not override these reproductions.
- **G4: PASS for the defined raw frozen-probe immutability gate.** No attempted or successful probe mutation was found. This does not mark I11 complete: R4 blocks acceptance of the mutable-to-frozen lifecycle handoff.
- **DESIGN AMENDMENT REQUIRED: NO.** All findings admit evaluator/test-only repairs while preserving producer cognition, SQL/schema/order and the Option B scope.
- **Ready to merge / publish protocols PR: NO.** Resolve the four findings, retain RED/repair evidence, rerun affected/foundation/full required verification, and perform fresh exact-repair-head independent review before publication. This report applies only to 6fb1aac95034ba04558e10b7509605fdd35b30fd and does not pre-approve later repairs.
