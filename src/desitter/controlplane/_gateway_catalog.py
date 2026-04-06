"""Built-in gateway metadata catalogs.

These tables centralize the built-in resource and query metadata used by
the gateway without mixing them into gateway orchestration code.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSpec:
    collection_attr: str
    register_method: str
    update_method: str
    transition_method: str | None = None


@dataclass(frozen=True)
class QuerySpec:
    method_name: str
    parameter_resources: dict[str, str]


RESOURCE_SPECS: dict[str, ResourceSpec] = {
    "claim": ResourceSpec("claims", "register_claim", "update_claim", "transition_claim"),
    "assumption": ResourceSpec("assumptions", "register_assumption", "update_assumption"),
    "prediction": ResourceSpec("predictions", "register_prediction", "update_prediction", "transition_prediction"),
    "analysis": ResourceSpec("analyses", "register_analysis", "update_analysis"),
    "theory": ResourceSpec("theories", "register_theory", "update_theory", "transition_theory"),
    "discovery": ResourceSpec("discoveries", "register_discovery", "update_discovery", "transition_discovery"),
    "dead_end": ResourceSpec("dead_ends", "register_dead_end", "update_dead_end", "transition_dead_end"),
    "parameter": ResourceSpec("parameters", "register_parameter", "update_parameter"),
    "independence_group": ResourceSpec("independence_groups", "register_independence_group", "update_independence_group"),
    "pairwise_separation": ResourceSpec("pairwise_separations", "add_pairwise_separation", "update_pairwise_separation"),
}


QUERY_SPECS: dict[str, QuerySpec] = {
    "claim_lineage": QuerySpec("claim_lineage", {"cid": "claim"}),
    "assumption_lineage": QuerySpec("assumption_lineage", {"cid": "claim"}),
    "prediction_implicit_assumptions": QuerySpec(
        "prediction_implicit_assumptions",
        {"pid": "prediction"},
    ),
    "refutation_impact": QuerySpec("refutation_impact", {"pid": "prediction"}),
    "assumption_support_status": QuerySpec(
        "assumption_support_status",
        {"aid": "assumption"},
    ),
    "predictions_depending_on_claim": QuerySpec(
        "predictions_depending_on_claim",
        {"cid": "claim"},
    ),
    "parameter_impact": QuerySpec("parameter_impact", {"pid": "parameter"}),
}


__all__ = ["QuerySpec", "RESOURCE_SPECS", "ResourceSpec", "QUERY_SPECS"]