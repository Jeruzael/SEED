# B10 Astra Evaluation — MAJOR-2 Remediation Record

Date: 2026-10-12. Branch: `seed-0.2-b10-impl-05-astra` (PR #31).
Starting head: `f8b776146bb4c993c452c7605eccf0134d2f3f60`.
Reviewed engineering head: `01e6d28d38091903f6193fd89d5d01af940dd38a`.
Commits: `00976f1` (tests), `3b62531` (service + view),
`01e6d28` (view backward-consciousness + DOM test).

## The finding

`EvaluationService.compare()` decided compatibility by equality of
three manifest fields — `experiment` (whole dict), `plan_digest` and
`science_digest`. The science digest identifies the recorded
scientific CONTENT (design section 15), so two runs with identical
experimental definitions and provenance but different recorded
outcomes were reported incompatible. Result identity was conflated
with comparison eligibility; additionally, a bare metric ID was
silently resolved to the first matching produced row.

## Compatibility matrix (Phase A audit)

All dimensions below were mapped to fields actually stored in the
published artifacts and verified by the independent reviewer
against a genuine published artifact.

| Dimension | Stored source | Rule | Validation |
|---|---|---|---|
| Experiment ID/version | `manifest.experiment.{id,version}` | Must match | Exact values from receipt-verified manifests |
| Frozen plan digest | `manifest.plan_digest`; `analysis-plan.json` `digest` + freeze `receipt.digest`; `metrics.plan_digest` | Must match, binding verified per run | Receipt-verified files; cross-file digest equality per run; a contradicting stored value is invalid evidence (409); a missing link is not established |
| Plan-carried definitions (analysis-plan version; members incl. family/scenario/rule versions, protocol, variant, seed; metric versions; populations; windows; baselines; thresholds; question rules) | `analysis-plan.json` plan body | Must match — established by verified plan-digest equality (the digest covers the whole canonical body; the producer-side binding recomputes it) | Plan digest equality after binding verification; differing top-level fields are disclosed as `plan_fields` |
| Run protocol | `manifest.experiment.protocol` | Must match | Exact value |
| Source commit | `manifest.experiment.source_commit` | Must match | Exact value |
| Dependency lock | `manifest.experiment.lock_digest` | Must match | Exact value |
| Execution profile | `manifest.experiment.profile_digest` | Must match | Exact value |
| Adapter version | `manifest.experiment.adapter_version` | Must match | Exact value |
| Selected measurement | `metrics.produced` rows keyed by identity `member:metric:population:window` + plan metric registry | Paired only when exactly one row per run, identities equal, versions equal the registered version | Explicit states: paired / unavailable / ambiguous / unpaired / version_mismatch / not_established |
| Science digest | `manifest.science_digest` | **Result identity, not eligibility** | Reported separately as provenance with equal/different |

Contract notes: in plan schema v1, eligibility/coverage/
aggregation/standardization/missing_rules are contract-fixed
constants (`development/evaluation/analysis.py`), so they cannot
differ between two valid plans; a root freezes exactly one plan
body per experiment+version, so cross-plan comparisons are
incompatible in v1 by design (section 17: equal plan digest is
necessary, not sufficient). Deliberately varied axes are intra-plan
(members) and pair across runs by stored measurement identity.

## RED evidence (at `f8b7761`)

New suite `tests/dashboard/test_evaluation_comparison_compatibility.py`:
**10 failed / 1 passed**. Signature failures: two genuinely
published runs sharing the frozen plan (with the preregistered MAE
floor) and provenance, with derived MAE 0.0 vs 0.5, returned
`compatible: false` solely because their science digests differ;
a forged plan binding (plan-file digest contradicting the manifest,
rehashed) returned HTTP 200 because the old code never read the
plan; a pair with a required provenance field stripped from BOTH
manifests would have matched by `None == None`. The single pass was
the pre-existing chunk-integrity rejection (preservation guard).

## Implementation (`3b62531`, `01e6d28`)

- `compare()` reads manifest, analysis-plan (when inventoried) and
  metrics for both runs through the single request session before
  deciding; near-limit comparisons therefore produce the bounded
  429 rather than skipping checks.
- Eligibility is computed from the seven manifest/plan dimensions
  above, each with status `match` / `differs` / `not_established`;
  the response carries `eligibility`
  (`compatible` / `incompatible` / `not_established`), the
  conservative boolean `compatible` (true only for `compatible`),
  exact `reasons`, and `plan_fields` when both plans are present
  and differ.
- `scientific_identity.science_digest` reports the two digests and
  their equality separately; stored `findings` are carried verbatim
  per run; no ranking or verdict is produced anywhere.
- Metric pairing is by full stored identity with the explicit
  states above; unavailable values are never zero, and an ambiguous
  metric lists its candidate identities without choosing a row.
- The compare view renders three separate cards — Compatibility,
  Scientific identity, Scientific results — and stays tolerant of
  legacy responses without an `eligibility` field (the pre-existing
  DOM test passes unmodified).

Changed files: `dashboard/services/evaluation.py`,
`dashboard/static/views/evaluation.js`,
`tests/dashboard/test_evaluation_comparison_compatibility.py` (new),
`tests/dashboard/test_evaluation_assets.py` (one added DOM test).
No `development/**`, protected-scope, endpoint, schema or
dependency changes.

## GREEN evidence (author, at `01e6d28`)

New suite 11/11; dashboard 335 passed; evaluation 631 passed;
full repository 1,553 passed / 2 warnings (1,541 + 11 + 1);
MAJOR-1 budget/deadline file 15/15 (inside the dashboard run);
7/7 standalone scenarios; JS syntax, compileall and
`git diff --check` clean. Resource evidence: genuine comparison
reads (receipts, chunk indexes, manifests, plans, metrics for two
runs) total a few KiB against the unchanged 1 MiB / 2 s per-request
budget, instrumented in
`test_compare_reads_plan_within_same_budget`.

## Independent narrow review

Fresh clone at `01e6d28`
(`docs/reviews/2026-10-12-b10-astra-major2-review.md`):
**MAJOR-2: CLOSED — BLOCKER 0 / MAJOR 0 / MINOR 1 / UNRESOLVED 0 —
G6 & MAJOR-1 PRESERVATION CONFIRMED — DESIGN AMENDMENT REQUIRED:
NO.** The reviewer reproduced the RED pattern exactly on
`f8b7761` (10 failed / 1 passed, both signature defects), audited
the matrix against a genuine artifact, and passed six probes:
lock-only difference names `lock_digest`; a one-sided metric is
`unavailable` with the correct missing side; identical runs are
compatible with identity equal; self-compare under a two-population
plan is `ambiguous`; an incompatible pair still returns descriptive
rows and findings; no ranking vocabulary appears in any response.

## Remaining limitation (new MINOR, tracked)

The observer does not re-hash the served plan BODY against its
stated digest / freeze-receipt `body_sha256`. A plan body edited
in place with the stated digests kept and transport hashes
recomputed (the section-15 out-of-model attacker who can rewrite
payload and receipt together) would pass as `plan_digest: match`;
only consumers of the body itself (the metric-version lookup)
react. This is not a regression (the old code never read the plan),
a genuine pipeline cannot emit such an artifact, and the same trust
is placed in the unrecomputed manifest and science digest. It is
recorded for the subsequent final cleanup pass, which may close it
at `EvaluationService._plan_state` if Gio directs. Together with
the five previously tracked MINOR items, six MINORs remain open;
I26–I29 is not claimed 0/0/0/0.

PR #31 remains OPEN and unmerged. I30 not started; I31 NOT
AUTHORIZED; no empirical execution performed.

## Post-review CI note (2026-10-12, appended)

The first CI run at the documentation head `bd71461`
(run `38253014501`) failed on macOS only: Linux Python 3.11 and
3.13 passed; `test (macos-py313)` failed in the new suite's
`test_compare_reads_plan_within_same_budget`. The failure was in
the TEST's instrumentation, not the product: it resolved file
descriptors to paths via `/proc/self/fd`, a Linux-only facility,
so on macOS the plan-read assertion could not name the reads (the
compare itself returned 200 within budget). Fixed test-only at
`cfc8b96` by naming descriptors from the `os.open` call's own path
argument (portable; descriptor-relative opens pass the payload
file name) with close tracking; product code unchanged. The fresh
exact-head CI for the final head is recorded in the PR #31
completion report.
