"""Core client orchestration surface.

This module holds the shared client lifecycle, generic gateway verbs,
and internal result-handling helpers.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from ._types import ClientResult
from ..controlplane.gateway import Gateway, GatewayResult
from ..epistemic.ports import WebRepository


class _DeSitterClientCore:
    """Shared client lifecycle and generic gateway orchestration."""

    def __init__(
        self,
        gateway: Gateway,
        *,
        repo: WebRepository | None = None,
    ) -> None:
        """Initialize a client."""
        raise NotImplementedError

    @property
    def gateway(self) -> Gateway:
        """The gateway instance backing this client."""
        raise NotImplementedError

    def save(self) -> None:
        """Persist the in-memory web through the repository."""
        raise NotImplementedError

    def __enter__(self):
        """Enter the context manager, returning self."""
        raise NotImplementedError

    def __exit__(self, *args: object) -> None:
        """Exit the context manager; calls save()."""
        raise NotImplementedError

    def register(
        self,
        resource: str,
        *,
        dry_run: bool = False,
        **payload: object,
    ) -> ClientResult[Any]:
        """Register a new resource using keyword arguments."""
        raise NotImplementedError

    def get(self, resource: str, identifier: str) -> ClientResult[Any]:
        """Retrieve a single resource by ID."""
        raise NotImplementedError

    def list(self, resource: str, **filters: object) -> ClientResult[list[Any]]:
        """List resources, optionally filtering by keyword arguments."""
        raise NotImplementedError

    def set(
        self,
        resource: str,
        identifier: str,
        *,
        dry_run: bool = False,
        **payload: object,
    ) -> ClientResult[Any]:
        """Update a resource using keyword arguments."""
        raise NotImplementedError

    def transition(
        self,
        resource: str,
        identifier: str,
        new_status: str | Enum,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Any]:
        """Transition a status-bearing resource to a new state."""
        raise NotImplementedError

    def query(self, query_type: str, **params: object) -> ClientResult[Any]:
        """Run a named gateway query."""
        raise NotImplementedError

    def _invoke_gateway(self, func, *args, **kwargs) -> GatewayResult:
        """Call a gateway method, wrapping unexpected errors."""
        raise NotImplementedError

    def _handle_resource_result(
        self,
        resource: str,
        result: GatewayResult,
    ) -> ClientResult[Any]:
        """Convert a gateway result into a typed ClientResult."""
        raise NotImplementedError

    def _handle_resource_list_result(
        self,
        resource: str,
        result: GatewayResult,
    ) -> ClientResult[list[Any]]:
        """Convert a gateway list result into a typed ClientResult."""
        raise NotImplementedError

    def _handle_query_result(self, result: GatewayResult) -> ClientResult[Any]:
        """Convert a gateway query result into a typed ClientResult."""
        raise NotImplementedError

    def _resource_key(self, resource: str) -> str:
        """Validate and return a canonical resource key."""
        raise NotImplementedError


__all__ = ["_DeSitterClientCore"]
