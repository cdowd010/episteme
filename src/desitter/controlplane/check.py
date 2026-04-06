"""Read-only structural diagnostics.

Pure functions that inspect the epistemic web and return findings without
mutating state or performing I/O. Managed-prose operations (which carry
a filesystem collaborator) live in ``prose.py``.
"""
from __future__ import annotations

from ..epistemic.ports import EpistemicWebPort
from ..epistemic.types import Finding


# ── Diagnostics ──────────────────────────────────────────────────


def check_refs(
    web: EpistemicWebPort,
) -> list[Finding]:
    """Verify all cross-references in the epistemic web are consistent.

    Checks that every ID reference in the web (e.g. ``Claim.assumptions``,
    ``Prediction.claims``) points to an existing entity.

    Args:
        web: The epistemic web to check.

    Returns:
        list[Finding]: Findings for any broken references.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def check_stale(
    web: EpistemicWebPort,
) -> list[Finding]:
    """Identify analyses that should be reviewed after parameter changes.

    Reports analyses whose recorded results may be stale because one or
    more referenced parameters changed after the last recorded run.
    Findings may also include directly affected predictions in the same
    blast radius.

    Args:
        web: The epistemic web to check.

    Returns:
        list[Finding]: WARNING findings for stale analyses and predictions.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


__all__ = ["check_refs", "check_stale"]
