# Reproducible SEED verification

This guide covers current local verification and the GitHub Actions workflow introduced after B6. B7 adds the sixth deterministic self-model scenario.
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
for scenario in baseline_scenario prediction_error_scenario world_model_scenario curiosity_scenario semantic_scenario self_model_scenario; do
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

Do not overwrite files under [baselines/](baselines/). For post-B6 hardening, all
scenario behavior remains identical to the fresh starting run. The semantic
scenario renames current source digests from unchanged_b5_source_sha256 to
source_sha256 because the authorized body parser correction changes body.py.
Its regression test still compares every behavioral field and the other eleven
source digests exactly. An environment-dependent footprint or a later approved
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
| linux-py313 | ubuntu-24.04 | 3.13 | Same checks plus six standalone scenario commands and JSON validation |
| macos-py313 | macos-15 | 3.13 | Same checks plus six standalone scenario commands and JSON validation |

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

The B7 implementation has 646 passing local tests and six passing standalone synthetic scenarios. Seven historical B0–B6 artifacts remain byte-identical; schema and additive database footprint are the only permitted historical scenario differences. See the [B7 execution record](seed-0.2-development-plan.md#b7-implementation-record--2026-09-24) for final review results. Hosted B7 checks have not run: automatic approval review rejected the implementation push pending explicit owner authorization to transfer the source to the existing Jeruzael/SEED remote. The rejection did not change the remote. Earlier hosted results above remain evidence only for their stated commits.
