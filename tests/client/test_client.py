"""Tests for the M6 client surface.

Coverage:
  connect()                — graph, repo, and mutual-exclusion branches
  _EpistemeClientCore      — save, context manager, validate
  generic verbs            — register, get, list, set, transition, query
  typed helpers            — hypothesis, assumption, prediction, analysis,
                             observation (hypothesis family)
  typed helpers            — parameter, independence_group, pairwise_separation
                             (structure family)
  typed helpers            — objective, discovery, dead_end (registry family)
  error paths              — EpistemicError surfaced as ClientResult error
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from episteme.client._client import EpistemeClient, connect
from episteme.client._types import ClientResult
from episteme.controlplane.factory import build_gateway
from episteme.controlplane.gateway import GatewayResult
from episteme.epistemic.graph import EpistemicGraph
from episteme.epistemic.model import (
    Assumption,
    AssumptionId,
    AssumptionType,
    DeadEnd,
    DeadEndId,
    Discovery,
    DiscoveryId,
    Hypothesis,
    HypothesisId,
    HypothesisType,
    IndependenceGroup,
    IndependenceGroupId,
    Objective,
    ObjectiveId,
    ObjectiveKind,
    ObjectiveStatus,
    Observation,
    ObservationId,
    ObservationStatus,
    PairwiseSeparation,
    PairwiseSeparationId,
    Parameter,
    ParameterId,
    Prediction,
    PredictionId,
    PredictionStatus,
)
from episteme.epistemic.types import (
    ConfidenceTier,
    Criticality,
    DeadEndStatus,
    DiscoveryStatus,
    EvidenceKind,
    HypothesisStatus,
    MeasurementRegime,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_client(graph: EpistemicGraph | None = None) -> EpistemeClient:
    """Build a test client backed by an in-memory graph (no repo)."""
    g = graph or EpistemicGraph()
    from episteme.adapters.payload_validator import SchemaPayloadValidator
    gw = build_gateway(g, payload_validator=SchemaPayloadValidator())
    return EpistemeClient(gw)


# ── connect() ─────────────────────────────────────────────────────────────────


class TestConnect:
    def test_connect_with_graph_returns_client(self):
        client = connect(graph=EpistemicGraph())
        assert isinstance(client, EpistemeClient)

    def test_connect_with_graph_has_no_repo(self):
        client = connect(graph=EpistemicGraph())
        assert client._repo is None

    def test_connect_with_repo_loads_graph(self):
        graph = EpistemicGraph()
        repo = MagicMock()
        repo.load.return_value = graph
        client = connect(repo=repo)
        repo.load.assert_called_once()
        assert isinstance(client, EpistemeClient)

    def test_connect_with_repo_sets_repo(self):
        repo = MagicMock()
        repo.load.return_value = EpistemicGraph()
        client = connect(repo=repo)
        assert client._repo is repo

    def test_connect_repo_and_graph_raises(self):
        with pytest.raises(ValueError):
            connect(repo=MagicMock(), graph=EpistemicGraph())


# ── Lifecycle ─────────────────────────────────────────────────────────────────


class TestLifecycle:
    def test_save_calls_repo(self):
        repo = MagicMock()
        repo.load.return_value = EpistemicGraph()
        client = connect(repo=repo)
        client.save()
        repo.save.assert_called_once()

    def test_save_without_repo_is_noop(self):
        client = _make_client()
        client.save()  # should not raise

    def test_context_manager_returns_self(self):
        client = _make_client()
        with client as ctx:
            assert ctx is client

    def test_context_manager_calls_save_on_exit(self):
        repo = MagicMock()
        repo.load.return_value = EpistemicGraph()
        client = connect(repo=repo)
        with client:
            pass
        repo.save.assert_called_once()

    def test_gateway_property(self):
        g = EpistemicGraph()
        client = _make_client(g)
        assert client.gateway is not None


# ── Generic verbs ─────────────────────────────────────────────────────────────


class TestGenericVerbs:
    """Round-trip tests through the real gateway using the generic API."""

    def test_register_returns_ok(self):
        client = _make_client()
        result = client.register(
            "hypothesis",
            id="H-001",
            statement="Cats prefer fish",
            type="derived",
            scope="global",
        )
        assert result.status == "ok"
        assert result.changed is True
        assert isinstance(result.data, Hypothesis)

    def test_register_duplicate_returns_error(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        result = client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        assert result.status == "error"
        assert result.data is None

    def test_get_existing_entity(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        result = client.get("hypothesis", "H-001")
        assert result.status == "ok"
        assert isinstance(result.data, Hypothesis)

    def test_get_missing_entity(self):
        client = _make_client()
        result = client.get("hypothesis", "MISSING")
        assert result.status == "error"
        assert result.data is None

    def test_list_empty(self):
        client = _make_client()
        result = client.list("hypothesis")
        assert result.status == "ok"
        assert result.data == []

    def test_list_returns_all(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s1", type="derived", scope="g")
        client.register("hypothesis", id="H-002", statement="s2", type="foundational", scope="g")
        result = client.list("hypothesis")
        assert result.status == "ok"
        assert len(result.data) == 2

    def test_set_updates_field(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="original", type="derived", scope="g")
        result = client.set("hypothesis", "H-001", statement="updated")
        assert result.status == "ok"
        assert result.data.statement == "updated"

    def test_transition_hypothesis_status(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        result = client.transition("hypothesis", "H-001", HypothesisStatus.DEFERRED)
        assert result.status == "ok"

    def test_transition_accepts_string_status(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        result = client.transition("hypothesis", "H-001", "deferred")
        assert result.status == "ok"

    def test_dry_run_does_not_mutate(self):
        client = _make_client()
        result = client.register(
            "hypothesis",
            dry_run=True,
            id="H-001",
            statement="s",
            type="derived",
            scope="g",
        )
        assert result.changed is False
        # entity should not be persisted
        get_result = client.get("hypothesis", "H-001")
        assert get_result.status == "error"

    def test_query_hypothesis_lineage(self):
        client = _make_client()
        client.register("hypothesis", id="H-001", statement="s", type="derived", scope="g")
        result = client.query("hypothesis_lineage", cid="H-001")
        assert result.status == "ok"

    def test_validate_returns_list(self):
        client = _make_client()
        findings = client.validate()
        assert isinstance(findings, list)

    def test_validate_with_extra_validator(self):
        client = _make_client()
        mock_validator = MagicMock()
        mock_validator.validate.return_value = []
        findings = client.validate(extra_validators=(mock_validator,))
        mock_validator.validate.assert_called_once()
        assert isinstance(findings, list)


# ── Hypothesis helpers ────────────────────────────────────────────────────────


class TestHypothesisHelpers:
    def test_register_hypothesis(self):
        client = _make_client()
        result = client.register_hypothesis(
            id="H-001",
            statement="Gravity is constant",
            type=HypothesisType.FOUNDATIONAL,
            scope="physics",
            refutation_criteria="Measure deviation >0.01",
        )
        assert result.status == "ok"
        assert isinstance(result.data, Hypothesis)

    def test_get_hypothesis(self):
        client = _make_client()
        client.register_hypothesis(id="H-001", statement="s", scope="g")
        result = client.get_hypothesis("H-001")
        assert result.status == "ok"
        assert result.data.id == HypothesisId("H-001")

    def test_list_hypotheses(self):
        client = _make_client()
        client.register_hypothesis(id="H-001", statement="s", scope="g")
        result = client.list_hypotheses()
        assert len(result.data) == 1

    def test_set_hypothesis(self):
        client = _make_client()
        client.register_hypothesis(id="H-001", statement="original", scope="g")
        result = client.set_hypothesis("H-001", statement="updated")
        assert result.status == "ok"
        assert result.data.statement == "updated"

    def test_transition_hypothesis(self):
        client = _make_client()
        client.register_hypothesis(id="H-001", statement="s", scope="g")
        result = client.transition_hypothesis("H-001", HypothesisStatus.DEFERRED)
        assert result.status == "ok"


# ── Assumption helpers ────────────────────────────────────────────────────────


class TestAssumptionHelpers:
    def test_register_assumption(self):
        client = _make_client()
        result = client.register_assumption(
            id="A-001",
            statement="Instrument calibrated",
            type=AssumptionType.EMPIRICAL,
            scope="lab",
            criticality=Criticality.MODERATE,
        )
        assert result.status == "ok"
        assert isinstance(result.data, Assumption)

    def test_get_assumption(self):
        client = _make_client()
        client.register_assumption(id="A-001", statement="s", type=AssumptionType.EMPIRICAL, scope="g")
        result = client.get_assumption("A-001")
        assert result.status == "ok"
        assert result.data.id == AssumptionId("A-001")

    def test_list_assumptions(self):
        client = _make_client()
        client.register_assumption(id="A-001", statement="s1", type=AssumptionType.EMPIRICAL, scope="g")
        client.register_assumption(id="A-002", statement="s2", type=AssumptionType.METHODOLOGICAL, scope="g")
        result = client.list_assumptions()
        assert len(result.data) == 2

    def test_set_assumption(self):
        client = _make_client()
        client.register_assumption(id="A-001", statement="original", type=AssumptionType.EMPIRICAL, scope="g")
        result = client.set_assumption("A-001", statement="updated")
        assert result.status == "ok"
        assert result.data.statement == "updated"


# ── Prediction helpers ────────────────────────────────────────────────────────


class TestPredictionHelpers:
    def _setup_prediction(self, client):
        client.register_hypothesis(id="H-001", statement="s", scope="g")
        return client.register_prediction(
            id="P-001",
            observable="temperature",
            tier=ConfidenceTier.FULLY_SPECIFIED,
            evidence_kind=EvidenceKind.NOVEL_PREDICTION,
            measurement_regime=MeasurementRegime.MEASURED,
            hypothesis_ids=["H-001"],
            predicted=100.0,
        )

    def test_register_prediction(self):
        client = _make_client()
        result = self._setup_prediction(client)
        assert result.status == "ok"
        assert isinstance(result.data, Prediction)

    def test_get_prediction(self):
        client = _make_client()
        self._setup_prediction(client)
        result = client.get_prediction("P-001")
        assert result.status == "ok"
        assert result.data.id == PredictionId("P-001")

    def test_list_predictions(self):
        client = _make_client()
        self._setup_prediction(client)
        result = client.list_predictions()
        assert len(result.data) == 1

    def test_transition_prediction(self):
        client = _make_client()
        self._setup_prediction(client)
        result = client.transition_prediction("P-001", PredictionStatus.SUPERSEDED)
        assert result.status == "ok"


# ── Observation helpers ───────────────────────────────────────────────────────


class TestObservationHelpers:
    def test_register_observation(self):
        client = _make_client()
        result = client.register_observation(
            id="OBS-001",
            description="Temperature reading",
            value=42.0,
            date=date(2026, 1, 1),
            status=ObservationStatus.PRELIMINARY,
        )
        assert result.status == "ok"
        assert isinstance(result.data, Observation)

    def test_get_observation(self):
        client = _make_client()
        client.register_observation(
            id="OBS-001",
            description="d",
            value=1.0,
            date=date(2026, 1, 1),
            status=ObservationStatus.PRELIMINARY,
        )
        result = client.get_observation("OBS-001")
        assert result.status == "ok"

    def test_transition_observation(self):
        client = _make_client()
        client.register_observation(
            id="OBS-001",
            description="d",
            value=1.0,
            date=date(2026, 1, 1),
            status=ObservationStatus.PRELIMINARY,
        )
        result = client.transition_observation("OBS-001", ObservationStatus.VALIDATED)
        assert result.status == "ok"


# ── Parameter helpers ─────────────────────────────────────────────────────────


class TestParameterHelpers:
    def test_register_parameter(self):
        client = _make_client()
        result = client.register_parameter(
            id="PAR-001",
            name="threshold",
            value=0.85,
            unit="dimensionless",
        )
        assert result.status == "ok"
        assert isinstance(result.data, Parameter)

    def test_get_parameter(self):
        client = _make_client()
        client.register_parameter(id="PAR-001", name="threshold", value=0.85)
        result = client.get_parameter("PAR-001")
        assert result.status == "ok"
        assert result.data.id == ParameterId("PAR-001")

    def test_list_parameters(self):
        client = _make_client()
        client.register_parameter(id="PAR-001", name="n1", value=1.0)
        client.register_parameter(id="PAR-002", name="n2", value=2.0)
        result = client.list_parameters()
        assert len(result.data) == 2

    def test_set_parameter(self):
        client = _make_client()
        client.register_parameter(id="PAR-001", name="threshold", value=0.85)
        result = client.set_parameter("PAR-001", value=0.90)
        assert result.status == "ok"
        assert result.data.value == 0.90


# ── IndependenceGroup helpers ─────────────────────────────────────────────────


class TestIndependenceGroupHelpers:
    def test_register_independence_group(self):
        client = _make_client()
        result = client.register_independence_group(
            id="IG-001",
            label="Control vs Treatment",
            measurement_regime=MeasurementRegime.MEASURED,
            notes="Randomised assignment",
        )
        assert result.status == "ok"
        assert isinstance(result.data, IndependenceGroup)

    def test_get_independence_group(self):
        client = _make_client()
        client.register_independence_group(id="IG-001", label="G1")
        result = client.get_independence_group("IG-001")
        assert result.status == "ok"
        assert result.data.id == IndependenceGroupId("IG-001")

    def test_list_independence_groups(self):
        client = _make_client()
        client.register_independence_group(id="IG-001", label="G1")
        result = client.list_independence_groups()
        assert len(result.data) == 1


# ── PairwiseSeparation helpers ────────────────────────────────────────────────


class TestPairwiseSeparationHelpers:
    def _setup(self, client):
        client.register_independence_group(id="IG-001", label="G1")
        client.register_independence_group(id="IG-002", label="G2")

    def test_register_pairwise_separation(self):
        client = _make_client()
        self._setup(client)
        result = client.register_pairwise_separation(
            id="PS-001",
            group_a="IG-001",
            group_b="IG-002",
            basis="Random assignment confirmed",
        )
        assert result.status == "ok"
        assert isinstance(result.data, PairwiseSeparation)

    def test_get_pairwise_separation(self):
        client = _make_client()
        self._setup(client)
        client.register_pairwise_separation(id="PS-001", group_a="IG-001", group_b="IG-002", basis="b")
        result = client.get_pairwise_separation("PS-001")
        assert result.status == "ok"

    def test_list_pairwise_separations(self):
        client = _make_client()
        self._setup(client)
        client.register_pairwise_separation(id="PS-001", group_a="IG-001", group_b="IG-002", basis="b")
        result = client.list_pairwise_separations()
        assert len(result.data) == 1


# ── Objective helpers ─────────────────────────────────────────────────────────


class TestObjectiveHelpers:
    def test_register_objective(self):
        client = _make_client()
        result = client.register_objective(
            id="T-001",
            title="Increase yield",
            kind=ObjectiveKind.GOAL.value,
            status=ObjectiveStatus.ACTIVE,
        )
        assert result.status == "ok"
        assert isinstance(result.data, Objective)

    def test_get_objective(self):
        client = _make_client()
        client.register_objective(id="T-001", title="t", kind="explanatory", status=ObjectiveStatus.ACTIVE)
        result = client.get_objective("T-001")
        assert result.status == "ok"
        assert result.data.id == ObjectiveId("T-001")

    def test_list_objectives(self):
        client = _make_client()
        client.register_objective(id="T-001", title="t1", kind="explanatory", status=ObjectiveStatus.ACTIVE)
        result = client.list_objectives()
        assert len(result.data) == 1

    def test_transition_objective(self):
        client = _make_client()
        client.register_objective(id="T-001", title="t", kind="explanatory", status=ObjectiveStatus.ACTIVE)
        result = client.transition_objective("T-001", ObjectiveStatus.ACHIEVED)
        assert result.status == "ok"


# ── Discovery helpers ─────────────────────────────────────────────────────────


class TestDiscoveryHelpers:
    def test_register_discovery(self):
        client = _make_client()
        result = client.register_discovery(
            id="D-001",
            title="Key finding",
            date=date(2026, 4, 1),
            summary="We found something",
            impact="Changes the field",
            status=DiscoveryStatus.NEW,
        )
        assert result.status == "ok"
        assert isinstance(result.data, Discovery)

    def test_get_discovery(self):
        client = _make_client()
        client.register_discovery(
            id="D-001",
            title="t",
            date=date(2026, 4, 1),
            summary="s",
            impact="i",
            status=DiscoveryStatus.NEW,
        )
        result = client.get_discovery("D-001")
        assert result.status == "ok"
        assert result.data.id == DiscoveryId("D-001")

    def test_transition_discovery(self):
        client = _make_client()
        client.register_discovery(
            id="D-001",
            title="t",
            date=date(2026, 4, 1),
            summary="s",
            impact="i",
            status=DiscoveryStatus.NEW,
        )
        result = client.transition_discovery("D-001", DiscoveryStatus.INTEGRATED)
        assert result.status == "ok"


# ── DeadEnd helpers ───────────────────────────────────────────────────────────


class TestDeadEndHelpers:
    def test_register_dead_end(self):
        client = _make_client()
        result = client.register_dead_end(
            id="DE-001",
            title="Failed approach",
            description="We tried X and it did not work",
            status=DeadEndStatus.ACTIVE,
        )
        assert result.status == "ok"
        assert isinstance(result.data, DeadEnd)

    def test_get_dead_end(self):
        client = _make_client()
        client.register_dead_end(id="DE-001", title="t", description="d", status=DeadEndStatus.ACTIVE)
        result = client.get_dead_end("DE-001")
        assert result.status == "ok"
        assert result.data.id == DeadEndId("DE-001")

    def test_list_dead_ends(self):
        client = _make_client()
        client.register_dead_end(id="DE-001", title="t", description="d", status=DeadEndStatus.ACTIVE)
        result = client.list_dead_ends()
        assert len(result.data) == 1

    def test_transition_dead_end(self):
        client = _make_client()
        client.register_dead_end(id="DE-001", title="t", description="d", status=DeadEndStatus.ACTIVE)
        result = client.transition_dead_end("DE-001", DeadEndStatus.RESOLVED)
        assert result.status == "ok"


# ── Error handling ────────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_epistemic_error_returns_error_result(self):
        """EpistemicError from the gateway is surfaced as a ClientResult, not raised."""
        from episteme.epistemic.errors import EpistemicError

        client = _make_client()
        with patch.object(client._gateway, "register", side_effect=EpistemicError("boom")):
            result = client.register("hypothesis", id="X", statement="s", type="DERIVED", scope="g")
        assert result.status == "error"
        assert "boom" in result.message
        assert result.data is None

    def test_unexpected_exception_returns_error_result(self):
        """Unexpected exceptions from the gateway are wrapped, not raised."""
        client = _make_client()
        with patch.object(client._gateway, "get", side_effect=RuntimeError("unexpected")):
            result = client.get("hypothesis", "H-001")
        assert result.status == "error"
        assert "unexpected" in result.message.lower() or "Unexpected" in result.message

    def test_none_payload_values_stripped(self):
        """None keyword arguments should not be forwarded to the gateway."""
        client = _make_client()
        result = client.register(
            "hypothesis",
            id="H-001",
            statement="s",
            type="derived",
            scope="g",
            source=None,
        )
        assert result.status == "ok"
