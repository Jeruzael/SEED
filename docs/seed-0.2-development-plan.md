# SEED 0.2 — Developmental Core

Canonical roadmap and batch tracker. Initialized **2026-09-21** from the owner's SEED 0.2 master development instruction and inspection of the current checkout.

**Current authorization: owner approved B9 implementation after publication of the design cleanup.** B9 Astra is **IMPLEMENTED on `seed-0.2-b9`**, with local tests/browser checks recorded below; final independent review is in progress. B0–B8 remain **VERIFIED at source/CI level**, schema v7. B9 hosted CI, merge and deployment are not claimed. B10 is **NOT STARTED**. Installed SEED remains **UNTOUCHED**. Historical design-only restrictions below describe earlier checkpoints and are superseded for implementation by the owner's subsequent instruction. See [B9 implementation](#b9-implementation--2026-09-30) and [B8 hosted closure](#b8-hosted-verification-closure--2026-09-29).

## Objective and architectural transition

SEED means **Situated Experiential Emergent Development**. Evolve the existing Germination prototype incrementally into a system that learns from observed consequences and prediction error, while keeping behavior inspectable, reproducible, and under owner control.

The B7 autonomous cycle in `seed/organism.py` is:

```text
perceive state_before
→ choose predefined internal action
→ predict immediate post-action observation
→ perform action (consolidate: one guarded bounded semantic run and checkpoint)
→ perceive state_after
→ describe observed differences
→ evaluate the original prediction against state_after
→ assess curiosity using a snapshot of prior published beliefs
→ calculate unchanged legacy reward from state_before
→ update contextual action value
→ atomically store episode, transition, prediction, evaluation, curiosity, and B4 eligibility
→ process at most 100 queued transitions into persistent descriptive world beliefs
→ optionally claim and perform one guarded existing internal reflection
→ publish one bounded descriptive self-model snapshot
→ record final runtime telemetry
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
| B4 | World Model | VERIFIED | B1, B3 | Full suite: 327 passed; independent review: 75 B4 tests passed | Schema v3; prospective persistent descriptive statistics; no behavioral influence |
| B5 | Prediction-Error Curiosity | VERIFIED | B3, B4 | Full suite: 426 passed; independent review found no issues | Schema v4; error-anchored salience; owner-controlled auxiliary reflection |
| B6 | Memory Consolidation | VERIFIED | B1, B4 | Full suite: 497 passed; review finding fixed and tested | Schema v5; bounded semantic revisions; original memories preserved |
| B7 | Self Model | VERIFIED | B3, B6 | 646 tests on Linux 3.11/3.13 and macOS 3.13; six scenarios on both 3.13 jobs; post-merge run 36104979944 | Schema v6; bounded descriptive singleton; no upstream influence |
| B8 | Decision-System Upgrade | VERIFIED | B5, B7 | 747 tests on Linux 3.11/3.13 and macOS 3.13; seven scenarios on both 3.13 jobs; post-merge run 36443249417 | Schema v7; exact B8 merge verified at source/CI level; deployment not performed |
| B9 | Astra Development UI | IMPLEMENTED | B0 and B1–B8 | Local Python3.13.15: 851 passed, 2 existing warnings; seven scenarios; temporary browser checks | Seven views and bounded readers; independent review in progress; hosted CI/deployment pending |
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

**Implemented v1 inputs:** Existing raw Q, prospective battery/load/disk risk, historical support uncertainty, and resource eligibility. Information gain, goal progress and other candidate inputs from the initial roadmap were excluded by the approved B8 design.

**Verification:** Decision inputs and selection-time values are inspectable; deterministic scenarios exercise resource constraints, missing predictions, conflicting signals, and fallback behavior. Q values remain compatible. New decision weights and utility meanings are explicitly specified and tested before behavior is described as improved.

### B9 — Astra Development UI

**Purpose:** Display actual developmental state through the local dashboard.

**Designed views:** Development, Predictions, World Model, Curiosity, Semantic Memory (including consolidation runs), Self Model, and Decisions. Astra extends the existing observer shell as a DEVELOPMENT section; Observer Edition 0.1 and the six existing observer views remain. The [specification](superpowers/specs/2026-09-29-b9-astra-development-ui-design.md) is OWNER APPROVED / COMPLETE at `3dc9b8fdab2f4c12227e2371e679a57a02a5cf6f`; implementation is NOT STARTED.

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


## B4 execution log — 2026-09-22

**Status: VERIFIED.** Branch: `seed-0.2-b4`. Starting commit: `b404035`, including
verified B3 `a51536e` and owner documentation updates. Initial tree was clean;
initial full suite: 252 passed, no skipped/excluded tests, two upstream warnings.
Native plan: `docs/superpowers/plans/2026-09-22-seed-b4.md`. The owner checkpointed
partial work in `24dca90` (`b4 partial implementation`) while execution was underway;
that checkpoint is preserved. Delivery commit is the commit containing this final
record, titled `seed-0.2 B4: add persistent world model`; its resolved hash is reported
in the completion report after Git verification. No merge or push is performed.

Objective: persistent statistical regularities from completed observations, with
inspectable evidence, contradictions and confidence. B4 adds no causal inference
and makes no intelligence, understanding, or predictive-improvement claim.

### B4 architecture decisions

1. World beliefs describe observed statistical regularities, not causal effects
   of actions. Action conditioning identifies the action selected during a transition.
2. Evidence eligibility is prospective and explicit: only B4 autonomous writes opt
   in. B1/B2/B3 transitions are never silently backfilled, regardless of timestamps.
3. Persistent beliefs are separate from the unchanged B2 on-demand predictor.
   Neither beliefs nor their confidence/counts are consumed by prediction or policy.
4. Confidence combines bounded evidence support with observed consistency; it is
   labeled `evidence_consistency`, not certainty or a truth probability.
5. Contradictory observations remain evidence, revise statistics, and increment
   contradiction counts; they are never discarded for disagreeing.

Legacy `concepts` remain reflection-derived summaries. B4 `world_beliefs` are
transition-derived persistent statistical models. Reflection and consolidation
remain byte-for-byte unchanged inside the existing organism methods.

### Schema v3 and preservation

The additive migration ladder is unversioned → v1 → v2 → v3, in one migration
transaction. Existing v1/v2 statements and prior tables are retained. Exactly one
supported integer schema row is required; future/ambiguous versions are rejected
before constructor schema writes. Current v3 reopen is a no-op.

Four new tables:

- `world_beliefs`: stable key and integer ID, signal, global/action scope and scope
  value, numeric_delta/boolean_frequency family, JSON value, evidence and
  contradiction counts, confidence, creation/update timestamps, first/last source
  transition IDs, and model version 1. Unique statistical identity and schema
  checks constrain supported scopes, signals, counts and confidence.
- `world_pending`: the same statistical representation for one valid sample.
  Pending samples persist across restart and are not returned as published beliefs.
  On the second valid sample, the accumulated statistics move into world_beliefs
  and the pending row is removed atomically. Creation time records first accumulated
  evidence; updated_at records the latest model processing time.
- `world_model_queue`: primary-key transition IDs eligible for prospective learning.
- `world_model_processed`: primary-key transition IDs, processing time, model version
  and valid-signal count; a compact durable idempotency/provenance ledger.

All source ID columns reference transitions. There is no migration backfill or
rewriting of episodes, transitions, prediction/error JSON, Q values, concepts,
identity, runtime, commands, settings, annotations, events, automations or audit.

`Memory` retains backup-before-migration for an existing legacy/v1/v2 database.
Tests compare every row in the fourteen prior application tables, including B1
NULL, B2 prediction-only, and B3 prediction+evaluation transitions. The v2 snapshot
retains schema 2 and exact rows. Failed backup prevents migration; injected failure
in the final v3 step rolls back every applied step for legacy/v1/v2 fixtures.
Existing future-version rejection and legacy preservation regressions also pass.

### Evidence, statistics, contradictions and confidence

`seed/world_model.py` reads only persisted source observations. Supported numeric
signals are battery_pct and disk_free_pct (finite nonboolean numbers in 0..100)
and load_ratio (finite nonboolean number >=0). Both before and after must be valid;
the sample is after−before. Boolean target network_reachable reads the existing
**after.network** sensor key and requires an exact Boolean. No new sensor is added.

Each valid signal contributes once to global scope and once to its selected action
scope (observe/reflect/consolidate/rest). There are at most 20 combined pending and
published statistical identities. Unknown actions provide no evidence. Two valid
samples for the particular signal/scope are required to publish a belief.

Numeric payload: mean_delta, mean_absolute_delta, min_delta, max_delta. Means use
incremental updates, with a convex weighted sum for opposite signs to avoid overflow
at finite load extremes; there is no history rescan or statistical dependency.
Boolean payload: true_count, false_count, probability_true; counts sum to evidence.
Both families persist confidence_kind=evidence_consistency.

Contradictions use **pre-update evidence_count >=4**:

- Numeric: mean > epsilon and new delta < −epsilon, or the reverse. Epsilons are
  battery .05 percentage points, disk .01 percentage points, load .02 ratio units.
  Equality and values inside the deadband are neutral.
- Boolean: probability_true >=.75 with new False, or <=.25 with new True. Interior
  probabilities are ambiguous and do not turn ordinary variation into contradiction.

Confidence = clamp(min(.95,n/20) × (1−c/n), 0, .95); n=0 gives 0. All contradictory
samples still increase n and revise the value. Confidence can plateau before the
support cap and decline as the contradiction ratio rises. There is no recency
weighting, forgetting, calibration, causal inference or prediction-error dependency.

Missing/None/wrong-type/nonfinite/out-of-domain fields are skipped per signal;
valid other fields still contribute. Serialized states are decoded independently,
limited to 16,384 characters, and malformed/deep/non-object states are unavailable.
An invalid before-state does not prevent a valid Boolean after-observation.
Processed records retain valid-signal counts, including zero; rejected fields are
not fabricated or retried indefinitely. Original transition JSON is not changed.

### Ordering, idempotency, atomicity and recovery

`Memory.record_transition_experience(..., world_model_eligible=False)` retains old
caller semantics. The autonomous cycle passes True; inserting the queue entry is
in the same transaction as episode+transition+prediction+evaluation. Queue insertion
failure rolls back the complete pair, so no uncommitted experience becomes evidence.
Owner command and historical/default callers do not opt in.

WorldModel.recover runs once during core construction and once after each successful
autonomous pair commit. Each pass selects **at most 100 queued IDs**, ascending, from
the dedicated queue. Normal no-backlog work processes the new transition only.
Source reads use the transition primary key, never a lifetime history scan. The
update visits at most four signals × two scopes.

WorldModel.observe_transition(id) takes the Memory lock and begins IMMEDIATE before
reading model state. Pending/belief revisions, small WORLD_MODEL events, processed
marker insertion and queue deletion commit atomically. A previously processed or
ineligible ID is a no-op. Out-of-order queued calls are refused, preserving the
meaning of pre-update contradictions across recovery. Concurrent connections cannot
double count the same source. Recovery passes are idempotent.

A model failure leaves the completed real transition and queue entry intact and
rolls back all model work. The existing core error path can stop the process; a later
restart retries eligible records. No hidden restart loop, skip-on-failure policy,
automatic rebuild, or historical replay utility is introduced. A corrupt internal
model row or persistent storage error can block FIFO progress and requires diagnosis.
As in B1–B3, actions/Q/other telemetry can commit before a later failure: the entire
physical cycle is not transactional.

### Telemetry and read-only inspection

WORLD_MODEL emits a per-belief event on creation, contradiction, statistical value
change, or confidence change. Payloads contain stable key, signal/scope, old/new
values and confidence, counts, change kind, and transition ID. Pending samples do
not emit belief events. At capped confidence, evidence/timestamp-only changes do
not emit events; Boolean raw count changes alone are also suppressed when frequency
is unchanged. Existing event retention applies. No full-model dump or anthropomorphic
message is emitted.

New observer routes:

- `GET /api/world-beliefs`: keyset `after`, limit 1..100 (default 50), optional signal,
  scope and scope_value filters, items and next_cursor. Only published beliefs appear.
- `GET /api/world-beliefs/{belief_id}`: value, provenance, counts, confidence and
  timestamps; missing IDs return 404; invalid/oversized IDs return 422.

The service validates direct callers too and uses SQLite mode=ro. Legacy inspection
returns available=false and no rows without migrating. Operator startup now requires
all four v3 tables and version 3. Local Host/Origin/token boundaries remain unchanged.
No frontend, new listener, runtime model dump, production aggregate-metrics endpoint,
or maintenance rebuild route is added.

### Deterministic metrics and baseline comparison

Reproduce: `.venv/bin/python -m tests.world_model_scenario`.
Artifact: `docs/baselines/seed-0.2-b4-comparison.json`, anchored to B3 `a51536e`,
starting commit `b404035`, the unchanged B3 artifact hash and unchanged core-source
hashes. All observations and homes are synthetic. Write timestamps are omitted
from deterministic belief snapshots; actual persisted rows still retain them.

The revision fixture supplies 20 positive numeric/True network transitions followed
by two negative numeric/False network transitions, all with action observe:

- One transition: 0 published beliefs, 8 pending statistics.
- At 20 samples: confidence .95.
- At 22 samples: 8 beliefs (2 per signal; 4 global and 4 action); every belief has
  evidence 22, contradictions 2, and confidence **0.8636363636363635**.
- Numeric mean delta 18/22, mean absolute delta 1, min −1, max +1.
- Network counts True 20, False 2; observed frequency 20/22.
- 22 processed transitions, **88 valid signal samples**; **176 scoped evidence** and
  **16 scoped contradictions** count the global/action duplication explicitly.
- 0 unprocessed eligible transitions. Counts describe development records, not
  knowledge or intelligence. Aggregate count queries occur only in the fixture,
  never during normal model updates or dashboard inspection.

The original eight-cycle control reproduces every B3 non-footprint metric exactly,
including all predictions/support counts, eight evaluations, action sequence, Q
values/visits, rewards/delays, concept count and 16 perceptions. The three B3 full,
partial and unavailable evaluation cases reproduce **every non-schema field** and
all aggregate metrics exactly; only schema changes from 2 to 3.

Checkpointed control database: **249,856 bytes**, 61 × 4,096-byte pages, zero WAL/SHM
bytes after close (B3: 180,224 bytes, 44 pages). This is a fixture measurement, not a
portable size/performance threshold. Statistical rows are bounded, but the durable
processed ledger grows by one compact row per eligible transition; detailed
transitions already grow with experience. A recovery backlog is not silently pruned.

### Tests, review, and isolation evidence

New test files/fixture:

- `tests/test_world_migrations.py`: v2 preservation/backup, final-step ladder rollback,
  failed backup and atomic prospective eligibility.
- `tests/test_world_model.py`: hand-calculated statistics, action/global scope,
  promotion/restart, contradiction boundaries, confidence rise/fall, invalid signals,
  extreme finite numbers, malformed JSON, duplicate/concurrent processing, model
  failure/retry, historical exclusion, FIFO recovery bounds and material telemetry.
- `tests/test_world_model_cycle.py`: post-commit timing, startup recovery without
  sensing/network, all-action predictor/evaluator/policy/reward/Q/delay equivalence,
  concept/evidence preservation, real cycle failure and restart recovery.
- `tests/dashboard/test_world_beliefs.py`: read-only pagination/filter/detail,
  validation, legacy empty state and missing-v3-table operator refusal.
- `tests/test_world_model_scenario.py` and `tests/world_model_scenario.py`: literal
  confidence/statistics fixture and comparison against the immutable B3 artifact.

Four prior test files change only supported-current-version assertions (and one
migration test name): test_transition_migrations.py, test_prediction_cycle.py,
test_prediction_error_cycle.py, test_prediction_error_scenario.py. All earlier
behavior, provenance, future-version, backup, sensor and owner-authority tests remain.

RED runs reproduced missing migration/queue/model/core/read paths before their
implementation. A final count-only Boolean telemetry regression was reproduced and
fixed without changing learning. Test-harness corrections addressed a chained
pytest.approx comparison, colliding fixture directories, local TestClient Host,
ServiceError type, and the saved artifact's `control` key; production rules were
not weakened to match those mistakes.

Independent fresh read-only review: **no Critical, Important, or Minor findings**;
reviewer independently ran **75 B4 tests**, all passing. Review boundary rulings:
optional rebuild/metrics/UI remain omitted; whole-cycle atomicity retains the
explicit earlier boundary; live deployment remains outside fixture verification.
No material or deferred review findings remain.

Final intended suite: `.venv/bin/python -m pytest -q` → **327 passed**, **0 skipped**,
**0 excluded**, **2 existing upstream deprecation warnings** (Starlette/httpx and
AnyIO aliases). Warnings were not suppressed; dependencies were not upgraded.
Standalone world-model CLI output matches the committed comparison artifact.
`.venv/bin/python -m compileall -q seed dashboard tests` and both final/range
`git diff --check` pass. Source comparison with B3 verifies unchanged predictor, evaluator, learner, body,
config, commands, instance-lock implementation, outcome helpers, telemetry helpers,
main entry point and all four prior baseline artifacts.

Normal autonomous perception frequency remains **2**. World-model work adds **zero
perceptions, network requests, DNS lookups or socket connections**. The existing two
fixed reachability probes per normal cycle remain. All validation used temporary
homes and synthetic sensors; installed memory was neither read nor migrated. No
installation, process restart, LaunchAgent change or listener was performed.

Files changed in B4: seed/{migrations,memory,organism,world_model}.py;
dashboard/app.py, dashboard/api/observer.py, dashboard/services/seed_service.py;
the six new tests/fixture and four prior test files listed above; the B4 plan,
comparison artifact, this tracker, and short B4 pointers above the owner's preserved
B3 README/architecture reference text. No B5 implementation is included.

### Known limitations and B5 prerequisites

Retained limitations: immediate rest prediction horizon before the longer wait;
charging-parser discharging false positive; inferred wakes based on wall-clock gaps;
incomplete whole-cycle atomicity; two existing reachability probes per normal cycle.
B4 is limited to immediate descriptive transition statistics, two scope dimensions,
fixed contradiction deadbands, cumulative evidence/contradictions, and a compact but
growing processed ledger. There is no causal or long-horizon model, forgetting,
semantic consolidation or belief-driven prediction/behavior. B3 engineering accuracy
must still be read with coverage; it is distinct from evidence_consistency confidence.

**Ready for B5: YES**, no B4 blocker. B5 still requires explicit owner authorization
and a scoped curiosity design: define the prediction-error/uncertainty inputs and
missing-data handling, bound any influence on existing internal actions or timing,
preserve owner stop and resource/network boundaries, and add deterministic regressions
against this B4 baseline. Curiosity must not authorize new tools, destinations,
external actions, LLM cognition, semantic consolidation or later-batch planning.
B5–B10 remain NOT STARTED. Stop after B4 delivery.


## B5 execution log — 2026-09-22

**Status: VERIFIED.** Started 2026-09-22; completed 2026-09-23 (Asia/Manila).
Branch `seed-0.2-b5`, owner-created from merge `29dd45b`,
identical tree to verified B4 `39e07dc`. Initial tree clean; baseline suite **327
passed**, no skips/exclusions, two existing warnings. Native execution plan:
`docs/superpowers/plans/2026-09-22-seed-b5.md`. Delivery commit is the commit containing
this record, titled `seed-0.2 B5: add bounded computational curiosity`; its resolved
hash and clean-tree result are reported after commit. No automatic merge or push.

Objective: persist deterministic computational salience from B3 error and prior B4
beliefs, with only a guarded, optional use of the existing internal reflection
capability. B5 introduces no emotion, goals, permission, capability expansion,
self-preservation, LLM cognition, or B6+ work.

### B5 architecture decisions

1. Prediction error is the required anchor. Perfect prediction gives zero curiosity
   even with no published beliefs. Missing evaluation gives unavailable, never zero
   error or maximal curiosity.
2. Uncertainty and novelty modulate prediction surprise with half-offset factors;
   neither can independently generate curiosity, and zero novelty/uncertainty does
   not erase meaningful prediction error.
3. Assessment uses the pre-update world model. The exact components and selected
   prior-belief snapshots are stored, never recomputed with later beliefs.
4. Attention can request only the existing internal reflect function, at most once
   for a transition. It cannot invoke owner commands, sensors, other internal actions,
   new tools, destinations, shell operations or permission changes.
5. Curiosity never changes Q-learning, reward, predictor inputs, B3 scoring, B4
   evidence weight, action choice, epsilon/alpha or returned cycle delay.
6. Reflection requires high salience, sufficient coverage, supported resource
   safety, persistent transition/time cooldown and owner authorization.
7. Durable attention claims use at-most-once semantics. Failed or interrupted work
   consumes its budget; losing optional reflection is preferable to repeated work.
8. The existing `prediction_error_curiosity` setting remains **False by default**.
   It now accepts a strict Boolean True to enable guarded auxiliary reflection.
   Every autonomous assessment is recorded regardless of this setting. Existing
   False values remain authoritative and produce `disabled_by_owner` suppression
   for otherwise eligible attention. No new opt-in UI or automatic setting rewrite
   is added; the existing owner settings service/API supports the Boolean. The
   `advanced_concept_inference` placeholder must still remain False.

### Formula, components and thresholds

`seed/curiosity.py` provides pure `assess_curiosity(evaluation,before,action,after,
prior_beliefs)`. Every persisted assessment identifies **curiosity_v1 / version 1**.
Supported input is B3 prediction_error_v1/version 1, evaluated aggregate with valid
finite nonboolean mean_normalized_error and coverage in 0..1, positive coverage,
and at least one usable modeled observation. Otherwise status=unavailable,
score=NULL, level=UNAVAILABLE, no attention eligibility.

For valid input:

```text
prediction_surprise = mean_normalized_error × coverage
uncertainty_modifier = 0.5 + 0.5 × uncertainty
novelty_modifier = 0.5 + 0.5 × novelty
score = clamp(prediction_surprise × uncertainty_modifier × novelty_modifier, 0, 1)
```

Usable signals follow the B4 observation rules: valid before/after numeric pairs
for battery/load/disk deltas, and exact Boolean after.network for network_reachable.
Missing/invalid signals do not enter the component denominator. Components may use
valid observed signals independently of whether that individual forecast was
available; the B3 aggregate error and coverage remain the required score anchor.

`WorldModel.applicable_beliefs(action)` reads at most eight keyed published candidates
in one SQL statement. Select the action-conditioned belief, then global, then none,
for each signal. Pending statistics are not published beliefs and do not reduce
novelty/uncertainty. Both scopes are never counted together for one signal.

Per signal:

- Uncertainty = clamp(1−prior confidence,0,1), or 1 with no published belief. This
  means lack of established consistent experiential support, not truth probability.
- Novelty = 1 with no belief; .5 with fewer than four prior evidence samples; 1 for
  a contradiction against an established belief; otherwise 0.
- Arithmetic mean over usable signals produces the uncertainty/novelty components.

B4 updating and B5 novelty share the canonical pure `world_model.contradicts`
helper. Numeric deadbands remain battery .05, disk .01, load .02; strict opposite
signs outside the deadband and prior n>=4 are required. Boolean majority thresholds
remain >=.75 and <=.25 with prior n>=4. B4 sample validity, scope, two-sample
publication, confidence formula, equal evidence weighting and update results are
unchanged. Refactoring exposes helpers; it does not introduce a second rule.

Levels: score <.20 LOW; .20≤score<.50 NOTABLE; .50≤score<.75 HIGH; score≥.75 VERY_HIGH.
These are descriptive numeric labels. No score is assigned for unavailable data.

Each component stores the observed sample, uncertainty, novelty, contradiction,
and selected prior belief's key/scope/count/confidence/last source ID/statistical
value. This bounded snapshot of at most four selected beliefs preserves meaning
when the live model changes. Tests demonstrate both pending→published promotion and
an established mean reversing sign after assessment: curiosity retains the prior
positive mean and its contradiction, not the revised negative direction.

### Schema v4 and prospective atomic persistence

Additive v4 introduces two tables without rewriting any prior table:

- `curiosity_assessments`: unique transition foreign key, creation time, model/version,
  status, nullable score, level, surprise/uncertainty/novelty/coverage, components JSON,
  eligibility, claim/completion flags, suppression/failure reasons, claim/completion
  timestamps. Schema checks constrain evaluated versus unavailable score/level and
  Boolean attention flags. Completion requires a prior claim.
- `curiosity_runtime`: singleton last_reflection_transition_id and last_reflection_at.
  These identify the last **claimed** auxiliary action, even if it failed or did
  not finish; they do not reset on process restart.

Memory's optional `curiosity` parameter defaults to absent. Autonomous B5 callers
compute it after B3 error and before reward/Q persistence. The exact copied payload
is inserted in the existing transaction with episode, transition, prediction,
evaluation and prospective B4 queue entry. Failed assessment insertion rolls all
of those inserts back. Later attention updates mutate only outcome/eligibility
metadata; the historical score and components stay unchanged.

The migration ladder supports fresh/legacy/v1/v2/v3→v4, v4 reopen no-op, rejection
of future/ambiguous versions, and backup before upgrading existing memory. Tests
compare all prior rows, including v3 published/pending beliefs, queue and markers,
and verify the snapshot still has version 3 and original contents. An injected
failure at the final v4 step rolls back every applied migration step from each
prior version. Failed backup prevents schema changes. No B1–B4 assessments are
backfilled: absence remains distinct from a zero-curiosity experience.

### Runtime ordering and bounded attention

Core ordering: B3 evaluation → read prior beliefs → assess curiosity → unchanged
legacy reward/Q update → commit experience/assessment → emit its linked summary →
B4 bounded recovery/update → optional claimed internal reflection. Existing memory
and learning telemetry retain their meaning. A HIGH experience still contributes
one B4 sample per valid signal/scope, exactly like a LOW experience.

`seed/curiosity_attention.py` implements the only optional effect. Static guards
are evaluated separately from the score, in this deterministic priority:

1. unavailable evaluation;
2. level below HIGH;
3. coverage below .50;
4. selected action already reflect;
5. valid actual load_ratio >.8;
6. valid actual battery_pct <20 with charging exactly False;
7. valid actual disk_free_pct <10.

Resource equality boundaries (.8 load, 20 battery, 10 disk) are allowed. Unknown,
invalid or missing resource fields do not fabricate violations. A valid high score
is not changed by any suppression. The coverage guard is also tested independently
with a synthetic HIGH assessment below .50, even though the formula mathematically
bounds a normal score by coverage and makes that combination unreachable.

At claim time, static guards are rechecked against the persisted source. A disabled
owner setting suppresses otherwise eligible reflection; an owner stop wins over
all other reasons. If a previous claim exists, both conditions must hold:

- at least **10 actual completed autonomous transitions**, including the current
  transition, after the previous claim's source;
- at least **300 seconds** since the prior claim's timestamp.

A bounded indexed transition range reads at most ten IDs. ID gaps and owner-command
experience episodes cannot provide budget. A backwards wall-clock jump conservatively
keeps the time cooldown active. Without a prior claim, no cooldown is owed.

BEGIN IMMEDIATE serializes the claim, cooldown row and claim event before invoking
reflection. A claimed assessment cannot be invoked again by retry or another
connection. Suppressed decisions are terminal for that transition; they are not
reconsidered later using newer beliefs, resources or settings. The owner stop flag
is checked again after claiming and before calling reflect.

There is no recursive assessment, extra perception, fake transition, auxiliary
reward/Q update, delay change, observe/rest/consolidate invocation, or automatic
attention replay on startup. At most one existing reflection reads the usual
latest 80 episodes and performs the existing two summary calculations. Policy
reflection and owner-command reflection retain their existing algorithms.

Reflection now has explicit provenance in REFLECTION start events and any CONCEPT
events: policy_selected, owner_requested, or curiosity_triggered. The auxiliary
case includes its source transition ID. Existing policy action and owner command
records supply their own linkage; neither is recorded as auxiliary attention.

An ordinary auxiliary exception records a bounded failure reason and CURIOSITY
failure event, preserves the completed transition/assessment/claim, and allows the
core to continue. SQLite errors propagate through existing storage error handling;
the claim is not released. A crash after claim may lose an optional reflection.
No automatic recovery retries an auxiliary claim. The whole physical cycle remains
non-transactional: existing action/Q/concept effects may precede later failures.

### Telemetry, inspection and metrics

CURIOSITY events carry transition ID, score/level, surprise/uncertainty/novelty,
coverage and attention outcome. Creation, claim, completion, dynamic suppression
and ordinary auxiliary failure are recorded without dumping the full world model.
Static suppression is visible in the assessment event/row. Existing event retention
remains unchanged. No large runtime history or major frontend is added.

Bounded observer endpoints:

- `GET /api/curiosity`: newest first; limit 1..100, default 50, inclusive `before`
  transition-ID cursor and returned next_cursor. Fetches at most limit+1 rows.
- `GET /api/curiosity/{transition_id}`: one exact assessment, including components
  and attention outcome; invalid/oversized IDs return 422, absent IDs 404.
- `GET /api/curiosity/summary`: **latest 100 assessments only**, with assessment
  count, mean score/components, level counts, eligible/claimed/completed reflection
  counts, suppression counts/reasons and failure count. Unavailable scores are
  excluded from means and retained in level counts. Empty means are NULL.

Eligible count reflects current stored eligibility; successful/failed claims can
remain eligible, while suppressed outcomes are not. Claimed and completed counts
are separate, so incomplete optional work is not presented as successful. Suppressed
count includes below-threshold and unavailable decisions. All counts and denominators
refer to this bounded window, never lifetime development or intelligence.

Direct service calls enforce bounds too. ReadStore uses SQLite mode=ro. Legacy
queries return unavailable/empty without migration. Operator startup requires both
v4 tables and schema version 4. Existing local Host/Origin/token and settings-audit
boundaries remain in force. No new listener or writable curiosity API is added.

### Deterministic evaluation and compatibility

Artifact: `docs/baselines/seed-0.2-b5-comparison.json`.
Reproduce: `.venv/bin/python -m tests.curiosity_scenario`.
The nine isolated cases use the real core/predictor/evaluator/assessment/model and
synthetic pre/post observations, deterministic action choice and fixed clocks.

| Case | Score | Level | Auxiliary outcome |
| --- | --- | --- | --- |
| High, allowed | .925 | VERY_HIGH | One completed curiosity reflection |
| Zero prediction error | 0 | LOW | Below threshold |
| High load | .925 | VERY_HIGH | high_load |
| Low uncharged battery | .95 | VERY_HIGH | low_battery |
| Low disk | .9375 | VERY_HIGH | low_disk |
| Policy already reflected | .925 | VERY_HIGH | already_reflected |
| Owner setting disabled | .925 | VERY_HIGH | disabled_by_owner |
| One evaluated signal | .25 | NOTABLE | Below threshold; coverage .25 |
| Unavailable evaluation | NULL | UNAVAILABLE | No reflection |

Every case has exactly one transition, one assessment, one processed B4 marker,
and two perceptions. Returned delay is 8 seconds for observe, 12 for the selected
reflect case. The allowed case retains legacy reward −.4 and Q .502 after the fifth
visit from old Q .7 with alpha .18. Its auxiliary reflection creates no extra Q row
or experience. These selected cases verify arithmetic and boundaries, not improvement.

Comparison against the immutable B4 artifact:

- All B4 world fixture statistics, evidence, contradictions and confidence match
  exactly; only reported schema changes to 4.
- Every non-footprint eight-cycle control metric matches, including actions,
  predictions/support counts, scores, Q values, delays and 16 perceptions.
- Every non-schema field in the three B3 evaluation cases and all aggregate
  scoring metrics match exactly.
- Predictor, evaluator, learner, body, commands, instance lock, transition helper,
  telemetry helper and main entry point remain byte-identical to B4. All five
  B0–B4 baseline artifacts remain byte-identical. Config changes only to accept the
  existing curiosity Boolean; reflection changes only for provenance and optional
  invocation; B4 changes only through shared rules/keyed reads.

Checkpointed eight-cycle fixture storage: **282,624 bytes**, 69×4,096-byte pages,
zero WAL/SHM after close; B4 was 249,856 bytes/61 pages. These are measured fixture
sizes, not portable thresholds. Assessment storage grows one bounded record per
new autonomous transition; claim state is a singleton, and per-assessment lookup,
reflection, cooldown, and dashboard windows remain bounded. Existing B4 processed
markers and detailed transition storage continue growing with experience.

### B5 tests and verification

New tests and fixture:

- `tests/test_curiosity_migrations.py`: seven backup/migration/preservation/rollback
  and exact atomic-persistence cases.
- `tests/test_curiosity.py`: literal formula, error anchor, level boundaries,
  unavailable/invalid aggregates, component averages, novelty, pure snapshot,
  static guards, scope preference, bounded lookup and canonical contradiction reuse.
- `tests/test_curiosity_attention.py`: claims committed before callbacks, concurrent
  connections, restart/lost work, both cooldown conditions, ID gaps/owner episodes,
  claim-event rollback, terminal suppression, failure budgets, serious storage errors,
  owner-stop races and bounded range queries.
- `tests/test_curiosity_cycle.py`: pre-update snapshot/promotion/direction reversal,
  complete real-cycle timing, owner setting, all-action predictor/error/Q/delay and
  evidence isolation, provenance/no-double-reflect, failure continuation and zero
  additional socket/DNS/perception activity.
- `tests/dashboard/test_curiosity.py`: recent pagination/detail, rolling100 metrics,
  direct/HTTP validation, fixed query bounds, legacy reads and operator refusal.
- `tests/test_curiosity_scenario.py` and `tests/curiosity_scenario.py`: nine real
  controlled cases and comparisons with the saved B4 artifact.

Earlier tests retain all behavior assertions. Current-version checks move to 4;
strict event-order assertions include REFLECTION provenance and linked CURIOSITY
creation; settings validation now rejects a nonboolean curiosity value rather than
True; the B4 fixture reports the actual current schema instead of hardcoding 3.
No test is removed, skipped or excluded.

RED runs preceded migration, persistence, model helpers, assessment, attention,
core configuration/integration, read routes and scenario implementation. New test
harness corrections used the actual legacy reward arithmetic and persisted epsilon=0
when applying settings, so random exploration could not make assertions flaky.
Earlier tests failed on the intended schema/telemetry/Boolean-setting changes and
were updated without weakening their policy/scoring/preservation checks.

Final `.venv/bin/python -m pytest -q`: **426 passed**, **0 skipped/excluded**,
**2 existing upstream deprecation warnings**. All **99 B5 tests** pass. Independent
fresh read-only review reported **no Critical, Important or Minor findings** and
confirmed the default-off owner setting is consistent with the authorized optional
attention boundary. The reviewer did not rerun tests; full-suite and artifact
execution evidence is supplied by the parent. No deferred findings remain.
The standalone B5 CLI exactly matches the saved artifact. Compilation with
`.venv/bin/python -m compileall -q seed dashboard tests`, `git diff --check`,
and whitespace checks across all 31 changed/new files pass.

All work uses temporary homes and synthetic observations. Installed memory was not
read or migrated, and no installation, core restart, LaunchAgent change or listener
was performed. Normal cycles still have **two perceptions** and the same returned
intervals. Assessment and auxiliary reflection add **zero sockets, DNS requests or
reachability probes**. The existing two probes per autonomous cycle remain.

Files changed: core curiosity.py and curiosity_attention.py; additive changes in
migrations.py, memory.py, organism.py, world_model.py and config.py; observer routes,
read service and operator schema guard; seven new test/fixture files listed above;
version/telemetry/config expectations in eight prior test files and actual-schema
reporting in the B4 fixture; B5 plan, artifact, this tracker and brief README/architecture
pointers above the preserved B3 reference text.

### Limitations and B6 prerequisites

Retained limitations: immediate rest horizon, charging-parser defect, incomplete
whole-cycle atomicity, two existing probes per cycle, B4 processed-marker growth,
and world beliefs limited to immediate descriptive statistics. Curiosity_v1 is a
bounded heuristic; novelty is coarse and confidence is not a truth probability.
It creates no goals, capabilities or external behavior. Optional reflection is off
by default, can only reuse the existing reflection, and is at most once; crashes
can lose it and cooldown uses persistent wall time. Added internal work consumes a
small bounded amount of processing time but never shortens returned cycle delays.
No claim of calibrated psychological curiosity or developmental improvement is made.

**Ready for B6: YES**, with no B5 blocker. B6 requires separate explicit authorization
and a scoped semantic-consolidation design: define source windows, derived concept
meaning/provenance, idempotency and persistence, conflict handling, measurable
verification and resource bounds. Preserve original memories and owner control;
curiosity must not silently weight evidence or consolidation, merge/prune beliefs,
forget experiences, or introduce later self-model/planning/tool capabilities.
B6–B10 remain NOT STARTED. Stop after B5 delivery.

## B6 execution log — 2026-09-23

**Objective:** retain compact, revisable semantic knowledge derived exclusively
from published B4 world beliefs while preserving every original memory.
Authorized by the owner's B6 instruction; B7 and later work remains unauthorized.
Branch **seed-0.2-b6** starts at **2ddad70**, the merge of verified B5 **ad83ea6**.
Delivery commit: the commit containing this record, titled
**seed-0.2 B6: add semantic memory consolidation**. Native execution; no live
installation, memory migration, restart, LaunchAgent change, or listener.

### B6 architecture decisions

1. Semantic memory is downstream of published B4 world beliefs. It never rescans
   lifetime episodes to rediscover patterns or rewrites upstream statistics.
2. Promotion requires **evidence_count >= 8 AND confidence >= 0.30**. These
   semantic_v1 engineering defaults are not statistical guarantees or settings.
3. Knowledge is revisable: loss of eligibility weakens an existing record;
   restored eligibility reactivates it. Prior revisions remain inspectable.
4. Consolidation preserves autobiographical memory. No deletion, pruning,
   expiration, forgetting, or semantic-promotion vacuum is introduced.
5. The existing policy-selected consolidate action and owner consolidate command
   each invoke one bounded run, retaining the existing checkpoint.
6. Semantic memory has no influence on policy, prediction, prediction error,
   curiosity, or world-model learning in B6.

The layers remain distinct: episodes/transitions record **what happened**;
world_beliefs record **currently observed statistical regularities**;
semantic_memories record **consolidated sufficiently supported regularities**.
The original concepts/concept_evidence remain legacy reflection products, with
their algorithm and meaning unchanged. There is no migration between these layers.

### Model, revision and provenance

Every record uses **semantic_v1**, model_version **1**, and a unique structural key
composed of semantic type, signal, scope, scope value and version. Supported
signals are battery_pct, load_ratio, disk_free_pct and network_reachable; scopes
are global and the four existing action conditions.

Numeric records use numeric_delta_summary and copy mean_delta,
mean_absolute_delta, min_delta and max_delta, with interpretation
observed_transition_delta. Boolean records use boolean_frequency_summary and copy
true_count, false_count and probability_true, with interpretation
observed_boolean_frequency. No LLM, generated prose, cross-signal concept or
causal claim is involved. Payload validation rejects malformed JSON, nonfinite
statistics, invalid domains, inconsistent Boolean evidence and unsupported identities.

Creation starts at revision 1, active. Canonical source fingerprints detect changed
evidence, contradictions, confidence, complete source value or provenance, even
when clocks are equal or move backward. JSON formatting and equivalent numbers
such as 1 and 1.0 do not count as material changes. Timestamp-only source changes
do not mutate the semantic row or its timestamps. source_belief_updated_at therefore
identifies the source state last materially consolidated, not every later write.

Changed eligible sources revise once; sources below either promotion threshold
become weakened; renewed support returns them to active with another revision.
Each mutation first stores the complete previous row in semantic_memory_history.
created_at stays fixed; revision and updated_at advance only on material/status
changes. Evidence counts, contradictions and source confidence remain visible.
Exact source belief ID, B4 model version and update time are retained, plus first
and last transition provenance; original B4 evidence remains accessible without
copying every transition ID.

A malformed source is counted as a failed item while other valid sources proceed.
An existing semantic record becomes source_unavailable once, preserving its last
valid payload and statistics. Recovery of valid source data can reactivate it.
The bounded read layer also reports a missing or corrupt source through
source_status=source_unavailable without rewriting stored semantic history.
Its status filter refers to the persisted consolidation status. No orphan sweep
or automatic semantic deletion occurs.

### Persistence, scheduling and failure semantics

Schema **4 → 5** adds semantic_memories, semantic_memory_history,
consolidation_runs and consolidation_state. Existing tables and rows are retained.
The existing backup-before-migration and transactional migration ladder cover
fresh, legacy, v1, v2, v3, v4 and v5 reopen, with future-version refusal. Migration
creates no semantic rows, history, runs or cursor: there is no automatic backfill.
An explicit later run may consolidate already-published eligible B4 beliefs.

At most **100** world beliefs are examined per invocation, in ascending ID order
after a persistent cursor, wrapping to lower IDs only within the remaining budget.
This cyclic cursor eventually revisits changed older beliefs; a monotonically
increasing exclusion watermark would miss them. Canonical fingerprints make
revisits idempotent. No correctness state depends on RAM. The normal B4 identity
space is currently 20; valid multi-pass tests lower the budget, while a synthetic
105-row malformed overflow fixture verifies the hard 100 limit and continued work.

A started audit is committed first. One IMMEDIATE transaction then includes all
current/history changes, progress, semantic events and completed run counters.
A serious failure rolls this transaction back; a separate failed audit records
zero committed successes where storage permits, then the error propagates.
Malformed-item failures can coexist with successful changes in completed_with_errors.
A failed source can also cause a source_unavailable revision, so failed_count and
revised_count are not disjoint totals. weakened_count counts transitions into
weakened status; subsequent changed weakened statistics count as revisions.

Repeated unchanged runs add only run/event audit records and cursor/checkpoint
metadata: creates, revisions and weakened counts stay zero, and semantic rows,
history and timestamps remain unchanged. No automatic startup, wake, shutdown,
curiosity or periodic consolidation is added. An interrupted run may retain a
running audit; a later explicit run re-examines durable source/progress state,
without automatically replaying the interrupted invocation.

### Triggers, resources and inspection

Policy-selected consolidate receives the existing fresh pre-action state explicitly.
Owner consolidate uses the latest persisted state and provenance owner_requested;
it creates no learner transition, curiosity assessment or Q update.
Both retain last_consolidation metadata with original at/episodes/concepts fields
plus run_id and status. The existing checkpoint telemetry remains.

Known load_ratio > .8, battery_pct < 20 with charging exactly False, or
disk_free_pct < 10 suppresses the run with high_load, low_battery or low_disk.
A suppressed run has zero work counts and is not a failure. Missing or invalid
resource values are unknown, not assumed unsafe; owner state may be stale.
No guard performs perception. Selected action, legacy reward/Q and returned
20-second consolidate delay remain unchanged.

CONSOLIDATION and SEMANTIC_MEMORY events record started/completed/suppressed/failed
runs, creations and revisions with status/provenance. Event payloads are bounded.
Run audit results contain at most 100 examined IDs and bounded item failure reasons.

Read-only observer endpoints:
- /api/semantic-memories: signal/scope/status filters, ascending ID keyset pages.
- /api/semantic-memories/{id}: structured current record and source availability.
- /api/semantic-memories/{id}/history: prior revisions, newest first.
- /api/consolidation-runs: newest run audits first.

Pages default to 50, maximum 100, with one lookahead row; detail is one ID.
History and run cursors are inclusive descending cursors. Legacy reads return
unavailable empty lists or 404 detail without migration. Direct and HTTP argument
bounds are validated, and operator mode requires all v5 tables. No frontend redesign.

### B6 deterministic evidence and compatibility

The standalone fixture is **.venv/bin/python -m tests.semantic_scenario**.
The saved **docs/baselines/seed-0.2-b6-comparison.json** anchors verified B5 and its
artifact hash, records all outputs, and includes unchanged upstream source hashes.

A real B4 battery evidence sequence consolidates global and observe scope:
8 consistent observations create two active revision-1 records (confidence .4).
An unchanged run leaves both rows identical. Eighteen valid opposing observations
produce n=26, contradictions=18, confidence .2923076923076923; both rows weaken
at revision 2. One consistent observation restores confidence .3166666666666667
at n=27; both reactivate at revision 3. Four complete prior revisions remain.
All 27 episodes, 27 transitions, 27 processed markers and two world beliefs survive.

All nine B5 curiosity cases match exactly, including score/components, suppression,
reflection claims/completion/provenance, predictions, evaluation, Q and delays.
B4 world statistics match the saved fixture exactly apart from current schema.
B3 scores and every non-schema case field match; all eight-cycle control metrics
match apart from the expected additive database footprint. Two perceptions per
autonomous cycle remain, with zero additional sockets, DNS or reachability probes.
The existing two probes per autonomous cycle are unchanged.

Predictor, evaluator, learner, body, world model, curiosity, curiosity attention,
configuration, commands, runtime, transition helpers and telemetry are byte-identical
to verified B5. All six B0–B5 baseline artifacts remain byte-identical.
Checkpointed control storage is **311,296 bytes**, 76×4,096-byte pages, versus
B5's 282,624 bytes/69 pages; both have zero WAL/SHM after close. These are fixture
measurements, not portable storage thresholds or intelligence scores.

### B6 tests and files

71 new tests cover migration/backup/rollback/preservation (7), engine thresholds,
payloads, revisions, real contradiction/recovery, idempotency, bounds/restart,
guards and atomic failure (38), command/cycle/isolation behavior (8), bounded
read-only inspection, legacy/security bounds and source damage (16), and full
deterministic revision/compatibility artifacts (2).

Existing tests retain their behavioral checks. Current schema assertions move to
5, three action spies forward the explicit existing state argument, and the B5
scenario reports the current schema rather than hardcoding 4. No tests are removed
or skipped. RED runs preceded migrations, engine, integration, reads and fixture;
an equivalent-number idempotency regression was reproduced and corrected.
Fixture-only corrections used the repository's actual entry-point layout and
existing artifact keys.

Files: new seed/semantic_memory.py and dashboard/services/semantic_memory.py;
additive migrations.py, organism.py, observer routes, SeedService delegations and
operator schema guard; new semantic migration/engine/cycle/dashboard/scenario tests
and fixture; schema/spies in prior regression tests; B6 plan, artifact, this tracker
and brief README/architecture pointers above the preserved B3 reference snapshot.

Full **.venv/bin/python -m pytest -q: 497 passed, 0 skipped/excluded**.
Two existing upstream deprecation warnings remain. Compilation and tracked diff
whitespace checks pass. Independent review found no Critical or Important issues
and one Minor issue: transaction acquisition occurred outside failure auditing.
An injected acquisition failure reproduced a misleading running audit. Moving
BEGIN IMMEDIATE inside the existing try handler fixes it; the new regression
verifies failed status, completion time, zero committed successes and safe retry.
The reviewer independently ran the original 70 B6 tests; the parent ran the new
regression RED→GREEN and the complete 497-test suite after the fix. No deferred
review findings remain. The standalone artifact matches a fresh CLI run exactly;
all 28 changed/new files pass whitespace checks.

### B6 limitations and B7 prerequisites

semantic_v1 only consolidates B4 descriptive world beliefs. It supplies no causal
knowledge, cross-signal concepts, multi-step temporal patterns, forgetting, or
decision influence. Promotion thresholds are engineering defaults. Revisions are
observed only when consolidation is explicitly invoked; full audit/history storage
grows, although per-run processing and inspection are bounded.

Inherited limitations remain: immediate prediction/rest horizon, charging-parser
defect, incomplete whole-cycle atomicity, two existing reachability probes per
autonomous cycle, processed-marker growth, descriptive non-causal world statistics,
and heuristic default-off curiosity attention. B6 does not repair or broaden these.

B7 requires explicit authorization and a scoped design for evidence-grounded
self-model records, their source windows, provenance, uncertainty, revisions,
resource bounds and tests. Semantic confidence must not become an unsupported
capability or psychological claim. Policy/decision integration remains B8.

**B6 status: VERIFIED. Ready for B7: YES**, with no remaining B6 blocker.
B7–B10 remain NOT STARTED; await separate explicit authorization.

## Documentation refresh — 2026-09-23

Owner requested a README and documentation update after verified B6 commit
**dc225af**. README.md and docs/architecture.md now describe B0–B6 and schema v5
throughout, replacing the former B3 reference snapshots and temporary update
banners. docs/implementation-log.md now indexes all seven batch artifacts and the
B4–B6 execution records. Historical batch entries and baseline artifacts are retained.

The refresh documents the current cycle ordering, distinct memory layers,
world-model evidence/contradiction rules, default-off optional curiosity reflection,
semantic eligibility/revisions/history, resource and processing bounds, inspection
APIs, migration/atomicity boundaries, reproducible development commands and known
limitations. Policy/reward/Q isolation and the separate installed-app deployment
boundary remain explicit. B7–B10 stay NOT STARTED.

Validation: relative documentation links and heading anchors, local command paths,
model constants/defaults and API names checked against the repository; Markdown
fences and whitespace checked. This is a documentation-only change. Runtime code,
tests and baseline artifacts are unchanged; the recorded B6 result remains
497 passed with zero skips and two existing dependency warnings. No live process,
installed memory or migration was accessed for this refresh.

## Post-B6 hardening — 2026-09-23

Owner authorized the bounded H0–H5 instruction after the B6 merge. This is not B7.
Task branch: seed-0.2-post-b6-hardening, based on reviewed master
f18ed31bc622ed219558a1f0aa7f4c4566cc0d56. See the dated
[hardening record](reviews/2026-09-23-post-b6-hardening.md) for exact evidence,
findings, file purposes, resume state and owner-controlled remaining gates.

Current changes correct new battery observations (complete status fields instead
of substring charging matches), centralize core software version 0.2 and clarify
bootstrap/source/runtime/schema metadata, and add a full-SHA-pinned read-only CI
workflow. The existing B0 false-positive characterization is intentionally updated;
original recorded observations and baseline artifacts remain untouched. Version
reporting does not prove the installed organism has been upgraded.

Fresh local baseline: 497 passed. Fresh post-change suite: 539 passed, zero skips,
two existing warnings, on macOS 26.5.1 arm64 / Python 3.13.15. All five standalone
scenario behaviors match the starting run; only expected body-source hash metadata
changes. The seven historical artifact hashes remain identical. These counts are
separate from B6 acceptance. Learner formulas, schema v5, model/attention bounds,
owner controls, security and memory preservation are unchanged.

H0–H2 and H4 are locally verified; H3 is implemented and locally validated.
H5 local regression and self-review are verified; independent review supplied an
initial no-findings assessment but could not finish because of a usage limit.
Hosted Linux/Python 3.11 and 3.13 plus macOS/Python
3.13 execution is pending owner-authorized push/PR. No hosted execution, merge,
branch-rule change or installation is implied by local checks. Detailed ruleset/
protection inspection was restricted; exact required-check names await real runs.

[Verification guide](verification.md) and [deferred decision issue](review-follow-ups.md)
record follow-ups. Low-disk reward versus consolidation suppression remains OPEN
for B8 or a separately authorized change; no reward correction is implemented here.


## Pre-B7 closure — 2026-09-23

The owner authorized SEED_Pre_B7_Closure_Instructions.md, including a narrow
wording fix, push, PR and hosted artifact inspection. This supersedes the earlier
local-only handoff boundary; merging and deployment remain unauthorized.
Starting HEAD 08dd9d357ba39fc11a092bf3b81181e3b0221c37 and base
f18ed31bc622ed219558a1f0aa7f4c4566cc0d56 were confirmed with a clean tree on
seed-0.2-post-b6-hardening.

The dashboard now displays Not charging for charging=false without inferring
battery power. One committed asset regression covers the three label branches.
CI checkout explicitly selects the PR head to meet the exact-SHA artifact gate.
Fresh local results: 60 focused and 540 full-suite tests passed, zero failures or
skips, two existing warnings; all five scenarios and historical baseline hashes
unchanged. Hosted CI and final independent review are pending at this checkpoint.
The [hardening review](reviews/2026-09-23-post-b6-hardening.md) records closure
progress. Low-disk mismatch stays OPEN; B7–B10 remain NOT STARTED.


## B7 design execution record — 2026-09-24

**Authorization:** the owner's SEED_B7_Self_Model_Design_Instructions.md and explicit
“please proceed” authorize design/specification only. No implementation, migration,
API, test, frontend, deployment or later batch is authorized by this record.

**Starting state:** clean master and origin/master at
`585affec56ddb0e4580f6df6926b9b6bde291dc0`, PR #9 merge, then a new dedicated
`seed-0.2-b7` branch. Previous branches and history were preserved. Current schema
remains v5 and core version 0.2. The post-merge Actions run
[35884486727](https://github.com/Jeruzael/SEED/actions/runs/35884486727) has successful
linux-py311, linux-py313 and macos-py313 jobs on that exact SHA; job metadata was
reconfirmed during this design audit. Owner-provided post-merge evidence reports
542 passes per job. No new hosted artifact download audit is claimed here.

**Fresh baseline:** `.venv/bin/python -m pytest -q` → **542 passed, zero failures or
skips, two existing dependency warnings**, exit 0, macOS 26.5.1 arm64 / Python 3.13.15.
Each of the following standalone commands exited 0 with valid JSON, exactly matching
the preceding portability-correction output:

- `.venv/bin/python -m tests.baseline_scenario`
- `.venv/bin/python -m tests.prediction_error_scenario`
- `.venv/bin/python -m tests.world_model_scenario`
- `.venv/bin/python -m tests.curiosity_scenario`
- `.venv/bin/python -m tests.semantic_scenario`

All execution used synthetic data and resolved temporary homes. Audit output is
local ignored `.review-artifacts/b7-design/`. Dependency lock and all seven
historical baseline hashes remain unchanged. No dependencies were installed.

**Deliverable:** [Self Model design](superpowers/specs/2026-09-23-b7-self-model-design.md).
The requested filename date is preserved; actual preparation/review is 2026-09-24.
The required source, documentation and test inventory was read completely, with
migration and scenario fixtures inspected. A written 12-point self-review is
included in the spec. This is an inline self-review, not an independent code review.

**Design decision:** select a bounded persisted current snapshot over derived-only
inspection and a revision ledger. Proposed schema v6 adds only self_model_current
(singleton, updated_at, model, model_version, source_transition_id, data_json).
The proposed update follows committed experience, B4 recovery and optional curiosity
reflection, before final runtime telemetry; it has no upstream consumers. Source
cutoffs, status/freshness policies, atomic bounded telemetry, restart/failure behavior,
readonly inspection, complete synthetic JSON examples, acceptance scenario and
concrete test/file map are specified. No proposed schema or API is implemented.

**Important boundaries resolved:** static action selectability is separate from
substantive audited work; consolidation audits have no invented transition linkage;
recorded prior runtime success does not claim current completion; count queries
saturate instead of scanning all history; migration explicitly passes through v5;
existing event retention remains within the bounded B7 transaction. Low-disk reward
versus consolidation suppression remains OPEN for B8 or separately authorized work.

**Files changed:** exactly this tracker, docs/implementation-log.md and the new
B7 design spec. No code, tests, migrations, dependencies, README, architecture guide,
baseline artifacts or installed data changed. Validation covers required spec
sections, strict JSON examples, proposed DDL syntax in an in-memory scratch DB,
relative links, whitespace, exact documentation-only scope and baseline hashes.
These are documentation checks, not execution of B7 acceptance tests.

**Delivery:** documentation-only commit `docs: design B7 self model` on seed-0.2-b7;
resolved commit identity is supplied in the handoff. Branch push for inspection is
permitted; no merge or implementation PR. Implementation remains behind owner
review and a separate follow-up authorization.

B7 design/specification: **COMPLETE FOR OWNER REVIEW**.
B7 implementation: **NOT STARTED**.
B8–B10: **NOT STARTED**.
Installed organism: **UNTOUCHED**.


## B7 implementation record — 2026-09-24

The owner approved the written design at `89f4561bee0a8bca930a329f88bbaef5af3e82e1` and explicitly requested implementation and continuation. Native execution continues on `seed-0.2-b7`, based on verified master `585affec56ddb0e4580f6df6926b9b6bde291dc0`. The [implementation plan](superpowers/plans/2026-09-24-seed-b7.md) records tasks and review focus. No installed process, installed memory, launch configuration or deployment changed.

### Implementation and preservation

Schema v6 adds only `self_model_current`, initially empty. Existing supported memory is backed up before transactional additive migration; failure rolls back every earlier schema path. Original records and historical missing values remain untouched. Snapshot publication and its bounded existing-style SELF_MODEL event are atomic, including event retention. Busy/VM limits, stop, duplicate, rollback and connection restoration have regression coverage.

The publisher runs once after optional reflection and before final cycle runtime. Fixed source registries describe committed observations, prediction performance, bounded storage counts, the action catalog, independent consolidation audit, stored runtime and retained ERROR records. It performs no perception, process probe, network call, policy update or semantic work. The parameter-free read-only `/api/self-model` validates nested payloads and projects freshness from original source clocks; startup and reads never refresh evidence.

Limits: 100 raw evaluations (invalid records consume the window); 100 retained errors plus one lookahead; four storage counts capped at 1,001; 14 evidence reads plus timeout read; 100,000 SQLite VM steps; zero busy wait; 16 KiB source JSON, 32 KiB snapshot, 1 KiB telemetry and 40 KiB API response. Counts beyond 1,000 are lower bounds. Recorded failures are not a lifetime rate, logical page size is not filesystem footprint, and prediction scores are not calibrated competence.

Commits: `b39a6bd` schema and preservation, `abaf736` bounded publisher, `3c6e8a1` downstream cycle and observer. Tests were run failing before each implementation. No test was removed, skipped or excluded. Strict event expectations add only the downstream SELF_MODEL event; historical comparison tests permit only actual schema and additive database-footprint differences.

### Verification evidence

Fresh local full suite: **646 passed, zero skipped, two existing dependency warnings**, Python 3.13.15. Coverage includes v5 backups and rows, all earlier migration rollbacks, exact metric denominators, nested corruption, raw-window exclusion, 1,000/1,001 count boundary, independent source clocks, retained-error provenance, transactional event retention, interrupted connection restoration, failed write preservation, no-op restart, owner-command isolation and a four-read observer query budget.

All four actions, with curiosity enabled and disabled, run in pairs against absent, valid, corrupt, failed-write and disabled self models. Actions, rewards, predictions, evaluations, Q values, learning parameters, world processing, curiosity, semantic records, delays and perception counts remain equal. A separate real Body probe test uses synthetic host sensors and a stubbed socket, proving exactly the two existing fixed reachability calls.

The new deterministic [comparison artifact](baselines/seed-0.2-b7-comparison.json) records all seven immutable historical hashes and reproduces fresh, insufficient, scored, stale, failure, restart, suppressed-consolidation and paired-policy cases. Three valid B3 evaluations produce coverage **5/12**, error **.06**, accuracy **.94**, with **two** scored samples. Consolidation remains selectable when its last audit reports low_disk suppression. This verifies reporting, not a reward-policy fix or a developmental improvement claim.

All six standalone scenario CLIs pass with synthetic temporary homes and strict JSON. Compileall and git diff --check pass. All seven historical artifact hashes and bytes match the approved-design base; learner, sensors, predictor, evaluator, world model, curiosity/attention, semantic engine, commands, configuration, telemetry, Memory and dependency lock remain byte-identical. Independent review is complete; both important findings are fixed with failing regressions followed by passing focused and full suites. Hosted CI remains pending owner authorization to push. B7 status remains **IMPLEMENTED** until required acceptance evidence is complete. B8–B10 remain **NOT STARTED**. The existing low-disk decision mismatch stays open for separate authorization.


### Final independent review and corrective verification

One fresh whole-branch reviewer inspected `89f4561..824a723` against the approved design, plan and review focus. The reviewer independently passed all 92 original B7 tests and exercised real retention/VM rollback. It found two important issues, no critical or minor findings, and no behaviors declined for judgment:

1. Ordinary rollback/progress-removal/timeout-restoration errors could escape optional B7 processing, skip remaining cleanup or mask an interrupt. Cleanup now attempts each step independently, releases the memory lock unconditionally and reports failure through a bounded logger diagnostic. A failed rollback/progress removal prevents diagnostic transactions. Failure diagnostics own only their own transaction. KeyboardInterrupt/SystemExit propagate even when cleanup also fails, including interruption during diagnostic emission. Actual storage failure can still affect later existing core operations; B7 does not claim to repair an unusable connection.
2. Nested domains were individually valid but contradictory across fields. The reader now rejects observation timestamps after transition completion, runtime measurements without singleton-source identity, and failure counts/status/reasons inconsistent with valid metadata.

Twelve new regression cases were observed failing before fixes: four cleanup fault sites, two primary interrupts with cleanup failure, two diagnostic interrupts, and four observer contradictions. The final focused suite passes **77** tests; the complete suite passes **646**, with zero skips and the two existing dependency warnings. All six scenario CLIs, compilation, whitespace checks and historical/core-file byte comparisons pass again. No review finding was deferred; no design ruling was needed. The approved spec and original seven artifacts remain unchanged.

### Delivery boundary

Source changes are committed locally on `seed-0.2-b7`. Automatic approval review rejected the attempted push because explicit authorization is required to transfer this implementation/source history to the `Jeruzael/SEED` remote. The rejected command did not run. No implementation PR, hosted B7 run, merge or deployment occurred. The owner must approve pushing the final branch and opening a draft PR before hosted Linux 3.11/3.13 and macOS 3.13 acceptance can be completed. B7 therefore remains **IMPLEMENTED, locally verified**, not fully VERIFIED. B8–B10 and the installed organism remain untouched.


### B7 hosted verification closure — 2026-09-25

This record supersedes the earlier B7 implementation/delivery checkpoints above without rewriting their historical evidence. [PR #10](https://github.com/Jeruzael/SEED/pull/10) merged as master `ab7c2b45508828685fc9b0a65807e08cee1cff98` (Merge pull request #10 from Jeruzael/seed-0.2-b7). The documentation-closure task fetched origin and confirmed that exact clean starting master before creating `docs/b7-verification-closure`.

Post-merge [SEED verification run 36104979944](https://github.com/Jeruzael/SEED/actions/runs/36104979944) completed successfully on that exact merge commit:

| Exact check | Python | Full suite | Standalone scenarios |
| --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 646 passed | Not configured for this job; scenario tests remain in pytest |
| `test (linux-py313)` | 3.13.15 | 646 passed | All six passed |
| `test (macos-py313)` | 3.13.15 | 646 passed | All six passed |

The six standalone scenarios are `baseline_scenario`, `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`, `semantic_scenario` and `self_model_scenario`. GitHub job results were independently confirmed during this closure. The supplied artifact-inspection record confirms for all three jobs: `checked_out_sha` equals `ab7c2b45508828685fc9b0a65807e08cee1cff98`, `dirty_tree` is empty, dependency installation exit is 0, pip check succeeds, pytest exit is 0 and the requirements-lock.txt hash is unchanged.

**B7 status: VERIFIED at source/CI level. Schema: v6.** Deployment/live-device validation remains **NOT PERFORMED**; the installed organism is untouched. The low-disk reward/consolidation decision mismatch remains **OPEN**. B8–B10 remain **NOT STARTED**. B8 may begin only under separate explicit authorization and design scope.

This closure changes only the five current-state documentation files. Production code, tests, schema/migrations, workflow behavior, dependencies and historical baselines remain unchanged. The documentation PR is separate from the verified B7 merge and must not be represented as covered by the earlier run.


## B8 design execution record — 2026-09-25

**Authorization:** the owner's SEED_B8_Decision_System_Design_Instructions.md and
explicit instruction authorize design/specification only. Production implementation,
migrations, tests, APIs, UI, B9–B10 and installation remain unauthorized.

**Starting state:** fetched origin, checked out master, fast-forward pulled and
verified clean HEAD/origin/master at `92e6aa47ec01d80e123e1c9a90c10f9e59e367fb`
(PR #11 documentation closure), then created `seed-0.2-b8`. No reset/rewrite or B7
branch reuse. Software version 0.2/schema 6 remain unchanged. Owner-supplied exact-master
[run 36121878229](https://github.com/Jeruzael/SEED/actions/runs/36121878229) reports
646 passes on Linux 3.11 / Linux 3.13 / macOS 3.13 and six scenarios on both 3.13 jobs; this
phase does not claim another hosted artifact audit.

**Fresh baseline:** `.venv/bin/python -m pytest -q` → **646 passed, zero failures or
skips, two existing warnings**, Python 3.13.15, exit 0. All six standalone commands
`.venv/bin/python -m tests.baseline_scenario`, `tests.prediction_error_scenario`,
`tests.world_model_scenario`, `tests.curiosity_scenario`, `tests.semantic_scenario`
and `tests.self_model_scenario` (each with the same interpreter/module invocation)
exited 0 with valid JSON exactly matching saved B7 outputs. Resolved temporary homes
and synthetic sensors only; ignored audit files under `.review-artifacts/b8-design/`.
All eight B0–B7 artifact hashes remain unchanged; no installed home was accessed.

**Deliverable:** [Decision-System Upgrade design](superpowers/specs/2026-09-25-b8-decision-system-design.md),
including required evidence inventory, alternatives, exact math, strict healthy and
degraded examples, future deterministic scenarios/tests/file map and 16-point written
self-review. This is an inline design review, not independent code review or execution
of future B8 acceptance tests.

**Selected recommendation:** separate `decision_v1` with one keyed Q snapshot and
one raw 200-row prediction-history snapshot; all four predictions precede selection.
Keep legacy reward/Q update/visits/alpha; use bounded Q component and forecast resource
risk/support uncertainty: `0.50*Q + 0.35*(1-R) + 0.15*(1-U)`. Hard costly-action
resource constraints apply to exploration and exploitation. Epsilon remains the
exploration probability among eligible actions. Unsupported auxiliary evidence falls
back to eligible raw-Q ordering. Following owner review, exploitation/fallback ties
use injected uniform random choice among eligible maxima; singleton winners consume
no choice call, and choice_index identifies the actual selection_candidates pool. B4/B5/B6/B7 feedback, information gain, cost proxies and goals are
excluded with explicit reasons. No resource or intelligence improvement is claimed.

**Low-disk design:** keep the old reward; exclude autonomous consolidate when B6's
known-resource guard would suppress work, and guard autonomous reflect equivalently.
Owner commands retain their existing availability/audits. The issue remains OPEN in
implemented code until separately authorized implementation is verified.

**Persistence/inspection proposal:** additive schema 7 `decision_records`, keyed to
transitions, compact three-target candidate evidence and selected-prediction digest,
16 KiB bound, atomic with the
existing experience group and no historical backfill. Bounded DECISION summary and
two future read-only inspection routes; no frontend. A necessary narrow B7 schema 6/7
compatibility change is specified without changing self_model_v1 meaning or relabeling
old snapshots. Current schema, source, tests and endpoints are unchanged.

**Validation and scope:** strict example JSON and literal score checks, proposed DDL
syntax in a temporary in-memory database, required headings, relative links, whitespace,
baseline hashes and exact documentation-only scope checked. These document checks do
not implement B8 tests or run migration on SEED memory. Only this tracker,
`docs/implementation-log.md` and the new spec change. README, architecture, review
follow-ups, verification guide, CI, dependencies and every baseline are untouched.

**Delivery:** local documentation-only commit `docs: design B8 decision system`;
resolved hash and clean-tree result supplied after commit. No push/PR/merge, production
implementation or live deployment is part of this delivery. Stop for owner review.

B8 design/specification: **AMENDED AND COMPLETE FOR OWNER REVIEW**.
B8 implementation: **NOT STARTED**.
B9–B10: **NOT STARTED**.
Installed organism: **UNTOUCHED**.


### B8 owner-review amendment — 2026-09-26

The owner explicitly authorized SEED_B8_Design_Amendment_Instructions.md, documentation
only. Starting clean `seed-0.2-b8`/origin branch HEAD was
`3014625fe031b3b6d71f1d0320ce62b627569acf`, one commit ahead of verified master
`92e6aa47ec01d80e123e1c9a90c10f9e59e367fb`, zero behind. Fetch/checkout/status/log
confirmed that state; no reset, new branch, implementation plan or source edit.

**Owner review found 0 Critical, 2 Important, 1 Minor design findings.** The amended
specification resolves these design findings only:

1. **Important — deterministic rest tie bias:** remove fixed priority. Composite
   ties use absolute 1e-12 tolerance, fallback ties use exact raw-Q equality, and an
   injected choice selects uniformly among eligible tied maxima. Epsilon's separate
   draw remains `u < epsilon`. Unique pools consume no choice; choice_index is null
   then and otherwise indexes selection_candidates in every mode.
2. **Important — oversized/redundant durable record:** 16,384-byte compact contract
   with a four-field history summary, three resource projections per candidate,
   components/Q/eligibility, and selected_prediction_sha256. No row/contributor ledger,
   four full forecasts or duplicated selected prediction. The full selected B2 payload
   remains in transitions.prediction_json; canonical digest equality is checked before
   action/persistence and on bounded reads. Source-clock count/maximum metadata preserves
   freshness validation. Lifetime growth remains unbounded; no pruning is introduced.
3. **Minor — fatal stale expiry:** >5-second selection age skips without action,
   reward/Q/visits, experience/transition/decision or completed-cycle B3–B7 updates.
   A <=512-byte diagnostic expires the attempt. Explicit completed/skipped/stopped
   CycleResult semantics keep retry distinct from stop/fatal errors. Retry waits the
   captured observe_interval (default 8 seconds, validated 8..3600); fresh perception
   occurs in the next normal cycle. Existing interruptible waits prevent busy loops.

Read API limits now use 16,385-byte sentinels per record/prediction/pre-state,
49,155 input payload bytes per item and 2,457,750 for 50 items, plus bounded metadata.
List summaries<=1,024 bytes, list response<=53,248 bytes, detail<=17,408 bytes;
detail returns compact record only. No inference, reconstruction or rescore on reads.
The proposed v7 table changes only its JSON size CHECK; current schema is still 6.

Validation: both complete JSON examples parse and encode to **4,195 / 4,292 bytes**
with the exact compact encoding; selected-prediction digests checked against canonical
B2 payloads; normalization/conflict/partial/degraded/tie arithmetic and API budgets
recalculated. Markdown/links/whitespace and all eight historical artifact hashes
checked. Product source/tests are unchanged; the product suite was not rerun for this
amendment. The original 646-pass baseline above remains historical evidence.

Only the B8 specification and two tracker documents change. Local commit title:
`docs: refine B8 decision design`; resolved SHA and clean-tree status are reported
in the handoff. No push/PR, code/tests/migration/API/UI, B9/B10 or installed-home work.
The low-disk mismatch remains OPEN in implemented code.

B8 design/specification: **AMENDED AND COMPLETE FOR OWNER REVIEW**.
B8 implementation: **NOT STARTED**.
B9–B10: **NOT STARTED**.
Installed organism: **UNTOUCHED**. Stop for owner review.


## B8 implementation — 2026-09-28

The owner reviewed the amendment and authorized implementation on 2026-09-27, then directed continuation on 2026-09-28. Work remained on `seed-0.2-b8` from approved design `4c24d7e`, using the [implementation plan](superpowers/plans/2026-09-27-seed-b8.md). No installed-home, push, merge, deployment, B9 or B10 work was performed.

Implemented separate bounded snapshot/selection and pure frozen-record contracts; shared B2 batch inference; additive schema7 decision persistence; explicit completed/skipped/stopped cycle results; and two read-only decision endpoints. The current autonomous ordering is documented in [architecture](architecture.md#autonomous-cycle-and-ordering). Q values and visits remain raw, reward/update formulas and delays remain unchanged, and B4/B5/B6/B7 remain downstream-only. B7 accepts retained schema6 snapshots and reports schema7 only after a new publication.

The [B8 comparison](baselines/seed-0.2-b8-comparison.json) covers fallback, low disk, constraints/equality/charging, conflicting and partial forecasts, exploration, both injected tie winners, epsilon equality, stale history, prospective payload identity, Q compatibility, owner low-disk audit, restart, and five-second stale boundaries. Its eight historical artifact hashes match the approved base. The eight-context autonomous control now selects observe four times and rest four times; degraded rest Q is 1.09575648 after four visits. A direct legacy Learner regression preserves the former observe/reflect/consolidate/rest sequence and historical formulas.

Historical scenario compatibility uses explicit leaf changes: new control action/Q/support counts, current schema, two known source hashes (earlier body parser and B8 shared predictor), and seven fields in the policy-reflection fixture. That fixture now starts with eligible load .2 and observes load1e300; its B5 surprise magnitude, score .925 and already_reflected suppression remain exact. All other B3/B4/B5/B6/B7 calculation fields remain compared to immutable historical artifacts.

Independent fresh-context review found 0 Critical and 2 Important issues: inconsistent frozen policy provenance accepted by the reader, and invalid UTF-8 scalar text failing an entire page. Six failing regressions proved them; both were fixed with structural support/reason validation and canonical SQL scalar projection. No review findings remain deferred. Additional regressions verify VM interruption, cleanup/lock release and KeyboardInterrupt, read-only corrupt-slot pagination, whole-experience rollback, owner stop, pre-telemetry state validation, and a full delayed nonfatal retry. Final command results are recorded in [verification](verification.md#b8-local-verification--2026-09-28).

Status remains IMPLEMENTED pending hosted acceptance/owner review; local correctness evidence is not a claim of deployment or measured developmental improvement.


### B8 PR-head hosted acceptance — 2026-09-28

[PR #12 — Seed 0.2 b8](https://github.com/Jeruzael/SEED/pull/12) is **open**, from `seed-0.2-b8` to `master`, and is not merged. Base master at PR creation and at this checkpoint: `92e6aa47ec01d80e123e1c9a90c10f9e59e367fb` (B7/schema v6). The exact verified implementation head is `acaccce889b18d165252c6977d41e5113e74e681`. [SEED verification run 36407866250](https://github.com/Jeruzael/SEED/actions/runs/36407866250) completed **SUCCESS** for that head.

| Exact check | Python | Tests | Standalone scenarios | Artifact ID |
| --- | --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 747 passed; 2 existing warnings | Intentionally disabled by matrix | `10963505882` |
| `test (linux-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed | `10963101024` |
| `test (macos-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed | `10962179746` |

The seven scenarios are `baseline_scenario`, `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`, `semantic_scenario`, `self_model_scenario`, and `decision_scenario`. The owner-supplied artifact-inspection record confirms:

- All three `checked_out_sha` values equal `acaccce889b18d165252c6977d41e5113e74e681`; each `dirty_tree` is empty.
- `dependencies.exit = 0`, `pytest.exit = 0`, and successful `pip check` on every job.
- The unchanged requirements-lock SHA-256 is `1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769`.
- Both Python 3.13 artifacts have `scenarios.exit = 0`, seven byte-for-byte identical Linux/macOS scenario JSON outputs, and empty scenario stderr.

GitHub metadata and job logs were checked during this cleanup: PR state/base/head, run and job success, Python versions, 747-test results, scenario-step outcomes and all three artifact IDs match that record. The artifact-content findings above retain their supplied inspection provenance.

Status at this acceptance checkpoint: implementation **IMPLEMENTED**; local verification **PASS**; hosted acceptance of the stated implementation SHA **PASS**; merged to master **NO**; exact post-merge master verification **NOT RUN**; B8 overall **NOT YET VERIFIED**. No deployment, live-memory migration or restart occurred; B9–B10 remain **NOT STARTED**.

This documentation update creates a new PR head. Run 36407866250 does **not** cover it. All three exact checks must pass on the final documentation SHA before merge readiness; merge then requires owner direction, followed by verification of the exact merge commit on master before marking B8 VERIFIED. No history rewrite or automatic merge is authorized.


### B8 hosted verification closure — 2026-09-29

#### Merge identity

[PR #12](https://github.com/Jeruzael/SEED/pull/12) is merged into `master`. Final PR documentation head: `a8760bd2fab33c185ff25945bf74f31934666143`. B8 merge commit: `e0075e21f545921324aa5d5c9e2f4217b0a06cca`, with message `Merge pull request #12 from Jeruzael/seed-0.2-b8` / `Seed 0.2 b8`. Local master and GitHub master both matched this merge with a clean local working tree before closure edits. SSH fetch was unavailable to this session; the authenticated GitHub connection supplied the remote verification.

#### Hosted run and matrix

[Post-merge run 36443249417](https://github.com/Jeruzael/SEED/actions/runs/36443249417) (`SEED verification`) completed **SUCCESS**, event `push`, exact `head_sha = e0075e21f545921324aa5d5c9e2f4217b0a06cca`. All three jobs checked out that exact merge. This Sep 29 closure records the Sep 28 merge/run checkpoint.

| Exact check | Python | Tests | Standalone scenarios |
| --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 747 passed; 2 existing warnings | Intentionally not configured by matrix |
| `test (linux-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |
| `test (macos-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |

#### Scenarios

Both Python 3.13 jobs passed all seven standalone scenarios: `baseline_scenario`, `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`, `semantic_scenario`, `self_model_scenario`, and `decision_scenario`. The supplied artifact audit confirms byte-for-byte identical Linux/macOS scenario JSON outputs and empty stderr for all fourteen executions. Linux Python 3.11 intentionally omits the standalone step; its full pytest suite still includes scenario tests.

#### Artifact audit

| Hosted artifact | Artifact ID | SHA-256 digest |
| --- | --- | --- |
| Linux Python 3.11 | `10978873702` | `fc928359b4ff8a8b723b412a3abed07734c0870be1e10c0f2da6d4469a7b9a43` |
| Linux Python 3.13 | `10978124787` | `da9ac8764e56b0df48c7a022bc9854deaf3e756506e26592bd6268382f9563ae` |
| macOS Python 3.13 | `10979428432` | `86e0c061282f17c69e97da615306958a31380b20a78b2cbff6673ca581fbb5b8` |

The owner-supplied post-merge artifact-inspection record confirms:

- All three `checked_out_sha` and `event_sha` values equal `e0075e21f545921324aa5d5c9e2f4217b0a06cca`; each `dirty_tree` is empty (`""`).
- Every job has `dependencies.exit = 0`, `pytest.exit = 0`, and successful `pip check`.
- The requirements-lock SHA-256 remains `1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769`.
- Both Python 3.13 artifacts have `scenarios.exit = 0`. All seven Linux/macOS scenario JSON outputs are byte-for-byte identical, and all fourteen scenario stderr logs are empty.

During this closure, GitHub PR/merge identity, run event/head/success, exact job names, Python versions, 747-test results, scenario-step outcomes, and artifact IDs/digests were independently corroborated. Artifact-content findings above retain the supplied inspection provenance.

#### Boundaries and final B8 status

This verifies source/hosted CI behavior on the exact B8 merge commit. It does not constitute installation, live-memory migration, real-device sensor validation, or deployment certification. No install, restart, live-memory migration or deployment was performed; installed SEED remains **UNTOUCHED**.

B0–B8: **VERIFIED at source/CI level**. B8 merge and exact post-merge hosted verification: **COMPLETE**. Schema: **v7** in source. B9–B10: **NOT STARTED**. Deployment/live-device validation: **NOT PERFORMED**. Autonomous low-disk eligibility is resolved and verified; legacy reward remains unchanged and consolidation does not reclaim disk.

This six-file documentation closure is published for owner review and must not merge automatically. Normal CI applies to its PR head. After owner-directed merge, verify only documentation scope and its own green CI; the established B8 technical acceptance stays tied to `e0075e21f545921324aa5d5c9e2f4217b0a06cca`. A later documentation merge does not require another acceptance-documentation cycle.


## B9 design execution record — 2026-09-29

Authorized scope is design/specification and the two tracker documents only. No B9 implementation plan, production code, tests, routes, migrations, dependencies, deployment or B10 work is included. The local design commit is not authorized for push or a PR.

**Baseline:** `seed-0.2-b9` starts from exact verified master `af05f6566c026cd5438453dada85c92e1a4f2bc4` (PR #13 documentation closure), clean before branching. Authenticated GitHub metadata and job logs confirm exact master run **36454551620**: **747 passed** in each Linux Python 3.11/3.13 and macOS Python 3.13 job; all seven standalone scenarios passed on both 3.13 jobs. SSH fetch failed with `Permission denied (publickey)`; the signed GitHub merge object was imported only after its SHA matched, then local master advanced by fast-forward. No remote write occurred. This documentation baseline does not replace B8’s implementation-merge verification or imply deployment.

**Design:** The [Astra specification](superpowers/specs/2026-09-29-b9-astra-development-ui-design.md) selects the existing FastAPI/vanilla ES-module shell with a DEVELOPMENT section. A framework rewrite and separate frontend/service are rejected because the existing shell has no blocking limitation. The seven designed views are Development, Predictions, World Model, Curiosity, Semantic Memory, Self Model and Decisions. Six existing observer views remain; the four OPERATE placeholders remain unimplemented; metadata stays Observer Edition 0.1.

**Read contracts:** Proposed `GET /api/predictions` and `GET /api/predictions/{transition_id}` expose stored B1/B2/B3 evidence without inference/evaluation. Inclusive signed-64-bit pagination defaults to20/max50; list/detail use at most4/3 SELECTs and300000 VM steps. Each JSON payload has a16384-byte limit and16385-byte SQL sentinel; compact list/detail responses cap at27648/35840 bytes. No schema/core change is needed. The audit also proved byte/corruption/work gaps in older B4–B6 readers, retained counts and direct episode detail, so the design specifies narrow future guards and a semantic source JOIN while preserving existing routes/cursors. B7/B8 services remain unchanged. The landing page is a separately timed evidence mosaic with at most seven cold GETs including bootstrap; no background Astra polling or implicit status/process read.

**Interpretation and verification contract:** The design fixes Learning’s future highest-Q wording, preserves Concepts versus B6 Semantic Memory, defines lossless signed-64-bit links, explicit unavailable/legacy/corrupt states, source clocks, query/payload/render bounds, accessibility/mobile wireframes and deterministic temporary-home fixture cases. Browser strategy keeps dependencies unchanged and requires a future documented manual pass in addition to automated API/asset/security tests. These are designed acceptance criteria, not delivered UI or B10 evaluation.

**Fresh characterization:** Python **3.13.15**, `.venv/bin/python -m pytest -q tests/dashboard` with a new temporary `SEED_HOME`: **160 passed, 2 existing warnings in 2.57s**. No tests were added or changed; no fresh full suite, standalone scenarios, browser pass or screenshots were performed for this documentation task. Documentation validation passed: exactly the three allowed files differ from the baseline, fences are balanced, all53 internal links/anchors resolve, literal bounds/fixture arithmetic pass, historical B8 sections remain byte-identical, and `git diff --check` passes. Local checkpoint `4087fefcfe12fa9d582bba3cb5e53ddeae00d735` appeared during final validation and is preserved; the design completion is committed separately without rewriting it.

**Status:** B0–B8 **VERIFIED at source/CI level**; B9 overall **IN PROGRESS**; B9 design/specification **COMPLETE FOR OWNER REVIEW**; B9 implementation **NOT STARTED**; B10 **NOT STARTED**. Schema **v7**. Deployment/live-device validation **NOT PERFORMED**. Installed organism **UNTOUCHED**. Stop after the local documentation commit for owner review.


### B9 owner-review preparation amendment — 2026-09-29

The supplied independent review after the pushed design checkpoint reported **0 Critical, 1 Important, 0 Minor**. Finding: the newly bounded `/api/development` may return503 `development_read_unavailable`, rejecting the existing Overview `Promise.all` and hiding unrelated valid evidence. Read-only inspection confirmed this behavior in `dashboard/static/views/overview.js`.

**Resolution in the design:** Future Overview settles development independently while status/storage/health retain their existing required-source and failure behavior. Valid identity/activity/resource/storage/health evidence remains visible. Recorded experiences and all other development-only metrics show **Unavailable**, never zero; Development, measured shows an explicit bounded-count notice and no fabricated lifecycle timeline. The backend remains exact counts or bounded503, at most300000 VM operations with busy_timeout0; no estimates, sampling or extra retries. The specification adds only the `overview.js` compatibility responsibility to its future file map and defines the matching automated/manual regression contract, deterministic temporary-home budget-exhaustion case and self-review answer. No implementation is claimed.

**Revision and scope:** Start `a6aa042c343c5e90dcf74c3fc90436e006d04e98`, with parent checkpoint `4087fefcfe12fa9d582bba3cb5e53ddeae00d735` preserved. The tree was clean. SSH fetch again failed with `Permission denied (publickey)`; authenticated GitHub reads confirmed the branch at the same SHA, master at `af05f6566c026cd5438453dada85c92e1a4f2bc4`, no open branch PR and no hosted run for the starting head. Publication was attempted through the existing authenticated GitHub connection, but automatic approval review rejected the document upload because it required direct trusted authorization for the payload and destination. At that failed-attempt checkpoint, no remote branch update occurred and publication awaited explicit owner confirmation. **Superseding publication fact:** the owner subsequently published the completed amendment successfully; authenticated GitHub verification now confirms remote `seed-0.2-b9` at `3dc9b8fdab2f4c12227e2371e679a57a02a5cf6f`. No PR has been opened, and no hosted CI is claimed for that branch head. Publication does not authorize implementation. Prior commits remain unchanged. Only the specification and two tracker documents change. No fresh dashboard test run is needed for this documentation amendment; the earlier **160 passed / 2 existing warnings, Python3.13.15** remains local characterization, not independent hosted evidence.

**Mechanical validation:** PASS — three authorized documents only; balanced Markdown fences; all 53 internal file/anchor links resolve; literal byte/fixture arithmetic valid; development backend budget unchanged; future file map adds only `overview.js`; historical B8 sections byte-identical; no unresolved task markers; `git diff --check` clean. No fresh suite/browser run or hosted success is claimed.

**Status:** B0–B8 **VERIFIED at source/CI level**; B9 overall **IN PROGRESS**; B9 design/specification **COMPLETE FOR OWNER REVIEW**; B9 implementation **NOT STARTED**; B10 **NOT STARTED**. Schema **v7**. Deployment/live-device validation **NOT PERFORMED**. Installed organism **UNTOUCHED**. Publish only the documentation amendment to `seed-0.2-b9`, then stop for owner review; no PR or implementation plan.


### B9 owner approval and publication-status cleanup — 2026-09-29

**Owner approval:** The owner approved the B9 Astra Development UI design/specification at `3dc9b8fdab2f4c12227e2371e679a57a02a5cf6f`, including the Overview compatibility amendment, as the architectural contract for B9. Approval covers design acceptance and this documentation cleanup only. The owner-supplied closure reports **0 Critical / 0 Important remaining**; the historical supplied review remains **0 Critical / 1 Important / 0 Minor**, with its Important finding resolved in the design. No new independent review or implementation is claimed.

**Publication verified:** The earlier upload rejection remains recorded above as historical. The owner subsequently published `3dc9b8f` successfully. Authenticated GitHub reads confirm the full SHA on `seed-0.2-b9`, master at `af05f6566c026cd5438453dada85c92e1a4f2bc4`, no open branch PR and no hosted workflow run for the approved design head. Local HEAD matches the published head, the starting tree is clean, and the branch is three commits ahead of that master with no divergence. SSH fetch still fails with public-key authentication; this verification uses the authenticated repository connection and does not claim a successful SSH pull.

**Cleanup scope:** Only this tracker and `docs/implementation-log.md` change. The specification remains byte-identical to the owner-approved commit; its review-stage heading is retained as part of that approved artifact, while these current-state records carry owner acceptance. All three existing B9 commits and historical B0–B8 records are preserved. No fresh tests were run: Python3.13.15, **160 passed / 2 existing warnings** remains historical local dashboard characterization, not hosted branch evidence.

**Current status:** B0–B8 **VERIFIED at source/CI level**; B9 overall **IN PROGRESS**; B9 design/specification **OWNER APPROVED / COMPLETE**; B9 implementation **NOT STARTED**; B10 **NOT STARTED**. Schema **v7**. Deployment/live-device validation **NOT PERFORMED**. Installed organism **UNTOUCHED**. Commit and publish only this cleanup, then stop for the next owner instruction. No implementation plan, production/test/API/schema/dependency change, PR, deployment, installed-home access or B10 work is authorized.

**Cleanup validation:** PASS — only the two intended documentation files differ; the approved specification is byte-identical; prior B9 commits and historical B8 sections are preserved; stale pending-publication wording is superseded; Markdown fences and all 50 internal links/anchors in these two documents are valid; `git diff --check` is clean.


## B9 implementation — 2026-09-30

The owner authorized implementation after published cleanup `16dcd8b4c60741092c0c538f08f0bf85fef27de9`. Native execution continued on `seed-0.2-b9` under the [implementation plan](superpowers/plans/2026-09-29-b9-astra-development-ui.md). Reader/client/view commits are `6f850a4`, `9d197c9`, `ed7e359` and `d8f669f`; the intervening fixture checkpoint `e3bd0fd` is preserved.

Implemented: bounded prediction history/detail; narrow B4–B6, retained-count and exact-episode safeguards; seven manual-refresh Astra views; exact signed64 links; per-source state and clock labels; abort/generation isolation; mobile/focus behavior; Overview partial-count-outage compatibility. Learning no longer claims highest-Q selection explains B8 choices; legacy Concepts and B6 Semantic Memory remain distinct.

Local acceptance: **851 tests passed, 2 existing dependency warnings**; all seven standalone scenarios emitted valid JSON; temporary-fixture browser checks cover all seven views, stored literals, MAX_ID paging, B8 low-disk/corrupt records, B6 history, B7 stale/missing sources, filters, skip/menu focus, six widths, light/dark and Overview count503. Details and limits are in the [verification record](verification.md#b9-local-implementation-verification--2026-09-30). Independent whole-branch review is the remaining local gate. No production core, schema, migration, dependencies, B7/B8 services, baseline artifacts, installed-home data, deployment or B10 changes. This implementation has not been published by this task; the earlier push authorization covered documentation cleanup only.
