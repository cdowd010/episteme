"""Gateway result types."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..epistemic.types import Finding


@dataclass
class GatewayResult:
    """Stable result envelope returned by every gateway operation."""

    status: str
    changed: bool
    message: str
    findings: list[Finding] = field(default_factory=list)
    transaction_id: str | None = None
    data: Mapping[str, object] | None = None


__all__ = ["GatewayResult"]