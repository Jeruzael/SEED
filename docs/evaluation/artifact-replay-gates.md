# B10 I21–I25 artifacts, integrity, replay and re-execution engineering gates — 2026-10-11

Branch `seed-0.2-b10-impl-04-artifacts` starts at verified clean local/remote master `2940fae9fdd084a3e7017a230f531df97a57515f` (science closure PR #28 normal merge; final closure-master CI [38131113558](https://github.com/Jeruzael/SEED/actions/runs/38131113558) passed all three required jobs: linux-py311 `114445469871`, linux-py313 `114445469844`, macos-py313 `114445469681`). Owner authorizes I14–I30 engineering sequentially; this branch covers I21–I25 only. I26–I30 not started; I31 NOT AUTHORIZED. Technical fixtures below are not empirical B10 experiments. Registered dispatch remains disabled.

Starting gates: I01–I08 COMPLETE / VERIFIED, G1 PASS, G2 PASS; I09–I13 COMPLETE / VERIFIED, G3 PASS, G4 PASS; I14–I20 COMPLETE / VERIFIED / CLOSED, G5 PASS.

Protected scope for the whole phase: `seed/**` NONE expected; schema v7 unchanged; dependency lock unchanged; new external dependencies NONE; workflow changes NONE; installed SEED untouched.

## Task record

| Task | Evidence and separate commit |
| --- | --- |
| I21 | artifacts.py, indexes.py; test_artifacts.py 5 passed (journal reused in place with sha256/evidence-digest join and no raw prediction/outcome duplication; combined journal+event detail 64 KiB and per-file/control caps rejected before completion; post-ACK assembly failure leaves journal byte-identical and writes an honest INCOMPLETE pending manifest; partial inventory preserves failure block and synthesizes UNAVAILABLE rows for every unproduced registered measurement; checkpoint snapshots inventoried with sha256, SQLite header and no WAL/SHM). Run record staged as sibling `partials/<run-id>.record.json`; payload stays `publication: pending` until I22/I23. RED: 5 failed (foundation behavior missing: artifacts); GREEN: 5 passed; adjacent checkpoint/analysis/paths/limits 52 passed. | 316aee6595828ad32dcd721eec75f92f02a87caa |
| I22 | science.py, canonical.py canonical_stream; test_science.py 4 passed (producer-shaped all-table projection incl sqlite_sequence, sorted tables, PK ordering, rogue-table compatibility failure; exact incidental projection pid→incidental_pid, B7 storage page_size/page_count/logical_allocated_bytes→incidental_storage, run_id→incidental_run_id, logical fields preserved; digest cases: changed joined outcome changes digest, operational prose and storage run ID do not, deterministic recomputation, streaming sections). Domain SEED_B10_SCIENCE_V1\0 over canonical_bytes sections; science joins journal+post-ACK into one transition per tuple. | 8135ad6b3bae0bc86316301b6c2582e3cfb04724 |
| I23 | integrity.py; artifacts.read_run_record receipts fallback; test_integrity.py 3 passed (integrity distinct from science: operational prose changes integrity only, changed outcome changes both; inventory attacks: modified/missing/extra/symlink all fail verify_receipt, payload+receipt rewrite limitation recorded as a different self-consistent digest, never authenticity; crash ladder: rename crash leaves staged partial unexposed, receipt crash leaves unindexed unreceipted run directory, republish refused/no overwrite). Publication order: finalize science digest into manifest, rebuild chunks, fsync tree, atomic rename partials->runs, detached receipt (<=16 KiB, includes chunks.json hash), record relocation, bounded runs-index (<=60) last. | d29b06a66cda1eca8788ee9516e50ea778e1de01 |
| I24 | reader.py, replay.py; test_reader.py + test_replay.py 5 passed (replay joins stored journal/post-ACK records only -- Predictor/DecisionSystem/WorldModel poisoned without effect, stored prediction/action/outcome presented verbatim; chunk reads verified against receipt-bound chunks.json with scope/budget limits and unsafe ids refused; lossless paging with reused ordinals across phases via full EventKey and opaque cursors; forged cursor, missing receipt (RECEIPT_UNAVAILABLE), stale inode/mtime fingerprint downgrade to verification_pending, read-only SQLite snapshot inspection with write-denying authorizer and 100k VM step budget). Verification labels are scoped: whole_payload_verified_at_publication is never presented as a fresh full verification. | df0b0da043c4006c942efcd6e8de1422711ff9c7 |
| I25 | reexecution.py, cli.py, __main__.py; reader.detail now carries bounded measurements for descriptive comparison; test_reexecution.py + test_cli.py + test_comparison.py 7 passed (same-profile fresh run matches canonical science with new run ID/receipt and original bytes unchanged; incompatible source/lock/schema/dirty profiles refused as INCOMPATIBLE_REEXECUTION; protocol mismatch blocked despite matching plan digest -- compatibility is 14-dimension, not plan-digest-only; bounded earliest divergence with phase/subcase/ordinal/field/expected/actual, <=100 differences, <=64 KiB; CLI verbs validate/verify/replay work on opaque run IDs only, run/suite/reexecute return EMPIRICAL_DISPATCH_DISABLED under the I30 + separate empirical authorization lock, arbitrary paths/code rejected; compare() is DESCRIPTIVE_ONLY and invents no improved/worse classification). Fresh re-execution constructs a new owned run from the original recorded inputs (durable journal, run record, frozen plan) through the same assemble/finalize/publish pipeline; it never executes artifact-contained code and never touches the original. | 1b6463a7f18e516aedefba76941eab0199770068 |

RED/repair evidence for each task is retained in ignored `.superpowers/b10-artifacts/` and summarized here at each task commit.

## Final author verification (2026-10-11, at ea65163)

| Check | Result |
| --- | --- |
| Focused I21–I25 + adversarial suites | 29 passed |
| Complete evaluation suite | 581 passed in 381.84s |
| Full repository | 1,464 passed, 2 existing warnings, in 415.16s |
| Seven standalone regressions (baseline, prediction_error, world_model, curiosity, semantic, self_model, decision) | All PASS, valid JSON |
| Protected scope (seed/**, schema, lock, workflows) | NONE changed in 2940fae..ea65163 |

Branch pushed to origin at ea65163ba5c1541e98072e8e4342251e34bbb619 without merge or PR, per owner instruction. Fresh independent complete-diff review and G6 remain pending.

## Owner independent-review remediation (2026-10-11)

The owner's independent source inspection of the published head raised five
deeper findings beyond the first review cycle. Each was reproduced RED
before repair (tests/evaluation/test_remediation.py; RED log preserved in
the working records):

- **F1 (MAJOR)** — re-execution never executed: it rebuilt envelopes from
  stored rows, so a tampered stored prediction re-executed to `matched`.
  Repaired in efb00f4: genuine disposable-worker re-execution
  (`PrequentialDriver` + `ChannelRouter` + real organism) from the
  recorded execution inputs only; stored rows are never read; only fresh
  organism evidence is staged/assembled/finalized/published; incompatible
  records (driver-mismatched journals, declared checkpoints, tampered
  execution blocks) fail closed with INCOMPATIBLE_REEXECUTION; non-COMPLETED
  fresh executions stage a partial and report INCOMPLETE_COMPARISON.
- **F2 (MAJOR)** — scientific outputs were trusted, not derived. Repaired
  in 90ee816: assembly re-derives every registered measurement and finding
  from journal evidence via the I14–I20 metric code and rejects any
  supplied row that differs; COMPLETED runs must supply the full derived
  set; underived rows on non-COMPLETED runs become UNAVAILABLE stamped
  with the run's own reason, or `not_produced` when the run has none.
- **F3 (MAJOR)** — reader pages scanned the whole event history per page.
  Repaired in f1c81f5/b8426ac/e8c6f9b: streamed byte-offset replay index,
  fingerprint-cached by the reader; page reads are windowed with
  incremental byte/deadline budgets; the generic event join stays strict
  and is no longer used for paging.
- **F4 (MAJOR)** — replay silently dropped non-point-update stages, skipped
  attempts and duplicate-digest rows. Same commits: the row inventory is
  lossless — journal frames in journal order, then unbound event lines
  (every stage, skipped attempt, duplicate) in file order, each exactly
  once.
- **F5 (MAJOR)** — no storage-budget admission. Repaired in 90ee816:
  assembly estimates payload bytes and requires budget capacity before
  canonicalization; publish re-requires capacity at the commit boundary,
  with the budget reconciled from on-disk usage including crash-retained
  state.

Follow-on repair 9530e14 moved shared artifact IO into the leaf module
`artifact_io.py` after the F2 derivation imports broke the reader
dependency boundary (`reader → replay → integrity → artifacts →
metrics.producers → scenarios`); 241096d repointed one cap-monkeypatch
test at the leaf module.

## Remediation verification (author side, at 241096d)

- RED evidence: all five findings reproduced before repair; the
  regression tests live in tests/evaluation/test_remediation.py and fail
  on the pre-remediation head, pass after.
- Focused evaluation sets (artifacts, integrity, replay, comparison,
  reader, reexecution, CLI, remediation, dependency audit): green.
- Complete evaluation suite and full repository suite: full repository
  1,482 passed / 2 warnings at 241096d. Two earlier contaminated runs are
  recorded honestly: one filled the 512 MB tmpfs /tmp with test
  scratch (121 disk-full errors in unrelated root tests); one ran with
  TMPDIR on slow overlay disk and produced timing flakes in
  worker/state/frozen/scenario tests — the same flakes reproduce at the
  pre-remediation head under the same conditions and vanish on tmpfs.
- All seven standalone scenarios PASS.
- G6 remains for the fresh independent complete-diff review; this ledger
  entry is author-side evidence only.

## G6 acceptance (fresh independent complete-diff review, 2026-10-11)

- Reviewed head `8fa069c` (engineering code `241096d`), tree materialized
  independently via `git archive`; complete diff `2940fae..8fa069c`.
- Verdict: BLOCKER 0 / MAJOR 0 / MINOR 1 (documentation) / UNRESOLVED 0;
  the single MINOR was this ledger's `not_produced` wording, corrected in
  `b4c7b3d`, after which the branch stands at 0 / 0 / 0 / 0.
- F1–F5 each verified HOLDS under reviewer-written adversarial probes
  (21 probes passed), including a fully rebound forgery of a stored
  outcome, which genuine re-execution catches as SCIENTIFIC_DIVERGENCE.
- Independent evaluation suite: 599 passed. Standalone scenarios: 7/7.
  Author-side full repository suite at `241096d`: 1,482 passed.
- G1–G5 PRESERVED. **G6 PASS.**
- Review record: docs/reviews/2026-10-11-b10-artifacts-review.md.
- Per the owner's instruction, no PR was opened and nothing was merged;
  PR publication, PR-head CI, merge and post-merge master CI remain
  separate owner-gated steps. I31 remains NOT AUTHORIZED.

## Final remediation A–D (owner instruction, 2026-10-11)

Four remaining independent-review concerns, each handled test-first with
its own commit; RED logs preserved in the working records.

- **A — re-execution fidelity (MAJOR), `e107b75`.** The recorded-scenario
  outcome server is gone. Re-execution resolves the registered scenario
  engine (stationary-action-v2 / constrained-v1 / rest-shift-v2 /
  evidence-v1) from the run's recorded truth and requires the truth to
  equal the engine's own evaluator view exactly; missing or mismatched
  scenario definitions are INCOMPATIBLE. The fresh learner acts through
  the ordinary driver/channel and the engine computes outcomes for the
  freshly selected actions; divergences are preserved, never forced.
  Declared initial checkpoints are supported through the approved
  completed-fixture launch pathway: the checkpoint bytes are validated
  (descriptor-relative read, manifest digest, state projection) and seed
  a `COMPLETED_OWNED_FIXTURE` launch; corrupt or undeclared checkpoints
  are incompatible. (Narrow follow-up `MINOR-1/MINOR-2` fixes: the
  compatibility report's initial-state check now reads the checkpoint
  through the same descriptor-safe validated helper instead of a plain
  path read, and re-execution stages the fresh journal/checkpoint copy
  only after a budget admission covering those bytes plus the run slot;
  regression tests in tests/evaluation/test_review_minors.py.) The disposable root now lives in the target root's
  owned `work/` area under budget admission and is destroyed afterwards;
  no external temp root is allocated. RED evidence: against the prior
  implementation the fresh-action, missing-scenario and checkpoint
  fidelity tests fail (tampered outcomes re-executed to a match).
- **B — complete replay budget enforcement (MAJOR), `021aa93` +
  `b6acf18`.** The replay index is incremental and resumable: every
  physical byte pulled while indexing is charged to the request's
  existing 1 MiB / 2 s budget (reader `_tick`), as are row line reads;
  a request that exhausts its budget during indexing fails with an
  explicit bounded error and the partial index retains progress in the
  reader cache for the next request. Rows are served only from a
  complete index; the single-record escape is preserved.
- **C — admission before initial staging (MAJOR), `d07c9c4`.**
  `write_run_record` charges the run slot + peak record bytes before
  creating the run directory or temp file; journal creation charges the
  run slot before mkdir; every payload-file write, the detached receipt
  and the runs-index update are admitted against current on-disk usage
  before allocation. Renames are not double-charged; crash-retained
  partials count through the existing reconciliation.
- **D — checkpoint descriptor traversal (BLOCKER concern), `60ec70f`.**
  Reproduced at the open level: a staged `checkpoints` symlink made the
  assembly read foreign bytes. Nested artifact opens on the assembly,
  integrity and reader paths now walk descriptor-relatively
  (`paths._open_nested`): every intermediate directory is opened
  O_NOFOLLOW and validated, components are strictly checked, and
  descriptors close on every path. Applied to staged reads/writes,
  integrity payload reads and fsync, and snapshot inspection (with
  pre/post identity checks around SQLite's native open, per the Option
  B exception). The one plain-path checkpoint read the independent
  review later found in the re-execution compatibility report was
  routed through the same validated helper in the MINOR-1 follow-up
  above.

Author verification at the final HEAD is recorded in the entry below
after the serial runs complete; G6 acceptance remains for the fresh
independent complete-diff review.

## Final remediation verification (author side, at 279c54f)

Run serially against the clean final HEAD `279c54f` (engineering code
`e107b75` plus docs/style follow-ups):

- Focused sets (remediation, admission, checkpoint paths, replay
  budget, re-execution fidelity, artifacts, integrity, reader, replay,
  comparison, CLI, science, dependency): green at each remediation
  commit and in the final focused pass.
- Complete evaluation suite: **622 passed** (188 s).
- Full repository suite: **1,505 passed, 2 warnings** (214 s).
- Seven standalone scenarios (baseline, prediction_error, world_model,
  curiosity, semantic, self_model, decision): **7/7 PASS**.
- `compileall` on development/evaluation: OK. `git diff --check`
  2940fae..HEAD: OK. Protected paths (`seed/**`, dependencies/lock,
  workflows): **no changes**.
- One earlier evaluation run at `01ca123` was interrupted at ~92% by a
  service restart and is not counted; the runs above are the evidence
  for this HEAD.

G6 acceptance remains for the fresh independent complete-diff review.

## Independent review of remediation A–D and MINOR follow-ups

The fresh independent complete-diff review at `98cab3b` (independent
tree; evaluation suite 622 passed; 22 reviewer probes) verified A–D
HOLD on all named surfaces and F1–F5 unregressed, with verdict
0 BLOCKER / 0 MAJOR / 2 MINOR / 0 UNRESOLVED — both MINORs in
re-execution secondary paths (compatibility-report checkpoint read;
re-execution staging admission), reproduced above and fixed in the
follow-up commit with regression tests RED against the pre-fix code.
A narrow independent re-review of those two fixes follows; G6 is
recorded only from that re-review.

## Final acceptance

The narrow independent re-review at `377f39a` closed both MINORs with
discriminating probes (fail at `98cab3b`, pass at `377f39a`) and
confirmed no scope creep. Final acceptance for I21–I25:

```text
BLOCKER 0
MAJOR 0
MINOR 0
UNRESOLVED 0

G1 PASS
G2 PASS
G3 PASS
G4 PASS
G5 PASS
G6 PASS

DESIGN AMENDMENT REQUIRED: NO
```

Review record: docs/reviews/2026-10-11-b10-artifacts-final-remediation-review.md.
Publication (PR, PR-head CI, merge, post-merge master CI, closure)
remains owner-gated and has not been performed. I31 remains
NOT AUTHORIZED.
