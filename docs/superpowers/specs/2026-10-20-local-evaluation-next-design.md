# Local evaluation prerequisites: proposed next engineering design

Status: design preparation under Gio's no-new-spending constraint, 2026-10-20.
No implementation, experiment, permit, signature or gate acceptance is supplied.
The analysis is based on source commit
`042b90384e200590b076896961e7f450935a5f62`.

## Purpose and recommendation

Use the existing development machine to make scientific evidence reproducible
before investing in infrastructure. Separate the next work into frozen
reexecution and admission/retention designs. Both can be inspected locally;
neither is solved by choosing a cloud host.

The existing post-ACK repair supports bounded online evidence and fresh online
reexecution. It does not implement full fresh A/C frozen reproduction. The
supplied P1 addendum expressly calls for a separately reviewed amendment for that
path and for the retention conflict. This document prepares that review.

## Frozen reproduction

Current concrete gaps:

| Area | Current limitation |
|---|---|
| `development/evaluation/reexecution.py` | Compatibility admits PREQUENTIAL; input handling rejects C and assumes default training/measured journal keys plus one `initial` checkpoint. |
| `development/evaluation/prequential.py` | `PrequentialDriver.run` stops its worker, so A needs an explicit train-to-freeze lifecycle before cleanup. |
| `development/evaluation/fixtures.py` and `worker.py` | C fixture helpers exist, but the closed worker protocol has no fixture-preparation operation. |
| `development/evaluation/frozen.py` and `artifacts.py` | Real probes have no learning ACK. Their prediction/observation fields are rejected by the generic event path, while current derivation consumes journal checkpoints. |
| `artifacts.py` and `metrics/producers.py` | Shared-plan measurements need exact member evidence attribution; C requires variant-scoped source identities rather than one source substituted across variants. |

Recommend a protocol-specific orchestrator plus a versioned, typed frozen-probe
record. Do not relax the online checks or manufacture learning checkpoints.

1. Bind exact member, shared frozen plan, initial-state recipe, settings, phase
   RNG/UUID/clock streams, fixture versions, ordered subcases, read times and
   checkpoint identities. Missing historical inputs remain incompatible.
2. For A, regenerate the declared 320-transition training prefix, freeze before
   releasing the mutable worker, verify cleanup and then run 80 frozen probes.
3. For C, regenerate the declared 128-transition fixture and approved
   fresh/contradictory/unavailable/stale sources. Preserve source lineage and
   execute four subcases of 16 probes as one registered member.
4. Validate bounded probe evidence separately from post-ACK updates. Retain the
   actual selection, candidates, action-dependent outcome, read time, source
   identity and captured baseline provenance. There is no learning ACK or
   confirmed update to invent.
5. Derive and publish from the explicit member and variant bindings. Preserve
   every registered identity, formula and unavailable/applicability rule.
   Count training transitions and frozen probes distinctly.
6. Compare canonical science and frozen source identities from the fresh run
   while preserving original artifacts byte for byte.

Alternative: probing a copy of a validated stored frozen checkpoint can test
assay-from-checkpoint reproduction. It does not regenerate A's training or C's
fixture construction and cannot satisfy the full fresh-reexecution requirement.

Before implementation, settle through the required independent design review:
the evidence/count contract, phase-stream continuation versus restart, C clone
and source binding, shared-plan member attribution, and any published-contract
amendment. No experiment ID, plan body, scientific formula, schema-v7 producer,
truth boundary or resource ceiling changes are proposed.

Future regression evidence must include genuine A train/freeze/probe/publication/
fresh reproduction, all C subcases with their distinct sources, immutable probe
databases, literal losses and denominators, truthful absent provenance, and
unchanged originals. Missing/duplicate probes, wrong identities, changed stream
or read time, partial training, cleanup failure, writes and exhausted caps must
refuse or report incompatibility/divergence. Preserve existing online checks.

## Admission and retention

DEC-04 is an independent admission defect: fresh reexecution checks compatibility
before rejecting a global published index of 32. The design distinguishes
**32 per registered batch** from **60 retained runs per owned root**.

The proposed correction is a cheap capacity check before compatibility, followed
by a root lease, current byte/occupancy reconciliation, atomic reservation,
one-use-key consumption and only then worker allocation. Published runs,
partials, workspaces and reservations all count. Existing `Budget` reservations
are in memory; they do not themselves establish durable cross-process admission.
This remains a proposed ordering pending the control-plane design and DEC-04
decision, not a mechanical replacement of one constant.

The retention arithmetic remains:

| Arrangement | Consequence |
|---|---|
| One root: 30 originals + 30 fresh results | 60 retained slots, zero spare. Cannot satisfy the proposed two-spare margin. Smaller batches do not change final occupancy. |
| One root: 30 originals + only 20 currently supported online reproductions | A limited report at most; omits full frozen reproduction and cannot establish full G7. Failures/partials still count. |
| Two explicitly fixed and bound roots | Candidate for nondestructive review: preserve originals in the source root, write fresh results into the destination and compare verified evidence across them. Current APIs do not implement this. |

The two-root candidate is worth reviewing, not silently adopting. Its amendment
must define whether root limits are per root or campaign-wide, bind the fixed
root pair in authority and lineage, preserve complete inventory and prevent
duplicate attempts across roots. It must not become an unlimited-root escape
from global limits. Owner/design decisions must establish the scope of the
proposed two-slot and 80%-byte margins before qualification.

Thirty simultaneous 448-MiB reservations would use 13.125 GiB, already above
80% of the 16-GiB root cap (12.8 GiB). Prefer a complete campaign forecast plus
sequential atomic run reservations. That avoids unnecessary simultaneous
reservations; it does not remove final retained bytes, control overhead, partials
or crash remnants from the forecast.

Future tests: batch 31/32/33; root 59/60/61; partial retention; concurrent
occupancy; duplicate originals; restart/crash recovery; peak bytes; zero-write
refusal; wrong-root/lineage rejection; immutable originals; and full member
reconciliation including failures and unavailable results.

## Sequence and remaining authority

First review these contracts and policy choices. Then prepare a bounded
implementation plan for the approved design, using disposable technical
identities on existing equipment. Review and verify resulting engineering
changes before integration. Qualified-host evidence, personal Stage A closure,
independent administration, canonical permits, registered dispatch and G7
remain separate gates. No source change follows automatically from this note.

Controlling references:

- [B10 design](2026-10-02-b10-development-evaluation-design.md)
- [Current readiness worksheet](../../evaluation/2026-10-20-admission-readiness.md)
- [No-new-spending infrastructure proposal](2026-10-20-i31-infrastructure-proposal.md)
- Supplied `SEED_I31_P1_Safe_Execution_Enablement_Design_2026-10-16.md`,
  resource/margin section, and
  `SEED_I31_P1_Review_Disposition_Addendum_v1_1_2026-10-16.md`,
  DEC-04, DEC-05 and DEC-06 sections. These records are preserved externally.
