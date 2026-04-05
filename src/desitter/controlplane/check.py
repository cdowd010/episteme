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

    Uses a file-hash cache to skip unchanged registries.
    """
    raise NotImplementedError


def check_stale(context: ProjectContext) -> list[Finding]:
    """Identify analyses that should be reviewed after parameter changes.

    Reports analyses whose recorded results may be stale because one or more
    referenced parameters changed after the last recorded run. Findings may
    also include directly affected predictions in the same blast radius.
    """
    raise NotImplementedError


def sync_prose(
    context: ProjectContext,
    repo: WebRepository,
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    """Update managed prose blocks derived from canonical state.

    Returns a summary of which blocks were updated.
    """
    raise NotImplementedError


def verify_prose_sync(
    context: ProjectContext,
    repo: WebRepository,
) -> list[Finding]:
    """Assert that all prose blocks are in sync with canonical state.

    Returns findings for any blocks that have drifted.
    """
    raise NotImplementedError
