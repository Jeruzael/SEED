# MAJOR-1 Remediation Record — Aggregate Astra HTTP Request Budgets

- **Instruction:** SEED B10 I26–I29 MAJOR-1 Resource Budget Remediation
  (owner instruction, 2026-10-12). MAJOR-1 only; MAJOR-2 and the two
  pre-existing MINORs are explicitly out of scope.
- **Starting head:** `898ddae4dcfec7fbc2f814358c03f6c220ac0be1`
  (PR #31 head, verified open and unmerged; master `3406e1f`).
- **Remediated head:** `afc936eb685e6bb64c44166858066dca114b897d`
  - `2eb9b28` test: add MAJOR-1 aggregate HTTP budget reproduction tests
  - `afc936e` fix: enforce aggregate Astra HTTP request resource budgets
  - (this record and the independent review are appended docs-only)

## The defect

`EvaluationReader._begin()` created a fresh `RequestBudget`
(1 MiB / 2 s) on the shared reader instance for **every reader call**.
`EvaluationService` composes several reader calls per HTTP request —
`detail()` = `reader.detail()` + `_stored_file()` (another
`reader.detail()` plus one `reader.chunk()` per 64 KiB chunk);
`compare()` = four `_stored_file()` calls — so the approved contract
of section 13/17 (1 MiB physical reads, 1 MiB serialized response,
one 2-second deadline **per HTTP request**) was in fact enforced per
internal operation, and the shared mutable budget fields
(`self._budget`) were exposed to concurrent FastAPI requests.

## RED reproduction (at 898ddae)

The reproduction suite is
`tests/dashboard/test_evaluation_http_budget.py`.

Physical reads instrumented at `Path.read_bytes`, `os.pread` and
`os.read` through real FastAPI `TestClient` requests. 9 failed /
1 passed (the genuine-fixture guard passed):

| Case | Measured at 898ddae |
| --- | --- |
| Detail, calibrated 5,000 B limit, genuine fixture | HTTP 200 with **7,160 B** physically read |
| Compare, real 1 MiB ceiling, large valid fixtures | HTTP 200 with **1,268,594 B** physically read |
| Nested-call budget identity (one detail request) | **3 distinct budgets** created and charged |
| Multi-chunk compare boundary 1,048,575 / 1,048,576 / 1,048,577 | served (HTTP 409 via the parse cap below; never the required 200/200/429 pattern) |
| File-size race (growing `metrics.json`) | **102,344 B** physically read against a 4,096 B allowance |
| Concurrency (paused request A, full request B) | request A charged **4 distinct budgets** (contamination) |
| Server deadline (0.6 s calibrated, 3 × 0.35 s nested reads) | HTTP **200** after ~1.05 s of aggregate work |
| Serialized response ceiling | **1,048,577-byte** body returned with HTTP 200 |

One enabling defect found by the reproduction: the service parsed
stored files with the generic 64 KiB message cap, so a *valid*
256 KiB `metrics.json` (allowed by the artifact contract) made
`detail` fail with 409 before any budget question arose. The
independent reviewer reproduced this separately on the old head.

## Implementation decisions

- **Request-scoped reader session** (`EvaluationReader.request_session()`,
  held in a per-instance `contextvars.ContextVar`): one session = one
  `RequestBudget` + one deadline + one read cache, shared by every
  nested reader call of the request. Standalone reader calls keep the
  historical per-call guarantee via fresh transient sessions, so the
  standalone `EvaluationReader` API and reader-level contracts are
  preserved. The service opens exactly one session per service call
  (one HTTP request); concurrent requests own independent sessions —
  no budget state lives on the shared reader instance.
- **Read-once memoization inside the session:** receipts, parsed
  chunk indexes, raw file reads and assembled verified files are
  cached per session, so nested calls never physically re-read a
  byte (this also removes the previously charged duplicate
  receipt/manifest/chunk-index reads, per instruction section 6).
- **Physical-read admission:** `_read()` is descriptor-based — size
  from `fstat`, admitted against the session budget before I/O, and
  every `pread` is capped at the admitted length; `chunk()` and
  `verified_file()` admit and cap each chunk the same way. A file
  that grows after any check cannot be over-read; a short read is a
  typed `ContractError`, never silent data.
- **`verified_file()`** assembles stored files from receipt-verified
  chunks; bytes already read in the session are verified in place
  against the receipt-verified chunk hashes instead of re-read.
- **Shared replay-index cache** stays cross-request (resumable
  progress preserved) and is guarded by a per-run `RLock`; budget
  state is never part of the cache. Fingerprint and chunk-verified
  state mutations are under a cache lock. No lock wraps the service.
- **Error taxonomy:** `replay.BudgetError` escaping a service call is
  mapped to HTTP 429 — `resource_limit` for byte exhaustion,
  `deadline_exceeded` when the session deadline has passed — never
  mislabeled as artifact corruption (409 `artifact_error` unchanged
  for invalid evidence; 404/503 semantics unchanged).
- **Serialized response ceiling:** every JSON route serializes once
  via `JSONResponse` and rejects a body over 1,048,576 bytes with
  429 `resource_limit` before returning; nothing is truncated. The
  octet-stream route asserts the same ceiling.
- **Enabling correction (narrow):** `_stored_file()` now parses with
  `strict_json(data, max_bytes=len(data))` — the bytes are already
  length-bounded and chunk-verified by the reader — aligning the
  parse cap with the artifact contract. This only widens cases that
  previously errored; no previously-successful response changes.
- `development/evaluation/replay.py` is **byte-untouched**; the
  session passes the existing `RequestBudget` object into
  `build_index`/`read_rows` exactly as before.

## GREEN evidence (author, at afc936e)

- New suite: **10/10 passed**.
- Measured aggregates after the fix: compare on the RED fixture
  **567,706 B** (was 1,268,594 B); detail on the same large fixture
  283,853 B; genuine-fixture detail exactly **3,222 B**
  (receipt 1,123 + manifest 750 + metrics 471 + chunks.json 878,
  each byte once).
- Boundary compares fabricated to aggregate totals of exactly
  **1,048,575 → 200, 1,048,576 → 200, 1,048,577 → 429
  `resource_limit`**, with instrumented physical reads never above
  1,048,576 (the unaffordable final chunk is refused at admission,
  before any physical read).
- Deadline: nested reads crossing the single session deadline fail
  with 429 `deadline_exceeded`; no successful-but-incomplete response.
- Concurrency: interleaved requests charge exactly one budget each,
  distinct objects; parallel replay paging correct.
- Regression: `tests/dashboard` **318 passed**; `tests/evaluation`
  **631 passed** (includes all replay-budget, reader, integrity,
  security, API, cancellation/timeout suites); full repository
  **1,536 passed, 2 warnings** (= 1,526 baseline + 10 new); seven
  standalone scenarios **7/7 PASS**; `compileall` clean;
  `git diff --check` clean; protected scope (`seed/**`, `.github/**`,
  requirements/lock) **zero diff**; no new dependencies (imports are
  stdlib `contextvars`/`threading` only); no new endpoints; empirical
  dispatch lock untouched.

## Fresh independent narrow review

Conducted at `afc936e` from an independent clone; the reviewer
reproduced the defect on `898ddae` with their own measurements
(identical values: compare 1,268,594 B, detail 7,160 B, 3 budgets,
A charged 4 budgets, growth 102,344 B, deadline 200, oversized
response 200), verified the new head with their own runs (new suite
10/10; dashboard 318; evaluation 631; full repository 1,548 passed
including their 12 probes), ran 7 independent probes (three-way byte
accounting — physical counter == session consumption == exact
on-disk sum; 24-thread mixed stress; distinct error labels; session
release after success and failure; one-byte forgery still 409;
response ceiling exact at ±1 byte) and 5 G6-preservation probes
(resumable lossless traversal of a >1 MiB genuine history across
budget interruptions, corruption vs `BudgetError` typing,
chunk-verification lifecycle, standalone per-call budgets).

**Verdict: BLOCKER 0 / MAJOR 0 / MINOR 2 / UNRESOLVED 0 —
MAJOR-1 CLOSED by this repair — G6 PRESERVATION CONFIRMED —
DESIGN AMENDMENT REQUIRED: NO.**
Full review: `docs/reviews/2026-10-12-b10-astra-major1-review.md`.
The 2 MINORs are observations about the fix itself (missing file in
`_read` now raises typed `ContractError` instead of leaking
`FileNotFoundError` — beneficial, no caller depended on it; and
transient standalone sessions linger in the calling thread's context
until the next `_begin()` — correctness-neutral). Both are recorded
here and tracked with the other MINORs for a later separate repair.

## Status of remaining findings

- **MAJOR-2** (scientific comparison compatibility correctness):
  OPEN — the next task after MAJOR-1, per owner instruction. Not
  addressed here; compare's compatibility logic is behaviorally
  unchanged by this repair.
- **Pre-existing MINOR-1** (client/server event-key grammar
  divergence) and **MINOR-2** (stale "Untrusted artifact preview"
  label quote in the historical browser record): OPEN, untouched,
  tracked for the later separate repair / closure pass.
- **Review MINORs from this remediation (2):** recorded above,
  OPEN, non-blocking.
- I26–I29 is therefore **not** claimed 0/0/0/0 overall.
- I30 not started. I31 NOT AUTHORIZED. No B10 experiments executed.
  Installed SEED organism untouched.

# Follow-up (2026-10-12): final deadline verification

A follow-up instruction required verifying the remaining end-to-end
server-processing deadline gap: after the remediation above, the
reader deadline was checked only during admitted/charged physical
reads, so CPU processing after the final read and JSON response
construction could, in principle, return HTTP 200 past the 2-second
server-processing deadline.

**Gap reproduced (RED at `3364ace`).** With a deterministic fake
monotonic clock patched only into the reader/replay module
namespaces: processing advanced +3.0 s after the final artifact read
(stored-JSON decoding) returned HTTP 200; serialization advanced
+3.0 s during JSON response construction returned HTTP 200; all
Evaluation routes behaved likewise; the past-deadline boundary case
returned 200. Result: 4 failed / 1 passed among the five new tests
(the concurrency independence guard passed — MAJOR-1 sessions
already kept independent deadlines).

**Corrective implementation (`fefce84`; tests `6224e4f`).**
Dashboard-only; `development/evaluation/reader.py` and
`replay.py` are byte-unchanged.

- `EvaluationService.request_context()` opens the reader session at
  API route entry; the service's inner session open reuses that
  ambient session, so ONE deadline spans request validation,
  service processing, reader operations, stored-data decoding,
  response preparation and response construction. No second
  two-second allowance exists after the service returns.
- `_guarded` checks the session deadline after the service call
  succeeds, so post-read CPU inside the service cannot return
  success late.
- Every Evaluation route calls a final `guard.enforce()` after the
  response is fully constructed and before returning it. On expiry:
  HTTP 429 `deadline_exceeded`, bounded envelope, no partial
  success. Errors raised by the service (404/409/422/503) are never
  converted, because enforcement runs only on the success path.
- Direct `EvaluationService` and standalone `EvaluationReader`
  behavior are unchanged.

**GREEN evidence (author, at `fefce84`).** New deadline tests 5/5;
budget test file 15/15; dashboard 323 passed; evaluation 631
passed; full repository 1,541 passed / 2 warnings (1,526 + 10
MAJOR-1 + 5 deadline); 7/7 standalone scenarios; compile and
`git diff --check` clean; protected scope unchanged. Boundary:
at exactly the deadline a request succeeds; strictly past it, 429.
One disclosed incident: an intermediate evaluation run showed
46 failed / 97 errors because the VM's 512 MB /tmp tmpfs filled
with pytest scratch (490 MB); after cleanup the clean rerun gave
631 passed and 7/7 scenarios — an environment artifact, not a
regression.

**Independent narrow review** (fresh clone, exact head `fefce84`;
`docs/reviews/2026-10-12-b10-astra-major1-deadline-review.md`):
BLOCKER 0 / MAJOR 0 / MINOR 1 / UNRESOLVED 0 — MAJOR-1 DEADLINE
CONTRACT COMPLETE — G6 PRESERVATION CONFIRMED — DESIGN AMENDMENT
REQUIRED: NO. The reviewer reproduced the gap on `3364ace`
(4 failed / 11 passed on the full budget file), confirmed every
suite count, and ran 13 probes at different seams (overruns inside
verified-file assembly and binary response rendering; summed
partial advances across service and serialization showing no
second allowance; the 2.0 s vs 2.0 s + 1 µs boundary; no session
leak after a 429; direct service callers). The single MINOR is a
pre-existing precedence note: if the deadline expires before the
physical read that would detect a corruption, the admission gate's
429 preempts the not-yet-established 409; no raised error is ever
converted and no success is returned. It is tracked with the other
MINOR findings for a later separate repair.

**Final deadline interpretation.** The Evaluation HTTP deadline is
one 2-second server-processing budget per request, established when
the handler begins and enforced at read admission, after service
processing, and after final response construction. It does not
guarantee instant preemption of arbitrary blocking OS operations
and does not include external network-transfer latency.

PR #31 remains OPEN and unmerged; MAJOR-2 remains OPEN.
