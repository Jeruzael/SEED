# B10 I21–I25 — Final Replay Budget Remediation Independent Review

- **Date:** 2026-10-11
- **Scope:** findings R-BUDGET-1 / R-BUDGET-2 against the replay budget
  path, two-tree method: defect head `377f39a` (docs `2e0d9ec`) vs
  repaired head fix `491ad63` (docs `0c0e410`) on
  `seed-0.2-b10-impl-04-artifacts`. Canonical base `2940fae`.
- **Method:** fresh independent reviewer; both trees materialized via
  `git archive`; reviewer-written probes (fixture helpers only reused);
  the earlier G6 PASS at `377f39a` is preserved as historical evidence
  in `2026-10-11-b10-artifacts-final-remediation-review.md` and is not
  reinterpreted by this review.

## Findings and verdict

```text
BLOCKER 0
MAJOR 0
MINOR 0
UNRESOLVED 0

R-BUDGET-1: CLOSED
R-BUDGET-2: CLOSED

G1 PASS (preserved)
G2 PASS (preserved)
G3 PASS (preserved)
G4 PASS (preserved)
G5 PASS (preserved)
G6 PASS — publication-eligible

DESIGN AMENDMENT REQUIRED: NO
```

## R-BUDGET-1 — unmetered single-record fallback: CLOSED

- Old tree: with a warm index (receipt 1,123 B; first-row line cost
  2,503 B) and the request budget shrunk to receipt + row_cost − 1,
  `events(limit=1)` returned the row through the unmetered retry
  instead of raising. A digest-corrupt second row silently truncated
  `events(limit=2)` to a 1-row page.
- New tree: receipt + row_cost − 1 raises with nothing returned;
  receipt-only raises on repeated calls (never a successful empty page
  with an unchanged cursor); receipt + row_cost exactly serves the
  row. Corrupt second row propagates `ContractError`; corrupt first
  row raises. `events()` catches only `replay.BudgetError`, re-raises
  it on an empty page, and returns a bounded partial page (cursor at
  the unserved row) only when rows were already served.

## R-BUDGET-2 — accounting after physical reads: CLOSED

- Old tree: a cold request on the oversized-history artifact performed
  **1,102,368 physical bytes against the 1,048,576 budget**
  (instrumented `os.pread` + `Path.read_bytes`); a raising charge
  callback left the old scan with journal offset 52,662 at 0 bytes
  charged (state advanced before charging).
- New tree: the same cold request performs **exactly 1,048,576**
  physical bytes — never over. `RequestBudget.pull()` caps each
  streaming read at the remaining allowance before `os.pread`;
  known-length row lines are preflighted with `admit(spans)`; offsets
  advance only after a successful charge. A 256 KiB-budget traversal
  delivers 24/24 rows exactly once with worst per-request physical
  reads equal to the cap. Incremental builds in 4,096 B budgets keep
  pulled == charged at every step and reproduce the unbounded index
  exactly.
- Typed distinction: `replay.BudgetError` (a `ContractError` subclass;
  external error surface unchanged). An expired-deadline budget makes
  `read_rows`/`advance` raise `BudgetError` with zero physical reads;
  corruption raises plain `ContractError`, not `BudgetError`.

## Regression and preservation

- Reviewer probes: 6/6 on the new tree (5 discriminating failures on
  the old tree; one non-discriminating probe disclosed as such).
- Focused replay/reader/remediation/adversarial/dependency/CLI set:
  54 passed. Complete evaluation suite from the independent new tree:
  **631 passed**.
- Diff scope `2e0d9ec..0c0e410`: only `reader.py`, `replay.py`, the gate
  ledger and three test files. F1–F5 and A–D remediation code
  untouched. Protected scope (`seed/**`, dependencies, workflows):
  none. Empirical dispatch remains locked (exit 2,
  `EMPIRICAL_DISPATCH_DISABLED`). No PR opened; nothing merged; I31
  not executed.

## Author verification at the repaired head (491ad63)

Focused sets 52 passed; complete evaluation suite **631 passed**; full
repository suite **1,514 passed, 2 warnings**; seven standalone
scenarios 7/7 PASS; compileall and `git diff --check` clean.

**Explicit statement:** the original unmetered single-record fallback
has been eliminated; no replay read path in the repaired head bypasses
the request budget, including the first returned record.
