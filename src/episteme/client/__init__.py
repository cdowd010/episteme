"""Python client API for Episteme.

This module is the public facade for the Python client surface. Core
client orchestration, typed resource helpers, and result/error types are
kept in narrower private modules.
"""
from __future__ import annotations

from ._client import EpistemeClient, connect
from ._types import ClientResult, EpistemeClientError


__all__ = ["ClientResult", "EpistemeClient", "EpistemeClientError", "connect"]
