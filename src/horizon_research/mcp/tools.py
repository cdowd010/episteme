"""MCP tool handlers — thin wrappers over the control plane.

Every tool here delegates immediately to the Gateway or a read-only
service. No business logic lives in this file.

Result envelopes follow the status-first convention:
  {"status": "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run", ...}

Tool naming convention: <verb>_<resource> or <verb>_<noun>
  register_claim, get_prediction, list_assumptions,
  run_health_check, get_status, run_script, …
"""
from __future__ import annotations

from ..adapters.json_repository import JsonRepository
from ..adapters.markdown_renderer import MarkdownRenderer
from ..adapters.sandbox_executor import SandboxExecutor
from ..adapters.transaction_log import JsonTransactionLog
from ..controlplane.context import ProjectContext
from ..controlplane.gateway import Gateway
from ..controlplane.health import run_health_check
from ..controlplane.status import get_status
from ..controlplane.validate import DomainValidator


def _build_gateway(context: ProjectContext) -> Gateway:
    """Construct a fully wired Gateway from a ProjectContext."""
    repo = JsonRepository(context.paths.data_dir)
    validator = DomainValidator()
    renderer = MarkdownRenderer()
    tx_log = JsonTransactionLog(context.paths.query_transaction_log_file)
    from ..epistemic.ports import ProseSync  # imported for type only
    # prose_sync placeholder — implement in Phase 3
    prose_sync = _NullProseSync()
    return Gateway(context, repo, validator, renderer, prose_sync, tx_log)


class _NullProseSync:
    """No-op ProseSync used until the prose sync adapter is implemented."""

    def sync(self, web):
        return {}


def register_tools(server, context: ProjectContext) -> None:
    """Register all MCP tool handlers on the FastMCP server instance.

    Each handler follows the pattern:
      1. Resolve resource alias
      2. Delegate to gateway or service
      3. Return status-first dict
    """
    gateway = _build_gateway(context)

    @server.tool()
    def register_resource(resource: str, payload: dict, dry_run: bool = False) -> dict:
        """Register a new resource entity in the epistemic web.

        resource: entity type (e.g. "claim", "assumption", "prediction")
        payload:  entity fields as a dict
        dry_run:  if True, validate without writing
        """
        result = gateway.register(resource, payload, dry_run=dry_run)
        return _envelope(result)

    @server.tool()
    def get_resource(resource: str, identifier: str) -> dict:
        """Retrieve a single resource by ID."""
        result = gateway.get(resource, identifier)
        return _envelope(result)

    @server.tool()
    def list_resources(resource: str) -> dict:
        """List all resources of a given type."""
        result = gateway.list(resource)
        return _envelope(result)

    @server.tool()
    def transition_resource(
        resource: str, identifier: str, new_status: str, dry_run: bool = False
    ) -> dict:
        """Transition a resource to a new status."""
        result = gateway.transition(resource, identifier, new_status, dry_run=dry_run)
        return _envelope(result)

    @server.tool()
    def validate_web() -> dict:
        """Run all domain validators and return findings."""
        repo = JsonRepository(context.paths.data_dir)
        validator = DomainValidator()
        from ..controlplane.validate import validate_project
        findings = validate_project(context, repo)
        return {
            "status": "CLEAN" if not any(
                f.severity.name == "CRITICAL" for f in findings
            ) else "BLOCKED",
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in findings
            ],
        }

    @server.tool()
    def health_check() -> dict:
        """Run all health checks and return a structured report."""
        repo = JsonRepository(context.paths.data_dir)
        validator = DomainValidator()
        report = run_health_check(context, repo, validator)
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
        repo = JsonRepository(context.paths.data_dir)
        from ..controlplane.status import format_status_dict
        status = get_status(context, repo)
        return {"status": "ok", "data": format_status_dict(status)}


def _envelope(result) -> dict:
    """Convert a GatewayResult to a status-first MCP response dict."""
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
