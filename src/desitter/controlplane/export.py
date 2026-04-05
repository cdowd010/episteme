"""Bulk export operations.

Produces self-contained exports of the epistemic web in various formats.
Exports are point-in-time snapshots — they do not affect canonical state.
"""
from __future__ import annotations

from pathlib import Path

from ..epistemic.ports import WebRepository
from ..epistemic.web import EpistemicWeb
from ..config import ProjectContext


def export_json(
    context: ProjectContext,
    repo: WebRepository,
    output_path: Path,
    *,
    pretty: bool = True,
) -> None:
    """Export the full epistemic web as a single JSON file.

    Produces a point-in-time snapshot. Useful for archiving, sharing,
    or feeding into external tools. The canonical on-disk state is not
    affected.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.
        output_path: Destination file path for the JSON export.
        pretty: If ``True``, indent the JSON output for readability.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def export_markdown(
    context: ProjectContext,
    repo: WebRepository,
    output_dir: Path,
) -> dict[str, Path]:
    """Export each entity type as a separate markdown file.

    Produces a point-in-time snapshot. The canonical on-disk state is
    not affected.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.
        output_dir: Destination directory for the markdown files.

    Returns:
        dict[str, Path]: Mapping of ``{entity_type: file_path}`` for
            each file written.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
