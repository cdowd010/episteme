"""Adversarial integrity checks on script output.

Meta-verification asks: "Even if the script passed, is the result
trustworthy?" Checks include:

  - Benchmark output parseable and within plausible range
  - No suspicious file modifications outside the sandbox
  - Script exit code matches declared expectations
  - Machine-readable output schema validates

These are run after a script completes, before its result is accepted.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...epistemic.types import Finding, Severity
from .scripts import ScriptRunResult


@dataclass
class MetaVerifyResult:
    """Outcome of post-run integrity checks.

    passed:   True if all checks passed.
    findings: Individual findings from each check.
    """
    passed: bool
    findings: list[Finding]


def check_benchmark_output(result: ScriptRunResult) -> list[Finding]:
    """Validate machine-readable benchmark output schema and value ranges.

    Returns findings for any anomalies.
    """
    raise NotImplementedError


def check_exit_code_consistency(result: ScriptRunResult) -> list[Finding]:
    """Verify that exit code is consistent with stdout/stderr content.

    A zero exit with "ERROR" in stdout is suspicious.
    """
    raise NotImplementedError


def run_meta_verify(result: ScriptRunResult) -> MetaVerifyResult:
    """Run all post-run integrity checks on a script result."""
    findings: list[Finding] = []
    findings.extend(check_benchmark_output(result))
    findings.extend(check_exit_code_consistency(result))
    passed = not any(f.severity == Severity.CRITICAL for f in findings)
    return MetaVerifyResult(passed=passed, findings=findings)
