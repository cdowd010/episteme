"""Concrete DeSitter client and factory helpers.

This module assembles the final ``DeSitterClient`` class from its mixin
bases and exposes the ``connect`` factory used by callers.
"""
from __future__ import annotations

from ._core import _DeSitterClientCore
from ._resources import _DeSitterClientResourceHelpers
from ..epistemic.ports import EpistemicWebPort, WebRepository


class DeSitterClient(_DeSitterClientResourceHelpers, _DeSitterClientCore):
    """Python client that owns persistence and exposes typed helpers."""


def connect(
    *,
    repo: WebRepository | None = None,
    web: EpistemicWebPort | None = None,
) -> DeSitterClient:
    """Build a ``DeSitterClient``, optionally backed by a repository."""
    raise NotImplementedError


def _without_none(**payload: object) -> dict[str, object]:
    """Return a copy of *payload* with all ``None`` values removed."""
    raise NotImplementedError


__all__ = ["DeSitterClient", "_without_none", "connect"]
