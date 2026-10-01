# B9 Astra Development UI Implementation Plan

**Closure update — 2026-10-02:** B9 is MERGED / VERIFIED at source/CI level via PR #14 on master `b7d8b832924c7ff1512708965fa021fed4306866`; all three required jobs succeeded in exact run 36833492768. The implementation/review/publication checkpoints below remain historical; their pending hosted/merge status is superseded by the [canonical closure record](../../seed-0.2-development-plan.md#b9-sourceci-closure--2026-10-02). Deployment/live-device validation remains NOT PERFORMED; installed organism UNTOUCHED. B10 - Development Evaluation & Experimental Foundation is NOT STARTED, with design not yet authorized under this documentation-alignment task.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox tracking.

**Goal:** Implement the owner-approved seven-view Astra observer and bounded stored-evidence readers, preserving existing Overview usability.

**Architecture:** Extend the existing FastAPI/vanilla ES-module dashboard. Stored evidence is validated and bounded in read adapters; browser code formats it without model computation. Preserve observer/operator separation and schema v7.

**Tech Stack:** Existing Python, SQLite, FastAPI, pytest, vanilla JavaScript/HTML/CSS; no dependencies added.

**Spec:** `docs/superpowers/specs/2026-09-29-b9-astra-development-ui-design.md`, owner approved at `3dc9b8f`; implementation starts from published `16dcd8b4c60741092c0c538f08f0bf85fef27de9`.

## Global Constraints

- User authorized implementation after approval/publication; earlier design-only stops are historical. Continue native execution on the existing `seed-0.2-b9` branch.
- No `seed/` changes, schema/migrations, dependencies, operator controls, installed-home access, deployment or B10. Keep B7/B8 read services and Observer Edition 0.1 metadata unchanged.
- New readers: mode=ro, zero busy timeout, scoped read transaction, <=300000 VM steps with 1000-step callback, strict bounded payloads, no producers/sensors/process calls.
- Predictions: inclusive positive signed64 cursor, default20/max50; <=4 list/3 detail SELECTs; source JSON16384/sentinel16385; list27648/detail35840 bytes.
- Existing model maxima/cursors remain unchanged; section8 gives exact row/response ceilings, corruption and legacy envelopes. No corrupt-row refill or per-row source queries.
- Seven Astra views only fetch while active; manual Refresh; ten-second request deadline; seven cold landing requests including bootstrap. Never synthesize zeros, calibration, causality, improvement or historical decision scores.
- Existing six views and four OPERATE placeholders remain. Overview independently settles development counts while required-source error behavior remains unchanged.
- Browser acceptance uses temporary fixtures and existing browser tools; no project browser dependency. Source/CI verification is distinct from deployment.

## Review Focus

1. Near-MAX_ID cursors and escaped numeric-looking strings: exact identity through JSON, links and pages (Task3 and manual Task5).
2. Corrupt source belief versus corrupt semantic record: preserve valid semantic payload, consume corrupt slots (Task2).
3. Partial service outage and navigation cancellation: preserve valid Overview sections and prevent stale DOM writes (Task3/4).
4. Boundary JSON growth after canonical encoding or nested history payload: reject explicitly within byte/work caps (Task1/2).
5. Large filtered retained databases: bounded503, callback cleanup, no empty-success substitution or refill (Task1/2/5).

### Task 1: Shared read guards and prediction projection

**Files:** Create `dashboard/services/evidence_reads.py`, `dashboard/services/predictions.py`, `tests/dashboard/test_predictions.py`; modify `dashboard/services/seed_service.py`, `dashboard/api/observer.py`.

**Interfaces:** `PredictionReadService(store).list(before=None,limit=20)->dict`, `.detail(transition_id)->dict`; `SeedService.predictions`/`prediction` delegate. Shared `bounded_read(store, error_code='evidence_read_unavailable', budget=300000)`, `schema(db, tables)->(version,set)`, `strict_json(raw, limit=16384, array_limit=100, history=False)->dict`, `compact(value)->bytes`, `capped(value,limit,error_code)->dict`, scalar/projection helpers consumed by Task2. Exact field/status/wrapper shapes follow spec7.

- [x] Write tests for absent API, list presence/no full JSON, strict queries, legacy/missing/future schemas, corrupt metadata/payloads, supported shapes, sibling independence, pagination/gaps/MAX_ID, sentinel/canonical bounds, busy/VM/SELECT/response caps and no producer/writes.
- [x] Run `.venv/bin/python -m pytest -q tests/dashboard/test_predictions.py`; observe missing-route/behavior failures before implementing.
- [x] Implement guards and prediction service, delegates and two strict GET routes. Preserve other routes and B7/B8 serialization.
- [x] Run targeted tests then dashboard suite; expected all pass with existing warnings only. Commit `feat: expose bounded prediction evidence`.

### Task 2: Bound older read adapters and retained counts

**Files:** Modify `dashboard/services/evidence_reads.py`, `seed_service.py`, `semantic_memory.py`, `dashboard/api/observer.py`; extend `tests/dashboard/test_world_beliefs.py`, `test_curiosity.py`, `test_semantic_memory.py`, `test_reads.py`, `test_http.py`.

**Interfaces:** Keep existing public service methods/filter/cursor signatures. Shared guards from Task1; valid existing row shapes unchanged, corrupt rows retain reliable IDs and `read_status/read_reason` with null payload. Semantic source LEFT JOIN; history nested payload exception; summary adds valid/corrupt counts. Development remains exact counts or `development_read_unavailable`; direct memory detail uses existing route and explicit warnings.

- [x] Add failing cases for malformed/oversized/duplicate JSON, scalar/type corruption, canonical expansion, nested history payload, corrupt source isolation, no-refill cursors, bounded summary denominators, missing supporting tables/future schemas, zero timeout/VM cleanup and SELECT ceilings.
- [x] Add count-budget failure preserving no mutation and direct memory state/note/tag limits. Run targeted tests; expected failures against existing permissive readers.
- [x] Implement spec8 adapters, caps and compact route responses without changing legacy list, learner, process or operator code.
- [x] Run all dashboard tests and full suite; expected passing. Commit `feat: bound Astra legacy evidence reads`.

### Task 3: Evidence client, navigation and Overview compatibility

**Files:** Modify `dashboard/static/api.js`, `app.js`, `index.html`, `styles.css`, `views/overview.js`, `views/learning.js`, `views/concepts.js`, `views/memory.js`; create `dashboard/static/evidence.js`, `tests/dashboard/test_astra_assets.py`.

**Interfaces:** `api.getEvidence(path,signal,maxBytes)` returns bounded lossless parsed JSON and typed HTTP errors. Shared evidence helpers own ID/hash validation, badges, timestamps, links, paging and per-record details. Renderers take `(root,signal)` and derive validated hash queries from shared helpers. API path allowlist/caps follow spec12; renderer generation/abort handling resides in app.

- [x] Write failing asset/security contracts for new evidence helper, strict query-aware hashes, four required/optional Overview fetch outcomes, explicit missing values, no forbidden dependencies and focus/mobile semantics.
- [x] Implement bounded streaming/lossless parsing and shared helpers. Keep old `api.get` compatible; preserve HTTP code/status for Overview.
- [x] Implement shell routing/cleanup/focus/inert mobile navigation, preserve #main, remove only Astra implicit status fetch, and preserve existing Overview refresh/SSE lifecycle.
- [x] Isolate Overview development failure, fix Learning/Concepts wording and missing Q defaults, add exact memory detail hash mode. No model math or guessed provenance.
- [x] Run dashboard asset/HTTP tests; actual browser behavior is verified in Task5. Commit `feat: add Astra navigation and evidence client`.

### Task 4: Seven Astra views

**Files:** Create `dashboard/static/views/{development,predictions,world_model,curiosity,semantic_memory,self_model,decisions}.js`; extend `test_astra_assets.py`.

**Interfaces:** Export `renderDevelopment`, `renderPredictions`, `renderWorldModel`, `renderCuriosity`, `renderSemanticMemory`, `renderSelfModel`, `renderDecisions`; consume Task3 helpers and unchanged/new API envelopes from Tasks1/2. No new routes/model projections beyond the specification.

- [x] Add failing registration/source/bounds/copy tests for all seven modules and preserved six observers/four placeholders.
- [x] Implement landing six independent source reads plus explicit optional count load; independent card states and read/source times.
- [x] Implement predictions, world, curiosity, semantic tabs/history, self-model and frozen decisions with specified fields, filters, cursor semantics and explicit details. Do not hide required evidence on mobile.
- [x] Run asset/API/dashboard tests; expected passing. Commit `feat: render Astra development evidence views`.

### Task 5: Deterministic fixtures, browser acceptance and closure

**Files:** Create `tests/dashboard/astra_fixture.py`; extend relevant dashboard tests; update `README.md`, `docs/architecture.md`, `docs/verification.md`, `docs/seed-0.2-development-plan.md`, `docs/implementation-log.md` with actual results, preserving historical evidence and baselines.

**Interfaces:** Fixture builder takes an explicit temporary destination and case, returns ID manifest; never defaults to installed home. Cases follow spec16 including Overview count-budget exhaustion. Existing model producers only construct temporary fixtures.

- [x] Add fixture assertions for empty/legacy/B1–B8, corruption/boundaries and development-only budget failure; run red before implementing fixture support.
- [x] Build fixture and run full suite with a disposable SEED_HOME; verify unchanged baselines/core/B7/B8/schema/dependencies.
- [x] Launch dashboard only against temporary fixtures in observer mode. Use available browser tools for spec15 manual acceptance: seven routes/details/filters, MAX_ID, error states, Overview degraded counts, keyboard/focus/menu, widths320/760/761/1120/1121/1440, themes/reduced motion, request caps/abort and SSE coexistence. Record any unavailable verification honestly.
- [x] Update docs with delivered behavior, source SHA, test results and browser evidence; do not mark hosted/deployed verification without evidence. Commit implementation closure.
- [x] Dispatch one fresh whole-branch reviewer under executing-plans; fix actionable correctness findings with red/green regression tests and rerun required checks. Stop before merge/deployment/B10. The later C0–C18 owner instruction authorizes branch publication after review, then a stop before PR/merge/deployment/B10.


## Owner-authorized corrective pass (C0–C18)

Start `20e19add6ee35c9dc120510333b0207d25294cb8`; preserve all existing commits. The owner's later corrective instructions supersede the earlier cleanup-only publication boundary: publish the corrected branch only after correction, verification and fresh review gates, then stop without a PR. Core/schema/dependencies/workflows/baselines/B7/B8 readers/installed home/B10 remain outside scope. Historically, the prior fresh-review attempt was interrupted by a provider usage limit and Task5's review checkbox stayed open; the later successful whole-branch review below closes that gate.

- [x] C0: clean local expected HEAD; SSH fetch/pull attempted, authenticated GitHub ref confirms exact remote SHA.
- [x] C1–C7/C9: reproduce and fix bootstrap retry, B3/B5 structural evidence, disclosure/focus/captions, complete Overview degradation, placeholders, Astra identity and3/2/1 grid.
- [x] C8: correct current tracker status; retain historical design-only checkpoints.
- [x] C10–C14: focused/full tests, seven scenarios, compileall, pip check, scope audit and corrected temporary-browser matrix.
- [x] C15–C16: fresh whole-branch review; fix/recheck actionable findings; record actual final evidence.
- [x] C17: preserve existing commits; commit corrections and final evidence documentation.
- [x] C18: preserved branch published by the owner; authenticated GitHub confirms remote `seed-0.2-b9` at `1f7d7692fc397826d4dc79dcfe924073b0ee5bb0`. Earlier SSH/HTTPS attempts failed at their recorded checkpoint; that authentication blocker is historical and superseded by successful publication. No history was rewritten and no PR was open at the start of this cleanup. The subsequent owner instruction authorizes final documentation cleanup, push, PR creation and exact-head hosted CI inspection, then a stop before merge/deployment/B10.

Final reviewed source head `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981`, base `16dcd8b`: independent PASS,0 Critical/0 Important/0 Minor, none deferred. Local and independent148-focused/883-full results passed with2 existing warnings. All7 scenarios, compileall, pip check, whitespace and unchanged-category audits passed. Corrected browser matrix and limitations are recorded in docs/verification.md; deployment/live-device/hosted acceptance is not claimed. B9 overall remains NOT YET VERIFIED.
