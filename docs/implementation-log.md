# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current verified state

**SEED 0.2 is verified through B6**, implemented in commit **dc225af**. Current schema is **v5**. The recorded full suite has **497 passing tests**, zero skips, and two existing dependency deprecation warnings. B7 is ready for separately authorized design and implementation; B7–B10 remain unstarted.

| Batch | Status | Capability | Evidence |
| --- | --- | --- | --- |
| B0 | VERIFIED | Baseline and guardrails | [Baseline](baselines/seed-0.1-baseline.json) |
| B1 | VERIFIED | Transition-based experience | [Comparison](baselines/seed-0.2-b1-comparison.json) |
| B2 | VERIFIED | Prospective environmental prediction | [Comparison](baselines/seed-0.2-b2-comparison.json) |
| B3 | VERIFIED | Prediction-error evaluation | [Evaluation](baselines/seed-0.2-b3-evaluation.json) |
| B4 | VERIFIED | Persistent descriptive world model | [Execution record](seed-0.2-development-plan.md#b4-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b4-comparison.json) |
| B5 | VERIFIED | Bounded computational curiosity | [Execution record](seed-0.2-development-plan.md#b5-execution-log--2026-09-22), [comparison](baselines/seed-0.2-b5-comparison.json) |
| B6 | VERIFIED | Semantic memory consolidation | [Execution record](seed-0.2-development-plan.md#b6-execution-log--2026-09-23), [comparison](baselines/seed-0.2-b6-comparison.json) |
| B7–B10 | NOT STARTED | Self model, decision upgrade, development UI, evaluation | Separate authorization required |

## Post-B6 hardening — separate from B7

The [2026-09-23 hardening record](reviews/2026-09-23-post-b6-hardening.md) covers the corrected battery parser, explicit source/runtime/dashboard/schema metadata, and a pinned least-privilege CI workflow. Fresh local macOS/Python 3.13 verification passes **539 tests** and all five scenarios. Historical B0–B6 counts and artifacts are preserved.

[Verification instructions](verification.md) document reproducible evidence, pending hosted matrix checks and owner-controlled merge settings. The [low-disk decision mismatch](review-follow-ups.md) remains **OPEN: separate owner authorization required**. No B7–B10 or deployment work is included.

## Current boundaries

The autonomous cycle records before/action/after experience, a prospective prediction, its evaluation, and a curiosity assessment before updating persistent world beliefs. Existing consolidate actions promote sufficiently supported beliefs into revisable semantic memory. The [architecture guide](architecture.md#autonomous-cycle-and-ordering) specifies the ordering and separate transaction boundaries.

The contextual bandit, reward/Q update, epsilon, alpha and action delays remain unchanged. Optional curiosity reflection is owner-controlled and **off by default**. Semantic memory has no upstream influence and deletes no original experience. Normal autonomous cycles retain two perceptions and their existing fixed reachability probes; B2–B6 add no network activity.

## Historical evidence

All seven artifacts in [baselines/](baselines/) represent their own development stages. Do not rewrite older results to match the current schema or footprint. Missing historical fields can be valid evidence of earlier capabilities rather than corruption. Detailed historical implementation plans remain under [superpowers/plans/](superpowers/plans/).

The current README and architecture guide supersede their former B3 snapshots. Historical execution records remain unchanged; the post-B6 documentation refresh is recorded in the tracker.

## Deployment boundary

Source commits, merges and documentation updates do not update the installed organism. Installation, restart and live-memory migration are separate owner-directed operations. A passing development suite does not imply deployment.
