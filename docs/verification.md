# Reproducible SEED verification

This guide covers current local verification and the GitHub Actions workflow introduced after B6. B8 adds the seventh deterministic decision scenario.
The [hardening record](reviews/2026-09-23-post-b6-hardening.md) distinguishes fresh
local evidence from historical B6 results and pending hosted checks.

## Local environment and evidence

Use Python 3.11+ in a separate environment or a suitable existing `.venv`.
Install **requirements-lock.txt unchanged**. Do not upgrade pip/packages, unpin
versions or remove a supported matrix entry to hide an installation failure.
A failed installation blocks dependent checks and must be reported.

The existing tests use temporary synthetic homes and mocked sensor boundaries.
Still set a new temporary SEED_HOME for each verification session. Never point
these commands at installed memory or run install.sh, main.py or LaunchAgent
controls as part of verification.

From the repository root, the following Bash commands preserve failure status and
keep outputs in the ignored evidence directory. Choose a new output subdirectory
when preserving an earlier run for comparison.

```bash
bash <<'BASH'
set -euo pipefail
mkdir -p .review-artifacts/local/scenarios
export SEED_HOME="$(mktemp -d "${TMPDIR:-/tmp}/seed-verify.XXXXXX")"
trap 'status=$?; printf "%s\n" "$status" > .review-artifacts/local/session.exit; exit "$status"' EXIT
.venv/bin/python --version 2>&1 | tee .review-artifacts/local/python.log
.venv/bin/python -m pip install -r requirements-lock.txt 2>&1 | tee .review-artifacts/local/dependencies.log
.venv/bin/python -m pip check 2>&1 | tee .review-artifacts/local/pip-check.log
.venv/bin/python - <<'PY'
import hashlib, json, platform, subprocess, sys
from pathlib import Path
result = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
              checked_out_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              dirty_tree=subprocess.check_output(['git','status','--porcelain=v1'],text=True),
              lock_sha256=hashlib.sha256(Path('requirements-lock.txt').read_bytes()).hexdigest())
Path('.review-artifacts/local/environment.json').write_text(json.dumps(result,indent=2)+'\n')
PY
.venv/bin/python -m pytest -q --junitxml=.review-artifacts/local/pytest.xml 2>&1 | tee .review-artifacts/local/pytest.log
for scenario in baseline_scenario prediction_error_scenario world_model_scenario curiosity_scenario semantic_scenario self_model_scenario decision_scenario; do
  .venv/bin/python -m "tests.${scenario}" > ".review-artifacts/local/scenarios/${scenario}.json" 2> ".review-artifacts/local/scenarios/${scenario}.stderr.log"
  .venv/bin/python -m json.tool ".review-artifacts/local/scenarios/${scenario}.json" > /dev/null
done
git diff --check
BASH
```

Run the interpreter/version and environment capture even when investigating a
failed dependency setup; missing test/scenario files mean those checks did not
complete. JSON validation alone is not a behavior comparison: investigate every
difference against a saved pre-change run and the relevant historical artifact.

Do not overwrite files under [baselines/](baselines/). Historical post-B6 hardening preserved scenario behavior. B8 intentionally changes autonomous selection; `tests/scenario_compatibility.py` checks explicit hand-derived changes and compares every other field. The semantic
scenario renames current source digests from unchanged_b5_source_sha256 to
source_sha256 because the authorized body parser correction changes body.py.
Its regression test still compares every behavioral field and the remaining source digests exactly; B8 additionally changes predictor.py to share batch inference. An environment-dependent footprint or a later approved
metadata difference must be explicitly explained, not broadly ignored.

## Hosted workflow

[seed-ci.yml](../.github/workflows/seed-ci.yml) runs on pull requests targeting
master, pushes to master, and manual dispatch. It does not use pull_request_target.
The job has contents: read only, no repository secrets or deployment credentials,
and checkout credential persistence disabled. Superseded runs are cancelled;
each job has a 20-minute timeout. Matrix fail-fast is disabled so one failing
entry does not cancel the others. No failure is made non-blocking.

| Matrix ID | Runner label | Python | Checks |
| --- | --- | --- | --- |
| linux-py311 | ubuntu-24.04 | 3.11 | Locked install, pip check, full pytest suite (including scenario tests) |
| linux-py313 | ubuntu-24.04 | 3.13 | Same checks plus seven standalone scenario commands and JSON validation |
| macos-py313 | macos-15 | 3.13 | Same checks plus seven standalone scenario commands and JSON validation |

PR runs explicitly check out `github.event.pull_request.head.sha`; push/manual
runs use `github.sha`. This satisfies the closure requirement that artifact
checked_out_sha equals the PR head, rather than GitHub's synthetic merge SHA.
The event SHA is recorded separately. See the official
[checkout head example](https://github.com/actions/checkout#checkout-pull-request-head-commit-instead-of-merge-commit).

Labels were checked against the official [runner-image inventory](https://github.com/actions/runner-images#available-images).
Each run records its exact Python/platform/machine, runner image identifiers,
checked-out SHA, event SHA, dirty-tree status and lock SHA-256. A matrix label is
not evidence of having executed that environment. The macOS job also uses synthetic
homes; it is not an installation or real-device sensor test.

### Action provenance

Official release tags were resolved through the corresponding repository's Git
ref API on 2026-09-23. Each resolved to a commit object; action.yml was read at that
commit. Human-readable release versions annotate the full pins in the workflow.

| Official action release | Pinned commit |
| --- | --- |
| [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | 3d3c42e5aac5ba805825da76410c181273ba90b1 |
| [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0) | 5fda3b95a4ea91299a34e894583c3862153e4b97 |
| [upload-artifact v7.0.1](https://github.com/actions/upload-artifact/releases/tag/v7.0.1) | 043fb46d1a93c77aae656e7c1c64a875d1fc6a0a |

These actions use their Node 24 runtime on GitHub-hosted runners; they do not add
a Node dependency to SEED's core. Future updates must resolve and inspect official
release commits again rather than copying an unverified hash.

The workflow follows GitHub's guidance on [Python testing and artifacts](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
and [full-SHA pins and least privilege](https://docs.github.com/en/actions/reference/security/secure-use).

### Failure evidence and artifacts

Shell steps use set -euo pipefail. Dependency installation, pip check and pytest
logs preserve pipeline failures. Exit traps save numeric status; scenarios stop
on a failed command or invalid JSON. Step outcomes explicitly record success,
failure or skipped. A skipped scenario step is not a successful scenario run.

Outcome recording and artifact upload use always() without masking prior failure.
Only `.review-artifacts/ci/` is uploaded: environment metadata, dependency logs,
pytest log/JUnit, exit files, step outcomes and scenario JSON/stderr. The directory
contains generated verification outputs, not homes, databases, backups, tokens,
credentials or the whole checkout. Its explicit hidden-directory inclusion is
limited to that path. Artifact names include the matrix ID and run attempt;
retention is 14 days. No evidence artifact is a deployment package.

## Status and owner-controlled merge checks

The macOS test-isolation correction in [PR #9](https://github.com/Jeruzael/SEED/pull/9)
passed [SEED verification run 35883121881](https://github.com/Jeruzael/SEED/actions/runs/35883121881)
on 2026-09-23 for commit cb70d004ac128390e29a2d72d9ae6aa1fc30c4bf.
All three job artifacts were downloaded and inspected: 542 tests each, zero
failures/skips, matching checkout SHA and lock hash, clean checkout, successful
locked installation/pip check, and all five scenarios on each 3.13 job. The 3.11
standalone-scenario step is intentionally disabled by the unchanged matrix;
its full pytest suite still includes scenario tests. No failure was hidden.

Exact observed check names, which the owner should require on master:

- `test (linux-py311)` — ubuntu-24.04, Python 3.11.16
- `test (linux-py313)` — ubuntu-24.04, Python 3.13.15
- `test (macos-py313)` — macos-15 (15.7.9 arm64), Python 3.13.15

The linked PR records the current final head and its matching run/artifact audit,
including any subsequent evidence-only documentation commit. A successful run
for an earlier commit does not verify a later head. The documentation follow-up
must also pass all three jobs before the final closure handoff.

The earlier PR #8 macOS run failed a host-dependent stale-runtime unit test and
skipped scenarios; its Linux jobs passed. PR #8 merged without waiting for a
passing macOS gate. The correction injects process state in tests and leaves
production lifecycle logic and the workflow unchanged.

Required-check enforcement remains an owner-controlled repository setting.
Review repository Settings → Rules / Branches and existing rules before requiring
the observed checks, subject to permissions and plan support. No rule, visibility,
billing or permissions change was made. Initial detailed protection/ruleset reads
were restricted; documentation does not establish enforcement. See
[GitHub repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

Hosted synthetic macOS verification is not installation or live-device validation.
The installed organism remains untouched. Deployment and B7–B10 are outside this
correction; B7 needs separate owner authorization after source/CI closure.


## B7 verification checkpoint

**B7 is VERIFIED at source/CI level**, following [PR #10](https://github.com/Jeruzael/SEED/pull/10) and post-merge [SEED verification run 36104979944](https://github.com/Jeruzael/SEED/actions/runs/36104979944) on master `ab7c2b45508828685fc9b0a65807e08cee1cff98`. GitHub confirms all three jobs completed successfully:

| Exact check | Python | Tests | Standalone scenarios |
| --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 646 passed | Not configured; full pytest includes scenario tests |
| `test (linux-py313)` | 3.13.15 | 646 passed | All six passed |
| `test (macos-py313)` | 3.13.15 | 646 passed | All six passed |

Both 3.13 jobs passed `baseline_scenario`, `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`, `semantic_scenario` and `self_model_scenario`. The supplied artifact-inspection record confirms all three checkouts matched the merge SHA, had an empty `dirty_tree`, dependency installation exit 0, successful pip check, pytest exit 0 and an unchanged requirements-lock.txt hash. Seven historical B0–B6 artifacts remain unchanged.

See the [final closure record](seed-0.2-development-plan.md#b7-hosted-verification-closure--2026-09-25). Deployment/live-device validation remains **NOT PERFORMED**, the low-disk decision mismatch remains **OPEN**, and B8–B10 remain **NOT STARTED**. These results verify the stated merge commit, not a later documentation PR head.

## B8 local verification — 2026-09-28

B8 is implemented on `seed-0.2-b8`, from reviewed amended design `4c24d7e`.
The current local Python is **3.13.15**. With a fresh temporary `SEED_HOME`, the
full suite passed **747 tests**, zero failures/skips, with the same two existing
Starlette/httpx/anyio deprecation warnings. `pip check` reported no broken
requirements; no dependency or lock changes were made. Core standard-library-only
execution remains covered by the `python -S` regression. Compileall and
`git diff --check` pass.

All **seven** standalone scenario commands above completed with strict JSON.
The B8 scenario repeated byte-for-byte and matched
[seed-0.2-b8-comparison.json](baselines/seed-0.2-b8-comparison.json).
All eight B0–B7 artifact files match `4c24d7e` byte-for-byte. Learner, sensors,
prediction-error math, world model, curiosity/attention, semantic engine, settings,
commands and requirements-lock sources also match that base. B8 intentionally
changes prediction organization and autonomous eligibility/selection; historical
comparison exceptions are explicit in `tests/scenario_compatibility.py`.

Both complete amended-spec examples pass the implemented strict reader contract:
healthy **4,195 bytes** with digest
`4e37f7a1986ae0c28236684ed04cd8865f121082d1d3a4893c5cbc202c28d1a9`,
and degraded **4,292 bytes** with digest
`4dc446ec70f9233e55914f9d25157da1d6ccf9b4b0bb8979642a87cb980732de`.
Record and selected-prediction serializers retain their distinct separators.

Independent review found two Important reader issues and no Critical issues.
Six regressions failed before correction and passed afterward: contradictory
stored policy-support/failure provenance is rejected without rescoring, and invalid
UTF-8 scalar evidence becomes one corrupt page slot instead of a whole-page error.
No review findings are deferred. Tests also exercise VM budgets, cleanup failures,
interrupt preservation, full-page/response limits, rollback, retained-v6 B7
snapshots, stop precedence and bounded nonfatal stale retries.

Local evidence is retained under `.review-artifacts/b8-final/` (ignored).
At that local-only checkpoint, hosted CI, branch publication and a PR had not yet
occurred. Hosted acceptance subsequently passed for implementation SHA `acaccce`,
as recorded below. That result does not cover this later documentation update.
B8 remains IMPLEMENTED pending final-head checks, owner-directed merge and exact
post-merge master verification. Installation, live-memory migration and restart
remain NOT PERFORMED; B9–B10 remain unauthorized and unstarted.


## B8 PR-head hosted verification — 2026-09-28

[PR #12](https://github.com/Jeruzael/SEED/pull/12), from `seed-0.2-b8` to `master`, is open and unmerged. Implementation head `acaccce889b18d165252c6977d41e5113e74e681` passed [SEED verification run 36407866250](https://github.com/Jeruzael/SEED/actions/runs/36407866250). Master remains at `92e6aa47ec01d80e123e1c9a90c10f9e59e367fb` (B7/schema v6); the feature branch implements schema v7.

| Exact check | Python | Tests | Standalone scenarios |
| --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 747 passed; 2 existing warnings | Intentionally not configured |
| `test (linux-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |
| `test (macos-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |

Artifact IDs are `10963505882` (Linux 3.11), `10963101024` (Linux 3.13), and `10962179746` (macOS 3.13). The supplied artifact-inspection record confirms exact checkout SHA `acaccce889b18d165252c6977d41e5113e74e681`, empty `dirty_tree`, dependency and pytest exit codes 0, successful pip check, and unchanged lock hash `1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769` on all three jobs. Both Python 3.13 artifacts confirm scenario exit 0, empty scenario stderr, and byte-identical outputs for all seven scenarios listed in the local reproduction commands. GitHub run/job metadata, logs and artifact IDs were corroborated during this cleanup; artifact-content findings are attributed to that supplied inspection record.

**This verifies the stated implementation PR head only. It does not verify the future merge commit on master or the subsequent documentation commit.** The latter must receive its own three successful exact checks; expected results remain 747 tests per job and seven standalone scenarios on both Python 3.13 jobs. B8 remains **IMPLEMENTED, NOT YET VERIFIED**. PR #12 must not merge without owner direction; exact post-merge master verification is still required. Deployment/live-device validation is **NOT PERFORMED** and B9–B10 remain **NOT STARTED**.


## B8 post-merge verification closure — 2026-09-29

**B8 is VERIFIED at source/CI level on master `e0075e21f545921324aa5d5c9e2f4217b0a06cca`, schema v7.** [PR #12](https://github.com/Jeruzael/SEED/pull/12) merged from final documentation head `a8760bd2fab33c185ff25945bf74f31934666143`. Exact [post-merge run 36443249417](https://github.com/Jeruzael/SEED/actions/runs/36443249417) (`SEED verification`, event `push`, `head_sha = e0075e21f545921324aa5d5c9e2f4217b0a06cca`) completed **SUCCESS**. This closure records the Sep 28 merge/run checkpoint; the local and PR-head sections above remain historical evidence.

| Exact check | Python | Tests | Standalone scenarios |
| --- | --- | --- | --- |
| `test (linux-py311)` | 3.11.16 | 747 passed; 2 existing warnings | Intentionally not configured by matrix |
| `test (linux-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |
| `test (macos-py313)` | 3.13.15 | 747 passed; 2 existing warnings | All seven passed |

Both Python 3.13 jobs passed `baseline_scenario`, `prediction_error_scenario`, `world_model_scenario`, `curiosity_scenario`, `semantic_scenario`, `self_model_scenario`, and `decision_scenario`.

| Hosted artifact | Artifact ID | SHA-256 digest |
| --- | --- | --- |
| Linux Python 3.11 | `10978873702` | `fc928359b4ff8a8b723b412a3abed07734c0870be1e10c0f2da6d4469a7b9a43` |
| Linux Python 3.13 | `10978124787` | `da9ac8764e56b0df48c7a022bc9854deaf3e756506e26592bd6268382f9563ae` |
| macOS Python 3.13 | `10979428432` | `86e0c061282f17c69e97da615306958a31380b20a78b2cbff6673ca581fbb5b8` |

The owner-supplied post-merge artifact-inspection record confirms:

- All three `checked_out_sha` and `event_sha` values equal `e0075e21f545921324aa5d5c9e2f4217b0a06cca`; each `dirty_tree` is empty (`""`).
- Every job has `dependencies.exit = 0`, `pytest.exit = 0`, and successful `pip check`.
- The requirements-lock SHA-256 remains `1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769`.
- Both Python 3.13 artifacts have `scenarios.exit = 0`. All seven Linux/macOS scenario JSON outputs are byte-for-byte identical, and all fourteen scenario stderr logs are empty.

During this closure, GitHub PR/merge identity, run event/head/success, exact job names, Python versions, 747-test results, scenario-step outcomes, and artifact IDs/digests were independently corroborated. Artifact-content findings above retain the supplied inspection provenance.

B8 merge verification and exact post-merge hosted verification are **COMPLETE**. This acceptance covers source/CI behavior on the B8 merge, not installation, live-memory migration, real-device sensors or deployment certification. Deployment/live-device validation remains **NOT PERFORMED**, installed SEED is **UNTOUCHED**, and B9–B10 remain **NOT STARTED**.

The documentation closure PR receives its own normal CI and requires owner-directed merge. Its later docs-only merge does not replace or invalidate B8 technical acceptance at `e0075e21f545921324aa5d5c9e2f4217b0a06cca` and does not require another acceptance-documentation commit. See the [canonical closure record](seed-0.2-development-plan.md#b8-hosted-verification-closure--2026-09-29).


## B9 local implementation verification — 2026-09-30

Scope: approved B9 design at `3dc9b8f`, implementation starting from published cleanup `16dcd8b`. Historical B0–B8 results above remain unchanged. Local environment: macOS, Python3.13.15. This record does not claim Linux/Python3.11 execution, new hosted CI, merge or installed-organism deployment.

- Full suite under a disposable `SEED_HOME`: **851 passed, 2 existing warnings in8.41s**. Warnings concern Starlette TestClient/httpx and anyio's BlockingPortal alias.
- All seven unchanged standalone scenarios passed and produced parseable JSON: baseline, prediction_error, world_model, curiosity, semantic, self_model and decision.
- New reader tests exercise strict queries, IDs/cursors, corruption/no-refill, source isolation, byte/structure/type bounds, query/VM budgets, busy reads, missing/legacy/future schemas, and before/after SQLite dump preservation. Shared JS tests run with available Node, without a project dependency; they cover lossless numbers/escaped strings, malformed input, streamed byte caps, typed errors, deadline versus navigation abort, and hash allowlists. Node-specific tests skip explicitly when Node is unavailable.
- Fixture builder refuses non-temporary or nonempty destinations. Named empty, predictions, models, self, decisions, boundary, legacy/version fallback, counts and combined homes have deterministic records/ID manifests. Decision121/122/123/124 fixtures preserve approved producer-generated records and digests;124 alone is intentionally damaged. Fixture inspection compares before/after SQL dumps.
- `git diff 16dcd8b -- seed requirements-lock.txt requirements.txt docs/baselines dashboard/services/self_model.py dashboard/services/decisions.py dashboard/app.py` was empty. Python3.11 grammar parsing passed for dashboard sources; this is not Python3.11 runtime evidence.

Temporary observer browser acceptance used localhost ports8765–8769, fixed reader clock1700000000 and a stubbed process status against `/private/tmp/seed-b9-browser-*`. Installed SEED/LaunchAgent was not accessed. Verified all seven routes; prediction literal mean0.208125/score0.791875 and Boolean false; exact episode link; semantic current3/history2→1; B7 stale61-second observation and missing network; B8 corrupt124, next122, low-disk rest utility0.375 with consolidate Q100 excluded; signed64 MAX_ID→9007199254740993 navigation; world signal filter; healthy curiosity raw3/evaluated denominator2; and explicit transient source503 without hiding sibling evidence.

Overview remained usable when only the development budget was reduced to1 VM callback threshold: organism, activity, battery/load, storage and health remained visible; count-derived fields said Unavailable and the Development card showed the503 message. No partial counts or synthetic zeros were rendered.

Request log verified cold Development one bootstrap+six data GETs; optional counts added one; Refresh after loading counts made seven data GETs without another bootstrap or `/status`. Invalid direct links made no data request. Skip-to-content preserved the active hash and focused main. Mobile menu removed inert while open, Escape restored inert and focused its toggle. Live Activity connected, then navigation rendered Astra normally.

Settled viewport checks at320/760/761/1120/1121/1440 showed no document horizontal overflow. Development columns were1/1/2/2/2/2. Light/dark mobile layouts and desktop layout were inspected; keyboard-focusable table regions preserve access to wide evidence. Local screenshots are retained under `.review-artifacts/b9/` (not committed). Reduced-motion behavior is source-verified by the existing CSS media rule; OS-level reduced-motion emulation was not available in the browser tool. Browser network-stall injection is covered by the deterministic JS deadline test, not claimed as a manual network test.

Final independent whole-branch review is pending at this checkpoint. B9 status is IMPLEMENTED with local verification; hosted CI and deployment remain separate gates.

## B9 corrective verification — 2026-09-30

Starting checkout and authenticated remote ref were `20e19add6ee35c9dc120510333b0207d25294cb8`. SSH fetch/pull failed public-key authentication; no history was rewritten. Corrective reader commit `0647d88` enforces B3 source-header provenance and B5 status/score/level structure without recalculation. Client commit `01263f1f751a4a641d3f0af688b282bb9fd6e195` corrects bootstrap failure recovery, disclosure/focus behavior, table semantics, Overview degradation, placeholders, Astra identity and Development columns.

Regression evidence: the B3/B5 additions first produced 9 failures and 8 passes; corrected prediction/read suites passed 107 tests. Five new client/DOM contracts first failed, then all 18 asset tests passed. Real ES modules run against a small dependency-free DOM harness where practical. Required four-file focused run: **138 passed, 2 existing warnings**. All dashboard tests: **286 passed, 2 existing warnings**. Full local macOS/Python3.13.15 suite: **873 passed, 2 existing warnings in 8.82s**. The same Starlette/httpx and anyio warnings remain. All seven standalone scenario commands exited0. `compileall seed dashboard tests`, project-interpreter `pip check` and `git diff --check` passed. Pip disabled its unwritable cache; no broken requirements were found.

The correction browser pass used disposable homes only. A temporary middleware on port8771 failed the first bootstrap once; explicit Refresh recovered, and subsequent Astra navigation reused the successful bootstrap. Its request log shows two bootstrap requests in that application lifetime; a later full reload correctly made a third. Initial load retained body focus; nav, same-page detail, Back and Forward focused the heading; Refresh retained button focus. Mobile Tab left the open disclosure, Escape restored menu-button focus, closed sidebar was inert, and desktop cleared inert. The navigation itself scrolled at a short desktop height while brand/footer remained outside it. Evidence tables exposed meaningful captions, column scope and labelled focusable scrolling regions.

All seven Astra titles/breadcrumbs/eyebrows and observer identity restoration passed. All four OPERATE placeholders explicitly said they are unimplemented and B9 adds observation only. Overview under the count-budget503 retained its valid sections, showed the exact bounded-count/lifecycle notices and all four unavailable fields. Corrected Development columns at320/760/761/1120/1121/1440 were **1/1/2/2/3/3**, without document overflow. Light/dark/system themes, narrow prediction tables and console checks passed. Stored prediction literals0.208125/0.791875 and false, semantic current3/history2→1, B7 stale/missing evidence, frozen low-disk decision123 (rest utility0.375; consolidate Q100 excluded), corrupt124 and exact9007199254740993 routing were rechecked after the corrections. Screenshot artifacts: `.review-artifacts/b9/development-corrected-desktop.png` and `development-corrected-mobile.png` (local, not committed).

Reduced-motion emulation remains unavailable; only its CSS rule is verified. Network-stall timing remains deterministic JS evidence rather than browser network emulation. Full-range byte audit against `16dcd8b` is empty for `seed/`, both requirements files, `.github/`, `docs/baselines/`, `dashboard/services/self_model.py`, `dashboard/services/decisions.py` and `dashboard/app.py`; schema remains v7. No install, deployment, installed-home access or B10 work occurred. Fresh independent review is in progress; this checkpoint does not claim a passing review, hosted CI or overall B9 verification.

### Final corrective source checks — 2026-10-01

Tested corrective source head: `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981`. The intervening owner checkpoint `8d5711374502d33abd163e620c95afd00d5f8793` and all prior commits are preserved. Final local macOS/Python3.13.15 results: **148 focused tests passed in 3.16s; 883 full-suite tests passed in 9.62s; two existing warnings in each run**. All seven standalone scenarios passed again. Compilation, pip dependency consistency, whitespace and the full unchanged-category scope audit passed. No dependencies were added.

Independent review identified eleven additional corrections beyond C1–C9: bootstrap stall deadline; invalid/timezone/UTC/raw timestamp presentation; prediction episode/reward list fields; maximum prediction list plus expanded detail DOM size; newest-page Predictions Refresh; Yes/No/Unavailable curiosity flags; cancellation of a replaced semantic-history request; first-page reset after eviction of the initial cursor from the20-descriptor history; per-source/history provenance links; independent default20 history paging within the2000-element ceiling; contextual null consolidation completion. Each finding has a demonstrated failing-then-passing executable Node regression. The50-row plus full prediction/evaluation detail case initially rendered1010 elements; eliminating redundant timestamp wrappers preserves the1000-element ceiling and all displayed evidence. Stored scores, flags and IDs are not modified.

Additional browser acceptance on disposable port8772 deliberately stalled the first bootstrap for12 seconds. The app displayed its10-second timeout; explicit Refresh recovered without reloading. Predictions Refresh removed `before`, preserved `limit`, showed newest transition11 and retained focus on Refresh. Curiosity table and Development flags displayed Yes/No. Prediction columns expose episode links and legacy reward; timestamp details expose UTC and raw epoch, with local GMT+8/Asia/Manila text. Desktop and320px checks showed no document overflow; the final console check was empty. Updated local screenshots are `development-final-desktop.png` and `development-final-mobile.png` under `.review-artifacts/b9/`. Viewport override was reset. Reduced-motion emulation remains unavailable; its CSS rule is source-checked only. Semantic cancellation and the long pagination reset are executable client regression evidence, not manual stalled-history/21-page browser claims.

Final fresh whole-branch independent review **PASS**, range `16dcd8b4c60741092c0c538f08f0bf85fef27de9` through `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981`: **0 Critical / 0 Important / 0 Minor**, none deferred. Independent rerun:148 focused /883 full tests, two existing warnings. Maximum100-ID Self Model projection rendered992 elements below1500; semantic list100/default-history20 and direct-history100 stayed below2000. VM interruption, zero busy timeout, rollback and callback removal were independently inspected/exercised. Earlier incomplete reviews remain historical. B9 remains IMPLEMENTED, NOT YET VERIFIED; hosted CI NOT RUN, PR NOT OPEN, merge NO, deployment/live-device validation NOT PERFORMED, installed organism UNTOUCHED and B10 NOT STARTED.

Final provenance browser checks on the disposable combined fixture confirmed Self Model links to actual transitions1–11 and its Runs-page link, plus semantic-history source-belief/transition links. The page rendered716 elements. Browser console errors were empty; local `semantic-history-final.png` records the expanded source disclosure. Maximum Self Model100-ID and semantic history limits are exercised by executable DOM checks rather than a manually constructed large browser fixture.

### B9 corrected branch publication — 2026-10-01

Authenticated GitHub confirms the published branch head before final PR cleanup is `1f7d7692fc397826d4dc79dcfe924073b0ee5bb0`. The owner subsequently published the preserved branch after the historical SSH/HTTPS authentication failures; branch publication is COMPLETE, with no history rewritten. Reviewed source head remains `1a284377e7a896f8e9ce2d07e38c0ff96f6ce981`; both commits after it are documentation-only. Local148-focused/883-full verification and independent review remain local evidence, not hosted evidence. At this checkpoint PR hosted CI is NOT RUN and no PR is open; B9 overall remains NOT YET VERIFIED. Merge NO, deployment NOT PERFORMED, installed organism UNTOUCHED, B10 NOT STARTED. The final publication-status cleanup changes only four documentation files; no fresh Python suite is required.
