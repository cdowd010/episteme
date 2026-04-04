# Horizon Research — Project Tracker

Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` blocked

---

## Phase 1 — Domain Core
> Goal: fully tested epistemic kernel. Zero I/O. Pure Python.

- [x] `epistemic/types.py` — typed IDs, enums, Finding
- [x] `epistemic/model.py` — all 11 entity dataclasses
- [x] `epistemic/web.py` — EpistemicWeb aggregate root (register, transition, query, copy-on-write)
- [x] `epistemic/invariants.py` — tier, independence semantics, coverage validators
- [x] `epistemic/ports.py` — WebRepository, WebRenderer, WebValidator, ScriptExecutor protocols
- [ ] Tests: entity construction and field defaults (~10 tests)
- [ ] Tests: register happy path for all entity types (~11 tests)
- [ ] Tests: duplicate ID, broken reference, cycle detection (~15 tests)
- [ ] Tests: bidirectional link maintenance (~6 tests)
- [ ] Tests: claim_lineage, assumption_lineage on multi-level graphs (~8 tests)
- [ ] Tests: all invariant validators with known violations (~15 tests)

**Exit criteria:** ~80 tests passing. No external deps. Runs in milliseconds.

---

## Phase 2 — Persistence, Testing, and Packaging
> Goal: JSON adapter, context builder, installable package.

- [ ] `adapters/json_repository.py` — load/save EpistemicWeb as JSON files
- [ ] `adapters/transaction_log.py` — JSONL provenance log (append/read)
- [ ] `controlplane/context.py` — `load_config` + `build_context` implementations
- [ ] `config.py` — `horizon.toml` parsing
- [ ] `pyproject.toml` — verify `pip install -e .` works
- [ ] Tests: round-trip load/save for all entity types
- [ ] Tests: context path derivation from workspace root

---

## Phase 3 — Gateway and Control-Plane Services
> Goal: single mutation boundary wired to JSON repo. CLI and MCP can both use it.

- [ ] `controlplane/gateway.py` — register, get, list, set, transition, query
- [ ] `controlplane/validate.py` — validate_project, validate_structure
- [ ] `controlplane/render.py` — SHA-256 fingerprint cache + incremental render
- [ ] `adapters/markdown_renderer.py` — claims, predictions, assumptions, summary views
- [ ] `controlplane/check.py` — check_refs, check_stale, sync_prose, verify_prose_sync
- [ ] `controlplane/automation.py` — render trigger table wired into gateway
- [ ] Tests: gateway register → validate-after-write → rollback on violation
- [ ] Tests: dry-run semantics
- [ ] Tests: resource alias resolution

---

## Phase 4 — MCP, CLI, Init, Health
> Goal: usable by AI agents and humans. Ships the MCP server.

- [ ] `controlplane/health.py` — run_health_check (validate + stale + structure)
- [ ] `controlplane/metrics.py` — compute_metrics, tier_a_evidence_summary
- [ ] `controlplane/status.py` — get_status, format_status_dict
- [ ] `cli/main.py` — all Click commands implemented (register, get, list, transition, validate, health, status, render, export)
- [ ] `cli/formatters.py` — Rich tables + JSON fallback for all result types
- [ ] `mcp/server.py` — FastMCP server wired and runnable
- [ ] `mcp/tools.py` — all tool handlers delegating to gateway
- [ ] `__main__.py` — `python -m horizon_research` works
- [ ] Tests: CLI commands via CliRunner
- [ ] Tests: MCP tool handlers with gateway fakes

---

## Phase 5 — Human-First UX
> Goal: output that feels as natural as requests or pandas.

- [ ] Rich progress bars for long-running operations
- [ ] `horizon status` dashboard (color-coded, summary panels)
- [ ] `horizon validate --fix` dry-run suggestions
- [ ] Consistent error messages with actionable hints
- [ ] `horizon init` command (scaffold a new project)

---

## Phase 6 — Execution Pipeline
> Goal: registered scripts run in a sandbox, results machine-readable.

- [ ] `adapters/sandbox_executor.py` — subprocess with timeout + env injection
- [ ] `controlplane/execution/policy.py` — resolve_policy implementation
- [ ] `controlplane/execution/scripts.py` — run_script, run_all_scripts
- [ ] `controlplane/execution/meta_verify.py` — post-run integrity checks
- [ ] `controlplane/export.py` — export_json, export_markdown
- [ ] Tests: executor with real tmp_path scripts
- [ ] Tests: meta_verify anomaly detection

---

## Phase 7 — Governance as Opt-In
> Goal: session boundaries and close gates for rigorous projects.

- [ ] `controlplane/governance/session.py` — open/close/list sessions
- [ ] `controlplane/governance/boundary.py` — check_boundary wired into gateway
- [ ] `controlplane/governance/close.py` — close-gate validation + optional git publish
- [ ] CLI: `horizon session open|close|list`
- [ ] MCP: session tools
- [ ] Tests: boundary enforcement, close gate blocking, git publish

---

## Backlog
> Post-Phase 7. Not scheduled.

- [ ] Literature watch (background monitoring, opt-in)
- [ ] Multi-workspace / repo management tools
- [ ] Web UI (read-only dashboard)
- [ ] Export to BibTeX / Zotero
- [ ] numpy/scipy integration for benchmark verification scripts
- [ ] VSCode extension (wraps MCP server)
