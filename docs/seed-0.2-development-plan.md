# SEED 0.2 — Developmental Core

Canonical roadmap and batch tracker. Initialized **2026-09-21** from the owner's SEED 0.2 master development instruction and inspection of the current checkout.

**Current authorization: B3 — Prediction Error, explicitly authorized on 2026-09-22. B0–B3 are VERIFIED. B4–B10 remain NOT STARTED and are not authorized.** Broader dashboard implementation remains paused.

## Objective and architectural transition

SEED means **Situated Experiential Emergent Development**. Evolve the existing Germination prototype incrementally into a system that learns from observed consequences and prediction error, while keeping behavior inspectable, reproducible, and under owner control.

The B3 autonomous cycle in `seed/organism.py` is:

```text
perceive state_before
→ choose predefined internal action
→ predict immediate post-action observation
→ perform action
→ perceive state_after
→ describe observed differences
→ evaluate the original prediction against state_after
→ calculate unchanged legacy reward from state_before
→ update contextual action value
→ atomically store linked episode, transition, prediction, and evaluation
```

The target architecture is:

```text
perceive state(t)
→ predict future state
→ select action
→ perform action
→ perceive state(t+1)
→ compare prediction with observation
→ evaluate outcome
→ learn
→ update world model
→ update policy
→ remember experience
→ update self-model
```

The target describes direction, not an implemented pipeline or authorization to implement it. Preserve the current Q learner during the transition. Predictions, beliefs, curiosity, and capability claims must come from measurable records, not language-model interpretation or anthropomorphic claims.

## Batch tracking

Allowed status values: **NOT STARTED**, **IN PROGRESS**, **BLOCKED**, **IMPLEMENTED**, **VERIFIED**. `IMPLEMENTED` means code exists; `VERIFIED` requires the batch's acceptance criteria and tests to pass. Unapproved work stays `NOT STARTED`, even where earlier dashboard work provides useful infrastructure.

Dependencies below are proposed engineering prerequisites, not instructions to start dependent work automatically.

| Batch | Name | Status | Depends On | Tests | Notes |
| --- | --- | --- | --- | --- | --- |
| B0 | Baseline and Guardrails | VERIFIED | — | Full suite: 107 passed; baseline artifact and regression evidence recorded | Minimal specified API restored; core unchanged in B0 |
| B1 | Transition-Based Experience | VERIFIED | B0 | Full suite: 138 passed; independent review approved | Schema v2; observed transitions; unchanged legacy reward/policy; no B2 |
| B2 | Predictor | VERIFIED | B1 | Full suite: 182 passed; review finding fixed/tested | Prospective action-conditioned statistics; no prediction error or policy influence |
| B3 | Prediction Error | VERIFIED | B1, B2 | Full suite: 252 passed; independent review approved | Deterministic post-observation evaluation; no policy/reward feedback |
| B4 | World Model | NOT STARTED | B1, B3 | Not added or executed for B4 | Persistent observation-grounded beliefs and contradictions |
| B5 | Prediction-Error Curiosity | NOT STARTED | B3, B4 | Not added or executed for B5 | Bounded influence on safe internal activity only |
| B6 | Memory Consolidation | NOT STARTED | B1, B4 | Not added or executed for B6 | Actual pattern/knowledge processing; no automatic episode deletion |
| B7 | Self Model | NOT STARTED | B3, B6 | Not added or executed for B7 | Evidence-grounded capabilities, accuracy, resources, and limitations |
| B8 | Decision-System Upgrade | NOT STARTED | B5, B7 | Not added or executed for B8 | Combine decision signals while retaining Q-value compatibility |
| B9 | Astra Development UI | NOT STARTED | B0 and each exposed data-producing batch; B1–B8 for full scope | Not added or executed for B9 | Existing observer UI is groundwork, not developmental UI completion |
| B10 | Development Evaluation | NOT STARTED | B3–B8; B9 for UI inspection of evaluation results | Not added or executed for B10 | Repeatable experiments and measurable improvement criteria |

First planned sprint: **B0 → B1 → B2 → B3**. Each requires a separate explicit instruction. B6 need not depend on B5 if curiosity is not part of its approved scope. B9 may be scoped incrementally only when explicitly authorized, after the data it displays exists. Evaluation design should inform earlier acceptance criteria; that does not authorize implementing B10 early.

## Work breakdown and acceptance criteria

### B0 — Baseline and Guardrails

**Purpose:** Make the current implementation reproducible before changing developmental behavior.

**Expected work:** Identify the intended source baseline and installed/runtime compatibility; document the current cycle, configuration, schema version, dependencies, and safety boundaries. Reconcile the paused dashboard's unfinished tests within the explicitly authorized B0 scope or separate dashboard work. Do not silently omit those tests to produce a passing baseline.

**Verification:** Full agreed baseline suite passes; standalone core behavior and current reward/update calculations are characterized deterministically; schema preservation/restart assumptions are recorded; owner memories remain untouched. Record commit identity, commands, interpreter, and results. Existing partial dashboard tests do not by themselves establish B0 verification.

### B1 — Transition-Based Experience

**Purpose:** Introduce explicit experience transitions and move learning after observed action outcomes.

**Conceptual fields:** `state_before`, `prediction`, `action`, `state_after`, `outcome`, `prediction_error`, `utility`. Prediction/error fields may be absent until their producing batches exist; absence must not be filled with invented values.

**Expected work:** Define action/outcome timing, incomplete transitions, restart semantics, and an additive persistence representation before coding. Preserve legacy episodes and the Q learner while documenting any intentional order change.

**Verification:** Deterministic tests prove the authorized perceive → choose → act → observe outcome → evaluate → learn order; before/after states are linked correctly; interrupted/failed actions cannot fabricate successful outcomes; old records remain readable; migration and rollback behavior are tested on fixtures. Do not claim passive environmental change was caused by an internal action without evidence.

### B2 — Predictor

**Purpose:** Predict measurable environmental variables before their next observations.

**Initial candidate signals:** Battery percentage, normalized load ratio, disk free percentage, and network reachability. Choose the initial supported subset in the batch specification.

**Expected work:** Use interpretable statistical methods, without large ML frameworks. Persist or expose predicted value, confidence, evidence count, and model version. Define prediction horizon and cold-start behavior. Network prediction must use existing observations, not new external activity.

**Verification:** Predictions are made without using their future observations; simple hand-calculated sequences produce expected values; missing/stale signals, insufficient evidence, restart, and model-version compatibility are covered. Confidence semantics and resource bounds are documented.

### B3 — Prediction Error

**Purpose:** Compare predicted and observed states and make the discrepancy observable.

**Expected work:** Record per-signal error and a justified aggregate where signals can be compared. Link errors to the correct prediction and transition. Document units, normalization, missing-signal policy, and usable evidence count.

**Verification:** Hand-calculated exact-match, mismatch, categorical network, missing-data, non-finite, and timing cases pass; errors survive restart and are available through structured telemetry; unavailable errors are never recorded as zero accuracy loss.

### B4 — World Model

**Purpose:** Persist learned beliefs grounded in observations or transitions.

**Candidate belief fields:** Value, confidence, evidence count, contradiction count, created time, updated time, and evidence provenance.

**Expected work:** Define how repeated evidence updates a belief and how contradictions revise it. Specify the relation to existing `concepts`; do not silently reinterpret historical rolling-window concept confidence as calibrated belief confidence.

**Verification:** Repeated evidence, conflicting evidence, insufficient data, restart, and legacy compatibility are deterministic and tested. No LLM invents a belief. Evidence supporting a belief can be inspected.

### B5 — Prediction-Error Curiosity

**Purpose:** Use prediction error, uncertainty, and novelty to influence bounded internal activity.

**Permitted examples:** Observe sooner within resource limits, request reflection, mark an experience important, or temporarily increase observation attention.

**Verification:** Curiosity signals are reproducible and inspectable; scheduling/action influence respects configured limits; missing/error-prone sensors cannot cause unbounded work; explicit owner stop prevails. Curiosity cannot authorize shell commands, browsing, downloads, privilege changes, or arbitrary external actions.

### B6 — Memory Consolidation

**Purpose:** Upgrade checkpoint-only consolidation into knowledge processing.

**Target:** Recent transitions → recurring patterns → comparison with beliefs → confidence/contradiction updates → semantic memory updates.

**Verification:** Known input patterns produce expected semantic updates; repeated runs do not count the same evidence twice; contradictory input is represented; bounded windows and restart recovery are tested. Autobiographical episodes are not automatically deleted. Report actual processing results rather than promising storage savings.

### B7 — Self Model

**Purpose:** Represent measurable capabilities and limitations.

**Candidate fields:** Available/unavailable sensors and internal actions, prediction accuracy, error rates, memory health, database size, recent failures, and current resource usage.

**Verification:** Every field has a measurement/source and freshness policy; unsupported capabilities remain unavailable; stale/error conditions are reflected truthfully; persistence and telemetry are tested. No speculative feelings, consciousness, or personality claims.

### B8 — Decision-System Upgrade

**Purpose:** Make the contextual bandit one signal among several instead of replacing it prematurely.

**Candidate inputs:** Learned action value, predicted outcome, information gain, resource cost, uncertainty, constraint risk, and goal progress where goals are actually defined.

**Verification:** Decision inputs and selection-time values are inspectable; deterministic scenarios exercise resource constraints, missing predictions, conflicting signals, and fallback behavior. Q values remain compatible. New decision weights and utility meanings are explicitly specified and tested before behavior is described as improved.

### B9 — Astra Development UI

**Purpose:** Display actual developmental state through the local dashboard.

**Potential views:** Predictions, World Model, Surprise, Uncertainty, Self Model, Development, and Consolidation.

**Verification:** Read APIs and views reflect real persisted/telemetry records, with provenance, timestamps, empty/error states, and honest uncertainty; display values match fixtures; keyboard access, responsive layouts, bounded queries, and local-only security remain intact. UI code observes through defined interfaces and does not become the cognition engine.

### B10 — Development Evaluation

**Purpose:** Establish whether SEED improves through experience using repeatable experiments.

**Candidate metrics:** Prediction accuracy/error over time, uncertainty reduction, belief stability/revision, contradictions, learning speed, and observations needed to form reliable models.

**Verification:** Versioned deterministic experiments identify input sequences, seeds, baselines, evaluation windows, units, and success/failure thresholds. Training/evaluation leakage and incomparable windows are excluded. Report negative results as well as improvements. No “emergent,” “smarter,” or “developmental improvement” claim without supporting measurements. A repeatable evaluation can be verified even if its measured result shows no improvement; that result must remain explicit.

## Repository facts at roadmap initialization (historical)

These facts describe the checkout before B0. The B0 execution log below records repairs and supersedes the initial test/ready state; this historical inventory is retained for traceability.

### Source identity and runtime

- The project is now a Git repository at this workspace root, on `master`, with inspected HEAD **`6dd5429` — `initial commit`**. The working tree was clean before adding this tracker. Earlier inspection documents saying Git was absent describe an earlier state and are not current Git evidence.
- `main.py` now constructs the organism inside `main()` and installs SIGTERM/SIGINT handlers; importing it no longer starts an organism. `SEED_HOME` still defaults to `~/Library/Application Support/SEED`.
- `seed/organism.py` retains the predefined-reward cycle. It calls `Learner.reward()` and `Learner.update()` **before** performing the chosen action. There is no `state_after` observation linked to an experience yet.
- `seed/learner.py` is still an epsilon-greedy contextual bandit over observe, reflect, consolidate, and rest. Defaults remain epsilon 0.15 and alpha 0.18. Earlier dashboard work added selection-time values, visit counts, exploration provenance, and candidate actions to `Decision`.
- `seed/body.py` observes battery/charging, load averages, free disk, time, machine/OS identity, and network reachability. Its pre-existing network probe opens a fixed TCP connection to **1.1.1.1:443**. This is a compatibility fact, not authorization for additional network behavior.
- `seed/organism.py` reflection uses the most recent 80 episodes and qualifying sensor samples to form mean load/battery concepts. Evidence count is a rolling sample count; confidence is the existing heuristic, not calibrated prediction confidence. Consolidation still records a checkpoint only.
- `seed/runtime.py`, `seed/telemetry.py`, and `seed/commands.py` add core ownership, session-bound commands, heartbeat/current-activity records, and structured events from earlier dashboard work. Wake detection remains an inferred heartbeat/cycle gap, not a native sleep notification.
- Settings and rotating-log/backup helpers have been added in the checkout. Existing configuration rejects enabling prediction-error curiosity and advanced concept inference; these settings do not constitute B5 or B4 implementations.
- The existing per-user LaunchAgent label is `local.seed.organism`; the installed configuration previously inspected has RunAtLoad and no KeepAlive. This instruction did not change or restart it.

### Schema and migration state

| Layer | Inspected state | Developmental implications |
| --- | --- | --- |
| Original schema | `meta`, `episodes`, `q_values`, `concepts`; SQLite WAL; no explicit schema version | Preserve all legacy rows and their original meanings |
| Current checkout migration | `seed/migrations.py` declares `VERSION = 1` and records it in `seed_schema` | Dashboard infrastructure version; **not** a SEED 0.2 developmental schema version |
| Additive checkout tables | `events`, `runtime`, `concept_evidence`, `commands`, `annotations`, `settings`, `automations`, `automation_runs`, `audit` | Their presence does not mean all corresponding services are complete |
| Installed database | Read-only inspection on 2026-09-21 found the original four tables plus SQLite's `sqlite_sequence`, with no `seed_schema` | The dashboard source changes have not been deployed to this database |
| Developmental records | No transition, predictor, prediction-error, world-model, or self-model persistence has been implemented as a 0.2 batch | Exact new schemas must be decided and authorized per batch |

`Memory` construction in the checkout is a **write-capable operation**: it can create tables and apply migrations, taking a SQLite backup before upgrading a nonempty legacy database. It must not be used as a read-only inspection tool against the owner's installed home. This planning task used SQLite `mode=ro` for installed schema inspection and did not invoke migrations there.

The migration currently supports its single known version and rejects other versions. Future batches need explicit ordered version steps; do not assume the existing function already implements a general multi-version migration ladder.

### Dashboard state and unfinished work

- A separate FastAPI/static-JavaScript dashboard now exists. Its CLI binds to `127.0.0.1`, default 8765, with Host/Origin and mutation-token checks. Observer queries use read-only SQLite connections.
- The six observer views exist: Overview, Live Activity, Environment, Memory, Concepts, and Learning. Historical counts and lifecycle records in the current Development panel are not the developmental models or evaluation views envisaged by B9.
- Command broker, queue, settings, backup, and process-control backend code exists. Owner interaction, operator UI completion, automation scheduler, and final integration/security review were still pending when the owner changed this task to planning only.
- `dashboard/automation/` currently contains only its package initializer. The automations API returns an unavailable/empty result; automation tables are infrastructure only.
- `tests/dashboard/test_interaction.py` was added test-first immediately before the scope change. It imports **`dashboard.services.interaction`**, which does not exist yet. Therefore the **full suite does not currently collect successfully**. It also anticipates owner-note/summary routes and operator legacy-schema refusal that are not yet implemented.
- The current `create_app(..., operator=True)` does not yet enforce the planned startup rejection of an incompatible legacy schema. Do not treat planned security behavior or test expectations as implemented guarantees.
- A read-only observer preview was started during the earlier dashboard work. Its running Python process predates subsequent source edits; it is not evidence that the final on-disk operator code is validated. No preview was started or installed by this roadmap task.
- `docs/architecture.md` is an earlier inspection; the dashboard spec/implementation plan and scratch ledger are plans/progress records, not proof of a completed release. This tracker records the current differences explicitly.

### Compatibility and environment

- Repository README requires Python 3.11+. The project `.venv` currently uses **Python 3.13.15**. The system `python3` was previously observed as 3.9.6; use the project interpreter for reproducible tests.
- Dashboard dependencies are separate from the standard-library core. `requirements-lock.txt` records the resolved environment used during dashboard development.
- A pre-dashboard source archive exists at `.checkpoints/source-20260921-102020.tar.gz`. It is a source checkpoint, not an installed-memory backup or a verified restoration procedure.
- Do not run `install.sh` during roadmap inspection: it copies source into the installed app and restarts the LaunchAgent. Deployment and baseline validation must be deliberate and separately scoped.

## Inspection and test evidence — roadmap initialization

All commands below were inspection or tests against temporary fixtures. The new roadmap task changed no runtime source, installed memories, or schema definitions. Temporary fixture creation/migration/backup occurs inside the tests and is not a migration of the installed database.

| Date | Command / inspection | Result | Meaning |
| --- | --- | --- | --- |
| 2026-09-21 | Source file inventory and focused review of organism, learner, memory, migrations, configuration, dashboard routes, and existing tests | Completed | Confirms actual cycle, infrastructure, and unfinished components |
| 2026-09-21 | `git rev-parse --show-toplevel`, `git branch --show-current`, `git log -3 --format='%h %s'`, `git status --porcelain=v1` | Root matches workspace; master; HEAD `6dd5429`; initially clean | A Git baseline now exists; no new commit was created for a WBS batch |
| 2026-09-21 | `.venv/bin/python -m pytest -q` | **Collection failed**: missing `dashboard.services.interaction` in `tests/dashboard/test_interaction.py` | Current full suite is not passing; no baseline verification claim |
| 2026-09-21 | `.venv/bin/python -m pytest -q --ignore=tests/dashboard/test_interaction.py` | **58 passed, 2 warnings** | Diagnostic subset only; explicitly excludes the unfinished test module |
| 2026-09-21 | Installed SQLite schema query using `mode=ro` and explicit connection close | Original unversioned schema confirmed | No owner records inspected or changed beyond schema metadata |

The two subset warnings are upstream Starlette TestClient deprecations concerning the `httpx` transport and an AnyIO `BlockingPortal` alias. They were not suppressed or resolved during planning. No developmental experiment or B0 acceptance run was performed.

## Architecture decision log

| Decision | Reason | Alternatives considered | Consequences | Batch introduced |
| --- | --- | --- | --- | --- |
| Treat the user's new instruction as a planning-only boundary and pause dashboard implementation | Explicit immediate-task scope prohibits runtime/schema changes and says to stop afterward | Finish pending dashboard features first; start B0 immediately | Preserve the visible work-in-progress, including failing interaction-test collection; further implementation needs an explicit instruction | Roadmap initialization; no batch |
| Distinguish core Developmental 0.2 from Dashboard Operator Edition 0.2 | The two earlier names refer to different deliverables | Count operator/telemetry infrastructure as completed B0/B9 | All developmental batch statuses stay NOT STARTED; useful infrastructure is documented without claiming developmental progress | Roadmap initialization; no batch |
| Retain the Q learner and original memories during incremental transition work | Owner's compatibility and memory-preservation constraints | Replace the learner or reinterpret legacy episodes wholesale | New transition/evaluation semantics must be explicit and additive; no fabricated historical predictions | Owner constraint; implementation deferred to B1/B8 |
| Keep developmental learning in the standard-library core and observability in the dashboard adapter | Core/dashboard separation and no LLM dependency | Put predictors in the dashboard or add an LLM-based world model | Future modules must work without the dashboard; UI consumes evidence rather than generating beliefs | Owner constraint; all future batches |
| Record diagnostic subset results separately from the failed full suite | Excluding unfinished tests is not baseline verification | Report 58 passing tests as the whole-suite result | B0 must explicitly resolve/reconcile the incomplete interaction work before a VERIFIED baseline | Roadmap initialization; no batch |

Prediction algorithms, normalization, confidence mathematics, transition tables, and policy weights have **not** been selected by this roadmap. Record their alternatives and consequences in the authorizing batch's decision record.

## Unresolved questions and known limitations

1. **B0 baseline boundary — resolved:** Characterize commit `6dd5429` plus minimal specified interaction/API guard repairs. Broader dashboard completion is separate. The full intended suite is run without exclusions.
2. **Source versus installed runtime:** The installed app/database remain legacy while the checkout contains telemetry/schema additions. B0 must identify which version is the evaluation baseline and record a safe upgrade/rollback policy without implicitly deploying it.
3. **Transition timing:** Define whether `state_after` is measured immediately after an internal action or after the scheduled interval, and how sleep gaps, failed perception, shutdown, and incomplete transitions are represented.
4. **Causality and utility:** Internal reflection/rest mostly influence SEED's work rate, not the MacBook's external workload. Separate observed environmental change from action-caused outcomes; specify what utility actually measures.
5. **Prediction/evaluation semantics:** Select signal units, horizons, cold-start defaults, treatment of missing sensors, confidence evidence, normalized errors, baseline comparisons, and reproducible evaluation windows in the relevant batches.
6. **Legacy evidence:** Original episodes have one state; old concepts lack supporting IDs and creation history. Do not backfill fictional transitions, predictions, or confidence histories.
7. **Migration expansion:** Version 1 supports dashboard additions, but ordered future migration steps and cross-version compatibility need batch-specific design and fixtures.
8. **Partial operator capabilities:** B0 restores the specified interaction backend and legacy-mode refusal. Operator UI, automation, and comprehensive deployment review remain separate unfinished work; B0 verification is not deployment certification.
9. **Existing network sensing:** The fixed reachability probe predates this roadmap. Whether to replace it with strictly local link-state observation requires an explicit batch decision; no such change was made here.
10. **No measured developmental improvement yet:** There are no predictor accuracy, prediction-error reduction, belief-revision, or self-model evaluation results to report.

Unresolved B1+ questions remain tracked for future explicit scope decisions. They do not authorize later batches. The B0 baseline boundary is resolved above.

## Batch execution and change discipline

For every explicitly authorized batch:

1. Record the instruction, precise objective, prerequisites, acceptance criteria, and rollback boundary. Update only that batch to IN PROGRESS.
2. Use a clearly identifiable commit or commit series; suggested naming is `seed-0.2 B<N>: <specific change>`. Keep other WBS batches out of the change.
3. Prefer additive versioned migrations and small modules. Preserve existing behavior unless the active batch explicitly changes it.
4. Test unit calculations, persistence, migration preservation, legacy compatibility, restart/incomplete work, corrupt data, telemetry, resource bounds, dashboard reads, and owner control as applicable.
5. Record the exact changed files, schema/behavior changes, test commands/results, unresolved concerns, and follow-up work below. Never mark VERIFIED merely because code exists.
6. Report results and **stop**. Wait for the next explicit batch instruction; dependencies and sprint order do not authorize automatic continuation.

### Per-batch record template

Copy this structure when a batch is explicitly authorized; it is not an active implementation record.

```text
Date:
Batch:
Authorization:
Objective:
Prerequisites and acceptance criteria:
Starting commit and ending commit(s):
Files changed:
Schema changes and migration version:
Behavior changes:
Backup / recovery / reversibility:
Tests added:
Tests executed (exact commands):
Results:
Telemetry / inspection evidence:
Known issues:
Architectural decisions:
Follow-up work:
Final status:
```

### Roadmap initialization record — not B0

- **Date:** 2026-09-21.
- **Objective:** Initialize the canonical 0.2 tracker and reconcile it with current source.
- **Files changed:** Created `docs/seed-0.2-development-plan.md` only for the new planning instruction.
- **Schema changes:** None.
- **Behavior changes:** None.
- **Tests added:** None.
- **Tests executed/results:** Full-suite collection failure and 58-test diagnostic subset as recorded above.
- **Known issues:** Paused dashboard interaction work; differing checkout/installed schema; incomplete operator/automation verification.
- **Follow-up:** Await explicit B0 authorization and resolve its baseline boundary within that instruction.

## Completion criteria and ready state

This roadmap is initialized when B0–B10 are listed with valid statuses, dependencies, acceptance criteria, current repository/schema facts, honest test evidence, and the decision/update process. Those planning requirements are satisfied by this document; they do not mark a development batch implemented or verified.

SEED 0.2 is complete only when each authorized batch meets its acceptance criteria, relevant tests and full regression gates pass, migrations preserve memories, runtime/dashboard separation and owner authority remain intact, and repeatable evaluation results are recorded without overstating improvement.

**Ready state:** B0–B3 VERIFIED. B4–B10 remain NOT STARTED and unauthorized; B4 requires an explicit instruction.


## B0 execution log — 2026-09-21

Status: VERIFIED. Starting commit: `6dd5429`; scoped working branch: `seed-0.2-b0`.

- Objective: establish the current implementation as a reproducible, non-developmental baseline.
- Scope decision: use the committed checkout, with a minimal repair of its specified interaction API, as the baseline. Do not finish operator UI/automation or alter the installed app.
- Evidence: Git history contains the interaction tests but no interaction implementation or rename. Task 8 in the approved dashboard plan defines the exact service and route signatures.
- Initial verification: `.venv/bin/python -m pytest -q` fails collection with `ModuleNotFoundError: dashboard.services.interaction`.
- Execution sequence: repair the intended API and schema guard; add deterministic learner/lifecycle/sensor characterization; verify migration preservation and safety boundaries; write safe JSON metrics and baseline documentation; run the full suite and commit B0 only.
- Runtime constraint: preserve all existing core decision/reward/action timing. No installed database inspection or migration is needed for B0.


### B0 repository and repair evidence

The intended baseline is the current checkout based on `6dd5429`, including pre-existing dashboard infrastructure. It is **not** the separately installed legacy app, which B0 neither executes nor migrates. The tracker itself was untracked at B0 start; the B0 commit includes the previously requested roadmap and its execution record.

`git log --all -- dashboard/services tests/dashboard/test_interaction.py` and `git ls-tree` found the tests in the initial commit but no implementation, rename, or historical version of `dashboard.services.interaction`. The approved dashboard plan's Task 8 explicitly defines `note(text, important)`, `annotate(episode_id, important, tags)`, `summary(since)`, and their routes. This is sufficient to repair the missing backend without designing a new feature or expanding UI scope.

B0 adds that small service and its route models. Notes have `event=owner`, `state={source: owner}`, no sensor fields, and separate importance/tags. Annotation changes do not rewrite episodes. Mutations reuse existing origin/token/observer-mode checks and commit their episode/annotation/event/audit writes together. Summaries count retained records in an explicit time interval and report coverage; no AI response, prediction, or invented confidence history is generated. Malformed notes/tags/intervals and unknown episodes are rejected.

B0 also restores the already-specified read-only startup check for operator mode: required tables must exist and `seed_schema` must contain exactly the supported version. Legacy/future schemas are rejected with no migration. Observer-mode legacy reads remain compatible. No core file, installation script, sensor, migration definition, cycle order, frontend asset, or dependency version was changed for this repair.

### Precise learning control condition

State keys are `energy|activity|storage|phase`:

| Component | Current rule, evaluated in this order |
| --- | --- |
| Energy | Missing/None battery → `unknown`, even if charging; otherwise truthy charging → `charging`; battery <20 → `low`; battery <55 → `mid`; otherwise `high` |
| Activity | `load_ratio > 0.75` → `busy`; otherwise `calm`; missing load defaults to 0 |
| Storage | `disk_free_pct < 10` → `tight`; otherwise `ok`; missing disk defaults to 100 |
| Phase | `local_hour < 6` → `night`; otherwise `day`; missing hour defaults to 12 |

Actions, in tie-candidate order: **observe, reflect, consolidate, rest**. Missing Q rows behave as value 0 and visits 0. Defaults are epsilon **0.15** and alpha **0.18**, configurable within the existing validated bounds.

A random draw less than epsilon selects uniformly from all four actions. Otherwise the learner selects uniformly among actions tied for the highest current Q value. Selection-time Q values, visits, chosen score, epsilon, exploration branch, and candidate actions are captured before update. B0 tests replace random draws/choice with fixed behavior; they do not rely on sampled distributions or random luck.

Reward starts at zero; the following contributions are **additive**:

| Condition | Action-dependent contribution |
| --- | --- |
| Known battery <20 and not charging | rest: +1.2; every other action: −0.6 |
| Load ratio >0.8 | rest: +1.0; every other action: −0.4 |
| Disk free percentage <10 | consolidate: +0.8; every other action: −0.2 |
| Battery unknown, ≥40, or charging; and load ratio <0.5 | observe/reflect: +0.45; other actions: 0 |

The sum is rounded to four decimal places. Load exactly 0.8 does not incur the high-load reward penalty; load exactly 0.5 does not receive the low-load bonus. Context classification and reward thresholds intentionally differ in the existing implementation.

```text
Q_new = Q_old + alpha × (reward − Q_old)
visits_new = visits_old + 1
```

Only the selected state/action row is updated. There is no discount factor, next-state maximum, measured action outcome, or prediction error. Binary floating-point comparisons use tolerances in tests.

Current cycle timing is preserved:

1. Apply a new settings revision and check the cycle-start gap.
2. Perceive one state and emit PERCEPTION.
3. Choose from current values and emit DECISION.
4. Calculate the heuristic reward from that same state, update Q, and emit LEARNING.
5. Emit ACTION start; call reflect/consolidate if selected; emit ACTION completion.
6. Store one experience episode with the original state, action, reward, and context note; update latest state/action metadata.
7. Enter idle/resting and wait for the action's interval: observe 8s, reflect 12s, consolidate 20s, rest 35s by default. Refresh heartbeat/check owner requests in interruptible waits of at most 2s.

Reflection summarizes the latest 80 episode rows, excluding owner-source sensor evidence. It requires at least eight qualifying samples per signal, computes mean load/battery, and sets confidence to `min(0.95, 0.4 + sample_count / 200)`. Existing concepts are rolling sample summaries, not calibrated world-model beliefs. Consolidation records counts/time in `last_consolidation`; it does not delete memories or perform semantic consolidation.

### Lifecycle control condition

- Process construction acquires a nonblocking core lock, initializes memory/configuration/session identity, and records STARTING. `main()` installs SIGTERM/SIGINT handlers; these only request stop.
- `run()` records a wake with `reason=process_start`, perceives during normal cycles, and waits on the stop event between cycles. The stop test exercises the actual run loop with only sensing and waiting replaced.
- A **wall-clock gap between cycle starts strictly greater than 45 seconds** records an inferred wake. Exactly 45 seconds does not; a backwards wall-clock movement does not. This is not an authoritative OS sleep detector, nor does it continuously record sleep onset.
- Actual macOS suspension freezes the process; a dashboard cannot infer definite SLEEPING merely from missing heartbeat data. Long configured intervals or slow work can also create inferred wake records.
- Normal termination records a `sleep` episode with `reason=process_stop`, using the last stored state rather than a new network/sensor call. Runtime becomes STOPPED; DB and lock are closed. A new instance preserves identity and episodes.
- Startup/cycle errors are recorded as ERROR; the existing startup-failure test confirms lock release. No automatic restart loop or KeepAlive is introduced.

### Schema and persistence control condition

Current checkout version remains **1**, stored in `seed_schema`. The original tables remain `meta`, `episodes`, `q_values`, and `concepts`. Added tables are `events`, `runtime`, `concept_evidence`, `commands`, `annotations`, `settings`, `automations`, `automation_runs`, and `audit`; SQLite also maintains `sqlite_sequence`.

Explicit indexes are `events_category_id(category,id)`, `events_ts(ts)`, and `episodes_event_ts(event,ts)`; primary/unique keys create SQLite autoindexes. The JSON baseline records the explicit SQL and actual table inventory. No new schema/index was added in B0.

`migrate()` uses BEGIN IMMEDIATE, executes additive statements, writes version 1, and commits; failure rolls back that migration. Repeating supported-version migration is idempotent. Unknown versions are rejected. Base-schema `CREATE TABLE IF NOT EXISTS` initialization occurs in `Memory` before `migrate()`, so the migration transaction is not a guarantee that all constructor setup is atomic. Future versions require explicit new migration steps.

For an existing legacy file containing an episodes table (even if empty), `Memory` requests a SQLite backup before the new schema is applied. Backup uses SQLite's backup API, a bounded passive checkpoint attempt, integrity verification, and timestamped publication. A backup failure stops the upgrade. These paths are exercised only on temporary fixtures in B0.

Existing tests providing the preservation guarantees are:

- `tests/test_migrations.py::test_preserves_rows_and_is_idempotent`: compares every original episode, Q, concept, and meta row before/after migration and rerun.
- `tests/test_migrations.py::test_migration_rollback`: injects an invalid statement and confirms migration rollback.
- `tests/test_migrations.py::test_unknown_schema_refused`: confirms unsupported versions are rejected.
- `tests/dashboard/test_storage.py::test_legacy_upgrade_backed_up_before_schema`: verifies the snapshot still has legacy schema and its episode.
- `tests/dashboard/test_storage.py::test_failed_backup_does_not_migrate`: verifies a failed snapshot does not apply schema versioning.
- `tests/dashboard/test_storage.py::test_backup_while_writing`: verifies backup integrity with concurrent temporary-database commits.

No installed database was opened or modified during B0. Tests and the simulation use temporary homes. There is no need to hash or copy live memory to establish these source-level guarantees.

### Resource / environment baseline

| Signal | Source and type | Current failure behavior | External network activity |
| --- | --- | --- | --- |
| `battery_pct` | Fixed `/usr/bin/pmset -g batt`; first percentage parsed as integer or None | Command errors/timeouts return empty output; missing percentage → None | No |
| `charging` | Boolean/None derived from pmset text | Empty output → None; otherwise boolean text heuristic; **discharging false-positive described below** | No |
| `load_ratio` | `os.getloadavg()[0] / (os.cpu_count() or 1)`, rounded to 3 decimals | Missing CPU count uses 1; load-average call errors propagate to cycle error handling | No |
| `load_5m_ratio` | Five-minute load average divided by CPU count, rounded to 3 decimals | Same as one-minute load | No |
| `disk_free_pct` | `shutil.disk_usage(SEED_HOME).free / total × 100`, rounded to 2 decimals | Disk-query errors propagate; there is no fabricated healthy fallback | No |
| `network` | Boolean from fixed TCP connect to 1.1.1.1:443, 1-second timeout | OSError, including connection failure/timeout, → False; not a general internet-quality measure | **Yes: existing fixed connection probe** |
| `wall_time` | `time.time()`, epoch seconds (float) | System clock changes affect gap inference; no monotonic wall-time correction | No |
| `local_hour` | `time.localtime().tm_hour`, integer | Uses host local timezone; no separate timezone model | No |
| `hostname` | `platform.node()`, string | May be empty; no additional fallback or claim of availability | No |
| `machine` | `platform.machine()`, string | May be empty | No |
| `macos` | `platform.mac_ver()[0]`, string | May be empty on unsupported platforms | No |

Load ratios are normalized load averages, **not CPU utilization percentages**. Tests replace the actual OS/network calls and use synthetic machine strings. The machine-readable artifact contains only synthetic states, public project configuration, versions, source hashes, and controlled measurements—not hostnames, owner paths, tokens, or private memories.

### Safety and owner authority evidence

| Boundary | Evidence and practical limit |
| --- | --- |
| No root required | Standard user process and per-user LaunchAgent in install script; no sudo/escalation code. There is **no explicit root-launch refusal** if an owner manually invokes the program as root; this is recorded rather than claimed as enforced. |
| Owner can stop | SIGTERM/SIGINT set stop event; actual run-loop regression confirms normal sleep/stop record and lock release; queued requests cannot force restart. |
| No self-replication/hidden persistence | Inspected core source contains no installer/replicator; explicit installer copies only into the designated user app directory and writes the documented LaunchAgent. No KeepAlive is added. Installer/uninstaller were not executed during B0. |
| No arbitrary generated shell | Body uses a fixed pmset argument array; process adapter uses fixed launchctl arguments and validated configuration; broker dispatch is an allowlist. Existing unknown-command/injection tests and B0 HTTP extra-field tests pass. CLI log tail is a fixed command. |
| Local dashboard | CLI exposes no host option and returns host 127.0.0.1; existing binding/Host/Origin tests pass. No listener was started for B0. |
| Mutations/confirmations | Origin + per-process token + operator mode required; stop/restart/rotate_logs require matching confirmation; unknown/reset commands are rejected. B0 tests exercise the HTTP boundary without invoking live process mutations. |
| Memory boundary | Read-only observer adapter, non-destructive annotations, additive migrations, temporary-fixture preservation tests; no live migration or installation. |
| Core independent of dashboard | A B0 subprocess uses Python `-S` (no site packages), runs the real core with synthetic perception in a temporary home, and verifies no FastAPI/Uvicorn import. |

These checks establish the defined baseline boundaries; they are not a certification against a malicious same-user process, exhaustive malformed-data handling, or a complete operator deployment audit.

### Reproducible metrics and artifact

Machine-readable snapshot: **`docs/baselines/seed-0.1-baseline.json`**. Reproduce the controlled metrics with:

```sh
.venv/bin/python -m tests.baseline_scenario
```

The helper creates/resolves a temporary directory, substitutes synthetic perception and clock values, and uses a deterministic first-candidate tie break with epsilon 0 (only in the control; production default remains 0.15). Its CLI was tested after resolving the system temporary-path symlink alias; production path validation was not changed.

Metric definitions:

- **Observation count:** valid retained experience records in the controlled sequence; owner notes and lifecycle rows excluded. The existing live dashboard's raw experience count does not validate sensor quality. The controlled input is explicitly valid.
- **Action distribution:** counts by action for autonomous experience records; a mixed owner-command dataset must distinguish manual observations. The control contains no manual requests.
- **Context coverage:** distinct keys in populated Q rows; this corresponds to learned/visited contexts in the control.
- **Policy coverage:** number of populated state/action rows, including negative/zero values; not a percentage of all possible contexts.
- **Concept count:** persisted concept rows, without implying calibrated belief quality.
- **Lifecycle counts:** raw wake, sleep, and experience rows. Wake includes process start/inferred resume; sleep includes process stop.
- **Database footprint:** measured main/WAL/SHM bytes after checkpoint and close, with page size/count and Python/SQLite versions. Physical size is environment-dependent and not a fixed cross-platform acceptance threshold.

The sequence **A, A, B, A, B, B, B, B** uses A = charging/high-energy/calm/storage-ok/day, and B = low battery/busy/tight storage/night. It produces:

| Metric | Controlled result |
| --- | --- |
| Observations | 8 |
| Actions | observe 4; reflect 1; consolidate 1; rest 2 |
| Context / policy coverage | 2 contexts; 5 Q rows |
| Concepts | 0; the reflection window has insufficient samples when reflection is chosen |
| Episode counts | wake 1; experience 8; sleep 1 |
| Charging-context observe Q | 0.2018844 after 3 visits |
| Constrained-context Q | observe −0.216; reflect −0.216; consolidate −0.036; rest 0.6552 (2 visits) |
| Database footprint in captured environment | 118,784 main bytes; 0 WAL/SHM bytes after checkpoint/close; 29 pages × 4,096 bytes |

`tests/test_baseline_scenario.py` checks the real resulting policy against hand-calculated values. Prediction accuracy/error metrics are **unavailable** in B0 and are not fabricated or measured.

### B0 known discrepancies, limitations, and follow-up / B1+ notes

- **Existing charging parser defect:** substring matching finds “charging” inside “discharging,” so discharge output can return `charging=True`. A characterization test pins the actual current behavior, and the baseline artifact identifies the defect. No sensor semantics were changed; future real-device comparisons must account for this issue or explicitly authorize a sensor repair first.
- **Current heuristic reward precedes action.** This is the intended B0 control condition, not observed-consequence learning. B1 owns the transition/timing change.
- **Inferred wakes can be false positives** from long configured intervals or delayed cycles, and are sensitive to clock changes. No native notifications were introduced.
- **Full suite previously blocked by missing interaction code:** repaired from the existing specification; no test was removed, skipped, or excluded. Only the small backend was restored; the operator UI and scheduler remain outside B0.
- **Installed app remains legacy.** B0 verifies the checkout and fixture migrations, not a deployment. Existing startup scripts copy source and restart SEED; do not run them as baseline verification.
- **Upstream warnings remain:** two deprecation warnings from Starlette/httpx/AnyIO TestClient, recorded without suppressing or upgrading dependencies.
- **No developmental capabilities or performance claims:** no transitions, predictions, prediction error, world model, curiosity, semantic consolidation, self-model, new scoring, or developmental UI was implemented. Future comparison must use equivalent controlled inputs/settings and distinguish returned intervals from actual waited wall time.

### B0 acceptance record

**Final status: VERIFIED.** All B0 acceptance criteria are satisfied. No B1 work is authorized or implemented.

Files changed in this B0 commit:

- `dashboard/app.py`: reject legacy/unknown schemas in operator mode without migration.
- `dashboard/api/operator.py`: restore the previously specified note, annotation, and summary routes.
- `dashboard/services/interaction.py`: implement the minimal transactional owner interaction service.
- `tests/dashboard/test_interaction.py`: input, attribution, rollback, authorization, schema, and oversized-ID regression coverage.
- `tests/test_baseline_learner.py`: deterministic state, reward, exploration/exploitation, Q-update, visit, and provenance characterization.
- `tests/test_baseline_lifecycle.py`: cycle order, gap boundaries, heartbeat, stop, and persistence characterization.
- `tests/test_baseline_environment.py`: sensor sources, values, failures, fixed network probe, and existing charging-parser defect.
- `tests/test_baseline_safety.py`: dashboard-free core subprocess and owner-control regression checks.
- `tests/baseline_scenario.py`: temporary, deterministic control simulation and CLI.
- `tests/test_baseline_scenario.py`: expected control policy/metrics and CLI regression checks.
- `docs/baselines/seed-0.1-baseline.json`: safe machine-readable schema, source hashes, behavior, and measured control baseline.
- `docs/seed-0.2-development-plan.md`: canonical roadmap and this B0 execution/acceptance record.

Verification commands and results:

- `.venv/bin/python -m pytest -q`: **107 passed, 2 upstream deprecation warnings, 0 failures**. Full intended suite; no test exclusions or skips. Includes existing migration/legacy-memory preservation tests identified above.
- `.venv/bin/python -m tests.baseline_scenario`: successful standalone synthetic run with the recorded eight observations, two contexts, five policy rows, and expected hand-calculated Q values.
- `.venv/bin/python -m compileall -q dashboard tests`: passed.
- `git diff --check`: passed; new documentation also checked for trailing whitespace.
- Source/hash comparison against `6dd5429`: core and `main.py` unchanged; recorded JSON source hashes match. JSON parses and contains no local usernames/absolute paths/tokens/private memory data.

Independent read-only review reported no Critical or Important findings. Its one Minor finding was reproduced by a failing HTTP regression test: IDs above SQLite's signed 64-bit range caused `OverflowError`. The service now rejects that input with HTTP 422; the regression and full suite pass. No outstanding review blockers remain.

Schema remains version 1, with no B0 migration or core-source change. All database writes during B0 verification used temporary fixtures; installed memories were not accessed or modified. No install, core restart, or new listener was performed for B0.

Git scope: branch `seed-0.2-b0`, starting commit `6dd5429`; this record and the twelve listed files are committed together as `seed-0.2 B0: establish verified developmental baseline`. Reverting this B0 commit restores the prior checkout without changing installed memory. The prior checkout's missing-service collection failure would return.

**Ready for B1: YES**, subject to explicit owner authorization. The recorded sensor/lifecycle limitations remain part of the control condition, not claims that they were repaired.


## B1 execution log — 2026-09-22

Status: VERIFIED. Branch: `seed-0.2-b1`. Starting commit: `ecd9c65` (owner-created branch at B0 merge, identical tree to verified `b6d7a28`). Working tree initially clean; baseline command `.venv/bin/python -m pytest -q`: 107 passed, no skipped/excluded tests, two upstream warnings.

Objective: observable autonomous transitions with unchanged contextual-bandit policy and legacy reward values, evaluated after action and second perception. Execution plan: `docs/superpowers/plans/2026-09-22-seed-b1.md`. Native implementation continues under the owner's detailed approved B1 design.

Architectural decision: B1 preserves B0 reward semantics while moving reward evaluation and Q-learning after action completion and post-action observation. This isolates transition architecture from later changes to prediction, utility, curiosity, and decision policy.

Preflight: existing learner commits Q updates independently; focused experience persistence will make the episode and transition atomic. Actions such as reflection may already have committed effects if a later observation/write fails; do not claim transactionality across the entire physical cycle. Backup runs before the migration; version validation must precede all constructor schema writes. Sensor snapshots must be copied to prevent reused mutable data changing provenance.

### B1 implementation and schema

- `seed/migrations.py`: VERSION 2; retain the exact v1 statements and add a v1→v2 step. An unversioned database applies both steps in one migration transaction. Exactly one supported integer schema row is required; empty, duplicate, and future versions are refused.
- `seed/memory.py`: inspect schema before write-capable constructor initialization; back up an existing legacy or v1 database with an episodes table before upgrading. Failed backups prevent migration; failed constructor setup closes its connection. Existing path and symlink checks remain in place. Direct low-level `migrate(db)` still does not create filesystem backups; `Memory` is the supported upgrade entry point.
- New `transitions` table: integer autoincrement ID, unique non-null `episode_id` foreign key, start/completion wall timestamps, full before/after JSON, action, outcome JSON, legacy reward, nullable prediction and prediction-error JSON. Episode primary/unique linkage provides its lookup index. No old row is rewritten or backfilled; all prediction fields remain SQL NULL.
- `Memory.record_transition_experience(...)` validates JSON before writes and inserts both records in one SQLite transaction. Episode timestamps equal completion timestamps; episode state remains state-before, keeping the existing reflection and historical read meanings. Latest-state metadata instead records state-after, the most recent observation.
- `seed/transitions.py`: copy complete JSON observations, reject non-dictionary/non-string top-level keys and nonfinite/unserializable values. Missing fields and None remain missing/None. Outcomes traverse sorted union keys: before/after values plus explicit presence flags; numeric pairs produce delta; other pairs produce changed, distinguishing booleans from numbers. Overflowing finite-float differences produce `delta=null, delta_unavailable=true`, never fabricated numeric change. Outcomes describe observed differences, not causal effects.
- `seed/organism.py`: extract the existing action dispatch; observe/rest remain no additional processing; reflect/consolidate call their unchanged routines. Action completes and state-after is observed before reward evaluation and Q update. Decision provenance is emitted before action; pre/post PERCEPTION phases, ACTION start/complete, linked LEARNING and MEMORY records identify the completed experience. Runtime retains decision context and action start, exposes current action and last completed action, then returns idle/resting after successful persistence.
- `dashboard/app.py`: the existing operator schema check now also requires transitions; it continues to refuse incompatible versions without migration. No new routes, views, or frontend changes.

### B1 failure and provenance boundaries

Action failure or invalid/failed post-observation produces no reward update or successful experience pair. Through `run()`, errors become ERROR telemetry/runtime and storage/lock close. No incomplete transition is synthesized, replayed, or filled with predictions after restart. Pre-action decision/action events remain inspectable; a completed action can legitimately exist without a completed transition if its following observation fails.

The episode+transition pair is atomic, verified with a failing SQLite insert trigger. This does **not** make the entire cycle transactional: reflection/consolidation can commit effects before later failure, and the existing learner commits its Q update before the pair is written. Thus a later storage failure may retain that Q update without the experience pair; the error propagates and stops the runtime, rather than silently continuing or claiming successful cycle completion. B1 preserves the existing learner storage API and limits its new atomic guarantee to the requested experience pair.

Owner observe/reflect/consolidate still use existing command, episode, and audit behavior, with no transition and no policy update. A historical or owner episode without a transition is valid; it is not evidence of corruption. No live installed memory was accessed or migrated, no app was installed/restarted, and no new listener was started.

### B1 test evidence and B0 test adaptations

New coverage:

- `tests/test_transition_migrations.py`: fresh→v2, legacy→v2, populated v1→v2, reopen/no new backup, failed backup, failure in v2 SQL rolling back v1→v2 and both legacy steps, and ambiguous/future schema rejection before mutation. Representative rows from **all 13 existing tables** (`meta`, `episodes`, `q_values`, `concepts`, `events`, `runtime`, `concept_evidence`, `commands`, `annotations`, `settings`, `automations`, `automation_runs`, `audit`) are compared exactly. Backups contain their original version and rows.
- `tests/test_transitions.py`: observed numeric/boolean/unchanged/missing/None/added/removed fields, invalid JSON/nonfinite observations, numeric overflow, snapshot detachment, exact persisted fields/NULLs/link, pair rollback, and historical reads.
- `tests/test_transition_cycle.py`: all four actions with real learner/storage and deterministic traces; deliberately different before/after reward contexts prove reward still uses before. A reused sensor dictionary proves snapshots cannot overwrite provenance. Action/second-observation failure leaves Q unchanged and no success records; owner commands never enter the transition table.
- `tests/dashboard/test_interaction.py`: a claimed-v2 database without transitions is rejected for operator mode.

Exactly these B0 fixture/assertion adaptations were needed:

1. `test_current_cycle_records_learning_before_action` became `test_b1_cycle_moves_legacy_learning_after_action_and_second_observation`. Expected telemetry order now includes the second perception and learning after action; original .655 Q result and delay remain asserted.
2. `test_start_wait_heartbeat_stop_and_restart_preserve_identity` expects three perceptions (startup + two per cycle), previously two. All lifecycle/identity/stop assertions remain.
3. `tests/baseline_scenario.py` supplies each of the eight original decision contexts twice, for before/after. Its tests keep every original hand-calculated policy and lifecycle assertion and add eight transitions/sixteen autonomous perceptions. Standalone CLI remains tested. The B0 JSON is unchanged.

No tests removed, skipped, or excluded. RED runs reproduced missing v2/backup behavior, missing transition helpers/storage, old cycle ordering/early learning, and incomplete operator schema guard before the implementations passed. Current full-suite result: **138 passed, 2 existing upstream deprecation warnings**. Independent review approved with no findings; final verification results are recorded below.

### B1 baseline comparison

Artifact: `docs/baselines/seed-0.2-b1-comparison.json`. The B0 JSON SHA256 is recorded to anchor the comparison; B0 JSON itself is immutable. Run `.venv/bin/python -m tests.baseline_scenario` for the current controlled simulation.

All nine comparable B0 metrics are identical: eight autonomous experiences; actions observe 4/reflect 1/consolidate 1/rest 2; two contexts; five Q rows; zero concepts; lifecycle wake 1/experience 8/sleep 1; exact stored Q values and visits; action sequence; returned intervals. B1 additionally has eight linked transitions and sixteen autonomous PERCEPTION events. In this environment the checkpointed database grows from 118,784 bytes (29 pages) to 147,456 bytes (36 pages), page size 4,096; WAL/SHM zero after close. Physical sizes vary with SQLite/platform and are measurements, not universal thresholds.

Unchanged source verified against `b6d7a28`: learner (state keys, actions, epsilon/alpha defaults, reward and Q equation), sensors, configuration, commands, core lock, telemetry helpers, and main process entry point. Owner controls, loopback/security tests, standard-library-only core, and inferred wake threshold retain their B0 coverage. Schema, experience ordering, perception frequency, linked persistence, and learning timing changed intentionally. No policy/intelligence improvement is claimed.

### B1 resource costs and limitations

- Normal autonomous perception calls increase **1→2 per cycle**. Each performs the existing pmset query, disk/load/time/platform reads, and fixed 1.1.1.1:443 TCP reachability probe. Thus normal probes increase **1→2 per cycle**; no new destination or kind of network operation is added. Each additional perception can incur the existing pmset timeout (2s) plus network timeout (1s), aside from ordinary OS-call time. Total cycle duration can increase; configured post-cycle intervals are unchanged, so probes per wall minute need not exactly double. Startup/inferred-wake observations are additional and unchanged. Tests/simulation replace sensors and never probe the public network.
- Rest's transition ends with the **immediate** second observation before the scheduled longer wait. It does not measure the consequence of the full rest interval or sleep. Other observed differences are also correlations, not attributed causes.
- Existing charging parser false-positive for “discharging” remains unchanged and characterized.
- Wake inference still uses a wall-clock cycle-start gap >45s; long work/intervals can look like resume. Start/completion timestamps are raw wall time; clock adjustment can make them non-monotonic, so they must not be treated as guaranteed elapsed-duration measurements.
- No predictor, prediction error, curiosity, world model, self-model, utility redesign, semantic consolidation, new autonomous tools, or development UI exists. Prediction columns are NULL; no fake zero scores.
- Full cycle atomicity is not claimed (see failure boundary above). Unknown sensor values stay unknown; JSON validation does not calibrate sensors or correct existing numeric-field assumptions in the unchanged learner.
- Installed app remains untouched and may still use legacy schema. Operator mode requires the current schema; observer reads of historical memory remain supported. No deployment approval is implied by passing fixture tests.

### B2 prerequisites

B2 needs explicit authorization and a scoped prediction design: supported signals, observation horizon (B1 currently immediate post-action), cold-start and missing-value policy, evidence/uncertainty meaning, model version/provenance, and deterministic evaluation without future-state leakage. The v2 transition link and nullable prediction columns provide storage groundwork only. Account for the existing charging defect and increased sensing cost when selecting/evaluating signals. B2 must not be started by this B1 task.

### B1 final acceptance — VERIFIED

Files changed (15):

- Core: `seed/migrations.py`, `seed/memory.py`, `seed/organism.py`, new `seed/transitions.py`.
- Compatibility guard: `dashboard/app.py`.
- New regressions: `tests/test_transition_migrations.py`, `tests/test_transitions.py`, `tests/test_transition_cycle.py`.
- Existing tests/control: `tests/dashboard/test_interaction.py`, `tests/test_baseline_lifecycle.py`, `tests/baseline_scenario.py`, `tests/test_baseline_scenario.py`.
- Documentation/artifact: `docs/seed-0.2-development-plan.md`, `docs/superpowers/plans/2026-09-22-seed-b1.md`, `docs/baselines/seed-0.2-b1-comparison.json`.

Final checks:

- `.venv/bin/python -m pytest -q`: **138 passed, 0 skipped/excluded, 2 upstream warnings** (Starlette/httpx and AnyIO aliases, unchanged from B0).
- `.venv/bin/python -m tests.baseline_scenario`: successful deterministic run, eight linked transitions and all nine comparable B0 metrics unchanged.
- `.venv/bin/python -m compileall -q seed dashboard tests`: passed.
- `git diff --check`: passed. New files also checked for trailing whitespace; JSON parses and contains no actual host/user/path/private-memory data.
- B0 learner/sensor/config/command/runtime/telemetry/entry-point sources and original baseline JSON match `b6d7a28` byte for byte.

Independent read-only review approved the implementation with **no Critical, Important, or Minor findings** and independently reproduced 138 passing tests. Review scope decisions are explicit:

1. Whole-cycle atomicity remains outside the focused pair invariant; retained Q/action effects on later failure are documented. Cost: failed cycles can leave policy/action effects without a complete transition, requiring inspection rather than replay.
2. Real sensor accuracy/latency and live migration were not exercised; synthetic fixtures preserve the owner's installed memory. Cost: deployment and real-device behavior still require separately authorized verification; charging defect remains.
3. Rest outcomes end before its scheduled wait, as authorized. Cost: these records cannot evaluate the environmental consequence of a full rest interval.
4. Arbitrary future nested sensor formats and hostile internal API calls were not introduced as supported contracts; current Body emits flat JSON primitives and the core owns persistence. Cost: expanding that boundary requires new validation/tests.
5. No policy-improvement evaluation was performed or claimed. Cost: this batch supports architectural comparison only.
6. Review did not certify final tracker/commit cleanliness; those are the implementer's delivery checks recorded here and verified after committing.

Commit scope: the 15 files above are committed on `seed-0.2-b1` as `seed-0.2 B1: add transition-based experience`, retaining the owner's existing B0 merge ancestry. No automatic merge or push. No installed schema change. Source rollback alone after a future deployment would not downgrade schema v2: restore the verified pre-upgrade backup only through an authorized recovery process, preserving the newer database separately if recovery is ever needed.

**Ready for B2: YES**, with no B1 acceptance blocker. Explicit B2 authorization remains required. Stop here.


## B2 execution log — 2026-09-22

Status: VERIFIED. Branch: `seed-0.2-b2`, already created at `845416c` (merged B1, tree identical to verified `858a483`). Working tree initially clean. Initial full suite: 138 passed, no skipped/excluded tests, two existing dependency warnings.

Objective: deterministic prospective environmental expectations targeting `next_post_action_observation`. Implementation plan: `docs/superpowers/plans/2026-09-22-seed-b2.md`; native execution follows the owner's approved B2 instruction.

Architecture decision: B2 prediction is action-conditioned but does not influence the B1 contextual-bandit policy. This permits prospective outcome modeling now while preserving experimental isolation; future authorized decision-system work may reuse it for candidate-action evaluation. B2 confidence represents evidence support, not calibrated predictive accuracy.

Source mapping: the existing sensor key is `network`; B2's prediction target `network_reachable` reads it directly. Do not change stored observation keys, add targets/probes, or infer unavailable current values. Schema remains v2. Preserve the B1 failure boundary: episode+transition+prediction commit together, but earlier Q/action effects are outside that transaction.

### B2 model and evidence contract

`seed/predictor.py` adds `Predictor(memory).predict(state_before, action) -> Prediction`. A frozen dataclass carries a plain model/version/horizon/action/signals contract; `to_dict()` detaches it for telemetry and persistence. Model **transition_delta_v1**, version **1**; horizon **next_post_action_observation**, belonging to the same selected autonomous transition. Inference has no clock or random input and no learned mutable model state.

Targets are **battery_pct, load_ratio, disk_free_pct, network_reachable**. The forecast target network_reachable explicitly reads the existing observation key **network**. No new sensor target/source or observation alias is added. Historical B1 transitions without predictions are valid evidence; no old prediction is generated or rewritten.

One SELECT reads **at most 200 most recently inserted completed transitions**, ordered by descending primary key. B1's table contains completed records only. Raw rows are bounded before parsing; invalid rows consume that window, so sparse/corrupt evidence cannot trigger a lifelong search. Only action/before/after fields are read, not predictions or outcomes. No new indexes or migration are needed.

For each numeric target independently:

1. Require usable current value; otherwise emit unavailable with missing/invalid-current reason, no value, evidence_count 0, confidence 0.
2. Validate historical before and after: actual int/float (booleans excluded), finite; battery/disk in 0..100; load >=0. Skip malformed JSON, non-dictionaries, missing/None/wrong-type/out-of-range values. Extra unrelated fields do not become targets.
3. Compute valid historical deltas after−before. Prefer selected-action evidence with **at least 2 samples** (`action_mean_delta`); otherwise all-action evidence with **at least 2** (`global_mean_delta`); otherwise current-value `persistence`, with no historical support claimed.
4. Predict current + mean delta. Mean accumulation normalizes by maximum absolute delta before summing, avoiding overflow even for three maximal finite deltas. Clamp percentages to 0..100 and load to >=0. If positive load addition exceeds floating-point representability, cap at the largest finite float; `clamped` records a changed result. This is a serialization safeguard, not a new sensor upper bound.

Network requires an actual boolean current `network` value; missing/invalid current remains unavailable regardless of history. Historical evidence uses actual boolean **state-after** network values; its state-before network value need not exist. Apply the same action/global two-sample threshold (`action_boolean_frequency` / `global_boolean_frequency`), calculate probability_true=count_true/n, and predict True for probability >=0.5, including ties. Persistence copies the current boolean, with no fabricated empirical probability.

Every signal's confidence is labeled **confidence_kind=evidence_support**: `min(0.95, evidence_count / 20)`. Persistence and unavailable signals have zero evidence/confidence. This is not calibrated accuracy, probability of numeric correctness, or a reward input. Boolean probability_true is a historical frequency, separate from confidence.

### B2 temporal integration and storage

The autonomous order is now before observation → decision → prediction → action → after observation → outcome → unchanged legacy reward → Q update → persistence. A PREDICTION event explicitly says “Prediction generated” and contains the model payload after DECISION and before ACTION start. It records expectations, not environment facts. No additional runtime fields or dashboard views are needed; existing generic telemetry provides inspection.

The dictionary serialized before action is passed directly to `record_transition_experience(..., prediction=prediction)` after completion. Storage serializes that payload without recomputing inference and inserts it in the existing prediction_json column within the same episode/transition transaction. Optional `prediction=None` preserves the old storage API and historical SQL NULLs. Prediction_error_json is never written and remains SQL NULL. Schema stays **version 2**, with migration code byte-for-byte unchanged.

Prediction generation itself performs only the bounded SELECT and in-memory calculations: no database writes, sensing, sockets, DNS, subprocesses, or random draws. Telemetry is emitted by the cycle afterward. Policy choice already happened and never consumes the prediction; reward still receives state-before/action only, and alpha/Q/delay/reflect/consolidate logic remains unchanged. Owner commands retain their B1 provenance and do not invoke the autonomous predictor.

If action or post-observation fails, the pre-action prediction event may remain, but no completed transition/prediction pair is fabricated. Prediction errors are not evaluated, including on failure. The B1 transaction boundary is unchanged: earlier Q or action effects can survive a later pair-write failure; there is no broad transactional redesign or automatic replay.

### B2 tests and changes to existing expectations

- New `tests/test_predictor.py`: cold-start contract/determinism, hand-calculated -1/-2/-1 deltas, action-specific patterns and global fallback, per-signal threshold, boolean frequencies/majority/tie, current unavailable despite history, malformed/missing/None/nonfinite/invalid historical values, signal bounds, finite extreme arithmetic, 200-row cutoff and confidence cap. Invalid recent rows cannot cause searching beyond the bound.
- Inference-only tests deny SQLite writes through an authorizer, compare every persistent row before/after, and forbid sensor/socket/DNS calls while actual inference runs. Test fixtures use synthetic observations and temporary databases only.
- New `tests/test_prediction_cycle.py`: trace actual core/learner/storage order, change historical evidence during action and use distinct post-state to detect any late recomputation, compare persisted JSON exactly with the pre-action payload/event, verify two perceptions, prove all four policy/reward/Q/delay outcomes remain unchanged under contradictory forecast payloads, simulate pair-write rollback, and reopen old B1 NULL predictions without backfill. Prediction errors remain NULL.
- Existing `tests/test_baseline_lifecycle.py` adds PREDICTION between DECISION and ACTION; learning/action phase assertions retain their original meaning. Existing `tests/test_transition_cycle.py` now expects prediction_json populated for new autonomous cycles while continuing to require NULL prediction errors. Direct B1 storage tests still verify NULL when no prospective prediction was supplied. No tests removed, skipped, or excluded.
- `tests/baseline_scenario.py` and its regression add structural counts from prediction payloads only. This helper does not read actual state-after to evaluate predictions.

RED runs demonstrated the absent predictor, missing invocation/storage argument, absent structural counts, and the review's extreme-float mean failure before fixes. Existing B1 event/NULL assertion failures were the explicitly intended B2 changes above, not hidden exclusions.

### B2 structural evaluation and B1 comparison

Safe artifact: `docs/baselines/seed-0.2-b2-comparison.json`, anchored to verified commit `858a483` and the SHA256 of the unchanged B1 comparison artifact. Reproduce with `.venv/bin/python -m tests.baseline_scenario`. The synthetic sequence and paired observations are unchanged from B1.

| Structural metric | Eight-cycle result |
| --- | --- |
| Completed prediction payloads | 8 |
| Target opportunities / predicted / unavailable | 32 / 32 / 0 |
| Prediction coverage | 100% in this fully populated synthetic fixture only |
| Action-specific methods | 8 signal predictions |
| Global fallback methods | 16 signal predictions |
| Persistence methods | 8 signal predictions |
| Evidence counts for each of the four targets, in cycle order | 0, 0, 2, 3, 4, 5, 6, 7 |
| Non-NULL prediction-error records | 0 |

All **11 comparable B1 metrics** match exactly: observations, action distribution, context coverage, policy coverage, concept count, lifecycle counts, Q values/visits, action sequence, returned delays, transition count, and autonomous perception count. The control still has eight transitions, two contexts, five Q rows, and sixteen autonomous perceptions. No accuracy/error, surprise, curiosity, or improvement measurement is computed or claimed.

Measured checkpointed DB footprint is 172,032 bytes (42×4,096-byte pages), versus B1's 147,456; WAL/SHM zero after close in this environment. This reflects stored payloads/events and is not a universal size/performance threshold. Algorithm cost is one bounded 200-row read/parse and four target calculations per cycle; history accumulation creates no additional learned model state.

### B2 limitations and B3 prerequisites

- Confidence is evidence support, not calibrated predictive accuracy. Action association is not causal attribution. A recent global fallback may combine unlike contexts; no context/world-model conditioning was added.
- The horizon is the same immediate post-action observation as B1. Rest predictions do not cover the later rest interval. No extra perception: still **two per normal autonomous cycle**, each with the existing network probe; predictor itself adds **zero** network operations.
- The charging parser defect, inferred wake timing, and B1 partial-cycle persistence limitation remain unchanged. Existing learner/snapshot validation assumptions also remain: predictor tolerance does not redesign the learner's handling of malformed live observations.
- SQL/storage failures still use the existing core error handling; invalid individual historical sensor/JSON values are skipped. The fixed row window bounds history size, not arbitrarily malicious individual JSON blob sizes.
- No B3 prediction-error/accuracy scoring, B4 beliefs, curiosity, semantic inference, self-model, planning, LLM, new tools, sensor changes, or UI work. No live installed memory access, deployment, restart, or new listener.
- B3 requires explicit authorization and a defined evaluation contract: supported actual-value mapping (network_reachable→network), availability/missing/invalid policies, per-signal units and any normalization, correct transition/model/horizon linkage, deterministic scoring and persistence rules, and whether already-stored prospective B2 records may be evaluated. B1 NULL predictions must remain distinguishable from unavailable B2 signals and from any legitimate zero-valued future score.

### B2 review evidence

Independent read-only review found one Important numerical issue and no Critical or Minor findings: three maximal finite load deltas could overflow the original scaled-sum mean. A real SQLite regression reproduced `OverflowError` before the fix; max-absolute normalization fixes both positive and negative three-sample extremes. The fix preserves ordinary hand-calculated results and adds no policy/error behavior. Final full-suite verification below supersedes the review's pre-fix verdict; no second review was requested.

Review scope decisions:

1. Whole-cycle atomicity and charging parsing remain expressly excluded B1 limitations. Cost: a failed persistence step can retain earlier effects; charging evidence retains its known defect.
2. Prediction accuracy is deferred by the B2 instruction. Cost: coverage/support are not evidence that forecasts are useful.
3. Final tracker/artifact/commit verification belongs to this task's delivery checks. Cost if omitted: unsupported completion claims; the checks below supply the evidence.
4. Network spelling is an explicit mapping, not a sensor expansion. Cost: B3 must use the documented mapping to evaluate the correct observation field.
5. The actual prediction path detaches one dictionary; neither telemetry nor action code mutates it. No additional immutable nested-object framework is introduced. Cost: future mutating consumers require snapshot-integrity tests.
6. The completed-record table contract makes a bounded latest-row query sufficient; no redundant historical completion filtering is added. Cost: a future pending-transition schema must revise eligibility and tests.

### B2 final acceptance — VERIFIED

Files changed (12):

- `seed/predictor.py`: new bounded statistical inference module and explicit prediction contract.
- `seed/organism.py`: prediction call/telemetry after decision and before action, passing the same payload to persistence.
- `seed/memory.py`: optional prediction serialization in the existing atomic experience insert.
- `tests/test_predictor.py`, `tests/test_prediction_cycle.py`: new algorithm, safety, ordering, isolation, and persistence regressions.
- `tests/test_baseline_lifecycle.py`, `tests/test_transition_cycle.py`: minimal B2 event/prediction expectation updates.
- `tests/baseline_scenario.py`, `tests/test_baseline_scenario.py`: structural metric capture and deterministic expectations.
- `docs/baselines/seed-0.2-b2-comparison.json`: safe reproducible structural comparison, no accuracy claims.
- `docs/superpowers/plans/2026-09-22-seed-b2.md`, `docs/seed-0.2-development-plan.md`: implementation plan and canonical batch record.

Final verification:

- `.venv/bin/python -m pytest -q`: **182 passed, 0 skipped/excluded, 2 existing upstream warnings**. The review finding's positive/negative extreme regressions pass with all normal-value tests.
- `.venv/bin/python -m tests.baseline_scenario`: standalone CLI remains covered in the suite; a fresh temporary control run after the fix exactly reproduces the B2 comparison artifact.
- `.venv/bin/python -m compileall -q seed dashboard tests`: passed.
- `git diff --check` and explicit whitespace checks including new files: passed. JSON parses; comparison artifact contains no real username, local path, private memory, or credentials.
- Byte comparisons against `858a483`: learner, sensors, configuration, commands, core lock, migrations/schema, transition outcome helpers, telemetry helpers, entry point, and both B0/B1 artifacts unchanged.
- Independent review's one Important issue addressed by a demonstrated failing test and green full suite; no deferred Critical/Important/Minor findings.

Git delivery: retain existing branch `seed-0.2-b2`, based on merged B1 `845416c`; commit the 12 scoped files as `seed-0.2 B2: add prospective environmental predictor`. No automatic merge or push. Commit identity and clean-tree check are reported after commit. Installed memory remains untouched. No schema migration added.

**Ready for B3: YES**, no B2 acceptance blocker. B3 is not started and requires explicit authorization. Stop here.


## B3 execution log — 2026-09-22

Status: VERIFIED. Branch `seed-0.2-b3` created from verified B2 `008b704`; initial tree clean, baseline `.venv/bin/python -m pytest -q`: 182 passed, 0 skipped/excluded, two existing dependency warnings. Plan: `docs/superpowers/plans/2026-09-22-seed-b3.md`; native execution continues under the approved B3 design.

Objective: pure deterministic evaluation of the original prospective prediction after actual post-action observation. Architectural decisions: evaluate only after target observation; never feed errors into policy/reward; average only evaluated normalized errors with coverage tracked separately; preserve confidence as B2 evidence support. No rolling API/UI is needed to satisfy B3; inspect persisted records/telemetry and the deterministic artifact. Schema remains v2 and historical B1/B2 records remain unchanged.

### B3 evaluator contract and scoring

`seed/prediction_error.py` provides pure `evaluate_prediction(prediction, actual_state) -> PredictionEvaluation`; `to_dict()` produces the plain payload. Evaluator **prediction_error_v1**, version **1**, records the supported prediction model/version and horizon. Current supported input is B2 `transition_delta_v1`, model version 1, horizon `next_post_action_observation`; unknown/malformed metadata produces not-evaluated signals rather than silently reinterpreted scores. The ordinary core path supplies a dictionary. Direct evaluation also accepts serialized prediction JSON up to 16,384 characters, safely rejecting malformed/deep/oversized strings. Extra dictionary fields are not traversed or copied; scoring visits exactly four targets and never queries history.

Numeric targets retain the B2 physical domains: finite int/float, booleans excluded; battery/disk 0..100, load >=0. Out-of-domain or unrepresentable values are unavailable, not clamped into a false comparison. For valid pairs:

- `signed_error = actual - predicted`; positive means actual higher, negative means actual lower.
- `absolute_error = abs(signed_error)`.
- Battery/disk normalized error = absolute error / 100, bounded to 0..1; raw absolute error is in percentage points.
- Load normalized error = absolute error / max(1, abs(predicted), abs(actual)), bounded to 0..1. Load error remains in load-ratio units, not CPU percentage. The denominator is persisted implicitly through the versioned `bounded_relative` rule.
- Non-finite intermediate results are not evaluated; no NaN/Infinity is serialized. Tests exercise both directions between zero and the largest finite float, as well as oversized integers and invalid ranges.

For `network_reachable`, read actual observation key **network** and require exact booleans on both sides. Store correct and classification_error (0/1). If the original forecast has a valid finite nonboolean probability_true in 0..1, use Brier error `(probability_true - int(actual))²` as normalized error (`boolean_brier`). Otherwise use classification error (`boolean_mismatch`), omitting probability/Brier fields. Do not invent probability for persistence or echo malformed probability values. Classification and probabilistic error are distinct even if the Boolean classification is correct.

Each target appears in the output. Unavailable prediction → `not_evaluated / prediction_unavailable`; malformed prediction → `not_evaluated / invalid_prediction`; unusable actual → `not_evaluated / actual_unavailable`. These records contain no zero-valued substitute score. Unavailable prediction takes precedence when both sides are absent.

Aggregate only evaluated targets: arithmetic mean of normalized errors, accuracy_score = 1−mean, both bounded to 0..1. Coverage = evaluated count / **4**, independent of the score. With none evaluated, status=unavailable, evaluated_signals=0, target_signals=4, coverage=0, mean_normalized_error=null, accuracy_score=null.

**accuracy_score is an engineering summary over heterogeneous normalized signal errors, not a calibrated probability of correctness.** One perfectly scored available target has accuracy_score 1 but coverage .25. B2 confidence remains evidence support and is neither rewritten nor calibrated by B3.

### B3 cycle, telemetry, persistence, and isolation

After post-action sensing and outcome derivation, the cycle evaluates the exact dictionary generated before action. Predictor is called **once** and is never rerun to score outcomes. PREDICTION_ERROR telemetry follows post-action PERCEPTION and precedes the unchanged legacy reward/Q update. The evaluator result is passed directly to storage; neither prediction nor error is recomputed during serialization.

`record_transition_experience(..., prediction_error=None)` adds one optional parameter, serializing before the transaction and using the existing prediction_error_json column. Episode, transition, prediction, and evaluation persist together; injected insertion failure rolls the entire pair back. Default None preserves old callers and historical NULLs. Tests reopen representative B1 (both NULL), B2 (prediction only), and B3 (both populated) records and compare older rows exactly. No backfill, schema change, migration, or new table is introduced; schema remains **2**.

Evaluation is calculation only: no database access, sockets, DNS, sensors, randomness, or state changes. Tests deny database actions/connections and sensing/network entry points and verify unchanged inputs and persistent rows. Normal autonomous cycles retain two perceptions and one prospective prediction. Earlier B1 action/Q/telemetry effects may survive a later persistence failure; the new atomic guarantee remains the linked experience pair, not the whole physical cycle.

Error is never used for action choice, candidate ranking, epsilon, alpha, reward, Q values, delay, reflection/consolidation, annotations, or importance. Two controlled runs for each of the four actions produce zero versus nonzero evaluation errors while their decision provenance, reward, Q/visits, and delays are identical. Owner commands retain their existing provenance. No world model, curiosity, novelty/attention mechanism, semantic inference, self-model, calibration, planning, new tool, or UI is implemented.

### B3 metric vocabulary and fixture

Metrics are defined without adding a production rolling-summary API:

| Metric | Definition and denominator |
| --- | --- |
| Prediction availability coverage (B2) | Predicted targets / four target opportunities per transition; distinct from evaluation coverage |
| Evaluation coverage | Evaluable prediction/actual pairs / 4; absent targets reduce coverage, not accuracy |
| Mean normalized error (one transition) | Equal-weight arithmetic mean of available target normalized errors |
| Transition accuracy_score | 1−mean normalized error; unavailable if no target can be scored |
| Mean normalized error/score across a fixture | Mean of the corresponding scores for transitions with at least one evaluated target; report scored-transition count separately |
| Mean coverage | Mean coverage across all fixture transitions, including zero-coverage ones |
| Battery MAE | Mean absolute battery error in percentage points over evaluated battery pairs |
| Load-ratio MAE | Mean absolute load-ratio error over evaluated load pairs |
| Disk-free MAE | Mean absolute disk-free error in percentage points over evaluated disk pairs |
| Network classification accuracy | Fraction of evaluated Boolean predictions whose class matches actual |
| Network mean Brier error | Mean squared probability error over evaluated network pairs with a valid original probability; exclude mismatch-only cases |

For all signal summaries, report sample count, exclude not-evaluated records, and use null when no samples exist. B1 NULL predictions and B2 NULL errors are outside the B3 evaluation era, never successes or failures.

Deterministic chain: `.venv/bin/python -m tests.prediction_error_scenario`. Each of three independent temporary homes starts with two known completed historical transitions, then uses the real predictor, cycle, evaluator, and storage against fixed current/future observations. Clock/random selection/sensing are replaced with fixed values; no real sensors, network, installed database, or random outcome. The safe artifact is **`docs/baselines/seed-0.2-b3-evaluation.json`**, anchored to `008b704` and the B2 artifact hash.

The common prospective prediction is battery 73, load .4, disk 49, network True with probability .5. Three cases:

| Case | Actual values | Evaluation |
| --- | --- | --- |
| Full | battery 71, load .6, disk 48, network False | normalized errors .02/.20/.01/.25; mean .12; accuracy_score .88; coverage 1 |
| Partial | battery 73 only | one perfect target; score 1; coverage .25 |
| Unavailable | no valid target values | no evaluated targets; score/error null; coverage 0 |

Across this fixture: 3 transitions, 2 scored; mean coverage 5/12; mean normalized error .06 and mean accuracy_score .94 across the two scored transitions. Battery MAE 1 percentage point (2 samples), load MAE .2 (1), disk MAE 1 percentage point (1), network classification accuracy 0 (1), network mean Brier .25 (1). These intentionally selected cases verify arithmetic/availability, not general predictive performance or improvement.

The separate original eight-cycle control still matches all **11 B2 control metrics**, including Q values, actions, delays, transition count, and sixteen perceptions. Prediction availability/method/evidence counts are unchanged. It now has eight populated evaluations. Checkpointed control DB size in this environment is 180,224 bytes (44×4,096), versus B2's 172,032; WAL/SHM zero after close. This is a measurement, not a cross-platform threshold.

### B3 tests and prior-test adaptations

- `tests/test_prediction_error.py`: literal numeric/Boolean/Brier arithmetic, sign and normalization, full/partial/none aggregation, model/version/horizon guards, malformed/oversized/deep JSON, missing/None/wrong-type/nonfinite/pathological numbers, invalid probability fallback, extra fields and purity/IO isolation.
- `tests/test_prediction_error_cycle.py`: explicit order including outcome/evaluation; exactly one predictor call; exact payload/event/storage equality and episode link; four-action policy isolation under differing errors; atomic rollback and B1/B2 historical preservation.
- `tests/prediction_error_scenario.py` with `tests/test_prediction_error_scenario.py`: actual history→prediction→observation→evaluation→storage fixture and standalone CLI, expected metric denominators/results.
- Existing lifecycle and prospective-cycle event assertions add PREDICTION_ERROR after post-PERCEPTION. Existing new-cycle NULL assertions now require evaluator payloads; the B2 isolation test's deliberately unsupported fake model produces an unavailable evaluation. Historical/default-storage NULL assertions remain intact. Original control expects eight errors instead of zero; all policy/support assertions remain unchanged.

RED runs reproduced the absent module, missing evaluator invocation, missing storage parameter, and absent fixture before implementation. No tests were removed, skipped, or excluded.

### B3 independent review and retained boundaries

Independent read-only review found **no Critical, Important, or Minor issues** and independently passed all **70 B3-specific tests** plus diff checks. No fixes or deferred findings remain. Review scope rulings:

1. Whole-cycle atomicity stays at the explicit B1 boundary; cost: earlier Q/action/telemetry effects may outlive failed pair persistence.
2. Optional rolling metrics API/runtime fields/frontend are omitted; cost: inspection uses stored telemetry/artifact rather than new dashboard summaries.
3. B4 learning/calibration and behavioral feedback remain prohibited; cost: B3 makes errors measurable but does not use them to improve behavior.
4. Final docs/artifact/commit/clean-tree evidence is supplied by the parent delivery checks below, not implied by code-review approval.
5. Live sensors and installed memory are untouched; cost: fixture verification does not certify deployment/real-device behavior.

Known existing limitations remain: rest horizon is immediate before the longer wait; charging parser can misclassify discharging; inferred wakes rely on wall-clock gaps; whole-cycle atomicity is incomplete; the two normal perceptions each perform the existing fixed reachability probe. Evaluation adds no probes or perceptions. Predictor/evaluator tolerance does not rewrite B1 live-state validation or learner input assumptions. Mixed normalized scores are engineering conventions and equal-weight missing-signal averages require coverage to be read alongside the score.

### B4 prerequisites

Explicit authorization and a scoped world-model design are required. Define evidence selection/linkage to actual observations, belief representation and versioning, bounded update/replay behavior, contradiction handling, any additive schema/backup requirements, and the distinction between observation correlation and causal claims. Preserve prediction/evaluator provenance and unknown/NULL historical semantics. B3's accuracy_score must not be relabeled as belief confidence; any later confidence meaning requires its own definition and tests. No B4 work began.

### B3 final acceptance — VERIFIED

Files changed (14):

- Core: `seed/prediction_error.py`, `seed/organism.py`, `seed/memory.py`.
- New tests/fixture: `tests/test_prediction_error.py`, `tests/test_prediction_error_cycle.py`, `tests/prediction_error_scenario.py`, `tests/test_prediction_error_scenario.py`.
- Existing expectation updates: `tests/test_baseline_lifecycle.py`, `tests/test_baseline_scenario.py`, `tests/test_transition_cycle.py`, `tests/test_prediction_cycle.py`.
- Records: `docs/baselines/seed-0.2-b3-evaluation.json`, `docs/superpowers/plans/2026-09-22-seed-b3.md`, `docs/seed-0.2-development-plan.md`.

Verification:

- `.venv/bin/python -m pytest -q`: **252 passed, 0 skipped/excluded, 2 existing upstream dependency warnings**.
- `.venv/bin/python -m tests.prediction_error_scenario`: standalone fixture CLI verified by the suite; artifact regenerated from the same real fixture and hand-calculated expectations tested.
- Original eight-cycle scenario compared with B2: all 11 policy/control metrics and prediction-support counts unchanged; eight new evaluations.
- `.venv/bin/python -m compileall -q seed dashboard tests`: passed.
- `git diff --check` plus explicit new-file whitespace/JSON checks: passed.
- Byte comparison to `008b704`: predictor, learner, sensors, config, commands, core lock, migrations/schema, transition outcome helper, telemetry helpers, main entry point, and all B0/B1/B2 baseline artifacts unchanged.

Git scope: dedicated `seed-0.2-b3` from `008b704`, with these 14 files committed as `seed-0.2 B3: evaluate prospective prediction error`. No automatic merge/push. Commit identity and clean working tree are checked after commit. No live memory opened/migrated, no installation/restart, and no listener started.

**Ready for B4: YES**, with no B3 acceptance blocker. B4 remains NOT STARTED and requires explicit authorization. Stop here.
