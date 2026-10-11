# Seventh fresh independent full-branch B10 science review

Review complete. Exact base `e6da08efc219a0415de6dcd11fac485cf4461f41`; exact held head `40538507f6cbc3c429bcae07598558542918d288`, branch `seed-0.2-b10-impl-03-science`. This is a read-only review of the complete I14–I20 branch, not a targeted acceptance of R18/R19. No delegation, checkout/index/HEAD mutation, publication, registered experiment, installed-home access or later-layer execution occurred. Scratch evidence is exclusively under `/private/tmp`.

**0 BLOCKER / 2 MAJOR / 0 MINOR / 2 unresolved. G1–G4 preserved PASS; G5 FAIL. Ready to merge: NO.** The owner's required zero-finding gate is not satisfied. Both findings are evaluator-only defects; neither requires DESIGN AMENDMENT REQUIRED or a cognition/schema/formula change. They are independent: malformed reported values can pass final reconciliation even when measurement generation is correct; incomplete captured source inventories can produce incorrect genuine measurement output before reconciliation.

The review consulted the original owner attachment `c509427c-6582-4d1d-8bc0-4aeaa667a930/Pasted text.txt`, approved specification, approved implementation plan and storage amendment, all six historical negative science reviews and the full science gate ledger. It inspected the complete base..head code/test/documentation changes and relevant original B2/B3/B4/B5/B6/B7/B8 producer/schema contracts firsthand. Historical reviews and author gates were treated as evidence/history, not independent acceptance.

## MAJOR R20 — structured measurements are accepted without their value contract

Location: `development/evaluation/metrics/findings.py:39–41`, invoked by `_valid_row` at line 138, `reconcile_output` and suite summarization.

Coverage/support rows validate supplemental paired math but do not validate or bind the actual structured `value`. The catch-all for the other structured IDs requires only a dictionary. Three mandatory engineering metrics additionally require their zero violations/mismatched key, but this does not validate their other counts/structure. The scalar and signed window-change repairs therefore leave the registered structured output contract open.

Independently generated genuine prediction output had two target opportunities, one paired target and `coverage={'seed':0.5}`. Changing only `value` from `{'seed':0.5}` to `{'seed':1.0}` was accepted: reconciliation PASS and suite `completed_valid_count=1`. All supplemental evidence/counts remained unchanged. A support output with methods `action_mean_delta:2` and support `2:2` accepted methods `action_mean_delta:999` and support `999:999`; empty dictionaries were also accepted.

This extends materially beyond prediction coverage/support. Sixteen independently preserved genuine-output mutations across eight metric IDs all passed reconciliation and counted the completed member as valid:

- coverage falsely changed from .5 to 1, and empty;
- support method/frequency counts changed to 999, and empty;
- observed adaptation with 15 rest exposures and completed delay 394 changed to 0 exposures and delay -99, despite its unchanged three five-exposure confirmation windows, and empty;
- original real B4 evidence output with two published beliefs changed to published 999, and empty;
- original real B6 creation latency 9-8=1 changed to -1, and empty;
- original real B6 content-matched count 2 changed to 999, and empty;
- original real B6 status history reactivations 0 changed to -1, and empty;
- a real B7 publication copied with one deliberately wrong load claim produced a truthful `self.unsupported-claims` negative audit (`unsupported=1`, a claim explicitly `supported=False`). Changing only that reported count to 0 concealed the negative audit and was accepted, as was empty.

These are internal contradictions in ordinary bounded evaluation output, not demands for signed artifacts or adversarial author authenticity. The source databases were not repaired or changed by audit. The broad defect follows the catch-all dispatch for structured registered IDs; the eight reproduced IDs are concrete witnesses, not a claim that coverage/support exhaust the scope.

Evidence: `/private/tmp/b10-seventh-structured-controls/evidence.json`; complete originals/mutations and suite/reconciliation results `/private/tmp/b10-seventh-structured-breadth/evidence.json`; executable fixture `/private/tmp/b10-seventh-structured-breadth.py`, stdout `/private/tmp/b10-seventh-structured-breadth.log`.

Impact: false coverage/support/latency/counts and concealed source mismatches can be labeled complete valid science. Preregistered ID/digest/dimension matching does not make an arbitrary payload trustworthy. G5's honest complete reporting gate fails.

Remedy: evaluation-local closed, bounded contracts for every registered structured metric, checking required/allowed fields, exact count/Boolean/finite numeric types, domains, identities, availability and arithmetic. Bind duplicate summary fields to their independent complete counts/evidence; coverage value must equal checked method coverage, support frequencies/method counts must reconcile, observed/censored adaptation must match windows/exposures/horizon, and audit count summaries must preserve actual negative/unavailable evidence. Long reports must use complete aggregate counts/whole-input audit identity, not derive totals from the first-eight diagnostic sample. Preserve real zero, unavailable, censored and negative measurements. Add genuine-output negative controls for the complete registered structured contract rather than repairing only the two prediction dictionaries. No original producer or scientific threshold change is authorized or needed.

## MAJOR R21 — semantic opportunity completeness is not reconciled to captured sources

Location: `development/evaluation/metrics/producers.py:330–411`, particularly the one-sided check at lines 401–403; associated publication-based scope filtering in `_scoped_source` lines 766–775.

The promotion audit iterates only supplied auxiliary eligibility events. It rejects duplicates and over-counts relative to actual run eligible count, but never establishes that all independently captured eligible examined sources are represented, nor accounts for omitted original creations. Original creation events can be complete and correct while a smaller supplied opportunity list yields a smaller supposedly complete metric.

Independent real-producer control: eight actual rest transitions through original Memory/WorldModel published two B4 source rows (global and rest-action), each with evidence count 8/confidence .4. Original Consolidator at logical time 9 recorded `source_beliefs_examined=2`, `eligible_beliefs=2`, `created_count=2`, actual examined IDs [1,2], and two original creation telemetry records. Complete pre-run source versions at time 8, all run rows, all original creation events and both publications were captured independently.

The honest measurement was MEASURED with two eligible opportunities and two latency-1 promotions. Removing only one `semantic_eligibility_history` event, retaining every original source/run/event/publication, yielded MEASURED with one eligible opportunity, one promotion, no exclusion reason and reconciliation PASS / suite `completed_valid_count=1`. This reproduction uses unmodified original producer output; it is not fabricated favorable cognition.

Evidence: `/private/tmp/b10-seventh-source-inventory/evidence.json`, including original run/source facts and both outputs; `/private/tmp/b10-seventh-source-inventory.py`; corrected successful execution `/private/tmp/b10-seventh-source-inventory.retry.log`. Before/after `iterdump` equality confirms the audit did not mutate the source DB.

Scoped negative control: original B4 again created two threshold-eligible sources. The actual original Consolidator with load .9 was suppressed for high_load, examined no sources, created none and published no semantic rows. This is a genuine unpublished-source/resource-suppressed control; it is not a claim that a completed successful original eligible new source inexplicably fails to publish. The unscoped metric correctly returned UNAVAILABLE / NO_ELIGIBLE_CONSOLIDATION_OPPORTUNITY with two not-an-actual-opportunity exclusions. Action=rest and/or signal=load_ratio filtered auxiliary opportunities through existing semantic publications, erased both source facts and returned MISSING_ELIGIBILITY_HISTORY with no exclusions. This scope consequence is included in R21, not counted as a third finding or alleged false favorable measured result. Original successful unsuppressed new eligible sources are created; no impossible producer outcome was invented.

Scoped evidence: `/private/tmp/b10-seventh-unpublished-scope/evidence.json`, original source/run and four outputs; `/private/tmp/b10-seventh-unpublished-scope.py` and `.log`; audit DB equality preserved.

Impact: an omitted source can disappear from promotion denominator and output without missing-evidence qualification; action/signal source populations depend on having a publication, so negative or suppressed source facts can disappear. G5 source fidelity/completeness fails even when the final reporting validator receives genuinely generated rows.

Remedy: independently derive the expected bounded source/run opportunity inventory from original pre-run captured source versions, actual examined IDs/run outcome/cutoff, thresholds and resource evidence. Match supplied events one-to-one and explicitly account for every expected source/creation with valid promotion, reasoned exclusion, or unavailable/inconsistent evidence. Partial/missing auxiliary inventory must not become a smaller complete denominator. Scope eligible/excluded sources using captured source identity/action/signal, not presence of a semantic publication. Global recorded eligible counts cannot simply be equated to a filtered action/signal count: validate the global original inventory and independently establish its scoped subset. Preserve genuinely suppressed/failed/no-created/unchanged/revised outcomes and original revision-one proof; no forced consolidation, source editing or producer behavior change.

## Independent execution and inspected author evidence

Ran the required complete evaluation suite once, serial, at the held head:

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/private/tmp/b10-science-seventh-review tests/evaluation`

**460 passed in 242.42s, exit 0**; wrapper runtime 242.720361 seconds. Full command/head/stdout/stderr/exit/runtime are preserved in `/private/tmp/b10-science-seventh-review.log`. This independently executes all foundation/protocol/science regression cases, including the actual R18 paired-counterpart and R19 original-creation cases; it does not detect R20/R21.

Separately inspected actual serial author orchestration `/private/tmp/verify_b10_science_R18_R19_final.py` and logs at exact code `14c8bf65020ead1d321180f78854bd467ba1c389`:

- evaluation 460 passed / 298.19s;
- repository 1343 passed / 318.08s, two existing Starlette HTTPX/AnyIO deprecation warnings;
- eight focused science modules 203 passed / 85.39s;
- separate literal/adversarial node/module selection 200 passed / 85.07s;
- seven standalone regressions baseline, prediction_error, world_model, curiosity, semantic, self_model, decision: actual output JSON independently parsed as dictionaries; every corresponding stderr file empty;
- compileall / pip check / whitespace / protected scope / clean source recorded successful; pip output “No broken requirements found.”

These are inspected author executions, not claimed reviewer reruns. Code14c8bf6..held HEAD changes only four bookkeeping documents. No redundant full repository/focused/literal/standalone run was performed, in accordance with the review request. No registered default suite was frozen or dispatched.

Failure evidence retained: the first standalone scratch source-inventory script invocation lacked `PYTHONPATH=.` and exited with ModuleNotFoundError for tests before constructing the fixture; `/private/tmp/b10-seventh-source-inventory.log` remains intact. The corrected invocation passed and has a separate retry log. Historical mixed-path fixture-discovery errors, C poll timeout attempts and other author RED/harness failures remain in ignored logs and historical records; this review does not erase them or reinterpret a passing retry as an absent failure. No timeout/resource/core changes or hidden exclusions were made.

## Full-branch breadth and limitations

I14 A/B: inspected literal action-dependent .50/.40/.60/.55 outcomes, declared detached resets/common battery/disk/network/hour facts, online/frozen lengths, hidden rest-only change at 321 and unchanged other effects. Real selector remains unforced; absence of rest exposure remains scientifically unavailable. Private engine/truth does not enter worker input or producer defaults. Independent evaluation includes literal/reset/invalid phase/action/no-forced-selection cases.

I15 C: construction uses 128 actual permitted producer transitions, original B4 contradiction/lifetime records and B6/B7 producer publications. Cold has no invented source; source-unavailable setup retains the source row and edits only the declared pre-freeze robustness fixture; stale time is +301 transported through the closed real frozen WorkerHandle. Four variant probes remain immutable with actual whole-table/database-byte checks. Setup mutations are not frozen learning claims. Aggregate four-clone/generating storage admission and missing/null distinctions remain enforced.

I16 D: eight declared contexts preserve omitted/null resources; original equality .8/20/10 guards versus just-over/under and unknown resource restrictions are independently referenced. Real epsilon1/alpha.18 counterpart starts from cloned equal state and independently learns/selects; it is not forged exploitation or paired prediction samples. Utility is evaluator-only, never legacy reward/Q or eligibility. Original actual Q/decision linkage and complete pair/equal-start qualification remain audited.

I17/I18: permitted raw200 history/cutoff/filter/no-refill/current/future exclusion is retained. The four-row literal genuine B2 .40 versus persistence/global .50 with support2/4 is preserved. Boolean frequency supplies genuine probability, support confidence does not. Primary MAE uses fixed scale100 percentage/1 load with unclipped loss; both methods use paired intersection and retained standalone coverage/reasons/action strata. Five-paired-target action summary minimum and same qualifying action set for standardized early/late remain distinct from natural mix. R18's finite/domain/math/null/both-numerator/per-action counterpart checks are present and executed independently; actual zeros and normalized losses>1 remain valid. R20 concerns the still-unchecked structured values.

Adaptation: whole-horizon carrier retains the already prepared rest candidate immediately before 321 without forcing its selection. Only actual postshift rest exposures occupy positions; missing/fallback entries break window qualification. Support2, five paired exposures/window, three consecutive windows and tolerance.02 remain fixed. Insufficient prechange evidence, sparse horizon and actual right censoring remain distinct; all-action completed delay is separate from rest-exposure delay. Unrelated horizons/populations are inapplicable, not silently relabeled.

I19: original B4 lifetime means/counts/contradictions remain unchanged. Original B5 component math is checked separately against captured B3/prior B4 and confirmed B1 evidence, not merely recomputed internal arithmetic. B6 typed normalization rejects Boolean-for-numeric tricks, checks current/historical source content and actual ordered history/status/reactivation chains. Original revision-one creation content, telemetry source/run/semantic identity and counts survive later revisions; equal-clock/created0 subsequent runs do not repeat old creations. These positive R19 cases and missing/wrong event/source/clock/history controls passed in the independent complete evaluation. R21 exposes incomplete source opportunity accounting independently of those identity checks. B7 distinct claims and complete captured component/status/clock/cutoff references retain wrong/missing/error claims in denominators; publication session proof missing remains explicitly unavailable. B8 all candidate guards/Q snapshots, actual selected update/state/action/transition linkage, digest and scoped skipped-attempt inventories remain separate from reranking or utility recalculation.

I20: independently constructed default_plan without dispatch and counted all **33 IDs, 30 members, 3220 slots**, family counts A10/B5/C5/D10 and protocols prequential20/frozen10. Fixed A1–40/361–400 and B281–320/321–360/761–800 windows, applicability, exploratory separation and complete failed/incomplete/absent seed accounting remain explicit. Default empirical classification thresholds are empty/descriptive, not invented successes; support/event/guard thresholds are version-bound definitions. Invalid scalar/ID/dimension/inventory/classification reports reject. R20 means structured invalid values can still enter a completed valid member.

Capacity: independently executed complete evaluation includes the actual 1032-opportunity/516-real-run fixture, preserving all-input fact counts/digest and bounded first-eight non-inferential diagnostic sample. It establishes that concrete narrower capacity, not universal 2048-opportunity/default-suite fit. The original 2048 opportunity/source bound remains enforced; exceeding it rejects, rather than pruning data, changing bounds or promoting placeholder admission into actual-fit proof. Frozen/lifetime/source-at-capture restrictions remain disclosed.

Documentation: current authority/status paragraphs match owner's I14–I30 engineering authorization while retaining I21+ predecessor waits and I31 empirical prohibition. Technical specification/plan changes in this branch are status/authority-only. Six negative reviews and repair/failure histories remain preserved; docs do not claim independent final acceptance, G5 closure, PR/hosted merge or empirical efficacy.

## Protected state and gate rulings

Complete base..head scope is 38 files / 4717 additions / 31 deletions, confined to development/evaluation, tests/evaluation and approved documentation. Git ls-tree blob/tree inventories were independently compared base..head for seed (24 files), .github (1), docs/baselines (9) and requirements-lock.txt (1); identical exact Git object IDs/modes/paths establish protected byte identity. Absent requirements.txt, pyproject.toml, package.json and package-lock.json also remain absent. Schema migrations are unchanged within protected seed. Worktree/index remained clean; git diff --check base..head exited 0; exact held HEAD verified before and after. No installed organism was opened. Coordinator.dispatch still raises FOUNDATION_ONLY_DISPATCH_DISABLED.

- G1 PASS preserved: protected core/schema/dependencies and trusted-code capability/storage/dependency gates regressions pass; approved SQLite native-open limitation retained.
- G2 PASS preserved: closed worker/control truth boundary, detached permitted observations, private scenario ownership and leakage regressions pass.
- G3 PASS preserved: actual original cycle, pre-update durable point checkpoint/constant ACK, original B3 result and actual update/failure fidelity regressions pass. New source capture is downstream audit, not cognition feedback.
- G4 PASS preserved: complete frozen raw tables/DB bytes, denied mutations, permitted read-only transaction behavior and transported stale projection regressions pass.
- G5 FAIL: R20 and R21 prevent trustworthy complete measurement/source/reporting definitions. A green engineering test suite is not zero-finding review or empirical success.

## Explicit declined-scope rulings

1. I31/default A10/B5/C5/D10 empirical execution, final empirical freeze/dispatch, efficacy/superiority/intelligence/consciousness or favorable organism performance: unauthorized and not judged; G5 concerns laboratory definitions/reporting integrity.
2. I21–I25 artifact publication/reader/projection/replay/re-execution, later Astra/browser/I30 release and B11–B16: later sequential work, not implemented or executed here. Construction of an inert default inventory is not an experiment.
3. Hosted exact PR-head/master/closure CI, PR creation, merge, publication and documentation closure: separate later gates; no hosted claim made and none executed.
4. Installed/live SEED, host sensors/network actions, service/browser/deployment/live-device validation: prohibited; no installed-home access or empirical live validation performed.
5. Cognition/schema/dependencies/formulas/tuning, altered reward/Q/eligibility, forgetting/regime reset, rescheduled consolidation or forced exposures/seeds: declined; negative producer findings remain evidence. Both fixes can stay evaluation-local.
6. Missing independent publication-session evidence, absent B7 PID claim, frozen mutation suppression, bounded/capped counts, lifetime-at-capture semantics, missing/unproved partial source scopes: limitations retained, not invented evidence or producer repair. Scoped source-loss in R21 remains actionable despite those limits.
7. Placeholder/default admission or 1032 fixture extrapolated as universal fit: declined. Actual bounds/excess rejection remain required; no resource enlargement or hidden truncation justified.
8. Adversarial concurrent same-UID SQLite native-open races, native VFS, signed authenticity and OS/hostile-code sandboxing: approved explicit exclusions/deferred; ordinary unsafe paths, trusted-code routing and detected mismatches remain in scope. These exclusions do not excuse internally inconsistent structured output or missing source accounting.
9. Cross-profile/platform bit identity, signing-based authenticity and inferential statistics/generalization/NHST: not promised, separately deferred; this local run does not establish them.
10. Redundant reviewer full repository/focused/literal/standalone reruns: deliberately omitted per request; actual author logs were inspected, while complete evaluation and additional bounded technical controls were independently executed.

The assessment is complete, with the two material findings unresolved at the held head. No additional blocker/major/minor finding was established. Repair followed by a new fresh complete assessment is required before a zero-finding/G5/merge acceptance claim.
