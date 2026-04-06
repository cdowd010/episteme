"""Client helper declarations for narrative and registry resources."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from ._types import ClientResult
from ..epistemic.model import DeadEnd, Discovery, Theory
from ..epistemic.types import DeadEndStatus, DiscoveryStatus, TheoryStatus


class _DeSitterClientRegistryHelpers:
    """Typed helpers for theories, discoveries, and dead ends."""

    def register_theory(
        self,
        id: str,
        title: str,
        status: TheoryStatus | str,
        *,
        dry_run: bool = False,
        summary: str | None = None,
        related_claims: Iterable[str] | None = None,
        related_predictions: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[Theory]:
        """Register a theory via the generic client API."""
        raise NotImplementedError

    def register_discovery(
        self,
        id: str,
        title: str,
        date: date | str,
        summary: str,
        impact: str,
        status: DiscoveryStatus | str,
        *,
        dry_run: bool = False,
        related_claims: Iterable[str] | None = None,
        related_predictions: Iterable[str] | None = None,
        references: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[Discovery]:
        """Register a discovery via the generic client API."""
        raise NotImplementedError

    def register_dead_end(
        self,
        id: str,
        title: str,
        description: str,
        status: DeadEndStatus | str,
        *,
        dry_run: bool = False,
        related_predictions: Iterable[str] | None = None,
        related_claims: Iterable[str] | None = None,
        references: Iterable[str] | None = None,
        source: str | None = None,
    ) -> ClientResult[DeadEnd]:
        """Register a dead end via the generic client API."""
        raise NotImplementedError

    def get_theory(self, identifier: str) -> ClientResult[Theory]:
        """Retrieve a theory by ID."""
        raise NotImplementedError

    def get_discovery(self, identifier: str) -> ClientResult[Discovery]:
        """Retrieve a discovery by ID."""
        raise NotImplementedError

    def get_dead_end(self, identifier: str) -> ClientResult[DeadEnd]:
        """Retrieve a dead end by ID."""
        raise NotImplementedError

    def list_theories(self, **filters: object) -> ClientResult[list[Theory]]:
        """List all theories, optionally filtered."""
        raise NotImplementedError

    def list_discoveries(self, **filters: object) -> ClientResult[list[Discovery]]:
        """List all discoveries, optionally filtered."""
        raise NotImplementedError

    def list_dead_ends(self, **filters: object) -> ClientResult[list[DeadEnd]]:
        """List all dead ends, optionally filtered."""
        raise NotImplementedError

    def transition_theory(
        self,
        identifier: str,
        new_status: TheoryStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Theory]:
        """Transition a theory to a new status."""
        raise NotImplementedError

    def transition_discovery(
        self,
        identifier: str,
        new_status: DiscoveryStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[Discovery]:
        """Transition a discovery to a new status."""
        raise NotImplementedError

    def transition_dead_end(
        self,
        identifier: str,
        new_status: DeadEndStatus | str,
        *,
        dry_run: bool = False,
    ) -> ClientResult[DeadEnd]:
        """Transition a dead end to a new status."""
        raise NotImplementedError


__all__ = ["_DeSitterClientRegistryHelpers"]
