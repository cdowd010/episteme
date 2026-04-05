"""Markdown renderer: implements WebRenderer.

Generates human-readable markdown surfaces from the epistemic web.
All rendering is pure transformation: web → {path: content}. No disk I/O.
The caller (views/render.py) decides what to write where.

Implements the WebRenderer protocol from epistemic/ports.py.
"""
from __future__ import annotations

from ..epistemic.web import EpistemicWeb


class MarkdownRenderer:
    """Renders an ``EpistemicWeb`` to a dict of ``{relative_path: markdown_content}``.

    All rendering is pure transformation: web → ``{path: content}``. No disk
    I/O occurs here — the caller (``views/render.py``) decides what to write
    where. Implements the ``WebRenderer`` protocol from ``epistemic/ports.py``.
    """

    def render(self, web: EpistemicWeb) -> dict[str, str]:
        """Generate all markdown surfaces for the given web.

        Composes output from claims, predictions, assumptions, and summary
        sub-renderers. Returns a dict mapping relative output paths to
        their markdown content. Callers write these to disk; this method
        is pure with no side effects.

        Args:
            web: The epistemic web to render.

        Returns:
            dict[str, str]: Mapping of ``{relative_path: markdown_content}``.
        """
        surfaces: dict[str, str] = {}
        surfaces.update(self._render_claims(web))
        surfaces.update(self._render_predictions(web))
        surfaces.update(self._render_assumptions(web))
        surfaces.update(self._render_summary(web))
        return surfaces

    def _render_claims(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the claims registry as a markdown table.

        Args:
            web: The epistemic web containing claims to render.

        Returns:
            dict[str, str]: Single-entry dict mapping path to content.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    def _render_predictions(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the predictions table, grouped by independence group and tier.

        Args:
            web: The epistemic web containing predictions to render.

        Returns:
            dict[str, str]: Single-entry dict mapping path to content.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    def _render_assumptions(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the assumptions registry with falsifiable-consequence column.

        Args:
            web: The epistemic web containing assumptions to render.

        Returns:
            dict[str, str]: Single-entry dict mapping path to content.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    def _render_summary(self, web: EpistemicWeb) -> dict[str, str]:
        """Render a top-level summary view with counts and health indicators.

        Args:
            web: The epistemic web to summarize.

        Returns:
            dict[str, str]: Single-entry dict mapping path to content.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError
