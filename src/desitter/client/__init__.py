"""Python client API for deSitter.

This module is the public facade for the Python client surface. Core
client orchestration, typed resource helpers, and result/error types are
kept in narrower private modules.
"""
from __future__ import annotations

from ._core import _DeSitterClientCore
from ._resources import _DeSitterClientResourceHelpers
from ._types import ClientResult, DeSitterClientError
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


__all__ = ["ClientResult", "DeSitterClient", "DeSitterClientError", "connect"]
