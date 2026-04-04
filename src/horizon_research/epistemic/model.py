"""Core epistemic entities.

Relationships are ID references, not object references. To traverse
the graph, go through the EpistemicWeb.

Native Python collections throughout: set, list, dict. The web is
the encapsulation boundary, not the type system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .types import (
    AssumptionId,
    ClaimId,
    ConceptId,
    ConfidenceTier,
    DiscoveryId,
    EvidenceKind,
    FailureId,
    FailureStatus,
    HypothesisId,
    IndependenceGroupId,
    MeasurementRegime,
    ParameterId,
    PredictionId,
    PredictionStatus,
    ScriptId,
)


@dataclass
class Claim:
    """An atomic, falsifiable assertion.

    depends_on forms a DAG. assumptions and verified_by have bidirectional
    links maintained by the EpistemicWeb.
    """
    id: ClaimId
    statement: str
    type: str                                    # "foundational" | "derived"
    scope: str                                   # "global", "domain-specific"
    falsifiability: str
    category: str = "qualitative"                # "numerical" | "qualitative"
    assumptions: set[AssumptionId] = field(default_factory=set)
    depends_on: set[ClaimId] = field(default_factory=set)
    verified_by: set[ScriptId] = field(default_factory=set)


@dataclass
class Assumption:
    """A premise taken as given."""
    id: AssumptionId
    statement: str
    type: str                                    # "E" (empirical), "M" (methodological)
    scope: str
    used_in_claims: set[ClaimId] = field(default_factory=set)
    falsifiable_consequence: str | None = None
    notes: str | None = None


@dataclass
class Prediction:
    """A testable consequence of one or more claims."""
    id: PredictionId
    observable: str
    tier: ConfidenceTier
    status: PredictionStatus
    evidence_kind: EvidenceKind
    measurement_regime: MeasurementRegime
    predicted: Any                               # the predicted value/outcome
    specification: str | None = None             # human-readable formula/relationship being tested
    claim_id: ClaimId | None = None
    script: ScriptId | None = None
    independence_group: IndependenceGroupId | None = None
    correlation_tags: set[str] = field(default_factory=set)
    observed: Any = None
    observed_bound: Any = None
    free_params: int = 0
    conditional_on: str | None = None
    falsifier: str | None = None
    benchmark_source: str | None = None
    notes: str | None = None


@dataclass
class IndependenceGroup:
    """Predictions sharing a common derivation chain.

    member_predictions is bidirectional with Prediction.independence_group.
    """
    id: IndependenceGroupId
    label: str
    claim_lineage: set[ClaimId] = field(default_factory=set)
    assumption_lineage: set[AssumptionId] = field(default_factory=set)
    member_predictions: set[PredictionId] = field(default_factory=set)
    measurement_regime: str | None = None
    notes: str | None = None


@dataclass
class PairwiseSeparation:
    """Documents why two independence groups are genuinely separate."""
    group_a: IndependenceGroupId
    group_b: IndependenceGroupId
    basis: str


@dataclass
class Script:
    """A verification program that checks whether predictions hold."""
    id: ScriptId
    command: str
    claims_covered: set[ClaimId] = field(default_factory=set)
    machine_readable_output: bool = False
    requires_network: bool = False
    requires_sandbox: bool = True
    notes: str | None = None


@dataclass
class Hypothesis:
    """A higher-level theoretical path being explored."""
    id: HypothesisId
    title: str
    status: str
    summary: str | None = None
    related_claims: set[ClaimId] = field(default_factory=set)
    related_predictions: set[PredictionId] = field(default_factory=set)


@dataclass
class Discovery:
    """A significant finding during research."""
    id: DiscoveryId
    title: str
    date: date
    summary: str
    impact: str
    status: str
    references: list[str] = field(default_factory=list)


@dataclass
class Failure:
    """A known problem or dead end."""
    id: FailureId
    title: str
    description: str
    status: FailureStatus
    session_opened: int
    session_resolved: int | None = None
    related_predictions: set[PredictionId] = field(default_factory=set)
    related_claims: set[ClaimId] = field(default_factory=set)


@dataclass
class Concept:
    """A defined term in the project vocabulary."""
    id: ConceptId
    sort_order: int
    term: str
    definition: str
    aliases: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


@dataclass
class Parameter:
    """A physical or mathematical constant referenced by verification scripts.

    Parameters live in project/data/parameters.json and are read by
    scripts at runtime. The sandbox executor makes them available as
    structured input so scripts don't hard-code constants.
    """
    id: ParameterId
    name: str
    value: Any                          # numeric, string, or structured
    unit: str | None = None             # SI or domain unit, human-readable
    uncertainty: Any = None             # absolute uncertainty, same type as value
    source: str | None = None           # citation or derivation note
    notes: str | None = None
