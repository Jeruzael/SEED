# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current verified state

**SEED 0.2 — B7 VERIFIED, schema v6.** [PR #10](https://github.com/Jeruzael/SEED/pull/10) merged B7 into master `ab7c2b45508828685fc9b0a65807e08cee1cff98`. Post-merge [SEED verification run 36104979944](https://github.com/Jeruzael/SEED/actions/runs/36104979944) passed **646 tests on each of the three jobs**: Linux Python 3.11.16, Linux Python 3.13.15 and macOS Python 3.13.15. All six standalone scenarios passed on both Python 3.13 jobs; recorded artifact inspection confirmed the exact checkout SHA, clean tree, successful dependency/test checks and unchanged lock hash. See the [closure record](seed-0.2-development-plan.md#b7-hosted-verification-closure--2026-09-25). Deployment/live-device validation remains **NOT PERFORMED**. B8 design is now **COMPLETE FOR OWNER REVIEW**, based on verified master `92e6aa47ec01d80e123e1c9a90c10f9e59e367fb` (PR #11); B8 implementation and B9–B10 remain **NOT STARTED**. See the [B8 design record](seed-0.2-development-plan.md#b8-design-execution-record--2026-09-25).

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
| B8 | IN PROGRESS | Decision upgrade design COMPLETE FOR OWNER REVIEW; implementation NOT STARTED | [Specification](superpowers/specs/2026-09-25-b8-decision-system-design.md), [design record](seed-0.2-development-plan.md#b8-design-execution-record--2026-09-25) |
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
older pending-check statements describe their recorded checkpoint. The
[low-disk decision mismatch](review-follow-ups.md) remains **OPEN in implemented code**. The authorized B8 design resolves it through autonomous eligibility while preserving legacy reward and owner-command audits. Implementation requires separate authorization; B7 continues to report suppression without changing selection.

## Current boundaries

The autonomous cycle records before/action/after experience, a prospective prediction, its evaluation, and a curiosity assessment before updating persistent world beliefs. After optional reflection, B7 publishes one descriptive snapshot before final runtime telemetry. Existing consolidate actions promote sufficiently supported beliefs into revisable semantic memory. The [architecture guide](architecture.md#autonomous-cycle-and-ordering) specifies the ordering and separate transaction boundaries.

The contextual bandit, reward/Q update, epsilon, alpha and action delays remain unchanged. Optional curiosity reflection is owner-controlled and **off by default**. Semantic memory has no upstream influence and deletes no original experience. Normal autonomous cycles retain two perceptions and their existing fixed reachability probes; B2–B7 add no network activity.

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
two tracker documents change. B8 design is COMPLETE FOR OWNER REVIEW; implementation,
B9 and B10 are NOT STARTED. Installed organism remains UNTOUCHED.
