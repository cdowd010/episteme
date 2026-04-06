"""Client helper declarations for structural support resources."""
from __future__ import annotations

from typing import Iterable

from ._types import ClientResult
from ..epistemic.model import IndependenceGroup, PairwiseSeparation, Parameter
from ..epistemic.types import MeasurementRegime


class _DeSitterClientStructureHelpers:
    """Typed helpers for parameters and evidence-structure resources."""

    def register_parameter(
        self,
        id: str,
        name: str,
        value: object,
        *,
        dry_run: bool = False,
        unit: str | None = None,
        uncertainty: object | None = None,
        source: str | None = None,
        notes: str | None = None,
    ) -> ClientResult[Parameter]:
        """Register a parameter via the generic client API."""
        raise NotImplementedError

    def register_independence_group(
        self,
        id: str,
        label: str,
        *,
        dry_run: bool = False,
        claim_lineage: Iterable[str] | None = None,
        assumption_lineage: Iterable[str] | None = None,
        measurement_regime: MeasurementRegime | str | None = None,
        notes: str | None = None,
    ) -> ClientResult[IndependenceGroup]:
        """Register an independence group via the generic client API."""
        raise NotImplementedError

    def register_pairwise_separation(
        self,
        id: str,
        group_a: str,
        group_b: str,
        basis: str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[PairwiseSeparation]:
        """Register a pairwise separation via the generic client API."""
        raise NotImplementedError

    def get_parameter(self, identifier: str) -> ClientResult[Parameter]:
        """Retrieve a parameter by ID."""
        raise NotImplementedError

    def get_independence_group(self, identifier: str) -> ClientResult[IndependenceGroup]:
        """Retrieve an independence group by ID."""
        raise NotImplementedError

    def get_pairwise_separation(self, identifier: str) -> ClientResult[PairwiseSeparation]:
        """Retrieve a pairwise separation by ID."""
        raise NotImplementedError

    def list_parameters(self, **filters: object) -> ClientResult[list[Parameter]]:
        """List all parameters, optionally filtered."""
        raise NotImplementedError

    def list_independence_groups(self, **filters: object) -> ClientResult[list[IndependenceGroup]]:
        """List all independence groups, optionally filtered."""
        raise NotImplementedError

    def list_pairwise_separations(self, **filters: object) -> ClientResult[list[PairwiseSeparation]]:
        """List all pairwise separations, optionally filtered."""
        raise NotImplementedError


__all__ = ["_DeSitterClientStructureHelpers"]
