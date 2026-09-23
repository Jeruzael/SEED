# SEED Current Architecture

> **B6 update (2026-09-23):** Semantic memory consolidation and schema v5 are verified. Existing consolidate commands now run bounded, revisable consolidation from B4 beliefs while preserving original memories. See [the B6 execution record](seed-0.2-development-plan.md#b6-execution-log--2026-09-23) for behavior, tests and limits. The detailed text below is the preserved B3 reference snapshot; its status and not-yet-implemented statements describe that earlier state.

**Current verified development state: SEED 0.2 B3**

This document describes the active SEED source architecture after completion of developmental batches B0 through B3.

Historical batch requirements, implementation decisions, verification results, limitations, and acceptance records are maintained in:

```text
docs/seed-0.2-development-plan.md
```

Reproducible baseline and evaluation artifacts are stored under:

```text
docs/baselines/
```

Batch-specific execution plans are stored under:

```text
docs/superpowers/plans/
```

This document describes the **current architecture**, not the historical starting state.

---

## Architectural objective

SEED means:

**Situated Experiential Emergent Development**

The current developmental architecture is intended to move incrementally from simple contextual behavior toward systems capable of learning from observed transitions and prediction error while preserving:

* inspectability;
* reproducibility;
* bounded resource usage;
* historical provenance;
* owner authority;
* explicit capability boundaries.

The MacBook is treated as both SEED's body and its first environment.

---

## Current runtime composition

The main organism is `SeedOrganism`.

Conceptually:

```text
SeedOrganism
├── Body
├── Memory
├── Learner
├── Predictor
├── Prediction Error Evaluator
├── Telemetry
├── Command Queue
└── Instance Lock
```

### Body

`seed/body.py`

The body exposes bounded observations of the host environment.

Current observations include:

* battery percentage;
* charging state;
* normalized system load;
* free disk percentage;
* local hour;
* wall-clock time;
* load-average information;
* network reachability;
* hostname;
* machine architecture;
* macOS/platform identity.

Network reachability uses the existing fixed TCP probe to:

```text
1.1.1.1:443
```

The predictor and prediction-error evaluator do not add additional probes.

---

## Memory

`seed/memory.py`

Memory owns the core SQLite connection and persistent organism state.

It provides:

* autobiographical episodes;
* contextual action values;
* concepts;
* transition persistence;
* metadata;
* schema initialization;
* migration coordination;
* transaction boundaries for linked experience storage.

The current schema version is:

```text
2
```

Write-capable construction checks existing schema state before migration.

Supported older memory is backed up before a required schema upgrade through the normal `Memory` path.

The migration design is additive.

Historical records are preserved rather than rewritten to imitate newer developmental stages.

---

## Learner

`seed/learner.py`

The learner remains the original bounded contextual-bandit system.

Current autonomous actions are:

```text
observe
reflect
consolidate
rest
```

The learner uses an epsilon-greedy policy.

The legacy Q update remains conceptually:

```text
Q_new = Q_old + alpha × (reward - Q_old)
```

The B1–B3 architecture deliberately preserves this learning mechanism so prediction and prediction-error behavior can be evaluated without simultaneously changing the decision policy.

At B3:

* predictions do not affect action choice;
* prediction errors do not affect reward;
* prediction errors do not affect Q values;
* prediction errors do not affect epsilon;
* prediction errors do not affect alpha;
* prediction errors do not affect delays.

---

## Predictor

`seed/predictor.py`

B2 introduced a deterministic prospective predictor.

Model:

```text
transition_delta_v1
```

Model version:

```text
1
```

Prediction horizon:

```text
next_post_action_observation
```

History window:

```text
latest 200 completed transitions
```

Minimum historical evidence for a historical prediction method:

```text
2 usable samples
```

The predictor contains no persistent learned mutable model separate from transition history.

Inference is derived from completed historical transitions at prediction time.

---

## Prediction targets

The predictor currently produces expectations for:

```text
battery_pct
load_ratio
disk_free_pct
network_reachable
```

The network prediction target maps to the existing observation field:

```text
network_reachable ← state["network"]
```

No additional sensor field is introduced merely to satisfy predictor naming.

---

## Numeric prediction

For a usable numeric target, historical evidence is derived from:

```text
delta = state_after - state_before
```

Evidence selection follows:

```text
action-specific evidence
        ↓
global evidence
        ↓
persistence
```

### Action-specific prediction

If at least two valid historical transitions exist for the selected action and target:

```text
predicted =
current + mean(action-specific historical delta)
```

### Global fallback

If action-specific evidence is insufficient but at least two valid historical samples exist globally:

```text
predicted =
current + mean(global historical delta)
```

### Persistence fallback

If insufficient historical evidence exists:

```text
predicted = current
```

Persistence carries:

```text
evidence_count = 0
confidence = 0
```

and does not pretend historical evidence exists.

---

## Numeric validation and bounds

Numeric observations must be:

* actual integers or floats;
* not booleans;
* finite;
* within the supported physical domain.

Battery and free disk require:

```text
0 <= value <= 100
```

Load ratio requires:

```text
value >= 0
```

Predicted battery and disk values are clamped to:

```text
0..100
```

Predicted load is constrained to finite non-negative representable values.

The predictor records whether clamping changed the raw result.

Historical malformed values are skipped per signal.

Invalid recent rows still consume the fixed 200-row history window, preventing malformed data from triggering an unbounded search through lifetime history.

---

## Network prediction

Historical network evidence uses actual Boolean post-transition observations.

Evidence selection uses the same structure:

```text
action-specific Boolean frequency
        ↓
global Boolean frequency
        ↓
persistence
```

With sufficient historical evidence:

```text
probability_true =
true_samples / evidence_count
```

Classification is deterministic:

```text
True  when probability_true >= 0.5
False otherwise
```

A 50/50 tie therefore resolves to `True`.

If historical evidence is insufficient, the current Boolean network state is persisted as the predicted value.

---

## Predictor confidence semantics

Every signal uses:

```text
confidence_kind = evidence_support
```

The current support formula is:

```text
confidence =
min(0.95, evidence_count / 20)
```

This is not a calibrated probability.

For example:

```text
confidence = 0.95
```

means the predictor has reached the configured historical evidence-support ceiling.

It does not mean:

```text
95% probability of correctness
```

Actual prediction quality is evaluated independently by B3.

---

## Prediction-error evaluator

`seed/prediction_error.py`

B3 introduced a pure deterministic evaluator.

Evaluator:

```text
prediction_error_v1
```

Evaluator version:

```text
1
```

Supported prediction contract:

```text
model = transition_delta_v1
model_version = 1
horizon = next_post_action_observation
```

Unknown or malformed prediction contracts are not silently reinterpreted.

Their targets are marked not evaluated.

The evaluator performs no:

* history lookup;
* database access;
* sensing;
* network operation;
* DNS;
* subprocess execution;
* randomness;
* mutation of its inputs.

It scores exactly the four supported targets.

---

## Numeric prediction error

For valid numeric prediction/actual pairs:

```text
signed_error = actual - predicted
```

Positive signed error means the actual observation was higher than predicted.

Negative signed error means it was lower.

Absolute error is:

```text
absolute_error =
abs(signed_error)
```

### Battery and disk normalization

Battery and disk values occupy the known percentage domain:

```text
0..100
```

Their normalized error is:

```text
normalized_error =
absolute_error / 100
```

### Load normalization

Load ratio does not have a fixed 0..100 domain.

Its normalized error is:

```text
normalized_error =
absolute_error /
max(1, abs(predicted), abs(actual))
```

Normalized errors are bounded to:

```text
0..1
```

Non-finite intermediate calculations are not converted into artificial scores.

They become not-evaluated results instead.

---

## Network prediction error

For `network_reachable`, both predicted and actual values must be exact booleans.

Basic classification records:

```text
correct
classification_error
```

where classification error is:

```text
0 when classification matches
1 when classification differs
```

If the original prediction contains a valid:

```text
probability_true
```

in the range:

```text
0..1
```

the evaluator calculates Brier error:

```text
brier_error =
(probability_true - int(actual))²
```

That Brier value becomes the network signal's normalized error.

If no valid probability was present in the original prospective prediction, classification mismatch is used instead.

The evaluator never invents a probability after observing the outcome.

---

## Evaluation availability

Every supported target appears in the evaluation payload.

Signals can be:

```text
evaluated
```

or:

```text
not_evaluated
```

Not-evaluated reasons include:

```text
prediction_unavailable
invalid_prediction
actual_unavailable
nonfinite_calculation
```

Missing information is not replaced with a zero-error value.

That prevents absent evidence from being counted as predictive success.

---

## Aggregate prediction error

Only evaluated targets participate in aggregate error.

For one transition:

```text
mean_normalized_error =
mean(normalized errors for evaluated targets)
```

The engineering score is:

```text
accuracy_score =
1 - mean_normalized_error
```

Evaluation coverage is calculated independently:

```text
coverage =
evaluated_signals / 4
```

The aggregate payload records:

```text
status
evaluated_signals
target_signals
coverage
mean_normalized_error
accuracy_score
```

If no signals can be evaluated:

```text
status = unavailable
evaluated_signals = 0
coverage = 0
mean_normalized_error = null
accuracy_score = null
```

Missing signals therefore reduce coverage rather than artificially improving or worsening accuracy.

---

## Score semantics

`accuracy_score` is an engineering summary over heterogeneous normalized signal errors.

It is **not**:

* calibrated probability;
* confidence;
* certainty;
* causal evidence;
* reward;
* utility;
* policy value.

A transition can legitimately have:

```text
accuracy_score = 1
coverage = 0.25
```

when its one available target was predicted exactly.

Consumers must therefore interpret accuracy and coverage together.

B2 predictor confidence remains a separate concept representing historical evidence support.

---

## Autonomous B3 cycle

The current autonomous cycle is:

```text
apply settings
→ infer wake if necessary
→ perceive state_before
→ record pre-action PERCEPTION telemetry
→ choose internal action
→ record DECISION telemetry
→ generate prospective prediction
→ record PREDICTION telemetry
→ record action start
→ perform selected action
→ record action completion
→ perceive state_after
→ record post-action PERCEPTION telemetry
→ derive observed transition outcome
→ evaluate original prediction against state_after
→ record PREDICTION_ERROR telemetry
→ calculate unchanged legacy reward from state_before
→ update contextual Q value
→ atomically persist linked experience data
→ record LEARNING telemetry
→ record MEMORY telemetry
→ update latest-state metadata
→ return the selected action delay
```

The important temporal property is:

```text
prediction
    occurs before
action
    occurs before
state_after
    occurs before
prediction evaluation
```

The predictor is called once for the completed autonomous cycle.

The prediction is not regenerated for evaluation.

---

## Learning isolation

Prediction and evaluation are intentionally isolated from the current learner.

At B3, neither prediction values nor prediction errors alter:

* action choice;
* candidate ranking;
* contextual state key;
* epsilon;
* alpha;
* legacy reward;
* Q-value update;
* action delay;
* reflection behavior;
* consolidation behavior;
* annotations;
* importance;
* owner-command execution.

Controlled tests verify that runs with zero and nonzero prediction errors retain the same action, legacy reward, Q update, and delay.

This gives B3 a clean measurement boundary.

Later developmental batches may use prediction error in carefully specified ways, but B3 itself does not.

---

## Transition memory

B1 introduced explicit transition persistence.

Conceptually:

```text
episodes
   |
   | one-to-one for autonomous transition experience
   |
transitions
```

The transition table contains:

```text
id
episode_id
started_at
completed_at
state_before_json
action
state_after_json
outcome_json
legacy_reward
prediction_json
prediction_error_json
```

`episode_id` is unique within the transition table.

One completed autonomous transition therefore links to one experience episode.

---

## Historical transition semantics

SEED does not backfill information that did not historically exist.

Valid historical states include:

### Pre-B1

```text
episode exists
transition does not
```

### B1

```text
transition exists
prediction_json = NULL
prediction_error_json = NULL
```

### B2

```text
transition exists
prediction_json = populated
prediction_error_json = NULL
```

### B3

```text
transition exists
prediction_json = populated
prediction_error_json = populated
```

These are valid historical eras rather than corruption states.

---

## Experience persistence transaction

For current B3 experience persistence, the following logical information is written together:

```text
experience episode
+
transition
+
prospective prediction
+
prediction evaluation
```

If the transition insert fails, the linked newly attempted experience episode is rolled back with it.

Prediction and prediction-error payloads are serialized before the transaction and stored without recomputing inference or evaluation.

---

## Whole-cycle atomicity boundary

The entire physical organism cycle is not transactional.

Before final experience persistence, earlier operations may already have effects.

Examples include:

* reflection updates;
* consolidation metadata;
* telemetry;
* Q-value updates.

Therefore, if final persistence fails after one of those effects has committed, SEED may retain those earlier effects without a completed transition row.

This behavior is explicitly documented.

The architecture does not claim whole-cycle rollback.

---

## Outcome semantics

`seed/transitions.py` describes observed differences between:

```text
state_before
```

and:

```text
state_after
```

Numeric values can record deltas.

Other values record whether they changed.

Presence flags distinguish:

```text
missing
```

from:

```text
present with null/None
```

Observed differences are correlations between two measurements.

They are not automatically treated as causal effects of the selected action.

---

## Observation snapshot integrity

Observations are detached before transition processing.

This prevents mutable sensor dictionaries from rewriting historical provenance after reuse.

Stored `state_before` therefore remains the actual pre-action snapshot even if the underlying sensor implementation later mutates or reuses its original Python object.

---

## Schema and migration

Current schema version:

```text
2
```

Schema evolution is additive.

The current migration path supports:

```text
unversioned legacy memory
→ schema v1
→ schema v2
```

Unsupported, ambiguous, duplicate, or future schema versions are refused instead of guessed.

Migration failures roll back.

Existing memory rows are preserved.

The supported write-capable `Memory` path performs backup before upgrading memory that requires migration.

Direct low-level migration code does not substitute for that filesystem backup policy.

---

## Dashboard boundary

The dashboard remains architecturally separate from the autonomous organism.

Observer access uses a narrow storage/service layer and read-only database connections where appropriate.

The dashboard does not instantiate another autonomous `SeedOrganism`.

Operator mode requires the expected current schema.

If required tables or the expected schema version are absent, operator mode refuses the storage rather than migrating it.

Dashboard/operator protections include the existing bounded local-control mechanisms, including:

* loopback-oriented access;
* Host/Origin validation;
* mutation Origin requirements;
* CSRF protection;
* bounded JSON request size;
* strict request models;
* fixed operator command allowlists.

The dashboard must not become a second organism or a migration engine.

---

## Owner-command boundary

Owner commands remain distinct from autonomous transitions.

Owner-requested:

```text
observe
reflect
consolidate
```

retain their existing provenance.

They do not automatically:

* create autonomous policy transitions;
* update contextual Q values;
* invoke the autonomous predictor as a policy step;
* generate prediction-error learning.

This keeps operator intervention distinguishable from autonomous experience.

---

## Lifecycle

The organism starts through the normal user-level process/LaunchAgent path.

On process start, SEED records wake state.

Actual macOS sleep suspends the process.

Wake is currently inferred when the elapsed wall-clock gap between cycle starts exceeds the configured threshold.

This remains an approximation rather than an authoritative macOS sleep event.

Shutdown records a final lifecycle/sleep state when normal termination completes.

The process does not use privileged persistence and does not resist deliberate shutdown.

---

## Current action timing

Current action delays remain approximately:

```text
observe       configurable, baseline 8 s
reflect       configurable, baseline 12 s
consolidate   20 s
rest          configurable, baseline 35 s
```

The post-action observation occurs before the later waiting interval.

That matters particularly for `rest`.

---

## Prediction horizon limitation

Current predictor and evaluator horizon:

```text
next_post_action_observation
```

For all actions, evaluation compares the prediction against the immediate second perception.

For `rest`, this happens before the longer scheduled rest delay.

Therefore current rest prediction does **not** model:

```text
state after the full rest period
```

It models:

```text
state at the immediate post-action observation
```

Future multi-horizon prediction would require an explicit new contract.

---

## Resource bounds

The predictor performs one bounded history query per autonomous cycle.

Maximum raw history rows:

```text
200
```

Targets evaluated:

```text
4
```

The evaluator performs no database query.

A normal autonomous cycle still performs two environmental perceptions:

```text
state_before
state_after
```

Each perception retains the existing body sensor behavior, including the fixed reachability probe.

B2 and B3 add no new network destinations.

---

## Current known limitations

Known current limitations include:

1. Charging-state parsing can misclassify the string `discharging`.

2. Wake detection is inferred from wall-clock gaps rather than native macOS sleep/wake notifications.

3. Wall-clock timestamps can be affected by clock adjustment and must not automatically be treated as monotonic elapsed-duration measurements.

4. Prediction horizon is immediate post-action observation only.

5. Rest evaluation does not cover the later rest interval.

6. Global predictor fallback may combine unlike environmental contexts.

7. Action-conditioned historical association does not establish causation.

8. Predictor confidence represents evidence support rather than calibrated predictive accuracy.

9. B3 aggregate `accuracy_score` is an engineering convention rather than calibrated probability.

10. Whole-cycle atomic persistence is intentionally incomplete.

11. Predictor/evaluator validation does not redesign all legacy learner assumptions about malformed live state.

12. Normal autonomous cycles still perform the existing fixed reachability probe twice because they contain two perceptions.

---

## Not implemented at B3

The following are explicitly outside the verified B3 architecture:

* persistent world-model beliefs;
* belief contradiction handling;
* causal reasoning;
* curiosity driven by prediction error;
* novelty-driven action selection;
* prediction-error reward shaping;
* prediction-driven candidate action planning;
* semantic memory consolidation;
* episode deletion based on learned importance;
* self-modeling;
* autonomous planning;
* arbitrary external tool use;
* autonomous tool acquisition;
* arbitrary network actions;
* generated shell execution;
* autonomous source-code modification;
* automatic capability expansion;
* language-model-based cognition.

Later batches require separate design, acceptance criteria, tests, and explicit authorization.

---

## Current developmental boundary

The B3 system can now answer three distinct questions:

```text
What did I observe?
What did I predict?
How wrong was I?
```

It does **not yet** use the answer to the third question to construct a persistent world model or alter behavior.

That boundary separates B3 from later developmental work.

The next planned architectural stage is B4 world modeling, but B4 is not implemented and requires its own explicit design and authorization.
