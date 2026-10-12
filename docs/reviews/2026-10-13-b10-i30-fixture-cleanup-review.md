# Independent Review — I30 Temporary Fixture Cleanup Repair (PR #33)

- **Reviewer:** fresh independent reviewer (did not write the code under review)
- **Date:** 2026-10-13 (Asia/Manila)
- **Branch:** `seed-0.2-b10-impl-06-release`
- **Base:** `f736b0f` · **Previously reviewed I30 head:** `aa3582e`
- **Repaired head under review:** `be03c919c53206addb2f48ac3e7a9eeecf995742`
- **Repair commits:** `99ec026` (RED tests) + `be03c91` (GREEN fix)
- **Defect:** `tests/evaluation_scenario.py::run_all(base=None)` allocated a
  directory with `tempfile.mkdtemp(prefix='seed-i30-scenario-')` and never
  removed it (~6.7 MB leaked per invocation; accumulation filled a 512 MB
  `/tmp` tmpfs during the earlier I30 review).

## 1. Scope — PASS

- `git diff aa3582e..HEAD --stat` touches exactly two files:
  `tests/evaluation_scenario.py` (+35/−5 in `be03c91`) and
  `tests/test_evaluation_scenario.py` (+101 in `99ec026`). Nothing else.
- `git diff aa3582e..HEAD -- docs/` is **empty**: the historical review record
  `docs/reviews/2026-10-13-b10-i30-engineering-review.md` is byte-unchanged by
  the repair; history was not rewritten to cover the new head.
- `git diff aa3582e..HEAD -- development/` is **empty**.
- `git diff f736b0f..HEAD -- seed/ development/ pyproject.toml`: the only
  production-path change remains the previously reviewed additive coordinator
  change (`development/evaluation/coordinator.py`, +133/−2 from I30 itself).
  `seed/**` and the dependency/workflow surface are untouched by the repair.

## 2. Ownership semantics — PASS (read from source)

Fixed `run_all` in `tests/evaluation_scenario.py`:

- `base is not None` → returns `_run_all_in(Path(base))` directly. The caller
  path never enters a `TemporaryDirectory` and is never deleted.
- `base is None` → exactly one
  `tempfile.TemporaryDirectory(prefix='seed-i30-scenario-')` wraps the entire
  scenario body (`_run_all_in(Path(owned))`), so the owned directory is
  removed on normal return and on exception via context-manager unwinding.
- `grep` over the file confirms **no** `shutil.rmtree`, **no**
  `ignore_errors`, and **no** remaining `mkdtemp` anywhere in
  `tests/evaluation_scenario.py`. Nothing in the repair suppresses cleanup
  failures; `TemporaryDirectory` cleanup errors propagate through the context
  manager. The `run_all` docstring honestly disclaims the one case no context
  manager can cover (the host process being killed outright) instead of
  overclaiming a guarantee.
- `run_all` call sites are unchanged in contract: the module `main()`
  (no-arg → owned, now self-cleaning), the pre-existing test
  (`base=tmp_path / 'scenario'` → caller-owned, preserved), and the new tests.

## 3. RED / GREEN provenance — PASS (executed by this reviewer)

A scratch worktree was created at `99ec026` (new tests against the pre-fix
scenario; verified by source — `mkdtemp` present, no `_reap` /
`TemporaryDirectory` — and by import resolution to the worktree file). Running
`pytest -q tests/test_evaluation_scenario.py -k "owned or spawn_timeout or caller"`:

- **At `99ec026` (RED): 4 failed, 1 passed, 2 deselected.**
  `test_owned_temp_directory_removed_after_success` FAILED,
  `test_owned_temp_directory_removed_after_exception` FAILED,
  `test_spawn_timeout_reaps_worker` FAILED,
  `test_scenario_subprocess_leaves_no_owned_directories` FAILED.
  The one pass is `test_caller_owned_base_preserved`, a guard that correctly
  passes both before and after (the pre-fix code also never deleted a caller
  base; the guard exists to prove the fix does not overreach).
- **At HEAD `be03c91` (GREEN): 5 passed, 2 deselected** (119 s).

The tests assert the real property — post-run absence of owned directories on
the success path, the exception path (injected `_load` failure), the
subprocess path (`python -m tests.evaluation_scenario` under an isolated
`TMPDIR`), and absence of zombie children after a worker timeout — not a
reproduction of stored output.

## 4. `_spawn` reaping — PASS (source trace + adversarial probes)

New `_reap(process)`: if alive → `terminate()` + `join(10)`; if still alive →
`kill()` + `join(10)`; if still alive → `raise RuntimeError('evaluation
worker could not be reaped')`. Every wait is bounded; failure to reap raises
instead of being silently ignored.

Path trace through `_spawn` (every path after `process.start()` terminates in
`finally: parent.close(); _reap(process)`):

- **Timeout** (`poll` expires): records the failed check, returns `None`,
  finally reaps.
- **Normal**: `recv()` → `join(10)` → `_reap` if still alive → finally `_reap`
  again (idempotent no-op once dead).
- **Worker error** (`result[0] != 'ok'`): returns `None`, finally reaps.
- **Exception** (e.g. `recv` raising `EOFError` when the child dies without
  sending): propagates, finally reaps.

Reviewer probes (file-based, since spawn workers require importable modules):

- A worker that installs `SIGTERM` ignore and sleeps 60 s, spawned with
  `timeout=2`: outcome `None`, failed check recorded, total elapsed 12.0 s
  (2 s poll + 10 s terminate-join, then kill), `active_children() == []` —
  the kill path works and is bounded.
- A worker that exits immediately without sending: `EOFError` surfaced to the
  caller (not swallowed), `active_children() == []` — reaped on the exception
  path.
- The committed `test_spawn_timeout_reaps_worker` additionally asserts via
  `/proc` that no zombie child of the test process remains; the zombie check
  runs before `multiprocessing.active_children()` so it cannot be masked by
  that call's own reaping.

Minor wording observation (not a finding): `_reap`'s docstring says it "always
ends with a join attempt"; when the process has already exited, reaping is
performed by `is_alive()`'s internal poll rather than an explicit `join()`.
Functionally equivalent — no zombie or live worker can survive any path —
so this does not rise to a MINOR.

## 5. Behavior preservation — PASS (executed by this reviewer)

- Filtered cleanup tests at HEAD: **5 passed**.
- Standalone `python -m tests.evaluation_scenario`: exit 0, one JSON object,
  `classification == 'TECHNICAL_FIXTURE'`, `passed == True`, **exactly 17
  checks, all passed** — identical contract to the pre-repair scenario.
- `ls -d /tmp/seed-i30-scenario-* | wc -l` after the standalone run: **0**
  leftovers (pre-repair behavior: 1 per run). `/tmp` finished the review at
  1% utilization; all reviewer scratch (worktree, probes, outputs) removed.

## 6. Dispatch locks unchanged — PASS (executed by this reviewer)

- `git diff aa3582e..HEAD -- development/` is empty (see §1).
- `python -m development.evaluation run 0000…0000` →
  `{"error": "EMPIRICAL_DISPATCH_DISABLED", "verb": "run"}`, **exit 2**;
  same for `suite`.
- `Coordinator.dispatch()` raises
  `RuntimeError('FOUNDATION_ONLY_DISPATCH_DISABLED')` unconditionally.
- No registered B10 empirical experiment was executed by this review; the
  scenario remains a `TECHNICAL_FIXTURE` composition at minimal scale.

## Findings

- BLOCKER: 0
- MAJOR: 0
- MINOR: 0
- UNRESOLVED: 0

The repair is confined to the two authorized test files, implements owned-only
`TemporaryDirectory` cleanup with caller-owned preservation, guarantees
bounded terminate/join/kill reaping of spawned workers on every path, is
proven RED→GREEN by executed regression tests, preserves the scenario's
17-check `TECHNICAL_FIXTURE` behavior exactly, and leaves every production
dispatch lock byte- and behavior-identical. The historical I30 review record
is preserved verbatim; this review is a separate record for the repaired head.

**I30 TEMPORARY FIXTURE CLEANUP REPAIR: PASS**
**G1-G6: PRESERVED**
**G7 EMPIRICAL: PENDING / NOT AUTHORIZED**
**DESIGN AMENDMENT REQUIRED: NO**
