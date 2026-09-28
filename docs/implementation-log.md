# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current implementation and acceptance state

**SEED 0.2 — B8 IMPLEMENTED; hosted acceptance passed for implementation SHA `acaccce889b18d165252c6977d41e5113e74e681`, schema v7.** [PR #12](https://github.com/Jeruzael/SEED/pull/12) remains open against master. [Run 36407866250](https://github.com/Jeruzael/SEED/actions/runs/36407866250) passed 747 tests on all three Linux/macOS jobs and all seven standalone scenarios on both Python 3.13 jobs. The supplied artifact-inspection record confirms the exact clean checkout and successful dependency/test/scenario results; GitHub run/job metadata and logs corroborate acceptance. A new documentation head requires its own checks; merge and exact post-merge master verification remain outstanding, so B8 is **not yet VERIFIED**. Master remains B7/schema v6. Owner approval on 2026-09-27 authorized implementation; deployment/live-device validation remains **NOT PERFORMED**, and B9–B10 remain unstarted. See the [acceptance record](seed-0.2-development-plan.md#b8-pr-head-hosted-acceptance--2026-09-28).

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
| B8 | IMPLEMENTED; hosted acceptance passed for `acaccce` | Bounded decision selection, compact persistence and read-only inspection | [PR-head acceptance](seed-0.2-development-plan.md#b8-pr-head-hosted-acceptance--2026-09-28); final docs-head checks, merge and master verification outstanding |
| B9–B10 | NOT STARTED | Development UI and evaluation | Separate authorization required |

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
