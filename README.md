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
8. [Phase 4 — CLI, Init, Doctor](#8-phase-4--cli-init-doctor)
9. [Phase 5 — Human-First UX](#9-phase-5--human-first-ux)
10. [Phase 6 — Execution Pipeline](#10-phase-6--execution-pipeline)
11. [Phase 7 — Governance as Opt-In](#11-phase-7--governance-as-opt-in)
12. [After Phase 7: The Backlog](#12-after-phase-7-the-backlog)
13. [Principle Compliance Matrix](#13-principle-compliance-matrix)
14. [Migration Path from Current Codebase](#14-migration-path-from-current-codebase)
15. [Standing Decisions](#15-standing-decisions)
16. [Data Flow Diagram](#16-data-flow-diagram)
17. [End-to-End Traces](#17-end-to-end-traces)
18. [Testing Strategy and Fixture Model](#18-testing-strategy-and-fixture-model)
19. [Where to Put New Code](#19-where-to-put-new-code)
20. [CI/CD Rollout](#20-cicd-rollout)

---

## 1. Goal

Someone can `pip install horizon-research`, run `horizon init`, register
research claims/predictions/hypotheses, validate their work, render readable
outputs, and get a useful `horizon doctor` report — all without an AI agent,
without JSON editing, and without understanding governance or session types.

The rebuild starts from the epistemic web — the core data structure — and
layers outward. Each phase ships something testable.

Horizon should be rebuilt as a **control plane over a research data plane**.
The epistemic web is the domain kernel, but the product is larger than the
kernel: the gateway, validators, renderers, doctor, execution policy, and
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

A clean rebuild avoids all of that. We use the existing codebase as a
**behavioral specification** — it tells us what the correct outputs are for
given inputs — and build a new system that produces the same results with
clean architecture.

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
    context building, gateway, validators, renderers, doctor/status, execution
    policy, and optional governance services.
- The **epistemic web** is the in-memory domain kernel inside the control
    plane, not the whole product.

This distinction matters because it keeps the rebuild from collapsing into
"just a graph library." The product is valuable because it manages the
research project end-to-end.

### 3.2 Control-Plane Subsystems We Should Keep

1. **ProjectContext** — one explicit runtime contract for paths, config,
     caches, logs, and feature flags.
2. **Gateway** — the single mutation and query boundary exposed to the CLI and
     automation.
3. **Read-only services** — validate, render, doctor, status, export, and
     other computed read models.
4. **Execution-policy pipeline** — registered scripts, sandboxing,
     machine-readable benchmark validation, and meta-verification.
5. **Governance layer** — sessions, boundaries, and close gates as opt-in.
6. **Outer-shell workspace tooling** — multi-program or repo-management tools
     stay outside the product core.

Not every old implementation detail survives. But these subsystem boundaries
were good ideas and should be preserved.

### 3.3 The Layer Cake

```
┌─────────────────────────────────────────────────┐
│  CLI / API Adapters                             │
│  Parses input, formats output, sets exit codes  │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  ProjectContext                                 │
│  Runtime contract: paths, config, caches, logs  │
└──────────────────────┬──────────────────────────┘
                                             │
┌──────────────────────▼──────────────────────────┐
│  Control-Plane Services                         │
│  Gateway | Validate | Render | Doctor | Status  │
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
    mutations, adapters perform I/O, and the CLI speaks to users.
- **Low Coupling**: The gateway talks to the domain through typed entities and
    ports, not through global module state.

### 3.4 Package Layout

```
epistemic/                          # Top-level package
├── __init__.py
├── domain/                         # Core domain model
│   ├── __init__.py
│   ├── types.py                    # Enums, typed IDs, findings
│   ├── model.py                    # Entity dataclasses
│   ├── web.py                      # EpistemicWeb aggregate root
│   ├── invariants.py               # Cross-entity validation rules
│   └── ports.py                    # Repository, renderer, executor, tx log
├── controlplane/                   # Product logic above the domain
│   ├── __init__.py
│   ├── context.py                  # ProjectContext builder and path derivation
│   ├── automation.py               # Declarative render/stale-trigger contracts
│   ├── gateway.py                  # Single mutation/query boundary
│   ├── validate.py                 # Read-only validation orchestration
│   ├── render.py                   # Generated surfaces (incremental SHA-256 caching)
│   ├── check.py                    # check-refs, check-stale, sync-prose, verify-prose-sync
│   ├── metrics.py                  # Repo metrics, correlation-aware tier-A evidence
│   ├── doctor.py                   # Health checks (composes validate + render-check + structure)
│   ├── status.py                   # Read models / summaries (consumes metrics)
│   ├── export.py                   # Bulk export
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── scripts.py              # Registered script dispatch
│   │   ├── policy.py               # Execution policy normalization
│   │   └── meta_verify.py          # Adversarial integrity checks
│   └── governance/
│       ├── __init__.py
│       ├── boundary.py             # Session boundary enforcement
│       ├── session.py              # Session metadata helpers
│       └── close.py                # Close-gate engine (git publish optional)
├── adapters/                       # Infrastructure
│   ├── __init__.py
│   ├── json_repository.py          # Implements WebRepository
│   ├── markdown_renderer.py        # Implements WebRenderer
│   ├── sandbox_executor.py         # Implements ScriptExecutor
│   └── transaction_log.py          # Query/mutation provenance log
├── cli/                            # CLI adapter
│   ├── __init__.py
│   ├── main.py                     # Entry point, arg parsing, dispatch
│   └── formatters.py               # Human/JSON output formatting
├── horizon_research/               # Public compatibility wrapper
│   ├── __init__.py                 # Version + public helpers
│   ├── cli.py                      # Thin adapter to internal CLI
│   └── __main__.py                 # `python -m horizon_research`
└── config.py                       # User config loading
```

**Principles:**
- **Single Responsibility (S)**: `domain/` models epistemic truth,
    `controlplane/` orchestrates product behavior, `adapters/` perform I/O,
    `cli/` handles presentation.
- **High Cohesion**: Gateway, validate, render, and doctor sit together as the
    control-plane layer because they jointly manage the project.
- **Acyclic Dependencies (ADP)**: `cli → controlplane → domain ← adapters`.
- **Stable Dependencies (SDP)**: `domain/` changes least, `cli/` changes most.

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
        status: str
        changed: bool
        message: str
        findings: list[Finding]
        transaction_id: str | None = None


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

**No frameworks.** stdlib only in the domain. `json` and `pathlib` only in
adapters. No ORM, no dependency injection container, no schema library.

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
   [P]-type assumptions need falsifiable consequences

### 4.4 Generalizing Beyond Physics

The current system has physics-flavored vocabulary. To make it general-purpose:

- **Tier A/B/C** → user-defined confidence tiers (any domain)
- **Measurement regime** → evidence availability categories (any domain)
- **Observed/predicted values** → expected/actual outcomes (numeric, categorical, boolean)
- **Independence groups** → evidence independence clusters (applies to medicine,
  ML, social science — anywhere correlated evidence inflates confidence)

The invariants (bidirectionality, acyclicity, referential integrity, independence
semantics) are **domain-independent**. They're properties of sound reasoning.

### 4.5 What the Web Looks Like Across Domains

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

### 5.1 Type Foundation (`domain/types.py`)

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

### 5.2 Entity Classes (`domain/model.py`)

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
    type: str                                    # "P" (postulate), "D" (derived)
    scope: str                                   # "global", "sector-specific"
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
    type: str                                    # "P" (physical), "M" (mathematical)
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

### 5.3 The Aggregate Root (`domain/web.py`)

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
    IndependenceGroup, PairwiseSeparation, Prediction, Script,
)
from .types import (
    AssumptionId, ClaimId, ConceptId, DiscoveryId, FailureId, Finding,
    HypothesisId, IndependenceGroupId, PredictionId, ScriptId, Severity,
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
        new.claims[claim.id] = claim

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
        """Deep copy for copy-on-write mutation semantics."""
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

### 5.4 Cross-Entity Validation (`domain/invariants.py`)

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
        if assumption.type == "P" and not assumption.falsifiable_consequence:
            findings.append(Finding(
                Severity.WARNING,
                f"assumptions/{aid}",
                "[P] assumption has no falsifiable consequence",
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

### 5.5 Ports (`domain/ports.py`)

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
| 1.1 | `domain/types.py` — IDs, enums, Finding | Enum membership, Finding construction |
| 1.2 | `domain/model.py` — All entity dataclasses | Construction, field defaults |
| 1.3 | `domain/web.py` — EpistemicWeb with register methods | Happy path: register each entity type |
| 1.4 | `domain/web.py` — Rejection cases | Duplicate ID, broken reference, cycle detection |
| 1.5 | `domain/web.py` — Bidirectional links | Register claim → assumption.used_in_claims auto-updated |
| 1.6 | `domain/web.py` — Lineage queries | claim_lineage, assumption_lineage on multi-level graphs |
| 1.7 | `domain/invariants.py` — All validators | Build webs with known violations, assert findings |
| 1.8 | `domain/ports.py` — Protocol definitions | No tests (type definitions only) |

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
dependencies = []                    # stdlib-only core

[project.scripts]
horizon = "epistemic.cli.main:main"
horizon-research = "epistemic.cli.main:main"

[project.optional-dependencies]
compute = ["numpy>=2.4,<3", "scipy>=1.17,<2"]
literature = []
dev = ["pytest>=8.3,<9", "pytest-cov>=6,<7", "ruff>=0.11,<0.12"]
```

Core package has **zero dependencies**. Compute libraries are opt-in for
verification scripts that need them.

Keep a thin public wrapper package as the release boundary:

```python
# horizon_research/cli.py
from epistemic.cli.main import main
```

This preserves a stable console-script and import contract while the internal
engine evolves. During migration the wrapper can point at the legacy CLI;
after cutover it points at the rebuilt CLI with no user-facing entrypoint
change.

Packaging contracts should be tested as code, not left implicit in prose:

- `pyproject.toml` declares the public console scripts and extras
- `horizon_research.__main__` supports `python -m horizon_research`
- coverage settings and workflow artifact expectations are locked by tests
- editable-install smoke tests happen in Phase 2; wheel and sdist smoke tests
    become mandatory by the Phase 4 exit criteria

### 6.4 Phase 2 Deliverables

| Step | What | Tests |
|------|------|-------|
| 2.1 | `adapters/json_repository.py` — load all entity types from JSON | Round-trip: construct web → save → load → compare |
| 2.2 | Schema evolution — handle v1/v2 JSON variants | Load v1 fixture, assert correct domain objects |
| 2.3 | `InMemoryRepository` | Already trivial — verify protocol compliance |
| 2.4 | `pyproject.toml` + `horizon_research/` wrapper — installable package boundary | `pip install -e .`, console-script smoke, `python -m horizon_research` |
| 2.5 | Contract tests for packaging, config, and workflow surfaces | Parse `pyproject.toml`, default paths, coverage settings, workflow artifact contract |
| 2.6 | Load current Horizon project data | Load the live `project/data/` into new domain model |
| 2.7 | Characterization tests | Load current project → validate → compare findings with `horizon validate` output |

### Phase 2 Exit Criteria

- [ ] `JsonFileRepository` can load all current JSON data files
- [ ] Save→load round trip produces identical domain objects
- [ ] Package installs cleanly with `pip install -e .`
- [ ] Public console scripts and `python -m horizon_research` are stable
- [ ] Packaging/config/workflow contracts are locked by tests
- [ ] Characterization tests confirm behavioral equivalence with current system

---

## 7. Phase 3 — Gateway and Control-Plane Services

**Goal:** Build the product layer that makes Horizon a control plane again:
`ProjectContext`, a typed gateway, read-only services, and the explicit write
transaction boundary.

This phase is where the rebuild stops looking like a domain library and starts
looking like Horizon.

### 7.1 ProjectContext (`controlplane/context.py`)

Implement the runtime contract first. The control plane should build one
`ProjectContext` and thread it through gateway, validation, rendering, doctor,
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
- `doctor.py` — composes validate, render-check, and project-structure checks
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
| 3.9 | `controlplane/status.py`, `doctor.py`, `export.py` | Read-model and doctor tests |
| 3.10 | Transaction / provenance log adapter | Append, rollback, and dry-run behavior tests |

**Target: ~60 additional tests.**

### Phase 3 Exit Criteria

- [ ] Gateway is the single mutation/query boundary used by the CLI
- [ ] Full register → validate → render → sync → log pipeline works end-to-end
- [ ] Downstream failures restore prior canonical state cleanly
- [ ] Dry-run returns the same result envelope without persisting
- [ ] Read-only services run from explicit `ProjectContext`
- [ ] Render outputs and stale triggers come from declarative automation config
- [ ] Markdown output matches current Horizon behavior for the same data

---

## 8. Phase 4 — CLI, Init, Doctor

**Goal:** The product is usable from the command line. New users can start a
project and check its health.

### 8.1 CLI Output Contract

Every command supports two output modes:

- **Human mode** (default): Formatted text to stdout.
- **Machine mode** (`--json`): A JSON envelope to stdout.

The JSON envelope always has a `status` key and a shape that can be reliably
parsed by scripts and agent tooling:

```json
{
  "status": "CLEAN" | "BLOCKED" | "ok" | "error",
  "...": "command-specific fields"
}
```

This dual-output pattern is how the tool serves both interactive researchers
and the AI agent framework. All agent/script consumers should parse
`result["status"]` first and branch on it.

### 8.2 CLI Command Dispatch Table

| Command | Service Module | Read/Write |
| --- | --- | --- |
| `validate` | `validate.run_validate(context, ...)` | Read |
| `render` | `render.run_render(context, ...)` | Write (generates markdown) |
| `status` | `status.print_status(context, ...)` | Read |
| `scaling` | `status.print_scaling(context, ...)` | Read |
| `get` | `gateway.get(context, ...)` | Read |
| `list` | `gateway.list(context, ...)` | Read |
| `set` | `gateway.set(context, ...)` | Write |
| `append` | `gateway.append(context, ...)` | Write |
| `transition` | `gateway.transition(context, ...)` | Write |
| `register` | `gateway.register(context, ...)` | Write |
| `query` | `gateway.query(context, ...)` | Read |
| `run-script` | `execution.run_script(context, ...)` | Execute |
| `check-stale` | `check.run_check_stale(context)` | Read |
| `check-refs` | `check.run_check_refs(context, ...)` | Read (+ cache) |
| `sync-prose` | `check.run_sync_prose(context, ...)` | Write |
| `verify-prose-sync` | `check.run_verify_prose_sync(context, ...)` | Read |
| `research-watch` | `research_watch.run_research_watch(context, ...)` | Mixed (opt-in) |
| `version` | (inline) | Read |
| `doctor` | `doctor.run_doctor(context)` | Read |
| `init` | `init.run_init(context, ...)` | Write (creates scaffold) |
| `export` | `export.run_export(context, ...)` | Read |
| `program` | `program_manager.run_program_command(...)` | Outer shell |

Every command is one function call with `context` as the first argument. The
CLI is a dispatch table, nothing more.

### 8.3 CLI Entry Point (`cli/main.py`)

Thin dispatch layer. Parses argv, builds `ProjectContext`, constructs the
gateway and read-only services, calls the right control-plane operation, and
formats output.

```python
def main():
    command, args = parse_argv(sys.argv)
    context = build_project_context(Path.cwd())
    repo = JsonFileRepository(context.paths.data_dir)
    gateway = build_gateway(context, repo)

    if command == "validate":
        result = run_validate(context, repo)
        format_result(result, json_mode=args.json)
    elif command == "register":
        entity = parse_entity(args.resource_type, args.id, args.payload)
        result = gateway.register(args.resource_type, entity, dry_run=args.dry_run)
        format_result(result, json_mode=args.json)
    # ... etc
```

**Principles:**
- **Single Responsibility**: CLI parses input and formats output. Nothing else.
- **Separation of Concerns**: CLI depends on the control-plane layer, not on
  domain internals.
- **KISS**: One function dispatches. No plugin loading, no middleware.

Keep `horizon_research.cli` and `horizon_research.__main__` as thin public
adapters over this internal CLI. The release boundary stays stable even if the
internal engine package and module graph keep changing during the rebuild.

### 8.2 Configuration and Context (`config.py`, `controlplane/context.py`)

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
    else:
        return HorizonConfig()

def build_project_context(workspace: Path) -> ProjectContext:
    config = load_config(workspace)
    project_dir = workspace / config.project_dir
    return ProjectContext(
        workspace=workspace,
        config=config,
        paths=ProjectPaths(
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
        ),
    )
```

### 8.3 `horizon init`

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
- `--with-agent` — adds template agent adapter files
- `--with-governance` — adds session types, boundary rules (Phase 7)

Idempotent: safe to run on an existing project (fills in missing pieces).

### 8.4 `horizon doctor`

Project health check composed from existing capabilities:

1. Are all expected data files present and valid JSON?
2. Do cross-references resolve? (validates the web)
3. Are rendered views current? (render `--check` under the hood)
4. Are there orphaned resources?
5. Schema validation pass/fail
6. Verification coverage gaps

Clear, readable output with severity levels.

### 8.5 `horizon export --format=json`

Bulk export of all data. The "eject button."

### 8.6 Phase 4 Deliverables

| Step | What | Tests |
|------|------|-------|
| 4.1 | `config.py` — load from horizon.toml with defaults | Config with/without toml, custom project_dir |
| 4.2 | `cli/main.py` — validate, get, list, register, transition | Subprocess tests: check JSON output shape |
| 4.3 | `cli/formatters.py` — human + JSON output | Unit tests for formatting |
| 4.4 | `horizon init` | Creates correct directory structure |
| 4.5 | `horizon doctor` | Reports known issues in test fixture |
| 4.6 | `horizon export --format=json` | Exports all data as valid JSON |
| 4.7 | `horizon version` | Prints version, Python version, workspace path |
| 4.8 | Backward compat | Current Horizon repo works with new CLI |

### Release Checkpoint: First Internal Product Alpha

After Phase 4, someone can:

```bash
pip install horizon-research
cd my-research-project
horizon init
horizon register claim C-001 '{"statement":"...", "type":"P", ...}'
horizon validate --json
horizon render
horizon doctor
horizon export --format=json
```

### Phase 4 Exit Criteria

- [ ] CLI dispatches all core commands
- [ ] `horizon init` creates valid project scaffold
- [ ] `horizon doctor` reports health accurately
- [ ] Both human and JSON output modes work
- [ ] Config is optional (defaults work without horizon.toml)
- [ ] Current Horizon repo data loadable through new system

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
| 5 | `horizon status` | Readable summary with doctor counts. |
| 6 | `horizon log [id]` | Mutation history from transaction log. |
| 7 | Quickstart guide | Install, init, add hypothesis, add prediction, validate, render. |

For `horizon add prediction`, also prompt for:
- The mathematical relationship being tested (human-readable)
- The expected value with units

This is the formula contract that closes the false-negative gap.

### 9.2 What This Phase is NOT

- No progressive-disclosure dual CLI. Simple commands (`add`, `show`, `check`)
  coexist with power commands (`register`, `get`, `set`, `query`).
- No `horizon dashboard`. `status` is enough.
- No static HTML rendering. Markdown is fine for now.

### Release Checkpoint: First External Human-Usable Alpha

### Phase 5 Exit Criteria

- [ ] A researcher can use the tool without writing JSON
- [ ] Interactive add works for all core entity types
- [ ] `horizon show` displays entity with relationships
- [ ] Quickstart guide is written and tested

---

## 10. Phase 6 — Execution Pipeline

**Goal:** Verification scripts run in a sandboxed environment with
adversarial integrity checking.

### 10.1 Three-Layer Architecture

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

### 10.2 Sandbox Executor (implements ScriptExecutor port)

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

### 10.3 Meta-Verification

Five layers, ported from the current system:
- **L1**: Static AST analysis (unconditional success prints, missing exit codes)
- **L2**: Runtime execution (script exits cleanly)
- **L3**: Sabotage injection (break constants, verify detection)
- **L4**: Reference value cross-check
- **L5**: Tolerance audit

L1 walks the AST to find `print()` calls containing success keywords (like
"CONFIRMED ✓") that are NOT inside an `if` block. This catches the most
dangerous anti-pattern: scripts that claim success unconditionally.

L3 uses a sabotage registry — each entry describes a specific constant
corruption and what it should break. A **multi-constant sabotage registry**
also tests for compensating errors (e.g., M_Pl ×2 AND M_Z ×2 might preserve
a ratio).

Runtime results are cached using **semantic AST fingerprints** — the AST is
hashed rather than source text, so comment-only edits reuse expensive L2/L3
results.

Sabotage registry and reference values move to project-level metadata (not
hardcoded in product code).

### 10.4 Benchmark Validation

Scripts with `machine_readable_output: true` produce structured data following
the `verification_benchmark_v1` contract:

```json
{
  "schema": "verification_benchmark_v1",
  "predictions": {
    "A-001": {
      "predicted": 0.2253,
      "computed": 0.2254,
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

### 10.5 Phase 6 Deliverables

| Step | What | Tests |
|------|------|-------|
| 6.1 | `sandbox_executor.py` — implements ScriptExecutor | Integration with test scripts |
| 6.2 | Sandbox runner — write guard, network guard, subprocess guard | Security tests |
| 6.3 | Execution policy — context normalization | Policy parsing and validation |
| 6.4 | `horizon run-script <id>` | End-to-end script execution |
| 6.5 | Meta-verification L1-L3 | AST analysis, sabotage injection |
| 6.6 | Benchmark validation | Compare predicted vs. observed with tolerance |
| 6.7 | Limitation tests for known integrity blind spots | Honest-but-wrong verifier fixtures, documented non-goals |

### Phase 6 Exit Criteria

- [ ] Scripts execute in sandboxed environment
- [ ] Deny-by-default: no network, no writes outside allowed paths
- [ ] Meta-verification catches unconditional success prints
- [ ] Sabotage injection detects scripts that don't actually verify
- [ ] Benchmark validation catches tolerance violations
- [ ] Known trust-engine blind spots are codified in tests and documentation

---

## 11. Phase 7 — Governance as Opt-In

**Goal:** Sessions, boundaries, and close gates work as an opt-in layer
without affecting the core experience.

### 11.1 Deliverables

| # | Feature | Description |
|---|---------|-------------|
| 1 | `horizon init --with-governance` | Adds session types, boundary rules, close config |
| 2 | `horizon upgrade --add=governance` | Add governance to existing project |
| 3 | Mutation provenance | `_last_modified`, `_modified_by` on every write. In governance mode: `_modification_session`. |
| 4 | Conditional session logic | `governance.enabled = false`: no boundaries, no close gate, no session numbers |
| 5 | Git integration conditional | Core never touches git. Governance uses it when available. |
| 6 | Session data reclassification | `session_state.json`, `session_summaries.json`, `session_types.json` are governance data |
| 7 | Split `session_close.py` | Reusable close-gate engine (checks + findings) separate from git publish workflow |
| 8 | Split verification framework | Generic L1-L3 in product code; sabotage coverage/reference values in project metadata |

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
- [ ] Session boundaries enforced when governance enabled
- [ ] Close gate runs checks and returns findings
- [ ] Git publish is optional and separate from close-gate logic
- [ ] Mutation provenance recorded on every write

---

## 12. After Phase 7: The Backlog

Everything below is real and valuable but not on the critical path.

### High-Value (Do When There's Demand)

- Schema versioning + `horizon migrate`
- `horizon export --format=csv|notebook|bibtex`
- `horizon import` from BibTeX/CSV
- Domain generalization — configurable resource types beyond physics
- Research graph traversal — `horizon trace`, `horizon impact`
- Shell completions
- Example projects

### Medium-Value (Real Features, Not Urgent)

- Schema-driven gateway — resource types in config instead of Python
- Static HTML rendering — `horizon render --format=html`
- `horizon doctor` as CI check
- Multi-user merge / conflict resolution
- `horizon challenge` — adversarial analysis of claims

### Aspirational (Someday, Maybe)

- Hypothesis tournaments
- Interactive graph explorer
- Paper draft generation
- Evidence quality scoring
- MCP server
- Pre-registration export (OSF format)
- Progressive-disclosure CLI modes
- XDG-compliant config paths

---

## 13. Principle Compliance Matrix

| Principle | How It's Followed | Where |
|-----------|-------------------|-------|
| **Reuse/Release Equivalence (REP)** | The public release boundary is `horizon_research`; internal engine modules can change behind it without changing console scripts | Phase 2 packaging, migration path |
| **S — Single Responsibility** | Each module has exactly one reason to change | `web.py` (graph rules), `controlplane/gateway.py` (transaction boundary), `json_repository.py` (serialization), `main.py` (parsing) |
| **O — Open/Closed** | New validators = new functions, not modifications. New entity types = new classes. | `invariants.py`, `model.py` |
| **L — Liskov Substitution** | `InMemoryRepository` and `JsonFileRepository` interchangeable | `ports.py`, all adapters |
| **I — Interface Segregation** | `WebRepository` has only `load()` and `save()`. `ScriptExecutor` is separate. | `ports.py` |
| **D — Dependency Inversion** | Domain defines protocols. Adapters implement them. The control plane depends on abstractions. | `ports.py`, `controlplane/gateway.py` |
| **Low Coupling** | Domain has zero imports from adapters or CLI | Package DAG: `cli → controlplane → domain ← adapters` |
| **High Cohesion** | `domain/` = reasoning. `controlplane/` = product orchestration. `adapters/` = I/O. `cli/` = UI. | Package layout |
| **Common Closure (CCP)** | Modules that change together are packaged together: automation/render/check, execution policy/meta-verify, governance close/session/boundary | `controlplane/`, `execution/`, `governance/` |
| **Common Reuse (CRP)** | Optional governance and literature surfaces stay separate from the core install and core workflows | Package layout, optional extras |
| **DRY** | Bidirectional links maintained once (web mutations). Validation rules each exist once. | `web.py`, `invariants.py` |
| **KISS** | Plain dataclasses, native Python types, `dict`/`set`/`list`. No metaclasses, no frameworks. | Entire codebase |
| **YAGNI** | No plugin system, no event bus, no database, no web server, no generic graph engine | Explicit in Phase 1-7 scope limits |
| **Separation of Concerns** | Structural invariants (mutation-time) vs semantic validation (on-demand) vs persistence vs rendering vs UI | Layer architecture |
| **Convention over Configuration** | Default `project/` layout and minimal `horizon.toml`; declarative automation graph only for the places that truly vary | `controlplane/context.py`, `controlplane/automation.py` |
| **Principle of Least Privilege** | Execution defaults to no network, no subprocess, no writes outside declared roots; CI defaults to read-only permissions except release jobs | `execution/policy.py`, `adapters/sandbox_executor.py`, CI/CD rollout |
| **Law of Demeter** | Entities hold IDs, not objects. Traverse through `EpistemicWeb` methods. | `model.py`, `web.py` |
| **Composition over Inheritance** | No entity inherits from another. Protocols for interfaces, not abstract base classes. | `model.py`, `ports.py` |
| **Encapsulation** | All invariant enforcement inside `EpistemicWeb`. External code uses methods, not direct mutation. | `web.py` |
| **Abstraction** | External code sees `web.register_claim()`, not back-reference bookkeeping. | `web.py` |
| **Polymorphism** | All validators: `(Web) -> list[Finding]`. All repos: `WebRepository` protocol. | `invariants.py`, `ports.py` |
| **Fail Fast** | Domain throws on broken refs/cycles. Don't wait for post-hoc validation. | `web.py` |
| **Acyclic Dependencies (ADP)** | `cli → controlplane → domain ← adapters`. No cycles. | Package DAG |
| **Stable Dependencies (SDP)** | `domain/` (most stable) ← everything else. `cli/` (least stable) → `controlplane/`. | Package DAG |
| **Stable Abstractions (SAP)** | Stable packages define protocols and normalized contracts; unstable packages stay concrete and close to I/O | `domain/ports.py`, `controlplane/automation.py`, `cli/`, `adapters/` |

---

## 14. Migration Path from Current Codebase

### 14.1 Coexistence Strategy

Build `epistemic/` as a **separate package** alongside `src/horizon_core/`.
Both systems read the same JSON files.

1. Build `epistemic/` with full test coverage (Phases 1-3)
2. Write `JsonFileRepository` to read the same JSON the current system uses
3. Run both systems against same data — characterization tests
4. Build the new control plane (`epistemic/controlplane`) and CLI on top of it
5. Gradually move commands from old CLI to new CLI
6. When all commands are routed, remove `src/horizon_core/`

### 14.2 Behavioral Equivalence Tests

For each command:
- Run through old system → capture JSON output
- Run through new system → capture JSON output
- Assert structural equivalence (same keys, compatible values)

This is the safety net for the migration.

### 14.3 What Gets Ported vs. Rewritten

| Component | Action | Rationale |
|-----------|--------|-----------|
| Domain model (entities, invariants) | **Rewrite** from scratch | New typed model is strictly better |
| Control-plane context | **Preserve the concept, rewrite the implementation** | One runtime contract object is correct; globals and monkey-patching are not |
| Declarative automation graph | **Preserve the concept, rewrite the loader** | Source -> output wiring and stale-trigger propagation belong in structured config, not scattered code |
| Gateway | **Preserve the subsystem, rewrite the implementation** | Single mutation/query boundary is a keeper; untyped spec tables and global wiring are not |
| JSON serialization | **Rewrite** to read same format | Clean adapter, no legacy cruft |
| Validation rules | **Port** the logic, rewrite the wiring | Rules are correct, wiring is broken |
| Rendering | **Port** the templates, rewrite incremental caching | Templates are proven, caching needs clean I/O |
| Sandbox execution | **Port** largely as-is | Already the cleanest subsystem |
| Meta-verification | **Port** L1-L3, move registries to project metadata | Generic logic stays, project-specific data moves |
| Session/governance | **Rewrite** as opt-in layer | Currently fused with core; needs clean separation |
| Public `horizon_research` wrapper | **Preserve** | Stable release boundary and console scripts while internals are replaced |
| CLI surface | **Preserve** command names, **rewrite** implementation | User muscle memory; clean dispatch |
| `_sync_compatibility_state` | **Delete** | The entire reason for the rebuild |

---

## 15. Standing Decisions

- Horizon is rebuilt as a **control plane** over a project **data plane**.
- The gateway remains the single mutation/query boundary.
- The live research workflow is never blocked by the rebuild.
- New projects are core-only by default.
- Governance (sessions, boundaries, close gates) is opt-in.
- Literature watch is opt-in, off by default.
- Agent config is opt-in, not shipped by default.
- Network access is off by default.
- Distribution name: `horizon-research`.
- Import namespace: `epistemic` (internal), `horizon_research` (public).
- Primary CLI: `horizon`.
- Optional CLI alias: `horizon-research`.
- Declarative automation graph remains the source of truth for generated-output
    wiring and stale-trigger propagation.
- Packaging, config, and workflow contracts should be tested as code.
- Flat JSON files. Reconsider only if merge conflicts become a real problem.
- Native Python types (`dict`, `set`, `list`) in the domain model.
- stdlib-only core. Compute deps (`numpy`, `scipy`) are optional extras.

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

Module imports: `cli/main.py` → `controlplane/validate.py` →
`domain/invariants.py`, `adapters/json_repository.py`. No cycles.

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
| Domain model unit tests | In-memory only | `domain/web.py`, `domain/invariants.py` |
| Repository round-trip tests | Product fixture | `adapters/json_repository.py` |
| Validator unit tests | Product fixture | `controlplane/validate.py` |
| Renderer snapshot tests | Product fixture | `controlplane/render.py` |
| Automation/config contract tests | Parse files as data | `controlplane/automation.py`, `pyproject.toml`, workflow files |
| Gateway integration tests | Product fixture + InMemoryRepo | `controlplane/gateway.py` |
| Rollback tests | Product fixture | `controlplane/gateway.py` |
| CLI integration tests | Repo fixture or subprocess | `cli/main.py` |
| Config loading tests | Temp dirs | `controlplane/context.py` |
| Limitation/gap tests | Synthetic fixtures | `execution/meta_verify.py`, benchmark validators |
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
  → cli/main.py, cli/formatters.py

Is it resolving paths from config or building ProjectContext?
  → controlplane/context.py

Is it declarative wiring between source data, generated outputs, and stale triggers?
    → controlplane/automation.py

Is it CRUD on a resource type, or orchestrating a mutation pipeline?
  → controlplane/gateway.py

Is it validating data for correctness?
  → controlplane/validate.py (orchestration) or domain/invariants.py (pure rules)

Is it generating markdown from JSON?
  → controlplane/render.py

Is it computing project health metrics?
  → controlplane/metrics.py

Is it checking links, staleness, or prose sync?
  → controlplane/check.py

Is it displaying project state or health summaries?
  → controlplane/status.py or controlplane/doctor.py

Is it executing scripts or enforcing sandbox policy?
  → controlplane/execution/scripts.py (dispatch) or adapters/sandbox_executor.py

Is it adversarial integrity checking of scripts?
  → controlplane/execution/meta_verify.py

Is it archiving/activating research programs?
  → program_manager (outer shell — NOT in the product core)

Is it about session types, boundaries, or close gates?
  → controlplane/governance/boundary.py, session.py, close.py

Is it pure domain logic (entities, invariants, graph queries)?
  → domain/
```

**The seven rules:**

1. If it parses `sys.argv`, it goes in `cli/`.
2. If it computes paths from config, it goes in `controlplane/context.py`.
3. If it expresses source -> output or stale-trigger wiring, it goes in `controlplane/automation.py`.
4. If it mutates canonical JSON, it goes through `controlplane/gateway.py`.
5. If it only reads data and returns findings, it goes in `controlplane/validate.py` or `domain/invariants.py`.
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
    installable CLI (`horizon init`, register, validate, render, doctor,
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
              └─► Phase 4 (CLI + Init + Doctor)
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
3. **Time to first user** — 4 phases to a usable CLI product.
4. **Each phase ships something real** — No phase is pure infrastructure.
5. **No speculative abstraction** — Plugin systems, event buses, config
   profiles all deferred until there's demand.
6. **Principled architecture** — Every design decision maps to a named
   software engineering principle (see the matrix above).
7. **Safe migration** — The old system keeps working. Characterization
   tests catch behavioral regressions. Both systems coexist during transition.

---

## The First 100 Lines You Write

```
1. domain/types.py       — ClaimId, AssumptionId, ..., Finding, Severity
2. domain/model.py       — Claim, Assumption, Prediction (dataclasses with set/list/dict)
3. domain/web.py          — EpistemicWeb with register_claim + invariant checks
4. tests/test_web.py      — 20 tests: register, duplicate, broken ref, cycle
5. domain/invariants.py   — validate_tier_constraints, validate_coverage
6. tests/test_invariants.py — 10 tests: tier violations, coverage gaps
```

That's Phase 1. Everything else builds on this foundation.
