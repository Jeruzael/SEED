# Fresh Independent Narrow Review — SEED B10 MAJOR-1 (Aggregate Astra HTTP Request Resource Budgets)

- **Reviewer:** berg, acting as fresh independent narrow reviewer (did not author the work under review)
- **Review date:** 2026-10-12
- **Branch:** `seed-0.2-b10-impl-05-astra`
- **Old (defective) head:** `898ddae4dcfec7fbc2f814358c03f6c220ac0be1`
- **New (remediated) head:** `afc936eb685e6bb64c44166858066dca114b897d` (commits `2eb9b28` tests-only, `afc936e` fix; local only, not pushed at review time)
- **Canonical base (master):** `3406e1f2d5f757032befc9b91380ea7636b827fb`
- **Review tree:** independent clone at `/tmp/seed-review-major1` (`git clone --no-hardlinks`, checkouts verified clean at each head). All suites and probes ran in the review tree, never in the author's working tree. Imports verified to resolve to the review tree (`dashboard`, `development`, `seed` `__file__` all under `/tmp/seed-review-major1`).
- **Environment:** Python 3.12.3 (`~/workspace/SEED/.venv/bin/python`). The VM's 512 MB `/tmp` tmpfs filled once during setup and produced the known bogus SQLite "database or disk is full" fixture errors; after cleaning pytest scratch the identical runs proceeded normally. This environmental artifact is disclosed, not counted as a finding.
- **Scope of verdict:** MAJOR-1 only — aggregate per-HTTP-request resource budgets (1 MiB physical reads, 1 MiB serialized response, one 2 s deadline, concurrent-request isolation) in the Astra Evaluation observer. This review does not approve merging PR #31; publication remains owner-gated. I30 not started; I31 NOT AUTHORIZED; no B10 experiment was executed.

## 1. Defect reproduction on the old head (898ddae) — reviewer's own run

Method: in the review tree at `898ddae`, the ONLY addition was the new test file copied from `afc936e` (`tests/dashboard/test_evaluation_http_budget.py`). Result: **9 failed, 1 passed** — the same shape as the author's RED claim, with the reviewer's own measured values identical to the claimed ones:

| Test | Reviewer-measured result at 898ddae |
| --- | --- |
| Detail, calibrated 5,000 B limit | HTTP 200 while physically reading **7,160 bytes** (per-call aggregates 3,222 B fit individually; the request total did not) |
| Detail, large valid fixture | **409** — the service's generic 64 KiB `strict_json` cap rejects a valid 256 KiB metrics file before budgets are even reached (latent defect, see §5) |
| Compare, large valid fixtures | HTTP 200 while physically reading **1,268,594 bytes** vs the 1,048,576 ceiling |
| Boundary compare (1 MiB − 1 fabricated) | **409** (trips the same 64 KiB parse cap on the way through) |
| Nested-call budget identity | One HTTP detail request charged **3 distinct** `RequestBudget` objects (created 3) |
| File-growth race | Physically read **102,344 bytes** against a 4,096-byte allowance (stat-then-`read_bytes` over-read) |
| Concurrency interleave | Request A charged **4 distinct budgets** (its own, B's, and its later resets) — shared mutable budget state on the shared reader confirmed |
| Aggregate deadline | Work spread across nested calls past one 0.6 s deadline returned **HTTP 200** (each call had restarted the clock) |
| Serialized response ceiling | A **1,048,577-byte** serialized body returned HTTP 200 (no ceiling existed) |
| Genuine-fixture guard | Passed (small fixture fits under any accounting) |

**MAJOR-1 defect CONFIRMED as real and exploitable exactly as described**: budgets and deadlines applied per internal reader call, not per HTTP request, and concurrent requests contaminated each other's budget state through the shared reader instance.

## 2. Fix verification on the new head (afc936e) — reviewer's own runs

- New suite `tests/dashboard/test_evaluation_http_budget.py`: **10 passed**.
- `tests/dashboard`: **318 passed** (308 pre-existing + 10 new).
- `tests/evaluation`: **631 passed**.
- Dashboard + evaluation total: **949 passed** — matches the author's claim exactly.
- Full repository (clean serial run in the review tree): **1,548 passed, 2 warnings** — the author's claimed 1,536 plus this review's 12 probe tests that exist only in the review tree (1,536 + 12 = 1,548, exact). Disclosure: a first full-repo attempt was contaminated by the reviewer (a `/tmp/pytest-of-root` cleanup deleted the running suite's own tmp root mid-run, producing 1,174 `FileNotFoundError` setup errors and 1 consequent failure, all in the reviewer's scratch management, none in the code); the clean rerun above is the evidence of record.
- The four G6 contract files run individually: `test_replay_budget.py`, `test_replay_budget_escape.py`, `test_reader.py`, `test_remediation.py` — **29 passed**.

## 3. G6 preservation (reader.py changed; replay.py untouched) — EXPLICIT VERDICT: PRESERVED

`development/evaluation/replay.py` is byte-untouched by the fix (0-line diff), so `RequestBudget` semantics, the resumable `ReplayIndex`, and row materialization are inherently unchanged. The reader-side G6 surfaces were re-verified by the reviewer with new probes (reviewer-authored, run only in the review tree, 5/5 passed):

1. **Resumable lossless paging**: a genuine published 24-frame history (journal + events > 1 MiB) traversed via standalone `reader.events()` across repeated per-call budget interruptions (≥1 `BudgetError` observed) delivered **every row exactly once, in order**, resuming the shared index instead of restarting it.
2. **Corruption ≠ exhaustion**: after corrupting one journal byte, traversal raised `ContractError` that is **not** a `BudgetError` — invalid evidence still propagates as corruption, never relabeled as resource exhaustion, including mid-traversal.
3. **Typed error taxonomy intact**: `BudgetError` remains a subclass of `ContractError`.
4. **Partial-page semantics**: unchanged code path in `reader.events()` (the author's suite's partial-page and cursor-progress tests pass inside the 631; the reviewer's traversal probe exercised the same resume machinery end-to-end).
5. **Chunk-verification lifecycle**: `detail()` reports `chunk_verification: none` before any chunk read and `chunk_verified` after a verified `chunk()` read, exactly as before.
6. **Fingerprint invalidation**: fingerprint computation and the stale/`verification_pending` logic are unchanged except that the swap is now performed under the cache lock; the evaluation suite's fingerprint/invalidation tests pass.

## 4. Reviewer's independent probes on the new head (7/7 passed)

Reviewer-authored probes at the service/HTTP level (distinct from the author's tests; fixture sizes differ from the author's where applicable):

1. **Three-way accounting equality — detail**: physical bytes counted at `Path.read_bytes`/`os.pread`/`os.read` == session budget consumption == exact on-disk sum of the files a detail request should touch. Genuine fixture: **3,222 bytes** by all three measures (receipt 1,123 + manifest 750 + metrics 471 + chunks.json 878, each read exactly once). Any unmetered read or double read would break the equality; none did.
2. **Three-way accounting equality — compare** (reviewer's own fixture parameters: 40,000-byte metrics, 90 MiB dummy chunk index): physical == consumed == exact two-run file sum, and ≤ 1 MiB.
3. **Concurrency stress**: 24 threads × 10 iterations of mixed `detail`/`events`/`measurements`/`runs` against ONE shared service instance: every result byte-identical to the single-threaded baseline, zero exceptions.
4. **Error labeling**: missing run → 404 `not_found`; budget-starved request (calibrated 3,000 B) → 429 `resource_limit`; one flipped byte in stored metrics → 409 `artifact_error`. Resource exhaustion is never mislabeled as corruption, and vice versa.
5. **Session release**: after a successful service call, after a `resource_limit` failure, and after a subsequent successful call, the reader's session context variable is `None` in the calling thread — no session (or its consumption) leaks into the next request on success OR exception paths; the request after a failure runs on a fresh full budget.
6. **Forgery rejection at HTTP level**: flipping one byte in a fabricated run's `metrics.json` → files-endpoint chunk request **409**, detail request **409** (chunk-hash verification performed on the verified-file path, including on bytes reused from the session raw cache — the hash loop runs on both assembly paths in the code and the forgery is caught behaviorally).
7. **Response ceiling (runs endpoint, reviewer's own payloads)**: serialized body of exactly **1,048,576** bytes → 200 with `len(content) == 1,048,576`; **1,048,577** bytes → 429 `resource_limit` with a short error envelope (≤ 1 MiB), never a truncated payload.

## 5. Diff audit (898ddae..afc936e)

Changed files (complete list): `tests/dashboard/test_evaluation_http_budget.py` (+589, commit `2eb9b28`), `dashboard/api/evaluation.py`, `dashboard/services/evaluation.py`, `development/evaluation/reader.py` (commit `afc936e`). Full diff read line by line.

- **Protected scope: EMPTY** — `seed/**`, `.github/**`, `requirements*`/lock: 0-line diff (also 0-line against master `3406e1f`). `development/evaluation/replay.py`: untouched. `development/evaluation/cli.py` (empirical dispatch lock): untouched. No schema change. **No new dependencies** (added imports are stdlib `contextvars`/`threading`/`contextlib` and `JSONResponse` from the already-used FastAPI).
- **No new endpoints**: the route set and all request validation (including the event-key grammar) are byte-identical; the API diff only wraps existing returns in `_respond()` and adds the files-route length assertion.
- **Scientific comparison logic unchanged**: `compare()`'s dimension extraction and `compatible` computation are untouched; only `_stored_file()` internals changed (receipt passed in / `verified_file()` + parse cap). MAJOR-2 (comparison compatibility correctness) was **not** addressed, as instructed.
- **Both pre-existing MINORs untouched**: the client/server ordinal-grammar divergence (API `_event_key` unchanged; `dashboard/static/**` 0-line diff) and the stale "Untrusted artifact preview" documentation label (no docs changed in either commit) remain exactly as they were, tracked for their separate repairs.
- **Enabling correction (disclosed in the fix and confirmed necessary)**: `_stored_file` previously parsed stored files with the generic 64 KiB `strict_json` message cap, so any valid published artifact whose manifest/metrics exceeded 64 KiB failed detail/compare with 409 — the reviewer reproduced this at the old head. The fix parses against the file's own receipt-verified length. This widens only cases that previously errored; no previously-successful response changes content.
- **Reader accounting audit**: every physical read in `reader.py` now flows through an admitted+charged path — `_read` (descriptor fstat admission, pread capped at the admitted length), `verified_file` (per-chunk admit + capped pread + charge), `chunk` (admit + pread capped at the admitted expected length, strict length equality), and replay build/row reads (session budget passed through). No `read_bytes` or uncapped read remains in the reader; the service/API layers perform no file reads of their own. `os.stat`/`scandir` metadata operations remain uncharged, as before (they transfer no content bytes).
- **Deadline semantics**: the session (and its deadline) starts when the service begins processing the validated request; all artifact I/O happens inside it. API-layer validation before that point is pure bounded CPU work (regexes, the 512-byte cursor cap) with no I/O, so no un-deadlined read path exists. The server detects expiry at every admission/charge and never returns a successful response after it (author's deadline test + this review's §1/§2 runs).
- **Session/cache hygiene**: ambient sessions are installed via `ContextVar` token and reset in a `finally` block (verified on success and exception paths by probe 5). Session caches (receipts, chunk indexes, raw reads, verified files) are per-request and released with the session; the only cross-request state is the pre-existing replay-index cache (now per-run `RLock`-guarded), fingerprint map and chunk-verified set (now under a cache lock) — no budget or deadline state is shared. Within one request, `verified_file` may serve bytes read earlier in the same session; those bytes are chunk-hash-verified before serving, so a mid-request on-disk change yields either the consistent verified snapshot or a 409, never unverified content. Cross-request staleness is impossible (caches die with the session).

## 6. Findings

**BLOCKER 0 / MAJOR 0 / MINOR 2 / UNRESOLVED 0**

Both MINORs are non-blocking observations about the fix itself; neither affects MAJOR-1 closure:

- **MINOR-1 (behavior delta, beneficial)**: `reader._read` on a missing file now raises typed `ContractError` where the old code leaked an uncaught `FileNotFoundError` (its `getsize` failure path fell through to `read_bytes`). The error surface becomes more consistent with the reader contract; the full evaluation suite (631) passes, so no caller depended on the leaked exception. Noted for the record; no action required.
- **MINOR-2 (hygiene)**: a transient (non-ambient) session created by a standalone reader call remains installed in the calling thread's context after the call returns, until the next `_begin()` replaces it; its read caches (bounded by one call's ≤ 1 MiB) linger per-thread. The HTTP path always uses ambient sessions, which are token-reset, so this affects only direct reader API users and is correctness-neutral. Noted; no action required.

## 7. Verdict

**BLOCKER 0 / MAJOR 0 / MINOR 2 / UNRESOLVED 0**

**MAJOR-1: CLOSED by this repair.** The defect was independently reproduced at `898ddae` with the reviewer's own measurements (compare physically reading 1,268,594 bytes under HTTP 200; 3–4 distinct budgets charged inside single requests; aggregate deadline evaded; no response ceiling). At `afc936e` the aggregate contract holds under the author's suite (10/10), the full dashboard+evaluation suites (949 passed), the G6 contract files (29/29), and the reviewer's seven independent probes — including exact three-way byte accounting (physical == charged == on-disk sum) proving no unmetered or duplicated read remains in the serving paths, and a 24-thread stress proving per-request isolation on the shared service.

**G6 PRESERVATION: CONFIRMED** (see §3). `replay.py` untouched; reader contracts — resumable index progress, lossless inventory, partial-page-on-budget semantics, typed `BudgetError` vs corruption, verification labels, fingerprint invalidation — all hold.

**PUBLICATION NOTE:** this review verifies the local head `afc936e` only. PR #31 still points at `898ddae`; updating it requires pushing `afc936e` to the PR branch and obtaining fresh PR-head CI success (Linux Python 3.11, Linux Python 3.13, macOS Python 3.13) at that exact head — the green CI at `898ddae` does not verify the new head. **This review does not approve merging**, and merging remains owner-gated. The two pre-existing MINORs and MAJOR-2 remain open and tracked separately; no 0/0/0/0 claim for I26–I29 overall is made here.

**Full-repository evidence:** 1,548 passed / 2 warnings in the review tree (author's 1,536 + 12 reviewer probes), matching the author's full-suite claim with no remainder.

**DESIGN AMENDMENT REQUIRED: NO**

# Follow-up note (2026-10-12, appended; verdict above unchanged)

A final deadline verification pass was executed after this review.
The remaining end-to-end server-processing deadline gap (post-read
processing and response construction were unchecked) was
reproduced at `3364ace`, repaired at `fefce84`, and verified by a
fresh independent narrow review: BLOCKER 0 / MAJOR 0 / MINOR 1 /
UNRESOLVED 0 — MAJOR-1 DEADLINE CONTRACT COMPLETE — G6
PRESERVATION CONFIRMED — DESIGN AMENDMENT REQUIRED: NO. Full
record:
`docs/reviews/2026-10-12-b10-astra-major1-deadline-review.md` and
the follow-up section appended to
`docs/reviews/2026-10-12-b10-astra-major1-remediation.md`.
