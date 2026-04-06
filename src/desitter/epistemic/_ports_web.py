"""Epistemic aggregate and repository protocols."""
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

    Any implementation that satisfies this protocol — an in-memory
    ``EpistemicWeb``, a DB-backed proxy, or a test double — can be used
    wherever an epistemic web is required. The ``Gateway`` and all
    control-plane code depend on this protocol rather than the concrete
    ``EpistemicWeb`` class.

    Every mutation method returns a NEW web instance. Callers must
    replace their reference with the return value. The old instance is
    never modified.

    Attributes:
        version: Monotonically increasing version counter. Zero for
            in-memory webs; incremented by the repository on each save.
            Used for optimistic concurrency control.
        claims: Registry of all claims, keyed by ``ClaimId``.
        assumptions: Registry of all assumptions, keyed by
            ``AssumptionId``.
        predictions: Registry of all predictions, keyed by
            ``PredictionId``.
        theories: Registry of all theories, keyed by ``TheoryId``.
        discoveries: Registry of all discoveries, keyed by
            ``DiscoveryId``.
        analyses: Registry of all analyses, keyed by ``AnalysisId``.
        independence_groups: Registry of all independence groups, keyed
            by ``IndependenceGroupId``.
        pairwise_separations: Registry of all pairwise separation
            records, keyed by ``PairwiseSeparationId``.
        dead_ends: Registry of all dead end records, keyed by
            ``DeadEndId``.
        parameters: Registry of all parameters, keyed by
            ``ParameterId``.
    """

    version: int

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

    def get_claim(self, cid: ClaimId) -> Claim | None:
        """Return a claim by ID, or ``None`` if it does not exist.

        Args:
            cid: The claim identifier to look up.

        Returns:
            Claim | None: The claim instance, or ``None`` if not found.
        """
        ...

    def get_assumption(self, aid: AssumptionId) -> Assumption | None:
        """Return an assumption by ID, or ``None`` if it does not exist.

        Args:
            aid: The assumption identifier to look up.

        Returns:
            Assumption | None: The assumption instance, or ``None`` if
                not found.
        """
        ...

    def get_prediction(self, pid: PredictionId) -> Prediction | None:
        """Return a prediction by ID, or ``None`` if it does not exist.

        Args:
            pid: The prediction identifier to look up.

        Returns:
            Prediction | None: The prediction instance, or ``None`` if
                not found.
        """
        ...

    # ── Graph queries ─────────────────────────────────────────────

    def claims_using_assumption(self, aid: AssumptionId) -> set[ClaimId]:
        """Return the IDs of all claims that directly reference this assumption.

        Args:
            aid: The assumption to search for in claim ``assumptions`` sets.

        Returns:
            set[ClaimId]: IDs of claims whose ``assumptions`` contains ``aid``.
        """
        ...

    def claim_lineage(self, cid: ClaimId) -> set[ClaimId]:
        """Return the transitive closure of a claim's ``depends_on`` chain.

        The input claim itself is NOT included in the result.

        Args:
            cid: The claim whose ancestor chain to compute.

        Returns:
            set[ClaimId]: All ancestor claim IDs, excluding ``cid`` itself.
        """
        ...

    def assumption_lineage(self, cid: ClaimId) -> set[AssumptionId]:
        """Return all assumptions reachable from a claim and its ancestors.

        Expands through both claim ``depends_on`` chains and assumption
        ``depends_on`` chains to capture every presupposed assumption.

        Args:
            cid: The claim whose full assumption lineage to compute.

        Returns:
            set[AssumptionId]: All transitively reachable assumption IDs.
        """
        ...

    def prediction_implicit_assumptions(self, pid: PredictionId) -> set[AssumptionId]:
        """Return every assumption in the full derivation chain of a prediction.

        Combines assumptions from all claim lineages, conditional_on
        chains, and transitive assumption depends_on chains.

        Args:
            pid: The prediction whose implicit assumptions to compute.

        Returns:
            set[AssumptionId]: All assumption IDs the prediction depends
                on. Empty set if the prediction does not exist.
        """
        ...

    def refutation_impact(self, pid: PredictionId) -> dict[str, set]:
        """Compute the blast radius when a prediction is refuted.

        Args:
            pid: The prediction to analyze.

        Returns:
            dict[str, set]: Keys are ``claim_ids`` (direct claims),
                ``claim_ancestors`` (transitive ancestors excluding direct
                claims), and ``implicit_assumptions`` (full assumption
                chain). All values are empty sets if the prediction does
                not exist.
        """
        ...

    def assumption_support_status(self, aid: AssumptionId) -> dict[str, set]:
        """Compute the dependency and test coverage of an assumption.

        Args:
            aid: The assumption to analyze.

        Returns:
            dict[str, set]: Keys are ``direct_claims`` (claims that
                directly reference this assumption), ``dependent_predictions``
                (predictions whose derivation chain includes this assumption),
                and ``tested_by`` (predictions that explicitly test it).
                All values are empty sets if the assumption does not exist.
        """
        ...

    def claims_depending_on_claim(self, cid: ClaimId) -> set[ClaimId]:
        """Return all claims that transitively depend on this claim.

        Args:
            cid: The claim to trace forward from.

        Returns:
            set[ClaimId]: All downstream claim IDs. Does not include
                ``cid`` itself.
        """
        ...

    def predictions_depending_on_claim(self, cid: ClaimId) -> set[PredictionId]:
        """Return all predictions whose derivation chain includes this claim.

        Args:
            cid: The claim to trace forward from.

        Returns:
            set[PredictionId]: All prediction IDs whose ``claim_ids``
                intersects with ``cid`` or its downstream dependents.
        """
        ...

    def parameter_impact(self, pid: ParameterId) -> dict[str, set]:
        """Compute the full blast radius of a parameter change.

        Args:
            pid: The parameter whose impact to compute.

        Returns:
            dict[str, set]: Keys are ``stale_analyses``,
                ``constrained_claims``, ``affected_claims``, and
                ``affected_predictions``. All values are empty sets if
                the parameter does not exist.
        """
        ...

    # ── Registration mutations ────────────────────────────────────

    def register_claim(self, claim: Claim) -> EpistemicWebPort:
        """Register a new claim. Returns a new web instance.

        Args:
            claim: The claim to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered claim.

        Raises:
            DuplicateIdError: If ``claim.id`` already exists.
            BrokenReferenceError: If any referenced ID does not exist.
            CycleError: If ``depends_on`` would create a cycle.
        """
        ...

    def register_assumption(self, assumption: Assumption) -> EpistemicWebPort:
        """Register a new assumption. Returns a new web instance.

        Args:
            assumption: The assumption to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered assumption.

        Raises:
            DuplicateIdError: If ``assumption.id`` already exists.
            BrokenReferenceError: If any ``depends_on`` ID does not exist.
            CycleError: If ``depends_on`` would create a cycle.
        """
        ...

    def register_prediction(self, prediction: Prediction) -> EpistemicWebPort:
        """Register a new prediction. Returns a new web instance.

        Args:
            prediction: The prediction to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered prediction.

        Raises:
            DuplicateIdError: If ``prediction.id`` already exists.
            BrokenReferenceError: If any referenced ID does not exist.
        """
        ...

    def register_analysis(self, analysis: Analysis) -> EpistemicWebPort:
        """Register a new analysis reference. Returns a new web instance.

        Args:
            analysis: The analysis to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered analysis.

        Raises:
            DuplicateIdError: If ``analysis.id`` already exists.
            BrokenReferenceError: If any ``uses_parameters`` ID does not exist.
        """
        ...

    def register_theory(self, theory: Theory) -> EpistemicWebPort:
        """Register a new theory. Returns a new web instance.

        Args:
            theory: The theory to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered theory.

        Raises:
            DuplicateIdError: If ``theory.id`` already exists.
            BrokenReferenceError: If any referenced claim or prediction ID
                does not exist.
        """
        ...

    def register_independence_group(self, group: IndependenceGroup) -> EpistemicWebPort:
        """Register a new independence group. Returns a new web instance.

        Args:
            group: The group to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered group.

        Raises:
            DuplicateIdError: If ``group.id`` already exists.
            BrokenReferenceError: If any lineage claim or assumption ID
                does not exist.
        """
        ...

    def register_discovery(self, discovery: Discovery) -> EpistemicWebPort:
        """Register a new discovery. Returns a new web instance.

        Args:
            discovery: The discovery to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered discovery.

        Raises:
            DuplicateIdError: If ``discovery.id`` already exists.
            BrokenReferenceError: If any referenced ID does not exist.
        """
        ...

    def register_dead_end(self, dead_end: DeadEnd) -> EpistemicWebPort:
        """Register a new dead end record. Returns a new web instance.

        Args:
            dead_end: The dead end to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered dead end.

        Raises:
            DuplicateIdError: If ``dead_end.id`` already exists.
            BrokenReferenceError: If any referenced ID does not exist.
        """
        ...

    def register_parameter(self, parameter: Parameter) -> EpistemicWebPort:
        """Register a new parameter. Returns a new web instance.

        Args:
            parameter: The parameter to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the registered parameter.

        Raises:
            DuplicateIdError: If ``parameter.id`` already exists.
        """
        ...

    def add_pairwise_separation(self, sep: PairwiseSeparation) -> EpistemicWebPort:
        """Register a pairwise independence separation. Returns a new web instance.

        Both referenced groups must already exist and must be distinct.

        Args:
            sep: The separation record to add. Must have a unique ``id``.

        Returns:
            EpistemicWebPort: New web containing the separation record.

        Raises:
            DuplicateIdError: If ``sep.id`` already exists.
            BrokenReferenceError: If either group does not exist or both
                groups are the same.
        """
        ...

    # ── Update mutations ──────────────────────────────────────────

    def update_claim(self, new_claim: Claim) -> EpistemicWebPort:
        """Replace a claim's fields. Returns a new web instance.

        The new claim must share the same ``id`` as an existing claim.
        Bidirectional links are updated by diffing old vs new references.

        Args:
            new_claim: The updated claim. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated claim.

        Raises:
            BrokenReferenceError: If the claim does not exist or if any
                newly referenced ID does not exist.
            CycleError: If the updated ``depends_on`` would create a cycle.
        """
        ...

    def update_assumption(self, new_assumption: Assumption) -> EpistemicWebPort:
        """Replace an assumption's fields. Returns a new web instance.

        Backlinks ``used_in_claims`` and ``tested_by`` are preserved.

        Args:
            new_assumption: The updated assumption. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated assumption.

        Raises:
            BrokenReferenceError: If the assumption does not exist or if
                any ``depends_on`` ID does not exist.
            CycleError: If the updated ``depends_on`` would create a cycle.
        """
        ...

    def update_prediction(self, new_prediction: Prediction) -> EpistemicWebPort:
        """Replace a prediction's fields. Returns a new web instance.

        Bidirectional links with assumptions and independence groups are
        updated by diffing old vs new references.

        Args:
            new_prediction: The updated prediction. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated prediction.

        Raises:
            BrokenReferenceError: If the prediction does not exist or if
                any newly referenced ID does not exist.
        """
        ...

    def update_parameter(self, new_parameter: Parameter) -> EpistemicWebPort:
        """Replace a parameter's fields. Returns a new web instance.

        The ``used_in_analyses`` backlink is preserved from the existing record.

        Args:
            new_parameter: The updated parameter. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated parameter.

        Raises:
            BrokenReferenceError: If the parameter does not exist.
        """
        ...

    def update_analysis(self, new_analysis: Analysis) -> EpistemicWebPort:
        """Replace an analysis's fields. Returns a new web instance.

        ``claims_covered`` is preserved; ``Parameter.used_in_analyses``
        backlinks are updated by diffing old vs new ``uses_parameters``.

        Args:
            new_analysis: The updated analysis. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated analysis.

        Raises:
            BrokenReferenceError: If the analysis does not exist or if
                any ``uses_parameters`` ID does not exist.
        """
        ...

    def update_theory(self, new_theory: Theory) -> EpistemicWebPort:
        """Replace a theory's fields. Returns a new web instance.

        Args:
            new_theory: The updated theory. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated theory.

        Raises:
            BrokenReferenceError: If the theory does not exist or if any
                referenced claim or prediction ID does not exist.
        """
        ...

    def update_independence_group(self, new_group: IndependenceGroup) -> EpistemicWebPort:
        """Replace an independence group's annotation fields. Returns a new web instance.

        ``member_predictions`` backlink is preserved from the existing record.

        Args:
            new_group: The updated group. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated group.

        Raises:
            BrokenReferenceError: If the group does not exist or if any
                lineage ID does not exist.
        """
        ...

    def update_pairwise_separation(self, new_sep: PairwiseSeparation) -> EpistemicWebPort:
        """Replace a pairwise separation record's fields. Returns a new web instance.

        Args:
            new_sep: The updated separation. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated separation record.

        Raises:
            BrokenReferenceError: If the separation does not exist, if
                either group does not exist, or if both groups are the same.
        """
        ...

    def update_discovery(self, new_discovery: Discovery) -> EpistemicWebPort:
        """Replace a discovery's fields. Returns a new web instance.

        Args:
            new_discovery: The updated discovery. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated discovery.

        Raises:
            BrokenReferenceError: If the discovery does not exist or if
                any referenced ID does not exist.
        """
        ...

    def update_dead_end(self, new_dead_end: DeadEnd) -> EpistemicWebPort:
        """Replace a dead end's fields. Returns a new web instance.

        Args:
            new_dead_end: The updated dead end. Must match an existing ``id``.

        Returns:
            EpistemicWebPort: New web with the updated dead end.

        Raises:
            BrokenReferenceError: If the dead end does not exist or if
                any referenced ID does not exist.
        """
        ...

    # ── Status transitions ────────────────────────────────────────

    def transition_prediction(self, pid: PredictionId, new_status: PredictionStatus) -> EpistemicWebPort:
        """Change a prediction's lifecycle status. Returns a new web instance.

        Args:
            pid: The prediction ID to transition.
            new_status: The target ``PredictionStatus`` value.

        Returns:
            EpistemicWebPort: New web with the updated prediction status.

        Raises:
            BrokenReferenceError: If the prediction does not exist.
        """
        ...

    def transition_dead_end(self, did: DeadEndId, new_status: DeadEndStatus) -> EpistemicWebPort:
        """Change a dead end's lifecycle status. Returns a new web instance.

        Args:
            did: The dead end ID to transition.
            new_status: The target ``DeadEndStatus`` value.

        Returns:
            EpistemicWebPort: New web with the updated dead end status.

        Raises:
            BrokenReferenceError: If the dead end does not exist.
        """
        ...

    def transition_claim(self, cid: ClaimId, new_status: ClaimStatus) -> EpistemicWebPort:
        """Change a claim's lifecycle status. Returns a new web instance.

        Args:
            cid: The claim ID to transition.
            new_status: The target ``ClaimStatus`` value.

        Returns:
            EpistemicWebPort: New web with the updated claim status.

        Raises:
            BrokenReferenceError: If the claim does not exist.
        """
        ...

    def transition_theory(self, tid: TheoryId, new_status: TheoryStatus) -> EpistemicWebPort:
        """Change a theory's lifecycle status. Returns a new web instance.

        Args:
            tid: The theory ID to transition.
            new_status: The target ``TheoryStatus`` value.

        Returns:
            EpistemicWebPort: New web with the updated theory status.

        Raises:
            BrokenReferenceError: If the theory does not exist.
        """
        ...

    def transition_discovery(self, did: DiscoveryId, new_status: DiscoveryStatus) -> EpistemicWebPort:
        """Change a discovery's lifecycle status. Returns a new web instance.

        Args:
            did: The discovery ID to transition.
            new_status: The target ``DiscoveryStatus`` value.

        Returns:
            EpistemicWebPort: New web with the updated discovery status.

        Raises:
            BrokenReferenceError: If the discovery does not exist.
        """
        ...

    # ── Result recording ──────────────────────────────────────────

    def record_analysis_result(
        self,
        anid: AnalysisId,
        result: object,
        *,
        git_sha: str | None = None,
        result_date: date | None = None,
    ) -> EpistemicWebPort:
        """Record the output of a completed analysis run. Returns a new web instance.

        Sets ``last_result``, ``last_result_sha``, and ``last_result_date``
        on the analysis, preserving all other fields.

        Args:
            anid: The analysis ID to update.
            result: The output value of the analysis run.
            git_sha: Optional git SHA of the analysis code at run time.
            result_date: Optional date when the result was recorded.

        Returns:
            EpistemicWebPort: New web with the analysis result recorded.

        Raises:
            BrokenReferenceError: If the analysis does not exist.
        """
        ...

    # ── Removal mutations ─────────────────────────────────────────

    def remove_prediction(self, pid: PredictionId) -> EpistemicWebPort:
        """Remove a prediction from the web. Returns a new web instance.

        Tears down backlinks and scrubs soft references in theories,
        dead ends, and discoveries.

        Args:
            pid: The prediction ID to remove.

        Returns:
            EpistemicWebPort: New web without the prediction.

        Raises:
            BrokenReferenceError: If the prediction does not exist.
        """
        ...

    def remove_claim(self, cid: ClaimId) -> EpistemicWebPort:
        """Remove a claim from the web. Returns a new web instance.

        Raises if any claim or prediction still hard-references this claim.
        Callers must first update or remove all referencing entities.

        Args:
            cid: The claim ID to remove.

        Returns:
            EpistemicWebPort: New web without the claim.

        Raises:
            BrokenReferenceError: If the claim does not exist or is still
                referenced by other claims or predictions.
        """
        ...

    def remove_assumption(self, aid: AssumptionId) -> EpistemicWebPort:
        """Remove an assumption from the web. Returns a new web instance.

        Raises if any claim, prediction, or other assumption still
        references this assumption.

        Args:
            aid: The assumption ID to remove.

        Returns:
            EpistemicWebPort: New web without the assumption.

        Raises:
            BrokenReferenceError: If the assumption does not exist or is
                still referenced by other entities.
        """
        ...

    def remove_parameter(self, pid: ParameterId) -> EpistemicWebPort:
        """Remove a parameter from the web. Returns a new web instance.

        Raises if any analysis still references this parameter.

        Args:
            pid: The parameter ID to remove.

        Returns:
            EpistemicWebPort: New web without the parameter.

        Raises:
            BrokenReferenceError: If the parameter does not exist or is
                still used by analyses.
        """
        ...

    def remove_analysis(self, anid: AnalysisId) -> EpistemicWebPort:
        """Remove an analysis from the web. Returns a new web instance.

        Raises if any claim or prediction still hard-references this analysis.

        Args:
            anid: The analysis ID to remove.

        Returns:
            EpistemicWebPort: New web without the analysis.

        Raises:
            BrokenReferenceError: If the analysis does not exist or is
                still referenced by claims or predictions.
        """
        ...

    def remove_independence_group(self, gid: IndependenceGroupId) -> EpistemicWebPort:
        """Remove an independence group from the web. Returns a new web instance.

        Raises if any prediction or pairwise separation still references
        this group.

        Args:
            gid: The independence group ID to remove.

        Returns:
            EpistemicWebPort: New web without the group.

        Raises:
            BrokenReferenceError: If the group does not exist or is still
                referenced by predictions or separations.
        """
        ...

    def remove_theory(self, tid: TheoryId) -> EpistemicWebPort:
        """Remove a theory from the web. Returns a new web instance.

        Theories are leaf entities — removal is always structurally safe.

        Args:
            tid: The theory ID to remove.

        Returns:
            EpistemicWebPort: New web without the theory.

        Raises:
            BrokenReferenceError: If the theory does not exist.
        """
        ...

    def remove_discovery(self, did: DiscoveryId) -> EpistemicWebPort:
        """Remove a discovery from the web. Returns a new web instance.

        Discoveries are leaf entities — removal is always structurally safe.

        Args:
            did: The discovery ID to remove.

        Returns:
            EpistemicWebPort: New web without the discovery.

        Raises:
            BrokenReferenceError: If the discovery does not exist.
        """
        ...

    def remove_dead_end(self, did: DeadEndId) -> EpistemicWebPort:
        """Remove a dead end from the web. Returns a new web instance.

        Dead ends are leaf entities — removal is always structurally safe.

        Args:
            did: The dead end ID to remove.

        Returns:
            EpistemicWebPort: New web without the dead end.

        Raises:
            BrokenReferenceError: If the dead end does not exist.
        """
        ...

    def remove_pairwise_separation(self, sid: PairwiseSeparationId) -> EpistemicWebPort:
        """Remove a pairwise separation record from the web. Returns a new web instance.

        Args:
            sid: The separation record ID to remove.

        Returns:
            EpistemicWebPort: New web without the separation record.

        Raises:
            BrokenReferenceError: If the separation does not exist.
        """
        ...


class WebRepository(Protocol):
    """Persistence abstraction for loading and saving the epistemic web.

    Implementors provide storage-specific serialization/deserialization
    logic. The ``Gateway`` and ``DeSitterClient`` depend on this protocol
    rather than any specific storage format.

    Concrete implementations include:
    - ``JsonRepository`` — JSON files on the local filesystem.
    - Future: database-backed, remote API, etc.
    """

    def load(self) -> EpistemicWebPort:
        """Deserialize and return the full epistemic web from storage.

        Returns:
            EpistemicWebPort: The fully hydrated epistemic web.
        """
        ...

    def save(self, web: EpistemicWebPort) -> None:
        """Serialize and persist the epistemic web to storage.

        Args:
            web: The web instance to persist.
        """
        ...

    @property
    def supports_native_validation(self) -> bool:
        """Whether the backend can run domain validation natively.

        When ``True``, the gateway may skip the Python-side invariant
        check and delegate validation to the backend (e.g. a DB with
        constraint checks). Defaults to ``False``.

        Returns:
            bool: ``True`` if the backend performs native validation.
        """
        return False


__all__ = ["EpistemicWebPort", "WebRepository"]