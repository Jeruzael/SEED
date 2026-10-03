# B10 foundation storage-safety design amendment — 2026-10-03

**OWNER APPROVED DIRECTION / PUBLICATION IN PROGRESS. DOCUMENTATION / DESIGN AMENDMENT ONLY.** The owner selected **Option B**: preserve strong application-level capability/path isolation for trusted checked-in B10 code; explicitly exclude adversarial concurrent same-UID filesystem mutation during SQLite's internal native file-open interval. This record amends the [canonical specification](2026-10-02-b10-development-evaluation-design.md) and [implementation plan](../plans/2026-10-02-b10-development-evaluation-implementation.md). It does not fix implementation or establish G1/G2.

## Provenance and authorization

| Item | Exact identity / state |
| --- | --- |
| Canonical master / amendment branch point | `196631baef225fa02983f40ffca22cc26190757d`; verified clean locally and via authenticated GitHub |
| Starting baseline CI | [Run 37019823351](https://github.com/Jeruzael/SEED/actions/runs/37019823351); all three required jobs successful; baseline only |
| Separate amendment branch | `docs/b10-foundation-storage-safety-amendment`, created from exact canonical master; not the foundation branch |
| Original approved technical design | `6cd7504b96dec158bbedbadec4f133150f0e80b9` |
| Original approved technical plan | `ef82df33771661a27c6ced6db65e3aaeb4e5fba5` |
| Triggering stopped foundation branch/head | `seed-0.2-b10-impl-01-foundation` / `df0569a99f192a576fa2d60d0c2050500403fbc9` |
| Reviewed engineering head before review bookkeeping | `1dd7c580ac329d18fb9b04768fdaeb3558efc6a3` |
| Independent foundation review | **0 BLOCKER / 9 MAJOR / 1 MINOR**; R1–R10 unresolved |
| Foundation I01–I08 | **IMPLEMENTED CHECKPOINT / NOT VERIFIED**, not complete; no foundation PR |
| G1 / G2 | **NOT VERIFIED / NOT VERIFIED** |

The foundation head's independent review and author audit found that checked Python paths were reopened by sqlite3.connect, and safe checkpoint/clone creation descriptors were discarded before native pathname opens. A controlled replacement reproduction read a foreign DB. The previous broad descriptor-identity promise failed to distinguish application-controlled file opens from SQLite-controlled opens. Local passing foundation tests were not proof of that protection. The historical stop and findings remain valid; this amendment changes the acceptance contract before later repair.

Only five documents may change in this task: existing B10 specification, this amendment record, existing B10 implementation plan, canonical tracker and implementation log. No source/tests/workflows/dependencies/schema changes, native VFS, R1–R10 repair, foundation integration/PR, I09+, empirical execution, deployment, installed-organism access or B11–B16 work. The stopped foundation branch and all eight task commits remain untouched. Stop after amendment publication and exact post-merge verification.

## Alternatives considered and owner decision

| Alternative | Assessment / disposition |
| --- | --- |
| Option A — strengthen native file-open boundary with a capability-aware custom/native SQLite VFS or equivalent native interception | Could enforce stronger guarantees if separately designed/qualified; not claimed impossible. Requires native ABI/platform/lifecycle and Python 3.11/3.13 Linux/macOS qualification, including WAL/journal/SHM and cleanup. **NOT ADOPTED FOR B10 V1** solely to close the excluded hostile race. |
| **Option B — trusted-code application capability/path isolation plus explicit native-race limitation** | **OWNER SELECTED / APPROVED DIRECTION.** Keep fixed owned roots, narrow assigned state, safe existing paths, pre/post/ongoing/backup validation and terminal detected mismatch handling. Do not claim OS sandbox protection from malicious same-UID code racing native opens. |
| Continue broad native-open descriptor promise using post-connect checks only | Rejected as an overclaim: native SQLite may already read headers before Python can revalidate. Detection remains required, but is not prevention of preliminary native access. |
| Connect through retained `/dev/fd` path | Prior local macOS read test retained the DB inode, but writable/WAL semantics failed; directory-descriptor child DB could not open. Not a qualified portable substitute for normal persistence. No such mechanism is adopted. |
| Remove capability/path validation or allow arbitrary/live/foreign roots | Rejected. Outside the owner-selected exception and incompatible with scientific isolation. |

Why Option B: B10 already excludes arbitrary same-UID hostile code from its security guarantee. A custom VFS materially expands B10 into native filesystem security infrastructure rather than an evaluation system; it adds ABI/platform and sidecar lifecycle complexity beyond the required trusted-code threat model. No native layer or dependency is added. A future stronger profile may revisit it only under separate design authorization.

## Exact amended guarantee

B10 infrastructure is for **trusted checked-in SEED/B10 code operating in evaluator-owned local development storage**. It must retain all of these protections:

- Fixed checkout-owned evaluation root; no arbitrary user-selected output/DB path.
- Worker receives only its assigned learner-state capability; no another-run/another-seed/evaluator-storage/arbitrary-file request.
- No installed/live SEED home, copy, inherited SEED_HOME or fallback.
- Application-controlled path resolution rejects existing symlinks, non-directory root components, nonregular state files, foreign/unexpected ownership, traversal, absolute child paths, NUL, unsupported separators/identities and unsafe hard links where detectable.
- Evaluator truth/plans/reports/findings remain outside learner state/configuration/cognition; no report/hidden-score ingestion, untrusted plugins or artifact execution.
- Organism schema remains v7; no evaluator tables or migration, no B1–B8 source/formula/default change, no new dependency.
- Only the assigned evaluation worker is a trusted writer for its learner DB; a second B10 trusted writer is rejected.
- Detected unexpected inode, owner/type, unsafe sidecar, replacement or capability mismatch is terminal for the affected run. Do not continue, automatically reopen/resume, or use invalid state as trusted scientific evidence; cleanup may not follow a mismatched path.

**B10-managed ordinary files/artifact reads and writes:** descriptor-relative/no-follow opening and descriptor identity protection remain required where the application owns the open. The former general path-safety promise is retained here; it is not weakened by SQLite's limitation.

**SQLite database and SQLite-managed WAL/journal/SHM:** standard Python sqlite3 delegates actual opens to native code. Required application controls are:

| Stage | Binding control / failure behavior |
| --- | --- |
| Before connection | Validate fixed evaluator-owned directory, assigned capability/directory identity, directory ownership/type, expected state filename, existing file type/owner/no symlink, unsafe hard links where detectable and root/reservation bounds. No arbitrary path. Prefer existing-file SQLite semantics such as `mode=rw` for an already-created DB where compatible with normal producer behavior; fresh initialization is separately admitted owned creation. |
| Immediately after successful connection | Revalidate expected main DB identity, regular-file status/ownership, capability directory identity and observable SQLite database path/facts. Pre/post conflict is terminal; do not use affected state as valid science. This cannot guarantee prevention of native header reads during an excluded race. |
| During operation | Bounded periodic/transaction-boundary checks of main DB identity, physical growth, permitted observable WAL/SHM/journal types/ownership, learner capability and root/reservation state. Every detected unsafe replacement/mismatch is terminal. Resource ceilings and transaction overshoot rules remain unchanged. |
| Before checkpoint/clone/publication | Revalidate state identity and capability, plus unchanged backup/workspace admission requirements. Never publish a learner checkpoint as trusted if validation fails; retain actual invalid/incomplete prefixes without reporting completed acceptance. |

## Exact excluded guarantee and disclosure

**Only adversarial concurrent same-UID filesystem mutation during SQLite's internal native file-open interval is newly explicit here.** Examples: malicious same-UID code intentionally replacing the learner DB pathname between application validation and native open; swapping WAL/SHM/journal files while SQLite opens them; racing identities specifically to defeat capability checks. B10 v1 does not guarantee prevention of these attacks. Existing unsafe paths, ordinary-file descriptor protection, incorrect trusted-code routing and detected mismatches remain in scope.

These controls protect B10 from accidental path misuse, stale/foreign capabilities, unsafe pre-existing paths and incorrect trusted-code routing. They do not form an OS-level sandbox against malicious same-UID code racing SQLite's native file opens. Such hostile concurrent mutation is outside B10 v1's trusted-code guarantee. Do not describe SQLite protection as race-proof, tamper-proof, hostile-code safe, descriptor-bound or native-open protected. The actual limitation must travel with future engineering verification reports.

**DEFERRED**, not hidden B10 v1 prerequisites: hostile same-UID filesystem sandboxing; capability-aware native SQLite VFS; signed artifact authenticity; OS sandboxing/containers solely for hostile evaluator-code defense. None permits foreign/evaluator/live data in learner state under the trusted-code contract.

## Review findings and future repairs

R1 disposition is **DESIGN CONTRACT AMENDMENT APPROVED — IMPLEMENTATION FIX STILL REQUIRED**. R1 remains **UNRESOLVED / REMEDIATION REQUIRED**, not PASS. All other findings retain their original severity and implementation obligations.

| Finding | Severity | Status / future obligation |
| --- | --- | --- |
| R1 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — implement amended capability/pre-existing-path/existing-file/post-connect/observable-sidecar/terminal-mismatch/no-installed-fallback contract. |
| R2 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — statement finalization/autocommit growth monitoring. |
| R3 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — checkpoint/clone workspace admission/enforcement. |
| R4 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — shared run-budget terminal latch. |
| R5 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — profile_digest admission. |
| R6 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — live root capacity/reservation reconciliation. |
| R7 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — terminal FAILED state after ambiguous action effect; no retry. |
| R8 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — strict nested public prediction schema. |
| R9 | MAJOR | UNRESOLVED / REMEDIATION REQUIRED — fresh worker launch from completed owned clone. |
| R10 | MINOR | UNRESOLVED / REMEDIATION REQUIRED — dependency graph dynamic-import/alias coverage. |

Future R1 repair tests (planned only): reject pre-existing symlink/nonregular/foreign DB before connection; existing-file connection never silently creates a missing expected DB; observable pre/post identity mismatch terminates; observable unsafe WAL/SHM/journal type/owner fails closed; another learner/evaluator capability cannot be routed to SQLite; poisoned SEED_HOME unused; second B10 trusted writer rejected; documentation/verification claims disclose the native-race limitation. Controlled mismatch injection tests detection, not prevention of the excluded malicious native-open attack. I03/I06/I07 and the plan's remediation matrix preserve required future R2–R10 tests. **No repair code or tests are created/run here.** Task IDs I01–I31, phases A–P and G1–G7 remain unchanged.

## Engineering and publication boundaries

**B10 engineering IN PROGRESS. Foundation I01–I08 IMPLEMENTED CHECKPOINT / NOT VERIFIED; NOT COMPLETE. G1 NOT VERIFIED. G2 NOT VERIFIED. I09–I30 NOT STARTED / NOT AUTHORIZED. Empirical evaluation NOT STARTED / NOT AUTHORIZED. NO B10 EXPERIMENTS EXECUTED. INSTALLED SEED UNTOUCHED; DEPLOYMENT NOT PERFORMED.**

Amendment publication is separate from foundation implementation. Current amendment review/PR/exact-head CI/normal merge/exact post-merge master CI are pending; no prior CI is reused as amendment evidence. After successful verification the amendment alone becomes **OWNER APPROVED / MERGED / VERIFIED AT DOCUMENTATION-CI LEVEL**; engineering findings and G1/G2 remain pending.

Only a later **B10 FOUNDATION REVIEW REMEDIATION — R1–R10 ONLY** owner instruction may integrate the newly verified canonical master into the existing stopped foundation branch, repair findings, rerun focused/full/seven-scenario verification, perform fresh foundation review, determine G1/G2 and then open a foundation PR if eligible. Do not perform those steps now, rewrite/discard task history, create a protocol branch, implement I09 or run experiments.

Documentation checks before publication: PASS — git diff --check, complete authorized diff/scope inspection, 89 local links/anchors and balanced Markdown/Mermaid fences; 31 task IDs, phases A–P and G1–G7 preserved; R1–R10 all unresolved and G1/G2 NOT VERIFIED. Spec scientific sections 7–17 and plan I09–I31 task bodies remain byte-identical to canonical base. Core/schema/dependencies/workflows/roadmap/baselines unchanged; stopped foundation ref unchanged. No new code/tests or fresh local production/scientific run for this documentation task. Amendment independent review/hosted CI/merge/exact master verification are separate pending gates.
