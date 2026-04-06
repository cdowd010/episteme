"""Artifact-oriented export and rendering protocols."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from ._ports_web import EpistemicWebPort


@dataclass(frozen=True)
class Artifact:
    """Portable artifact emitted by a renderer or exporter."""

    name: str
    content: object
    media_type: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


class ArtifactSink(Protocol):
    """Consume artifacts emitted by renderers or exporters."""

    def emit(self, artifacts: Iterable[Artifact]) -> None:
        """Consume a stream of artifacts."""
        ...


class WebExporter(Protocol):
    """Produce portable artifacts from the epistemic web."""

    def export(self, web: EpistemicWebPort) -> Iterable[Artifact]:
        """Serialize the web into a stream of portable artifacts."""
        ...


class WebRenderer(Protocol):
    """Generate human-readable artifacts from the web."""

    def render(self, web: EpistemicWebPort) -> Iterable[Artifact]:
        """Return rendered artifacts ready for an ArtifactSink."""
        ...


__all__ = ["Artifact", "ArtifactSink", "WebExporter", "WebRenderer"]