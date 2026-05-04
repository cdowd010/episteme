"""Tests for health, status, and metrics views (Milestone 7).

Coverage:
  run_health_check  -- HEALTHY / WARNINGS / CRITICAL, sort order
  compute_metrics   -- entity counts, prediction stats, coverage gaps
  tier_a_evidence_summary -- group bucketing, confirmed counts
  get_status        -- assembles ProjectStatus from graph + metadata
  format_status_dict -- serializes to primitive dict
"""
from __future__ import annotations

import pytest

from episteme.epistemic.graph import EpistemicGraph
from episteme.epistemic.model import (
    Assumption,
    AssumptionId,
    AssumptionType,
    Hypothesis,
    HypothesisId,
    HypothesisType,
    IndependenceGroup,
    Prediction,
    PredictionId,
    PredictionStatus,
)
from episteme.epistemic.types import (
    AssumptionStatus,
    ConfidenceTier,
    EvidenceKind,
    HypothesisCategory,
    IndependenceGroupId,
    MeasurementRegime,
    Severity,
)
from episteme.controlplane.validate import DomainValidator
from episteme.views.health import HealthReport, run_health_check
from episteme.views.metrics import GraphMetrics, compute_metrics, tier_a_evidence_summary
from episteme.views.status import ProjectStatus, format_status_dict, get_status


# ── Helpers ───────────────────────────────────────────────────────────────


def _clean_graph() -> EpistemicGraph:
    """Minimal valid graph that passes all domain invariants."""
    return EpistemicGraph()


def _graph_with_warning() -> EpistemicGraph:
    """Graph that produces a WARNING finding (EMPIRICAL assumption without consequence)."""
    g = EpistemicGraph()
    g = g.register_assumption(
        Assumption(
            id=AssumptionId("A-W"),
            statement="Empirical assumption without consequence",
            type=AssumptionType.EMPIRICAL,
        )
    )
    return g


def _graph_with_critical() -> EpistemicGraph:
    """Graph that produces a CRITICAL finding.

    CONFIRMED + MEASURED + no observed value violates a domain invariant
    (checked by validate_tier_constraints) but is legal to register.
    """
    g = EpistemicGraph()
    g = g.register_prediction(
        Prediction(
            id=PredictionId("P-BAD"),
            observable="x",
            predicted=1.0,
            tier=ConfidenceTier.FULLY_SPECIFIED,
            status=PredictionStatus.CONFIRMED,
            measurement_regime=MeasurementRegime.MEASURED,
            # observed intentionally omitted — triggers CRITICAL invariant
        )
    )
    return g


# ── run_health_check ──────────────────────────────────────────────────────


class TestRunHealthCheck:
    def test_healthy_on_clean_graph(self):
        graph = _clean_graph()
        validator = DomainValidator()
        report = run_health_check(graph, validator)
        assert report.overall == "HEALTHY"
        assert report.findings == []
        assert report.critical_count == 0
        assert report.warning_count == 0

    def test_warnings_overall_when_only_warnings(self):
        graph = _graph_with_warning()
        validator = DomainValidator()
        report = run_health_check(graph, validator)
        assert report.overall == "WARNINGS"
        assert report.critical_count == 0
        assert report.warning_count > 0

    def test_critical_overall_when_critical_present(self):
        graph = _graph_with_critical()
        validator = DomainValidator()
        report = run_health_check(graph, validator)
        assert report.overall == "CRITICAL"
        assert report.critical_count > 0

    def test_findings_sorted_critical_first(self):
        graph = _graph_with_critical()
        validator = DomainValidator()
        report = run_health_check(graph, validator)
        severities = [f.severity for f in report.findings]
        # Critical findings must precede Warning/Info
        saw_non_critical = False
        for s in severities:
            if s != Severity.CRITICAL:
                saw_non_critical = True
            if saw_non_critical:
                assert s != Severity.CRITICAL

    def test_returns_health_report_type(self):
        report = run_health_check(_clean_graph(), DomainValidator())
        assert isinstance(report, HealthReport)


# ── compute_metrics ───────────────────────────────────────────────────────


class TestComputeMetrics:
    def test_empty_graph_all_zeros(self):
        m = compute_metrics(EpistemicGraph())
        assert m.hypothesis_count == 0
        assert m.assumption_count == 0
        assert m.prediction_metrics.total == 0

    def test_entity_counts(self, base_graph):
        m = compute_metrics(base_graph)
        assert m.hypothesis_count == 1
        assert m.assumption_count == 1
        assert m.objective_count == 1
        assert m.prediction_metrics.total == 1

    def test_prediction_by_status(self, base_graph):
        m = compute_metrics(base_graph)
        assert m.prediction_metrics.by_status.get("pending", 0) == 1

    def test_prediction_by_tier(self, base_graph):
        m = compute_metrics(base_graph)
        assert m.prediction_metrics.by_tier.get("fully_specified", 0) == 1

    def test_tier_a_counts(self, base_graph):
        m = compute_metrics(base_graph)
        assert m.prediction_metrics.tier_a_total == 1
        assert m.prediction_metrics.tier_a_confirmed == 0

    def test_tier_a_confirmed_increments(self):
        g = EpistemicGraph()
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-C"),
                observable="x",
                predicted=1.0,
                tier=ConfidenceTier.FULLY_SPECIFIED,
                status=PredictionStatus.CONFIRMED,
            )
        )
        m = compute_metrics(g)
        assert m.prediction_metrics.tier_a_confirmed == 1

    def test_stressed_predictions_listed(self):
        g = EpistemicGraph()
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-S"),
                observable="x",
                predicted=1.0,
                status=PredictionStatus.STRESSED,
            )
        )
        m = compute_metrics(g)
        assert "P-S" in m.prediction_metrics.stressed

    def test_uncovered_quantitative_hypothesis_flagged(self):
        g = EpistemicGraph()
        g = g.register_hypothesis(
            Hypothesis(
                id=HypothesisId("C-Q"),
                statement="Quant hyp",
                type=HypothesisType.FOUNDATIONAL,
                category=HypothesisCategory.QUANTITATIVE,
            )
        )
        m = compute_metrics(g)
        assert "C-Q" in m.uncovered_quantitative_hypotheses

    def test_covered_quantitative_hypothesis_not_flagged(self):
        g = EpistemicGraph()
        g = g.register_hypothesis(
            Hypothesis(
                id=HypothesisId("C-Q"),
                statement="Quant hyp",
                type=HypothesisType.FOUNDATIONAL,
                category=HypothesisCategory.QUANTITATIVE,
            )
        )
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-1"),
                observable="x",
                predicted=1.0,
                hypothesis_ids={HypothesisId("C-Q")},
            )
        )
        m = compute_metrics(g)
        assert "C-Q" not in m.uncovered_quantitative_hypotheses

    def test_empirical_assumption_without_consequence_flagged(self):
        g = EpistemicGraph()
        g = g.register_assumption(
            Assumption(
                id=AssumptionId("A-E"),
                statement="Empirical with no consequence",
                type=AssumptionType.EMPIRICAL,
                # falsifiable_consequence intentionally absent
            )
        )
        m = compute_metrics(g)
        assert "A-E" in m.empirical_assumptions_without_consequence

    def test_empirical_assumption_with_consequence_not_flagged(self):
        g = EpistemicGraph()
        g = g.register_assumption(
            Assumption(
                id=AssumptionId("A-E2"),
                statement="Empirical with consequence",
                type=AssumptionType.EMPIRICAL,
                falsifiable_consequence="observation X would falsify",
            )
        )
        m = compute_metrics(g)
        assert "A-E2" not in m.empirical_assumptions_without_consequence

    def test_falsified_empirical_assumption_not_flagged(self):
        """Falsified assumptions should not be flagged for missing consequence."""
        g = EpistemicGraph()
        g = g.register_assumption(
            Assumption(
                id=AssumptionId("A-F"),
                statement="Falsified empirical",
                type=AssumptionType.EMPIRICAL,
                status=AssumptionStatus.FALSIFIED,
            )
        )
        m = compute_metrics(g)
        assert "A-F" not in m.empirical_assumptions_without_consequence

    def test_returns_graph_metrics_type(self):
        assert isinstance(compute_metrics(EpistemicGraph()), GraphMetrics)


# ── tier_a_evidence_summary ───────────────────────────────────────────────


class TestTierAEvidenceSummary:
    def test_empty_graph_returns_empty_dict(self):
        result = tier_a_evidence_summary(EpistemicGraph())
        assert result == {}

    def test_ungrouped_prediction_keyed_ungrouped(self):
        g = EpistemicGraph()
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-1"),
                observable="x",
                predicted=1.0,
                tier=ConfidenceTier.FULLY_SPECIFIED,
            )
        )
        result = tier_a_evidence_summary(g)
        assert "ungrouped" in result
        assert "P-1" in result["ungrouped"]["predictions"]

    def test_non_tier_a_prediction_excluded(self):
        g = EpistemicGraph()
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-FIT"),
                observable="x",
                predicted=1.0,
                tier=ConfidenceTier.FIT_CHECK,
                evidence_kind=EvidenceKind.FIT_CONSISTENCY,
            )
        )
        result = tier_a_evidence_summary(g)
        assert result == {}

    def test_confirmed_count_correct(self):
        g = EpistemicGraph()
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-C"),
                observable="x",
                predicted=1.0,
                tier=ConfidenceTier.FULLY_SPECIFIED,
                status=PredictionStatus.CONFIRMED,
            )
        )
        result = tier_a_evidence_summary(g)
        assert result["ungrouped"]["confirmed"] == 1

    def test_grouped_predictions_keyed_by_group(self):
        g = EpistemicGraph()
        g = g.register_independence_group(
            IndependenceGroup(id=IndependenceGroupId("IG-1"), label="Group A")
        )
        g = g.register_prediction(
            Prediction(
                id=PredictionId("P-G"),
                observable="x",
                predicted=1.0,
                tier=ConfidenceTier.FULLY_SPECIFIED,
                independence_group=IndependenceGroupId("IG-1"),
            )
        )
        result = tier_a_evidence_summary(g)
        assert "IG-1" in result
        assert "P-G" in result["IG-1"]["predictions"]


# ── get_status ────────────────────────────────────────────────────────────


class TestGetStatus:
    def test_returns_project_status_type(self, base_graph):
        status = get_status(base_graph)
        assert isinstance(status, ProjectStatus)

    def test_metrics_populated(self, base_graph):
        status = get_status(base_graph)
        assert isinstance(status.metrics, GraphMetrics)
        assert status.metrics.hypothesis_count == 1

    def test_metadata_passed_through(self, base_graph):
        status = get_status(
            base_graph,
            project_name="Test Project",
            location="Lab A",
            health_summary="HEALTHY",
            governance_session=3,
            extra={"note": "test"},
        )
        assert status.project_name == "Test Project"
        assert status.location == "Lab A"
        assert status.health_summary == "HEALTHY"
        assert status.governance_session == 3
        assert status.extra == {"note": "test"}

    def test_extra_defaults_to_empty_dict(self, base_graph):
        status = get_status(base_graph)
        assert status.extra == {}


# ── format_status_dict ────────────────────────────────────────────────────


class TestFormatStatusDict:
    def test_returns_dict(self, base_graph):
        status = get_status(base_graph, project_name="P", location="L", health_summary="HEALTHY")
        d = format_status_dict(status)
        assert isinstance(d, dict)

    def test_top_level_keys(self, base_graph):
        status = get_status(base_graph, project_name="P", health_summary="HEALTHY")
        d = format_status_dict(status)
        assert "project_name" in d
        assert "metrics" in d
        assert "health_summary" in d

    def test_metrics_nested_keys(self, base_graph):
        status = get_status(base_graph)
        d = format_status_dict(status)
        m = d["metrics"]
        assert "hypothesis_count" in m
        assert "predictions" in m
        assert "by_status" in m["predictions"]
        assert "tier_a_confirmed" in m["predictions"]

    def test_entity_counts_correct(self, base_graph):
        status = get_status(base_graph)
        d = format_status_dict(status)
        assert d["metrics"]["hypothesis_count"] == 1
        assert d["metrics"]["assumption_count"] == 1
        assert d["metrics"]["predictions"]["total"] == 1
