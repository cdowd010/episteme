# deSitter — Tracker

Status: `[ ]` pending · `[~]` in progress · `[x]` done

**Target:** a researcher can `ds.connect()` from a Python script or notebook, register and update all entity types, record analysis results, run queries, and get a health report — all without touching raw dicts or JSON files.

---

## Architecture Rules

These are execution constraints. Work that violates them should be rejected.

- All writes flow through `controlplane/gateway.py`. No second mutation path.
- The client changes calling conventions only. No business logic, no invariant bypass.
- `EpistemicWeb` is the kernel mutation surface. The Gateway orchestrates around it.
- `controlplane/` depends on abstractions from `epistemic/ports.py`. Concrete wiring stays in `factory.py`.
- Payload validation stays behind the `PayloadValidator` port. No inline validation in the Gateway.
- Fail fast: schema errors, broken references, and invariant failures surface before persistence.
- YAGNI: no concurrency control, indexing, CLI, or MCP until this target ships.

---

## What Is Done

- [x] Epistemic kernel: `types.py`, `model.py`, `web.py`, `invariants.py`, `errors.py`, `codec.py`, `ports.py`
- [x] Gateway metadata tables: `_gateway_catalog.py` (RESOURCE_SPECS, QUERY_SPECS), `_gateway_results.py` (GatewayResult)
- [x] Config dataclasses: `DesitterConfig`, `ProjectPaths`, `ProjectContext`
- [x] `DomainValidator.validate()` in `controlplane/validate.py`
- [x] Adapters: `json_repository.py` (load/save), `transaction_log.py`, `payload_validator.py`
- [x] Typed helper signatures declared in `client/_hypothesis.py`, `_registry.py`, `_structure.py`

---

## What Remains

### 1. Config

- [ ] `load_config(workspace: Path) -> DesitterConfig` — parse `desitter.toml`; return defaults if absent
- [ ] `build_context(workspace: Path, config: DesitterConfig) -> ProjectContext` — derive all paths

### 2. Gateway

All methods in `controlplane/gateway.py` are stubbed. Implement in order:

- [ ] `__init__` — store web, validator, payload_validator
- [ ] `web` property — return current in-memory web
- [ ] `resolve_resource` — validate and return canonical resource key
- [ ] `_resource_spec` — look up ResourceSpec by resource key
- [ ] `_typed_identifier` — coerce string ID to resource's NewType
- [ ] `_lookup_entity` — find entity in web by resource key and string ID
- [ ] `_validate_payload` — delegate to PayloadValidator if configured
- [ ] `_matches_filters` — test serialized entity dict against filter predicates
- [ ] `_error_result` — construct error GatewayResult
- [ ] `_finalize_mutation` — run validators on new web; CRITICAL blocks; swap on success
- [ ] `register` — validate payload → build entity → call kernel → _finalize_mutation
- [ ] `get` — look up entity → serialize → return
- [ ] `list` — collect all entities of type → filter → serialize → return
- [ ] `set` — fetch existing → merge payload → rebuild entity → call kernel → _finalize_mutation
- [ ] `transition` — fetch existing → call kernel transition method → _finalize_mutation
- [ ] `query` — resolve QuerySpec → coerce params → call web method → serialize → return
- [ ] `record_analysis_result` — narrow wrapper over `EpistemicWeb.record_analysis_result`

### 3. Factory

- [ ] `build_gateway(web, *, payload_validator)` — instantiate `DomainValidator`, construct and return `Gateway`

### 4. Validate

- [ ] `validate_project(web, extra_validators)` — run `DomainValidator` plus any extras, return combined findings

### 5. Client Core

All methods in `client/_core.py` and `client/_client.py` are stubbed. Implement:

- [ ] `_DeSitterClientCore.__init__(gateway, *, repo)` — store gateway and repo
- [ ] `_DeSitterClientCore.gateway` property
- [ ] `_DeSitterClientCore.save()` — call `repo.save(gateway.web)` if repo present
- [ ] `_DeSitterClientCore.__enter__` / `__exit__` — context manager; auto-save on exit
- [ ] `_DeSitterClientCore.register(resource, *, dry_run, **payload)` → `ClientResult`
- [ ] `_DeSitterClientCore.get(resource, identifier)` → `ClientResult`
- [ ] `_DeSitterClientCore.list(resource, **filters)` → `ClientResult`
- [ ] `_DeSitterClientCore.set(resource, identifier, *, dry_run, **payload)` → `ClientResult`
- [ ] `_DeSitterClientCore.transition(resource, identifier, new_status, *, dry_run)` → `ClientResult`
- [ ] `_DeSitterClientCore.query(query_type, **params)` → `ClientResult`
- [ ] `_DeSitterClientCore._invoke_gateway` — call gateway method, wrap unexpected errors
- [ ] `_DeSitterClientCore._handle_resource_result` — convert GatewayResult to ClientResult
- [ ] `connect(*, repo, web)` — load config + context, build web via repo or empty, build gateway via factory, return DeSitterClient
- [ ] `_without_none(**payload)` — strip None values from payload dict

### 6. Typed Helpers — implementations

All three helper mixins have signatures but raise NotImplementedError. Implement all as thin wrappers over `self.register(...)`, `self.get(...)`, `self.list(...)`, `self.set(...)`, `self.transition(...)`:

**`_hypothesis.py`** (Claims, Assumptions, Predictions, IndependenceGroups, PairwiseSeparations)
- [ ] `register_claim`, `get_claim`, `list_claims`, `set_claim`, `transition_claim`
- [ ] `register_assumption`, `get_assumption`, `list_assumptions`, `set_assumption`
- [ ] `register_prediction`, `get_prediction`, `list_predictions`, `set_prediction`, `transition_prediction`
- [ ] `register_independence_group`, `get_independence_group`, `list_independence_groups`, `set_independence_group`
- [ ] `register_pairwise_separation`, `get_pairwise_separation`, `list_pairwise_separations`

**`_structure.py`** (Analyses, Parameters)
- [ ] `register_analysis`, `get_analysis`, `list_analyses`, `set_analysis`
- [ ] `register_parameter`, `get_parameter`, `list_parameters`, `set_parameter`
- [ ] `record_analysis_result(analysis_id, result, *, sha, date)` — delegate to gateway

**`_registry.py`** (Theories, Discoveries, DeadEnds)
- [ ] `register_theory`, `get_theory`, `list_theories`, `set_theory`, `transition_theory`
- [ ] `register_discovery`, `get_discovery`, `list_discoveries`, `set_discovery`, `transition_discovery`
- [ ] `register_dead_end`, `get_dead_end`, `list_dead_ends`, `set_dead_end`, `transition_dead_end`

### 7. Health Check

- [ ] `run_health_check(web, validator)` in `views/health.py` — run validator, compute overall status, return `HealthReport`

### 8. Tests

- [ ] Gateway: register round-trip for at least one entity (claim)
- [ ] Gateway: get / list / set / transition round-trips
- [ ] Gateway: query round-trips (claim_lineage, refutation_impact, parameter_impact)
- [ ] Gateway: CRITICAL finding blocks mutation, web unchanged
- [ ] Gateway: dry_run returns findings without mutating
- [ ] Gateway: broken reference returns error result
- [ ] Gateway: duplicate ID returns error result
- [ ] Gateway: record_analysis_result round-trip
- [ ] Client: `connect()` returns a working client against a temp workspace
- [ ] Client: register_* / get_* / list_* helpers for all entity types
- [ ] Client: set_* helpers for all entity types
- [ ] Client: transition_* helpers for status-bearing entities
- [ ] Client: record_analysis_result round-trip through client
- [ ] Client: dry_run=True validates without writing
- [ ] Client: schema validation errors surface as ClientResult errors, not exceptions
- [ ] Health: run_health_check returns HEALTHY on a clean web
- [ ] Health: run_health_check returns WARNING / CRITICAL on a web with violations

---

## Exit Criteria

Every item below must be true before this target is closed:

- [ ] `client = ds.connect()` works from a Python script in a real workspace directory
- [ ] All 10 entity types can be registered through typed keyword-argument helpers
- [ ] All 10 entity types can be updated through typed `set_*` helpers
- [ ] All status-bearing entities can be transitioned through typed helpers
- [ ] Analysis results can be recorded programmatically via `record_analysis_result`
- [ ] All named queries return structured `ClientResult` objects suitable for notebooks
- [ ] `run_health_check` returns a `HealthReport` with correct overall status
- [ ] Validation failures (schema errors, broken refs, CRITICAL invariants) fail fast without writing
- [ ] dry_run=True validates and returns findings without mutating the web
- [ ] All of the above is covered by automated tests

---

## Deferred

Everything below is deferred until the exit criteria above are met:

- CLI command handlers
- MCP server and tools
- `controlplane/check.py` (staleness detection)
- `controlplane/render.py` and `controlplane/export.py`
- `controlplane/prose.py`
- `views/status.py` and `views/metrics.py`
- `adapters/markdown_renderer.py`
- Payload schema artifact files under `schemas/payloads/`
- Optimistic concurrency control
- Query performance indexing
