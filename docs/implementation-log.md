# SEED Implementation Log

This is a navigation index. The [development tracker](seed-0.2-development-plan.md) holds the canonical batch requirements, decisions, acceptance evidence, limitations and readiness gates. The [README](../README.md) explains current use; the [architecture guide](architecture.md) describes current implementation contracts.

## Current source and design state

**SEED 0.2 — B0–B9 COMPLETE / VERIFIED at source/CI level, schema v7.** B9 remains merged via [PR #14](https://github.com/Jeruzael/SEED/pull/14) at master `b7d8b832924c7ff1512708965fa021fed4306866`, exact run 36833492768 successful. The clean B10 design starting checkpoint is `5c90d6683450dab64713ca09104e2ec70a0199bb` on `seed-0.2-b10-design`; authenticated GitHub confirms exact [run 36909840669](https://github.com/Jeruzael/SEED/actions/runs/36909840669) with all three required jobs successful. Current authorization is **B10 DESIGN REVISION ONLY**. B10 overall is **IN PROGRESS**, [design](superpowers/specs/2026-10-02-b10-development-evaluation-design.md) **REVISED / COMPLETE FOR FINAL OWNER REVIEW**, implementation **NOT STARTED / NOT AUTHORIZED**. Revision starts clean at `189f8ce507f791fd5ac4c4a1b04d0b7a0b3855fb`, one design-only commit after `5c90d6683450dab64713ca09104e2ec70a0199bb`. Four owner-approved revision directions are incorporated, with the complete resulting design still awaiting final approval. No B10 experiment or implementation plan is produced. All eleven former OPEN architecture decisions are resolved as PROVISIONAL choices pending owner review. B11–B16 remain [PLANNED / NOT STARTED](seed-0.2-development-plan.md#seed-03-roadmap-direction--2026-10-02). Deployment/live-device validation remains NOT PERFORMED; installed organism UNTOUCHED. The dated records below preserve earlier states and authorizations; current status supersedes them only within this design scope.

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
| B9 | VERIFIED at source/CI level | Astra Development UI; merged PR #14; local verification and independent review PASS; exact post-merge hosted checks PASS | [Source/CI closure](seed-0.2-development-plan.md#b9-sourceci-closure--2026-10-02); master b7d8b83, run 36833492768 |
| B10 | IN PROGRESS | Development Evaluation & Experimental Foundation | [Design revised for final owner review](superpowers/specs/2026-10-02-b10-development-evaluation-design.md); implementation NOT STARTED / NOT AUTHORIZED |

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

**Historical design checkpoint:** B9 overall is **IN PROGRESS**, design/specification **COMPLETE FOR OWNER REVIEW**, implementation **NOT STARTED**. B0–B8 remain **VERIFIED at source/CI level**; B10 **NOT STARTED**; deployment/live-device validation **NOT PERFORMED**; installed organism **UNTOUCHED**. Local documentation commit only; stop for owner review without pushing or opening a PR.


### B9 design-review amendment — 2026-09-29

Supplied independent review: **0 Critical, 1 Important, 0 Minor**. The proposed bounded `/api/development` failure could reject Overview’s existing all-or-nothing fetch and hide valid evidence. The amended specification requires future Overview to settle that source independently, preserve successful status/storage/health sections and show development-only values as **Unavailable**, never zero. Backend work limits stay intact; future regression/manual coverage, a deterministic budget-exhaustion fixture, the `overview.js` file-map entry and compatibility self-review are specified, not implemented.

**Historical amendment checkpoint:** Documentation-only amendment from `a6aa042c343c5e90dcf74c3fc90436e006d04e98`; both prior B9 commits remain intact. No fresh test run or hosted test evidence is claimed. B9 design is **COMPLETE FOR OWNER REVIEW**, overall **IN PROGRESS**, implementation **NOT STARTED**; B10 **NOT STARTED**, schema **v7**, deployment/live-device validation **NOT PERFORMED**, installed organism **UNTOUCHED**. Commit and publish the three authorized documents to the existing branch, then stop; no PR or implementation plan.

Mechanical validation passed: three-file scope, balanced fences, 53 internal links/anchors, literal arithmetic, unchanged backend bounds and historical B8 records, and clean diff whitespace. No unresolved task markers remain.

Historical publication checkpoint: automatic approval review rejected the earlier GitHub document upload for lack of direct trusted payload/destination authorization; no remote update occurred at that attempt. **Superseded:** the owner subsequently published the amended design successfully, and authenticated GitHub verification confirms remote `seed-0.2-b9` at `3dc9b8fdab2f4c12227e2371e679a57a02a5cf6f`. No PR exists and no hosted CI is claimed for this branch head. B9 implementation remains **NOT STARTED**.


### B9 owner approval and publication cleanup — 2026-09-29

Owner approved the B9 design/specification at `3dc9b8fdab2f4c12227e2371e679a57a02a5cf6f`, including the Overview compatibility resolution. This approval does not authorize implementation. The owner-supplied review closure reports **0 Critical / 0 Important remaining**; the earlier **0 Critical / 1 Important / 0 Minor** finding and failed publication attempt remain historical records, superseded by the resolution and verified publication above.

**Historical approval checkpoint:** Only the development tracker and this log change; the approved specification remains byte-identical and the three existing B9 commits remain intact. No fresh test run is claimed. B9 design/specification is **OWNER APPROVED / COMPLETE**, overall **IN PROGRESS**, implementation **NOT STARTED**; B10 **NOT STARTED**, schema **v7**, deployment/live-device validation **NOT PERFORMED**, installed organism **UNTOUCHED**. Publish the cleanup to the existing branch and stop; no PR or implementation plan.


## B9 Astra implementation — 2026-09-30

The owner's later implementation instruction supersedes the historical design-only stop above. Native execution on `seed-0.2-b9` implements the approved seven-view Astra observer and bounded evidence readers. The [tracker](seed-0.2-development-plan.md#b9-implementation--2026-09-30) records scope/commit checkpoints; [verification](verification.md#b9-local-implementation-verification--2026-09-30) records the local851-test suite, seven standalone scenarios, temporary fixture preservation and browser acceptance.

Browser verification found an omitted transition ID in prediction detail; a failing regression check preceded the fix. Table regions are keyboard focusable and retain horizontal overflow on narrow screens. The intervening fixture checkpoint `e3bd0fd` remains intact. Final independent review is in progress. B9 is IMPLEMENTED locally; hosted CI, publication, merge and deployment are not claimed. B0–B8 evidence, schema v7 and installed SEED are unchanged; B10 remains NOT STARTED.

### B9 corrective implementation — 2026-10-01

The owner-authorized C0–C18 pass preserves starting head `20e19add6ee35c9dc120510333b0207d25294cb8` and the later owner checkpoint `8d57113`. Reader fixes `0647d88`, accessibility/client fixes `01263f1`, review corrections `5872b93`, render-bound fix `23ac2cd`, lifecycle fixes `ef214b9` cursor-history fix `5961efd` and final provenance/history fixes `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981` are separate commits. The [final source verification record](verification.md#final-corrective-source-checks--2026-10-01) records148 focused/883 full tests, two existing warnings, seven passing scenarios, browser checks and limits, and unchanged core/schema/dependencies/workflows/baselines/B7/B8 readers. Final independent whole-branch review **PASS** from `16dcd8b` through `1a28437`: **0 Critical / 0 Important / 0 Minor**, none deferred. Independent148-focused/883-full reruns and maximum DOM/source-ID checks passed. B9 local verification PASS; overall NOT YET VERIFIED; hosted CI NOT RUN, PR NOT OPEN, merge NO, deployment NOT PERFORMED, installed organism UNTOUCHED and B10 NOT STARTED. The corrected branch is to be published only after the review gate passes, then stop before PR, merge, deployment or B10.

### B9 publication blocker — 2026-10-01

**Historical blocker checkpoint, superseded below:** After the passing review and documentation commit `46476ad3a31da6ff8be071cdfe9ebd650a977c25`, authorized publication was attempted over both transports. `git push origin seed-0.2-b9` failed with `Permission denied (publickey)`; HTTPS push using the existing `osxkeychain` credential helper and disabled terminal prompts failed with `could not read Username for 'https://github.com': terminal prompts disabled`. Authenticated GitHub connector verification still reports remote `seed-0.2-b9` at `ef214b9e650b4356e94b3c64be292e9b711e67c2`. No history was rewritten and no remote update is claimed. Local commits remain preserved; C18 is pending working Git authentication. This subsequent documentation-only blocker record does not change reviewed source `1a28437` or its verification results. No PR, merge, deployment or B10 action occurred.

### B9 publication-status cleanup — 2026-10-01

The earlier Git-authentication blocker is historical: the owner subsequently published the preserved branch successfully. Authenticated GitHub confirms `seed-0.2-b9` at `1f7d7692fc397826d4dc79dcfe924073b0ee5bb0` before this cleanup; no history was rewritten and no PR was open at the start. Reviewed source remains `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981`; both intervening commits are documentation-only. C18 branch publication is COMPLETE. This four-document truthfulness cleanup changes no technical result and requires no fresh Python test run. Hosted PR CI is NOT RUN at this checkpoint; B9 remains NOT YET VERIFIED, with merge NO, deployment NOT PERFORMED, installed organism UNTOUCHED and B10 NOT STARTED. The owner now authorizes cleanup publication, one B9 PR to master and hosted verification, then a stop before merge.

### Pre-B10 canonical documentation alignment — 2026-10-02

Current status records B9 source/CI closure on exact merged master and retains all dated design, failed-publication and local-verification checkpoints as historical. B10 is renamed/reframed as Development Evaluation & Experimental Foundation, not a capability expansion; it remains NOT STARTED with design not yet authorized under this task. The tracker records the owner-supplied B11–B16 roadmap titles as PLANNED / NOT STARTED, with implementation authorization NONE; the [canonical roadmap index](roadmaps/seed-b10-to-0.3-development-roadmap-v1.0.md) links the full original 38-page v1.0 PDF, preserved byte-for-byte rather than reconstructed. All eleven identified B10 architecture decisions remain OPEN in the existing B10 planning section. Proposed v1.1 revisions remain pending and are not inserted into approved v1.0. No runtime, tests, schema, dependencies, workflows, installed-home or deployment changes are authorized or performed.


### B10 design — 2026-10-02

The [B10 specification](superpowers/specs/2026-10-02-b10-development-evaluation-design.md) defines an external coordinator and disposable trusted workers, mechanically private evaluator truth, immutable frozen assays and score-before-current-learning prequential cycles. Four shared experiment families, paired prediction baselines, separately cloned policy trajectories, exact metrics/windows/seeds, two digest contracts, bounded immutable artifacts, replay/re-execution and observer-only Astra inspection are specified for later authorization. Existing cognition, reward/Q/weights, 200-row predictor history, lifetime world-model accumulation and schema v7 are preserved.

All eleven former OPEN decisions are RESOLVED — PROVISIONAL for owner review; no OPEN B10 architecture question remains. Adversarial self-review covers leakage, contamination, metrics/coverage/baseline fairness, isolation, replay, integrity, paths/resources, frozen mutation, sequencing and UI claims. Trusted-code/process isolation and same-profile reproducibility limits remain explicit; signatures, inference and later capabilities are DEFERRED. Negative/null results are valid acceptance outcomes.

Only the specification, development tracker and this log change. Starting clean head and existing exact CI run 36909840669 are verified; no fresh production tests/scenarios/experiments/browser checks/hosted B10 CI are claimed. Original roadmap/index and historical baselines remain unchanged. B10 overall IN PROGRESS; design COMPLETE FOR OWNER REVIEW; implementation NOT STARTED / NOT AUTHORIZED. Stop before implementation planning/coding, publication/PR, B11 or deployment; installed SEED UNTOUCHED.

Documentation verification: PASS — exact three-file scope; balanced Markdown/Mermaid fences; 63 local links/anchors; 25 specification sections and all eleven decision dispositions; literal metric/float/budget arithmetic; clean diff whitespace; all 11 tracked baseline/roadmap files byte-identical to starting HEAD, including the approved PDF checksum. These are documentation checks, not B10 test/experiment execution.


### B10 design revision — 2026-10-02

The [revised B10 specification](superpowers/specs/2026-10-02-b10-development-evaluation-design.md) starts at clean 189f8ce, exactly one design-only commit after 5c90d66. A now tests stationary action-conditioned load effects; B changes only rest (-0.10→+0.05) at hidden 321. Literal examples use conditional contributor counts, actual exposure and unchanged B2 support/window rules; B4 lifetime accumulation remains explicit. No measured action is forced or balanced and sparse samples remain unavailable.

Minimal durable evidence/point-score journal gates constant SCORE_ACK; aggregates/final artifacts/digests/indexes/UI follow later, and post-ACK failure cannot erase or retry actual learning. Frozen results use FROZEN_SELECTION_ASSAY and disclose suppressed reflect/consolidate mutation; normal cognitive effects require prequential evaluation. All C setup occurs before freeze. Metrics, examples, sample thresholds, adversarial review, future-test design, acceptance and the decision register reflect the revisions. Unrelated design directions/caps remain intact; no OPEN architecture question remains.

Only specification/tracker/log change; roadmap PDF/index, historical baselines and all source/runtime/schema/tests/dependency/workflow files remain unchanged. Owner-approved revision directions do not imply approval of the resulting complete specification. **B10 DESIGN REVISED / COMPLETE FOR FINAL OWNER REVIEW. B10 IMPLEMENTATION NOT STARTED / NOT AUTHORIZED.** Overall IN PROGRESS; no implementation plan, experiment execution, PR, deployment or installed-organism access. Stop for final review; documentation checks are recorded after execution, not production/B10 tests or fresh hosted CI.

Revision documentation verification: PASS — git diff --check; complete revision diff reviewed; exactly the three authorized documents; balanced Markdown/Mermaid fences and 65 local links/anchors; updated A/B, lifetime, B3 aggregate, exposure-window and checkpoint/resource arithmetic; stale universal A/B formulas absent (the separately named C conflict fixture remains valid); all 11 baseline/roadmap files byte-identical to starting `189f8ce` and pre-B10 baseline `5c90d66`. Frozen wording explicitly discloses suppressed mutation. No production suites/new tests/B10 experiments or fresh hosted CI executed/claimed.
