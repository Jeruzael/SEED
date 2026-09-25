# SEED 0.2 B8 — Decision-System Upgrade Design

## Goal

Make the existing contextual bandit one selection signal among several, using only
pre-action evidence and the existing four internal actions. Recommend a separate
`DecisionSystem`, explicit eligibility, one shared candidate-prediction snapshot,
and a small versioned utility rule. Preserve learning semantics and make every
completed decision inspectable.

**Design/specification: COMPLETE FOR OWNER REVIEW. Implementation: NOT STARTED.**
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
5. Specify deterministic fallback, corrupt-data behavior, provenance, limits and
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
| Candidate predictions | Not currently; yes after proposed reorder | B2 pure batch over completed `transitions` | One query, latest 200 raw rows | Shared ID cutoff and frozen contributor indexes | Descriptive action/global correlations | Immediate resource forecasts | Explicit missing/stale states; conservative effective penalties, then Q fallback if no usable resource forecast | Yes | Makes prediction prospective for selection |
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
exact B2 prediction; per-target contributor indexes and resource availability; and
utility. Even constrained candidates have computed components when inputs are safe.
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

`history.rows` contains at most 200 `{id, completed_at}` entries in descending ID
order; `cutoff_id` is the first ID, or null when empty/unavailable. Every candidate
stores four arrays of zero-based indexes into this shared list; indexes follow its
order, are distinct and match B2 evidence counts/method scopes. Persistence and
unavailable targets have empty arrays. Malformed/nonfinite completion metadata is
represented as null and makes any forecast using that row unavailable for scoring;
B2 itself does not suddenly use timestamps in its statistical math.

Freshness is a B8 scoring rule, not a B2 formula change. A historical resource forecast
is usable when its support count >=2, all contributor completion times are finite
and <= `selected_at`, and its newest contributor is no more than **300 seconds** old.
Equality at 300 is fresh. Older contributors may still be in the latest-200 mixture;
this is a recency-of-latest-support rule, not a claim that all evidence is recent.
Record indexes/times so that limitation is visible. A future source time or missing
time makes that signal `invalid`; otherwise an older newest source makes it `stale`.
No TTL changes the stored candidate prediction; only its B8 scoring availability.

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

For a persistence-only, unavailable, stale or invalid resource forecast, record raw
risk as null and status explicitly, then use **effective risk=1**. Missing evidence
cannot become a favorable zero risk. `forecast_resource_risk R` is the arithmetic
mean of the three effective risks, always in [0,1]. This denominator never shrinks.
No current observation is relabeled as supported action-conditioned prediction.

## Uncertainty semantics

`model_uncertainty U` is a versioned **lack-of-evidence-support measure**. For each
of the same three usable resource forecasts, raw uncertainty is
`1 - min(.95, evidence_count / 20)`, identical to `1 - B2 confidence` after validating
its consistency with count. Unsupported targets have raw uncertainty null and
**effective uncertainty=1**. U is the mean over the fixed three targets.

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
Exploration occurs exactly when `u < epsilon`; epsilon 0 never explores and epsilon
1 always explores. Explore uniformly via the injected RNG's `choice()` over eligible
actions in canonical order, recording the chosen index. Never explore excluded actions.

For exploitation with `policy_basis=composite`, find maximum eligible utility;
all candidates within **absolute 1e-12** of that maximum form the tie set (no relative
or transitive tie grouping). Choose first in fixed priority **rest, observe, reflect,
consolidate**. For legacy-Q fallback use exact raw-Q equality, then the same priority.
This intentionally replaces random exploitation tie-breaking in the autonomous path;
legacy `Learner.choose()` retains its original random ties.

`selection_mode=explore` whenever epsilon fires, including degraded evidence;
otherwise `exploit` for composite or `fallback` for legacy-Q basis.
`policy_basis=composite|legacy_q` and `fallback_reason` are separate: degradation does
not secretly turn epsilon off. `choice_index` is null outside exploration. Store the
eligible pool/tie set in `selection_candidates`; utility cannot override constraints.

## Missing/corrupt evidence fallback

| Situation | Exact behavior |
| --- | --- |
| Some resource predictions usable | Composite ranking; unsupported targets effective R/U=1; retain statuses/null raw values |
| All eligible resource predictions unsupported, including pure persistence | Legacy raw-Q ordering under constraints; `fallback_reason=no_supported_resource_forecast` |
| Auxiliary snapshot read/VM/size failure | Empty-history canonical B2 batch; legacy-Q basis; failure reason from fixed enum |
| Invalid optional candidate batch | Discard batch, canonical empty-history predictions; `fallback_reason=invalid_prediction` |
| Absent/corrupt B4, B6 or B7 | No effect; they are not read by B8 |
| Missing current resource fields with legacy-compatible shape | Preserve presence, constrain costly actions; observe/rest remain; prediction follows B2 unknown rules |
| Malformed current state, Q, epsilon, RNG or candidate identity | Bounded ERROR; abort before action, no Q/experience/decision insert |
| Unexpected empty eligible set with otherwise valid contract and no stop | Reassert resource-safe rest as sole eligible action; `policy_basis=legacy_q`, `fallback_reason=no_eligible_candidate`; all components still recorded; do not override an invalid-Q or owner-stop abort |
| Owner stop | Cancel without selecting/executing another action, including rest |
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
   input and capture the monotonic observation time plus wall `selected_at`.
2. Under one lock/read transaction: state key, one Q query, one raw-history query.
   Release/restore the connection before computation/telemetry. No B4/B6/B7 reads.
3. Compute all four B2 predictions from that frozen history. Freeze contributor
   metadata; validate predictions; apply documented fallback if necessary.
4. Compute all constraints and components, then the eligible set. Check owner stop.
   Draw epsilon and choose using the prescribed basis/ties. Preflight the unchanged
   selected Q update for finite representability without writing or sensing.
5. Before action, check stop again. If more than **5 monotonic seconds** have elapsed
   since the current pre-observation, abort `stale_decision` through the existing
   ERROR/stop path; do not act, loop, re-perceive or claim a completed transition.
   Emit bounded DECISION and selected PREDICTION; use the same frozen prediction.
   Set existing runtime last-decision fields via the raw-Q adapter, then ACTION start.
   Recheck stop and the same monotonic age limit immediately before dispatch; a race
   here can leave selection telemetry
   with no completed record, but must not execute after an observed stop.
6. Perform existing action; ACTION complete; second perception; outcome; B3 evaluates
   **that same** prediction. No resnapshot, regeneration or post-outcome scoring.
7. Read B5's existing at-most-eight prior published beliefs, assess curiosity before
   the current transition changes B4. Preserve B3/B5 formulas and event meanings.
8. Compute existing reward from state_before; ordinary `Learner.update`; obtain new
   raw Q as today. Atomically insert episode, transition, exact prediction/evaluation,
   B4 queue, B5 assessment **and new decision record**. No utility is a learning target.
9. Preserve CURIOSITY summary, bounded B4 recovery, LEARNING/MEMORY, metadata, optional
   claimed B5 reflection, then B7 publication and final runtime telemetry.
10. Return existing delay for the selected action. Stop cancellation returns a
    distinct `None` cycle result; `run()` exits on that result/stop before computing
    a wait deadline. It does not treat cancellation as a completed rest cycle.

No complete physical-cycle transaction is claimed. Actions, telemetry and the
existing separately committed Q update may precede a failed experience transaction.
The record can only certify selection evidence for a completed linked transition,
not that every observed external resource change was caused by its internal action.

## Decision persistence

| Choice | Evaluation |
| --- | --- |
| DECISION/runtime only | No schema, but events expire and runtime is current-only; loses durable transition evidence |
| Nullable JSON on `transitions` | Direct atomic linkage, but alters the established row and mixes expanding contracts |
| New transition-keyed `decision_records` | Additive, naturally absent for historical/owner records, clear validator and bounded read boundary; select |

One record per future completed autonomous transition. No writes on owner commands,
startup, read, failed action/post-observation or incomplete cycle. Generate a 32-character
lowercase hexadecimal `decision_id` before selection telemetry for correlation; it is
not a transition ID and need not be globally indexed. At insertion attach the actual
transition ID, not a guessed next ID. `created_at` is insertion wall time; `selected_at`
is the selection-start wall time captured after the pre-observation, before evidence
acquisition; it is not a claim about dispatch time. Wall clocks can go backward: do not require
created_at >= selected_at or silently reorder timestamps.

The stored JSON is **at most 65,536 UTF-8 bytes**, strict finite JSON, no duplicate
keys, maximum depth 12, maximum array length 200 and maximum 8,192 total object keys
plus array elements. These limits include all nesting. Strings are at most 128 UTF-8
bytes except fixed contracts still validated by exact enum. No raw history states,
episodes, notes, hostnames, paths, tokens or free-form error text are included.

The exact field contract is defined below and exemplified in full. Unknown fields
or versions are invalid; do not reinterpret them. All numeric validations reject
Boolean-as-number. IDs are integers 1..2^63−1; counts/indexes are integers; timestamps
finite nonnegative numbers or explicit null only where allowed. Current input object
contains only present keys from battery_pct, charging, load_ratio, disk_free_pct,
network, local_hour with the state domains above; absent keys remain absent.

- Top-level fields: `model`, `model_version`, `weights_version`, `decision_id`,
  `transition_id`, `created_at`, `selected_at`, `state_key`, `current`, `history`,
  `epsilon`, `alpha`, `random_draw`, `choice_index`, `policy_basis`, `selection_mode`,
  `eligible_actions`, `selection_candidates`, `selected_action`, `fallback_reason`,
  `candidates`. Model=`decision_v1`, versions=1; state key must equal legacy state_key
  on current inputs. Epsilon [0,1], alpha (0,1] per current configuration, draw [0,1).
- `history`: exactly `status`, `reason`, `cutoff_id`, `rows`. Status=`ok|empty|unavailable`;
  ok requires 1..200 rows; empty requires none and null reason/cutoff; unavailable
  requires none, null cutoff and reason `history_read_error`,
  `history_budget_exceeded`, `oversized_history` or `invalid_prediction`. Ok reason is null.
  Row fields exactly `id`, `completed_at`; IDs unique descending, times finite or null.
- `candidates`: exactly four action keys. Each has exactly `eligible`,
  `constraint_reasons`, `q_value`, `visits`, `q_missing`, `components`, `resource_status`,
  `raw_risk`, `raw_uncertainty`, `evidence_indexes`, `decision_utility`, `prediction`.
  Eligibility/reasons must reproduce the guards; missing Q means exactly 0/0.
- `components`: exactly `q_component`, `forecast_resource_risk`, `model_uncertainty`;
  finite [0,1]. Utility finite [0,1], consistent with formula within 1e-12.
  `resource_status`, `raw_risk`, `raw_uncertainty` have exactly the three numeric target
  keys. Status=`usable|persistence|unavailable|stale|invalid`. Raw numbers in [0,1]
  only when usable, otherwise null. Components reproduce the fixed effective defaults.
- `evidence_indexes`: exactly all four B2 targets, each a unique in-range ordered
  index list, length matching evidence_count. Invalid metadata may produce an invalid
  resource status but must not invent supporting IDs. The source action-selection
  match is certified during snapshot construction; read validation can check structure,
  count/freshness, not re-query 200 source states to rerun inference.
- `prediction`: exact existing B2 version-1 envelope and per-signal conditional
  shape. Envelope fields action/signals/model/model_version/horizon. Four signals.
  Unavailable: status/reason/evidence_count/confidence/confidence_kind only; reason
  missing_current_value or invalid_current_value, count/confidence=0.
  Predicted numeric: status/value/method/clamped/evidence_count/confidence/confidence_kind;
  method action_mean_delta, global_mean_delta or persistence. Boolean predicted:
  status/value/method/evidence_count/confidence/confidence_kind, plus probability_true
  only for action_boolean_frequency or global_boolean_frequency. No Boolean clamped.
  Confidence kind=evidence_support; count 0 for persistence/unavailable, otherwise
  2..200; confidence exactly min(.95,count/20); numeric/network domains as B2.
- Action lists are unique canonical-order subsets except exploitation tie set order
  also canonical. Selection must satisfy epsilon, basis, tie priority, pool membership
  and choice index (index into eligible list; null unless explore). The winning action
  and candidate prediction.action must match SQL columns and linked transition.action.
  Fallback reason null only for composite basis; nonnull for legacy_q. All eligible
  unsupported implies legacy_q; partial usable evidence permits composite only unless
  the explicit defensive empty-set fallback applies.

Validate the frozen evidence fields before beginning the experience transaction.
After inserting its transition, attach the actual transition ID and insertion time,
then validate and serialize the complete record before inserting decision_records
inside that same transaction. Any final size/linkage failure rolls the whole
experience group back; do not reserve or guess a transition ID. Full-record bytes
are compact JSON (`sort_keys=True`, `separators=(',', ':')`, `allow_nan=False`). The
selected nested prediction, existing PREDICTION event, and transition prediction
must be structurally identical and byte-identical under the **existing prediction
serializer** `json.dumps(payload, sort_keys=True, allow_nan=False)`. Do not require
literal substring equality against the compact outer record. Validate this equality
before insert; detail reads also compare to the linked persisted prediction.
In-memory record mutation, over-limit serialization or linkage mismatch aborts the
experience transaction; no silent truncation or fake successful B8 record.

Healthy synthetic record (all forecasts have global support from the same two rows;
current battery 80/load .2/disk 50, no charging; all three risks zero, U=.9;
Q(reflect)=1 gives utility .375+.35+.015=.74):

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
    "network": true,
    "local_hour": 12
  },
  "history": {
    "status": "ok",
    "reason": null,
    "cutoff_id": 2,
    "rows": [
      {
        "id": 2,
        "completed_at": 998
      },
      {
        "id": 1,
        "completed_at": 997
      }
    ]
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
      "resource_status": {
        "battery_pct": "usable",
        "load_ratio": "usable",
        "disk_free_pct": "usable"
      },
      "raw_risk": {
        "battery_pct": 0,
        "load_ratio": 0,
        "disk_free_pct": 0
      },
      "raw_uncertainty": {
        "battery_pct": 0.9,
        "load_ratio": 0.9,
        "disk_free_pct": 0.9
      },
      "evidence_indexes": {
        "battery_pct": [
          0,
          1
        ],
        "load_ratio": [
          0,
          1
        ],
        "disk_free_pct": [
          0,
          1
        ],
        "network_reachable": [
          0,
          1
        ]
      },
      "decision_utility": 0.615,
      "prediction": {
        "action": "observe",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 50.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "global_boolean_frequency",
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support",
            "probability_true": 1.0
          }
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
      "resource_status": {
        "battery_pct": "usable",
        "load_ratio": "usable",
        "disk_free_pct": "usable"
      },
      "raw_risk": {
        "battery_pct": 0,
        "load_ratio": 0,
        "disk_free_pct": 0
      },
      "raw_uncertainty": {
        "battery_pct": 0.9,
        "load_ratio": 0.9,
        "disk_free_pct": 0.9
      },
      "evidence_indexes": {
        "battery_pct": [
          0,
          1
        ],
        "load_ratio": [
          0,
          1
        ],
        "disk_free_pct": [
          0,
          1
        ],
        "network_reachable": [
          0,
          1
        ]
      },
      "decision_utility": 0.74,
      "prediction": {
        "action": "reflect",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 50.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "global_boolean_frequency",
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support",
            "probability_true": 1.0
          }
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
      "resource_status": {
        "battery_pct": "usable",
        "load_ratio": "usable",
        "disk_free_pct": "usable"
      },
      "raw_risk": {
        "battery_pct": 0,
        "load_ratio": 0,
        "disk_free_pct": 0
      },
      "raw_uncertainty": {
        "battery_pct": 0.9,
        "load_ratio": 0.9,
        "disk_free_pct": 0.9
      },
      "evidence_indexes": {
        "battery_pct": [
          0,
          1
        ],
        "load_ratio": [
          0,
          1
        ],
        "disk_free_pct": [
          0,
          1
        ],
        "network_reachable": [
          0,
          1
        ]
      },
      "decision_utility": 0.615,
      "prediction": {
        "action": "consolidate",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 50.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "global_boolean_frequency",
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support",
            "probability_true": 1.0
          }
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
      "resource_status": {
        "battery_pct": "usable",
        "load_ratio": "usable",
        "disk_free_pct": "usable"
      },
      "raw_risk": {
        "battery_pct": 0,
        "load_ratio": 0,
        "disk_free_pct": 0
      },
      "raw_uncertainty": {
        "battery_pct": 0.9,
        "load_ratio": 0.9,
        "disk_free_pct": 0.9
      },
      "evidence_indexes": {
        "battery_pct": [
          0,
          1
        ],
        "load_ratio": [
          0,
          1
        ],
        "disk_free_pct": [
          0,
          1
        ],
        "network_reachable": [
          0,
          1
        ]
      },
      "decision_utility": 0.615,
      "prediction": {
        "action": "rest",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 50.0,
            "method": "global_mean_delta",
            "clamped": false,
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "global_boolean_frequency",
            "evidence_count": 2,
            "confidence": 0.1,
            "confidence_kind": "evidence_support",
            "probability_true": 1.0
          }
        }
      }
    }
  }
}
```

Degraded synthetic record: empty history, low disk, Q(consolidate)=100 cannot
bypass its constraint; Q(rest)=1 wins eligible raw-Q fallback. Persistence forecasts
remain recorded facts about the B2 fallback, with null raw B8 risk/uncertainty and
effective penalties of 1. This is its first transition.

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
    "network": true,
    "local_hour": 12
  },
  "history": {
    "status": "empty",
    "reason": null,
    "cutoff_id": null,
    "rows": []
  },
  "epsilon": 0.15,
  "alpha": 0.18,
  "random_draw": 0.5,
  "choice_index": null,
  "policy_basis": "legacy_q",
  "selection_mode": "fallback",
  "eligible_actions": [
    "observe",
    "rest"
  ],
  "selection_candidates": [
    "rest"
  ],
  "selected_action": "rest",
  "fallback_reason": "no_supported_resource_forecast",
  "candidates": {
    "observe": {
      "eligible": true,
      "constraint_reasons": [],
      "q_value": 0,
      "visits": 0,
      "q_missing": true,
      "components": {
        "q_component": 0.5,
        "forecast_resource_risk": 1,
        "model_uncertainty": 1
      },
      "resource_status": {
        "battery_pct": "persistence",
        "load_ratio": "persistence",
        "disk_free_pct": "persistence"
      },
      "raw_risk": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "raw_uncertainty": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "evidence_indexes": {
        "battery_pct": [],
        "load_ratio": [],
        "disk_free_pct": [],
        "network_reachable": []
      },
      "decision_utility": 0.25,
      "prediction": {
        "action": "observe",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 5.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "persistence",
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          }
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
      "resource_status": {
        "battery_pct": "persistence",
        "load_ratio": "persistence",
        "disk_free_pct": "persistence"
      },
      "raw_risk": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "raw_uncertainty": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "evidence_indexes": {
        "battery_pct": [],
        "load_ratio": [],
        "disk_free_pct": [],
        "network_reachable": []
      },
      "decision_utility": 0.375,
      "prediction": {
        "action": "reflect",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 5.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "persistence",
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          }
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
      "resource_status": {
        "battery_pct": "persistence",
        "load_ratio": "persistence",
        "disk_free_pct": "persistence"
      },
      "raw_risk": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "raw_uncertainty": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "evidence_indexes": {
        "battery_pct": [],
        "load_ratio": [],
        "disk_free_pct": [],
        "network_reachable": []
      },
      "decision_utility": 0.4975247524752475,
      "prediction": {
        "action": "consolidate",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 5.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "persistence",
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          }
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
      "resource_status": {
        "battery_pct": "persistence",
        "load_ratio": "persistence",
        "disk_free_pct": "persistence"
      },
      "raw_risk": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "raw_uncertainty": {
        "battery_pct": null,
        "load_ratio": null,
        "disk_free_pct": null
      },
      "evidence_indexes": {
        "battery_pct": [],
        "load_ratio": [],
        "disk_free_pct": [],
        "network_reachable": []
      },
      "decision_utility": 0.375,
      "prediction": {
        "action": "rest",
        "model": "transition_delta_v1",
        "model_version": 1,
        "horizon": "next_post_action_observation",
        "signals": {
          "battery_pct": {
            "status": "predicted",
            "value": 80.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "load_ratio": {
            "status": "predicted",
            "value": 0.2,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "disk_free_pct": {
            "status": "predicted",
            "value": 5.0,
            "method": "persistence",
            "clamped": false,
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          },
          "network_reachable": {
            "status": "predicted",
            "value": true,
            "method": "persistence",
            "evidence_count": 0,
            "confidence": 0.0,
            "confidence_kind": "evidence_support"
          }
        }
      }
    }
  }
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
        CHECK(length(CAST(data_json AS BLOB)) <= 65536)
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

Extend the existing **DECISION** category; keep one event before action, not four
candidate events or a new parallel category. Source becomes `decision`; message
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
  prediction equality. No history rescan or decision recomputation.

Validate identical bounds for direct Python and HTTP callers; reject unknown query
keys, repeated scalar keys, nonintegers, nonfinite numbers and oversized IDs with 422.
No action filter is offered because an unindexed filtered scan would violate the
raw-window bound. Reads use SQLite `mode=ro`, zero busy timeout, one read snapshot,
fixed table-name metadata query and `SELECT version ... LIMIT 2`; never instantiate
Memory, probe processes, call service.status, perceive, publish B7, migrate or write.

For each page row use a PK join to its transition; transfer at most **65,537** record
bytes and **16,385** selected-prediction bytes (one sentinel beyond each limit).
Validate model/versions/SQL mirrors, linkage, supported state key, domains, constraints,
components, epsilon selection, counts/indexes, prediction structure and selected
prediction equality. The current-input projection must also match the linked
transition state_before projection; read its JSON with the same 16,385-byte cap.
Malformed/oversized linked evidence makes that item corrupt, not an excuse to reread
unbounded data. IDs in history must precede the linked transition ID; no source row
must be opened to establish that structural invariant.

List envelope: exactly `available`, `status`, `reason`, `items`, `next_cursor`.
Available schema-7 list status=`stored`, reason=null, including an empty table.
Each valid item is a <=2 KiB summary containing exactly `available=true`, `status=stored`,
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
bytes capped at **131,072 list**, **73,728 detail**; reject excess rather than truncate
valid evidence. The API always describes stored selection time, not current policy.

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
| Current-state freshness | <=5 monotonic seconds from perception to dispatch check | stale_decision abort; no automatic retries |
| Record | 65,536 bytes, depth12, arrays200, structural entries8,192 | Fail experience insert, no truncation |
| Individual B2 payload | 16,384 bytes | Invalid optional batch → empty-history batch before selection |
| DECISION event | 2,048 bytes | Contract error, no unbounded diagnostic |
| Inspection | 50 items/page + one metadata lookahead; four SELECTs; 300,000 VM steps | Explicit 503/invalid item, no refill |
| Inspection payload transfer | <=50 × (65,537+16,385+16,385) bytes, plus metadata | Sentinel checks, never transfer whole oversized blobs |
| API serialized responses | List128 KiB; detail72 KiB | Explicit invalid response, not truncation |
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
network=true, hour12; epsilon0. All unmentioned Q values are 0. Source transitions
are inserted before the selected cycle; their timestamps satisfy freshness. Global
zero-delta support can give all four actions identical predicted current resources.

| Case | Literal evidence and expected result |
| --- | --- |
| 1. Q-only fallback | Empty history; Q(reflect)=.7, others0. All eligible, every raw risk/uncertainty null, effective R=U=1. Raw-Q winner reflect, same unique eligible legacy winner; mode fallback, reason no_supported_resource_forecast |
| 2. Low disk | Current disk5; empty history; Q(consolidate)=100, Q(rest)=1. Reflect/consolidate constrained low_disk, pool observe/rest. Rest selected; legacy reward −.2, old rest Q1 → .784 at alpha.18; no autonomous B6 run. Separately issue owner consolidate with persisted disk5: accepted, low_disk audit, zero semantic work/Q/transition changes |
| 3. Load/battery/boundaries | Current battery10, charging=false, load.9, disk50: reflect/consolidate reasons high_load and low_battery, observe/rest eligible. Q(rest)=1 wins fallback; reward2.2, Q1→1.216. At load.8,battery20,disk10 no known guard. At battery10,charging=true,load.2,disk50 no battery guard. Missing disk constrains costly actions as unknown_resources |
| 4. Conflicting signals | 20 action-specific samples per action (80 total), confidence .95/U=.05. Q(reflect)=1 → Qcomponent .75; predicted reflect battery0/load1/disk0 → R1, utility .5175. Observe Q0 → .5; predicted80/.2/50 → R0, utility .7425. Rest and consolidate Q−1 → .25 and same safe forecast → .6175. Observe wins despite reflect's higher Q |
| 5. Partial/all missing | Current disk absent, battery/load usable, charging=false. 20 samples support safe battery/load, so each candidate R=1/3, U=(.05+.05+1)/3=11/30. Observe Q0 → utility .25+7/30+.095 = .5783333333333334; raw disk risk/U null, not zero. Reflect/consolidate unknown_resources. Give rest Q−1 so observe wins composite. Then use empty history: all resources unsupported, legacy-Q fallback; no fabricated certainty |
| 6. Exploration | Low-disk pool [observe,rest], epsilon1, draw.5, injected choice selects index0: observe. Q(consolidate)=100 cannot enter pool. Repeat with index1: rest. Epsilon0 performs no random choice; draw exactly epsilon does not explore |
| 7. Tie | All Q0, 20 supported identical safe forecasts: utility .7425 for all; fixed tie priority picks rest. Difference <=1e-12 remains a tie; >1e-12 wins strictly. Qfallback uses exact raw equality, not tolerance |
| 8. Prediction identity | During selected action append strongly contradictory source transitions and return a distinct after-state. B3 input, selected PREDICTION event, persisted transition and recorded selected candidate remain equal under canonical serialization; contributor cutoff excludes all added rows and current transition |
| 9. Q compatibility | Healthy case1 reflect Q.7/visits4, legacy reward .45 → .655/visits5 at alpha.18. Every unselected Q row unchanged; utility never stored as Q or passed as reward. Repeat all actions under permitted state, epsilon0/1 and another valid alpha |
| 10. Restart | Close/reopen schema7; exact record survives and detail is unchanged. Existing B1–B7 transitions still have zero invented decision records; migration creates empty table. Startup/read creates none |
| 11. Auxiliary damage/freshness | Oversized history blob or injected history read failure with valid Q gives canonical empty-history batch and explicit reason. Newest support age300 usable, >300 stale; future/null contributor timestamp invalid. All unusable means Qfallback. Never reread beyond raw200 |
| 12. Fundamental corruption/stop | Malformed/nonfinite Q, incompatible live state, invalid RNG, unsafe cleanup or stop prevents action/Q/experience/decision write; stop cancels without ERROR where otherwise healthy. Stop after DECISION can leave event only. Rest never overrides owner stop |

Case4 history is realizable: repeat per-action before/after numeric deltas −80/+.8/−50
for reflect and zero for the other actions, with valid Boolean outcomes. The live
current state is shared. This fixture establishes a scoring conflict, not a causal
benefit of observe. Equality and expected totals use pytest.approx with abs1e-12
except intentional exact tie/serialization assertions. The future artifact records
component values, constraints, basis/mode, predictions, selected action, rewards/Q
and absence/availability, not invented development metrics.

## Test strategy

These are **future** tests, not tests written or executed in this design phase.

| Future file | Concrete tests/acceptance |
| --- | --- |
| `tests/test_decision.py` | `test_q_normalization_literals_and_finite_extremes`, `test_weighted_totals_and_conflicting_signals`, `test_partial_missing_uses_fixed_denominators`, `test_all_unsupported_uses_raw_q_order`, `test_exact_and_tolerant_ties`, `test_constraints_match_semantic_guard`, `test_unknown_resources_and_charging_boundaries`, `test_epsilon_pool_and_draw_boundary`, `test_invalid_q_state_rng_and_update_abort`, `test_no_eligible_defensive_rest`, `test_freshness_boundary_and_bad_clocks`, `test_payload_strict_fields_versions_bounds_and_cross_field_consistency` |
| `tests/test_predictor.py` | Add `test_batch_reads_one_raw200_snapshot`, `test_batch_matches_legacy_predict_per_action`, `test_candidate_source_indexes_match_exact_samples`, `test_size_failure_does_not_refill_or_partially_filter`, `test_batch_keeps_b2_global_network_extreme_math`, `test_batch_inference_has_no_sensor_network_or_write_calls` |
| `tests/test_decision_cycle.py` | `test_predictions_precede_rng_selection_and_action`, `test_selected_prediction_identity_after_history_changes`, `test_q_reward_visits_adapter_and_learning_telemetry_compatibility`, `test_two_perceptions_and_fixed_probes`, `test_prior_beliefs_before_current_world_update`, `test_owner_commands_bypass_decision_and_low_disk_audit`, `test_stop_before_and_after_selection`, `test_stale_decision_aborts_without_extra_perception`, `test_transaction_failure_preserves_existing_q_boundary`, `test_sql_budget_and_cleanup_faults_preserve_interrupts` |
| `tests/test_decision_migrations.py` | `test_fresh_v7_and_empty_decision_table`, `test_v6_upgrade_backup_preserves_every_prior_row`, `test_all_older_ladders_and_final_step_rollback`, `test_failed_backup_prevents_upgrade`, `test_unsupported_ambiguous_schema_refused`, `test_reopen_and_no_backfill`, `test_decision_insert_failure_rolls_back_entire_experience_group` |
| `tests/dashboard/test_decisions.py` | `test_list_detail_keysets_and_raw_corrupt_slot`, `test_exact_query_byte_and_vm_budgets`, `test_legacy_missing_future_schema_responses`, `test_link_and_selected_prediction_corruption`, `test_direct_http_bounds_and_unknown_filters`, `test_no_memory_migration_process_sensors_or_writes`, `test_valid_record_reopens_without_recompute` |
| Existing B7 tests | Explicitly add v6→v7 stored-schema preservation/new-publication cases; unchanged self_model_v1 calculations/fields, zero B7 effect on selection and same read-only guarantees |
| `tests/decision_scenario.py`, `tests/test_decision_scenario.py` | All 12 cases above, stable strict-JSON standalone CLI, exact saved future artifact, all eight historical hashes unchanged |

Adapt existing cycle spies that force `Learner.choose()` to instead control B8
selection evidence/RNG or a correctly frozen decision result. Keep legacy choose
unit tests. Earlier prediction-does-not-affect-selection assertions intentionally
cease to describe autonomous B8; replace them with explicit prediction-influences-
selection checks while preserving their reward, chosen-action delay, no-future-leakage
and downstream independence assertions. Update strict event-order expectations for
prediction computation before selection; selected PREDICTION telemetry still follows
DECISION. No tests removed/skipped to hide changes.

Old scenario action sequences/Q results can differ under B8 selection and deterministic
ties; do not overwrite historical artifacts to make them look unchanged. Separate
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
| Historical mixture and wall-clock changes | Latest200 window, exact contributor metadata, newest-support TTL and future-time rejection for scoring; older samples may remain |
| Evidence becomes stale during work | Five-second monotonic pre-action guard; no unbounded resampling/retry |
| Q saturation / extreme values | Document finite-tail ties; raw-Q fallback; finite update preflight; never repair stored values silently |
| Rest tie preference changes behavior | Explicit policy decision, all-action fairness still possible through epsilon; no claim that ties make rest optimal |
| Storage growth | Bounded per-record payload and PK inspection; no silent pruning; lifetime size still grows |
| Migration accidentally disables B7 | Explicit literal ladder versions and narrow v6/v7 B7 compatibility tests |
| Pre-action events or Q survive later failure | Exact existing transactional boundary recorded; no fake completion or replay |
| New validator diverges from writer | Shared pure B8 contract validation for writer/reader; cross-field and corruption fixtures |
| Owner command confused with eligibility | Separate dispatch paths and no Q/decision records for commands; suppressed audit remains truthful |

## Acceptance criteria

Design acceptance: verified exact base and clean dedicated branch; fresh baseline;
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
- Weights .50/.35/.15, transforms/ramps/TTL/ties fixed; no settings or tuning.
- B4/B5/B6/B7/goal/opportunity/cost inputs excluded for stated provenance reasons.
- Unknown resources constrain costly autonomous actions; invalid legacy state/Q aborts.
- Epsilon remains probabilistic on eligible actions even under legacy-Q fallback.
- All four predictions share one history snapshot; selected prediction is never rerun.
- Decision storage is a new schema7 table, atomic with experience, no historical backfill.
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
| `seed/predictor.py` | Pure shared forecasting helper plus one-snapshot batch and exact contributor indexes; old predict compatibility |
| `seed/organism.py` | Reorder prediction/selection, frozen payload propagation, stop-cancellation handling and legacy telemetry adapter |
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
| 3. Selected prediction identity | PASS: frozen shared payload and canonical equality across B3/event/record/transition |
| 4. Q compatibility | PASS: raw adapter, unchanged reward/update/visits/schema; utility never learned; corrupt Q abort explicit |
| 5. Low-disk closure | PASS as design: canonical guard excludes consolidate even at Q100; owner suppressed audit retained; running issue remains open |
| 6. Constraints | PASS: Boolean eligibility applies before exploration/ranking; stop overrides rest |
| 7. Missing evidence | PASS: raw null/status, effective risk/uncertainty1, fixed denominator, eligible raw-Q fallback |
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

**Stop here for owner review. B8 implementation and B9–B10 remain NOT STARTED.**
