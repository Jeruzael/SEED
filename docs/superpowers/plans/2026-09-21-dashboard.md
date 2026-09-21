# SEED Local Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a truthful local observatory, then safe owner operations, while preserving the working SEED prototype and its memories.

**Architecture:** A standalone FastAPI server serves local static assets and exposes a narrow service adapter. Add standard-library telemetry and a persistent command queue to the existing core; only the organism executes core actions. Ship the observer gate before enabling mutations.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, SQLite, vanilla JavaScript/CSS/HTML, SSE, pytest/httpx for isolated tests.

**Spec:** `docs/superpowers/specs/2026-09-21-dashboard-design.md`, approved 2026-09-21. Read `docs/architecture.md` alongside it.

## Global Constraints

- The server binds only to `127.0.0.1`, default port 8765.
- The core retains its standard-library-only runtime.
- Keep the existing four tables and contents.
- Take a consistent backup before applying a migration to installed data.
- Do not infer exploration from current Q values.
- An explicit owner stop never triggers automatic restart.
- Default memory budget is 2 GiB.
- Experimental features default off.
- All tests use temporary homes and mocked telemetry/process management, never the owner's live memory or LaunchAgent.
- Do not run the current installer during implementation.
- Preserve the installed LaunchAgent's interpreter.
- Idle consolidation remains unavailable because the current core has no user-idle sensor.
- No arbitrary shell execution, privilege escalation, destructive reset, or new outbound network behavior.

## Review Focus

1. Legacy schema, missing data, and malformed stored JSON must not create data or fabricate current activity: Tasks 1, 3, 4.
2. A stale heartbeat, PID reuse, or an interrupted command must not authorize a second organism or replay a side effect: Tasks 2, 6.
3. Symlinks and pre-existing unrelated files must not redirect backup, retention, or rotation outside approved storage: Task 7.
4. Browser requests with hostile Host/Origin or embedded markup must not mutate SEED or execute script: Tasks 4, 5, 6.
5. Clock jumps, DST repetition, and a second scheduler must not duplicate automation runs or override owner stop: Task 9.

## Delivery structure and working setup

Tasks 1–5 form Observer Edition 0.1; Tasks 6–10 form Operator Edition 0.2. They share persistence, identity, security, and telemetry contracts, so this is one ordered integration plan with two independently verifiable release gates. Future idle sensing is outside this implementation; its rule stays unavailable as approved.

The workspace is not a Git repository. Before source changes, create a timestamped source archive within a local `.checkpoints/` directory, excluding virtual environments, bytecode, checkpoints, and any data. Do not initialize Git or copy installed memories as an incidental planning action. At each task boundary record changed files and verified commands in `docs/implementation-log.md`; make commits only if Git is intentionally established during execution.

Use `/opt/homebrew/bin/python3.13 -m venv .venv`. Plain `python3` currently resolves to 3.9.6. Create `requirements-dashboard.txt` with FastAPI/Uvicorn and `requirements-dev.txt` adding pytest/httpx. Resolve compatible releases during implementation using official package documentation, then record exact installed versions. Do not install into SEED's installed virtual environment.

All test commands below use `.venv/bin/python -m pytest`. Create `tests/__init__.py`, `tests/dashboard/__init__.py`, and an immutable copy of the original schema in `tests/fixtures/legacy.sql`. UI code has no npm/build requirement.

## Task 1: Additive persistence and isolated regression fixtures

**Files:** create `seed/migrations.py`, `seed/telemetry.py`, `seed/paths.py`, `tests/conftest.py`, `tests/fixtures/legacy.sql`, `tests/test_migrations.py`; modify `seed/memory.py`.

**Interfaces:** `migrate(db: sqlite3.Connection) -> None`; `Telemetry(memory: Memory)` with `emit(category: str, source: str, message: str, data: dict) -> int`, `runtime(**fields) -> None`; `checked_path(home: Path, relative: str) -> Path`. Migrations use a dedicated `seed_schema` version table, not an assumed unused global `user_version`.

- [ ] Create the environment/dependency files and a `legacy_home` fixture that executes the frozen SQL in a temporary directory and inserts one identity, episode, concept, and Q row. Add a `home` fixture that creates a migrated temporary database, closes the initializer connection, and returns its directory. `Memory.episode()` gains an integer return value without breaking existing callers.
- [ ] Write preservation and idempotence tests before implementing migration:

```python
import sqlite3
from seed.migrations import migrate

def test_migration_preserves_original_rows(legacy_home):
    with sqlite3.connect(legacy_home / "memory.sqlite3") as db:
        tables = ("meta", "episodes", "concepts", "q_values")
        before = {t: db.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        migrate(db)
        migrate(db)
        assert before == {t: db.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
```

- [ ] Run `tests/test_migrations.py -q`; confirm failure is the missing migration implementation.
- [ ] Implement each migration with `BEGIN IMMEDIATE`, individual `execute()` statements, version write, commit, and rollback on failure. Avoid `executescript()` inside an assumed active transaction. Reject unknown newer schema versions. Add tables:

```sql
CREATE TABLE seed_schema(version INTEGER NOT NULL);
CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
 category TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL, data_json TEXT NOT NULL);
CREATE TABLE runtime(singleton INTEGER PRIMARY KEY CHECK(singleton=1), data_json TEXT NOT NULL);
CREATE TABLE concept_evidence(name TEXT PRIMARY KEY, created_at REAL,
 updated_at REAL NOT NULL, episode_ids_json TEXT NOT NULL);
CREATE TABLE commands(id TEXT PRIMARY KEY, name TEXT NOT NULL, session_id TEXT NOT NULL,
 created_at REAL NOT NULL, expires_at REAL NOT NULL, status TEXT NOT NULL, result_json TEXT);
CREATE TABLE annotations(episode_id INTEGER PRIMARY KEY REFERENCES episodes(id),
 important INTEGER NOT NULL DEFAULT 0, tags_json TEXT NOT NULL DEFAULT '[]');
CREATE TABLE settings(singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL,
 data_json TEXT NOT NULL);
CREATE TABLE automations(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data_json TEXT NOT NULL);
CREATE TABLE automation_runs(rule_id TEXT NOT NULL, occurrence TEXT NOT NULL,
 status TEXT NOT NULL, result_json TEXT, PRIMARY KEY(rule_id, occurrence));
CREATE TABLE audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
 action TEXT NOT NULL, parameters_json TEXT NOT NULL, result_json TEXT NOT NULL);
```

Add timestamp/category indexes for events and timestamp/event indexes for episodes. Enable foreign keys on writer connections. Telemetry writes share `Memory`'s lock; no connections are shared without synchronization. Cap events at 50,000 and audit at 20,000 records, pruning in batches after 100 inserts. Never prune episodes. Report the retained window in read APIs.
- [ ] Test rollback with an injected failing migration statement, newer-version refusal, malformed JSON reads, and monotonic event IDs after pruning. `checked_path` rejects absolute paths, `..`, and any symlink component; validate the configured home as the approved root.
- [ ] Run `tests/test_migrations.py -q`, record results and checkpoint source. Installed-data migration backup is completed in Task 7 before any deployment.

## Task 2: Truthful core telemetry and lifecycle ownership

**Files:** create `seed/runtime.py`, `tests/test_core_telemetry.py`; modify `seed/learner.py`, `seed/organism.py`, `seed/memory.py`, `main.py`.

**Interfaces:** extend `Decision` with `values: dict[str,float]`, `visits: dict[str,int]`, `exploration: bool`, `epsilon: float`, `candidates: list[str]`. Add `InstanceLock(path: Path)` context manager using nonblocking `fcntl.flock`. Add `SeedOrganism.close() -> None` for deterministic cleanup. Keep `cycle() -> float`, `reflect()`, `consolidate()`, and `stop()` compatible.

- [ ] Write the decision-provenance regression:

```python
from seed.learner import Learner, state_key
from seed.memory import Memory

def test_decision_keeps_values_before_update(home):
    memory = Memory(home / "memory.sqlite3")
    try:
        state = {"battery_pct": 80, "charging": True, "load_ratio": .1,
                 "disk_free_pct": 80, "local_hour": 12}
        memory.set_q(state_key(state), "reflect", .7, 4)
        learner = Learner(memory, epsilon=0)
        decision = learner.choose(state)
        learner.update(decision, .45)
        assert decision.action == "reflect"
        assert decision.exploration is False
        assert decision.values["reflect"] == .7
        assert decision.visits["reflect"] == 4
    finally:
        memory.close()
```

- [ ] Run `tests/test_core_telemetry.py -q` and observe missing provenance failure.
- [ ] Capture values and visits once per selection and preserve the existing random branch and tie-breaking behavior:

```python
snapshot = {a: self.memory.get_q(key, a) for a in ACTIONS}
values = {a: pair[0] for a, pair in snapshot.items()}
exploration = random.random() < self.epsilon
candidates = list(ACTIONS) if exploration else [a for a in ACTIONS if values[a] == max(values.values())]
action = random.choice(candidates)
```

Emit actual operation order: PERCEPTION → DECISION → LEARNING → ACTION → MEMORY, preserving the current core's update-before-action behavior. The UI must reflect this order instead of pretending reward comes from a different algorithm. Learning events include old/new value and reward. Reflection emits changed concepts and supporting episode IDs for each sensor's actual qualifying sample set.
- [ ] Acquire the core lock before database construction; generate a UUID session, record PID/session/start/heartbeat/current activity/next observation. Refresh heartbeat every two seconds during interruptible waits without running sensors again. Record action completion separately from current resting/idle state. Wrap startup and loop in `try/finally`; release lock and close database even when startup perception fails. Move organism construction and signal registration into `main()` so importing `main` has no side effects.
- [ ] Test forced exploration, ties, unchanged reward arithmetic/default delays, one mocked-sensor cycle, reflection sample provenance, lock contention, SIGTERM-compatible stop, and injected perception failure. Use monkeypatched `Body.perceive` everywhere; never call real telemetry in tests. For stale metadata expose uncertainty, not SLEEPING; legacy stop remains labeled process stop.
- [ ] Run `tests/test_core_telemetry.py tests/test_migrations.py -q`; checkpoint and record results.

## Task 3: Read-only service, storage inventory, and process observation

**Files:** create `dashboard/__init__.py`, `dashboard/services/__init__.py`, `dashboard/services/seed_service.py`, `dashboard/services/read_store.py`, `dashboard/services/storage.py`, `dashboard/services/process.py`, `tests/dashboard/test_reads.py`.

**Interfaces:** `SeedService(home: Path, process=None, clock=time.time)` exposes `status()`, `environment()`, `history(limit=200)`, `memories(search='', event=None, sort='newest', page=1, page_size=50)`, `memory(episode_id: int)`, `concepts()`, `learning()`, `development()`, `storage()`, `health()`, and `events(after=0, limit=100)`, all returning JSON-compatible dictionaries. `ServiceError(code: str, message: str, status: int)` defines structured failures. `ProcessController(home: Path).status() -> dict` is read-only here.

- [ ] Add a missing-home test and a seeded legacy retrieval test:

```python
from dashboard.services.seed_service import SeedService

def test_missing_home_is_not_created(tmp_path):
    missing = tmp_path / "absent"
    status = SeedService(missing).status()
    assert status["data_state"] == "missing"
    assert not missing.exists()

def test_legacy_episode_is_retrievable(legacy_home):
    service = SeedService(legacy_home)
    page = service.memories(page_size=1)
    assert page["total"] == 1
    assert len(page["items"]) == 1
    assert service.learning()["last_decision"] is None
```

- [ ] Run `tests/dashboard/test_reads.py -q`, verify missing module failure, then implement reads using URI `mode=ro`, short-lived connections, bound parameters and a one-second busy timeout. Never call `Memory()` from observer requests. Decode JSON defensively with explicit record-level warnings.

```python
SORTS = {"newest": "id DESC", "oldest": "id ASC", "reward": "reward DESC, id DESC"}
if sort not in SORTS or not 1 <= page_size <= 100 or not 1 <= page <= 100000:
    raise ServiceError("invalid_query", "Invalid pagination or sort", 422)
query = "SELECT * FROM episodes WHERE (?='' OR note LIKE ?) ORDER BY " + SORTS[sort] + " LIMIT ? OFFSET ?"
```

Include event/state/action/note in the final search predicate; only predefined sort fragments enter SQL. Return items, total, page, page_size. Do not pass owner text into SQL syntax.
- [ ] Implement fixed `launchctl print gui/<uid>/local.seed.organism` with `shell=False`, two-second timeout, no user-supplied arguments. Distinguish unregistered, loaded/not running, running, and inspection failure. Match active session/lock evidence before reporting AWAKE. Stale heartbeat yields `lifecycle=null` and a reason; process status alone does not prove current action. Legacy snapshots expose `compatibility='legacy'`.
- [ ] Count main DB/WAL/SHM, logs, backups, and other files without following symlinks. Report logical table bytes separately when `dbstat` is available; otherwise mark unavailable and never double-count logical event bytes as physical usage. Cache status 2s, storage 5s, counts 10s, history 30s with bounded instance-owned caches. Aggregate retained observations, contexts, learning visits, wake gaps, owner notes, rewards, action distributions, and available event milestones.
- [ ] Test query injection, event filtering, all sort modes, page bounds, corrupt database, malformed JSON, negative/future heartbeat age, unknown PID identity, log errors, and symlink inventory exclusion. Verify observer calls preserve legacy schema and rows.
- [ ] Run `tests/dashboard/test_reads.py -q`; checkpoint and record results.

## Task 4: Loopback HTTP API and resumable SSE

**Files:** create `dashboard/app.py`, `dashboard/__main__.py`, `dashboard/security.py`, `dashboard/api/__init__.py`, `dashboard/api/observer.py`, `dashboard/api/stream.py`, `tests/dashboard/test_http.py`, `tests/dashboard/test_stream.py`.

**Interfaces:** `create_app(home: Path, port: int = 8765, operator: bool = False) -> FastAPI`; `server_options(port: int) -> dict` always returns host `127.0.0.1`; `encode_event(event: dict) -> str`; `SecurityContext` owns a random process token exposed only to same-origin bootstrap. `/api/bootstrap` returns token and capability flags.

- [ ] Add endpoint, host, and binding tests:

```python
from fastapi.testclient import TestClient
from dashboard.app import create_app
from dashboard.__main__ import server_options

def test_local_status_and_host_rejection(legacy_home):
    with TestClient(create_app(legacy_home), base_url="http://127.0.0.1:8765") as client:
        assert client.get("/api/status").status_code == 200
        assert client.get("/api/status", headers={"host": "attacker.example"}).status_code == 403
    assert server_options(8765)["host"] == "127.0.0.1"
```

- [ ] Run the HTTP and stream test files to verify missing APIs fail. Map all read methods from Task 3 to approved `/api` routes; return error envelopes `{error: {code, message}}` without tracebacks/paths. Return 404 for missing episode and 503 for unavailable DB. Serve HTML and static assets from the package directory, not the working directory.
- [ ] Implement exact authority checks for `127.0.0.1:<configured port>`; reject foreign Origin on reads and writes. Mutation guard additionally requires JSON, `X-SEED-CSRF`, and same-origin Origin. Limit request bodies to 16 KiB with streaming enforcement, including chunked requests. Disable CORS; set CSP `default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'`, nosniff and no-store for sensitive responses. Disable automatic docs endpoints or protect them with the same checks.
- [ ] Implement streaming from indexed event IDs, honoring validated `Last-Event-ID`. Use two-second polling, 15-second keepalives, batches of at most 100, at most eight clients, disconnect cancellation, and worker-thread SQLite reads. Send `event: gap` when cursor precedes retention, and `event: reset` when cursor exceeds the database maximum. Legacy schema sends capability notice and heartbeat, not fabricated events.

```python
import json
def encode_event(event):
    payload = json.dumps(event, ensure_ascii=True, separators=(",", ":"))
    return f"id: {event['id']}\nevent: seed\ndata: {payload}\n\n"
```

- [ ] Test reconnect ordering, expired/future/malformed cursors, embedded newlines, eight-client cap, disconnect cleanup, Origin rejection, missing token, oversized chunked body, and attempts to configure `0.0.0.0`. Unit-test generator/cursor behavior without hanging TestClient on an infinite stream.
- [ ] Run `tests/dashboard/test_http.py tests/dashboard/test_stream.py -q`; checkpoint and record results.

## Task 5: Observer interface and first release gate

**Files:** create `dashboard/static/index.html`, `dashboard/static/styles.css`, `dashboard/static/app.js`, `dashboard/static/api.js`, `dashboard/static/charts.js`, `dashboard/static/views/overview.js`, `activity.js`, `environment.js`, `memory.js`, `concepts.js`, `learning.js`; create `tests/dashboard/test_assets.py`; update `README.md`, create `docs/dashboard.md`.

**Interfaces:** `api.get(path, signal)` returns decoded JSON or throws an error carrying code/message; `renderOverview(root,data)`, `renderActivity(root,data)`, `renderEnvironment(root,data)`, `renderMemory(root,data)`, `renderConcepts(root,data)`, `renderLearning(root,data)` render text safely; `renderChart(root, samples, {label,unit})` provides an SVG and accessible data table. `app.js` owns navigation and aborts view-specific requests when leaving a view.

- [ ] Add served-asset regression before implementing the shell:

```python
from fastapi.testclient import TestClient
from dashboard.app import create_app

def test_shell_has_accessible_local_entrypoint(legacy_home):
    with TestClient(create_app(legacy_home), base_url="http://127.0.0.1:8765") as client:
        html = client.get("/").text
        assert '<main id="main"' in html
        assert 'href="#main"' in html
        assert client.get("/static/app.js").status_code == 200
```

- [ ] Run `tests/dashboard/test_assets.py -q`. Build semantic sidebar/header/main, mobile navigation button with expanded state, skip link, empty/error/freshness states, and initial theme from system preference. Save theme locally. Keep interaction/command/automation/settings links visible with honest availability text until their task lands.

```javascript
export function text(tag, value, className = '') {
  const node = document.createElement(tag);
  node.textContent = value == null ? 'Unavailable' : String(value);
  node.className = className;
  return node;
}
```

Use DOM construction for untrusted strings, never `innerHTML`. Format timestamps in the local timezone and expose full timestamps. Show normalized load ratio without a CPU-percent label. Label legacy and stale values beside the metric, not only in a global banner.
- [ ] Build six observer views against Task 3 contracts. Memory: search/event/sort/page controls and full episode details. Concepts: confidence/evidence/payload/provenance. Learning: context picker, all actions, visits, before/after decision values and exploration explanation. Overview: identity, resources, runtime, lifecycle, storage budget, errors, milestones. Environment: latest snapshot and historical SVG/data-table pairs. Activity: EventSource, filters/search/details, 500-item bounded buffer, pause scrolling, clear visible cursor, reconnect/gap status.
- [ ] Use CSS variables for dark/light palettes, minimum 16px body text, 44px interactive targets, explicit focus rings, no color-only state, restrained status pulse, and `prefers-reduced-motion`. Poll only active views with the service intervals; pause nonessential polling when the document is hidden.
- [ ] Run a temporary-home server and inspect desktop/mobile layouts, keyboard order, theme contrast, empty/missing/corrupt data, and hostile owner text such as `<img src=x onerror=alert(1)>`. Confirm it renders literally. Verify paused scrolling does not discard events and clear does not delete records. Record browser evidence and any unavailable checks in the implementation log.
- [ ] Run all tests through Task 5. Complete Observer gate only when status/environment/memory/concepts/learning/storage/errors and SSE work on both legacy and instrumented fixtures. Document running `SEED_HOME=<approved path> .venv/bin/python -m dashboard` without installing or restarting the live core.

## Task 6: Fixed command broker and serialized core requests

**Files:** create `dashboard/command_broker/__init__.py`, `dashboard/command_broker/broker.py`, `seed/commands.py`, `dashboard/api/operator.py`, `tests/dashboard/test_commands.py`; extend `dashboard/services/process.py`, `seed/organism.py`, `dashboard/app.py`.

**Interfaces:** `CommandBroker(service, process, storage, clock=time.time).request(name: str, confirmation: str | None = None) -> dict`; `CommandQueue(memory).claim(session_id: str) -> dict | None`, `complete(command_id: str, result: dict)`, `fail(command_id: str, reason: str)`; `ProcessController.start()/stop()/restart() -> dict`; `POST /api/commands/{name}`, `GET /api/commands/{id}/result`. `GET /api/commands` publishes availability and confirmation requirements.

- [ ] Test no arbitrary execution and operation-specific confirmation before implementation:

```python
import pytest
from dashboard.services.seed_service import ServiceError

@pytest.mark.parametrize("name", ["sh", "observe; touch /tmp/seed-injection", "reset", "delete_memories", "factory_reset"])
def test_unknown_commands_rejected(broker, name):
    with pytest.raises(ServiceError) as error:
        broker.request(name, confirmation="RESET SEED")
    assert error.value.code == "unknown_command"

def test_confirmation_is_bound_to_operation(broker):
    with pytest.raises(ServiceError) as error:
        broker.request("stop", confirmation="restart")
    assert error.value.code == "confirmation_required"
```

Create `broker` fixture in `tests/conftest.py` from a migrated temporary service and fake process/storage objects recording calls. No tests invoke launchctl mutations.
- [ ] Run `tests/dashboard/test_commands.py -q`. Implement a fixed dictionary of callables for observe/reflect/consolidate/backup/start/stop/restart/export_status/open_logs/rotate_logs. Backup and rotation return unavailable until Task 7. Require `confirmation == name` for stop/restart/rotate_logs and a same-origin CSRF-authenticated request. Reject extra fields.
- [ ] Enqueue core commands only for a verified live instrumented session, TTL 60 seconds, maximum 20 pending requests. Claim with a transaction and status predicate; never execute from the HTTP worker. On organism startup mark previous session's running commands interrupted and pending commands expired. Check for owner stop before each command; commands do not postpone termination.

```sql
UPDATE commands SET status='running'
WHERE id=? AND status='pending' AND session_id=? AND expires_at>?;
```

The loop checks the queue during two-second waits. Observe records a fresh sensor episode without selecting another learned action; reflect/consolidate invoke existing fixed functions and record completion. Manual commands never masquerade as autonomous policy choices or update Q values unless the existing cycle does so independently.
- [ ] Validate the expected plist label, canonical installed app/main.py, approved SEED_HOME, current user's LaunchAgents path, interpreter file, absence of KeepAlive, and ownership before lifecycle mutations. Use only fixed bootstrap/bootout/kickstart arrays with timeouts. Recheck state after each operation; return observed result. Respect manually running instances by returning an actionable conflict rather than killing an arbitrary PID.
- [ ] Add audit rows for accepted requests and final success/failure, sanitizing and bounding parameters. Test stopped/legacy/unknown process rejection, expired commands, duplicate claims, interrupted work, stop during wait, plist tampering, subprocess timeout, extra JSON fields, and missing/foreign Origin/token at the real API boundary.
- [ ] Run command, security, and core tests; checkpoint and record results.

## Task 7: Safe backups, storage settings, and bounded logging

**Files:** create `seed/config.py`, `seed/logging_setup.py`, `seed/backup.py`, `dashboard/services/settings.py`, `dashboard/services/backups.py`, `tests/dashboard/test_storage.py`, `tests/dashboard/test_settings.py`; update `seed/organism.py`, `main.py`, broker storage handlers and API settings routes.

**Interfaces:** `validate_settings(data: dict) -> dict` remains standard-library only; `SettingsStore(home).get() -> dict`, `update(data: dict, revision: int) -> dict`; `seed.backup.create_backup(home: Path) -> dict` is a standard-library primitive shared by migrations and the dashboard; `BackupStore(home).create() -> dict`, `prune(retention: int) -> dict` wrap it with dashboard audit/retention; `configure_logging(home, max_bytes: int, count: int)`; `StorageService(home).rotate_logs() -> dict` lives in `dashboard/services/storage.py`. `PATCH /api/settings` uses optimistic revision checking and audit. The core must never import the dashboard to perform a backup.

- [ ] Write finite/range/path validation and preservation tests:

```python
import pytest
from seed.config import validate_settings
from dashboard.services.backups import BackupStore

@pytest.mark.parametrize("value", [float('nan'), float('inf'), -1, 1.1])
def test_learning_rate_is_finite_and_bounded(value):
    with pytest.raises(ValueError):
        validate_settings({"alpha": value})

def test_backup_does_not_follow_symlink(home, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / "backups").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        BackupStore(home).create()
    assert list(outside.iterdir()) == []
```

- [ ] Run storage/settings tests for expected missing-module failure. Implement strict keys/types (bool is not an integer), epsilon 0–1, alpha >0–1, port 1024–65535, UI refresh 2–60s, observe 8–3600s, reflect 12–3600s, rest 35–3600s, budget 64 MiB–64 GiB, logs 1–100 MiB/count 1–10, retention 1–100. Defaults preserve existing behavior; consolidate remains 20s. Backup directory is fixed under SEED home. Name length 1–64; theme system/light/dark. Reject unsupported experimental enablement with an explicit capability error.
- [ ] Core reads accepted setting revisions at cycle boundaries and records effective values; dashboard distinguishes saved from applied settings. Port takes effect only on dashboard restart. Move name updates through audited settings to the core identity application step. Prevent partial writes on invalid input.
- [ ] Back up via SQLite backup API into an exclusively created temporary file under validated backups directory, with a bounded busy/progress deadline. Attempt `wal_checkpoint(PASSIVE)` first; checkpoint contention does not justify a raw copy. Close and integrity-check the destination, atomically publish a timestamp-plus-random-suffix name, and record BACKUP result. Add a manifest for files created by this service; retention removes only manifest-owned regular files. Revalidate paths when operating, not just when saving settings.
- [ ] Add a pre-migration snapshot path for existing nonempty legacy DBs before Task 1 migration runs in an upgraded core. Use `seed.backup.create_backup()` under the core instance lock before any schema initialization. Fail without altering the legacy DB if snapshot/integrity verification fails. Fresh temporary/new databases do not require historical backups. Test that this path imports no dashboard or external package.
- [ ] Replace normal core prints with rotating Python logs; no change to sensing or learning. Record shutdown/errors through the logger. Rotate active core logs via the core queue, not concurrent rename by the dashboard. Dashboard rotates its own handler directly. Legacy launchd stdout/stderr files are reported but cannot be safely rotated as managed logs until deployment redirects normal output to the new handlers; show that capability limit. Document bounded emergency output handling during deployment.
- [ ] Test backup while a second connection commits rows, restored integrity and preserved Q/concept rows, read-only/full-disk failure, symlink replacement, filename collision, unrelated-file retention preservation, stale settings revision, and core-applied intervals. Verify no test touches live data.
- [ ] Run storage/settings/migration/command tests; checkpoint and record results.

## Task 8: Owner interaction and operator UI

**Files:** create `dashboard/services/interaction.py`, `dashboard/static/views/interaction.js`, `commands.js`, `settings.js`, `tests/dashboard/test_interaction.py`; extend operator routes and frontend navigation.

**Interfaces:** `InteractionService(home).note(text: str, important: bool = False) -> dict`, `annotate(episode_id: int, important: bool, tags: list[str]) -> dict`, `summary(since: float) -> dict`; routes `POST /api/notes`, `PATCH /api/memories/{id}/annotation`, `GET /api/summary?since=...`. `api.mutate(path, method, body, token)` includes Origin through the browser and the bootstrap CSRF token.

- [ ] Write attribution test before implementation:

```python
import json
from dashboard.services.interaction import InteractionService
from dashboard.services.seed_service import SeedService

def test_owner_note_is_attributed_and_not_sensor_evidence(home):
    note = InteractionService(home).note("Battery is always full", important=True)
    episode = SeedService(home).memory(note["id"])
    assert episode["event"] == "owner"
    assert episode["state"]["source"] == "owner"
    assert "battery_pct" not in episode["state"]
    assert episode["important"] is True
```

- [ ] Run interaction tests, then implement transactional episode+annotation+audit inserts. Trim text, require 1–4000 characters, limit tags to ten strings of at most 32 characters, require actual boolean importance, and reject annotation of nonexistent IDs. Core reflection ignores owner-source episodes as sensor evidence without changing legacy sensor rows.
- [ ] Summaries count actual retained episodes/events in the requested interval and report coverage. Explain actions from persisted decision payloads, with unavailable history stated explicitly. Return structured counts/deltas, no generated persona prose. Do not infer confidence history where no old/new snapshots exist.
- [ ] Build note/important controls, deterministic summary and explanation panels, safe reflect request, command progress/results, backup download/export within approved files, bounded logs view, and validated settings with effective/saved labels. Standard confirmations name the operation and send its exact confirmation field. Disable duplicate submissions and show expired/interrupted commands honestly.

```javascript
export async function mutate(path, method, body, token) {
  const response = await fetch(path, {
    method, headers: {'Content-Type': 'application/json', 'X-SEED-CSRF': token},
    body: JSON.stringify(body), credentials: 'same-origin'
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || 'Request failed');
  return result;
}
```

- [ ] Test hostile markup remains literal, notes never affect concept samples, annotation preserves the original episode, summary interval bounds/coverage, and mutation audit contains old/new safe settings. Browser-check confirmations, keyboard focus restoration, and error retry behavior.
- [ ] Run interaction/commands/settings/HTTP tests; checkpoint and record results.

## Task 9: Visible, constrained automation

**Files:** create `dashboard/automation/__init__.py`, `dashboard/automation/rules.py`, `dashboard/automation/scheduler.py`, `dashboard/static/views/automation.js`, `tests/dashboard/test_automation.py`; extend application lifespan and operator API.

**Interfaces:** `validate_rule(data: dict) -> dict`; `Scheduler(home, broker, clock=time.time).tick() -> list[dict]`; `RuleStore(home).list()/update(rule_id: str, data: dict, revision: int)`; `GET /api/automations`, `PUT /api/automations/{id}`. The scheduler owns a nonblocking file lock separate from the core lock.

- [ ] Write strict rule tests:

```python
import pytest
from dashboard.automation.rules import validate_rule

@pytest.mark.parametrize("data", [
    {"kind": "shell", "command": "echo unsafe", "enabled": True},
    {"kind": "daily_backup", "action": "restart", "enabled": True},
    {"kind": "idle_consolidation", "enabled": True},
])
def test_unavailable_or_arbitrary_rules_are_rejected(data):
    with pytest.raises(ValueError):
        validate_rule(data)
```

- [ ] Run automation tests. Seed disabled rules only on explicit operator initialization. Hardcode kind-to-action mapping, validate daily local HH:MM and IANA timezone using `zoneinfo`, storage threshold 50–95%, cooldown at least 300 seconds. Idle rule is listed with unsupported-sensor reason and cannot enable. No configurable executable, URL, path, start, stop, or restart action.
- [ ] Tick every 30 seconds while dashboard runs. Claim a unique occurrence in `automation_runs` before execution. Daily keys are local calendar dates; run at most one missed occurrence for the current date, never replay prior days. Nonexistent DST scheduled times run at the first later valid local time; repeated hours share the same daily key. Event-triggered wake journal keys use event ID. Storage guard cooldown survives restart.

```sql
INSERT OR IGNORE INTO automation_runs(rule_id, occurrence, status)
VALUES(?, ?, 'running');
```

If a claimed run survives a crash as `running`, mark interrupted and require review rather than retrying an uncertain action. Use the safe broker for backup/checkpoint/log rotation; automation cannot bypass required capability checks. Sleep/stop does not trigger any start behavior. Suspend each rule after three consecutive failures; owner re-enable resets the reviewed failure state and is audited.
- [ ] Build editable disabled/enabled/time/threshold controls, revision-aware saves, next/last run and errors, explicit “runs only while dashboard is open/running” text, and idle-sensor unavailability. Show actual automation audit events in Live Activity.
- [ ] Test duplicate scheduler lock, duplicate daily occurrences, DST repeated/skipped times, backward/forward clock changes, restart after uncertain run, three-failure suspension, stale revision, owner stop, and symlink state paths. Inject clocks and fake broker; do not wait real minutes or run system commands.
- [ ] Run automation/command/security tests; checkpoint and record results.

## Task 10: Integration verification, documentation, and handover

**Files:** create `tests/test_standalone.py`, `tests/dashboard/test_integration.py`, `docs/commands.md`, `docs/security.md`; finalize `README.md`, `docs/dashboard.md`, `docs/architecture.md`, `docs/implementation-log.md`, and `.gitignore` if Git is introduced.

**Interfaces:** documented CLI is `.venv/bin/python -m dashboard [--port PORT] [--operator]`, with SEED_HOME from environment and fixed loopback host. Observer mode is default and cannot mutate. Operator mode refuses unsupported legacy schema; an upgraded core or documented explicit maintenance migration is required first.

- [ ] Add standalone import invariant:

```python
import os
import subprocess
import sys

def test_import_main_does_not_create_memory(tmp_path):
    home = tmp_path / "seed-home"
    env = dict(os.environ, SEED_HOME=str(home))
    result = subprocess.run([sys.executable, "-c", "import main"], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert not home.exists()
```

- [ ] Add integration fixture that runs the real organism loop with patched deterministic Body perception against a temporary home, and a real Uvicorn child process bound to 127.0.0.1 on a free port. Ensure fixture teardown stops children even on assertion failure. Test HTTP status, first SSE event, reconnect cursor, owner note, queued reflection completion, consistent backup, and stop. Mock LaunchAgent mutation; never stop installed SEED.
- [ ] Run the complete suite once with `.venv/bin/python -m pytest -q`. Run `.venv/bin/python -m compileall -q seed dashboard main.py seedctl.py`. Confirm standalone core works without importing FastAPI/Uvicorn. Run a bounded real HTTP/SSE smoke check and verify listener address with `lsof` where available.
- [ ] Finish desktop/mobile keyboard and visual checks for all ten views. Verify log/storage thresholds, offline backend state, token expiration after server restart, missing legacy telemetry, reduced motion, high-contrast text, and screen-reader labels. Correct failures, then rerun only affected checks followed by final relevant integration coverage.
- [ ] Document every route and command, confirmations, queue TTL, retention limits, safe backup restore procedure with core stopped, automation limitations, resource intervals, error interpretation, learning provenance, and legacy compatibility. Explain normalized load and inferred wakes. State that consolidation does not delete memory or guarantee freed space.
- [ ] Provide an installation/update procedure that first stops the expected LaunchAgent, backs up SQLite, stages reviewed source excluding `.venv`, tests and checkpoints, preserves the installed interpreter/plist environment, applies additive migrations, and then starts only on explicit owner installation authorization. Do not execute `install.sh` or alter the live installation as part of verification. Explain rollback: stop upgraded core, restore its pre-upgrade source and verified backup only after owner approval; restoring backup discards later records.
- [ ] Review the finished diff/source against the approved safety and acceptance criteria. Native execution uses one independent final review under the executing-plans skill; subagent execution uses task reviews and final review. Record actual test counts, browser evidence, and any unverified checks. Do not label unavailable verification as passed.

## Coverage and handoff

| Approved requirement | Implementation task |
| --- | --- |
| Additive persistence, structured events, provenance | 1–2 |
| Lifecycle, current activity, sleep/wake honesty | 2–3 |
| API, resources, memory/concepts/learning/development | 3–4 |
| SSE, filtering, charts, accessibility, responsive themes | 4–5 |
| Fixed commands, process control, confirmations, audit | 6 |
| Storage budgets, backups, settings, log bounds | 7 |
| Owner notes, annotations, deterministic interaction | 8 |
| Allowlisted automation, failure limits, owner stop | 9 |
| Regression/security checks, documentation, handover | 10 |

Recommended execution: **Native**, in this task, because each phase depends on the same small core and persistence contracts. It avoids repeatedly handing shared state between implementers. Subagent-driven execution remains an option if the owner prefers independent review after every task.

Plan review is pending. No product code, dependencies, installed application files, or existing memories were modified while preparing it.
