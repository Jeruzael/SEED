# Fresh Independent Narrow Review — SEED B10 MAJOR-1 Final Deadline Verification

- **Reviewer:** berg, acting as fresh independent narrow reviewer (did not author the work under review)
- **Review date:** 2026-10-12
- **Previous head (gap present):** `3364ace6cfe545d8ad7ad49b44a6318ea71bac2b` — PR #31's published head; already contains the MAJOR-1 aggregate-budget remediation (`afc936e`, independently reviewed: MAJOR-1 CLOSED, `docs/reviews/2026-10-12-b10-astra-major1-review.md`)
- **Reviewed head (this follow-up):** `fefce843b5be7492bb2cc8d3fc3de4019b8905a5` — commits `6224e4f` (tests) + `fefce84` (fix) on top of `3364ace`
- **Canonical base (master):** `3406e1f2d5f757032befc9b91380ea7636b827fb`
- **Review tree:** independent clone at `/tmp/seed-review-deadline` (`git clone --no-hardlinks` from the author's clone, detached checkout at `fefce84`, verified clean). All suites and probes ran in the review tree. The author's working tree was never modified; nothing was pushed, committed, or PR'd by this review.
- **Environment:** Python 3.12.3 (`~/workspace/SEED/.venv/bin/python`). Tmpfs discipline observed throughout: `/tmp` usage stayed between 2% and 30% during this review (pytest scratch deleted between large runs); every count below comes from a clean, non-disk-full run.

## 1. The claimed gap

After the MAJOR-1 remediation, the reader session's deadline was checked only during admitted/charged physical reads. `EvaluationService._guarded()` returned its result while the session was still active, but no deadline check ran afterwards: CPU processing after the final read (stored-JSON decoding in the service, response-dict construction) and JSON response construction in the API layer (`_respond`) could complete after the 2-second server-processing deadline and still return HTTP 200.

## 2. Reproduction on the previous head `3364ace` (reviewer's own run)

Method: checked out `3364ace`, copied **only** the updated test file from `fefce84` into the tree (`git show fefce84:tests/dashboard/test_evaluation_http_budget.py`), ran the five new deadline tests, then the full updated file. The fake monotonic clock is patched only into the reader/replay module namespaces; no sleep-based timing is involved.

Observed, per test:

| Test | Required | Observed at `3364ace` |
| --- | --- | --- |
| `test_deadline_after_last_artifact_read` (strict_json advances clock +3.0 s after the final read) | 429 | **FAILED — HTTP 200** ("processing past the deadline returned 200") |
| `test_deadline_includes_json_serialization` (JSONResponse.render advances +3.0 s) | 429 | **FAILED — HTTP 200** |
| `test_deadline_applies_to_all_evaluation_routes` | 429 on every route | **FAILED — HTTP 200** (first route checked, `/api/evaluation/runs`, already returned 200) |
| `test_deadline_boundary_at_and_past` | 200 at exactly the deadline; 429 past it | **FAILED — past-deadline case returned HTTP 200** (the at-exactly-deadline 200 assertion inside the same test passed) |
| `test_concurrent_request_deadlines_are_independent` | pass | **PASSED** (MAJOR-1 sessions already had independent deadlines, as the author stated) |

Full updated file at `3364ace`: **4 failed, 11 passed** — exactly the author's stated pattern. The gap was real: on the previous head, a request whose post-read processing or serialization finished past the deadline returned success.

## 3. Verification on the new head `fefce84` (reviewer's own runs, clean tree)

| Suite | Result |
| --- | --- |
| `tests/dashboard/test_evaluation_http_budget.py` (10 MAJOR-1 + 5 deadline) | **15 passed** |
| `tests/dashboard` | **323 passed**, 2 warnings |
| `tests/evaluation` | **631 passed**, 2 warnings |
| Full repository (`pytest -q`, serial, clean tmpfs) | **1,541 passed**, 2 warnings (= 1,526 baseline + 10 MAJOR-1 + 5 deadline — exact) |

On the author's disclosed incident (an intermediate run showing 46 failed / 97 errors with all standalone scenarios failing at 100% tmpfs, then a clean rerun at 631 passed / 7/7): the explanation is consistent with everything this review observed. The failure signature (mass SQLite disk-I/O errors under a full 512 MB tmpfs) is the documented VM failure mode, and with scratch cleaned between runs every suite passed at the exact claimed counts. No evidence contradicts the disclosure.

## 4. Reviewer's own probes (13 checks; 12 passed, 1 expectation corrected by evidence — see MINOR-1)

Probes were written independently of the author's tests and used different injection seams.

**(a) Overrun at different seams than the author's:**
- a1 — clock advanced +3.0 s inside `EvaluationReader.verified_file` (the last reader call of `service.detail`, after the final physical charge, before all service-side CPU): **429 `deadline_exceeded`** ✓ (caught by `_guarded`'s post-call check)
- a2 — clock advanced +3.0 s inside the plain `Response.render` used by the **binary chunk route** (response-object construction after `service.chunk` returned): **429 `deadline_exceeded`** ✓ (caught by the route's `guard.enforce()`)

**(b) Legitimate errors are not converted:**
- Nonexistent run → **404 `not_found`** preserved with the clock advanced +3.0 s during error-response rendering ✓
- Bad query (`limit=99`) → **422 `invalid_request`** preserved ✓
- No-root service → **503 `evaluation_unavailable`** preserved ✓ (the no-op guard path works)
- Corrupted artifact (one byte flipped inside stored metrics; chunk-hash verification fails in the service) with the clock advanced +3.0 s during error rendering → **409 `artifact_error`** stands ✓
- Precedence boundary (see MINOR-1): corrupted artifact with the clock advanced +3.0 s *at `verified_file` entry*, i.e. before the `chunks.json` read that detection requires → **429 `deadline_exceeded`**. The admission gate refuses the detecting read once the deadline has passed, so the corruption is never established. This precedence is inherited from the MAJOR-1/R-BUDGET preflight-admission design, not introduced by this follow-up (the same scenario at `3364ace` also yields 429 whenever a charge/admission fires after expiry), and the returned error truthfully reports the condition the server actually established. No *raised* error is ever converted: `enforce()` runs only on the success path, and `_guarded`'s post-call check runs only when the call returned.

**(c) No second allowance:** partial advances summed across seams against the one deadline — +1.2 s in the service seam + +1.2 s in render = 2.4 s → **429**; +0.9 s + +0.9 s = 1.8 s → **200** ✓. A fresh 2-second allowance after the service returned would have passed the first case; it did not.

**(d) Boundary with reviewer clock control (service seam):** advance of exactly 2.0 s → **200** (the deadline is exceeded only strictly past it — `deadline_passed()` is a strict `>` comparison, matching the contract reading); advance of 2.0 s + 1 µs → **429** ✓.

**(e) Session hygiene:**
- After a deadline 429 through the API, a fresh request with no clock advance → **200** (no leaked or poisoned session; `request_session`'s context reset runs even when `enforce()` raises inside the `with` block) ✓
- A **direct** `EvaluationService.detail()` call (no API layer, no `request_context`) with the overrun seam → raises `ServiceError` **429 `deadline_exceeded`** from `_guarded`'s own session and post-call check ✓ — direct callers keep the same call/response shape; the deadline contract now also covers their post-read CPU, which is the instruction's mandatory behavior, not a shape change.

## 5. Coverage assessment

**Routes:** all eight Evaluation routes wrap their bodies in `service.request_context()` and call `guard.enforce()` after response construction, before returning — `GET /api/evaluation/runs`, `/runs/{run_id}`, `/runs/{run_id}/measurements`, `/runs/{run_id}/events`, `/runs/{run_id}/events/{event_key}`, `/runs/{run_id}/curve`, `/compare`, and `/runs/{run_id}/files/{file_id}` (binary). No Evaluation route returns a success response without passing `enforce()` (verified by full diff read and by probes a2/c across both response forms).

**Remaining success-after-deadline paths within scope: none found.** Notes on the boundaries of that statement:
- When `enforce()` itself raises, the resulting 429 error envelope is rendered by the app's exception handler *after* the check. That is the bounded error response the contract mandates, not a success path.
- External network transfer after the handler returns is outside the server-processing boundary by the contract's own definition, and the implementation claims nothing about it.
- Non-Evaluation routers (bootstrap, observer, operator, settings) are outside the Evaluation deadline contract and are untouched by this change.
- A blocking OS read in flight cannot be preempted mid-syscall; the design instead guarantees (as before) that success is never *returned* after expiry — the final check sits between response construction and return. This matches the instruction's defined processing boundary.

**Nesting:** the API's `request_context()` opens the reader session at route entry; `_guarded`'s inner `request_session()` reuses that ambient session (reader semantics byte-unchanged since `afc936e`), and probe (c) behaviorally confirms a single summed allowance across the service and serialization phases — no reset, no second deadline.

## 6. Diff audit (`3364ace..fefce84`)

- Changed files: exactly three — `dashboard/api/evaluation.py` (+114/−… net), `dashboard/services/evaluation.py`, `tests/dashboard/test_evaluation_http_budget.py` (+177 test lines). Full diff read line by line.
- **`development/**`: zero-line diff** — `reader.py`, `replay.py` and `development/evaluation/cli.py` (empirical dispatch lock) are byte-unchanged. `seed/**`, `.github/**`, requirements/lock: zero-line diff. No new dependencies (the fix adds one stdlib import, `contextlib.contextmanager`). No new endpoints; the route set is identical.
- Compare/scientific logic untouched — **MAJOR-2 was not addressed**, as required.
- The two pre-existing MINORs (client/server event-key grammar divergence; stale "Untrusted artifact preview" doc label) and the two MAJOR-1 review observations (typed `ContractError` for a missing file in `_read`; transient standalone sessions lingering in thread context) are untouched by this diff.
- **G6 preservation: CONFIRMED by carry-over and re-verification.** Because `reader.py`/`replay.py` are byte-identical to the G6-reviewed `afc936e` tree, the MAJOR-1 review's G6 verdict stands; this review additionally re-ran the G6 suites explicitly: `tests/evaluation/test_replay_budget.py` + `test_replay_budget_escape.py` + `test_reader.py` = **18 passed**, inside the full `tests/evaluation` run of **631 passed**.

## 7. Findings

- **BLOCKER: 0**
- **MAJOR: 0**
- **MINOR: 1** — *MINOR-1 (precedence observation, pre-existing, not introduced by this follow-up):* when the deadline expires before the physical read that would detect an artifact corruption, the admission gate's `BudgetError` (429 `deadline_exceeded`) preempts the not-yet-established corruption (409). Errors that are actually raised are never converted (verified for 404/409/422/503), and no success is returned either way; the 429 truthfully reports the condition the server established first. This is inherent to the mandated preflight-admission accounting (a reader forbidden to read cannot validate what it cannot read) and is recorded here so the precedence is documented rather than implicit. Non-blocking; no code change recommended within this task's scope.
- **UNRESOLVED: 0**

## 8. Verdict

**BLOCKER 0 / MAJOR 0 / MINOR 1 / UNRESOLVED 0**

**MAJOR-1 deadline contract: COMPLETE.** The gap reproduced on `3364ace` (HTTP 200 after the deadline in post-read processing, in serialization, across routes, and past the boundary) is closed at `fefce84`: one deadline now spans request validation, service processing, post-read CPU and response construction for every Evaluation route, in both JSON and binary forms, with the boundary exact (at-deadline 200, one tick past 429), no second allowance, independent concurrent deadlines preserved, and legitimate error precedence intact.

**DESIGN AMENDMENT REQUIRED: NO**

**Publication note:** this review verifies the local head `fefce84` only. Updating PR #31 to this head requires pushing the branch and fresh exact-head PR CI success on Linux Python 3.11, Linux Python 3.13, and macOS Python 3.13; the previously green CI at `3364ace` does not cover this head. This review does **not** approve merging PR #31. MAJOR-2 (scientific comparison compatibility correctness) remains open and untouched, as do the two pre-existing MINORs and the two MAJOR-1 review observations; I26–I29 is not claimed 0/0/0/0.
