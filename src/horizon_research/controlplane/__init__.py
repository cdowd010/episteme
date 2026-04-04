"""Control-plane services — mutations and structural queries.

Always available. No feature flags required.
Both CLI and MCP route through these services.

Modules:
  gateway    — Single mutation/query boundary
  validate   — Structural validation (read-only)
  check      — Stale/ref checks (read-only)
  results    — Record analysis results (planned Phase 6)
  export     — Bulk export (read-only)
  automation — Render-trigger policy table

Dependency rule: controlplane → epistemic, adapters, config. Never → views, features.
"""
