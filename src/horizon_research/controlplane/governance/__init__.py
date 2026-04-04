"""Governance layer — session boundaries and close gates.

This entire package is opt-in. It is only active when
ProjectContext.config.governance_enabled is True.

Subsystems:
  session  — Session metadata helpers (current session, open/close)
  boundary — Enforce that mutations happen within open sessions
  close    — Close-gate engine that validates and optionally publishes
"""
