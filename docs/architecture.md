# SEED architecture inspection

Inspected 2026-09-21 before implementation. All source files and installation scripts in this prototype were read. This directory is not a Git repository and contains no AGENTS.md, dependency manifest, API, dashboard, or test suite.

## Existing runtime

- `main.py` resolves `SEED_HOME` (default `~/Library/Application Support/SEED`), constructs `SeedOrganism`, installs SIGTERM/SIGINT handlers, and runs it. Construction currently happens at import time.
- `seed/organism.py` owns memory, sensors, learner, identity, and lifecycle. A cycle senses, chooses an action, computes reward, updates learning, optionally reflects or consolidates, records an episode, and persists latest state/action. Delays are 8/12/20/35 seconds for observe/reflect/consolidate/rest.
- `seed/body.py` uses a fixed `pmset` command, load averages normalized by CPU count, disk usage, platform identity, local time, and a TCP reachability probe to `1.1.1.1:443`. The existing probe opens an outbound connection. The dashboard must not add network probes.
- `seed/learner.py` implements an epsilon-greedy contextual bandit, with epsilon 0.15 and alpha 0.18. It stores four action values per encountered context. Decisions contain context, action, and selected pre-update score, but not exploration provenance or alternatives.
- `seed/memory.py` provides a thread-locked SQLite connection, WAL mode, parameterized writes, and a commit after each operation. There is no schema-version migration system.
- `seedctl.py` prints a JSON status snapshot or executes a fixed log-tail command. It does not inspect process health.

## Persistence

| Table | Existing fields and purpose |
| --- | --- |
| `meta` | JSON values by key: identity, last wake/sleep, last state/action, last consolidation |
| `episodes` | id, timestamp, event, state JSON, action, reward, note |
| `q_values` | context/action primary key, value, visit count |
| `concepts` | name, confidence, evidence count, payload JSON, last update |

Reflection reads the latest 80 episodes and derives mean load and mean battery concepts when at least eight suitable readings exist. Concept evidence is the sample count in that window, not lifetime evidence. Supporting episode IDs and creation timestamps are not retained. Consolidation records a checkpoint; it does not delete episodes or reduce database size.

## Lifecycle and installation

`install.sh` copies the project to the installed app directory, creates the per-user `local.seed.organism` LaunchAgent, and starts it. It uses RunAtLoad without KeepAlive. stdout and stderr go to `seed.log` and `seed.err.log`, without rotation. `uninstall.sh` removes startup behavior and preserves memories.

The installed plist was inspected read-only. Its label matches the source, but its Python executable is an installed virtual environment rather than the install script's dynamically selected executable. Preserve this installation-specific configuration.

The existing database was opened in SQLite read-only mode for schema/count inspection only. At inspection it held 216 episodes, 2 concepts, and 7 state-action rows; its main file was 57,344 bytes, excluding WAL and SHM. No installed files or memories were changed.

Wake is inferred when the gap between cycle starts exceeds 45 seconds. Process termination records a `sleep` episode with `process_stop`. Neither is an authoritative native macOS sleep notification. There is no heartbeat, process ownership lock, active-action timing, or persisted failure telemetry.

## Integration constraints

1. Keep the core usable without dashboard dependencies.
2. Read existing data through a narrow service, with read-only connections for observer requests.
3. Add telemetry and migrations incrementally; never replace the database or backfill invented historical facts.
4. Capture decision provenance at selection time, before learning updates change the Q values.
5. Execute core commands through the running organism, not a second organism instantiated by the web server.
6. Report missing or stale telemetry explicitly; old `last_action` metadata is not proof of current execution.
7. Do not invoke the existing installer as a routine development step: it replaces installed app files and restarts SEED.

The proposed dashboard design is in `docs/superpowers/specs/2026-09-21-dashboard-design.md`.
