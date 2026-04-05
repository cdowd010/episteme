"""Generated view surfaces with incremental SHA-256 caching.

Renders the epistemic web into human-readable files (markdown tables,
summary views, etc.). Only re-renders surfaces whose input fingerprint
has changed since the last run.

Does NOT mutate the epistemic web.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..epistemic.ports import WebRenderer
from ..epistemic.web import EpistemicWeb
from ..config import ProjectContext


def compute_fingerprint(web: EpistemicWeb) -> str:
    """Compute a SHA-256 fingerprint of the web's serializable state.

    Used by ``render_all`` to decide whether re-rendering is needed.
    The fingerprint changes when any entity in the web is added,
    removed, or modified.

    Args:
        web: The epistemic web to fingerprint.

    Returns:
        str: A hex-encoded SHA-256 digest.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def load_render_cache(context: ProjectContext) -> dict[str, str]:
    """Load the ``{surface_name: last_fingerprint}`` cache from disk.

    Args:
        context: Project paths (determines cache file location).

    Returns:
        dict[str, str]: The cached fingerprints. Returns an empty dict
            if the cache file does not exist.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def save_render_cache(context: ProjectContext, cache: dict[str, str]) -> None:
    """Persist the render cache to disk.

    Args:
        context: Project paths (determines cache file location).
        cache: The ``{surface_name: fingerprint}`` mapping to persist.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def render_all(
    context: ProjectContext,
    web: EpistemicWeb,
    renderer: WebRenderer,
    *,
    force: bool = False,
) -> dict[str, bool]:
    """Render all surfaces, skipping unchanged ones unless ``force=True``.

    Computes the web's fingerprint, compares it against the cached
    fingerprint for each surface, and only re-renders surfaces whose
    input has changed. Updates the cache after rendering.

    Args:
        context: Project paths and runtime configuration.
        web: The epistemic web to render.
        renderer: The view renderer that produces markdown surfaces.
        force: If ``True``, re-render all surfaces regardless of cache.

    Returns:
        dict[str, bool]: ``{surface_name: was_written}`` for each surface.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
