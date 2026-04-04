"""Sandbox executor: implements ScriptExecutor.

Runs verification scripts in a controlled subprocess environment:
  - Bounded working directory
  - Controlled environment variables (parameters injected as JSON)
  - Timeout enforcement
  - Optional network isolation (platform-dependent)

Implements the ScriptExecutor protocol from epistemic/ports.py.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..epistemic.ports import ExecutionResult


class SandboxExecutor:
    """Runs scripts in a subprocess with controlled environment and timeout.

    script_dir:    Directory where script files are located.
    parameters:    Dict of parameter constants injected into the script env.
    default_timeout: Wall-clock timeout in seconds (default: 300).
    """

    def __init__(
        self,
        script_dir: Path,
        parameters: dict | None = None,
        default_timeout: int = 300,
    ) -> None:
        self._script_dir = script_dir
        self._parameters = parameters or {}
        self._default_timeout = default_timeout

    def execute(
        self,
        script_id: str,
        command: str,
        **policy: object,
    ) -> ExecutionResult:
        """Run command in the sandbox and return its result.

        policy kwargs:
          timeout_seconds (int): override the default timeout.
          network_allowed (bool): ignored on platforms without network ns.
          env (dict[str, str]): extra environment variables.
        """
        raise NotImplementedError

    def _build_env(self, extra: dict[str, str] | None) -> dict[str, str]:
        """Build the subprocess environment.

        Injects HORIZON_PARAMETERS as a JSON string so scripts can read
        constants without hard-coding them.
        """
        raise NotImplementedError
