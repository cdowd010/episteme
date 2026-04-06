"""Bulk export orchestration.

Produces self-contained exports of the epistemic web via a pluggable
``WebExporter`` and ``ArtifactSink``. Exports are point-in-time
snapshots — they do not affect canonical state.
"""
from __future__ import annotations

from ..epistemic.ports import ArtifactSink, EpistemicWebPort, WebExporter


def export(
    web: EpistemicWebPort,
    exporter: WebExporter,
    sink: ArtifactSink,
) -> None:
    """Export the web using the provided exporter.

    Delegates artifact production to *exporter* and delivery to *sink*.

    Args:
        web: The epistemic web to export.
        exporter: A ``WebExporter`` implementation that produces export
            artifacts.
        sink: An ``ArtifactSink`` implementation that consumes those
            artifacts.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
