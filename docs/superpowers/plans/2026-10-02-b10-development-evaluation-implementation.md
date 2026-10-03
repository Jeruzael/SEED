# B10 Development Evaluation & Experimental Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement I01–I30 task-by-task after separate owner approval and explicit implementation authorization. I31 is later scientific evaluation execution, requiring its own owner authorization after verified engineering closure. Native execution is the previously selected method. Steps use checkbox (`- [ ]`) tracking. This document authorizes no execution.

**Goal:** Plan a trustworthy external evaluator of existing B1–B8 behavior, with isolated deterministic workers, preregistered evidence and an observer-only Astra view.

**Architecture:** A checked-in development coordinator owns scenarios, hidden truth, AnalysisPlans, scoring journals and artifacts. Disposable workers invoke existing SEED mechanisms through evaluation-local adapters; dependencies point from evaluation to SEED. A dedicated bounded artifact reader serves Astra without importing execution/scoring machinery or recomputing cognition.

**Tech Stack:** Existing Python 3.11/3.13, standard library, SQLite, FastAPI, pytest and vanilla browser ES modules; existing locked dependencies only.

**Spec:** [Owner-approved B10 specification](../specs/2026-10-02-b10-development-evaluation-design.md), complete technical design approved at `6cd7504b96dec158bbedbadec4f133150f0e80b9`. The merged specification is authoritative, now amended only for storage safety by the owner-selected Option B in the [2026-10-03 amendment](../specs/2026-10-03-b10-foundation-storage-safety-amendment.md). Original technical plan approval is `ef82df33771661a27c6ced6db65e3aaeb4e5fba5`; unrelated scientific content/limits remain unchanged. Current authority is amendment documentation/publication only, not repair execution.

**Status — 2026-10-02:** **B10 IMPLEMENTATION PLAN OWNER APPROVED / COMPLETE / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL. B10 IMPLEMENTATION NOT STARTED / NOT AUTHORIZED. B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED. NO B10 EXPERIMENTS EXECUTED.** B10 overall IN PROGRESS; design OWNER APPROVED / COMPLETE / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL. The owner explicitly approved the complete revised technical plan at `ef82df33771661a27c6ced6db65e3aaeb4e5fba5`; Plan publication was independently reviewed with no findings and merged via [PR #17](https://github.com/Jeruzael/SEED/pull/17) at `6dcd36c041af75637743bcb35d7c73eaab068b57`; exact master push [run 37018411597](https://github.com/Jeruzael/SEED/actions/runs/37018411597) passed all three required jobs. Canonical tracker/log record the distinct approval, PR-CI and master-CI evidence; closure documentation has its own publication verification gates. Approval does not authorize I01–I30 or I31.

**Current status — 2026-10-03:** B10 engineering IN PROGRESS; I01–I08 **IMPLEMENTED CHECKPOINT / NOT VERIFIED** at stopped foundation `df0569a99f192a576fa2d60d0c2050500403fbc9` (reviewed engineering head `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3`, 0 BLOCKER / 9 MAJOR / 1 MINOR). Storage amendment **OWNER APPROVED / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL**. R1 **DESIGN CONTRACT AMENDMENT APPROVED — IMPLEMENTATION FIX STILL REQUIRED**; R1–R10 all **UNRESOLVED / REMEDIATION REQUIRED**. **G1 NOT VERIFIED; G2 NOT VERIFIED**. Current task edits documentation only on a separate branch from canonical master `196631baef225fa02983f40ffca22cc26190757d`; no remediation, foundation PR, I09+ code, empirical execution or installed-home access. Earlier dated status records are historical.

## Global Constraints

- Current authority: **B10 FOUNDATION STORAGE-SAFETY DESIGN AMENDMENT ONLY**, on `docs/b10-foundation-storage-safety-amendment` from master `196631baef225fa02983f40ffca22cc26190757d`. Five authorized documentation files only; independent amendment review, exact PR CI, normal merge, exact post-merge master CI, closure record, then STOP. Do not edit source/tests/workflows/dependencies/schema, add a native VFS, repair R1–R10, integrate/rewrite the stopped foundation branch, open a foundation PR, implement I09+, execute experiments, deploy or access installed SEED. Later foundation remediation needs separate owner authorization.
- Phases A–O / I01–I30 are engineering implementation. Phase P / I31 is scientific evaluation execution, not implementation development. After I30 merges and exact post-merge master CI and engineering closure succeed, STOP. Only a later explicit **B10 EMPIRICAL EVALUATION EXECUTION** instruction permits creation of the empirical branch, final empirical AnalysisPlan freeze, A–D suite dispatch or empirical conclusions. Implementation authorization never automatically advances to I31.
- Preserve every LOCKED invariant and approved PROVISIONAL contract. No B11–B16 behavior. No tuning predictor/Q/curiosity/world/semantic/self/decision behavior to improve an unfavorable B10 result.
- `development/evaluation → seed/**`; never the reverse. Ordinary SEED and other dashboard views operate with evaluation absent. No evaluator table, migration, plan/report/truth/finding ingestion or evaluator reward/Q input.
- LEARNER_STATE_ROOT and EVALUATION_ROOT are disjoint. Workers receive only assigned disposable state and closed observation/ACK capabilities. No inherited installed `SEED_HOME`, host sensors, network, shell/tool actions, arbitrary paths/imports/code or artifact execution. Ordinary application-managed files retain descriptor-relative/no-follow/identity protection. SQLite requires pre-connect capability/path admission, immediate post-connect identity/path-fact revalidation, bounded ongoing/transaction-boundary and pre-backup/publication checks, terminal detected mismatches and one assigned trusted writer per DB. Only adversarial concurrent same-UID mutation during native SQLite opens is excluded; no native VFS is adopted for B10 v1.
- Frozen protocol is `FROZEN_SELECTION_ASSAY`, with complete unprojected table and DB-byte equality; no mutable constructors/recovery/publication or reflect/consolidate internal effects. Online protocol uses actual `SeedOrganism.cycle()`, not duplicated cognition.
- Prediction → outcome → minimal durable external checkpoint → constant `SCORE_ACK` → current learning. Aggregation/baselines/final digests/indexes/UI never gate ACK. No retry, rollback or double-learning after ambiguous or acknowledged updates.
- AnalysisPlan freezes durably before any dispatch, including training. Its complete body/version/digest, inventory, windows, seeds, thresholds, exclusions and finding rules are immutable. Revisions need new identity/digest, explanation and fresh execution.
- Execution PLANNED/RUNNING/COMPLETED/INCOMPLETE/FAILED/INVALID, measurements MEASURED/UNAVAILABLE/NOT_EVALUATED and question findings POSITIVE/MIXED/NEGATIVE/INCONCLUSIVE/NOT_EVALUATED are independent. No overall scientific PASS or intelligence grade.
- Default seeds 0–4; 30 registered runs. All 33 metric IDs are accounted for per member, with adaptation-delay version 2 and other metrics version 1. Missing evidence is null with reason, never fabricated zero; descriptive-only findings remain NOT_EVALUATED.
- Same-profile canonical science is reproducible; unconditional cross-platform exact equality, hostile same-UID sandboxing, signed authenticity and inferential statistics remain deferred. Scientific and whole-byte integrity digests are distinct.
- All resource ceilings in section 8 below are binding; specs may lower but never raise them. Essential evidence is lossless or the run is explicitly incomplete. No silent metric pruning, forced exposure, seed replacement or repeat-until-positive execution.

## Review Focus

1. Constructor/default-bound clock references and host Body fallback: install adapters before producer import/construction; poison live calls and characterize normal-cycle parity (I04/I10/I13).
2. A crash/fsync failure around ACK or a swallowed post-ACK producer exception: retain exact completed/unconfirmed updates, terminate without retry and never invent a completed transition (I09/I12/I13).
3. SQLite transaction context exits/commits bypassing size monitoring or read-only protection: intercept every owned writer commit path and deny frozen writes including operational tables (I06/I11).
4. Duplicate ordinals across phases/C subcases and large signed 64 IDs: tuple-key journals/replay/cursors, exact string transport and no event conflation (I08/I21/I24/I26/I27).
5. Valid chunk with a replaced receipt/index/path, or incompatible populations with equal plan digest: descriptor identity, scoped integrity states and complete scientific compatibility checks (I23/I24/I25/I26).

## 1. Verified baseline and authority

Planning started on clean **master**, HEAD `2b4d9c76323dcafc4a6e99b3b6f7227ead19703a`, then created only `seed-0.2-b10-implementation-plan` from that exact commit. Authenticated GitHub independently confirmed master and [run 36990393150](https://github.com/Jeruzael/SEED/actions/runs/36990393150), push event at the same SHA: `test (linux-py311)`, `test (linux-py313)`, `test (macos-py313)` all completed/success. This is baseline evidence, not new planning tests or empirical evaluation.

Revision started on clean `seed-0.2-b10-implementation-plan`, HEAD `bec6fd913f7d397ef92eb548ee9317d09ea6ea24`, whose parent is the exact planning base above. The branch diff from that base contains only this plan, tracker and implementation log. Approved specification and protected roadmap/baselines match the base; no implementation/evaluation branches, evaluation source/tests or experiment workspace exist. The current revision changes only engineering/empirical governance; no new production test run, hosted CI or experiment evidence is claimed.

Design [PR #15](https://github.com/Jeruzael/SEED/pull/15) merged at `fd98bb2926ce452305c8e09a020fcb6aa2c50009`; closure [PR #16](https://github.com/Jeruzael/SEED/pull/16) produced current master. B0–B9 remain COMPLETE / VERIFIED at source/CI level, schema v7. [Canonical tracker](../../seed-0.2-development-plan.md) and [implementation log](../../implementation-log.md) retain those closure records. [Roadmap index](../../roadmaps/seed-b10-to-0.3-development-roadmap-v1.0.md), original PDF and historical baselines are protected.

This plan is a proposed execution contract for owner review, not permission to implement any checkbox. No current DESIGN AMENDMENT REQUIRED blocker was found by source inspection. Adapter equivalence and bounded evidence feasibility are future gates, not proved by this document. If those gates require changing cognition, producer semantics/schema or approved limits, stop and document **BLOCKER — DESIGN AMENDMENT REQUIRED** before downstream work.

## 2. Repository audit and core-touch analysis

| Existing boundary inspected | Actual interface/behavior relevant to implementation |
| --- | --- |
| `seed/organism.py:42–83,194–280` | Constructor acquires instance lock, creates Memory/Body, recovers B4/commands, sets identity/settings/runtime. Cycle prepares all candidate predictions before selection; action side effects precede second perception; line 244 calls imported `evaluate_prediction`, then B5, legacy reward/Q, paired B1 persistence, B4 recovery, attention and B7. Cycle is not one transaction. `run()` processes autonomous timing/commands and is forbidden in evaluation. |
| `seed/memory.py:48–76,111–158` / `seed/migrations.py` | Constructor creates/migrates SQLite, WAL and possibly backup. `record_transition_experience` commits episode, transition, B4 queue, B5 and B8 record together; Q is a separate commit. `db`, `_lock`, `get_q`, `get_meta` suffice for frozen inference reads. Schema VERSION=7 remains unchanged. |
| `seed/predictor.py:85–155` | `predict_candidates(state, actions, snapshot=rows)` performs existing pure inference. Latest 200 raw rows, no corrupt-row refill; support >=2 action, then global, then persistence; finite scaled means/clamps and Boolean frequency. Confidence is evidence support, not probability/accuracy. |
| `seed/prediction_error.py:95` / `seed/curiosity.py:37` | Existing pure B3 evaluation returns `PredictionEvaluation`; B5 takes actual error and prior applicable B4 facts. Evaluation wrapper must return the original result unchanged. External point scores differ from B3 normalization and never replace it. |
| `seed/world_model.py:135–213` | `recover()` drains <=100 queued IDs per call; `observe_transition()` uses exactly-once processed/queue state; lifetime means and contradictions, no forgetting. Freeze must drain to empty with bounded progress, not assume one recover call suffices. |
| `seed/semantic_memory.py:100–206` | `Consolidator.run(state, provenance)` accepts only policy_selected/owner_requested; cursor/history/runs persist. Resource guards, 8-sample/0.30 promotion, source fingerprints and source_unavailable behavior remain. Declared every-eight maintenance uses owner_requested in producer, declared_maintenance in evaluator evidence. |
| `seed/self_model.py:588–689` | `_read_evidence` has source limits; `SelfModel.update(tid,session,stop)` publishes singleton and can return failed/skipped after catching exceptions. `project_snapshot(payload,read_at)` is pure. Default `clock=time.time` binds at import; actual organism passes a lambda. Raw storage/PID and capped counts must be checked against source, not invented totals. |
| `seed/decision.py:97–257`, `decision_record.py` | Injectable `rng`; `prepare(state,selected_at,decision_id)` owns shared Q/history snapshot; `select(prepared)` chooses eligible exploration/maxima ties. `Selection` preserves state/prediction/record. Structural record validation and prediction_digest are reader-safe; writer certification may characterize fixtures but observer must not rerank. |
| `seed/learner.py:61–83`, `config.py` | Legacy reward and `old+.18*(reward-old)` unchanged; defaults epsilon .15/alpha .18. B8 preflight calls reward before action and actual update calls it again. D random counterpart uses epsilon 1.0 through existing settings, not forged records. Low-disk consolidate reward remains even though B8 guards block it. |
| `seed/body.py`, `runtime.py`, `paths.py` | Body invokes host commands/network/sensors and real time; must never instantiate it in a worker. InstanceLock uses no-follow flock/PID. checked_path rejects symlink components but is insufficient alone for race-safe evaluator roots; evaluation adds descriptor-relative ownership/type checks. |
| Clock/RNG/UUID sites | Organism/memory/world/telemetry/commands use module time; B6/attention clocks can be supplied; B7 has bound default. Organism/decision use UUID; Learner legacy choose uses module random although cycle uses B8. Fresh worker bootstrap isolates all adapters; no coordinator/dashboard/global normal-process patch. |
| `dashboard/app.py`, `dashboard/api/observer.py` | FastAPI router factories under **api/**, not routes/**; create_app(home, port, operator). Existing SecurityMiddleware enforces loopback Host/Origin, CSP, CSRF/operator rules. Evaluation remains GET-only even in operator mode and optional on absent package/root. |
| `dashboard/services/read_store.py`, `evidence_reads.py` | Existing services open organism DB mode=ro, bounded transactions/VM and strict JSON; evaluator reader must use its own root and stricter independent artifact schema, never reuse learner-home fallback or migrate snapshots. |
| `dashboard/static/{app,api,evidence}.js`, `views/decisions.js` | Dynamic view modules under **static/views/**; bounded streamed evidence parser preserves large IDs, el uses textContent, generation/AbortController guards, manual active Astra reads. Current opaque-cursor helper assumes numeric IDs; Evaluation needs its own cursor validation. Existing 10 s client evidence timeout is not B10's 2 s request contract. |
| `tests/` / `tests/dashboard/` | pytest unit and cycle integration tests coexist; conftest home/legacy_home use tmp_path. Cycle tests inject perceptions/RNG; history factories are in test_predictor/test_decision; seven standalone scenario modules use owned TemporaryDirectory. Astra fixture restricts destination to temporary storage; Node DOM harness exists, no browser dependency. |
| `.github/workflows/seed-ci.yml` | Exact PR-head checkout; locked install and full `python -m pytest -q` on all three jobs; seven standalone scenarios on Python 3.13 Linux/macOS only. Existing Python 3.11 scenario skip is workflow policy, not permission to skip new acceptance tests. Python B10 technical tests must collect on all jobs; browser availability/results recorded separately. |

**Existing B1–B8 source modifications proposed: none.** The necessary seams are external: replace worker-local organism Body binding before construction; inject DecisionSystem.rng; wrap instance prepare/select/action/B7 methods for capture/staged clocks; replace worker-local imported `seed.organism.evaluate_prediction`; provide owned SQLite connection/transaction proxy and frozen read facade. These preserve formulas, settings, ordering and producer APIs, with no reverse dependency or production default change. Do not refactor core for convenience.

| Potential hot spot | Why needed / external alternative | Cognition or outside-B10 change? | Existing evidence / future regression |
| --- | --- | --- | --- |
| `seed/organism.py` | Score/capture boundary and synthetic Body; evaluation-local delegation wraps original call, no file edit. | None intended. | test_prediction_error_cycle, test_decision_cycle; I13 test_adapter_matches_original_cycle. |
| `seed/memory.py` | Commit/page/physical bounds; worker-local sqlite connection factory/proxy, no file edit. | Limits only disposable evaluation writers; normal Memory unchanged. | test_transitions/test_migrations; I06 transaction-proxy parity and I13 complete table equality. |
| `seed/{decision,learner,predictor}.py` | RNG and preselection evidence; existing injected rng/pure batch interfaces, no file edit. | No changed selection/ties/weights/reward/math. | test_decision/test_predictor/test_baseline_learner; I04/I10/I17/I13. |
| `seed/{world_model,semantic_memory,self_model,curiosity_attention,telemetry}.py` | Clock coverage, maintenance/update fidelity; local proxy references and delegated instance methods, no file edit. | Stored timestamps controlled only in worker; actual producer results retained. | Existing corresponding cycle/unit tests; I04/I13/I19. |

For any later proposal to touch one of these files, answer necessity, external alternative, cognition impact, normal-behavior impact, existing tests and new equivalence regression before edit. If external adapters cannot satisfy LOCKED invariants without core/schema/producer changes, stop for a design amendment rather than slipping changes into an infrastructure PR.

## 3. Architecture-to-code map

All paths below are **future proposed files**, not current deliverables. In task file inventories, a bare Python filename or metrics/scenarios path means `development/evaluation/<path>`; a bare test filename means `tests/evaluation/<path>`, except dashboard tests: test_evaluation_assets.py always means `tests/dashboard/test_evaluation_assets.py`. Each brace group expands into the listed exact files. Package initializers remain inert; worker imports must not pull in coordinator/scenarios/truth. No dynamic plugin registry.

| Approved component | Existing dependency / interface used | Proposed responsibility/location | Must not modify or depend upstream on | Tests / task dependencies / main risk |
| --- | --- | --- | --- | --- |
| Coordinator | CycleResult and closed worker channel | `development/evaluation/coordinator.py` phase/limits/member lifecycle | Core run loop/commands, installed state | I07/I12/I30; specs/roots/channel; partial-state ambiguity |
| Learner worker | SeedOrganism.cycle, Memory/producer APIs | `worker.py`, `bootstrap.py` spawn entry and capability-only launch | Scenario, metrics, AnalysisPlan/truth imports or config | I04/I07/I08/I13; isolated pre-import setup; clock/host leakage |
| SyntheticBody adapter | Existing Body(home).perceive(), core perform_action | `adapters.py` SyntheticBody and delegated capture | Actual Body initialization, duplicated internal action effects | I10/I13; channel; perception fallback |
| Deterministic profile | time/uuid/rng use sites, lock identity | `determinism.py`, `profile.py` controlled streams and source facts | Coordinator real clock, global normal processes | I04/I05; canonical; bound defaults |
| Scenario engine | Existing ACTIONS/validated_state domains | `scenarios/{stationary,shift,evidence,constrained}.py`, inert registry | Core cognition/action eligibility; forced policy | I14–I16; private engine; action-mix confounding |
| Evaluator-private truth | No core dependency | `scenarios/private.py` parent-only rules/view | Worker import graph/messages | I08/I14; allowlist; sentinel leakage |
| AnalysisPlan | Approved section 6/12/15 contracts | `analysis.py` inventory/freeze/reconciliation | Learner tables/settings/ACK contents | I02/I20; typed canonical; plan drift |
| Experiment specification | Source/settings/schema facts | `specs.py`, `registry.py` closed registered definitions | Arbitrary formulas/module names/output paths | I01/I02; metric/scenario allowlists; oversize expansion |
| Baseline runner | Captured same-cutoff history; B8 epsilon 1 policy | `baselines.py`, coordinator counterpart role | Hidden rules/future outcome history; learner RNG | I16/I17; isolated state; asymmetric inputs |
| Metric registry | Raw B1–B8 evidence; independent reference equations | `metrics/{registry,prediction,producers,findings}.py` | Producer tuning, model updates, confidence-as-accuracy | I18–I20; immutable plan; literal math/denominator bugs |
| Minimal score journal | Existing B8 digest and original pure B3 result | `checkpoint.py`, `point_scores.py` parent durability | Aggregate/baseline/task-utility/final digest/index/UI work | I09/I10; channel; failed ACK/double learning |
| Disposable state/clone | Memory schema v7, SQLite backup | `state.py`, `db_adapter.py` owned mutable/frozen facades | Normal schema/migrations, installed backup | I06/I11; paths/limits; WAL/transaction escape |
| Artifact publisher | Captured rows/snapshots, closed inventory | `artifacts.py`, `indexes.py` bounded atomic payload/partials | Learner writes/report ingestion | I21/I23; plan/report/digests; publication crash |
| Scientific digest | All-table projection, B8 selected digest validation | `canonical.py`, `science.py` typed streaming science | Raw producer payload rewriting or unlisted exclusions | I02/I22; evidence join; incidental-field overreach |
| Artifact-integrity digest | Exact bytes/receipt/chunk identity | `integrity.py` length framing and chunk verification | Scientific reserialization or authenticity claims | I23/I24; publication inventory; receipt substitution |
| Replay | Stored tuple/digest joins, structural validators | `reader.py`, `replay.py` bounded recorded-data assembly | Predictor/DecisionSystem/WorldModel/Consolidator/SelfModel execution | I24; integrity; recomputed history |
| Deterministic re-execution | Trusted current checkout/profile, owned checkpoints | `reexecution.py` fresh run and divergence | Artifact code/import paths, checkout/install/migration | I25; coordinator/reader; incompatible identity |
| Evaluation artifact reader | stdlib file/SQLite reads; pure record validation | `reader.py` dedicated evaluation root capability | Coordinator, worker, scenario or scoring imports | I24/I26; indexes; read-budget breach |
| Astra Evaluation service/routes | Existing FastAPI/SecurityMiddleware/ServiceError | `dashboard/services/evaluation.py`, **`dashboard/api/evaluation.py`** | Organism service storage substitution/execution endpoints | I26; stable reader contract; optional import failure |
| Astra Evaluation UI | el/parseEvidence/active view shell | **`dashboard/static/views/evaluation.js`**, `evaluation_support.js` | Model math, historical reranking, mutate(), automatic re-execution | I27–I29; routes; overclaim/cursor/DOM errors |
| CLI | Checked registered IDs, bounded coordinator/re-execution | `cli.py`, `__main__.py` explicit developer verbs | main.py/default installed home/arbitrary paths/code | I25/I30; all engineering gates; unsafe dispatch |

Storage: `.seed-evaluation/work/<run-id>/learner/` for assigned state; `.seed-evaluation/evaluation/{plans,runs,partials,receipts}/` plus bounded root index for evaluator data. Fixed checkout-owned root only. A future `.gitignore` entry belongs to I03, not this planning task. Every plan copy/reservation counts against existing bounds; no separate unbounded plan store.

## 4. Shared interfaces and task execution rules

These are **planned signatures**, not implementation code. I01 declares the RootCapability protocol used by I02; I03 supplies its safe concrete implementation. I02 unit tests use a closed fake capability to prove serialization/durability ordering, and I03 integration tests repeat freeze admission with real owned descriptors. This avoids a dependency cycle while keeping filesystem safety gated before dispatch. I01 defines immutable dataclasses/closed mappings in contracts.py: ExperimentSpec, AnalysisPlan, FrozenPlan, RunRequest, WorkerLaunch, Observation, Action, PreUpdateEvidence, CheckpointFrame, CompletedEvidence, Attempt, RunResult, Measurement, QuestionFinding, Population, Payload, Receipt, RunSummary, RunDetail, Event, Curve, ReplayPage, ReexecutionResult and VerificationReport. `Json` is the closed bounded JSON value union; `EventKey` is `(phase,subcase,ordinal,stage)`; Action is one of the four existing strings. `ReadFacade`, `OwnedState`, `RootCapability`, `LearnerClient`, `WorkerHandle`, `CaptureSession`, `Budget`, `Profile`, `Streams`, `Clock`, `UUIDStream`, `RunArtifact` are named interfaces/classes defined in the tasks that produce them. WorkerLaunch contains only assigned learner capability, protocol/phase schedule, public settings, learner RNG state and opaque deterministic UUID configuration identity; no AnalysisPlan, scenario seed/config, evaluator path, truth, metric or experiment name that conveys answers.

**Every task follows this five-step test-first cycle after authorization** (checkboxes apply individually to each task, not permission today):

- [ ] Write the task's named tests/assertions below in its specified test file; classify and include all listed failure/boundary cases.
- [ ] Run `python -m pytest -q <task test file(s)>`; confirm failure for the missing intended behavior, not an unrelated import/fixture error.
- [ ] Implement the exact planned interface in the task's files, preserving Global Constraints and approved spec equations/contracts.
- [ ] Run the same focused command and relevant existing regressions; expected all pass, no new skipped acceptance checks. Use actual results, never promised counts.
- [ ] Inspect diff and `git diff --check`, then commit only those source/tests/support docs with the task's stated message. Independent review belongs to its PR gate.

No helper imports tests into production evaluation modules. Future `tests/evaluation/conftest.py` owns independent temp roots, poison live Body/network/clock assertions, fixed-channel fakes, checkpoint/crash injection and literal row factories. Fixture helpers generate declared producer state; they cannot force the registered measured SEED trajectory. Rollback defaults: revert the narrow commit before further dependent work; retain labeled evaluator prefixes, discard/recreate only owned disposable learner state, never touch installed SEED or migrate normal state. Each task below specifies additional recovery concerns and whether runtime changes are confined to evaluation (E), observer (O), or validation/no running experiment (V); **none changes normal SEED cognition**.

## 5. Dependency-driven phases and actionable tasks

### Phase A — Contracts, package skeleton and isolation

#### B10-I01 — Closed types and registries

**Files:** create `development/__init__.py`, `development/evaluation/{__init__,contracts,registry}.py`, `tests/evaluation/{__init__,conftest,test_contracts}.py`. Uses existing ACTIONS/observation contract. **Depends:** none. **Runtime:** V. **Commit:** `feat: define closed B10 evaluation contracts`.

**Interfaces:** `decode_message(raw: bytes, operation: str) -> Json`; registry lookup by fixed ID/version; the shared types in section 4. Package import performs no work, root access or dispatch. Operations are observation/action_catalog/apply/checkpoint/constant acknowledgment only; no reflective dispatch.

**Tests (unit, leakage/security, negative, bounds):** `test_closed_message_limits` asserts 64 KiB accepted at permitted structure and one-byte-over rejected, depth 16/entries 4096 boundaries, duplicate keys/unknown fields/unknown enum/nonfinite/invalid domains rejected; `test_public_types_exclude_truth` asserts learner operation/field sets contain no truth/score/config/expected-result; `test_registry_rejects_code` rejects module paths/expressions/plugins. Observation permits only six approved fields, preserves missing/null distinctions, load[0, 2], finite percentages[0, 100], hour[0, 23].

**Acceptance/failure/recovery:** typed public/private contracts distinct; empty initialization inert. Invalid input fails closed before any worker work, with fixed nonsensitive errors. Revert inert package/tests; no state exists.

#### B10-I02 — ExperimentSpec, typed canonical plan and freeze admission

**Files:** create `specs.py`, `analysis.py`, `canonical.py`, `tests/evaluation/test_specs.py`, `test_analysis.py`, `test_canonical.py`; extend registry.py. Uses source settings/versions without executing core. **Depends:** I01. **Runtime:** V. **Commit:** `feat: validate and freeze B10 analysis plans`.

**Interfaces:** `validate_spec(raw: Json) -> ExperimentSpec`; `expand_inventory(plan: AnalysisPlan) -> tuple[Measurement,...]` descriptors; `canonical_bytes(value: Json) -> bytes`; `analysis_digest(plan: AnalysisPlan) -> str`; `freeze_plan(plan: AnalysisPlan, capability: RootCapability) -> FrozenPlan` (capability implemented I03). Freeze body/digest/receipt durably before dispatch; no post-start rewrite even before first measurement. Thresholds carry version/metric/population/direction/role/rationale/missing rule.

**Tests (unit, reproducibility, negative, bounds):** `test_plan_digest_typed_values`: `assert digest(1) != digest(1.0)` and `assert digest(+0.0) != digest(-0.0)`, reorder keys equal/arrays unequal, tagged finite float hex round trip and top-level single LF. `test_inventory_admission` rejects expansion exceeding 128 KiB plan/256 KiB metrics/4 MiB control or seed/run/phase caps without pruning. `test_freeze_precedes_dispatch` asserts no dispatch without matching durable body/receipt and immutable version/digest. Parameterized `test_every_analysis_field_is_frozen` covers every field group in spec 6/12; changed rules require new version/digest/explanation/fresh run. No retrospective frozen flag.

**Acceptance/failure/recovery:** experiment IDs exact regex/positive versions; requested metric/scenario/version/limits registered; conflicting spec/plan INVALID before worker. Canonical domain `SEED_B10_ANALYSIS_PLAN_V1\0`; excludes only own digest and incidental receipt time/ID. Preserve old receipt on defect; new plan identity, never overwrite. No file publication until safe root primitive I03 is available.

#### B10-I03 — Owned roots, reservations and mechanical dependency gate

**Files:** create `paths.py`, `limits.py`, `tests/evaluation/test_paths.py`, `test_dependency.py`, `test_limits.py`; modify `.gitignore` only to ignore `.seed-evaluation/`. Uses seed.paths only as characterization, not sufficient safety. **Depends:** I01/I02. **Runtime:** V. **Commit:** `feat: isolate B10 roots and admit bounded work`.

**Interfaces:** `RootCapability.open(kind: str, identity: str, mode: str) -> file descriptor`; `Budget.reserve(request: RunRequest) -> reservation`; limits constants/enforcers section 8. Worker-facing capability admits only assigned learner slot, no evaluator/foreign root, arbitrary path or installed fallback. Root creation and application-managed ordinary files use exclusive no-follow directory-relative opens, effective-UID/regular-file/link/descriptor identity checks. These do not assert a descriptor binding across SQLite native opens. I06 validates DB/sidecars under the amended trusted-code model; detected storage mismatches are terminal. Root/control-file writes require current bounds/reservations; every admission reconciles actual retained usage with outstanding reservations without double-counting active runs (R6).

**Tests (leakage/security, integration, negative, bounds):** `test_root_attack_matrix` rejects absolute/traversal/encoded separators/NUL/symlinks/path swaps/nonregular/foreign ownership/hard link where detectable; `test_no_inherited_home_or_secrets` poisons installed SEED_HOME and credentials and asserts worker launch has neither. `test_dependency_direction` AST+resolved import graph denies direct/indirect seed→evaluation, worker→private coordinator/scenario/scorer and reader→executor; inspect imports and fixed registry, not only literal grep. `test_seed_operates_without_evaluator` uses a copied trusted source temp tree without evaluation/config/artifacts, synthetic Body and temporary home to construct/cycle/close normal SEED; compare original behavior. Root reservation one-over/retained 60/16 GiB fail before operation; no automatic deletion. Future R1 tests reject existing unsafe paths and foreign assigned capabilities before SQLite, and test detectable pre/post identity conflict; an injected observable mismatch asserts terminal detection, not prevention of excluded hostile native races. R6 tests over-cap freeze/control writes, changing retained usage between admissions and active-run reservation reconciliation. R10 tests aliased and unresolved dynamic imports in helpers reached from protected roots, not just immediate module prefixes.

**Acceptance/failure/recovery:** mandatory **G1** dependency/storage gate. No evaluator tables or storage ingestion, absence preserves core. Safe delete only owned empty reservations after identity recheck; never follow unsafe root to clean it. Detected capability/inode/type/owner/replacement mismatch stops the affected run; it cannot be silently reopened or trusted for publication. Preserve invalid/incomplete owned evidence and do not clean a mismatched/foreign path. No scientific dispatch yet.

### Phase B — Deterministic execution profile

#### B10-I04 — Independent streams, logical clocks and pre-import bootstrap

**Files:** create `determinism.py`, `bootstrap.py`, `tests/evaluation/test_determinism.py`; extend contracts launch types. Uses identified time/RNG/UUID bindings. **Depends:** I01/I02/I03. **Runtime:** E. **Commit:** `feat: control disposable worker determinism`.

**Interfaces:** `Streams.for_identity(identity: Json) -> Streams`; `.scenario(phase,event_index,channel)->float`, separate learner/baseline/legacy RNGs; `Clock.stage(phase,ordinal,stage)->None`, `.wall()->float`, `.monotonic()->float`; `UUIDStream.next_hex(role: str)->str`; `install_worker_adapters(launch: WorkerLaunch) -> CaptureSession` before producer imports/construction. Worker process only, never patch coordinator/dashboard/normal process clocks.

**Tests (unit, integration, reproducibility, leakage, negative):** `test_keyed_scenario_draws` exact domain/canonical key and first 53 bits/2**53 in[0, 1), policy variant excluded; `test_named_stream_independence` asserts consuming baseline/legacy cannot change learner or scenario. `test_clock_schedule` base 1800000000, 10*ordinal and stage 0/1/2/3/4, training offset, repeated same stage stable, stale +301 s, retry intervals, no wake inference at 10 s. `test_uuid_preinitialization_identity` distinct role/counters, 32 hex, ignores storage run ID, no circular post-init digest. `test_bound_clock_and_host_poison` covers B7 default/producer references before import; live wall/monotonic/body/network/uuid fallback raises; parent real clocks unaffected.

**Acceptance/failure/recovery:** dedicated `random.Random` SHA256 learner/baseline seeds and algorithm/profile/draw evidence as spec 9; no global production monkey patch. Abort unsupported binding; fresh worker next attempt, no stream restoration from another run. A normal-control subprocess proves no changed defaults. Retry-clock offsets are declared and accumulated across skipped attempts and subsequent stages, so retry advancement cannot make wall or monotonic time regress when the next completed ordinal starts.

#### B10-I05 — Source and execution-profile compatibility

**Files:** create `profile.py`, `tests/evaluation/test_profile.py`. Uses requirements-lock.txt, core/schema versions and Python/SQLite runtime facts. **Depends:** I04. **Runtime:** V. **Commit:** `feat: validate B10 source and execution profiles`.

**Interfaces:** `capture_profile(checkout: RootCapability) -> Profile`; `require_source(spec: ExperimentSpec, profile: Profile) -> None`; record commit, clean tracked/untracked source state, lock digest, Python implementation/version, SQLite compile/runtime, OS/arch and adapter versions. Repository identity queries are coordinator-owned read-only Git operations, never learner shell/tool actions or artifact-supplied commands.

**Tests (unit, reproducibility, negative/security):** `test_dirty_or_changed_source_rejected` rejects dirty tracked code/dependency contents, untracked executable source and mismatched lock before dispatch; generated ignored owned evidence is not source. `test_profile_compatibility` same supported profile eligible, changed source/schema/adapter/runtime incompatible; environment report contains no secret variables/absolute user path. No automatic checkout/install/migration. R5 future repair must define canonical complete profile identity, compare ExperimentSpec.profile_digest (including runtime/core/adapter facts), and require admission before scientific learner construction; explicit technical fixture launches remain separate.

**Acceptance/failure/recovery:** complete identity precedes worker construction; incompatible re-execution is explicit later I25. Report actual profile without promising cross-platform equality; no learner state on rejected source.

### Phase C — Disposable learner state and lifecycle

#### B10-I06 — Owned SQLite initialization, clone and transaction bounds

**Files:** create `state.py`, `db_adapter.py`, `tests/evaluation/test_state.py`, `test_db_adapter.py`. Uses Memory, migrations VERSION7, sqlite backup; no changes to seed files. **Depends:** I03/I04/I05. **Runtime:** E. **Commit:** `feat: manage isolated B10 SQLite state`.

**Interfaces:** `OwnedState.fresh(capability,public_settings)->OwnedState`; `.checkpoint()->Path`; `.clone(slot)->OwnedState`; `.raw_tables()->Json`; `ReadFacade(db,lock).get_q/get_meta`; evaluation-local connection proxy covers context-manager __exit__, explicit commit/rollback, executescript auto-commit and all producer transaction paths. Page cap 32 MiB applied before writers; growth checked after **each** committed producer transaction, not just cycle end. R2 includes autocommit writer finalization through fetch/exhaustion/iteration/close, not execute alone. R3 admits full checkpoint/clone allocation and checks the shared workspace through completion/cleanup; R4 shares a terminal run-budget writer-stop latch across original/clone connections and consults it before every subsequent transaction. No literal ceiling or overshoot allowance changes.

**SQLite identity contract (R1, future repair):** before connection validate fixed owned directory/capability identity, owner/type, expected filename, pre-existing file/no symlink/unsafe hard-link checks where detectable, root/reservation bounds; explicitly admit fresh owned initialization and prefer existing-file URI semantics such as `mode=rw` for already-created state where producer-compatible. Immediately after successful connection revalidate main DB identity/type/owner, capability directory identity and observable SQLite database path/facts before accepting state. Perform bounded periodic/transaction-boundary main/sidecar/capability/root/growth checks and pre-checkpoint/clone/publication revalidation. A detected conflict is terminal, no scientific trust or unsafe cleanup/retry. This detects observable mismatches; standard sqlite3 cannot guarantee preventing malicious same-UID swaps inside native opens. Such races alone are excluded, not ordinary-file safety or trusted-code capability/routing checks. No native VFS is adopted.

**Tests (integration, reproducibility, negative, bounds):** `test_clone_preserves_all_tables` asserts schema/settings/meta/sqlite_sequence/B1/Q/B4 queue+pending+processed/B5 attention/B6 history+cursor+runs/B7/B8 byte/logical fidelity in consistent closed backup, no live-WAL file copy. `test_transaction_proxy_parity` checks commit/rollback/exception/row_factory/progress-handler/timeouts/in_transaction versus raw connection. `test_every_commit_enforces_growth` hits 32 MiB logical/64 MiB physical/128 MiB workspace and one atomic <=36 MiB physical overshoot; no next producer transaction, LIMIT_REACHED prefix. `test_foreign_or_installed_clone_rejected` and independent home mutations. Future R1 repair tests: `test_existing_unsafe_sqlite_path` (symlink/nonregular/foreign ownership before connect), `test_existing_file_sqlite_admission` (missing expected DB not silently recreated), `test_post_connect_sqlite_identity` (observable pre/post conflict terminal), `test_sqlite_sidecar_validation` (observable unsafe WAL/SHM/journal owner/type terminal), `test_sqlite_capability_mismatch` (another learner/evaluator path rejected), `test_sqlite_no_installed_fallback` (poisoned SEED_HOME unused). R2 tests returned-row writer finalization; R3 tests backup workspace admission/completion; R4 tests a sibling cannot commit after the shared latch. These tests are required future remediation, not created/run by this amendment.

**Acceptance/failure/recovery:** fresh schema v7, no migration beyond ordinary fresh initialization, clone state complete. WAL/SHM not retained as snapshot. Logical transaction failure rolls back its transaction only; acknowledged earlier updates remain. Physical crossing preserves actual committed data and terminates; the connection proxy latches a writer-stop condition checked before every subsequent explicit or implicit producer transaction, even if a producer catches the first error. Only bounded read/checkpoint/close cleanup remains permitted; cleanup checkpoint/close handled within reserved allowance, no pretending state fit cap. Storage mismatch is terminal and invalidates trust in affected state/checkpoints; no publish or continued producer write. A failed clone/checkpoint admission preserves the source prefix; no blind cleanup of paths whose capability identity failed.

#### B10-I07 — Spawned worker lifecycle and bounded shutdown

**Files:** create `worker.py`, `coordinator.py`, `tests/evaluation/test_workers.py`; extend bootstrap.py. Uses SeedOrganism constructor/cycle/close only with installed local adapters. **Depends:** I01–I06. **Runtime:** E. **Commit:** `feat: bound disposable B10 worker lifecycle`.

**Interfaces:** `WorkerHandle.start(launch: WorkerLaunch)->WorkerHandle`, `.request(message)->Json`, `.stop(reason)->RunResult`; `Coordinator.admit(request)->RunRequest`; minimal scaffold dispatch gated by frozen plan/G1 and later truth/checkpoint gates. Use fresh spawn processes, not inherited fork caches; package entry imports no evaluator truth. Sanitized environment allowlist, no inherited SEED_HOME/credentials/socket configuration. R9 adds an explicit closed launch mode for an admitted completed owned schema-v7 fixture/clone in a fresh process; preserve all tables/settings/sequences and independent process-local locks/RNG/cache. This lifecycle plumbing is not I11 frozen assay or automatic partial-run resume. Only the assigned evaluation worker is a trusted writer for its DB.

**Tests (integration, leakage, negative/failure, performance/bounds):** `test_repeated_workers_are_independent` no shared home/locks/RNG/UUID/cache/settings/queue/cursor; `test_worker_timeout_and_cleanup`120 s run/1800 s suite/5 s cleanup fake real clock enforcement and force termination after graceful window; parent can preserve prefix if worker dies. `test_one_worker_and_two_clone_slots` strict active count, no evaluation use of run()/process_commands()/main.py. `test_invalid_launch_never_constructs` fixed public bootstrap schema, constructor failures recorded without secret errors. Future `test_second_trusted_sqlite_writer_rejected` asserts a second B10 writer cannot enter an assigned DB; R9 asserts completed owned clone launch preserves complete state in a fresh worker. R1 storage mismatch must terminate the affected worker boundedly and forbid checkpoint/publication trust. R7 tests terminal failure/no subsequent dispatch after an action may already have taken effect.

**Acceptance/failure/recovery:** known owned PID/capability, no concurrent writers, bounded parent real time/memory monitoring with best-effort 512 MiB clearly reported. Kill/cleanup only assigned worker/owned state; no automatic resume after ambiguity. CLI scientific dispatch remains unavailable until later gates.

### Phase D — Mechanical learner/evaluator truth boundary

#### B10-I08 — Closed channel, scenario capability and negative leakage tests

**Files:** create `channel.py`, `scenarios/{__init__,private}.py`, `tests/evaluation/test_channel.py`, `test_leakage.py`; extend worker/coordinator. **Depends:** I01–I07. **Runtime:** E. **Commit:** `feat: enforce B10 learner truth isolation`.

**Interfaces:** `LearnerClient.observation(phase: str, ordinal: int)->Observation`, `.action_catalog()->tuple[Action,...]`, `.apply(action: Action,ordinal: int)->Observation`; bounded `send_checkpoint(evidence: PreUpdateEvidence)->constantACK` as protocol transport, not worker score API. Parent `ScenarioEngine.initial_observation/apply_action` and `PrivateTruthView` never available to client. Tuple identity includes declared subcase and stage; one outstanding request, duplicate/out-of-order rejection.

**Tests (leakage/security, unit, integration, negative, bounds):** `test_all_forbidden_dispatch_and_sentinels` truth/config/score/expected/reflection unknown ops/extra fields/names/messages/exception timing fixed errors; `test_truth_absent_in_all_learner_state` scan every table/JSON/file/settings/meta/B4/B6/B7/Q for private sentinel and plan/report/finding values. `test_protocol_tuple_identity` distinguishes training/measured/C variants/ordinal reuse, rejects reordered ACK/action/frame, no concurrent channel. Detached mappings, 64 KiB/depth 16/4096 entries, network null and omitted load/disk valid; nonfinite/unknown/host timestamps rejected.

**Acceptance/failure/recovery:** **G2** zero forbidden truth via learner-visible APIs/state. Worker receives no scenario seed/rules/root/plan; private annotations only parent artifacts. Legitimate outcomes/B3 feedback allowed. Contract violation FAILED; no unsafe operation dispatched. R7 requires a terminal channel/worker latch after malformed outcome/exception following a possible action effect: preserve ambiguous prefix, boundedly stop, no identical retry or later operation. R8 requires a strict nested public producer-prediction contract, rejecting unknown/truth fields/domains, not a free-form dict; checkpoint/ACK execution remains I09. Trusted-code capability guarantee only; the storage amendment excludes hostile concurrent same-UID SQLite native-open races, without relaxing truth/storage routing.

### Phase E — Minimal durable pre-update checkpoint

#### B10-I09 — Point scoring and durable journal, excluding publication work

**Files:** create `point_scores.py`, `checkpoint.py`, `tests/evaluation/test_checkpoint.py`. Uses existing B8 prediction_digest and closed preserved evidence. **Depends:** I02/I03/I08. **Runtime:** E. **Commit:** `feat: checkpoint B10 scores before learning`.

**Interfaces:** `point_scores(evidence: PreUpdateEvidence)->Json`; `ScoreJournal.append(frame: CheckpointFrame)->None`; `.ack(evidence)->str` returns only `SCORE_ACK` after validate/append/flush/fsync. Exact section 8 header/evidence fields and compact finite ASCII JSON identity hashes; precreate file and durably establish directory before worker dispatch.

**Tests (unit, integration, negative/failure, bounds):** `test_point_score_literal` numeric absolute errors and Boolean correctness, `assert brier(.75,False)==.5625`; support-confidence-only Brier unavailable, all-unavailable honest statuses, malformed contract no ACK. `test_fsync_precedes_constant_ack` asserts `capture_prediction < capture_outcome < point_score < append < flush < fsync < ACK < current_learning`. `test_pre_ack_failure_blocks_current_updates` partial write/flush/fsync/10 s deadline/malformed/duplicate reject no ACK. `test_ack_path_calls_no_aggregates` poison aggregation/baselines/utility/artifact/science/integrity/index/UI functions; ACK still works. Header<=4 KiB, before/prediction/after<=16 KiB each, frame<=64 KiB; byte-over rejects before write.

**Acceptance/failure/recovery:** point vector exactly four approved signals/statuses/reasons; no task utility/aggregate/labels in ACK. Journal outside learner root, reuse in payload not duplicate. Interrupted partial append retained visibly, never synthesize ACK or retry frame/current transition. INCOMPLETE storage/deadline versus FAILED protocol distinguished. G3 also requires actual-cycle I10/I13.

#### B10-I10 — Delegated cycle capture and exact B3 call wrapper

**Files:** create `adapters.py`, `tests/evaluation/test_cycle_adapter.py`; extend worker/bootstrap. Uses original organism Body binding, instance prepare/select/perform_action and imported evaluate_prediction. **Depends:** I04/I06/I08/I09. **Runtime:** E. **Commit:** `feat: adapt existing SEED cycles for external scoring`.

**Interfaces:** `SyntheticBody(home: Path, client: LearnerClient, clock: Clock).perceive()->dict`; `CaptureSession.attach(core: SeedOrganism)->None`; `evaluate_with_checkpoint(prediction: dict, outcome: dict)->PredictionEvaluation`. Keep original B3 function reference, call exactly once, block on external constant ACK, return **same original result**; never implement B1–B8 again. Capture `prepare` detached batch/history/Q before `select` and original Selection before action/outcome. Synthetic action request delegates alongside actual core internal action, not replaces it.

**Tests (integration, reproducibility, leakage, negative):** `test_prediction_precedes_selection_and_outcome` retains all candidate predictions and exact selected digest/cutoff with one batch, two perceptions, original Q/history snapshot. `test_original_b3_result_returned_unchanged` equality/identity and same B3 diagnostics. `test_synthetic_body_installed_before_constructor` poison real Body and sensor calls. `test_prior_action_effects_remain_before_checkpoint` reflect/consolidate use only prior completed data, preserved even on no ACK; no current Q/experience/B4/B7. Synthetic observation messages exclude wall_time; adapter derives controlled logical wall_time locally for ordinary producer metadata, never host time.

**Acceptance/failure/recovery:** no core file edits; no truth/score in worker return. Stage clocks selection 0/start 1/outcome 2/after ACK stage 3/publication-maintenance 4 via delegated boundaries, not arbitrary call count. Failed attach/import aborts worker before run. Once ACK given, original current-update path continues under existing bounds; later failures cannot withdraw ACK.

### Phase F — Frozen selection assay

#### B10-I11 — Snapshot/drain and strict immutable frozen worker

**Files:** create `frozen.py`, `tests/evaluation/test_frozen.py`; extend state.py/worker. Uses Predictor, Learner read/reward, DecisionSystem.prepare/select, pure B3/B5/B7 projection. **Depends:** I06/I08/I10. **Runtime:** E. **Commit:** `feat: preserve immutable B10 frozen assays`.

**Interfaces:** `freeze_state(owned: OwnedState)->OwnedState`; `FrozenWorker.probe(observation: Observation,key: EventKey)->CompletedEvidence`; minimal ReadFacade with db/lock/get_q/get_meta, mode=ro/query_only/write-denying authorizer; no Memory/SeedOrganism constructor. Drain prior B4 queue with bounded progress before checkpoint; reject pending commands/incomplete training/work. Snapshot selection declared before held-out results.

**Tests (integration, reproducibility, negative/failure, leakage):** `test_all_frozen_tables_and_db_bytes_equal` checks every table/schema/sqlite_sequence/unprojected JSON and DB bytes before/after every subcase and end; deny INSERT/UPDATE/DELETE/DDL, persistent database-changing PRAGMAs, recovery and publication including operational tables. Permit only the read transactions and connection-local busy_timeout save/set/restore needed by existing DecisionSystem._snapshot; assert these cannot alter stored bytes. `test_frozen_history_cutoff_fixed` keeps 200 training rows only; held-out outcomes are never appended. `test_reflect_consolidate_are_assays` preserves selected labels/synthetic effects, suppresses internal action mutation and records exact `driver=frozen_projection_v1`, assay_kind and internal_action_effects; no normal promotion/revision/Q/B7 claim. `test_c_setup_before_freeze` proves missing/stale diagnostics cannot repair or publish.

**Acceptance/failure/recovery:** **G4** complete raw equality, independent of incidental scientific projection. Reader-local objects only; no outcome caches become evidence. Pure diagnostics tagged frozen projection. Attempted write FAILED immediately, preserve source checkpoint and bounded failure evidence; next variant uses a fresh read clone, never repair frozen state.

### Phase G — Existing prequential learning and failure fidelity

#### B10-I12 — Online scheduling, update capture and bounded skipped cycles

**Files:** create `prequential.py`, `tests/evaluation/test_prequential.py`; extend coordinator/adapters. Uses actual cycle, CycleResult, B4 recover/B6 consolidate/B7 update and stored source facts. **Depends:** I07/I08/I09/I10. **Runtime:** E. **Commit:** `feat: drive bounded prequential SEED evaluation`.

**Interfaces:** `PrequentialDriver.run(request: RunRequest, worker: WorkerHandle)->RunResult`; `capture_updates(core, key: EventKey)->CompletedEvidence`. Capture actual completed episode/transition/Q/B4/B5/B6/B7 IDs/stages, not inferred success from a cycle return. Maintenance every 8 completed A/B mutable transitions uses existing owner_requested producer provenance with external declared_maintenance annotation, after scored completion; resource-suppressed opportunities retained. Attention off. Parent records skipped attempts separately and advances declared retry clock by returned observe_interval without real learner sleep.

**Tests (integration, reproducibility, negative/failure, bounds):** `test_online_actual_flow_and_maintenance` ACK before current B5/reward/Q/B1/B4/B7 learning; original pure B3 discrepancy calculation is unchanged, existing equations and exact maintenance opportunities. `test_stale_attempt_is_not_sample` >5 s core age no second perception/current-learning/score row, 8 consecutive skipped ceiling and 2048 total attempts, retry interval preserved; 5.0 s boundary completes. `test_post_ack_failure_preserves_actual_updates` inject Q/persistence/B4/B7/aggregation/index/digest/publication failure; already-acknowledged cycle finishes where safe, no next cycle, actual stages confirmed/unconfirmed, INCOMPLETE; invalid produced inventory FAILED/SCIENTIFIC_REPORT_INVALID. Producer swallowed exceptions detected by actual return/state evidence, not swallowed as success.

**Acceptance/failure/recovery:** no rollback/replay/relearning on ambiguous updates. Core skipped state is nonfatal; evaluator limits yield explicit prefix. Close/capture before next dispatch, preserve learner snapshot/checkpoint journal in evaluator evidence; never claim whole-cycle atomicity.

#### B10-I13 — Independent adapter equivalence and critical STOP gate

**Interfaces:** consume CaptureSession, ScoreJournal, FrozenWorker, PrequentialDriver and original SeedOrganism from I09–I12. Test-owned parity/failure reports expose exact source tables, journal tuples, update-stage confirmation and comparison differences; `docs/evaluation/engineering-gates.md` records the independent review result. No new execution or cognition interface is produced.

**Files:** create `tests/evaluation/test_adapter_equivalence.py`, `test_failure_fidelity.py`; documentation `docs/evaluation/engineering-gates.md`. No new producer algorithm. **Depends:** I10/I11/I12. **Runtime:** V (test-owned workers). **Commit:** `test: prove B10 adapter parity and failure ordering`.

**Tests (integration, reproducibility, leakage/security, negative):** `test_adapter_matches_original_cycle` original trusted cycle versus adapted cycle under identical controlled state/settings/RNG/perceptions/logical stages; compare all tables/IDs/raw payloads/Q/reward/tie choices/action effects/B4/B6/B7, apart from explicitly incidental PID/storage geometry, which are separately source-audited. Use external spies for original time stages; never compare to a reimplemented algorithm. `test_every_failure_stage_is_accounted` no ACK and ACK crash ladder, including transaction commit then failed capture, producer catches and cleanup failure; journal tuple and update evidence agree, no automatic retry. `test_normal_control_has_no_evaluation_dependency` original process behavior untouched.

**Acceptance/failure/recovery:** independent code review verifies G1–G4 and adapter fidelity before scientific interpretation. If a mismatch requires changing core cognition/schema/ordering, **STOP — DESIGN AMENDMENT REQUIRED**; do not fix predictor/reward to satisfy experiment. Roll back protocol PR or repair evaluator-only defect with a new regression, retaining original evidence/versions.

### Phase H — Four registered synthetic families

#### B10-I14 — Stationary A and rest-only shift B

**Files:** create `scenarios/stationary.py`, `shift.py`, `tests/evaluation/test_scenarios_ab.py`; extend registry.py. Uses private engine/client boundary and existing policy. **Depends:** I08/I11/I12/I13. **Runtime:** E. **Commit:** `feat: register B10 action-conditioned scenarios`.

**Interfaces:** fixed `stationary-action-v2` and `rest-shift-v2` engines with public observation/action submission and private truth references. A load effects observe 0/rest -0.10/reflect +0.10/consolidate+.05; battery-.25 pp/disk-.05 pp/network true. Common reset battery 80/uncharged/load.5/disk 50/network false/hour 12 each trial, explicit reset event. B changes only rest to+.05 at hidden 321. No forced action/seed replacement.

**Tests (unit, integration, leakage, reproducibility):** `test_a_distinct_action_guard` invalid identical target coefficients; outcome from.5 `[.50,.40,.60,.55]`; `test_b_only_rest_changes_at321` other rules unchanged, no worker regime label. `test_phase_lengths_and_exposure` Aonline 400/A frozen 320+80, B online 800, first post shift rest/prechange rest candidate evidence captured without selection intervention, exact registered windows; missing exposure remains unavailable. Coefficients/scenario versions private and fixed.

**Acceptance/failure/recovery:** literal scenario engine fixtures, not scientific positive assertions. Retain unsupported action coverage/fallbacks; scenario bug needs new version/explanation and fresh run, no edited historical artifacts or core tuning.

#### B10-I15 — C producer fixtures and four immutable variants

**Files:** create `scenarios/evidence.py`, `fixtures.py`, `tests/evaluation/test_scenario_c.py`. Uses permitted transition producer APIs/B4/B6/B7 before freeze. **Depends:** I06/I11/I13. **Runtime:** E. **Commit:** `feat: construct B10 evidence robustness fixtures`.

**Interfaces:** `build_fixture(fixture_id: str, owned: OwnedState)->OwnedState`; C conflict 128 declared producer transitions (+.10 load 64 then-.10 load 64) repeating action catalog, tagged producer_fixture_v1; no forged B8 record. C bundle cold/conflict/unavailable/stale each 16 probes, independent snapshots and read time; cold fresh without publication, stale last-evidence+301 s. Source-unavailable keeps source row ID, invalidates declared typed payload **before freeze**, then existing consolidation; records fixture edit digest/provenance.

**Tests (integration, leakage, negative, reproducibility):** `test_c_variant_initial_provenance` actual source/history IDs and unchanged clone digest where appropriate; `test_unavailable_keeps_candidate_source` row retained, producer emits source_unavailable; `test_all_c_mutations_precede_freeze` immutable probe/rawstate equality and no promotion/new publication claims. Missing load/disk omitted, battery/network nullable, no nonfinite cycle input.

**Acceptance/failure/recovery:** fixture mutations are robustness setup only, not measured cognition. Snapshot aggregate<=128 MiB/four 32 MiB, fixture-generating 128 counted. Preserve original fixtures; replace defect by new named version, not correction during probe.

#### B10-I16 — D contexts and separately cloned eligible-random policy

**Files:** create `scenarios/constrained.py`, `tests/evaluation/test_scenario_d.py`; extend baselines.py and coordinator role dispatch. Uses unchanged constraints/B8 epsilon/legacy Q. **Depends:** I06/I12/I13. **Runtime:** E. **Commit:** `feat: register constrained B10 policy comparisons`.

**Interfaces:** D 128 per trajectory, eight ordered contexts normal/load.9/battery 15 uncharged/disk 5/battery null/charging null/load omitted/disk omitted; cloned equal initial state, keyed exogenous stream, separate RNG. Random counterpart epsilon 1.0, alpha.18 via existing settings before measured dispatch, certified exploration records. Synthetic effects follow spec 10, omitted fields preserved.

**Tests (unit, integration, leakage, reproducibility):** `test_d_guards_and_boundaries` equality.8/20/10 eligible, just-over/under/missing restricted, observe/rest always eligible; constraints/eligibility violation count 0. `test_random_eligible_real_records` separate same-start trajectory/valid random choice, no forged exploitation/tie record. `test_task_utility_is_external` normal 1/.75/.5/.25 and constrained rest 1/observe.25/others 0 never enter reward/Q; actual trajectories/outcomes differ and cannot be paired prediction samples.

**Acceptance/failure/recovery:** guard violation fails engineering gate with evidence, utility cannot excuse it. Null/mixed policy difference accepted. Revert evaluator defect; do not rebalance actions or change B8 weights/eligibility.

### Phase I — Fair baselines and literal metrics

#### B10-I17 — Same-cutoff prediction baseline forecasts

**Files:** create/extend `baselines.py`, `tests/evaluation/test_baselines.py`. Uses captured raw 200 rows/validity semantics independently of truth and cutoff. **Depends:** I10/I14/I16. **Runtime:** E. **Commit:** `feat: add matched B10 prediction baselines`.

**Interfaces:** `forecast_baselines(observation: Observation, action: Action, history: tuple[Json,...], cutoff: int | None)->Json`; at most persistence and global-history mean-delta/frequency; global requires 2 usable, otherwise persistence, Boolean probability only genuine frequency. Independent filters/clamps characterize B2 inputs without calling action-conditioned B2 to manufacture a baseline.

**Tests (unit, integration, negative, leakage):** `test_four_row_matched_fixture`: two rest -0.1/two reflect +0.1, current 0.5, target 0.4 yields persistence/global 0.5 errors 0.1/0.1, actual B2 rest 0.4, error 0, supports global 4/rest 2; one target not a 5-sample window. `test_raw200_corruption_no_refill` current target/future rows excluded, same raw cutoff/order/filters; available IDs/digests retained. `test_boolean_probability_and_fallback` persistence classification only, frequency>=2; no confidence probability. Poison private truth/boundary imports.

**Acceptance/failure/recovery:** deferred baseline scoring uses captured **prior** cutoff despite later DB growth. Invalid bounds fail explicit, honest missing retained. Revert baseline commit/new metric version on semantic correction, never use future samples or reinterpret old output silently.

#### B10-I18 — Numeric/Boolean populations, coverage and rest adaptation

**Files:** create `metrics/{__init__,registry,prediction}.py`, `tests/evaluation/test_prediction_metrics.py`, `test_adaptation.py`. **Depends:** I02/I14/I17. **Runtime:** E. **Commit:** `feat: measure B10 prediction populations faithfully`.

**Interfaces:** `measure_prediction(metric_id: str, evidence: tuple[CompletedEvidence,...], population: Population, plan: FrozenPlan)->Measurement`; ordered fsum formulas; versioned registry 33 IDs, adaptation-delay v2. Paired intersections and per-method coverage/cross-tabs, action strata/method support/qualifying action set/window dimensions fixed by plan.

**Tests (unit, negative, reproducibility, bounds):** `test_literal_metrics_and_support` MAE fsum/n, percentage normalization 100/load 1, unclipped, Brier 0.5625, confidence-only unavailable, zero opportunities null; high support wrong prediction remains wrong. `test_paired_windows_and_standardization` five each action both windows, equal weight fixed qualifying C and action mix weighted overall reported separately; missing/changed C incompatible, exclusion cross-tab reconciles. `test_rest_window_and_lifetime_literals` B2 k 0/10/20 errors.15/.075/0; actual raw 200 eviction by other actions and current excluded. `test_adaptation_exposure_rules` pre 321 rest candidate action_mean>=2 mandatory, exposure windows 5/three consecutive MAE<=.02, fallback breaks qualification without removing exposure index; insufficient prechange/qualification unavailable vs eligible-but-never passing not_observed/right censored actual rest exposure/global 480. Fixed A1–40/361–400/B281–320/321–360/761–800; no imputed action.

**Acceptance/failure/recovery:** **G5** literal metric/baseline correctness also requires I19/I20. Point B3 diagnostics separately labeled; thresholds frozen with roles, not post-hoc scientific PASS. Semantic calculation bug fixes evaluator and versions, no SEED tuning.

#### B10-I19 — Independent B4–B8 evidence audits and source fidelity

**Files:** create `metrics/producers.py`, `tests/evaluation/test_producer_metrics.py`. Uses captured actual source snapshots and existing pure structural validators only; no producer updates during measurement/replay. **Depends:** I10/I12/I15/I16/I18. **Runtime:** E. **Commit:** `feat: audit B10 producer evidence without tuning cognition`.

**Interfaces:** `measure_producers(evidence: tuple[CompletedEvidence,...], sources: Json, plan: FrozenPlan)->tuple[Measurement,...]`; source cutoffs/limits/build and read times retained. No reimplementation of learning algorithms; independent reference checks characterize published facts.

**Tests (unit, integration, negative):** `test_world_lifetime_and_contradictions` n 0=20, q=20/40/60→-.025/0/+.0125; prior>=4 and epsilon battery 0.05/load.02/disk.01, Boolean prior.75/.25; scoped lifetime separate from window adaptation/global mixture. `test_curiosity_literal_and_missing` error 0.2, coverage 1, uncertainty 1, novelty 1→.2, novelty 0→.1; shift load loss.15/four valid signals→B3 aggregate 0.0375, not fixed peak. `test_semantic_opportunities_and_provenance` actual 8/.30 support, resource/cursor/source fingerprint/history/next eligible consolidation, no opportunity unavailable, frozen NOT_EVALUATED. `test_self_claims_are_source_checked` bounded/capped counts/storage/PID/freshness/unsupported producer claim measured negative retained, evaluator fabrication 0. `test_decision_links_q_and_guards` structural original digest/provenance/ties/skips/Q compatibility and zero mandatory constraint violations; no observer reranking.

**Acceptance/failure/recovery:** every supported evaluator claim links source facts; weak actual B7 claim is disclosed not repaired. B4 no forgetting, B6 history, B7 semantics, B8 weights remain. Missing denominator null, no cap-as-total. Correct evaluator only; serious producer weakness reported for later separately authorized batch.

### Phase J — Frozen AnalysisPlan enforcement and complete reporting

#### B10-I20 — Registered inventory, findings and suite reconciliation

**Files:** create `metrics/findings.py`, `tests/evaluation/test_reporting.py`; extend analysis/specs/registry. **Depends:** I02/I18/I19. **Runtime:** E. **Commit:** `feat: reconcile preregistered B10 scientific outputs`.

**Interfaces:** `reconcile_output(plan: FrozenPlan, measurements: tuple[Measurement,...], findings: tuple[QuestionFinding,...])->VerificationReport`; `classify_questions(plan, measurements, execution_status)->tuple[QuestionFinding,...]`; checked-in default plan factory expands all 33 IDs per member with declared dimensions/per-run/suite inventories and applicability before dispatch. Adaptation only B/task utility only D; frozen mutation metrics preregistered NOT_EVALUATED. No arbitrary expressions.

**Tests (unit, integration, negative, bounds):** `test_all_registered_measurements_accounted` omission/duplicate/version dimension mismatch/unregistered primary fails FAILED/SCIENTIFIC_REPORT_INVALID; every sparse/unfavorable/inapplicable metric present with reason. `test_execution_and_findings_independent` COMPLETED with fixture POSITIVE/MIXED/NEGATIVE/INCONCLUSIVE per exhaustive frozen rules; default descriptive NOT_EVALUATED, missing UNAVAILABLE never zero or automatic negative; FAILED/INCOMPLETE prefix questions INCONCLUSIVE, INVALID no execution NOT_EVALUATED. `test_exploratory_never_replaces_primary` separate EXPLORATORY_DIAGNOSTIC/non-inferential inventory. `test_suite_counts_failed_seeds` every planned member/pair visible, incomplete excluded from complete aggregate; sample weighted/per run mean/median/min/max/planned valid counts separate. Inventory/control file exact size admission, no favorable filter.

**Acceptance/failure/recovery:** freeze and output identify same immutable plan. No post-hoc threshold/classification. Failed report retains actual learning/checkpoints and expected inventory, no retry; corrected scientific rules require new version/digest/fresh run.

### Phase K — Bounded immutable artifact system

#### B10-I21 — Lossless payload assembly, update joins and prepublished indexes

**Files:** create `artifacts.py`, `indexes.py`, `tests/evaluation/test_artifacts.py`; extend limits/coordinator. **Depends:** I09/I11/I12/I20. **Runtime:** E. **Commit:** `feat: assemble bounded B10 complete and partial evidence`.

**Interfaces:** `assemble_payload(result: RunResult, plan: FrozenPlan, capability: RootCapability)->Payload`; `build_indexes(payload: Payload)->Json`; fixed section 14 manifest/analysis-plan/preupdate/events/metrics/truth/checkpoints/chunks/index/operations inventory. Online events reference journal tuple/digest, preserve original B1 outcome/B8 candidate+selection/B3/B5/Q/B4/B6/B7 facts without duplicate raw prediction/outcome. Combined detail cap 64 KiB across both files; training and probes counted losslessly. Index publishes exact bins<=200 points/4 series, cursor offsets and counts; UI bins not scientific authority.

**Tests (integration, negative/failure, bounds):** `test_journal_reused_and_detail_reconciled`1024 details 64 MiB total, attempts separate<=512 B/1 MiB shared control cap; no lost training/partial update; ambiguous updates unconfirmed. `test_bound_every_file_and_snapshot` caps section 8 before encode/write, plan 128 KiB/metrics 256 KiB/index 128 KiB, snapshots aggregate 128 MiB, <=32 files/224 MiB; no silent essential truncation. `test_post_ack_detail_failure_preserves_state` INCOMPLETE actual learning durable journal retained, no next cycle/retry. `test_partial_inventory_preserved` status reason/phase/counters/all planned measurements, no complete comparison.

**Acceptance/failure/recovery:** payload still partial until science/integrity validation I22/I23; no completed publication yet. No copies of full artifact/journal; no report learner ingestion. Retain crash prefix; incidental oversized operational prose may fixed code+omitted bytes only. No lossless record fit means STOP/incomplete; never raise cap.

#### B10-I22 — Scientific projection and complete state identity

**Files:** create `science.py`, `tests/evaluation/test_science.py`; extend canonical.py. **Depends:** I02/I06/I21. **Runtime:** E. **Commit:** `feat: hash canonical B10 scientific evidence`.

**Interfaces:** `project_state(snapshot: OwnedState)->Json`; `iter_science(payload: Payload)->iterator[bytes]`; `science_digest(payload)->str`; typed b10_science_v1 joins stored tuples (no cognition), includes complete plan/source/profile/initial state/streams/evidence/measurements/findings/terminal codes.

**Tests (unit, integration, reproducibility, negative/bounds):** `test_all_tables_and_sequences_in_science` sorted table name/PK or full canonical row/multiplicity/columns/schema/JSON typed; <=64 tables/100000 rows; unknown producer schema fails compatibility. `test_exact_incidental_projection` only spec 15 exclusions PID/storage geometry/root/run ID/real execution time/log prose/offset cache; logical clocks/provenance/settings/Q/errors/plan/freeze assertion preserved, raw fidelity checked separately. `test_science_digest_cases` changed outcome/plan/event order changes; changed incidental run ID/time/storage geometry same science; int/float/±0 distinctions and UTF8 producer string tag/depth/string/integer bounds. Outer 2048 attempts+1024 joined transitions streaming, not doubled pre/post array.

**Acceptance/failure/recovery:** domain `SEED_B10_SCIENCE_V1\0`, exact typed encoding, no digest circularity. Raw checkpoint remains intact; frozen raw equality stricter than projection. Unknown scientific field cannot be silently dropped; requires new projection version/amendment if substantive. Preserve old science, never overwrite historic identity.

#### B10-I23 — Whole-byte receipt, chunk hashes and atomic publication

**Files:** create `integrity.py`, `tests/evaluation/test_integrity.py`; extend artifacts.py. **Depends:** I03/I21/I22. **Runtime:** E. **Commit:** `feat: verify and atomically publish B10 artifacts`.

**Interfaces:** `integrity_digest(payload: Payload)->str`; `make_receipt(payload)->Receipt`; `publish(payload, receipt, capability)->RunArtifact`; fixed ASCII filename order/u64 big endian length framing/domain `SEED_B10_ARTIFACT_V1\0`/complete exact bytes. Detached receipt<=16 KiB outside payload, chunks 64 KiB arrays<=512 KiB excludes itself/own hash in receipt; all files accounted. fsync/files/directory, atomic same-filesystem rename, final receipt and bounded root index. Root index exposure only after validated publish/receipt; orphan crash states preserved/quarantined as partial, never complete without receipt.

**Tests (unit, integration, security, reproducibility, negative/failure):** `test_integrity_distinct_from_science` real timestamps/raw whitespace change integrity, scientific outcome changes both. `test_inventory_attack_and_replacement` missing/extra/changed length/symlink/path swap/rewritten index fail trusted receipt validation; receipt+payload rewrite authenticity limit disclosed. `test_atomic_publish_crash_ladder` crash each fsync/rename/receipt/index boundary no half complete artifact advertised; immutable completed data cannot overwrite. Entire payload incremental verification and strict size/reservation margins.

**Acceptance/failure/recovery:** **G6** publishable evidence integrity, no signed authenticity claim. Rename not full copy; partials count retention. Failed publication after ACK INCOMPLETE/no rollback learning; receipt/report contract failure FAILED as appropriate; old valid artifact preserved, new run identity for corrections.

### Phase L — Recorded replay and fresh deterministic re-execution

#### B10-I24 — Dedicated bounded artifact reader and no-cognition replay

**Files:** create `reader.py`, `replay.py`, `tests/evaluation/test_reader.py`, `test_replay.py`. Uses pure structural B8 validation/digest only, no executor/scorer imports. **Depends:** I21/I22/I23. **Runtime:** E read-only. **Commit:** `feat: replay validated B10 recorded evidence`.

**Interfaces:** `EvaluationReader(capability: RootCapability).runs(cursor: str | None,limit=20)->ReplayPage`; `.detail(run_id)->RunDetail`, `.measurements/.events(cursor,limit)->ReplayPage`, `.event(run_id,key: EventKey)->Event`, `.curve(run_id,metric,series)->Curve`, `.chunk(run_id,file_id,chunk)->bytes`; `Replay.page(...)` joins stored journal/post records without executing historical cognition. Optional snapshots queried mode=ro/query_only/write authorizer/100000 VM steps.

**Tests (integration, leakage/security, negative, bounds):** `test_replay_never_calls_cognition` poison Predictor/DecisionSystem/WorldModel/Consolidator/SelfModel and metrics recomputation, validates stored original B8 digest/plan/inventory/receipt. `test_chunk_scope_and_budget` metadata included 1 MiB/2 s budget, detail<=912 KiB metadata without index/full plan, per requested chunk digest and fingerprint inode/length/mtime/ctime invalidate; whole verification incremental outside request, scopes verification_pending/chunk_verified/whole_payload_verified_at_publication with freshness. `test_lossless_paging_with_reused_ordinals` EventKey exact, 20 maximum/earlier byte budget with next cursor, no row drop/refill. Malformed old schema/unsafe absent root errors no repair/migration.

**Acceptance/failure/recovery:** missing evaluator root unavailable, missing learner cannot fallback. Manifest filenames fixed file IDs; opaque version cursor<=512 B data only, no SQL/path interpretation. Full plan inspection separate chunk requests. Reader errors isolated, no artifact mutation, preserve suspect bytes for owner review.

#### B10-I25 — Trusted CLI re-execution and compatible scientific comparison

**Files:** create `reexecution.py`, `cli.py`, `__main__.py`, `tests/evaluation/test_reexecution.py`, `test_cli.py`, `test_comparison.py`. **Depends:** I05/I07/I13/I20/I23/I24. **Runtime:** E. **Commit:** `feat: reexecute trusted B10 runs with bounded divergence`.

**Interfaces:** `reexecute(reader: EvaluationReader, run_id: str, profile: Profile)->ReexecutionResult`; `compare(left: RunDetail,right: RunDetail,metric_id: str)->Json`; explicit `python -m development.evaluation validate|run|suite|verify|replay|reexecute` trusted verbs, registered ID/version/run ID selectors only, fixed root enable/disable, no supplied path/code/checkout/install. Run/suite and actual empirical re-execution dispatch disabled unless engineering gate receipts/config are valid and I30 is merged, independently reviewed, exact-master CI verified and closure recorded; a separate later explicit B10 EMPIRICAL EVALUATION EXECUTION instruction is still required. Technical fixtures exercise dispatch contracts without granting scientific execution authority.

**Tests (integration, reproducibility, negative/security, bounds):** `test_same_profile_science_matches` fresh owned run/original immutable plan/checkpoint inputs/source/profile →equal canonical digest, new storage ID/receipt, old bytes unchanged. `test_incompatible_reexecution_refused` source/lock/profile/rules/fixture/producer version fail INCOMPATIBLE_REEXECUTION, no tool install. `test_bounded_earliest_divergence` phase/ordinal/field/expected actual, max 100 differences/64 KiB; incomplete pair not exact equality. `test_compatibility_more_than_plan_digest` same plan but changed protocol/population/actionC/window/metric/source/profile/baseline/rule/fixture blocked automatic equivalent/improved/worse; descriptive no rule cannot invent scientific classification. CLI re-execution one bounded run, no recursive/repeated retry.

**Acceptance/failure/recovery:** artifact replay distinct from fresh execution; no artifact imports/executable payload. Original immutable; failed new run retained partial, all caps including retention enforced. Default 30 suite plus reexecutions cannot expand beyond 32; split separately admitted verification suites after budget/root checks, not exemption.

### Phase M — Optional Astra Evaluation backend

#### B10-I26 — Read-only optional service and exact routes

**Files:** create `dashboard/services/evaluation.py`, `dashboard/api/evaluation.py`, `tests/dashboard/test_evaluation.py`; modify `dashboard/app.py`, `dashboard/__main__.py` only for explicit evaluation enable and optional router load. No change to SeedService cognition/organism root. **Depends:** I24/I25 stable reader. **Runtime:** O. **Commit:** `feat: expose bounded observer-only B10 artifacts`.

**Interfaces:** `EvaluationService(reader: EvaluationReader | None)` delegates read-only reader; `evaluation_router(service)->APIRouter(prefix='/api/evaluation')`. Exact GET routes: `/runs`, `/runs/{run_id}`, `/runs/{run_id}/measurements`, `/runs/{run_id}/events`, `/runs/{run_id}/events/{event_key}`, `/runs/{run_id}/curve`, `/compare`, `/runs/{run_id}/files/{file_id}`; query/cursor/tuple allowlists and file chunk integer. Scientific finding details in measurement/detail responses; replay through event pages, no new execution/re-execution verbs. Snapshot chunks application/octet-stream attachment; JSON/text escaped/nosniff/CSP existing security preserved.

**Tests (integration, dashboard, leakage/security, negative, bounds):** `test_get_only_even_operator` mutation methods unavailable even with valid operator CSRF, no run/re-execute endpoints; Host/Origin/CSP checks unchanged. `test_optional_reader_absence_and_no_home_fallback` disabled/missing evaluation package/root preserves ordinary app/views, separate capability cannot stand in for learner DB. `test_all_route_bounds` run ID32 hex/event tuple/cursor 512 B/lossless signed 64 source IDs/page 20/scan 60/read+response 1 MiB/2 s/compare 2/points 200 x 4/VM100000. Detail limit 912 KiB metadata, plan chunks separate; corruption fixed typed error not empty-success. No request time scoring/full payload scan.

**Acceptance/failure/recovery:** optional import only of dedicated reader, not coordinator/scenarios/metrics; disabled stub no import dependency. Existing observer/operator behavior regressions pass. Revert router integration to remove Evaluation; immutable artifacts remain development-owned, no core state touched.

### Phase N — Bounded Astra Evaluation UI

#### B10-I27 — Evaluation client, opaque routes and cancellation

**Files:** create `dashboard/static/evaluation_support.js`, `tests/dashboard/test_evaluation_assets.py`; modify `dashboard/static/{api,evidence,app}.js`. **Depends:** I26. **Runtime:** O. **Commit:** `feat: add bounded Astra Evaluation navigation`.

**Interfaces:** bounded Evaluation JSON client with 2 s deadline/1 MiB stream cap/1024 B error cap, chunk client 64 KiB binary no execute; reuse parseEvidence lossless integer handling and el/textContent. `parseEvaluationRoute(hash)->{params,invalid}` strict 32 hex run IDs/opaque 512 B cursor/registered metric/tuple; render generation AbortController isolation, separate opaque page history. Add Evaluation to ASTRA/sections/dynamic views, no implied SEED status read or background polling. Existing evidence limits/routes/client 10 s timeout for other views unchanged.

**Tests (dashboard/Node, negative/security, bounds):** `test_evaluation_routes_and_lossless_ids` values 9007199254740993/MAX signed 64 exact strings through response/link/paging, numeric looking scientific IDs not coerced, cursor not numeric ID; invalid duplicate query/byte over/tuple rejected. `test_evaluation_client_cancel_and_timeout` slow responses/canceled navigation old generation cannot modify DOM/error/connection, 2 s deadline cleanup/stream oversize/corrupt UTF8 rejects. Existing Astra asset/regression routes intact.

**Acceptance/failure/recovery:** navigation/manual Refresh only; no mutate/eventsource/poll/local storage artifact. Public bounded copy-only view failure independent. Revert client/navigation commit, retains other dashboard views unchanged.

#### B10-I28 — Stored measurements, findings, comparison and replay view

**Files:** create `dashboard/static/views/evaluation.js`; extend test_evaluation_assets.py; modify styles.css only for needed accessible Evaluation layout. **Depends:** I27. **Runtime:** O. **Commit:** `feat: render separate B10 execution and scientific findings`.

**Interfaces:** `renderEvaluation(root,signal)->cleanup`; paged run/measurement/events, detail, precomputed curves, fixed inventory chunk inspection, stored comparison and replay. Prominent **Execution** and **Scientific findings** headings; experiment/version/protocol/driver/source/plan version digest/seed/training counts/denominator/coverage/baseline/exclusions/limitations/integrity scope. Frozen labels, partial/unavailable/no-classification and EXPLORATORY_DIAGNOSTIC visible. No universal green PASS/reranking/imputed zero/automatic re-execution.

**Tests (dashboard/Node, negative, bounds):** `test_negative_findings_visible_on_completed_run` complete can contain negative/mixed/inconclusive/NOT_EVALUATED, registered produced unavailable counts and raw links all visible. `test_comparison_blocks_incompatibility` show exact reasons/side by side only, no arbitrary better/worse. `test_evaluation_dom_and_chart_caps`20 table rows/200 points × 4/800 total/1500 DOM/one current detail/two compared runs; lossless next/previous through all inventory, no full artifact download. `test_escaped_hostile_artifact_strings` textContent no innerHTML/eval/HTML execution; loading/no-root/no-runs/integrity error/timeouts distinct.

**Acceptance/failure/recovery:** no model math/history reconstruction; bin start end/ncoverage explicit, no interpolated truth. Keyboard labels/table captions/graph data alternative included. Revert view commit; readers/artifacts/core unaffected.

#### B10-I29 — Disposable browser fixture and actual accessibility verification

**Interfaces:** `build(destination: Path, case: str) -> dict` in tests/dashboard/evaluation_fixture.py accepts only an explicit empty temporary destination and the registered cases below, returning fixture run IDs and metadata for the test server/browser. It consumes I21–I24 publication/reader contracts and I26 create_app integration; it produces no installed-home fallback or experiment API.

**Files:** create `tests/dashboard/evaluation_fixture.py`, `test_evaluation_fixture.py`; extend asset tests; `docs/evaluation/browser-verification.md`. Uses temporary-root pattern/astra_dom.mjs; no browser library dependency. **Depends:** I26/I27/I28. **Runtime:** V/O fixture only. **Commit:** `test: verify Astra Evaluation observer behavior`.

**Tests (dashboard/browser, integration, security, bounds):** `test_fixture_disposable_and_bounded` explicit temp destination only, cases empty/complete-negative/partial/missing integrity/malformed/maximum IDs/incompatible plans/maximum inventory and truth annotations post completion. Actual browser acceptance against disposable fixture home/root: widths 320/760/761/1120/1121/1440, themes/reduced motion, keyboard focus/skip link/menu/Refresh, paging/curve alternatives, late abort/cancellation, two-run compare, fixed file chunks and existing Overview views. Measure network/DOM caps and 2 s client; DOM harness alone does not claim browser acceptance.

**Acceptance/failure/recovery:** evidence records actual unavailable browser checks as unverified; required browser acceptance blocked until completed, never skip and claim green. No installed home/browser live-organism access. Close fixture server/delete owned temp work only; preserve verification report.

### Phase O — Engineering Qualification

I30 alone proves engineering readiness. This phase may run finite technical fixtures to verify both protocols and all families, but must not execute the full registered B10 scientific suite or create actual B10 empirical findings. Engineering qualification and empirical execution have different branches, PRs, authorization gates and milestones.

#### B10-I30 — Engineering release gate and bounded suite inventory tooling

**Files:** create `tests/evaluation/test_suite.py`, `test_engineering_acceptance.py`, `tests/evaluation_scenario.py`, `tests/test_evaluation_scenario.py`; extend cli/coordinator; docs/evaluation/{usage, engineering-gates}.md and canonical tracker/log/README/architecture/verification only with actual future evidence. Optional narrowly reviewed `.github/workflows/seed-ci.yml` addition for B10 technical scenario follows future authorization; current planning changes no workflow. **Depends:** I01–I29 and previous PR exact master gates. **Runtime:** E tooling/technical fixtures, no empirical claim. **Commit:** `test: qualify bounded B10 engineering acceptance`.

**Interfaces:** `verify_suite(plan: FrozenPlan, members: tuple[RunArtifact,...])->VerificationReport` in coordinator.py performs bounded suite reconciliation; `registered_suite(plan: FrozenPlan)->tuple[RunRequest,...]` deterministic 30 members A10/B5/C5 bundles/D10, all seeds 0–4/protocols/variants/planned failed entries; technical standalone scenario uses hand literal fixtures/temp state/failure ladder, distinct from full scientific suite. Acceptance validator maps section 9 all 22 gates, engineering portions only; future experiment run stage not fabricated PASS.

**Tests (integration, reproducibility, negative/failure, bounds):** `test_suite_expansion_and_accounting`30 declared/8 seeds expanding 48 rejected/32 ceiling reexecutions included/limits 120 s 1800 s, all member failures counted. `test_technical_acceptance_matrix` each G1–G6/22 technical row links actual named tests/evidence, existing seven scenarios/baseline bytes retained; no science interpreted before technical review/CI. Test-owned finite fixtures exercise both protocols/all families without tuning/empirical success assertions. The acceptance matrix must leave empirical portions pending, and reject any scientific dispatch permission inferred from implementation authorization alone or an unmerged/unverified I30 head.

**Acceptance/failure/recovery:** I30 belongs only to `seed-0.2-b10-impl-06-release`. Require focused tests → full local suite → standalone technical scenarios → browser verification where applicable → independent engineering review → exact PR CI → merge → exact post-merge master CI → engineering closure record with exact merged SHA/run/jobs. Only then record **B10 ENGINEERING IMPLEMENTATION COMPLETE / VERIFIED**; G1–G6 and required Astra/regression acceptance must pass, with actual counts and no skipped new checks. G7 and positive empirical findings are not prerequisites. At closure **B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED** and **B10 overall IN PROGRESS**. **MANDATORY STOP AFTER I30 ENGINEERING CLOSURE**: no automatic I31, empirical branch, final empirical plan freeze or suite execution. Failed I30 leaves engineering incomplete and prevents empirical work; revert release integration or repair engineering under review, with no installed state/schema impact.

### Phase P — Registered Empirical Evaluation

I31 alone is scientific evaluation execution using the already merged and verified engineering system. It is not implementation development and cannot share I30’s implementation branch or PR.

#### B10-I31 — Full preregistered suite and empirical closure evidence

**Interfaces:** consume `registered_suite`, `freeze_plan`, bounded Coordinator dispatch, `publish`, Replay and `reexecute` from earlier tasks. The I30 `verify_suite(plan: FrozenPlan, members: tuple[RunArtifact,...])->VerificationReport` reconciles every planned member and registered suite measurement. The trusted CLI selects the checked-in default experiment/plan ID `b10-shared-suite`, version 1; it accepts no supplied formula or scenario code. The suite report references immutable member IDs/digests, explicitly accounts for failures, and is charged to existing evaluator control/root budgets. It does not add evaluator data to learner state.

**Files:** future `docs/evaluation/b10-v1-results.md`, compact frozen AnalysisPlan provenance and evidence inventories under docs/evaluation/; canonical tracker/log actual closure only. Full frozen plan, receipt and large artifacts stay in the owned EVALUATION_ROOT outside Git; compact documentation links their versions/digests/inventories. Full 224 MiB artifacts stay ignored, not Git baselines. No cognition/source/tuning changes. **Depends:** I30 engineering PR merged, independent review complete, exact post-merge master CI successful and engineering closure recorded at that exact SHA; G1–G6; a later separate explicit owner **B10 EMPIRICAL EVALUATION EXECUTION** instruction. **Runtime:** E scientific execution, not implementation development. **Commit:** `docs: record preregistered B10 empirical evidence`.

**Procedure/tests (integration, reproducibility, evidence/security, bounds):**

- [ ] Confirm the later explicit empirical-execution authorization and recorded I30 engineering closure. Verify the exact engineering master SHA, independent review, exact post-merge CI run/jobs and clean source; no PR-head substitution.
- [ ] Create `seed-0.2-b10-eval-01-empirical` fresh from that exact verified engineering master. Never start from the planning branch, an earlier implementation branch, unmerged I30 or a PR head lacking post-merge verification. This branch primarily records scientific execution provenance, compact results/inventories and closure documentation.
- [ ] Immediately before execution, verify the exact supported execution profile, generate the final registered AnalysisPlan, calculate its digest and durably freeze the complete body/receipt with frozen-before-execution evidence. Only then dispatch any member, including training. Technical fixture plans from engineering do not substitute for this final empirical freeze; no modified-after-results plan is reused.
- [ ] Execute all 30 approved members: A 10, B 5, C 5 bundles, D 10, seeds `0,1,2,3,4`. No seed replacement/retry/repeat-until-positive; scenario rules, thresholds, metric inventory, eligibility, windows and classification rules remain frozen after execution begins. Account for every planned member and failed/partial entry.
- [ ] Validate complete/partial published inventories, both digests, raw source facts and every registered measurement; replay recorded artifacts without cognition.
- [ ] Fresh same-profile re-execute required compatible complete evidence under separately admitted <=32 run/1800 s cap suites (max one fresh request each, no recursive batch). Preserve originals and bounded earliest-divergence reports; no silent repair/rerun under the same scientific identity.
- [ ] Run existing CLI verification and test_engineering_acceptance validators against actual artifacts; independent scientific evidence review assesses the 22 acceptance criteria’s applicable empirical portions, receipt/hash provenance and frozen-plan linkage. No predetermined positive result; technical fixture PASS cannot replace actual registered evidence.

**Acceptance/failure/recovery:** **G7 — Empirical Evaluation Closure** belongs exclusively to Phase P/I31. Only actual registered work/accounting/evidence/reproducibility/independent scientific review can establish **B10 EMPIRICAL EVALUATION COMPLETE**. Negative/mixed/null/inconclusive findings are valid. Engineering defect, determinism failure, corrupted artifact, incompatible re-execution, resource limit, missing planned member or unexpected evaluator bug must be classified under the frozen plan and preserve actual learning/results/checkpoints/failed/partial evidence with exact denominators. Missing or invalid required evidence prevents closure. **STOP on a technical defect requiring changed evaluation behavior**; correct engineering under a separately reviewed change and create a new experiment/AnalysisPlan version where scientifically required before a separately authorized corrected execution. Never delete inconvenient results, rewrite history, silently repair/rerun under the same identity, raise budgets/select seeds or retune B1–B8. Owner review determines overall B10 completion only after empirical closure; no deployment/installed validation implied.

## 6. Mandatory STOP gates and future branch/PR strategy

Use **seven future branches: six sequential engineering implementation branches and one separate empirical evaluation branch**. Each engineering branch is created later from the newly fetched exact verified master after its predecessor merges. The empirical branch is created only after I30 engineering closure and a later explicit empirical-execution authorization, from the exact master SHA recorded by that closure. Existing B7/B8/B9 and design publication use branch→master with review/exact PR CI/normal merge/separate master CI. Short sequential branches avoid long-lived divergent executor/artifact contracts and make rollback/review practical. Do not create any below today; planning branch is not an implementation branch.

| Future branch / PR | Tasks | Mandatory boundary before next PR |
| --- | --- | --- |
| `seed-0.2-b10-impl-01-foundation` | I01–I08 (A–D) | **G1** dependency/storage and absent-evaluator; **G2** truth/API/storage isolation; deterministic profile/clone/lifecycle literal tests. No scientific measurements. |
| `seed-0.2-b10-impl-02-protocols` | I09–I13 (E–G) | **G3** durable score-before-current-learning/failure fidelity/adapter parity; **G4** frozen raw immutability. Independent ordering review required; no learning claims. |
| `seed-0.2-b10-impl-03-science` | I14–I20 (H–J) | **G5** literal registered scenarios/baselines/metrics/plan inventory/findings. No full scientific suite before artifact gate. |
| `seed-0.2-b10-impl-04-artifacts` | I21–I25 (K–L) | **G6** bounded immutable complete/partial artifacts/two digests/no-cognition replay/same-profile re-execution technical fixtures. CLI scientific dispatch remains authority-gated. |
| `seed-0.2-b10-impl-05-astra` | I26–I29 (M–N) | Optional GET-only reader, all browser/bounds/accessibility tests, core absent-evaluator regression. No execution endpoint. |
| `seed-0.2-b10-impl-06-release` | I30 only (O) | G1–G6, Astra/regressions, independent engineering review, exact PR CI, merge, exact post-merge master CI and engineering closure record. **STOP** with engineering COMPLETE / VERIFIED, empirical NOT STARTED / NOT AUTHORIZED and B10 overall IN PROGRESS. |
| `seed-0.2-b10-eval-01-empirical` — evaluation branch | I31 only (P) | Later explicit **B10 EMPIRICAL EVALUATION EXECUTION** authorization; fresh branch from exact I30 verified engineering master; final empirical freeze before dispatch. **G7** actual registered scientific evidence and independent evidence review; no required positive finding. |

Each engineering commit is one numbered task after red/green/evidence; split a task commit only when independently testable interface unit requires it, preserving IDs/traceability. Never one giant B10 commit. I30 and I31 must have distinct branches and PRs. I31 primarily commits scientific provenance/results/evidence documentation, not new implementation code. Stop downstream at any gate failure; evaluator-only defects need reviewed engineering correction, technical design changes need owner amendment. Publication/merge authority must be established separately from coding; implementation authorization cannot be interpreted as empirical-execution authorization.

### I30 engineering closure and mandatory STOP

The recorded boundary is: **I30 complete → engineering PR merged → exact post-merge master CI successful → engineering closure record → B10 ENGINEERING IMPLEMENTATION COMPLETE / VERIFIED → STOP**. The closure record identifies the merged engineering SHA, independent review and exact CI run/jobs. No I31 automatically follows, no full registered suite begins, and G7 is not an engineering-completion requirement. At this boundary empirical evaluation remains NOT STARTED / NOT AUTHORIZED and B10 overall remains IN PROGRESS.

Only a **new explicit owner B10 EMPIRICAL EVALUATION EXECUTION instruction after engineering closure** unlocks Phase P. Without it, do not freeze the final empirical AnalysisPlan for execution, create the empirical branch, dispatch A–D suite members or produce empirical conclusions. I31 starts from the exact verified engineering master, never the planning branch, an earlier implementation branch, unmerged I30 or an unverified PR head. This authorization boundary supplements G1–G7 without adding a task or a new numbered gate.

### G7 — Empirical Evaluation Closure

G7 is exclusively Phase P/I31 and passes only when all preregistered members are accounted for, registered measurement inventory is complete, required evidence is valid, artifacts validate, replay and required same-profile re-execution succeed, independent scientific evidence review completes, findings remain linked to the frozen AnalysisPlan, and negative/mixed/inconclusive findings are preserved honestly. Missing or invalid required evidence prevents closure. G1–G6 establish technical readiness; G7 establishes empirical completion. No scientific positivity is required.

## 7. Test strategy and acceptance traceability

Task test files/names/assertions above are concrete future verification mechanisms, not files created or tests run today. All phases specify unit/integration/leakage/reproducibility/negative/bounds/browser as relevant. Future commands use existing environment `python -m pytest -q tests/evaluation/<namedfile>.py` (each task files), then `python -m pytest -q`; `.venv/bin/python` may replace python only when using verified locked local venv. Existing standalone commands: `python -m tests.baseline_scenario`, `python -m tests.prediction_error_scenario`, `python -m tests.world_model_scenario`, `python -m tests.curiosity_scenario`, `python -m tests.semantic_scenario`, `python -m tests.self_model_scenario`, `python -m tests.decision_scenario`; each invoked with `python -m` and JSON validated. New technical scenario `python -m tests.evaluation_scenario`, never full science as quick unit check. `python -m pip check`, scoped compile check and whitespace/scope/protected byte checks support engineering verification.

### Engineering verification ladder — I01–I30

Unit tests → focused integration → full local suite → standalone technical scenarios → browser verification where applicable → independent code review → exact PR CI → merge → exact post-merge master CI → B10 engineering closure. **Then STOP after I30.** No registered empirical suite or actual scientific findings belong to this ladder.

### Empirical verification ladder — Phase P/I31 only

After the later explicit owner authorization: verify the exact engineering baseline and clean supported profile → freeze final AnalysisPlan with digest/receipt → execute registered suite → validate complete/partial artifacts → artifact replay → required same-profile deterministic re-execution → independent scientific evidence review → empirical closure. Do not combine the two ladders.

No exact run/job/test count until actually reported. CI existing 3 jobs retained; Python 3.11 scenario-step policy disclosed, new acceptance tests not conditionally skipped. Any CI runtime failure stops engineering merge, not permission to loosen caps or omit acceptance. All 22 criteria’s technical enforcement can be implemented/tested during I01–I30 using declared fixtures; applicable actual empirical validation belongs to Phase P/I31/G7. Engineering completion needs no positive scientific result, and I30 must leave empirical portions pending rather than manufacturing PASS entries.

| Spec 23 gate | Phase / task and responsible module | Concrete test(s) | Evidence artifact | Verification stage |
| --- | --- | --- | --- | --- |
| 1 Identity/no host/no installed/unchanged cognition | A–C I03–I07/I13 profile/bootstrap/state | test_dirty_or_changed_source_rejected; test_bound_clock_and_host_poison; test_adapter_matches_original_cycle | profile/source/lock manifest, isolation/parity report | PR1/PR2 and I30 technical; P/I31 actual identity/parity evidence |
| 2 Truth/no evaluator Q/dependency | A/D I03/I08 paths/channel | test_dependency_direction; test_all_forbidden_dispatch_and_sentinels; test_truth_absent_in_all_learner_state | import graph, leakage/sentinel report | G1/G2 technical; P/I31 actual truth/storage evidence |
| 3 Frozen raw immutability/assay labels | F/H I11/I15 frozen/fixtures | test_all_frozen_tables_and_db_bytes_equal; test_reflect_consolidate_are_assays; test_all_c_mutations_precede_freeze | raw table + DB hashes, snapshot/probe labels | G4 technical; P/I31 frozen A/C actual equality |
| 4 Score before learning/no ACK overload/failure fidelity | E/G I09/I10/I12/I13 checkpoint/adapters | test_fsync_precedes_constant_ack; test_ack_path_calls_no_aggregates; test_every_failure_stage_is_accounted | preupdate journal/fsync ordering/actual update prefix | G3 technical; P/I31 every actual online event |
| 5 All families/protocols/bounds/seed accounting | H/O/P I14–I16/I30/I31 coordinator/suite | test_phase_lengths_and_exposure; test_suite_expansion_and_accounting | suite plan/member inventory/partials | I30 technical inventory; P/I31/G7 actual suite accounting |
| 6 Literal rules/math/exposure/populations/baselines | H/I I14/I17/I18 baselines/prediction metrics | test_four_row_matched_fixture; test_rest_window_and_lifetime_literals; test_adaptation_exposure_rules; test_paired_windows_and_standardization | literal report + paired IDs/exclusions/support/action mix | G5 technical literals; P/I31 actual metrics/populations |
| 7 B4–B8 facts/0 guards/no evaluator fabrication | I I19 producers | test_world_lifetime_and_contradictions; test_curiosity_literal_and_missing; test_semantic_opportunities_and_provenance; test_self_claims_are_source_checked; test_decision_links_q_and_guards | raw sources/fidelity/negative unsupported claims | G5 technical fidelity; P/I31 independent empirical evidence review |
| 8 Two digests/replay/reexecution | K/L I22–I25 science/integrity/replay | test_science_digest_cases; test_integrity_distinct_from_science; test_replay_never_calls_cognition; test_same_profile_science_matches | science hash/receipt/replay/divergence report | G6 technical fixtures; P/I31/G7 actual replay/fresh matches |
| 9 Immutable partial complete/no report ingestion/security | K/L I21/I23/I24 | test_partial_inventory_preserved; test_atomic_publish_crash_ladder; test_inventory_attack_and_replacement | immutable payload/partial reason/inventory | G6 technical publication; P/I31 retained actual runs |
| 10 All limits/prefix/no silent trimming | A/C/G/K–N I03/I06/I12/I21/I24/I26/I28 | test_root_attack_matrix; test_every_commit_enforces_growth; test_stale_attempt_is_not_sample; test_bound_every_file_and_snapshot; test_all_route_bounds; test_evaluation_dom_and_chart_caps | budget/counter/read/DOM reports, prefix terminal | Each engineering PR/I30 bounds; P/I31/G7 actual counters/prefixes |
| 11 Observer/accessibility/no run endpoint | M/N I26–I29 | test_get_only_even_operator; test_negative_findings_visible_on_completed_run; browser matrix I29 | HTTP/Node/browser report | PR5/I30 technical browser acceptance; P/I31 actual stored findings display |
| 12 Existing local hosted tests/scenarios/baselines | O I30 verification docs/workflow | test_technical_acceptance_matrix; full pytest/seven scenarios/protected byte check | local logs/exact PR and master CI reports | Every engineering PR/I30 exact CI closure; deployment separate |
| 13 Durable freeze ordering | A/J I02/I20 analysis | test_freeze_precedes_dispatch | immutable plan/receipt/dispatch ordering | PR1 technical ordering; P/I31 final freeze before every member/training |
| 14 No plan field drift/identity rewrite | A/J I02/I20 | test_every_analysis_field_is_frozen | plan body/digest/change explanation/version | PR1/PR3 technical immutability; P/I31 actual freeze/re-execution |
| 15 Complete exact registered inventory | J/K I20/I21 | test_all_registered_measurements_accounted; test_suite_counts_failed_seeds | metrics/question/member expected produced inventory | PR3/G6 technical inventory; P/I31/G7 complete actual inventory |
| 16 Independent execution/measurement/finding | J/N I20/I28 | test_execution_and_findings_independent; test_negative_findings_visible_on_completed_run | manifest/metrics/findings/UI report | PR3/PR5 technical state fixtures; P/I31 actual independent findings |
| 17 Negative/mixed/inconclusive/missing honesty | I/J/P I18/I20/I31 | test_literal_metrics_and_support; test_execution_and_findings_independent | raw losses/unavailable reasons/descriptive findings | G5 technical missing/negative fixtures; P/I31/G7 actual honest findings |
| 18 Evaluation storage/absent home fail closed | A/D/M I03/I08/I26 | test_no_inherited_home_or_secrets; test_truth_absent_in_all_learner_state; test_optional_reader_absence_and_no_home_fallback | tables/file sentinel/config denial report | G1/G2/PR5 technical isolation; P/I31 actual roots/state evidence |
| 19 Mechanical one way/absent evaluator/optional reader | A/M I03/I26 | test_dependency_direction; test_seed_operates_without_evaluator; test_optional_reader_absence_and_no_home_fallback | import graph/normal cycle/app absence | G1/PR5/I30 technical absent-evaluator regression |
| 20 Complete plan/freeze identity in digests/replay | A/K/L I02/I22/I23/I24 | test_exact_incidental_projection; test_science_digest_cases; test_replay_never_calls_cognition | plan body/science projection/integrity/replay | G6 technical identity; P/I31/G7 actual plan/digest/replay linkage |
| 21 Full compatibility not just plan digest | L/M/N I25/I26/I28 | test_compatibility_more_than_plan_digest; test_comparison_blocks_incompatibility | compatibility dimensions/reasons/side by side UI | PR4/PR5 technical compatibility; P/I31 actual suite aggregates |
| 22 Exploratory not primary/no post hoc promotion | J/N I20/I28 | test_exploratory_never_replaces_primary | separated diagnostic inventory/findings/UI | PR3/PR5 technical separation; P/I31/G7 actual primary/diagnostic inventory |

## 8. Resource enforcement map

All literal ceilings copied from approved spec 13–17; power-of-two KiB/MiB/GiB. One-over tests in listed owner task are mandatory. Pre=admission/before operation; incremental=before allocation/write or per operation; post=after committed transaction as explicitly allowed.

| Approved cap | Enforcement owner / timing / failure |
| --- | --- |
| 1024 completed total, training<=512/measured<=1024/sum<=1024; 1024 lossless details | I02 spec pre/I12 loop incremental/I21 reconcile; C fixture training counts; INCOMPLETE prefix on runtime cap, INVALID on oversized request |
| 2048 attempts, 8 consecutive skips, skipped entry<=512 B (<=1 MiB within control) | I12 loop before attempt/I21 encode; skips never transitions/errors/learning; LIMIT_REACHED |
| <=8 seeds/32 runs including policy/reexecutions; default 30 | I02/I30 expanded inventory pre; reject 8 seeds→48 runs, no exemption for baseline/fresh verification |
| 120 s run/1800 s suite/10 s ACK/5 s cleanup included in suite | I07 parent real clock/I09 ACK before learning/I12 per dispatch; terminates owned worker with INCOMPLETE prefix |
| One active worker, each worker/coordinator 512 MiB accounting | I07 preactive/portable monitor incremental; best-effort physical monitor limits reported, no hard OS promise |
| Logical DB32 MiB; physical DB+WAL+SHM64 MiB/clone; 2 slots/128 MiB workspace | I06 page cap before writer/admission, physical post each commit; <=36 MiB one atomic overshoot charged 92 MiB margin, no start next transaction, stop checkpoint/close LIMIT_REACHED |
| Transition combined journal+events<=64 KiB; 1024<=64 MiB | I09/I21 per record before encoding/write, avoid duplicate raw prediction/outcome; post-ACK over limit INCOMPLETE actual updates preserved |
| Snapshot aggregate 128 MiB (up to four C snapshots of 32 MiB) | I06/I15/I21 pre backup size/after backup before publish, all variants charged; no WAL copy |
| Control/metric/index aggregate 4 MiB, operational 4 MiB | I02 inventory admission/I21 incremental; skipped 1 MiB/plan/receipts/indexes count same budget, no essential pruning |
| Plan/manifest/index each 128 KiB; metrics 256 KiB; chunks 512 KiB; receipt 16 KiB | I02/I21/I23 strict closed before write/read; plan store<=60 referenced 128 KiB plans, every copy charged root/reservations |
| Published<=224 MiB/32 files, uncompressed | I21/I23 before every write/publish inventory; detail 64+snap 128+control 4+operations 4=200 MiB, 24 MiB format margin; no archives |
| Total run reservation 448 MiB | I03 pre/I06/I21 incremental; 224+128+4=356 MiB/92 MiB remaining; rename publication not full duplicate; charge workspace/unpublished/published/diagnostics jointly |
| Owned root 16 GiB/60 retained directories including partials; <=4 stale outside suite included 60 | I03 pre existing bytes+reservations/I23 index bounded; 32 run reserve<=14 GiB plus bounded index; no automatic deletion |
| 2 prediction baselines/4 signals/200 raw rows; one D counterpart | I17 per forecast admission/I16 suite inventory; no expanding history/search |
| Replay/API pages 20/detail 64 KiB/request read+response 1 MiB/2 s; queried snapshot 100000 VM steps | I24/I26 incremental byte/deadline and SQLite progress; next cursor on budget early page, no full raw scan |
| Run index scan<=60/index 128 KiB; compare<=2 runs | I24/I26 bounded fixed index/compatibility pre; no arbitrary filesystem scan |
| Detail load 16+512+128+256=912 KiB metadata | I24/I26 receipt/chunks/manifest/metrics only; no event index/full plan in this request; plan separate 64 KiB chunks with metadata in 1 MiB budget |
| Re-execution one fresh bounded request; <=100 divergences/64 KiB report | I25 pre identity/capacity/current limits/incremental diff; not recursive retry, no full suite exemption |
| Chart 200 points/series, 4 series; UI 800 points/20 rows/1500 DOM/1 detail/2 compare | I21 pre published exact bins/I26 server/I28 before DOM; raw records paged losslessly, no UI cap shortens science |
| Messages 64 KiB/depth 16/4096 entries; strings 4096 B; closed science int[-2**256, 2**256-1] | I01/I08 before decode/send, producer stricter limits retained; I22 streaming outer 2048 attempts+1024 joined transitions and logical 64 tables/100000 rows |

## 9. Schema, dependencies, security and risk register

**Schema decision:** organism schema stays **v7**, with no migration/new evaluator table and no changes to seed/migrations.py. Evaluation schemas (`b10_experiment_v1`, `b10_analysis_plan_v1`, `b10_preupdate_checkpoint_v1`, `b10_artifact_v1`, `b10_science_v1`) are evaluator-owned versioned files outside learner storage. Any need for organism schema change is **BLOCKER — DESIGN AMENDMENT REQUIRED**, not planned scope.

**Dependency decision:** no new dependency needed by audit. Standard library sqlite3/hashlib/json/dataclasses/multiprocessing/unittest.mock/pathlib/os/stat/time/random/uuid/math provide planned mechanisms; existing FastAPI/Starlette/client pytest and vanilla JS suffice. Reuse Node DOM harness and actual browser tools rather than adding Playwright. requirements files/lock unchanged. Later discovery of need requires owner approval, alternatives/supply-chain analysis, and scope update before adding anything.

Security is implemented in I01/I03/I05/I07/I08/I21/I23/I24/I26/I27/I28, not postponed: strict schemas/no arbitrary import, no-follow descriptor root ownership/type/identity, artifact counts/byte bounds, credential environment allowlist, no host fallback/inherited SEED_HOME, private fixed errors, GET-only/CSP/escaping, no executable artifact/browser launch. Worker capability and storage checks protect trusted code from accidental leakage, stale/foreign capabilities, unsafe pre-existing paths and incorrect routing. Application-managed ordinary files retain descriptor/no-follow protection; standard sqlite3 native opens use pre/post/ongoing/backup validation and terminal detected mismatch handling. Adversarial concurrent same-UID mutation specifically during the native DB/WAL/journal/SHM open interval is excluded; no prevention claim is permitted. B10 v1 does not adopt a custom/native VFS solely for that excluded threat: native ABI/lifecycle and Python 3.11/3.13 Linux/macOS qualification materially expand scope. Hostile filesystem sandboxing, capability-aware native SQLite VFS, signed authenticity and OS sandboxing/containers solely for hostile evaluator-code defense remain DEFERRED, not hidden prerequisites. Native mechanisms are not claimed impossible. Receipt+payload rewrite can forge a matching pair; show verified_against_receipt, never authentic/tamper-proof.

| Risk | Likelihood / impact | Detection | Mitigation / owner phase |
| --- | --- | --- | --- |
| Evaluator truth leakage | Medium / critical | import graph/closed operations/sentinel all tables files | separate process/public launch/constant ACK A/D |
| Installed home accident | Low / critical | poison inherited home/foreign capability tests | fixed owned root/no installed default A/C |
| Altered B1–B8 behavior | Medium / high | original-cycle parity/existing regressions | no seed edits; amendment stop G |
| Adapter not normal cycle equivalent | High / high | all table/Q/action stage comparison | delegate original functions/independent review E/G |
| Clock/RNG/UUID contamination | Medium / high | host poison/default bound clock/stream tests | pre-import spawn bootstrap/named streams B |
| Frozen mutation | Medium / critical | authorizer/raw all tables+DB bytes | minimal read facade/no constructors/actions F |
| Score after learning | Medium / critical | fsync ACK trace/current update failures | exact B3 wrapper/minimal parent journal E/G |
| Double learning/ambiguous partial commit | Medium / critical | crash ladder/actual update capture | no retry/resume/rollback; incomplete prefix G |
| Baseline asymmetry | Medium / high | cutoff/validity/paired IDs/exclusion tests | same history inputs/separate trajectories I |
| Metric implementation error | Medium / high | hand literal numeric/Boolean/B windows | fsum/versioned formulas/independent math review I |
| AnalysisPlan drift/post hoc threshold | Medium / critical | every field mutation/digest/freeze order | immutable plan/new version and fresh run A/J |
| Incomplete classified complete/positive | Medium / high | report/member inventory/state fixtures | independent states/prefix rules J/K |
| Artifact corruption/receipt replacement | Medium / high | inventory/chunks/fingerprint/crash ladder | exact bytes/detached receipt/scope limits K/L |
| Unsafe application paths / observable SQLite mismatch | Medium / critical | ordinary-file descriptor/path-swap tests; SQLite existing-path/pre-post/sidecar/capability tests | descriptor-relative/no-follow for B10-managed files; amended SQLite validation/terminal failure A/C/K/L |
| Hostile concurrent same-UID SQLite native-open race | Explicitly outside B10 v1 guarantee | disclose limitation; no prevention test/claim substituted for detection | native VFS/hostile filesystem sandbox qualification DEFERRED; no trusted-code path/truth exception |
| Cross run state leakage | Medium / high | mutate one clone/stream/cursor/home | fresh spawn/consistent backup/complete initial identity C |
| Digest mismatch/incidental over exclusion | High / high | typed float/all table/raw vs projection fixtures | versioned exact projection/separate fidelity K/L |
| Replay recomputes cognition | Low / critical | poison all producer/scorer calls | reader-only stored join/import graph L |
| Dashboard overclaims | Medium / high | complete-negative/unsupported/descriptive UI tests | separate headings/coverage/limits/compatibility M/N |
| CI/runtime explosion | Medium / medium | per PR duration/technical budget tests | small focused fixtures/full science separate, bounds not raised O |
| Excessive artifact growth | Medium / high | byte/reservation/DB commit caps | lossless or incomplete, no automatic deletion A/C/K |
| Sparse unforced rest exposure | High / medium | support/action mix/exposure inventory | honestly unavailable/censored; never force policy H/I |
| Per transaction physical overshoot | Medium / high | commit proxy coverage/DB WAL post checks | explicit 36 MiB allowance/92 MiB reservation/stop C |
| B7 caught failure misread as success | Medium / high | returned status/source cutoff actual update audit | stages confirmed/unconfirmed; no fabricated publication G/I |
| Worst case 64 KiB detail cannot fit | Medium / high | encoded combined journal+post fixture one-over | compact references/no duplicates, INCOMPLETE actual learning, no cap change K |
| Premature Empirical Execution | Medium / critical | Compare empirical branch base with recorded I30 engineering closure SHA, review and exact post-merge master CI | Full suite must not begin before engineering merge/review/CI/closure; separate eval branch only after later explicit owner authorization and exact engineering master verification; P / I31 |

## 10. Rollback, closure milestones and unresolved blockers

| Major layer | Revert/recovery | Remaining state / schema / artifacts |
| --- | --- | --- |
| A–D foundation | Preserve stopped task history until separately authorized remediation; on detected storage mismatch terminate, retain invalid/incomplete prefix, no scientific publication or automatic reopen/resume; cleanup only positively revalidated owned paths | actual owned learner state/clone/checkpoint prefixes may exist; no foreign/installed cleanup, no schema change; R1–R10 and G1/G2 pending |
| E–G protocols | Revert layer PR or evaluator-only fix with regression; stop next dispatch | raw disposable learner state/durable journal/partial stages retained; no resume/double learning; schema 7 unchanged |
| H–J science | Revert faulty metric/scenario/report code; new versions/explanation before fresh run | historical negative/failed metrics retain old rules; fixtures disposable but provenance preserved; no source cognition tuning |
| K–L artifacts | Disable publish/reader on defect; retain/quarantine owned prefix | immutable complete/partials and receipts not rewritten; index may be rebuilt from validated fixed inventory only as recorded maintenance, not scientific repair; schema untouched |
| M–N Astra | Revert dashboard route/view integration or disable Evaluation | artifacts remain; other views/core unaffected; no operator execution controls |
| O / I30 engineering release | Revert release integration or separately review engineering repair; failed I30 leaves engineering incomplete and empirical execution blocked | Technical fixture evidence only; no actual empirical findings, schema/installed state untouched |
| P / I31 empirical execution | Stop on defect; classify under frozen plan, retain actual negative/failed/partial evidence; engineering correction separately reviewed, new experiment/AnalysisPlan version where scientifically required before authorized corrected execution | No deletion of inconvenient results or history rewrite; immutable artifacts/actual learning prefixes retained; never installed rollback |

Artifacts can be disposable technical fixtures; scientific complete/partial results are preserved until explicit owner maintenance. They reside only in owned ignored development root and differ from normal SEED state by capability, schema and manifest. A rollback requiring installed SEED access is a scope failure: stop. No organism migration is planned, so no rollback migration.

### Milestone A — B10 Design Complete

Original design milestone achieved: **OWNER APPROVED / COMPLETE / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL**. This storage-only amendment has owner-approved direction and separate publication/review/CI gates; unrelated scientific design is not reopened.

### Milestone B — B10 Engineering Implementation Complete

Reached only after I30 closure: evaluator engineering implemented; G1–G6 passed; required Astra/browser and regression acceptance verified; independent review complete; exact merged-master CI successful and closure recorded. Canonical status becomes **B10 ENGINEERING IMPLEMENTATION COMPLETE / VERIFIED**, **B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED**, **B10 overall IN PROGRESS**. STOP. It does not mean experiments ran or scientific findings were positive; G7 is not required here.

### Milestone C — B10 Empirical Evaluation Complete

Reached only after separately authorized Phase P/I31/G7: preregistered suite executed, every planned member accounted for, required valid evidence and findings preserved, replay/re-execution reviewed and independent scientific evidence review complete. Negative/mixed/null/inconclusive findings do not prevent methodological completion; missing/invalid required evidence may prevent closure. Findings remain per question/subsystem, never an overall scientific PASS.

**Overall B10 completion:** engineering completion alone always leaves B10 IN PROGRESS. Only after successful empirical closure may owner review determine whether overall B10 can be marked COMPLETE / VERIFIED. Engineering COMPLETE / VERIFIED and Empirical Evaluation COMPLETE are separate from per-question POSITIVE/MIXED/NEGATIVE/INCONCLUSIVE findings.

**Historical planning-audit blockers:** none were established at the original audit. Current foundation independent review records nine MAJOR/one MINOR unresolved findings; R1 contract is amended, implementation repair remains required (see below). Future proof obligations are adapter equivalence/default-clock coverage, complete commit monitoring, critical ACK failure fidelity, worst case detail budget and same-profile determinism. They are named STOP gates, not assumed passing. Any failure that requires core cognition/producer/schema/approved scope/limit change becomes **DESIGN AMENDMENT REQUIRED** before implementation continues. No missing new dependency or schema migration was identified.

### Foundation review remediation obligations — future separate authorization only

The stopped foundation branch remains at `df0569a99f192a576fa2d60d0c2050500403fbc9`; reviewed implementation head was `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3`. All findings remain **UNRESOLVED / REMEDIATION REQUIRED**; no new I-number, phase or gate is added. After this amendment merges/verifies, only a later **B10 FOUNDATION REVIEW REMEDIATION — R1–R10 ONLY** instruction may integrate amended canonical master into existing foundation history and execute test-first repairs, full regressions/seven scenarios/fresh independent foundation review/G1/G2 determination and eventual foundation PR. This amendment does none of those steps.

| Finding | Severity / current disposition | Existing task / future required acceptance |
| --- | --- | --- |
| R1 | MAJOR; DESIGN CONTRACT AMENDMENT APPROVED — IMPLEMENTATION FIX STILL REQUIRED; UNRESOLVED / REMEDIATION REQUIRED | I03/I06/I07 pre/post/ongoing/backup capability/identity/sidecar/root validation, existing-file admission, terminal mismatch, no installed fallback, sole trusted writer and truthful native-race disclosure. |
| R2 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I06 autocommit/returned-row statement finalization growth monitoring, all cursor exhaustion/close paths. |
| R3 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I06 checkpoint/clone complete workspace reservation/admission and completion/cleanup enforcement. |
| R4 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I06 shared run-budget terminal latch forbids sibling writers after a stop. |
| R5 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I05 canonical complete profile_digest binding, scientific preconstruction admission. |
| R6 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I02/I03/I07 control-file/root admission and live retained/reservation reconciliation, no active-run double count. |
| R7 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I07/I08 terminal FAILED channel/worker after ambiguous apply; no subsequent operation/retry. |
| R8 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I01/I08 strict nested public prediction fields/domains, no truth bag or I09 execution. |
| R9 | MAJOR; UNRESOLVED / REMEDIATION REQUIRED | I06/I07 explicit completed owned clone launch in fresh worker, complete state/process-local independence; no partial resume/I11 assay. |
| R10 | MINOR; UNRESOLVED / REMEDIATION REQUIRED | I03 dependency graph follows reachable aliased/nonliteral dynamic imports from protected roots. |

Future threat-model documentation check must reject a B10 claim of hostile same-UID SQLite native-open prevention, without weakening ordinary-file descriptor protection or trusted-code isolation. **G1 NOT VERIFIED; G2 NOT VERIFIED** until separate engineering remediation/review/CI establish them. I09–I30 remain NOT STARTED / NOT AUTHORIZED; no empirical evaluation/experiments.

## 11. Planning self-review and owner checkpoint

**Historical implementation-plan checkpoint — 2026-10-02.** This closing block preserves that phase's status/authority and is not the current engineering or amendment status. Current authority/status is at the top of this document and in the owner-approved storage-safety amendment record.

Self-review checked spec sections 3–20/23 against tasks: architecture/truth/storage A/D; deterministic identity B; lifecycle/state C; score order E/G; frozen F; families H; baselines/producers I; preregistration/findings J; artifacts/digests K; replay/reexecution L; Astra M/N; all 22 technical criteria through O/I30 and applicable empirical criteria P/I31/G7/section 7. Governance review preserves all 31 task IDs, G1–G7, external adapters, schema v7, no new dependencies, unchanged resource ceilings and existing risk/rollback/test-first structure; only the I30/I31 branch/PR/authorization/milestone separation changes. Every task has files, exact interfaces/test names/assertions, dependencies, acceptance/failure/recovery, runtime classification and commit boundary. Five Review Focus classes have owning tests. Shared type/interface names and staged dependencies are consistent; no duplicated cognition or orphan acceptance gate. This is a planning self-review, not independent code review or executable verification.

Planning document verification is recorded in tracker/log only after actual documentation checks. The approved spec/roadmap/baselines/source/tests/workflows/dependencies remain unchanged. No implementation or empirical branches, source code, tests, API/UI, experiment, installed organism access or deployment were created/performed.

**B10 IMPLEMENTATION PLAN OWNER APPROVED / COMPLETE / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL**

**B10 IMPLEMENTATION NOT STARTED / NOT AUTHORIZED**

**B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED**

**NO B10 EXPERIMENTS EXECUTED**

**STOP AFTER IMPLEMENTATION-PLAN PUBLICATION AND CLOSURE.** The complete plan is owner-approved at `ef82df33771661a27c6ced6db65e3aaeb4e5fba5`; I01–I30 engineering coding still requires separate explicit implementation authorization. I31 still requires a later separate explicit empirical-execution authorization after merged, verified I30 engineering closure; no final empirical freeze or execution before that instruction. B11–B16 PLANNED / NOT STARTED. DEPLOYMENT / LIVE-DEVICE VALIDATION NOT PERFORMED. INSTALLED SEED UNTOUCHED.
