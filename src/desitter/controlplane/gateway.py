"""The single mutation/query boundary for the control plane.

Both the MCP server and the CLI route all operations through the Gateway.
There is no MCP-specific or CLI-specific business logic — the Gateway is
the one implementation.

Responsibilities:
  - Resource-oriented register/get/list/set/transition/query operations
  - Payload parsing and normalization
  - Resource alias resolution (plural/hyphenated → canonical keys)
  - Dry-run semantics
    - Transaction orchestration (validate after mutation, persist only on success)
  - Provenance logging via TransactionLog

Not responsible for:
  - Storing canonical domain rules in untyped dicts
  - Mutating module globals
  - Owning validation rules themselves
  - Formatting human CLI output
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..epistemic.codec import (
    build_entity,
    entity_id_type,
    entity_to_dict,
    normalize_payload,
    serialize_value,
    status_enum_type,
)
from ..epistemic.ports import (
    PayloadValidator,
    ProseSync,
    TransactionLog,
    WebRepository,
    WebRenderer,
    WebValidator,
)
from ..epistemic.types import Finding, Severity
from ..epistemic.web import EpistemicError
from ..config import ProjectContext


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
    """Internal descriptor linking a canonical resource key to its EpistemicWeb wiring.

    Attributes:
        collection_attr: Name of the dictionary attribute on ``EpistemicWeb``
            (e.g. ``"claims"``).
        register_method: Name of the ``EpistemicWeb`` method used to add a
            new entity of this type (e.g. ``"register_claim"``).
        update_method: Name of the ``EpistemicWeb`` method used to update an
            existing entity (e.g. ``"update_claim"``).
        transition_method: Name of the ``EpistemicWeb`` method used to transition
            an entity's status, or ``None`` if the resource does not support
            status transitions.
    """
    collection_attr: str
    register_method: str
    update_method: str
    transition_method: str | None = None


@dataclass(frozen=True)
class _QuerySpec:
    """Internal descriptor linking a named query to its EpistemicWeb method.

    Attributes:
        method_name: Name of the ``EpistemicWeb`` method to invoke.
        parameter_resources: Mapping of query parameter names to their
            canonical resource keys, used to coerce string identifiers
            into typed ID values.
    """
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
"""Registry of resource specs keyed by canonical resource name.

Each entry maps a resource to its collection attribute and mutation
methods on ``EpistemicWeb``.  Adding a new entity type requires one
entry here plus a corresponding ``GATEWAY_RESOURCE_ALIASES`` entry.
"""


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
"""Supported named queries and their parameter-to-resource mappings.

Each key is a query name accepted by ``Gateway.query()``. The spec
declares which ``EpistemicWeb`` method to invoke and how to coerce
string arguments into typed identifier values.
"""


@dataclass
class GatewayResult:
    """Stable result envelope returned by every gateway operation.

    Consumed by both MCP tool handlers and CLI formatters. The uniform
    shape allows callers to handle success and error cases consistently
    without inspecting exception types.

    Attributes:
        status: One of ``"ok"``, ``"error"``, ``"CLEAN"``, ``"BLOCKED"``,
            or ``"dry_run"``.  ``"BLOCKED"`` means validation produced
            CRITICAL findings that prevented persistence.
        changed: ``True`` if the persistent state was modified on disk.
        message: Human-readable summary of the operation outcome.
        findings: Validation findings collected during the operation.
            May be empty for read-only operations.
        transaction_id: UUID4 transaction log identifier. Set for
            persisted mutations; ``None`` for read-only or dry-run ops.
        data: Resource payload for get/list/query results. ``None``
            when no entity data is returned.
    """
    status: str
    changed: bool
    message: str
    findings: list[Finding] = field(default_factory=list)
    transaction_id: str | None = None
    data: dict | None = None


class Gateway:
    """Single mutation/query boundary for the control plane.

    Both the MCP server and the CLI route all operations through this
    class. There is no MCP-specific or CLI-specific business logic.

    The Gateway is responsible for:

    - Resource-oriented CRUD: ``register``, ``get``, ``list``, ``set``,
      ``transition``, ``query``.
    - Payload normalization and schema validation via a
      ``PayloadValidator``.
    - Resource alias resolution (plural/hyphenated forms to canonical keys).
    - Dry-run semantics (validate without persisting).
    - Post-mutation validation: mutations are rolled back if CRITICAL
      invariant violations are detected.
    - Provenance logging via ``TransactionLog``.

    Every public method returns a ``GatewayResult`` and never raises.
    """

    def __init__(
        self,
        context: ProjectContext,
        repo: WebRepository,
        validator: WebValidator,
        renderer: WebRenderer,
        prose_sync: ProseSync,
        tx_log: TransactionLog,
        payload_validator: PayloadValidator | None = None,
    ) -> None:
        """Initialize a fully wired gateway service boundary.

        Args:
            context: Project paths and runtime configuration.
            repo: Persistence adapter for loading/saving the web.
            validator: Domain validation service.
            renderer: View renderer for markdown outputs.
            prose_sync: Adapter that synchronizes prose artifacts.
            tx_log: Provenance logger for operations.
        """
        self._context = context
        self._repo = repo
        self._validator = validator
        self._renderer = renderer
        self._prose_sync = prose_sync
        self._tx_log = tx_log
        self._payload_validator = payload_validator

    @property
    def repo(self) -> WebRepository:
        """Read-only access to repository dependency for read services."""
        return self._repo

    @property
    def validator(self) -> WebValidator:
        """Read-only access to validator dependency for health/report services."""
        return self._validator

    @property
    def renderer(self) -> WebRenderer:
        """Read-only access to renderer dependency for view generation services."""
        return self._renderer

    def resolve_resource(self, alias: str) -> str:
        """Resolve a resource alias to its canonical key.

        Handles plural forms (``"claims"`` → ``"claim"``), hyphenated
        forms (``"dead-end"`` → ``"dead_end"``), and identity mappings.

        Args:
            alias: User-supplied resource name.

        Returns:
            str: The canonical resource key.

        Raises:
            KeyError: If the alias is not in ``GATEWAY_RESOURCE_ALIASES``.
        """
        key = GATEWAY_RESOURCE_ALIASES.get(alias)
        if key is None:
            raise KeyError(f"Unknown resource type: {alias!r}")
        return key

    def register(
        self,
        resource: str,
        payload: dict,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Register a new resource entity.

        Normalizes the payload, validates it against the entity's JSON Schema,
        builds a typed entity, registers it on the web, runs post-mutation
        validation, and persists only if no CRITICAL findings are raised.

        Args:
            resource: Resource alias or canonical key.
            payload: Entity attributes as a raw dict.
            dry_run: If ``True``, validate but do not persist.

        Returns:
            GatewayResult: Status ``"ok"`` on success, ``"BLOCKED"`` if
                validation fails, ``"error"`` for bad input.
        """
        try:
            canonical = self.resolve_resource(resource)
            spec = self._resource_spec(canonical)
        except KeyError as exc:
            return self._error_result(str(exc))

        normalized_payload = normalize_payload(payload)
        payload_findings = self._validate_payload(canonical, normalized_payload)
        if payload_findings:
            return self._error_result(
                "Payload validation failed",
                findings=payload_findings,
            )

        try:
            entity = build_entity(canonical, normalized_payload)
            web = self._repo.load()
            new_web = getattr(web, spec.register_method)(entity)
            identifier = str(getattr(entity, "id"))
        except (EpistemicError, TypeError, ValueError) as exc:
            return self._error_result(str(exc))

        return self._finalize_mutation(
            operation="register",
            resource=canonical,
            identifier=identifier,
            new_web=new_web,
            dry_run=dry_run,
            message=f"Registered {canonical} {identifier}",
        )

    def get(self, resource: str, identifier: str) -> GatewayResult:
        """Retrieve a single resource entity by ID.

        Args:
            resource: Resource alias or canonical key.
            identifier: The string form of the entity's ID.

        Returns:
            GatewayResult: ``data["resource"]`` contains the serialized entity
                on success, or ``status="error"`` if not found.
        """
        try:
            canonical = self.resolve_resource(resource)
            web = self._repo.load()
            entity = self._lookup_entity(web, canonical, identifier)
        except KeyError as exc:
            return self._error_result(str(exc))

        if entity is None:
            return self._error_result(f"{canonical} {identifier!r} does not exist")

        return GatewayResult(
            status="ok",
            changed=False,
            message=f"Retrieved {canonical} {identifier}",
            data={"resource": entity_to_dict(entity)},
        )

    def list(self, resource: str, **filters: object) -> GatewayResult:
        """List all entities of a resource type, optionally filtered.

        Entities are sorted by ID for deterministic output. Filters are
        matched field-by-field against the serialized entity dict: list
        fields support ``contains`` semantics, dicts support subset
        matching, and scalars use equality.

        Args:
            resource: Resource alias or canonical key.
            **filters: Field-value pairs to match against. Only entities
                matching all filters are returned.

        Returns:
            GatewayResult: ``data["items"]`` contains the list of matching
                entities; ``data["count"]`` contains the count.
        """
        try:
            canonical = self.resolve_resource(resource)
            spec = self._resource_spec(canonical)
            web = self._repo.load()
        except KeyError as exc:
            return self._error_result(str(exc))

        registry = getattr(web, spec.collection_attr)
        items = [
            entity_to_dict(entity)
            for _, entity in sorted(registry.items(), key=lambda item: str(item[0]))
        ]

        if filters:
            items = [
                item for item in items
                if self._matches_filters(item, filters)
            ]

        return GatewayResult(
            status="ok",
            changed=False,
            message=f"Listed {len(items)} {canonical} item(s)",
            data={"items": items, "count": len(items)},
        )

    def set(
        self,
        resource: str,
        identifier: str,
        payload: dict,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Update fields on an existing resource entity.

        Merges the incoming payload onto the existing entity's serialized
        dict, validates the merged result, and persists only if validation
        passes. The payload ``id`` field, if present, must match
        ``identifier``.

        Args:
            resource: Resource alias or canonical key.
            identifier: The string form of the entity's ID.
            payload: Partial entity attributes to apply.
            dry_run: If ``True``, validate but do not persist.

        Returns:
            GatewayResult: Status ``"ok"`` on success, ``"BLOCKED"`` if
                validation fails, ``"error"`` for bad input.
        """
        try:
            canonical = self.resolve_resource(resource)
            spec = self._resource_spec(canonical)
            web = self._repo.load()
        except KeyError as exc:
            return self._error_result(str(exc))

        existing = self._lookup_entity(web, canonical, identifier)
        if existing is None:
            return self._error_result(f"{canonical} {identifier!r} does not exist")

        normalized_payload = normalize_payload(payload)
        incoming_identifier = normalized_payload.get("id")
        if incoming_identifier is not None and incoming_identifier != identifier:
            return self._error_result(
                f"Payload id {incoming_identifier!r} does not match {identifier!r}"
            )

        merged_payload = entity_to_dict(existing)
        merged_payload.update(normalized_payload)

        payload_findings = self._validate_payload(canonical, merged_payload)
        if payload_findings:
            return self._error_result(
                "Payload validation failed",
                findings=payload_findings,
            )

        try:
            entity = build_entity(canonical, merged_payload)
            new_web = getattr(web, spec.update_method)(entity)
        except (EpistemicError, TypeError, ValueError) as exc:
            return self._error_result(str(exc))

        return self._finalize_mutation(
            operation="set",
            resource=canonical,
            identifier=identifier,
            new_web=new_web,
            dry_run=dry_run,
            message=f"Updated {canonical} {identifier}",
        )

    def transition(
        self,
        resource: str,
        identifier: str,
        new_status: str,
        *,
        dry_run: bool = False,
    ) -> GatewayResult:
        """Transition a resource entity to a new status.

        Resolves the target status through the resource's status enum,
        delegates to the web's transition method, and persists only if
        post-mutation validation passes.

        Args:
            resource: Resource alias or canonical key.
            identifier: The string form of the entity's ID.
            new_status: The target status value (matched against the
                resource's status enum).
            dry_run: If ``True``, validate but do not persist.

        Returns:
            GatewayResult: Status ``"ok"`` on success, ``"error"`` if the
                resource does not support transitions or the status value
                is invalid.
        """
        try:
            canonical = self.resolve_resource(resource)
            spec = self._resource_spec(canonical)
        except KeyError as exc:
            return self._error_result(str(exc))

        if spec.transition_method is None:
            return self._error_result(f"Resource {canonical!r} does not support transition")

        status_enum = status_enum_type(canonical)
        if status_enum is None:
            return self._error_result(f"Resource {canonical!r} does not define a status enum")

        try:
            web = self._repo.load()
            typed_identifier = self._typed_identifier(canonical, identifier)
            target_status = new_status
            if not isinstance(new_status, status_enum):
                target_status = status_enum(new_status)
            new_web = getattr(web, spec.transition_method)(typed_identifier, target_status)
        except (EpistemicError, TypeError, ValueError) as exc:
            return self._error_result(str(exc))

        return self._finalize_mutation(
            operation="transition",
            resource=canonical,
            identifier=identifier,
            new_web=new_web,
            dry_run=dry_run,
            message=(
                f"Transitioned {canonical} {identifier} to {serialize_value(target_status)}"
            ),
        )

    def query(self, query_type: str, **params: object) -> GatewayResult:
        """Run a named read-only query across the epistemic web.

        Validates that exactly the required parameters are provided,
        coerces string identifiers to typed IDs, invokes the
        corresponding ``EpistemicWeb`` method, and serializes the result.

        Args:
            query_type: One of the keys in ``_QUERY_SPECS`` (e.g.
                ``"claim_lineage"``, ``"refutation_impact"``).
            **params: Named query parameters matching the spec's
                ``parameter_resources`` keys.

        Returns:
            GatewayResult: ``data`` contains the serialized query result.
                ``status="error"`` if the query type is unknown or
                parameters are missing/unexpected.
        """
        query_spec = _QUERY_SPECS.get(query_type)
        if query_spec is None:
            return self._error_result(f"Unknown query type: {query_type!r}")

        missing = sorted(set(query_spec.parameter_resources) - set(params))
        if missing:
            return self._error_result(
                f"Missing query parameter(s) for {query_type!r}: {missing}"
            )

        unexpected = sorted(set(params) - set(query_spec.parameter_resources))
        if unexpected:
            return self._error_result(
                f"Unexpected query parameter(s) for {query_type!r}: {unexpected}"
            )

        try:
            web = self._repo.load()
            coerced_params = {
                name: self._typed_identifier(resource_name, str(params[name]))
                for name, resource_name in query_spec.parameter_resources.items()
            }
            result = getattr(web, query_spec.method_name)(**coerced_params)
        except (TypeError, ValueError) as exc:
            return self._error_result(str(exc))

        serialized = serialize_value(result)
        data = serialized if isinstance(serialized, dict) else {"result": serialized}

        return GatewayResult(
            status="ok",
            changed=False,
            message=f"Query {query_type} completed",
            data=data,
        )

    def _resource_spec(self, resource: str) -> _ResourceSpec:
        """Look up the resource spec for a canonical resource key.

        Args:
            resource: Canonical resource key.

        Returns:
            _ResourceSpec: The spec descriptor.

        Raises:
            KeyError: If the resource is not in ``_RESOURCE_SPECS``.
        """
        spec = _RESOURCE_SPECS.get(resource)
        if spec is None:
            raise KeyError(f"Unsupported resource type: {resource!r}")
        return spec

    def _typed_identifier(self, resource: str, identifier: str) -> object:
        """Coerce a string identifier to the resource's typed ID (e.g. ClaimId)."""
        return entity_id_type(resource)(identifier)

    def _lookup_entity(self, web, resource: str, identifier: str) -> object | None:
        """Find an entity in the web's registry by resource key and string ID.

        Returns ``None`` if the entity does not exist.
        """
        spec = self._resource_spec(resource)
        registry = getattr(web, spec.collection_attr)
        return registry.get(self._typed_identifier(resource, identifier))

    def _validate_payload(self, resource: str, payload: dict[str, object]) -> list[Finding]:
        """Run payload schema validation if a validator is configured."""
        if self._payload_validator is None:
            return []
        return self._payload_validator.validate(resource, payload)

    def _finalize_mutation(
        self,
        *,
        operation: str,
        resource: str,
        identifier: str,
        new_web,
        dry_run: bool,
        message: str,
    ) -> GatewayResult:
        """Validate, optionally persist, and log a mutation.

        Runs post-mutation validation on ``new_web``. If any CRITICAL
        findings are present, returns ``BLOCKED`` without persisting.
        If ``dry_run`` is ``True``, returns ``dry_run`` status without
        persisting. Otherwise saves the web, appends a transaction log
        record, and returns ``ok``.

        Args:
            operation: Operation verb (e.g. ``"register"``, ``"set"``).
            resource: Canonical resource key.
            identifier: Entity identifier string.
            new_web: The mutated ``EpistemicWeb`` instance to validate.
            dry_run: Whether to skip persistence.
            message: Human-readable success message.

        Returns:
            GatewayResult: The operation outcome.
        """
        findings = self._validator.validate(new_web)
        critical_findings = [
            finding for finding in findings if finding.severity == Severity.CRITICAL
        ]
        if critical_findings:
            return GatewayResult(
                status="BLOCKED",
                changed=False,
                message="Mutation blocked by validation",
                findings=findings,
            )

        entity = self._lookup_entity(new_web, resource, identifier)
        data = {"resource": entity_to_dict(entity)} if entity is not None else None

        if dry_run:
            return GatewayResult(
                status="dry_run",
                changed=False,
                message=message,
                findings=findings,
                data=data,
            )

        self._repo.save(new_web)
        transaction_id = self._tx_log.append(f"{operation}:{resource}", identifier)
        return GatewayResult(
            status="ok",
            changed=True,
            message=message,
            findings=findings,
            transaction_id=transaction_id,
            data=data,
        )

    def _matches_filters(self, item: dict[str, object], filters: dict[str, object]) -> bool:
        """Test whether a serialized entity dict matches all filter predicates.

        Supports list-contains, dict-subset, and scalar-equality matching.
        """
        for field_name, expected in filters.items():
            actual = item.get(field_name)
            normalized_expected = serialize_value(expected)
            if isinstance(actual, list):
                if isinstance(normalized_expected, list):
                    if not all(expected_item in actual for expected_item in normalized_expected):
                        return False
                    continue
                if normalized_expected not in actual:
                    return False
                continue
            if isinstance(actual, dict) and isinstance(normalized_expected, dict):
                for key, value in normalized_expected.items():
                    if actual.get(key) != value:
                        return False
                continue
            if actual != normalized_expected:
                return False
        return True

    def _error_result(
        self,
        message: str,
        *,
        findings: list[Finding] | None = None,
    ) -> GatewayResult:
        """Construct an error GatewayResult with the given message."""
        return GatewayResult(
            status="error",
            changed=False,
            message=message,
            findings=findings or [],
        )
