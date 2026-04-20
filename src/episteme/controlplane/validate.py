"""Read-only validation orchestration.

Composes validators over an already-loaded epistemic web and returns a
unified finding list.

Concrete deployment checks belong to the adapter that owns that
deployment, not to this generic control-plane module.
"""
from __future__ import annotations

from ..epistemic.invariants import validate_all
from ..epistemic.ports import EpistemicWebPort, WebValidator
from ..epistemic.types import Finding


class DomainValidator:
    """``WebValidator`` implementation that runs all domain invariants.

    Delegates to ``epistemic.invariants.validate_all`` which runs the
    full suite of semantic and coverage invariant checks on the web.
    """

    def validate(self, web: EpistemicWebPort) -> list[Finding]:
        """Run all epistemic invariants and return findings.

        Args:
            web: The epistemic web to validate.

        Returns:
            list[Finding]: All findings from all invariant validators,
                ordered by the fixed validator execution order.
        """
        return validate_all(web)


def validate_project(
    web: EpistemicWebPort,
    extra_validators: list[WebValidator] | None = None,
) -> list[Finding]:
    """Run all validators on an epistemic web.

    Composes domain invariant validation (via DomainValidator) with any
    additional validators injected by the caller. Returns the combined
    finding list.

    Responsibility: validation only. Loading the web is the caller's
    responsibility via a WebRepository adapter.

    Args:
        web: The epistemic web to validate.
        extra_validators: Additional validator instances to run after
            the default domain validators. May be ``None``.

    Returns:
        list[Finding]: Combined findings from all validators.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
