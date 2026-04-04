"""Research goal tracking — a feature layer, not the epistemic kernel.

ResearchGoals answer the "why" layer: what is this project trying to achieve,
and how will we know if it succeeded? They are project management metadata,
not epistemic entities. The EpistemicWeb has no knowledge of goals.

Goals live in goals.json (managed by this module), not project_config.json
or the epistemic web. The gateway validates that linked_predictions IDs exist
in the web on load and surfaces broken links as health findings.

GoalId is defined here rather than in epistemic/types.py because goals are
a feature, not part of the epistemic kernel. Code that only uses the
epistemic web never needs to import from this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType

from ..epistemic.types import PredictionId


GoalId = NewType("GoalId", str)


@dataclass
class ResearchGoal:
    """A researcher-stated intention that motivates the epistemic work.

    Managed by the goals feature layer. The epistemic web has no knowledge
    of goals — the link is maintained manually via `horizon goal link` and
    validated (not auto-maintained) by the gateway.
    """
    id: GoalId
    statement: str
    type: str                                    # "primary" | "secondary" | "opportunistic"
    success_criteria: list[str] = field(default_factory=list)
    status: str = "active"                       # "active" | "achieved" | "abandoned"
    linked_predictions: set[PredictionId] = field(default_factory=set)
    notes: str | None = None
