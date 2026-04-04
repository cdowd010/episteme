# Horizon Research — Project Tracker

Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` blocked

---

## Phase 1 — Domain Core
> Goal: fully tested epistemic kernel. Zero I/O. Pure Python.

- [x] `epistemic/types.py` — typed IDs, enums, Finding (`TheoryId`, `AnalysisId`, `DeadEndId`, `DeadEndStatus`); `GoalId` lives in `features/goals.py`
- [x] `epistemic/model.py` — 11 entity dataclasses: `Claim`, `Assumption`, `Prediction`, `Theory`, `Discovery`, `Analysis`, `IndependenceGroup`, `PairwiseSeparation`, `DeadEnd`, `Concept`, `Parameter`; `source` field on all research content entities; `Analysis.uses_parameters` + `Parameter.used_in_analyses` for staleness detection; `ResearchGoal` moved to `features/goals.py`
- [x] `epistemic/web.py` — EpistemicWeb aggregate root; bidirectional maintenance for `uses_parameters` ↔ `used_in_analyses` in `register_analysis`
- [x] `epistemic/invariants.py` — tier, independence semantics, coverage validators
- [x] `epistemic/ports.py` — `WebRepository`, `WebRenderer`, `WebValidator`, `ProseSync`, `TransactionLog` protocols (no `ScriptExecutor` — consumer model)
- [ ] Tests: entity construction and field defaults, including `source`, `uses_parameters`, `used_in_analyses` (~12 tests)
- [ ] Tests: register happy path for all entity types (~11 tests)
- [ ] Tests: duplicate ID, broken reference, cycle detection (~15 tests)
- [ ] Tests: bidirectional link maintenance — `claim.analyses` ↔ `analysis.claims_covered`; `analysis.uses_parameters` ↔ `parameter.used_in_analyses`; `prediction.tests_assumptions` ↔ `assumption.tested_by` (~12 tests)
- [ ] Tests: claim_lineage, assumption_lineage on multi-level graphs (~8 tests)
- [ ] Tests: all invariant validators with known violations, including `validate_assumption_testability` (falsifiable_consequence set but tested_by empty → WARNING) (~18 tests)

**Exit criteria:** ~80 tests passing. No external deps. Runs in milliseconds.

---

## Phase 2 — Persistence, Testing, and Packaging
> Goal: JSON adapter, context builder, installable package.
> Core only — no goals, no schedules, no session counter.

- [ ] `adapters/json_repository.py` — load/save EpistemicWeb as JSON files (`analyses.json`, `theories.json`, `dead_ends.json`); round-trip includes `source`, `uses_parameters`, `used_in_analyses`
- [ ] `adapters/project_config_repository.py` — owns `project_config.json`: project name, description, `ProjectFeatures` flags only; no goals, no schedules, no session counter
- [ ] `adapters/transaction_log.py` — JSONL provenance log (append/read)
- [ ] `config.py` — `load_config` + `build_context` + `ProjectFeatures`; `horizon.toml` parsing with `[features]` block; already implemented as stub
- [ ] `pyproject.toml` — verify `pip install -e .` works
- [ ] `horizon_research/__init__.py` — re-export common public API entry points + `record()` SDK shim
- [ ] Tests: round-trip load/save for all entity types including new fields
- [ ] Tests: `ProjectFeatures` round-trip through `project_config.json`; partial update preserves other fields
- [ ] Tests: context path derivation from workspace root

---

## Phase 3 — Core and View Services
> Goal: single mutation boundary + view services wired to JSON repo. Core only —
> no goals, no sessions, no feature tools. CLI and MCP both use this layer.

- [ ] `core/gateway.py` — register, get, list, set, transition, query
- [ ] `core/validate.py` — validate_project, validate_structure (structural web invariants only)
- [ ] `core/check.py` — check_refs, check_stale (uses `Analysis.uses_parameters` ↔ `Parameter.used_in_analyses` to identify stale predictions), sync_prose, verify_prose_sync
- [ ] `core/export.py` — export_json, export_markdown
- [ ] `core/automation.py` — render trigger table wired into gateway
- [ ] `views/render.py` — SHA-256 fingerprint cache + incremental render
- [ ] `views/health.py` — run_health_check; structural findings + broken `source` references
- [ ] `views/status.py` — get_status, format_status_dict
- [ ] `views/metrics.py` — compute_metrics, tier_a_evidence_summary
- [ ] `adapters/markdown_renderer.py` — claims, predictions, assumptions, theories, analyses summary views; renders `doi:` and `arxiv:` sources as links
- [ ] Tests: gateway register → validate-after-write → rollback on violation
- [ ] Tests: dry-run semantics
- [ ] Tests: resource alias resolution
- [ ] Tests: `check_stale` identifies correct stale predictions after parameter change
- [ ] Tests: `validate_assumption_testability` surfaces assumptions with falsifiable_consequence but no tested_by predictions

---

## Phase 4 — CLI and MCP Server
> Goal: two first-class interfaces over the same core. Ships the MCP server.
> Core tools available on both. Feature tools are MCP-only and feature-gated.

### Core CLI
- [ ] `cli/main.py` — core commands: `register`, `get`, `list`, `transition`, `validate`, `health`, `status`, `render`, `export`, `init`
- [ ] `cli/formatters.py` — Rich tables + JSON fallback; `doi:` and `arxiv:` sources rendered as clickable links in terminal
- [ ] `__main__.py` — `python -m horizon_research` works
- [ ] `horizon init` — creates `project_config.json` (name, description, feature flags), directory structure; idempotent; no goals or schedules baked in
- [ ] `horizon init --with-agent` — generates `.horizon/agents.md` + per-tool adapter files
- [ ] `horizon init --refresh` — regenerates agent bootstrap files only; never touches project data

### MCP Server
- [ ] `mcp/server.py` — FastMCP server; feature-gated tool registration from `ProjectFeatures`
- [ ] `mcp/tools.py` — core tool handlers: `register`, `get`, `list`, `set`, `transition`, `query`, `validate`, `health`, `status`, `render`, `check_stale`, `check_refs`, `export`, `record_result`

### MCP Feature Tools (feature-gated; registered only when flag enabled)
- [ ] `features.goals` — `features/goals.py` CRUD + `adapters/goals_repository.py` (`goals.json`); MCP tools: `get_goal`, `list_goals`, `add_goal`, `achieve_goal`, `link_goal_prediction`; gateway validates linked prediction IDs exist; broken links surface as health findings
- [ ] `features.protocols` — `features/protocols.py`; MCP tool: `get_protocol(name)`; `load_protocols` registry provides agents documentation on usage
- [ ] Feature-gated tool surface: MCP server reads `project_config.json` at startup; disabled features have no exposed tools

### Tests
- [ ] Tests: core CLI commands via CliRunner
- [ ] Tests: MCP core tool handlers with gateway fakes
- [ ] Tests: feature-gated tool registration (`features.goals=false` → no goal tools; `features.inference_gap_analysis=false` → no gap tool)
- [ ] Tests: `horizon init` creates correct directory structure; `project_config.json` contains only name/description/features; no goals or schedules

---

## Phase 5 — Human-First UX
> Goal: the audit scaffold becomes navigable. A researcher or AI agent can traverse
> the web, surface structural gaps, and audit any chain without writing JSON.

- [ ] Rich progress bars for long-running operations
- [ ] `horizon status` dashboard (color-coded, summary panels, goal progress)
- [ ] `horizon validate --fix` dry-run suggestions
- [ ] Consistent error messages with actionable hints
- [ ] `horizon add <type>` — interactive prompts for all core entity types; prompts for `source`, `derivation` on research content entities
- [ ] `horizon show <type> [id]` — human-readable view with relationships; `source` rendered as link where applicable
- [ ] `horizon log [id]` — mutation history from transaction log
- [ ] Shell completions (bash, zsh, fish) with resource ID tab-completion
- [ ] `horizon goal add|list|achieve|link` — interactive goal management (only available when `features.goals=true`)
- [ ] `horizon config set|get` — read/write `project_config.json` fields without editing JSON directly
- [ ] `horizon status` shows goal progress when `features.goals=true`; shows core web stats always
- [ ] `features/discovery.py` — structural gap reporter; returns `StructuralGap` list (structural observations only — no suggestions, no prescriptions); no writes, no external deps
- [ ] `horizon inspect` CLI command — Rich table of structural gaps; `--json` for piping to an agent; each gap identifies entity ID, gap type, and navigable context
- [ ] Quickstart guide: install → init → add theory → add claim → add prediction → record result → inspect → render

---

## Phase 6 — Results Ingestion
> Goal: Horizon consumes results from researcher-run analyses. No execution, no sandboxing.

- [ ] `adapters/results_repository.py` — load/save `AnalysisResult` list from `data/results.json`; multiple results per prediction in insertion order
- [ ] `core/results.py` — `record_result(context, prediction_id, value, uncertainty, status, notes, dry_run)`; persists to `data/results.json`; transitions prediction status; appends to transaction log
- [ ] `horizon record <prediction_id>` CLI command — `--value`, `--uncertainty`, `--status`, `--notes`, `--no-transition`, `--json`
- [ ] `record_result` MCP tool — returns standard `GatewayResult` envelope
- [ ] `horizon_research.record()` SDK shim — one-line instrumentation for any Python script
- [ ] Git SHA auto-capture in `horizon record` — calls `git rev-parse HEAD`; warns if `Analysis.path` file has uncommitted changes at record time
- [ ] `core/export.py` — `export_json`, `export_markdown` (includes recorded results with uncertainty and git_sha)
- [ ] `horizon results <prediction_id>` — show result history from `data/results.json`; displays value, uncertainty, status, git_sha, source, timestamp
- [ ] Tests: `record_result` persists to `data/results.json` and transitions prediction status correctly
- [ ] Tests: `--no-transition` suppresses status change
- [ ] Tests: uncertainty round-trips through JSON
- [ ] Tests: git SHA captured when in git repo; warning emitted when analysis file has uncommitted changes
- [ ] Tests: `parameter_snapshot` captures values of all `Analysis.uses_parameters` at record time; round-trips through JSON
- [ ] Tests: SDK shim delegates to same gateway endpoint as CLI

---

## Phase 7 — Governance as Opt-In
> Goal: session boundaries and close gates for rigorous projects.
> All of this is behind `features.governance=true`. The core product has no concept of sessions.

- [ ] `features/governance/session.py` — open/close/list sessions; session counter lives here, not in `project_config.json`
- [ ] `features/governance/boundary.py` — check_boundary wired into gateway (only active when governance enabled)
- [ ] `features/governance/close.py` — close-gate validation + optional git publish
- [ ] `features/governance/schedules.py` — `AnalysisSchedule` + `ProjectSchedules`; `due_analyses` computed relative to session counter; health check includes `due_analyses` only when this feature is on
- [ ] CLI: `horizon session open|close|list` (only when `features.governance=true`)
- [ ] MCP: session tools + `due_analyses` in health (only registered when `features.governance=true`)
- [ ] Tests: boundary enforcement, close gate blocking, git publish
- [ ] Tests: session counter increments on `session open`
- [ ] Tests: `due_analyses` computed correctly when governance enabled; absent from health when disabled

---

## Backlog
> Post-Phase 7. Not scheduled. All items here are MCP feature tools unless noted.

- [ ] **Literature watch** — MCP feature (`features.literature_watch`); background monitoring of sources; agent-facing tool surface
- [ ] **Experiment ideation** — MCP feature (`features.experiment_ideation`); `suggest_experiments` tool driven by active theories and open claims; structural observations only, no logical prescriptions
- [ ] **AI-assisted chain audit** — an AI agent calls traversal tools (`get_prediction_chain`, `get_structural_gaps`) and reasons over results with its own domain knowledge; no Horizon-internal LLM needed; the Phase 5 traversal API is the foundation
- [ ] **Persisted structural gaps** — promote `StructuralGap` to a tracked entity with lifecycle (reviewed/dismissed/acted-on); ephemeral reporting (Phase 5) ships first
- [ ] **Multi-workspace / repo management** — tooling outside the product core
- [ ] **Web UI** — read-only dashboard; wraps MCP server
- [ ] **Export to BibTeX / Zotero** — uses `source` field DOI/arXiv pointers
- [ ] **numpy/scipy integration** — optional extras for researcher analyses
- [ ] **VSCode extension** — wraps MCP server
- [ ] **`source` format validation** — `health_check` lint rule that flags malformed `doi:` and `arxiv:` references
