# B10 I21–I25 Independent Review — Artifacts, Integrity, Replay, Re-execution

- Branch: `seed-0.2-b10-impl-04-artifacts`; base `2940fae`; reviewed head
  `8fa069c` (engineering code `241096d`).
- Method: fresh independent reviewer, tree materialized via `git archive`
  (not the author's working tree); complete diff `2940fae..8fa069c`
  reviewed (26 files, +3,766/−8); complete evaluation suite run from the
  independent tree; 21 reviewer-written adversarial probes; seven
  standalone scenarios. This review followed two repair cycles: the first
  independent cycle (18 findings + 2, all resolved and re-verified at
  `0b8c0e9`/`a53f7b2`) and the owner's independent-review remediation
  F1–F5 (`90ee816`, `f1c81f5`, `b8426ac`, `e8c6f9b`, `efb00f4`, `9530e14`,
  `241096d`), each reproduced RED before repair.

## Verdict

**BLOCKER 0 · MAJOR 0 · MINOR 1 (documentation, corrected in `b4c7b3d`) ·
UNRESOLVED 0.** After the one-line ledger correction the branch stands at
**0 / 0 / 0 / 0**. G1–G5 preserved; **G6 PASS**.

## Per-claim results (owner findings F1–F5)

- **F1 genuine re-execution — HOLDS.** Disposable worker + driver +
  organism executed from the record's execution block only; stored rows
  never read for the comparison target. Reviewer probes: genuine run
  matched; naive stored tampering fails closed; the strongest forgery
  (tampered `state_after` with recomputed header digests and rebound
  events) yields SCIENTIFIC_DIVERGENCE (earliest difference
  `point_scores.battery_pct.absolute_error` 0.0 vs 47.0); tampered
  measurement row divergent; tampered execution counts and declared
  checkpoints → INCOMPATIBLE_REEXECUTION; non-COMPLETED →
  INCOMPLETE_COMPARISON; temp root destroyed; source tree byte-identical.
- **F2 scientific derivation — HOLDS.** Assembly re-derives every
  registered measurement and finding from staged journal evidence and
  rejects differing, fabricated, missing (COMPLETED), or
  foreign-evidence rows; event bodies scanned for smuggled
  prediction/state keys.
- **F3 windowed paging — HOLDS.** Reader never calls the strict join for
  pages; fingerprint-cached streamed index; instrumented probe: index
  built once, a 5-row mid-history page read ≤10 stored lines; past-
  deadline index builds fail closed.
- **F4 lossless inventory — HOLDS.** Non-update stages, skipped attempts
  and duplicate-digest lines each delivered exactly once in the specified
  order; the strict join still refuses dangling duplicates.
- **F5 budget admission — HOLDS.** Publish boundary refuses with no run
  dir, receipt or index created; crash-retained partial usage counts
  against the budget and blocks a second assembly before any payload
  write.

## The one MINOR (corrected)

The remediation ledger entry said underived rows on non-COMPLETED runs
"become UNAVAILABLE `not_produced`"; the code stamps the run's own reason
when present (`not_produced` only when the run has none). Behaviour is
correct and more informative; the ledger wording was corrected in
`b4c7b3d` (docs-only).

## Counts and scope

- Independent evaluation suite: **599 passed, 0 failed**.
- Reviewer probes: **21 passed**. Standalone scenarios: **7/7**.
- Author-side full repository suite at `241096d`: **1,482 passed** (not
  independently rerun; the evaluation suite above was).
- Protected scope: `seed/**` NONE; dependency/lock/workflow changes NONE;
  only shared-module change is additive `canonical_stream` (+6 lines).
  Dependency audit passes, including the new `artifact_io` leaf.
- Disclosed limitation (unchanged): payload + detached-receipt rewrite is
  not detectable by integrity digests and is never presented as
  authenticity; record relocation and runs-index-last ordering bound the
  publication claim to `whole_payload_verified_at_publication`.

I31 remains NOT AUTHORIZED; no empirical suite was executed. No PR was
opened and nothing was merged by this review.
