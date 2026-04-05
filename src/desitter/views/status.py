"""Read models and project status summaries.

Computes human-friendly summaries from metrics and the epistemic web.
Consumed by the CLI `status` command and the MCP `project_status` tool.

All functions are read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.ports import WebRepository
from ..config import ProjectContext
from .metrics import WebMetrics, compute_metrics


@dataclass
class ProjectStatus:
    """High-level project status snapshot.

    Suitable for display as a CLI dashboard or for structured agent
    consumption via MCP.

    Attributes:
        project_name: Display name of the project.
        workspace: Filesystem path to the project root.
        metrics: Full ``WebMetrics`` snapshot.
        health_summary: One of ``"HEALTHY"``, ``"WARNINGS"``, or
            ``"CRITICAL"``.
        governance_session: Current governance session number if
            governance mode is enabled, otherwise ``None``.
        extra: Arbitrary additional metadata for extensibility.
    """
    project_name: str
    workspace: str
    metrics: WebMetrics
    health_summary: str
    governance_session: int | None
    extra: dict = field(default_factory=dict)


def get_status(
    context: ProjectContext,
    repo: WebRepository,
) -> ProjectStatus:
    """Build a full project status snapshot.

    Loads the web, computes metrics, runs a lightweight health check,
    and assembles a ``ProjectStatus``.

    Args:
        context: Project paths and runtime configuration.
        repo: Repository adapter used to load the web.

    Returns:
        ProjectStatus: The assembled project status.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError


def format_status_dict(status: ProjectStatus) -> dict:
    """Serialize a ``ProjectStatus`` to a plain dict for MCP/JSON output.

    Converts all dataclass fields to JSON-serializable primitives.

    Args:
        status: The project status to serialize.

    Returns:
        dict: A JSON-serializable representation of the status.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
