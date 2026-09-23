# Reproducible SEED verification

This guide covers local verification and the post-B6 GitHub Actions workflow.
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
for scenario in baseline_scenario prediction_error_scenario world_model_scenario curiosity_scenario semantic_scenario; do
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
| linux-py313 | ubuntu-24.04 | 3.13 | Same checks plus five standalone scenario commands and JSON validation |
| macos-py313 | macos-15 | 3.13 | Same checks plus five standalone scenario commands and JSON validation |

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

Local macOS/Python 3.13 verification does not establish Linux, Python 3.11 or
GitHub-hosted macOS results. **Pre-B7 hosted CI is pending execution on the final PR head.**
No hosted run was triggered during the initial H0–H5 hardening. The owner has
now authorized the pre-B7 push/PR and artifact inspection. YAML/structure and shell validation
are local checks, not a claim that GitHub has executed the workflow. actionlint
was unavailable locally; the checked YAML was parsed with Ruby Psych and its run
scripts checked with bash -n.

After pushing/opening the authorized PR, inspect a real run for the relevant revision, confirm
all three jobs and artifacts, and copy the exact check names GitHub reports.
The job name template is test (matrix ID); exact required-check names are not yet
recorded because there has been no hosted run. Do not configure guessed names.

The owner can then use repository Settings → Rules / Branches to require those
observed status checks for master, subject to account permissions and plan support.
Review existing rules before changing anything. Documentation and workflow code
do not enable branch protection by themselves. See [GitHub repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

During the read-only audit, GitHub reported zero runs and protected=false in the
branch summary. Detailed branch protection returned 403 for integration access;
rulesets returned 403 with a private-repository plan restriction. Detailed rule
status therefore remains unknown. No visibility, billing, permissions or rules
were changed. Those settings, hosted execution, merge and deployment remain
separate owner-controlled steps.
