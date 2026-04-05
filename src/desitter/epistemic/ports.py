"""Abstract interfaces the domain REQUIRES but does not IMPLEMENT.

Implemented by the adapters layer. Domain code programs against these
protocols, never against concrete classes.
"""
from __future__ import annotations

from typing import Protocol

from .types import Finding
from .web import EpistemicWeb


class WebRepository(Protocol):
    """Abstract persistence interface for the epistemic web.

    Implementations handle serialization and storage of the complete
    epistemic web. The domain layer programs against this protocol;
    concrete implementations (e.g. ``JsonRepository``) live in the
    adapters layer.

    Implementations must ensure that a round-trip ``save`` then ``load``
    reconstructs an equivalent ``EpistemicWeb`` with all bidirectional
    links intact.
    """

    def load(self) -> EpistemicWeb:
        """Deserialize and return the full epistemic web from storage.

        Returns:
            EpistemicWeb: A fully hydrated web with all entities and
                their bidirectional links reconstructed.

        Raises:
            TypeError: If stored data has an unexpected structure.
        """
        ...

    def save(self, web: EpistemicWeb) -> None:
        """Serialize and persist the epistemic web to storage.

        Args:
            web: The complete epistemic web to persist. All entities
                in the web are serialized to the backing store.
        """
        ...


class WebRenderer(Protocol):
    """Generate human-readable artifacts from the epistemic web.

    Renderers are pure transformation functions: they take a web and
    produce string content keyed by relative output path. No disk I/O
    occurs in the renderer — the caller decides what to write where.
    """

    def render(self, web: EpistemicWeb) -> dict[str, str]:
        """Render the epistemic web into human-readable surfaces.

        Args:
            web: The epistemic web to render.

        Returns:
            dict[str, str]: A mapping of ``{relative_path: content}``
                for all generated surfaces (e.g. markdown tables,
                summary views).
        """
        ...


class WebValidator(Protocol):
    """Validate the epistemic web and report findings.

    Validators run all domain invariant rules against the web and
    return a list of findings. They are read-only — no mutations.
    """

    def validate(self, web: EpistemicWeb) -> list[Finding]:
        """Run all validation rules against the web.

        Args:
            web: The epistemic web to validate.

        Returns:
            list[Finding]: All findings discovered during validation,
                ordered by validator execution sequence. May include
                INFO, WARNING, and CRITICAL severities.
        """
        ...


class ProseSync(Protocol):
    """Update managed prose blocks derived from canonical state.

    Prose sync adapters maintain human-readable documentation
    (e.g. auto-generated sections in markdown files) that mirror
    the canonical epistemic web state.
    """

    def sync(self, web: EpistemicWeb) -> dict[str, object]:
        """Synchronize prose blocks with the current web state.

        Args:
            web: The epistemic web whose state should be reflected
                in managed prose blocks.

        Returns:
            dict[str, object]: A summary of changes made, keyed by
                block or file identifier.
        """
        ...


class TransactionLog(Protocol):
    """Append provenance records for gateway mutations and queries.

    Every successful mutation through the gateway is recorded with
    a unique transaction ID, enabling audit trails and undo/redo
    reasoning.
    """

    def append(self, operation: str, identifier: str) -> str:
        """Record an operation and return its transaction ID.

        Args:
            operation: A colon-delimited operation descriptor,
                e.g. ``"register:claim"`` or ``"set:parameter"``.
            identifier: The ID of the entity affected by the operation.

        Returns:
            str: A unique transaction ID (typically a UUID4) assigned
                to this provenance record.
        """
        ...


class PayloadValidator(Protocol):
    """Validate inbound mutation payloads before the gateway mutates the web.

    Payload validators run schema-level checks on the raw input dictionaries
    before they are coerced into domain entities. This catches structural
    issues (wrong types, missing required fields, unknown fields) early,
    before the more expensive domain-level validation.
    """

    def validate(self, resource: str, payload: dict[str, object]) -> list[Finding]:
        """Return findings describing payload/schema issues, if any.

        Args:
            resource: The canonical resource key (e.g. ``"claim"``,
                ``"prediction"``).
            payload: The normalized payload dictionary to validate.

        Returns:
            list[Finding]: CRITICAL findings for schema violations.
                An empty list means the payload is structurally valid.
        """
        ...
