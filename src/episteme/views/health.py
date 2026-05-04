"""Health checks for the project.

Composes domain validation into a single structured health report.
The caller passes the already-loaded graph directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.ports import EpistemicGraphPort, GraphValidator
from ..epistemic.types import Finding, Severity


@dataclass
class HealthReport:
    """Structured health report for an epistemic graph.

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
    graph: EpistemicGraphPort,
    validator: GraphValidator,
) -> HealthReport:
    """Run domain invariant validation and return a structured report.

    Findings are sorted CRITICAL first, then WARNING, then INFO.

    Args:
        graph: The in-memory epistemic graph to validate.
        validator: Domain validator to run invariant checks.

    Returns:
        HealthReport: Structured report with overall status and findings.
    """
    findings = validator.validate(graph)

    _severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    findings_sorted = sorted(findings, key=lambda f: _severity_order[f.severity])

    if any(f.severity == Severity.CRITICAL for f in findings_sorted):
        overall = "CRITICAL"
    elif any(f.severity == Severity.WARNING for f in findings_sorted):
        overall = "WARNINGS"
    else:
        overall = "HEALTHY"

    return HealthReport(overall=overall, findings=findings_sorted)

