"""Composition root for gateway construction.

``build_gateway`` is the single place that wires a concrete ``EpistemicWeb``
and two abstract dependencies (``WebValidator``, ``PayloadValidator``) into a
``Gateway``. Both MCP tools and the Python client call this function rather
than constructing a ``Gateway`` directly.

Persistence (``WebRepository``) is NOT wired here — it belongs to
``DeSitterClient``, which owns all persistence decisions.
"""
from __future__ import annotations

from ..adapters.payload_validator import JsonSchemaPayloadValidator
from ..epistemic.ports import EpistemicWebPort, PayloadValidator
from ..epistemic.web import EpistemicWeb
from .gateway import Gateway
from .validate import DomainValidator


def build_gateway(
    web: EpistemicWebPort,
    *,
    payload_validator: PayloadValidator | None = None,
) -> Gateway:
    """Construct a ``Gateway`` from an in-memory epistemic web.

    This is the single composition root for gateway construction.
    Callers supply a pre-loaded (or empty) web; the factory injects
    the standard ``DomainValidator`` and ``JsonSchemaPayloadValidator``.

    Args:
        web: The epistemic web the gateway will hold in memory. Pass
            ``EpistemicWeb()`` for a new in-memory session or a web
            loaded from ``JsonRepository.load()`` for a persistent one.
        payload_validator: Optional custom payload validator. If ``None``,
            a default ``JsonSchemaPayloadValidator`` is used.

    Returns:
        Gateway: A ready-to-use gateway owning the given web.
    """
    raise NotImplementedError
