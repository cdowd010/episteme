"""Human and JSON output formatting for CLI commands.

Uses Rich for terminal output (tables, panels, color, progress).
Falls back to plain JSON when --json flag is passed.

No business logic lives here. Formatters receive structured data from
the control plane and render it for human consumption.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...core.gateway import GatewayResult
from ...views.health import HealthReport
from ...views.status import ProjectStatus

console = Console()
error_console = Console(stderr=True)


def print_gateway_result(result: GatewayResult, *, as_json: bool = False) -> None:
    """Print a GatewayResult in human or JSON mode.

    Human mode: Rich panel with status, message, and findings table.
    JSON mode:  Raw JSON to stdout.
    """
    if as_json:
        _print_json(result)
        return
    color = "green" if result.status == "ok" else "red"
    console.print(Panel(result.message, title=f"[{color}]{result.status}[/]"))
    if result.findings:
        _print_findings_table(result.findings)


def print_health_report(report: HealthReport, *, as_json: bool = False) -> None:
    """Print a HealthReport in human or JSON mode."""
    if as_json:
        data = {
            "status": report.overall,
            "critical": report.critical_count,
            "warnings": report.warning_count,
            "findings": [
                {"severity": f.severity.name, "source": f.source, "message": f.message}
                for f in report.findings
            ],
        }
        print(json.dumps(data, indent=2))
        return
    color = {"HEALTHY": "green", "WARNINGS": "yellow", "CRITICAL": "red"}.get(
        report.overall, "white"
    )
    console.print(Panel(
        f"[{color}]{report.overall}[/]  "
        f"critical={report.critical_count}  warnings={report.warning_count}",
        title="Health",
    ))
    if report.findings:
        _print_findings_table(report.findings)


def print_status(status: ProjectStatus, *, as_json: bool = False) -> None:
    """Print a ProjectStatus dashboard in human or JSON mode."""
    if as_json:
        from ...views.status import format_status_dict
        print(json.dumps(format_status_dict(status), indent=2))
        return
    m = status.metrics
    table = Table(title=f"Status — {status.project_name}", show_header=True)
    table.add_column("Resource")
    table.add_column("Count", justify="right")
    table.add_row("Claims", str(m.claim_count))
    table.add_row("Assumptions", str(m.assumption_count))
    table.add_row("Scripts", str(m.script_count))
    table.add_row("Independence Groups", str(m.independence_group_count))
    pm = m.prediction_metrics
    table.add_row("Predictions", str(pm.total))
    table.add_row("  Tier A confirmed", str(pm.tier_a_confirmed))
    console.print(table)


def _print_findings_table(findings) -> None:
    """Render findings as a Rich table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Severity")
    table.add_column("Source")
    table.add_column("Message")
    severity_colors = {"CRITICAL": "red", "WARNING": "yellow", "INFO": "blue"}
    for f in findings:
        color = severity_colors.get(f.severity.name, "white")
        table.add_row(f"[{color}]{f.severity.name}[/]", f.source, f.message)
    console.print(table)


def _print_json(obj: Any) -> None:
    """Serialise obj to JSON and print to stdout."""
    print(json.dumps(obj.__dict__ if hasattr(obj, "__dict__") else obj, indent=2, default=str))
