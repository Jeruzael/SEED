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
