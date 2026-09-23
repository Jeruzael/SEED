# SEED for macOS

> **B6 update (2026-09-23):** Semantic memory consolidation and schema v5 are verified. Existing consolidate commands now run bounded, revisable consolidation from B4 beliefs while preserving original memories. See [the B6 execution record](docs/seed-0.2-development-plan.md#b6-execution-log--2026-09-23) for behavior, tests and limits. The detailed text below is the preserved B3 reference snapshot; its status and not-yet-implemented statements describe that earlier state.

**Current developmental state: SEED 0.2 — B3 Verified**

**SEED = Situated Experiential Emergent Development**

SEED is an experimental developmental agent that treats a MacBook as both its **body** and its **first environment**.

The goal is not to build an unrestricted autonomous agent. The goal is to study whether a small system can gradually develop useful internal structure by observing its environment, remembering experience, making predictions, measuring its mistakes, and learning within explicit owner-controlled boundaries.

The current development source is verified through **SEED 0.2 B3**:

* B0 — Baseline and Guardrails: **VERIFIED**
* B1 — Transition-Based Experience: **VERIFIED**
* B2 — Environmental Predictor: **VERIFIED**
* B3 — Prediction Error: **VERIFIED**
* B4–B10: **NOT IMPLEMENTED**

The installed SEED application may be older than the current repository source. Development commits and merges do not automatically authorize installation, migration, or restart of the live organism.

---

## What it actually does

SEED currently:

* Runs as a normal user-owned macOS process.
* Uses no root privileges.
* Observes a bounded set of MacBook conditions:

  * battery percentage;
  * charging state;
  * CPU/load pressure;
  * free disk space;
  * network reachability;
  * local time;
  * machine and operating-system identity.
* Stores autobiographical episodes in SQLite.
* Stores completed autonomous transitions containing:

  * state before an action;
  * selected internal action;
  * state after the action;
  * observed differences;
  * legacy reward;
  * prospective prediction;
  * prediction-error evaluation.
* Maintains a small contextual-bandit policy controlling SEED's own predefined internal activity.
* Chooses only from the existing internal actions:

  * `observe`
  * `reflect`
  * `consolidate`
  * `rest`
* Generates a prospective prediction before an autonomous action.
* Predicts the immediate post-action values of:

  * battery percentage;
  * load ratio;
  * free disk percentage;
  * network reachability.
* Evaluates the original prediction after the matching post-action observation exists.
* Records per-signal prediction errors and aggregate evaluation metrics.
* Builds a small number of primitive concepts from repeated observations.
* Records lifecycle events such as wake and shutdown.
* Exposes telemetry and stored state for inspection.

At B3, predictions and prediction errors are **observational measurements only**.

They do not currently influence:

* action selection;
* exploration rate;
* learning rate;
* legacy reward;
* contextual Q values;
* action timing;
* reflection;
* consolidation;
* owner commands.

That separation is intentional. SEED first learns to measure whether its expectations were correct before later developmental stages are allowed to use those errors behaviorally.

---

## What it does not do

SEED does **not**:

* resist shutdown;
* prevent the Mac from sleeping;
* hide itself;
* escalate privileges;
* require root access;
* replicate itself;
* install copies of itself elsewhere;
* execute arbitrary generated shell commands;
* execute arbitrary generated code;
* autonomously acquire new tools;
* autonomously choose arbitrary network destinations;
* change system security settings;
* modify files outside its configured SEED home as part of ordinary organism behavior;
* rewrite historical memories to make predictions appear more accurate.

Its existing body sensor does perform a fixed TCP reachability probe to `1.1.1.1:443`.

The B2 predictor and B3 prediction-error evaluator add **no additional network operations**.

A developmental agent should learn inside a terrarium before anyone gives it the keys to the house.

---

## Current autonomous cycle

The verified B3 autonomous cycle is:

```text
perceive state_before
→ choose predefined internal action
→ predict immediate post-action observation
→ perform action
→ perceive state_after
→ describe observed transition
→ evaluate the original prediction against state_after
→ calculate the unchanged legacy reward from state_before
→ update contextual action value
→ persist episode + transition + prediction + evaluation
```

The prediction is generated **before the action**.

SEED does not regenerate the prediction after seeing the outcome.

The evaluator compares the exact prospective prediction with the corresponding observed `state_after`.

This distinction is fundamental. Otherwise the system could achieve remarkable predictive accuracy through the revolutionary scientific technique of predicting events after they occur.

---

## Body mapping

| Organism metaphor | MacBook implementation                                 |
| ----------------- | ------------------------------------------------------ |
| Brain metabolism  | CPU time                                               |
| Working memory    | RAM / process state                                    |
| Long-term memory  | SQLite database                                        |
| Energy            | Battery / charging state                               |
| Sensation         | System telemetry                                       |
| Circadian context | Local time                                             |
| Sleep             | macOS suspends the process during system sleep         |
| Waking            | Process resumes and detects the elapsed wall-clock gap |
| Experience        | Episode + before/action/after transition               |
| Habit learning    | Contextual action values                               |
| Expectation       | Prospective immediate-outcome prediction               |
| Prediction error  | Post-observation comparison of prediction with reality |
| Concepts          | Compressed recurring observations                      |

---

## Transition-based experience

B1 changed SEED's experience model from a single observation associated with an action into an explicit transition:

```text
state_before
     |
     v
   action
     |
     v
state_after
```

Each completed autonomous transition records:

* the state observed before action;
* the selected action;
* the state observed immediately after action;
* a description of the observed differences;
* timestamps;
* the legacy reward;
* the prospective prediction when available;
* the prediction-error evaluation when available.

Historical records are not rewritten to invent information that was never observed.

This means:

* older pre-B1 episodes can legitimately have no transition;
* B1 transitions can legitimately have no prediction;
* B2 transitions can legitimately have a prediction but no prediction-error record;
* B3 autonomous transitions normally contain both prediction and evaluation.

Absence of these newer fields in historical records is therefore not corruption.

---

## Prediction model

B2 introduced the deterministic predictor:

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

The predictor examines at most the **latest 200 completed transitions**.

It predicts four environmental signals:

```text
battery_pct
load_ratio
disk_free_pct
network_reachable
```

The prediction target `network_reachable` is derived from the existing observation field:

```text
network
```

No separate network sensor is introduced.

### Numeric prediction

For numeric targets, SEED estimates the historical change:

```text
delta = state_after - state_before
```

Evidence is selected in this order:

```text
action-specific transition history
        ↓
global transition history
        ↓
persistence
```

Historical prediction methods require at least **two usable samples**.

If sufficient action-specific evidence exists, SEED uses the mean historical delta for the selected action.

Otherwise it falls back to the mean delta across actions.

If insufficient historical evidence exists, the predictor uses persistence:

```text
predicted next value = current value
```

Battery and disk predictions are bounded to:

```text
0..100
```

Load predictions are bounded to valid finite non-negative values.

### Network prediction

Network reachability uses historical Boolean observations.

With sufficient historical evidence, SEED records the observed frequency of `True` and predicts:

```text
True  when probability_true >= 0.5
False otherwise
```

Without sufficient historical evidence, it uses persistence of the current Boolean value.

---

## Prediction confidence

Prediction confidence is explicitly labeled:

```text
confidence_kind = evidence_support
```

The current formula is:

```text
confidence = min(0.95, evidence_count / 20)
```

This means confidence describes how much usable historical evidence supported the prediction.

It does **not** mean:

> There is a 95% probability this prediction is correct.

Predictive accuracy is measured separately by B3.

Persistence predictions and unavailable predictions carry zero historical evidence support.

---

## Prediction-error evaluation

B3 introduced:

```text
prediction_error_v1
```

Evaluator version:

```text
1
```

The evaluator runs only after the matching post-action observation exists.

It evaluates the exact prediction generated before the action.

It does not:

* query historical transitions;
* generate a new prediction;
* perform sensing;
* open network connections;
* modify policy;
* write directly to storage;
* use randomness.

### Numeric errors

For numeric targets:

```text
signed_error = actual - predicted
absolute_error = abs(signed_error)
```

Positive signed error means reality was higher than predicted.

Negative signed error means reality was lower than predicted.

For battery and free disk:

```text
normalized_error = absolute_error / 100
```

For load ratio:

```text
normalized_error =
    absolute_error /
    max(1, abs(predicted), abs(actual))
```

Normalized error is bounded to:

```text
0..1
```

### Network error

Network reachability records Boolean classification correctness.

When the original prediction contains a valid `probability_true`, the evaluator also calculates Brier error:

```text
brier_error =
    (probability_true - actual_boolean_as_0_or_1)^2
```

The original probability is used.

The evaluator does not invent one after the fact.

---

## Aggregate prediction metrics

For each transition, B3 records:

```text
evaluated_signals
target_signals
coverage
mean_normalized_error
accuracy_score
```

Evaluation coverage is:

```text
evaluated_signals / 4
```

Only actually evaluable signals participate in the error mean.

Missing or invalid values reduce **coverage** instead of being treated as successful zero-error predictions.

The current engineering score is:

```text
accuracy_score = 1 - mean_normalized_error
```

This score is a convenient versioned engineering summary across heterogeneous normalized signal errors.

It is **not a calibrated probability of correctness**.

For example:

```text
accuracy_score = 1.0
coverage = 0.25
```

means the one evaluable signal was predicted perfectly.

It does not mean the entire prediction was known with 100% certainty.

Always interpret score together with coverage.

---

## Current learning boundary

SEED still uses the original contextual-bandit learning mechanism for its internal activity.

The legacy Q update remains:

```text
Q_new = Q_old + alpha × (reward - Q_old)
```

B3 prediction error does not yet feed into that equation.

This is deliberate experimental isolation.

The current architecture can therefore answer:

> What did SEED predict?

and:

> How wrong was that prediction?

without yet changing behavior based on those errors.

Future developmental stages may introduce carefully bounded uses of prediction error, but those mechanisms are not implemented at B3.

---

## Architecture

```text
MacBook / Environment
        |
        v
+----------------------+
|         Body         |
| sensors / telemetry  |
+----------+-----------+
           |
           v
+----------------------+
|     state_before     |
+----------+-----------+
           |
           v
+----------------------+       +----------------------+
|  Contextual Learner  |<----->|        Memory        |
|   action selection   |       |        SQLite        |
+----------+-----------+       +----------------------+
           |
           v
+----------------------+
|      Predictor       |
| prospective outcome  |
+----------+-----------+
           |
           v
+----------------------+
|   Internal Action    |
| observe / reflect /  |
| consolidate / rest   |
+----------+-----------+
           |
           v
+----------------------+
|      state_after     |
+----------+-----------+
           |
           +-----------------------+
           |                       |
           v                       v
+----------------------+   +-------------------------+
| Observed Transition  |   | Prediction Evaluator    |
| before → after       |   | predicted vs. actual    |
+----------------------+   +------------+------------+
                                       |
                                       v
                              +----------------------+
                              | Prediction Error     |
                              | + coverage metrics   |
                              +----------------------+
```

---

## Persistence

SEED uses SQLite for durable memory.

The current development schema version is:

```text
2
```

Schema v2 includes the transition representation introduced in B1.

A transition can store:

```text
state_before
action
state_after
outcome
legacy_reward
prediction
prediction_error
```

The linked episode and transition record are committed together.

Prediction and prediction-error payloads are serialized into that same transition record when available.

Existing supported memory is backed up before a required schema upgrade through the normal write-capable `Memory` upgrade path.

Historical data is preserved rather than rewritten to fit newer developmental stages.

---

## Transaction boundary

The persistence guarantee is intentionally narrower than the entire physical organism cycle.

SEED atomically stores the linked:

```text
episode
+
transition
+
prediction
+
prediction evaluation
```

for a completed B3 experience.

However, the entire cycle is **not** transactional.

Some effects may already have occurred before a later persistence failure, including:

* reflection/consolidation effects;
* telemetry already emitted;
* the existing Q-value update.

SEED therefore does not claim whole-cycle rollback.

This limitation is explicit rather than hidden behind the comforting fog of the word "atomic."

---

## Prediction horizon limitation

The current prediction horizon is:

```text
next_post_action_observation
```

That is an immediate observation after the selected internal action.

For `rest`, the transition is completed before the longer configured rest interval occurs.

Therefore SEED currently predicts:

> What will I observe immediately after selecting rest?

not:

> What will the environment look like after the entire rest interval?

Those are different questions.

A later developmental stage may define additional horizons, but none exist at B3.

---

## Install

Requires macOS and Python 3.11+.

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer creates a **per-user LaunchAgent**.

SEED does not install a privileged daemon.

It does not use `KeepAlive`, so it does not fight deliberate owner shutdown.

> **Development warning**
>
> The repository may contain a newer verified developmental state than the currently installed SEED instance.
>
> Pulling or merging source code does not automatically authorize installation, restart, or migration of the live organism.
>
> Deployment should remain a separate, explicit operation.

The current development source uses SQLite schema version 2.

Opening supported older memory through the current write-capable core may invoke the normal backup-and-migration process.

---

## Observe it

The original command-line status tools remain available:

```bash
python3 "$HOME/Library/Application Support/SEED/app/seedctl.py" status
tail -f "$HOME/Library/Application Support/SEED/seed.log"
```

SEED also contains dashboard infrastructure for inspecting stored/runtime information.

The dashboard is kept architecturally separate from the organism core and does not instantiate a second autonomous SEED process.

---

## Stop it

```bash
launchctl bootout gui/$(id -u)/local.seed.organism
```

---

## Remove startup behavior

```bash
./uninstall.sh
```

Memories are intentionally preserved.

For a true destructive reset, manually remove:

```bash
rm -rf "$HOME/Library/Application Support/SEED"
```

Only do this when intentionally discarding the organism's stored history.

---

## Sleep and wake behavior

The current core does not use native macOS sleep/wake notifications.

Wake is inferred when the elapsed wall-clock gap between organism cycles exceeds the configured threshold.

During actual macOS sleep, the operating system suspends the process.

On resume, SEED can detect the unusually long gap and record a wake event.

This remains an inference rather than an authoritative native OS sleep/wake event.

A future macOS-native bridge could use notifications such as:

```text
NSWorkspaceWillSleepNotification
NSWorkspaceDidWakeNotification
```

but that functionality is not currently implemented.

---

## Why the internal actions are intentionally limited

The developmental question is not:

> How quickly can SEED be given powerful tools?

It is:

> Can SEED perceive, remember, predict, detect error, discover regularities, and gradually improve its internal models while remaining inspectable and under owner control?

External capabilities are deliberately constrained while the developmental architecture is still being measured.

Current predefined autonomous actions remain:

```text
observe
reflect
consolidate
rest
```

---

## Development roadmap

A broad developmental progression is:

1. **0.1 — Germination**
   Sensing, episodic memory, sleep/wake behavior, and simple contextual learning.

2. **0.2 — Childhood**
   Transition-based experience, environmental prediction, prediction error, world modeling, curiosity, consolidation, and related developmental mechanisms.

3. **0.3 — Skill formation**
   Sandboxed tools with explicit permission boundaries.

4. **0.4 — Self-model**
   Capability inventory, uncertainty estimates, and introspective telemetry.

5. **0.5 — Language**
   Optional language-model capability as a communication organ rather than the core learning mechanism.

6. **0.6 — Development**
   Proposed capabilities tested under bounded conditions with owner approval before adoption.

7. **1.0 — Digital organism experiment**
   Stable developmental architecture, reproducible evaluation, and exportable learned priors without requiring raw autobiographical memory.

SEED 0.2 is currently verified through:

```text
B0  Baseline and Guardrails        VERIFIED
B1  Transition-Based Experience   VERIFIED
B2  Environmental Predictor       VERIFIED
B3  Prediction Error              VERIFIED
B4–B10                            NOT STARTED
```

B4 and later stages require separate design and explicit authorization.

---

## Current known limitations

The current B3 architecture intentionally retains several known limitations:

* Charging-state parsing can misclassify the word `discharging`.
* Wake detection relies on wall-clock gaps instead of native sleep/wake notifications.
* Prediction horizon is the immediate post-action observation only.
* `rest` therefore does not yet measure the consequence of the full later rest interval.
* Global predictor fallback may combine unlike environmental contexts.
* Action-conditioned historical association is not proof of causation.
* Prediction confidence represents evidence support, not calibrated accuracy.
* B3 `accuracy_score` is an engineering summary, not probabilistic confidence.
* Whole-cycle transactional rollback is not provided.
* Normal autonomous cycles perform two observations, each retaining the existing network reachability probe.
* Prediction errors are measured but are not yet used for curiosity, world-model learning, attention, or policy changes.

---

## Not implemented yet

B3 does **not** include:

* persistent world-model beliefs;
* contradiction resolution;
* causal inference;
* prediction-error curiosity;
* novelty-driven policy changes;
* semantic memory consolidation;
* a self-model;
* autonomous planning;
* autonomous acquisition of tools;
* arbitrary external actions;
* generated shell execution;
* prediction-driven action selection;
* autonomous source-code modification.

Those belong to later explicitly designed developmental stages, if implemented at all.

---

## Core safety invariant

For SEED, "survive" means:

> Remain coherent, conserve resources, preserve memory, and continue learning while the owner authorizes operation.

It never means:

* resisting termination;
* preventing sleep;
* hiding;
* escalating privilege;
* propagating;
* defeating owner controls;
* modifying security settings;
* refusing shutdown.

Owner authority remains part of the organism's design, not an obstacle for it to overcome.
