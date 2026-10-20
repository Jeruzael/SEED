# Evaluation evidence repair and readiness

Status: engineering repair locally verified; hosted integration checks pending.
No empirical acceptance claim.

## Current disposition

The checkpoint interface and bounded post-ACK publication/online replay repairs
are implemented in the isolated branch. A fresh agent review identified one
baseline-validation gap; its author repair passes 60 focused checks. Final local
verification passes 1,653 tests and seven deterministic scenarios. Exact-head
hosted CI remains pending.

The [admission worksheet](../../evaluation/2026-10-20-admission-readiness.md)
records unresolved gates. Gio subsequently requested an
[infrastructure proposal](../specs/2026-10-20-i31-infrastructure-proposal.md),
which now recommends local engineering on existing resources following Gio's
explicit no-budget/no-spending instruction. The priced cloud design is deferred
reference. No provisioning or spending was authorized.
The [next local engineering design](../specs/2026-10-20-local-evaluation-next-design.md)
maps frozen reproduction and nondestructive retention alternatives for review;
it does not implement them.

Milestones 4 and 5 remain conditional on the decisions and empirical evidence
described below. The [review record](../../reviews/2026-10-20-evaluation-evidence-repair-review.md)
distinguishes completed engineering evidence from those pending prerequisites.

## Authority and scope

Gio authorized the five proposed milestones in the current Codex conversation:
repair the checkpoint interface; prove the measurement/publication/replay path;
resolve scientific-execution prerequisites; execute registered I31 only after
its gates; then propose a focused B11 Nursery design from the results.
Gio subsequently specified a stop threshold of 45% weekly allowance remaining
(55% used). Account-wide usage is checked between substantial work units.

This authorization does not supply a personal signature, choose unresolved
DEC-03 options, provide cloud expenditure approval, or itself satisfy execution
admission. Stage A closure v1.1 preparation already exists and remains unsigned.
Do not recreate it or repeat the completed independent Stage A review.

Binding engineering references:

- `docs/superpowers/specs/2026-10-02-b10-development-evaluation-design.md`
- `docs/superpowers/plans/2026-10-02-b10-development-evaluation-implementation.md`
- `SECURITY.md` and `.github/PULL_REQUEST_TEMPLATE.md`

## Global constraints

- Isolated `codex/seed-evaluation-repair` worktree, based on
  `7015a9f80f8640b494c9977252337a67ea4a79ca`.
- Keep cognition, installed learner state, producer schema, metric formulas,
  populations, frozen plans, supplied evidence, and execution locks unchanged.
- Checkpoint/ACK v1 remains selected-only. Baselines and candidate detail belong
  to bounded post-ACK records, as the approved artifact specification requires.
- Preserve missing provenance as unavailable; reject ambiguous attribution.
- Technical fixtures use disposable state. They are not registered experiments.
- No owner keys, signatures, cloud resources, spending, deployment, or master
  changes. Review and exact-head checks precede any proposed integration.

## Milestone 1: checkpoint source interface

Implement a lossless, bounded schema-v7 source adapter for producer metrics,
separate from the canonical scientific-digest projection. Use explicit existing
checkpoint metadata to bind each source to its member. An initial or unlabelled
snapshot cannot become a producer source by list position.

Write integration tests first, observe the defect, then repair. Verify literal
world evidence counts from real producer APIs, raw JSON preservation, schema
and size rejection, missing historical/self evidence, and source attribution.
Run focused tests and relevant artifact/science/integrity suites.

## Milestone 2: measurement path

Trace preselection capture through post-ACK events into artifact derivation.
Preserve selected evidence in the journal, join by exact event identity/digests,
and carry baseline/history and B8 candidate/selection provenance within the
existing combined record cap. Verify with bounded integration fixtures that
baseline pairing uses the original cutoff and adaptation receives the original
unselected candidate. Include publication and replay where the supported
protocol permits, without treating online replay as frozen replay.

Investigate frozen reexecution and suite-versus-retention admission separately.
Record remaining unsupported paths honestly before broadening implementation.

## Milestone 3: admission readiness

Reconcile later primary records, existing v1.1 closure preparation, P0/P1 reviews,
and the current implementation. Prepare a concrete list of satisfied evidence,
missing engineering, and owner-only decisions. Do not fabricate gate completion.

## Milestones 4 and 5: conditional scientific work

The registered 30-member I31 execution requires verified admission and the
required owner decisions. Preserve failures and all registered conditions.
Independent scientific review and G7 remain separate acceptance decisions.
The B11 design must identify which conclusions depend on those results; absent
results cannot be replaced by technical fixture outcomes.

## Verification and review

Use RED-to-GREEN regression evidence for each behavioral repair, then the
repository's required checks. Obtain a fresh whole-change review. Record the
tested commit/working state and limitations. Do not claim remote CI, owner
approval, deployment, or empirical findings without primary evidence.

Review focus: raw-source fidelity; malformed/oversized SQLite; initial versus
member-bound snapshots; post-ACK size/identity boundaries; current/future history
leakage; absent baseline/candidate provenance; repeated/failed transitions;
old artifacts and replay compatibility; untouched scientific execution locks.
