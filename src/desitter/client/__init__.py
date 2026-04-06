"""Python client API for deSitter.

This module is the public facade for the Python client surface. Core
client orchestration, typed resource helpers, and result/error types are
kept in narrower private modules.
"""
from __future__ import annotations

from ._client import DeSitterClient, connect
from ._types import ClientResult, DeSitterClientError


__all__ = ["ClientResult", "DeSitterClient", "DeSitterClientError", "connect"]
