"""Health checks for the project.

Composes domain validation into a single structured health report.
Intended as the primary "is everything OK?" surface for MCP tools and the CLI.

The web is always available in memory via ``client.gateway.web`` — health
checks do not need a repository reference; the caller passes the web directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.ports import EpistemicWebPort, WebValidator
from ..epistemic.types import Finding, Severity


@dataclass
class HealthReport:
    """Structured health report for an epistemic web.

    Attributes:
        overall:  ``"HEALTHY"``, ``"WARNINGS"``, or ``"CRITICAL"``.
        findings: All findings, sorted CRITICAL first.
    """
    overall: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        """Count CRITICAL findings."""
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        """Count WARNING findings."""
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)


def run_health_check(
    web: EpistemicWebPort,
    validator: WebValidator,
) -> HealthReport:
    """Run domain invariant validation and return a structured report.

    Args:
        web: The in-memory epistemic web to validate.
        validator: Domain validator to run invariant checks.

    Returns:
        HealthReport: Structured report with overall status and findings.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError

