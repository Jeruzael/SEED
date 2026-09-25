# SEED 0.2 B7 — Self Model Design

Design status: **COMPLETE FOR OWNER REVIEW**. Implementation: **NOT STARTED**.
Written and reviewed on **2026-09-24 (Asia/Manila)**. The filename retains the
2026-09-23 date explicitly requested in the owner's design instruction.
This is a proposed contract, not a description of implemented B7 behavior.

## Goal

Represent measurable capabilities and limitations as structured, versioned facts
from existing evidence. Preserve unknown, unavailable, stale and erroneous states.
Provide durable current-state inspection without changing any decision or learning
input. Owner approval of this document and separate implementation authorization
are required before production, migration, test, API or dashboard changes.

## Verified starting state

- Repository: Jeruzael/SEED; clean approved master and origin/master at
  `585affec56ddb0e4580f6df6926b9b6bde291dc0`, merge of PR #9.
- Dedicated design branch: `seed-0.2-b7`; no reset or history rewrite.
- Fresh local `.venv/bin/python -m pytest -q`: **542 passed, zero failed/skipped,
  two existing dependency warnings**, exit 0. macOS 26.5.1 arm64, Python 3.13.15.
- Fresh standalone commands, each exit 0 and valid JSON:
  `.venv/bin/python -m tests.baseline_scenario`,
  `.venv/bin/python -m tests.prediction_error_scenario`,
  `.venv/bin/python -m tests.world_model_scenario`,
  `.venv/bin/python -m tests.curiosity_scenario`,
  `.venv/bin/python -m tests.semantic_scenario`.
  All five outputs equal the preceding portability-correction outputs exactly.
- GitHub run [35884486727](https://github.com/Jeruzael/SEED/actions/runs/35884486727)
  job metadata confirms success for linux-py311, linux-py313 and macos-py313 on
  that exact merge SHA. The owner's supplied post-merge evidence reports 542
  tests on each. This design audit reconfirmed job metadata and local results;
  it did not repeat the prior hosted-artifact download audit.
- Dependency lock SHA256:
  `1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769`.
  All seven historical baseline artifacts remain unchanged.
- Local audit output is in ignored `.review-artifacts/b7-design/`; it is not
  production storage or a new committed B7 comparison artifact.
- Current implementation remains B0–B6, schema **5**, core software version **0.2**.
  Hardening and portability correction are closed at source/CI level. Installed
  organism, installed home, processes, LaunchAgent and deployment were untouched.

## Existing architecture and evidence sources

The required README, architecture, tracker, implementation log, verification guide,
core modules, observer/read services and named tests were read completely. Migration
fixtures for unversioned and v1–v4 storage and all five scenario modules were also
inspected. Relevant source contracts at the verified base are:

| Source | Existing fact | Consequence for B7 |
| --- | --- | --- |
| `seed/organism.py::cycle` | Two observations; one prospective prediction; post-observation evaluation; prior-belief curiosity; unchanged reward/Q; atomic experience; B4 recovery; optional reflection | Add only a downstream call after optional reflection |
| `seed/memory.py::record_transition_experience` | Episode, transition, prediction/error, curiosity and B4 queue entry commit together | A committed transition ID is mandatory; never derive from an uncommitted argument |
| `seed/learner.py` | Q writes commit separately before the experience transaction | B7 cannot roll back or replay earlier effects |
| `transitions.state_after_json` | Exact persisted post-action observation; `completed_at` is separate | Use this row, not mutable `meta.last_state`, which owner observations also change |
| `seed/body.py` | Nine relevant recorded fields; missing battery/ambiguous charging can be null | Static implementation support does not prove current observation availability |
| `seed/prediction_error.py` | Four-target `prediction_error_v1`, coverage separate from normalized score | Aggregate existing evaluations only; never rerun predictor/evaluator |
| `seed/world_model.py` | Recovery handles at most 100 queued IDs; published/pending identities normally total at most 20 | Inspect bounded queue depth; do not run recovery or consume beliefs in B7 |
| `seed/curiosity_attention.py` | Optional reflection claims/outcomes occur after B4; off by default | B7 follows it and neither requests nor suppresses it |
| `seed/semantic_memory.py` | A bounded consolidation audit records suppression, failures and actual work counters | Report latest run independently; it has no transition foreign key |
| `runtime.data_json` | Heartbeat, session, last successful cycle; last-success value is updated at cycle end | Before final runtime write this can describe the preceding cycle; label it as reported |
| `events` | Monotonic IDs; `(category,id)` index; existing retention | Count a bounded retained ERROR sample; do not claim exhaustive failures |
| `seed/telemetry.py::emit` | May prune retained events on every 100th event ID | Reuse existing retention inside the B7 VM budget; do not invent a second retention policy |
| `Memory.stats`, `SeedService.status/health/storage` | Some lifetime counts and filesystem inventory; status checks host process ownership | Do not reuse these as a bounded B7 builder or read endpoint |
| `ReadStore.connection` | Checked paths and SQLite `mode=ro`, no core construction | Preserve this observer boundary |
| `seed/migrations.py` | v4→v5 currently writes `VERSION` directly | Explicitly write intermediate 5 before adding the future 5→6 step |

The whole cycle is not transactional. Consolidation, concepts, Q and telemetry can
commit before later stages fail. B7 adds one independent transaction, not a wider
rollback claim. Existing charging-parser hardening applies to new observations;
B7 cannot certify or repair historical sensor accuracy.

## Requirements

1. Every measurement has a named source, bounded read, units, status and freshness.
2. Only committed evidence at explicit cutoffs may contribute. Unknown is not
   safe, missing is not zero, and stale is not current.
3. A durable singleton and a bounded summary event commit atomically on success.
4. Restart preserves the snapshot and its original timestamps; no backfill,
   replay, fresh sensing or startup publication.
5. Calculation/storage failure does not deliberately fail a completed autonomous
   cycle or erase its previous snapshot. Existing unrelated core failures retain
   their current behavior.
6. Observer inspection is bounded and read-only, including legacy/error cases.
7. B7 has no upstream consumers and adds no external activity or scheduling.
8. Implementation acceptance must prove persistence, telemetry, corruption,
   freshness, bounds and policy isolation with deterministic temporary fixtures.

## Non-goals

B7 does not implement B8 decision integration, goals or goal progress, planning,
arbitrary tool use, source-code self-modification, self-generated commands, new
sensors, new network calls, browsing, downloads, privilege escalation, deployment
automation, personality, emotions, consciousness, introspective narrative,
LLM-generated free-form self-description, automatic memory deletion, B9 Self Model
UI, or B10 developmental-improvement claims. No anthropomorphic records are allowed.
There is no memory-health scalar, calibrated confidence, causal capability claim,
new owner setting, trigger endpoint, background scheduler, thread, sleep or retry loop.

## Design alternatives

| Approach | Advantages | Costs / limitations | Decision |
| --- | --- | --- | --- |
| A: derive entirely on read | No new schema; minimal stored duplication | Repeated multi-table work; no durable exact source cutoff after restart; cannot satisfy persisted-self-model acceptance cleanly | Reject for B7 |
| B: persisted current snapshot | One bounded row; explicit evidence cutoffs; atomic publication; restart continuity; cheap observer reads | Overwrites the preceding snapshot; requires precise failure and freshness semantics | **Select** |
| C: current plus revision ledger | Full historical snapshots and change comparisons | Dynamic observations would produce frequent revisions; unbounded growth/retention choices; extra replay/query complexity and overlap with B10 | Reject for B7 |

The selected design retains small existing-style events, not a second snapshot
history. Those summaries cannot reconstruct every former snapshot and must not be
advertised as such. This tradeoff meets B7 persistence with the smallest architecture.

## Selected architecture

```text
committed cycle and existing records at fixed cutoffs
    → bounded reader and deterministic builder in seed/self_model.py
    → one self_model_current row + one SELF_MODEL summary transaction
    → read-only snapshot validation and freshness projection
    → GET /api/self-model
```

`SelfModel(memory, clock=time.time).update(transition_id, session_id, stop_event)`
is the proposed core entry point. It returns an operational result only to its
caller for diagnostics; the organism must not branch policy or timing on it.
The already-observed `state_after` is read from the just-committed row, avoiding
an additional mutable input and proving persistence provenance. A pure builder
accepts a bounded evidence bundle and explicit measurement time. A pure validator
and projection function are shared with the read service; they import no dashboard
code and perform no I/O. No new dependency is needed.

## Self-model field catalog

Every dynamic field uses the measurement envelope defined below. Nested members
of one envelope inherit its status and source; members with different clocks are
separate envelopes. The following tables enumerate the complete v1 catalog.
Query identifiers refer to Resource bounds. `O`, `P`, `S`, `R`, `C`, `E` refer to
freshness policies defined in Status and freshness semantics. All null values
retain their explicit reason. Source IDs, timestamp kind, clock and TTL are exposed
through the referenced entry in `sources`.

| Field | Meaning, exact source and bounded query | Units / validation | Availability, freshness, stale/error behavior and provenance |
| --- | --- | --- | --- |
| `observations.battery_pct` | `transitions.state_after_json.battery_pct` at current ID; Q3 | Percent, finite nonboolean number 0..100 | O; missing/null unavailable (`not_recorded`), invalid error; stale retains value; observation row ID + its `wall_time` |
| `observations.charging` | Same row's `charging`; Q3 | Exact boolean | O; null means unknown charging, not False or battery power; wrong type error |
| `observations.load_ratio` | Same row's `load_ratio`; Q3 | Finite nonboolean number >=0, normalized one-minute load, not CPU percent | O; missing unavailable; invalid error; no fabricated upper bound |
| `observations.load_5m_ratio` | Same row's `load_5m_ratio`; Q3 | Finite nonboolean number >=0, normalized five-minute load | O; same rules |
| `observations.disk_free_pct` | Same row's `disk_free_pct`; Q3 | Percent, finite nonboolean number 0..100 | O; missing unavailable; invalid error |
| `observations.network` | Same row's `network`; Q3 | Exact boolean, result of the existing fixed reachability probe | O; False is a valid recorded negative result, not sensor unavailability; missing unavailable; invalid error |
| `observations.hostname` | Same row's `hostname`; Q3 | Nonempty UTF-8 string <=128 bytes | O; empty/null unavailable, oversized/wrong type error; never used as an authorization identity |
| `observations.machine` | Same row's `machine`; Q3 | Nonempty string <=128 bytes | O; same rules |
| `observations.macos` | Same row's `macos`; Q3 | Nonempty string <=128 bytes | O; same rules; absent OS metadata is not proof of platform support |
| `capabilities.sensors.<each of the nine names>` | Fixed mapping to the corresponding observation envelope; `seed/body.py::Body.perceive` contract | `{supported:true, reading:"observations.<name>"}` | Static support only. Currently available iff referenced status=available; stale iff stale; unknown for unavailable/error/insufficient. Never infer working hardware from support |
| `resources.<battery_pct,charging,load_ratio,disk_free_pct,network>` | Fixed aliases to the corresponding observation paths | String path; no duplicated measurement | Exact same O status, source and timestamp as observation, including false/null |
| `capabilities.actions.observe` | `Learner.choose` candidate list + `perform_action`; fixed v1 catalog | Implemented/selectable/owner_controlled true; `work_kind=no_additional_processing` | Static contract, not proof of observation triggered by action; observations occur outside dispatcher |
| `capabilities.actions.reflect` | Same candidate list + `SeedOrganism.reflect` | True flags; `work_kind=bounded_reflection` | Static; selectable does not assert new concepts were written |
| `capabilities.actions.consolidate` | Same list + `Consolidator.run` | True flags; `work_kind=guarded_semantic_consolidation` | Static; suppression does not change selectable; latest run reported separately |
| `capabilities.actions.rest` | Same list + delay mapping | True flags; `work_kind=post_cycle_wait` | Static; action dispatch has no substantive work; B7 does not wait |
| `capabilities.unsupported.<arbitrary_tools,planning,self_modification>` | Fixed, audited absence from the allowed core action contract | Envelope value false, status not_supported, source catalog | No expiry: statement about producer contract only; never inferred from history or enabled by owner text |
| `last_selected_action` | Current `transitions.action`; Q3 | One of four fixed action strings | O uses completion source, not state wall_time; unavailable on absent record (update fails); invalid action error; ID exposed |
| `prediction_performance.window` | Q4 raw latest 100 transitions at/below source ID | Counts and ID list; exact partition defined below | S-like query freshness, TTL 300; empty window is an available zero count, never zero error; malformed rows counted |
| `prediction_performance.coverage` | Mean persisted B3 coverage across supported valid evaluations, including unavailable aggregates | `{samples,mean}`, mean 0..1 | P with newest valid evaluation completion; no samples insufficient_evidence unless malformed-only (error); own source ID list |
| `prediction_performance.score` | Mean persisted mean_normalized_error and accuracy_score across valid evaluated B3 aggregates only | `{samples,mean_normalized_error,accuracy_score}`, scores 0..1 | P with newest scored completion; no scored samples insufficient_evidence, never score zero/one; source IDs separate from coverage |
| `memory.storage` | Q2, Q7–Q10, Q13–Q14 | Schema integer; read-check true; page size/count and logical allocated bytes; four bounded counts | S: 60 seconds since consistent query snapshot. SQL failure aborts update; no fabricated readable=false snapshot. Not an integrity check or physical WAL-inclusive footprint |
| `memory.latest_consolidation` | Q11 latest audit by ID; fixed selected columns only | Run ID, audit status/provenance, start/end, source_beliefs_examined, created/revised/weakened/unchanged/failed counts, nullable suppression reason | C: 300 seconds from completed_at, or started_at for running audit; absent unavailable; malformed error; run source independent of current transition |
| `memory.runtime_reported` | Q12 runtime singleton: heartbeat, last_successful_cycle, session_id | Seconds since epoch, session string <=128 bytes; last_successful_cycle nullable | R: 10 seconds from heartbeat; missing heartbeat unavailable, invalid/future error; reported previous cycle time does not certify liveness/current success |
| `recent_failures` | Q5 latest 101 retained ERROR IDs at/below Q6 event cutoff; keep first 100 | Count 0..100, lookahead bool, oldest/newest IDs, latest valid event time/source/category, invalid metadata count | E: 60 seconds from query snapshot, not age of last error. Empty sample count=0 is valid only for this retained window; corrupt metadata remains visible |

`recent_failures.count` counts the selected retained ERROR rows even when their
metadata is malformed. `latest_valid_event` is the highest-ID row in the first100
with finite nonfuture timestamp and a nonempty source <=128 bytes; its exact shape
is `{id,ts,category:"ERROR",source}`, or null. Oldest/newest IDs describe the raw
sample. `has_older_retained_errors` comes only from the 101st row. Invalid metadata
increments invalid_metadata_count and yields reason=partial_window; if all sampled
metadata is invalid, status=error with the raw count retained. No substring search
of messages classifies a storage failure. All numeric storage facts must be valid;
logical_allocated_bytes is page_size × page_count with positive page size, nonnegative
count and product within signed 64-bit range. It describes allocation before the
B7 upsert/event, which can itself increase pages.

Static action envelopes have `source=catalog`, `status=available`, `reason=null`.
`owner_controlled=true` means existing stop/settings/command authority still bounds
execution; it does not imply all four actions have individual enable switches.
No generic `substantive_work_performed` boolean is emitted: a selected/completed
action does not prove a new concept or semantic revision. Latest consolidation
counters report actual audited work. Suppressed audits retain zero work counts,
status=suppressed and their recorded reason; failed counts are not disjoint from
revision counts. Policy-selected audit provenance alone is insufficient to link
that audit to the current transition. Reflect has no complete per-transition work
audit in the existing schema, so B7 makes no stronger claim.

Candidate decisions: accept the aggregate prediction measures above. Per-signal
numeric MAE, network classification accuracy and Brier means are measurable from
B3 but are omitted from v1 to keep this summary small; detailed source evaluations
retain them. Do not invent error *rates*: ERROR records lack a reliable common
attempt denominator. Storage/database error subtypes are not reliably structured
in existing generic ERROR metadata, so report category/source and no guessed SQL
failure rate. Reject a health scalar and runtime integrity scan. Adopt bounded
row-count facts instead of unbounded exact lifetime counts; omit concepts/history
counts and filesystem tree inventory. These are deliberate scope decisions, not
unresolved requirements.

### Prediction eligibility and arithmetic

Q4 bounds raw rows **before** validation, descending ID, never filling the window
from older rows after exclusions. A row cannot contribute if its ID exceeds the
trigger ID, completion is missing/nonfinite/future relative to `measured_at`, or its
start is after completion. Partition the raw window into `valid_evaluations`,
`missing_evaluations` (SQL NULL), `unsupported_evaluations` (well-formed unknown
contract), and `invalid_evaluations` (invalid JSON, size, time or contract values).
These counts sum to `raw_rows`; record ascending `raw_transition_ids` (at most 100).

Supported metadata is exactly evaluator prediction_error_v1/version 1, prediction
model transition_delta_v1/version 1, horizon next_post_action_observation. Require
all four known signal entries; evaluated numeric signal errors must be finite and
nonnegative with normalized_error in 0..1 and correct scoring_method; network
entries require strict correct boolean, classification_error 0/1 consistent with
correct, and the recorded mismatch/Brier method's required finite 0..1 fields.
Not-evaluated entries require the existing explicit reason and no numeric score.
Require aggregate target_signals=4, evaluated_signals matching actual evaluated
entries, coverage=count/4, aggregate status and nullable scores consistent with
that count. Cross-check aggregate mean against persisted normalized entries and
accuracy_score=1-mean with absolute tolerance 1e-12. This validates recorded
arithmetic; it never recomputes a prediction or compares against new observations.

Coverage includes valid unavailable aggregates (coverage zero). Score means include
only valid evaluated aggregates. Compute means using scaled finite accumulation
(`math.fsum(value/n)` for bounded scores), never summing extreme raw load values.
Read coverage beside score: a partial perfect prediction can have accuracy 1 with
coverage .25. Scores are heterogeneous engineering summaries, not confidence,
calibration, improvement or a probability that the system is capable.
When some rows are invalid, valid rows still contribute and `reason=partial_window`
on coverage/score makes exclusion visible. With no denominator, status is error if
any invalid rows exist, otherwise insufficient_evidence (`no_supported_evaluations`
or `no_scored_evaluations`). Unsupported/missing rows do not become errors or zeros.

## Status and freshness semantics

Measurement envelope (all four keys required):
`{"value":...,"status":"available","reason":null,"source":"observation"}`.
A source reference must resolve inside the same payload; no external fetch is
required to interpret it. Fixed source registry entries expose table/record IDs,
`source_observed_at`, `timestamp_kind`, and `ttl_seconds`. Root `measured_at` is
builder time, not observation time; root `source_transition_id` is the committed
trigger, `source_event_id` is the maximum event ID visible **before B7 telemetry**,
and `source_session_id` is the producing organism session passed by the cycle.

| Status | Exact meaning |
| --- | --- |
| available | Valid measurement with its required timestamp, within its stated freshness policy; not a hardware, integrity or liveness guarantee |
| unavailable | Supported measurement not recorded, including null sensor, absent run or missing timestamp; value null for absent data |
| stale | Previously valid available measurement beyond its TTL; retain value and original provenance |
| error | Wrong type/range, malformed data, inconsistent contract or clock contradiction; do not present an invalid value as a measurement |
| not_supported | Fixed capability absent from the producer's v1 contract; value false |
| insufficient_evidence | Retrospective metric has no supported denominator; value includes samples=0 and null means |

The closed measurement reason vocabulary is null, not_recorded, missing_timestamp,
invalid_value, invalid_json, oversized_source, invalid_timestamp, clock_regression,
source_expired, snapshot_expired, partial_window, invalid_evidence,
no_supported_evaluations, no_scored_evaluations, no_consolidation_run,
missing_runtime, outside_action_contract. Available uses null or partial_window;
stale uses source_expired when the source TTL is exceeded, otherwise snapshot_expired;
error uses the applicable invalid/oversized/clock code. A malformed-only prediction
window uses error/invalid_evidence and retains samples=0/null metrics. Missing run
and missing runtime use their corresponding unavailable reasons. Static unsupported
capabilities use not_supported/outside_action_contract. Missing value precedes
missing timestamp; invalid value precedes both. Source-specific validation errors
are confined to the affected measurement envelope.

The closed measurement reason vocabulary is null, not_recorded, missing_timestamp,
invalid_value, invalid_json, oversized_source, invalid_timestamp, clock_regression,
source_expired, snapshot_expired, partial_window, invalid_evidence,
no_supported_evaluations, no_scored_evaluations, no_consolidation_run,
missing_runtime, outside_action_contract. Available uses null or partial_window;
stale uses source_expired when the source TTL is exceeded, otherwise snapshot_expired;
error uses the applicable invalid/oversized/clock code. A malformed-only prediction
window uses error/invalid_evidence and retains samples=0/null metrics. Missing run
and missing runtime use their corresponding unavailable reasons. Static unsupported
capabilities use not_supported/outside_action_contract. Missing value precedes
missing timestamp; invalid value precedes both. Source-specific validation errors
are confined to the affected measurement envelope.

Unknown is represented by unavailable/insufficient_evidence, with a reason, rather
than a seventh status. For valid sensor values with missing wall_time, preserve
value but status=unavailable/reason=missing_timestamp. Invalid values become null;
raw malformed values are never copied into the model. Status precedence is
invalid/clock error, absent/insufficient/not_supported, then age-based stale, then
available. A source clock greater than builder time is error/clock_regression;
no clamping to age zero. Finite timestamps must be nonboolean and >=0.

Freshness policy is fixed engineering metadata, not a new setting:

| Policy / registry key | Timestamp and TTL | On read / restart |
| --- | --- | --- |
| O / observation | Persisted state_after.wall_time, 60s; require wall_time <= completed_at <= measured_at | Stale after 60s; no fallback to completion or builder time |
| O / transition | Current transition.completed_at, 60s | Last selection is historical once stale |
| S / storage | measured_at, 60s | Facts describe the sampled database, not the database at read time |
| S / prediction_window | measured_at, 300s; exposes raw completed-time range where valid | Window counts can be fresh while metric evidence is old |
| P / prediction_coverage | Newest valid contributing completion, 300s | Stale if either source age or snapshot age exceeds 300s |
| P / prediction_score | Newest scored contributing completion, 300s | Independent of coverage's denominator and clock |
| R / runtime | runtime.heartbeat, 10s; last_successful_cycle remains an explicit timestamp inside value | No process/lock probe; never assert live ownership; null success is not failure |
| C / consolidation | Latest run completed_at, or started_at if still running, 300s | Stale audit retained, including incomplete running audit |
| E / errors | measured_at, 60s; individual error times retained as historical facts | Old latest error does not make a current zero/nonzero sample query invalid |
| catalog | Versioned source contract, no TTL, no observation timestamp | Refers only to the saved producer contract, not the currently running binary |

Age exactly TTL is available; greater is stale. The API returns a detached
projection at `read_at`, recomputing envelope status/reason, never changing storage.
Persisted error/unavailable/insufficient states cannot be promoted by a read.
Available or already-stale values remain stale if either relevant age exceeds TTL;
if read_at precedes measured_at or a required source time, the dynamic envelope
becomes error/clock_regression. A subsequent read with a valid clock can project
from the unchanged stored status again. Static contract facts never claim liveness.
Snapshot existence is distinct from any field's availability; no global healthy flag.
A long owner-configured cycle interval can legitimately leave resource fields stale.

## Data model

Root keys are exactly `model`, `model_version`, `measured_at`, `source_transition_id`,
`source_event_id`, `source_session_id`, `sources`, `capabilities`, `observations`,
`resources`, `last_selected_action`, `prediction_performance`, `memory`, and
`recent_failures`. Model is `self_model_v1`, model_version integer 1. The ten source
keys are catalog, observation, transition, prediction_window, prediction_coverage,
prediction_score, storage, consolidation, runtime, plus errors.
Only fixed catalogs and fields listed here may be serialized; unknown input keys
are ignored during bounded extraction, not recursively copied. Source registry
objects use `table` (nullable for catalog), `ids` (at most 100),
`source_observed_at`, `timestamp_kind`, `ttl_seconds`; prediction_window also has
`oldest_completed_at` and `newest_completed_at`, and catalog has `contract`.
Storage uses table=null and its fixed `tables` list. Event cutoff remains root-level.

IDs are positive signed 64-bit integers; event cutoff may be 0 for no events.
Root measurement time and update time agree exactly. All numbers must be finite;
booleans are not accepted as numbers. All strings are <=128 UTF-8 bytes. Invalid/nonfinite source timestamps are stored
as null in the source registry with the referring envelope marked error; raw invalid
values never escape into output. Count
values are nonnegative integers. SQL scalar count bounds are represented as
`{"count":n,"relation":"exact"}` up to 1000; seeing 1001 IDs returns
`{"count":1001,"relation":"at_least"}` without continuing the scan.
Consolidation's per-run counts are 0..100; failed_count can represent its existing
whole-run failure marker, and no summation infers disjointness. Allowed audit statuses
are running, suppressed, completed, completed_with_errors and failed; allowed
provenances are policy_selected and owner_requested; model must be semantic_v1/1.
Suppression reason is copied only for suppressed status and must be high_load,
low_battery or low_disk. Other statuses expose null suppression_reason. A running
run must have null completed_at; a terminal run requires a finite completion no
earlier than start. Invalid metadata makes the audit envelope error, not success.

Output JSON uses strict finite encoding, ASCII escaping, maximum 32,768 bytes,
maximum depth 12, maximum 512 total object members, and maximum 100 elements in
any array. Reject duplicate keys and nonfinite constants on reads. Enforce shape,
source references, types, status/reason combinations, model version and column/
payload agreement. Size is checked before parsing; a bounded lexical depth pass
precedes JSON decoding. No JSON1 extension is required. Corrupt/unknown snapshots
are errors, not repaired or partially trusted by observer reads.

## Example payloads

Both examples below are complete synthetic **persisted** payloads. They do not
contain real host identity or owner data. Every dynamic envelope uses the same
source-reference convention, so a status can be interpreted without copying clocks
onto each scalar. The second represents a new update with missing/ambiguous sensor
data, an old observation, no scored evaluations, a suppressed consolidation and
an observed retained error. It is not a successful-cycle or capability score.

### Available synthetic evidence

```json
{
  "model": "self_model_v1",
  "model_version": 1,
  "measured_at": 1700000002,
  "source_transition_id": 3,
  "source_event_id": 50,
  "source_session_id": "synthetic-session",
  "sources": {
    "catalog": {
      "table": null,
      "ids": [],
      "source_observed_at": null,
      "timestamp_kind": "producer_contract",
      "ttl_seconds": null,
      "contract": "self_model_v1"
    },
    "observation": {
      "table": "transitions",
      "ids": [
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "state_after.wall_time",
      "ttl_seconds": 60
    },
    "transition": {
      "table": "transitions",
      "ids": [
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "completed_at",
      "ttl_seconds": 60
    },
    "prediction_window": {
      "table": "transitions",
      "ids": [
        1,
        2,
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 300,
      "oldest_completed_at": 1700000000,
      "newest_completed_at": 1700000002
    },
    "prediction_coverage": {
      "table": "transitions",
      "ids": [
        1,
        2,
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "newest_contributing_completion",
      "ttl_seconds": 300
    },
    "prediction_score": {
      "table": "transitions",
      "ids": [
        1,
        2,
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "newest_contributing_completion",
      "ttl_seconds": 300
    },
    "storage": {
      "table": null,
      "ids": [],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 60,
      "tables": [
        "seed_schema",
        "episodes",
        "transitions",
        "world_model_queue",
        "semantic_memories"
      ]
    },
    "consolidation": {
      "table": "consolidation_runs",
      "ids": [
        1
      ],
      "source_observed_at": 1700000001,
      "timestamp_kind": "completed_at",
      "ttl_seconds": 300
    },
    "runtime": {
      "table": "runtime",
      "ids": [
        1
      ],
      "source_observed_at": 1700000000,
      "timestamp_kind": "heartbeat",
      "ttl_seconds": 10
    },
    "errors": {
      "table": "events",
      "ids": [],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 60
    }
  },
  "capabilities": {
    "sensors": {
      "battery_pct": {
        "supported": true,
        "reading": "observations.battery_pct"
      },
      "charging": {
        "supported": true,
        "reading": "observations.charging"
      },
      "load_ratio": {
        "supported": true,
        "reading": "observations.load_ratio"
      },
      "load_5m_ratio": {
        "supported": true,
        "reading": "observations.load_5m_ratio"
      },
      "disk_free_pct": {
        "supported": true,
        "reading": "observations.disk_free_pct"
      },
      "network": {
        "supported": true,
        "reading": "observations.network"
      },
      "hostname": {
        "supported": true,
        "reading": "observations.hostname"
      },
      "machine": {
        "supported": true,
        "reading": "observations.machine"
      },
      "macos": {
        "supported": true,
        "reading": "observations.macos"
      }
    },
    "actions": {
      "observe": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "no_additional_processing"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "reflect": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "bounded_reflection"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "consolidate": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "guarded_semantic_consolidation"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "rest": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "post_cycle_wait"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      }
    },
    "unsupported": {
      "arbitrary_tools": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      },
      "planning": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      },
      "self_modification": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      }
    }
  },
  "observations": {
    "battery_pct": {
      "value": 80,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "charging": {
      "value": true,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "load_ratio": {
      "value": 0.2,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "load_5m_ratio": {
      "value": 0.25,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "disk_free_pct": {
      "value": 70,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "network": {
      "value": false,
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "hostname": {
      "value": "synthetic-host",
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "machine": {
      "value": "synthetic-arch",
      "status": "available",
      "reason": null,
      "source": "observation"
    },
    "macos": {
      "value": "synthetic-os",
      "status": "available",
      "reason": null,
      "source": "observation"
    }
  },
  "resources": {
    "battery_pct": "observations.battery_pct",
    "charging": "observations.charging",
    "load_ratio": "observations.load_ratio",
    "disk_free_pct": "observations.disk_free_pct",
    "network": "observations.network"
  },
  "last_selected_action": {
    "value": "observe",
    "status": "available",
    "reason": null,
    "source": "transition"
  },
  "prediction_performance": {
    "window": {
      "value": {
        "raw_rows": 3,
        "raw_transition_ids": [
          1,
          2,
          3
        ],
        "valid_evaluations": 3,
        "missing_evaluations": 0,
        "unsupported_evaluations": 0,
        "invalid_evaluations": 0
      },
      "status": "available",
      "reason": null,
      "source": "prediction_window"
    },
    "coverage": {
      "value": {
        "samples": 3,
        "mean": 1.0
      },
      "status": "available",
      "reason": null,
      "source": "prediction_coverage"
    },
    "score": {
      "value": {
        "samples": 3,
        "mean_normalized_error": 0.1,
        "accuracy_score": 0.9
      },
      "status": "available",
      "reason": null,
      "source": "prediction_score"
    }
  },
  "memory": {
    "storage": {
      "value": {
        "schema_version": 6,
        "bounded_reads_succeeded": true,
        "page_size": 4096,
        "page_count": 100,
        "logical_allocated_bytes": 409600,
        "episode_count": {
          "count": 3,
          "relation": "exact"
        },
        "transition_count": {
          "count": 3,
          "relation": "exact"
        },
        "world_model_queue_depth": {
          "count": 0,
          "relation": "exact"
        },
        "semantic_memory_count": {
          "count": 2,
          "relation": "exact"
        }
      },
      "status": "available",
      "reason": null,
      "source": "storage"
    },
    "latest_consolidation": {
      "value": {
        "run_id": 1,
        "status": "completed",
        "provenance": "policy_selected",
        "started_at": 1700000001,
        "completed_at": 1700000001,
        "source_beliefs_examined": 2,
        "created_count": 2,
        "revised_count": 0,
        "weakened_count": 0,
        "unchanged_count": 0,
        "failed_count": 0,
        "suppression_reason": null
      },
      "status": "available",
      "reason": null,
      "source": "consolidation"
    },
    "runtime_reported": {
      "value": {
        "heartbeat": 1700000000,
        "last_successful_cycle": 1700000000,
        "session_id": "synthetic-session"
      },
      "status": "available",
      "reason": null,
      "source": "runtime"
    }
  },
  "recent_failures": {
    "value": {
      "count": 0,
      "has_older_retained_errors": false,
      "oldest_event_id": null,
      "newest_event_id": null,
      "latest_valid_event": null,
      "invalid_metadata_count": 0
    },
    "status": "available",
    "reason": null,
    "source": "errors"
  }
}
```

### Degraded and stale synthetic evidence

```json
{
  "model": "self_model_v1",
  "model_version": 1,
  "measured_at": 1700000002,
  "source_transition_id": 3,
  "source_event_id": 50,
  "source_session_id": "synthetic-session",
  "sources": {
    "catalog": {
      "table": null,
      "ids": [],
      "source_observed_at": null,
      "timestamp_kind": "producer_contract",
      "ttl_seconds": null,
      "contract": "self_model_v1"
    },
    "observation": {
      "table": "transitions",
      "ids": [
        3
      ],
      "source_observed_at": 1699999882,
      "timestamp_kind": "state_after.wall_time",
      "ttl_seconds": 60
    },
    "transition": {
      "table": "transitions",
      "ids": [
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "completed_at",
      "ttl_seconds": 60
    },
    "prediction_window": {
      "table": "transitions",
      "ids": [
        1,
        2,
        3
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 300,
      "oldest_completed_at": 1700000000,
      "newest_completed_at": 1700000002
    },
    "prediction_coverage": {
      "table": "transitions",
      "ids": [],
      "source_observed_at": null,
      "timestamp_kind": "newest_contributing_completion",
      "ttl_seconds": 300
    },
    "prediction_score": {
      "table": "transitions",
      "ids": [],
      "source_observed_at": null,
      "timestamp_kind": "newest_contributing_completion",
      "ttl_seconds": 300
    },
    "storage": {
      "table": null,
      "ids": [],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 60,
      "tables": [
        "seed_schema",
        "episodes",
        "transitions",
        "world_model_queue",
        "semantic_memories"
      ]
    },
    "consolidation": {
      "table": "consolidation_runs",
      "ids": [
        1
      ],
      "source_observed_at": 1700000001,
      "timestamp_kind": "completed_at",
      "ttl_seconds": 300
    },
    "runtime": {
      "table": "runtime",
      "ids": [
        1
      ],
      "source_observed_at": 1699999982,
      "timestamp_kind": "heartbeat",
      "ttl_seconds": 10
    },
    "errors": {
      "table": "events",
      "ids": [
        49
      ],
      "source_observed_at": 1700000002,
      "timestamp_kind": "query_snapshot",
      "ttl_seconds": 60
    }
  },
  "capabilities": {
    "sensors": {
      "battery_pct": {
        "supported": true,
        "reading": "observations.battery_pct"
      },
      "charging": {
        "supported": true,
        "reading": "observations.charging"
      },
      "load_ratio": {
        "supported": true,
        "reading": "observations.load_ratio"
      },
      "load_5m_ratio": {
        "supported": true,
        "reading": "observations.load_5m_ratio"
      },
      "disk_free_pct": {
        "supported": true,
        "reading": "observations.disk_free_pct"
      },
      "network": {
        "supported": true,
        "reading": "observations.network"
      },
      "hostname": {
        "supported": true,
        "reading": "observations.hostname"
      },
      "machine": {
        "supported": true,
        "reading": "observations.machine"
      },
      "macos": {
        "supported": true,
        "reading": "observations.macos"
      }
    },
    "actions": {
      "observe": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "no_additional_processing"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "reflect": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "bounded_reflection"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "consolidate": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "guarded_semantic_consolidation"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      },
      "rest": {
        "value": {
          "implemented": true,
          "selectable": true,
          "owner_controlled": true,
          "work_kind": "post_cycle_wait"
        },
        "status": "available",
        "reason": null,
        "source": "catalog"
      }
    },
    "unsupported": {
      "arbitrary_tools": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      },
      "planning": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      },
      "self_modification": {
        "value": false,
        "status": "not_supported",
        "reason": "outside_action_contract",
        "source": "catalog"
      }
    }
  },
  "observations": {
    "battery_pct": {
      "value": null,
      "status": "unavailable",
      "reason": "not_recorded",
      "source": "observation"
    },
    "charging": {
      "value": null,
      "status": "unavailable",
      "reason": "not_recorded",
      "source": "observation"
    },
    "load_ratio": {
      "value": 0.2,
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "load_5m_ratio": {
      "value": 0.25,
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "disk_free_pct": {
      "value": 70,
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "network": {
      "value": false,
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "hostname": {
      "value": "synthetic-host",
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "machine": {
      "value": "synthetic-arch",
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    },
    "macos": {
      "value": "synthetic-os",
      "status": "stale",
      "reason": "source_expired",
      "source": "observation"
    }
  },
  "resources": {
    "battery_pct": "observations.battery_pct",
    "charging": "observations.charging",
    "load_ratio": "observations.load_ratio",
    "disk_free_pct": "observations.disk_free_pct",
    "network": "observations.network"
  },
  "last_selected_action": {
    "value": "observe",
    "status": "available",
    "reason": null,
    "source": "transition"
  },
  "prediction_performance": {
    "window": {
      "value": {
        "raw_rows": 3,
        "raw_transition_ids": [
          1,
          2,
          3
        ],
        "valid_evaluations": 0,
        "missing_evaluations": 3,
        "unsupported_evaluations": 0,
        "invalid_evaluations": 0
      },
      "status": "available",
      "reason": null,
      "source": "prediction_window"
    },
    "coverage": {
      "value": {
        "samples": 0,
        "mean": null
      },
      "status": "insufficient_evidence",
      "reason": "no_supported_evaluations",
      "source": "prediction_coverage"
    },
    "score": {
      "value": {
        "samples": 0,
        "mean_normalized_error": null,
        "accuracy_score": null
      },
      "status": "insufficient_evidence",
      "reason": "no_scored_evaluations",
      "source": "prediction_score"
    }
  },
  "memory": {
    "storage": {
      "value": {
        "schema_version": 6,
        "bounded_reads_succeeded": true,
        "page_size": 4096,
        "page_count": 100,
        "logical_allocated_bytes": 409600,
        "episode_count": {
          "count": 3,
          "relation": "exact"
        },
        "transition_count": {
          "count": 3,
          "relation": "exact"
        },
        "world_model_queue_depth": {
          "count": 0,
          "relation": "exact"
        },
        "semantic_memory_count": {
          "count": 2,
          "relation": "exact"
        }
      },
      "status": "available",
      "reason": null,
      "source": "storage"
    },
    "latest_consolidation": {
      "value": {
        "run_id": 1,
        "status": "suppressed",
        "provenance": "policy_selected",
        "started_at": 1700000001,
        "completed_at": 1700000001,
        "source_beliefs_examined": 0,
        "created_count": 0,
        "revised_count": 0,
        "weakened_count": 0,
        "unchanged_count": 0,
        "failed_count": 0,
        "suppression_reason": "low_disk"
      },
      "status": "available",
      "reason": null,
      "source": "consolidation"
    },
    "runtime_reported": {
      "value": {
        "heartbeat": 1699999982,
        "last_successful_cycle": 1699999982,
        "session_id": "synthetic-session"
      },
      "status": "stale",
      "reason": "source_expired",
      "source": "runtime"
    }
  },
  "recent_failures": {
    "value": {
      "count": 1,
      "has_older_retained_errors": false,
      "oldest_event_id": 49,
      "newest_event_id": 49,
      "latest_valid_event": {
        "id": 49,
        "ts": 1699999992,
        "category": "ERROR",
        "source": "organism"
      },
      "invalid_metadata_count": 0
    },
    "status": "available",
    "reason": null,
    "source": "errors"
  }
}
```

For the first stored example, a read at 1700000063 projects observation/transition,
storage and errors as stale, runtime as stale, and prediction metrics according to
their independent 300-second policies. `measured_at` and all source IDs/times stay
unchanged. A read at 1699999999 reports dynamic clock errors. API envelope examples:
`{"available":false,"status":"unavailable","reason":"legacy_schema","read_at":1700000002,"snapshot":null}`
and `{"available":true,"status":"stored","reason":null,"read_at":1700000002,"snapshot":<projected payload>}`.
The placeholder in the latter explains composition; the fenced JSON above is exact.

## Update trigger and cycle ordering

Exactly one attempt per successful normal autonomous cycle, immediately after
`curiosity_attention.execute(...)`, before the existing delay lookup and final
runtime/idle write. No preceding stage moves:

1. Apply settings and existing wake handling; observe before; choose; predict.
2. Perform selected action; observe after; describe outcome; evaluate original
   prediction; assess curiosity against prior published beliefs.
3. Compute unchanged legacy reward/Q and commit experience/evaluation/curiosity/
   B4 eligibility together.
4. Recover the existing B4 queue; write existing learning/memory telemetry and
   last-state/action metadata; finish optional existing curiosity reflection.
5. **B7 attempt** reads that persisted transition, recent completed evaluations,
   post-recovery queue depth, latest consolidation audit and event cutoff.
6. Existing delay lookup, final runtime/idle telemetry and returned delay.

B7 can observe current action's already-committed consolidation audit and optional
reflection events, but cannot invent an exact transition link for those audits.
A remaining B4 backlog is reported as a count, not “all learned.” Final runtime
last_successful_cycle has not yet been written; B7 explicitly reports the stored
prior value. It never writes a premature successful-cycle assertion itself.

Check stop before acquiring the Memory lock, after acquisition and before commit;
use a nonblocking lock attempt so B7 adds no lock wait. A stop during calculation
aborts/rolls back B7 only; a stop just after commit leaves the snapshot valid and
normal shutdown proceeds. Progress checks also observe stop. No updates on owner
commands, startup, wake, shutdown, API reads or timers. Earlier stage failure means
no B7 attempt. Repeated source ID or lower ID is a no-op; no duplicate event, no
backdating. A later failed attempt is not queued or replayed on restart.

## Persistence and schema proposal

Recommend **schema v6**, adding only this table, with no history or progress table:

```sql
CREATE TABLE self_model_current (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    updated_at REAL NOT NULL CHECK(updated_at >= 0),
    model TEXT NOT NULL CHECK(model = 'self_model_v1'),
    model_version INTEGER NOT NULL CHECK(model_version = 1),
    source_transition_id INTEGER NOT NULL REFERENCES transitions(id)
        CHECK(source_transition_id > 0),
    data_json TEXT NOT NULL
        CHECK(length(CAST(data_json AS BLOB)) <= 32768)
);
```

Types, finite timestamps, signed ID range, bounded strict JSON and column/payload
agreement are additionally validated in application code; SQLite affinity and SQL
CHECKs alone do not establish that contract. No extra index is needed: singleton
and transition primary keys cover all lookups. Source event ID is JSON provenance,
not a foreign key, because existing event retention can remove that row. The
transition FK has no cascade; B7 never deletes a source row.

Under the acquired Memory lock, require `db.in_transaction == False`. Save its
existing busy_timeout, set busy_timeout=0 for this optional work, install the
bounded progress handler, and BEGIN IMMEDIATE. If another writer owns the DB,
skip publication as failure without waiting. Within this transaction read prior
source ID and evidence, build/validate JSON, upsert singleton, append bounded
SELF_MODEL event, and commit. The snapshot and success event either both exist or
neither does. Cutoffs are from this consistent transaction and exclude B7's own
summary. Do not call helper methods that independently commit or scan histories.
Always remove the owned progress handler and restore busy_timeout in finally;
existing core code has no competing progress handler. Never roll back a transaction
that B7 did not start. Restoration/rollback failures indicate unusable storage and
must be surfaced as diagnostics, not reported as a successful B7 update.

## Migration and compatibility

Proposed `VERSION=6`, explicit supported set 1..6, and `V6_STATEMENTS` containing
the table above. Change the existing v4→v5 step to set version=5 and local version=5
explicitly; then execute v5→v6 and write 6. Otherwise changing only VERSION would
skip v6 for earlier fixtures. Preserve previous table definitions and row meanings.

Fresh storage applies the complete additive ladder and leaves the singleton empty.
Unversioned and v1–v5 existing stores follow the existing Memory backup-before-write
policy and one transactional migration ladder. Failed backup prevents upgrading;
failed v6 SQL rolls back all migration steps to the original version. Constructor
base-schema setup retains its current documented boundary; this is not a claim that
all constructor work belongs to the migration transaction. Low-level migrate still
is not a substitute for the filesystem backup entry point.

Reopening v6 does not back up again, publish a snapshot or rewrite historical data.
Future, missing/duplicate/malformed version rows are refused before constructor
schema writes, preserving the existing fail-closed policy. A declared-v6 store
missing the new table is structural damage; observer reports error and core B7
publication fails visibly, with no opportunistic repair. Do not synthesize a row
from old transitions during upgrade or restart. Before the first successful new
cycle, inspection is unavailable/awaiting_first_cycle.

Operator startup's existing required-table set must add self_model_current and
continue checking the supported VERSION. Observer v0–v5 reads remain unavailable
without migration. Code rollback after a deployed v6 upgrade is not schema downgrade:
use a separately owner-authorized backup recovery, preserving the newer DB. No
installation or recovery operation is part of this design task.

## Failure and restart semantics

| Condition | Required result |
| --- | --- |
| Missing/null sensor or absent evaluation | Publish explicit unavailable/insufficient measurement; no zero substitute |
| Malformed historical evaluation inside raw100 | Count invalid row; consume its slot; derive only valid remainder with partial_window reason |
| Malformed current state JSON | Publish observation errors and null values while retaining valid independent facts; never reuse prior resource values as fresh |
| Invalid current transition ID/action timing or missing row | Reject attempt; previous snapshot remains; no fabricated committed source |
| Malformed runtime/latest audit | Affected envelope error; other independently valid fields can publish |
| Oversized model / SQL read or write / telemetry insert / commit failure | Roll back owned transaction, preserve previous snapshot and all upstream commits; diagnostic failure only |
| Owner stop or busy Memory lock | Skip quietly; no new event; previous snapshot ages normally |
| Process interruption before commit | SQLite atomicity retains previous row; no success event from aborted publication |
| Crash after commit | New row and event survive; restart only reads it and ages it |
| Existing row corrupt | Observer error; next higher source ID can replace it with a newly validated snapshot, with no history repair |

Catch ordinary `Exception` at the B7 boundary after cleanup; do not swallow
KeyboardInterrupt/SystemExit. Failure telemetry is one best-effort small SELF_MODEL
`status=failed` event in a separate nonblocking transaction after rollback, with
fixed reason codes and no raw exception/message/record data. The attempt uses at
most 2,000 VM instructions in addition to the normal budget, never recursively
logs a logging failure and never retries. On storage failure that also prevents
this event, emit one fixed bounded message through the existing `seed` logger.
No durable failure record can be guaranteed on an unwritable database. API age and
source cutoff therefore remain the authoritative indication that the snapshot
has not advanced. B7 does not alter runtime.last_error, owner commands or reward.
An unrelated final runtime write can still fail under the core's existing rules;
B7 failure isolation is not a guarantee that a broken database lets the core run.

Restart constructs no self-model evidence, performs no sensing for B7, resets no
B7 timestamp and retries no old transition. The next normal completed cycle can
replace the current row. No missing optional update is retrospectively backfilled.

## Resource bounds

Limits are fixed model constants, not user-controlled query arguments. These bound
rows, returned bytes, VM work and object processing; they do **not** guarantee an
absolute wall-clock deadline for OS I/O or SQLite commit/fsync.

| Query | Bounded operation / result |
| --- | --- |
| Q1 | Prior singleton source_transition_id, one row; no prior JSON load |
| Q2 | seed_schema version LIMIT 2; exactly one supported version required |
| Q3 | Current transition primary-key lookup: ID, bounded action, start/completion and bounded state_after blob; one row |
| Q4 | `transitions WHERE id<=? ORDER BY id DESC LIMIT 100`: ID, start/completion, bounded evaluation blob only |
| Q5 | `events WHERE category='ERROR' AND id<=? ORDER BY id DESC LIMIT 101` using events_category_id; ID, ts, bounded source; keep 100 plus lookahead |
| Q6 | `SELECT id FROM events ORDER BY id DESC LIMIT 1`; root cutoff, zero if empty |
| Q7–Q10 | Four fixed PK-ordered LIMIT 1001 scans: episodes.id, transitions.id, world_model_queue.transition_id, semantic_memories.id; saturating counts, no COUNT(*) |
| Q11 | `consolidation_runs ORDER BY id DESC LIMIT 1`; fixed scalar columns and bounded result_json only for suppression reason |
| Q12 | runtime WHERE singleton=1; bounded data_json, one row |
| Q13–Q14 | PRAGMA page_size and page_count; scalar logical allocation facts |

At most **14 evidence SELECT/PRAGMA reads** and **one busy_timeout read** per attempt;
BEGIN/COMMIT/ROLLBACK, temporary timeout assignments, two publication writes and at most one existing
event-retention DELETE are separate control/write statements, not hidden evidence queries. Q6 precedes
Q5. Queries execute within the same B7 transaction. Combined rows returned <=4,214
(4,004 count IDs + 100 evaluations + 101 errors + at most 9 other rows).

Each source JSON is returned with
`substr(CAST(column AS BLOB),1,16385)`; more than 16,384 bytes is invalid, and truncated
JSON is never parsed. This bounds bytes crossing into Python, not all SQLite disk
page activity on a damaged database. Same bounded-prefix rule applies to action,
source, audit status/model/provenance strings with limit129 and accepted max128.
No error messages or event data_json are read. A full audit result is never copied;
if its blob is oversized, the independent audit counters/status remain readable
but suppression reason is null and the audit envelope is error/oversized_source.
Maximum JSON returned to builder is 102 × 16,385 bytes (100 evaluations + current
state + runtime), plus one audit blob of 16,385 bytes; total <1.7 MiB. No huge raw
history, SQL offset or filesystem scan is permitted.

Register a progress callback each 1,000 SQLite VM operations; abort at 100 callbacks
(100,000 operations), or on stop. It covers evidence reads and publication writes;
rollback and connection restoration run with the handler removed. Failure-event
budget is separately 2,000 operations, no evidence reads. A missing index or damaged
schema cannot turn a capped return set into an unbounded completed scan. Validate
inputs using the byte/depth/member caps before traversing fixed fields. Processing
cost is O(100 × source-byte-cap + 4 × 1001 + 100), plus capped SQLite index work;
source history size does not increase the number of sampled rows. Connection/lock
settings must be restored even after interruption. No integrity_check, checkpoint, vacuum, backup, new pruning policy or expensive
filesystem inventory is added per update. The existing emit helper can perform its
ordinary event-retention DELETE; that statement is inside the same VM budget and
transaction, so interruption rolls it back with the B7 publication.

Output row <=32 KiB; summary data_json <=1 KiB; API body <=40 KiB. Serialization
failure rejects publication rather than silently dropping required fields. Storage
for snapshots stays one row. Events use the existing log, whose retention behavior
is addressed below; original experiences/models remain untouched. Actual cycle
work time increases by bounded local work; the configured/returned delay and the
existing interruptible wait behavior are unchanged.

## Telemetry

Success category **SELF_MODEL**, source **self_model**, fixed message
`Self model snapshot updated`. Exact data keys:
`model`, `model_version`, `source_transition_id`, `status` (updated),
`field_status_counts` (all six status keys, counts of measurement envelopes only),
`prediction_sample_count` (score denominator), `recent_failure_count` (sample count),
`source_event_id`. Do not count static alias members or every nested scalar as fields.
Data encodes to <=1,024 bytes. It is a summary, not a full snapshot.

Failure event uses the same model/version/source transition, status=failed and
`reason` in calculation_failed, invalid_source, invalid_schema, storage_failed,
resource_limit, invalid_snapshot. It has no invented counts. Source ID and category
are not a psychological interpretation. No event on duplicate, lower ID or stop.

Reuse the existing low-level `seed.telemetry.emit` unchanged inside the owned
transaction. Its existing every-100th-ID retention DELETE is included in the VM
budget and rolls back with a failed publication. B7 must neither disable that
cadence (which could accidentally prevent future cleanup when IDs align) nor add
a new cleanup policy. Source error records sampled just before the summary can
subsequently expire; their bounded metadata remains in the snapshot. Event history
is not permanent. Original episodes, transitions, beliefs, concepts and semantic
records are never deleted by B7. No telemetry helper modification is required.

## Read-only inspection API

Propose `GET /api/self-model`, no parameters or body, in the observer router.
`SelfModelReadService(ReadStore, clock)` uses the existing checked-path mode=ro
connection, a read transaction, scoped progress budget <=100,000 instructions and
busy_timeout=0. Do not call SeedService.status, ProcessController, Memory,
SeedOrganism, migration, sensing, filesystem inventory, network or mutation services.
At most four evidence reads: fixed-name schema-table existence query LIMIT 2,
seed_schema LIMIT 2, one bounded singleton read, and exact source transition
ID existence check. Fixed-name schema discovery is VM-capped; no full table inventory.
Retrieve data_json with 32,769-byte prefix, validate before parsing/projection.
ReadStore's existing connection setup is separate from this evidence-read budget.

| Storage case | HTTP and response |
| --- | --- |
| Valid v6 row | 200, available=true/status=stored/reason=null/read_at/snapshot projected at read_at |
| Unversioned or v1–v5 | 200, available=false/status=unavailable/reason=legacy_schema/snapshot=null |
| Valid v6, no row | 200, available=false/status=unavailable/reason=awaiting_first_cycle/snapshot=null |
| v6 missing table, corrupt/oversized/inconsistent row or missing source transition | 200, available=false/status=error/reason=invalid_snapshot/snapshot=null |
| Unsupported future or ambiguous/malformed version | 409 existing ServiceError envelope, incompatible_schema; never parse model |
| Missing DB, unsafe path, inaccessible/busy/damaged DB | Existing sanitized 503 ServiceError; no home creation |
| Any query parameter | 422 invalid_query; no arbitrary window/time/model controls |

The three 200 unavailable/error shapes also include read_at. `available=true`
means a valid stored snapshot exists, never that every field is current or the
process is alive. A read returns historical IDs/clocks and fresh status projection,
without recomputation from newer evidence. No cache is needed. Response <=40 KiB;
reject oversized representation. No frontend view or new listener is created.

## Security and owner-control boundaries

Reuse existing loopback binding, Host/Origin checks, observer/operator separation,
request limits, fixed paths and error sanitization. The endpoint requires no new
permission and grants no mutations. Operator schema refusal remains fail-closed.
Do not traverse paths from payloads or render stored strings as HTML. Error summaries
exclude raw messages, stack traces, commands and event payloads. Hostname/platform
observations stay in the existing local inspection boundary, never exported by B7.
Source names and versioned catalogs are data, never instructions or executable tools.
Owner stop wins over optional B7 work; owner settings and command dispatch remain
unchanged. No private installed data is required for acceptance fixtures.

## B8 isolation

There must be no reads of self_model_current or B7 objects from Learner.choose,
Learner.reward, Learner.update, Predictor.predict, evaluate_prediction,
assess_curiosity, WorldModel, Consolidator, curiosity attention or owner command
handlers. The only organism reference is construction of a side-effect-free
adapter and the post-commit update call. No B7 values enter state_before/state_after,
reward, Q rows, epsilon/alpha, action candidates, prediction/error payloads,
curiosity components/eligibility, world/semantic evidence or interval calculations.

Plan deterministic paired runs for all four actions and curiosity enabled/disabled:
identical database evidence/settings/random draws/observations/clocks, with absent,
contradictory, stale, corrupt and valid pre-existing B7 snapshots, plus a no-op B7
control. Assert identical action, complete decision provenance, legacy reward,
Q value/visits, epsilon, alpha, prediction, prediction error, curiosity assessment/
claim/outcome, world belief/pending/processed results, semantic changes/history/run
counters, concepts, owner command outcomes and returned delay. Normal perception
count stays two; network probe count stays two only when exercising the existing
mocked Body probe path, with zero real networking. B7-only calls forbid sensing,
sockets, DNS and subprocesses. Freeze clocks for comparison; operational event IDs,
B7 events and additive storage footprint are expected differences, never policy
outputs. Also test multiple cycles so a snapshot cannot affect the next decision.
B9 frontend and B10 comparative improvement experiments remain absent.

## Deterministic scenario

Proposed `tests/self_model_scenario.py` uses fixed synthetic clocks, sensor data,
actions and temporary resolved homes; CLI emits sorted strict JSON. It does not
open installed storage, invoke OS sensors or create a listener. Compact stages:

1. Fresh v6 has no snapshot: observer unavailable/awaiting_first_cycle. A direct
   builder fixture with a committed NULL evaluation yields insufficient score;
   production automatic trigger remains the normal cycle only.
2. Three completed real B3 evaluations from fixed before/after inputs (full,
   partial, unavailable, as in the B3 fixture) produce valid_evaluations=3,
   scored=2, mean coverage=5/12, mean error=.06, accuracy=.94. Verify literals.
3. Current row includes all nine valid observation fields; report available and
   exact source row/wall_time, with known page/count facts from that fixture.
4. Advance read clock 61 seconds without writing: observation becomes stale;
   source ID/value/time and database bytes remain unchanged. Advance 301 seconds
   to demonstrate prediction staleness separately.
5. Persist one synthetic ERROR with fixed source/time; next completed cycle's
   snapshot includes count1/latest event. A later-than-cutoff injected error is
   excluded until a new snapshot; no claim about unrecorded failures.
6. Close/reopen: identical stored payload and cutoff, older freshness projection,
   zero startup B7 events/updates. Next cycle advances singleton exactly once.
7. Separate suppressed-consolidation fixture shows selectable=true alongside
   audit status=suppressed/zero work, with no invented transition attribution.
8. Paired control returns equality for the B8 isolation outputs above. Include a
   forced B7 write failure preserving prior singleton and the completed transition.

Stable artifact `docs/baselines/seed-0.2-b7-comparison.json` will record exact
approved implementation base, model/schema versions, fixtures, literal expected
metrics, preservation hashes and policy equality. Omit platform-dependent physical
DB size from equality comparisons; check logical page arithmetic within each run.
This artifact is not created by the present documentation task. No trend,
intelligence, self-awareness or developmental-improvement conclusion is emitted.

## Test strategy

All entries are **planned tests, not implemented or passed B7 acceptance**.
Use repository pytest patterns, temporary homes and injected clocks; no new test
framework, dependencies or real OS/network calls. Tests target observable contracts
and failure boundaries rather than mirror implementation details.

| File / test group | Concrete acceptance cases |
| --- | --- |
| `tests/test_self_model_migrations.py` | Fresh, populated v5 and unversioned/v1–v4 ladder; exact prior-row preservation including sqlite_sequence; one pre-upgrade backup; backup failure; injected final-step rollback for each prior version; reopen no-op; no invented singleton/backfill; future/duplicate/malformed version refusal before writes; v4 step does not skip v6; FK/check/size constraints |
| `tests/test_self_model.py` computation | Nine valid observations; missing battery; charging null vs false; network false vs missing; missing/old/invalid state timestamp; malformed state; unsupported capability never becomes available; finite extreme load values; nonfinite/boolean-as-number/oversized strings rejected; complete fixed catalog |
| Same file, retrospective metrics | Hand-calculated full/partial/unavailable B3 metrics; missing/unknown versions; malformed/oversized/deep/duplicate-key evaluation; invalid aggregate arithmetic; denominator zero vs absent; no future ID/time leakage; mixed invalid rows counted without backfill; exactly 100 raw rows selected before filtering |
| Same file, memory/errors | Exact vs at_least counts at 999/1000/1001/1002; four bounded tables; logical page arithmetic; absent/completed/running/suppressed/failed audit; no false transition link; oversized result JSON; runtime absent/missing heartbeat/null last success; latest100 retained ERROR sample with lookahead; empty sample; corrupt timestamp/source; old errors and out-of-cutoff rows |
| Same file, freshness | TTL boundary/equality; independent observation/coverage/score/storage/runtime/audit/error clocks; clock rollback at build/read; missing timestamp never replaced; read projection never mutates persisted status; no accidental liveness claim |
| Same file, bounds/atomicity | SQL trace and progress abort; >100 evaluations/errors, >1000 counts; invalid rows consume slots; large source blobs capped in SQL; byte/depth/member/array limits; 32KiB payload and 1KiB summary; one-row upsert; snapshot/event trigger failures roll back both; failed BEGIN does not roll back another transaction; duplicate/lower ID no-op; timeout/handler/lock restored |
| `tests/test_self_model_cycle.py` | Exact post-attention/pre-runtime ordering; one attempt per normal successful cycle; no owner/start/wake/shutdown/read trigger; current after-state from committed row despite changed meta; previous-cycle runtime label; two perceptions; no extra probes; all-action and multi-cycle presence/absence/adversarial snapshot isolation; failure doesn't deliberately fail cycle; stop before/during/after commit; no retries on restart |
| `tests/dashboard/test_self_model.py` | All response cases/statuses; strict bounded parse; provenance/TTL projection at fixed clock; legacy v5 no migration; no Memory/process/sensor calls; readonly SQL authorizer and before/after dumps; missing home remains absent; fixed query budget; query rejection; Host/Origin/operator/security regressions unchanged; operator missing-v6-table refusal |
| `tests/test_self_model_scenario.py` | Literal stage assertions and independent subprocess CLI; stable strict JSON; synthetic-only I/O; saved comparison matches; no platform-dependent footprint equality |
| Existing telemetry/migration/cycle tests | Existing retention behavior unchanged; every-100th boundary and VM-budget rollback coverage; current-schema expectations advance only after implementation; strict event-order expectations add one downstream summary without weakening upstream invariants |

Future implementation gates: targeted regressions; full suite without exclusions;
all six standalone scenarios (the five existing plus B7); historical hashes; scoped
diff/compile checks; existing Linux 3.11/3.13 and macOS 3.13 CI. No expected B7 test
count is invented. Current 542 baseline and two warnings remain separate evidence.

## Documentation changes

This design phase changes exactly this file, the development tracker and the
implementation-log index. README, architecture, verification guide, baselines and
all code/tests remain unchanged. Current tracker text supersedes historical pending
CI statements without rewriting historical batch records or counts.
After separate implementation authorization, README/architecture will describe
actual v6 behavior, inspection and failure boundaries; tracker/log will record
actual tests and limitations. Source/CI verification still does not imply deployment.

## Risks and mitigations

| Risk / practical limit | Mitigation and acceptance evidence |
| --- | --- |
| Stored snapshot mistaken for live capability | Per-field source clocks, immutable measurement time, read projection, no live-process assertion; TTL tests |
| Latest consolidation misattributed to a selected action | Independent run ID/provenance, no synthesized transition link; suppressed action fixture |
| Optional work adds cycle execution time or DB contention | Fixed reads/bytes/VM caps, zero busy wait, nonblocking lock; unchanged returned intervals; no hard fsync latency claim |
| Database cannot record its own failure | Retain old snapshot, best-effort one failure event then bounded logger fallback; observable stale cutoff; failure injection |
| Malformed imports consume bounded evidence window | Visible exclusion counts, no older-row refill and no false zero; corruption/bounds tests |
| Event pruning means provenance event IDs later disappear | ID remains a historical cutoff, not FK or permanent event-retention promise; snapshot contains necessary metadata |
| Snapshot overwrite loses history | Intentional B7 tradeoff; immutable source records and bounded events remain; no B10 history ledger |
| Low-disk legacy reward favors suppressed consolidation | Existing OPEN follow-up remains B8/separate scope; B7 reports suppression without changing reward |
| Timestamp changes and long configured intervals | Explicit clock errors and stale fields; do not silently relax thresholds or modify schedule |
| Memory connection setting cleanup fails | Diagnose unusable connection; do not claim success or mask later existing storage failures; cleanup tests |

No unresolved architecture choice blocks owner review. Runtime cost, SQL query
plans, rollback behavior and cross-platform portability remain implementation
verification risks; this design does not claim they have already passed B7 tests.

## Acceptance criteria

Implementation is acceptable only when all of the following are demonstrated:

- A1: Every catalog field has the source, units, availability and independent
  freshness behavior above; computation and freshness test groups cover it.
- A2: v6 singleton + summary atomic publication, upgrade/backup preservation,
  pre-first-cycle absence and restart continuity pass migration/atomicity tests.
- A3: Malformed, missing, future, stale and insufficient evidence cannot become
  ordinary measurements; exact B3 denominators and exclusion counts pass literal tests.
- A4: Every query, source/output byte size and VM budget is exercised at and beyond
  its cap; no hidden lifetime count, new sensing or external work occurs.
- A5: Cycle-order, failure, duplicate, stop and multi-cycle isolation tests prove
  no changes to B0–B6 decision/learning outputs or owner command behavior.
- A6: Read-only API validates schema/provenance and projects age without writes,
  migration, process probes, frontend changes or security regression.
- A7: Deterministic scenario and all prior scenarios pass; prior baseline artifacts
  remain byte-identical; full supported-platform CI passes without skipped tests.
- A8: Actual implementation files/tests/limitations and source-vs-installed state
  are documented, and owner review occurs before any later batch or deployment.

This document satisfies the design deliverable, not A1–A8 implementation verification.

## Open questions resolved

- Architecture: singleton snapshot, no revision ledger or derived-on-request engine.
- Timing: after optional attention, before final runtime; report prior stored cycle
  success explicitly instead of moving that runtime write or fabricating current success.
- Evidence: current transition's persisted after-state, not meta.last_state or a new
  perception; bounded retrospective evaluations, no rescoring or model retraining.
- Counts: exact through 1000 then truthful lower bound, not unbounded COUNT queries.
- Freshness: fixed per-source TTLs, null/clock errors explicit; no live ownership claim.
- Failures: isolated optional transaction, prior snapshot retained, no replay queue.
- Schema: additive v6 and one current table; no historical rewrite or backfill.
- Telemetry: atomic small event using unchanged helper and existing retention inside the VM budget.
- Scope: inspection API only; no B8 inputs, B9 view or B10 improvement claim.
- Owner decision remaining: approve this contract and separately authorize its
  implementation. No additional requirement has been left implicit for coding.

### Written self-review — 2026-09-24

| Required check | Review result / ambiguity resolved |
| --- | --- |
| 1. Evidence traceability | PASS: complete catalog and Q1–Q14 mapping; action execution vs substantive work separated; no invented run-to-transition join |
| 2. Freshness | PASS: separate clocks/TTLs; state wall_time not replaced by completed_at; prior runtime success labeled; projection never rewrites persisted time |
| 3. No anthropomorphism | PASS: structured measurements only; engineering score meanings and unsupported capabilities explicit |
| 4. Bounded work | PASS as design: row caps alone insufficient for corrupt stores, so byte prefixes and VM caps added; exact counts saturate |
| 5. Persistence | PASS as design: singleton/event atomicity, duplicate trigger handling, empty-before-first-cycle and no startup replay specified |
| 6. Migration | PASS as design: v4 intermediate-version hazard explicitly resolved; fresh/legacy/v5/future/rollback/backup cases mapped |
| 7. No B8 leakage | PASS: no upstream consumers; adversarial snapshot and no-op controls test every required output over multiple cycles |
| 8. No B9 leakage | PASS: observer endpoint only; no frontend file in implementation map |
| 9. No B10 leakage | PASS: retrospective scores have explicit denominators, no trends/improvement claims or revision ledger |
| 10. Failure semantics | PASS as design: invalid rows counted; prior snapshot preserved; unwritable-storage telemetry limitation acknowledged; no fake healthy status |
| 11. Testing | PASS as plan: A1–A8 map to named deterministic files/groups; no B7 test implementation or pass claim |
| 12. Historical integrity | PASS: seven baseline artifacts and runtime tree unchanged; historical counts preserved; only three authorized docs edited |

## Implementation file map

This map is a proposal only, not permission to edit these files now.

| File | Necessary future responsibility |
| --- | --- |
| `seed/self_model.py` (new) | Fixed catalog/bounds, evidence reader, pure builder/validator/projection, owned optional transaction and failure boundary |
| `seed/migrations.py` | Additive v6 table and explicit v5 intermediate step; preserve previous definitions |
| `seed/organism.py` | Construct inert adapter; single downstream update call; no policy changes |
| `seed/telemetry.py` | **No planned edit**: reuse low-level emit within owned transaction and VM budget; no new log framework |
| `seed/memory.py` | **No planned edit**: existing DB/RLock and version-driven backup policy suffice; no new committing stats helper |
| `dashboard/services/self_model.py` (new) | Bounded readonly current snapshot, strict schema check and freshness projection |
| `dashboard/services/seed_service.py` | Small delegation only; do not reuse lifetime-count/host-status helpers |
| `dashboard/api/observer.py` | One parameter-free GET route and query rejection |
| `dashboard/app.py` | Add current table to existing operator required-schema guard |
| `dashboard/services/read_store.py` | **No planned edit**: reuse checked readonly connection; scope endpoint-specific budgets in new service |
| The six new test/scenario files named in Test strategy | Computation, migrations, cycle, dashboard, fixture and CLI acceptance (six files total) |
| Existing migration/current-schema/strict-event tests | Minimal expected version/event updates and telemetry boundary coverage; no weakened assertions |
| `docs/baselines/seed-0.2-b7-comparison.json` | New synthetic comparison; all seven earlier artifacts remain unchanged |
| `README.md`, `docs/architecture.md`, `docs/implementation-log.md`, `docs/seed-0.2-development-plan.md` | Document verified implemented contract and actual evidence only after separate authorization |

No dependencies, frontend assets, deployment scripts, learner/predictor/evaluator,
world/semantic algorithms, commands, settings or sensor implementations need edits.
