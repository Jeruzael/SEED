# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current verified state

**SEED 0.2 is verified through B6**, with subsequent hardening and macOS CI
portability correction closed at source/CI level on master
`585affec56ddb0e4580f6df6926b9b6bde291dc0` (PR #9 merge). Current schema remains
**v5**. Fresh 2026-09-24 local baseline: **542 passed**, zero failed/skipped, two
existing dependency warnings; all five scenario outputs unchanged. Historical B6
acceptance remains **497 passed** at **dc225af**.

**B7 design/specification is COMPLETE FOR OWNER REVIEW. B7 implementation is NOT
STARTED.** The [B7 design](superpowers/specs/2026-09-23-b7-self-model-design.md)
and [execution record](seed-0.2-development-plan.md#b7-design-execution-record--2026-09-24)
define the proposed singleton, evidence/freshness contract and tests. Implementation
requires separate authorization after review. B8–B10 remain unstarted.

| Batch | Status | Capability | Evidence |
| --- | --- | --- | --- |
| B0 | VERIFIED | Baseline and guardrails | [Baseline](baselines/seed-0.1-baseline.json) |
| B1 | VERIFIED | Transition-based experience | [Comparison](baselines/seed-0.2-b1-comparison.json) |
| B2 | VERIFIED | Prospective environmental prediction | [Comparison](baselines/seed-0.2-b2-comparison.json) |
| B3 | VERIFIED | Prediction-error evaluation | [Evaluation](baselines/seed-0.2-b3-evaluation.json) |
| B4 | VERIFIED | Persistent descriptive world model | [Execution record](seed-0.2-development-plan.md#b4-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b4-comparison.json) |
| B5 | VERIFIED | Bounded computational curiosity | [Execution record](seed-0.2-development-plan.md#b5-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b5-comparison.json) |
| B6 | VERIFIED | Semantic memory consolidation | [Execution record](seed-0.2-development-plan.md#b6-execution-log--2026-09-23), [comparison](baselines/seed-0.2-b6-comparison.json) |
| B7 | NOT STARTED | Self Model design complete for owner review | [Design](superpowers/specs/2026-09-23-b7-self-model-design.md); separate implementation authorization required |
| B8–B10 | NOT STARTED | Decision upgrade, development UI, evaluation | Separate authorization required |

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
[low-disk decision mismatch](review-follow-ups.md) remains **OPEN: separate owner
authorization required**. This B7 design task changes no runtime behavior.

## Current boundaries

The autonomous cycle records before/action/after experience, a prospective prediction, its evaluation, and a curiosity assessment before updating persistent world beliefs. Existing consolidate actions promote sufficiently supported beliefs into revisable semantic memory. The [architecture guide](architecture.md#autonomous-cycle-and-ordering) specifies the ordering and separate transaction boundaries.

The contextual bandit, reward/Q update, epsilon, alpha and action delays remain unchanged. Optional curiosity reflection is owner-controlled and **off by default**. Semantic memory has no upstream influence and deletes no original experience. Normal autonomous cycles retain two perceptions and their existing fixed reachability probes; B2–B6 add no network activity.

## Historical evidence

All seven artifacts in [baselines/](baselines/) represent their own development stages. Do not rewrite older results to match the current schema or footprint. Missing historical fields can be valid evidence of earlier capabilities rather than corruption. Detailed historical implementation plans remain under [superpowers/plans/](superpowers/plans/).

The current README and architecture guide supersede their former B3 snapshots. Historical execution records remain unchanged; the post-B6 documentation refresh is recorded in the tracker.

## Deployment boundary

Source commits, merges and documentation updates do not update the installed organism. Installation, restart and live-memory migration are separate owner-directed operations. A passing development suite does not imply deployment.
