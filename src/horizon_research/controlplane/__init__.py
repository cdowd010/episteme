"""Control-plane services.

Orchestrates the product above the epistemic kernel. All business logic
that isn't domain modeling lives here.

Dependency rule: controlplane depends on epistemic, never the reverse.
No external library imports — stdlib only.

Subsystems:
  context    — ProjectContext: runtime contract for paths, config, caches
  gateway    — Single mutation/query boundary (MCP + CLI route through this)
  validate   — Read-only validation orchestration
  render     — Incremental view generation (SHA-256 fingerprints)
  check      — check-refs, check-stale, sync-prose, verify-prose-sync
  metrics    — Repo metrics and correlation-aware tier-A evidence
  health     — Health checks (composes validate + render-check + structure)
  status     — Read models / summaries
  export     — Bulk export
  execution/ — Script dispatch, policy, meta-verification
  governance/— Sessions, boundaries, close gates (opt-in)
"""
