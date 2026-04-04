"""Registered script dispatch and result handling.

Looks up a script by ID in the epistemic web, applies the execution
policy, delegates to a ScriptExecutor, and returns a structured result.

Does not implement sandboxing — that lives in adapters/sandbox_executor.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ...epistemic.model import Script
from ...epistemic.ports import ExecutionResult, ScriptExecutor
from ...epistemic.types import ScriptId
from ...epistemic.web import EpistemicWeb
from ..context import ProjectContext
from .policy import ExecutionPolicy


@dataclass
class ScriptRunResult:
    """Structured result of running a verification script.

    script_id:   The script that was run.
    exit_code:   0 = success.
    stdout:      Raw stdout from the script.
    stderr:      Raw stderr from the script.
    passed:      True if exit_code == 0.
    benchmark:   Parsed machine-readable output (if available).
    """
    script_id: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    benchmark: dict | None = None


def run_script(
    script_id: ScriptId,
    web: EpistemicWeb,
    context: ProjectContext,
    executor: ScriptExecutor,
    policy: ExecutionPolicy | None = None,
) -> ScriptRunResult:
    """Look up a script and run it via the executor.

    Applies policy defaults if none are provided.
    Returns a ScriptRunResult with parsed benchmark output if the script
    declares machine_readable_output=True.
    """
    raise NotImplementedError


def run_all_scripts(
    web: EpistemicWeb,
    context: ProjectContext,
    executor: ScriptExecutor,
    policy: ExecutionPolicy | None = None,
) -> list[ScriptRunResult]:
    """Run every registered script in the web.

    Returns results in script registration order.
    """
    raise NotImplementedError
