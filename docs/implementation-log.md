# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current source and design state

**SEED 0.2 — B0–B8 VERIFIED at source/CI level, schema v7. B9 design/specification COMPLETE FOR OWNER REVIEW; B9 overall IN PROGRESS, implementation NOT STARTED.** Current verified source baseline is master `af05f6566c026cd5438453dada85c92e1a4f2bc4` (PR #13 documentation closure); exact [run 36454551620](https://github.com/Jeruzael/SEED/actions/runs/36454551620) passed 747 tests on all three Linux/macOS jobs and all seven standalone scenarios on both Python 3.13 jobs. B8 technical acceptance remains [PR #12](https://github.com/Jeruzael/SEED/pull/12), merge `e0075e21f545921324aa5d5c9e2f4217b0a06cca`, and [post-merge run 36443249417](https://github.com/Jeruzael/SEED/actions/runs/36443249417); its [closure record](seed-0.2-development-plan.md#b8-hosted-verification-closure--2026-09-29) remains historical evidence. The [B9 specification](superpowers/specs/2026-09-29-b9-astra-development-ui-design.md) authorizes no implementation; the review amendment authorizes a documentation commit and push to the existing branch only, with no PR. B10 remains **NOT STARTED**. Deployment/live-device validation remains **NOT PERFORMED** and installed SEED is **UNTOUCHED**.

The starting baseline was master `585affec56ddb0e4580f6df6926b9b6bde291dc0` (PR #9 merge), schema v5, 542 tests. Historical B6 acceptance remains 497 passed at dc225af.

| Batch | Status | Capability | Evidence |
| --- | --- | --- | --- |
| B0 | VERIFIED | Baseline and guardrails | [Baseline](baselines/seed-0.1-baseline.json) |
| B1 | VERIFIED | Transition-based experience | [Comparison](baselines/seed-0.2-b1-comparison.json) |
| B2 | VERIFIED | Prospective environmental prediction | [Comparison](baselines/seed-0.2-b2-comparison.json) |
| B3 | VERIFIED | Prediction-error evaluation | [Evaluation](baselines/seed-0.2-b3-evaluation.json) |
| B4 | VERIFIED | Persistent descriptive world model | [Execution record](seed-0.2-development-plan.md#b4-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b4-comparison.json) |
| B5 | VERIFIED | Bounded computational curiosity | [Execution record](seed-0.2-development-plan.md#b5-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b5-comparison.json) |
| B6 | VERIFIED | Semantic memory consolidation | [Execution record](seed-0.2-development-plan.md#b6-execution-log--2026-09-23), [comparison](baselines/seed-0.2-b6-comparison.json) |
| B7 | VERIFIED | Bounded descriptive self model | [Closure record](seed-0.2-development-plan.md#b7-hosted-verification-closure--2026-09-25), [comparison](baselines/seed-0.2-b7-comparison.json) |
| B8 | VERIFIED | Bounded decision selection, compact persistence and read-only inspection | [Closure record](seed-0.2-development-plan.md#b8-hosted-verification-closure--2026-09-29); exact master run 36443249417 |
| B9 | IN PROGRESS | Astra Development UI design complete for owner review; implementation NOT STARTED | [Design record](seed-0.2-development-plan.md#b9-design-execution-record--2026-09-29); fresh existing dashboard baseline 160 passed, 2 warnings |
| B10 | NOT STARTED | Development evaluation | Separate authorization required |

## Post-B6 hardening — separate from B7

The [2026-09-23 hardening record](reviews/2026-09-23-post-b6-hardening.md) covers
the battery parser, source/runtime/schema metadata, wording and CI follow-ups.
The historical wording checkpoint passed 540 tests; the subsequent macOS isolation
correction brought the verified baseline to 542. All seven B0–B6 artifacts remain
unchanged. The exact-master [Actions run](https://github.com/Jeruzael/SEED/actions/runs/35884486727)
has successful Linux Python 3.11/3.13 and macOS Python 3.13 jobs. Source/CI closure
does not mean installed-device deployment or validation.

[Verification instructions](verification.md) provide reproduction guidance;
older pending-check statements describe their recorded checkpoint. The [low-disk decision mismatch](review-follow-ups.md) is resolved in B8 autonomous selection through resource eligibility, with legacy reward and owner-command audits preserved.

## Current boundaries

The autonomous cycle records before/action/after experience, a prospective prediction, its evaluation, and a curiosity assessment before updating persistent world beliefs. After optional reflection, B7 publishes one descriptive snapshot before final runtime telemetry. Existing consolidate actions promote sufficiently supported beliefs into revisable semantic memory. The [architecture guide](architecture.md#autonomous-cycle-and-ordering) specifies the ordering and separate transaction boundaries.

The legacy learner remains compatible; B8 changes autonomous selection while preserving reward/Q update formulas, epsilon, alpha and action delays. Optional curiosity reflection is owner-controlled and **off by default**. Semantic memory has no upstream influence and deletes no original experience. Normal autonomous cycles retain two perceptions and their existing fixed reachability probes; B2–B7 add no network activity.

## Historical evidence

The seven B0–B6 artifacts and new B7 artifact in [baselines/](baselines/) represent their own development stages. Do not rewrite older results to match the current schema or footprint. Missing historical fields can be valid evidence of earlier capabilities rather than corruption. Detailed historical implementation plans remain under [superpowers/plans/](superpowers/plans/).

The current README and architecture guide supersede their former B3 snapshots. Historical execution records remain unchanged; the post-B6 documentation refresh is recorded in the tracker.

## Deployment boundary

Source commits, merges and documentation updates do not update the installed organism. Installation, restart and live-memory migration are separate owner-directed operations. A passing development suite does not imply deployment.


## B8 design — 2026-09-25

The [B8 specification](superpowers/specs/2026-09-25-b8-decision-system-design.md)
compares three architectures and selects a separate versioned decision system with
preselection candidate predictions, hard resource constraints, bounded Q/forecast-risk/
support-uncertainty scoring, eligible-only epsilon exploration and explicit Q fallback.
It proposes additive schema 7 decision records and bounded read-only inspection, with
only the necessary B7 schema compatibility adjustment. No proposal is implemented.

Fresh design baseline: **646 passed**, zero failures/skips, two existing warnings;
all six temporary-home scenarios match saved B7 outputs and all eight B0–B7 artifacts
remain unchanged. The source still implements B7/schema 6. Only the specification and
two tracker documents change. B8 design is AMENDED AND COMPLETE FOR OWNER REVIEW; implementation,
B9 and B10 are NOT STARTED. Installed organism remains UNTOUCHED.


### B8 design amendment — 2026-09-26

Owner review found **0 Critical, 2 Important, 1 Minor design findings** at
`3014625fe031b3b6d71f1d0320ce62b627569acf`. The amended specification removes fixed
rest tie bias through injected random choice among eligible maxima; limits durable
records to 16 KiB using compact resource forecasts/history summary and a canonical
selected-prediction SHA-256 link; and makes stale_decision a nonfatal skipped cycle
with an observe_interval retry. Explicit cycle results separate retry, completion,
owner stop and fatal errors. The [amendment record](seed-0.2-development-plan.md#b8-owner-review-amendment--2026-09-26)
contains revised API budgets and validation evidence.

Full compact examples encode to 4,195 and 4,292 bytes; digest/arithmetic/document checks
pass and all eight historical artifacts remain unchanged. No production suite rerun
was needed for documentation-only edits. These are design resolutions only; B8
implementation is NOT STARTED, B9–B10 are NOT STARTED, and installed SEED is UNTOUCHED.


## B8 implementation — 2026-09-28

Owner-approved implementation follows amended design `4c24d7e`. Candidate inference now precedes selection from one bounded Q/history snapshot. Completed cycles atomically persist compact decision evidence and a digest link to the unchanged selected B2 prediction. Stale attempts are nonfatal skipped cycles with a full interruptible observation-interval retry. Schema7 and bounded read-only decision inspection are implemented; B7 compatibility is narrow and no frontend is added.

The new [comparison artifact](baselines/seed-0.2-b8-comparison.json) anchors all eight unchanged historical artifacts. Independent review's two Important reader findings were reproduced and fixed; no findings are deferred. See the [tracker](seed-0.2-development-plan.md#b8-implementation--2026-09-28) and [verification evidence](verification.md#b8-local-verification--2026-09-28). Hosted CI, merge and installed-organism deployment remain separate owner-directed steps.


## B9 design — 2026-09-29

The [Astra specification](superpowers/specs/2026-09-29-b9-astra-development-ui-design.md) extends the existing Observer Edition 0.1 shell with seven DEVELOPMENT views. It defines a bounded stored prediction/evaluation read API, narrow safeguards for proven older-reader gaps, frozen-record presentation, exact ID links, state/time vocabulary, accessibility/responsive wireframes and future acceptance fixtures. Learning and Decisions remain distinct; legacy Concepts and B6 Semantic Memory remain distinct. B7/B8 readers and schema v7 remain unchanged.

Branch `seed-0.2-b9` starts at verified master `af05f6566c026cd5438453dada85c92e1a4f2bc4`. Fresh characterization on Python **3.13.15** with a temporary `SEED_HOME`: **160 existing dashboard tests passed, 2 existing warnings in 2.57s**. No new tests, full-suite/scenario/browser rerun or screenshots are claimed. Only the specification, development tracker and this log change; no implementation plan, production code, dependencies, migration, deployment, installed-home access or B10 work. The [tracker record](seed-0.2-development-plan.md#b9-design-execution-record--2026-09-29) holds the exact scope and verification details.

Documentation scope, fences,53 internal links/anchors, literal arithmetic and historical B8 preservation checks passed. The local checkpoint `4087fefcfe12fa9d582bba3cb5e53ddeae00d735` is preserved beneath the separate completion commit.

B9 overall is **IN PROGRESS**, design/specification **COMPLETE FOR OWNER REVIEW**, implementation **NOT STARTED**. B0–B8 remain **VERIFIED at source/CI level**; B10 **NOT STARTED**; deployment/live-device validation **NOT PERFORMED**; installed organism **UNTOUCHED**. Local documentation commit only; stop for owner review without pushing or opening a PR.


### B9 design-review amendment — 2026-09-29

Supplied independent review: **0 Critical, 1 Important, 0 Minor**. The proposed bounded `/api/development` failure could reject Overview’s existing all-or-nothing fetch and hide valid evidence. The amended specification requires future Overview to settle that source independently, preserve successful status/storage/health sections and show development-only values as **Unavailable**, never zero. Backend work limits stay intact; future regression/manual coverage, a deterministic budget-exhaustion fixture, the `overview.js` file-map entry and compatibility self-review are specified, not implemented.

Documentation-only amendment from `a6aa042c343c5e90dcf74c3fc90436e006d04e98`; both prior B9 commits remain intact. No fresh test run or hosted test evidence is claimed. B9 design is **COMPLETE FOR OWNER REVIEW**, overall **IN PROGRESS**, implementation **NOT STARTED**; B10 **NOT STARTED**, schema **v7**, deployment/live-device validation **NOT PERFORMED**, installed organism **UNTOUCHED**. Commit and publish the three authorized documents to the existing branch, then stop; no PR or implementation plan.

Mechanical validation passed: three-file scope, balanced fences, 53 internal links/anchors, literal arithmetic, unchanged backend bounds and historical B8 records, and clean diff whitespace. No unresolved task markers remain.

Publication pending: automatic approval review rejected the GitHub document upload for lack of direct trusted payload/destination authorization. No remote branch update occurred; the local amendment awaits explicit owner confirmation to publish.
