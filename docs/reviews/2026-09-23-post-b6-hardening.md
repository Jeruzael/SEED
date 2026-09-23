# Post-B6 hardening — 2026-09-23

## Scope and resume ledger

Owner-authorized H0–H5 from SEED_Codex_Post_B6_Hardening_Instructions.md.
Native inline implementation, one independent review at the end. No B7–B10,
learner redesign, schema change, dependency upgrades, live installation or remote
writes. Local evidence lives in ignored `.review-artifacts/`; no owner memory.

Initial checkout: Jeruzael/SEED, clean seed-0.2-b6 at
1f273df5cc9a7ceaf3d3ad0de0cb2a7dc1e741b9. The reviewed master merge
f18ed31bc622ed219558a1f0aa7f4c4566cc0d56 is locally present, one commit ahead,
and has the identical file tree. GitHub read-only inspection confirms master at
that revision. Created seed-0.2-post-b6-hardening from that verified base without
resetting, rewriting or discarding work. No applicable AGENTS.md found.

Ruling: use the explicitly requested task branch in the existing native workspace;
the owner already chose native execution, and the tree is clean. H0's baseline
precedes production changes. The supplied H0–H5 specification is the execution plan.

Pre-flight interfaces: H1 changes only current sensor observations, preserving
learner/guard formulas. H2 changes runtime/bootstrap metadata, not freshness or
schema. H3 consumes unchanged pinned dependencies and existing scenarios. H5 must
explain any source-hash metadata change in those scenarios rather than rewrite
historical artifacts. H4 documents the existing low-disk mismatch only.

## H0 — freshly verified starting state

- Python 3.13.15 in the existing .venv; exact interpreter/platform/lock and seven
  baseline SHA-256 hashes saved in `.review-artifacts/h0/environment.json`.
- Existing fixture review: Memory/SeedOrganism instances use tmp_path/temporary
  homes; sensor tests replace OS/network boundaries. A separate newly created
  SEED_HOME was passed to every baseline command and inherited subprocess.
- `.venv/bin/python -m pip install --no-index -r requirements-lock.txt`: exit 0.
  Existing pinned packages satisfy the lock offline; no packages changed.
- `.venv/bin/python -m pip check`: exit 0, no broken requirements.
- `.venv/bin/python -m pytest -q --junitxml=.review-artifacts/h0/pytest.xml`:
  exit 0, 497 passed, 0 skipped, two existing Starlette/httpx and AnyIO warnings.
- All five `python -m tests.<scenario>` commands exit 0 and produce valid JSON:
  baseline_scenario, prediction_error_scenario, world_model_scenario,
  curiosity_scenario, semantic_scenario. Outputs and stderr saved in h0/.
- No existing CI workflow. GitHub run listing reports total_count=0. Branch summary
  reports protected=false, but detailed branch protection returns 403 (integration
  access), and rulesets returns 403 (private-repository plan restriction). Detailed
  enforcement status is unknown; no settings changed. Evidence: h0/github.json.
- Source findings reproduced by inspection: substring charging test; hardcoded
  runtime 0.1; ambiguous bootstrap version meaning; missing CI; low-disk reward
  versus suppression. H1/H2 will capture executable RED evidence; H4 the diagnostic.

## Historical checkpoint after H0

H0 VERIFIED locally. H1 next: reproduce discharging false positive with failing
parser/guard tests, then correct only the existing sensor boundary. H2–H5 unrun.
Current task HEAD f18ed31; only .gitignore and this record added/updated so far.

## H1 — verified locally

RED: 25 parser/guard failures, eight passes; the actual cycle also failed on
(15, True) versus (15, False). Evidence h1-red.log and h1-cycle-red.log. The small
parser now reads one InternalBattery record, complete status fields and bounded
percentage independently. Negative status wins over AC; conflicting/unknown
status is unknown. Multiple battery records are unavailable rather than guessed.
Fixed command, timeout and network probe unchanged. Focused battery/learner/
curiosity/semantic suite: 180 passed, exit 0. Full suite: 531 passed, exit 0.

Ruling: the first full run had one related source-hash mismatch (530 passed).
B6's fixture called all hashes unchanged_b5_source_sha256, which is no longer
truthful for body.py. Rename current output to source_sha256, verify body.py's
actual current digest, and retain exact comparison for every behavioral output
and the other eleven hashes. No baseline JSON is edited. This is the authorized
sensor correction's provenance metadata, not normalization of a behavior change.

## H2 — verified locally

Eight metadata tests failed against the old runtime/bootstrap contract, including
literal runtime 0.1 versus required 0.2. seed/version.py supplies CORE_VERSION=0.2;
the organism reports it. Bootstrap retains version/token/operator/refresh_seconds
and adds core_source_version, dashboard_version, dashboard_edition and
supported_schema_version. Runtime evidence, lifecycle/freshness and schema remain
untouched. No commit/build identity invented. The overview's absent-version label
now says Unavailable instead of guessing Legacy 0.1, under Reported core version.

Focused metadata/HTTP/read/asset/telemetry tests: 31 passed. Full suite: 539 passed,
zero skips, two existing warnings, exit 0. Legacy dumps unchanged. A standalone
Node harness executed the actual overview and API modules with synthetic DOM/fetch,
checking missing and older stopped versions and stale labeling; exit 0. Evidence:
h2-*.log and overview-version.mjs. No browser visual or installation verification.

## Historical checkpoint after H2

H0–H2 locally verified. H3 workflow written, pending YAML/structure/shell/local
validation; H4 diagnostic and H5 final review/documentation pending. HEAD remains
f18ed31 on seed-0.2-post-b6-hardening. No live or remote mutation performed.

## H3 — implemented and locally validated; hosted execution pending

The workflow and [verification guide](../verification.md) provide three bounded
matrix entries: Linux/Python 3.11, Linux/Python 3.13 and macOS/Python 3.13.
Each installs the unchanged lock and runs the full suite; both 3.13 entries also
run all five standalone scenarios. Official action releases and commit objects
were checked through read-only GitHub access, including action.yml at each pin.
Evidence: `.review-artifacts/action-pins.json`.

Ruby Psych parsed YAML successfully. Structural assertions checked events,
permissions, matrix, pins, timeout and artifact scope. Every shell block passed
bash -n. A disposable failing tee pipeline returned 23, as intended. No failure
is hidden by continue-on-error. Evidence: workflow-validation.log and workflow.json.
actionlint was unavailable; this is not an actionlint or hosted validation claim.

The workflow's actual environment, dependency, pytest and scenario shell blocks
were extracted and executed locally with the existing .venv first on PATH and a
new synthetic SEED_HOME. Each returned 0. This did not execute GitHub actions,
artifact upload, the hosted matrix, or GitHub's conditional/outcome machinery.
Evidence: run-workflow-locally.py, local-workflow-results.json, *-local.sh/log and ci/.

## H4 — diagnostic verified; decision correction deferred

The real Learner.reward and semantic resource_suppression diagnostic returned
observe=0.25, reflect=0.25, consolidate=0.8, rest=-0.2 and suppression=low_disk;
exit 0. No database or organism was created for this diagnostic. The mismatch
remains **OPEN: separate owner authorization required**, assigned to B8 unless
the owner chooses a distinct scope. [Review follow-ups](../review-follow-ups.md)
contains the exact reproduction and future acceptance scenarios.

## H5 — local handoff and evidence

This section supersedes the historical checkpoints above. H0, H1, H2 and H4 are
locally VERIFIED. H3 is IMPLEMENTED and locally validated. H5's local regression,
scope and documentation checks are VERIFIED. Required hosted matrix evidence is
PENDING owner-authorized push/PR, so the whole task is not completely verified.

### Checkout and revision identity

Repository: Jeruzael/SEED in the native SEED_macOS_prototype_0.1 workspace.
Initial revision: 1f273df5cc9a7ceaf3d3ad0de0cb2a7dc1e741b9 on seed-0.2-b6.
Implementation base: f18ed31bc622ed219558a1f0aa7f4c4566cc0d56 on
seed-0.2-post-b6-hardening. The final code was tested as working-tree changes to
that base. The containing local commit identifies the delivered tree; its exact
ending SHA and clean-tree status are saved after commit in
`.review-artifacts/final-revision.json` and reported in the owner handoff.
No remote write or history rewrite is authorized or performed.

### Finding disposition

| Finding | Disposition |
| --- | --- |
| Discharging/not-charging false positives | Reproduced with failing raw-input tests; fixed for new observations |
| Sensor result reaching actual consumers | Verified through real Body, learner context, both resource guards and cycle counts |
| Runtime 0.1 and ambiguous dashboard metadata | Reproduced; fixed current runtime and added explicit source/component/schema fields |
| Missing CI | Implemented and locally validated; hosted results pending |
| Low-disk positive consolidation reward versus suppression | Reproduced; decision change deferred and OPEN |
| Repository rule enforcement | Detailed inspection blocked by 403; unknown, not claimed enabled or absent |

### Changed files and purpose

| File | Purpose |
| --- | --- |
| .gitignore | Exclude local synthetic review evidence |
| .github/workflows/seed-ci.yml | Least-privilege pinned CI, matrix, failure propagation and bounded evidence upload |
| seed/body.py | Correct complete battery fields and preserve truthful unknowns |
| seed/version.py | Lightweight CORE_VERSION source of truth |
| seed/organism.py | Use CORE_VERSION for existing runtime.version |
| dashboard/app.py | Preserve bootstrap version and add four explicitly named metadata fields |
| dashboard/static/views/overview.js | Label reported runtime version and show Unavailable when absent |
| tests/test_battery_regression.py | Raw parser cases, real sensor-to-guard path and threshold regressions |
| tests/test_baseline_environment.py | Intentionally correct the historical false-positive characterization |
| tests/test_curiosity_cycle.py | Real raw-battery cycle and unchanged perception/probe/transition/Q counts |
| tests/test_version_metadata.py | Runtime/bootstrap contract, stale/legacy/absent records, token checks and import isolation |
| tests/semantic_scenario.py | Truthful current source_sha256 output name |
| tests/test_semantic_scenario.py | Permit only authorized body digest change; retain every behavioral assertion |
| README.md | Current parser, metadata, results and pending/deferred work |
| docs/architecture.md | Sensor and identity boundaries without developmental redesign |
| docs/implementation-log.md | Separate hardening entry and evidence links |
| docs/seed-0.2-development-plan.md | Current authorization and separate hardening status; preserve B0–B6 history |
| docs/verification.md | Reproducible commands, CI provenance, evidence and owner-controlled merge checks |
| docs/review-follow-ups.md | Reproduction and future acceptance criteria for the unresolved decision mismatch |
| docs/reviews/2026-09-23-post-b6-hardening.md | Starting audit, execution record and final handoff |

### Fresh verification and exact commands

Interpreter: Python 3.13.15, Clang 21.0.0, existing .venv/bin/python.
Platform: macOS-26.5.1-arm64-arm-64bit-Mach-O.
Unchanged requirements-lock.txt SHA-256:
1fe34b077636964cde188c0f19317f7615f27200d4ac49aedeeb13df401fd769.
Every runtime/persistence command used a temporary synthetic home.
The local workflow run used python resolving to the same .venv interpreter.

| Command/check | Exit and result |
| --- | --- |
| python -m pip install -r requirements-lock.txt | 0; existing locked dependencies satisfied |
| python -m pip check | 0; no broken requirements |
| python -m pytest -q --junitxml=.review-artifacts/ci/pytest.xml | 0; 539 passed, 0 failed, 0 skipped, 2 existing warnings |
| python -m tests.baseline_scenario | 0; valid JSON, behavioral output identical to H0 |
| python -m tests.prediction_error_scenario | 0; valid JSON, behavioral output identical to H0 |
| python -m tests.world_model_scenario | 0; valid JSON, behavioral output identical to H0 |
| python -m tests.curiosity_scenario | 0; valid JSON, behavioral output identical to H0 |
| python -m tests.semantic_scenario | 0; valid JSON, behavior identical; only explained body-source metadata change |
| python -m json.tool on each scenario output | 0 for all five files |
| /opt/homebrew/bin/node .review-artifacts/overview-version.mjs | 0; actual overview/API modules with synthetic DOM/fetch |
| git diff --check | 0; no whitespace errors |

The existing warnings are Starlette's httpx TestClient deprecation and AnyIO's
BlockingPortal alias deprecation. Dependencies were not changed to silence them.
The suite gained 42 tests: 33 battery cases/integration cases, one real-body cycle,
and eight metadata cases. Existing test selection was not reduced or skipped.
The two intentional expectation changes are explained under H1 above.

Logs, JUnit, JSON, environment metadata and numeric exits are in
`.review-artifacts/ci/`; the initial run is separately preserved in h0/.
comparison.json records the exact comparison and unchanged seven historical
artifact hashes. final-scope.json records the final source/contract audit and
documentation-link checks. Local evidence is ignored by Git, not uploaded.

### Review and preserved contracts

The independent reviewer received the full owner scope, actual base/HEAD, all
tracked and untracked changes, and test/scenario evidence. Its initial report
found no actionable correctness, security or scope regression, and specifically
confirmed the source-hash adjustment retained every behavioral field and the
other eleven digests. It then hit a usage limit before completing its final
focused tests/documentation pass. This is partial independent review, not final
independent approval. The implementer completed a separate self-review of all
changed code/tests/workflow and documentation; no actionable issue found.

Diff and byte comparisons preserve learner/action/reward/Q formulas, epsilon,
alpha, delays, schema v5 and migrations, predictor/error/world-model logic,
semantic bounds/history/idempotence, curiosity defaults/cooldowns/stop behavior,
and retention. Body's fixed command/timeout/probe and perception method remain
unchanged outside the parser. The organism's only change is version import/use.
Dashboard middleware, routes, services and command broker remain unchanged; full
HTTP tests and new metadata tests cover current/legacy observers and token checks.
No new sensing, network target, memory deletion, backfill or historical relabeling.
All seven historical baseline files and locked requirements match their H0 hashes.
Changed-file inspection excludes credentials, real databases, homes, backups and
local environments from the commit.

The installed organism was not modified, started, stopped or migrated. No install,
uninstall or main-program invocation occurred. The UI consumer was tested through
a synthetic Node harness; browser visual/E2E and real-device installation checks
were not performed. Linux, Python 3.11 and GitHub-hosted macOS were unavailable
locally; local macOS 26.5.1 is not evidence for the configured macos-15 runner.

### Readiness and remaining gates

Ready for owner review of local source and evidence. Merge readiness awaits real
hosted runs for the relevant revision, inspection of all matrix jobs/artifacts,
and owner-controlled rule/check setup using names reported by those runs.
Detailed protection/ruleset status remains unknown after restricted reads.
Final independent review also remains incomplete as described above. Source
readiness is not deployment readiness. Low-disk policy correction, live-device
installation validation and B7–B10 remain outside this handoff. Stop here; no
automatic push, PR, merge, release, installation or next-batch implementation.


## Pre-B7 closure — authorized follow-up

This section supersedes the earlier local-only handoff for the closure work. The
owner explicitly authorized SEED_Pre_B7_Closure_Instructions.md and proceeding
with the branch push, PR and hosted verification; no merge or live deployment.
P0 observed clean seed-0.2-post-b6-hardening at
08dd9d357ba39fc11a092bf3b81181e3b0221c37, merge base with master
f18ed31bc622ed219558a1f0aa7f4c4566cc0d56. Remote tracking already pointed to the
reviewed hardening commit; no reset or unrelated change was needed.

P1/P2: dashboard/static/views/overview.js changes only On battery to Not charging
for charging===false. True remains Charging; missing/null/other remain Charging
state unavailable. The HTTP asset regression in tests/test_version_metadata.py
failed first on the old label (one failure, exit 1), then passed with the fix.
The existing synthetic Node harness also executed the actual overview/API modules
for true, false, missing, null and string values; all intended labels passed.
No Node/npm dependency was introduced. Parser and core code remain unchanged.

P7 preparation found the workflow's default checkout would test GitHub's synthetic
merge commit, contradicting the required artifact checked_out_sha=PR head.
The smallest correction sets checkout ref to
`${{ github.event.pull_request.head.sha || github.sha }}`. This is verification
identity handling, with the same pins, permissions, matrix and tests. Official
[checkout guidance](https://github.com/actions/checkout#checkout-pull-request-head-commit-instead-of-merge-commit)
confirms the distinction. No event payload is interpolated into a shell command.

P3 fresh local evidence lives in ignored `.review-artifacts/pre-b7/`:

- `.venv/bin/python -m pytest -q tests/test_version_metadata.py tests/test_battery_regression.py tests/test_baseline_environment.py tests/test_curiosity_cycle.py`: exit 0, 60 passed.
- `.venv/bin/python -m pytest -q --junitxml=.review-artifacts/pre-b7/pytest.xml`: exit 0, 540 passed, zero failures/skips, two existing warnings.
- `.venv/bin/python -m tests.baseline_scenario`, `.venv/bin/python -m tests.prediction_error_scenario`, `.venv/bin/python -m tests.world_model_scenario`, `.venv/bin/python -m tests.curiosity_scenario`, `.venv/bin/python -m tests.semantic_scenario`: each exit 0, valid JSON and exactly equal to the prior H5 output, including current source metadata.
- `/opt/homebrew/bin/node .review-artifacts/pre-b7/overview-battery.mjs`: exit 0.
- `git diff --check`: exit 0. All seven historical baseline hashes unchanged.

Python 3.13.15 / macOS 26.5.1 arm64, same locked dependencies. Runtime and
persistence tests used a new temporary synthetic SEED_HOME. local-results.json
records exact commands/exits and platform; red.log preserves the initial failure.
The two warnings are the same Starlette/httpx and AnyIO deprecations.

P4–P8 checkpoint: documentation reflects the 540-test follow-up without changing
historical B0–B6 counts. Final independent review is requested. Push/PR, final-head
hosted jobs and artifact inspection remain pending here; no closure VERIFIED
claim is made before those gates pass. Low-disk mismatch remains OPEN, installed
organism untouched, and B7–B10 NOT STARTED.
