"""Validation rules that span multiple entities.

These require looking at the web as a whole. Each function is pure:
(EpistemicWeb) -> list[Finding].

Structural invariants (refs exist, no cycles, bidirectional links) live
in web.py and are enforced at mutation time.

Semantic/coverage invariants live here and are checked on demand.
"""
from __future__ import annotations

from .types import Finding, Severity
from .web import EpistemicWeb


def validate_tier_constraints(web: EpistemicWeb) -> list[Finding]:
    """Tier A: 0 free params. Tier B: must state conditional_on."""
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        if pred.tier.value == "A" and pred.free_params != 0:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                f"Tier A prediction has {pred.free_params} free params (must be 0)",
            ))
        if pred.tier.value == "B" and not pred.conditional_on:
            findings.append(Finding(
                Severity.WARNING,
                f"predictions/{pid}",
                "Tier B prediction missing 'conditional_on'",
            ))
        if pred.measurement_regime.value == "measured" and pred.observed is None:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime='measured' requires an observed value",
            ))
        if pred.measurement_regime.value == "bound_only" and pred.observed_bound is None:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime='bound_only' requires observed_bound",
            ))
    return findings


def validate_independence_semantics(web: EpistemicWeb) -> list[Finding]:
    """Groups must have consistent back-refs. Every pair needs separation basis."""
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

    # Check pairwise separation completeness
    group_ids = sorted(web.independence_groups.keys())
    seen_pairs: set[tuple[str, str]] = set()
    for ps in web.pairwise_separations:
        pair = (min(ps.group_a, ps.group_b), max(ps.group_a, ps.group_b))
        seen_pairs.add(pair)

    for i, a in enumerate(group_ids):
        for b in group_ids[i + 1:]:
            pair = (min(a, b), max(a, b))
            if pair not in seen_pairs:
                findings.append(Finding(
                    Severity.CRITICAL,
                    "independence_groups/pairwise_separation_basis",
                    f"Missing pairwise separation for ({a}, {b})",
                ))

    return findings


def validate_coverage(web: EpistemicWeb) -> list[Finding]:
    """Check for verification gaps."""
    findings: list[Finding] = []

    for cid, claim in web.claims.items():
        if claim.category == "numerical" and not claim.verified_by:
            findings.append(Finding(
                Severity.INFO,
                f"claims/{cid}",
                "Numerical claim lacks verification script",
            ))

    for aid, assumption in web.assumptions.items():
        if assumption.type == "E" and not assumption.falsifiable_consequence:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "Empirical [E] assumption has no falsifiable consequence",
            ))

    stressed = [
        pid for pid, p in web.predictions.items()
        if p.status.value == "STRESSED"
    ]
    if stressed:
        findings.append(Finding(
            Severity.WARNING,
            "predictions",
            f"STRESSED predictions requiring vigilance: {stressed}",
        ))

    return findings


def validate_all(web: EpistemicWeb) -> list[Finding]:
    """Run all domain validators."""
    return (
        validate_tier_constraints(web)
        + validate_independence_semantics(web)
        + validate_coverage(web)
    )
