# Fresh independent complete-diff review — repaired B10 I09–I13

**Canonical base:** `d0a5da528611af1526723b3ec04f6a86b3d1d1c8`.

**Exact reviewed head:** `2be1e6feb660d81f189098ef62f92631a115631f`, branch `seed-0.2-b10-impl-02-protocols`.

This is a fresh review of the complete canonical-base-to-repaired-head diff, including all **21 changed files**, all protocol code/tests/documentation, the original-cycle/control surfaces, and foundation preservation. It is not an approval inferred from the author's repairs or test counts. The authoritative owner instruction, approved I09–I13 specification/plan, and owner-selected Option B storage amendment remain the acceptance contract.

The checkout was clean at the exact head at review start and final identity check. A Git archive at `/private/tmp/b10-final-review-head` was used for independent tests/reproductions. The reviewer made no checkout/index/ref/source changes, created no agents, accessed no installed SEED, and executed no registered B10 scientific experiment. All additional scripts/logs are outside the checkout in `/private/tmp`.

The initial review at `6fb1aac95034ba04558e10b7509605fdd35b30fd` remains historical and is **byte-identical** to `/private/tmp/b10-protocols-independent-review.md` in `docs/reviews/2026-10-04-b10-protocols-review.md`. Its original failure verdict and unresolved counts were not rewritten.

## Findings

**NONE. Current exact-head counts: 0 BLOCKER / 0 MAJOR / 0 MINOR / 0 UNRESOLVED.**

The four initial findings are independently resolved as follows.

| Initial finding | Exact repaired surface | Independent resolution evidence | Ruling |
| --- | --- | --- | --- |
| R1 MAJOR — detached journal ancestry still ACKed | `development/evaluation/checkpoint.py:53` stores evaluation/partials/run identities; `_validate_storage` at line 120 revalidates every ancestor and the exact file; lines 105/115 validate before write and after fsync | All before/during-fsync file/run/partials/evaluation replacement regressions passed. Additional reviewer matrix replaced **root/evaluation/partials** while retaining the original descendant directory and journal inode, both before append and during fsync: **6 cases rejected ACK and latched terminal failure**. A later identical attempt also rejected. | RESOLVED; G1/G3 protection restored. |
| R2 MAJOR — unacknowledged attempt/prior effects discarded | `development/evaluation/prequential.py:26` retains terminal response plus bounded attempt summary; failure paths call it before returning, and missing response keeps ACK unknown | A real policy-selected consolidate followed by injected flush failure retained actual producer **consolidation ID 1**, the exact events through checkpoint, tuple `measured/default/1/pre`, attempt 1, `INCOMPLETE/STORAGE_INTERRUPTED`, `acked=False`, and a **12129-byte** worker capture. No next cycle, current update, or fake completed event occurred. Additional unavailable-response probe with checkpoint bytes present retained `acked=null`, capture unavailable, exact attempt, and no invented update. | RESOLVED; failed-attempt evidence survives `run()`. |
| R3 MINOR — PID normalization hid non-PID raw JSON spelling | `tests/evaluation/test_adapter_equivalence.py:156–168` validates decoded actual-PID locations, then replaces only corresponding scalar spans in the original text | Actual PID-only differences compare equal; reviewer poison cases for non-PID whitespace, key order, numeric spelling and string escaping remain unequal. All original-cycle parity cases and the new poison regressions passed. No broader incidental/storage-geometry exclusion is used. | RESOLVED; raw lexical fidelity preserved outside audited PID spans. |
| R4 MAJOR — freeze double-close/failed cleanup accepted | `development/evaluation/state.py:178` delegates fixture completion to original core close; `frozen.py:30` forwards ownership; `worker.py:112` uses core owner and `worker.py:328` requires closed receipt | Original real one-training-cycle reproduction now returns a validated fixture with **cleanup_status='closed'**. Original core close owns both Memory and instance lock; its idempotent final call does not re-close Memory. Actual failed-close-during-freeze test rejects fixture acceptance, reports failed cleanup/INCOMPLETE, and preserves the checkpoint and committed training row. Foundation completed-fixture/backup tests also passed. | RESOLVED; ordinary close ownership and failed handoff are truthful. |

No repair modifies original cognition, producer SQL/schema, B3, reward/Q, action behavior or the ordering in `SeedOrganism.cycle()`. No design amendment is required.

## Independent verification

1. **Complete evaluation suite:** independently ran all evaluation tests without exclusions on the exact-head archive:

   `PYTHONDONTWRITEBYTECODE=1 <workspace .venv>/bin/python -m pytest -q -p no:cacheprovider tests/evaluation --basetemp=/private/tmp/b10-final-review-pytest`

   **257 passed in 91.48s; exit 0.** Log: `/private/tmp/b10-final-review-pytest.log`.

   This includes the full checkpoint/B3/cycle/frozen/prequential/parity/failure ladder, all 18 repair regressions, and foundation capability/storage/backup/budget/channel/leakage/dependency tests. It independently exercises normal and failed freeze cleanup, malformed/duplicate/partial durability, genuine producer post-commit failures, swallowed B7/B6 failures, no-retry prefix capture, raw frozen equality and evaluation-absent original control.

2. **Additional reviewer probes:** `/private/tmp/b10-final-independent-unit-probes.py` and `.log`: six ancestor replacement cases preserving descendant/file identity, six PID/lexical checks, and unknown-response terminal evidence. All passed against the exact-head archive. These are additional to checked-in regressions.

3. **Actual prior-action/pre-ACK failure reproduction:** `/private/tmp/b10-final-preack-probe.py` and `.log`: real original-cycle consolidate, flush failure, actual returned capture and producer row inspected, then retained bounded driver evidence asserted. Passed; terminal summary <=512 bytes, capture 12129 bytes <=64 KiB, only one cycle attempt.

4. **Original normal freeze reproduction rerun:** `/private/tmp/b10-review-freeze-cleanup-repro.py` against the repaired archive; `/private/tmp/b10-final-freeze-probe.log` records completed training, validated fixture and `cleanup_status=closed`.

5. **Complete exact-base/head diff hygiene:** `git diff --check` passed; changed-file set inspected. `git status --short` was empty and HEAD/branch remained exact throughout review.

6. **Foundation direction/schema:** fresh `audit_dependencies('/private/tmp/b10-final-review-head') == ()`; `seed.migrations.VERSION == 7`. Exact diff for `seed/**`, dependency/lock files and `.github` is empty. Existing original producers remain authoritative; no evaluator table/migration exists.

7. **Historical review preservation:** `cmp` confirmed the checked-in initial review equals the original report bytes.

8. **Author evidence inspected separately:** post-review logs record 1140 full-suite tests/two existing warnings, 257 evaluation tests, 101 separately selected critical tests and seven standalone regression artifacts. These are corroborating author verification. This reviewer independently ran the complete evaluation suite and probes above; the full repository suite and standalone scripts were not rerun by this reviewer, and their author counts were not substituted for independent gate analysis.

## Complete protocol assessment

**I09:** The point vector remains exactly the four approved signals with finite bounded literal losses, Boolean correctness and genuine-probability-only Brier (`.75/False -> .5625`). Unavailable evidence remains explicit, never zero. Closed evidence/header/component/frame bounds and tuple order are checked before write. The journal is precreated/directory-synced and parent-owned. Append/flush/fsync and post-durability identity checks precede constant ACK. Protocol failures are FAILED; storage/deadline failures are INCOMPLETE. The terminal latch forbids retry/ACK after any failed durability. No aggregates, baselines, utility, publication, final digests, indexes or UI run on the ACK path.

**I10:** Synthetic Body is bound before original mutable construction; host sensing and fallback are blocked. Actual unchanged cycle owns decision preparation, selection, action effects and normal second perception. Detached candidate/history/Q/selection evidence precedes outcome. B3 wrapper retains and invokes the original exactly once and returns its same result object after ACK. Prior reflect/consolidate effects remain legitimate; current transition Q/B1/B4/B7 cannot proceed without ACK. Logical stages remain deterministic and are tied to delegated boundaries.

**I11:** Freeze rejects incomplete training, pending commands/open transaction/nonprogressing pending B4 work, performs the owned checkpoint, closes through the original owner, and requires successful cleanup before admitting its manifest. The separate frozen worker constructs pure/read components over a minimal facade, not a mutable organism. Immutable read-only SQLite/query-only/authorizer protections deny stored mutations. All-table/schema/sqlite_sequence/operational/raw JSON and DB-byte comparisons pass; held-out observations never append history, the 200-row cutoff remains fixed, and reflect/consolidate are explicitly labelled frozen assays with internal mutation suppressed. The source is preserved after failed writes/cleanup.

**I12:** Online driver invokes the actual cycle and captures actual persisted rows/source IDs and producer returns. A returned Python call alone is not success. Confirmed/unconfirmed post-ACK prefixes remain, without rollback/retry/double-learning. Skipped attempts remain non-samples, advance logical retry time, preserve the exact >5s/5.0s core boundary, and stop at 8 consecutive/2048 total attempts. Every-eight-completed maintenance occurs after scored completion, retains actual owner_requested producer status/opportunities, and remains outside ACK. Failed/unavailable attempts now have bounded truthful terminal evidence. Cleanup failure remains explicit.

**I13:** The control independently binds a test body before the original constructor and invokes the original cycle; it does not call construct_core/SyntheticBody/CaptureSession. Both paths use equivalent initial rows/settings/RNG/perceptions/logical stages. Four original actions and eight-cycle maintenance compare actual outputs and all raw tables/IDs/producer payloads; only actual audited PID scalar locations differ. Exact raw JSON outside those spans is preserved. The full before-/after-ACK failure ladder and ordinary evaluation-absent control pass. No duplicated cognition was introduced.

**Scope/foundation:** Only I09–I13 engineering/technical evidence is present. One-way dependencies, assigned evaluator-owned state, ordinary artifact identity checks, native SQLite pre/post/ongoing/backup protections, single trusted writer, shared terminal resource latch and truth separation remain in scope and tested. No installed-home fallback, deployment, new dependency/workflow, I14+ registered scenarios/metrics/artifact architecture/replay/UI, or B10 scientific experiment execution appears in this diff.

## Explicit considered-and-declined behavior rulings

The following lists the behaviors considered but not judged defective, with reasons. It precedes the gate verdict.

| Behavior considered | Why declined as a finding |
| --- | --- |
| Native same-UID SQLite open race / no custom VFS | Owner-approved Option B explicitly excludes prevention of that native interval. Required observed identity/type/capability mismatch detection remains enforced; ordinary journal paths are protected separately. |
| Mutable producer cognition/SQL/schema/order | Complete diff leaves `seed/**` unchanged; adapters forward original methods and compare against original cycle. Repairs are evaluator-only. |
| Dependency/lock/workflow changes | Exact diff is empty for these surfaces; dependency audit passes. |
| Numeric/Boolean unavailable scoring | Closed approved domains/statuses/reasons; no invented zero and no support-confidence Brier. Literal tests pass. |
| Frame score recomputation/small hashes | Bounded deterministic validation/approved identity hashes, not aggregate science or learner feedback. |
| Aggregate ACK work/truth-bearing ACK | Poison and closed-channel checks pass; only SCORE_ACK crosses to learner. Scores/private truth remain parent-side. |
| Partial/flush/fsync/deadline/duplicate failures | No ACK/current learning; terminal latch and explicit protocol/storage classification. Partial original evidence is retained. |
| Journal ancestor replacement retaining child inode | Repaired full ancestry checks reject both before and after fsync, even when the leaf file and descendant identity survive; independently reproduced. |
| Arbitrary continuous malicious same-UID code undoing filesystem mutations around checks | Outside the trusted checked-in-code/OS-sandbox promise. No ordinary observed mismatch is excused; no race-proof claim is made. |
| Synthetic observation wall time/host paths | Wire payload is allowlisted; wall time is controlled local metadata. Body/network/subprocess fallback poisoned before construction. |
| Original B3 wrapper identity | Calls retained original exactly once and returns the same original result; no replacement error implementation. |
| Candidate/history/Q provenance | Detached original prepare/select evidence before outcome; selected digest/cutoff and deterministic stages pass. |
| Prior reflect/consolidate effects before checkpoint | Existing prior-evidence action behavior is expressly legitimate, including after missing ACK. Failure capture now preserves actual consolidation evidence. |
| Freeze source closure / shared Memory ownership | Original core close owns Memory and lock; callback avoids previous premature Memory close. Successful receipt is required; failed close does not admit a fixture. |
| Frozen facade/transaction/introspection/busy_timeout allowances | Required by original read paths; connection-local operations do not change stored bytes. Write/DDL/persistent PRAGMA/publication attempts fail and latch. |
| Frozen history/cache/action labels | No held-out row insertion or evidence accumulation; raw equality/fixed 200 cutoff pass. Reflect/consolidate are labelled projections rather than normal mutation claims. |
| Frozen pending commands/queue/open transactions | Explicit guard plus bounded progress drain; incomplete work does not become a trusted frozen fixture. |
| Absent registered C variants/full scientific suite | I14+ is not authorized. Technical pre-freeze setup/read/write protections are tested without registered experiment dispatch. |
| Skipped retry scheduling / exact 5-second boundary | Core semantics remain authority; skipped attempts are not scored/completed, retry caps and logical schedule pass. |
| Q/B1/B4/B5/B7/B8 success confirmation | Actual visits, transition/episode/source IDs, persisted producer rows and returns are captured. Prediction/evaluation payloads are on actual transition rows, not separate invented IDs. |
| Swallowed producer errors and post-commit exceptions | Actual stored prefixes/returns determine confirmation; failure ladder passes without rollback/relearning/next-cycle dispatch. |
| B6 maintenance resource suppression | Actual producer opportunity/run/status retained, every eighth completion outside ACK, genuine owner_requested provenance. No new attention feature is enabled. |
| Failed/unavailable response capture | One bounded terminal response/summary retains only actual available facts; absent response leaves ACK null and capture unavailable. No fabricated producer confirmation. |
| Raw JSON chunk strings | Lossless bounded transport; source producer payload/SQL unchanged. It adds no registered artifact publishing/science machinery. |
| Terminal capture stores a bounded returned response alongside journal | Required technical failure evidence; one terminal record, not duplicated published scientific payloads or an I14+ artifact system. Existing completed detail bound remains enforced. |
| Cleanup status after already-recorded failure | Driver returns explicit cleanup interruption while preserving original captured failure facts; it does not convert that run to success or retry. |
| Shared bootstrap/channel in parity control | Isolation/determinism scaffolding; independently constructed body/original constructor/cycle remain the oracle. No cognition reimplementation. |
| Forced original actions/exploration parity fixtures | Valid controlled RNG tests exercise original four-action behavior and maintenance; unchanged selector is called. No observed algorithm mismatch or tuning. |
| PID regex lexical handling | Audited actual numeric/null PID scalar spans only, with original text elsewhere retained. Unsupported encodings/count mismatches fail assertions instead of silently widening exclusions. Lexical poison checks pass. |
| Incidental storage geometry/PID exclusion | Only actual audited PID locations used; no geometry exclusion needed or introduced. |
| Evaluation-absent normal SEED | Copied original source constructs, cycles, persists, closes without evaluation package; no reverse dependency. |
| External aggregation/index/publication fault fixtures | Explicitly authorized technical failure probes; no production I14+ infrastructure or scientific conclusions. |
| Initial report retains negative verdict | Required historical evidence, clearly bound to original head; current gate record distinguishes repairs and pending final review. Byte identity verified. |
| Current documents still say independent gate/publication pending | Accurate at the reviewed snapshot; they do not claim PR/hosted CI/merge/closure completion. This new report supplies a separate exact-head verdict. |
| Existing warnings/author broad verification | Existing warnings are unrelated. Author logs were inspected, but independent suite/probes and code reasoning—not author counts—establish this review's findings/gates. |
| Future exact PR/master CI/closure | Later publication requirements, not defects in this engineering diff; no baseline or local result substitutes for them. |

## Gate verdict

**Final current-head counts: 0 BLOCKER / 0 MAJOR / 0 MINOR / 0 UNRESOLVED — NONE.** Initial R1–R4 are all **RESOLVED**; their historical severities/failed-head evidence remain intact.

- **G1 PASS — preserved**, within the owner-approved trusted-code storage contract. The new journal ordinary-file ancestry mismatch gap is repaired and independently tested; existing capability/SQLite/growth/backup/single-writer protections pass.
- **G2 PASS — preserved.** Closed channel, parent-only scoring/truth, learner storage isolation and dependency direction are intact.
- **G3 PASS.** Durable score-before-current-learning, constant ACK, original B3/cycle parity, exact non-PID raw producer fidelity, and full prefix/attempt/maintenance/cleanup failure fidelity are demonstrated at the exact reviewed head.
- **G4 PASS.** Separate frozen read path cannot mutate stored learner state; complete raw equality and fixed history pass, assay claims are explicit, and mutable-to-frozen cleanup handoff now correctly admits only successfully closed state.
- **DESIGN AMENDMENT REQUIRED: NO.** No original cognition/schema/SQL/order change is needed or present.
- **Independent review verdict: APPROVED / ELIGIBLE TO PUBLISH THE PROTOCOLS PR.** No unresolved code-review finding blocks merge. Actual repository merge must still satisfy the separately required exact PR-head hosted CI and gated publication process; this report does not claim those future gates, merge, post-merge master CI or documentation closure have happened.

This verdict applies only to canonical base `d0a5da528611af1526723b3ec04f6a86b3d1d1c8` through exact head `2be1e6feb660d81f189098ef62f92631a115631f`. It authorizes no I14–I30/I31 science infrastructure/execution, installed-device work, deployment or later unreviewed engineering.
