# SEED 0.2 B8 — Decision-System Upgrade Design

## Goal

Make the existing contextual bandit one selection signal among several, using only
pre-action evidence and the existing four internal actions. Recommend a separate
`DecisionSystem`, explicit eligibility, one shared candidate-prediction snapshot,
and a small versioned utility rule. Preserve learning semantics and make every
completed decision inspectable.

**Design/specification: AMENDED AND COMPLETE FOR OWNER REVIEW. Implementation: NOT STARTED.**
Amended 2026-09-26 following owner review: 0 Critical, 2 Important, 1 Minor design
findings. This revision supersedes the original tie, durable-record and stale-expiry
contracts at `3014625fe031b3b6d71f1d0320ce62b627569acf`; no implementation began.
This document specifies future behavior; it does not authorize implementation.
The owner explicitly authorized only this spec and the two tracker documents.
B9–B10 remain NOT STARTED. Installed organism: UNTOUCHED.

## Verified starting state

- Repository: `Jeruzael/SEED`; clean `master` and `origin/master` verified at
  `92e6aa47ec01d80e123e1c9a90c10f9e59e367fb`, PR #11 documentation-closure merge.
  Fetch, checkout, fast-forward pull, status, revision and log were checked before
  creating **seed-0.2-b8**. No history was reset or rewritten.
- B0–B7: VERIFIED at source/CI level; software version 0.2; schema **6**.
  Owner-supplied exact-master [run 36121878229](https://github.com/Jeruzael/SEED/actions/runs/36121878229)
  reports 646 passes on Linux/Python 3.11.16, Linux/Python 3.13.15 and macOS/Python
  3.13.15, with all six standalone scenarios on both 3.13 jobs. This task does not
  claim a new hosted artifact audit.
- Fresh local `.venv/bin/python -m pytest -q`: **646 passed, zero failures/skips,
  two existing upstream warnings**, Python 3.13.15, exit 0.
- Fresh `.venv/bin/python -m tests.<module>` for `baseline_scenario`,
  `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`,
  `semantic_scenario`, `self_model_scenario`: all exit 0, valid JSON, exactly equal
  to the saved B7 implementation outputs. All runs used synthetic, resolved temporary
  homes. Local audit output is ignored `.review-artifacts/b8-design/`.
- All **eight** B0–B7 baseline artifacts are retained byte-for-byte. The instruction's
  “seven prior artifacts” wording predates the eighth B7 artifact; preserve all eight.
- No live writable SEED home was inspected, installed, restarted, accessed or migrated.
  Deployment/live-device validation remains NOT PERFORMED. The low-disk mismatch
  remains OPEN in running code; the proposed resolution is specified below.

## Current decision pipeline

The audited source at the base commit runs:

```text
settings / inferred-wake handling → one state_before perception and PERCEPTION
→ Learner.choose: state_key, four separate Q reads, epsilon draw, random choice
→ DECISION (raw Q provenance)
→ Predictor.predict(state_before, selected_action), one latest-200 history read
→ PREDICTION → ACTION start → existing internal action → ACTION complete
→ one state_after perception → outcome → B3 evaluation / PREDICTION_ERROR
→ B5 prior-belief read (up to eight rows) and post-outcome curiosity assessment
→ unchanged reward(state_before, action) → Q update
→ atomic episode + transition + prediction + evaluation + B4 queue + B5 assessment
→ CURIOSITY → B4 recover (up to 100) → LEARNING / MEMORY / latest-state metadata
→ optional B5 reflection → B7 snapshot → final runtime telemetry → action delay
```

`seed/learner.py` contains a contextual bandit, not long-horizon planning. Its
`Decision.score`, `values` and `visits` are pre-update raw Q evidence. `choose()`
currently ignores all predictions and constraints, and randomly breaks exact Q ties.
Prediction therefore cannot currently explain why an action was selected.

`observe` and `rest` perform no extra internal processing. Every ordinary action has
both perceptions; rest only has a longer subsequent wait. `reflect` examines up to
80 recent episodes, excludes explicit owner-source episodes, and produces existing
battery/load summaries when at least eight qualifying samples exist. `consolidate`
invokes the B6 guarded, bounded semantic engine and existing checkpoint. Its legacy
checkpoint includes existing count work; B8 does not claim to bound that older path.
Delays remain observe 8, reflect 12, consolidate 20, rest 35 seconds under current
base settings, with the existing configuration-derived timing semantics preserved.

B2 estimates immediate post-action observations using action history with at least
two samples, otherwise global history with at least two, otherwise persistence.
The horizon precedes rest's wait. B2 support confidence and B4 consistency confidence
are different descriptive quantities. B3 errors and B5 scores exist only after the
outcome. B6 summarizes B4; B7 reports the previous completed cycle when the next
selection begins. No persisted general goal contract exists.

The audit read the required source and documentation, and inspected test contracts
across learner, predictor/evaluator, transitions, world model, curiosity, semantic
memory, self model, migrations, six scenarios and dashboard reads. Particularly
relevant existing regressions are `test_prospective_order_and_exact_pre_action_payload`,
`test_suppression_preserves_selected_action_legacy_reward_and_delay`, and
`test_snapshot_presence_corruption_and_failure_never_change_upstream_outputs`.
Their B7 selection assumptions need explicitly scoped B8 adaptations, not deletion.

## Requirements

1. Freeze state, Q and one bounded history snapshot before computing all four
   candidate predictions, constraints and utilities; select only afterward.
2. Keep hard constraints separate from graded scores and apply them to exploration.
3. Preserve reward, Q schema/update/visits, alpha, epsilon probability, action set,
   delay formulas and B2–B7 meanings. Store utility separately from Q.
4. Persist exact selection-time evidence with each new completed autonomous
   transition; expose bounded read-only inspection without frontend work.
5. Specify fallback reproducible with injected RNG, corrupt-data behavior, provenance, limits and
   hand-calculable acceptance. No claim of improved performance.

## Non-goals

No production code, tests, migrations, APIs, UI, CI, settings, dependencies, baseline
artifacts or deployment are changed in this phase. Future B8 also excludes new goals,
LLMs, tools, multi-step planning, causal models, sensor changes, learned weights,
energy measurement, reward redesign, Q migration, forgetting, new scheduler/threads,
B9 visualizations and B10 developmental experiments.

## Selection-time evidence inventory

Reads listed here are proposed B8 selection reads, not extra downstream B3–B7 work.

| Signal/input | Available before action? | Exact source | Bounded read | Freshness/provenance | Causal or descriptive? | Safe decision meaning | Missing/corrupt behavior | Use? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q/value and visits | Yes | `q_values`, existing `state_key(state_before)` | One query, four action keys | Frozen before selection; missing row distinguished | Learned legacy-reward association | Relative learned preference | Missing row 0/0; malformed existing row aborts selection | Yes | Required compatible learned signal |
| Battery | Yes | Fresh `state_before.battery_pct` | No extra read | Current perception, presence retained | Observation | Constraint; forecast's current input | Unknown blocks costly autonomous actions; never healthy default | Yes | Immediate resource evidence |
| Charging | Yes | Fresh `state_before.charging` | None | Current fact; not a predicted future value | Observation | Known charging removes battery-only forecast penalty | Unknown is unprotected and blocks costly actions | Yes | Distinguishes low battery while charging |
| Load | Yes | Fresh `state_before.load_ratio` | None | Current perception | Observation | Constraint and forecast input | Missing is unknown; invalid explicit value aborts legacy-incompatible state | Yes | Immediate workload evidence |
| Disk | Yes | Fresh `state_before.disk_free_pct` | None | Current perception | Observation | Constraint and forecast input | Same missing/invalid distinction as load | Yes | Resolves suppressed-work mismatch |
| Network | Yes | `state_before.network` | None | Current perception | Observation | B2 input only | B2 unavailable rules | Prediction only | No action-specific generic danger rationale |
| Candidate predictions | Not currently; yes after proposed reorder | B2 pure batch over completed `transitions` | One query, latest 200 raw rows | Shared ID cutoff; compact support/freshness provenance | Descriptive action/global correlations | Immediate resource forecasts | Explicit missing/stale states; conservative effective penalties, then Q fallback if no usable resource forecast | Yes | Makes prediction prospective for selection |
| B4 confidence/support/contradictions/presence | Yes | `world_beliefs`; action/global rows | Zero selected; alternative would read at most 20 identities | Lifetime cumulative evidence; no TTL; overlaps B2 transitions | Descriptive consistency | Could describe consistency, not calibrated uncertainty | Absent is unknown, never confidence zero interpreted as certainty | No | No unique required signal; avoids combining incompatible confidence meanings |
| Current B5 curiosity score | No | `assess_curiosity` needs current B3 error/after | Zero | Post-outcome | Descriptive salience | None at selection | Excluded even if a previous score exists | No | Would leak future evidence or substitute a stale different outcome |
| B6 semantic summaries | Yes | `semantic_memories` | Zero | Last explicit consolidation of B4 | Derived descriptive summary | No unique environmental forecast | Excluded | No | Duplicate underlying evidence; promotion is not another independent observation |
| B7 self model | Yes, prior cycle | `self_model_current` | Zero | Prior completed cycle, separate source clocks | Descriptive | No unique fresh selection evidence | Absent/stale/corrupt irrelevant to selection | No | Fresh resources and static catalog already available |
| Goals/progress | No | No goal contract exists | Zero | Not available | Not applicable | None | Excluded, no fabricated zero progress | No | No new goal system |
| Processing opportunity | Partly | Reflect's 80 episodes; B6 beliefs/cursor/fingerprints | Zero | Would require separate exact processing analysis | Work availability, not information gain | Omitted in v1 | Excluded | No | Duplicates action logic for little added certainty |
| Per-action energy/CPU cost | No calibrated source | None | Zero | Not measured | Not established | None | Excluded | No | Avoids invented measurements |

## Signals explicitly excluded

No current/future prediction error, B5 curiosity, future observation, future Q,
post-action B4 update, semantic confidence, prior-cycle B7 snapshot, goal progress,
network danger, information-gain bonus or energy-cost scalar enters selection.
B4 presence/absence and contradiction rate are deliberately not additional uncertainty
terms. Unknown world beliefs do not block selection or trigger a database read.
A current-resource scalar is also omitted: resources set eligibility; forecasts set
risk. This avoids counting the same current bad state twice as weighted penalties.

## Design alternatives

| Architecture | Advantages | Costs and failure risks | Ruling |
| --- | --- | --- | --- |
| A: weighted scoring inside `Learner.choose` | Few new modules; familiar call site | Couples Q storage/update with predictor, eligibility and persistence; makes legacy `Decision.score` easy to overload; still needs prediction reordering | Reject |
| B: lexicographic constraints, resource risk, then Q | Simple explanation; strong guards; no weight tuning | Risk-first can discard every graded Q difference; Q-first can make forecasts irrelevant; arbitrary priority discontinuities; weak composite evidence | Reject for B8; eligible-Q ordering remains the explicit fallback |
| C: separate versioned `DecisionSystem` | Pure scoring inputs; fixed bounded math; Q remains intact; clear recorded decision | One new engine, evidence contract, migration and read adapter; constants require owner review | Select, with only three score components and no world/semantic/self-model reads |

C is the smallest option here that both separates learning from selection and makes
Q one graded signal. Choosing more evidence sources merely because they exist would
increase work and double counting without satisfying another requirement.

## Selected architecture

Future `seed/decision.py` owns `decision_v1`, version 1: bounded evidence acquisition,
pure validation/component calculation, eligibility and injected-random selection.
The predictor owns all forecasting math. The learner owns reward/update and its
legacy public `choose()` remains usable for characterization/direct callers.
The autonomous cycle calls the new decision system, not legacy `choose()`.

The result contains an immutable/detached record payload, the selected frozen B2
prediction, and a legacy `Decision` adapter. All four candidates remain visible,
including constrained ones. No cached decision state is required across cycles or
restart. Fixed policy constants live in source; no setting or weight editor is added.

## Candidate action contract

Canonical enumeration and storage order: `observe`, `reflect`, `consolidate`, `rest`.
Only these four identities are accepted, exactly once each. Unknown, duplicate or
missing candidate identities are a decision-contract error, not permission to execute
an arbitrary action. There are no dynamically registered tools.

Each candidate has eligibility/reasons; raw Q/visits/row-absence; bounded components;
compact three-target resource forecasts and utility. Full B2 predictions and contributor
metadata exist only in the frozen in-memory result; the selected full prediction is
stored once in its linked transition and identified in the record by canonical digest. Even constrained candidates have computed components when inputs are safe.
Eligibility, selection and actual substantive action completion are separate facts.
A valid recorded decision can lead to a suppressed/no-op action or fail before any
completed transition; it does not certify that semantic work occurred.

## Hard constraints

The current observation is detached using the existing transition validation first.
Its full serialized state_before must be <=16,384 UTF-8 bytes; otherwise abort
`invalid_state` before action so every future B8-linked observation remains inspectable
within the source-read bound. Do not truncate fields or rewrite the observation.
For supported sensor fields, require exact finite nonboolean numeric domains:
battery/disk 0..100, load >=0; charging/network Boolean or null; local hour integer
0..23 when present. Missing fields remain absent. Battery null, charging null and
network null are valid unknowns. Explicit null/invalid load or disk, malformed battery,
or malformed local hour are `invalid_state`: abort before action because legacy
`state_key`/reward cannot safely process them. Do not sanitize those values and then
silently change legacy reward. The legacy defaults for *absent* load/disk/hour remain
inside state-key/reward only; B8 eligibility must still see them as absent/unknown.

| Condition on current state | `observe` | `reflect` | `consolidate` | `rest` |
| --- | --- | --- | --- | --- |
| Valid load > .8 | Eligible | `high_load` | `high_load` | Eligible |
| Valid battery <20 AND charging exactly false | Eligible | `low_battery` | `low_battery` | Eligible |
| Valid disk <10 | Eligible | `low_disk` | `low_disk` | Eligible |
| Any battery/charging/load/disk missing or permitted unknown | Eligible | `unknown_resources` | `unknown_resources` | Eligible |
| Owner stop observed | Cancel cycle | Cancel cycle | Cancel cycle | Cancel cycle |
| Invalid state/Q/contract | Abort cycle | Abort cycle | Abort cycle | Abort cycle |

Reasons accumulate in the fixed order `high_load`, `low_battery`, `low_disk`,
`unknown_resources`; equality at .8/20/10 is allowed. Known low battery while charging
is not `low_battery`. An unknown battery remains unknown even if charging is true.
For known inputs the first reason must equal B6's existing
`resource_suppression(state_before)`. Implementation reuses that canonical helper
for the primary known-resource reason; any detail collection must be equivalence-tested
against it. B6 and B5 guard semantics themselves do not change. Unknown-resource
suppression is a deliberate stricter B8 autonomous rule, not an owner-command rule.

Apply the same costly-action constraints to reflect: it processes 80 episodes and
writes concepts, and B5 already guards optional reflection using these resource
thresholds. Observe/rest remain eligible for valid state/Q. Neither performs extra
processing or makes a claim of zero whole-cycle energy use. Rest is always in the
resource-eligible set; owner stop overrides even rest. Eligibility is a Boolean
filter, never a utility discount that high Q or epsilon can overcome.

## Q compatibility

Preserve `q_values` columns, keys and historical rows; `Learner.reward()` unchanged;
`new = old + alpha * (reward - old)` unchanged; visits increment once unchanged;
alpha and epsilon settings/defaults unchanged. The reward still reads **state_before**
after the outcome; B8 does not make it an outcome-based reward.

One keyed query freezes all four raw Q values/visits for the existing state key.
Absent rows map to Q=0, visits=0 with `q_missing=true`. Existing rows must contain
finite nonboolean numeric Q and an integer visits >=0 and < SQLite max int; reject
rather than coerce numeric strings, nulls or nonfinite values. The upper visits bound
leaves room for the next increment. No arbitrary historical Q envelope is assumed.
An invalid Q read is fundamental: fail before action with bounded ERROR diagnostic
`invalid_q` or `q_read_error`. Do not reset memory or write utility/zero to repair it.

The adapter retains `score=q_value[selected]`, `values=raw Q map`, visits map, epsilon,
exploration and state key. `candidates` is the actual eligible exploration pool or
exploitation tie set. New `decision_utility` lives only in the B8 record/summary.
`LEARNING.old_value` continues to report raw Q. `Learner.update` still reads the
selected row and applies its existing equation. The core's existing single-writer
assumption applies; external concurrent Q mutation is unsupported, not silently
reconciled by this design. Extreme finite Q that would overflow the unchanged update
is detected by a pre-action calculation of the selected legacy reward/update and
aborts `invalid_q_update`; this guard does not change the equation or persist early.

## Q normalization

| Choice | Assessment |
| --- | --- |
| Normalize by known reward extrema | Normal rewards are bounded but historical Q has no enforced matching domain; cannot assume old rows fit |
| Monotonic saturation `q/(1+abs(q))` | Deterministic, bounded for every finite float, retains graded magnitude without configuration; select |
| Clamp to configured fixed Q range | Requires arbitrary endpoints, flattens all tails, and adds settings/compatibility questions |
| Rank-only contribution | Preserves ordinal preference but discards magnitude and changes component value when another candidate changes |

Define `Q(q) = 0.5 + 0.5 * (q / (1 + abs(q)))`, using finite IEEE-754 double
arithmetic, then clamp only final roundoff into [0,1]. Inputs outside representable
finite double are invalid. Real-number ordering is strictly increasing; finite-double
saturation can tie very large magnitudes. Do not claim strict float ordering at the
tails. Fallback uses **raw** Q ordering, without this saturation.

Literal values: Q(-3)=.125, Q(-1)=.25, Q(0)=.5, Q(1)=.75, Q(3)=.875.
No normalized value is written into the Q table.

## Candidate prediction batching

Compare four independent `predict()` calls (reject: four snapshots/parses) with a
single reusable history snapshot (select). Future
`Predictor.predict_candidates(state_before, actions, *, snapshot)` returns the
four predictions and contributor metadata without reading when a snapshot is
supplied. `DecisionSystem` obtains the snapshot; the pure per-action forecasting
helper is shared with `predict(state, action)`. The old public method retains its
single-action output, math, fallback, 200-row order and direct-call compatibility.

Under the Memory lock, acquire a read transaction, read Q once, then read latest
**200 raw completed transition rows** once, descending ID. Fetch ID, completion
time, action and before/after JSON, not old predictions/errors. Both reads share
one SQLite snapshot. SQL projects Q/visits only when their SQLite types are numeric/
integer, otherwise a fixed invalid marker; it never transfers malformed unbounded
text in those columns. Project historical actions to the four names or a fixed
`unknown_action` sentinel (retaining their global B2 evidence eligibility), and
completion metadata to finite numeric values or null. No arbitrary source strings
are returned. Commit/release before selection telemetry or action. No prior
world-model read occurs here. Do not open a transaction over perception or action.

For B8's bounded reader, each before/after blob is capped at **16,384 UTF-8 bytes**
before transfer/decoding, using SQL byte-length and guarded projection. If any blob
exceeds that limit, mark the entire auxiliary snapshot unavailable (`oversized_history`)
and compute all four predictions with empty history. This avoids silently changing
B2's selected sample population by partial size-based filtering. Ordinary malformed
or non-object in-limit JSON consumes a raw slot and is skipped exactly as B2 does;
no refill. The old public `predict()` is not given a new silent size filter.

Preserve B2 numeric validation, scaled mean, clamps, per-signal action→global→
persistence preference, Boolean frequency/tie and support confidence exactly.
Both before/after dictionaries must decode for inclusion, including network history;
network samples then use only the after Boolean. Do not tighten B2's global-action
sample rule merely because B4 rejects unknown actions. Batch provenance records
which of the frozen rows actually contributed, not a later model summary.

The in-memory snapshot retains at most 200 IDs/completion times and contributor
membership sufficient to certify B2 evidence counts and action/global selection.
None of that row ledger or contributor arrays is durable decision JSON. Persist
only `history={status,reason,cutoff_transition_id,raw_rows_examined}` and the compact
three-target candidate forecasts specified under Decision persistence.

Freshness remains a B8 scoring rule, not a B2 formula change. A historical resource
forecast is usable when count>=2, every contributor completion time is finite,
nonnegative and <= `selected_at`, and the greatest contributor completion time is
no more than **300 seconds** old. Equality at 300 is fresh. Older contributors can
remain in the latest-200 mixture; this tests newest support, not all-sample recency.

For each target, compute transiently and persist only the maximum valid completion
time and its source ID (highest ID breaks equal timestamp ties), plus
`invalid_source_count`, the number of contributors with missing, nonnumeric,
nonfinite or negative timestamps. The maximum includes finite future times, so a
maximum >selected_at identifies future contamination. If no valid times exist,
both newest-source fields are null. Thus count of invalid clocks plus maximum time
preserves the original all-contributors clock check without storing every source.
A nonzero invalid count or future maximum yields status `invalid`; otherwise age>300
yields `stale`. These statuses make risk/uncertainty unsupported without changing B2
forecast math. Persistence/unavailable targets have no contributor timestamps.

This compact provenance explains the score and validates the writer's reported
freshness decision; it cannot reconstruct samples or independently prove their
original values. Do not claim full predictor replayability or rerun history on reads.

An auxiliary read/VM/size/contract failure with valid captured Q produces one
explicit empty-history batch before selection. All four predictions then retain
canonical B2 persistence/unavailable meaning; record the history failure rather
than invent a prediction model. No second database read, future recomputation,
new sensing or network activity is allowed. On an internally malformed batch,
discard all four, use this same deterministic empty-history path and record
`invalid_prediction`. If even canonical empty-history construction fails, abort a
core contract error; do not execute with an uninspectable prediction.

The selected detached payload is frozen before action and passed unchanged to
PREDICTION, B3 and transition persistence. B3 never invokes prediction again.

## Resource-risk semantics

For each candidate and each **usable historical resource forecast**:

```text
clamp01(x) = min(1, max(0, x))
battery_risk = 0 if current charging is exactly true
               else clamp01((40 - predicted_battery_pct) / 40)
load_risk    = clamp01((predicted_load_ratio - 0.5) / 0.5)
disk_risk    = clamp01((20 - predicted_disk_free_pct) / 20)
```

These continuous engineering severities are not probabilities or measured causal
costs. Current charging is an explicit short-horizon assumption; unknown charging
uses the unprotected battery formula. Missing battery forecasts remain missing
even when charging is true. Network has no risk term. Current hard guards use
20/.8/10 independently of these soft forecast ramps (40/.5/20).

For a persistence-only, unavailable, stale or invalid resource forecast, retain its
explicit compact status; raw risk is conceptually unavailable, then use **effective
risk=1**. Do not store a redundant per-target raw-risk dictionary. Missing evidence
cannot become a favorable zero risk. `forecast_resource_risk R` is the arithmetic
mean of the three effective risks, always in [0,1]. This denominator never shrinks.
No current observation is relabeled as supported action-conditioned prediction.

## Uncertainty semantics

`model_uncertainty U` is a versioned **lack-of-evidence-support measure**. For each
of the same three usable resource forecasts, raw uncertainty is
`1 - min(.95, evidence_count / 20)`, identical to `1 - B2 confidence` after validating
its consistency with count. Unsupported targets have no supported raw uncertainty and
**effective uncertainty=1**. The compact forecast status/count/confidence reproduces
this rule; no duplicate per-target raw-uncertainty dictionary is stored. U is the mean over the fixed three targets.

This is not posterior uncertainty, prediction-error calibration or expected information
gain. B4 consistency confidence and contradiction rate are not averaged into it.
Risk measures forecast level; U measures support for that level. They share a forecast
source but measure different properties; count is rewarded once, not added again as
another confidence component. Missing penalties deliberately reduce both unsupported
level benefit and unsupported confidence benefit; they are policy defaults, not two
independent statistical observations.

## Information / processing-opportunity ruling

**No information-gain or processing-opportunity component in v1.** Observe already
gets the same two perceptions as rest/reflect/consolidate; no extra information bonus
is justified. Reflection's eight qualifying samples indicate potential summary work,
not fresh observations. Accurate consolidation opportunity requires B6 eligibility
(n>=8, confidence>=.30), validation, existing-record fingerprint/status and cyclic
cursor semantics. A second preflight engine would duplicate substantial logic.
Even sufficient samples can reproduce unchanged summaries. Do not add those reads,
a shared opportunity helper or a no-work penalty in B8 v1. Supported actions can
legitimately do no substantive work; their action/audit records remain truthful.

## Processing-cost ruling

Compare: (1) no scalar, hard guards plus forecast risk; (2) fixed versioned
**processing-cost proxy** for known code paths; (3) measured runtime/energy costs.
Select (1). Reflect reads up to 80 episodes; consolidation processes up to 100 beliefs
and checkpoint work, but these bounds do not establish comparable energy units.
Option (2) adds another arbitrary preference and risks double counting the costly-action
guards; (3) needs an explicit later measurement effort. No cost proxy or measured-cost
field is populated with fabricated values. Different existing delays remain real,
but no immediate prediction pretends to model the whole rest interval.

## Component catalog

| Component | Range/meaning | Source/normalization | Weight in utility | Availability/missing rule | Duplication ruling |
| --- | --- | --- | --- | --- | --- |
| `q_component` | [0,1], bounded legacy preference | Raw Q; saturating transform above | .50 | Missing row uses existing 0 Q; corrupt existing Q aborts | Only learned-reward term |
| `forecast_resource_risk` | [0,1], mean engineering severity | Three B2 forecast levels; ramps above | .35 on complement | Fixed denominator; unsupported risk effective 1 | No weighted current-risk term |
| `model_uncertainty` | [0,1], mean lack of support | Three B2 evidence counts/confidences | .15 on complement | Fixed denominator; unsupported uncertainty effective 1 | No B4/B6/B7 confidence terms |
| Current resource risk | No scalar | Current resources drive hard eligibility | None | Unknown costly actions constrained | Avoid duplicate current-state penalty |
| Information gain / processing opportunity | Not available as unique gain | No selected source | None | Excluded | No invented observation advantage |
| Processing-cost proxy / energy cost | Not selected / not measured | No selected source | None | Excluded | No arbitrary second costly-action penalty |
| Goal progress / B5 curiosity | Unavailable at selection | No selected source | None | Excluded | No future or nonexistent evidence |

## Exact utility equation and weights

```text
decision_utility(a) = clamp01(0.50 * Q(a) + 0.35 * (1 - R(a)) + 0.15 * (1 - U(a)))
```

Constants are fixed by `decision_v1`, `model_version=1`, `weights_version=1`.
No user settings, learned tuning or normalization over candidates are introduced.
All components are dimensionless in [0,1]; weights total 1; utility is in [0,1].
Use finite double arithmetic with the displayed operation order; no display rounding
before ranking. Only final roundoff is clamped. Store actual finite computed values.

Q receives half the total range to retain substantial learned preference; forecast
level receives .35 and support .15 so established resource evidence can outweigh a
moderate Q advantage. These are reviewable policy choices, not measured optimal
weights. No component can dominate accidentally through raw units. In partial evidence
there is no weight redistribution. When **no eligible candidate has even one usable
historical resource forecast**, use eligible raw-Q fallback instead of this ranking.
Still store the hypothetical components/utility for audit; `policy_basis=legacy_q`
makes clear that they did not determine the winner.

## Exploration and tie-breaking

Read applied epsilon once; require finite nonboolean [0,1]. Invalid configuration
aborts before action. Draw `u=random()` once from an injected RNG, require 0<=u<1.
Exploration occurs exactly when `u < epsilon`; epsilon 0 never explores, epsilon 1
always explores, and u==epsilon does not explore. This draw is separate from choice.

Construct `selection_candidates` in canonical action order after hard constraints:

- Exploration: every eligible action.
- Composite exploitation: eligible actions whose stored computed utility is within
  **absolute 1e-12** of the eligible maximum. No relative/transitive tie grouping.
- Legacy-Q fallback exploitation: eligible actions exactly equal to maximum eligible
  **raw Q**. No tolerance or normalized-Q substitution.

If the pool has one member, select it without calling choice. If it has multiple
members, call the same injected RNG's uniform `choice(selection_candidates)` exactly
once. Validate that the returned action belongs to the pool. The interface has no
other stochastic selection operation. Runtime randomness is intentional; acceptance
fixtures inject exact draws and choices. No hidden fixed action preference exists
in tie handling. Rest is not favored merely because Q or utility ties.

`choice_index` is an integer index into **selection_candidates** whenever choice
was called, including exploration, composite exploit ties and raw-Q fallback ties.
It is null exactly when that pool has one member. Do not index eligible_actions
instead for a smaller exploitation tie pool. This also applies to defensive singleton
rest fallback and singleton exploration. Record epsilon draw regardless of pool size.

`selection_mode=explore` whenever epsilon fires, including degraded evidence;
otherwise `exploit` for composite or `fallback` for legacy-Q basis.
`policy_basis=composite|legacy_q` and fallback_reason remain separate: degradation
never secretly disables epsilon. Hard-constrained actions enter neither exploration
nor tie pools. Legacy `Learner.choose()` remains unchanged; raw-Q ties now preserve
its random-choice semantics while B8 excludes constrained candidates first.

## Missing/corrupt evidence fallback

| Situation | Exact behavior |
| --- | --- |
| Some resource predictions usable | Composite ranking; unsupported targets effective R/U=1; retain compact forecast statuses |
| All eligible resource predictions unsupported, including pure persistence | Legacy raw-Q ordering under constraints; `fallback_reason=no_supported_resource_forecast` |
| Auxiliary snapshot read/VM/size failure | Empty-history canonical B2 batch; legacy-Q basis; failure reason from fixed enum |
| Invalid optional candidate batch | Discard batch, canonical empty-history predictions; `fallback_reason=invalid_prediction` |
| Absent/corrupt B4, B6 or B7 | No effect; they are not read by B8 |
| Missing current resource fields with legacy-compatible shape | Preserve presence, constrain costly actions; observe/rest remain; prediction follows B2 unknown rules |
| Malformed current state, Q, epsilon, RNG or candidate identity | Bounded ERROR; abort before action, no Q/experience/decision insert |
| Unexpected empty eligible set with otherwise valid contract and no stop | Reassert resource-safe rest as sole eligible action; `policy_basis=legacy_q`, `fallback_reason=no_eligible_candidate`; all components still recorded; do not override an invalid-Q or owner-stop abort |
| Stale selection age >5s | Nonfatal skipped cycle, fixed stale_decision diagnostic, retry after the captured observe_interval; no completed-cycle effects |
| Owner stop | Explicit stopped result; terminate without retry or another action, including rest |
| Failed read-transaction cleanup | Abort storage error; never continue on an unsafe connection |
| Corrupt previously stored decision | Read API returns explicit unavailable/corrupt status; no rescoring or rewrite |

Auxiliary fallback reasons, in priority order, are `history_read_error`,
`history_budget_exceeded`, `oversized_history`, `invalid_prediction`, then
`no_supported_resource_forecast`; `no_eligible_candidate` overrides those for the
structural defensive case. Only one bounded reason is stored; per-signal status and
history status retain detail. Fundamental errors are diagnostics, not fake decisions.
A normal fallback still respects epsilon; fixed-RNG acceptance makes it deterministic.

## Low-disk mismatch resolution

With `disk_free_pct <10`, B6 would suppress semantic work, but legacy reward still
adds .8 for consolidate (other terms may also apply). **Keep that reward unchanged.**
Constrain autonomous consolidate before selection using the same known-resource
suppression rule. High historical Q, high utility and epsilon cannot select it.
Reflect is also constrained; observe/rest remain resource-eligible. The low-disk
reward contribution on the eventual selected action remains −.2.

Owner consolidate still reaches the existing owner handler and B6 engine, using its
existing latest-state/provenance rules. It can record `low_disk` suppression and its
checkpoint without a transition/Q update. Autonomous selectability does not grant or
remove owner-command availability. A B7 static action catalog is not current eligibility.
This is a **designed resolution only**. Do not close the implemented issue or rewrite
`docs/review-follow-ups.md` until future implementation and acceptance prove it.

## Cycle ordering

1. Preserve settings application and inferred-wake handling. Check stop; take the
   existing detached pre-observation and PERCEPTION event. Validate legacy-compatible
   input; capture monotonic observation time, wall `selected_at`, applied epsilon/alpha
   and current `observe_interval` for this attempt. Generate decision_id for correlation.
2. Under one lock/read transaction: state key, one Q query, one raw-history query.
   Release/restore the connection before computation/telemetry. No B4/B6/B7 reads.
3. Compute all four B2 predictions from the frozen history, validate the transient
   source metadata and compact projections, and apply only documented auxiliary
   fallbacks. Fundamental storage/Q/contract errors still raise; expiry never masks them.
4. Check owner stop first, then age. More than **5 monotonic seconds** since the
   pre-observation returns the skipped result below before RNG/selection telemetry.
   Otherwise calculate constraints/components, choose via the injected RNG contract,
   and freeze the exact selected prediction plus its canonical SHA-256 digest.
5. Check stop and age again before the successful-selection DECISION event. Emit
   DECISION and selected PREDICTION using the frozen result; preserve the raw-Q runtime
   adapter and existing ACTION-start telemetry. Check stop and age immediately before
   dispatch. A late expiry after telemetry emits the explicit terminal skipped diagnostic
   with the same decision_id; no ACTION-complete or durable decision is invented. Only
   after the final stop/age guard passes, perform the existing pure finite Q-update
   preflight immediately before dispatch; stale attempts never reach reward preflight.
6. Only after those checks, perform the existing action; ACTION complete; second
   perception; outcome; B3 evaluates **the exact same selected prediction**. No
   resnapshot/regeneration or post-outcome selection scoring.
7. Read B5's at-most-eight prior published beliefs; assess curiosity before the current
   transition changes B4. Preserve B3/B5 formulas and event meanings.
8. Compute existing reward from state_before; ordinary Learner.update; obtain new raw
   Q. Validate frozen prediction digest again and atomically insert episode, transition,
   full selected prediction/evaluation, B4 queue, B5 assessment and compact decision
   record. Utility is never a learning target.
9. Preserve CURIOSITY summary, bounded B4 recovery, LEARNING/MEMORY, metadata, optional
   claimed B5 reflection, B7 publication and final runtime telemetry.
10. Return an explicit immutable `CycleResult(status, delay_seconds, reason)` with
    the disjoint meanings below; do not overload None as a whole cycle result.

| Result | delay_seconds | reason | run() behavior |
| --- | --- | --- | --- |
| `completed` | Existing selected-action delay | null | Normal interruptible wait, then next autonomous cycle |
| `skipped` | This attempt's applied observe_interval, integer 8..3600 (default 8) | `stale_decision` | Same interruptible wait, then fresh perception in a new cycle |
| `stopped` | null | `owner_stop` | Terminate loop immediately; no retry |
| Fatal storage/Q/contract failure | No result; raises | Existing bounded ERROR reason | Existing fatal error/shutdown path |

Expiry equality at 5 seconds remains valid; only >5 skips. A skipped attempt performs
**no action, reward evaluation/update, Q write/visit, experience episode, transition,
decision record, second perception, B3 evaluation, B4 update, B5 assessment/attention,
B6 consolidation or B7 publication**. Existing prior self-model records remain unchanged, not deleted.
Startup/inferred-wake bookkeeping retains its separate existing meaning.

On expiry emit exactly one bounded diagnostic, clear current_action/action_started_at,
set runtime activity idle and next_observation_at to now+retry delay, and preserve
last successful action/reward/cycle and last_error. An already emitted last_decision
is selection-attempt provenance, not completion; its diagnostic explicitly expires
it. No ERROR event, lifecycle ERROR, failed-process flag or shutdown is caused by
ordinary stale expiry. A genuine diagnostic/storage failure remains fatal.

`run()` first checks stop_event again after receiving a result, exiting even if a
skipped/completed result was already produced. Otherwise it captures one monotonic
deadline at return plus result.delay_seconds and uses
its existing stop-event wait (<=2-second heartbeat/command polling slices). Do not
subtract elapsed selection time from the retry delay or re-enter selection inside
the same cycle. Thus repeated expiry attempts are at least observe_interval apart,
with no busy loop, new scheduler/thread or new setting. Changed settings apply at
the next cycle; this wait uses the captured value. Owner commands may still run
through their separate existing path while waiting. Owner stop wins every guard and
interrupts the wait immediately; it is never converted into stale retry. Invalid or
backwards/nonfinite monotonic readings are a fatal clock contract error, not expiry.

The selected prediction remains immutable through successful completion. Its full
payload lives in the linked transition; the compact decision keeps the digest.
Actions, telemetry and the separately committed Q update can still precede a later
experience-transaction failure. No whole-physical-cycle transaction or causal effect
of an internal action on external resources is claimed.

## Decision persistence

| Choice | Evaluation |
| --- | --- |
| DECISION/runtime only | Events expire and runtime is current-only; loses durable transition evidence |
| Nullable JSON on transitions | Atomic linkage, but alters the established row and mixes growing contracts |
| New transition-keyed decision_records | Additive, naturally absent historically, clear compact contract; retain this choice |

One compact record per future completed autonomous transition. No writes on owner
commands, startup, reads, failed action/post-observation, stopped or stale skipped
attempts. Generate a 32-character lowercase hexadecimal decision_id before evidence
work for attempt/event correlation. It is not a guessed transition ID. Attach the
actual new transition ID during the experience transaction. created_at is insertion
wall time; selected_at is selection-start wall time captured after pre-observation,
before evidence acquisition. Wall clocks can reverse: no created_at>=selected_at rule.

The durable record limit is **16,384 UTF-8 bytes**, encoded with
`json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
allow_nan=False).encode('utf-8')`. Strict JSON rejects duplicate/unknown keys,
nonfinite values and Boolean-as-number. Depth<=8, arrays<=4 elements, total object
keys plus array elements<=512; strings<=128 UTF-8 bytes and exact enums where defined.
The three resource targets are a fixed object, not an open-ended registry. No source
row ledger, contributor arrays, full B2 prediction copy, network forecast, episodes,
notes, hostnames, paths, tokens or free-form errors appear in the record.

Exact fields and domains:

- Top level: `model`, `model_version`, `weights_version`, `decision_id`, `transition_id`,
  `created_at`, `selected_at`, `state_key`, `current`, `history`, `prediction_contract`,
  `selected_prediction_sha256`, `epsilon`, `alpha`, `random_draw`, `choice_index`,
  `policy_basis`, `selection_mode`, `eligible_actions`, `selection_candidates`,
  `selected_action`, `fallback_reason`, `candidates`. Model=decision_v1 and versions=1.
  No B8 record has shipped; this amendment revises the proposed v1 contract without
  introducing a migration between two nonexistent B8 implementations.
- IDs are exact integers 1..2^63−1; timestamps finite nonnegative numbers. Epsilon[0,1],
  alpha(0,1], draw[0,1). `current` includes only present battery_pct, charging,
  load_ratio, disk_free_pct, local_hour with the existing State/constraints domains;
  network is omitted because it neither determines utility nor state_key. State_key
  must match this projection. Missing fields remain absent. No separate raw-risk or
  raw-uncertainty dictionaries are stored; effective defaults derive from status.
- `prediction_contract`: exactly model=transition_delta_v1, model_version=1,
  horizon=next_post_action_observation. One common envelope defines the interpretation
  of all candidate resource projections; it is not four full prediction copies.
- `history`: exactly status, reason, cutoff_transition_id, raw_rows_examined.
  Status=`ok|empty|unavailable`. Count is an exact integer 0..200: raw rows materialized
  by the bounded read before any discard. Ok requires count 1..200, cutoff highest
  materialized ID, reason null. Empty requires count 0/cutoff null/reason null.
  Unavailable requires a reason from history_read_error, history_budget_exceeded,
  oversized_history, invalid_prediction. Read/budget errors before a completed fetch
  report count 0/cutoff null; post-fetch size/batch rejection retains its known count
  and cutoff, even though the effective forecasting history becomes empty. Count 0
  iff cutoff null. Never guess a cutoff after a failed read. Cutoff<current transition ID.
- `candidates`: exactly the four canonical actions. Each has exactly eligible,
  constraint_reasons, q_value, visits, q_missing, components, decision_utility,
  resource_forecasts. Boolean eligibility/missing flags; raw Q finite; visits integer
  in the compatible range; q_missing=true implies Q0/visits0. Reasons are the fixed
  ordered guard enums. Components has exactly q_component, forecast_resource_risk,
  model_uncertainty, each finite[0,1]; utility finite[0,1]. Writer checks formulas and
  guards against frozen evidence; readers validate stored facts without rescore.
- `resource_forecasts`: exactly battery_pct, load_ratio, disk_free_pct. Each target
  has exactly status, value, method, evidence_count, confidence,
  newest_source_transition_id, newest_source_completed_at, invalid_source_count.
  Status=`usable|persistence|unavailable|stale|invalid`. Value follows B2 numeric
  domains, or null only for unavailable. Method=`action_mean_delta|global_mean_delta|
  persistence` or null only for unavailable. Count 0/confidence 0 for unavailable or
  persistence; otherwise count 2..200 and confidence=min(.95,count/20). Count cannot
  exceed history.raw_rows_examined. Confidence means evidence_support, fixed by the
  shared contract, not a second independently measured number.
- For historical methods: invalid_source_count is integer 0..evidence_count and
  counts unusable clock metadata, not missing numeric samples. If all contributor
  clocks are invalid, both newest-source fields are null. Otherwise they are the
  maximum valid contributor completion time and its ID (highest ID on equal time).
  ID<=history cutoff and <linked transition ID. Invalid count>0 or a maximum later
  than selected_at makes status invalid; otherwise age>300 makes stale; else usable.
  Null source fields are also required for persistence/unavailable, with invalid
  count 0. History empty/unavailable admits only persistence/unavailable projections.
  A stale/invalid projection retains its actual forecast/support facts, but contributes
  effective risk1/uncertainty1. Unavailable current value stores value/method null,
  never a synthetic zero. All usable status rules retain the original fixed denominator.
- All action lists are unique canonical-order subsets. Selected action is in the
  eligible list and selection_candidates. Writer certifies the exact pool (eligible
  exploration, tolerant utility maxima or exact raw-Q maxima). More than one pool
  member requires choice_index in 0..len(pool)−1 and selected_action=pool[index]; a
  singleton requires index null and that sole action. Mode/basis/epsilon/fallback
  reason consistency follows the selection contract; no fixed tie priority remains.
- `selected_prediction_sha256`: exactly 64 lowercase hex characters; canonical hash
  rule below. SQL model/version/action/mode/created_at/transition mirrors must match
  JSON; record selected_action matches linked transition.action. This digest links
  the full selected prediction only; it is not a signature/authenticity claim about
  the entire record or a replacement for predictor working evidence.

The full selected B2 prediction's authoritative durable location remains
**transitions.prediction_json**. Compute its digest before action over exactly:

```text
canonical = json.dumps(selected_prediction, sort_keys=True,
                       ensure_ascii=True, allow_nan=False).encode('utf-8')
selected_prediction_sha256 = hashlib.sha256(canonical).hexdigest()
```

This is the existing prediction serializer: default separators (including spaces),
not the compact record encoding. No hashing raw SQL whitespace, no numeric coercion,
no rounding (80 and80.0 have different canonical bytes). Validate the original B2
payload first, compute and freeze the digest with the selected payload, and verify
again before dispatch and before persistence. Digest mismatch then is a fatal mutation
contract error, not stale retry. Pass that same full payload unchanged to PREDICTION,
B3 and transition storage; the record stores only its digest and compact projections.

Full selected B2 validation retains the original envelope action/signals/model/
model_version/horizon and four signals. Numeric predicted fields are status/value/
method/clamped/evidence_count/confidence/confidence_kind; methods are action_mean_delta,
global_mean_delta or persistence. Boolean predicted fields omit clamped and add
probability_true only for action_boolean_frequency/global_boolean_frequency; otherwise
method=persistence. Unavailable fields are status/reason/evidence_count/confidence/
confidence_kind only; reason missing_current_value or invalid_current_value.
Confidence kind=evidence_support, count 0 for persistence/unavailable else 2..200,
confidence=min(.95,count/20); value/probability domains remain B2's. All batch payloads
receive this in-memory validation before projection; unselected full payloads are
not written to decision_records. Full B2 payload limit remains 16,384 bytes.

Validate frozen compact evidence and its selected digest before the transaction.
After inserting the transition, attach actual transition ID/insertion time, validate
and serialize the complete compact record before its insertion in the same transaction.
Final size/linkage failure rolls back the entire experience group; no truncation or
invented completion. Earlier Q/action effects retain their existing failure boundary.
On list/detail reads strictly parse the linked full selected prediction, validate its
contract, reserialize with the canonical rule and require the digest to match. A
mismatch makes the record corrupt. Also compare the selected projection's B2 value,
method/count/confidence to the selected transition prediction, not to regenerated
history. A matching digest establishes linkage, not proof of the omitted samples.

`decision_records` grows one compact record per completed autonomous transition;
B8 introduces no pruning. The payload is deliberately minimized, but lifetime growth
remains unbounded until a separately designed retention policy exists.

Healthy full example: Q(reflect)=1, all candidates R0/U.9 from two global zero-delta
samples (latest support ID2 at998); utility reflect=.74, other actions=.615. Unique
winner reflect consumes no choice call and stores choice_index=null. The selected
full B2 prediction has numeric values80.0/.2/50.0, global_mean_delta, count2,
confidence .1, clamped=false; network=true with global_boolean_frequency,
probability_true1.0/count 2/confidence .1. This defines the full canonical digest input. The full compact record encodes to
**4,195 bytes**; its SHA-256 linkage is shown explicitly below.

<!-- B8_HEALTHY_JSON -->
```json
{
  "model": "decision_v1",
  "model_version": 1,
  "weights_version": 1,
  "decision_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "transition_id": 3,
  "created_at": 1002,
  "selected_at": 1000,
  "state_key": "high|calm|ok|day",
  "current": {
    "battery_pct": 80,
    "charging": false,
    "load_ratio": 0.2,
    "disk_free_pct": 50,
    "local_hour": 12
  },
  "history": {
    "status": "ok",
    "reason": null,
    "cutoff_transition_id": 2,
    "raw_rows_examined": 2
  },
  "epsilon": 0.15,
  "alpha": 0.18,
  "random_draw": 0.5,
  "choice_index": null,
  "policy_basis": "composite",
  "selection_mode": "exploit",
  "eligible_actions": [
    "observe",
    "reflect",
    "consolidate",
    "rest"
  ],
  "selection_candidates": [
    "reflect"
  ],
  "selected_action": "reflect",
  "fallback_reason": null,
  "candidates": {
    "observe": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 0,
      "visits": 0,
      "q_missing": true,
      "components": {
        "q_component": 0.5,
        "forecast_resource_risk": 0,
        "model_uncertainty": 0.9
      },
      "decision_utility": 0.615,
      "resource_forecasts": {
        "battery_pct": {
          "status": "usable",
          "value": 80.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "usable",
          "value": 0.2,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "usable",
          "value": 50.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        }
      }
    },
    "reflect": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 1,
      "visits": 4,
      "q_missing": false,
      "components": {
        "q_component": 0.75,
        "forecast_resource_risk": 0,
        "model_uncertainty": 0.9
      },
      "decision_utility": 0.74,
      "resource_forecasts": {
        "battery_pct": {
          "status": "usable",
          "value": 80.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "usable",
          "value": 0.2,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "usable",
          "value": 50.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        }
      }
    },
    "consolidate": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 0,
      "visits": 0,
      "q_missing": true,
      "components": {
        "q_component": 0.5,
        "forecast_resource_risk": 0,
        "model_uncertainty": 0.9
      },
      "decision_utility": 0.615,
      "resource_forecasts": {
        "battery_pct": {
          "status": "usable",
          "value": 80.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "usable",
          "value": 0.2,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "usable",
          "value": 50.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        }
      }
    },
    "rest": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 0,
      "visits": 0,
      "q_missing": true,
      "components": {
        "q_component": 0.5,
        "forecast_resource_risk": 0,
        "model_uncertainty": 0.9
      },
      "decision_utility": 0.615,
      "resource_forecasts": {
        "battery_pct": {
          "status": "usable",
          "value": 80.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "usable",
          "value": 0.2,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "usable",
          "value": 50.0,
          "method": "global_mean_delta",
          "evidence_count": 2,
          "confidence": 0.1,
          "newest_source_transition_id": 2,
          "newest_source_completed_at": 998,
          "invalid_source_count": 0
        }
      }
    }
  },
  "prediction_contract": {
    "model": "transition_delta_v1",
    "model_version": 1,
    "horizon": "next_post_action_observation"
  },
  "selected_prediction_sha256": "4e37f7a1986ae0c28236684ed04cd8865f121082d1d3a4893c5cbc202c28d1a9"
}
```

Degraded full example: empty history/current disk5, Q(consolidate)=100 but costly
actions constrained; Q(observe)=Q(rest)=1, pool[observe,rest], injected choice_index0
selects observe in raw-Q fallback (epsilon.15, draw.5). Both eligible utilities=.375;
consolidate's hypothetical utility=.4975247524752475 cannot override its constraint.
The selected full B2 payload has numeric persistence values80.0/.2/5.0, clamped=false,
count 0/confidence 0.0; network=true persistence, count 0/confidence 0.0 and no probability.
The compact record has no copy of that full payload; its digest links the transition.
It encodes to **4,292 bytes**. Both complete records satisfy the 16,384-byte cap.

<!-- B8_DEGRADED_JSON -->
```json
{
  "model": "decision_v1",
  "model_version": 1,
  "weights_version": 1,
  "decision_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "transition_id": 1,
  "created_at": 1002,
  "selected_at": 1000,
  "state_key": "high|calm|tight|day",
  "current": {
    "battery_pct": 80,
    "charging": false,
    "load_ratio": 0.2,
    "disk_free_pct": 5,
    "local_hour": 12
  },
  "history": {
    "status": "empty",
    "reason": null,
    "cutoff_transition_id": null,
    "raw_rows_examined": 0
  },
  "epsilon": 0.15,
  "alpha": 0.18,
  "random_draw": 0.5,
  "choice_index": 0,
  "policy_basis": "legacy_q",
  "selection_mode": "fallback",
  "eligible_actions": [
    "observe",
    "rest"
  ],
  "selection_candidates": [
    "observe",
    "rest"
  ],
  "selected_action": "observe",
  "fallback_reason": "no_supported_resource_forecast",
  "candidates": {
    "observe": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 1,
      "visits": 4,
      "q_missing": false,
      "components": {
        "q_component": 0.75,
        "forecast_resource_risk": 1,
        "model_uncertainty": 1
      },
      "decision_utility": 0.375,
      "resource_forecasts": {
        "battery_pct": {
          "status": "persistence",
          "value": 80.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "persistence",
          "value": 0.2,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "persistence",
          "value": 5.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        }
      }
    },
    "reflect": {
      "eligible": false,
      "constraint_reasons": [
        "low_disk"
      ],
      "q_value": 1,
      "visits": 4,
      "q_missing": false,
      "components": {
        "q_component": 0.75,
        "forecast_resource_risk": 1,
        "model_uncertainty": 1
      },
      "decision_utility": 0.375,
      "resource_forecasts": {
        "battery_pct": {
          "status": "persistence",
          "value": 80.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "persistence",
          "value": 0.2,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "persistence",
          "value": 5.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        }
      }
    },
    "consolidate": {
      "eligible": false,
      "constraint_reasons": [
        "low_disk"
      ],
      "q_value": 100,
      "visits": 4,
      "q_missing": false,
      "components": {
        "q_component": 0.995049504950495,
        "forecast_resource_risk": 1,
        "model_uncertainty": 1
      },
      "decision_utility": 0.4975247524752475,
      "resource_forecasts": {
        "battery_pct": {
          "status": "persistence",
          "value": 80.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "persistence",
          "value": 0.2,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "persistence",
          "value": 5.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        }
      }
    },
    "rest": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 1,
      "visits": 4,
      "q_missing": false,
      "components": {
        "q_component": 0.75,
        "forecast_resource_risk": 1,
        "model_uncertainty": 1
      },
      "decision_utility": 0.375,
      "resource_forecasts": {
        "battery_pct": {
          "status": "persistence",
          "value": 80.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "load_ratio": {
          "status": "persistence",
          "value": 0.2,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        },
        "disk_free_pct": {
          "status": "persistence",
          "value": 5.0,
          "method": "persistence",
          "evidence_count": 0,
          "confidence": 0.0,
          "newest_source_transition_id": null,
          "newest_source_completed_at": null,
          "invalid_source_count": 0
        }
      }
    }
  },
  "prediction_contract": {
    "model": "transition_delta_v1",
    "model_version": 1,
    "horizon": "next_post_action_observation"
  },
  "selected_prediction_sha256": "4dc446ec70f9233e55914f9d25157da1d6ccf9b4b0bb8979642a87cb980732de"
}
```

## Schema / migration proposal

**Proposed schema 7; current schema remains 6.** Add only this table, using the
existing SQLite foreign-key/backup/migration conventions:

```sql
CREATE TABLE decision_records (
    transition_id INTEGER PRIMARY KEY REFERENCES transitions(id),
    created_at REAL NOT NULL,
    model TEXT NOT NULL CHECK(model = 'decision_v1'),
    model_version INTEGER NOT NULL CHECK(model_version = 1),
    selected_action TEXT NOT NULL
        CHECK(selected_action IN ('observe','reflect','consolidate','rest')),
    selection_mode TEXT NOT NULL
        CHECK(selection_mode IN ('exploit','explore','fallback')),
    data_json TEXT NOT NULL
        CHECK(length(CAST(data_json AS BLOB)) <= 16384)
);
```

Primary-key traversal supplies list/detail access; no secondary index, free-text
search or filtered scan is required. Application validation adds finite-number,
strict JSON, field and cross-link rules that this DDL alone cannot enforce.
`Memory.record_transition_experience(..., decision=None)` remains compatible with
old callers. Autonomous B8 supplies the frozen payload; storage attaches its actual
new transition ID and insertion time and inserts it in the **same existing transaction**
as experience, prediction/evaluation, curiosity and world eligibility. Other callers
retain absence. Failure rolls back that entire group, not the earlier Q/action effects.

Preserve every old table/row, including Q, identity, schema-era null prediction fields,
semantic history and stored B7 snapshot. No defaults/backfill manufacture past
selection evidence. Upgrade supported unversioned and v1–v6 databases through the
existing ladder; back up existing Memory before mutation; failure prevents upgrade.
A v7 reopen is a no-op; unsupported/future/ambiguous versions fail before writes.

Two specific ladder hazards require future edits: include **6** explicitly in the
supported version set when VERSION becomes 7, and make the existing v5→v6 step write
literal 6 and set local `version=6` before the new v6→v7 step. Do not let that earlier
step write the new global VERSION and accidentally skip v7. Final-step failure must
roll back all applied steps from every older version. Operator startup must require
the new table at current schema without migrating from inspection.

Rollback means restore a verified pre-upgrade backup under separately authorized
recovery, keeping newer data separately; reverting source does not downgrade a v7 DB.
No live migration, backup or restoration is authorized by this design phase.

## Decision telemetry

Successful-selection events use the contract below; stale expiry instead emits one
terminal diagnostic in the existing DECISION category, source=decision, message
`Decision attempt expired`. Its exact payload is model, model_version, decision_id,
status=`skipped`, reason=`stale_decision`, phase=`before_selection_event|before_dispatch`,
retry_delay_seconds (captured observe_interval). Cap: **512 UTF-8 bytes** using compact
strict JSON. This event identifies an attempt, never an action completion; it has no
transition ID, raw payloads or utility dump. The same decision_id explicitly expires
any earlier DECISION/PREDICTION/ACTION-start telemetry after a late guard failure.
Normal expiry occurs before successful-selection telemetry when possible. No ERROR
category is used for ordinary expiry, so B7 failure counts are not polluted by it.

For successful selection extend the existing **DECISION** category; emit one event
before action, not four candidate events or a new parallel category. The terminal
skipped diagnostic is an additional event only when a previously announced attempt
expires; it is necessary to make the incomplete attempt explicit. Source becomes `decision`; message
`Internal action selected`. Payload <= **2,048 UTF-8 bytes**. Exact fields:
`model`, `model_version`, `decision_id`, `state_key`, `selected_action`,
`selection_mode`, `policy_basis`, `eligible_actions`, `constraint_reasons` (four-action
map), `q_value`, `decision_utility`, `epsilon`, `fallback_reason`. No full prediction,
raw history, notes or source blobs. Strict fields and numerical rules mirror the
record. Transition ID is unavailable then; correlate by decision_id once committed.

Existing selected **PREDICTION** event remains the full bounded B2 payload, unchanged
in meaning. Runtime `last_decision` retains the legacy adapter's raw-Q fields, so
current learning inspection does not read a utility as Q. Do not add four predictions
to runtime or change the frontend. `LEARNING.old_value/new_value` remain raw Q.
Bounded existing ERROR diagnostics cover fundamental pre-action failures. No completed
record is fabricated just to attach an aborted selection event. Existing retention
still applies to events; durable decision evidence belongs to the new table.

## Read-only inspection API

Future `DecisionReadService(ReadStore)` and delegations/routes provide only:

- `GET /api/decisions?before=<id>&limit=<n>`: newest first, **inclusive** positive
  signed-64-bit cursor; default limit 20, max **50**, min 1. No other filters/order
  parameters. Fixed parameterized SQL, `transition_id <= ? ORDER BY transition_id DESC`.
  Fetch limit+1 primary-key metadata rows; use the first lookahead ID as next_cursor.
  Read/validate payloads for the first limit rows only; never refill past corrupt rows.
- `GET /api/decisions/{transition_id}`: one exact positive signed-64-bit ID.
  Return the full validated record with source transition linkage and verify selected
  prediction digest. No history rescan, inference or decision rescoring.

Validate identical bounds for direct Python and HTTP callers; reject unknown query
keys, repeated scalar keys, nonintegers, nonfinite numbers and oversized IDs with 422.
No action filter is offered because an unindexed filtered scan would violate the
raw-window bound. Reads use SQLite `mode=ro`, zero busy timeout, one read snapshot,
fixed table-name metadata query and `SELECT version ... LIMIT 2`; never instantiate
Memory, probe processes, call service.status, perceive, publish B7, migrate or write.

For each page row use a PK join to its transition. Transfer at most **16,385 bytes
for each of the compact record, linked selected prediction and state_before** (one
sentinel beyond each 16,384-byte limit). Total payload cap: 49,155 bytes per item,
2,457,750 bytes for a 50-item page, plus bounded scalar metadata. No source-history
rows are loaded. History cutoff/newest-source IDs must precede linked transition ID;
newest-source IDs cannot exceed the stored cutoff.

Strictly validate field sets, types/domains, SQL mirrors, count/confidence/freshness
consistency, eligible/pool membership, choice-index/mode/draw semantics, and selected
projection equality to the linked full prediction's value/method/count/confidence.
Require the selected-prediction canonical SHA-256 digest to match; mismatch is corrupt.
Current's five-key projection must match the linked state_before projection. Reject
oversized or malformed linked evidence without refill. The full selected prediction
is read for digest validation only; detail returns the compact record, not another
copy of that payload. It remains stored authoritatively in the transition.

The read validator never calls the predictor or scorer, reconstructs unselected
predictions, recalculates Q/R/U/utility, or reranks a historical decision. It validates
the frozen reported components, pool and provenance, not a newly computed choice.
Full formula/pool certification belongs to the pre-action writer and deterministic
acceptance; a compact audit is not full replay or a tamper-proof evidence signature.

List envelope: exactly `available`, `status`, `reason`, `items`, `next_cursor`.
Available schema-7 list status=`stored`, reason=null, including an empty table.
Each valid item is a <=1,024-byte summary containing exactly `available=true`, `status=stored`,
`reason=null`, `transition_id`, `created_at`, `selected_at`, `model`, `model_version`,
`selected_action`, `selection_mode`, `policy_basis`, `eligible_actions`,
`constraint_reasons`, `q_value`, `decision_utility`, `fallback_reason`, `decision_id`.
No candidate payloads in a list. A corrupt row produces only
`{available:false,status:"error",reason:"invalid_decision",transition_id:<id>}`;
its ID consumes the page budget and advances pagination normally. No partial trusted
summary is emitted from a corrupt payload.

Detail envelope: exactly `available`, `status`, `reason`, `transition_id`, `record`.
A valid detail is true/stored/null with full record. An existing corrupt record is
HTTP 200 false/error/invalid_decision with record=null. A missing decision at schema7
is HTTP 404 `decision_not_found`; historical absence is legitimate, not backfilled.
Legacy/unversioned or v1–v6 reads return HTTP 200 unavailable/legacy_schema, empty list
or detail record=null. A missing home is unavailable/missing_home and is never created.
Unknown/ambiguous/future schema returns 409 incompatible_schema; schema7 missing the
required table returns unavailable/error with reason missing_decision_table, never
an upgrade. Busy/SQL-budget failure returns 503 decision_read_unavailable. Response
bytes capped at **53,248 list (52 KiB)**, **17,408 detail (17 KiB)**; reject excess rather than truncate
valid evidence. Encode responses with the same compact strict JSON encoding as
records. Fifty 1,024-byte summaries plus commas and the fixed envelope fit below
53,248 bytes; a 16,384-byte record plus the fixed detail envelope fits below 17,408.
No full selected prediction is returned, so a second 16 KiB response allowance is
unnecessary. The API describes stored selection time, not current policy.

At most four SELECTs per request: table metadata, version, list metadata (or direct
payload join for detail), one batch PK payload join for list. Up to 51 metadata rows
and 50 payload joins; no COUNT, OFFSET, unbounded search or blob-refill loop. A single
**300,000 SQLite VM-step budget** applies across each request, with handler cleanup
and connection close in all exits. No new route is implemented in this phase.

## B7 relationship

Do not add B8 capabilities, utilities or eligibility fields to `self_model_v1` merely
to advertise this batch. B7 remains after completed experience, B4 and optional B5
reflection, with no upstream consumers. Its catalog's `selectable` describes static
existing action availability, not this cycle's resource eligibility; B8 detail is the
source for the latter. No goal, competence or psychological inference is added.

**Concrete compatibility exception:** schema 7 would otherwise break B7. The audit
found hardcoded 6 in `seed/self_model.py` evidence schema checks, storage-schema
publication and snapshot validation, and an upper schema bound of 6 in
`dashboard/services/self_model.py`. Future B8 must make narrow compatibility edits:
accept supported DB schema 6/7, report the actual DB schema in newly published storage
metadata, validate stored schema_version 6 or 7, and permit the observer at schema7.
Keep self_model_v1/model_version 1 and its fields/formulas/limits unchanged. A retained
snapshot measured on v6 continues to report 6 after migration until a real new cycle
publishes 7. No migration/startup/read refresh or relabeling of historical snapshots.
Tests must prove v6 preservation and v7 publication/read compatibility. This change
is necessary for B7 acceptance, not a new upstream relationship.

## Owner-command boundary

Owner observe/reflect/consolidate continue through existing command handling,
confirmation, session, expiry and audit rules; do not call DecisionSystem. Their
existing resource suppression and provenance remain authoritative. No decision record,
Q update or autonomous transition is generated for them. Owner reflect is not newly
blocked by B8's autonomous guard. Stop cancels pending autonomous work and optional
attention as described; no utility, fallback or reward can override it. Existing
process/LaunchAgent lifecycle and security middleware remain unchanged.

## Resource bounds

| Work/payload | Hard v1 bound | Failure policy |
| --- | --- | --- |
| Candidate set | Exactly 4, fixed 4 B2 targets each | Contract error |
| Selection Q | One keyed SELECT, <=4 rows | Fundamental read/row failure abort |
| Selection predictor history | One SELECT, <=200 raw rows; each before/after <=16,384 bytes | Empty-history auxiliary fallback; no refill |
| Selection history transfer | <=6,553,600 JSON bytes plus <=200 bounded metadata rows | Above-limit source makes full auxiliary snapshot unavailable |
| Source parsing / batch calculations | <=400 bounded source decodes, four candidates over same parsed data; no extra DB queries | Malformed ordinary rows consume slots |
| Preselection B4/B6/B7/episode reads | **0** | Deliberately excluded |
| Selection SQLite execution | 100,000 VM steps total across Q/history; callback every 1,000; busy_timeout=0 | Q failure abort; history-only failure may fallback after safe cleanup |
| Current-state freshness | <=5 monotonic seconds from perception to dispatch check | Nonfatal stale skip; retry after captured observe_interval 8..3600s; stop interrupts |
| Record | 16,384 bytes, depth8, arrays4, structural entries512 | Compact projections/digest only; fail experience insert, no truncation |
| Individual B2 payload | 16,384 bytes | Invalid optional batch → empty-history batch before selection |
| Successful DECISION event / stale diagnostic | 2,048 / 512 bytes | Fixed fields, no raw evidence; ordinary expiry nonfatal |
| Inspection | 50 items/page + one metadata lookahead; four SELECTs; 300,000 VM steps | Explicit 503/invalid item, no refill |
| Inspection payload transfer | <=50 × (16,385+16,385+16,385) =2,457,750 bytes; detail49,155; plus bounded metadata | Sentinel checks; no historical prediction reconstruction |
| API serialized responses | List52 KiB; detail17 KiB; summaries1,024 bytes each | Compact JSON, explicit invalid response rather than truncation |
| New threads / timers / scheduler / sensors / sockets / APIs outside local inspection | **0** | Not authorized |

The read acquisition saves/restores prior busy timeout and removes the progress
handler on every exit. Own only the transaction acquired by B8; reject entry inside
an existing transaction. Cleanup independently attempts rollback if needed, progress
removal, timeout restoration and unconditional lock release. Preserve primary
KeyboardInterrupt/SystemExit and re-raise after cleanup. If safe connection state
cannot be established, abort; never hide it as ordinary optional-evidence fallback.
The VM counter covers both reads without being reset between them. The timeout read
is a fixed PRAGMA, not a Q/history evidence query. No success/failure writes inside
the evidence-read transaction.

Per-selection limits do not imply bounded lifetime database size or fixed physical
I/O latency. One bounded decision record accumulates per new autonomous transition;
existing episodes, transition/B4/B5/B6 histories and action checkpoint work remain.
No pruning or retention policy for decision records is introduced. VM limits bound
SQLite execution, not JSON CPU or total device latency; payload/structure limits and
the pre-action monotonic age check cover those separate risks.

## Security boundaries

Decision utility grants no capability. Only the existing four internal actions can
execute. No shell invocation, filesystem exploration, downloads, package installation,
privilege changes, browsing, new network destinations, arbitrary tools, replication,
self-modification, persistence changes or shutdown resistance. Keep existing local
Host/Origin/token boundaries, path/symlink checks and observer read-only connections.
Errors use fixed enums, not raw database dumps. Core remains standard-library-only
and runs without dashboard dependencies; inspection imports only pure validators.

## B9/B10 isolation

Future B8 inspection endpoints support audit; no frontend page/chart, weight editor,
interactive policy control or developmental UI is part of B8. No weight optimization,
hyperparameter search, improvement threshold, behavioral trend claim or learned tuning.
Deterministic fixtures demonstrate correctness of this contract, not that B8 is
smarter, safer in every real setting, or more resource-efficient. B10 would need separate
matched experiments; it remains unauthorized and unstarted.

## Deterministic scenario

Future `tests/decision_scenario.py` uses real temporary Memory/DecisionSystem/cycle,
synthetic sensors, fixed wall/monotonic clocks and injected RNG. CLI emits strict
stable JSON (no host paths, random IDs, actual clock times or footprint promises).
Artifact: future `docs/baselines/seed-0.2-b8-comparison.json`, anchored to this exact
B7 base, approved design commit and all eight prior artifact hashes. Do not create
that code/artifact in this phase.

Unless specified, current state is battery80, charging=false, load=.2, disk50,
network=true, hour12; epsilon 0. All unmentioned Q values are 0. Source transitions
are inserted before the selected cycle; their timestamps satisfy freshness. Global
zero-delta support can give all four actions identical predicted current resources.

| Case | Literal evidence and expected result |
| --- | --- |
| 1. Q-only fallback | Empty history; Q(reflect)=.7, others0. All eligible, every resource status persistence, effective R=U=1. Raw-Q winner reflect, same unique eligible legacy winner; mode fallback, reason no_supported_resource_forecast |
| 2. Low disk | Current disk5; empty history; Q(consolidate)=100, Q(rest)=1. Reflect/consolidate constrained low_disk, pool observe/rest. Rest selected; legacy reward −.2, old rest Q1 → .784 at alpha.18; no autonomous B6 run. Repeat with Q(observe)=1 to tie eligible observe/rest: consolidate Q100 remains outside the tie pool. Separately issue owner consolidate with persisted disk5: accepted, low_disk audit, zero semantic work/Q/transition changes |
| 3. Load/battery/boundaries | Current battery10, charging=false, load.9, disk50: reflect/consolidate reasons high_load and low_battery, observe/rest eligible. Q(rest)=1 wins fallback; reward2.2, Q1→1.216. At load.8,battery20,disk10 no known guard. At battery10,charging=true,load.2,disk50 no battery guard. Missing disk constrains costly actions as unknown_resources |
| 4. Conflicting signals | 20 action-specific samples per action (80 total), confidence .95/U=.05. Q(reflect)=1 → Qcomponent .75; predicted reflect battery0/load1/disk0 → R1, utility .5175. Observe Q0 → .5; predicted80/.2/50 → R0, utility .7425. Rest and consolidate Q−1 → .25 and same safe forecast → .6175. Observe wins despite reflect's higher Q |
| 5. Partial/all missing | Current disk absent, battery/load usable, charging=false. 20 samples support safe battery/load, so each candidate R=1/3, U=(.05+.05+1)/3=11/30. Observe Q0 → utility .25+7/30+.095 = .5783333333333334; disk value/method null and status unavailable, effective disk risk/U1. Reflect/consolidate unknown_resources. Give rest Q−1 so observe wins composite. Then use empty history: all resources unsupported, legacy-Q fallback; no fabricated certainty |
| 6. Exploration | Low-disk pool [observe,rest], epsilon 1, draw.5, injected choice selects index0: observe. Q(consolidate)=100 cannot enter pool. Repeat with index1: rest. Epsilon0 never explores but can consume choice for a tie; draw exactly epsilon does not explore |
| 7a. Composite tie | All Q0, 20 supported identical safe forecasts: utility .7425 for all. With epsilon 0/draw.5, pool[observe,reflect,consolidate,rest], injected index0 selects observe, repeat index1 selects reflect. Also test maxima differing5e-13 share the pool; difference2e-12 excludes the lower action. Choice uses the tolerant maximum pool only |
| 7b. Cold-start raw-Q tie | Empty history/all Q0/epsilon 0/draw.5. All eligible, utility.25 each (audit only); exact raw-Q pool includes all four. Inject index0→observe and index1→reflect. No rest preference. Under disk5, tied costly actions are excluded before choice: pool[observe,rest], index1→rest |
| 7c. Unique winner | Case1 reflect alone in pool, index=null, choice call count 0; epsilon random draw still occurs once. Repeat a unique composite winner. Singleton exploration also consumes no choice |
| 8. Prediction identity | During selected action append strongly contradictory source transitions and return a distinct after-state. B3 input, selected PREDICTION event and persisted transition retain exact canonical equality; compact record digest matches that payload. Shared in-memory source cutoff excludes added/current rows; no durable ledger or full candidate copies |
| 9. Q compatibility | Healthy case1 reflect Q.7/visits4, legacy reward .45 → .655/visits5 at alpha.18. Every unselected Q row unchanged; utility never stored as Q or passed as reward. Repeat all actions under permitted state, epsilon 0/1 and another valid alpha |
| 10. Restart | Close/reopen schema7; exact record survives and detail is unchanged. Existing B1–B7 transitions still have zero invented decision records; migration creates empty table. Startup/read creates none |
| 11. Auxiliary damage/freshness | Oversized history blob or injected history read failure with valid Q gives canonical empty-history batch and explicit reason. Newest support age300 usable, >300 stale; future/null contributor timestamp invalid. All unusable means Qfallback. Never reread beyond raw200 |
| 12. Fundamental corruption/stop | Malformed/nonfinite Q, incompatible live state, invalid RNG, unsafe cleanup or stop prevents action/Q/experience/decision write; stop cancels without ERROR where otherwise healthy. Stop after DECISION can leave event only. Rest never overrides owner stop |
| 13. Compact audit | Persist/reopen the two full examples: three resource projections per action, no history rows/contributor arrays/full predictions/network projections, selected digest matches linked canonical prediction, <=16,384 bytes. Mutate linked selected prediction → invalid_decision; read performs no prediction/scoring calls |
| 14. Nonfatal stale skip | At default observe_interval8, monotonic age5.001s before selection event → skipped/stale_decision/delay8; one pre-perception, zero action/reward/Q/visits/transition/decision/B3–B7 updates. Diagnostic<=512 bytes; existing B7 snapshot unchanged. Advance wait7.999s: no new attempt; after8s a new cycle perceives fresh and can complete. Repeat expiry to prove no busy loop, and late expiry after DECISION to prove matching terminal attempt diagnostic |
| 15. Stop/fatal distinction | Stop before expiry or during retry → stopped/no retry. Invalid Q/DB/clock/cleanup contract raises the fatal path even if elapsed time also exceeds5s; never relabel it skipped. No stale diagnostic after an observed owner stop |


Case4 history is realizable: repeat per-action before/after numeric deltas −80/+.8/−50
for reflect and zero for the other actions, with valid Boolean outcomes. The live
current state is shared. This fixture establishes a scoring conflict, not a causal
benefit of observe. Equality and expected totals use pytest.approx with abs1e-12
except intentional exact tie/serialization assertions. The future artifact records
component values, compact forecasts, constraints, basis/mode, selected digest/action, rewards/Q
and absence/availability, not invented development metrics.

## Test strategy

These are **future** tests, not tests written or executed in this design phase.

| Future file | Concrete tests/acceptance |
| --- | --- |
| `tests/test_decision.py` | `test_q_normalization_literals_and_finite_extremes`, `test_weighted_totals_and_conflicting_signals`, `test_partial_missing_uses_fixed_denominators`, `test_all_unsupported_uses_raw_q_order`, `test_composite_tie_uses_injected_random_choice`, `test_q_fallback_tie_preserves_random_tie_semantics`, `test_constraints_exclude_actions_before_tie_choice`, `test_unique_winner_does_not_consume_choice_rng`, `test_constraints_match_semantic_guard`, `test_unknown_resources_and_charging_boundaries`, `test_epsilon_pool_and_draw_boundary`, `test_invalid_q_state_rng_and_update_abort`, `test_no_eligible_defensive_rest`, `test_freshness_boundary_and_bad_clocks`, `test_payload_strict_fields_versions_bounds_and_cross_field_consistency`, `test_compact_decision_record_under_byte_cap`, `test_decision_record_omits_history_row_ledger`, `test_decision_record_omits_unselected_full_predictions`, `test_selected_prediction_digest_matches_transition` |
| `tests/test_predictor.py` | Add `test_batch_reads_one_raw200_snapshot`, `test_batch_matches_legacy_predict_per_action`, `test_transient_contributors_and_compact_freshness_summary_match_exact_samples`, `test_size_failure_does_not_refill_or_partially_filter`, `test_batch_keeps_b2_global_network_extreme_math`, `test_batch_inference_has_no_sensor_network_or_write_calls` |
| `tests/test_decision_cycle.py` | `test_predictions_precede_rng_selection_and_action`, `test_selected_prediction_identity_after_history_changes`, `test_q_reward_visits_adapter_and_learning_telemetry_compatibility`, `test_two_perceptions_and_fixed_probes`, `test_prior_beliefs_before_current_world_update`, `test_owner_commands_bypass_decision_and_low_disk_audit`, `test_stop_before_and_after_selection`, `test_stale_decision_is_nonfatal_skipped_cycle`, `test_stale_decision_retry_has_no_q_or_transition_effect`, `test_stale_retry_does_not_spin`, `test_owner_stop_is_not_stale_retry`, `test_stale_skip_has_one_perception_and_bounded_diagnostic`, `test_late_expiry_marks_attempt_terminal`, `test_fatal_contract_error_is_not_stale`, `test_transaction_failure_preserves_existing_q_boundary`, `test_sql_budget_and_cleanup_faults_preserve_interrupts` |
| `tests/test_decision_migrations.py` | `test_fresh_v7_and_empty_decision_table`, `test_v6_upgrade_backup_preserves_every_prior_row`, `test_all_older_ladders_and_final_step_rollback`, `test_failed_backup_prevents_upgrade`, `test_unsupported_ambiguous_schema_refused`, `test_reopen_and_no_backfill`, `test_decision_insert_failure_rolls_back_entire_experience_group` |
| `tests/dashboard/test_decisions.py` | `test_list_detail_keysets_and_raw_corrupt_slot`, `test_exact_query_byte_and_vm_budgets`, `test_legacy_missing_future_schema_responses`, `test_link_and_selected_prediction_corruption`, `test_direct_http_bounds_and_unknown_filters`, `test_no_memory_migration_process_sensors_or_writes`, `test_valid_record_reopens_without_recompute`, `test_digest_mismatch_is_corrupt`, `test_detail_read_never_reruns_predictor` |
| Existing B7 tests | Explicitly add v6→v7 stored-schema preservation/new-publication cases; unchanged self_model_v1 calculations/fields, zero B7 effect on selection and same read-only guarantees |
| `tests/decision_scenario.py`, `tests/test_decision_scenario.py` | All 15 numbered cases above, including the three tie subcases, stable strict-JSON standalone CLI, exact saved future artifact, all eight historical hashes unchanged |

Adapt existing cycle spies that force `Learner.choose()` to instead control B8
selection evidence/RNG or a correctly frozen decision result. Keep legacy choose
unit tests. Earlier prediction-does-not-affect-selection assertions intentionally
cease to describe autonomous B8; replace them with explicit prediction-influences-
selection checks while preserving their reward, chosen-action delay, no-future-leakage
and downstream independence assertions. Update strict event-order expectations for
prediction computation before selection; selected PREDICTION telemetry still follows
DECISION. No tests removed/skipped to hide changes.

Adapt successful cycle return assertions to CycleResult(completed, existing delay, null);
add distinct skipped/stopped assertions without weakening successful-cycle invariants.
Old scenario action sequences/Q results can differ under B8 selection and injected
random ties; do not overwrite historical artifacts to make them look unchanged. Separate
unchanged formula fixtures from intentionally changed selection outputs in the new B8
comparison. Existing B3/B4/B5/B6/B7 calculation fixtures retain their contracts; only
actual schema/footprint and deliberate action-selection effects may differ. Run the
full intended suite, all seven CLIs including the new B8 CLI, compilation and diff
checks on temporary homes; retain the existing hosted Linux/macOS matrix when later
push/CI authorization permits. Passing these tests proves correctness, not improvement.

## Documentation changes

This phase changes exactly this specification, the current authorization/B8 row and
new dated record in `docs/seed-0.2-development-plan.md`, and the navigation/current
boundary in `docs/implementation-log.md`. Historical entries stay historical.
README, architecture, verification guide, review follow-ups and all baselines remain
unchanged now; their future B8 updates must describe actual implemented contracts,
new inspection/migration, intentional selection changes and verified mismatch closure.
No B8 implementation plan is created under this design-only instruction.

## Risks and mitigations

| Risk | Decision/mitigation and retained limit |
| --- | --- |
| Correlation mistaken for causation | Label forecasts as descriptive; immediate horizon; no promised battery/CPU benefit |
| Heuristic weights/thresholds | Fixed/versioned, literal tests and owner review; not optimized or calibrated |
| Missing support discourages actions | Explicit effective penalties, fixed denominator and raw-Q fallback; records expose the tradeoff |
| Historical mixture and wall-clock changes | Latest200 transient evidence; compact invalid-clock count/maximum-time proof; newest-support TTL; older samples may remain and full replay is deliberately unavailable |
| Evidence becomes stale during work | Five-second guard skips dispatch nonfatally; observe_interval wait between attempts prevents busy loops; repeated load can still postpone completed work |
| Q saturation / extreme values | Document finite-tail ties; raw-Q fallback; finite update preflight; never repair stored values silently |
| Hidden tie bias | No fixed action preference; uniform injected choice among eligible maxima, separately from epsilon; fixtures choose at least two different tied actions |
| Storage growth | Compact projections/digest, 16 KiB cap and PK inspection; no redundant four-prediction/history ledger; lifetime growth remains unbounded without a separately designed retention policy |
| Migration accidentally disables B7 | Explicit literal ladder versions and narrow v6/v7 B7 compatibility tests |
| Pre-action events or Q survive later failure | Exact existing transactional boundary recorded; no fake completion or replay |
| New validator diverges from writer | Shared pure B8 contract validation for writer/reader; cross-field and corruption fixtures |
| Owner command confused with eligibility | Separate dispatch paths and no Q/decision records for commands; suppressed audit remains truthful |

## Acceptance criteria

Design acceptance: verified exact base and clean dedicated branch; original fresh baseline;
amendment verified at the requested design SHA without rerunning unchanged product tests;
complete evidence inventory and alternatives; exact mathematics, exclusions, fallback,
constraints, ordering, persistence/inspection/limits; complete healthy/degraded examples;
future tests and file map; written self-review; exactly three documentation files
committed. No runtime change or implementation authorization is implied.

Future implementation acceptance requires every scenario/test contract above, no
open Critical/Important review findings, full regression and platform evidence,
immutable prior artifacts, additive backup-tested v7, verified B7 compatibility,
selected prediction identity, unchanged Q/reward/owner boundaries and no B9/B10 or
installed-home changes. The known mismatch can be marked closed only at that gate.

## Open questions resolved

- Separate DecisionSystem selected; Q is one of three weighted components.
- Weights .50/.35/.15 and transforms/ramps/TTL unchanged; injected random eligible ties; no settings or tuning.
- B4/B5/B6/B7/goal/opportunity/cost inputs excluded for stated provenance reasons.
- Unknown resources constrain costly autonomous actions; invalid legacy state/Q aborts.
- Epsilon remains probabilistic on eligible actions even under legacy-Q fallback.
- All four predictions share one history snapshot; selected prediction is never rerun.
- Decision storage is a compact 16 KiB schema7 record with selected-prediction digest, atomic with experience and no historical backfill.
- Stale expiry skips work nonfatally, waits captured observe_interval and re-perceives; stop and fatal errors are distinct.
- B7 receives only necessary schema compatibility, with historical schema6 snapshots preserved.
- Owner commands bypass policy; rest is resource-safe fallback, not a way around stop.
- Read-only APIs are future B8 audit scope, frontend/evaluation work remains later.

No implementation-critical question is deferred. Owner review may accept or amend
these explicit policy choices; implementation still requires separate authorization.

## Implementation file map

All paths in this table are proposed future edits, **not changes made now**.

| Path | Necessary purpose |
| --- | --- |
| `seed/decision.py` (new) | Versioned acquisition, pure math/constraints, selection, frozen result and shared strict record validator |
| `seed/learner.py` | Keep reward/update/legacy choose; only a small raw-Q adapter/helper if needed, without model dependencies |
| `seed/predictor.py` | Pure shared forecasting helper plus one-snapshot batch, transient contributors and compact provenance; old predict compatibility |
| `seed/organism.py` | Reorder prediction/selection, frozen payload propagation, explicit completed/skipped/stopped CycleResult, bounded stale retry and legacy telemetry adapter |
| `seed/memory.py` | Optional decision argument, validated atomic insert linked to actual transition ID; keep existing Q boundary |
| `seed/migrations.py` | Add v7 table, retain explicit v6 support and correct literal sequential ladder |
| `seed/self_model.py`, `dashboard/services/self_model.py` | Narrow actual-schema6/7 compatibility only; preserve self_model_v1 meaning/history |
| `dashboard/services/decisions.py` (new) | Bounded validated ReadStore list/detail; no core startup or process inspection |
| `dashboard/services/seed_service.py`, `dashboard/api/observer.py` | Delegations and two fixed read routes |
| `dashboard/app.py` | Current-schema operator table guard includes decision_records; no migration or UI |
| Test files named in Test strategy | Exact math, constraints, batch/persistence/rollback/owner/stop/read bounds, compatible B7 and deterministic fixture |
| Existing affected cycle/scenario tests | Adapt intentional selection/schema/event assumptions while preserving all unaffected invariants |
| `docs/baselines/seed-0.2-b8-comparison.json` (future new) | Deterministic correctness evidence and immutable B7/prior artifact anchors |
| `README.md`, `docs/architecture.md`, `docs/verification.md`, `docs/review-follow-ups.md` | Explain implemented behavior/verification and close mismatch only after acceptance |
| `docs/implementation-log.md`, `docs/seed-0.2-development-plan.md` | Actual future implementation and evidence/status record |

No frontend, dependency, sensor, command, reward, world-model, curiosity, semantic
engine, CI or deployment edits are required. Reusing the existing semantic guard
requires no change to its behavior. Scope expansion needs an explicit design amendment.

## Written self-review

This is an inline design self-review, not independent implementation review. Each
ruling below checks the proposed contract; none claims future tests already passed.

| Check | Result and resolved evidence |
| --- | --- |
| 1. Pre-action truthfulness | PASS: current state/Q/prior transitions only; no current B3/B5 or B7 feedback |
| 2. Prediction ordering | PASS: one raw200 snapshot, all four predictions before RNG/selection |
| 3. Selected prediction identity | PASS: frozen full payload equality across B3/event/transition; compact record canonical SHA-256 linkage checked before action/persistence and on reads |
| 4. Q compatibility | PASS: raw adapter, unchanged reward/update/visits/schema; utility never learned; corrupt Q abort explicit |
| 5. Low-disk closure | PASS as design: canonical guard excludes consolidate even at Q100; owner suppressed audit retained; running issue remains open |
| 6. Constraints | PASS: Boolean eligibility applies before exploration/ranking; stop overrides rest |
| 7. Missing evidence | PASS: compact unavailable status/null value, effective risk/uncertainty1, fixed denominator, eligible raw-Q fallback |
| 8. No causal overclaim | PASS: descriptive action/global forecasts; no immediate rest-wait outcome claim |
| 9. No fake information gain | PASS: two perceptions for every action; no observe bonus/opportunity engine |
| 10. Bounded work | PASS: explicit Q/history/blob/structure/VM/page/event limits; no scans/refills; existing action costs not mislabeled bounded B8 work |
| 11. Owner authority | PASS: commands bypass scorer, original audits/confirmation retained, stop cancellation defined |
| 12. No B9 | PASS: future audit API only; no frontend, charts, weight editor or policy UI |
| 13. No B10 | PASS: literal correctness cases only; no improvement, optimality or developmental-evaluation claims |
| 14. Persistence | PASS: additive v7, literal v6 ladder, backup/rollback/no-backfill, exact reopen; B7 schema6 snapshots preserved with narrow compatibility; earlier Q boundary distinct |
| 15. Testability | PASS: literal conflict/partial/tie/Q cases plus failure/ordering/preservation tests and stable future CLI |
| 16. Historical integrity | PASS: all eight B0–B7 artifacts untouched; no earlier absence filled, no historical result relabeled; only three authorized docs changed |

Self-review corrections incorporated: preserve schema6 support when proposing7;
keep Q score distinct from utility; preserve epsilon even during fallback; distinguish
unknown absent resources from invalid legacy input; specify unsupported-history B2
persistence rather than invented predictions; distinguish compact outer JSON from
canonical selected-prediction equality; keep all eight historical artifacts; state
that low-disk closure is designed but not implemented.

Owner-review amendment self-checks (0 Critical, 2 Important, 1 Minor design findings):

- **Tie bias:** equal eligible values have no hidden fixed action preference. Tie
  choice remains random through injected/testable RNG; choice_index addresses the
  actual selection_candidates pool in all modes; unique pools consume no choice.
- **Durable storage:** record contains only compact selection evidence and digest;
  no redundant four-prediction/history-row ledger remains. 16 KiB cap verified by
  both complete examples; digest validates linked selected prediction without replay.
- **Stale expiry:** old pre-action evidence prevents dispatch without killing an
  otherwise healthy organism. Retry waits observe_interval, cannot busy-loop, and
  does not create a completed action/Q/experience/model update. Stop remains separate.

These findings are resolved in the amended **design only**. No implementation finding
is declared fixed, no production acceptance test ran, and implementation is unstarted.

**Stop here for owner review. B8 implementation and B9–B10 remain NOT STARTED.**
