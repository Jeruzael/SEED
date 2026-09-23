# Review follow-ups

## Low-disk reward versus suppressed consolidation

**OPEN: separate owner authorization required.** Roadmap owner: B8 decision-system
upgrade, unless the owner authorizes a distinct narrowly scoped change. Reproduced
2026-09-23 against reviewed base f18ed31 and the unchanged learner/consolidator in
post-B6 hardening. This issue is documented, not fixed.

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

The owner must approve the intended reward semantics and these scenarios before
implementation. This follow-up does not authorize B8 or mark any later batch done.
