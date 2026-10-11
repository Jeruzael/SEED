# B10 I29 — Astra Evaluation Browser Verification

- **Branch:** `seed-0.2-b10-impl-05-astra`
- **Tested commit:** `790c3bb` (branch head during acceptance)
- **Browser:** Muse Browser (Chromium, leased browser VM; no version
  number exposed by the environment)
- **Status:** COMPLETED WITH TWO DOCUMENTED ENVIRONMENT GAPS — 9 of 11
  checklist items PASS in the actual browser; item 3 is partial and
  item 10 unverified for environment reasons recorded below. No item
  is marked passed on DOM-harness evidence alone.

## Fixture cases (tests/dashboard/evaluation_fixture.py)

`build(destination, case)` publishes genuine technical-fixture
artifacts through the approved I21–I24 publication contracts into an
explicit empty disposable directory; non-empty or state-like
destinations are refused, and installed SEED state is never used.

| Case | Evidence (tests/dashboard/test_evaluation_fixture.py) |
|---|---|
| empty | Reader returns an empty run index |
| complete-negative | COMPLETED run whose stored finding is NEGATIVE (preregistered threshold rule `mae-floor`, direction `ge`, floor 1 vs measured MAE 0) |
| partial | INCOMPLETE run; stored finding INCONCLUSIVE |
| missing-receipt | Receipt deleted after publication (labeled damage); detail read raises a typed error |
| malformed | Manifest damaged after publication (labeled damage); detail read raises a typed error |
| max-ids | Stored event evidence carries source IDs `9223372036854775807` and `9007199254740993` verbatim |
| incompatible-plans | Two runs; manifests differ in experiment and plan digest |
| max-inventory | 21 published runs; reader pages 20 + cursor + 1, lossless |
| truth-annotations | Private boundary marker present only in `truth.json`, reachable solely through bounded file inspection |

DOM-harness evidence (Node, real view code):
`tests/dashboard/test_evaluation_assets.py` — negative findings
visible on a completed run, incompatible comparison blocked with
exact dimensions and no ranking language, DOM/table caps enforced,
hostile artifact strings rendered as text (no `innerHTML`/`eval` in
the view source).

## Browser reachability and security handling

The browser VM cannot reach the dashboard servers bound to this
machine's loopback (direct loopback navigation blocked before
dispatch; DNS-to-loopback names reach only the browser VM's own
loopback; `host.docker.internal` refused). The dashboard application
is unchanged and loopback-only.

Acceptance therefore ran through temporary Pinggy tunnels approved by
the owner under an explicit security plan:

- a test-only loopback proxy presented the exact Host/Origin the
  app's security middleware requires (the app itself untouched) and
  enforced a secret gate: requests without the gate cookie received
  404; the cookie was set only via a one-time secret path. The gate
  was verified locally and through the public tunnel (no-cookie →
  404, gate path → 302, with-cookie → 200);
- each tunnel creation was individually approved by the owner
  (runtime SSH permission); tunnel URLs and gate secrets were treated
  as credentials — never committed, never recorded here;
- exposure window: tunnels created 2026-10-12 ~00:09–00:11 CST,
  browser run completed 00:21 CST, teardown verified immediately
  after: all tunnel/proxy/server processes stopped (0 remaining),
  gate secret files deleted, all three tunnel URLs unreachable, all
  six local ports closed;
- exposed data was limited to synthetic fixture artifacts and an
  empty disposable organism home, observer mode only.

Tunnel latency repeatedly exceeded the app's own 2,000 ms read
deadline (surfaced in the UI verbatim as "Evaluation read timed out
after 2000 ms. Retry when ready."), so several views needed Refresh
retries — itself direct browser evidence that the client enforces
the approved 2 s deadline.

## Actual browser checklist (verbatim evidence in the run report)

| # | Item | Result |
|---|---|---|
| 1 | Run list shows the completed run | **PASS** — table "Published evaluation runs", row `aaaa…` / COMPLETED / science digest / `whole_payload_verified_at_publication`, links "Open" and "Select to compare"; no run/execute controls |
| 2 | Separate Execution / Scientific findings headings; NEGATIVE visible; no global PASS badge | **PASS** — "Execution" [h2] and "Scientific findings" [h2]; findings row `prediction | NEGATIVE | PREREGISTERED_THRESHOLD_RULE`; the full page text contains no "PASS" badge or word |
| 3 | Measurements, replay events, recorded event detail | **PARTIAL** — Measurements PASS (caption "Registered measurements", `prediction.numeric-mae | 1 | MEASURED | 0`). Replay events COULD NOT VERIFY in the browser: the events view timed out on ~9 attempts through the tunnel (2 s client deadline vs tunnel latency). Events and event detail are verified by API tests and Node DOM tests; not claimed as browser-verified |
| 4 | Curves data alternative; file chunk preview not executed | **PASS** — "Stored curve series" table; "Artifact files" table with chunk counts; `manifest.json` chunk 0 shows "Bytes 750" and an "Untrusted artifact preview" rendering the JSON as literal text, not HTML |
| 5 | Two-run comparison shows Incompatible + dimensions, no ranking | **PASS** — "Incompatible for automatic comparison: the dimensions below differ. Side-by-side descriptive inspection only; the UI does not rank the runs."; dimensions table shows `experiment … Differs`, `plan_digest … Differs`; no better/worse language in full page text |
| 6 | No-root server shows the unavailable state; Overview still works | **PASS** — heading "Evaluation unavailable", text "Evaluation unavailable / no artifact root configured. Other dashboard views are unaffected."; Overview then loaded fully (organism, activity, memory, system health) |
| 7 | Skip link, keyboard navigation, captions, visible focus | **PASS** — first element `<a class="skip" href="#main">Skip to content</a>`; one Tab shows it with a visible focus outline (screenshot); Tab traverses nav incl. Evaluation with visible focus; real h1/h2 headings; every data table has a `<caption>`; table wrappers are `tabindex="0"` scroll regions with descriptive `aria-label`s |
| 8 | Theme cycle keeps the Evaluation view working | **PASS** — Theme button cycled system → dark; app re-rendered in dark and the Evaluation view remained fully usable (screenshot) |
| 9 | Manual Refresh reloads data in place | **PASS** — Refresh on the detail kept the URL, showed "Reading stored evaluation artifact…", then reloaded detail with a fresh "Read at" timestamp |
| 10 | Viewport widths 320/760/761/1120/1121/1440 | **COULD NOT VERIFY** — the browser environment offers no viewport-resize control. At the rendered ~1920px width the layout was usable with no page overflow; tables sit in labelled horizontal scroll regions (structural narrow-width mitigation). Exact-width behavior is not claimed |
| 11 | DOM element count on detail page (cap 1,500) | **PASS** — complete detail document ≈ 145 elements, well under the cap |

Unverified-item disposition: items 3 (replay sub-part) and 10 remain
explicitly unverified in a real browser; both are covered by the API
suite and the Node DOM harness, and neither is silently marked
passed. Whether this state satisfies the phase gate is the owner's
decision.
