# SEED Architecture

**SEED 0.2 — B7 implemented, schema v6.** The local suite passes 634 tests with two existing dependency warnings. Independent review and hosted B7 CI are pending. The [development tracker](seed-0.2-development-plan.md#b7-implementation-record--2026-09-24) is the canonical acceptance ledger; [historical artifacts](baselines/) preserve each batch's evidence. The installed organism is a separate deployment and may be older.

The earlier [post-B6 hardening](reviews/2026-09-23-post-b6-hardening.md) and macOS portability correction closed at source/CI level on master `585affec56ddb0e4580f6df6926b9b6bde291dc0`, with 542 tests. B7 adds descriptive inspection of recorded evidence. B8–B10 remain unstarted.

## Runtime composition

| Component | Source | Responsibility |
| --- | --- | --- |
| Organism | `seed/organism.py` | Sequence autonomous cycles, lifecycle, settings and owner commands |
| Body | `seed/body.py` | Existing host observations and fixed reachability probe |
| Memory | `seed/memory.py`, `seed/migrations.py` | SQLite connection, schema upgrade and linked experience persistence |
| Learner | `seed/learner.py` | Existing contextual bandit and legacy reward/Q update |
| Predictor | `seed/predictor.py` | Prospective immediate-outcome prediction from bounded transition history |
| Evaluator | `seed/prediction_error.py` | Pure comparison of the original prediction with its matching observation |
| World model | `seed/world_model.py` | Persistent descriptive statistics from explicitly queued transitions |
| Curiosity | `seed/curiosity.py`, `seed/curiosity_attention.py` | Pure assessment and durable budget for optional existing reflection |
| Consolidator | `seed/semantic_memory.py` | Bounded promotion and revision of supported world beliefs |
| Self model | `seed/self_model.py` | Bounded descriptive singleton, validation, atomic summary event and freshness projection |
| Infrastructure | `seed/telemetry.py`, `seed/commands.py`, `seed/runtime.py` | Events, owner-command queue and instance lock |
| Dashboard | `dashboard/` | Separate local observer and explicit operator controls |

`Body` observes battery/charging state, load, disk availability, local time, wall-clock time, network reachability and host identity. The existing network probe connects to `1.1.1.1:443`. There is no new sensing or network activity in B2–B7 model processing.

## Sensor and version boundaries after hardening

battery_state() retains its `(percentage | None, charging | None)` interface and fixed pmset command/timeout. It reads one InternalBattery record, validates a 0–100 integer percentage independently, and matches complete normalized status fields. Explicit discharging/not charging is false even on AC. Conflicting status fields, multiple battery records and unrecognized status do not invent a positive charging value. Charged on AC retains the legacy externally-powered true meaning. Historical observations are never relabeled.

The source of core software identity is the side-effect-free `seed/version.py` constant CORE_VERSION=0.2. A running organism writes that value into existing runtime telemetry. The observer never constructs Memory or substitutes its own source identity when stored runtime is absent or older. Existing freshness/ownership/lifecycle checks remain authoritative.

Bootstrap retains token, operator, refresh_seconds and the legacy version label, and adds:

| Field | Meaning |
| --- | --- |
| core_source_version | Core source accompanying this dashboard, currently 0.2 |
| dashboard_version | Dashboard component version, currently 0.1 |
| dashboard_edition | Observer Edition, separate from operator mode |
| supported_schema_version | Imported migration VERSION, currently 6; not an observed database schema |

The actual recorded core software version remains `/api/status` → runtime.version. A stopped/stale record keeps its prior version and freshness state; no record means unavailable. The overview uses “Reported core version” and an Unavailable fallback. Bootstrap exposes no invented build SHA, and no Git subprocess is added to runtime processing.

## Autonomous cycle and ordering

```text
apply settings; infer wake if necessary
→ perceive and detach state_before
→ choose predefined action using the contextual bandit
→ generate and record one prospective prediction
→ perform the action
    reflect: existing legacy concept mechanism
    consolidate: one guarded semantic run plus checkpoint
    observe/rest: no additional action work
→ perceive and detach state_after
→ describe observed differences
→ evaluate the original prediction
→ assess curiosity from the pre-update published world-model snapshot
→ calculate legacy reward using state_before; update Q
→ atomically persist episode + transition + prediction + evaluation
  + curiosity assessment + world-model queue entry
→ recover at most 100 queued transitions into B4 statistics
→ record learning/memory telemetry and latest-state metadata
→ optionally claim and perform one guarded existing reflection
→ publish one self-model snapshot from committed evidence
→ update final runtime telemetry
→ return the selected delay for the subsequent wait
```

Prediction precedes action; evaluation follows the matching `state_after`. Curiosity is assessed before B4 incorporates the current transition. Policy consolidation runs before that transition exists, consuming only previously published beliefs. Detached observation snapshots prevent sensor dictionary reuse from altering provenance.

A normal cycle performs two perceptions. An inferred wake can separately perform the existing wake observation. Delays are 8 seconds for observe, 12 for reflect and 35 for rest by default (configurable), and 20 seconds for consolidate. Post-action observation precedes the wait, including for rest.

## Policy and isolation

The learner uses epsilon-greedy choice among `observe`, `reflect`, `consolidate`, and `rest`, with random choice among tied candidates. Its state key describes energy, load, storage and time-of-day categories. Default epsilon is .15; default alpha is .18.

```text
Q_new = Q_old + alpha × (legacy_reward - Q_old)
```

Legacy reward uses the pre-action observation and selected action. B2–B7 do not change this equation, reward inputs, action ranking, epsilon, alpha, state keys, or returned delays. In particular, suppressing a consolidation run does not alter its selected action or reward.

B5 can add one optional internal reflection after persistence. That limited attention mechanism does not create an extra policy choice, transition or Q update. World beliefs and semantic memories do not feed back into prediction or policy. Semantic memory also does not affect curiosity scoring, cooldown, reflection eligibility, or B4 evidence weight. B8 owns future decision integration.

## Prediction and evaluation

The model contract is `transition_delta_v1`, version 1, horizon `next_post_action_observation`. Targets are `battery_pct`, `load_ratio`, `disk_free_pct`, and `network_reachable`; the last maps to the existing observed field `network`.

One predictor query reads at most the newest **200 raw completed transitions**, limiting rows before filtering malformed evidence. For each target, two usable action-specific samples enable action-conditioned estimation; otherwise two global samples enable global estimation; otherwise the current value is persisted. A missing or invalid current target remains unavailable.

Numeric predictions add the mean historical `after - before` delta to the current value. Battery/disk predictions are clamped to 0–100; load is finite and nonnegative. Boolean history uses the frequency of true post-action observations; `probability_true >= .5` predicts true. Persistence does not invent a historical probability. Numeric validation excludes booleans, nonfinite numbers and invalid domains; Boolean targets require exact booleans.

Predictor confidence is `min(.95, evidence_count / 20)`, labeled `evidence_support`. Persistence and unavailable results have zero historical support. It is not calibrated accuracy.

The pure `prediction_error_v1` evaluator (version 1) accepts the supported prospective contract and compares it with the matching actual observation. It performs no history lookup, database access, sensing, subprocess, network, randomness or input mutation.

| Measure | Definition |
| --- | --- |
| Signed numeric error | `actual - predicted` |
| Absolute numeric error | `abs(actual - predicted)` |
| Battery/disk normalized error | `absolute_error / 100` |
| Load normalized error | `absolute_error / max(1, abs(predicted), abs(actual))` |
| Boolean classification error | 0 for a match, 1 for a mismatch |
| Boolean Brier error | `(original_probability_true - int(actual))²` when that probability is valid |
| Coverage | Number of evaluated targets divided by 4 |
| Mean normalized error | Mean over evaluated targets only |
| Accuracy score | `1 - mean_normalized_error` |

Normalized errors are bounded to 0–1. Network uses Brier error when a valid original probability exists, otherwise classification error. Unknown contracts and invalid/missing inputs are not silently reinterpreted. Targets are `evaluated` or `not_evaluated`, with reasons such as prediction_unavailable, invalid_prediction, actual_unavailable or nonfinite_calculation.

An unavailable aggregate has zero coverage and null error/accuracy. Missing observations never count as zero error. An accuracy score of 1 at coverage .25 means only one target was evaluable and exact. Score and support confidence are distinct engineering measures, neither a probability of truth nor policy reward.

## Persistent world model — B4

`WorldModel` accumulates descriptive numeric deltas and Boolean post-action frequencies, model version 1. Each valid sample contributes once to its global scope and once to its action scope. Four signals and five scopes (global plus four actions) yield at most **20 normal belief identities**.

A one-sample statistic stays in `world_pending`. At two samples it becomes a published `world_beliefs` row. Numeric values retain mean delta, mean absolute delta and extrema; Boolean values retain true/false counts and probability_true. Every belief records evidence, contradictions, creation/update times and first/last transition provenance.

Contradictions are tested against the prior statistic only after four samples:

- Numeric: the new delta opposes the prior mean's sign and both exceed the signal's epsilon in magnitude (.05 battery, .02 load, .01 disk).
- Boolean: false contradicts a prior probability >= .75; true contradicts a prior probability <= .25.

```text
confidence = min(.95, n / 20) × (1 - contradiction_count / n)
confidence_kind = evidence_consistency
```

The result is bounded to 0–.95. Confidence and contradiction counts describe accumulated support and consistency, not causal evidence or a calibrated truth probability.

New autonomous transitions atomically enter `world_model_queue` with their experience. Recovery processes at most **100 queued IDs in ascending order** at construction and after cycle persistence. Each transition's world updates, processed marker and queue removal share an IMMEDIATE transaction. A failed update leaves the experience and queue entry intact for retry. Duplicate processing is prevented by durable markers, not an in-memory set. Older history is not automatically enqueued or backfilled.

Curiosity reads at most eight keyed published rows (global/action candidates for four signals), preferring action scope and falling back to global. B2 continues to use its independent transition-history predictor.

## Computational curiosity — B5

`curiosity_v1`, version 1, assesses the original B3 error against a detached snapshot of prior B4 beliefs. It stores one assessment per new autonomous transition regardless of the owner attention setting.

```text
prediction_surprise = mean_normalized_error × coverage
score = clamp(prediction_surprise
              × (.5 + .5 × uncertainty)
              × (.5 + .5 × novelty), 0, 1)
```

Per valid B4 signal sample, uncertainty is `1 - prior confidence`, or 1 when no published belief exists. Novelty is 1 without a prior belief, .5 with fewer than four prior samples, and otherwise 1 for contradiction or 0 for consistency. Uncertainty and novelty are averaged over usable samples. These components retain their pre-update source snapshots. Unavailable evaluations/samples remain unavailable rather than becoming invented zero-error evidence.

| Score | Level |
| --- | --- |
| < .20 | LOW |
| .20 to < .50 | NOTABLE |
| .50 to < .75 | HIGH |
| >= .75 | VERY_HIGH |
| Unavailable | UNAVAILABLE |

The owner setting `prediction_error_curiosity` defaults to **false**. When enabled, HIGH/VERY_HIGH assessments can invoke the existing reflection only if coverage >= .5, the selected action was not reflect, resource guards pass, and no owner stop is pending. Both **10 subsequent actual autonomous transitions** and **300 seconds** must separate reflection claims.

The claim and cooldown state commit before the callback. Work is at most once: restart cannot replay it, and a crash may lose claimed work. Reflection failures do not release the consumed budget. Reflection uses up to 80 recent episodes and updates only the legacy concept mechanism; it introduces no perception, network access, transition or Q update. Provenance distinguishes policy_selected, owner_requested and curiosity_triggered reflection. Curiosity cannot force consolidation or increase evidence weight.

## Semantic memory — B6

`semantic_v1`, model version 1, consumes **published B4 world beliefs only**. It does not rescan lifetime episodes or independently rediscover statistical patterns. Eligibility requires **evidence_count >= 8 AND confidence >= .30**. These fixed engineering defaults keep semantic promotion distinct from B4's two-sample publication threshold.

| Semantic type | Canonical payload |
| --- | --- |
| `numeric_delta_summary` | mean_delta, mean_absolute_delta, min_delta, max_delta; interpretation `observed_transition_delta` |
| `boolean_frequency_summary` | true_count, false_count, probability_true; interpretation `observed_boolean_frequency` |

Identity combines semantic type, signal, scope, scope value and model version. Source belief ID, source model version, source update time, evidence, contradictions and first/last transition provenance remain inspectable. No LLM-generated prose, causal assertion, new signal or richer scope is introduced.

An eligible new identity creates one active record at revision 1. Canonical source fingerprints detect material changes to evidence, contradictions, confidence, source values or provenance even when timestamps are equal or reversed. Formatting changes, equivalent numbers such as 1 and 1.0, and timestamp-only changes cause no revision. Source update time therefore reflects the last materially consolidated source state.

Before mutation, the complete prior row is saved in `semantic_memory_history`. Loss of eligibility changes status to `weakened`; restored support returns it to `active`, each with a new revision. Creation time remains fixed. A malformed source is counted as an item failure and can mark existing knowledge `source_unavailable` while preserving its last valid statistics. Other valid items continue. The read layer also reports missing/corrupt sources without rewriting history or sweeping for orphans.

### Invocation and bounded progress

Existing policy-selected and owner-requested `consolidate` each invoke the same engine. Policy uses its already-observed pre-action state; owner requests use the latest persisted state. Both retain checkpoint metadata (`at`, episode/concept counts, run_id and status). Owner requests do not create learner transitions or Q updates.

Resource suppression uses no new perception. A known load > .8, battery < 20 with charging exactly false, or disk < 10 produces a suppressed audit with high_load, low_battery or low_disk and zero work counts. Unknown/invalid values are not assumed to violate a guard; owner state may be stale.

Each run reads **at most 100 world beliefs** after a persistent ID cursor in ascending order, wrapping within the remaining budget. This cyclic cursor revisits older changed IDs and survives restart. Fingerprints make unchanged revisits idempotent. Migration/startup/wake/shutdown and curiosity add no consolidation invocation. An explicit later run may promote already-published eligible beliefs.

### Transaction and audit

A started run audit commits first. One IMMEDIATE transaction includes semantic changes, prior revisions, cursor, per-item events and final counters. Acquisition or processing failure rolls back work and records a failed audit with zero committed successes where storage permits, then propagates the error. A crash can leave a running audit; later explicit work uses durable progress without automatically replaying the invocation.

Runs expose examined, eligible, created, revised, weakened, unchanged and failed counts. Malformed items allow completed_with_errors; a failed source can also cause a source_unavailable revision, so failed/revised counts can overlap. weakened_count measures entry into weakened status; further changes to an already-weakened record count as revisions.

Repeated unchanged runs can add run/events and update cursor/checkpoint metadata, but leave semantic rows, timestamps and history untouched. No original memory is deleted, pruned or expired. Run audits and revision history grow over time.

## Descriptive self model — B7

`self_model_v1` is a durable current description, not a decision input. `SelfModel.update` runs once after optional curiosity reflection and before final runtime telemetry. It reads the just-committed transition's `state_after_json`, never the latest-state metadata or fresh sensors. Owner commands, inspection, startup and reopen do not trigger publication. Equal or older transition IDs are skipped. Stored runtime may therefore describe the prior completed cycle; no current heartbeat is invented.

The fixed catalog describes the four existing actions and their capabilities. Consolidation remains selectable even when its most recent audit reports suppression. Observation fields, coverage and scores, storage counts, consolidation, runtime and retained failures each carry a value, status, reason and source reference. Unknown, invalid and unavailable evidence remain distinct from zero or false. These fields never influence the learner, predictor, evaluator, world model, curiosity, semantic memory, reward, or delays.

Prediction performance considers the latest 100 raw transitions through the current ID. Missing, unsupported and malformed records consume that window. Coverage averages valid B3 evaluations, including unavailable evaluations with zero coverage; error and accuracy average only evaluations with scores. Scores are engineering summaries with explicit sample counts, not calibrated competence. Three synthetic valid cases yield coverage 5/12, mean error .06, mean accuracy .94 and two scored samples.

Freshness uses original source timestamps: observations 60 seconds, prediction evidence 300 seconds, storage 60 seconds, consolidation 300 seconds, runtime 10 seconds, failures 60 seconds. The catalog is static. A read projects stale/clock-error statuses without replacing stored values or timestamps. Missing runtime stays missing after restart. Backward clock movement is reported, not silently corrected.

Publication uses a nonblocking memory lock, zero SQLite busy timeout, at most 14 evidence reads plus the timeout read, and a 100,000-step SQLite VM budget. Counts read at most 1,001 IDs and become lower bounds beyond 1,000. Failures use the latest 100 retained ERROR records plus one lookahead; they are not a failure rate. Source JSON is capped at 16 KiB; snapshots at 32 KiB, with depth/member/array and domain validation. Database size is logical page size × page count, not filesystem usage.

The singleton and bounded SELF_MODEL summary event commit together, including existing event-retention behavior. An interrupted or failed replacement preserves the last committed snapshot; a separate failure diagnostic is best effort. Stop, duplicate and contention paths cannot fabricate a new snapshot. The shared connection's timeout and progress handler are restored. This transaction does not make the entire autonomous cycle atomic.

`GET /api/self-model` accepts no parameters and uses four bounded reads on a read-only connection with a 100,000-step budget. It validates the schema, persisted envelope, nested domains and source transition before projection. Legacy storage returns unavailable with `legacy_schema`; an empty v6 singleton reports `awaiting_first_cycle`; corrupt payloads report `invalid_snapshot`. Incompatible schema versions return 409 and inaccessible databases return the existing sanitized 503 response. The response is capped at 40 KiB. No live process, Memory constructor, sensor, migration or write is invoked.

## Storage layers and schema

| Layer | Tables | Role |
| --- | --- | --- |
| Experience | `episodes`, `transitions` | Original observations, action, differences, reward, prediction and evaluation |
| Legacy reflection | `concepts`, `concept_evidence` | Existing recent-observation summaries, separate from semantic knowledge |
| World model | `world_pending`, `world_beliefs`, `world_model_queue`, `world_model_processed` | Prospective statistical accumulation, publication, retry and provenance |
| Curiosity | `curiosity_assessments`, `curiosity_runtime` | Assessments, attention outcomes and durable cooldown |
| Semantic knowledge | `semantic_memories`, `semantic_memory_history` | Current consolidated records and complete prior revisions |
| Consolidation | `consolidation_runs`, `consolidation_state` | Run audit and persistent cyclic cursor |
| Self model | `self_model_current` | One validated current snapshot, source transition and measurement timestamp |
| Supporting state | `meta`, `q_values`, telemetry/operator tables | Identity, learned policy, settings, lifecycle and local controls |

Supported migration path:

```text
unversioned → v1 instrumentation → v2 transitions
→ v3 world model → v4 curiosity → v5 semantic memory → v6 self model
```

The write-capable `Memory` constructor checks existing schema and backs up supported older memory before upgrading. The migration ladder is transactional and additive. Unknown, future, ambiguous or duplicate schema versions are refused. Direct low-level migration does not substitute for the constructor's filesystem backup policy. V5 creates empty semantic/history/run/progress tables; v6 adds only the empty self_model_current singleton table. Neither step backfills history.

Historical records remain valid across eras: episodes may lack transitions, transitions may lack predictions, predictions may lack evaluations, and older experiences may lack world-model eligibility or curiosity. These absences are not corruption and are not filled with invented observations.

### Atomicity boundaries

One current experience transaction stores the linked episode/transition (including prediction and evaluation), its B4 queue entry, and curiosity assessment. World-model processing and semantic consolidation use their own transactions. Curiosity claims and reflection effects also commit separately.

The entire physical cycle is **not transactional**. Reflection, consolidation, telemetry and Q updates can survive a later experience-storage failure. No whole-cycle rollback is claimed. Observed before/after differences remain descriptive association; presence flags distinguish missing fields from present null values.

## Dashboard and inspection

The dashboard never constructs a second organism. Observer services use read-only SQLite connections; operator mode requires schema v6 and its required tables rather than migrating storage. The CLI binds to `127.0.0.1`, with no arbitrary host option. Existing Host/Origin checks, required mutation Origin, CSRF, bounded request bodies, strict models and fixed command allowlists remain in place.

B4–B7 inspection routes are bounded:

| Route | Result and filters |
| --- | --- |
| `/api/self-model` | One persisted current snapshot with read-time freshness; no parameters |
| `/api/world-beliefs` | Ascending ID pages; signal, scope, scope_value, after, limit |
| `/api/world-beliefs/{id}` | One published belief and provenance |
| `/api/curiosity` | Newest assessments first; inclusive before transition ID, limit |
| `/api/curiosity/summary` | Summary over at most 100 recent assessments |
| `/api/curiosity/{transition_id}` | One assessment and attention outcome |
| `/api/semantic-memories` | Ascending ID pages; signal, scope, persisted status, after, limit |
| `/api/semantic-memories/{id}` | One current record and source_status |
| `/api/semantic-memories/{id}/history` | Prior revisions newest first; inclusive before revision, limit |
| `/api/consolidation-runs` | Newest audits first; inclusive before run ID, limit |

List pages default to 50 and allow 1–100 items, with one lookahead row for next_cursor. Use the returned cursor with the appropriate after/before parameter. Semantic source_status reports current source availability separately from the persisted semantic status; the status filter selects the latter. A history record is the saved prior state, not a fresh source interpretation.

Legacy storage without the corresponding feature tables returns unavailable empty lists or 404 details, without migration. These are inspection APIs; B9's broader development UI is still unimplemented.

## Owner commands and lifecycle

Owner observe, reflect and consolidate remain distinct from autonomous policy experience. Owner observation stores an episode; reflection uses owner_requested provenance; consolidation runs the same bounded B6 engine with owner_requested provenance. None automatically performs autonomous prediction/evaluation or learner Q updates.

The per-user LaunchAgent has no KeepAlive. The core uses an instance lock, honors termination signals and does not resist shutdown. Actual system sleep suspends the process; wake is inferred from a large wall-clock gap rather than native macOS notifications. Normal shutdown records last-known lifecycle state without fresh sensing or a semantic consolidation pass.

## Bounds and known limitations

| Operation | Bound |
| --- | --- |
| Predictor history | Latest 200 raw transitions; four targets |
| Evaluator | Four targets; no database query |
| World-model recovery | 100 queued transitions per pass |
| Curiosity prior-belief snapshot | At most eight keyed published rows |
| Optional reflection | At most once per eligible claimed transition; 10-transition and 300-second cooldowns |
| Legacy reflection window | 80 recent episodes |
| Semantic run | 100 published beliefs, with durable cyclic progress |
| Feature inspection page | 100 returned items plus one lookahead |

Bounds limit model work, not total database growth. Existing checkpoint counts, retained episodes, B4 processed markers, assessments, audits and semantic history remain subject to growing storage.

Inherited limitations include historical battery misclassification (corrected only for new observations), inferred wake, wall-clock adjustments, immediate prediction/rest horizon, mixed contexts in global fallback, legacy learner assumptions about malformed live state, and incomplete whole-cycle atomicity. Normal autonomous cycles still have two existing reachability probes.

World beliefs and action associations are descriptive rather than causal. Predictor support, B3 accuracy, B4 consistency, B5 curiosity and B6 promotion thresholds are separate engineering measures, not calibrated certainty. Curiosity is coarse and optional work can be lost after a claim. Semantic knowledge only summarizes B4's existing signals/scopes and changes when consolidation is invoked; it has no cross-signal concepts or multi-step temporal patterns.

Semantic-driven policy, prediction-error reward shaping, candidate-action planning, forgetting, arbitrary external tools, generated shell/code execution, autonomous source modification and LLM cognition are not implemented. B8–B10 require explicit authorization and their own acceptance evidence.

The [low-disk decision mismatch](review-follow-ups.md) is reproduced and deferred to separately authorized B8 or a new owner-defined scope. No learner formula or consolidation guard is changed to resolve it in B7.

## Verification

The [B7 record](seed-0.2-development-plan.md#b7-implementation-record--2026-09-24) and [comparison artifact](baselines/seed-0.2-b7-comparison.json) cover migration preservation, exact metrics, corruption, bounded processing, transactional failures, restart/freshness, read-only inspection and unchanged all-action policy runs.

The [B6 execution record](seed-0.2-development-plan.md#b6-execution-log--2026-09-23) records the 497-test suite, 71 new B6 tests, independent review and corrected transaction-acquisition audit regression. Coverage includes migration/backup/rollback, material revision and idempotency, actual contradictory evidence followed by reactivation, bounded/restarted work, failure isolation, resource suppression, read-only APIs and upstream compatibility.

The [B6 comparison artifact](baselines/seed-0.2-b6-comparison.json) reproduces the semantic lifecycle and checks B5 curiosity, B4 statistics, B3 evaluation and baseline policy outputs. Earlier batch artifacts remain immutable. Reproduction commands are in the [README](../README.md#development-verification); they use synthetic observations and temporary homes rather than installed memory or live sensors.

For current local commands, pinned-action provenance, CI failure handling and pending hosted/merge-rule gates, use the [verification guide](verification.md). The 497-test B6 result above remains a historical acceptance record; the hardening result is recorded separately.
