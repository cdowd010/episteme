"""Shared pytest fixtures for the Episteme test suite."""
from __future__ import annotations

from datetime import date

import pytest

from episteme.epistemic.web import EpistemicWeb
from episteme.epistemic.model import (
    Analysis,
    AnalysisId,
    Assumption,
    AssumptionId,
    AssumptionType,
    Claim,
    ClaimId,
    ClaimType,
    Observation,
    ObservationId,
    ObservationStatus,
    Parameter,
    ParameterId,
    Prediction,
    PredictionId,
    PredictionStatus,
    Theory,
    TheoryId,
    TheoryStatus,
)
from episteme.epistemic.types import (
    Criticality,
    ConfidenceTier,
    EvidenceKind,
    MeasurementRegime,
)


@pytest.fixture
def base_web() -> EpistemicWeb:
    """EpistemicWeb populated with the standard set of test entities.

    Entity graph:
        Theory T-001  ←→  Claim C-001  →  Assumption A-001 (LOAD_BEARING)
                              ↓
                         Prediction P-001 (stress_criteria set)
                              ↑
                         Observation OBS-002 (VALIDATED)
        Observation OBS-001 (standalone, PRELIMINARY)
        Parameter PAR-001 (last_modified=2026-04-10)
        Analysis AN-001   (last_result_date=2026-04-05)  ← stale
    """
    web = EpistemicWeb()

    web = web.register_theory(
        Theory(id=TheoryId("T-001"), title="Catalysis Theory", status=TheoryStatus.ACTIVE)
    )

    web = web.register_assumption(
        Assumption(
            id=AssumptionId("A-001"),
            statement="Detector calibrated",
            type=AssumptionType.EMPIRICAL,
            scope="global",
            criticality=Criticality.LOAD_BEARING,
        )
    )

    web = web.register_claim(
        Claim(
            id=ClaimId("C-001"),
            statement="Catalyst X increases yield",
            type=ClaimType.FOUNDATIONAL,
            scope="global",
            falsifiability="Show yield does not increase",
            assumptions={AssumptionId("A-001")},
            theories={TheoryId("T-001")},
        )
    )

    web = web.register_prediction(
        Prediction(
            id=PredictionId("P-001"),
            observable="yield",
            tier=ConfidenceTier.FULLY_SPECIFIED,
            status=PredictionStatus.PENDING,
            evidence_kind=EvidenceKind.NOVEL_PREDICTION,
            measurement_regime=MeasurementRegime.MEASURED,
            predicted=0.15,
            claim_ids={ClaimId("C-001")},
            stress_criteria="Yield increase <10% but >5% would be stressed",
        )
    )

    web = web.register_observation(
        Observation(
            id=ObservationId("OBS-001"),
            description="Initial yield measurement",
            value=12.5,
            date=date(2026, 4, 1),
            status=ObservationStatus.PRELIMINARY,
        )
    )

    web = web.register_observation(
        Observation(
            id=ObservationId("OBS-002"),
            description="Controlled experiment result",
            value=14.8,
            date=date(2026, 4, 15),
            status=ObservationStatus.VALIDATED,
            predictions={PredictionId("P-001")},
        )
    )

    web = web.register_parameter(
        Parameter(
            id=ParameterId("PAR-001"),
            name="threshold",
            value=0.85,
            last_modified=date(2026, 4, 10),
        )
    )

    web = web.register_analysis(
        Analysis(id=AnalysisId("AN-001"), uses_parameters={ParameterId("PAR-001")})
    )

    web = web.record_analysis_result(
        AnalysisId("AN-001"), result=42, result_date=date(2026, 4, 5)
    )

    return web
