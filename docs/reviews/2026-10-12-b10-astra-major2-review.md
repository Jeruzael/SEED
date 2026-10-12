# B10 MAJOR-2 — Independent Narrow Review: Scientific Comparison Remediation

Reviewer: fresh independent narrow reviewer (separate clone; did not author the work).
Date: 2026-10-12.
Branch: `seed-0.2-b10-impl-05-astra` (PR #31, OPEN, unmerged).
Previous head (defect present): `f8b776146bb4c993c452c7605eccf0134d2f3f60`.
Reviewed head: `01e6d28d38091903f6193fd89d5d01af940dd38a`
(commits `00976f1` tests, `3b62531` service+view fix, `01e6d28` view backward-consciousness + DOM test).
Master: `3406e1f2d5f757032befc9b91380ea7636b827fb`.

## Verdict

```text
MAJOR-2: CLOSED
BLOCKER: 0
MAJOR: 0
MINOR: 1 (new observation, tracked — see Findings)
UNRESOLVED: 0
G6 / MAJOR-1 PRESERVATION: CONFIRMED
DESIGN AMENDMENT REQUIRED: NO
```

Overall I26–I29 is **not** claimed 0/0/0/0: the five previously tracked MINOR
items remain open, plus the one new MINOR observation recorded below (six
tracked MINOR items in total after this review). Publication still requires
pushing `01e6d28` to PR #31 and fresh three-job CI at that exact head; this
review does not approve merging.

## Tree and environment

- Independent clone: `git clone --no-hardlinks ~/workspace/SEED /tmp/seed-review-major2`;
  the author's working tree was never modified. Nothing pushed, committed, or PR'd.
- Python: the repository venv interpreter (`~/workspace/SEED/.venv/bin/python`),
  with imports verified to resolve to the clone (`dashboard.services.evaluation`
  loaded from `/tmp/seed-review-major2/...`).
- `/tmp` (512 MB tmpfs) was checked before every suite run and pytest scratch
  was deleted between runs; all counts below come from clean runs. No disk-full
  artifacts were encountered or relied on.

## 1. Reproduction on the previous head `f8b7761`

Only the new test file (`tests/dashboard/test_evaluation_comparison_compatibility.py`,
copied from `01e6d28`) was added to the old tree. Reviewer's own observed result:

```text
10 failed, 1 passed
```

matching the author's RED claim exactly. The two signature defects were
confirmed individually:

- **False incompatibility (the MAJOR-2 defect):** two genuinely published runs
  with identical `plan_digest` and differing `science_digest` (MAE 0.0 vs 0.5,
  derived through the real machinery) failed as `assert data['compatible'] is True`
  → `assert False is True`. The old code reported scientifically comparable runs
  INCOMPATIBLE solely because their recorded outcomes differed.
- **Forged plan binding accepted:** a plan artifact whose stated digest was
  forged (rehashed so transport integrity passes) returned **HTTP 200**, because
  the old code never read the plan at all (`assert 200 == 409`).

The single pass was `test_forged_metrics_rejected` — the pre-existing
chunk-integrity rejection (forged metrics without rehash → 409), i.e. a
preservation guard, as the author stated.

## 2. Verification on the reviewed head `01e6d28`

Reviewer's own runs, exact counts:

| Suite | Result |
|---|---|
| `tests/dashboard/test_evaluation_comparison_compatibility.py` | **11 passed** |
| `tests/dashboard` (complete) | **335 passed** |
| `tests/evaluation` (complete) | **631 passed** |
| `tests/dashboard/test_evaluation_http_budget.py` (explicit rerun) | **15 passed** |

All match the author's GREEN claims (335 = 323 + 11 new API tests + 1 new DOM
test). `node --check` on the view: OK. `git diff --check f8b7761..01e6d28`:
clean. `compileall` on the service: OK. (The author's full-repository figure of
1,553 was not independently re-run; the two suites that contain every changed
file's tests were run in full, and the diff — see §6 — touches nothing outside
`dashboard/` and dashboard tests.)

## 3. Compatibility-matrix audit against stored artifacts

A genuine run was published through the real pipeline in the reviewer's tree
and its artifacts dumped. Every eligibility dimension maps to a real stored
field — nothing is assumed:

- `manifest.experiment` = `{id, version, source_commit, lock_digest,
  profile_digest, protocol, adapter_version}` — the source of six of the seven
  dimensions (experiment id+version, protocol, source, lock, profile, adapter).
- Plan binding chain observed identical on one value across all four carriers:
  `manifest.plan_digest` == `analysis-plan.json` `digest` ==
  `analysis-plan.json` `receipt.digest` == `metrics.plan_digest`
  (`138fb11c…` in the reviewer's fixture).
- The plan body carries every plan-carried dimension the design names:
  `members` (family, scenario_version, rule_version, protocol, variant, seed),
  `metrics` (id, version), `populations`, `windows`, `baselines`, `thresholds`,
  `questions`, `seeds`, `analysis_plan_version`, plus the plan-schema-v1
  constants (eligibility/coverage/aggregation/standardization/missing_rules are
  fixed by `development/evaluation/analysis.py` validation and cannot differ
  between two valid v1 plans).
- On the producer side the binding is genuinely cryptographic:
  `analysis_digest()` (analysis.py:282) hashes the canonical plan body, and
  `require_frozen` recomputes it and checks `body_sha256` — a genuine pipeline
  cannot emit a plan whose body disagrees with its digest.
- Measurement pairing identity is the stored string
  `member:metric:population:window` (`member-0:prediction.numeric-mae:all:whole`
  observed), not a name-similarity inference.
- **No eligibility input is an outcome:** service code (read in full, §6)
  builds dimensions only from `manifest.experiment`, the binding-gated
  `plan_digest`, and nothing else. Probes confirm it behaviorally: identical
  values + differing provenance → incompatible (probe e); differing values +
  identical definitions → compatible (author B1 + probe b variant). Findings
  are carried verbatim; `science_digest` appears only under
  `scientific_identity`.

**Plan-body tamper probes (reviewer's own).** The plan file's stated digests
were left untouched, one plan-body field was edited, and chunks/receipt were
rehashed (transport integrity valid):

- threshold value 1 → 5 in the body: compare returns **compatible**,
  `plan_digest` status `match`, `plan_fields` `[]` — not caught, no flip.
- member `rule_version` 2 → 99 in the body: **compatible**, not caught.
- plan-body metric version 1 → 2: metric state flips to `version_mismatch`
  (the version check reads the body), but eligibility stays `compatible`.

So on the observer path the digest coverage is: cross-checked **stated**
digests under the receipt integrity model. The observer does not re-hash the
served plan body against its stated digest or against the freeze receipt's
`body_sha256`. This is recorded as the review's single MINOR below, with the
reasoning and its bounds. It does not block MAJOR-2 closure: it is not a
regression (the old code never read the plan), it is the same limitation the
accepted design (§15) places on every value the observer serves — the science
digest itself is never recomputed by the observer either, and §15 explicitly
scopes stored-byte integrity to the trusted receipt ("someone able to rewrite
both payload and receipt can forge a new matching pair") — and every
cross-file inconsistency mode (the realistic corruption modes) **is** caught
with 409.

## 4. Reviewer probes (own design, own fixtures)

All probes were run against genuinely published fixtures in the reviewer's
tree (publication via the approved pipeline; edits rehashed and labeled):

- **(a) lock-only difference:** same plan, same outcome; only
  `lock_digest` differs → `eligibility: incompatible`, sole reason
  `lock_digest: differs`, all six other dimensions `match`. **Pass.**
- **(b) metric missing on one side:** the MAE row removed from the right
  run's `metrics.json` produced inventory (rehashed) → metric state
  `unavailable`, `missing: ['right']`, right value `None` — never zero;
  eligibility unaffected (`compatible`), correctly separating measurement
  availability from comparison eligibility. **Pass.**
- **(c) identical everything:** two runs, same plan/provenance/outcome →
  `compatible: true`, `scientific_identity.science_digest.equal: true`
  (also confirms run IDs do not enter the science digest). **Pass.**
- **(d) self-compare, two-population plan:** run compared with itself under
  a plan registering MAE for populations `all` and `resting` → metric state
  `ambiguous` with both candidate identities; no self-pairing shortcut.
  **Pass.**
- **(e) incompatible pair, descriptive output:** source/profile-incompatible
  pair with a metric requested → HTTP 200, metric `paired` with both stored
  rows side by side, findings present for both runs, reasons naming exactly
  `source_commit` and `profile_digest`. **Pass.**
- **(f) ranking-vocabulary scan:** the full JSON of probes (a), (b), (c), (e)
  scanned case-insensitively for `better`, `worse`, `equivalent`, `verdict`,
  `winner`, `improved` — none present. **Pass.**

## 5. MAJOR-1 preservation

- `tests/dashboard/test_evaluation_http_budget.py` rerun explicitly in the
  reviewed tree: **15 passed** — the aggregate 1 MiB read budget, the 1 MiB
  serialized-response ceiling, the single 2-second deadline (including the
  post-read and serialization enforcement), concurrency isolation, and
  not-established/409/error-taxonomy behavior all intact.
- Near-limit compare coverage inside that file: `test_compare_aggregate_budget`
  (fabricated boundary compares at the exact ±1-byte totals) and
  `test_serialized_response_ceiling` — both pass, so the new plan reads did
  not create a skipped-check path: evidence is read through the session
  before any eligibility decision, and over-budget comparisons still fail
  with the bounded 429.
- The service diff introduces **no direct filesystem reads**: imports are
  unchanged, there is no `open(`, `os.`, or `read_bytes` anywhere in
  `dashboard/services/evaluation.py` (the only `Path(` is the pre-existing
  `from_root`); all artifact bytes flow through `reader.receipt()` /
  `reader.verified_file()` inside the request session.
- G6 surface untouched: `development/**` diff is zero lines (§6), and the
  full evaluation suite (631, including replay-budget, replay-escape,
  re-execution, and reader suites) passes.

## 6. Diff audit (`f8b7761..01e6d28`, read in full)

Changed files — exactly the four claimed, nothing else:

```text
dashboard/services/evaluation.py                    +233/-40 area (compare rewrite + helpers)
dashboard/static/views/evaluation.js                renderCompare only
tests/dashboard/test_evaluation_assets.py           +43/-0 (one ADDED DOM test)
tests/dashboard/test_evaluation_comparison_compatibility.py  new, 482 lines
```

- Zero diff under `development/**`, `seed/**`, `.github/**` (verified
  directly); no dependency or lockfile changes; no workflow changes.
- No new endpoints: `dashboard/api/evaluation.py` is untouched; the compare
  route, methods, and query contract are unchanged.
- View changes are confined to a single hunk inside `renderCompare`
  (three cards: Compatibility / Scientific identity / Scientific results;
  eligibility-driven text with a legacy-boolean fallback; per-dimension
  Status including `Not established`; differing plan fields; metric-state
  handling; per-run findings tables). No `innerHTML`/`eval` introduced;
  rendering remains text-based.
- The assets-test change is purely additive: the pre-existing
  `test_comparison_blocks_incompatibility` (legacy response shape) is
  byte-unmodified and passes against the new view via the backward-tolerant
  fallback; the new `test_comparison_separates_eligibility_from_identity`
  covers the new shape.
- Empirical dispatch untouched (`development/evaluation/cli.py` not in the
  diff; `EMPIRICAL_DISPATCH_DISABLED` intact). None of the five previously
  tracked MINOR items lives in a touched file; none was silently fixed or
  closed.

## 7. Design-decision judgments

**(i) Present-but-contradictory binding → 409 (not `not_established`):
CORRECT.** The implementation draws a principled line: *absence* of evidence
yields `not_established`; *contradiction within the artifact's own verified
files* (plan-file digest or metrics plan_digest disagreeing with the manifest)
is invalid stored evidence, the same class as every other `artifact_error`
409 in this API. Calling it `not_established` would understate a provably
broken artifact; calling it `incompatible` would fabricate a scientific
conclusion from corrupt input. The reviewer reproduced both branches
(forged stated digest → 409; missing plan file → `not_established`).

**(ii) Boolean `compatible` false for `not_established`, with `eligibility`
disambiguating: ACCEPTABLE.** The boolean stays conservative — it can never
overclaim compatibility — and the three-state field is the authoritative
contract, documented in the service docstring and rendered distinctly by
the view ("Compatibility not established from the stored evidence" ≠
"Incompatible"). Legacy consumers reading only the boolean get the safe
direction (no descriptive pairing presented as established). This is a
minimal, backward-conscious refinement of the response, as authorized.

**(iii) Plan-digest equality REQUIRED (any plan difference → incompatible
in v1): FAITHFUL to the design.** Design §17 states verbatim "Equal plan
digest is necessary, not sufficient", and the freeze contract enforces one
plan body per (experiment, plan version) per root — verified in
`analysis.py` (digest computed from the body; freeze identity bound to
experiment+version; `require_frozen` recomputes). Cross-plan "variant
pairing" would require inferring correspondence the stored contract does
not declare; the approved varying axes are intra-plan members, and those
pair exactly by the stored measurement identity. The implementation also
softens the refusal correctly per §17: incompatible pairs still get
labeled side-by-side inspection with exact reasons and `plan_fields`
naming the differing plan fields (reviewer-verified: `thresholds`,
`members`).

## Findings

- **BLOCKER: 0.**
- **MAJOR: 0.**
- **MINOR 1 (new, tracked for the final cleanup pass):** the observer does
  not re-hash the served analysis-plan body against its stated digest /
  freeze-receipt `body_sha256`. A plan body edited in place with transport
  integrity rehashed (stated digests untouched) is served as
  `plan_digest: match` with `plan_fields: []` for plan-carried fields
  (thresholds, member rule versions — reviewer probes T1/T2); only the
  metric-version lookup, which reads the body, reacts (T3). Bounds: not a
  regression (the pre-MAJOR-2 code never read the plan); a genuine pipeline
  cannot emit such an artifact (producer-side binding is cryptographic);
  the gap requires the §15 out-of-model attacker who can rewrite payload
  and receipt — the same trust the observer already places in the manifest
  and the science digest, neither of which it recomputes; and all
  cross-file inconsistency modes are caught with 409. Recorded so the
  matrix claim is precise: on the observer path, plan-carried dimensions
  are covered by *cross-checked stated digests under the receipt integrity
  model*, not by observer-side re-hashing. Disposition: track with the
  other MINORs; if the cleanup pass wants the stronger property, verifying
  `receipt.body_sha256` against the canonical served body inside
  `_plan_state` is the narrow place to add it.
- **UNRESOLVED: 0.**

## Final verdict lines

```text
MAJOR-2: CLOSED
BLOCKER: 0
MAJOR: 0
MINOR: 1 (new, tracked; five pre-existing MINORs also remain tracked)
UNRESOLVED: 0
G6 PRESERVATION: CONFIRMED (development/** zero diff; evaluation 631 passed)
MAJOR-1 PRESERVATION: CONFIRMED (budget/deadline suite 15/15 in the reviewed tree)
DESIGN AMENDMENT REQUIRED: NO
```

The false-incompatibility defect and the silent first-row metric selection
are repaired and independently verified; different results alone no longer
cause an incompatibility verdict, genuine incompatibilities are named
dimension-by-dimension, missing evidence is honestly `not_established`,
and no ranking or verdict is produced anywhere in the response or the view.
