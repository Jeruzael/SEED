"""I30: the 22-criterion B10 technical acceptance matrix.

Maps every acceptance criterion of the approved implementation plan
(section 7 traceability) to the real tests that enforce it, the
evidence record that governs it, and its engineering gate G1-G6.
Technical and empirical status are separate: G1-G6 establish
engineering readiness, while every empirical portion remains
PENDING_EMPIRICAL until a separately authorized I31 evaluation
produces actual registered evidence (docs/evaluation/
b10-v1-results.md, which does not exist during I30).

The matrix refuses full scientific acceptance whenever any required
technical evidence is missing, unidentified or failed, and refuses
to let an empirical requirement be marked complete from technical
fixtures or from I30's own authorization.
"""
import re
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from development.evaluation.contracts import ContractError

REPO = Path(__file__).resolve().parents[2]
EMPIRICAL_RESULTS = 'docs/evaluation/b10-v1-results.md'

TECHNICAL_PASS = 'TECHNICAL_PASS'
TECHNICAL_FAIL = 'TECHNICAL_FAIL'
NOT_VERIFIED = 'NOT_VERIFIED'
PENDING_EMPIRICAL = 'PENDING_EMPIRICAL'
EMPIRICAL_COMPLETE = 'EMPIRICAL_COMPLETE'
_GATES = ('G1', 'G2', 'G3', 'G4', 'G5', 'G6')


@dataclass(frozen=True)
class Criterion:
    number: int
    description: str
    component: str
    tests: tuple[str, ...]
    evidence: str
    gate: str
    technical: str = TECHNICAL_PASS
    empirical: str = PENDING_EMPIRICAL
    note: str = ''


CRITERIA = (
    Criterion(1, 'Identity, no host access, no installed state, unchanged cognition',
              'profile/bootstrap/state (I03-I07, I13)',
              ('test_dirty_or_changed_source_rejected',
               'test_bound_clock_and_host_poison',
               'test_adapter_matches_original_cycle'),
              'docs/reviews/2026-10-04-b10-foundation-closure.md', 'G1'),
    Criterion(2, 'Evaluator truth isolation; no evaluator Q or dependency',
              'paths/channel (I03, I08)',
              ('test_dependency_direction',
               'test_all_forbidden_dispatch_and_sentinels',
               'test_truth_absent_in_all_learner_state'),
              'docs/evaluation/engineering-gates.md', 'G2'),
    Criterion(3, 'Frozen raw immutability and assay labels',
              'frozen/fixtures (I11, I15)',
              ('test_all_frozen_tables_and_db_bytes_equal',
               'test_reflect_consolidate_are_assays',
               'test_c_conflict_is_producer_owned_not_forged_policy',
               'test_stale_uses_301_seconds_without_mutation'),
              'docs/reviews/2026-10-04-b10-protocols-closure.md', 'G4',
              note='Plan name test_all_c_mutations_precede_freeze maps to '
                   'the producer-owned C fixture tests: fixture mutations '
                   'are producer setup preceding the freeze, after which '
                   'the frozen worker cannot mutate.'),
    Criterion(4, 'Score before learning, no ACK overload, failure fidelity',
              'checkpoint/adapters (I09, I10, I12, I13)',
              ('test_fsync_precedes_constant_ack',
               'test_ack_path_calls_no_aggregates',
               'test_pre_ack_failure_ladder_has_no_current_learning',
               'test_post_ack_failure_preserves_actual_prefix',
               'test_external_post_ack_failure_never_relearns'),
              'docs/reviews/2026-10-04-b10-protocols-closure.md', 'G3',
              note='Plan name test_every_failure_stage_is_accounted maps '
                   'to the failure-fidelity ladder tests, which account '
                   'for every injected failure stage.'),
    Criterion(5, 'All families, protocols and bounds with seed accounting',
              'coordinator/suite (I14-I16, I30)',
              ('test_phase_lengths_and_exposure',
               'test_suite_expansion_and_accounting'),
              'docs/evaluation/science-infrastructure-gates.md', 'G5'),
    Criterion(6, 'Literal rules, math, exposure, populations and baselines',
              'baselines/prediction metrics (I14, I17, I18)',
              ('test_four_row_matched_fixture',
               'test_rest_window_and_lifetime_literals',
               'test_adaptation_exposure_rules',
               'test_paired_windows_and_standardization'),
              'docs/evaluation/science-infrastructure-gates.md', 'G5'),
    Criterion(7, 'B4-B8 fact fidelity, zero guards, no evaluator fabrication',
              'metric producers (I19)',
              ('test_world_lifetime_and_contradictions',
               'test_curiosity_literal_and_missing',
               'test_semantic_opportunities_and_provenance',
               'test_self_claims_are_source_checked',
               'test_decision_links_q_and_guards'),
              'docs/evaluation/science-infrastructure-gates.md', 'G5'),
    Criterion(8, 'Two digests, replay and same-profile re-execution',
              'science/integrity/replay (I22-I25)',
              ('test_science_digest_cases',
               'test_integrity_distinct_from_science',
               'test_replay_never_calls_cognition',
               'test_same_profile_science_matches'),
              'docs/evaluation/artifact-replay-gates.md', 'G6'),
    Criterion(9, 'Immutable partial/complete publication, no report ingestion, security',
              'artifacts (I21, I23, I24)',
              ('test_partial_inventory_preserved',
               'test_atomic_publish_crash_ladder',
               'test_inventory_attack_and_replacement'),
              'docs/evaluation/artifact-replay-gates.md', 'G6'),
    Criterion(10, 'All limits, prefix retention, no silent trimming',
              'limits across I03-I28',
              ('test_root_attack_matrix',
               'test_every_commit_enforces_growth',
               'test_stale_attempt_is_not_sample',
               'test_bound_every_file_and_snapshot',
               'test_all_route_bounds',
               'test_evaluation_dom_and_chart_caps'),
              'docs/evaluation/artifact-replay-gates.md', 'G6'),
    Criterion(11, 'Observer accessibility and no execution endpoint',
              'Astra Evaluation (I26-I29)',
              ('test_get_only_even_operator',
               'test_negative_findings_visible_on_completed_run'),
              'docs/evaluation/browser-verification.md', 'G6'),
    Criterion(12, 'Existing local/hosted tests, scenarios and baselines retained',
              'release verification (I30)',
              ('test_technical_acceptance_matrix',),
              'docs/evaluation/engineering-gates.md', 'G6',
              note='Cross-cutting regression evidence for G1-G6: the full '
                   'repository suite, the seven pre-existing standalone '
                   'scenarios and protected-scope byte checks.'),
)

CRITERIA += (
    Criterion(13, 'Durable freeze ordering: freeze precedes any dispatch',
              'analysis (I02, I20)',
              ('test_freeze_precedes_dispatch',),
              'docs/reviews/2026-10-11-b10-science-infrastructure-closure.md',
              'G1'),
    Criterion(14, 'No plan field drift or identity rewrite',
              'analysis (I02, I20)',
              ('test_every_analysis_field_is_frozen',),
              'docs/reviews/2026-10-11-b10-science-infrastructure-closure.md',
              'G1'),
    Criterion(15, 'Complete exact registered measurement inventory',
              'reporting/suite (I20, I21, I30)',
              ('test_default_all_33_measurements_preregistered_and_applicable',
               'test_bad_completed_inventory_invalidates',
               'test_suite_keeps_failed_seeds_and_incomplete_prefixes',
               'test_verify_suite_measurement_inventory'),
              'docs/evaluation/science-infrastructure-gates.md', 'G5',
              note='Plan names test_all_registered_measurements_accounted '
                   'and test_suite_counts_failed_seeds map to the '
                   'preregistered-inventory and failed-seed accounting '
                   'tests in test_reporting.py.'),
    Criterion(16, 'Execution state and scientific findings are independent',
              'reporting/Astra (I20, I28)',
              ('test_execution_and_finding_states_independent',
               'test_negative_findings_visible_on_completed_run'),
              'docs/reviews/2026-10-11-b10-science-infrastructure-closure.md',
              'G5',
              note='Plan name test_execution_and_findings_independent is '
                   'implemented as test_execution_and_finding_states_'
                   'independent in test_reporting.py.'),
    Criterion(17, 'Negative, mixed, inconclusive and missing honesty',
              'metrics/reporting (I18, I20)',
              ('test_literal_metrics_and_support',
               'test_execution_and_finding_states_independent'),
              'docs/evaluation/science-infrastructure-gates.md', 'G5'),
    Criterion(18, 'Evaluation storage isolation; absent home fails closed',
              'paths/reader (I03, I08, I26)',
              ('test_no_inherited_home_or_secrets',
               'test_truth_absent_in_all_learner_state',
               'test_optional_reader_absence_and_no_home_fallback'),
              'docs/reviews/2026-10-04-b10-foundation-closure.md', 'G1'),
    Criterion(19, 'Mechanical one-way dependency; absent evaluator; optional reader',
              'dependency/reader (I03, I26)',
              ('test_dependency_direction',
               'test_seed_operates_without_evaluator',
               'test_optional_reader_absence_and_no_home_fallback'),
              'docs/evaluation/astra-evaluation-gates.md', 'G1'),
    Criterion(20, 'Complete plan/freeze identity in digests and replay',
              'science/integrity/replay (I02, I22-I24)',
              ('test_exact_incidental_projection',
               'test_science_digest_cases',
               'test_replay_never_calls_cognition'),
              'docs/evaluation/artifact-replay-gates.md', 'G6'),
    Criterion(21, 'Full compatibility, not just plan digest equality',
              're-execution/Astra comparison (I25, I26, I28)',
              ('test_compatibility_more_than_plan_digest',
               'test_comparison_blocks_incompatibility'),
              'docs/reviews/2026-10-12-b10-astra-evaluation-closure.md', 'G6'),
    Criterion(22, 'Exploratory diagnostics never replace primary findings',
              'reporting/Astra (I20, I28)',
              ('test_exploratory_never_replaces_primary',),
              'docs/reviews/2026-10-11-b10-science-infrastructure-closure.md',
              'G5'),
)


def _defined_test_names():
    names = set()
    for path in (REPO / 'tests').rglob('*.py'):
        names.update(re.findall(r'def (test_\w+)', path.read_text()))
    return names


def validate_matrix(rows, defined=None):
    """Structural honesty checks; any defect raises ContractError."""
    if defined is None:
        defined = _defined_test_names()
    if [row.number for row in rows] != list(range(1, 23)):
        raise ContractError()  # criteria must be exactly 1-22
    for row in rows:
        if row.gate not in _GATES:
            raise ContractError()  # engineering gates are G1-G6 only
        if not row.tests:
            raise ContractError()  # every criterion cites at least one test
        for name in row.tests:
            if name not in defined:
                raise ContractError()  # cited test cannot be identified
        if not (REPO / row.evidence).is_file():
            raise ContractError()  # cited evidence artifact is missing
        if row.technical not in (TECHNICAL_PASS, TECHNICAL_FAIL, NOT_VERIFIED):
            raise ContractError()  # unknown technical status
        if row.empirical not in (PENDING_EMPIRICAL, EMPIRICAL_COMPLETE):
            raise ContractError()  # unknown empirical status
        if row.empirical == EMPIRICAL_COMPLETE and \
                row.evidence != EMPIRICAL_RESULTS:
            # Empirical completion requires actual I31 evidence,
            # never technical fixtures.
            raise ContractError()
    return rows


def engineering_qualification(rows):
    validate_matrix(rows)
    return all(row.technical == TECHNICAL_PASS for row in rows)


def scientific_acceptance(rows):
    validate_matrix(rows)
    return all(row.empirical == EMPIRICAL_COMPLETE for row in rows) and \
        (REPO / EMPIRICAL_RESULTS).is_file()


def claim_full_acceptance(rows):
    """Full scientific acceptance is refused until G7 evidence exists."""
    if not (engineering_qualification(rows) and scientific_acceptance(rows)):
        raise ContractError()  # B10 scientific acceptance not established
    return True


def test_technical_acceptance_matrix():
    defined = _defined_test_names()
    validate_matrix(CRITERIA, defined)
    assert len(CRITERIA) == 22
    assert {row.gate for row in CRITERIA} == set(_GATES)
    assert engineering_qualification(CRITERIA)
    # Every empirical portion stays pending: G7 belongs to I31 alone.
    assert all(row.empirical == PENDING_EMPIRICAL for row in CRITERIA)
    assert not scientific_acceptance(CRITERIA)
    with pytest.raises(ContractError):
        claim_full_acceptance(CRITERIA)


def test_acceptance_matrix_refusals():
    defined = _defined_test_names()
    # An empirical requirement marked complete from technical evidence.
    forged = (replace(CRITERIA[0], empirical=EMPIRICAL_COMPLETE),) + \
        CRITERIA[1:]
    with pytest.raises(ContractError):
        validate_matrix(forged, defined)
    # A missing criterion.
    with pytest.raises(ContractError):
        validate_matrix(CRITERIA[:21], defined)
    # An unidentifiable cited test.
    ghost = (replace(CRITERIA[0], tests=('test_does_not_exist_anywhere',)),) \
        + CRITERIA[1:]
    with pytest.raises(ContractError):
        validate_matrix(ghost, defined)
    # Missing evidence artifact.
    lost = (replace(CRITERIA[0], evidence='docs/evaluation/nope.md'),) \
        + CRITERIA[1:]
    with pytest.raises(ContractError):
        validate_matrix(lost, defined)
    # A failed or unverified technical criterion blocks qualification.
    failed = (replace(CRITERIA[0], technical=TECHNICAL_FAIL),) + CRITERIA[1:]
    assert not engineering_qualification(failed)
    unverified = (replace(CRITERIA[0], technical=NOT_VERIFIED),) + \
        CRITERIA[1:]
    assert not engineering_qualification(unverified)
    # G7 is not an engineering gate and cannot be claimed here; neither
    # I30 authorization nor an unmerged head confers it.
    g7 = (replace(CRITERIA[0], gate='G7'),) + CRITERIA[1:]
    with pytest.raises(ContractError):
        validate_matrix(g7, defined)
    # A criterion with no cited test is a skipped mandatory check.
    skipped = (replace(CRITERIA[0], tests=()),) + CRITERIA[1:]
    with pytest.raises(ContractError):
        validate_matrix(skipped, defined)
