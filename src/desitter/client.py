"""Python client API for deSitter.

``DeSitterClient`` owns persistence (via an optional ``WebRepository``)
and provides a typed convenience API over ``Gateway``.

- ``connect()``        → in-memory, no persistence
- ``connect(path)``    → loads from JsonRepository; saves via ``save()``
- ``with connect(path) as client:`` → saves automatically on context exit
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Iterable, Mapping, TypeVar

from .adapters.json_repository import JsonRepository
from .controlplane.factory import build_gateway
from .controlplane.gateway import Gateway, GatewayResult
from .epistemic.codec import deserialize_entity
from .epistemic.ports import WebRepository
from .epistemic.web import EpistemicWeb
from .epistemic.model import (
    Analysis,
    Assumption,
    Claim,
    DeadEnd,
    Discovery,
    IndependenceGroup,
    PairwiseSeparation,
    Parameter,
    Prediction,
    Theory,
)
from .epistemic.types import (
    AssumptionType,
    ClaimCategory,
    ClaimStatus,
    ClaimType,
    ConfidenceTier,
    DeadEndStatus,
    DiscoveryStatus,
    EvidenceKind,
    Finding,
    MeasurementRegime,
    PredictionStatus,
    TheoryStatus,
)


ResultData = TypeVar("ResultData")


@dataclass(frozen=True)
class ClientResult(Generic[ResultData]):
    """Typed wrapper over a ``GatewayResult``.

    Provides the same status/changed/message contract as ``GatewayResult``
    but with a typed ``data`` field that holds a deserialized domain entity
    (or list of entities) instead of a raw dict.

    Attributes:
        status: One of ``"ok"``, ``"dry_run"``, etc.
        changed: ``True`` if persistent state was modified.
        message: Human-readable summary.
        findings: Validation findings (may be empty).
        transaction_id: UUID4 if the operation was persisted.
        data: The deserialized result, or ``None``.
    """

    status: str
    changed: bool
    message: str
    findings: list[Finding] = field(default_factory=list)
    transaction_id: str | None = None
    data: ResultData | None = None


class DeSitterClientError(Exception):
    """Raised when the gateway returns a non-success status.

    Attributes:
        status: The gateway status string (e.g. ``"error"``, ``"BLOCKED"``).
        message: Human-readable error message.
        findings: Validation findings associated with the failure.
    """

    def __init__(
        self,
        status: str,
        message: str,
        findings: list[Finding] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.findings = findings or []


class DeSitterClient:
    """Python client that owns persistence and provides a typed gateway API.

    Provides typed convenience methods for every resource type so that
    callers can use keyword arguments and receive deserialized domain
    objects instead of raw dicts.

    All mutations flow through ``self._gateway``. Persistence is managed
    by this class via the optional ``WebRepository``.

    Prefer constructing via ``connect()`` rather than directly.

    Attributes:
        _gateway: The ``Gateway`` holding the in-memory epistemic web.
        _repo:    Optional persistence backend; ``None`` → session-only.
    """

    def __init__(
        self,
        gateway: Gateway,
        *,
        repo: WebRepository | None = None,
    ) -> None:
        """Initialize a client.

        Args:
            gateway: A fully constructed ``Gateway`` holding the in-memory web.
            repo:    Optional persistence backend. If ``None``, ``save()``
                is a no-op and the web lives only for the session.
        """
        raise NotImplementedError

    @property
    def gateway(self) -> Gateway:
        """The gateway instance backing this client."""
        raise NotImplementedError

    def save(self) -> None:
        """Persist the in-memory web through the repository.

        No-op when no ``repo`` was provided at construction time.
        Calls ``self._repo.save(self._gateway.web)`` when a repo exists.
        """
        raise NotImplementedError

    def __enter__(self) -> "DeSitterClient":
        """Enter the context manager, returning self."""
        raise NotImplementedError

    def __exit__(self, *args: object) -> None:
        """Exit the context manager; calls ``save()`` unconditionally."""
        raise NotImplementedError

    def register(
        self,
        resource: str,
        *,
        dry_run: bool = False,
        **payload: object,
    ) -> ClientResult[Any]:
        """Register a new resource using keyword arguments instead of a raw dict.

        Args:
            resource: Resource alias or canonical key.
            dry_run: If ``True``, validate without writing to disk.
            **payload: Entity attributes as keyword arguments.

        Returns:
            ClientResult: Deserialized entity in ``data`` on success.

        Raises:
            DeSitterClientError: If the gateway returns a non-success status.
        """
        raise NotImplementedError

    def get(self, resource: str, identifier: str) -> ClientResult[Any]:
        """Retrieve a single resource by ID.

        Args:
            resource: Resource alias or canonical key.
            identifier: The entity's string ID.

        Returns:
            ClientResult: Deserialized entity in ``data``.

        Raises:
            DeSitterClientError: If the entity does not exist.
        """
        raise NotImplementedError

    def list(self, resource: str, **filters: object) -> ClientResult[list[Any]]:
        """List resources, optionally filtering by keyword arguments.

        Args:
            resource: Resource alias or canonical key.
            **filters: Field-value pairs to match.

        Returns:
            ClientResult: ``data`` is a list of deserialized entities.

        Raises:
            DeSitterClientError: If the gateway returns a non-success status.
        """
        raise NotImplementedError

    def set(
        self,
        resource: str,
        identifier: str,
        *,
        dry_run: bool = False,
        **payload: object,
    ) -> ClientResult[Any]:
        """Update a resource using keyword arguments instead of a raw dict.

        Args:
            resource: Resource alias or canonical key.
            identifier: The entity's string ID.
            dry_run: If ``True``, validate without writing to disk.
            **payload: Fields to update.

        Returns:
            ClientResult: Updated deserialized entity in ``data``.

        Raises:
            DeSitterClientError: If the entity does not exist or validation fails.
        """
        raise NotImplementedError

    def transition(
        self,
        resource: str,
        identifier: str,
        new_status: str | Enum,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Any]:
        """Transition a status-bearing resource to a new state.

        Args:
            resource: Resource alias or canonical key.
            identifier: The entity's string ID.
            new_status: Target status value (string or enum member).
            dry_run: If ``True``, validate without writing to disk.

        Returns:
            ClientResult: Updated deserialized entity in ``data``.

        Raises:
            DeSitterClientError: If the transition is invalid.
        """
        raise NotImplementedError

    def query(self, query_type: str, **params: object) -> ClientResult[Any]:
        """Run a named gateway query.

        Args:
            query_type: Query name (e.g. ``"claim_lineage"``).
            **params: Query parameters.

        Returns:
            ClientResult: Query result in ``data``.

        Raises:
            DeSitterClientError: If the query fails.
        """
        raise NotImplementedError

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
        """Register a claim with typed keyword arguments.

        Convenience wrapper over ``register("claim", ...)`` that provides
        type-safe parameters and elides ``None`` values from the payload.

        Args:
            id: Unique claim identifier.
            statement: The claim statement.
            type: Claim type (qualitative, numerical, etc.).
            scope: Scope description.
            falsifiability: How the claim can be falsified.
            dry_run: If ``True``, validate without persisting.
            status: Initial status. Defaults to ``ACTIVE``.
            category: Optional category.
            assumptions: IDs of assumptions this claim relies on.
            depends_on: IDs of parent claims in the dependency graph.
            analyses: IDs of analyses supporting this claim.
            parameter_constraints: Parameter name → constraint mappings.
            source: Provenance reference.

        Returns:
            ClientResult[Claim]: The registered claim entity.
        """
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
        """Register an assumption with typed keyword arguments.

        Args:
            id: Unique assumption identifier.
            statement: The assumption statement.
            type: Assumption type (empirical, mathematical, etc.).
            scope: Scope description.
            dry_run: If ``True``, validate without persisting.
            depends_on: IDs of parent assumptions.
            falsifiable_consequence: Description of a testable consequence.
            source: Provenance reference.
            notes: Free-form notes.

        Returns:
            ClientResult[Assumption]: The registered assumption entity.
        """
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
        """Register a prediction with typed keyword arguments.

        Args:
            id: Unique prediction identifier.
            observable: The observable quantity being predicted.
            tier: Confidence tier (A, B, or C).
            status: Initial prediction status.
            evidence_kind: Kind of evidence (measurement, simulation, etc.).
            measurement_regime: Regime classification.
            predicted: The predicted numerical value or range.
            dry_run: If ``True``, validate without persisting.
            specification: Detailed prediction specification.
            derivation: Derivation steps or reference.
            claim_ids: IDs of claims this prediction tests.
            tests_assumptions: IDs of assumptions this prediction tests.
            analysis: ID of the analysis producing this prediction.
            independence_group: ID of the independence group.
            correlation_tags: Tags marking correlated measurement channels.
            observed: Observed value, if available.
            observed_bound: Observed bound, if applicable.
            free_params: Number of free parameters in the prediction.
            conditional_on: IDs of assumptions this is conditional on.
            falsifier: ID of the prediction that falsified this one.
            benchmark_source: Benchmark reference.
            source: Provenance reference.
            notes: Free-form notes.

        Returns:
            ClientResult[Prediction]: The registered prediction entity.
        """
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
        """Register an analysis with typed keyword arguments.

        Args:
            id: Unique analysis identifier.
            dry_run: If ``True``, validate without persisting.
            command: Shell command that runs the analysis.
            path: Filesystem path to the analysis script.
            uses_parameters: IDs of parameters consumed by this analysis.
            notes: Free-form notes.
            last_result: Most recent result value.
            last_result_sha: SHA of the last result for staleness detection.
            last_result_date: Date of the last result.

        Returns:
            ClientResult[Analysis]: The registered analysis entity.
        """
        raise NotImplementedError

    def register_theory(
        self,
        id: str,
        title: str,
        status: TheoryStatus | str,
        *,
        dry_run: bool = False,
        summary: str | None = None,
        related_claims: Iterable[str] | None = None,
        related_predictions: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[Theory]:
        """Register a theory with typed keyword arguments.

        Args:
            id: Unique theory identifier.
            title: Display title.
            status: Theory status (proposed, active, etc.).
            dry_run: If ``True``, validate without persisting.
            summary: Summary description.
            related_claims: IDs of related claims.
            related_predictions: IDs of related predictions.
            source: Provenance reference.

        Returns:
            ClientResult[Theory]: The registered theory entity.
        """
        raise NotImplementedError

    def register_discovery(
        self,
        id: str,
        title: str,
        date: date | str,
        summary: str,
        impact: str,
        status: DiscoveryStatus | str,
        *,
        dry_run: bool = False,
        related_claims: Iterable[str] | None = None,
        related_predictions: Iterable[str] | None = None,
        references: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[Discovery]:
        """Register a discovery with typed keyword arguments.

        Args:
            id: Unique discovery identifier.
            title: Display title.
            date: Discovery date.
            summary: Summary description.
            impact: Impact assessment.
            status: Discovery status.
            dry_run: If ``True``, validate without persisting.
            related_claims: IDs of related claims.
            related_predictions: IDs of related predictions.
            references: External reference strings.
            source: Provenance reference.

        Returns:
            ClientResult[Discovery]: The registered discovery entity.
        """
        raise NotImplementedError

    def register_dead_end(
        self,
        id: str,
        title: str,
        description: str,
        status: DeadEndStatus | str,
        *,
        dry_run: bool = False,
        related_predictions: Iterable[str] | None = None,
        related_claims: Iterable[str] | None = None,
        references: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[DeadEnd]:
        """Register a dead end with typed keyword arguments.

        Args:
            id: Unique dead end identifier.
            title: Display title.
            description: What was attempted and why it failed.
            status: Dead end status.
            dry_run: If ``True``, validate without persisting.
            related_predictions: IDs of related predictions.
            related_claims: IDs of related claims.
            references: External reference strings.
            source: Provenance reference.

        Returns:
            ClientResult[DeadEnd]: The registered dead end entity.
        """
        raise NotImplementedError

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
        """Register a parameter with typed keyword arguments.

        Args:
            id: Unique parameter identifier.
            name: Display name.
            value: The parameter value.
            dry_run: If ``True``, validate without persisting.
            unit: Unit of measurement.
            uncertainty: Uncertainty value or range.
            source: Provenance reference.
            notes: Free-form notes.

        Returns:
            ClientResult[Parameter]: The registered parameter entity.
        """
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
        """Register an independence group with typed keyword arguments.

        Args:
            id: Unique independence group identifier.
            label: Display label.
            dry_run: If ``True``, validate without persisting.
            claim_lineage: IDs of claims in the group's derivation lineage.
            assumption_lineage: IDs of assumptions in the group's derivation lineage.
            measurement_regime: Measurement regime classification.
            notes: Free-form notes.

        Returns:
            ClientResult[IndependenceGroup]: The registered group entity.
        """
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
        """Register a pairwise separation record.

        Args:
            id: Unique separation record identifier.
            group_a: ID of the first independence group.
            group_b: ID of the second independence group.
            basis: Justification for the separation.
            dry_run: If ``True``, validate without persisting.

        Returns:
            ClientResult[PairwiseSeparation]: The registered separation.
        """
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

    def get_theory(self, identifier: str) -> ClientResult[Theory]:
        """Retrieve a theory by ID."""
        raise NotImplementedError

    def get_discovery(self, identifier: str) -> ClientResult[Discovery]:
        """Retrieve a discovery by ID."""
        raise NotImplementedError

    def get_dead_end(self, identifier: str) -> ClientResult[DeadEnd]:
        """Retrieve a dead end by ID."""
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

    def list_theories(self, **filters: object) -> ClientResult[list[Theory]]:
        """List all theories, optionally filtered."""
        raise NotImplementedError

    def list_discoveries(self, **filters: object) -> ClientResult[list[Discovery]]:
        """List all discoveries, optionally filtered."""
        raise NotImplementedError

    def list_dead_ends(self, **filters: object) -> ClientResult[list[DeadEnd]]:
        """List all dead ends, optionally filtered."""
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

    def transition_theory(
        self,
        identifier: str,
        new_status: TheoryStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Theory]:
        """Transition a theory to a new status."""
        raise NotImplementedError

    def transition_discovery(
        self,
        identifier: str,
        new_status: DiscoveryStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Discovery]:
        """Transition a discovery to a new status."""
        raise NotImplementedError

    def transition_dead_end(
        self,
        identifier: str,
        new_status: DeadEndStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[DeadEnd]:
        """Transition a dead end to a new status."""
        raise NotImplementedError

    def _invoke_gateway(self, func, *args, **kwargs) -> GatewayResult:
        """Call a gateway method, wrapping unexpected errors in DeSitterClientError."""
        raise NotImplementedError

    def _handle_resource_result(
        self,
        resource: str,
        result: GatewayResult,
    ) -> ClientResult[Any]:
        """Convert a gateway result into a typed ClientResult with a deserialized entity.

        Raises DeSitterClientError if the result status is not success.
        """
        raise NotImplementedError

    def _handle_resource_list_result(
        self,
        resource: str,
        result: GatewayResult,
    ) -> ClientResult[list[Any]]:
        """Convert a gateway list result into a typed ClientResult with deserialized entities.

        Raises DeSitterClientError if the result status is not success.
        """
        raise NotImplementedError

    def _handle_query_result(self, result: GatewayResult) -> ClientResult[Any]:
        """Convert a gateway query result into a typed ClientResult.

        Raises DeSitterClientError if the result status is not success.
        """
        raise NotImplementedError

    def _canonical_resource(self, resource: str) -> str:
        """Resolve a resource alias to its canonical key, falling back to the input."""
        raise NotImplementedError


def connect(path: str | Path | None = None) -> DeSitterClient:
    """Build a ``DeSitterClient``, optionally backed by a JSON repository.

    If ``path`` is ``None``, returns a purely in-memory client (no
    persistence; ``save()`` is a no-op and the web starts empty).

    If ``path`` is provided, loads the epistemic web from a
    ``JsonRepository`` rooted at *path*, constructs a fully wired
    gateway, and returns a persistent client.

    Args:
        path: Path to the project workspace directory containing the
            ``data/`` folder. ``None`` (default) creates a fresh
            in-memory session.

    Returns:
        DeSitterClient: A wired client; persistent when ``path`` is given.
    """
    raise NotImplementedError


def _without_none(**payload: object) -> dict[str, object]:
    """Return a copy of *payload* with all ``None`` values removed."""
    raise NotImplementedError


__all__ = [
    "ClientResult",
    "DeSitterClient",
    "DeSitterClientError",
    "connect",
]