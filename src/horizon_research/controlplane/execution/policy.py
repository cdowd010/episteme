"""Execution policy normalization.

Defines what constraints apply when running a verification script:
sandboxing, network access, timeouts, environment variables.

Scripts declare their requirements (requires_sandbox, requires_network).
The policy layer enforces organizational defaults on top of those.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...epistemic.model import Script


@dataclass
class ExecutionPolicy:
    """Resolved execution constraints for a single script run.

    sandbox_required:   Whether to run inside the sandbox executor.
    network_allowed:    Whether the script may make network calls.
    timeout_seconds:    Maximum wall-clock time for the script.
    env:                Extra environment variables to inject.
    """
    sandbox_required: bool = True
    network_allowed: bool = False
    timeout_seconds: int = 300
    env: dict[str, str] | None = None


DEFAULT_POLICY = ExecutionPolicy()


def resolve_policy(
    script: Script,
    override: ExecutionPolicy | None = None,
) -> ExecutionPolicy:
    """Merge script-declared requirements with any caller override.

    Script requirements take precedence over defaults but can be
    further constrained (never relaxed) by override.
    """
    raise NotImplementedError
