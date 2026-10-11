# B10 I29 — Astra Evaluation Browser Verification

- **Branch:** `seed-0.2-b10-impl-05-astra`
- **Engineering base:** `3406e1f2d5f757032befc9b91380ea7636b827fb`
- **Status:** IN PROGRESS — fixture and harness evidence complete;
  actual-browser items partially reachable (see "Browser environment"
  below). This record is updated with the final browser evidence
  before the phase is considered verified.

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

## Browser environment (actual browser attempt 1)

The Muse browser (Chromium, leased browser VM) could not reach the
dashboard servers bound to this machine's loopback:

- Direct loopback navigation was blocked before dispatch.
- A public DNS name resolving to loopback reached only the browser
  VM's own loopback, where no server listens.
- `host.docker.internal` / `gateway.docker.internal` refused the
  connection (servers are loopback-only by design).

The dashboard application itself is unchanged and loopback-only; a
test-only loopback proxy presents the exact Host/Origin the security
middleware requires (equivalent to an SSH port forward; the app is
untouched). One temporary public tunnel to the complete-negative
fixture server was approved and verified end-to-end (the Evaluation
API responded through it). Tunnels for the remaining two fixture
servers were not approved, so the comparison and unavailable-state
browser items are pending the owner's decision.

## Actual browser checklist

| # | Item | Result |
|---|---|---|
| 1 | Run list shows the completed run | PENDING (browser reachability) |
| 2 | Separate Execution / Scientific findings headings; NEGATIVE visible; no global PASS badge | PENDING |
| 3 | Measurements, replay events, recorded event detail | PENDING |
| 4 | Curves data alternative; file chunk preview not executed | PENDING |
| 5 | Two-run comparison shows Incompatible + dimensions, no ranking | PENDING (tunnel not approved) |
| 6 | No-root server shows the unavailable state; Overview still works | PENDING (tunnel not approved) |
| 7 | Skip link, keyboard navigation, captions, visible focus | PENDING |
| 8 | Theme cycle keeps the Evaluation view working | PENDING |
| 9 | Manual Refresh reloads data in place | PENDING |
| 10 | Viewport widths 320/760/761/1120/1121/1440 | PENDING |
| 11 | DOM element count on detail page (cap 1,500) | PENDING |

Items must not be marked passed on DOM-harness evidence alone.
