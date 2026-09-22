# SEED Implementation Log

This file is a navigation index for SEED development records.

The canonical SEED 0.2 development history, batch status, acceptance criteria, implementation decisions, verification results, known limitations, and readiness gates are maintained in:

* [`seed-0.2-development-plan.md`](./seed-0.2-development-plan.md)

Reproducible baseline and evaluation artifacts are stored in:

* [`baselines/`](./baselines/)

Detailed batch implementation plans are stored under:

* [`superpowers/plans/`](./superpowers/plans/)

---

## Current verified development state

SEED 0.2 is verified through:

| Batch  | Status      | Purpose                                            |
| ------ | ----------- | -------------------------------------------------- |
| B0     | VERIFIED    | Baseline and guardrails                            |
| B1     | VERIFIED    | Transition-based experience                        |
| B2     | VERIFIED    | Prospective environmental prediction               |
| B3     | VERIFIED    | Prediction-error evaluation                        |
| B4–B10 | NOT STARTED | Require separate design and explicit authorization |

Current development schema:

```text
2
```

Current B3 autonomous architecture:

```text
state_before
→ action selection
→ prospective prediction
→ internal action
→ state_after
→ observed transition
→ prediction-error evaluation
→ legacy reward
→ contextual Q update
→ persistent experience record
```

At B3, prediction and prediction-error data remain observational.

They do not yet influence the contextual learning policy.

---

## Historical artifacts

Historical baseline/evaluation artifacts should be treated as immutable evidence of the development stage that produced them.

They include:

```text
docs/baselines/seed-0.1-baseline.json
docs/baselines/seed-0.2-b1-comparison.json
docs/baselines/seed-0.2-b2-comparison.json
docs/baselines/seed-0.2-b3-evaluation.json
```

Do not rewrite older artifacts to reflect newer behavior.

Historical NULL or absent fields are valid representations of earlier developmental stages.

---

## Deployment boundary

Development commits, branch merges, and documentation updates do not automatically update the installed SEED organism.

The repository source and installed application may therefore represent different developmental states.

Installation, restart, and live-memory migration remain separate explicit operations.

No development batch should imply deployment merely because its source tests pass.

---

## Source of truth

Use the following precedence when determining current project status:

1. `docs/seed-0.2-development-plan.md` for canonical developmental state and acceptance records.
2. `docs/baselines/` for recorded reproducible evaluation artifacts.
3. `docs/superpowers/plans/` for historical batch execution plans.
4. `README.md` for the current high-level project description.
5. `docs/architecture.md` for the current architectural model.

This file should remain a lightweight index rather than duplicating the full development record.
