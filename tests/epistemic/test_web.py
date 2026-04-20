"""Tests for EpistemicWeb mutation operations."""
from __future__ import annotations

from desitter.epistemic.model import (
    ClaimId,
    ObservationId,
    PredictionId,
    TheoryId,
)


def test_theory_claim_bidirectional_links(base_web):
    """Registering a Claim with theories= auto-populates Theory.motivates_claims."""
    assert ClaimId("C-001") in base_web.theories[TheoryId("T-001")].motivates_claims
    assert TheoryId("T-001") in base_web.claims[ClaimId("C-001")].theories


def test_prediction_stress_criteria_stored(base_web):
    """stress_criteria field is persisted on the Prediction."""
    p = base_web.predictions[PredictionId("P-001")]
    assert p.stress_criteria == "Yield increase <10% but >5% would be stressed"


def test_standalone_observation(base_web):
    """Observations can exist without linking to any prediction."""
    obs = base_web.observations[ObservationId("OBS-001")]
    assert obs.predictions == set()


def test_observation_prediction_bidirectional(base_web):
    """Registering an observation with predictions= auto-populates Prediction.observations."""
    assert ObservationId("OBS-002") in base_web.predictions[PredictionId("P-001")].observations


def test_theory_removal_scrubs_claim_theories(base_web):
    """Removing a Theory clears its id from all Claim.theories sets."""
    web = base_web.remove_prediction(PredictionId("P-001"))
    web = web.remove_claim(ClaimId("C-001"))
    web = web.remove_theory(TheoryId("T-001"))
    assert TheoryId("T-001") not in web.theories


def test_observation_removal_cleans_prediction_backlink(base_web):
    """Removing an Observation tears down its Prediction.observations backlink."""
    web = base_web.remove_observation(ObservationId("OBS-002"))
    assert ObservationId("OBS-002") not in web.predictions[PredictionId("P-001")].observations
