# Horizon Rebuild Plan — From the Ground Up

*Unified build plan combining the product roadmap with a clean architecture
rebuild. Written for execution, not theory.*

---

## Table of Contents

1. [Goal](#1-goal)
2. [Why Rebuild Instead of Refactor](#2-why-rebuild-instead-of-refactor)
3. [Architecture: Control Plane, Gateway, and Principles](#3-architecture-control-plane-gateway-and-principles)
4. [The Epistemic Web: Core Data Structure](#4-the-epistemic-web-core-data-structure)
5. [Phase 1 — Domain Core](#5-phase-1--domain-core)
6. [Phase 2 — Persistence, Testing, and Packaging](#6-phase-2--persistence-testing-and-packaging)
7. [Phase 3 — Gateway and Control-Plane Services](#7-phase-3--gateway-and-control-plane-services)
8. [Phase 4 — MCP, CLI, Init, Health](#8-phase-4--mcp-cli-init-health)
9. [Phase 5 — Human-First UX](#9-phase-5--human-first-ux)
10. [Phase 6 — Execution Pipeline](#10-phase-6--execution-pipeline)
11. [Phase 7 — Governance as Opt-In](#11-phase-7--governance-as-opt-in)
12. [After Phase 7: The Backlog](#12-after-phase-7-the-backlog)
13. [Principle Compliance Matrix](#13-principle-compliance-matrix)
14. [Clean Break from the Current Codebase](#14-clean-break-from-the-current-codebase)
15. [Standing Decisions](#15-standing-decisions)
16. [Data Flow Diagram](#16-data-flow-diagram)
17. [End-to-End Traces](#17-end-to-end-traces)
18. [Testing Strategy and Fixture Model](#18-testing-strategy-and-fixture-model)
19. [Where to Put New Code](#19-where-to-put-new-code)
20. [CI/CD Rollout](#20-cicd-rollout)

---

## 1. Goal

AI agents are the primary target user. Horizon ships an MCP server so that
agents (Claude, Cursor, Copilot, etc.) can register research artifacts,
validate the epistemic web, check health, and run verification scripts —
all through a stable, tool-shaped API with no subprocess wrangling.

A standalone CLI is the secondary interface: it exists for human researchers
who want direct access and for scripting, testing, and debugging the product
itself. Every capability exposed over MCP is also reachable from the CLI.

Both surfaces share one backend: the control-plane gateway. If the gateway
is correct, both interfaces are correct.

The rebuild starts from the epistemic web — the core data structure — and
layers outward. Each phase ships something testable.

Horizon should be rebuilt as a **control plane over a research data plane**.
The epistemic web is the domain kernel, but the product is larger than the
kernel: the gateway, validators, renderers, health, execution policy, and
optional governance all belong to the control plane.

---

## 2. Why Rebuild Instead of Refactor

The existing codebase has proven the *domain model* — claims, predictions,
assumptions, verification scripts, independence groups, bidirectional
invariants, transactional mutations. These ideas are sound and battle-tested.

What's broken is the *wiring*:

- `_sync_compatibility_state()` in `horizon.py` is ~120 lines of
  monkey-patching that rewrites globals across 10+ modules at runtime
- Circular dependencies resolved through runtime function rebinding
- Modules are not independently testable
- No module boundary prevents reaching into any other module's state

Refactoring this in-place (the old Phase 2 plan) would require:
1. Writing characterization tests against the current fragile wiring
2. Threading `ProjectContext` through every module while keeping the old
   wiring alive as a fallback
3. Deleting the old wiring once everything passes
4. Repeating for every module

A clean rebuild avoids all of that. The existing codebase proved which
**ideas** are correct — gateway as mutation boundary, transactional writes,
bidirectional invariants, sandbox execution. We take those ideas and build
them right from scratch.

### What We Preserve

| Keep | Why |
|------|-----|
| JSON file format | Backward compatibility, human-readable, simple |
| CLI command surface | User muscle memory, agent tooling compatibility |
| Control-plane/data-plane split | It is the right product boundary: product code manages research state without embedding research content in the codebase |
| Gateway as a single mutation/query boundary | Centralizes writes, rollback, provenance, dry-run behavior, and stable external semantics |
| Transactional mutations (validate-after-write, rollback on failure) | Best architectural idea in current system |
| Incremental rendering (SHA-256 fingerprints) | Performance |
| Sandbox execution model | Security |
| Domain vocabulary (claims, assumptions, predictions, independence groups) | Correct domain modeling |
| Bidirectional invariants | Correct epistemic reasoning |

### What We Eliminate

| Remove | Why |
|--------|-----|
| `_sync_compatibility_state()` | Global state mutation |
| Module-level globals for paths | Untestable, fragile |
| Untyped `GATEWAY_RESOURCE_SPECS` dict-of-dicts | Replace the spec table, not the gateway concept itself |
| After-the-fact bidirectional link validation | Replaced by enforcement at mutation time |
| Wrapper functions that call `_sync_compatibility_state()` first | No global state to sync |
| `_ORIGINAL_*` snapshot variables | No state to snapshot |

---

## 3. Architecture: Control Plane, Gateway, and Principles

The first draft of this rebuild plan got one thing materially wrong: it
modeled Horizon mostly as a domain library with a CLI on top. That is too
small. Horizon is a **control plane** whose domain kernel is the epistemic
web.

### 3.1 The Right Top-Level Picture

- The **data plane** is the project state and artifacts: canonical registries,
    generated views, verification scripts, integrity metadata, and optional
    governance data.
- The **control plane** is the product code that manages that data plane:
    context building, gateway, validators, renderers, health/status, execution
    policy, and optional governance services.
- The **epistemic web** is the in-memory domain kernel inside the control
    plane, not the whole product.

This distinction matters because it keeps the rebuild from collapsing into
"just a graph library." The product is valuable because it manages the
research project end-to-end.

The filesystem and package layout need to reflect that. The top code folder
should be `src/horizon_research/`. `epistemic/` belongs *inside* that package
as the kernel data structure layer for storing and validating epistemic webs;
it should not be the umbrella package that everything else lives under.

### 3.2 Control-Plane Subsystems We Should Keep

1. **ProjectContext** — one explicit runtime contract for paths, config,
     caches, logs, and feature flags.
2. **Gateway** — the single mutation and query boundary exposed to both the
     MCP server and the CLI.
3. **MCP server** — the primary external API for AI agents. Exposes all
     gateway operations as typed MCP tools with structured `status`-first
     envelopes. Not aspirational — ships in Phase 4.
4. **Read-only services** — validate, render, health, status, export, and
     other computed read models.
5. **Execution-policy pipeline** — registered scripts, sandboxing,
     machine-readable benchmark validation, and meta-verification.
6. **Governance layer** — sessions, boundaries, and close gates as opt-in.
7. **Outer-shell workspace tooling** — multi-program or repo-management tools
     stay outside the product core.

Not every old implementation detail survives. But these subsystem boundaries
were good ideas and should be preserved.

### 3.3 The Layer Cake

```
┌─────────────────────────────────────────────────┐
│  MCP Server (primary)  │  CLI (secondary)        │
│  AI agents call tools  │  Humans and scripts     │
│  Structured envelopes  │  Human + --json modes   │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  ProjectContext                                 │
│  Runtime contract: paths, config, caches, logs  │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Control-Plane Services                         │
│  Gateway | Validate | Render | Health | Status  │
│  Execution Policy | Governance (opt-in)         │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Domain Core                                    │
│  EpistemicWeb, entities, invariants, lineage    │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Ports / Protocols                              │
│  Repository, renderer, executor, transaction log│
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Infrastructure Adapters                        │
│  JSON repository, markdown renderer, sandbox    │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Data Plane                                     │
│  project/data, generated views, verify scripts  │
└─────────────────────────────────────────────────┘
```

**Principles:**
- **Dependency Inversion (D)**: Domain defines interfaces; infrastructure
    implements them. Control-plane services depend on abstractions.
- **Separation of Concerns**: The domain models truth, the gateway manages
    mutations, adapters perform I/O, and MCP/CLI speak to their respective
    consumers.
- **Low Coupling**: Both MCP and CLI route through the gateway using typed
    entities and ports, never through global module state.
- **Single Gateway**: MCP and CLI are different presentations of the same
    operations. There is no MCP-specific business logic.

### 3.4 Package Layout

All code paths below are relative to `src/horizon_research/` unless noted
otherwise. The Python import root is `horizon_research`.

```
src/
└── horizon_research/               # Top-level product package and import root
    ├── __init__.py
    ├── __main__.py                 # `python -m horizon_research`
    ├── config.py                   # User config loading
    ├── mcp/                        # MCP server adapter (primary external interface)
    │   ├── __init__.py
    │   ├── server.py               # MCP server entry point, tool registration
    │   └── tools.py                # Tool handlers — thin wrappers over control plane
    ├── cli/                        # CLI adapter (secondary external interface)
    │   ├── __init__.py
    │   ├── main.py                 # Entry point, arg parsing, dispatch
    │   └── formatters.py           # Human/JSON output formatting
    ├── controlplane/               # Product orchestration above the kernel
    │   ├── __init__.py
    │   ├── context.py              # ProjectContext builder and path derivation
    │   ├── automation.py           # Declarative render/stale-trigger contracts
    │   ├── gateway.py              # Single mutation/query boundary
    │   ├── validate.py             # Read-only validation orchestration
    │   ├── render.py               # Generated surfaces (incremental SHA-256 caching)
    │   ├── check.py                # check-refs, check-stale, sync-prose, verify-prose-sync
    │   ├── metrics.py              # Repo metrics, correlation-aware tier-A evidence
    │   ├── health.py               # Health checks (composes validate + render-check + structure)
    │   ├── status.py               # Read models / summaries (consumes metrics)
    │   ├── export.py               # Bulk export
    │   ├── execution/
    │   │   ├── __init__.py
    │   │   ├── scripts.py          # Registered script dispatch
    │   │   ├── policy.py           # Execution policy normalization
    │   │   └── meta_verify.py      # Adversarial integrity checks
    │   └── governance/
    │       ├── __init__.py
    │       ├── boundary.py         # Session boundary enforcement
    │       ├── session.py          # Session metadata helpers
    │       └── close.py            # Close-gate engine (git publish optional)
    ├── adapters/                   # Infrastructure
    │   ├── __init__.py
    │   ├── json_repository.py      # Implements WebRepository
    │   ├── markdown_renderer.py    # Implements WebRenderer
    │   ├── sandbox_executor.py     # Implements ScriptExecutor
    │   └── transaction_log.py      # Query/mutation provenance log
    └── epistemic/                  # Kernel data structures for epistemic webs
        ├── __init__.py
        ├── types.py                # Enums, typed IDs, findings
        ├── model.py                # Entity dataclasses
        ├── web.py                  # EpistemicWeb aggregate root
        ├── invariants.py           # Cross-entity validation rules
        └── ports.py                # Repository, renderer, executor, tx log
```

**Principles:**
- **Single Responsibility (S)**: `epistemic/` models epistemic truth,
    `controlplane/` orchestrates product behavior, `adapters/` perform I/O,
    `mcp/` serves AI agents, `cli/` handles human presentation.
- **High Cohesion**: Gateway, validate, render, and health sit together as the
    control-plane layer because they jointly manage the project.
- **Acyclic Dependencies (ADP)**: `mcp → controlplane → epistemic ← adapters`
    and `cli → controlplane`. MCP and CLI are peers at the outer shell.
- **Stable Dependencies (SDP)**: `epistemic/` changes least, `mcp/` and `cli/`
    change most.
- **No duplicated logic**: `mcp/tools.py` never re-implements what
    `controlplane/` already does. Every tool handler is a thin wrapper that
    calls the same gateway or service function the CLI uses.

### 3.5 The Gateway We Keep

The gateway absolutely belongs in the rebuild. The domain model does **not**
replace it. They solve different problems:

- The **domain** enforces epistemic invariants inside one in-memory web.
- The **gateway** owns the external mutation and query surface.

The gateway should be responsible for:

- resource-oriented register/get/list/set/transition/query operations
- payload parsing and normalization
- resource alias resolution (plural/hyphenated forms → canonical keys)
- dry-run semantics
- transaction orchestration
- provenance logging
- stable result envelopes for CLI and automation

Resource aliases allow flexible naming on the command line:

```python
GATEWAY_RESOURCE_ALIASES = {
    "claim": "claim", "claims": "claim",
    "prediction": "prediction", "predictions": "prediction",
    "failure": "failure", "failures": "failure",
    "summary": "session_summary", "session-summary": "session_summary",
    # ... maps plural/hyphenated forms to canonical keys
}
```

This is a data-driven design. Adding a new resource type should mean adding
one entry, not writing a new handler class.

The gateway should **not** be responsible for:

- storing canonical domain rules in untyped dict-of-dicts
- mutating module globals
- owning validation rules themselves
- formatting human CLI output

In other words: keep the gateway boundary, replace the old implementation.

```python
@dataclass
class GatewayResult:
        status: str          # "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run"
        changed: bool
        message: str
        findings: list[Finding]
        transaction_id: str | None = None
        data: dict | None = None  # resource data for get/list/query results


class Gateway:
        """Single mutation/query boundary for the control plane."""

        def __init__(
                self,
                context: ProjectContext,
                repo: WebRepository,
                validator: WebValidator,
                renderer: WebRenderer,
                prose_sync: ProseSync,
                tx_log: TransactionLog,
        ) -> None:
                self._context = context
                self._repo = repo
                self._validator = validator
                self._renderer = renderer
                self._prose_sync = prose_sync
                self._tx_log = tx_log
```

### 3.6 The Runtime Contract: ProjectContext

The original architecture was right to want one runtime contract object. The
new plan should preserve that idea explicitly.

```python
@dataclass
class HorizonConfig:
        project_dir: Path = Path("project")
        governance_enabled: bool = False
        literature_watch_enabled: bool = False


@dataclass
class ProjectPaths:
        workspace: Path
        project_dir: Path
        data_dir: Path
        views_dir: Path
        knowledge_dir: Path
        integrity_dir: Path
        verify_script_dir: Path
        analysis_script_dir: Path
        cache_dir: Path
        render_cache_file: Path
        check_refs_cache_file: Path
        query_transaction_log_file: Path


@dataclass
class ProjectContext:
        workspace: Path
        config: HorizonConfig
        paths: ProjectPaths
```

Important rule: `ProjectContext` carries **data**, not callbacks. No monkey
patching. No hidden collaborators. It exists so every control-plane service can
be explicit about what project it is operating on.

### 3.7 Design Decisions

**Native Python types everywhere.** The domain model uses `dict`, `set`, and
`list` — not `Mapping`, `frozenset`, or `tuple`. The `EpistemicWeb` and the
gateway are the encapsulation boundaries, not the container types.

**Dataclasses, not frozen.** Entities are `@dataclass` with mutable fields.
Consistency is enforced by the aggregate root and the gateway transaction
boundary, not by pretending Python collections are immutable.

**Targeted dependencies for great UX.** The goal is a tool that feels as
natural to use as `requests`, `pandas`, or `numpy` — clean API, beautiful
output, sensible defaults, zero friction. To get there, we allow carefully
chosen dependencies at the CLI and adapter boundaries while keeping the
domain core pure Python.

Dependency philosophy:
- **Domain core (`epistemic/`)**: stdlib only. Zero external imports. This
  is the gravity well — it must be fast, portable, and free of supply-chain
  risk.
- **Control plane (`controlplane/`)**: stdlib only. Business logic should
  not depend on third-party libraries.
- **CLI (`cli/`)**: `click` for argument parsing and command composition.
  `rich` for terminal output (tables, panels, color, progress). These
  libraries are stable, well-maintained, and directly improve the user's
  experience.
- **MCP (`mcp/`)**: `fastmcp` as an optional extra. The MCP server is not
  needed for CLI-only use.
- **Adapters (`adapters/`)**: stdlib (`json`, `pathlib`). Adapters stay
  thin and dependency-free.
- **Compute**: `numpy`, `scipy` as optional extras for verification scripts
  that need them. Never required for core operations.

The dependency tree stays **shallow** — only direct dependencies we've
consciously chosen, no transitive dependency sprawl. If removing a
dependency would make the product worse to use, it earns its place. If
it only saves the developer a few lines of code internally, it doesn't.

---

## 4. The Epistemic Web: Core Data Structure

### 4.1 What Are We Modeling?

Research is a **directed graph with typed nodes and typed edges**:

- **Nodes** are epistemic artifacts: claims, assumptions, predictions,
  hypotheses, discoveries, scripts, independence groups, parameters, concepts,
  failures
- **Edges** are typed relationships with **bidirectional invariants**: if
  claim C-024 depends on assumption A-007, then A-007 must list C-024 in
  `used_in_claims`

This is not a chain (linear). It's not a tree (single parent). It's a
**web** — a directed graph with multiple node types, multiple edge types, and
cross-cutting constraints.

### 4.2 The Core Nouns

| Noun | Role | Key Relationships |
|------|------|-------------------|
| **Claim** | Atomic falsifiable assertion | depends_on → Claims, assumptions → Assumptions, verified_by → Scripts |
| **Assumption** | Premise taken as given | used_in_claims → Claims (bidirectional with claim.assumptions) |
| **Prediction** | Testable consequence of claims | claim_id → Claim, script → Script, independence_group → IndependenceGroup |
| **Script** | Verification program | claims_covered → Claims (bidirectional with claim.verified_by) |
| **Independence Group** | Predictions sharing derivation | member_predictions → Predictions (bidirectional with prediction.independence_group) |
| **Hypothesis** | Higher-level theoretical path | related_claims → Claims, related_predictions → Predictions |
| **Discovery** | Significant research finding | references (free-form) |
| **Failure** | Known problem or dead end | related_predictions, related_claims (advisory) |
| **Parameter** | Physical/mathematical constant | referenced by scripts at runtime |
| **Concept** | Defined vocabulary term | standalone |

### 4.3 The Invariants

These are the hard rules that define a consistent epistemic web:

1. **Bidirectional link integrity**: If A references B, B must back-reference A
   (claim↔assumption, claim↔script, prediction↔independence_group)
2. **Referential integrity**: Every referenced ID must exist
3. **Acyclicity**: Claim `depends_on` graph must be a DAG — no circular reasoning
4. **Tier constraints**: Tier A predictions must have 0 free parameters;
   Tier B must state `conditional_on`; measured predictions must have observed
   values
5. **Independence semantics**: Predictions in the same group share derivation;
   every pair of groups must document their separation basis
6. **Coverage**: Numerical claims should have verification scripts;
   empirical [E]-type assumptions need falsifiable consequences

### 4.4 Domain-General by Design

Horizon's vocabulary is chosen to be **domain-neutral without sacrificing
power for quantitative domains**. The entity names, relationship types, and
invariants are properties of sound empirical reasoning, not of any specific
field.

The naming principle: use the most general term that preserves the concept's
meaning. If a term sounds "physics-y" but is actually standard across
empirical disciplines, keep it. If it genuinely narrows the concept, rename
it.

| Horizon Term | Why It's General |
|-------------|-----------------|
| **Claim** | Any falsifiable assertion. Physics: "E8 predicts W mass." Medicine: "Drug X reduces mortality." ML: "Attention suffices for sequences." |
| **Assumption** | A premise taken as given. Exists in every empirical field. |
| **Prediction** | A testable consequence. Not physics-specific — every empirical discipline makes predictions. |
| **Independence Group** | Evidence clusters that share derivation. Applies to medicine (correlated endpoints), ML (correlated benchmarks), social science (non-independent samples). |
| **Confidence Tier (A/B/C)** | How strongly constrained the prediction is. A = zero free parameters. B = conditional. C = fit/consistency. This hierarchy applies to any quantitative discipline. |
| **Measurement Regime** | Whether evidence exists: measured, bound_only, unmeasured. Medicine uses "observed/censored." ML uses "evaluated/not_evaluated." The abstraction is the same: is evidence available? |
| **Specification** | The relationship being tested. Physics: a formula. Medicine: a statistical model. ML: a performance metric. |
| **Verification Script** | A program that checks a prediction. Language-agnostic, domain-agnostic. |

**What we don't do**: invent new jargon. "Claim" is clearer than "epistemic
assertion." "Prediction" is clearer than "testable consequence node." Keep
the vocabulary close to how researchers actually talk.

**Power for quantitative domains**: The tier system, tolerance-based
verification, numeric predictions with observed/predicted values, free
parameter counting, and sensitivity analysis all serve quantitative work
(physics, ML, computational biology, economics) without being physics-specific.
Qualitative domains (history, philosophy, some social science) can use the
same entities with `category: "qualitative"` and descriptive rather than
numeric predictions.

### 4.5 Vocabulary Mapping Guide

Different fields use different vocabulary for the same concepts. Horizon
uses general terms; researchers should map their domain language:

| Horizon | Physics | Medicine | Machine Learning | Social Science |
|---------|---------|----------|-----------------|----------------|
| Claim | Theoretical prediction | Hypothesis | Architecture claim | Theory |
| Assumption | Physical/mathematical premise | Study assumption | Training assumption | Methodological assumption |
| Prediction | Observable quantity | Primary endpoint | Benchmark score | Measured outcome |
| Tier A | Zero free params | Pre-registered primary | Zero-shot eval | Pre-registered |
| Tier B | Conditional prediction | Secondary endpoint | Few-shot eval | Exploratory |
| Measurement Regime: measured | Published data | Trial completed | Benchmark scored | Survey collected |
| Measurement Regime: bound_only | Upper/lower bound | Interim analysis | Partial eval | Pilot data |
| Independence Group | Sector (electroweak, QCD) | Organ system | Task family | Study population |
| Specification | Mathematical formula | Statistical model spec | Metric definition | Operationalization |

### 4.6 What the Web Looks Like Across Domains

**Physics:**
```
Claim: "E8 predicts the W boson mass"
  └─ Assumption: "Gauge group is compact and simple"
  └─ Prediction: "W mass = 80.379 GeV" (Tier A, measured, observed=80.377)
       └─ Script: gauge_couplings.py
       └─ IndependenceGroup: "electroweak_sector"
```

**Machine Learning:**
```
Claim: "Attention is sufficient for sequence modeling"
  └─ Assumption: "Training data is i.i.d."
  └─ Prediction: "BLEU > 28.0 on WMT14 EN-DE" (Tier A, measured, observed=28.4)
       └─ Script: train_and_evaluate.py
       └─ IndependenceGroup: "translation_benchmarks"
```

**Medicine:**
```
Claim: "Drug X reduces mortality in population Y"
  └─ Assumption: "No unmeasured confounders"
  └─ Prediction: "Hazard ratio < 0.8" (Tier RCT, measured, observed=0.72)
       └─ Script: survival_analysis.R
       └─ IndependenceGroup: "cardiovascular_endpoints"
```

Same structure. Same invariants. Different vocabulary.

---

## 5. Phase 1 — Domain Core

**Goal:** Build and fully test the epistemic web with zero I/O, zero
dependencies. This is the gravity well — get it right, and everything else
falls into place.

### 5.1 Type Foundation (`epistemic/types.py`)

```python
"""Value types and type aliases for the epistemic domain.

No external dependencies. No I/O. Pure data definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType


# ── Typed identifiers ─────────────────────────────────────────────
# NewType gives nominal typing: ClaimId and ScriptId are both str at
# runtime, but the type checker treats them as distinct types.

ClaimId = NewType("ClaimId", str)
AssumptionId = NewType("AssumptionId", str)
PredictionId = NewType("PredictionId", str)
HypothesisId = NewType("HypothesisId", str)
DiscoveryId = NewType("DiscoveryId", str)
ScriptId = NewType("ScriptId", str)
IndependenceGroupId = NewType("IndependenceGroupId", str)
ParameterId = NewType("ParameterId", str)
ConceptId = NewType("ConceptId", str)
FailureId = NewType("FailureId", str)


# ── Severity ──────────────────────────────────────────────────────

class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class Finding:
    """One validation result."""
    severity: Severity
    source: str
    message: str


# ── Confidence tiers ──────────────────────────────────────────────

class ConfidenceTier(Enum):
    """How strongly a prediction is constrained.
    A: Zero free parameters — pure prediction from theory.
    B: Conditional on stated assumptions beyond the core theory.
    C: Fit/consistency check — not a novel prediction.
    """
    A = "A"
    B = "B"
    C = "C"


# ── Evidence classification ───────────────────────────────────────

class EvidenceKind(Enum):
    NOVEL_PREDICTION = "novel_prediction"
    RETRODICTION = "retrodiction"
    FIT_CONSISTENCY = "fit_consistency"


class MeasurementRegime(Enum):
    MEASURED = "measured"
    BOUND_ONLY = "bound_only"
    UNMEASURED = "unmeasured"


class PredictionStatus(Enum):
    CONFIRMED = "CONFIRMED"
    STRESSED = "STRESSED"
    REFUTED = "REFUTED"
    PENDING = "PENDING"
    NOT_YET_TESTABLE = "NOT_YET_TESTABLE"


class FailureStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"
```

**Principles:** Encapsulation (typed IDs prevent mixing), KISS (plain enums
and dataclasses), Open/Closed (tiers can become registry-based later without
changing the interface).

### 5.2 Entity Classes (`epistemic/model.py`)

All entities use native Python types: `set`, `list`, `dict`. No `frozenset`,
no `tuple`, no `Mapping`. Relationships are expressed through typed ID
references, not object references.

```python
"""Core epistemic entities.

Relationships are ID references, not object references. To traverse
the graph, go through the EpistemicWeb.

Native Python collections throughout: set, list, dict. The web is
the encapsulation boundary, not the type system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .types import (
    AssumptionId, ClaimId, ConfidenceTier, DiscoveryId, EvidenceKind,
    FailureId, FailureStatus, HypothesisId, IndependenceGroupId,
    MeasurementRegime, ParameterId, PredictionId, PredictionStatus, ScriptId,
)


@dataclass
class Claim:
    """An atomic, falsifiable assertion.
    depends_on forms a DAG. assumptions and verified_by have bidirectional
    links maintained by the EpistemicWeb.
    """
    id: ClaimId
    statement: str
    type: str                                    # "foundational" | "derived"
    scope: str                                   # "global", "domain-specific"
    falsifiability: str
    category: str = "qualitative"                # "numerical" | "qualitative"
    assumptions: set[AssumptionId] = field(default_factory=set)
    depends_on: set[ClaimId] = field(default_factory=set)
    verified_by: set[ScriptId] = field(default_factory=set)


@dataclass
class Assumption:
    """A premise taken as given."""
    id: AssumptionId
    statement: str
    type: str                                    # "E" (empirical), "M" (methodological)
    scope: str
    used_in_claims: set[ClaimId] = field(default_factory=set)
    falsifiable_consequence: str | None = None
    notes: str | None = None


@dataclass
class Prediction:
    """A testable consequence of one or more claims."""
    id: PredictionId
    observable: str
    tier: ConfidenceTier
    status: PredictionStatus
    evidence_kind: EvidenceKind
    measurement_regime: MeasurementRegime
    predicted: Any                               # the predicted value/outcome
    specification: str | None = None             # human-readable formula/relationship being tested
    claim_id: ClaimId | None = None
    script: ScriptId | None = None
    independence_group: IndependenceGroupId | None = None
    correlation_tags: set[str] = field(default_factory=set)
    observed: Any = None
    observed_bound: Any = None
    free_params: int = 0
    conditional_on: str | None = None
    falsifier: str | None = None
    benchmark_source: str | None = None
    notes: str | None = None


@dataclass
class IndependenceGroup:
    """Predictions sharing a common derivation chain.
    member_predictions is bidirectional with Prediction.independence_group.
    """
    id: IndependenceGroupId
    label: str
    claim_lineage: set[ClaimId] = field(default_factory=set)
    assumption_lineage: set[AssumptionId] = field(default_factory=set)
    member_predictions: set[PredictionId] = field(default_factory=set)
    measurement_regime: str | None = None
    notes: str | None = None


@dataclass
class PairwiseSeparation:
    """Documents why two independence groups are genuinely separate."""
    group_a: IndependenceGroupId
    group_b: IndependenceGroupId
    basis: str


@dataclass
class Script:
    """A verification program that checks whether predictions hold."""
    id: ScriptId
    command: str
    claims_covered: set[ClaimId] = field(default_factory=set)
    machine_readable_output: bool = False
    requires_network: bool = False
    requires_sandbox: bool = True
    notes: str | None = None


@dataclass
class Hypothesis:
    """A higher-level theoretical path being explored."""
    id: HypothesisId
    title: str
    status: str
    summary: str | None = None
    related_claims: set[ClaimId] = field(default_factory=set)
    related_predictions: set[PredictionId] = field(default_factory=set)


@dataclass
class Discovery:
    """A significant finding during research."""
    id: DiscoveryId
    title: str
    date: date
    summary: str
    impact: str
    status: str
    references: list[str] = field(default_factory=list)


@dataclass
class Failure:
    """A known problem or dead end."""
    id: FailureId
    title: str
    description: str
    status: FailureStatus
    session_opened: int
    session_resolved: int | None = None
    related_predictions: set[PredictionId] = field(default_factory=set)
    related_claims: set[ClaimId] = field(default_factory=set)


@dataclass
class Concept:
    """A defined term in the project vocabulary."""
    id: ConceptId
    sort_order: int
    term: str
    definition: str
    aliases: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


@dataclass
class Parameter:
    """A physical or mathematical constant referenced by verification scripts.

    Parameters live in project/data/parameters.json and are read by
    scripts at runtime. The sandbox executor makes them available as
    structured input so scripts don't hard-code constants.
    """
    id: ParameterId
    name: str
    value: Any                          # numeric, string, or structured
    unit: str | None = None             # SI or domain unit, human-readable
    uncertainty: Any = None             # absolute uncertainty, same type as value
    source: str | None = None           # citation or derivation note
    notes: str | None = None
```

**Principles:**
- **Single Responsibility**: Each entity describes one epistemic concept.
  No entity knows how to serialize itself or render to markdown.
- **Law of Demeter**: Entities hold IDs, not object references. To traverse,
  go through the web.
- **Composition over Inheritance**: No entity inherits from another. Shared
  structural patterns (has status, has notes) are coincidence, not hierarchy.
- **KISS**: Plain dataclasses, native Python types.
- **Encapsulation**: External code should use the web's methods to mutate
  entities, not modify entity fields directly.

### 5.3 The Aggregate Root (`epistemic/web.py`)

The `EpistemicWeb` is the **single entry point for all domain operations**.
It enforces every invariant. External code never modifies entities directly —
it calls methods on the web, and the web ensures consistency.

```python
"""The EpistemicWeb: aggregate root for the epistemic domain.

External code NEVER modifies entities directly — it calls methods on the
web, and the web ensures consistency.

Every mutation method returns a NEW web. This gives free undo/redo and
eliminates state corruption.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .model import (
    Assumption, Claim, Concept, Discovery, Failure, Hypothesis,
    IndependenceGroup, PairwiseSeparation, Parameter, Prediction, Script,
)
from .types import (
    AssumptionId, ClaimId, ConceptId, DiscoveryId, FailureId, Finding,
    HypothesisId, IndependenceGroupId, ParameterId, PredictionId, ScriptId, Severity,
)


@dataclass
class EpistemicWeb:
    """Complete epistemic state of a research project.

    All mutations go through methods that enforce invariants and return
    a new web. The old web is left untouched (free rollback).
    """
    claims: dict[ClaimId, Claim] = field(default_factory=dict)
    assumptions: dict[AssumptionId, Assumption] = field(default_factory=dict)
    predictions: dict[PredictionId, Prediction] = field(default_factory=dict)
    hypotheses: dict[HypothesisId, Hypothesis] = field(default_factory=dict)
    discoveries: dict[DiscoveryId, Discovery] = field(default_factory=dict)
    scripts: dict[ScriptId, Script] = field(default_factory=dict)
    independence_groups: dict[IndependenceGroupId, IndependenceGroup] = field(
        default_factory=dict
    )
    pairwise_separations: list[PairwiseSeparation] = field(default_factory=list)
    failures: dict[FailureId, Failure] = field(default_factory=dict)
    concepts: dict[ConceptId, Concept] = field(default_factory=dict)
    parameters: dict[ParameterId, Parameter] = field(default_factory=dict)

    # ── Queries ───────────────────────────────────────────────────

    def get_claim(self, cid: ClaimId) -> Claim | None:
        return self.claims.get(cid)

    def get_assumption(self, aid: AssumptionId) -> Assumption | None:
        return self.assumptions.get(aid)

    def get_prediction(self, pid: PredictionId) -> Prediction | None:
        return self.predictions.get(pid)

    def claims_using_assumption(self, aid: AssumptionId) -> set[ClaimId]:
        """All claims that reference this assumption."""
        return {cid for cid, c in self.claims.items() if aid in c.assumptions}

    def claim_lineage(self, cid: ClaimId) -> set[ClaimId]:
        """Transitive closure of depends_on (all ancestors of a claim)."""
        visited: set[ClaimId] = set()
        stack = [cid]
        while stack:
            current = stack.pop()
            claim = self.claims.get(current)
            if claim is None:
                continue
            for dep in claim.depends_on:
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def assumption_lineage(self, cid: ClaimId) -> set[AssumptionId]:
        """All assumptions reachable through a claim and its ancestors."""
        all_claims = self.claim_lineage(cid) | {cid}
        result: set[AssumptionId] = set()
        for ancestor_id in all_claims:
            claim = self.claims.get(ancestor_id)
            if claim:
                result.update(claim.assumptions)
        return result

    # ── Mutations (return new web) ────────────────────────────────

    def register_claim(self, claim: Claim) -> EpistemicWeb:
        """Add a claim. Enforces: no duplicates, refs exist, no cycles,
        bidirectional links updated."""
        if claim.id in self.claims:
            raise DuplicateIdError(f"Claim {claim.id} already exists")
        self._check_refs_exist(claim.assumptions, self.assumptions, "assumption")
        self._check_refs_exist(claim.depends_on, self.claims, "claim")
        self._check_refs_exist(claim.verified_by, self.scripts, "script")
        self._check_no_cycle_with(claim)

        new = self._copy()
        # Deep-copy the incoming entity so a caller who keeps a reference
        # cannot mutate the web's stored copy after registration. All
        # register_* methods follow this same pattern.
        new.claims[claim.id] = copy.deepcopy(claim)

        # Maintain bidirectional: assumption.used_in_claims
        for aid in claim.assumptions:
            new.assumptions[aid].used_in_claims.add(claim.id)

        # Maintain bidirectional: script.claims_covered
        for sid in claim.verified_by:
            new.scripts[sid].claims_covered.add(claim.id)

        return new

    def register_assumption(self, assumption: Assumption) -> EpistemicWeb:
        """Add an assumption."""
        if assumption.id in self.assumptions:
            raise DuplicateIdError(f"Assumption {assumption.id} already exists")
        new = self._copy()
        new.assumptions[assumption.id] = assumption
        return new

    def register_prediction(self, prediction: Prediction) -> EpistemicWeb:
        """Add a prediction. Enforces: refs exist, bidirectional group link."""
        if prediction.id in self.predictions:
            raise DuplicateIdError(f"Prediction {prediction.id} already exists")
        if prediction.claim_id and prediction.claim_id not in self.claims:
            raise BrokenReferenceError(
                f"Claim {prediction.claim_id} does not exist"
            )
        if prediction.script and prediction.script not in self.scripts:
            raise BrokenReferenceError(
                f"Script {prediction.script} does not exist"
            )
        if prediction.independence_group:
            if prediction.independence_group not in self.independence_groups:
                raise BrokenReferenceError(
                    f"Independence group {prediction.independence_group} does not exist"
                )

        new = self._copy()
        new.predictions[prediction.id] = prediction

        # Maintain bidirectional: group.member_predictions
        if prediction.independence_group:
            new.independence_groups[prediction.independence_group].member_predictions.add(
                prediction.id
            )

        return new

    def register_script(self, script: Script) -> EpistemicWeb:
        """Add a verification script."""
        if script.id in self.scripts:
            raise DuplicateIdError(f"Script {script.id} already exists")
        new = self._copy()
        new.scripts[script.id] = script
        return new

    def register_hypothesis(self, hypothesis: Hypothesis) -> EpistemicWeb:
        if hypothesis.id in self.hypotheses:
            raise DuplicateIdError(f"Hypothesis {hypothesis.id} already exists")
        new = self._copy()
        new.hypotheses[hypothesis.id] = hypothesis
        return new

    def register_independence_group(self, group: IndependenceGroup) -> EpistemicWeb:
        if group.id in self.independence_groups:
            raise DuplicateIdError(f"Independence group {group.id} already exists")
        new = self._copy()
        new.independence_groups[group.id] = group
        return new

    def register_discovery(self, discovery: Discovery) -> EpistemicWeb:
        if discovery.id in self.discoveries:
            raise DuplicateIdError(f"Discovery {discovery.id} already exists")
        new = self._copy()
        new.discoveries[discovery.id] = discovery
        return new

    def register_failure(self, failure: Failure) -> EpistemicWeb:
        if failure.id in self.failures:
            raise DuplicateIdError(f"Failure {failure.id} already exists")
        new = self._copy()
        new.failures[failure.id] = failure
        return new

    def register_concept(self, concept: Concept) -> EpistemicWeb:
        if concept.id in self.concepts:
            raise DuplicateIdError(f"Concept {concept.id} already exists")
        new = self._copy()
        new.concepts[concept.id] = concept
        return new

    def add_pairwise_separation(self, sep: PairwiseSeparation) -> EpistemicWeb:
        """Document why two independence groups are separate."""
        if sep.group_a not in self.independence_groups:
            raise BrokenReferenceError(f"Group {sep.group_a} does not exist")
        if sep.group_b not in self.independence_groups:
            raise BrokenReferenceError(f"Group {sep.group_b} does not exist")
        new = self._copy()
        new.pairwise_separations.append(sep)
        return new

    def transition_prediction(
        self, pid: PredictionId, new_status: PredictionStatus
    ) -> EpistemicWeb:
        """Change a prediction's status."""
        if pid not in self.predictions:
            raise BrokenReferenceError(f"Prediction {pid} does not exist")
        new = self._copy()
        new.predictions[pid].status = new_status
        return new

    def transition_failure(
        self, fid: FailureId, new_status: FailureStatus,
        session_resolved: int | None = None,
    ) -> EpistemicWeb:
        """Change a failure's status, with side effects."""
        if fid not in self.failures:
            raise BrokenReferenceError(f"Failure {fid} does not exist")
        new = self._copy()
        new.failures[fid].status = new_status
        if new_status == FailureStatus.RESOLVED and session_resolved is not None:
            new.failures[fid].session_resolved = session_resolved
        elif new_status == FailureStatus.ACTIVE:
            new.failures[fid].session_resolved = None
        return new

    # ── Invariant checks ──────────────────────────────────────────

    def _check_refs_exist(self, ids: set, registry: dict, label: str) -> None:
        missing = ids - registry.keys()
        if missing:
            raise BrokenReferenceError(f"Non-existent {label}(s): {missing}")

    def _check_no_cycle_with(self, claim: Claim) -> None:
        """Verify adding this claim doesn't create a cycle in depends_on."""
        visited: set[ClaimId] = set()
        stack = list(claim.depends_on)
        while stack:
            current = stack.pop()
            if current == claim.id:
                raise CycleError(
                    f"Adding {claim.id} would create a dependency cycle"
                )
            if current in visited:
                continue
            visited.add(current)
            upstream = self.claims.get(current)
            if upstream:
                stack.extend(upstream.depends_on)

    def _copy(self) -> EpistemicWeb:
        """Deep copy for copy-on-write mutation semantics.

        O(n) cost per mutation where n is total entity count. Acceptable
        for research-scale webs (hundreds to low thousands of entities).
        If this becomes a bottleneck, structural sharing of unchanged
        sub-dicts is the migration path — not a change to make speculatively.
        """
        return copy.deepcopy(self)


# ── Domain exceptions ─────────────────────────────────────────────

class EpistemicError(Exception):
    """Base for all domain errors."""

class DuplicateIdError(EpistemicError):
    pass

class BrokenReferenceError(EpistemicError):
    pass

class CycleError(EpistemicError):
    pass

class InvariantViolation(EpistemicError):
    pass
```

**Principles:**
- **Encapsulation**: The web is the only way to mutate the graph. Invariants
  are enforced at every mutation.
- **Abstraction**: `web.register_claim(claim)` hides all back-reference
  bookkeeping.
- **DRY**: Bidirectional link maintenance happens in exactly one place per
  relationship. The current Horizon system maintains these in gateway
  registration AND validates them after the fact. Here, they're maintained
  at the point of mutation.
- **Single Responsibility**: The web enforces graph consistency. It does not
  serialize, render, or execute anything.
- **KISS**: `_copy()` + mutate is the simplest possible immutable update
  pattern. No event system, no observer pattern.
- **Fail Fast**: Throws immediately on broken references or cycles.

### 5.4 Cross-Entity Validation (`epistemic/invariants.py`)

```python
"""Validation rules that span multiple entities.

These require looking at the web as a whole. Each function is pure:
(EpistemicWeb) -> list[Finding].

Structural invariants (refs exist, no cycles, bidirectional links) live
in web.py and are enforced at mutation time.

Semantic/coverage invariants live here and are checked on demand.
"""
from __future__ import annotations

from .types import Finding, Severity
from .web import EpistemicWeb


def validate_tier_constraints(web: EpistemicWeb) -> list[Finding]:
    """Tier A: 0 free params. Tier B: must state conditional_on."""
    findings: list[Finding] = []
    for pid, pred in web.predictions.items():
        if pred.tier.value == "A" and pred.free_params != 0:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                f"Tier A prediction has {pred.free_params} free params (must be 0)",
            ))
        if pred.tier.value == "B" and not pred.conditional_on:
            findings.append(Finding(
                Severity.WARNING,
                f"predictions/{pid}",
                "Tier B prediction missing 'conditional_on'",
            ))
        if pred.measurement_regime.value == "measured" and pred.observed is None:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime='measured' requires an observed value",
            ))
        if pred.measurement_regime.value == "bound_only" and pred.observed_bound is None:
            findings.append(Finding(
                Severity.CRITICAL,
                f"predictions/{pid}",
                "measurement_regime='bound_only' requires observed_bound",
            ))
    return findings


def validate_independence_semantics(web: EpistemicWeb) -> list[Finding]:
    """Groups must have consistent back-refs. Every pair needs separation basis."""
    findings: list[Finding] = []

    # Check group membership consistency
    for gid, group in web.independence_groups.items():
        for pid in group.member_predictions:
            pred = web.predictions.get(pid)
            if pred is None:
                continue
            if pred.independence_group != gid:
                findings.append(Finding(
                    Severity.CRITICAL,
                    f"independence_groups/{gid}",
                    f"Prediction {pid} listed but doesn't back-reference this group",
                ))

    # Check pairwise separation completeness
    group_ids = sorted(web.independence_groups.keys())
    seen_pairs: set[tuple[str, str]] = set()
    for ps in web.pairwise_separations:
        pair = (min(ps.group_a, ps.group_b), max(ps.group_a, ps.group_b))
        seen_pairs.add(pair)

    for i, a in enumerate(group_ids):
        for b in group_ids[i + 1:]:
            pair = (min(a, b), max(a, b))
            if pair not in seen_pairs:
                findings.append(Finding(
                    Severity.CRITICAL,
                    "independence_groups/pairwise_separation_basis",
                    f"Missing pairwise separation for ({a}, {b})",
                ))

    return findings


def validate_coverage(web: EpistemicWeb) -> list[Finding]:
    """Check for verification gaps."""
    findings: list[Finding] = []

    for cid, claim in web.claims.items():
        if claim.category == "numerical" and not claim.verified_by:
            findings.append(Finding(
                Severity.INFO,
                f"claims/{cid}",
                "Numerical claim lacks verification script",
            ))

    for aid, assumption in web.assumptions.items():
        if assumption.type == "E" and not assumption.falsifiable_consequence:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "Empirical [E] assumption has no falsifiable consequence",
            ))

    stressed = [
        pid for pid, p in web.predictions.items()
        if p.status.value == "STRESSED"
    ]
    if stressed:
        findings.append(Finding(
            Severity.WARNING,
            "predictions",
            f"STRESSED predictions requiring vigilance: {stressed}",
        ))

    return findings


def validate_all(web: EpistemicWeb) -> list[Finding]:
    """Run all domain validators."""
    return (
        validate_tier_constraints(web)
        + validate_independence_semantics(web)
        + validate_coverage(web)
    )
```

**Principles:**
- **Open/Closed**: Add new validators as new functions. `validate_all` is the
  composition point.
- **DRY**: Each rule exists once.
- **Polymorphism**: All validators have signature `(EpistemicWeb) -> list[Finding]`.

### 5.5 Ports (`epistemic/ports.py`)

```python
"""Abstract interfaces the domain REQUIRES but does not IMPLEMENT.

Implemented by the adapters layer. Domain code programs against these
protocols, never against concrete classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .types import Finding
from .web import EpistemicWeb


class WebRepository(Protocol):
    """Load and save the epistemic web."""
    def load(self) -> EpistemicWeb: ...
    def save(self, web: EpistemicWeb) -> None: ...


class WebRenderer(Protocol):
    """Generate human-readable artifacts from the web."""
    def render(self, web: EpistemicWeb) -> dict[str, str]:
        """Return {relative_path: content} for all generated surfaces."""
        ...


class WebValidator(Protocol):
    """Validate the web and return findings."""
    def validate(self, web: EpistemicWeb) -> list[Finding]: ...


class ProseSync(Protocol):
    """Update managed prose blocks derived from canonical state."""
    def sync(self, web: EpistemicWeb) -> dict[str, object]: ...


class TransactionLog(Protocol):
    """Append provenance for gateway mutations and queries."""
    def append(self, operation: str, identifier: str) -> str: ...


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


class ScriptExecutor(Protocol):
    """Execute a verification script in a controlled environment."""
    def execute(
        self, script_id: str, command: str, **policy: object
    ) -> ExecutionResult: ...
```

**Principles:**
- **Dependency Inversion**: Domain defines what it needs. Infrastructure
  conforms.
- **Interface Segregation**: Each port is as narrow as possible. Read-only
  consumers only need `load()`.

### 5.6 Phase 1 Deliverables and Tests

| Step | What | Tests |
|------|------|-------|
| 1.1 | `epistemic/types.py` — IDs, enums, Finding | Enum membership, Finding construction |
| 1.2 | `epistemic/model.py` — All entity dataclasses, including `Parameter` | Construction, field defaults; verify `Parameter` round-trips value/unit/uncertainty |
| 1.3 | `epistemic/web.py` — EpistemicWeb with register methods | Happy path: register each entity type |
| 1.4 | `epistemic/web.py` — Rejection cases | Duplicate ID, broken reference, cycle detection |
| 1.5 | `epistemic/web.py` — Bidirectional links | Register claim → assumption.used_in_claims auto-updated |
| 1.6 | `epistemic/web.py` — Lineage queries | claim_lineage, assumption_lineage on multi-level graphs |
| 1.7 | `epistemic/invariants.py` — All validators | Build webs with known violations, assert findings |
| 1.8 | `epistemic/ports.py` — Protocol definitions | No tests (type definitions only) |

**Target: ~80 tests. All pure Python, no I/O, run in milliseconds.**

Example test session after Phase 1:

```python
from epistemic.domain.web import EpistemicWeb
from epistemic.domain.model import Assumption, Claim
from epistemic.domain.types import AssumptionId, ClaimId

web = EpistemicWeb()
web = web.register_assumption(Assumption(
    id=AssumptionId("A-001"),
    statement="The gauge group is compact and simple",
    type="P", scope="global",
))
web = web.register_claim(Claim(
    id=ClaimId("C-001"),
    statement="Particle spectrum follows from E8 structure",
    type="P", scope="global",
    falsifiability="Predict wrong particle masses",
    assumptions={AssumptionId("A-001")},
))
# A-001.used_in_claims is now {"C-001"} — maintained automatically
assert ClaimId("C-001") in web.assumptions[AssumptionId("A-001")].used_in_claims
```

### Phase 1 Exit Criteria

- [ ] All entity types constructable with native Python types
- [ ] Every register method enforces referential integrity
- [ ] Bidirectional links maintained on register for all three pairs
- [ ] Cycle detection on claim.depends_on works
- [ ] All invariant validators return correct findings
- [ ] Zero imports from outside stdlib

---

## 6. Phase 2 — Persistence, Testing, and Packaging

**Goal:** The domain model can load/save the same JSON files the current
Horizon system uses. The package is installable. Tests cover round-trips.

### 6.1 JSON Repository (`adapters/json_repository.py`)

Reads and writes the flat JSON files from `project/data/`. Handles the
current schema shapes (`claims/v1`, `predictions/v2`, etc.).

```python
"""Flat-JSON persistence adapter.

Implements WebRepository. Reads the same file structure as the current
Horizon system for backward compatibility.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..domain.model import Assumption, Claim, Prediction, Script, ...
from ..domain.ports import WebRepository
from ..domain.types import ClaimId, AssumptionId, ...
from ..domain.web import EpistemicWeb


class JsonFileRepository:
    """Load/save the epistemic web from flat JSON files on disk."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def load(self) -> EpistemicWeb:
        # Constructs EpistemicWeb directly from JSON dicts, bypassing the
        # register_* mutation methods. This is intentional: load() restores
        # a previously validated and persisted state, not an untrusted
        # payload. Consequence: bidirectional links must be correct in the
        # JSON (the gateway ensures this on every save). If the JSON was
        # manually edited and links are inconsistent, validate() will catch
        # it. Add parameters here when Parameter persistence is implemented.
        return EpistemicWeb(
            claims=self._load_claims(),
            assumptions=self._load_assumptions(),
            predictions=self._load_predictions(),
            scripts=self._load_scripts(),
            independence_groups=self._load_independence_groups(),
            hypotheses=self._load_hypotheses(),
            discoveries=self._load_discoveries(),
            failures=self._load_failures(),
            concepts=self._load_concepts(),
            parameters=self._load_parameters(),
            pairwise_separations=self._load_pairwise_separations(),
        )

    def save(self, web: EpistemicWeb) -> None:
        self._save_claims(web.claims)
        self._save_assumptions(web.assumptions)
        # ... each entity type

    def _load_claims(self) -> dict[ClaimId, Claim]:
        raw = self._read_json("claims.json")
        return {
            ClaimId(k): Claim(
                id=ClaimId(k),
                statement=v["statement"],
                type=v["type"],
                scope=v["scope"],
                falsifiability=v["falsifiability"],
                category=v.get("category", "qualitative"),
                assumptions={AssumptionId(a) for a in v.get("assumptions", [])},
                depends_on={ClaimId(d) for d in v.get("depends_on", [])},
                verified_by={ScriptId(s) for s in v.get("verified_by", [])},
            )
            for k, v in raw.get("claims", {}).items()
        }

    def _read_json(self, filename: str) -> dict:
        path = self._data_dir / filename
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def _write_json(self, filename: str, data: dict) -> None:
        path = self._data_dir / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
```

### 6.2 In-Memory Repository

```python
"""In-memory repository for tests. No disk I/O."""

class InMemoryRepository:
    def __init__(self, web: EpistemicWeb | None = None) -> None:
        self._web = web or EpistemicWeb()

    def load(self) -> EpistemicWeb:
        return self._web

    def save(self, web: EpistemicWeb) -> None:
        self._web = web
```

**Liskov Substitution**: `InMemoryRepository` and `JsonFileRepository` are
interchangeable. Tests use in-memory. Production uses JSON.

### 6.3 Packaging

```toml
[project]
name = "horizon-research"
version = "0.2.0"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1,<9",
    "rich>=13,<14",
]

[project.scripts]
horizon = "horizon_research.cli.main:main"
horizon-research = "horizon_research.cli.main:main"

[project.optional-dependencies]
mcp = ["fastmcp>=2,<3"]
compute = ["numpy>=2.4,<3", "scipy>=1.17,<2"]
dev = ["pytest>=8.3,<9", "pytest-cov>=6,<7", "ruff>=0.11,<0.12"]
```

Core package depends only on `click` (CLI framework) and `rich` (terminal
output). These two libraries directly improve the user experience — every
`horizon` command benefits from better argument parsing and beautiful output.
Compute libraries are opt-in for verification scripts that need them.

Use `horizon_research` as the public and internal package root. The stable
contract is the `horizon_research` import root plus the `horizon` console
script; `epistemic/` stays nested inside that package as the kernel rather
than becoming the package root.

```python
# src/horizon_research/__main__.py
from horizon_research.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
```

This keeps `python -m horizon_research` and the console-script entrypoint
stable while the internal subpackages evolve.

Packaging contracts should be tested as code, not left implicit in prose:

- `pyproject.toml` declares the public console scripts and extras
- `horizon_research.__main__` supports `python -m horizon_research`
- coverage settings and workflow artifact expectations are locked by tests
- editable-install smoke tests happen in Phase 2; wheel and sdist smoke tests
    become mandatory by the Phase 4 exit criteria

### 6.4 Phase 2 Deliverables

| Step | What | Tests |
|------|------|-------|
| 2.1 | `adapters/json_repository.py` — load all entity types from JSON, including `Parameter` | Round-trip: construct web → save → load → compare; verify Parameter value/unit/uncertainty survive round-trip |
| 2.2 | Schema evolution — handle v1/v2 JSON variants | Load v1 fixture, assert correct domain objects |
| 2.3 | `InMemoryRepository` | Already trivial — verify protocol compliance |
| 2.4 | `pyproject.toml` + `src/horizon_research/` package — installable product boundary | `pip install -e .`, console-script smoke, `python -m horizon_research` |
| 2.5 | Contract tests for packaging, config, and workflow surfaces | Parse `pyproject.toml`, default paths, coverage settings, workflow artifact contract |
| 2.6 | Schema versioning — add `_schema_version` top-level key to every JSON data file | Loader asserts version presence; migration registry maps `(from, to, transform_fn)` per resource type |

### Phase 2 Exit Criteria

- [ ] `JsonFileRepository` can load and save all entity types
- [ ] Save→load round trip produces identical domain objects
- [ ] Package installs cleanly with `pip install -e .`
- [ ] Public console scripts and `python -m horizon_research` are stable
- [ ] Packaging/config/workflow contracts are locked by tests
- [ ] Every JSON data file carries `_schema_version`; migration registry exists even if empty

---

## 7. Phase 3 — Gateway and Control-Plane Services

**Goal:** Build the product layer that makes Horizon a control plane again:
`ProjectContext`, a typed gateway, read-only services, and the explicit write
transaction boundary.

This phase is where the rebuild stops looking like a domain library and starts
looking like Horizon.

### 7.1 ProjectContext (`controlplane/context.py`)

Implement the runtime contract first. The control plane should build one
`ProjectContext` and thread it through gateway, validation, rendering, health,
status, and execution services.

```python
def build_project_context(workspace: Path) -> ProjectContext:
    config = load_config(workspace)
    project_dir = workspace / config.project_dir
    paths = ProjectPaths(
        workspace=workspace,
        project_dir=project_dir,
        data_dir=project_dir / "data",
        views_dir=project_dir / "views",
        knowledge_dir=project_dir / "knowledge",
        integrity_dir=project_dir / "integrity",
        verify_script_dir=project_dir / "src" / "verify",
        analysis_script_dir=project_dir / "src" / "analysis",
        cache_dir=project_dir / ".cache",
        render_cache_file=project_dir / ".cache" / "render.json",
        check_refs_cache_file=project_dir / ".cache" / "check_refs.json",
        query_transaction_log_file=project_dir / "logs" / "query_transactions.jsonl",
    )
    return ProjectContext(workspace=workspace, config=config, paths=paths)
```

### 7.2 Gateway (`controlplane/gateway.py`)

The gateway becomes the single external mutation and query boundary. The CLI,
future API surfaces, and automation should go through it instead of reaching
straight into the domain or repository.

```python
@dataclass
class GatewayResult:
    status: str
    changed: bool
    message: str
    findings: list[Finding]
    transaction_id: str | None = None


class Gateway:
    """Typed mutation/query boundary for the control plane."""

    def __init__(
        self,
        context: ProjectContext,
        repo: WebRepository,
        validator: WebValidator,
        renderer: WebRenderer,
        prose_sync: ProseSync,
        tx_log: TransactionLog,
    ) -> None:
        self._context = context
        self._repo = repo
        self._validator = validator
        self._renderer = renderer
        self._prose_sync = prose_sync
        self._tx_log = tx_log

    def register_claim(self, claim: Claim, *, dry_run: bool = False) -> GatewayResult:
        old_web = self._repo.load()
        new_web = old_web.register_claim(claim)
        findings = self._validator.validate(new_web)

        if any(f.severity == Severity.CRITICAL for f in findings):
            return GatewayResult(
                status="blocked",
                changed=False,
                message="registration blocked by CRITICAL findings",
                findings=findings,
            )

        if dry_run:
            return GatewayResult(
                status="ok",
                changed=True,
                message=f"dry run: claim {claim.id} would be registered",
                findings=findings,
            )

        self._repo.save(new_web)
        try:
            self._renderer.render(new_web)
            self._prose_sync.sync(new_web)
        except Exception:
            self._repo.save(old_web)
            self._renderer.render(old_web)
            self._prose_sync.sync(old_web)
            raise

        transaction_id = self._tx_log.append("register_claim", claim.id)
        return GatewayResult(
            status="ok",
            changed=True,
            message=f"registered claim {claim.id}",
            findings=findings,
            transaction_id=transaction_id,
        )
```

This preserves the old transactional idea, but in a cleaner way. The old
system needed raw file snapshots. The new system can usually roll back by
restoring the prior web, then rerendering and resyncing from that canonical
source of truth.

### 7.3 Read-Only Services

These remain separate from the gateway even though they all live in the
control-plane layer:

- `validate.py` — orchestrates domain validators plus structural/project
  checks (asset restrictions, repo layout, schemas, cross-references,
  constraints, coverage, prose consistency, scaling policy)
- `render.py` — derives markdown surfaces from canonical state. Uses
  **incremental SHA-256 fingerprinting**: hash each input JSON file, compare
  against a render cache; skip unchanged outputs. `--check` mode compares
  what _would_ be rendered against disk without writing (detects drift).
- `automation.py` — loads the declarative automation graph:
    - `render_outputs` declares source -> renderer -> path mappings
    - `session_close.stale_triggers` declares stale propagation rules
    - unknown renderers or malformed entries fail fast during normalization
    This keeps render/check/close wiring **open for extension, closed for
    modification**.
- `check.py` — four distinct operations:
  - `check-refs` — scan markdown for broken links (incremental, cached)
  - `check-stale` — find predictions stale due to parameter changes
    (driven by `automation_graph.json` rules, not hardcoded domain knowledge)
  - `sync-prose` — update `<!-- BEGIN AUTO:key -->` / `<!-- END AUTO:key -->`
    blocks inside hand-maintained markdown files
  - `verify-prose-sync` — read-only version of sync-prose (reports drift
    without modifying)
- `metrics.py` — pure computation, no I/O, no side effects:
  - `collect_repo_metrics(data)` — active failures, stressed predictions,
    active kill conditions, tier-A evidence
  - `collect_tier_a_evidence_metrics(predictions, groups)` —
    **correlation-aware** count of independent predictions (10 predictions
    from the same formula are weaker than 3 from separate derivation chains).
    Groups by `independence_group`, reports `raw_count`, `group_count`,
    `registry_backed_count`, and per-group details.
- `health.py` — composes validate, render-check, and project-structure checks
- `status.py` — consumes `metrics.py` output, formats for display. Bounded
  by the scaling policy (caps items per section as the project grows).
- `export.py` — bulk eject path

All depend on `ProjectContext`, the domain, and ports — not on the CLI.

### 7.4 The Transaction Boundary We Keep

Every write should still follow the same high-level shape:

1. Load canonical state
2. Apply one domain mutation
3. Validate the resulting web
4. Persist canonical state
5. Regenerate derived surfaces
6. Sync managed prose blocks if applicable
7. Append provenance / transaction log entry
8. Roll back to the prior web if downstream steps fail

This is one of the best ideas in the old architecture and should remain
central to the rebuild.

### 7.5 Mutation Provenance from Phase 3

Every gateway mutation (register, set, append, transition) should record
minimal provenance metadata on the affected resource:

```json
{
  "_last_modified": "2026-04-03T14:22:00Z",
  "_modified_by": "cli"
}
```

This is almost free — the gateway already writes JSON. It becomes
enormously valuable for:
- `horizon log claim C-003` (show mutation history per resource)
- Auditing prediction status changes
- Reproducibility claims in papers

In governance mode (Phase 7), extend with `_modification_session`. In
core-only mode, timestamps are sufficient.

Do not defer this to Phase 7. The cost of adding provenance at the gateway
level is near zero when the gateway is fresh, and retrofitting it later
requires a migration.

### 7.5 Phase 3 Deliverables

| Step | What | Tests |
|------|------|-------|
| 3.1 | `controlplane/context.py` — build `ProjectContext` from config | Default/custom project layout tests |
| 3.2 | `controlplane/gateway.py` — typed register/get/list/set/transition/query boundary | Integration tests through InMemoryRepository |
| 3.3 | Gateway rollback semantics | Simulate downstream render/sync failure and assert old web restored |
| 3.4 | `controlplane/validate.py` — validation orchestration | Compare findings with current system on characterization fixtures |
| 3.5 | `controlplane/automation.py` — declarative render + stale-trigger contracts | Normalize automation graph; unknown renderer fails fast |
| 3.6 | `controlplane/render.py` — generated surfaces with incremental SHA-256 cache | Snapshot tests for claims, predictions, assumptions, discoveries; cache hit/miss tests |
| 3.7 | `controlplane/check.py` — check-refs, check-stale, sync-prose, verify-prose-sync | Link scanner, staleness rules, AUTO marker sync |
| 3.8 | `controlplane/metrics.py` — repo metrics and tier-A evidence counting | Correlation-aware group counting, stressed/active failure summaries |
| 3.9 | `controlplane/status.py`, `health.py`, `export.py` | Read-model and health tests |
| 3.10 | Transaction / provenance log adapter | Append, rollback, and dry-run behavior tests |
| 3.11 | Mutation provenance — `_last_modified`, `_modified_by` on every gateway write | Write + read-back; provenance preserved through round-trip |

**Target: ~60 additional tests.**

### Phase 3 Exit Criteria

- [ ] Gateway is the single mutation/query boundary used by both MCP and CLI
- [ ] `GatewayResult` is the stable result contract for all operations
- [ ] Full register → validate → render → sync → log pipeline works end-to-end
- [ ] Downstream failures restore prior canonical state cleanly
- [ ] Dry-run returns the same result envelope without persisting
- [ ] Read-only services run from explicit `ProjectContext`
- [ ] Render outputs and stale triggers come from declarative automation config
- [ ] Markdown output matches current Horizon behavior for the same data
- [ ] Every gateway write records `_last_modified` and `_modified_by` provenance

---

## 8. Phase 4 — MCP, CLI, Init, Health

**Goal:** The product is usable by AI agents over MCP (primary) and by
humans over the CLI (secondary). New users — human or agent — can initialize
a project, register artifacts, validate, and check health.

### 8.1 Shared Result Envelope

Every operation — MCP tool call or CLI command — returns the same result
contract. This is the single most important interface decision in Phase 4:
MCP and CLI are two presentations of the same operation, not two separate
implementations.

`GatewayResult` is defined once in `controlplane/gateway.py` (see section 3.5).
Reproduced here for reference:

```python
@dataclass
class GatewayResult:
    status: str          # "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run"
    changed: bool
    message: str
    findings: list[Finding]
    transaction_id: str | None = None
    data: dict | None = None  # resource data for get/list/query results
```

JSON envelope (serialized from `GatewayResult`):

```json
{
  "status": "ok" | "error" | "CLEAN" | "BLOCKED" | "dry_run",
  "changed": true | false,
  "message": "...",
  "findings": [...],
  "transaction_id": "...",
  "data": { ... }
}
```

All consumers — agents via MCP, scripts via CLI `--json`, integration tests
— parse `result["status"]` first and branch on it. This contract cannot
change without a version bump.

### 8.2 MCP Server (`mcp/server.py`, `mcp/tools.py`)

The MCP server is the primary external interface. It exposes the full
control-plane gateway as MCP tools. Agents can register research artifacts,
query the epistemic web, validate, render, and check health — all through
structured tool calls with no subprocess or file manipulation needed.

**Design rules:**
- `mcp/tools.py` contains one handler per tool. Each handler is a thin
  wrapper that calls the same gateway or service function the CLI calls.
- No business logic lives in `mcp/`. If a handler does more than parse
  inputs + call the control plane + return the result, move the logic up.
- Input schemas are typed cleanly so agents see required/optional fields.
- All results use the shared `GatewayResult` envelope, serialized to JSON.

**MCP tool surface:**

| Tool | Control-Plane Call | Read/Write |
|------|--------------------|------------|
| `validate` | `validate.run_validate(context, ...)` | Read |
| `health` | `health.run_health(context)` | Read |
| `doctor` | `health.run_health(context)` (alias) | Read |
| `status` | `status.get_status(context, ...)` | Read |
| `get` | `gateway.get(resource_type, id)` | Read |
| `list` | `gateway.list(resource_type, ...)` | Read |
| `register` | `gateway.register(resource_type, payload, dry_run)` | Write |
| `set` | `gateway.set(resource_type, id, payload, dry_run)` | Write |
| `append` | `gateway.append(resource_type, id, key, value, dry_run)` | Write |
| `transition` | `gateway.transition(resource_type, id, status, dry_run)` | Write |
| `query` | `gateway.query(resource_type, filters)` | Read |
| `render` | `render.run_render(context, ...)` | Write |
| `check_stale` | `check.run_check_stale(context)` | Read |
| `check_refs` | `check.run_check_refs(context, ...)` | Read (+ cache) |
| `export` | `export.run_export(context, ...)` | Read |
| `init` | `init.run_init(context, ...)` | Write |
| `run_script` | `execution.run_script(context, ...)` | Execute |

**MCP server entry point** (`mcp/server.py`):

```python
def build_server(context: ProjectContext) -> MCPServer:
    """Wire the MCP server to the control-plane gateway."""
    repo = JsonFileRepository(context.paths.data_dir)
    gateway = build_gateway(context, repo)
    server = MCPServer(name="horizon-research")
    register_tools(server, context, gateway)
    return server


def main() -> None:
    context = build_project_context(Path.cwd())
    server = build_server(context)
    server.run()
```

**MCP tool handler shape** (`mcp/tools.py`):

```python
def tool_register(
    gateway: Gateway,
    resource_type: str,
    payload: dict,
    dry_run: bool = False,
) -> dict:
    result = gateway.register(resource_type, payload, dry_run=dry_run)
    return asdict(result)
```

**Dependency:** The MCP server depends on `fastmcp` (or an equivalent
stdlib-compatible MCP library). Add it to `[project.optional-dependencies]`
under `[mcp]` — not to the core install — so the package installs without
MCP in environments where it isn't needed.

```toml
[project.optional-dependencies]
mcp = ["fastmcp>=2,<3"]
```

**`pyproject.toml` console-script entry point:**

```toml
[project.scripts]
horizon = "horizon_research.cli.main:main"
horizon-mcp = "horizon_research.mcp.server:main"
```

### 8.3 CLI (`cli/main.py`, `cli/formatters.py`)

The CLI is the secondary interface — the developer and debugging surface. It
wraps the same gateway and service calls as the MCP server, with two output
modes: human-readable (default) and `--json` (same `GatewayResult` envelope
the MCP server returns).

**CLI dispatch table** — every command is one control-plane call:

| Command | Control-Plane Call | Read/Write |
|---------|--------------------|------------|
| `validate` | `validate.run_validate(context, ...)` | Read |
| `render` | `render.run_render(context, ...)` | Write |
| `status` | `status.get_status(context, ...)` | Read |
| `get` | `gateway.get(...)` | Read |
| `list` | `gateway.list(...)` | Read |
| `set` | `gateway.set(...)` | Write |
| `append` | `gateway.append(...)` | Write |
| `transition` | `gateway.transition(...)` | Write |
| `register` | `gateway.register(...)` | Write |
| `query` | `gateway.query(...)` | Read |
| `run-script` | `execution.run_script(...)` | Execute |
| `check-stale` | `check.run_check_stale(context)` | Read |
| `check-refs` | `check.run_check_refs(...)` | Read (+ cache) |
| `sync-prose` | `check.run_sync_prose(...)` | Write |
| `verify-prose-sync` | `check.run_verify_prose_sync(...)` | Read |
| `health` | `health.run_health(context)` | Read |
| `doctor` | `health.run_health(context)` (alias) | Read |
| `init` | `init.run_init(context, ...)` | Write |
| `export` | `export.run_export(...)` | Read |
| `version` | (inline) | Read |

**CLI entry point** — thin dispatch, nothing more:

```python
def main() -> int:
    command, args = parse_argv(sys.argv)
    context = build_project_context(Path.cwd())
    repo = JsonFileRepository(context.paths.data_dir)
    gateway = build_gateway(context, repo)

    result = dispatch(command, args, context, gateway)
    format_result(result, json_mode=args.json)
    return 0 if result.status not in ("error", "BLOCKED") else 1
```

**Principles:** Single Responsibility — CLI parses input and formats output.
Nothing else. CLI never re-implements control-plane logic.

### 8.4 Configuration and Context (`config.py`, `controlplane/context.py`)

```python
@dataclass
class HorizonConfig:
    project_dir: Path = Path("project")
    governance_enabled: bool = False
    literature_watch_enabled: bool = False


def load_config(workspace: Path) -> HorizonConfig:
    """Load from horizon.toml if present, else use defaults."""
    toml_path = workspace / "horizon.toml"
    if toml_path.exists():
        raw = tomllib.loads(toml_path.read_text())
        return HorizonConfig(
            project_dir=Path(raw.get("project_dir", "project")),
            governance_enabled=raw.get("governance", {}).get("enabled", False),
            literature_watch_enabled=raw.get("literature_watch", {}).get("enabled", False),
        )
    return HorizonConfig()
```

### 8.5 `horizon init`

Create a new project directory with empty registries:

```
<project_dir>/
├── data/
│   ├── claims.json
│   ├── assumptions.json
│   ├── predictions.json
│   ├── hypotheses.json
│   ├── discoveries.json
│   ├── scripts.json
│   ├── independence_groups.json
│   ├── failures.json
│   ├── concepts.json
│   └── parameters.json
├── views/                  (generated markdown goes here)
├── knowledge/              (generated + hand-maintained)
├── logs/
│   └── query_transactions.jsonl
├── src/
│   ├── verify/
│   └── analysis/
├── integrity/
│   ├── reference_values.json
│   └── tolerance_bounds.json
├── .cache/                 (managed by the control plane)
└── README.md
```

Options:
- `--with-governance` — adds session types, boundary rules, close config
  (Phase 7)
- `--with-agent` — adds template agent adapter files: `SYSTEM_BRIEFING.md`,
  `CLAUDE.md` / `.cursorrules` / `copilot-instructions.md`,
  `read_policy.json`, `execution_policy.json`. These are clean starting-point
  templates, not the battle-hardened instance files from this repo. Users
  customize from here.

Idempotent: safe to run on an existing project (fills in missing pieces,
never overwrites existing files).

### 8.6 `horizon health` / `horizon doctor`

Project health check composed from existing capabilities — the "research
linter" concept. Exposed under two names: `health` (for programmatic/MCP use)
and `doctor` (for human muscle memory, analogous to `brew doctor` or
`flutter doctor`).

1. Are all expected data files present and valid JSON?
2. Do cross-references resolve? (validates the web)
3. Are rendered views current? (render `--check` under the hood)
4. Are there orphaned resources?
5. Schema validation pass/fail
6. Verification coverage gaps
7. Staleness: predictions not recomputed since parameter changes
8. Coverage: claims without verification scripts, hypotheses without
   supporting predictions, empirical assumptions without falsifiable consequences

Clear, readable output with severity levels. Available as both an MCP tool
and a CLI command. This is the "linter for research" — valuable even to
researchers who don't use sessions, governance, or agents.

### 8.7 Phase 4 Deliverables

| Step | What | Tests |
|------|------|-------|
| 4.1 | `config.py` — load from horizon.toml with defaults | Config with/without toml, custom project_dir |
| 4.2 | `mcp/server.py` + `mcp/tools.py` — full tool surface over control plane | Tool calls return correct `GatewayResult` envelopes |
| 4.3 | MCP tool schema parity with CLI `--json` output | Both return identical `GatewayResult` JSON for same operation |
| 4.4 | `horizon-mcp` console-script entry point registered and runnable | Smoke test |
| 4.5 | `cli/main.py` — validate, get, list, register, transition | Subprocess tests: check JSON output shape |
| 4.6 | `cli/formatters.py` — human + JSON output | Unit tests for formatting |
| 4.7 | `horizon init` | Creates correct directory structure |
| 4.8 | `horizon health` (CLI + MCP tool) | Reports known issues in test fixture |
| 4.9 | `horizon export --format=json` | Exports all data as valid JSON |
| 4.10 | `horizon version` | Prints version, Python version, workspace path |
| 4.11 | Backward compat | Current Horizon repo works with new system |

### Release Checkpoint: First Internal Product Alpha

After Phase 4, an AI agent can:

```
# Via MCP tool calls:
tool: init  args: {}
tool: register  args: {resource_type: "claim", payload: {id: "C-001", ...}}
tool: validate  args: {}
tool: health    args: {}
tool: export    args: {format: "json"}
```

And a human can reach the same operations over the CLI:

```bash
pip install 'horizon-research[mcp]'
horizon init
horizon register claim C-001 '{"statement":"...", "type":"P", ...}'
horizon validate --json
horizon health
```

### Phase 4 Exit Criteria

- [ ] MCP server exposes the full tool surface over the control-plane gateway
- [ ] MCP tool results and CLI `--json` results share the same `GatewayResult` contract
- [ ] `horizon-mcp` console script entry point is registered and tested
- [ ] CLI dispatches all core commands
- [ ] `horizon init` creates valid project scaffold (idempotent, never overwrites)
- [ ] `horizon init --with-agent` generates clean agent adapter templates
- [ ] `horizon health` / `horizon doctor` reports health accurately (CLI + MCP)
- [ ] Both human and JSON CLI output modes work
- [ ] Config is optional (defaults work without horizon.toml)

---

## 9. Phase 5 — Human-First UX

**Goal:** Usable by a researcher who doesn't want to write JSON.

### 9.1 Deliverables

| # | Feature | Description |
|---|---------|-------------|
| 1 | Pretty-print output | `horizon list claims` shows a table. `--json` for machine output. |
| 2 | `horizon add <type>` | Interactive prompts. Asks required fields one at a time. No JSON. |
| 3 | `horizon show <type> [id]` | Human-readable view with relationships. |
| 4 | `horizon check` | Alias for `validate --quick`. Short, memorable. |
| 5 | `horizon status` | Readable summary with health counts. |
| 6 | `horizon log [id]` | Mutation history from transaction log (requires Phase 3 provenance). |
| 7 | Quickstart guide | Install, init, add hypothesis, add prediction, validate, render. |
| 8 | Shell completions | Generated from the argument parser for bash, zsh, and fish. Resource ID tab-completion by reading local data files. |

For `horizon add prediction`, also prompt for:
- The `specification` — the mathematical relationship or empirical claim being
  tested (human-readable, separate from the verification script). This field
  already exists on the `Prediction` entity from Phase 1. The interactive
  prompt makes it easy to fill in.
- The expected value with units

The specification is the **formula contract** — it lives on the prediction so
that Phase 6 verification layers can check whether the script is testing the
right thing, not just whether it tests honestly. A reviewer (human or agent)
can compare the specification against the script's logic without reading the
full implementation.

### 9.2 What This Phase is NOT

- No progressive-disclosure dual CLI. Simple commands (`add`, `show`, `check`)
  coexist with power commands (`register`, `get`, `set`, `query`).
- No `horizon dashboard`. `status` is enough.
- No static HTML rendering. Markdown is fine for now.

### Release Checkpoint: First External Human-Usable Alpha

### Phase 5 Exit Criteria

- [ ] A researcher can use the tool without writing JSON
- [ ] Interactive add works for all core entity types
- [ ] `horizon add prediction` collects the mathematical relationship (formula contract)
- [ ] `horizon show` displays entity with relationships
- [ ] `horizon log` shows per-resource mutation history from provenance data
- [ ] Shell completions generated for bash, zsh, and fish
- [ ] Quickstart guide is written and tested

---

## 10. Phase 6 — Execution Pipeline

**Goal:** Verification scripts run in a sandboxed environment with rigorous
integrity checking that catches **both false positives (scripts that claim
success when they shouldn't) and false negatives (scripts that don't
accurately test what they claim to test)**.

This is the hardest problem in the product. A verification system that can
be fooled — by accident or by subtle bugs — is worse than no verification
system, because it creates false confidence. The execution pipeline must
treat every script as **guilty until proven honest**.

### 10.1 The Verification Problem

The core question: **How do you know a script accurately represents what
it's supposed to verify?**

There are two failure modes:

1. **False positive (Type I trust failure):** Script reports PASS, but the
   prediction is actually wrong. Causes: unconditional success prints,
   hardcoded results, caught exceptions that silently pass, tolerance set
   too loose, compensating errors that cancel out.

2. **False negative (Type II trust failure):** Script reports FAIL (or tests
   the wrong thing entirely), but the prediction is actually correct. Causes:
   script tests a different relationship than the specification claims,
   sign error in formula, wrong units, stale reference values, overly tight
   tolerance.

Both failure modes are dangerous. False positives create false confidence
in wrong results. False negatives waste research effort investigating
"failures" that aren't real, or worse, cause researchers to abandon correct
predictions.

### 10.2 The Specification Contract

Every prediction carries a `specification` field — a human-readable
description of the mathematical relationship or empirical claim being tested.
This is the **ground truth** for what the verification script should compute.

```
Prediction P-007:
  observable: "W boson mass"
  specification: "M_W = (g² × v) / 2, using SM parameters"
  predicted: 80.379 GeV
  script: SCR-007
```

The specification is not executable code. It is the **what** — the
relationship the script is supposed to implement. The script is the **how**.
When these diverge, the verification is broken regardless of whether the
script reports PASS or FAIL.

The specification ships on the `Prediction` entity from Phase 1.
`horizon add prediction` (Phase 5) prompts for it interactively. But the
specification is useful from Phase 6 onward for automated analysis:

- **L1 static analysis** can check whether the script references the same
  variables and constants named in the specification
- **Sensitivity analysis** can verify that perturbing specification inputs
  produces the expected directional changes in output
- **Human/agent review** can compare specification against script logic

### 10.3 Three-Layer Architecture

```
┌──────────────────────────────────────────────┐
│  Script Registry + Dispatch                  │
│  "Which script, what command, what policy?"  │
└────────────────────┬─────────────────────────┘
                     ↓
┌──────────────────────────────────────────────┐
│  Execution Runner — Policy Enforcement       │
│  "Is this allowed? Build the sandbox."       │
└────────────────────┬─────────────────────────┘
                     ↓
┌──────────────────────────────────────────────┐
│  Sandbox Runner — Runtime Container          │
│  "Execute in restricted environment."        │
└──────────────────────────────────────────────┘
```

### 10.4 Sandbox Executor (implements ScriptExecutor port)

```python
class SandboxExecutor:
    """Implements ScriptExecutor port with deny-by-default sandboxing."""

    def __init__(self, workspace: Path, sandbox_runner: Path) -> None:
        self._workspace = workspace
        self._sandbox_runner = sandbox_runner

    def execute(
        self, script_id: str, command: str, **policy
    ) -> ExecutionResult:
        # Build sandboxed command based on policy
        # Execute in subprocess
        # Parse and return result
        ...
```

Each script declares an **execution context** that controls the sandbox:

```python
DEFAULT_EXECUTION_CONTEXT = {
    "requires_network": False,
    "requires_sandbox": False,
    "write_paths": [],
    "python_environment": "workspace",
    "allow_subprocess": False,
}
```

The sandbox runner is a deny-by-default Python-level wrapper:
1. **Scrub environment** — clear env vars except PATH/LANG/TERM, set temp HOME
2. **Apply resource limits** — no core dumps, 3-min CPU cap, 20 MB file size,
   64 open files
3. **Install write guard** — monkey-patch `builtins.open`, `Path.write_text`,
   `os.rename`, etc. to block writes outside allowed roots
4. **Install network guard** (unless allowed) — replace `socket.socket`,
   `http.client`, `urllib.request`
5. **Install subprocess guard** (unless allowed) — replace `subprocess.run`,
   `os.system`, `os.popen`
6. **Execute script** via `runpy.run_path` inside the controlled environment

On macOS, an outer `sandbox-exec` kernel-level sandbox can wrap the whole
thing for defense-in-depth. Both layers are deny-by-default.

Command normalization includes path-traversal protection — the target script
must resolve inside the workspace.

### 10.5 Verification Layers

Seven layers, each catching a different class of failure. Ordered from
cheapest to most expensive.

**L1 — Static AST Analysis (false positive detection)**

Catches scripts that claim success without doing real work:

- **Unconditional success detection**: Walk the AST for `print()` calls
  containing success keywords ("CONFIRMED", "PASS", "✓") that are NOT inside
  an `if` block gates. A script that prints "CONFIRMED" on every code path
  regardless of computation is fraudulent.
- **Hardcoded result detection**: Identify functions that return a constant
  value regardless of input. A script that `return 80.379` without computing
  anything is not a verification.
- **Dead branch detection**: Identify `if` branches that can never execute
  (e.g., `if False:`, unreachable code after `return`).
- **Input coverage**: Does the script actually import/read the parameters
  and constants referenced in its specification? A script that never loads
  the inputs it claims to test is suspect.

**L2 — Runtime Execution (basic sanity)**

- Script exits with code 0 (PASS) or non-zero (FAIL)
- Stdout/stderr captured and parsed
- Timeout enforcement
- Resource limit enforcement

**L3 — Sabotage Injection (false positive detection)**

Catches scripts that always report success regardless of input values:

- **Constant corruption**: For each registered constant, inject a known-wrong
  value. A genuine verification script should detect the corruption and FAIL.
  A script that still reports PASS is not actually checking.
- **Multi-constant sabotage**: Corrupt two constants simultaneously to catch
  compensating errors (e.g., M_W ×2 AND g ×2 might preserve a ratio).
- **Sign flip sabotage**: Negate key constants. Many formulas are symmetric
  under sign changes — this catches scripts that only check magnitudes.

**L4 — Sensitivity Analysis (false negative detection, NEW)**

Catches scripts whose output doesn't respond correctly to input changes:

- **Input perturbation**: For each input parameter, apply small perturbations
  (±1%, ±5%, ±10%). Verify the output changes in the expected direction and
  approximate magnitude. A script that produces identical output regardless
  of input perturbation is not computing a real function of those inputs.
- **Monotonicity checks**: For relationships where the specification implies
  a directional dependency (e.g., "mass increases with coupling"), verify
  that increasing the input increases the output.
- **Boundary probing**: Set values at the exact tolerance boundary. Verify
  the script's PASS/FAIL threshold matches the declared tolerance. A script
  that passes at 2× tolerance is too loose. A script that fails at 0.5×
  tolerance is too tight.
- **Zero-input test**: Where meaningful, run with zeroed or degenerate
  inputs. Verify the script produces a sensible degenerate output (zero,
  infinity, error) — not the same result as with real inputs.

Sensitivity analysis requires a **perturbation registry** per script:
which inputs to perturb, by how much, and what directional change to expect.
This lives in project metadata alongside the sabotage registry.

**L5 — Reference Value Cross-Check**

- Compare computed values against independently maintained reference values
- Track historical outputs — detect unexpected changes when inputs haven't
  changed
- Detect scripts that suddenly agree with new reference values without code
  changes (possible silent data corruption)

**L6 — Tolerance Audit**

- Verify declared tolerances are scientifically justified
- Flag predictions where rel_tol > 10% (suspiciously loose)
- Flag predictions where rel_tol < machine epsilon (impossibly tight)
- Compare tolerance against the actual spread of computed vs. observed values

**L7 — Dual-Implementation Verification (optional, for critical predictions)**

The strongest guarantee: two independent implementations of the same
verification, written by different authors (or an author and an AI agent):

- Register a second script for the same prediction
- Run both independently
- Compare outputs — they must agree within the declared tolerance
- Disagreement triggers mandatory human review

This is expensive and should be reserved for Tier A predictions and
high-stakes results. The system should make it easy to register dual
implementations but never require them.

```python
@dataclass
class DualVerificationResult:
    prediction_id: PredictionId
    primary_script: ScriptId
    secondary_script: ScriptId
    primary_result: ExecutionResult
    secondary_result: ExecutionResult
    agreement: bool                    # both within tolerance of each other
    divergence: float | None           # how far apart, if numeric
```

### 10.6 The Verification Report

Each script run produces a structured **verification report** that
aggregates findings across all applicable layers:

```python
@dataclass
class VerificationReport:
    script_id: ScriptId
    prediction_id: PredictionId | None
    layers_run: list[str]              # ["L1", "L2", "L3", "L4", ...]
    findings: list[Finding]
    trust_level: str                   # "verified", "partial", "unverified", "suspect"
    false_positive_risk: str           # "low", "medium", "high"
    false_negative_risk: str           # "low", "medium", "high"
    details: dict                      # per-layer results
```

`trust_level` summarizes the overall confidence:
- **verified**: Passed all applicable layers including sensitivity analysis
- **partial**: Passed L1-L3 but sensitivity analysis not yet configured
- **unverified**: Only L1-L2 run (no sabotage registry configured)
- **suspect**: Failed one or more layers

`false_positive_risk` and `false_negative_risk` are independent assessments.
A script can have low false-positive risk (sabotage injection works) but
high false-negative risk (no sensitivity analysis configured, specification
missing).

### 10.7 Benchmark Validation

Scripts with `machine_readable_output: true` produce structured data following
the `verification_benchmark_v1` contract:

```json
{
  "schema": "verification_benchmark_v1",
  "predictions": {
    "P-007": {
      "predicted": 80.379,
      "computed": 80.377,
      "tolerance": {
        "rel_tol": 0.001,
        "abs_tol": 1e-9
      },
      "status": "PASS"
    }
  }
}
```

The execution layer validates each prediction's computed value against its
declared tolerance, **independently of the script's self-reported pass/fail**.
This cross-check prevents scripts that claim PASS but actually deviate beyond
tolerance. Numeric comparison uses `math.isclose` with per-prediction
`rel_tol` / `abs_tol`. Percent deviation is computed relative to the observed
value.

### 10.8 Caching

Runtime results are cached using **semantic AST fingerprints** — the AST is
hashed rather than source text, so comment-only edits reuse expensive L2-L7
results. The cache key includes:

- AST hash of the script
- Hash of all input parameters/constants the script reads
- Hash of the perturbation and sabotage registries

If any of these change, cached results are invalidated.

### 10.9 What Lives Where

Product code (generic, ships with `horizon-research`):
- Sandbox executor, guards, and policy enforcement
- L1 AST analysis engine
- L2 runtime execution
- L3 sabotage injection framework
- L4 sensitivity analysis framework
- L5 reference value comparison
- L6 tolerance audit
- L7 dual-implementation comparison
- Benchmark validation
- Verification report generation
- Caching

Project metadata (per-project, lives in `project/integrity/`):
- Sabotage registry (which constants to corrupt, per script)
- Perturbation registry (which inputs to perturb, expected directions)
- Reference values
- Tolerance bounds

### 10.10 Phase 6 Deliverables

| Step | What | Tests |
|------|------|-------|
| 6.1 | `sandbox_executor.py` — implements ScriptExecutor | Integration with test scripts |
| 6.2 | Sandbox runner — write guard, network guard, subprocess guard | Security tests |
| 6.3 | Execution policy — context normalization | Policy parsing and validation |
| 6.4 | `horizon run-script <id>` | End-to-end script execution |
| 6.5 | L1 static analysis — unconditional success, hardcoded results, input coverage | AST analysis on known-good and known-bad fixtures |
| 6.6 | L3 sabotage injection — constant corruption, multi-constant, sign flip | Sabotage on scripts that don't actually verify |
| 6.7 | L4 sensitivity analysis — perturbation, monotonicity, boundary probing | Scripts with known input→output relationships |
| 6.8 | L5-L6 reference values and tolerance audit | Cross-check and tolerance bound tests |
| 6.9 | L7 dual-implementation verification | Agreement/disagreement detection |
| 6.10 | Benchmark validation — predicted vs. computed vs. tolerance | Tolerance violation detection |
| 6.11 | Verification report generation | Structured report with trust levels and risk assessment |
| 6.12 | Limitation tests for known blind spots | Honest-but-wrong verifier fixtures, documented non-goals |

### Phase 6 Exit Criteria

- [ ] Scripts execute in sandboxed environment
- [ ] Deny-by-default: no network, no writes outside allowed paths
- [ ] L1 catches unconditional success prints and hardcoded results
- [ ] L3 sabotage injection detects scripts that don't actually verify
- [ ] L4 sensitivity analysis detects scripts whose output doesn't respond to input changes
- [ ] L4 boundary probing verifies tolerance thresholds match declarations
- [ ] L7 dual-implementation detects disagreement between independent verifiers
- [ ] Benchmark validation catches tolerance violations independently of script self-report
- [ ] Verification reports clearly communicate false-positive and false-negative risk
- [ ] Every verification layer has explicit limitation tests for known blind spots
- [ ] Perturbation and sabotage registries live in project metadata, not product code

---

## 11. Phase 7 — Governance: The Professional Tier

**Goal:** Sessions, boundaries, and close gates work as an opt-in layer
that adds rigor for disciplined, long-running research projects.

Governance is not an afterthought — it's a **designed-in capability** that
the architecture supports from Phase 3 onward. The gateway's transaction
boundary, provenance system, and typed result envelopes all exist partly
to make governance possible. Phase 7 is when the user-facing surface ships,
but the hooks have been in place since Phase 3.

**Why opt-in, not default:** The core value proposition — epistemic web
validation, verification, health checks — stands on its own. A researcher
evaluating Horizon for the first time should get value immediately without
learning about session types or close gates. Governance is the natural
next step for researchers who want:

- **Session discipline**: Named work sessions with typed boundaries (which
  files can change in a "research" vs. "engineering" session)
- **Close gates**: Forced checks before closing a session (are all findings
  resolved? are views up to date? is the transaction log clean?)
- **Modification provenance**: Which session introduced each change
- **Audit trail**: Session summaries, boundary violation reports, close-gate
  findings

The UX should make governance feel like a **progression** — "you've been
using Horizon for a month, here's how to add structure" — not a burden.

### 11.1 Deliverables

| # | Feature | Description |
|---|---------|-------------|
| 1 | `horizon init --with-governance` | Adds session types, boundary rules, close config |
| 2 | `horizon upgrade --add=governance` | Add governance to existing core-only project (additive, non-destructive) |
| 3 | Mutation provenance extension | Governance mode extends Phase 3 provenance with `_modification_session` |
| 4 | Conditional session logic | `governance.enabled = false`: no boundaries, no close gate, no session numbers |
| 5 | Git integration conditional | Core never touches git. Governance uses it when available. |
| 6 | Session data reclassification | `session_state.json`, `session_summaries.json`, `session_types.json` are governance data |
| 7 | Split `session_close.py` | Reusable close-gate engine (checks + findings) separate from git publish workflow |
| 8 | `--with-agent` reinforcement | Verify agent templates from Phase 4 work correctly with governance; boundary enforcement and close gate reference `governance.enabled` so they're inert when governance is off |

### 11.2 Session Boundary Enforcement

```python
class SessionBoundary:
    """Enforces file-access rules based on session type."""

    def __init__(self, contract: dict) -> None:
        self._zones = contract["zones"]
        self._session_types = contract["session_types"]

    def check_violations(
        self, modified_files: list[str], session_type: str
    ) -> list[Finding]:
        allowed = self._allowed_zones(session_type)
        findings = []
        for f in modified_files:
            if not any(self._match(f, zone) for zone in allowed):
                findings.append(Finding(
                    Severity.CRITICAL,
                    f"session_boundary/{f}",
                    f"File outside allowed zone for session type '{session_type}'",
                ))
        return findings
```

### Release Checkpoint: Governance-Capable Beta

### Phase 7 Exit Criteria

- [ ] Core experience works identically with governance off
- [ ] `horizon upgrade --add=governance` adds governance to existing core-only project
- [ ] Session boundaries enforced when governance enabled
- [ ] Close gate runs checks and returns findings
- [ ] Git publish is optional and separate from close-gate logic
- [ ] Governance extends Phase 3 provenance with `_modification_session`
- [ ] Agent templates from Phase 4 work correctly under governance

---

## 12. After Phase 7: The Backlog

Everything below is real and valuable but not on the critical path.

### High-Value (Do When There's Demand)

- Schema versioning + `horizon migrate`
- `horizon export --format=csv|notebook|bibtex`
- `horizon import` from BibTeX/CSV (offline-first: local file parsing always
  works; online DOI/arXiv fetch is opt-in and requires explicit network
  permission)
- Research graph traversal — `horizon trace`, `horizon impact`
- Shell completions (already in Phase 5 deliverables)
- Example projects (ship sanitized fixtures as `examples/` with the package)
- `horizon resolve-conflicts` — JSON-structure-aware merge tool for
  multi-user scenarios

### Medium-Value (Real Features, Not Urgent)

- Schema-driven gateway — resource types in config instead of Python
- Static HTML rendering — `horizon render --format=html`
- `horizon health` as CI check
- One-file-per-resource layout (`data/claims/C-001.json`) — decision point
  for multi-user scalability; big migration, needs conscious design
- Multi-user merge / conflict resolution
- `horizon challenge` — adversarial analysis of claims

### Aspirational (Someday, Maybe)

- Hypothesis tournaments
- Interactive graph explorer
- Paper draft generation
- Evidence quality scoring
- Pre-registration export (OSF format)
- Progressive-disclosure CLI modes
- XDG-compliant config paths
- Session replay
- Reproducibility manifests
- Webhook/notification integration
- Research templates / starter kits

---

## 13. Principle Compliance Matrix

| Principle | How It's Followed | Where |
|-----------|-------------------|-------|
| **Reuse/Release Equivalence (REP)** | The public release boundary is `horizon_research`; the kernel lives in `horizon_research.epistemic`, and internal modules can change behind that stable root without changing console scripts | Phase 2 packaging |
| **S — Single Responsibility** | Each module has exactly one reason to change | `web.py` (graph rules), `controlplane/gateway.py` (transaction boundary), `json_repository.py` (serialization), `main.py` (parsing) |
| **O — Open/Closed** | New validators = new functions, not modifications. New entity types = new classes. | `invariants.py`, `model.py` |
| **L — Liskov Substitution** | `InMemoryRepository` and `JsonFileRepository` interchangeable | `ports.py`, all adapters |
| **I — Interface Segregation** | `WebRepository` has only `load()` and `save()`. `ScriptExecutor` is separate. | `ports.py` |
| **D — Dependency Inversion** | Domain defines protocols. Adapters implement them. The control plane depends on abstractions. | `ports.py`, `controlplane/gateway.py` |
| **Low Coupling** | Kernel code has zero imports from adapters, CLI, or MCP | Package DAG: `horizon_research.mcp → horizon_research.controlplane → horizon_research.epistemic ← horizon_research.adapters`; `horizon_research.cli → horizon_research.controlplane` |
| **High Cohesion** | `epistemic/` = kernel reasoning. `controlplane/` = product orchestration. `adapters/` = I/O. `cli/` = UI. | Package layout |
| **Common Closure (CCP)** | Modules that change together are packaged together: automation/render/check, execution policy/meta-verify, governance close/session/boundary | `controlplane/`, `execution/`, `governance/` |
| **Common Reuse (CRP)** | Optional governance and literature surfaces stay separate from the core install and core workflows | Package layout, optional extras |
| **DRY** | Bidirectional links maintained once (web mutations). Validation rules each exist once. | `web.py`, `invariants.py` |
| **KISS** | Plain dataclasses, native Python types, `dict`/`set`/`list`. No metaclasses. Dependencies only at CLI/MCP boundaries where they directly improve UX. | Entire codebase |
| **YAGNI** | No plugin system, no event bus, no database, no web server, no generic graph engine. Dependencies earn their place by improving end-user experience, not developer convenience. | Explicit in Phase 1-7 scope limits |
| **Separation of Concerns** | Structural invariants (mutation-time) vs semantic validation (on-demand) vs persistence vs rendering vs UI | Layer architecture |
| **Convention over Configuration** | Default `project/` layout and minimal `horizon.toml`; declarative automation graph only for the places that truly vary | `controlplane/context.py`, `controlplane/automation.py` |
| **Principle of Least Privilege** | Execution defaults to no network, no subprocess, no writes outside declared roots; CI defaults to read-only permissions except release jobs | `execution/policy.py`, `adapters/sandbox_executor.py`, CI/CD rollout |
| **Law of Demeter** | Entities hold IDs, not objects. Traverse through `EpistemicWeb` methods. | `model.py`, `web.py` |
| **Composition over Inheritance** | No entity inherits from another. Protocols for interfaces, not abstract base classes. | `model.py`, `ports.py` |
| **Encapsulation** | All invariant enforcement inside `EpistemicWeb`. External code uses methods, not direct mutation. | `web.py` |
| **Abstraction** | External code sees `web.register_claim()`, not back-reference bookkeeping. | `web.py` |
| **Polymorphism** | All validators: `(Web) -> list[Finding]`. All repos: `WebRepository` protocol. | `invariants.py`, `ports.py` |
| **Fail Fast** | Domain throws on broken refs/cycles. Don't wait for post-hoc validation. | `web.py` |
| **Acyclic Dependencies (ADP)** | `mcp → controlplane → epistemic ← adapters` and `cli → controlplane`. MCP and CLI are peers. No cycles. | Package DAG |
| **Stable Dependencies (SDP)** | `epistemic/` (most stable) ← everything else. `mcp/` and `cli/` (least stable) → `controlplane/`. | Package DAG |
| **Stable Abstractions (SAP)** | Stable packages define protocols and normalized contracts; unstable packages stay concrete and close to I/O | `epistemic/ports.py`, `controlplane/automation.py`, `cli/`, `adapters/` |

---

## 14. Clean Break from the Current Codebase

### 14.1 Why Not Migrate

The current codebase proved the domain model. It did its job. But the wiring
is fundamentally broken — module-level globals, monkey-patching, circular
dependencies resolved at runtime. Trying to incrementally refactor this into
the right architecture would mean:

1. Writing characterization tests around fragile wiring we plan to delete
2. Threading two architectures through every module simultaneously
3. Debugging subtle behavioral differences between old and new code paths
4. Carrying legacy patterns forward "temporarily" until they become permanent

That is exactly how codebases rot. The domain model is correct. The wiring
is not. Build the right thing from scratch.

### 14.2 What We Take Forward

**Ideas, not code:**

| What | How It Carries Forward |
|------|----------------------|
| Domain vocabulary (claims, assumptions, predictions, independence groups) | Rebuilt as typed entities in `epistemic/model.py` |
| Gateway as single mutation boundary | Rebuilt as `controlplane/gateway.py` with typed contracts |
| Transactional write → validate → render → rollback | Same pipeline, clean implementation |
| Declarative automation graph | Same config format, clean loader |
| Sandbox execution model | Same deny-by-default philosophy, clean executor |
| Bidirectional invariants | Enforced at mutation time instead of validated after the fact |
| Incremental rendering (SHA-256 fingerprints) | Same caching strategy, clean I/O |
| JSON file format | Same schema, read by new `JsonFileRepository` |

**Nothing** from `src/horizon_core/` or `src/horizon.py` is imported,
subclassed, or wrapped. The new `src/horizon_research/` package is a
standalone implementation that happens to read the same JSON format.

### 14.3 Transition Plan

1. Build `src/horizon_research/` as a new package tree
2. Old code stays in the repo untouched during development
3. New tests validate against the JSON schema, not against old code behavior
4. When the new system reaches Phase 4 (CLI + MCP working), delete the old
   code entirely
5. No coexistence period, no gradual migration, no behavioral equivalence
   tests against the old system

### 14.4 What About Existing Project Data?

The JSON data files in `project/data/` are the single source of truth. The
new `JsonFileRepository` reads the same JSON format the old system wrote.
If the new system can load, validate, render, and round-trip those files
correctly, the transition is complete. The data survives; the code doesn't.

---

## 15. Standing Decisions

- Horizon is rebuilt as a **control plane** over a project **data plane**.
- The gateway remains the single mutation/query boundary.
- This is a **clean-break rebuild**, not an incremental migration. Ideas
  carry forward; code does not.
- New projects are core-only by default.
- Governance (sessions, boundaries, close gates) is opt-in, off by default,
  but designed-in from Phase 3 as a first-class capability.
- Literature watch is opt-in, off by default.
- Agent config is opt-in, not shipped by default.
- Network access is off by default.
- Import paths are offline-first: local file parsing always works; online
  fetch is opt-in with explicit network permission.
- Git integration is optional: core operations never touch git; governance
  uses it when available. Horizon works for researchers using Dropbox,
  OneDrive, or a plain local folder.
- Distribution name: `horizon-research`.
- Import namespace: `epistemic` (internal), `horizon_research` (public).
- Primary CLI: `horizon`.
- Optional CLI alias: `horizon-research`.
- Declarative automation graph remains the source of truth for generated-output
    wiring and stale-trigger propagation.
- Mutation provenance (`_last_modified`, `_modified_by`) ships in Phase 3
    with the gateway, not deferred to governance. Governance extends it with
    `_modification_session`.
- Packaging, config, and workflow contracts should be tested as code.
- Flat JSON files. Reconsider only if merge conflicts become a real problem.
- Native Python types (`dict`, `set`, `list`) in the domain model.
- Domain core (`epistemic/`) and control plane (`controlplane/`) are stdlib
  only. CLI uses `click` and `rich` for a professional UX. MCP uses
  `fastmcp` as an optional extra. Compute deps (`numpy`, `scipy`) are
  optional extras. The dependency tree stays shallow — direct deps only.
- Vocabulary is domain-neutral by design. Entity names, relationship types,
  and invariants apply to any empirical discipline without modification.

---

## 16. Data Flow Diagram

The system has three operational paths — read, write, and execute:

```
                              ┌──────────────────┐
                              │   horizon.toml   │
                              │ (optional config) │
                              └────────┬─────────┘
                                       │
                              ┌────────┴─────────┐
                              │  ProjectContext   │
                              │  (built once)     │
                              └────────┬─────────┘
                                       │
            ┌──────────────────────────┼────────────────────────────┐
            │                          │                            │
    ┌───────┴───────┐         ┌───────┴────────┐          ┌───────┴───────┐
    │  Read Path    │         │  Write Path    │          │ Execute Path  │
    │               │         │                │          │               │
    │ validate      │         │ gateway CRUD   │          │ run-script    │
    │ render --check│         │                │          │               │
    │ status        │         │                │          │               │
    │ check-*       │         │                │          │               │
    └───────┬───────┘         └───────┬────────┘          └───────┬───────┘
            │                         │                           │
            │                    ┌────┴────┐                      │
            │                    │ 1. Write│                      │
            │                    │   JSON  │                      │
            │                    └────┬────┘                      │
            │                         │                           │
            │                    ┌────┴────┐                      │
            │                    │2. Render│                      │
            │                    │  views  │                      │
            │                    └────┬────┘                      │
            │                         │                           │
            │                    ┌────┴────┐                      │
            │                    │3. Sync  │                      │
            │                    │  prose  │                      │
            │                    └────┬────┘                      │
            │                         │                           │
            │                    ┌────┴────┐                      │
            │                    │4. Full  │                      │
            │                    │validate │                      │
            │                    └────┬────┘                      │
            │                         │                           │
            │                    ┌────┴────┐                      │
    ┌───────┴───────┐            │ Pass?   │          ┌───────────┴───────┐
    │  JSON files   │←───────── │ Commit  │          │  verification    │
    │  (canonical)  │  rollback │ or      │          │  scripts (stdout)│
    │               │  on fail  │ rollback│          │                  │
    └───────┬───────┘            └─────────┘          └────────┬────────┘
            │                                                  │
    ┌───────┴───────┐                                ┌────────┴────────┐
    │  Markdown     │                                │  Benchmark      │
    │  (generated)  │                                │  validation     │
    └───────────────┘                                └─────────────────┘
```

**JSON files are the single source of truth.** Every markdown file is derived
from JSON. Every validation operates on JSON. The only way to modify JSON is
through the gateway. Rolling back any operation is "restore the old web and
re-render."

---

## 17. End-to-End Traces

These traces serve as executable specifications — they document_exactly_ how
data flows through the system for the three most common operations.

### 17.1 Trace: `horizon validate --json`

1. **CLI**: parse `sys.argv` → command=`"validate"`, flags: `quick=False`,
   `output_json=True`
2. **Context**: `context = build_project_context(Path.cwd())` — reads
   `horizon.toml` if present, derives all paths, returns frozen
   `ProjectContext`
3. **Service call**: `validate.run_validate(context, quick=False)`
4. **Inside `run_validate`**:
   - `data = repo.load()` — reads JSON files into domain model
   - Run structural validators (asset restrictions, repo layout, schemas)
   - If not quick: run cross-references, constraints, machine-readable checks,
     coverage, prose consistency, scaling policy
   - Each validator returns `list[Finding]`; concatenate all
5. **Output**: JSON envelope `{"status": "CLEAN"|"BLOCKED", "critical": N,
   "warning": N, "info": N, "findings": [...]}`
6. **Exit**: `sys.exit(1 if critical > 0 else 0)`

Module imports: `src/horizon_research/cli/main.py` →
`src/horizon_research/controlplane/validate.py` →
`src/horizon_research/epistemic/invariants.py`,
`src/horizon_research/adapters/json_repository.py`. No cycles.

Functions that need paths take `context`. Functions that only analyze
in-memory data take `web` or `data`. Pure validators never touch the
filesystem.

### 17.2 Trace: `horizon register claim C-099 '{...}'`

1. **CLI**: parse → command=`"register"`, resource=`"claim"`, id=`"C-099"`,
   payload=JSON string, optional `--reason`, `--dry-run`, `--json`
2. **Context**: build `ProjectContext`
3. **Gateway entry**: `gateway.register("claim", "C-099", parsed_payload)`
4. **Inside the gateway**:
   1. Resolve `"claim"` → canonical resource key via alias table
   2. Load current web: `old_web = repo.load()`
   3. Build domain entity from parsed payload + register defaults
   4. `new_web = old_web.register_claim(claim)` — enforces refs, no cycles,
      maintains bidirectional links
   5. Validate: `findings = validator.validate(new_web)` — if CRITICAL, return
      `GatewayResult(status="blocked", ...)`
   6. If `--dry-run`: return result without persisting
   7. **Persist**: `repo.save(new_web)`
   8. **Render**: `renderer.render(new_web)` → regenerate affected markdown
   9. **Sync prose**: `prose_sync.sync(new_web)` → update AUTO blocks
   10. If render/sync fails: **rollback** — `repo.save(old_web)`,
       re-render, re-sync from old state
   11. **Log**: `tx_log.append("register_claim", "C-099")` → append to
       `query_transactions.jsonl`
5. **Return**: `GatewayResult(status="ok", changed=True, transaction_id=...)`

The guarantee: after any gateway command, the project is in a *consistent*
state — JSON, rendered markdown, and prose surfaces all agree.

### 17.3 Trace: `horizon run-script SCR-001 --json`

1. **CLI**: parse → command=`"run-script"`, script_id=`"SCR-001"`
2. **Context**: build `ProjectContext`
3. **Script dispatch**: load `scripts.json`, look up `"SCR-001"`, read
   command and execution context
4. **Command normalization**: parse command string, validate target script
   resolves inside workspace (path-traversal protection), bind `python` to
   current interpreter
5. **Build sandbox command**: read execution context
   (`requires_network=false`, `write_paths=[]`, etc.), construct the
   `sandbox_runner.py` invocation with appropriate flags
6. **Execute**: `subprocess.run(sandbox_command, ...)`, capture stdout/stderr
7. **Benchmark validation** (if `machine_readable_output: true`): parse
   structured benchmark data from stdout, validate predicted vs. computed
   values against declared tolerances — independently of script's
   self-reported pass/fail
8. **Return**: `{"status": "PASS"|"FAIL"|"ERROR", "script_id": "SCR-001",
   "backend": "...", "returncode": 0, ...}`

---

## 18. Testing Strategy and Fixture Model

### 18.1 Two Fixture Types

1. **Product fixture:** A minimal project directory created in `tmp_path` for
   each test. Contains only the JSON files needed for the test. No git repo,
   no governance metadata, no session types. This is the standard for unit
   and integration tests.

2. **Repo fixture:** Points `ProjectContext` at the real repo layout for
   characterization tests that verify backward compatibility with the
   development environment.

### 18.2 What to Test Where

| Test Type | Uses | Imports |
| --- | --- | --- |
| Domain model unit tests | In-memory only | `src/horizon_research/epistemic/web.py`, `src/horizon_research/epistemic/invariants.py` |
| Repository round-trip tests | Product fixture | `src/horizon_research/adapters/json_repository.py` |
| Validator unit tests | Product fixture | `src/horizon_research/controlplane/validate.py` |
| Renderer snapshot tests | Product fixture | `src/horizon_research/controlplane/render.py` |
| Automation/config contract tests | Parse files as data | `src/horizon_research/controlplane/automation.py`, `pyproject.toml`, workflow files |
| Gateway integration tests | Product fixture + InMemoryRepo | `src/horizon_research/controlplane/gateway.py` |
| Rollback tests | Product fixture | `src/horizon_research/controlplane/gateway.py` |
| CLI integration tests | Repo fixture or subprocess | `src/horizon_research/cli/main.py` |
| Config loading tests | Temp dirs | `src/horizon_research/controlplane/context.py` |
| Limitation/gap tests | Synthetic fixtures | `src/horizon_research/controlplane/execution/meta_verify.py`, benchmark validators |
| Characterization tests | Repo fixture | Old system + new system comparison |

### 18.3 The Key Property

Every test that uses `ProjectContext` can point it at an arbitrary directory.
No test ever needs to run `_sync_compatibility_state()` or import `horizon.py`
to make core modules work. This is the testability payoff of the rebuild.

Also keep **explicit limitation tests** for known blind spots. If the trust
engine cannot detect an "honest but wrong" verifier yet, that limitation
should live in a named test instead of disappearing into tribal knowledge.

---

## 19. Where to Put New Code

**Decision tree for placement:**

```
Is it parsing sys.argv or formatting CLI output?
    → src/horizon_research/cli/main.py, src/horizon_research/cli/formatters.py

Is it resolving paths from config or building ProjectContext?
    → src/horizon_research/controlplane/context.py

Is it declarative wiring between source data, generated outputs, and stale triggers?
        → src/horizon_research/controlplane/automation.py

Is it CRUD on a resource type, or orchestrating a mutation pipeline?
    → src/horizon_research/controlplane/gateway.py

Is it validating data for correctness?
    → src/horizon_research/controlplane/validate.py (orchestration) or src/horizon_research/epistemic/invariants.py (pure rules)

Is it generating markdown from JSON?
    → src/horizon_research/controlplane/render.py

Is it computing project health metrics?
    → src/horizon_research/controlplane/metrics.py

Is it checking links, staleness, or prose sync?
    → src/horizon_research/controlplane/check.py

Is it displaying project state or health summaries?
    → src/horizon_research/controlplane/status.py or src/horizon_research/controlplane/health.py

Is it executing scripts or enforcing sandbox policy?
    → src/horizon_research/controlplane/execution/scripts.py (dispatch) or src/horizon_research/adapters/sandbox_executor.py

Is it adversarial integrity checking of scripts?
    → src/horizon_research/controlplane/execution/meta_verify.py

Is it archiving/activating research programs?
  → program_manager (outer shell — NOT in the product core)

Is it about session types, boundaries, or close gates?
    → src/horizon_research/controlplane/governance/boundary.py, session.py, close.py

Is it pure domain logic (entities, invariants, graph queries)?
    → src/horizon_research/epistemic/
```

**The seven rules:**

1. If it parses `sys.argv`, it goes in `src/horizon_research/cli/`.
2. If it computes paths from config, it goes in `src/horizon_research/controlplane/context.py`.
3. If it expresses source -> output or stale-trigger wiring, it goes in `src/horizon_research/controlplane/automation.py`.
4. If it mutates canonical JSON, it goes through `src/horizon_research/controlplane/gateway.py`.
5. If it only reads data and returns findings, it goes in `src/horizon_research/controlplane/validate.py` or `src/horizon_research/epistemic/invariants.py`.
6. If it moves program directories around, it goes in `program_manager` (outer shell).
7. If it touches git, GitHub, or commit messages, it's governance/close-gate code.

---

## 20. CI/CD Rollout

CI should start **now**. CD should start only once the install surface is real.

### 20.1 Why CI/CD Belongs in the Plan

For Horizon, CI is not just a unit-test runner. It is an **off-machine audit
surface** that proves a delivered state still satisfies the control-plane
contracts:

- linting and unit/integration tests
- validation of canonical state
- generated-output drift detection
- markdown link integrity
- regression harness coverage for orchestration helpers
- artifact upload of machine-readable results

That model is already correct in the current repo and should survive the rebuild.

### 20.2 When to Set It Up

1. **Immediately, during the rebuild:** keep the existing post-push validation
    workflow on `main`. It protects delivered states while old and new systems
    coexist.
2. **By the end of Phase 1:** add a fast PR workflow for the new pure-domain
    surface. As soon as the domain exists, regressions in it are too expensive
    to catch manually.
3. **By the end of Phase 2:** make PR CI a required merge gate. This is the
    point where packaging, repositories, and characterization tests create a
    credible reusable product boundary.
4. **By the end of Phase 4:** add end-to-end product CI that exercises the
    installable CLI (`horizon init`, register, validate, render, health,
    export). That is the first point where the product is truly distributable.
5. **By the end of Phase 6:** add release automation (build, smoke install,
    publish prereleases/stable tags). Governance is optional and should not
    block package publishing.

### 20.3 Recommended Workflow Set

**`ci-pr.yml`** — fast pre-merge gate

- `ruff check`
- pure-domain and adapter unit tests
- packaging/config/workflow contract tests
- editable-install smoke test
- Linux first; add macOS once execution-path code lands

**`ci-main.yml`** — deeper post-merge audit lane

- full `pytest` with coverage
- `horizon validate --json`
- `horizon scaling --json`
- regression harness / orchestration checks
- `horizon render --check --json`
- `horizon check-refs --all --json`
- `horizon status --json`
- upload a validation bundle artifact (`coverage.xml`, JSON reports,
  workflow metadata)

**`release.yml`** — tag-driven delivery

- build `sdist` + wheel
- create a clean virtualenv and `pip install` the built artifacts
- smoke `horizon version`, `python -m horizon_research version`, and a tiny
  `horizon init` flow
- publish prereleases to TestPyPI first
- publish stable tags to PyPI only after smoke/install checks pass
- attach artifacts and release notes to a GitHub Release

### 20.4 What CI Should Test as Code

Do not rely on documentation to keep the automation honest. Add contract tests
that parse repo files directly and assert:

- `pyproject.toml` declares the expected console scripts and extras
- `horizon_research.__main__` remains functional
- coverage settings keep the right source roots and omit transient sabotage files
- workflow files still emit the expected coverage and validation artifacts
- default config/path contracts remain coherent

This is a good example of **Fail Fast**, **DRY**, and **Convention over
Configuration** applied to the build system itself.

### 20.5 CD Timing Recommendation

- **Now:** CI only. Do not try to publish packages yet.
- **After Phase 4 exit:** start TestPyPI prereleases for internal alpha builds.
- **After Phase 5 exit:** PyPI prereleases are reasonable if the human-first CLI
  is stable enough for external evaluation.
- **After Phase 6 exit:** stable PyPI releases become defensible because the
  execution pipeline, benchmark validation, and least-privilege runtime model
  are part of the shipped product rather than future promises.

If you want the short answer: **set up CI immediately, require PR CI by Phase 2,
start prerelease CD after Phase 4, and do stable release CD after Phase 6.**

---

## Dependency Graph

```
Phase 1 (Domain Core — epistemic web)
  └─► Phase 2 (Persistence + Testing + Packaging)
      └─► Phase 3 (Gateway + Control-Plane Services)
              └─► Phase 4 (CLI + Init + Health)
                    └─► Phase 5 (Human-First UX)
                          └─► Phase 6 (Execution Pipeline)
                                └─► Phase 7 (Governance Opt-In)
                                      └─► Backlog
```

Seven sequential phases. Each ships something testable. Each builds on the
last. The epistemic web is the foundation — get it right, and everything else
falls into place naturally.

---

## What This Plan Optimizes For

1. **Correctness first** — The domain model enforces invariants at every mutation.
   It's impossible to create an inconsistent epistemic web.
2. **Testability** — The domain is pure Python with no I/O. Tests run in
   milliseconds. External dependencies are injected through protocols.
3. **Time to first user** — 4 phases to a usable product.
4. **Each phase ships something real** — No phase is pure infrastructure.
5. **No speculative abstraction** — Plugin systems, event buses, config
   profiles all deferred until there's demand.
6. **Principled architecture** — Every design decision maps to a named
   software engineering principle (see the matrix above).
7. **Clean break** — Build the right thing from scratch. The old codebase
   proved the domain model; the new codebase gets the architecture right.
8. **Great UX** — Targeted dependencies (`click`, `rich`) make the tool
   feel professional and easy to use. Domain-general naming makes it
   accessible to any empirical discipline.
9. **Verification integrity** — Both false positives and false negatives
   are caught through a seven-layer verification pipeline, from static
   analysis through sensitivity testing to dual-implementation checks.

---

## The First 100 Lines You Write

```
1. epistemic/types.py    — ClaimId, AssumptionId, ..., Finding, Severity
2. epistemic/model.py    — Claim, Assumption, Prediction (dataclasses with set/list/dict)
3. epistemic/web.py      — EpistemicWeb with register_claim + invariant checks
4. tests/test_web.py      — 20 tests: register, duplicate, broken ref, cycle
5. epistemic/invariants.py — validate_tier_constraints, validate_coverage
6. tests/test_invariants.py — 10 tests: tier violations, coverage gaps
```

That's Phase 1. Everything else builds on this foundation.ves a delivered state still satisfies the control-plane
contracts:

- linting and unit/integration tests
- validation of canonical state
- generated-output drift detection
- markdown link integrity
- regression harness coverage for orchestration helpers
- artifact upload of machine-readable results

That model is already correct in the current repo and should survive the rebuild.

### 20.2 When to Set It Up

1. **Immediately, during the rebuild:** keep the existing post-push validation
    workflow on `main`. It protects delivered states while old and new systems
    coexist.
2. **By the end of Phase 1:** add a fast PR workflow for the new pure-domain
    surface. As soon as the domain exists, regressions in it are too expensive
    to catch manually.
3. **By the end of Phase 2:** make PR CI a required merge gate. This is the
    point where packaging, repositories, and characterization tests create a
    credible reusable product boundary.
4. **By the end of Phase 4:** add end-to-end product CI that exercises the
    installable CLI (`horizon init`, register, validate, render, health,
    export). That is the first point where the product is truly distributable.
5. **By the end of Phase 6:** add release automation (build, smoke install,
    publish prereleases/stable tags). Governance is optional and should not
    block package publishing.

### 20.3 Recommended Workflow Set

**`ci-pr.yml`** — fast pre-merge gate

- `ruff check`
- pure-domain and adapter unit tests
- packaging/config/workflow contract tests
- editable-install smoke test
- Linux first; add macOS once execution-path code lands

**`ci-main.yml`** — deeper post-merge audit lane

- full `pytest` with coverage
- `horizon validate --json`
- `horizon scaling --json`
- regression harness / orchestration checks
- `horizon render --check --json`
- `horizon check-refs --all --json`
- `horizon status --json`
- upload a validation bundle artifact (`coverage.xml`, JSON reports,
  workflow metadata)

**`release.yml`** — tag-driven delivery

- build `sdist` + wheel
- create a clean virtualenv and `pip install` the built artifacts
- smoke `horizon version`, `python -m horizon_research version`, and a tiny
  `horizon init` flow
- publish prereleases to TestPyPI first
- publish stable tags to PyPI only after smoke/install checks pass
- attach artifacts and release notes to a GitHub Release

### 20.4 What CI Should Test as Code

Do not rely on documentation to keep the automation honest. Add contract tests
that parse repo files directly and assert:

- `pyproject.toml` declares the expected console scripts and extras
- `horizon_research.__main__` remains functional
- coverage settings keep the right source roots and omit transient sabotage files
- workflow files still emit the expected coverage and validation artifacts
- default config/path contracts remain coherent

This is a good example of **Fail Fast**, **DRY**, and **Convention over
Configuration** applied to the build system itself.

### 20.5 CD Timing Recommendation

- **Now:** CI only. Do not try to publish packages yet.
- **After Phase 4 exit:** start TestPyPI prereleases for internal alpha builds.
- **After Phase 5 exit:** PyPI prereleases are reasonable if the human-first CLI
  is stable enough for external evaluation.
- **After Phase 6 exit:** stable PyPI releases become defensible because the
  execution pipeline, benchmark validation, and least-privilege runtime model
  are part of the shipped product rather than future promises.

If you want the short answer: **set up CI immediately, require PR CI by Phase 2,
start prerelease CD after Phase 4, and do stable release CD after Phase 6.**

---

## Dependency Graph

```
Phase 1 (Domain Core — epistemic web)
  └─► Phase 2 (Persistence + Testing + Packaging)
      └─► Phase 3 (Gateway + Control-Plane Services)
              └─► Phase 4 (CLI + Init + Health)
                    └─► Phase 5 (Human-First UX)
                          └─► Phase 6 (Execution Pipeline)
                                └─► Phase 7 (Governance Opt-In)
                                      └─► Backlog
```

Seven sequential phases. Each ships something testable. Each builds on the
last. The epistemic web is the foundation — get it right, and everything else
falls into place naturally.

---

## What This Plan Optimizes For

1. **Correctness first** — The domain model enforces invariants at every mutation.
   It's impossible to create an inconsistent epistemic web.
2. **Testability** — The domain is pure Python with no I/O. Tests run in
   milliseconds. External dependencies are injected through protocols.
3. **Time to first user** — 4 phases to a usable product.
4. **Each phase ships something real** — No phase is pure infrastructure.
5. **No speculative abstraction** — Plugin systems, event buses, config
   profiles all deferred until there's demand.
6. **Principled architecture** — Every design decision maps to a named
   software engineering principle (see the matrix above).
7. **Clean break** — Build the right thing from scratch. The old codebase
   proved the domain model; the new codebase gets the architecture right.
8. **Great UX** — Targeted dependencies (`click`, `rich`) make the tool
   feel professional and easy to use. Domain-general naming makes it
   accessible to any empirical discipline.
9. **Verification integrity** — Both false positives and false negatives
   are caught through a seven-layer verification pipeline, from static
   analysis through sensitivity testing to dual-implementation checks.

---

## The First 100 Lines You Write

```
1. epistemic/types.py    — ClaimId, AssumptionId, ..., Finding, Severity
2. epistemic/model.py    — Claim, Assumption, Prediction (dataclasses with set/list/dict)
3. epistemic/web.py      — EpistemicWeb with register_claim + invariant checks
4. tests/test_web.py      — 20 tests: register, duplicate, broken ref, cycle
5. epistemic/invariants.py — validate_tier_constraints, validate_coverage
6. tests/test_invariants.py — 10 tests: tier violations, coverage gaps
```

That's Phase 1. Everything else builds on this foundation.