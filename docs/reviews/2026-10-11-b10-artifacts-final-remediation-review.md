# B10 I21–I25 Artifacts — Final Remediation (A–D) Independent Review

- **Date:** 2026-10-11
- **Scope:** complete diff `2940fae9fdd084a3e7017a230f531df97a57515f`
  (master) → final head `377f39a` on `seed-0.2-b10-impl-04-artifacts`,
  covering the original I21–I25 implementation, the F1–F5 remediation,
  and the owner's final remediation instruction (concerns A–D) with its
  two MINOR follow-ups.
- **Method:** fresh independent reviewer; tree materialized independently
  via `git archive`; all tests run from the independent tree; adversarial
  probes written by the reviewer (not the author's tests).

## Complete-diff review at 98cab3b (engineering e107b75)

- Verdict: **BLOCKER 0 · MAJOR 0 · MINOR 2 · UNRESOLVED 0**
- Concerns A–D verified **HOLD on all named surfaces**; F1–F5
  unregressed; dependency boundary intact.
- Complete evaluation suite from the independent tree: **622 passed**.
- Reviewer probes: 22 passed; the 2 failures are the MINOR evidence.
- Standalone scenarios: 7/7.
- Protected scope: `seed/**` NONE; dependency/lock/workflows NONE.

Reviewer probes of note: tampered `state_after` (engine's outcome for a
different action) → divergent with exactly engine-consistent fresh
outcomes; three unestablished-truth variants → incompatible; replay
`advance` accounting — total charged == total pulled == journal+events
sizes exactly; cold page on a >1 MiB history → explicit bounded error,
resumable to a lossless exactly-once traversal; receipt/index admission
refused at exact capacity with no file created; publish succeeds with
exactly receipt+index headroom (rename not double-charged); hardlinked
checkpoint rejected; inside-root symlink target still rejected; payload
write through a symlinked `checkpoints` dir blocked with foreign bytes
untouched.

### The two MINORs (both in re-execution secondary paths)

- **MINOR-1 (D surface):** `compatibility_report`'s initial-state check
  read the published checkpoint via a plain `Path.read_bytes`
  (no descriptor traversal, no digest check) — a symlinked `checkpoints`
  dir made it consume foreign bytes and report `initial_state: True`.
  The decisive re-execution gate was already descriptor-safe, so no
  false match was possible.
- **MINOR-2 (C surface):** `reexecute()` staged the fresh journal (and
  checkpoint copy) into `partials/<new_id>` before any budget admission
  covered those bytes.

## MINOR follow-ups and narrow re-review at 377f39a

- Fix commit `377f39a`: the compatibility check now reads the checkpoint
  through `_initial_checkpoint` (descriptor-relative, digest-validated);
  `reexecute()` admits `len(fresh journal) + len(checkpoint) + 1 run
  slot` before `staging.mkdir`. Regression tests
  (`tests/evaluation/test_review_minors.py`) are RED against the pre-fix
  code and GREEN after; the ledger's D wording was narrowed to match.
- Fresh narrow re-review (independent trees at both heads): both
  MINORs **CLOSED** with discriminating reviewer probes (fail at
  `98cab3b`, pass at `377f39a`, including the INCOMPLETE staging path);
  diff confirmed to touch only the two narrow hunks plus tests/ledger;
  regression set green (48 passed).
- Final verdict:

```text
BLOCKER 0
MAJOR 0
MINOR 0
UNRESOLVED 0

G1 PASS (preserved)
G2 PASS (preserved)
G3 PASS (preserved)
G4 PASS (preserved)
G5 PASS (preserved)
G6 PASS

DESIGN AMENDMENT REQUIRED: NO
```

## Author verification at the final code head (279c54f / 377f39a)

- Complete evaluation suite: **622 passed**.
- Full repository suite: **1,505 passed, 2 warnings**.
- Seven standalone scenarios: **7/7 PASS**.
- compileall OK; `git diff --check` OK; protected paths unchanged.

## Remaining limitations (unchanged, disclosed)

- Registered empirical dispatch stays locked (I30 + separate owner
  empirical authorization not satisfied); CLI `run`/`suite`/`reexecute`
  return `EMPIRICAL_DISPATCH_DISABLED`, exit 2.
- Scientific comparison covers the frozen plan's bound outputs; unbound
  output kinds remain outside the claim, as designed.
- Snapshot inspection keeps the owner-approved Option B exception:
  SQLite's native read-only open is preceded and followed by descriptor
  identity validation of the exact checkpoint file.

No PR was opened and nothing was merged under this instruction.
Publication remains owner-gated. I31 remains NOT AUTHORIZED; no
registered B10 empirical experiments were executed.
