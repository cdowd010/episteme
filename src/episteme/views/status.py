"""Project-status read model, snapshot builder, and serialization.

Computes a compact summary of an epistemic graph suitable for dashboards,
AI agent context, and MCP status responses.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..epistemic.ports import EpistemicGraphPort
from .metrics import GraphMetrics, compute_metrics


# ── Read model ───────────────────────────────────────────────────


@dataclass
class ProjectStatus:
    """High-level project status snapshot.

    Suitable for any consumer that needs a compact summary of a loaded
    epistemic graph.

    Attributes:
        project_name: Display name of the project.
        location: Optional deployment-specific location label.
        metrics: Full ``GraphMetrics`` snapshot.
        health_summary: One of ``"HEALTHY"``, ``"WARNINGS"``, or
            ``"CRITICAL"``.
        governance_session: Current governance session number if
            governance mode is enabled, otherwise ``None``.
        extra: Arbitrary additional metadata for extensibility.
    """

    project_name: str
    location: str
    metrics: GraphMetrics
    health_summary: str
    governance_session: int | None
    extra: dict[str, object] = field(default_factory=dict)


# ── Snapshot builder ─────────────────────────────────────────────


def get_status(
    graph: EpistemicGraphPort,
    *,
    project_name: str = "",
    location: str = "",
    health_summary: str = "",
    governance_session: int | None = None,
    extra: Mapping[str, object] | None = None,
) -> ProjectStatus:
    """Build a full project status snapshot.

    Computes metrics and assembles a ``ProjectStatus`` from an already-
    loaded graph plus optional caller-supplied metadata.

    Args:
        graph: The epistemic graph to snapshot.
        project_name: Optional display name supplied by the caller.
        location: Optional deployment-specific location label.
        health_summary: Optional pre-computed health summary label.
        governance_session: Optional governance session number.
        extra: Optional additional metadata.

    Returns:
        ProjectStatus: The assembled project status.
    """
    metrics = compute_metrics(graph)
    return ProjectStatus(
        project_name=project_name,
        location=location,
        metrics=metrics,
        health_summary=health_summary,
        governance_session=governance_session,
        extra=dict(extra) if extra is not None else {},
    )


# ── Serialization ────────────────────────────────────────────────


def format_status_dict(status: ProjectStatus) -> dict:
    """Serialize a ``ProjectStatus`` to a plain primitive mapping.

    Converts dataclass fields to transport-friendly primitive values.

    Args:
        status: The project status to serialize.

    Returns:
        dict: A primitive representation of the status.
    """
    m = status.metrics
    pm = m.prediction_metrics
    return {
        "project_name": status.project_name,
        "location": status.location,
        "health_summary": status.health_summary,
        "governance_session": status.governance_session,
        "metrics": {
            "hypothesis_count": m.hypothesis_count,
            "assumption_count": m.assumption_count,
            "analysis_count": m.analysis_count,
            "objective_count": m.objective_count,
            "discovery_count": m.discovery_count,
            "dead_end_count": m.dead_end_count,
            "parameter_count": m.parameter_count,
            "independence_group_count": m.independence_group_count,
            "pairwise_separation_count": m.pairwise_separation_count,
            "predictions": {
                "total": pm.total,
                "by_status": pm.by_status,
                "by_tier": pm.by_tier,
                "tier_a_confirmed": pm.tier_a_confirmed,
                "tier_a_total": pm.tier_a_total,
                "stressed": pm.stressed,
            },
            "uncovered_quantitative_hypotheses": m.uncovered_quantitative_hypotheses,
            "empirical_assumptions_without_consequence": m.empirical_assumptions_without_consequence,
        },
        "extra": status.extra,
    }


__all__ = ["ProjectStatus", "format_status_dict", "get_status"]
