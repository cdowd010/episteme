"""Abstract interfaces the domain REQUIRES but does not IMPLEMENT.

Implemented by the adapters layer. Domain code programs against these
protocols, never against concrete classes.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Protocol

from .model import (
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
from .types import (
    AnalysisId,
    AssumptionId,
    ClaimId,
    ClaimStatus,
    DeadEndId,
    DeadEndStatus,
    DiscoveryId,
    DiscoveryStatus,
    Finding,
    IndependenceGroupId,
    ParameterId,
    PairwiseSeparationId,
    PredictionId,
    PredictionStatus,
    TheoryId,
    TheoryStatus,
)


class EpistemicWebPort(Protocol):
    """Dependency-inversion point for the epistemic web aggregate.

    The concrete ``EpistemicWeb`` (in-memory, copy-on-write) satisfies this
    protocol via Python structural subtyping — no changes to ``EpistemicWeb``
    are required. A DB-backed agent-scale implementation only needs to
    implement this protocol; the Gateway, validators, views, and invariant
    checks require no modification.

    **How the DB-scale pattern works** (for implementers):

    Systems like SQLAlchemy use an *identity map* — a session-local entity
    cache. Single-entity lookups hit the cache first, then issue a DB query
    on a miss. The 10 ``Mapping`` collection attributes are *lazy-loading
    proxies*: they look like Python dicts but first iteration triggers a
    paginated DB scan. Mutations are written to the session and flushed as
    a batch. Traversal queries map to recursive CTEs or graph-DB traversals.
    The ``supports_native_validation`` hook on ``WebRepository`` lets the
    backend run invariant checks as DB queries instead of in-memory scans.

    **Mutation methods** return ``EpistemicWebPort``. The in-memory
    implementation returns a new ``EpistemicWeb`` copy (cheap for small
    webs). A DB session implementation returns ``self`` after writing.
    Both satisfy this protocol — return types are covariant.

    **Collection attributes** are ``Mapping`` (read-only dict-like) not
    ``dict``. A lazy-loading DB proxy satisfies ``Mapping``; so does the
    concrete ``dict`` on ``EpistemicWeb``.
    """

    version: int

    # ── Collections ───────────────────────────────────────────────
    # Mapping (not dict) lets DB implementations return lazy-loading proxies
    # without any caller changes.
    claims: Mapping[ClaimId, Claim]
    assumptions: Mapping[AssumptionId, Assumption]
    predictions: Mapping[PredictionId, Prediction]
    theories: Mapping[TheoryId, Theory]
    discoveries: Mapping[DiscoveryId, Discovery]
    analyses: Mapping[AnalysisId, Analysis]
    independence_groups: Mapping[IndependenceGroupId, IndependenceGroup]
    pairwise_separations: Mapping[PairwiseSeparationId, PairwiseSeparation]
    dead_ends: Mapping[DeadEndId, DeadEnd]
    parameters: Mapping[ParameterId, Parameter]

    # ── Point lookups ─────────────────────────────────────────────

    def get_claim(self, cid: ClaimId) -> Claim | None: ...
    def get_assumption(self, aid: AssumptionId) -> Assumption | None: ...
    def get_prediction(self, pid: PredictionId) -> Prediction | None: ...

    # ── Traversal queries ─────────────────────────────────────────
    # Map to recursive CTEs or graph-DB traversals in DB implementations.

    def claims_using_assumption(self, aid: AssumptionId) -> set[ClaimId]: ...
    def claim_lineage(self, cid: ClaimId) -> set[ClaimId]: ...
    def assumption_lineage(self, cid: ClaimId) -> set[AssumptionId]: ...
    def prediction_implicit_assumptions(self, pid: PredictionId) -> set[AssumptionId]: ...
    def refutation_impact(self, pid: PredictionId) -> dict[str, set]: ...
    def assumption_support_status(self, aid: AssumptionId) -> dict[str, set]: ...
    def claims_depending_on_claim(self, cid: ClaimId) -> set[ClaimId]: ...
    def predictions_depending_on_claim(self, cid: ClaimId) -> set[PredictionId]: ...
    def parameter_impact(self, pid: ParameterId) -> dict[str, set]: ...

    # ── Register mutations ────────────────────────────────────────
    # In-memory: returns new EpistemicWeb copy.
    # DB session: returns self after persisting to session.

    def register_claim(self, claim: Claim) -> EpistemicWebPort: ...
    def register_assumption(self, assumption: Assumption) -> EpistemicWebPort: ...
    def register_prediction(self, prediction: Prediction) -> EpistemicWebPort: ...
    def register_analysis(self, analysis: Analysis) -> EpistemicWebPort: ...
    def register_theory(self, theory: Theory) -> EpistemicWebPort: ...
    def register_independence_group(self, group: IndependenceGroup) -> EpistemicWebPort: ...
    def register_discovery(self, discovery: Discovery) -> EpistemicWebPort: ...
    def register_dead_end(self, dead_end: DeadEnd) -> EpistemicWebPort: ...
    def register_parameter(self, parameter: Parameter) -> EpistemicWebPort: ...
    def add_pairwise_separation(self, sep: PairwiseSeparation) -> EpistemicWebPort: ...

    # ── Update mutations ──────────────────────────────────────────

    def update_claim(self, new_claim: Claim) -> EpistemicWebPort: ...
    def update_assumption(self, new_assumption: Assumption) -> EpistemicWebPort: ...
    def update_prediction(self, new_prediction: Prediction) -> EpistemicWebPort: ...
    def update_parameter(self, new_parameter: Parameter) -> EpistemicWebPort: ...
    def update_analysis(self, new_analysis: Analysis) -> EpistemicWebPort: ...
    def update_theory(self, new_theory: Theory) -> EpistemicWebPort: ...
    def update_independence_group(self, new_group: IndependenceGroup) -> EpistemicWebPort: ...
    def update_pairwise_separation(self, new_sep: PairwiseSeparation) -> EpistemicWebPort: ...
    def update_discovery(self, new_discovery: Discovery) -> EpistemicWebPort: ...
    def update_dead_end(self, new_dead_end: DeadEnd) -> EpistemicWebPort: ...

    # ── Transition mutations ──────────────────────────────────────

    def transition_prediction(self, pid: PredictionId, new_status: PredictionStatus) -> EpistemicWebPort: ...
    def transition_dead_end(self, did: DeadEndId, new_status: DeadEndStatus) -> EpistemicWebPort: ...
    def transition_claim(self, cid: ClaimId, new_status: ClaimStatus) -> EpistemicWebPort: ...
    def transition_theory(self, tid: TheoryId, new_status: TheoryStatus) -> EpistemicWebPort: ...
    def transition_discovery(self, did: DiscoveryId, new_status: DiscoveryStatus) -> EpistemicWebPort: ...

    def record_analysis_result(
        self,
        anid: AnalysisId,
        result: object,
        *,
        git_sha: str | None = None,
        result_date: date | None = None,
    ) -> EpistemicWebPort: ...

    # ── Remove mutations ──────────────────────────────────────────

    def remove_prediction(self, pid: PredictionId) -> EpistemicWebPort: ...
    def remove_claim(self, cid: ClaimId) -> EpistemicWebPort: ...
    def remove_assumption(self, aid: AssumptionId) -> EpistemicWebPort: ...
    def remove_parameter(self, pid: ParameterId) -> EpistemicWebPort: ...
    def remove_analysis(self, anid: AnalysisId) -> EpistemicWebPort: ...
    def remove_independence_group(self, gid: IndependenceGroupId) -> EpistemicWebPort: ...
    def remove_theory(self, tid: TheoryId) -> EpistemicWebPort: ...
    def remove_discovery(self, did: DiscoveryId) -> EpistemicWebPort: ...
    def remove_dead_end(self, did: DeadEndId) -> EpistemicWebPort: ...
    def remove_pairwise_separation(self, sid: PairwiseSeparationId) -> EpistemicWebPort: ...


class WebRepository(Protocol):
    """Load and save the epistemic web."""

    def load(self) -> EpistemicWebPort:
        """Deserialize and return the full epistemic web from storage."""
        ...

    def save(self, web: EpistemicWebPort) -> None:
        """Serialize and persist the epistemic web to storage.

        Implementations should increment ``web.version`` before writing
        so that callers can detect concurrent modification.
        """
        ...

    @property
    def supports_native_validation(self) -> bool:
        """True if the backend can run domain validation natively.

        JSON and in-memory backends return False (full in-memory scan).
        Future database backends may return True and implement validation
        as native queries instead of loading the full web into memory.
        """
        return False


class WebRenderer(Protocol):
    """Generate human-readable artifacts from the web."""

    def render(self, web: EpistemicWebPort) -> dict[str, str]:
        """Return {relative_path: content} for all generated surfaces."""
        ...


class WebValidator(Protocol):
    """Validate the web and return findings."""

    def validate(self, web: EpistemicWebPort) -> list[Finding]:
        """Run all validation rules and return a list of findings."""
        ...


class ProseSync(Protocol):
    """Update managed prose blocks derived from canonical state."""

    def sync(self, web: EpistemicWebPort) -> dict[str, object]:
        """Sync prose blocks and return a summary of changes."""
        ...


class TransactionLog(Protocol):
    """Append provenance for gateway mutations and queries."""

    def append(self, operation: str, identifier: str) -> str:
        """Record an operation and return its transaction ID."""
        ...


class PayloadValidator(Protocol):
    """Validate inbound mutation payloads before the gateway mutates the web."""

    def validate(self, resource: str, payload: dict[str, object]) -> list[Finding]:
        """Return findings describing payload/schema issues, if any."""
        ...
