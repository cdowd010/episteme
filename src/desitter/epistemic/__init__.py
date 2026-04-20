"""Epistemic domain kernel.

Models research truth as a directed graph of typed nodes (claims, 
assumptions, predictions, analyses, …) and typed edges with
bidirectional invariants.

Dependency rule: zero external imports. Only stdlib. This layer must be
fast, portable, and free of supply-chain risk.

Public surface:
  from desitter.epistemic.types import ClaimId, Finding, Severity, …
  from desitter.epistemic.model import Claim, Assumption, Prediction, …
  from desitter.epistemic.web import EpistemicWeb
  from desitter.epistemic.invariants import validate_all
  from desitter.epistemic.ports import WebRepository, WebRenderer, …
"""

from .model import (
    Analysis,
    Assumption,
    Claim,
    DeadEnd,
    Discovery,
    IndependenceGroup,
    Observation,
    PairwiseSeparation,
    Parameter,
    Prediction,
    Theory,
)
from .types import (
    AnalysisId,
    AssumptionId,
    AssumptionType,
    ClaimCategory,
    ClaimId,
    ClaimStatus,
    ClaimType,
    ConfidenceTier,
    Criticality,
    DeadEndId,
    DeadEndStatus,
    DiscoveryId,
    DiscoveryStatus,
    EvidenceKind,
    Finding,
    IndependenceGroupId,
    MeasurementRegime,
    ObservationId,
    ObservationStatus,
    ParameterId,
    PairwiseSeparationId,
    PredictionId,
    PredictionStatus,
    Severity,
    TheoryId,
    TheoryStatus,
)
from .errors import (
    BrokenReferenceError,
    CycleError,
    DuplicateIdError,
    EpistemicError,
    InvariantViolation,
)
from .web import EpistemicWeb

__all__ = [
    # types
    "ClaimId", "AssumptionId", "PredictionId", "TheoryId", "DiscoveryId",
    "AnalysisId", "IndependenceGroupId", "ParameterId", "DeadEndId",
    "PairwiseSeparationId", "ObservationId",
    "Severity", "Finding", "ConfidenceTier", "EvidenceKind", "MeasurementRegime",
    "PredictionStatus", "DeadEndStatus", "ClaimStatus", "TheoryStatus", "DiscoveryStatus",
    "ObservationStatus", "Criticality",
    "AssumptionType", "ClaimType", "ClaimCategory",
    # model
    "Claim", "Assumption", "Prediction", "Theory", "IndependenceGroup",
    "PairwiseSeparation", "Analysis", "Discovery", "DeadEnd", "Parameter",
    "Observation",
    # web
    "EpistemicWeb", "EpistemicError", "DuplicateIdError", "BrokenReferenceError",
    "CycleError", "InvariantViolation",
]
