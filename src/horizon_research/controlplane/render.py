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
from .context import ProjectContext


def compute_fingerprint(web: EpistemicWeb) -> str:
    """Compute a SHA-256 fingerprint of the web's serialisable state.

    Used to decide whether re-rendering is needed.
    """
    raise NotImplementedError


def load_render_cache(context: ProjectContext) -> dict[str, str]:
    """Load the {surface_name: last_fingerprint} cache from disk.

    Returns an empty dict if the cache file doesn't exist.
    """
    raise NotImplementedError


def save_render_cache(context: ProjectContext, cache: dict[str, str]) -> None:
    """Persist the render cache to disk."""
    raise NotImplementedError


def render_all(
    context: ProjectContext,
    web: EpistemicWeb,
    renderer: WebRenderer,
    *,
    force: bool = False,
) -> dict[str, bool]:
    """Render all surfaces, skipping unchanged ones unless force=True.

    Returns {surface_name: was_written} for each surface.
    """
    raise NotImplementedError
