"""Client helper declarations for core hypothesis resources."""
from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping

from ._types import ClientResult
from ..epistemic.model import Analysis, Assumption, Claim, Prediction
from ..epistemic.types import (
    AssumptionType,
    ClaimCategory,
    ClaimStatus,
    ClaimType,
    ConfidenceTier,
    EvidenceKind,
    MeasurementRegime,
    PredictionStatus,
)


class _DeSitterClientHypothesisHelpers:
    """Typed helpers for claims, assumptions, predictions, and analyses."""

    def register_claim(
        self,
        id: str,
        statement: str,
        type: ClaimType | str,
        scope: str,
        falsifiability: str,
        *,
        dry_run: bool = False,
        status: ClaimStatus | str | None = None,
        category: ClaimCategory | str | None = None,
        assumptions: Iterable[str] | None = None,
        depends_on: Iterable[str] | None = None,
        analyses: Iterable[str] | None = None,
        parameter_constraints: Mapping[str, str] | None = None,
        source: str | None = None,
    ) -> ClientResult[Claim]:
        """Register a claim via the generic client API."""
        raise NotImplementedError

    def register_assumption(
        self,
        id: str,
        statement: str,
        type: AssumptionType | str,
        scope: str,
        *,
        dry_run: bool = False,
        depends_on: Iterable[str] | None = None,
        falsifiable_consequence: str | None = None,
        source: str | None = None,
        notes: str | None = None,
    ) -> ClientResult[Assumption]:
        """Register an assumption via the generic client API."""
        raise NotImplementedError

    def register_prediction(
        self,
        id: str,
        observable: str,
        tier: ConfidenceTier | str,
        status: PredictionStatus | str,
        evidence_kind: EvidenceKind | str,
        measurement_regime: MeasurementRegime | str,
        predicted: object,
        *,
        dry_run: bool = False,
        specification: str | None = None,
        derivation: str | None = None,
        claim_ids: Iterable[str] | None = None,
        tests_assumptions: Iterable[str] | None = None,
        analysis: str | None = None,
        independence_group: str | None = None,
        correlation_tags: Iterable[str] | None = None,
        observed: object | None = None,
        observed_bound: object | None = None,
        free_params: int | None = None,
        conditional_on: Iterable[str] | None = None,
        falsifier: str | None = None,
        benchmark_source: str | None = None,
        source: str | None = None,
        notes: str | None = None,
    ) -> ClientResult[Prediction]:
        """Register a prediction via the generic client API."""
        raise NotImplementedError

    def register_analysis(
        self,
        id: str,
        *,
        dry_run: bool = False,
        command: str | None = None,
        path: str | None = None,
        uses_parameters: Iterable[str] | None = None,
        notes: str | None = None,
        last_result: object | None = None,
        last_result_sha: str | None = None,
        last_result_date: date | str | None = None,
    ) -> ClientResult[Analysis]:
        """Register an analysis via the generic client API."""
        raise NotImplementedError

    def get_claim(self, identifier: str) -> ClientResult[Claim]:
        """Retrieve a claim by ID."""
        raise NotImplementedError

    def get_assumption(self, identifier: str) -> ClientResult[Assumption]:
        """Retrieve an assumption by ID."""
        raise NotImplementedError

    def get_prediction(self, identifier: str) -> ClientResult[Prediction]:
        """Retrieve a prediction by ID."""
        raise NotImplementedError

    def get_analysis(self, identifier: str) -> ClientResult[Analysis]:
        """Retrieve an analysis by ID."""
        raise NotImplementedError

    def list_claims(self, **filters: object) -> ClientResult[list[Claim]]:
        """List all claims, optionally filtered."""
        raise NotImplementedError

    def list_assumptions(self, **filters: object) -> ClientResult[list[Assumption]]:
        """List all assumptions, optionally filtered."""
        raise NotImplementedError

    def list_predictions(self, **filters: object) -> ClientResult[list[Prediction]]:
        """List all predictions, optionally filtered."""
        raise NotImplementedError

    def list_analyses(self, **filters: object) -> ClientResult[list[Analysis]]:
        """List all analyses, optionally filtered."""
        raise NotImplementedError

    def transition_claim(
        self,
        identifier: str,
        new_status: ClaimStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Claim]:
        """Transition a claim to a new status."""
        raise NotImplementedError

    def transition_prediction(
        self,
        identifier: str,
        new_status: PredictionStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Prediction]:
        """Transition a prediction to a new status."""
        raise NotImplementedError


__all__ = ["_DeSitterClientHypothesisHelpers"]
