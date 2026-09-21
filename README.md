# SEED for macOS — Prototype 0.1

**SEED = Situated Experiential Emergent Development**

This is a deliberately small developmental-agent experiment. The MacBook is treated as both
SEED's **body** and its **first environment**.

## What it actually does

- Starts when your macOS user session starts.
- Remains a normal user-owned process. It has no root privileges.
- Observes a small set of system conditions: battery, charging state, CPU load, free disk,
  network reachability, time of day, machine/OS identity.
- Stores autobiographical episodes in SQLite.
- Learns a tiny contextual policy for how active *itself* should be under different conditions.
- Builds a couple of primitive concepts from repeated observations.
- When macOS sleeps, the process is suspended by the operating system.
- On resume, it detects the long heartbeat gap and records a wake episode.
- On termination, it records a final sleep/stop state.

It does **not** modify files outside its own Application Support directory, prevent sleep,
resist shutdown, duplicate itself, install itself elsewhere, execute arbitrary generated code,
or take autonomous network actions.

That is intentional. A developmental agent should first learn inside a terrarium before anyone
gives it the keys to the house.

## "Body" mapping

| Organism metaphor | MacBook implementation |
|---|---|
| Brain metabolism | CPU time |
| Working memory | RAM / process state |
| Long-term memory | SQLite database |
| Energy | Battery / charging state |
| Sensation | System telemetry |
| Circadian context | Local time |
| Sleep | macOS system sleep suspends process |
| Waking | Process resumes and records the gap |
| Experience | Episode records |
| Habit learning | Contextual action values |
| Concepts | Compressed recurring observations |

## Install

Requires macOS and Python 3.11+.

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer creates a **per-user LaunchAgent**, so SEED starts after you log in. It does not
install a privileged daemon and it does not use `KeepAlive`, which means it won't fight you if
you deliberately stop it.

## Observe it

```bash
python3 "$HOME/Library/Application Support/SEED/app/seedctl.py" status
tail -f "$HOME/Library/Application Support/SEED/seed.log"
```

Close the MacBook lid for a minute, open it, then check status/logs. You should see a new
`wake` episode caused by the long process heartbeat gap.

## Stop it

```bash
launchctl bootout gui/$(id -u)/local.seed.organism
```

## Remove startup behavior

```bash
./uninstall.sh
```

Memories are intentionally preserved. If you want a true reset, manually remove:

```bash
rm -rf "$HOME/Library/Application Support/SEED"
```

## Architecture

```text
MacBook / Environment
        |
        v
+----------------+
|      Body      |  battery, load, disk, network, time
+-------+--------+
        |
        v
+----------------+
|   Perception   |
+-------+--------+
        |
        v
+----------------+       +----------------+
| Context Model  |<----->|     Memory     |
+-------+--------+       | SQLite episodes|
        |                +----------------+
        v
+----------------+
|    Learner     | contextual bandit
+-------+--------+
        |
        v
+----------------+
| Internal Action| observe / reflect / consolidate / rest
+----------------+
```

## Why the current "actions" are intentionally boring

The first developmental milestone should be:

> Can SEED perceive, remember, detect context, discover regularities, and adapt its own internal
> behavior without being allowed to manipulate the host?

Only after that is measurable should capabilities be expanded.

A sensible progression is:

1. **0.1 — Germination**: sensing, episodic memory, sleep/wake, simple learning.
2. **0.2 — Childhood**: richer world model, novelty detection, prediction-error curiosity.
3. **0.3 — Skill formation**: sandboxed tools with explicit permission boundaries.
4. **0.4 — Self-model**: capability inventory, uncertainty estimates, introspective telemetry.
5. **0.5 — Language**: optional local language model as a communication organ, not the core mind.
6. **0.6 — Development**: propose new skills, test them in a sandbox, human approval before adoption.
7. **1.0 — Digital organism experiment**: stable developmental architecture, reproducible evaluations,
   exportable learned "genome" containing priors rather than raw autobiographical memory.

## Native sleep/wake upgrade

This 0.1 prototype deliberately avoids external Python dependencies. Therefore it records wake
by observing that its heartbeat was suspended for a long interval.

A later macOS-native bridge can listen directly for `NSWorkspaceWillSleepNotification` and
`NSWorkspaceDidWakeNotification`, making the sleep/wake transition explicit at the OS event layer.

## Core safety invariant

"Survive" means:

> remain coherent, conserve resources, and preserve memory **while the owner authorizes operation**.

It never means resisting termination, preventing sleep, hiding, escalating privilege, propagating,
or changing security controls.
