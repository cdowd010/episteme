"""The EpistemicWeb: aggregate root for the epistemic domain.

External code NEVER modifies entities directly — it calls methods on the
web, and the web ensures consistency.

Every mutation method returns a NEW web. This gives free undo/redo and
eliminates state corruption.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .model import (
    Assumption,
    Claim,
    Concept,
    Discovery,
    Failure,
    Hypothesis,
    IndependenceGroup,
    PairwiseSeparation,
    Parameter,
    Prediction,
    Script,
)
from .types import (
    AssumptionId,
    ClaimId,
    ConceptId,
    DiscoveryId,
    FailureId,
    FailureStatus,
    Finding,
    HypothesisId,
    IndependenceGroupId,
    ParameterId,
    PredictionId,
    PredictionStatus,
    ScriptId,
    Severity,
)


@dataclass
class EpistemicWeb:
    """Complete epistemic state of a research project.

    All mutations go through methods that enforce invariants and return
    a new web. The old web is left untouched (free rollback).
    """
    claims: dict[ClaimId, Claim] = field(default_factory=dict)
    assumptions: dict[AssumptionId, Assumption] = field(default_factory=dict)
    predictions: dict[PredictionId, Prediction] = field(default_factory=dict)
    hypotheses: dict[HypothesisId, Hypothesis] = field(default_factory=dict)
    discoveries: dict[DiscoveryId, Discovery] = field(default_factory=dict)
    scripts: dict[ScriptId, Script] = field(default_factory=dict)
    independence_groups: dict[IndependenceGroupId, IndependenceGroup] = field(
        default_factory=dict
    )
    pairwise_separations: list[PairwiseSeparation] = field(default_factory=list)
    failures: dict[FailureId, Failure] = field(default_factory=dict)
    concepts: dict[ConceptId, Concept] = field(default_factory=dict)
    parameters: dict[ParameterId, Parameter] = field(default_factory=dict)

    # ── Queries ───────────────────────────────────────────────────

    def get_claim(self, cid: ClaimId) -> Claim | None:
        return self.claims.get(cid)

    def get_assumption(self, aid: AssumptionId) -> Assumption | None:
        return self.assumptions.get(aid)

    def get_prediction(self, pid: PredictionId) -> Prediction | None:
        return self.predictions.get(pid)

    def claims_using_assumption(self, aid: AssumptionId) -> set[ClaimId]:
        """All claims that reference this assumption."""
        return {cid for cid, c in self.claims.items() if aid in c.assumptions}

    def claim_lineage(self, cid: ClaimId) -> set[ClaimId]:
        """Transitive closure of depends_on (all ancestors of a claim)."""
        visited: set[ClaimId] = set()
        stack = [cid]
        while stack:
            current = stack.pop()
            claim = self.claims.get(current)
            if claim is None:
                continue
            for dep in claim.depends_on:
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def assumption_lineage(self, cid: ClaimId) -> set[AssumptionId]:
        """All assumptions reachable through a claim and its ancestors."""
        all_claims = self.claim_lineage(cid) | {cid}
        result: set[AssumptionId] = set()
        for ancestor_id in all_claims:
            claim = self.claims.get(ancestor_id)
            if claim:
                result.update(claim.assumptions)
        return result

    # ── Mutations (return new web) ────────────────────────────────

    def register_claim(self, claim: Claim) -> EpistemicWeb:
        """Add a claim. Enforces: no duplicates, refs exist, no cycles,
        bidirectional links updated."""
        if claim.id in self.claims:
            raise DuplicateIdError(f"Claim {claim.id} already exists")
        self._check_refs_exist(claim.assumptions, self.assumptions, "assumption")
        self._check_refs_exist(claim.depends_on, self.claims, "claim")
        self._check_refs_exist(claim.verified_by, self.scripts, "script")
        self._check_no_cycle_with(claim)

        new = self._copy()
        # Deep-copy the incoming entity so a caller who keeps a reference
        # cannot mutate the web's stored copy after registration. All
        # register_* methods follow this same pattern.
        new.claims[claim.id] = copy.deepcopy(claim)

        # Maintain bidirectional: assumption.used_in_claims
        for aid in claim.assumptions:
            new.assumptions[aid].used_in_claims.add(claim.id)

        # Maintain bidirectional: script.claims_covered
        for sid in claim.verified_by:
            new.scripts[sid].claims_covered.add(claim.id)

        return new

    def register_assumption(self, assumption: Assumption) -> EpistemicWeb:
        """Add an assumption."""
        if assumption.id in self.assumptions:
            raise DuplicateIdError(f"Assumption {assumption.id} already exists")
        new = self._copy()
        new.assumptions[assumption.id] = assumption
        return new

    def register_prediction(self, prediction: Prediction) -> EpistemicWeb:
        """Add a prediction. Enforces: refs exist, bidirectional group link."""
        if prediction.id in self.predictions:
            raise DuplicateIdError(f"Prediction {prediction.id} already exists")
        if prediction.claim_id and prediction.claim_id not in self.claims:
            raise BrokenReferenceError(
                f"Claim {prediction.claim_id} does not exist"
            )
        if prediction.script and prediction.script not in self.scripts:
            raise BrokenReferenceError(
                f"Script {prediction.script} does not exist"
            )
        if prediction.independence_group:
            if prediction.independence_group not in self.independence_groups:
                raise BrokenReferenceError(
                    f"Independence group {prediction.independence_group} does not exist"
                )

        new = self._copy()
        new.predictions[prediction.id] = prediction

        # Maintain bidirectional: group.member_predictions
        if prediction.independence_group:
            new.independence_groups[prediction.independence_group].member_predictions.add(
                prediction.id
            )

        return new

    def register_script(self, script: Script) -> EpistemicWeb:
        """Add a verification script."""
        if script.id in self.scripts:
            raise DuplicateIdError(f"Script {script.id} already exists")
        new = self._copy()
        new.scripts[script.id] = script
        return new

    def register_hypothesis(self, hypothesis: Hypothesis) -> EpistemicWeb:
        """Add a hypothesis."""
        if hypothesis.id in self.hypotheses:
            raise DuplicateIdError(f"Hypothesis {hypothesis.id} already exists")
        new = self._copy()
        new.hypotheses[hypothesis.id] = hypothesis
        return new

    def register_independence_group(self, group: IndependenceGroup) -> EpistemicWeb:
        """Add an independence group."""
        if group.id in self.independence_groups:
            raise DuplicateIdError(f"Independence group {group.id} already exists")
        new = self._copy()
        new.independence_groups[group.id] = group
        return new

    def register_discovery(self, discovery: Discovery) -> EpistemicWeb:
        """Add a discovery."""
        if discovery.id in self.discoveries:
            raise DuplicateIdError(f"Discovery {discovery.id} already exists")
        new = self._copy()
        new.discoveries[discovery.id] = discovery
        return new

    def register_failure(self, failure: Failure) -> EpistemicWeb:
        """Add a failure record."""
        if failure.id in self.failures:
            raise DuplicateIdError(f"Failure {failure.id} already exists")
        new = self._copy()
        new.failures[failure.id] = failure
        return new

    def register_concept(self, concept: Concept) -> EpistemicWeb:
        """Add a concept definition."""
        if concept.id in self.concepts:
            raise DuplicateIdError(f"Concept {concept.id} already exists")
        new = self._copy()
        new.concepts[concept.id] = concept
        return new

    def register_parameter(self, parameter: Parameter) -> EpistemicWeb:
        """Add a parameter constant."""
        if parameter.id in self.parameters:
            raise DuplicateIdError(f"Parameter {parameter.id} already exists")
        new = self._copy()
        new.parameters[parameter.id] = parameter
        return new

    def add_pairwise_separation(self, sep: PairwiseSeparation) -> EpistemicWeb:
        """Document why two independence groups are separate."""
        if sep.group_a not in self.independence_groups:
            raise BrokenReferenceError(f"Group {sep.group_a} does not exist")
        if sep.group_b not in self.independence_groups:
            raise BrokenReferenceError(f"Group {sep.group_b} does not exist")
        new = self._copy()
        new.pairwise_separations.append(sep)
        return new

    def transition_prediction(
        self, pid: PredictionId, new_status: PredictionStatus
    ) -> EpistemicWeb:
        """Change a prediction's status."""
        if pid not in self.predictions:
            raise BrokenReferenceError(f"Prediction {pid} does not exist")
        new = self._copy()
        new.predictions[pid].status = new_status
        return new

    def transition_failure(
        self,
        fid: FailureId,
        new_status: FailureStatus,
        session_resolved: int | None = None,
    ) -> EpistemicWeb:
        """Change a failure's status, with side effects."""
        if fid not in self.failures:
            raise BrokenReferenceError(f"Failure {fid} does not exist")
        new = self._copy()
        new.failures[fid].status = new_status
        if new_status == FailureStatus.RESOLVED and session_resolved is not None:
            new.failures[fid].session_resolved = session_resolved
        elif new_status == FailureStatus.ACTIVE:
            new.failures[fid].session_resolved = None
        return new

    # ── Invariant checks ──────────────────────────────────────────

    def _check_refs_exist(self, ids: set, registry: dict, label: str) -> None:
        missing = ids - registry.keys()
        if missing:
            raise BrokenReferenceError(f"Non-existent {label}(s): {missing}")

    def _check_no_cycle_with(self, claim: Claim) -> None:
        """Verify adding this claim doesn't create a cycle in depends_on."""
        visited: set[ClaimId] = set()
        stack = list(claim.depends_on)
        while stack:
            current = stack.pop()
            if current == claim.id:
                raise CycleError(
                    f"Adding {claim.id} would create a dependency cycle"
                )
            if current in visited:
                continue
            visited.add(current)
            upstream = self.claims.get(current)
            if upstream:
                stack.extend(upstream.depends_on)

    def _copy(self) -> EpistemicWeb:
        """Deep copy for copy-on-write mutation semantics.

        O(n) cost per mutation where n is total entity count. Acceptable
        for research-scale webs (hundreds to low thousands of entities).
        If this becomes a bottleneck, structural sharing of unchanged
        sub-dicts is the migration path — not a change to make speculatively.
        """
        return copy.deepcopy(self)


# ── Domain exceptions ─────────────────────────────────────────────

class EpistemicError(Exception):
    """Base for all domain errors."""


class DuplicateIdError(EpistemicError):
    pass


class BrokenReferenceError(EpistemicError):
    pass


class CycleError(EpistemicError):
    pass


class InvariantViolation(EpistemicError):
    pass
