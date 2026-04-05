"""Repository metrics and correlation-aware tier-A evidence summaries.

Computes aggregate statistics over the epistemic web for use by the
status service and health checks.

All functions are pure: (EpistemicWeb) -> result. No I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.types import ConfidenceTier, PredictionStatus
from ..epistemic.web import EpistemicWeb


@dataclass
class PredictionMetrics:
    """Aggregate statistics for predictions."""
    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_tier: dict[str, int] = field(default_factory=dict)
    tier_a_confirmed: int = 0
    tier_a_total: int = 0
    stressed: list[str] = field(default_factory=list)


@dataclass
class WebMetrics:
    """Full metrics snapshot of an EpistemicWeb."""
    claim_count: int = 0
    assumption_count: int = 0
    analysis_count: int = 0
    theory_count: int = 0
    discovery_count: int = 0
    dead_end_count: int = 0
    parameter_count: int = 0
    independence_group_count: int = 0
    pairwise_separation_count: int = 0
    prediction_metrics: PredictionMetrics = field(default_factory=PredictionMetrics)
    uncovered_numerical_claims: list[str] = field(default_factory=list)
    empirical_assumptions_without_consequence: list[str] = field(default_factory=list)


def compute_metrics(web: EpistemicWeb) -> WebMetrics:
    """Compute aggregate metrics from the epistemic web.

    Pure function — no I/O, no side effects.
    """
    raise NotImplementedError


def tier_a_evidence_summary(web: EpistemicWeb) -> dict[str, object]:
    """Summarise tier-A prediction evidence, flagging correlated groups.

    Returns a dict suitable for inclusion in status output.
    """
    raise NotImplementedError
