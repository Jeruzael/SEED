# Fresh Independent Review — SEED B10 I26–I29 (Astra Evaluation UI, Phases M–N)

- **Reviewer:** berg, acting as fresh independent reviewer (did not author the work under review)
- **Review date:** 2026-10-12
- **Branch:** `seed-0.2-b10-impl-05-astra`
- **Reviewed head:** `fd7c064c30d7794a26ce8ac0a436b9c57c40c88d`
- **Canonical base (master):** `3406e1f2d5f757032befc9b91380ea7636b827fb`
- **Review tree:** independent clone at `/tmp/seed-review-i29` (`git clone --no-hardlinks`, detached checkout at `fd7c064`, verified clean). All suites and probes ran in the review tree, never in the author's working tree. Imports verified to resolve to the review tree (`dashboard`, `development`, `seed` `__file__` all under `/tmp/seed-review-i29`).
- **Environment:** Python 3.12.3 (`~/workspace/SEED/.venv/bin/python`), Node v24.20.0.
- **Scope of verdict:** engineering review only. No B10 empirical experiment was executed by the author or by this review. I31 remains NOT AUTHORIZED. This review does not create, merge, or approve any PR; publication remains owner-gated.

## 1. Scope and diff verification

Complete diff `3406e1f..fd7c064`: **18 files, +2010/−11**, 13 commits
(`656f7a1`, `178a004`, `ce37a9c`, `86f6d12`, `a34c5ea`, `fecda24`, `3c04fd2`,
`a09862c`, `5a4858a`, `9135a2a`, `790c3bb`, `c9a0a46`, `6495c67`, `fd7c064`).

**Protected scope: EMPTY diff — confirmed by direct measurement** for
`seed/**`, `.github/**`, `requirements*.txt`, and `development/**`
(includes the empirical dispatch lock in `development/evaluation/cli.py`,
byte-untouched). All changes are confined to `dashboard/**`,
`tests/dashboard/**`, and `docs/**`. The four non-ledger documentation
edits are status-string synchronization only (I26–I29 IN PROGRESS,
I30 NOT STARTED, I31 NOT AUTHORIZED); they do not overclaim closure.

## 2. Methods

1. Read the complete implementation: `dashboard/services/evaluation.py`,
   `dashboard/api/evaluation.py`, `dashboard/__main__.py` / `app.py`
   wiring, `dashboard/static/evaluation_support.js`,
   `dashboard/static/views/evaluation.js`, plus the helpers it delegates
   safety to (`api.js` `el`/`table`/`parseEvidence`, `evidence.js`
   `raw`/`details`/`route`/`parseRoute`), the fixture builder
   `tests/dashboard/evaluation_fixture.py`, and the author's three test
   files in full.
2. Ran the dashboard suite, the evaluation suite, and the full
   repository suite in the independent tree (Section 3), plus the seven
   standalone scenario scripts the way prior batches ran them
   (`python -m tests.<name>_scenario`).
3. Wrote and executed 23 reviewer API/service probes and 7 reviewer
   Node client probes (Section 4), including counterfactual and forgery
   probes designed to prove properties rather than reproduce recorded
   output.
4. Cross-checked `docs/evaluation/browser-verification.md` (historical
   tunnel record + both addenda) and
   `docs/evaluation/astra-evaluation-gates.md` against the code and
   against each other, including `git log -S` over full history for one
   quoted UI label (MINOR-2).

## 3. Suite results (reviewer's own runs, independent tree)

| Suite | Reviewer result | Author claim | Match |
|---|---|---|---|
| Dashboard (`pytest tests/dashboard`) | **308 passed, 2 warnings** (125.10 s) | 308 passed | ✓ exact |
| Evaluation (`pytest tests/evaluation`) | **630 passed, 1 failed** on overlay-disk TMPDIR — see note; **631/631 green** in the tmpfs full run | 631 passed | ✓ with environmental note |
| Full repository (`pytest`, serial, TMPDIR=/tmp) | **1,526 passed, 2 warnings** (235.99 s) | 1,526 passed, 2 warnings | ✓ exact |
| Standalone scenarios (baseline, prediction_error, world_model, curiosity, semantic, self_model, decision) | **7/7 exit 0** with complete JSON outputs | 7/7 PASS | ✓ |

**Environmental note on the single evaluation-suite failure.**
`tests/evaluation/test_frozen.py::test_all_frozen_tables_and_db_bytes_equal`
failed in the dedicated evaluation run with TMPDIR on this VM's slow
overlay disk: the test spawns a worker that builds a 200-row fixture and
fails at `tests/evaluation/test_completed_fixture.py:69` when the worker
misses a hard 90 s pipe deadline (`parent.poll(90)`). It is a deadline
expiry, not a data assertion. Characterization:

- The identical test **passed standalone in 30.03 s** with TMPDIR on
  tmpfs, and passed inside the full-repository tmpfs run (which contains
  all 631 evaluation tests).
- The I26–I29 diff does not touch `development/**` or
  `tests/evaluation/**` at all (verified empty), so the branch cannot
  have regressed this test; the same class of overlay-disk timing flake
  was recorded in earlier batches on this VM.

I therefore record the evaluation suite as 631/631 in a suitable
environment, with the flake and its mechanism disclosed rather than
silently absorbed.

## 4. Reviewer adversarial probes (all executed in the review tree)

### API / service probes — 23/23 PASS

- **P1 Mutation verbs (operator mode, valid CSRF + Origin):** POST, PUT,
  DELETE, PATCH against all 12 evaluation route shapes (runs, detail,
  measurements, events, event, curve, compare, files, plus invented
  `/run`, `/suite`, `/reexecute`, `/import`) → every response in
  {403, 404, 405}; none executed. (INFO: HEAD and OPTIONS also return
  405; no read or write surface beyond GET exists.)
- **P2 Cursor bound:** 513-byte cursor → 422; 512-byte cursor passes
  validation and reaches the reader, which rejects the forged value with
  a typed 409; multibyte cursors measured in UTF-8 bytes (257×`é` =
  514 B → 422; 256×`é` = 512 B → passes validation).
- **P3 Strict queries:** any query parameter on the detail route → 422;
  duplicate `left` key on compare → 422. (Author tests additionally
  cover duplicates/unknowns on the list route.)
- **P4 No creation, no fallback:** `EvaluationService.from_root` on (a)
  an empty directory, (b) a directory containing `.seed-evaluation`
  without the ownership marker, (c) a nonexistent path, and (d) a real
  organism home → unavailable in all four cases, and **nothing was
  created** (no `.seed-evaluation` appeared anywhere). This matters
  because `EvaluationRoot.create` (paths.py:235–252) *would* create a
  marked root if called on a fresh directory; the service's marker
  pre-check (`dashboard/services/evaluation.py:28`) is what guarantees
  the read-only property, and it holds under probing.
- **P5 Forged finding:** in a copy of the `complete-negative` fixture,
  `metrics.json` was edited on disk NEGATIVE → POSITIVE. Detail request
  → **409 typed error; the forged POSITIVE was never served.** Receipt
  verification catches artifact tampering before any stored value is
  rendered.
- **P6 Genuine NEGATIVE (counterfactual pair):**
  - P6a: via the API, the `complete-negative` run's stored finding is
    `NEGATIVE` with reason `PREREGISTERED_THRESHOLD_RULE`, and the
    measured row `prediction.numeric-mae` has value **0** (state
    MEASURED) against the preregistered floor of 1 (direction `ge`).
  - P6b: rebuilding the same fixture machinery with the floor lowered
    to 0 flips the derived finding to **POSITIVE**. The label is
    computed by the real derivation (`artifacts.derive_scientific_outputs`
    over the frozen plan), not hard-coded in the fixture.
- **P8 Event-key grammar (see MINOR-1):** 19-digit ordinal → 422;
  10-digit ordinal passes API validation (typed 409 from the reader);
  leading-zero ordinal `01` → **200**, serving ordinal 1's event.
- **P9 Compare honesty:** API compare of the `incompatible-plans`
  fixture → `compatible: false`; dimensions name `experiment` and
  `plan_digest` as differing; payload contains no better/worse/
  equivalent/verdict/rank language anywhere.
- **P9b Equal plan digest is not compatibility:** two runs published
  with the *same* plan (identical `plan_digest`, `match: true`) but
  different experiment versions → `compatible: false`, with
  `experiment` the differing dimension.
- **P12 Unknown run:** `f`×32 → 404 on detail, measurements, events,
  and files routes.
- **Max-ids:** both source IDs `9223372036854775807` and
  `9007199254740993` appear verbatim in the service events payload for
  the `max-ids` fixture.

### Client probes (Node, real modules) — 7/7 PASS

- Constants exact: timeout 2000 ms, response cap 1 MiB, chunk cap
  64 KiB, error cap 1024 B.
- `parseEvaluationRoute` preserves ordinals `9223372036854775807` and
  `9007199254740993` as exact strings; rejects `9223372036854775808`,
  negatives, leading zeros, floats, exponents, blanks.
- `parseEvidence` (api.js) rewrites out-of-safe-range integers to exact
  decimal strings end-to-end (`9223372036854775807`,
  `9007199254740993`, `-9223372036854775808`), leaves safe integers and
  floats numeric, and does not rewrite digit sequences inside strings.
  This closes the losslessness chain: server JSON → client parse →
  view `String(data.key[2])` / route parameter.
- Static sweep: no `innerHTML`, `outerHTML`, `insertAdjacentHTML`,
  `eval(`, `document.write`, or `new Function` in the new/changed JS;
  `el()` renders via `textContent`, `table()` via `createTextNode`,
  `raw()` via `JSON.stringify` into a `pre` — artifact strings are
  rendered as text.

### Dispatch lock (live CLI)

`python -m development.evaluation run|suite|reexecute <run_id>` in the
review tree → each prints `{"error": "EMPIRICAL_DISPATCH_DISABLED", …}`
and exits **2**. The lock code is outside the branch diff entirely.
Server binding: `server_options` hard-codes `host: 127.0.0.1`; the new
`--evaluation-root` flag adds no `--host` option.

### Error-mapping refinement (verified behavior, not a finding)

The review brief summarized the contract as "ReaderError → 404".
The implementation is more precise (`services/evaluation.py:54–67`):
ReaderError with reason `RECEIPT_UNAVAILABLE` or `ARTIFACT_NOT_PUBLISHED`
→ 404 `not_found`; other ReaderError → 409 `artifact_error`;
ContractError → 409. Probes confirm both halves (unknown run → 404;
forged/corrupt artifact → 409). Unavailable service → 503
`evaluation_unavailable`, confirmed by P4 and the author's tests.

## 5. Contract verification summary

- **Bounds:** page 20 (`_limit`, api:43), cursor 512 B UTF-8 (`_cursor`,
  api:53), chunk 64 KiB (service `_CHUNK`, api Content-Length checks,
  client cap), response 1 MiB (reader request budget + client cap),
  deadline 2 s (client), detail metadata 912 KiB (reader
  `DETAIL_BYTES = 912*1024`, reader.py:35), snapshot steps 100,000
  (reader `SQLITE_STEPS`, reader.py:37), run index 60 (publication
  layer, integrity.py:236), compare = 2 runs with 3 named dimensions,
  chart 4 series × 200 points (view slices + reader contract), UI rows
  20 / DOM cap enforced by construction and the author's DOM harness.
  Files served as `application/octet-stream` attachments only.
- **View honesty:** separate `Execution` and `Scientific findings`
  cards; findings rendered only from the stored detail payload;
  `null`/`undefined` measurements render `Unavailable`, never 0;
  replay panels state "Replay never invokes cognition" / "Recorded
  replay only; no cognition is invoked."; compare shows Match/Differs
  with an explicit no-ranking notice and never classifies; no code path
  synthesizes a universal PASS badge.
- **Fixture builder:** refuses unregistered cases, non-empty
  destinations, and state-like destinations (author test + code read);
  damaged cases are labeled technical fixtures; the `partial` case's
  stored finding is INCONCLUSIVE (author fixture test, green in my
  dashboard run).

## 6. Browser-acceptance records

- The historical tunnel-based record in
  `docs/evaluation/browser-verification.md` is **preserved verbatim**
  at the head of the file (tested commit `790c3bb`, 9 of 11 PASS,
  item 3 PARTIAL, item 10 COULD NOT VERIFY, teardown described). The
  2026-10-12 local macOS acceptance is a **separately headed
  addendum**, as is the earlier macOS `/tmp` pitfall note.
- The addendum's technical claims are consistent with the code I
  reviewed: the 2,000 ms deadline it cites is the enforced client
  constant; the replay/event strings it quotes match
  `views/evaluation.js`; the run ID, digests, and finding it reports
  match the `complete-negative` fixture I rebuilt independently.
- Provenance check: `git diff 6495c67..fd7c064` touches **only** the
  two docs files, so the dashboard code exercised on the Mac at
  `6495c67` is byte-identical to the code at the reviewed head.
- The ledger (`astra-evaluation-gates.md`) agrees with the addendum
  (11 of 11 after local acceptance, historical 9/11 retained) and
  correctly names this independent review as the next gate and the
  engineering PR as owner-gated and not created. One imprecision
  found — see MINOR-2.

## 7. Findings

### BLOCKER — none.

### MAJOR — none.

### MINOR-1 — Client/server event-key grammar divergence
`dashboard/api/evaluation.py:21` (`_DIGITS = ^[0-9]{1,10}$`, used by
`_event_key` at :62–70) versus `dashboard/static/evaluation_support.js`
(ordinal `^(0|[1-9][0-9]{0,18})$` + BigInt ≤ 2^63−1):

- The API rejects event ordinals above 9,999,999,999 that the client
  router accepts and preserves losslessly (probe P8: 19-digit ordinal
  → 422). Such an event would list in the UI but its detail link would
  be unservable.
- The API accepts leading-zero ordinals the client rejects (probe P8:
  `measured:default:01:update` → 200, serving ordinal 1), so the same
  recorded event is addressable under a non-canonical key the UI
  itself would never produce.

Impact today is theoretical: real ordinals are bounded by the
100,000 snapshot-step limit, far below 10 digits, and the reader
resolves by parsed tuple, so no integrity or honesty property is
violated. It is still a genuine divergence between two components
that each claim strict validation of the same grammar; the two
grammars should be reconciled (preferably the client's) in a
follow-up. Non-blocking.

### MINOR-2 — Browser-verification record quotes a UI label that does not exist
`docs/evaluation/browser-verification.md` item 4 (historical tunnel
run) describes the file-chunk preview as an **"Untrusted artifact
preview"**. `git log -S "Untrusted artifact"` over the full repository
history shows that string has **never existed in the dashboard
code**; the view renders the chunk in a plain `pre` element via text
helpers (`views/evaluation.js`, files panel). The substantive claim
in the same sentence — JSON rendered as literal text, not HTML, with
the chunk byte count shown — is true and verified against the code.
Only the quoted label is unsupported by evidence. The record should
be corrected (or the quote marks removed) in the closure
documentation pass. Non-blocking; the historical record otherwise
remains accurate and is preserved.

### UNRESOLVED — none.

### Observations (not counted as findings)

- `services/evaluation.py:93` (`metrics['findings']` in `detail()`)
  and `:169` (`stored['produced']` in `compare()`) index stored JSON
  without a KeyError guard inside `_guarded`. I could not construct a
  reachable failure: every artifact reaching those lines has passed
  receipt verification over the exact bytes, and the publisher only
  writes the guaranteed structure (probe P5: tampering → 409 before
  any such read). A defensive `.get` would be harmless hardening, not
  a correctness fix.
- The view's `readStoredJson` caps stored-JSON reads at 8 chunks
  (512 KiB) while the server detail bound is 912 KiB; a hypothetical
  `index.json` between those sizes would fail client-side parsing
  instead of rendering. Curve metadata is in practice bounded by the
  4-series × 200-point contract, far below either limit.
- The author's own tests are substantive, not self-referential: the
  operator-mode mutation test uses a real CSRF token; the fixture
  test asserts stored findings from disk; the asset tests execute the
  real ES modules under Node. My P6b counterfactual independently
  confirms the fixture NEGATIVE is derived, addressing the standing
  principle that a test must prove the property, not reproduce a
  recording.

## 8. Gate assessment

- **Dashboard / observer contract:** PASS. GET-only surface verified
  including operator mode with valid CSRF; loopback-only binding;
  no execution endpoints; optional read-only service with no root
  creation and no organism-home fallback; dispatch lock intact and
  untouched by the diff; protected scope untouched.
- **Scientific honesty rules:** PASS. Execution and findings are
  separate concepts in service payload, view structure, and browser
  evidence; findings are stored, receipt-verified, and never
  recomputed or forged past verification (P5); UNAVAILABLE is never
  rendered as 0; exploratory/diagnostic data is not promoted to
  findings; compare names differing dimensions, requires all three to
  match (P9b), and never ranks or classifies; replay is recorded-only
  and says so in the UI.
- **I29 browser acceptance:** COMPLETE as recorded — historical 9/11
  preserved, local macOS addendum separately identified and
  consistent with the code; the one imprecision is MINOR-2.
- **Empirical boundary:** preserved. No experiment executed; CLI
  dispatch still refuses with `EMPIRICAL_DISPATCH_DISABLED` (exit 2);
  I30 not implemented; I31 not authorized.

## 9. Verdict

**BLOCKER 0 / MAJOR 0 / MINOR 2 / UNRESOLVED 0**

**PUBLICATION-ELIGIBLE: YES** — for the owner-gated engineering PR,
subject to the standing requirement of exact PR-head CI success on
Linux Python 3.11, Linux Python 3.13, and macOS Python 3.13 before
any merge. Both MINORs are non-blocking: MINOR-1 is unreachable with
real ordinal ranges and violates no integrity property; MINOR-2 is a
documentation-label correction suitable for the closure pass.
Neither requires a code-behavior change to cognition, schema, or any
approved scientific rule.

**DESIGN AMENDMENT REQUIRED: NO**
