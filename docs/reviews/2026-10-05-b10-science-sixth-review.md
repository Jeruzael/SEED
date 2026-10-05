# B10 science infrastructure — sixth independent review (historical negative verdict)

Date: 2026-10-05. Independent reviewer `/root/b10_science_sixth_fresh_review` assessed the complete I14–I20 branch from `e6da08efc219a0415de6dcd11fac485cf4461f41` through fixed clean head `afff62d382a8e7fbbe5991c5a7ca5a77df6570b5`. Instructions, approved specification/plan/storage amendment, full branch diff, previous reviews and gate ledger were read firsthand. Review was read-only, without delegation, repository mutation, registered dispatch or publication.

**0 BLOCKER / 2 MAJOR / 0 MINOR / 2 unresolved. Local ready to merge: NO. G1–G4 PASS preserved; G5 FAIL.** No additional assessed findings or unfinished material assessment remained. Hosted PR CI, merge, distinct exact-master CI and separate documentation closure were separate pending gates. This historical verdict is not rewritten by later repairs.

## R18 — MAJOR: paired counterpart losses bypass report validation

At reviewed `findings.py:40/78` and `prediction.py:268`, a genuine admitted paired MAE measurement with primary loss approximately .1 and comparison loss approximately .2 accepts a negative, string, object or Boolean `baseline_value`. Reconciliation passes and suite `completed_valid=1`. The admitted primary-loss threshold remains POSITIVE: the defect is acceptance of a malformed counterpart, not that the changed counterpart causes that positive classification. Negative primary and bad denominator controls correctly reject.

Five actual paired targets also accept a negative per-action `baseline_numerator`, Boolean/string per-action mean, and mathematically inconsistent mean42.

Required evaluator-only remedy: emit the total counterpart numerator; validate both methods' top and action numerators/means against the same paired denominator, totals versus strata, opportunities/exclusions/coverage, finite non-Boolean types, nonnegative MAE, accuracy/Brier [0,1], absent-comparison/null rules and five-pair action/conditioned minima. Preserve unclipped normalized load errors above1, actual zero, signed window changes and structured audits. Validation must precede classification, reconciliation and aggregation.

Independent evidence preserved in `/private/tmp/b10-sixth-independent-controls-controlled.json` and `/private/tmp/b10-sixth-counterpart-strata.json`.

## R19 — MAJOR: repeated and lost semantic creation attribution

At reviewed `producers.py:322`, a current-row/source-fingerprint/created-clock match does not establish which actual consolidation run created the semantic memory. Real eight-transition WorldModel sources, original pre-run captures and real consolidation show:

- Actual creation counts [2,0] produce four claimed promotions, including two invented second-run zero latencies.
- Equal run logical timestamps still claim four promotions from two creations; clock matching alone is insufficient.
- A real later source/semantic revision leaves actual creation counts [2,0,0] but reported promotions zero. Original creations remain in history; current fingerprints erase them.

Required evaluator-only remedy: retain original pre-run B4/cutoff evidence; bind creation to original run/source/semantic IDs, revision1, actual created count and original run clocks; resolve revision1 from current or recorded history; deduplicate semantic creation identities. A recorded zero-created run cannot inherit earlier creations. Missing proof remains unavailable.

Existing independently captured original creation telemetry carries run/source/semantic IDs, revision1 and active status. It establishes attribution without changing producer/schema. Pre-run semantic-ID differences are required if relying on before/after deltas, but are an additional cross-check when original authoritative creation events already supply exact attribution. Count plus clock alone is insufficient.

Evidence preserved in `/private/tmp/b10-sixth-semantic-outcomes.json` and controlled original sources/counts in `/private/tmp/b10-sixth-independent-controls-controlled.json`.

## Verification and material controls

Independent complete evaluation: **413 passed in242.02s, exit0**, `/private/tmp/b10-science-sixth-review.log`. Actual author logs at code `7c1d486c` were inspected: evaluation413/repository1296(two existing warnings)/focused156/literal153/seven standalone JSON/compile/pip/whitespace/protected/clean PASS. Changes through reviewed HEAD are documentation only. Inspected author evidence is distinct from independently executed checks.

Independent source/literal controls confirmed A/B coefficients and rest-only320/321 boundary; raw200/no-refill cutoff; persistence/global/action support distinctions; natural versus standardized populations; fifteen actual rest exposures/three windows/transition delay394; original B5 source catches an internally consistent lie; original B8 catches false Q updates/unselected candidates; original B7 has122 distinct claims and counts a false clock once; typed B6 detects False replacing numeric zero; default30 members/33 IDs/3,220 slots, absent642 primary groups/3,210 missing primary slots; real516 runs/1,032 opportunities/928,903 bytes and excess rejection at unchanged2,048 bound. Controls: `/private/tmp/b10-sixth-source-controls.json`, `/private/tmp/b10-sixth-literal-controls.json`, semantic outcomes above.

R1–R17 targeted repairs were supported by inspection, regression and relevant controls. R18 extends R16's primary validation; R19 extends R17's original eligibility-source proof. Targeted repairs alone therefore do not establish exhaustive G5 acceptance. Initial semantic controls used an unbound WorldModel clock; those original attempts remain retained and were superseded by controlled logical-clock evidence, not represented as branch failures. Exact HEAD/clean tree/whitespace and protected-path checks passed; reviewer made no tracked/index/HEAD changes.

## Explicit scope rulings accepted by root

- I31 registered A10/B5/C5/D10 execution, final empirical freeze, efficacy conclusions and favorable performance requirements are unauthorized; technical fixtures only. G5 judges trustworthy definitions, not favorable science.
- I21–I30 artifact publication/readers/replay/re-execution/Astra/browser/release are later gated work; unimplemented layers are not completed here.
- Hosted PR CI, normal merge, exact-master push CI and separate closure publication require distinct exact-head evidence; neither baseline CI nor local tests substitute.
- Installed organism/home, services, live devices, host/network perception and deployment remain untouched and prohibited.
- Cognition/formulas/schema, forced exposure/reranking and utility/reward/Q tuning remain excluded. Both repairs use existing original facts and pure helpers without new learning algorithms or producer changes. No design amendment is required.
- Negative/unavailable producer facts remain evidence. Missing B7 session proof remains unavailable; absent PID claims, frozen projections and lifetime snapshots do not establish extra capabilities or updates.
- Placeholder sizing is not a universal fully populated fit guarantee. The real1,032-opportunity fixture establishes its narrower admission only; actual runtime caps reject excess.
- Approved same-UID native SQLite-open race exclusions, custom VFS/signing/hard isolation, unconditional cross-platform bit identity and inferential statistics remain excluded/deferred.
- Redundant reviewer repository/focused/literal/seven standalone reruns were omitted as requested; actual author logs were inspected and independent commands identified separately.

These exclusions do not excuse R18/R19. Historical negative reviews, failures, missing evidence and unfavorable outcomes remain visible.
