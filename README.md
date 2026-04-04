# Horizon Research

> **Early Development — not ready for use.**
> The API, file formats, and CLI surface are unstable and will change without notice.
> See [TRACKER.md](TRACKER.md) for current build status.

**A control plane for managing research epistemic webs.**

Horizon lets AI agents and human researchers register, validate, and reason about the structure of a research project — claims, assumptions, predictions, verification scripts, and the invariants that connect them — through a stable, tool-shaped API.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: Early Development](https://img.shields.io/badge/status-early%20development-orange.svg)]((TRACKER.md))

---

## What It Does

Research projects accumulate a hidden graph of epistemic dependencies: claim C depends on assumption A, prediction P follows from C, script S verifies P. When that graph is implicit and untracked, it breaks silently — a refuted prediction doesn't update the claims that depend on it, a changed assumption doesn't propagate to its consequences.

Horizon makes that graph explicit and enforces its consistency:

- **Register** claims, assumptions, predictions, scripts, and their relationships
- **Validate** the epistemic web against hard invariants (bidirectional links, DAG structure, tier constraints, coverage)
- **Verify** predictions by running registered scripts in a sandbox
- **Render** human-readable views (markdown tables, summaries) incrementally
- **Health-check** the project in one command — usable by CI or an AI agent

The primary interface is an **MCP server** so AI agents (Claude, Cursor, Copilot) can call all operations as typed tools. A full **CLI** provides the same surface for humans and scripts.

---

## Quick Start

```bash
pip install horizon-research          # CLI + adapters
pip install "horizon-research[mcp]"   # + MCP server
```

```bash
# Initialise a project workspace
horizon init

# Register a claim
echo '{"id": "C-001", "statement": "...", "type": "foundational", ...}' \
  | horizon register claim

# Run all health checks
horizon health

# Start the MCP server (for AI agent use)
python -m horizon_research.mcp.server
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full technical walkthrough.

---

## Goals

| Goal | Description |
|------|-------------|
| **AI-agent first** | MCP server is the primary interface. Agents register artifacts, validate webs, and run scripts without subprocess wrangling |
| **Human second** | Every MCP operation is also a CLI command. Humans get rich terminal output; scripts get `--json` |
| **Single gateway** | All mutations go through one boundary. No MCP-specific or CLI-specific business logic |
| **Invariants at mutation time** | Broken references, cycles, and bidirectional inconsistencies are caught the moment they're introduced — not discovered later |
| **Domain-neutral** | Works for physics, ML, medicine, social science. The vocabulary (claim, assumption, prediction) is general empirical reasoning, not field-specific jargon |
| **Zero-friction dependencies** | Domain core is stdlib-only. `click` and `rich` for CLI UX. `fastmcp` opt-in for MCP. `numpy`/`scipy` opt-in for compute scripts |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  MCP Server (primary)    │  CLI (secondary)           │
│  AI agents · tools API   │  Humans · scripts · --json │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  ProjectContext                                       │
│  Runtime contract: paths, config, caches, logs        │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  Control-Plane Services                               │
│  Gateway · Validate · Render · Health · Status        │
│  Execution Pipeline · Governance (opt-in)             │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  Domain Core  (epistemic/)                            │
│  EpistemicWeb · entities · invariants · lineage       │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  Ports / Protocols                                    │
│  WebRepository · WebRenderer · ScriptExecutor · TxLog │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  Infrastructure Adapters                              │
│  JSON repository · Markdown renderer · Sandbox        │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│  Data Plane                                           │
│  project/data/ · generated views · verify scripts     │
└──────────────────────────────────────────────────────┘
```

**Dependency rule:** arrows point down only. `mcp` and `cli` depend on `controlplane`. `controlplane` depends on `epistemic`. `adapters` implement the ports that `epistemic` defines. Nothing in `epistemic` imports from any other layer.

See [ARCHITECTURE.md](ARCHITECTURE.md) for data flow diagrams, package layout, design decisions, and the entity model.

---

## Package Layout

```
src/horizon_research/
├── epistemic/          # Domain kernel — stdlib only
│   ├── types.py        # Typed IDs, enums, Finding
│   ├── model.py        # Entity dataclasses (Claim, Prediction, …)
│   ├── web.py          # EpistemicWeb aggregate root
│   ├── invariants.py   # Cross-entity validation rules
│   └── ports.py        # Abstract interfaces (WebRepository, …)
├── controlplane/       # Product orchestration — stdlib only
│   ├── context.py      # ProjectContext and path derivation
│   ├── gateway.py      # Single mutation/query boundary
│   ├── validate.py     # Validation orchestration
│   ├── render.py       # Incremental view generation
│   ├── health.py       # Health check composition
│   ├── status.py       # Read models and summaries
│   ├── execution/      # Script dispatch, policy, meta-verify
│   └── governance/     # Sessions, boundaries, close gates (opt-in)
├── adapters/           # Infrastructure — stdlib only
│   ├── json_repository.py
│   ├── markdown_renderer.py
│   ├── sandbox_executor.py
│   └── transaction_log.py
├── mcp/                # MCP server adapter — requires fastmcp
│   ├── server.py
│   └── tools.py
└── cli/                # CLI adapter — requires click + rich
    ├── main.py
    └── formatters.py
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

### Build phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Domain core — EpistemicWeb, entities, invariants | In progress |
| 2 | Persistence, context, packaging | Pending |
| 3 | Gateway and control-plane services | Pending |
| 4 | MCP server, CLI, health | Pending |
| 5 | Human-first UX (Rich output, `horizon init`) | Pending |
| 6 | Execution pipeline (sandbox, meta-verify) | Pending |
| 7 | Governance — sessions, close gates (opt-in) | Pending |

See [TRACKER.md](TRACKER.md) for the full task-level breakdown.

---

## License

MIT — see [LICENSE](LICENSE).
