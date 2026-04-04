"""Read-only validation orchestration.

Composes epistemic domain validators with any control-plane checks
(file structure, path integrity, etc.) and returns a unified finding list.

Does NOT write to disk. Does NOT mutate the web.
"""
from __future__ import annotations

from ..epistemic.invariants import validate_all
from ..epistemic.ports import WebRepository, WebValidator
from ..epistemic.types import Finding, Severity
from ..epistemic.web import EpistemicWeb
from .context import ProjectContext


class DomainValidator:
    """WebValidator implementation that runs all domain invariants."""

    def validate(self, web: EpistemicWeb) -> list[Finding]:
        """Run all epistemic invariants and return findings."""
        return validate_all(web)


def validate_project(
    context: ProjectContext,
    repo: WebRepository,
    extra_validators: list[WebValidator] | None = None,
) -> list[Finding]:
    """Load the web from storage and run all validators.

    Returns the combined list of findings across all validators.
    extra_validators allows control-plane callers to inject additional rules.
    """
    raise NotImplementedError


def validate_structure(context: ProjectContext) -> list[Finding]:
    """Check that the expected directory and file structure is present.

    Returns INFO/WARNING/CRITICAL findings for missing paths.
    """
    raise NotImplementedError
