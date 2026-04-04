"""Feature services — opt-in capabilities gated by ProjectFeatures flags.

Each sub-module corresponds to one feature flag in ProjectFeatures.
Features are registered with the MCP server and CLI only when their flag
is enabled. Disabling a flag removes the tools/commands entirely.

Modules:
  goals       — Research goal tracking (features.goals)
  discovery   — Structural gap reporter (features.inference_gap_analysis)
  protocols   — Agent documentation registry (features.protocols)
  governance/ — Sessions, boundaries, close gates (features.governance)

Dependency rule: features → core, views, epistemic, config.
"""
