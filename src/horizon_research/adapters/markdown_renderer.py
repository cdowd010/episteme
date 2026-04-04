"""Markdown renderer: implements WebRenderer.

Generates human-readable markdown surfaces from the epistemic web.
All rendering is pure transformation: web → {path: content}. No disk I/O.
The caller (controlplane/render.py) decides what to write where.

Implements the WebRenderer protocol from epistemic/ports.py.
"""
from __future__ import annotations

from ..epistemic.web import EpistemicWeb


class MarkdownRenderer:
    """Renders an EpistemicWeb to a dict of {relative_path: markdown_content}."""

    def render(self, web: EpistemicWeb) -> dict[str, str]:
        """Generate all markdown surfaces for the given web.

        Returns a dict mapping relative output paths to their content.
        Callers write these to disk; this method is pure.
        """
        surfaces: dict[str, str] = {}
        surfaces.update(self._render_claims(web))
        surfaces.update(self._render_predictions(web))
        surfaces.update(self._render_assumptions(web))
        surfaces.update(self._render_summary(web))
        return surfaces

    def _render_claims(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the claims registry as a markdown table."""
        raise NotImplementedError

    def _render_predictions(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the predictions table, grouped by independence group and tier."""
        raise NotImplementedError

    def _render_assumptions(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the assumptions registry with falsifiable-consequence column."""
        raise NotImplementedError

    def _render_summary(self, web: EpistemicWeb) -> dict[str, str]:
        """Render a top-level summary view with counts and health indicators."""
        raise NotImplementedError
