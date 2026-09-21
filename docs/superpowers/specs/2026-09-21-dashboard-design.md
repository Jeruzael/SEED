# SEED local dashboard design

Status: approved by the owner on 2026-09-21; implementation has not started.

## Purpose and scope

Build the local observatory and control layer described in the owner's implementation brief. Preserve SEED's learning policy, memories, standalone operation, and owner control. Deliver Observer Edition 0.1 first, verify it, then add Operator Edition 0.2 features. These are sequential delivery gates within the requested scope, not removal of operator requirements.

## Architecture choice

Use Python FastAPI with vanilla HTML/CSS/JavaScript and Server-Sent Events. The server binds only to `127.0.0.1`, default port 8765. The core retains its standard-library-only runtime. Dashboard dependencies are separate.

Alternatives considered: embedding the web server in the organism would simplify commands but couple dashboard failures to SEED; a read-only SQLite viewer would minimize changes but cannot provide reliable current activity or decision provenance. A separate service with small additive core instrumentation supports both truthful observability and safe commands.

The browser calls `dashboard/api`; handlers call `dashboard/services/seed_service.py`. That adapter owns SQLite reads and approved control interfaces. API handlers and frontend code never construct an organism or import its internals directly.

## Data and telemetry

Keep the existing four tables and contents. Add versioned, transactional migrations for structured events, runtime status, command requests, owner annotations, settings, automations, and audit records. Migration tests start with an untouched legacy schema and verify preservation of every existing record. Take a consistent backup before applying a migration to installed data.

Events carry increasing ID, timestamp, category, source, message, and JSON data. Emit perception, decision, action start/completion, learning, memory, concept, lifecycle, error, owner, and automation events from their real execution points. Persist the selection-time Q values, visits, epsilon, exploration result, tie candidates, chosen action, and subsequent reward/update. Do not infer exploration from current Q values.

Record heartbeat, session identity, active action, start time, last successful cycle, next expected observation, and last error. Core event capture must not require a running dashboard. Bound event retention independently of autobiographical memories; stream clients receive an explicit gap indication if their cursor expires.

Record supporting episode IDs for future concept updates; old concepts display evidence count and an unavailable-provenance notice. Preserve the actual rolling-window evidence semantics. Missing creation dates, decision reasons, or historical confidence changes remain unavailable.

## Lifecycle truthfulness

Combine the fixed LaunchAgent status, process/session ownership, heartbeat freshness, and recorded lifecycle. Show AWAKE, STARTING, STOPPED, or ERROR only with supporting evidence. SLEEPING requires an explicit sleep observation; a stale heartbeat is labeled uncertain/stale rather than fabricated sleep. Display heartbeat-gap wake events as inferred. Label historical process-stop episodes accurately.

Use a single-instance core lock and serialize owner actions through the organism loop. A completed action becomes a last-action record while the current activity moves to its actual wait/rest state.

## Observer UI

Persistent desktop sidebar with Overview, Live Activity, Environment, Memory, Concepts, Learning, Interaction, Commands, Automation, and Settings. Responsive navigation on narrow screens. Neutral dark/light themes, restrained sage accent, readable sans-serif text and monospace runtime values, semantic headings, visible keyboard focus, sufficient contrast, and reduced-motion support.

Overview shows identity, development age, lifecycle, freshness, current activity/context, last reward, next observation, resources, storage, last wake/stop, and system health. Clearly distinguish process uptime from lifetime recorded activity.

Live Activity supports category filtering, text search, timestamps, expandable details, paused scrolling, and clearing the visible feed without deleting data. Use bounded in-memory rendering and cursor-based reconnection.

Environment shows the latest recorded sensor snapshot and its age. Render simple accessible SVG charts from real historical episodes when sufficient samples exist; otherwise show an empty state. Load ratio is a normalized load average, not CPU utilization percent.

Memory provides parameterized search/filtering, allowlisted sort keys, bounded pagination, full episode inspection, and non-destructive annotations. Concepts expose actual confidence, sample count, payload, timestamps, and available supporting episodes. Learning exposes all state-action values, visit counts, actual configuration, recent rewards, behavior distribution, and captured decision explanations.

Development metrics and milestones are derived from stored evidence. Retained-episode counts are labeled as such when lifetime totals cannot be established. No personality or consciousness claims.

## API and performance

Read routes: `/api/status`, `/api/events`, `/api/environment`, `/api/history`, `/api/memories`, `/api/memories/{id}`, `/api/concepts`, `/api/learning`, `/api/development`, `/api/storage`, `/api/health`, `/api/settings`, `/api/commands`, and `/api/automations`. `/api/stream` supplies SSE event IDs, reconnect support, and keepalives.

Cache status for two seconds, resources for five seconds, counts for ten seconds, and chart aggregates for thirty seconds. SSE checks for new events at a bounded interval and does not reread full memory. Enforce bounded queries, request sizes, stream queues, and client counts. Use short-lived read-only database connections and handle busy/missing/corrupt databases with structured errors and stale-state notices.

## Security and command broker

Reject unexpected Host and Origin values; do not enable cross-origin access. Require a per-process anti-CSRF token plus same-origin JSON requests for mutations. Serve frontend assets locally, apply a restrictive content security policy, and render owner/database strings as text. Loopback binding alone does not protect against browser-origin attacks.

Use a fixed command registry: observe, reflect, consolidate, backup, start, stop, restart, export_status, open_logs, and rotate_logs. There is no terminal, user-supplied executable, shell expression, arbitrary path, or generic launchctl endpoint. Process operations use fixed argument arrays, timeouts, the verified label, and validated installed plist paths. Open Logs displays a bounded log tail in the dashboard.

Observe, reflect, and consolidate requests are validated, persisted, and executed serially by the running organism. Expire old requests; never replay uncertain interrupted commands automatically. Return unavailable when stopped rather than silently starting SEED. Backup and export use service functions. Stop/restart/rotation require backend-enforced confirmation bound to the named operation. Destructive reset/delete/factory-reset commands are absent and explicitly rejected, even with typed confirmation.

Record owner requests, validated parameters, results, failures, and settings changes in an audit log. Do not log secrets. An explicit owner stop never triggers automatic restart.

## Interaction

Owner notes carry `source=owner`, timestamp, and optional importance/tags; store them as attributed observations, not inferred factual concepts. Exclude owner prose from sensor-evidence aggregation. Deterministic actions summarize recorded changes or explain a captured decision. Reflection uses the command broker. No simulated language-model chat.

## Storage, settings, and backups

Account separately for database/WAL/SHM, events, logs, backups, and other SEED files without following symlinks outside approved directories. Default memory budget is 2 GiB. Explain that current consolidation is a checkpoint and does not reclaim autobiographical memory. Storage warnings recommend review/consolidation without promising space savings.

Validate finite numeric values and bounded intervals/rates. Expose name, UI theme/refresh/port, observation/rest/reflection intervals, epsilon/alpha, memory budget, log size/count, and backup retention. Port changes require dashboard restart. Experimental features default off; unsupported features remain visibly unavailable rather than accepting inert settings.

Use rotating core log handlers and bounded dashboard logs. Preserve the installed LaunchAgent's interpreter; coordinate log redirection changes explicitly during installation. Backups remain under the approved SEED backups directory, reject path traversal and symlink escapes, use SQLite's backup API after a bounded WAL checkpoint attempt, verify integrity, then atomically publish a timestamped file and record the result. Retention affects only recognized generated backups, never arbitrary user files.

## Automation

Persist visible, editable, allowlisted rules, disabled by default: daily backup, idle consolidation, storage guard, wake journal, and daily deterministic summary. The dashboard scheduler runs only while its service runs and displays that limitation. Persist last-run markers and apply cooldowns, timezone-aware scheduling, and bounded missed-run handling.

The existing sensors do not measure user idle time. Idle consolidation therefore remains unavailable until a narrowly scoped idle sensor is implemented; do not substitute low CPU load for user inactivity. Wake journal consumes inferred wake events and labels that provenance. Storage guard may checkpoint and rotate logs, never delete memories. It explains that checkpointing is not compaction.

Rules cannot launch shell commands, install software, access arbitrary networks or files, change security, prevent sleep, or start/restart SEED. Failed runs are recorded and suspended after three consecutive failures until owner review. Duplicate scheduler execution is prevented with a single-instance lock.

## Delivery and verification

1. Complete architecture inventory and design review.
2. Add isolated legacy-schema fixtures and core regression tests; instrument telemetry without changing learning behavior.
3. Implement and verify the read-only service and six observer views, lifecycle freshness, storage, and error states.
4. Add broker/process control, consistent backups, confirmations, annotations, and deterministic interaction.
5. Add validated settings, bounded logs/storage, and safe automation.
6. Verify browser behavior, responsiveness/accessibility, reconnects, and regression tests; document launch, APIs, commands, security, automation, and troubleshooting.

Required automated coverage includes status, pagination/search, concepts, selection-time explanations, missing/stale/corrupt data, legacy migration preservation, allowlisted commands, injection rejection, confirmations, concurrent database backup integrity, settings/rule validation, traversal/symlink rejection, Host/Origin/CSRF defenses, loopback-only startup, owner stop behavior, and automation deduplication/failure limits. All tests use temporary homes and mocked telemetry/process management, never the owner's live memory or LaunchAgent.

Run the core independently against a temporary home and run a real local HTTP/SSE smoke test. Test keyboard navigation, empty/error states, mobile layout, and theme contrast in the browser. Document any validation that could not be run; do not claim it passed.

## Deployment boundary

Develop in this workspace. Do not run the current installer during implementation. Provide reviewed installation/update steps that preserve the installed interpreter, existing memories, and startup behavior. The first dashboard can observe the installed legacy database immediately, while new telemetry requires deploying the instrumented core. Show that compatibility limitation in the UI.
