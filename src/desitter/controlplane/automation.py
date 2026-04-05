"""Declarative render/stale-trigger contracts.

Defines which control-plane operations should automatically trigger
downstream effects (e.g., re-rendering views when the web changes,
invalidating caches when a resource is registered).

This module owns no I/O. It describes *what* should happen; the gateway
and render services perform the actual work.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RenderTrigger:
    """Declares that a mutation on a resource should trigger a render pass.

    Attributes:
        resource: The canonical resource key whose mutations trigger rendering
            (e.g. ``"claim"``, ``"prediction"``).
        surfaces: Which render surfaces to invalidate. ``None`` means
            all surfaces are invalidated.
    """
    resource: str
    surfaces: list[str] | None = None


# Default trigger table: any write to these resources invalidates all views.
DEFAULT_RENDER_TRIGGERS: list[RenderTrigger] = [
    RenderTrigger("claim"),
    RenderTrigger("assumption"),
    RenderTrigger("prediction"),
    RenderTrigger("analysis"),
    RenderTrigger("independence_group"),
    RenderTrigger("theory"),
    RenderTrigger("discovery"),
    RenderTrigger("dead_end"),
    RenderTrigger("parameter"),
]
"""Default trigger table: a write to any of these resources invalidates all view surfaces."""


def should_render(resource: str, triggers: list[RenderTrigger] | None = None) -> bool:
    """Return ``True`` if a mutation to *resource* should trigger a render pass.

    Args:
        resource: The canonical resource key to check.
        triggers: Custom trigger table. If ``None``, uses
            ``DEFAULT_RENDER_TRIGGERS``.

    Returns:
        bool: ``True`` if any trigger matches the resource.
    """
    active = triggers if triggers is not None else DEFAULT_RENDER_TRIGGERS
    return any(t.resource == resource for t in active)
