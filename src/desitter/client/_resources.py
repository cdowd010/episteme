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
    """Combined typed helper surface for built-in client resources."""


__all__ = ["_DeSitterClientResourceHelpers"]
