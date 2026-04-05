"""JSON Schema payload validation for gateway mutation inputs."""
from __future__ import annotations

from dataclasses import MISSING, fields
from datetime import date
from enum import Enum
import types
from typing import Any, Union, get_args, get_origin, get_type_hints

from jsonschema import Draft202012Validator, FormatChecker

from ..epistemic.codec import ENTITY_TYPES, normalize_payload
from ..epistemic.types import Finding, Severity


class JsonSchemaPayloadValidator:
    """JSON Schema-based payload validator for gateway mutation inputs.

    Derives JSON Schemas from domain dataclass type annotations at
    construction time and validates incoming payloads against them.
    Implements the ``PayloadValidator`` protocol from ``epistemic/ports.py``.

    Schemas are generated with ``Draft202012Validator`` and ``FormatChecker``
    for date format validation. Each entity type gets its own compiled
    validator instance, cached for the lifetime of this object.

    Attributes:
        _validators: Mapping of canonical resource keys to their compiled
            JSON Schema validators.
    """

    def __init__(self) -> None:
        self._validators = {
            resource: Draft202012Validator(
                _schema_for_entity(entity_cls),
                format_checker=FormatChecker(),
            )
            for resource, entity_cls in ENTITY_TYPES.items()
        }

    def validate(self, resource: str, payload: dict[str, object]) -> list[Finding]:
        """Validate a payload against the JSON Schema for the given resource.

        Normalizes the payload before validation. Returns CRITICAL findings
        for each schema violation.

        Args:
            resource: The canonical resource key (e.g. ``"claim"``).
            payload: The payload dictionary to validate.

        Returns:
            list[Finding]: One CRITICAL finding per schema error, or a
                single CRITICAL finding if the resource type is unrecognized.
                Empty list if the payload is valid.
        """
        validator = self._validators.get(resource)
        if validator is None:
            return [
                Finding(
                    Severity.CRITICAL,
                    f"payload/{resource}",
                    f"Unsupported payload resource: {resource!r}",
                )
            ]

        normalized = normalize_payload(payload)
        errors = sorted(validator.iter_errors(normalized), key=lambda error: list(error.path))
        return [
            Finding(
                Severity.CRITICAL,
                f"payload/{resource}",
                _format_error(error),
            )
            for error in errors
        ]


def _schema_for_entity(entity_cls: type[object]) -> dict[str, object]:
    """Generate a JSON Schema object for a domain dataclass.

    Inspects the dataclass fields and their type annotations to build
    a JSON Schema with ``properties``, ``required`` fields, and
    ``additionalProperties: false``.

    Args:
        entity_cls: The dataclass type to generate a schema for.

    Returns:
        dict[str, object]: A JSON Schema dictionary conforming to
            Draft 2020-12.
    """
    type_hints = get_type_hints(entity_cls)
    properties: dict[str, object] = {}
    required: list[str] = []

    for field in fields(entity_cls):
        properties[field.name] = _schema_for_annotation(type_hints[field.name])
        if field.default is MISSING and field.default_factory is MISSING:
            required.append(field.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _schema_for_annotation(annotation: object) -> dict[str, object]:
    """Convert a Python type annotation to a JSON Schema fragment.

    Handles ``Any``, ``None``, ``NewType``, ``Union``/``Optional``,
    ``set``/``frozenset``, ``list``, ``dict``, ``date``, ``Enum``
    subclasses, and primitive types (``str``, ``int``, ``float``,
    ``bool``).

    Args:
        annotation: A Python type annotation to convert.

    Returns:
        dict[str, object]: A JSON Schema fragment describing the type.
            Returns an empty dict ``{}`` for unconstrained types.
    """
    if annotation in (Any, object):
        return {}

    if annotation is type(None):
        return {"type": "null"}

    if hasattr(annotation, "__supertype__"):
        return _schema_for_annotation(annotation.__supertype__)

    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        return {
            "anyOf": [_schema_for_annotation(arg) for arg in get_args(annotation)]
        }

    if origin in (set, frozenset):
        item_schema = _schema_for_annotation(get_args(annotation)[0])
        return {
            "type": "array",
            "items": item_schema,
            "uniqueItems": True,
        }

    if origin is list:
        item_schema = _schema_for_annotation(get_args(annotation)[0])
        return {
            "type": "array",
            "items": item_schema,
        }

    if origin is dict:
        key_type, value_type = get_args(annotation)
        schema: dict[str, object] = {
            "type": "object",
            "additionalProperties": _schema_for_annotation(value_type),
        }
        if key_type in (str, Any, object) or hasattr(key_type, "__supertype__"):
            schema["propertyNames"] = {"type": "string"}
        return schema

    if annotation is date:
        return {"type": "string", "format": "date"}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {
            "type": "string",
            "enum": [member.value for member in annotation],
        }

    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}

    return {}


def _format_error(error) -> str:
    """Format a ``jsonschema`` validation error into a human-readable string.

    Constructs a dotted path from the error's JSON path and appends
    the error message.

    Args:
        error: A ``jsonschema.ValidationError`` instance.

    Returns:
        str: A formatted string like ``"payload.field_name: error message"``.
    """
    location = "payload"
    if error.path:
        location = "payload." + ".".join(str(part) for part in error.path)
    return f"{location}: {error.message}"