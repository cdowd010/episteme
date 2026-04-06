"""Service protocols that act on an epistemic web."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ._ports_web import EpistemicWebPort
from .types import Finding


class WebValidator(Protocol):
    """Validate the web and return findings."""

    def validate(self, web: EpistemicWebPort) -> list[Finding]:
        """Run all validation rules and return findings."""
        ...


class ProseSync(Protocol):
    """Update managed prose blocks derived from canonical state."""

    def sync(
        self,
        web: EpistemicWebPort,
        *,
        dry_run: bool = False,
    ) -> dict[str, object]:
        """Sync prose blocks and return a summary of changes."""
        ...

    def verify(self, web: EpistemicWebPort) -> list[Finding]:
        """Report prose blocks that have drifted from canonical state."""
        ...


class TransactionLog(Protocol):
    """Append provenance for gateway mutations and queries."""

    def append(self, operation: str, identifier: str) -> str:
        """Record an operation and return its transaction ID."""
        ...


class PayloadValidator(Protocol):
    """Validate inbound mutation payloads before the gateway mutates the web."""

    def validate(self, resource: str, payload: Mapping[str, object]) -> list[Finding]:
        """Return findings describing payload/schema issues, if any."""
        ...


__all__ = ["PayloadValidator", "ProseSync", "TransactionLog", "WebValidator"]