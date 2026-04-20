"""Validation rules that span multiple entities.

These require looking at the web as a whole. Each function is pure:
(EpistemicWeb) -> list[Finding].

Structural invariants (refs exist, no cycles, bidirectional links) live
in web.py and are enforced at mutation time.

Semantic/coverage invariants live here and are checked on demand.
"""
from __future__ import annotations

from .types import (
    AssumptionType,
    ClaimCategory,
    ClaimStatus,
    ClaimType,
    ConfidenceTier,
    Criticality,
    EvidenceKind,
    Finding,
    MeasurementRegime,
    ObservationStatus,
    PredictionStatus,
    Severity,
    TheoryStatus,
)
from .ports import EpistemicWebPort


def validate_tier_constraints(web: EpistemicWebPort) -> list[Finding]:
    """Validate confidence tier and measurement regime constraints across predictions.

    Enforces the following rules for each prediction in the web:

    - ``FULLY_SPECIFIED`` predictions must have exactly zero free parameters.
      Violation severity: CRITICAL.
    - ``CONDITIONAL`` predictions should declare at least one assumption in
      ``conditional_on``. Violation severity: WARNING.
    - For ``MEASURED`` regime, an ``observed`` value is required once the
      prediction reaches an adjudicated status (CONFIRMED, STRESSED, or
      REFUTED). Violation severity: CRITICAL.
    - For ``BOUND_ONLY`` regime, an ``observed_bound`` is required once
      adjudicated. Violation severity: CRITICAL.

    PENDING and NOT_YET_TESTABLE predictions are allowed to omit observed
    values even when a measurement regime is set, supporting the common
    workflow of registering a prediction before observations are recorded.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: All tier/measurement findings found.
    """
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        if pred.tier == ConfidenceTier.FULLY_SPECIFIED and pred.free_params != 0:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                f"FULLY_SPECIFIED prediction has {pred.free_params} free params (must be 0)",
            ))
        if pred.tier == ConfidenceTier.CONDITIONAL and not pred.conditional_on:
            findings.append(Finding(
                Severity.WARNING,
                f"predictions/{pid}",
                "CONDITIONAL prediction missing 'conditional_on'",
            ))

        requires_recorded_evidence = pred.status in {
            PredictionStatus.CONFIRMED,
            PredictionStatus.STRESSED,
            PredictionStatus.REFUTED,
        }

        if (
            requires_recorded_evidence
            and pred.measurement_regime == MeasurementRegime.MEASURED
            and pred.observed is None
        ):
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime=MEASURED requires an observed value",
            ))
        if (
            requires_recorded_evidence
            and pred.measurement_regime == MeasurementRegime.BOUND_ONLY
            and pred.observed_bound is None
        ):
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime=BOUND_ONLY requires observed_bound",
            ))
    return findings


def validate_independence_semantics(web: EpistemicWebPort) -> list[Finding]:
    """Validate independence group membership consistency and separation completeness.

    Checks two distinct properties:

    1. **Back-reference consistency** (CRITICAL): Every prediction listed in
       a group's ``member_predictions`` must have its ``independence_group``
       field pointing back to that group.

    2. **Pairwise separation completeness** (CRITICAL): Every pair of groups
       that both have at least one member prediction must have a corresponding
       ``PairwiseSeparation`` record. Empty groups (declarations of intent)
       are exempt to avoid registration deadlocks.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: All independence-related findings found.
    """
    findings: list[Finding] = []

    # Check group membership consistency
    for gid, group in web.independence_groups.items():
        for pid in group.member_predictions:
            pred = web.predictions.get(pid)
            if pred is None:
                continue
            if pred.independence_group != gid:
                findings.append(Finding(
                    Severity.CRITICAL,
                    f"independence_groups/{gid}",
                    f"Prediction {pid} listed but doesn't back-reference this group",
                ))

    # Check pairwise separation completeness.
    # A separation is only required once BOTH groups have at least one member
    # prediction. An empty group is a declaration of intent — requiring a
    # separation before any predictions exist creates an unresolvable
    # registration deadlock (the separation needs both groups, the second
    # group needs the separation to pass validation).
    group_ids = sorted(web.independence_groups.keys())
    seen_pairs: set[tuple[str, str]] = set()
    for ps in web.pairwise_separations.values():
        pair = (min(ps.group_a, ps.group_b), max(ps.group_a, ps.group_b))
        seen_pairs.add(pair)

    for i, a in enumerate(group_ids):
        for b in group_ids[i + 1:]:
            if (not web.independence_groups[a].member_predictions
                    or not web.independence_groups[b].member_predictions):
                continue
            pair = (min(a, b), max(a, b))
            if pair not in seen_pairs:
                findings.append(Finding(
                    Severity.CRITICAL,
                    "independence_groups/pairwise_separation_basis",
                    f"Missing pairwise separation for ({a}, {b})",
                ))

    return findings


def validate_coverage(web: EpistemicWebPort) -> list[Finding]:
    """Check for analysis and prediction coverage gaps across the web.

    Reports advisory findings for structural blind spots:

    - ``NUMERICAL`` claims with no linked analyses (INFO).
    - ``EMPIRICAL`` assumptions with no ``falsifiable_consequence`` (WARNING).
    - Any predictions in ``STRESSED`` status requiring vigilance (WARNING).

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: All coverage findings found.
    """
    findings: list[Finding] = []

    for cid, claim in web.claims.items():
        if claim.category == ClaimCategory.NUMERICAL and not claim.analyses:
            findings.append(Finding(
                Severity.INFO,
                f"claims/{cid}",
                "Numerical claim has no linked analyses",
            ))

    for aid, assumption in web.assumptions.items():
        if assumption.type == AssumptionType.EMPIRICAL and not assumption.falsifiable_consequence:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "Empirical [E] assumption has no falsifiable consequence",
            ))

    stressed = [
        pid for pid, p in web.predictions.items()
        if p.status == PredictionStatus.STRESSED
    ]
    if stressed:
        findings.append(Finding(
            Severity.WARNING,
            "predictions",
            f"STRESSED predictions requiring vigilance: {stressed}",
        ))

    return findings


def validate_assumption_testability(web: EpistemicWebPort) -> list[Finding]:
    """Flag assumptions with a falsifiable consequence but no testing predictions.

    If an assumption declares a ``falsifiable_consequence`` but has an empty
    ``tested_by`` set, it means the assumption claims to be testable but
    nothing in the web is actually testing it. Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per untested assumption with a
            falsifiable consequence.
    """
    findings: list[Finding] = []
    for aid, assumption in web.assumptions.items():
        if assumption.falsifiable_consequence and not assumption.tested_by:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "Assumption has falsifiable_consequence but no predictions in tested_by",
            ))
    return findings


def validate_retracted_claim_citations(web: EpistemicWebPort) -> list[Finding]:
    """Flag predictions or claims that still cite a retracted claim.

    Retracted claims are invalidated assertions that should not be relied
    upon. Any prediction whose ``claim_ids`` includes a retracted claim,
    or any claim whose ``depends_on`` includes a retracted claim, is a
    structural integrity violation. Severity: CRITICAL.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One CRITICAL finding per prediction or claim that
            cites a retracted claim.
    """
    findings: list[Finding] = []
    retracted = {
        cid for cid, c in web.claims.items()
        if c.status == ClaimStatus.RETRACTED
    }
    if not retracted:
        return findings
    for pid, pred in web.predictions.items():
        cited = pred.claim_ids & retracted
        if cited:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                f"Prediction cites retracted claim(s): {sorted(cited)}",
            ))
    for cid, claim in web.claims.items():
        bad_deps = claim.depends_on & retracted
        if bad_deps:
            findings.append(Finding(
                Severity.CRITICAL,
                f"claims/{cid}",
                f"Claim depends on retracted claim(s): {sorted(bad_deps)}",
            ))
    return findings


def validate_implicit_assumption_coverage(web: EpistemicWebPort) -> list[Finding]:
    """Flag assumptions that silently underpin predictions but are never tested.

    An assumption is 'silently depended on' if it appears in the implicit
    assumption set of one or more predictions (via claim lineage, depends_on
    chains, or conditional_on) but has no ``tested_by`` coverage and is not
    in the ``tests_assumptions`` of any prediction that depends on it.

    Reports one INFO finding per uncovered assumption, not per prediction.
    This helps researchers identify hidden structural dependencies that
    may represent blind spots in the testing strategy.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One INFO finding per uncovered implicit assumption.
    """
    findings: list[Finding] = []

    # Build: for each assumption, which predictions implicitly depend on it
    implicit_dependents: dict = {}
    for pid in web.predictions:
        for aid in web.prediction_implicit_assumptions(pid):
            implicit_dependents.setdefault(aid, set()).add(pid)

    for aid, pids in implicit_dependents.items():
        assumption = web.assumptions.get(aid)
        if assumption is None:
            continue
        # Explicit testers: predictions in the dependent set that list this assumption in tests_assumptions
        explicit_testers = {
            pid for pid in pids
            if aid in web.predictions[pid].tests_assumptions
        }
        if not assumption.tested_by and not explicit_testers:
            findings.append(Finding(
                Severity.INFO,
                f"assumptions/{aid}",
                f"Assumption implicitly underpins {len(pids)} prediction(s) "
                f"but has no tested_by coverage: {sorted(pids)}",
            ))

    return findings


def validate_tests_conditional_overlap(web: EpistemicWebPort) -> list[Finding]:
    """Flag predictions that both test and condition on the same assumption.

    ``tests_assumptions`` means 'this outcome bears on whether the assumption
    holds'. ``conditional_on`` means 'this prediction is only valid if the
    assumption holds'. These are logically contradictory for the same
    assumption — you cannot simultaneously test something you assume to be
    true. Severity: CRITICAL.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One CRITICAL finding per prediction with overlap
            between ``tests_assumptions`` and ``conditional_on``.
    """
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        overlap = pred.tests_assumptions & pred.conditional_on
        if overlap:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                f"Assumption(s) in both tests_assumptions and conditional_on "
                f"(logically contradictory): {sorted(overlap)}",
            ))
    return findings


def validate_foundational_claim_deps(web: EpistemicWebPort) -> list[Finding]:
    """Flag foundational claims that have dependencies on other claims.

    Foundational claims are axioms — by definition they should not depend
    on other claims. Having ``depends_on`` entries on a foundational claim
    indicates a misclassification or structural error. Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per foundational claim with non-empty
            ``depends_on``.
    """
    findings: list[Finding] = []
    for cid, claim in web.claims.items():
        if claim.type == ClaimType.FOUNDATIONAL and claim.depends_on:
            findings.append(Finding(
                Severity.WARNING,
                f"claims/{cid}",
                f"Foundational claim has depends_on entries "
                f"(foundational claims are axioms): {sorted(claim.depends_on)}",
            ))
    return findings


def validate_evidence_consistency(web: EpistemicWebPort) -> list[Finding]:
    """Flag logically inconsistent evidence_kind/tier combinations.

    ``FIT_CHECK`` is a fit/consistency check by definition — it cannot
    simultaneously be a ``NOVEL_PREDICTION`` (which would be
    ``FULLY_SPECIFIED`` or ``CONDITIONAL``). Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per prediction with a FIT_CHECK tier
            marked as NOVEL_PREDICTION evidence kind.
    """
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        if (pred.tier == ConfidenceTier.FIT_CHECK
                and pred.evidence_kind == EvidenceKind.NOVEL_PREDICTION):
            findings.append(Finding(
                Severity.WARNING,
                f"predictions/{pid}",
                "FIT_CHECK prediction marked as NOVEL_PREDICTION — "
                "fit checks are definitionally not novel predictions",
            ))
    return findings


def validate_conditional_assumption_pressure(web: EpistemicWebPort) -> list[Finding]:
    """Flag confirmed/stressed predictions conditional on assumptions under pressure.

    If prediction P is conditional on assumption A (A in ``P.conditional_on``),
    and some other prediction Q that explicitly tests A (A in
    ``Q.tests_assumptions``) has been REFUTED, then A is under adversarial
    pressure. P's status was established when A was considered sound; that
    basis is now in question.

    Only CONFIRMED and STRESSED predictions are flagged — PENDING predictions
    haven't been confirmed yet (no false sense of security to break), and
    REFUTED predictions are already in a terminal state.

    This does NOT automatically change any prediction's status. It surfaces
    the structural connection so the researcher cannot silently overlook it.
    Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per affected prediction, identifying
            the pressured assumptions and the refuting predictions.
    """
    findings: list[Finding] = []

    # Build: assumption → set of REFUTED predictions that test it
    # and some other prediction Q that explicitly tests A (A in Q.tests_assumptions)
    # has been REFUTED, then A is under adversarial pressure. P's status was
    # established when A was considered sound; that basis is now in question.

    # Only CONFIRMED and STRESSED predictions are flagged — PENDING predictions
    # haven't been confirmed yet (no false sense of security to break), and
    # REFUTED predictions are already in a terminal state.

    # This does NOT automatically change any prediction's status. It surfaces
    # the structural connection so the researcher cannot silently overlook it.
    refuted_tests: dict = {}
    for pid, pred in web.predictions.items():
        if pred.status == PredictionStatus.REFUTED:
            for aid in pred.tests_assumptions:
                refuted_tests.setdefault(aid, set()).add(pid)

    if not refuted_tests:
        return findings

    active_statuses = {PredictionStatus.CONFIRMED, PredictionStatus.STRESSED}
    for pid, pred in web.predictions.items():
        if pred.status not in active_statuses:
            continue
        pressured = pred.conditional_on & refuted_tests.keys()
        if not pressured:
            continue
        refuting_preds: set = set()
        for aid in pressured:
            refuting_preds.update(refuted_tests[aid])
        findings.append(Finding(
            Severity.WARNING,
            f"predictions/{pid}",
            f"Prediction {pid} is {pred.status.value} but is conditional on "
            f"assumption(s) {sorted(pressured)} whose tester(s) "
            f"{sorted(refuting_preds)} have been REFUTED. "
            f"The conditional basis of this prediction is now under pressure.",
        ))

    return findings


def validate_stress_criteria(web: EpistemicWebPort) -> list[Finding]:
    """Flag STRESSED predictions without explicit stress criteria.

    The boundary between CONFIRMED and STRESSED is philosophically
    ambiguous. Making the researcher declare ``stress_criteria`` upfront
    — what evidence would constitute tension without full refutation —
    ensures the adjudication is explicit and auditable rather than
    ad-hoc. Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per STRESSED prediction missing
            ``stress_criteria``.
    """
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        if pred.status == PredictionStatus.STRESSED and not pred.stress_criteria:
            findings.append(Finding(
                Severity.WARNING,
                f"predictions/{pid}",
                "STRESSED prediction has no stress_criteria — the boundary "
                "between CONFIRMED and STRESSED should be declared explicitly",
            ))
    return findings


def validate_retracted_observation_citations(web: EpistemicWebPort) -> list[Finding]:
    """Flag observations that still link to retracted claims or disputed/retracted observations.

    If an observation's ``related_claims`` includes claims that have been
    retracted, the observation's interpretation may be compromised.
    Also flags observations in RETRACTED status that are still linked to
    predictions. Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per problematic observation.
    """
    findings: list[Finding] = []
    retracted_claims = {
        cid for cid, c in web.claims.items()
        if c.status == ClaimStatus.RETRACTED
    }
    for oid, obs in web.observations.items():
        cited = obs.related_claims & retracted_claims
        if cited:
            findings.append(Finding(
                Severity.WARNING,
                f"observations/{oid}",
                f"Observation references retracted claim(s): {sorted(cited)}",
            ))
        if obs.status == ObservationStatus.RETRACTED and obs.predictions:
            findings.append(Finding(
                Severity.WARNING,
                f"observations/{oid}",
                f"Retracted observation still linked to prediction(s): "
                f"{sorted(obs.predictions)}",
            ))
    return findings


def validate_theory_abandonment_impact(web: EpistemicWebPort) -> list[Finding]:
    """Flag claims whose only theoretical motivation comes from abandoned/superseded theories.

    If all theories referenced by a claim have been abandoned or superseded,
    the claim has lost its theoretical motivation. This does not invalidate
    the claim (it may still be empirically supported), but the researcher
    should be aware. Severity: WARNING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One WARNING per claim with only abandoned/superseded
            theoretical motivation.
    """
    findings: list[Finding] = []
    terminal_statuses = {TheoryStatus.ABANDONED, TheoryStatus.SUPERSEDED}
    for cid, claim in web.claims.items():
        if not claim.theories:
            continue
        all_terminal = all(
            web.theories.get(tid) is not None
            and web.theories[tid].status in terminal_statuses
            for tid in claim.theories
        )
        if all_terminal:
            findings.append(Finding(
                Severity.WARNING,
                f"claims/{cid}",
                f"All motivating theories are abandoned/superseded: "
                f"{sorted(claim.theories)}. Claim has lost theoretical "
                f"motivation.",
            ))
    return findings


def validate_load_bearing_assumption_coverage(web: EpistemicWebPort) -> list[Finding]:
    """Flag LOAD_BEARING or HIGH criticality assumptions with no tested_by coverage.

    Load-bearing assumptions are single points of failure. If they have
    no predictions testing them, the project has a critical blind spot.
    Severity: WARNING for HIGH, CRITICAL for LOAD_BEARING.

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: One finding per high-criticality untested assumption.
    """
    findings: list[Finding] = []
    for aid, assumption in web.assumptions.items():
        if assumption.criticality == Criticality.LOAD_BEARING and not assumption.tested_by:
            findings.append(Finding(
                Severity.CRITICAL,
                f"assumptions/{aid}",
                "LOAD_BEARING assumption has no predictions in tested_by — "
                "this is a single point of failure with no active test",
            ))
        elif assumption.criticality == Criticality.HIGH and not assumption.tested_by:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "HIGH criticality assumption has no predictions in tested_by",
            ))
    return findings


def validate_all(web: EpistemicWebPort) -> list[Finding]:
    """Run all domain invariant validators and return the combined findings.

    Executes every semantic/coverage validator in a fixed order and
    concatenates their results. Structural invariants (refs exist, no
    cycles, bidirectional links) are enforced at mutation time in
    ``web.py``; this function covers the on-demand semantic checks.

    Validator execution order:
        1. Retracted claim citations
        2. Tests/conditional overlap
        3. Tier constraints
        4. Evidence consistency
        5. Independence semantics
        6. Coverage gaps
        7. Assumption testability
        8. Implicit assumption coverage
        9. Foundational claim dependencies
        10. Conditional assumption pressure
        11. Stress criteria
        12. Retracted observation citations
        13. Theory abandonment impact
        14. Load-bearing assumption coverage

    Args:
        web: The epistemic web to validate.

    Returns:
        list[Finding]: All findings from all validators, concatenated
            in execution order.
    """
    return (
        validate_retracted_claim_citations(web)
        + validate_tests_conditional_overlap(web)
        + validate_tier_constraints(web)
        + validate_evidence_consistency(web)
        + validate_independence_semantics(web)
        + validate_coverage(web)
        + validate_assumption_testability(web)
        + validate_implicit_assumption_coverage(web)
        + validate_foundational_claim_deps(web)
        + validate_conditional_assumption_pressure(web)
        + validate_stress_criteria(web)
        + validate_retracted_observation_citations(web)
        + validate_theory_abandonment_impact(web)
        + validate_load_bearing_assumption_coverage(web)
    )
