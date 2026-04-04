"""Governance layer — session boundaries and close gates.

Active only when features.governance = True.

Modules:
  session   — Open/close/list sessions; SessionRecord dataclass
  boundary  — Enforce mutations happen within open sessions
  close     — Close-gate validation + optional git publish
  schedules — AnalysisSchedule + ProjectSchedules; due_analyses computation
"""
