"""horizon_research — control plane for research epistemic webs.

Primary interface:  MCP server (AI agents call tools)
Secondary interface: CLI (humans and scripts)
Both route through:  controlplane.gateway.Gateway

Layer cake (top to bottom):
  mcp / cli       — external interfaces
  controlplane    — gateway, validate, render, health, status, execution, governance
  epistemic       — domain kernel: EpistemicWeb, entities, invariants, ports
  adapters        — JSON repo, markdown renderer, sandbox executor, tx log

Quick start (programmatic):
    from pathlib import Path
    from horizon_research.controlplane.context import build_context, load_config
    from horizon_research.adapters.json_repository import JsonRepository
    from horizon_research.epistemic import EpistemicWeb

    ctx = build_context(Path("."), load_config(Path(".")))
    repo = JsonRepository(ctx.paths.data_dir)
    web = repo.load()
"""

__version__ = "0.1.0"
