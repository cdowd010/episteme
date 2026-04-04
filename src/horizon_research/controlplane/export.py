"""Bulk export operations.

Produces self-contained exports of the epistemic web in various formats.
Exports are point-in-time snapshots — they do not affect canonical state.
"""
from __future__ import annotations

from pathlib import Path

from ..epistemic.ports import WebRepository
from ..epistemic.web import EpistemicWeb
from .context import ProjectContext


def export_json(
    context: ProjectContext,
    repo: WebRepository,
    output_path: Path,
    *,
    pretty: bool = True,
) -> None:
    """Export the full epistemic web as a single JSON file.

    Useful for archiving, sharing, or feeding into external tools.
    """
    raise NotImplementedError


def export_markdown(
    context: ProjectContext,
    repo: WebRepository,
    output_dir: Path,
) -> dict[str, Path]:
    """Export each entity type as a separate markdown file.

    Returns {entity_type: file_path} for each file written.
    """
    raise NotImplementedError
