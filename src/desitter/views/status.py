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

    Suitable for display as a dashboard or for structured agent consumption.
    """
    project_name: str
    workspace: str
    metrics: WebMetrics
    health_summary: str              # "HEALTHY" | "WARNINGS" | "CRITICAL"
    governance_session: int | None   # current session number if governance enabled
    extra: dict = field(default_factory=dict)


def get_status(
    context: ProjectContext,
    repo: WebRepository,
) -> ProjectStatus:
    """Build a full project status snapshot.

    Loads the web, computes metrics, runs a lightweight health check,
    and returns a ProjectStatus.
    """
    raise NotImplementedError


def format_status_dict(status: ProjectStatus) -> dict:
    """Serialise a ProjectStatus to a plain dict for MCP/JSON output."""
    raise NotImplementedError
