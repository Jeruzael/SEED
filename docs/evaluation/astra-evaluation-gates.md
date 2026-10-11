# B10 Astra Evaluation (I26–I29) — Engineering Gate Ledger

Branch: `seed-0.2-b10-impl-05-astra`
Canonical branch point: `3406e1f2d5f757032befc9b91380ea7636b827fb`
(verified master; PR #29 merged `b3277bf`, PR #30 merged `3406e1f`,
all exact-head and master CI runs SUCCESS on linux-py311, linux-py313,
macos-py313).

Starting gates: G1–G6 PASS; I01–I25 COMPLETE / VERIFIED / CLOSED.
Scope: I26–I29 ENGINEERING ONLY (Phases M–N). I30 not in this branch.
I31 NOT AUTHORIZED; no B10 experiments executed; empirical dispatch
locked. Protected scope: `seed/**`, schema v7, dependencies/lock,
workflows — no changes.

Flow (observer only, strictly one direction):

```text
Immutable B10 artifacts → EvaluationReader → EvaluationService
→ GET-only /api/evaluation → bounded Astra client → observer UI
```

The dashboard never acquires an evaluator execution capability: no
run/suite/re-execute/modify/delete/import endpoints exist.

## Task records

(Entries are appended as each task completes, with exact test counts.)

## Task records

- **I26** — commits `178a004` (feat) + `ce37a9c`, `86f6d12`, `a34c5ea`,
  `fecda24` (validation/test-expectation fixes). `EvaluationService`
  delegates only to `EvaluationReader`; explicit enablement via
  `create_app(..., evaluation_root=...)` / `--evaluation-root` /
  `SEED_EVALUATION_ROOT`; absent or marker-less root → typed
  `503 evaluation_unavailable`, no directory creation, no organism-home
  fallback (verified: no `.seed-evaluation` appears in the SEED home).
  All eight GET routes implemented with raw-query validation
  (duplicates/unknowns rejected, run ID 32-hex, cursor ≤512 B, chunk
  bounded int, dotted registered metric/series names allowed).
  Mutation verbs return 403/404/405 even with a valid operator CSRF
  token. Corrupted receipts produce typed errors, never empty success.
- **I27** — commits `3c04fd2` (feat) + `a09862c`. `evaluation_support.js`:
  strict `parseEvaluationRoute` (exact signed-64 ordinals as strings —
  `9007199254740993` and `9223372036854775807` round-trip losslessly;
  duplicates/unknown selectors/path-like IDs/oversized cursors
  rejected), bounded client (2 s deadline, 1 MiB stream cap, 1,024 B
  error cap, fatal UTF-8, caller-abort isolation), chunk client
  (64 KiB). Compare selection state: `left` alone is valid selection,
  `right` requires `left`.
- **I28** — commit `5a4858a`. `views/evaluation.js` renders Execution
  and Scientific findings as separate headed cards; a COMPLETED run
  with a NEGATIVE finding shows both, with no universal PASS badge
  (Node DOM tests). Measurements show UNAVAILABLE as unavailable,
  never zero; replay lists recorded stages incl. unconfirmed;
  comparison names exact differing dimensions and never ranks runs;
  DOM/table caps enforced (≤20 rows/page, ≤200 points, ≤1,500
  elements checked by harness); hostile artifact strings render as
  text (no `innerHTML`/`eval` in the view). Service detail gained the
  stored `findings` array from the receipt-verified metrics file
  (plan I26 interface: finding details in detail responses).
- **I29** — commit `9135a2a`. Disposable fixture builder with the nine
  registered cases (incl. a genuine NEGATIVE produced by a
  preregistered threshold rule, and 21-run max-inventory paging
  20 + cursor + 1). Browser verification record:
  `docs/evaluation/browser-verification.md` — actual-browser items
  PENDING the owner's tunnel decision (browser VM cannot reach
  loopback servers; one tunnel was approved and verified, two were
  declined). Not marked passed on harness evidence.

## Author verification (fresh counts, this branch)

- Focused I26–I29 + dashboard regressions: dashboard suite
  **308 passed** (296 at base + 12 new).
- Complete evaluation suite: **631 passed** (unchanged code path).
- Full repository suite: **1,526 passed, 2 warnings** (clean tmpfs,
  serial; one earlier run showed 1 failure —
  `test_world_model_scenario` — with `database or disk is full`
  caused by accumulated pytest scratch filling the 512 MB /tmp tmpfs;
  the test passes standalone and in the clean rerun).
- Seven standalone regressions: **7/7 PASS**.
- Python compileall OK; JS syntax checks OK; `git diff --check` OK;
  changed files 18 (dashboard + tests + docs only); protected scope
  `seed/**`, workflows, dependencies/lock: NONE.
- Empirical dispatch lock untouched; no experiments executed.

## Browser acceptance (I29, actual browser)

- Executed 2026-10-12 against branch head `790c3bb` in the Muse
  Browser (Chromium) via owner-approved, secret-gated temporary
  tunnels (see `docs/evaluation/browser-verification.md` for the
  security handling and verified teardown).
- **9 of 11 items PASS**, including: separate Execution / Scientific
  findings headings with a visible NEGATIVE finding and no PASS badge
  anywhere; incompatible comparison naming `experiment` and
  `plan_digest` with no ranking language; the unavailable state with
  a fully working Overview; skip link, keyboard focus, captions;
  theme cycle; in-place Refresh; ≈145 DOM elements on the detail
  page.
- Item 3 PARTIAL: measurements browser-verified; replay events could
  not load through the tunnel (latency vs the enforced 2 s client
  deadline, observed verbatim in the UI) — covered by API + DOM
  tests, not claimed as browser-verified.
- Item 10 COULD NOT VERIFY: no viewport-resize control in the
  browser environment; wide-viewport layout and scroll-region
  structure observed instead.
