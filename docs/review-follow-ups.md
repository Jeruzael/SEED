# Review follow-ups

## Low-disk reward versus suppressed consolidation

**RESOLVED IN B8 AND VERIFIED AT SOURCE/CI LEVEL.** The owner approved implementation on 2026-09-27. Autonomous reflect/consolidate are excluded below 10% disk even with Q=100; observe/rest remain eligible, and injected ties select either eligible maximum. Owner consolidation remains available, truthfully records its `low_disk` suppression audit, and performs no semantic work under that condition. Legacy reward and historical Q remain unchanged; consolidation still does not free disk. Tests: `test_low_disk_excludes_high_q_and_injected_tie_selects_either`, `test_b8_excludes_suppressed_autonomous_consolidate_preserving_owner_guard`, and `test_literal_b8_acceptance_and_saved_comparison`. [PR #12](https://github.com/Jeruzael/SEED/pull/12) merged at master `e0075e21f545921324aa5d5c9e2f4217b0a06cca`; exact [post-merge run 36443249417](https://github.com/Jeruzael/SEED/actions/runs/36443249417) passed all three jobs. Deployment/live-device validation remains **NOT PERFORMED**, installed SEED is **UNTOUCHED**, and B9–B10 remain **NOT STARTED**. See the [closure record](seed-0.2-development-plan.md#b8-hosted-verification-closure--2026-09-29).

**Historical finding:** Roadmap owner: B8 decision-system
upgrade, unless the owner authorizes a distinct narrowly scoped change. Reproduced
2026-09-23 against reviewed base f18ed31 and the unchanged learner/consolidator in
post-B6 hardening. This was documented for the separately approved B8 phase.

The real `Learner.reward` in seed/learner.py awards consolidation for low disk,
while `resource_suppression` in seed/semantic_memory.py suppresses semantic work
under the same condition. Semantic consolidation retains originals and is not a
storage-reclamation action. This diagnostic uses no database or organism startup:

```bash
.venv/bin/python - <<'PY'
from seed.learner import ACTIONS, Learner
from seed.semantic_memory import resource_suppression
state = dict(battery_pct=80, charging=True, load_ratio=.1, disk_free_pct=5., local_hour=12)
print({'rewards': {a: Learner(None).reward(state, a) for a in ACTIONS},
       'suppression': resource_suppression(state)})
PY
```

Observed output, exit 0:

```text
rewards: observe=0.25, reflect=0.25, consolidate=0.8, rest=-0.2
suppression: low_disk
```

Local evidence: `.review-artifacts/h4-low-disk.json`. The result demonstrates a
contract mismatch, not a measured long-running action distribution. Selection
also depends on existing Q values, exploration and tie-breaking.

### Compatibility boundary

The hardening task preserves the action set, reward/update formulas, Q values,
resource guards and delay semantics. No test is added to treat the mismatch as
desirable behavior. Historical rewards and experiences remain untouched.

A future design should distinguish knowledge consolidation from actual storage
reclamation, expose blocked/no-op outcomes to decision evaluation, and define
fallback behavior before changing reward or Q updates. It must not reward
nonexistent disk savings, remove the low-disk guard, bypass owner controls,
delete memories automatically, or rewrite historical rewards.

### Proposed future acceptance scenarios

| Scenario | Required evidence before accepting a decision change |
| --- | --- |
| Low disk alone | Suppressed consolidation receives no credit for reclaimed space; fallback and policy update are explicitly specified |
| Low disk plus low uncharged battery | Both constraints remain effective; no unsafe work is selected to escape the conflict |
| High load | Resource suppression still applies; no shortened wait or extra sensor work |
| Unknown sensor state | Unknown remains distinct from safe/unsafe; any policy change is explicit and tested |
| Every candidate constrained | A bounded, owner-compatible fallback is defined; no busy loop, invented capability or guard bypass |
| Restart with existing Q values | Historical policy values are preserved and the new decision rule behaves deterministically with them |
| Memory preservation | No episode, transition, evaluation, belief, curiosity record or semantic revision is deleted or backfilled |

The owner subsequently approved the amended B8 contract, retaining legacy reward semantics and resolving autonomous eligibility. No disk-cleanup capability or B9/B10 completion is claimed.
