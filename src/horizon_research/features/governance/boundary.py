"""Session boundary enforcement.

When governance is enabled, mutations to the epistemic web must occur
within an open session. This module provides the check that the gateway
calls before executing any mutation.

When governance is disabled (the default), all checks pass unconditionally.
"""
from __future__ import annotations

from ...epistemic.types import Finding, Severity
from ...config import ProjectContext
from .session import get_current_session


class SessionBoundaryError(Exception):
    """Raised when a mutation is attempted outside an open session."""


def check_boundary(context: ProjectContext) -> None:
    """Assert that governance allows a mutation right now.

    If governance_enabled is False, this is a no-op.
    Raises SessionBoundaryError if governance is enabled but no session is open.
    """
    if not context.config.governance_enabled:
        return
    session = get_current_session(context.paths.data_dir)
    if session is None:
        raise SessionBoundaryError(
            "Governance is enabled but no session is open. "
            "Run `horizon session open` first."
        )


def boundary_finding(context: ProjectContext) -> Finding | None:
    """Return a CRITICAL finding if boundary check would fail, else None.

    Useful for health checks that want to report boundary violations
    without raising.
    """
    try:
        check_boundary(context)
        return None
    except SessionBoundaryError as exc:
        return Finding(Severity.CRITICAL, "governance/boundary", str(exc))
