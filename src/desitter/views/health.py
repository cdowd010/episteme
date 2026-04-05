"""Health checks for the project.

Composes domain validation, analysis-staleness checks, and reference
integrity checks into a single health report. Intended as the primary
"is everything OK?" command for both MCP tools and the CLI.

Returns a structured report rather than raw findings, so callers can
make automated pass/fail decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.ports import WebRepository, WebValidator
from ..epistemic.types import Finding, Severity
from ..config import ProjectContext


@dataclass
class HealthReport:
    """Structured health report for a project.

    overall:  "HEALTHY" | "WARNINGS" | "CRITICAL"
    findings: All findings from all checks, sorted by severity.
    """
    overall: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        """Count CRITICAL findings in the aggregated report."""
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        """Count WARNING findings in the aggregated report."""
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)


def run_health_check(
    context: ProjectContext,
    repo: WebRepository,
    validator: WebValidator,
) -> HealthReport:
    """Run all health checks and return a structured report.

    Checks performed:
      1. Domain invariant validation (epistemic/invariants.py)
            2. Analysis staleness after parameter changes (controlplane/check.py)
            3. Cross-reference integrity (controlplane/check.py)
    """
    raise NotImplementedError
