"""View services — composed summaries and derived file generation.

Always available. No feature flags required.
Compose core service outputs into holistic reports or derived files.
Views are read-only with the exception of render (writes markdown to disk).

Modules:
  health   — Composed health report (aggregates validate + check)
  render   — Incremental markdown view generation (SHA-256 cache)
  status   — Summary read model for dashboard display
  metrics  — Evidence statistics (tier A summary, correlation-aware counts)

Dependency rule: views → core, epistemic, config. Never → features.
"""
