"""Client-facing result and error types.

These types define the public client contract independently from the
client orchestration and resource helper surfaces.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ..epistemic.types import Finding


ResultData = TypeVar("ResultData")


@dataclass(frozen=True)
class ClientResult(Generic[ResultData]):
    """Typed wrapper over a gateway result."""

    status: str
    changed: bool
    message: str
    findings: list[Finding] = field(default_factory=list)
    transaction_id: str | None = None
    data: ResultData | None = None


class DeSitterClientError(Exception):
    """Raised when the gateway returns a non-success status."""

    def __init__(
        self,
        status: str,
        message: str,
        findings: list[Finding] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.findings = findings or []


__all__ = ["ClientResult", "DeSitterClientError"]
