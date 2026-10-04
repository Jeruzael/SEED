# B10 I09–I13 protocols publication and closure — 2026-10-04

Canonical branch point: clean verified local/remote `master d0a5da528611af1526723b3ec04f6a86b3d1d1c8`. Protocol branch: `seed-0.2-b10-impl-02-protocols`. This separate `docs/b10-protocols-closure` branch starts from verified protocol master `4fce86257a4b35e1d8bd1e9c140d1a83f239a108` and changes documentation only.

## Task, review and gate evidence

[G3/G4 engineering gate record](../evaluation/engineering-gates.md) contains exact I09–I13 files/task commits/focused checks, durability/parity/raw-immutability/failure evidence, all four original findings and separate repair commits, and retained RED/repair history. [Initial complete-diff review](2026-10-04-b10-protocols-review.md) at `6fb1aac95034ba04558e10b7509605fdd35b30fd` remains byte-identical: 0 BLOCKER / 3 MAJOR / 1 MINOR / 4 unresolved; G3 FAIL. It is historical evidence, not rewritten acceptance.

[Fresh repaired-head complete-diff review](2026-10-04-b10-protocols-final-review.md) at `2be1e6feb660d81f189098ef62f92631a115631f`: **0 BLOCKER / 0 MAJOR / 0 MINOR / 0 unresolved**, R1–R4 RESOLVED, **G1/G2/G3/G4 PASS**. The reviewer independently ran all 257 evaluation tests (91.48s) and additional six-case ancestor-preserving-inode journal faults, actual consolidate+flush failure capture, unknown-response ACK/null, raw JSON/PID lexical poison and real freeze cleanup probes. The accepted documentation-only overlay at final PR head `f835a8d06bbba234cf717dcf189cd85959133845` has zero findings and preserves both reports.

Task/repair history is retained without squash. I09–I13 delegate original producers with no cognition fork. G3 proves capture prediction/outcome → approved point score → append/flush/fsync → constant SCORE_ACK → original current learning. Original-cycle control compares all four actions and eight-cycle maintenance, all raw tables/IDs/producer payloads, excluding only audited actual PID scalar spans. The actual pre/post-ACK failure ladder preserves confirmed/unconfirmed producer prefixes and prior effects; no rollback, automatic retry or relearning.

G4 uses the separate immutable reader/facade, mode=ro/query_only/write-denying authorizer, complete table/schema/sqlite_sequence/operational/raw JSON and DB-byte equality, fixed 200-row training cutoff, and explicit FROZEN_SELECTION_ASSAY reflect/consolidate labels with internal mutation suppressed. Freeze admits only successfully closed original-owner state; failed cleanup cannot publish a trusted fixture. G1/G2 remain preserved within the owner-approved Option B trusted-code storage contract; native hostile same-UID SQLite-open prevention is outside that contract.

## Final local verification

| Check | Actual result |
| --- | --- |
| Full repository, no exclusions | **1140 passed / 2 existing warnings**, 120.63s |
| Complete evaluation, no exclusions | **257 passed**, 110.50s |
| Separately selected checkpoint/cycle/frozen/online/parity/failure critical suite, no exclusions | **101 passed**, 82.36s |
| baseline, prediction_error, world_model, curiosity, semantic, self_model, decision standalone regressions | **All seven PASS**, JSON checked; disposable homes |
| Author doc links/fences, complete scope and diff hygiene | PASS |

All author RED/failure/repair/final-check logs remain in ignored `.superpowers/b10-protocols/`. These are technical regression fixtures, not B10 scientific experiments. Existing warnings are the prior Starlette HTTPX TestClient and AnyIO BlockingPortal deprecations.

## Protocols PR and normal merge

[Protocols PR #24](https://github.com/Jeruzael/SEED/pull/24): `seed-0.2-b10-impl-02-protocols` → `master`; exact base `d0a5da528611af1526723b3ec04f6a86b3d1d1c8`; exact head `f835a8d06bbba234cf717dcf189cd85959133845`; normal merge `4fce86257a4b35e1d8bd1e9c140d1a83f239a108`. All task/repair/documentation commits preserved. Exact merge tree equals independently reviewed PR tree; local Git merge object imported and verified byte-for-byte through its hash because terminal SSH transport is unavailable.

**Exact protocols PR-head CI:** [37155625889](https://github.com/Jeruzael/SEED/actions/runs/37155625889), event `pull_request`, exact head `f835a8d06bbba234cf717dcf189cd85959133845`, **SUCCESS**.

| Required job | Exact job ID | Conclusion |
| --- | --- | --- |
| test (macos-py313) | `111298301786` | SUCCESS |
| test (linux-py313) | `111298301927` | SUCCESS |
| test (linux-py311) | `111298302003` | SUCCESS |

Full-suite steps succeeded in all three jobs. Seven standalone scenarios succeeded on Linux/macOS Python 3.13; Python 3.11 retains the configured scenario skip. Workflow checks out exact PR head, not synthetic merge; PR CI is not reused as master CI.

**Separate exact post-merge master push CI:** [37189929244](https://github.com/Jeruzael/SEED/actions/runs/37189929244), event `push`, exact head `4fce86257a4b35e1d8bd1e9c140d1a83f239a108`, **SUCCESS**.

| Required job | Exact job ID | Conclusion |
| --- | --- | --- |
| test (linux-py311) | `111399804700` | SUCCESS |
| test (macos-py313) | `111399804746` | SUCCESS |
| test (linux-py313) | `111399804786` | SUCCESS |

Full-suite steps succeeded in all three jobs. Seven standalone scenarios succeeded on Linux/macOS Python 3.13; Python 3.11 retains the configured scenario skip. Workflow checks out exact PR head, not synthetic merge; PR CI is not reused as master CI.

## Preservation and scope

`seed/** NONE`; `schema v7 unchanged`; `dependencies none added`; dependency lock, workflows, baseline artifacts and approved roadmap unchanged. No evaluator table/migration in learner DB, APIs/UI, registered scientific families/full A–D suite, I14+ artifact/replay infrastructure, installed-home access or deployment. **NO B10 EXPERIMENTS EXECUTED. INSTALLED SEED UNTOUCHED. DEPLOYMENT NOT PERFORMED.**

## Separate documentation closure verification

This record is authored only after exact protocols merge/master CI succeeded. Its own `docs/b10-protocols-closure` PR must pass exact PR-head CI, normal merge and separate exact-master push CI, all three required jobs, and docs-only/clean-tree verification. Those future self-referential identities cannot be embedded into the commit that generates them; they are recorded separately in the final owner publication report and retained audit ledger. Protocol CI and older documentation CI cannot substitute for closure CI.

The following final status becomes effective **only after both exact closure PR/master CI gates pass**:

```text
B10 I09-I13 PROTOCOLS COMPLETE / VERIFIED
G1 PASS
G2 PASS
G3 PASS
G4 PASS
B10 OVERALL IN PROGRESS
B10 ENGINEERING IMPLEMENTATION IN PROGRESS
I01-I08 COMPLETE / VERIFIED
I14-I30 NOT STARTED / NOT AUTHORIZED
I31 NOT STARTED / NOT AUTHORIZED
B10 EMPIRICAL EVALUATION NOT STARTED / NOT AUTHORIZED
NO B10 EXPERIMENTS EXECUTED
INSTALLED SEED UNTOUCHED
DEPLOYMENT NOT PERFORMED
```

**Mandatory STOP follows verified closure.** No science-infrastructure branch, I14–I20 implementation, registered suite or empirical execution follows under this authority. The next phase requires a separate owner instruction.
