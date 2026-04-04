"""Value types and type aliases for the epistemic domain.

No external dependencies. No I/O. Pure data definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType


# ── Typed identifiers ─────────────────────────────────────────────
# NewType gives nominal typing: ClaimId and AnalysisId are both str at
# runtime, but the type checker treats them as distinct types.

ClaimId = NewType("ClaimId", str)
AssumptionId = NewType("AssumptionId", str)
PredictionId = NewType("PredictionId", str)
TheoryId = NewType("TheoryId", str)
DiscoveryId = NewType("DiscoveryId", str)
AnalysisId = NewType("AnalysisId", str)
IndependenceGroupId = NewType("IndependenceGroupId", str)
ParameterId = NewType("ParameterId", str)
ConceptId = NewType("ConceptId", str)
DeadEndId = NewType("DeadEndId", str)
PairwiseSeparationId = NewType("PairwiseSeparationId", str)



# ── Severity ──────────────────────────────────────────────────────

class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class Finding:
    """One validation result."""
    severity: Severity
    source: str
    message: str


# ── Confidence tiers ──────────────────────────────────────────────

class ConfidenceTier(Enum):
    """How strongly a prediction is constrained.

    FULLY_SPECIFIED: Zero free parameters — pure prediction from theory.
    CONDITIONAL: Valid only if explicitly stated assumptions hold.
    FIT_CHECK: Agreement unsurprising — model was fit to this data, or data
        predates the model (retrodiction). Use evidence_kind to distinguish
        fit vs. retrodiction sub-cases. Cannot be NOVEL_PREDICTION.
    """
    FULLY_SPECIFIED = "fully_specified"
    CONDITIONAL = "conditional"
    FIT_CHECK = "fit_check"


# ── Evidence classification ───────────────────────────────────────

class EvidenceKind(Enum):
    NOVEL_PREDICTION = "novel_prediction"
    RETRODICTION = "retrodiction"
    FIT_CONSISTENCY = "fit_consistency"


class MeasurementRegime(Enum):
    MEASURED = "measured"
    BOUND_ONLY = "bound_only"
    UNMEASURED = "unmeasured"


class PredictionStatus(Enum):
    CONFIRMED = "CONFIRMED"
    STRESSED = "STRESSED"
    REFUTED = "REFUTED"
    PENDING = "PENDING"
    NOT_YET_TESTABLE = "NOT_YET_TESTABLE"


class DeadEndStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class TheoryStatus(Enum):
    ACTIVE = "active"         # currently under investigation
    REFINED = "refined"       # initial formulation has been updated
    ABANDONED = "abandoned"   # no longer pursued
    SUPERSEDED = "superseded" # replaced by a better framework


class DiscoveryStatus(Enum):
    NEW = "new"                    # recently found, not yet integrated into the web
    INTEGRATED = "integrated"      # incorporated as claims or predictions
    ARCHIVED = "archived"          # historical record only


class ClaimStatus(Enum):
    ACTIVE = "active"        # normal, in-use
    REVISED = "revised"      # statement updated; downstream may need re-evaluation
    RETRACTED = "retracted"  # found to be wrong; predictions citing it are broken


class ClaimType(Enum):
    FOUNDATIONAL = "foundational"  # axiomatic starting point; must not depend on other claims
    DERIVED = "derived"            # follows from other claims via depends_on


class ClaimCategory(Enum):
    NUMERICAL = "numerical"    # a quantitative assertion; should have linked analyses
    QUALITATIVE = "qualitative"


class AssumptionType(Enum):
    EMPIRICAL = "E"        # can in principle be falsified by observation
    METHODOLOGICAL = "M"   # a choice of method or modelling convention
