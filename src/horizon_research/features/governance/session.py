"""Session metadata helpers.

A session is a numbered research work unit. Each session has an opening
state (what was true when it started) and may have a close record
(what changed and what the health was at close time).

Sessions are stored in project/data/governance/sessions.json.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionRecord:
    """Metadata for one research session.

    number:     Monotonically increasing session number (1-indexed).
    opened_at:  ISO 8601 timestamp.
    closed_at:  ISO 8601 timestamp, or None if still open.
    summary:    Optional human-written summary of what was done.
    """
    number: int
    opened_at: str
    closed_at: str | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)


def get_current_session(data_dir) -> SessionRecord | None:
    """Return the currently open session, or None if none is open."""
    raise NotImplementedError


def open_session(data_dir, summary: str | None = None) -> SessionRecord:
    """Open a new session. Raises if one is already open."""
    raise NotImplementedError


def close_session(data_dir, session_number: int, summary: str | None = None) -> SessionRecord:
    """Mark a session as closed. Raises if the session is not open."""
    raise NotImplementedError


def list_sessions(data_dir) -> list[SessionRecord]:
    """Return all session records in ascending order."""
    raise NotImplementedError
