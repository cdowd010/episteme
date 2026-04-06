"""Stable facade for typed client resource helpers.

The helper surface is grouped by resource families so the public client
class can stay stable while the declaration files remain easier to scan.
"""
from __future__ import annotations

from ._hypothesis import _DeSitterClientHypothesisHelpers
from ._registry import _DeSitterClientRegistryHelpers
from ._structure import _DeSitterClientStructureHelpers


class _DeSitterClientResourceHelpers(
    _DeSitterClientHypothesisHelpers,
    _DeSitterClientRegistryHelpers,
    _DeSitterClientStructureHelpers,
):
    """Combined typed helper surface for all built-in client resources.

    Merges the three resource family mixins into one class so that
    ``DeSitterClient`` need only inherit from a single helpers class.
    No new methods are defined here; all implementations live in the
    constituent mixin classes.

    Families:
    - ``_DeSitterClientHypothesisHelpers``: claims, assumptions,
      predictions, analyses.
    - ``_DeSitterClientRegistryHelpers``: theories, discoveries, dead ends.
    - ``_DeSitterClientStructureHelpers``: parameters, independence groups,
      pairwise separations.
    """


__all__ = ["_DeSitterClientResourceHelpers"]
