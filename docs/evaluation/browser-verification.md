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

## Addendum (2026-10-12) — running a fixture locally; the macOS `/tmp` pitfall

Operator instructions for building a disposable fixture (for example
`complete-negative`) and viewing it in the dashboard.

**Pitfall (macOS): a destination under `/tmp` always fails.**
`EvaluationRoot.create` opens the destination through
`development/evaluation/paths.py::_directory`, which walks every
path component with `O_NOFOLLOW` and refuses any component that is
not a real directory ("Resolve nothing silently: every existing
path component must be a real directory"). On macOS `/tmp` is a
symlink to `/private/tmp` (likewise `/var` → `/private/var`), so
`EvaluationRoot.create` raises `ContractError: INVALID_CONTRACT`
for any `/tmp/...` destination — after `build()`'s own
empty-directory checks have already passed. On Linux `/tmp` is a
real directory and the same command works, which is why the test
suite never trips over this. Reproduced 2026-10-12: a path through
a symlinked component raises `ContractError`; the same directory
addressed by its real path succeeds.

**Correct commands**

macOS — use the real path (`/private/tmp` is the same folder):

```bash
mkdir -p /private/tmp/seed-eval-demo
.venv/bin/python -c "from pathlib import Path; from tests.dashboard.evaluation_fixture import build; print(build(Path('/private/tmp/seed-eval-demo'), 'complete-negative'))"
```

Linux — `/tmp` is fine as written:

```bash
mkdir -p /tmp/seed-eval-demo
.venv/bin/python -c "from pathlib import Path; from tests.dashboard.evaluation_fixture import build; print(build(Path('/tmp/seed-eval-demo'), 'complete-negative'))"
```

Expected result:
`{'case': 'complete-negative', 'checkout': '<destination>', 'runs': ['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'], 'note': 'technical fixture; not an empirical B10 result'}`.

Any destination whose components are all real directories works
(for example a scratch folder under the user's home). The
destination must be empty: the builder refuses non-empty or
state-like destinations, and a fixture root must never be the
installed SEED home.

**Viewing it (observer mode, read-only):**

```bash
SEED_HOME=<disposable-home> .venv/bin/python -m dashboard --port 8971 --evaluation-root <fixture-destination>
```

`GET /api/evaluation/runs` then lists the published run and
`GET /api/evaluation/runs/<run_id>` returns its detail.

**Local verification (berg, Linux VM, 2026-10-12):** the exact
command above succeeded at `/tmp/seed-eval-demo`; the reader index
listed 1 run; the run detail status was `COMPLETED`; the stored
finding was `NEGATIVE` with reason `PREREGISTERED_THRESHOLD_RULE`;
the dashboard API returned the same run and detail with
`--evaluation-root` pointed at a durable copy of the fixture
(`~/workspace/seed-eval-demo` on the VM); the demo server was
stopped after verification (port closed, no process remaining).

## 2026-10-12 Local macOS Browser Acceptance Addendum

Executed in Chrome on the owner's Mac (Guest window), against the
isolated review checkout `~/SEED-astra-i29-review` at branch head
`6495c67cb2759623de9f1341b3abd0f5197da93c`, with a disposable review
directory `REVIEW_DIR=/private/tmp/seed-i29-mac.1ArWLd` (real path;
`/private/tmp`, never `/tmp`, per the pitfall documented above) and
an observer-only dashboard on `127.0.0.1:8971` (no `--operator`, no
tunnels, no installed-organism access). Environment:

- macOS 26.5.1 (build 25F80), MacBook Air (arm64);
- Google Chrome 154.0.8037.99 (Guest window);
- Python 3.13.15 (Homebrew), venv built from
  `requirements-lock.txt`;
- split execution: the owner ran the terminal steps (clone, venv,
  fixtures, server launch, teardown Ctrl+C) because Terminal is
  hard-blocked for the agent's computer control; the agent drove
  Chrome for all browser checks;
- fixture setup verified on disk before browsing: synthetic
  `home/memory.sqlite3` from `tests.dashboard.astra_fixture
  --case combined`, and `eval/.seed-evaluation` published by
  `tests.dashboard.evaluation_fixture` case `complete-negative`
  with run `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`; the dashboard
  Overview rendered the synthetic home (organism "SEED fixture",
  Generation 0).

### Test A — replay events and recorded event detail: PASS

In the actual browser, locally served (no tunnel latency):

- Run list shows the `aaaa…` run COMPLETED with science digest
  `0d574e6f11ad…` and `whole_payload_verified_at_publication`.
- The Replay events view loads: table "Recorded replay events"
  ("Recorded stages, including skipped and unconfirmed attempts.
  Replay never invokes cognition.") with the single recorded event
  `measured:default:1:update` · SELECTED ACTION `observe` ·
  LEARNER UPDATE `Confirmed` · INSPECT `Open`, plus First-page
  paging.
- The recorded event detail renders: "Recorded event — Recorded
  replay only; no cognition is invoked." with Phase `measured`,
  Subcase `default`, Ordinal `1`, Stage `update`; the formatted
  stored fields expand to the genuine recorded body
  (`"confirmed": true`, `"post_ack": {"action": "observe",
  "update": {"kind": "b1_transition", "source_ids": ["s1"]}}`,
  `"preupdate": {"evidence": {…}}`), displayed as text.
- The detail page also shows the separate Execution and Scientific
  findings sections with the stored finding `prediction · NEGATIVE
  · PREREGISTERED_THRESHOLD_RULE`.

This closes the replay half of item 3, which the tunnel-based run
could only mark PARTIAL.

### Test B — exact viewport widths (DevTools device toolbar)

Widths were set in the Responsive device toolbar and each value
was read back from the field before judging layout.

- **320 px: PASS** — mobile layout with hamburger navigation;
  Execution card fits the viewport, long run ID and verification
  strings wrap inside the card, findings and recorded-events
  tables reachable in their labeled scroll regions; no page-level
  horizontal overflow.
- **760 px: PASS** — mobile layout at the breakpoint; Execution
  and Scientific findings cards stack readably, findings table
  fully legible; no overlap or page-level overflow.
- **761 px: PASS** — single-column layout persists immediately
  above the breakpoint; section links (Measurements, Replay
  events, Curves, Files, All runs) and the Replay events panel
  reachable; no overlap or overflow.
- **1120 px: PASS** — medium layout at the boundary; Refresh and
  the Execution card fully readable, long verification strings
  wrap within the card; no overlap or page-level overflow.
- **1121 px: PASS** — identical medium presentation immediately
  above the boundary; all fields readable; no overlap or
  page-level overflow.
- **1440 px: PASS** — desktop-width viewport renders the same
  readable layout (DevTools "fit to window" scaling); no overlap
  or page-level overflow.

This closes item 10, which the tunnel-based run could not verify.

### Network latency (Chrome DevTools, local connection)

Recorded on the events view with the Network panel, no throttling:
17 requests, all HTTP 200; document 2 ms; the run-detail fetch
200 in 4 ms; `events?limit=20` 200 in 2 ms (2.8 kB); page Finish
39 ms, DOMContentLoaded 27 ms. On the run list, `runs?limit=20`
returned 200 in 2 ms both on navigation and on manual Refresh.
Every Evaluation request completed roughly three orders of
magnitude inside the approved 2,000 ms client deadline, which was
not changed.

### Regression checks (§8 of the acceptance instruction)

- Overview renders the synthetic fixture home and remains usable.
- Evaluation stays observer-only; no execution controls exist.
- Execution and Scientific findings remain separate sections.
- The COMPLETED run shows the stored NEGATIVE finding; no
  universal scientific PASS badge appears anywhere.
- Manual Refresh refetched in place (second `runs?limit=20`,
  200, 2 ms; "Read at" timestamp advanced) without navigating.
- Keyboard Tab traversal moved focus through the view's controls
  and scrollable evidence regions.
- Dark theme and light theme both render readably (theme cycled
  system → dark → light during the session).
- Browser navigation (list → detail → events → event detail →
  back; Evaluation ↔ Overview) never left stale content.

### Integrity confirmations and teardown

- No installed organism memory was accessed: every test process
  ran with `SEED_HOME` pointing at the disposable review
  directory and `--evaluation-root` at its `eval/` folder; the
  installed home `~/Library/Application Support/SEED` was never
  opened by the test setup, and no migration, install script, or
  LaunchAgent change was performed.
- No tunnel was used; the dashboard bound only `127.0.0.1:8971`
  for the whole session. No `--operator`, no empirical dispatch.
- Teardown: the owner stopped the test dashboard with Ctrl+C in
  its Terminal; a subsequent reload in Chrome returned
  `net::ERR_CONNECTION_REFUSED`, confirming port 8971 closed and
  no test server remaining. The disposable review directory and
  the screenshots are preserved until this evidence is reviewed.
- Screenshots (agent workspace, preserved):
  `.superpowers/b10-astra/mac-acceptance/` —
  `network-latency-full.jpg` (Network panel with per-request
  timings), `width-320.jpg`, `width-760.jpg`, `width-761.jpg`,
  `width-1120.jpg`, `width-1121.jpg`, `width-1440.jpg`,
  `theme-light-runlist.jpg` (light theme run list).

### Combined I29 browser acceptance

With this addendum, the two outstanding items from the
tunnel-based run are closed in a real browser on a direct local
connection: item 3 is fully PASS (replay list and event detail)
and item 10 is PASS at all six widths. **I29 browser acceptance
is COMPLETE (11 of 11)**, the earlier 9-of-11 record above
remaining unchanged as the historical tunnel-based result.
