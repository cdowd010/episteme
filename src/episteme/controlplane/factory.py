"""Composition root for gateway construction.

``build_gateway`` is the single place that wires an epistemic web and
optional abstract dependencies (``WebValidator``, ``PayloadValidator``)
into a ``Gateway``.

Persistence (``WebRepository``) is NOT wired here — it belongs to
``EpistemeClient``, which owns all persistence decisions.
"""
from __future__ import annotations

from ..epistemic.ports import EpistemicWebPort, PayloadValidator
from .gateway import Gateway
from .validate import DomainValidator


def build_gateway(
    web: EpistemicWebPort,
    *,
    payload_validator: PayloadValidator | None = None,
) -> Gateway:
    """Construct a ``Gateway`` around an epistemic-web implementation.

    This is the single composition root for gateway construction.
    Callers supply a pre-loaded (or empty) web and optionally inject
    dependencies. When ``payload_validator`` is ``None``, no payload
    validation is performed before mutations.

    Args:
        web: The epistemic web the gateway will hold.
        payload_validator: Optional payload validator implementation.
            If ``None``, gateway mutations skip schema pre-validation.

    Returns:
        Gateway: A ready-to-use gateway owning the given web.
    """
    raise NotImplementedError
