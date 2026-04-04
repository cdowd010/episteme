"""Close-gate engine.

Validates that a session meets all exit criteria before it can be closed:
  - No CRITICAL findings from domain validation
  - No stale render surfaces
  - All opened failures either resolved or explicitly acknowledged
  - Optional: git commit + tag on clean close

The close gate is intentionally strict. If a session cannot be closed
cleanly, it stays open until the researcher resolves the blockers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ...epistemic.ports import WebRepository, WebValidator
from ...epistemic.types import Finding, Severity
from ..context import ProjectContext
from ..health import run_health_check
from .session import SessionRecord, close_session


@dataclass
class CloseGateResult:
    """Result of attempting to close a session.

    status:   "CLEAN" | "BLOCKED"
    blockers: Findings that prevented a clean close.
    session:  The updated session record (only set if status == "CLEAN").
    """
    status: str
    blockers: list[Finding] = field(default_factory=list)
    session: SessionRecord | None = None


def run_close_gate(
    context: ProjectContext,
    repo: WebRepository,
    validator: WebValidator,
    session_number: int,
    *,
    dry_run: bool = False,
    summary: str | None = None,
    git_publish: bool = False,
) -> CloseGateResult:
    """Validate and close a session if all exit criteria are met.

    If dry_run=True, runs all checks but does not close the session.
    If git_publish=True and status is CLEAN, commits and tags the workspace.
    """
    raise NotImplementedError
