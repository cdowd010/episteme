"""Epistemic domain kernel.

The gravity well of the system. Models research truth as a directed graph
of typed nodes (claims, assumptions, predictions, scripts, …) and typed
edges with bidirectional invariants.

Dependency rule: zero external imports. Only stdlib. This layer must be
fast, portable, and free of supply-chain risk.

Public surface:
  from horizon_research.epistemic.types import ClaimId, Finding, Severity, …
  from horizon_research.epistemic.model import Claim, Assumption, Prediction, …
  from horizon_research.epistemic.web import EpistemicWeb
  from horizon_research.epistemic.invariants import validate_all
  from horizon_research.epistemic.ports import WebRepository, WebRenderer, …
"""

from .model import (
    Assumption,
    Claim,
    Concept,
    Discovery,
    Failure,
    Hypothesis,
    IndependenceGroup,
    PairwiseSeparation,
    Parameter,
    Prediction,
    Script,
)
from .types import (
    AssumptionId,
    ClaimId,
    ConceptId,
    ConfidenceTier,
    DiscoveryId,
    EvidenceKind,
    FailureId,
    FailureStatus,
    Finding,
    HypothesisId,
    IndependenceGroupId,
    MeasurementRegime,
    ParameterId,
    PredictionId,
    PredictionStatus,
    ScriptId,
    Severity,
)
from .web import (
    BrokenReferenceError,
    CycleError,
    DuplicateIdError,
    EpistemicError,
    EpistemicWeb,
    InvariantViolation,
)

__all__ = [
    # types
    "ClaimId", "AssumptionId", "PredictionId", "HypothesisId", "DiscoveryId",
    "ScriptId", "IndependenceGroupId", "ParameterId", "ConceptId", "FailureId",
    "Severity", "Finding", "ConfidenceTier", "EvidenceKind", "MeasurementRegime",
    "PredictionStatus", "FailureStatus",
    # model
    "Claim", "Assumption", "Prediction", "Script", "IndependenceGroup",
    "PairwiseSeparation", "Hypothesis", "Discovery", "Failure", "Concept", "Parameter",
    # web
    "EpistemicWeb", "EpistemicError", "DuplicateIdError", "BrokenReferenceError",
    "CycleError", "InvariantViolation",
]
