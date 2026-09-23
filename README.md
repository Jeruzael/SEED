# SEED for macOS

**SEED = Situated Experiential Emergent Development**

SEED is an experimental developmental agent that treats a MacBook as its body and first environment. It observes local conditions, remembers experience, predicts immediate outcomes, measures prediction error, and retains descriptive patterns within owner-controlled boundaries.

**Current source: SEED 0.2 — verified through B6.** SQLite schema **v5**. The verified B6 implementation is commit **dc225af**, with **497 tests passing**, no skips, and two existing dependency deprecation warnings. The installed application may be older; source updates do not install, restart, or migrate the live organism.

Post-B6 hardening corrects current battery-state parsing, separates source and runtime version metadata, and adds a least-privilege CI workflow. The macOS test-isolation correction passes **542 tests** locally and on all three hosted Linux/macOS jobs for correction commit `cb70d00`; all verification artifacts were inspected. [Corrective PR #9](https://github.com/Jeruzael/SEED/pull/9) records checks for its current head. This is separate from B7. See the [hardening record](docs/reviews/2026-09-23-post-b6-hardening.md) and [verification guide](docs/verification.md).

| Batch | Capability | Status |
| --- | --- | --- |
| B0 | Baseline and guardrails | VERIFIED |
| B1 | Transition-based experience | VERIFIED |
| B2 | Environmental predictor | VERIFIED |
| B3 | Prediction-error evaluation | VERIFIED |
| B4 | Persistent descriptive world model | VERIFIED |
| B5 | Bounded computational curiosity | VERIFIED |
| B6 | Semantic memory consolidation | VERIFIED |
| B7–B10 | Self model, decision upgrade, development UI, evaluation | NOT STARTED |

See the [architecture guide](docs/architecture.md) for contracts and data flow, the [development tracker](docs/seed-0.2-development-plan.md) for acceptance evidence, and the [implementation index](docs/implementation-log.md) for batch records. B7 requires separate explicit authorization.

## What SEED does

SEED runs as a normal user-owned macOS process. Its existing body observes battery and charging state, load, free disk space, network reachability, local time, and machine identity. A small contextual bandit selects from four predefined internal actions:

| Action | Internal work | Delay after the completed cycle |
| --- | --- | --- |
| `observe` | No additional action work beyond the cycle's observations | Configurable; default 8 seconds |
| `reflect` | Derive legacy concepts from up to 80 recent episodes | Configurable; default 12 seconds |
| `consolidate` | One guarded semantic consolidation run and a checkpoint | 20 seconds |
| `rest` | No additional action work; longer subsequent wait | Configurable; default 35 seconds |

A normal autonomous cycle performs **two perceptions**. Each retains the existing fixed TCP reachability probe to `1.1.1.1:443`. Prediction, scoring, world-model learning, curiosity, and consolidation add no network requests or new sensors.

## Current autonomous cycle

```text
perceive state_before
→ choose predefined internal action
→ predict immediate post-action observation
→ perform action (consolidate may revise semantic memory)
→ perceive state_after
→ describe observed differences
→ evaluate the original prospective prediction
→ assess curiosity against prior published world beliefs
→ calculate unchanged legacy reward from state_before
→ update contextual Q value
→ atomically store episode, transition, prediction, evaluation,
  curiosity assessment, and world-model queue entry
→ process at most 100 queued transitions into world beliefs
→ optionally perform one guarded existing reflection
→ wait for the selected action delay
```

The prediction is made before the action and is never regenerated after seeing the outcome. Curiosity uses the world model before it learns from this transition. Policy-selected consolidation uses already-published beliefs; the current transition is not persisted until later in the cycle.

## Prediction and error

`transition_delta_v1` predicts battery percentage, load ratio, free disk percentage, and network reachability at the **next immediate post-action observation**. It reads at most the latest 200 completed transitions, preferring action-specific evidence, then global evidence, then persistence of the current value. Historical methods require two usable samples.

Numeric predictions add the mean observed delta to the current value. Network predictions use the observed Boolean frequency; a probability of exactly .5 predicts `True`. Predictor confidence describes historical support, `min(.95, evidence_count / 20)`, rather than a probability of correctness.

`prediction_error_v1` compares that exact prediction with `state_after`. It records signed and absolute numeric error, normalized error, and Boolean classification/Brier error. Aggregate `accuracy_score = 1 - mean_normalized_error` must be read alongside coverage. Missing signals reduce coverage; they are not counted as correct predictions. The [architecture guide](docs/architecture.md#prediction-and-evaluation) documents the formulas and unavailable states.

## Four distinct memory layers

| Layer | Storage | Meaning |
| --- | --- | --- |
| Episodic experience | `episodes`, `transitions` | What happened before, during, and immediately after an action? |
| World model | `world_beliefs` | What statistical regularities are currently observed? |
| Semantic memory | `semantic_memories`, `semantic_memory_history` | Which supported regularities have been consolidated, and how have they changed? |
| Legacy concepts | `concepts`, `concept_evidence` | What summaries did the original reflection mechanism produce? |

B4 maintains global and action-conditioned statistics for the same four signals. It publishes a belief after two valid samples and retains evidence counts, contradictions, confidence, and transition provenance. Beliefs describe observed association, not causation. Learning uses an explicit durable queue; older transitions are not silently backfilled.

B6 consumes these published beliefs through **`semantic_v1`**. Promotion requires **at least eight observations and confidence >= .30**. Numeric summaries retain mean delta, mean absolute delta, minimum and maximum delta. Boolean summaries retain true/false counts and their frequency. These thresholds are engineering defaults, not statistical guarantees.

A material source change revises the semantic record and preserves its previous revision. Loss of eligibility marks it `weakened`; restored support reactivates it. Missing or corrupt sources can be reported as `source_unavailable` without erasing the last valid knowledge. Repeated unchanged consolidation leaves semantic records and their timestamps unchanged.

Each policy- or owner-requested consolidation examines **at most 100 beliefs**, using durable cyclic progress so older revised beliefs are revisited. Known high load (`> .8`), low battery (`< 20` while charging is exactly false), or low disk (`< 10`) suppresses the run without extra sensing. Every invocation has a run audit. No new startup, wake, shutdown, or curiosity-triggered consolidation is added.

**Consolidation preserves original memories.** It does not delete episodes, transitions, predictions, evaluations, curiosity assessments, world beliefs, or legacy concepts. No forgetting or pruning is implemented.

## Bounded computational curiosity

B5 stores a **`curiosity_v1`** assessment for each new autonomous transition, combining prediction surprise, prior-belief uncertainty, and novelty. This is a versioned computational heuristic, not a psychological claim.

The owner setting **`prediction_error_curiosity` defaults to `false`**. Assessments are recorded even when it is off. When enabled, a HIGH or VERY_HIGH assessment may invoke the existing internal reflection once, subject to coverage, resource, owner-stop, and cooldown checks. Both ten subsequent autonomous transitions and 300 seconds must separate claims. A policy-selected reflection is not repeated for the same transition.

This optional reflection creates no extra perception, learner transition, reward, or Q update. A durable claim prevents replay after restart, although a crash can lose the optional work. Curiosity never forces consolidation or weights world-model or semantic evidence.

## Battery and version reporting

The battery parser reads complete status fields: `discharging` and `not charging` report false, including under an AC header. `charging` reports true when trustworthy; `charged` on AC retains the existing externally-powered compatibility meaning. Invalid percentages and ambiguous/unrecognized status remain unavailable independently. Corrected current observations can change learner context and resource guards; historical observations are not rewritten and reward formulas are unchanged. The dashboard says `Not charging` for false; that boolean does not identify the power source.

Version fields have separate meanings:

| Field | Meaning |
| --- | --- |
| `/api/status` → `runtime.version` | Version last reported by the core that wrote the runtime record; use lifecycle/freshness to judge whether it is current |
| `/api/bootstrap` → `core_source_version` | Core source accompanying the dashboard (0.2), not evidence of an installed upgrade |
| `dashboard_version`, `dashboard_edition` | Dashboard component identity: 0.1, Observer Edition |
| Bootstrap `version` | Preserved legacy label: 0.1 Observer Edition |
| `supported_schema_version` | Schema supported by this source (5), not the inspected database's actual schema |

Unavailable runtime stays unavailable, and older/stopped telemetry keeps its reported version. The overview labels this “Reported core version.” No build commit is inferred from the dashboard checkout.

## Learning and capability boundaries

The contextual bandit, epsilon, alpha, legacy reward, and Q update remain unchanged:

```text
Q_new = Q_old + alpha × (reward - Q_old)
```

Predictions, evaluation scores, world beliefs, curiosity scores, and semantic memories do not change action selection or that update. B5's optional reflection is the current limited use of prediction error for additional internal activity. B8 owns future decision integration.

SEED does not resist shutdown, prevent sleep, hide, escalate privileges, replicate itself, change security settings, acquire tools, choose arbitrary network destinations, execute generated commands, or modify its own source. Owner authority remains part of its design.

## Persistence and compatibility

The current SQLite schema is **v5**. Supported older memory is backed up before upgrade through the write-capable `Memory` path; migrations are additive. Unsupported or ambiguous schema versions are refused. The dashboard's observer reads do not migrate storage.

Historical absences are valid: pre-B1 episodes may lack transitions; B1 transitions may lack predictions; B2 predictions may lack evaluations; pre-B4/B5 history may lack queued world-model evidence or curiosity assessments. Migration invents none of these. A later explicit consolidation may consume already-published eligible B4 beliefs.

Experience persistence, world-model updates, and semantic revisions have separate transaction boundaries. The **entire cycle is not atomic**: a Q update, reflection, consolidation, or telemetry may commit before a later experience-persistence failure.

## Development verification

Requires Python 3.11+; the verified development suite used Python 3.13.15. The dashboard and tests have separate dependencies from the standalone core.

From the repository root, set up a development environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
```

Run deterministic scenarios with temporary homes and synthetic observations:

```bash
.venv/bin/python -m tests.baseline_scenario
.venv/bin/python -m tests.prediction_error_scenario
.venv/bin/python -m tests.world_model_scenario
.venv/bin/python -m tests.curiosity_scenario
.venv/bin/python -m tests.semantic_scenario
```

Saved [baseline artifacts](docs/baselines/) are immutable evidence for their respective batches. Current executions can legitimately report a newer schema or a larger database footprint; compatibility tests explicitly account for these changes.

## Install and operate

Installation is a separate owner-directed operation on macOS. From the repository root:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer copies the application to `~/Library/Application Support/SEED/app`, creates a per-user LaunchAgent named `local.seed.organism`, and starts it. Starting the current core against supported older memory invokes the backup-and-migration path. No privileged daemon or `KeepAlive` is installed.

Inspect the installed organism:

```bash
python3 "$HOME/Library/Application Support/SEED/app/seedctl.py" status
tail -f "$HOME/Library/Application Support/SEED/seed.log"
```

The local dashboard can be started from a development environment with its dependencies installed:

```bash
.venv/bin/python -m dashboard
```

It binds to `127.0.0.1:8765` by default and uses `SEED_HOME`, or the standard SEED data directory when unset. Observer mode reads existing storage without constructing another organism. Explicit `--operator` mode enables local controls and requires the complete current schema. B4–B6 add bounded inspection APIs; the broader B9 development UI remains unimplemented. See [inspection endpoints](docs/architecture.md#dashboard-and-inspection).

Stop the installed organism:

```bash
launchctl bootout gui/$(id -u)/local.seed.organism
```

Remove startup behavior while preserving memories:

```bash
./uninstall.sh
```

Actual macOS sleep suspends the process. Wake is inferred from a large wall-clock gap; native macOS sleep/wake notifications are not implemented. Normal shutdown records lifecycle state without fresh sensing or semantic consolidation.

## Known limitations and next work

- Ambiguous battery output remains unknown. Unknown-state guard policy is unchanged, and historical charging observations may contain the pre-hardening parser defect.
- Prediction covers the immediate post-action observation; it does not cover the later rest interval.
- Global fallback combines contexts, and action-conditioned statistics do not establish causation.
- Confidence, accuracy, curiosity, and semantic thresholds are engineering measures, not calibrated certainty or intelligence scores.
- Whole-cycle rollback is not provided. Wall-clock adjustment can affect timing, and optional claimed reflection may be lost after a crash.
- Two existing reachability probes remain per normal autonomous cycle.
- Evidence markers, run audits, and semantic history grow with use. B6 adds no forgetting.
- Semantic knowledge is limited to B4's four signals and global/action scopes. It has no cross-signal concepts, multi-step temporal patterns, causal reasoning, or decision influence.

The [low-disk reward mismatch](docs/review-follow-ups.md) remains open: legacy reward can favor consolidation while low disk suppresses its semantic work. Consolidation is not disk cleanup; a decision change requires separate authorization.

**B7 is next, pending explicit authorization.** Self-modeling, the B8 decision upgrade, B9 development UI, and B10 development evaluation remain unstarted. Full acceptance results and inherited limitations are recorded in the [B6 execution log](docs/seed-0.2-development-plan.md#b6-execution-log--2026-09-23).
