"""MCP tool handlers — thin wrappers over the client and view services.

Every tool delegates immediately to ``client.gateway`` or a view function.
No business logic lives in this file.

Mutation tools (``register_resource``, ``set_resource``,
``transition_resource``) call ``client.save()`` after a successful
``"ok"`` result so that each MCP call is automatically persisted.

Result envelopes follow the status-first convention:
  {"status": "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run", ...}

Core tool surface:
  register_resource   — register any entity type
  get_resource        — retrieve by ID
  list_resources      — list all of a type
  set_resource        — update fields on an existing entity
  transition_resource — change status
  query_web           — named read-only queries
  validate_web        — run all domain validators         [feature-gated]
  health_check        — composed health report            [feature-gated]
  project_status      — high-level status snapshot        [feature-gated]
  render_views        — regenerate markdown views         [feature-gated]
  check_stale         — identify stale analyses           [feature-gated]
  check_refs          — verify all ID references          [feature-gated]
  export_web          — bulk export (JSON or markdown)    [feature-gated]
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...views.health import run_health_check
from ...views.status import get_status

if TYPE_CHECKING:
    from ...client import DeSitterClient


def register_tools(server, client: "DeSitterClient") -> None:
    """Register all MCP tool handlers on the FastMCP server instance.

    Uses closures over ``client`` so that each tool has access to both
    the gateway (for web operations) and ``client.save()`` (for persistence).

    Mutation tools call ``client.save()`` after every successful ``"ok"``
    result, making each MCP call a self-contained read-modify-persist unit.

    Args:
        server: A ``fastmcp.FastMCP`` server instance.
        client: A fully wired ``DeSitterClient``.
    """
    gateway = client.gateway

    @server.tool()
    def register_resource(resource: str, payload: dict, dry_run: bool = False) -> dict:
        """Register a new entity in the epistemic web.

        resource: entity type — "claim", "assumption", "prediction", "analysis",
                  "theory", "discovery", "dead_end", "parameter",
                  "independence_group"
        payload:  entity fields as a dict
        dry_run:  if True, validate without persisting to disk
        """
        result = gateway.register(resource, payload, dry_run=dry_run)
        if result.status == "ok":
            client.save()
        return _envelope(result)

    @server.tool()
    def get_resource(resource: str, identifier: str) -> dict:
        """Retrieve a single entity by ID."""
        return _envelope(gateway.get(resource, identifier))

    @server.tool()
    def list_resources(resource: str) -> dict:
        """List all entities of a given type."""
        return _envelope(gateway.list(resource))

    @server.tool()
    def set_resource(
        resource: str, identifier: str, payload: dict, dry_run: bool = False
    ) -> dict:
        """Update fields on an existing entity."""
        result = gateway.set(resource, identifier, payload, dry_run=dry_run)
        if result.status == "ok":
            client.save()
        return _envelope(result)

    @server.tool()
    def transition_resource(
        resource: str, identifier: str, new_status: str, dry_run: bool = False
    ) -> dict:
        """Transition an entity to a new status (e.g. PENDING → CONFIRMED)."""
        result = gateway.transition(resource, identifier, new_status, dry_run=dry_run)
        if result.status == "ok":
            client.save()
        return _envelope(result)

    @server.tool()
    def query_web(query_type: str, **params) -> dict:
        """Run a named read-only query across the epistemic web.

        query_type: "claim_lineage", "assumption_lineage",
                    "prediction_implicit_assumptions", "refutation_impact",
                    "assumption_support_status", "predictions_depending_on_claim",
                    "parameter_impact"
        """
        return _envelope(gateway.query(query_type, **params))

    @server.tool()
    def validate_web() -> dict:
        """Run all domain validators and return findings."""
        from ...controlplane.validate import validate_project
        try:
            findings = validate_project(gateway.web)
        except NotImplementedError as exc:
            return _feature_gated("validate_web", exc)
        status = "CLEAN" if not any(
            f.severity.name == "CRITICAL" for f in findings
        ) else "BLOCKED"
        return {
            "status": status,
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in findings
            ],
        }

    @server.tool()
    def health_check() -> dict:
        """Run all health checks and return a structured report.

        overall: "HEALTHY" | "WARNINGS" | "CRITICAL"
        """
        from ...controlplane.validate import DomainValidator
        try:
            validator = DomainValidator()
            report = run_health_check(gateway.web, validator)
        except NotImplementedError as exc:
            return _feature_gated("health_check", exc)
        return {
            "status": report.overall,
            "critical": report.critical_count,
            "warnings": report.warning_count,
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in report.findings
            ],
        }

    @server.tool()
    def project_status() -> dict:
        """Return a high-level project status snapshot."""
        from ...views.status import format_status_dict
        try:
            status = get_status(gateway.web)
            data = format_status_dict(status)
        except NotImplementedError as exc:
            return _feature_gated("project_status", exc)
        return {"status": "ok", "data": data}

    @server.tool()
    def render_views(force: bool = False) -> dict:
        """Regenerate all markdown view surfaces.

        force: if True, re-render even if nothing has changed.
        """
        from ...views.render import render_all
        from ...adapters.markdown_renderer import MarkdownRenderer
        try:
            written_by_surface = render_all(
                gateway.web,
                MarkdownRenderer(),
                force=force,
            )
        except NotImplementedError as exc:
            return _feature_gated("render_views", exc)
        return {
            "status": "ok",
            "changed": any(written_by_surface.values()),
            "message": "Rendered view surfaces",
            "data": {"written_by_surface": written_by_surface},
        }

    @server.tool()
    def check_stale() -> dict:
        """Identify analyses that need review after parameter changes."""
        from ...controlplane.check import check_stale
        try:
            findings = check_stale(gateway.web)
        except NotImplementedError as exc:
            return _feature_gated("check_stale", exc)
        return {
            "status": "ok",
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in findings
            ],
        }

    @server.tool()
    def check_refs() -> dict:
        """Verify all ID cross-references in the epistemic web are intact."""
        from ...controlplane.check import check_refs
        try:
            findings = check_refs(gateway.web)
        except NotImplementedError as exc:
            return _feature_gated("check_refs", exc)
        return {
            "status": "ok",
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in findings
            ],
        }

    @server.tool()
    def export_web(fmt: str = "json", output_path: str | None = None) -> dict:
        """Bulk-export the epistemic web.

        fmt: "json" or "markdown"
        output_path: write to this path; if None, returns an error (path required).
        """
        from pathlib import Path
        from ...controlplane.export import export_json, export_markdown
        if not output_path:
            return _feature_gated("export_web")
        out = Path(output_path)
        try:
            if fmt == "json":
                export_json(gateway.web, out)
            else:
                export_markdown(gateway.web, out)
        except NotImplementedError as exc:
            return _feature_gated("export_web", exc)
        return {"status": "ok", "changed": True, "message": f"Exported as {fmt} to {out}"}


def _feature_gated(tool_name: str, exc: NotImplementedError | None = None) -> dict:
    """Return a stable MCP error envelope for feature-gated tool handlers."""
    detail = str(exc).strip() if exc is not None else ""
    suffix = f" Detail: {detail}" if detail else ""
    return {
        "status": "error",
        "changed": False,
        "message": (
            f"Tool '{tool_name}' is not available yet (feature-gated).{suffix}"
        ),
    }


def _envelope(result) -> dict:
    """Convert a ``GatewayResult`` to a status-first MCP response dict."""
    out: dict = {
        "status": result.status,
        "changed": result.changed,
        "message": result.message,
    }
    if result.findings:
        out["findings"] = [
            {"severity": f.severity.name, "source": f.source, "message": f.message}
            for f in result.findings
        ]
    if result.transaction_id is not None:
        out["transaction_id"] = result.transaction_id
    if result.data is not None:
        out["data"] = result.data
    return out

