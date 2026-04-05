"""The single mutation/query boundary for the control plane.

Both the MCP server and the CLI route all operations through the Gateway.
There is no MCP-specific or CLI-specific business logic.

Responsibilities:
  - Hold the epistemic web in memory for the lifetime of a session.
  - Resource-oriented register/get/list/set/transition/query operations.
  - Payload parsing and normalization.
  - Resource alias resolution (plural/hyphenated → canonical keys).
  - Dry-run semantics (validate without mutating).
  - Post-mutation invariant enforcement (CRITICAL findings block mutation).

Not responsible for:
  - Persistence — that belongs to DeSitterClient via WebRepository.
  - Transaction logging — deferred to the persistence layer.
  - Prose sync, view rendering, or any I/O.
  - Formatting human CLI output.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.codec import (
    entity_id_type,
    entity_to_dict,
    normalize_payload,
    serialize_value,
    status_enum_type,
)
from ..epistemic.ports import (
    EpistemicWebPort,
    PayloadValidator,
    WebValidator,
)
from ..epistemic.types import Finding, Severity
from ..epistemic.web import EpistemicError


# Maps plural/hyphenated CLI forms to canonical resource keys.
# Adding a new resource type means adding one entry here.
GATEWAY_RESOURCE_ALIASES: dict[str, str] = {
    "claim": "claim",
    "claims": "claim",
    "assumption": "assumption",
    "assumptions": "assumption",
    "prediction": "prediction",
    "predictions": "prediction",
    "analysis": "analysis",
    "analyses": "analysis",
    "independence-group": "independence_group",
    "independence_group": "independence_group",
    "independence-groups": "independence_group",
    "independence_groups": "independence_group",
    "theory": "theory",
    "theories": "theory",
    "discovery": "discovery",
    "discoveries": "discovery",
    "dead-end": "dead_end",
    "dead_end": "dead_end",
    "dead-ends": "dead_end",
    "dead_ends": "dead_end",
    "parameter": "parameter",
    "parameters": "parameter",
    "pairwise-separation": "pairwise_separation",
    "pairwise_separation": "pairwise_separation",
    "pairwise-separations": "pairwise_separation",
    "pairwise_separations": "pairwise_separation",
    "summary": "session_summary",
    "session-summary": "session_summary",
}


@dataclass(frozen=True)
class _ResourceSpec:
    collection_attr: str
    register_method: str
    update_method: str
    transition_method: str | None = None


@dataclass(frozen=True)
class _QuerySpec:
    method_name: str
    parameter_resources: dict[str, str]


_RESOURCE_SPECS: dict[str, _ResourceSpec] = {
    "claim": _ResourceSpec("claims", "register_claim", "update_claim", "transition_claim"),
    "assumption": _ResourceSpec("assumptions", "register_assumption", "update_assumption"),
    "prediction": _ResourceSpec("predictions", "register_prediction", "update_prediction", "transition_prediction"),
    "analysis": _ResourceSpec("analyses", "register_analysis", "update_analysis"),
    "theory": _ResourceSpec("theories", "register_theory", "update_theory", "transition_theory"),
    "discovery": _ResourceSpec("discoveries", "register_discovery", "update_discovery", "transition_discovery"),
    "dead_end": _ResourceSpec("dead_ends", "register_dead_end", "update_dead_end", "transition_dead_end"),
    "parameter": _ResourceSpec("parameters", "register_parameter", "update_parameter"),
    "independence_group": _ResourceSpec("independence_groups", "register_independence_group", "update_independence_group"),
    "pairwise_separation": _ResourceSpec("pairwise_separations", "add_pairwise_separation", "update_pairwise_separation"),
}


_QUERY_SPECS: dict[str, _QuerySpec] = {
    "claim_lineage": _QuerySpec("claim_lineage", {"cid": "claim"}),
    "assumption_lineage": _QuerySpec("assumption_lineage", {"cid": "claim"}),
    "prediction_implicit_assumptions": _QuerySpec(
        "prediction_implicit_assumptions",
        {"pid": "prediction"},
    ),
    "refutation_impact": _QuerySpec("refutation_impact", {"pid": "prediction"}),
    "assumption_support_status": _QuerySpec(
        "assumption_support_status",
        {"aid": "assumption"},
    ),
    "predictions_depending_on_claim": _QuerySpec(
        "predictions_depending_on_claim",
        {"cid": "claim"},
    ),
    "parameter_impact": _QuerySpec("parameter_impact", {"pid": "parameter"}),
}


@dataclass
class GatewayResult:
    """Stable result envelope returned by every gateway operation.

    Consumed by both MCP tool handlers and CLI formatters.

    status:         "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run"
    changed:        True if the persistent state was modified.
    message:        Human-readable summary.
    findings:       Validation findings (may be empty).
    transaction_id: Set for mutations; None for read-only operations.
    data:           Resource payload for get/list/query results.
    """
    status: str
    changed: bool
    message: str
    findings: list[Finding] = field(default_factory=list)
    transaction_id: str | None = None
    data: dict | None = None


class Gateway:
    """Single mutation/query boundary for the control plane.

    Owns the epistemic web in memory for the lifetime of a session.
    Every public method returns a ``GatewayResult`` and never raises.
    Persistence is the caller's responsibility (``DeSitterClient.save()``).
    """

    def __init__(
        self,
        web: EpistemicWebPort,
        validator: WebValidator,
        payload_validator: PayloadValidator | None = None,
    ) -> None:
        """Initialize a gateway with an in-memory epistemic web.

        Args:
            web: Initial epistemic web. Use ``EpistemicWeb()`` for a new
                in-memory session or a pre-loaded web for a persistent one.
            validator: Domain validation service (invariant checks).
            payload_validator: Optional schema validator for incoming
                payloads. If ``None``, schema validation is skipped.
        """
        raise NotImplementedError

    @property
    def web(self) -> EpistemicWebPort:
        """The current in-memory epistemic web."""
        raise NotImplementedError

    def resolve_resource(self, alias: str) -> str:
        """Resolve a plural/hyphenated resource alias to its canonical key.

        Args:
            alias: User-supplied resource name (e.g. ``"claims"``
                or ``"dead-end"``).

        Returns:
            str: Canonical key (e.g. ``"claim"`` or ``"dead_end"``).

        Raises:
            KeyError: If the alias is not in ``GATEWAY_RESOURCE_ALIASES``.
        """
        raise NotImplementedError

    def register(
        self,
        resource: str,
        payload: dict,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Register a new resource entity.

        Validates payload, builds entity, registers on the in-memory web,
        enforces domain invariants. Updates ``self._web`` on success.

        Args:
            resource: Resource alias or canonical key.
            payload: Entity attributes as a raw dict.
            dry_run: If ``True``, validate without mutating the web.

        Returns:
            GatewayResult: ``"ok"`` on success, ``"BLOCKED"`` on invariant
                failure, ``"error"`` on bad input.
        """
        raise NotImplementedError

    def get(self, resource: str, identifier: str) -> GatewayResult:
        """Retrieve a single resource entity by ID.

        Args:
            resource: Resource alias or canonical key.
            identifier: String form of the entity's ID.

        Returns:
            GatewayResult: ``data["resource"]`` is the serialized entity
                on success, or ``status="error"`` if not found.
        """
        raise NotImplementedError

    def list(self, resource: str, **filters: object) -> GatewayResult:
        """List all entities of a resource type, optionally filtered.

        Entities are sorted by ID for deterministic output. Filters use
        list-contains, dict-subset, or scalar-equality semantics.

        Args:
            resource: Resource alias or canonical key.
            **filters: Field-value pairs to match.

        Returns:
            GatewayResult: ``data["items"]`` is the matching entity list;
                ``data["count"]`` is the total.
        """
        raise NotImplementedError

    def set(
        self,
        resource: str,
        identifier: str,
        payload: dict,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Update fields on an existing resource entity.

        Merges ``payload`` onto the existing serialized entity, validates
        the merged result, and updates the in-memory web on success.

        Args:
            resource: Resource alias or canonical key.
            identifier: String form of the entity's ID.
            payload: Partial entity attributes to apply.
            dry_run: If ``True``, validate without mutating the web.

        Returns:
            GatewayResult: ``"ok"`` on success, ``"BLOCKED"`` on invariant
                failure, ``"error"`` on bad input.
        """
        raise NotImplementedError

    def transition(
        self,
        resource: str,
        identifier: str,
        new_status: str,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Transition a resource entity to a new status.

        Args:
            resource: Resource alias or canonical key.
            identifier: String form of the entity's ID.
            new_status: Target status value (matched against the
                resource's status enum).
            dry_run: If ``True``, validate without mutating the web.

        Returns:
            GatewayResult: ``"ok"`` on success, ``"error"`` if the
                resource does not support transitions.
        """
        raise NotImplementedError

    def query(self, query_type: str, **params: object) -> GatewayResult:
        """Run a named read-only query across the epistemic web.

        Args:
            query_type: One of the keys in ``_QUERY_SPECS``.
            **params: Named query parameters matching the spec.

        Returns:
            GatewayResult: ``data`` holds the serialized query result.
                ``status="error"`` if query type is unknown.
        """
        raise NotImplementedError

    # ── Private helpers ───────────────────────────────────────────

    def _resource_spec(self, resource: str) -> _ResourceSpec:
        """Look up the _ResourceSpec for a canonical resource key.

        Raises:
            KeyError: If the resource is not in ``_RESOURCE_SPECS``.
        """
        raise NotImplementedError

    def _typed_identifier(self, resource: str, identifier: str) -> object:
        """Coerce a string identifier to the resource's typed ID newtype."""
        raise NotImplementedError

    def _lookup_entity(self, resource: str, identifier: str) -> object | None:
        """Find an entity in the in-memory web by resource key and string ID.

        Returns ``None`` if the entity does not exist.
        """
        raise NotImplementedError

    def _validate_payload(
        self,
        resource: str,
        payload: dict[str, object],
    ) -> list[Finding]:
        """Run schema validation if a PayloadValidator is configured."""
        raise NotImplementedError

    def _finalize_mutation(
        self,
        *,
        operation: str,
        resource: str,
        identifier: str,
        new_web: EpistemicWebPort,
        dry_run: bool,
        message: str,
    ) -> GatewayResult:
        """Enforce invariants and, if clean, commit the new web to memory.

        If any CRITICAL findings are produced, returns ``BLOCKED`` without
        updating ``self._web``. If ``dry_run`` is ``True``, validates but
        does not update ``self._web``. Otherwise sets ``self._web = new_web``.

        Persistence (``repo.save()``) is NOT called here — that belongs
        to ``DeSitterClient.save()``.
        """
        raise NotImplementedError

    def _matches_filters(
        self,
        item: dict[str, object],
        filters: dict[str, object],
    ) -> bool:
        """Test whether a serialized entity dict matches all filter predicates."""
        raise NotImplementedError

    def _error_result(
        self,
        message: str,
        *,
        findings: list[Finding] | None = None,
    ) -> GatewayResult:
        """Construct an error GatewayResult."""
        raise NotImplementedError

