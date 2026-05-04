"""Epistemic-graph metric read models and computation.

Pure functions. No I/O, no side effects. Counts entities, computes
detailed prediction statistics, and identifies coverage gaps.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.ports import EpistemicGraphPort
from ..epistemic.types import (
    AssumptionType,
    ConfidenceTier,
    HypothesisCategory,
    PredictionStatus,
    AssumptionStatus,
)


# ── Read models ──────────────────────────────────────────────────


@dataclass
class PredictionMetrics:
    """Aggregate statistics for predictions.

    Attributes:
        total: Total number of predictions in the graph.
        by_status: Count of predictions per ``PredictionStatus`` value.
        by_tier: Count of predictions per ``ConfidenceTier`` value.
        tier_a_confirmed: Number of Tier-A predictions with
            ``CONFIRMED`` status.
        tier_a_total: Total number of Tier-A predictions.
        stressed: IDs of predictions under epistemic stress (e.g.
            assumptions retracted or hypotheses refuted).
    """

    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_tier: dict[str, int] = field(default_factory=dict)
    tier_a_confirmed: int = 0
    tier_a_total: int = 0
    stressed: list[str] = field(default_factory=list)


@dataclass
class GraphMetrics:
    """Full metrics snapshot of an ``EpistemicGraph``.

    Provides entity counts for every collection plus detailed prediction
    metrics and coverage gap lists.

    Attributes:
        hypothesis_count: Number of hypotheses.
        assumption_count: Number of assumptions.
        analysis_count: Number of analyses.
        objective_count: Number of objectives.
        discovery_count: Number of discoveries.
        dead_end_count: Number of dead ends.
        parameter_count: Number of parameters.
        independence_group_count: Number of independence groups.
        pairwise_separation_count: Number of pairwise separations.
        prediction_metrics: Detailed prediction aggregate stats.
        uncovered_quantitative_hypotheses: IDs of numerical hypotheses that
            lack a covering prediction.
        empirical_assumptions_without_consequence: IDs of empirical
            assumptions that have no falsifiable consequence.
    """

    hypothesis_count: int = 0
    assumption_count: int = 0
    analysis_count: int = 0
    objective_count: int = 0
    discovery_count: int = 0
    dead_end_count: int = 0
    parameter_count: int = 0
    independence_group_count: int = 0
    pairwise_separation_count: int = 0
    prediction_metrics: PredictionMetrics = field(default_factory=PredictionMetrics)
    uncovered_quantitative_hypotheses: list[str] = field(default_factory=list)
    empirical_assumptions_without_consequence: list[str] = field(default_factory=list)


# ── Computation ──────────────────────────────────────────────────


def compute_metrics(graph: EpistemicGraphPort) -> GraphMetrics:
    """Compute aggregate metrics from the epistemic graph.

    Pure function. No I/O, no side effects. Counts entities in every
    collection, computes detailed prediction statistics, and identifies
    coverage gaps.

    Args:
        graph: The epistemic graph to analyze.

    Returns:
        GraphMetrics: A complete metrics snapshot.
    """
    # ── Entity counts ─────────────────────────────────────────────
    hypothesis_count = len(graph.hypotheses)
    assumption_count = len(graph.assumptions)
    analysis_count = len(graph.analyses)
    objective_count = len(graph.objectives)
    discovery_count = len(graph.discoveries)
    dead_end_count = len(graph.dead_ends)
    parameter_count = len(graph.parameters)
    independence_group_count = len(graph.independence_groups)
    pairwise_separation_count = len(graph.pairwise_separations)

    # ── Prediction metrics ────────────────────────────────────────
    predictions = list(graph.predictions.values())
    total = len(predictions)

    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    tier_a_confirmed = 0
    tier_a_total = 0
    stressed: list[str] = []

    for pred in predictions:
        status_key = pred.status.value
        by_status[status_key] = by_status.get(status_key, 0) + 1

        tier_key = pred.tier.value
        by_tier[tier_key] = by_tier.get(tier_key, 0) + 1

        if pred.tier == ConfidenceTier.FULLY_SPECIFIED:
            tier_a_total += 1
            if pred.status == PredictionStatus.CONFIRMED:
                tier_a_confirmed += 1

        if pred.status == PredictionStatus.STRESSED:
            stressed.append(str(pred.id))

    pred_metrics = PredictionMetrics(
        total=total,
        by_status=by_status,
        by_tier=by_tier,
        tier_a_confirmed=tier_a_confirmed,
        tier_a_total=tier_a_total,
        stressed=stressed,
    )

    # ── Coverage gaps ─────────────────────────────────────────────
    # Quantitative hypotheses with no covering prediction
    covered_hypotheses: set[object] = set()
    for pred in predictions:
        covered_hypotheses.update(pred.hypothesis_ids)

    uncovered_quantitative: list[str] = [
        str(h.id)
        for h in graph.hypotheses.values()
        if h.category == HypothesisCategory.QUANTITATIVE
        and h.id not in covered_hypotheses
    ]

    # Empirical assumptions missing a falsifiable consequence
    empirical_without_consequence: list[str] = [
        str(a.id)
        for a in graph.assumptions.values()
        if a.type == AssumptionType.EMPIRICAL
        and not a.falsifiable_consequence
        and a.status != AssumptionStatus.FALSIFIED
        and a.status != AssumptionStatus.RETIRED
    ]

    return GraphMetrics(
        hypothesis_count=hypothesis_count,
        assumption_count=assumption_count,
        analysis_count=analysis_count,
        objective_count=objective_count,
        discovery_count=discovery_count,
        dead_end_count=dead_end_count,
        parameter_count=parameter_count,
        independence_group_count=independence_group_count,
        pairwise_separation_count=pairwise_separation_count,
        prediction_metrics=pred_metrics,
        uncovered_quantitative_hypotheses=uncovered_quantitative,
        empirical_assumptions_without_consequence=empirical_without_consequence,
    )


def tier_a_evidence_summary(graph: EpistemicGraphPort) -> dict[str, object]:
    """Summarize Tier-A prediction evidence, flagging correlated groups.

    Identifies which Tier-A predictions share independence groups and
    flags groups where all confirmed predictions share a single group
    (i.e. no genuinely independent confirmation exists).

    Args:
        graph: The epistemic graph to analyze.

    Returns:
        dict[str, object]: Keys are independence group IDs (or
        ``"ungrouped"`` for Tier-A predictions with no group). Each
        value is a dict with ``predictions`` (list of IDs) and
        ``all_correlated`` (bool, True when every prediction in the
        group shares the same group and no other confirmation exists).
    """
    tier_a = [
        pred
        for pred in graph.predictions.values()
        if pred.tier == ConfidenceTier.FULLY_SPECIFIED
    ]

    groups: dict[str, list[str]] = {}
    for pred in tier_a:
        key = str(pred.independence_group) if pred.independence_group is not None else "ungrouped"
        groups.setdefault(key, []).append(str(pred.id))

    result: dict[str, object] = {}
    for group_key, pred_ids in groups.items():
        # A group is flagged as all_correlated when every Tier-A prediction
        # in the graph that has been confirmed sits in a single group —
        # meaning there is no independently-confirmed Tier-A prediction.
        confirmed_in_group = sum(
            1
            for p in tier_a
            if str(p.id) in pred_ids and p.status == PredictionStatus.CONFIRMED
        )
        result[group_key] = {
            "predictions": pred_ids,
            "confirmed": confirmed_in_group,
            "all_correlated": group_key != "ungrouped" and len(groups) == 1,
        }

    return result


__all__ = [
    "PredictionMetrics",
    "GraphMetrics",
    "compute_metrics",
    "tier_a_evidence_summary",
]
