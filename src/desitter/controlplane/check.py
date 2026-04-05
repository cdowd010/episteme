"""Cross-cutting project consistency checks.

Operations:
  check_refs      — verify all ID cross-references in the web are consistent
    check_stale     — identify analyses and dependent predictions made stale by parameter changes
  sync_prose      — update managed prose blocks to match canonical state
  verify_prose_sync — assert that no prose blocks have drifted from canonical state

These are read-only by default. sync_prose is the one write operation.
"""
from __future__ import annotations

from ..epistemic.ports import WebRepository
from ..epistemic.types import Finding
from ..config import ProjectContext


def check_refs(
    context: ProjectContext,
    repo: WebRepository,
    *,
    use_cache: bool = True,
) -> list[Finding]:
    """Verify all cross-references in the epistemic web are consistent.

    Checks that every ID reference in the web (e.g. ``Claim.assumptions``,
    ``Prediction.claims``) points to an existing entity. Uses a
    file-hash cache to skip unchanged registries when ``use_cache``
    is ``True``.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.
        use_cache: If ``True``, skip registries that have not changed
            since the last run.

    Returns:
        list[Finding]: Findings for any broken references.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def check_stale(context: ProjectContext) -> list[Finding]:
    """Identify analyses that should be reviewed after parameter changes.

    Reports analyses whose recorded results may be stale because one or
    more referenced parameters changed after the last recorded run.
    Findings may also include directly affected predictions in the same
    blast radius.

    Args:
        context: Project paths and runtime configuration.

    Returns:
        list[Finding]: WARNING findings for stale analyses and predictions.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def sync_prose(
    context: ProjectContext,
    repo: WebRepository,
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    """Update managed prose blocks derived from canonical state.

    Scans managed markdown files and rewrites blocks that are out of
    sync with the epistemic web.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.
        dry_run: If ``True``, compute changes but do not write to disk.

    Returns:
        dict[str, object]: A summary of which blocks were updated.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def verify_prose_sync(
    context: ProjectContext,
    repo: WebRepository,
) -> list[Finding]:
    """Assert that all managed prose blocks match canonical state.

    A read-only check that reports findings for any prose blocks that
    have drifted from the values the web would generate.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.

    Returns:
        list[Finding]: Findings for any drifted blocks.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
