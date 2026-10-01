# B9 — Astra Development UI design

Status: **COMPLETE FOR OWNER REVIEW**. B9 overall: **IN PROGRESS**; implementation: **NOT STARTED**. This is a specification, not an implementation plan or permission to implement. Only this specification, the development tracker and implementation log change. The initial design task authorized a local commit only. The 2026-09-29 review amendment authorizes publishing the documentation amendment to the existing `seed-0.2-b9` branch; no PR is authorized.

## 1. Purpose, baseline and scope

Astra is a local development observatory for the owner to inspect **recorded B1–B8 evidence**, its limits and provenance. It answers what records exist, what was recorded most recently, and what is absent, stale, corrupt or unavailable. It does not decide whether SEED is improving.

Design baseline is master `af05f6566c026cd5438453dada85c92e1a4f2bc4`, `Merge pull request #13 from Jeruzael/docs/b8-verification-closure` / `Document B8 verification closure`. Branch: `seed-0.2-b9`. The working tree was clean before branching. SSH fetch failed with `Permission denied (publickey)`; the authenticated GitHub connection confirmed master, PR #13 and the signed merge object. The identical commit was imported with its original signature after matching its Git object SHA, and local master advanced by fast-forward only. No history was rewritten.

[Master run 36454551620](https://github.com/Jeruzael/SEED/actions/runs/36454551620) completed successfully for exact `af05f656...`, event `push`. Job logs corroborate 747 tests in each of `test (linux-py311)` (Python 3.11.16), `test (linux-py313)` and `test (macos-py313)` (Python 3.13.15). Both 3.13 jobs ran all seven standalone scenarios; 3.11 intentionally omitted that separate step. This is hosted source evidence, not deployment. B8 technical acceptance remains attached to implementation merge `e0075e21f545921324aa5d5c9e2f4217b0a06cca`; the later documentation merge does not redefine it.

Fresh local characterization: `.venv/bin/python -m pytest -q tests/dashboard`, Python **3.13.15**, a new temporary `SEED_HOME`, **160 passed, 2 existing warnings in 2.57s**. The warnings concern Starlette/httpx and the anyio BlockingPortal alias. No fresh full-suite run, browser pass or standalone-scenario run was performed for this design. No tests were added or changed.

Source schema remains **v7** (`seed/migrations.py`). Dashboard metadata currently says **0.1 / Observer Edition** (`dashboard/app.py`). B0–B8 remain VERIFIED at source/CI level. Deployment/live-device validation: **NOT PERFORMED**. Installed organism: **UNTOUCHED**. B10: **NOT STARTED**.

B9 later implementation is limited to read adapters, observer routes, local presentation and their tests. It requires no `seed/` changes, schema, migrations, new telemetry, autonomous behavior, operator features, dependency changes or installed-home access. Do not run `install.sh`, construct `Memory` on installed storage, start/restart the installed organism, or perform B10 experiments. Temporary fixture construction in future tests is distinct from production observer reads.

## 2. Existing implementation audit

The [original dashboard specification](2026-09-21-dashboard-design.md) describes a larger intended product; it is historical intent, not an inventory of delivered UI. The [architecture guide](../../architecture.md) and [README](../../../README.md) provide the current core contracts. The following findings come from implementation and tests at the exact baseline.

| Surface / source | Actual behavior and limits |
| --- | --- |
| `dashboard/app.py`, `dashboard/__main__.py` | Separate FastAPI service; static vanilla HTML/CSS/ES modules; `127.0.0.1` only, default port 8765, no `--host`; proxy headers/access log disabled; no OpenAPI/docs routes. Bootstrap returns source/component/schema identity and operator flag. |
| `dashboard/security.py` | Exactly one expected Host; optional Origin must match; CSP restricts scripts/styles/connections to self; no-store/nosniff/referrer policy; same-origin JSON/token and operator mode required for mutations; 16 KiB mutation body limit. |
| `dashboard/services/read_store.py` | Symlink/path checks for SQLite and sidecars; ordinary connections use SQLite URI `mode=ro`; explicit `write=True` is reserved for existing operator services. Missing DB is 503 and not created; generic SQLite failures become 503. Generic `decode` is permissive and may substitute `{}` for invalid JSON. |
| `dashboard/api/observer.py`, `services/seed_service.py` | Observer endpoints already expose B4–B8 but not historical B1/B2/B3 prediction/evaluation records. Most older list services have row limits but not strict JSON-byte or VM-work bounds. |
| `dashboard/api/stream.py`, `views/activity.js` | SSE polls events every 2 seconds, reads at most 100 events per poll, caps streams at 8 and sends heartbeat every seventh tick; gap/reset/legacy/unavailable states exist. Browser feed keeps latest 500 entries and closes EventSource on abort/cleanup. |
| `dashboard/static/index.html`, `app.js` | Six implemented renderers: Overview, Live Activity, Environment, Memory, Concepts, Learning. OPERATE links for Interaction, Commands, Automation, Settings are placeholders. Router currently treats the whole hash as the page key; it has no query-aware detail links or deliberate heading focus. |
| `dashboard/static/api.js`, `charts.js` | Same-origin fetch, AbortSignal, text-node/`textContent` helpers, tables, native details, accessible SVG sample-table fallback. `response.json()` loses precision for integers beyond JavaScript's safe range; API errors currently discard structured code/status. |
| `dashboard/static/styles.css` | Existing dark/light/system tokens, visible focus, skip link, horizontal table overflow, reduced-motion rule; breakpoints are **max-width 1120px** and **max-width 760px**. Most primary controls are at least 44px, but theme and details controls have smaller overrides. |
| Existing view lifecycle | Overview refreshes every 10 seconds only while visible and not editing/inspecting details. Environment reads stored metadata/history; it does not sense. App currently fetches `/status` after every renderer, adding an uncounted request and process/status work. |
| Existing backend operator surface | Operator router, interaction note/annotation services, command broker, settings revisions, backups and storage helpers exist. Frontend placeholders are not implemented by their existence. `/automations` explicitly returns unavailable/empty. B9 adds no control buttons or writes. |
| Existing tests | `tests/dashboard/` covers read compatibility, model routes, pagination, security, storage/settings/commands/interaction and asset presence. `test_assets.py` fetches registered files and checks the skip/main shell; it is **not browser execution or accessibility certification**. No package manifest, Playwright, Puppeteer or Selenium infrastructure was found. |

The audit included `dashboard/services/{decisions,self_model,semantic_memory,interaction,settings,storage}.py`, all six existing view modules, and the dashboard test inventory and relevant contract tests. Existing storage inventory walks the SEED directory and `/status` probes process/lock state; neither becomes an implicit Astra data source. `/learning`, `/concepts`, `/memories` and `/development` have legacy full-table operations; B9 must not advertise them as already having strict work bounds.

## 3. Architecture choice and component identity

**Select Option B: DEVELOPMENT inside the existing local observatory.** Keep FastAPI, same-origin APIs, ES modules, CSS tokens, security middleware, read-only storage and observer/operator separation. Add the seven named pages and the missing prediction projection. Apply only the narrowly justified read safeguards in section 8; no aggregate cognition endpoint.

| Option | Migration / dependency cost | Security, regression and testing | Accessibility / local behavior | Decision |
| --- | --- | --- | --- | --- |
| A: replace dashboard with framework SPA/build/service shell | Rewrites six working views; new package/build/browser supply chain and deployment packaging | Duplicates established boundaries; broad regression matrix with no evidence benefit | Could be accessible but requires re-proving it; build/CDN assumptions add offline risk | Reject: no blocker in present shell justifies replacement. |
| B: DEVELOPMENT section in existing shell | Seven modules, shared presentation helpers and narrow read adapters; no new dependencies | Reuses Host/Origin/CSP and observer isolation; targeted regression tests | Existing semantic HTML/tables/details and local assets can be extended; concrete focus/mobile fixes specified below | Select. |
| C: `/astra` second frontend or service | Duplicated navigation, identity, packaging and possibly ports/processes | Duplicate security and inconsistent reads/status; more operational/test burden | Separate focus/navigation/theme behavior to verify; no offline benefit | Reject: no separate lifetime, trust or installation boundary is needed. |

Astra names the **DEVELOPMENT surface**, not another process, organism, schema or Operator Edition. Future B9 implementation keeps `DASHBOARD_VERSION='0.1'`, `DASHBOARD_EDITION='Observer Edition'`, bootstrap version fields and footer edition unchanged. No version bump is necessary for this section; component identity remains separate from B9 batch status and schema support. Operator mode continues to be represented by its explicit bootstrap Boolean, never by an inferred edition number.

Keep the SEED / LOCAL OBSERVATORY brand and footer “Local to this Mac” and “No language model connected.” Default HTML title remains `SEED — Local observatory`; active Astra views set the document title to `SEED — Astra / <Page>`. The breadcrumb is `SEED / Astra / <Page>`, page heading is the page name, and an eyebrow says `ASTRA · DEVELOPMENT EVIDENCE`. Existing observer pages keep their titles. Existing OPERATE placeholders say **“Not implemented in this dashboard. B9 adds observation only.”** even when backend operator mode is enabled; they must not suggest that toggling operator mode delivers missing UI.

## 4. Navigation, routes and request lifecycle

Retain order and all six implemented observer views:

```text
OBSERVE
  Overview       #overview
  Live Activity  #activity
  Environment    #environment
  Memory         #memory
  Concepts       #concepts
  Learning       #learning
DEVELOPMENT
  Development    #development
  Predictions    #predictions
  World Model    #world-model
  Curiosity      #curiosity
  Semantic Memory #semantic-memory
  Self Model     #self-model
  Decisions      #decisions
OPERATE
  Interaction    #interaction   [placeholder]
  Commands       #commands      [placeholder]
  Automation     #automation    [placeholder]
  Settings       #settings      [placeholder]
```

| Page | Future module / exported renderer | Accepted hash query and detail mode |
| --- | --- | --- |
| Development | `views/development.js` / `renderDevelopment` | None |
| Predictions | `views/predictions.js` / `renderPredictions` | `before`, `limit`; or `transition=<positive id>` for direct detail |
| World Model | `views/world_model.js` / `renderWorldModel` | `signal`, `scope`, `scope_value`, `after`, `limit`; or `belief=<id>` |
| Curiosity | `views/curiosity.js` / `renderCuriosity` | `before`, `limit`; or `transition=<id>` |
| Semantic Memory | `views/semantic_memory.js` / `renderSemanticMemory` | `tab=memories` (default): `signal`, `scope`, `status`, `after`, `limit`; `tab=runs`: `before`, `limit`; or `semantic=<id>` with optional `history_before`, `limit` |
| Self Model | `views/self_model.js` / `renderSelfModel` | None; singleton only |
| Decisions | `views/decisions.js` / `renderDecisions` | `before`, `limit`; or `transition=<id>` |

For B9 list UI, default `limit=20`, allowed UI choices 20/50; links may use any positive limit within the endpoint's existing maximum (100 for B4–B6, 50 for Predictions/Decisions). Direct detail mode rejects unrelated list/filter parameters instead of silently applying them. Hash parser rejects unknown/repeated keys, invalid IDs and >1024 UTF-8 bytes with an inline “Invalid view link” notice and a link to that page's first page; it does not request data for invalid input. Unknown page keys use Overview as today. Query names are allowlisted per page and values are passed through `URLSearchParams`, never interpolated into SQL or arbitrary URLs.

Preserve `#main` as the skip-link target: focus main without changing the active page or triggering a fallback fetch. Implement query-aware hash routing and browser Back/Forward; changing filters resets cursor; changing page size resets cursor. Newer/Older for descending lists and Previous/Next for ascending lists use a maximum **20 saved cursor descriptors** for the current view, not cached response pages. After 20, discard the oldest descriptor; First page is always available. Do not infer an earlier page by subtracting a page size.

Only the active page loads data. Navigation aborts its controller and closes the previous view cleanup. Each render has a generation token; a late response cannot update DOM, connection status or install a stale cleanup. Call a late renderer's cleanup immediately if its generation expired. B9 pages have manual Refresh, no interval, no EventSource and no hidden prefetch. Paging, filters and details cancel the previous request of the same pane; disable duplicate submissions while pending. A fixed **10-second client deadline** aborts a stalled read and exposes Retry; no automatic retry loops. Overview keeps its current refresh policy and Live Activity remains the only continuous SSE view.

For Astra views, remove the unconditional **post-render `/status` GET**. Their shell indicator says **“Stored evidence · local service reachable”** after a successful read, or “Service unavailable” if all reads fail, never “Core connected” from mere database access. No B9 page calls `/status`, `/storage`, `/health` or process APIs to fabricate freshness. Bootstrap is a single initial GET per app lifetime; refresh does not refetch it. This makes the complete landing budget, including cold bootstrap, seven requests (section 6).

## 5. Evidence matrix and current API inventory

P = persisted record; R = runtime record; F = UI formatting. F may format but not infer or change P/R values. Historical records do not get generic time-to-live expiry. Only B7's read projection and existing runtime freshness policy define staleness.

| Batch | Authoritative source and current exposure | Pagination/filter contract at baseline | Time, unavailable/legacy/corrupt behavior | B9 need and interpretation boundary |
| --- | --- | --- | --- | --- |
| B1 | P: `transitions`, linked `episodes`; Memory API exposes episodes only | No transition-history route. Memories use search/event/sort and offset pages, default 50/max 100, page <=100000 | `started_at`, `completed_at`, episode `ts` are separate; old episodes may have no transition; malformed episode state has warning | New prediction-history projection supplies bounded transition metadata. No invented observations, outcome or causality. |
| B2 | P: `transitions.prediction_json`; no history API | None | SQL NULL is valid pre-B2 absence; model `transition_delta_v1` v1, `next_post_action_observation`; no independent prediction timestamp | Same new projection. Confidence is **evidence support**, not calibrated correctness; `probability_true` is observed Boolean frequency. |
| B3 | P: `transitions.prediction_error_json`; B7 includes a separate bounded summary | None for individual evaluations | SQL NULL is valid pre-B3 absence. Per-signal not_evaluated differs from absent evaluation. Stored aggregate coverage/mean error/accuracy refer to this transition | Same projection; show values exactly. No new rolling trend, score threshold, intelligence or improvement claim. |
| B4 | P: `world_beliefs`; `/world-beliefs`, `/{belief_id}` | Ascending `id > after`, default after 0, default limit 50/max100; signal/scope/scope_value allowlists; limit+1 lookahead; next cursor = last returned ID | created/updated, source first/last transition IDs. Missing table => available false list, detail404. Invalid value JSON currently collapses to `{}` | Existing routes/fields sufficient; bounded/corruption guards required by section 8. Observational distributions, not causal effects; confidence kind evidence_consistency. |
| B5 | P: `curiosity_assessments`; `/curiosity`, `/summary`, `/{transition_id}`; flags may update after claim/completion | Descending `transition_id <= before`, default MAX_ID; limit50/max100; next cursor = last returned ID minus1 if lookahead exists; summary latest <=100 raw rows | `created_at`, `claimed_at`, `completed_at`; no TTL. Stored unavailable assessment differs from missing assessment. Bad components currently `{}`; missing table false/detail404 | Existing routes sufficient plus guards. Existing summary's evaluated-row means are retained with explicit window/denominators; no lifetime or emotional interpretation. |
| B6 | P: `semantic_memories`, `semantic_memory_history`, `consolidation_runs`; four existing route families | Current memories ascending id>after, signal/scope/status filters, default50/max100. History descending revision<=before per semantic ID; runs descending id<=before. Descending next = last returned minus1 with lookahead | Memory created/updated/source belief timestamp; history recorded_at; runs started/completed. Current source_status may be source_unavailable while stored semantic status stays active. Permissive payload/history decoding currently hides corruption | Existing routes sufficient plus guards and joined source lookup. Revisions/provenance preserved; no forgetting, disk reclamation or proof of causal knowledge. |
| B7 | P: `self_model_current`; `/self-model`, no query | One singleton; <=4 SELECTs, 100000 VM steps, 32769-byte sentinel, 32768-byte stored snapshot, <=40960-byte response | `measured_at`, source-specific timestamps, projected read_at. schema<6 => legacy; empty => awaiting_first_cycle; invalid => error/invalid_snapshot; missing DB503; future/ambiguous schema409. Retained schema6 snapshot remains valid on v7 | Existing route sufficient, unchanged. Render envelopes/status/reason/source TTL exactly. Snapshot describes recorded capabilities/limits; no personality or consciousness. |
| B8 | P: `decision_records` plus linked transition prediction/pre-state; `/decisions`, `/{transition_id}` | Inclusive descending before positive MAX_ID; default20/max50. Next cursor = **first unreturned ID**, not last-minus1. Unknown/repeated query rejected | selected_at/created_at; never current motivation. schema<7 legacy; no home explicit missing_home; invalid slot available false/error/invalid_decision; detail missing404; missing table error; busy/budget503 | Existing routes **unchanged**. Frozen evidence/digest only; no scorer call, utility recalculation, reranking or “reasoning” interpretation. |

Current older route inventory (all paths below begin `/api`):

| Route | Source/type and current bounds | Astra disposition |
| --- | --- | --- |
| `/status` | R runtime + P meta/counts and process/lock checks; cached2s, counts10s; heartbeat fresh only with matching lock/session and age0..10s | Existing observer shell/Overview only; not a B9 source. |
| `/environment` | P meta.last_state; reported age, no sensing | Existing Environment; do not use clamped age to override evidence clocks. |
| `/history?limit=200` | P latest experience/wake/sleep episodes; 2..500, displayed in ascending chronology; cache30s; JSON not byte-bounded | Existing charts only; no B9 trend/effect inference. |
| `/memories`, `/{episode_id}` | P episodes/annotations; parameterized search/event, newest/oldest/reward sort; offset/count scans; per-row annotation reads | Preserve old list; bounded exact detail link is specified in section 8. |
| `/concepts` | P legacy concepts/concept_evidence; all concepts, per-concept source lookup; confidence and rolling-window evidence | Preserve legacy Concepts, do not merge with B6 Semantic Memory or use as B9 landing source. |
| `/learning` | P all Q/visit rows, retained experience distribution, latest50 reward rows; R runtime.last_decision/epsilon/alpha | Preserve Learning; fix its explanation (section 11). No new model formulas. |
| `/development` | P retained episode GROUP BY counts, distinct Q contexts, summed visits, concept count, latest20 wake/sleep notes; **five SELECTs, lifetime scans presently unbounded** | Optional explicit landing-card load; apply bounded work guard, retain exact counts or return unavailable; not B10. |
| `/storage` | Filesystem inventory, settings budget, disk usage; cache5s, unbounded directory traversal | No Astra automatic request; do not confuse with B7 bounded logical storage snapshot. |
| `/health` | `/status`, last20 errors plus count, process freshness | Existing Overview only. |
| `/events` | P retained events; after exclusive0..MAX_ID, limit100/max100; gap/reset and latest ID | Existing Activity only. No new SSE topics. |
| `/stream` | Same event source; SSE Last-Event-ID, eight slots, 100 rows/tick, 2s polling | Existing Activity only; navigation must close it. |

`/settings`, `/commands`, `/summary`, owner notes/annotations and automation placeholder are existing operator-adjacent surfaces, not new B9 navigation implementations. Their presence is recorded, not interpreted as completion of Operator Edition 0.2.

## 6. Development landing: separately sourced cards

Show the notice **“A mosaic of separately recorded evidence. Cards do not describe one atomic current state.”** No “overall freshness,” maturity, development score, improvement arrows or success/failure thresholds.

The cold initial page makes **at most seven same-origin GETs total**: one bootstrap followed by these six fixed bounded reads in parallel using all-settled handling. Warm navigation/Refresh makes six. No per-card detail requests are automatic.

| Card | Initial request | Visible evidence/provenance and destination |
| --- | --- | --- |
| Latest transition / prediction / evaluation | `/api/predictions?limit=1` | Latest transition ID/completed_at, action and presence-only badges; “Contents checked on opening.” Do not display a score from list presence flags. Link to exact Predictions detail. A corrupt latest slot remains visible; do not hunt for a nicer record. |
| World Model | `/api/world-beliefs?limit=20` | Number of returned slots/valid/corrupt records and next-page availability, labelled **“this page”**, not global count. Per-row updated_at range only for valid timestamps, never a model freshness clock. Link to World Model. |
| Recent Curiosity | `/api/curiosity?limit=1` | Latest assessment ID/created_at, stored status/level/score and reflection state. Link to exact assessment. No summary lifetime claim. |
| Latest consolidation | `/api/consolidation-runs?limit=1` | Run ID, started/completed_at, provenance/status/audit reason. Link to Semantic Memory Runs. Missing run is not proof semantic memories do not exist. |
| Stored Self Model | `/api/self-model` | Snapshot measured_at/source transition, availability and distinct per-source freshness. Memory count relations exact/at_least and semantic-memory availability may be shown **as this B7 snapshot's description**, not current counts. Link to Self Model. |
| Latest stored decision | `/api/decisions?limit=1` | Transition/decision IDs, selected_at/created_at, selected action, mode/basis or corrupt state. Link to exact Decisions detail. |

A seventh visual card, **Legacy retained development counts**, starts **Not loaded** with an explicit “Load retained counts” button and no values/time. That button makes one `/api/development` read after the initial batch, protected by section 8. Label observations/owner interactions/wake/sleep counts/contexts/updates/concepts as retained records; show scope text and latest20 lifecycle rows. On budget failure show “Service unavailable: count query exceeded its read budget,” no partial/estimated counts. Manual Refresh reloads this card only if the owner already loaded it, making at most seven data GETs with cached bootstrap. It is never loaded concurrently with cold bootstrap. This deliberate lazy card keeps both truthfulness and the total initial request cap.

Each card owns request state, dashboard read time and model/record time. One 404/503/corrupt result does not hide other cards. Retained prior card contents during same-view Refresh are labelled “Last read <time>; refresh pending/failed”; do not relabel them as fresh.

## 7. New prediction-history read contract

### 7.1 Service, routes and input

Future `dashboard/services/predictions.py` defines `PredictionReadService(ReadStore)` by composition, like DecisionReadService (`__init__(store)`). `SeedService.predictions(before=None, limit=20)` and `.prediction(transition_id)` delegate. Add only:

```text
GET /api/predictions?before=<inclusive transition id>&limit=<n>
GET /api/predictions/{transition_id}
```

`MAX_ID = 9223372036854775807`. IDs/cursors are positive integers 1..MAX_ID; limit is1..50, default20. Omitted before uses MAX_ID. HTTP digit strings must be ASCII, length1..19, canonical decimal `[1-9][0-9]*`; reject zero, sign, whitespace, leading zero, decimal/exponent, Unicode digits and overflows. Reject unknown/repeated query keys; detail accepts no query. Direct service calls require `type(value) is int` (not Boolean, float or string); None is permitted only for omitted list cursor. All such input errors: HTTP422, `error.code=invalid_query`, fixed message without echoing untrusted input. Path validation occurs before integer conversion.

Read only; never `Predictor`, `predict_candidates`, `evaluate_prediction`, `Memory`, sensors, process controller or organism construction. Never repair old records or persist a “viewed” marker. Model identifiers come from stored JSON, never an inference run.

### 7.2 Schema, reads, pagination and metadata

Use one short-lived `ReadStore.connection()` in URI mode=ro, `PRAGMA busy_timeout=0`, one read transaction and a progress callback every1000 SQLite VM operations that interrupts at **300000** operations. Always uninstall the callback and rollback the read transaction in finally. No retries, writes or migration PRAGMAs. Schema discovery selects only `seed_schema`, `transitions`, `episodes` with LIMIT3. Version read uses LIMIT2; no generic table-name input.

- No database/home: HTTP200 `available=false,status=unavailable,reason=missing_home`; do not create files.
- Unversioned DB or valid version1: HTTP200 unavailable/legacy_schema for list and detail; B1 begins at schema2.
- Valid version2..7: predictions/evaluations may individually be absent. An empty v7 list is `available=true,status=stored,items=[]`.
- Unsupported/future/ambiguous/noninteger version: HTTP409 `incompatible_schema`.
- Version2..7 missing transitions/episodes: HTTP200 `available=false,status=error,reason=missing_transition_table` or `missing_episode_table`; never call this legacy.
- Valid schema, absent detail ID: HTTP404 `prediction_not_found`.
- Busy/VM interruption/damaged or incompatible SQL layout: HTTP503 `prediction_read_unavailable`. Response-size failure is503 `invalid_prediction_response`; no partial HTTP body.

List performs **at most four SELECTs**: schema, version, at most limit+1 transition IDs by `id <= before ORDER BY id DESC`, then one bounded metadata query for the first limit IDs with an episode PK LEFT JOIN. The **first unreturned ID** is next_cursor, mirroring B8. No OFFSET, COUNT, filter-by-validity, JSON decoding or JSON transfer to list. Corrupt metadata and absent/malformed prediction payloads consume their raw ID slot; no refill. An orphan episode makes invalid linkage, not disappearance. The ID lookahead is at most51 integers; only50 rows of metadata transfer.

SQL projects scalar type/enum checks before transfer: positive signed64 IDs; finite numeric started/completed/reward checked in Python after SQLite numeric type gating; action is one of observe/reflect/consolidate/rest or a fixed invalid marker. SQL `IS NOT NULL` provides the two presence Booleans. No unrestricted action text, state, outcome or episode note transfer. `completed_at < started_at` or a nonfinite/negative clock makes metadata corrupt, retaining the transition ID only. Future relative-to-browser timestamps are displayed with a clock notice rather than erased. Presence means SQL content exists, **not validity**.

The standard list envelope is exactly `available,status,reason,items,next_cursor`. Each valid summary contains exactly `available=true,status=stored,reason=null,transition_id,episode_id,started_at,completed_at,action,legacy_reward,prediction_present,evaluation_present`. Invalid metadata summary is `available=false,status=error,reason=invalid_transition,transition_id`; no replacement numeric values. IDs are JSON integers on the wire and handled losslessly by section 12. Empty result has next_cursor null, not0. Missing-feature envelopes have empty items/next_cursor null.

Each encoded summary is <=**512 bytes**, total compact list response <=**27648 bytes** (50×512 +2048 envelope/list overhead). Serialize deterministically with UTF-8, `ensure_ascii=True`, compact separators, finite numbers only; check actual encoded length before responding. Default20 returns no more than20 slots, hard max50. Insertions newer than the cursor do not shift older pages. Deletion of a cursor ID is harmless because comparison is inclusive; deletes can yield an empty final page. No search beyond the requested page. Refresh starts from newest; user navigation never silently mixes pages.

### 7.3 Detail, strict payload decoding and response limits

Detail uses **at most three SELECTs**: schema, version and one requested transition with episode PK LEFT JOIN. Select metadata and exactly two JSON BLOB sentinels:

```sql
substr(CAST(t.prediction_json AS BLOB),1,16385)
substr(CAST(t.prediction_error_json AS BLOB),1,16385)
```

Also project each original SQLite type and SQL NULL flag. Do not SELECT state_before_json, state_after_json, outcome_json or an episode payload. At most **32770 source JSON bytes** cross SQLite/Python per detail (2×16385); numeric/enum linkage metadata is separately bounded to1024 encoded bytes. JSON TEXT only, not arbitrary BLOB values. Each present payload must have both source UTF-8 and reserialized canonical JSON size <=**16384 bytes**; the16385th byte signals oversize. Reject invalid UTF-8, duplicate keys, NaN/Infinity/overflowed floats, trailing garbage, nonobject root, unpaired Unicode surrogates, depth>8, >512 total object members/array items, array length>64, keys>128 UTF-8 bytes or string values>256 UTF-8 bytes. Bounds are applied before recursion/rendering. No truncation presented as complete evidence.

Detail envelope contains `available,status,reason,transition_id,transition,prediction,evaluation`. `transition` is valid linkage metadata (episode_id, started_at, completed_at, action, legacy_reward) or null for invalid metadata. Each payload wrapper is exactly `{status,reason,data}`:

| Input | Wrapper |
| --- | --- |
| SQL NULL | `absent / not_recorded / null` |
| Valid supported model | `stored / null / <stored object>` |
| Bounded object with well-typed recognized header fields but unsupported model/version/horizon | `unsupported / unsupported_model / null` |
| Malformed/oversized/type/shape-invalid supported content | `corrupt / invalid_prediction` or `invalid_evaluation` `/ null` |

For missing-home/legacy/detail error envelopes `transition,prediction,evaluation` are null; for a valid transition with SQL NULL sources, both wrappers are present and absent. A malformed transition returns available=false/error/invalid_transition and null payloads; a valid transition stays available=true/stored even if one payload wrapper is corrupt, so a valid sibling is not erased. Valid evaluation alongside missing/invalid prediction can be displayed as **stored evaluation; original prediction unavailable**. No reconstruction or substituted actual sensor values.

Supported B2 header is model `transition_delta_v1`, integer model_version1, horizon `next_post_action_observation`, action equal to transition action, exact four target keys. Supported B3 header is evaluator `prediction_error_v1`, integer evaluator_version1, exact four signal keys and aggregate. A supported B3 record may legitimately have null prediction_model/version/horizon when the original prediction was invalid; display that limitation. If a valid B2 and nonnull B3 prediction header disagree, mark evaluation corrupt with invalid_evaluation; do not rescore.

Shape validation is read validation, **not producer/evaluator math**:

- Prediction signal: status predicted or unavailable. Predicted has value of the producer's target type, method, nonnegative evidence_count<=200, finite confidence0..0.95 and confidence_kind=evidence_support. Numeric values are nonnegative (percentage targets<=100), network value Boolean, probability_true if present0..1. Numeric clamped is Boolean. Method is persistence, action/global_mean_delta for numeric, persistence or action/global_boolean_frequency for Boolean. Unavailable has recorded reason, count/confidence/support fields and no invented value. Reject unknown signal fields for supported v1.
- Evaluation signal: not_evaluated with recorded reason, or evaluated with predicted/actual of the target type, normalized_error0..1 and the stored scoring_method. Numeric evaluated fields include signed_error, absolute_error (finite, nonnegative absolute) and percentage_range/bounded_relative. Boolean evaluated fields include correct Boolean, classification_error0/1 and boolean_mismatch/boolean_brier; Brier form also has probability_true and brier_error0..1. Reject unknown fields for supported v1.
- Aggregate: status evaluated/unavailable, evaluated_signals integer0..4, target_signals exactly4, coverage0..1, mean_normalized_error and accuracy_score each null or finite0..1; unavailable aggregate requires both scores null. Require supported types/keys, but **do not compute** errors, coverage, confidence or `1-error` to replace/check scores. Stored values remain evidence even when UI would have calculated something different.
- Exact known top-level sets follow the stored dataclasses: B2 `{action,signals,model,model_version,horizon}`; B3 `{signals,aggregate,prediction_model,prediction_model_version,horizon,evaluator,evaluator_version}`. Expose no arbitrary nested extensions from a supported v1 record. Unknown header model/version is unsupported rather than a fake v1.

Detail response cap is **35840 bytes** = 2×16384 accepted canonical payloads +3072 maximum metadata/wrapper overhead. The overhead is a checked ceiling, not permission to add fields. Validate source/canonical payload bounds independently; final serialization enforces35840. Metadata/wrapper failure yields503, not an inferred reduced record. List cap27648 and detail cap35840 include all JSON framing bytes, exclude HTTP headers and do not depend on compression. Service errors are fixed bounded messages, <=1024 response bytes.

### 7.4 Predictions presentation

List columns: transition, episode, completed time, action, legacy reward, prediction presence, evaluation presence, Inspect. Label list badges **Present (not yet inspected)** or **Absent**; list cannot claim JSON is valid. No row-level detail requests until selection. One selected detail at a time; direct detail hash performs one detail GET without loading a list.

Detail shows transition metadata and separate Prediction/Evaluation availability. Four signal rows show predicted value/unit, method, evidence_count, **evidence support**, stored actual, status and recorded errors/scoring method. Numeric signed/absolute error is shown when present; Boolean classification/Brier data is shown with its recorded method. Show model/version/horizon, aggregate coverage, evaluated/target counts, mean normalized error and **“Stored B3 accuracy_score — this transition only.”** Explain “Evidence support is not a calibrated probability of correctness.” Network frequency probability has its own label. No rolling accuracy chart. Full accepted objects are in explicit details, not automatically announced. Presence of real0/false is respected; missing/unavailable is text, never coerced to0.

## 8. Proven existing-read gaps and narrow future safeguards

“Existing routes sufficient” means sufficient **model semantics**, not a claim that every old reader already meets B9's byte/work/error contract. Source evidence: `SeedService._world_belief/_curiosity` use permissive `decode(...,{})`; list queries SELECT full JSON. `SemanticReadService.current` performs a source SELECT per row. `SeedService.development` scans retained tables. A LIMIT alone bounds result rows, not filter work, JSON size or count scans. These are concrete blockers to claiming bounded observation. Resolve them in dashboard read adapters only; no schema/core change or additional public route is needed.

A small future `dashboard/services/evidence_reads.py` owns scoped read-budget cleanup, strict byte/structure decoding and compact response-length checks for the new/extended readers. It must not change generic `ReadStore.decode` globally, affect operator writes, install a persistent callback, or wrap B7/B8 in a second competing budget. Reuse known pure stored-data validators where appropriate; no predictor, evaluator, consolidator, world-model learner or self-model producer invocation. Existing `normalized_source` may still validate a joined source belief, but discard its normalized data/fingerprint return: it only determines the existing source_status, never replaces the stored semantic payload. The new prediction service's model-specific shape rules remain in `predictions.py`.

### 8.1 Model route guard contract

For B4/B5/B6, preserve route names, filter allowlists, default50/max100 and current cursor arithmetic. Use read-only BEGIN, busy_timeout0, <=300000 VM steps (1000-step callback), finally cleanup and no refill. Probe only required named tables plus `seed_schema`; read version with LIMIT2. Versions below the model's introduction (B4=3, B5=4, B6=5) retain **exact legacy list envelopes** `{available:false,items:[],next_cursor:null}` and legacy detail404. A claimed supporting version with a missing required feature table reports `available:false,status:error,reason:missing_feature_table`; future/ambiguous versions409. Missing DB/busy/VM errors remain503 with fixed code `evidence_read_unavailable`; byte-cap failure503 `invalid_evidence_response`. Do not translate whole-database outage into an empty collection.

Lists first fetch bounded IDs with existing filters/lookahead, then at most one bounded payload query for returned IDs. Semantic current payload query LEFT JOINs its source belief by PK, avoiding per-row SELECTs while preserving source_status validation. This is **at most four SELECTs** including schema/version for normal model lists, **three** for detail. Semantic history allows **four** (schema, version, parent existence, bounded history query with lookahead); runs fit four. B5 summary is **three** (schema, version, latest100 payload/scalar rows); it does not query beyond its raw window. Model filter scans are interrupted at the VM budget, not allowed to grow indefinitely while searching for matches.

| Read contract | SQL JSON sentinel / source limit | Maximum encoded item (metadata included) | Whole compact response ceiling |
| --- | --- | --- | --- |
| World belief current/detail | value JSON16385 /16384 bytes |18432 bytes| list **1847296** =100×18432+4096; detail **20480** |
| Curiosity current/detail | components JSON16385 /16384 |18432| list **1847296**; detail **20480** |
| Semantic current/detail | payload16385 /16384; joined source belief value16385 /16384, never exposed as an extra full belief |18432| list **1847296**; detail **20480** |
| Semantic history | stored record JSON32769 /32768; decoded nested payload also <=16384 |34816| list **3485696** =100×34816+4096 |
| Consolidation runs | result JSON16385 /16384 |18432| list **1847296** |
| Curiosity summary | <=100 raw rows; each components sentinel<=16385 | Not a list | **16384** |
| Existing B7 self-model | unchanged32769 /32768 | Existing singleton | unchanged **40960** |
| Existing B8 decisions | unchanged3×16385 per slot | unchanged summary1024 | unchanged list **53248**, detail **17408** |

For B4/B5/B6 scalar text, SQL BLOB sentinels are129 bytes for model/signal/scope/status/key-like fields and257 for free-text reason fields; accepted UTF-8 limits128/256. Enum fields use SQL CASE fixed invalid markers where possible. Type-gate numeric scalars before transfer; reject nonfinite values, nonpositive source IDs, Boolean-as-number and malformed versions. New helper enforces JSON duplicate/finite/depth8/512-member/string256/key128/array100 limits; canonical encoded JSON must also meet the relevant source cap. No arbitrary-length strings are fetched first and truncated later. History records have the existing nested model shape, not a new shape invented by the UI. The sole string-size exception is the history snapshot’s `payload_json` field: permit up to16384 UTF-8 bytes, then strictly decode that inner JSON with the normal payload limits and replace it with the existing `payload` projection. The outer record remains bounded to32768 source/canonical bytes; inner and outer decoding each obey depth8/member512 limits. Other history strings remain limited to256 bytes. This exception preserves valid B6 serialization rather than rejecting an ordinary nested payload as corrupt.

Validate required stored field/type/domain structure: B4 signal/scope/type/model_version1, counts>=0 with contradiction_count<=evidence_count and confidence0..0.95; B5 known curiosity_v1/version1, evaluated/unavailable status, named levels, optional finite0..1 scalars, Boolean reflection flags and completed<=claimed, bounded reasons/components; B6 semantic_v1/version1, known signal/scope, positive revision, active/weakened/source_unavailable status, valid linkage IDs/counts/confidence and typed descriptive payload; history preserves recorded revision/recorded_at and full previous semantic shape; runs preserve known provenance/status, nonnegative counts, typed result audit. Use producer constants for enum allowlists, not new scoring thresholds. Validation may check structural/domain invariants; it must not recompute confidence, salience, means, fingerprints as an inferred replacement, utility or eligibility.

A damaged row consumes its existing page slot and returns only its reliable PK (plus semantic ID/revision for history), `read_status:'corrupt'`, `read_reason:'invalid_stored_evidence'`, and its payload field (`value`, `components`, `payload`, `record` or `result`) as null. Valid existing row shapes remain unchanged. Detail of a present corrupt row is200 with the same marker, not404. Do not send unchecked metadata alongside a corrupt badge. A semantic memory whose **source** is missing/corrupt still returns its valid stored semantic record and `source_status:'source_unavailable'`, distinct from corruption of the semantic record itself.

Curiosity summary preserves its existing bounded summary formulas and per-field evaluated finite-value denominators. `assessment_count` remains raw selected rows <=100; add `valid_assessment_count` and `corrupt_assessment_count`. Corrupt rows contribute no level/reason/mean/reflection values but **consume** the100-row window. Existing stored unavailable assessments remain valid rows and contribute existing availability/suppression counts; mean_score remains null if no evaluated score exists. Reason dictionaries include only validated bounded reason strings. Whole-summary byte cap is checked; do not silently drop dictionary entries or substitute0. This is bounded descriptive aggregation that already exists, not a new longitudinal evaluator.

### 8.2 Optional retained counts and direct episode link

`/api/development` retains its exact-count meaning and existing output keys. Apply a <=300000 VM-operation, zero-busy-timeout scoped read transaction and at most **six SELECTs**: one named-table check and the existing five data SELECTs. Count scans either finish within budget or fail503 `development_read_unavailable`; do not sample, estimate, or page through history to complete them. Project latest20 timeline scalar fields and note as4097-byte SQL sentinel; valid note<=4096 UTF-8 bytes. Invalid note is null with a per-entry `read_status:'corrupt'` marker; a source ts must be finite and nonnegative. Whole response ceiling **98304 bytes**. A count0 from a successful complete query is valid; unavailable counts are never0. **Compatibility rule:** hardening `/api/development` must not turn a retained-count failure into an Overview-wide failure. The current `dashboard/static/views/overview.js` awaits status, storage, development and health in one `Promise.all`; the future B9 renderer must settle development independently. This is a frontend compatibility adjustment, not a new model, API or process semantic. Do not weaken the backend work budget to keep Overview working.

The future Overview fetch contract is precise:

- `/api/status`, `/api/storage` and `/api/health` remain required for their existing Overview evidence. Preserve the current Overview error behavior when any of these required requests fails; this amendment does not generalize partial rendering for them.
- `/api/development` is independently settled as either successful data or an explicit unavailable result. A local catch or carefully typed `Promise.allSettled` equivalent is permitted; no success-shaped fallback object. A development failure alone never rejects the Overview render or discards successful required-source results. Navigation abort still cancels the render and cannot install a stale result.
- On `503 development_read_unavailable`, identity, current activity, battery/compute resources, Memory & storage, and System health still render from successful status/storage/health responses. Their own freshness and failure labels remain governed by those sources, not by the failed count request. The status-sourced Learned concepts metric remains visible.
- Recorded experiences (`dev.observations`) and every other development-only metric show **Unavailable**, never0 or a value taken from another source. The **Development, measured** card shows **“Retained development counts unavailable: bounded count read could not complete.”** Known contexts, Learning updates, Wake records and Owner interactions show Unavailable. Do not fabricate a scope, zero-filled counts, or an empty lifecycle timeline that looks like a successful result; say **“Lifecycle record unavailable.”** A prior successful development result must not appear as a current successful result after failure.
- Other development-request failures also settle as development unavailable with an appropriate source-specific notice, without falsely labelling every failure budget exhaustion. Required-source failures retain their existing behavior. Successful `/api/development` output, exact-count interpretation and genuine zeros remain unchanged.
- Keep the existing four source requests per Overview render and its refresh policy. Do not add an immediate retry, a refill scan, or another endpoint to reconstruct missing counts. The normal scheduled Overview refresh may attempt one new bounded read on its next eligible render; it is not a retry loop within the failed render.

These rules isolate the newly bounded source only. They do not change the existing status/process checks, storage semantics, health semantics or the Astra landing request budget.

Extend existing `#memory` only with direct `#memory?episode=<id>` mode, using the already-existing `/api/memories/{id}`. The normal Memory list/filter behavior remains unchanged. The exact-detail adapter uses <=3 SELECTs (row, named-table check, optional annotation), scoped <=300000 VM steps, mode=ro, zero busy timeout. State JSON uses16385 sentinel/16384 source and canonical cap; note4097/4096; event/action use fixed enum or129-byte scalar sentinel; annotation tags JSON4097/4096, at most10 strings of32 characters. Whole detail response <=**32768 bytes**. Preserve the existing warning/state convention for malformed state, add read_status/read_reason for affected content, never show its replacement `{}` as a real empty observation. Oversized untrusted content is explicitly unavailable, never silently truncated. Missing ID404; budget/busy503 `memory_read_unavailable`. No writes or annotations from this page.

These are the only old-route hardening targets. No general repair of old Learning/Concepts/Memory-list queries, storage walks, operator services or all application endpoints is folded into B9. Astra does not call those unbounded legacy operations in the background. Their pre-existing limitations remain documented; broader changes need separate scope.

### 8.3 Page-to-route gap disposition

| Astra page | Existing route(s) | Missing read contract | New backend needed? | Why |
| --- | --- | --- | --- | --- |
| Development | world-beliefs, curiosity, consolidation-runs, self-model, decisions, optional development | Latest transition summary; bounded optional counts; older-model guards | Prediction projection + narrow safeguards only | No new atomic cognition summary or new model. |
| Predictions | No dedicated B1/B2/B3 route | Section7 | **Yes**, new PredictionReadService and two read endpoints | Memory episodes do not expose linked stored forecast/evaluation history. |
| World Model | world-beliefs list/detail | Strict bytes/corruption/work guard | Existing route safeguard, no new route | Fields/filter semantics already sufficient. |
| Curiosity | list/summary/detail | Strict bytes/corruption/work guard and honest corrupt-window accounting | Existing route safeguard | Existing bounded window means retained. |
| Semantic Memory | current/detail/history/runs | Strict bytes/corruption/work guard; batch source join | Existing route safeguard | Existing model/provenance/revisions sufficient. |
| Self Model | self-model | None | No | Existing bounded stored projection is authoritative. |
| Decisions | decisions list/detail | None | No | Existing exact B8 contract is preserved. |

## 9. Detailed development views

### World Model

Initial read is `/world-beliefs?limit=20`. Filter controls: signal (four B4 targets), scope (global/action), scope_value (empty global or four actions). Preserve backend acceptance rules; if changing scope to global, clear an action value, and display the current chosen filter. Keyset cursor is **exclusive ascending after**, not newest-first. A first-page count is labelled records on this page, never total model size. Detail may reuse a fully returned valid row; direct belief link does one detail GET, not a list scan.

Table/detail shows signal, scope, scope_value, belief_type, typed value payload, evidence_count, contradiction_count, confidence with evidence_consistency label, created_at, updated_at, model_version and both source transition endpoints. Always show **“Descriptive statistics from observed transitions, not causal claims.”** An action condition is “Observed under action: rest,” never “rest improves battery.” Source endpoints are links to those exact transitions, not an implication that every ID in between contributed. No freshness TTL or causal arrow is invented.

### Curiosity

Heading **Curiosity**, subtitle **“Prediction-error salience, surprise and uncertainty.”** Initial list plus summary is exactly two GETs. Summary visibly states **latest <=100 retained assessments**, actual raw/valid/corrupt counts and evaluated-value denominators; do not label its means lifetime averages. Details opened from a valid list row reuse the returned payload; direct transition link loads one detail GET, without summary.

Display model/version, transition ID, created_at; status/score/level, prediction_surprise, uncertainty, novelty, coverage; reflection_eligible/claimed/completed independently; claimed_at/completed_at; suppression_reason/failure_reason and components. No synthetic combined “reflection succeeded” if only claim is stored. Say “surprise component” or “reflection suppressed: low_disk,” not “felt surprised,” “wanted to explore” or “bored.” Unknown/absent is distinct from false; Boolean fields get accessible Yes/No/Unavailable text. A null score from unavailable assessment is unavailable, not0.

### Semantic Memory and Consolidation

One page with mutually exclusive Memories / Consolidation Runs tabs; only active tab fetches. Memories list default20, ascending after, filters signal/scope/status as current API (no invented scope_value filter). Show semantic_key, signal/scope/value, semantic_type, status, revision, confidence, evidence_count, contradiction_count, source_belief_id and source_status, source belief model/version/updated_at, source first/last transitions, created/updated_at and payload. Existing legacy Concepts remain elsewhere.

Select a memory to inspect its already-returned detail and an explicit **Load revision history** button. A direct semantic link fetches one detail; history is a second on-demand GET, default20, inclusive revision before, descending. History preserves recorded_at and prior revisions/status/payload. Current revision is labelled current; do not insert a fake duplicate into historical rows or imply older revisions were deleted. On a repeated publication, unchanged stored timestamps remain unchanged.

Runs tab reads `/consolidation-runs?limit=20`. Show run ID, provenance, status, started/completed, source_beliefs_examined (“Examined”), eligible_beliefs (“Eligible”), created_count, revised_count, weakened_count, unchanged_count, failed_count and recorded result/audit reason. There is no run-detail endpoint: full bounded result from that page row supplies details. A source run ID outside the visible page is shown as text with a link to the Runs page; no scanning until found and no invented detail API.

Always show **“Consolidation processes bounded descriptive beliefs into revisable semantic records. It does not delete autobiographical memory and does not reclaim disk space.”** No consolidation command is added.

### Self Model

One `/self-model` GET; do not recompute in JavaScript. Render snapshot model/version, measured_at, source_transition_id, source_event_id, source_session_id and read_at. Sections map directly to stored envelopes:

| UI section | Exact snapshot source |
| --- | --- |
| Observation/sensor availability | `observations`, `capabilities.sensors`; `resources` are references to observation fields, not extra measurements |
| Action catalog/capabilities | `capabilities.actions`, `capabilities.unsupported`, `last_selected_action` |
| Prediction performance snapshot | `prediction_performance.window`, `.coverage`, `.score`, each source envelope/window/sample count |
| Memory/storage health | `memory.storage`, logical allocation, each count and relation exact/at_least |
| Consolidation status | `memory.latest_consolidation` and linked source run metadata |
| Runtime/session evidence | `memory.runtime_reported` and recorded source session; not a process probe |
| Recent failures/limitations | `recent_failures` and each unavailable/not_supported/error reason |

For every field, show its provided status/reason and source table/IDs/source_observed_at/timestamp_kind/ttl_seconds. Preserve schema6 snapshots retained on source schema7; label snapshot-reported schema distinctly from source-supported schema. B7 projection already handles observation/transition/storage/error60s, runtime10s, and prediction/consolidation300s policies and clock regression; do not refresh, merge, override, average or relabel those statuses in the browser. A stale stored value remains visible with its stale label. Mean prediction score here is B7's already-persisted bounded snapshot, not a B9 trend or a new B10 result. Catalog selectable flags describe a fixed supported action catalog, not B8 eligibility in a particular cycle. No personality, emotion, self-esteem, consciousness or invented competence score.

### Decisions

Use B8 routes **exactly**, including before semantics, response bounds and reason/status names. Initial list20, no row detail fetch. List displays selected_action, selection_mode, policy_basis, selected q_value, decision_utility, eligible_actions, constraint_reasons, fallback_reason, transition_id, decision_id, selected_at and created_at. Corrupt slots show transition ID and invalid_decision notice, never a reconstructed summary. No episode ID is fabricated from a decision; View transition goes to Predictions detail, which can then link the real episode.

Detail makes one on-demand GET and shows raw record model/version/weights_version, selected action, frozen selection_candidates, eligible_actions, constraints, fallback, history status/cutoff/raw_rows, epsilon/alpha/random_draw/choice_index, compact current resource projection, prediction contract and selected_prediction_sha256. Four candidate rows in fixed observe/reflect/consolidate/rest order show eligible, reasons, raw q_value, visits, q_missing, components.q_component, components.forecast_resource_risk, components.model_uncertainty, decision_utility, and the three resource_forecasts with status/value/method/evidence_count/confidence/source IDs/times/invalid_source_count. Do not sort by utility or recalculate the eligible maximum set.

Permitted copy is directly conditional on fields: composite+exploit => **“<action> was selected during composite exploitation from the stored selection_candidates set.”** legacy_q+fallback => **“<action> was selected by raw-Q fallback from the stored candidate set.”** explore => **“<action> was selected during exploration among the stored eligible actions.”** Use the exact recorded set as additional text; do not infer motive, goal, intent, thought or reasoning. Show raw scores rather than comparing them to present-day Q. The prediction digest is an opaque provenance identifier; no client digest regeneration, prediction reconstruction, rescoring or hidden fetch is required.

## 10. Cross-view identity, time and state vocabulary

### Correlation links

Links request only known IDs on explicit navigation; none checks target existence in the background. Detail404 says no retained record for that ID and preserves the originating link context. Source IDs are provenance endpoints, not evidence that every model existed for the transition.

| Source | Supported link |
| --- | --- |
| Transition/prediction detail | `episode_id` -> `#memory?episode=...`; transition_id -> `#decisions?transition=...` / `#curiosity?transition=...`, labelled “Check stored decision/assessment” because older transitions may lack them |
| Curiosity or Decision | transition_id -> `#predictions?transition=...` (“View transition evidence”) |
| World belief | source_first_transition_id / source_last_transition_id -> exact Predictions details; do not expand the inclusive range |
| Semantic memory/history | source_belief_id -> `#world-model?belief=...`; source transition endpoints -> Predictions; memory ID -> `#semantic-memory?semantic=...` |
| Self Model | source_transition_id and valid per-source transition IDs -> Predictions; source belief ID only if actually present; run ID displayed with Runs-page link as described above |
| Decision ID | Display/copy exact 32-hex value; public detail endpoint remains keyed by transition_id, **not** decision_id |

Hash IDs are canonical decimal strings checked by BigInt against signed64 bounds; never `parseInt` a cursor into a floating-point Number. Invalid/missing IDs are unlinked “Unavailable,” not0 or generated sequence numbers. Do not add a graph database, all-model join, automatic source-range expansion or provenance guessed from chronological proximity.

### Vocabulary and accessibility of state

| Label | Meaning and mapping |
| --- | --- |
| Stored | Valid persisted record, not a fresh sensor reading. Record timestamps accompany it. |
| Live | Only the existing verified runtime/SSE surface; never ordinary B9 GET success. |
| Last recorded / Last read | Distinguish producer evidence time from dashboard fetch time; retained old card on failed refresh gets Last read. |
| Not loaded | Optional request not made, e.g. retained counts/history. No values are guessed. |
| Awaiting first record | Supported, readable empty collection/singleton; for filtered empty pages say “No matching records on this page,” not first-ever absence. |
| Legacy schema | API positively identifies a schema lacking that model; never infer from a service outage. |
| Unavailable | Valid record has no value, unsupported model, absent historical prediction/evaluation, or known missing source; display specific reason. |
| Stale | Producer/read-adapter explicitly projects source_expired/snapshot_expired; no generic UI cutoff. |
| Suppressed | Recorded guard outcome, not corruption or a failed test. Reason shown. |
| Corrupt | Explicit invalid_decision/invalid_snapshot/invalid_transition, payload corrupt wrapper or read_status corrupt. Untrusted fields withheld; slot remains. |
| Service unavailable | 503, client deadline, transport or oversized response; Retry button; never an empty collection. |
| Incompatible schema | 409; explain supported source schema range; no offer to migrate in observer UI. |

Status and reason are visible text plus optional existing badge color/icon. Invalid timestamp is a separate **“Timestamp unavailable”** notice, not evidence a model is stale. No absent/null becomes0, false, an empty valid object or success. Genuine stored0/false is displayed. Badges have matching accessible names; use role=status only for short loading/completion/error messages, not entire record trees.

### Clocks

| Evidence | Displayed clock |
| --- | --- |
| Episode | `ts` labelled Episode recorded |
| Transition / B2 / B3 | started_at / completed_at labelled Transition started/completed; B2/B3 have no separate timestamp; do not label completed_at as prediction-generation time |
| World belief | created_at / updated_at, plus source transition IDs; no TTL |
| Curiosity | created_at, claimed_at, completed_at with separate labels |
| Semantic memory / history | created_at / updated_at; source_belief_updated_at; prior revision recorded_at |
| Consolidation | started_at / completed_at; null completion is “No completion recorded” |
| Self Model | measured_at, projected read_at and each source's own time/kind/TTL |
| Decision | selected_at / created_at; transition completion is available only on explicit transition navigation |
| Runtime / browser | Existing heartbeat is runtime evidence; browser “Read at” is only this fetch, never model update time |

Show local date/time with timezone and an accessible/copyable UTC representation plus raw epoch in details. Accept only finite nonnegative numeric epochs representable by browser Date. Invalid/out-of-range -> Timestamp unavailable, preserve bounded raw value text for inspection. If future relative to dashboard clock, show the absolute timestamp and “Ahead of dashboard clock”; no clamping to “just now.” If an interval is negative, display “Clock order inconsistent,” not a duration; keep records ordered by their API keyset, not sorted by dates. Producer-projected B7 clock_regression remains authoritative. Do not synthesize one global last-updated timestamp across cards.

## 11. Preserve Concepts, Learning and their distinct meanings

**Concepts** stays the legacy/rolling `concepts` + `concept_evidence` view. Add the future subtitle “Legacy concepts from reflection windows; B6 records are in Semantic Memory.” Do not move old rows into semantic tables, combine confidence values, or imply a revision/history that the legacy source lacks. Semantic Memory is its own B6 view with source beliefs and revision history.

**Learning** remains contextual Q values/visits, effective epsilon/alpha, reward history and retained action distribution. **Decisions** shows frozen B8 selection evidence. Change only future Learning presentation, not learner values or algorithms:

- Navigation description becomes **“Contextual action values and recorded reward updates.”**
- Rename “Why this action?” card to **“Last recorded selection adapter.”**
- Replace the unconditional “from the highest learned values” sentence with **“<action> is the last selection recorded by the runtime adapter. This adapter exposes Q values and the captured exploration flag; it does not identify whether B8 composite utility or raw-Q fallback determined exploitation.”**
- If exploration is a recorded Boolean, display “Recorded exploration: Yes/No”; otherwise Unavailable. Display the captured candidate set as **“Recorded selection candidates”**, without recomputing ties or attributing all alternatives to highest Q. Show recorded context, values, visits, epsilon and raw adapter data only when present/well typed.
- Add **“Current Q values are not a historical decision explanation. Open Decisions for persisted B8 selection evidence.”** Link to the Decisions page without guessing a transition ID: `runtime.last_decision` is the legacy Decision adapter and contains no B8 transition_id/decision_id or policy_basis. Its presence is not proof the corresponding cycle was persisted.
- Missing adapter: **“No selection adapter was recorded. Current Q values cannot explain an earlier selection.”** Missing Q rows in the existing Learning context table must be labelled “No stored value” with unavailable visits, replacing the current fabricated `0.0000`/0 display. This does not change B8's legitimate recorded q_missing/default0 values, which are shown with their explicit provenance in Decisions.

Do not introduce a new `/learning` query, recent-decision heuristic join, score formula, historical explanation generator or behavior change. Existing recent rewards/distribution remain labelled retained records, not policy quality.

## 12. Exact identifiers, serialization and render budgets

All new development requests use a future `api.getEvidence(path, signal, maxBytes)` in `api.js`, while existing observer requests retain `api.get` unless specifically stated. It streams response bytes up to the endpoint's documented ceiling plus1, cancels on excess, decodes strict UTF-8 and preserves HTTP status/error code in a structured exception. A Content-Length is an early rejection hint, not the only enforcement. No unbounded `response.text()`/`.json()` before the byte cap. HTTP error bodies have a1024-byte allowance. Request paths are selected from the declared local route allowlist; no arbitrary URI or host input.

**Signed64 identity is not JavaScript Number identity.** The bounded JSON decoding step tokenizes JSON strings/escapes and number tokens. Outside strings only, an integer token (no fraction/exponent) whose exact BigInt lies outside Number's safe integer interval is converted to its quoted canonical decimal text before JSON.parse; safe integers and finite fractional/exponent numbers retain normal JSON numeric handling. This is a syntax operation, not a model calculation. Never use a regex across JSON string contents; validate JSON syntax with the final parser, reject malformed tokens and nonfinite decoded numbers. Response caps bound input and transformed output (each converted token adds at most two quote bytes). Reject transformed output exceeding twice the response ceiling. No eval, script generation or dependency is permitted.

Known numeric/ID fields render an exact decimal string from this operation as text; no Number coercion, subtraction, sorting or percentage calculation on it. IDs/cursors are normalized to strings before URL construction and validated with BigInt. Preformatted details are labelled **“Formatted stored fields; large integers are displayed as decimal strings”** rather than claiming to be original JSON bytes. Never recalculate IDs from row indexes. Model values outside normal chartable Number range retain their exact textual value and omit the optional graphic. Original backend schemas and B7/B8 response types remain unchanged. Manual browser acceptance includes unsafe integer tokens, escaped strings containing digits, malformed JSON and pagination at MAX_ID; planned automated service tests guarantee wire identities.

Bounded data handling is measured at several boundaries:

| View | Initial data GETs (excluding cached bootstrap) | Rows retained / detail / render ceiling |
| --- | --- | --- |
| Development | Six fixed; optional counts separate | <=25 list slots (1+20+1+1+1), one B7 snapshot, seven cards; count timeline<=20 only after load |
| Predictions | One list or one direct detail | Default20/max50 summaries, one detail, four signal rows; <=1000 DOM elements |
| World Model | One list or one direct detail | Default20/API max100; one detail; <=1500 DOM elements |
| Curiosity | Two for list+summary; one for direct detail | Default20/API max100; summary<=100 raw-window scalar aggregates; <=1500 DOM elements |
| Semantic Memory | One active tab; direct detail one; history only on demand | Default20/API max100 per current page; one memory plus one history page, no append; <=2000 DOM elements |
| Self Model | One | One <=40960-byte response; fixed sections, <=100 stored window IDs/failure entries per producing bounds; <=1500 DOM elements |
| Decisions | One list or one direct detail | Default20/max50 summaries, one detail, exactly four candidates and at most12 resource forecast cells; <=1500 DOM elements |

The landing cold budget is one bootstrap+six data=**seven** requests. All other B9 cold routes add at most one bootstrap to the per-view counts above. B9 server calls have the limits in sections7–8; B7/B8 keep their existing limits. A browser detail request is on demand and never repeated per list row. List responses replace pages; do not accumulate all history on scrolling. Maximum20 cursor descriptors and one selected detail survive within an active view; navigation releases response objects/listeners. No model data in localStorage/sessionStorage; existing theme preference alone remains stored.

For new B9 graphics, maximum100 samples, but v1 uses tables and optional four-signal/four-candidate component bars rather than time-series charts. Keep existing Environment history200/max500 and Activity500 limits unchanged; these are pre-existing observer contracts, not a B9 increase. A record's nested arrays/objects go into a single preformatted text node under explicit details, not recursively expanded into unbounded DOM. Character count remains bounded by the accepted response cap. If a response violates structural/render bounds, show an explicit invalid-response notice, not a partial page presented as complete evidence. Long IDs/digests wrap and remain copyable in full.

## 13. Security and trust contract

Retain exactly the loopback server, expected Host and Origin checks, same-origin fetch credentials, no-store responses, CSP, local assets and observer read-only SQLite access. Every B9 page works with `operator=false`. Bootstrap CSRF token existing behavior is unchanged; B9 pages make no mutations and must not call `api.mutate`. No external CDN, font, analytics, remote telemetry, arbitrary URL calls, new socket/probe, generic SQL route, arbitrary file browser, raw HTML insertion or JS model execution. Database/owner strings are rendered only through textContent/createTextNode. Create link destinations only from allowlisted routes and validated IDs, never a database-provided URL.

Existing pure model validators may inspect frozen records; they must not become producers. Prohibit `Memory`, Predictor/evaluator calls, process/LaunchAgent access and organism startup in PredictionReadService and the new model read guards. Existing observer service construction may instantiate its dormant ProcessController as it already does, but Astra paths do not call it. No listener, scheduler, command or owner-setting write is added. No install/restart/live-memory migration during B9 verification.

Missing schema/data never offers an automatic repair button. A source-v7 dashboard observing a legacy database truthfully reports legacy; it does not upgrade or mark installed schema v7. Security and the future route guards are tested against temporary homes, malicious strings and exclusive DB locks.

## 14. Accessibility, layout and visualization

Keep semantic main/headings, skip link, text labels, visible focus and native tables/details/buttons. Every table receives a caption, column header scope and a labelled focusable horizontal-scroll region when overflow exists. Filters have associated labels and apply controls; no hover-only provenance. Primary navigation, refresh, tabs, filters and Inspect controls have min44px targets; raise B9 details/tab overrides to44px rather than inheriting smaller summary styling. State color is supplementary, not sole information.

On a **user-initiated** page/detail hash navigation (including Back/Forward), after rendering the new heading focus `#page-title` with temporary/permanent tabindex=-1, without auto-opening details. Initial page load does not steal focus. Same-view manual Refresh retains focused control; paging announces a short count/page result and retains paging focus where possible. Filter error focuses its associated error/field. Abort/late responses cannot change focus. Screen readers hear concise completion/error status, not full JSON dumps. Keyboard users can expand evidence, operate tabs, copy IDs and scroll dense tables.

Seventeen navigation entries require a scrollable nav flex child (`min-height:0`, overflow-y:auto) inside the existing fixed sidebar; brand/footer remain reachable. At mobile widths the closed sidebar is both offscreen **and inert/hidden from keyboard/assistive navigation**. Menu has aria-controls/expanded; opening moves focus to current nav link, Escape closes and restores menu focus, selecting a route closes and focuses its new heading. This is a disclosure navigation panel, not a falsely labelled modal; no focus trap. The rest of the page remains usable. When switching back to desktop, clear mobile inert/expanded artifacts. Preserve the skip link without routing `#main` to Overview.

Retain CSS thresholds exactly: wide desktop **>1120px**; compact **761–1120px**; mobile **<=760px**. Thus1120px itself intentionally uses the existing compact rule (the requested >=1120 representative range shares this boundary). Test1120/1121 and760/761 explicitly. Wide landing uses three columns; compact two; mobile one. Predictions/Decisions use a list plus detail below, not an obligatory side-by-side split that hides data. Tables use horizontal scrolling at narrow widths; no required columns/values are hidden. At320px/200% zoom the page shell has no horizontal overflow except labelled evidence table regions. Long strings wrap. On mobile, stale/corrupt notices stay above their tables.

ASCII wireframes are design targets only; no screenshots or rendered frontend assets are produced in this task.

```text
WIDE: Development (>1120px)
+------------------+----------------------------------------------------+
| SEED             | SEED / Astra / Development       [Theme] [Refresh] |
| OBSERVE (6)      | ASTRA - DEVELOPMENT EVIDENCE                       |
| DEVELOPMENT (7)  | Separately recorded evidence; not one atomic state |
| > Development    +----------------+----------------+------------------+
| OPERATE (4)      | Transition #24 | World Model    | Curiosity #18    |
| placeholders     | present/absent | 20 this page   | stored status    |
| scrollable nav   | completion time| source times   | created time     |
|                  +----------------+----------------+------------------+
| Observer 0.1     | Consolidation  | Self Model     | Decision #24     |
| Local to Mac     | run status/time| source freshness| corrupt slot    |
+------------------+----------------------------------------------------+
                   | Retained counts: Not loaded [Load retained counts] |
                   | Read times belong to cards, not producer updates.  |
                   +----------------------------------------------------+

Predictions list and selected detail (desktop/compact)
+----------------------------------------------------------------------+
| Predictions - stored B1/B2/B3 evidence                       [Refresh]|
| [20 per page]     [Newer] [Older]   Cursor shown in link               |
| Transition | Episode | Completed | Action | Pred | Eval | Inspect     |
| 24         | 31      | <time>    | rest   | yes* | yes* | [Open]      |
| * Presence does not validate payload                                 |
+----------------------------------------------------------------------+
| Transition #24 / Episode #31 [View episode] [Decision] [Curiosity]     |
| Prediction: Stored  Evaluation: Stored  Model/version/horizon         |
| Signal | Predicted | Method | Evidence support | Actual | Error/status|
| Battery ...                                                          |
| Coverage .25 | Mean normalized error .01 | Stored B3 score .99        |
| [details: formatted stored fields]                                   |
+----------------------------------------------------------------------+

Decisions: dense evidence
+----------------------------------------------------------------------+
| Decision <id> | transition24 | selected/created timestamps            |
| Selected rest / fallback / legacy_q / fallback_reason                 |
| Eligibility and stored selection_candidates (no reranking)            |
| Action | Eligible/reasons | Raw Q | Q comp | Risk | Uncertainty | U    |
| observe                                                               |
| reflect                                                               |
| consolidate                                                           |
| rest                                                                  |
| [details: 12 compact resource forecasts and provenance]               |
| Prediction digest <full copyable hex> [View transition evidence]      |
+----------------------------------------------------------------------+

MOBILE (<=760px)
+------------------------------------+
| [Menu] SEED        [Theme]          |   Open menu:
| Astra / Predictions     [Refresh]  |   [current link focus]
| [Corrupt] transition24             |   OBSERVE / DEVELOPMENT / OPERATE
| Recorded time / read time separate |   scrollable; Escape returns Menu
| [Previous] [Next]                  |
| < labelled horizontally scrollable |
|   full table; no columns removed > |
| Selected detail below table        |
| [details: stored fields]           |
+------------------------------------+
```

No radar intelligence chart, maturity gauge, brain animation, neural-network decoration or causal graph. Optional component bars display already-recorded values with exact numeric labels and table alternatives; no thresholds or change arrows. Honor existing prefers-reduced-motion for all animation/transition/scroll effects. Dark/light/system themes must pass a manual readable-contrast check (ordinary text4.5:1, large text3:1, meaningful UI boundaries/focus3:1); do not claim that CSS tokens alone prove contrast. Existing SVG charts keep their text/table fallback; no B9 chart is required when a table is clearer.

## 15. Browser verification strategy and future tests

Select **B: unchanged dependency surface**. Existing pytest/TestClient/security/asset infrastructure supports API and static contracts, but does not execute JavaScript or prove keyboard/layout behavior. A Playwright dependency would provide real browser automation at the cost of browser downloads, runtime/package pinning, CI and supply-chain expansion. No such infrastructure exists at baseline. It is not selected for B9 v1; a later separately authorized change can reconsider it. Required manual browser acceptance below is a real release gate, not replaced by string-matching tests. Do not add package files, browser downloads or Node runtime requirements under this design.

Future automated files and assertions (not created in this task):

| Test target | Required behavior |
| --- | --- |
| `tests/dashboard/test_predictions.py` | Empty v7; legacy0/1; v2 B1 no prediction; prediction/no evaluation; full and partial stored evaluation; independently absent/corrupt sibling; supported/unsupported headers; no recalculated metrics; schema2..7/future/ambiguous/missing required tables; detail404; unknown/repeated query, canonical ASCII digits, zero/negative/Boolean/float/oversized cursors and max signed64; descending inclusive keyset/first-unreturned lookahead with gaps and corrupt slots; concurrent insertion/deletion; raw absence vs presence-only flags; strict UTF-8/duplicates/NaN/exponent overflow/depth/nodes/string/source/canonical-byte limits; finite metadata/type gates and orphan episode; exact response caps; <=4 list/3 detail SELECTs; VM interruption and callback/transaction cleanup; zero busy wait and503; no refill/count scans; database dump unchanged; missing home not created; monkeypatched Predictor, evaluator, Memory, sensor/process calls fail if invoked. |
| `tests/dashboard/test_astra_assets.py` | Seven module URLs and renderer registrations/hash keys; all six observer views retained; actual OPERATE placeholders; navigation grouping; local module imports/no external assets/CDN/innerHTML/eval; CSP preserved; skip/main, heading focus hooks, labelled filters/table regions, min44px rules, responsive1120/760/reduced-motion rules; only documented route paths and no mutation or background timer/SSE in Astra modules; structured errors and capped evidence fetch path. Static checks do not claim runtime correctness. |
| Existing `test_world_beliefs.py` | Preserve filters/exclusive cursor and valid payloads; add corrupt slots, SQL sentinels, busy/VM/bytes, source IDs and no causal formatting assumptions; schema/empty distinctions. |
| Existing `test_curiosity.py` | Preserve latest100 contract and old successful summary values; add100 raw-slot corruption accounting, valid/unavailable/zero values and denominator behavior, partial failure flags, strict bounds and byte cap. |
| Existing `test_semantic_memory.py` | Preserve active/weakened/history/source_unavailable distinctions; source JOIN query count; corrupt current vs corrupt source, history slots/cursors, bounded result_json/scalars and all caps. |
| Existing `test_self_model.py`, `test_decisions.py` | Run unchanged contract regressions; no new scores/fields/routes to make UI easier. Keep negative cases for busy/VM/corrupt/freshness/clock reversal and frozen utility returned without recalculation. Add only a missing UI-driven case when genuinely needed. |
| Existing `test_reads.py`, `test_http.py`, `test_assets.py` | Narrow development-count VM/503/success behavior, exact memory-detail bounds and read-only damage cases; old list behavior remains; new reads inherit Host/Origin/observer protection; normal shell still usable; no operator route becomes a B9 control. |
| Overview compatibility regression in the planned `test_astra_assets.py` plus existing read/HTTP tests | Fixture: `/api/development` returns503 `development_read_unavailable`, with valid `/api/status`, `/api/storage` and `/api/health`. Check the bounded backend failure and the renderer’s independently settled development branch/explicit unavailable guards. Required UI contract: identity/activity/resource/storage/health evidence remains visible; Recorded experiences and all other development-only metrics say Unavailable; Development, measured shows the bounded-count notice and lifecycle unavailable; no zero substitution or page-wide error. Preserve success and required-source failure paths. Static checks do not execute the UI; the matching manual browser case below verifies actual rendering. |
| Future `tests/dashboard/astra_fixture.py` | Deterministic builder only for temporary test/manual homes; no execution/import side effects or default installed-home path; fixture supports section16. This is supporting test data construction, not an autonomous scenario/evaluator or a baseline rewrite. |

Do not copy model formula tests into frontend tests. Validate service contract and exact displayed literals; rendering must not invoke core formulas. Reuse existing approved producers/test helpers solely while **constructing synthetic fixtures**, then close writers before exercising read services. Fresh B9 automated test count will be reported when implementation exists;747 and160 are baseline evidence, not predictions of future counts.

Manual implementation acceptance uses a temporary deterministic home only, explicit `SEED_HOME`, local observer mode and browser devtools; never the installed home. Record browser/version/OS, exact source SHA, fixture case, viewport/theme, checks and any failure. Required passes:

1. Tab/Shift-Tab through skip link, all17 navigation entries, tabs/filters/paging/details/refresh; focus after navigation vs refresh; Back/Forward and #main work; no focus lost to aborted renders.
2. Mobile menu closed links cannot receive focus; open/current/Escape/focus return works; navigation remains scrollable at small heights.
3. Widths320,760,761,1120,1121 and1440; 200% zoom; full evidence accessible via horizontal scroll/details, long IDs/digests and malicious text do not break shell.
4. Dark, light and system theme, contrast targets above; reduced motion; readable status text without color; screen-reader headings/table captions/status announcements and no auto-announced large JSON.
5. Actual model availability/legacy/empty/corrupt/stale/suppressed/busy states; no fake zeros; missing link404 remains truthful; wall-clock future/reversal notices.
6. Devtools network confirms cold landing<=7 GETs, warm6 (or7 after explicitly loading counts), no unconditional status GET, no row N+1, only active tab/view, one detail, abort on navigation and ten-second deadline; no requests after leaving an Astra view.
7. Live Activity->Astra->Activity closes/reopens one SSE connection without duplicates; existing Overview refresh still pauses during editing/detail inspection. Seven Astra modules produce no new console errors.
8. MAX_ID/cursor `9223372036854775807` and `9007199254740993` survive JSON display, links and paging without rounding; numeric-looking escaped strings remain strings; raw model values are never silently coerced or recomputed.
9. Observer mode has no enabled mutations or hidden operator prompts; external-looking stored strings render as inert text and do not produce browser requests.
10. With the deterministic development-count budget-exhaustion fixture, confirm `/api/development` returns503 `development_read_unavailable` while status/storage/health remain valid. Overview must still show identity, current activity, resources, Memory & storage and System health; Recorded experiences and the other development-only metrics say Unavailable; Development, measured shows the bounded-count notice and no fabricated timeline. Verify no zero substitution, page-wide error, unrelated stale/failed labels or immediate retries. Restore the successful count read and confirm unchanged successful presentation, including genuine zeros. Check a required-source failure separately still follows the existing Overview error behavior.

No manual browser pass, screenshots or visual implementation is claimed by this design task.

## 16. Deterministic temporary-home acceptance fixture

Specify named isolated cases rather than one mutable live organism. Future fixture builder receives an explicit disposable path, fixed wall clock **1700000000**, deterministic IDs and RNG; refuses the standard installed SEED path and never starts an installed process. Cases can use several small databases so damage/legacy/high-ID tests cannot contaminate healthy cases. Fixture construction may use `Memory` and approved model helpers against that temporary path; dashboard inspection may not. Hash/dump each database before/after read acceptance to prove no writes. No new baseline artifacts replace B0–B8 evidence.

| Case | Deterministic records and required display |
| --- | --- |
| Empty v7 | Fresh schema7 with zero developmental records. Lists are readable empty, Self Model awaiting_first_cycle, no scores or fake prediction values. Exact retained count0 is displayed only after successful count query. |
| B1 only | Transition1, episode1, action observe, started_at1699999900/completed_at1699999901, legacy_reward0.25, both JSON columns NULL. List says Absent/Absent; detail metadata valid, two absent wrappers; decision/curiosity links may404 honestly. |
| B2 only | Transition2/episode2 at1699999910/11, observe; supported B2 payload, evaluation NULL. Predicted battery80, load0.5, disk50, network true with probability_true0.75; numeric method action_mean_delta, network action_boolean_frequency; evidence_count4/confidence0.2/confidence_kind evidence_support; clamped false for numeric. UI says evaluation not recorded, not zero error. |
| B3 full | Transition3/episode3 at1699999920/21 with same supported prediction; stored actual battery79/load0.75/disk49/network false. Stored numeric signed/absolute errors (-1,1), (0.25,0.25), (-1,1); normalized0.01,0.25,0.01. Network classification_error1/correct false/Brier0.5625, normalized0.5625. Aggregate evaluated_signals4,target_signals4,coverage1,mean_normalized_error0.208125,accuracy_score0.791875. Display these literals, do not calculate them in JS. |
| B3 partial / genuine zero | Transition4: battery predicted80/actual79; other signals not_evaluated with actual_unavailable reasons; coverage0.25,mean0.01,accuracy0.99, evaluated_signals1/targets4. Separate zero-error stored evaluation has actual=predicted, coverage1,mean0,score1, demonstrating valid0 is not absence. No trend is derived from these fixtures. |
| B4 | Construct eight source transitions (IDs11..18) with identical observed battery delta-0.12 and fixed source times; publish global numeric_delta belief. Expected evidence8,contradictions0,confidence0.4,mean_delta-0.12 and complete source endpoints. Use existing `tests/test_semantic_memory.py::source` shape/`tests/test_world_model.py` recorded-source pattern, not a new formula in UI. Render the noncausal notice and both provenance links. |
| B5 | Three recorded assessments built from existing `tests/test_curiosity_attention.py::store` shape: evaluated score0.4/NOTABLE with below_threshold suppression; unavailable score/parts null and unavailable_evaluation reason; evaluated HIGH with reflection eligible/claimed/completed fields exercising claimed-but-not-completed and recorded failure. Exact accepted producer values from fixture are displayed, not rederived. A100-row-window variant contains98 evaluated score0.8, one unavailable, one evaluated0.4: mean_score(98×0.8+0.4)/99 =78.8/99 =0.795959595959596, raw100; label evaluated denominator99. A separate damaged slot variant consumes one raw slot and increments corrupt_assessment_count. |
| B6 | Use approved semantic source and Consolidator against fixture only: promote source confidence0.4 => revision1 active; lower confidence0.2 => revision2 weakened; restore0.4 => revision3 active. History order2 then1, current3; accepted payload mean_delta-0.12 survives. Three run audits show creation, weakening and revision. Add owner_requested low_disk suppressed audit; source_status missing-source variant preserves valid current semantic payload. |
| B7 | Use existing `tests/test_self_model.py::record/update` shape to publish source transition with observation time1699999939 at measured_at1700000000; read at1700000000 makes that observation61s old/stale while a missing network field is unavailable and catalog remains supported. Show stored source TTL/reasons, exact/at_least counts, singleton measured time; a second read at1699999999 produces clock_regression projection without changing stored bytes. |
| B8 | Four valid linked transition slots before damage. Reuse approved `tests/test_decision.py` literal conflict fixture/RNG for composite exploit (observe utility0.7424999999999999; alternatives0.5175/0.6174999999999999); raw-Q fallback with no_supported_resource_forecast; low-disk constraint (consolidate Q100 excluded, rest Q1/utility0.375 selected); then corrupt one record JSON. Persist through approved frozen-record APIs during fixture creation with fixed times and source IDs before selected transition; copy the real digest, never invent one. List page limit2 with IDs124 corrupt and123 valid returns next_cursor122; detail124 is invalid_decision. Test untouched stored component value is rendered without recomputation. |
| Legacy | Unversioned legacy fixture plus schema1 and schema2 variants. Original six observer views remain usable to their existing extent; Astra distinguishes feature absent, valid transition without prediction and missing record, without migration or fatal page-wide failure. |
| Boundary/damage | Separate home with IDs1,9007199254740993,MAX_ID; prediction source exactly16384 vs16385 bytes, canonical expansion over cap, corrupt middle slot, malformed metadata, duplicate keys, deep tree, exclusive DB lock and reduced VM budget. Verify exact cursor/no-refill and corrupt/503 states. Use padding around a valid JSON object for exact source-byte boundaries. |
| Development count budget exhaustion | Proposed temporary v7 home with valid status/storage/health fixture evidence and retained rows. Use a reduced **development-reader-only** test VM budget to deterministically interrupt its count query; do not reduce the required sources’ budgets or add a production setting. Direct `/api/development` returns bounded503 `development_read_unavailable`, with no partial counts, retries or scanning beyond that budget. Overview remains usable with only development-derived values unavailable and an explicit Development, measured notice; no fake zeros or lifecycle timeline. Snapshot/hash the fixture DB before/after to confirm unchanged storage. This is a future fixture contract, not an implemented or executed case. |
| Browser fixture | Healthy combined records plus selectable empty/legacy/corrupt cases, long inert note strings, IDs/digests, keyboard/mobile/theme/reduced-motion checks. No “improving” badge or B10 success metric. |

Fixture IDs used by independently named B5/B6/B7 cases may differ from the combined B1/B2/B3 case: builder returns an explicit ID manifest for links, never silently assumes IDs from insertion order across model helpers. The B8 page variant has its own database: reserve source transitions1..80 for the approved conflict fixture (20 per action, all completed_at1699999000), then set the fixture-only autoincrement sequence to120 before persisting the four decisions through normal record linkage, producing IDs121..124. Select composite at1699999001, raw-Q fallback at1699999900, low-disk fallback at1699999910, and the later damaged slot at1699999920; each created_at is selected_at+1. The latter three see only stale resource contributors. Each of these four post-action observations is an empty dictionary, so it adds no usable forecast sample and cannot accidentally restore forecast support for the next fixture decision. Normal fixture serialization creates the matching transition IDs/digests; do not patch frozen records after persistence except the explicitly damaged124 JSON. Each raw-Q fixture sets its own Q values before selection: healthy fallback uses reflect0.7 with observe/consolidate/rest0 (reflect selected); low disk uses consolidate100/rest1/observe0/reflect0. The final pre-damage slot uses the same low-disk state/Q values and deterministic RNG as its predecessor. All source IDs precede the decisions. Actual UI links always use returned IDs. The spec's page assertions use the manifest, not guessed model adjacency.

Fixture scores above are literal acceptance data for **display and provenance**. They do not constitute experimental outcomes, improvement criteria or permission to change B1–B8 formulas.

## 17. B10 exclusion and future implementation file map

B9 displays recorded values and existing bounded summaries. Explicitly exclude rolling accuracy interpreted as improvement, intervention before/after studies, development/maturity scores, learning-speed benchmarks, statistical significance, success thresholds, baseline-versus-treatment comparisons, training/evaluation splits, policy-quality claims and “smarter over time.” Do not add empty evaluation widgets that imply B10 exists. B7's stored performance snapshot and B5's existing bounded summary are labelled with their producer/window and are not a new evaluator.

The following are **future implementation targets only**, not a sequential implementation plan and not files to create in this design task:

| File(s) | Responsibility / reason |
| --- | --- |
| `dashboard/services/predictions.py` | New exact section7 read projection and supported payload shape checks. |
| `dashboard/services/evidence_reads.py` | Shared scoped bounded-read/strict-decoding helpers for proven older-adapter gaps; no core imports that produce data. |
| `dashboard/api/observer.py` | Two prediction GETs/strict input handling; compact capped response serialization for hardened B4–B6/development/memory-detail routes; keep B7/B8 contract unchanged. |
| `dashboard/services/seed_service.py` | Prediction delegation, bounded B4/B5/development/direct-memory reads and B5 corrupt-window accounting; no observer status/process expansion. |
| `dashboard/services/semantic_memory.py` | Existing API safeguards, source JOIN and bounded histories/audits; preserve revisions and source_status semantics. |
| `dashboard/static/index.html` | Astra-compatible heading/breadcrumb and navigation/focus semantics while keeping default title/brand/edition; necessary markup accessibility hooks. |
| `dashboard/static/app.js` | Grouped registrations, query-aware hashes, #main handling, generation/abort cleanup, per-view request lifecycle, no Astra status request, focus/menu logic. |
| `dashboard/static/api.js` | Capped same-origin evidence GET, structured errors, lossless large-integer token handling and labelled table/details primitives. Existing mutation API not used by Astra. |
| `dashboard/static/evidence.js` | Shared state badges, timestamp/ID/link formatting, cursor state and bounded record presentation so seven views do not duplicate semantics. No model math. |
| `dashboard/static/styles.css` | Existing tokens/breakpoints retained; scrollable17-entry navigation, mobile inert/focus presentation, table regions, primary target sizing and evidence layout. |
| `dashboard/static/views/{development,predictions,world_model,curiosity,semantic_memory,self_model,decisions}.js` | Seven read-only page renderers with section4 routes. |
| `dashboard/static/views/overview.js` | Preserve existing Overview by independently settling the newly bounded `/api/development` source; unavailable retained counts render as Unavailable, never zero, while successful required-source evidence remains visible. Preserve existing status/storage/health failure behavior; no new model or process semantics. |
| `dashboard/static/views/learning.js` | Exact section11 wording/default-absence correction; no changes to learner/API data. |
| `dashboard/static/views/concepts.js` | Explicit legacy-concept subtitle and Semantic Memory link; no model merging. |
| `dashboard/static/views/memory.js` | On-demand exact episode detail hash mode; normal Memory list unchanged. |
| `tests/dashboard/test_predictions.py`, `test_astra_assets.py`, `astra_fixture.py` | Future contracts/registration checks and deterministic temporary fixture. |
| Existing dashboard test files named in section15 | Targeted compatibility/security/bounded-read regression extensions; no duplicated producer formula tests. |

`dashboard/app.py` metadata, `dashboard/security.py`, `dashboard/api/operator.py`, `dashboard/api/stream.py`, `dashboard/services/{decisions,self_model}.py`, `charts.js`, all `seed/`, schema, requirements, workflows, installer and historical baselines require **no change** in this design. If later implementation cannot meet this contract without core/schema/new dependency work, stop and seek owner review of the concrete blocker rather than expanding B9 silently.

## 18. Design acceptance and self-review

| Review question | Resolution |
| --- | --- |
| 1. Does a page invent B1–B8 data? | No. Typed stored fields, source-specific states and explicit missing wrappers; landing cards remain separate. |
| 2. Does B4 imply causality? | No. Permanent descriptive-statistics notice and action-conditioned wording; source range endpoints are not causal edges. |
| 3. Does Curiosity imply emotion? | No. Salience/surprise component and recorded reflection flags only. |
| 4. Does Self Model imply personality/consciousness? | No. Existing descriptive envelopes/catalog with exact provenance/status. |
| 5. Does Development imply improvement/maturity? | No. Counts/availability/navigation only; no overall score or trend. |
| 6. Is evidence support treated as calibrated probability? | No. Explicit support label; Boolean empirical probability separately named. |
| 7. Are historical decisions rescored? | No. Unchanged B8 read service and frozen candidate values/set/digest; no ranking arithmetic. |
| 8. Does UI reproduce model math? | No. Formatting, bounded parsing and navigation only. Existing producer summaries are not recalculated. |
| 9. Are there unbounded scans or N+1 detail requests? | No new UI N+1; guarded count/filter scans stop at a VM budget. Older untouched legacy routes are documented and not called by Astra implicitly. Semantic source join replaces its per-row lookup. |
| 10. Do B9 routes write/migrate/start core? | No. mode=ro, read transaction cleanup, no Memory/process/sensor production calls. |
| 11. Does B9 complete Operator Edition? | No. Explicit placeholders and unchanged0.1 Observer Edition metadata. |
| 12. Does B9 implement B10? | No. Section17 exclusions; fixture metrics are display data only. |
| 13. Are legacy/empty/absent/corrupt/service states distinct? | Yes. Schema/row/payload/HTTP levels are specified separately, without fake zeros. |
| 14. Are timestamps/freshness truthful? | Yes. Per-source clocks, B7 projection retained, browser read time separate, clock reversal explicit. |
| 15. Are mobile/keyboard/reduced-motion requirements concrete? | Yes. Explicit threshold edges, focus policy, inert mobile disclosure, scrollable nav/tables, text states and manual matrix. |
| 16. Are all new reads bounded? | Yes. SQL/VM/byte/response/GET/retention budgets including bootstrap and removal of hidden status fetch; source/canonical bytes checked. |
| 17. Is schema v7 unchanged? | Yes. No core/schema proposal is needed; all new structure is read/presentation only. |
| 18. Is installed organism untouched? | Yes. Source inspection and temporary characterization only; no installation, live memory or lifecycle operation. |
| 19. Does bounded hardening of an existing route break an existing observer page? | No under the amended design: `/api/development` may fail boundedly, so future Overview treats it as an independently degradable source; other successful Overview evidence remains visible and development-only values say Unavailable. Sections8.2,15–17 specify the compatibility adjustment and regression fixture. This behavior is specified, not implemented. |

All owner-requested design topics D0–D36 are resolved here: baseline/audit (§1–2), architecture/identity/navigation (§3–4), evidence/API gaps (§5,7–8), seven views (§6–9), cross-links/state/clocks (§10), legacy concepts/learning (§11), resource budgets (§7–8,12), security/accessibility/responsiveness/visuals (§13–14), verification/tests/fixtures (§15–16), B10/file map (§17), review/status (§18 and tracker). No implementation-critical decision is deferred. The larger older dashboard's unrelated limitations are explicitly outside this contract, not hidden implementation dependencies.

Initial design validation passed: exactly the three allowed documentation files differ from the verified base; Markdown fences are balanced, all53 internal file/anchor links across these documents resolve, literal byte/fixture arithmetic checks pass, and historical B8 sections remain byte-identical. `git diff --check` against the baseline also passed. The local checkpoint `4087fefcfe12fa9d582bba3cb5e53ddeae00d735` appeared during final validation and was preserved; the design completion is a separate local commit. No production files, new tests, implementation plan, screenshots, dependency/schema/API implementation, deployment, live-memory access or B10 work is included. **Review amendment boundary:** commit only these three documents, publish to the existing `seed-0.2-b9` branch as now authorized, then stop for owner review. Do not open a PR, create an implementation plan, implement B9 or start B10.


### Owner-review preparation amendment — 2026-09-29

The supplied independent review of published design `a6aa042c343c5e90dcf74c3fc90436e006d04e98` reported **0 Critical, 1 Important, 0 Minor**. Source inspection confirms that the proposed bounded development-count failure would reject Overview’s existing four-source `Promise.all`. The amended contract keeps the backend budget and exact-count semantics while specifying independent development-source degradation, unavailable-only development metrics, and preservation of other successful Overview evidence. Sections8.2,15–18 define the future renderer adjustment, automated/manual regression contract, deterministic fixture, file-map entry and compatibility self-review. No behavior is implemented in this amendment.

Amendment validation passed: exactly the three authorized documents differ from the starting head; Markdown fences are balanced; all 53 internal file/anchor links resolve; literal byte/fixture arithmetic is unchanged and valid; the development backend budget is preserved verbatim; only `overview.js` is added to the future file map; historical B8 sections remain byte-identical; no unresolved task markers remain; `git diff --check` passes. No fresh tests or browser checks were run for this documentation amendment.
