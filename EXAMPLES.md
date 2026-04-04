# Epistemic Web — Worked Examples

This document shows how data is ingested into the epistemic web through the gateway. It covers everything from the gateway inward: the entity model, the web's structural enforcement, the invariant validators, and the query traversals. The interface layer (CLI commands, MCP tool names) is not the focus here — what matters is the payload structure and the sequence rules the gateway enforces.

Read this alongside ARCHITECTURE.md. The architecture document explains *what* each piece is; these examples show *how they assemble*.

---

## How to Read These Examples

Each example shows a sequence of gateway calls and annotates what the web does automatically in response.

```python
# Call format
gateway.register("claim", { ... payload ... })
# → GatewayResult(status="ok", changed=True, tx_id="abc-123")

gateway.set("parameter", "PAR-001", { ... updated fields ... })
# → GatewayResult(status="ok", changed=True, tx_id="def-456")

gateway.transition("prediction", "P-001", "CONFIRMED")
# → GatewayResult(status="ok", changed=True, tx_id="ghi-789")

gateway.query("refutation_impact", pid="P-001")
# → GatewayResult(status="ok", changed=False, data={ ... })
```

**What the gateway enforces on every mutation:**
1. The resource alias resolves to a known entity type.
2. `repo.load()` reads the current web from disk — always fresh.
3. The entity is built from the payload and the web's mutation method is called. If this raises (broken reference, cycle, duplicate), the call returns `status="error"` immediately.
4. `validator.validate(new_web)` runs all ten semantic invariant checks. Any CRITICAL finding returns `status="BLOCKED"` and the disk is not touched.
5. If `dry_run=True`, returns `status="dry_run"` with findings but no write.
6. `repo.save(new_web)` atomically replaces the JSON files on disk.
7. The transaction is appended to the log. The result is returned.

**Bidirectional links the web maintains automatically** (you set the forward link, the web maintains the reverse):

| You set this… | Web automatically maintains… |
|---|---|
| `Claim.assumptions` | `Assumption.used_in_claims` |
| `Claim.analyses` | `Analysis.claims_covered` |
| `Analysis.uses_parameters` | `Parameter.used_in_analyses` |
| `Prediction.independence_group` | `IndependenceGroup.member_predictions` |
| `Prediction.tests_assumptions` | `Assumption.tested_by` |

**Registration order rules** (you cannot reference an entity that does not yet exist):
- Register `Parameter` before the `Analysis` that uses it.
- Register `Assumption` before the `Claim` that lists it.
- Register `Claim` before the `Prediction` that names it in `claim_ids`.
- Register `IndependenceGroup` before the `Prediction` that joins it.
- Register both `IndependenceGroup`s before the `PairwiseSeparation` that connects them.
- Register `Analysis` before the `Claim` that lists it in `analyses`.

---

## Section 1: Foundational Patterns

### 1.1 — Minimal Chain: One Claim, One Prediction, One Analysis

**Scenario:** A chemist claims that catalyst X increases reaction yield above 50%. They have one empirical assumption, one parameter, one analysis, and one prediction.

**Entity graph:**
```
PAR-001 (significance threshold)
    ↓ uses_parameters
AN-001 (yield_experiment.py)
    ↑ analyses (backlink auto-maintained)
C-001 (catalyst X raises yield)  ←  A-001 (conditions were controlled)
    ↓ claim_ids
P-001 (yield > 0.50)
    ↓ independence_group
IG-001 (single experimental run)
```

**Step 1: Register the parameter.**

```python
gateway.register("parameter", {
    "id":    "PAR-001",
    "name":  "significance_threshold",
    "value": 0.05,
    "unit":  None,
    "notes": "Two-tailed t-test alpha level",
})
# → ok | PAR-001 registered
# Web state: parameters: {PAR-001: Parameter(value=0.05, used_in_analyses=set())}
# Note: used_in_analyses is empty — it will be auto-populated when AN-001 is registered.
```

**Step 2: Register the assumption.**

```python
gateway.register("assumption", {
    "id":                      "A-001",
    "statement":               "Reaction temperature, pressure, and reagent concentration "
                               "were held constant across all experimental runs.",
    "type":                    "M",                   # AssumptionType.METHODOLOGICAL
    "scope":                   "Yield experiment batch 2024-06",
    "falsifiable_consequence": None,                  # Methodological — no direct falsifier
})
# → ok | A-001 registered
# Web state: Assumption(used_in_claims=set(), tested_by=set())
# Backlinks start empty; they will be filled by the Claim and Prediction that reference this assumption.
```

**Step 3: Register the analysis.**

```python
gateway.register("analysis", {
    "id":              "AN-001",
    "path":            "analyses/yield_experiment.py",
    "command":         "python yield_experiment.py --batch 2024-06",
    "uses_parameters": ["PAR-001"],
    "notes":           "Two-tailed Welch t-test, 30 runs per condition",
})
# → ok | AN-001 registered
# Web auto-update: PAR-001.used_in_analyses now includes AN-001.
# Analysis.claims_covered starts empty — it will be auto-populated by the Claim.
```

**Step 4: Register the claim.**

```python
gateway.register("claim", {
    "id":                    "C-001",
    "statement":             "Catalyst X increases mean reaction yield above 0.50 "
                             "under standard laboratory conditions.",
    "type":                  "foundational",          # ClaimType.FOUNDATIONAL
    "scope":                 "Aqueous organic synthesis, batch process",
    "falsifiability":        "A controlled experiment showing mean yield ≤ 0.50 under "
                             "identical conditions would falsify this claim.",
    "category":              "numerical",             # ClaimCategory.NUMERICAL
    "assumptions":           ["A-001"],               # takes A-001 as given
    "analyses":              ["AN-001"],              # covered by AN-001
    "parameter_constraints": {"PAR-001": "< 0.05"},  # the t-test must be significant
})
# → ok | C-001 registered
# Web auto-updates:
#   A-001.used_in_claims now includes C-001
#   AN-001.claims_covered now includes C-001
```

**Step 5: Register the independence group.**

```python
gateway.register("independence_group", {
    "id":               "IG-001",
    "label":            "2024-06 yield experiment batch",
    "claim_lineage":    ["C-001"],
    "assumption_lineage": ["A-001"],
    "measurement_regime": "measured",
})
# → ok | IG-001 registered
# Note: only one independence group — zero pairwise separations are required.
# member_predictions starts empty; populated when P-001 is registered.
```

**Step 6: Register the prediction.**

```python
gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "Mean yield in treated group relative to untreated control",
    "tier":             "fully_specified",         # ConfidenceTier.FULLY_SPECIFIED
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",        # EvidenceKind.NOVEL_PREDICTION
    "measurement_regime": "measured",
    "predicted":        0.55,                     # specific numerical forecast
    "specification":    "mean(yield_treated) > 0.50 with p < 0.05",
    "derivation":       "C-001 directly states yield exceeds 0.50; A-001 ensures the "
                        "difference is attributable to the catalyst.",
    "claim_ids":         ["C-001"],
    "tests_assumptions": [],                       # not testing A-001 — taking it as given
    "independence_group": "IG-001",
    "free_params":       0,                        # zero free parameters — pure forecast
    "falsifier":        "Mean yield ≤ 0.50 or p ≥ 0.05 would falsify.",
    "analysis":         "AN-001",
})
# → ok | P-001 registered
# Web auto-updates:
#   IG-001.member_predictions now includes P-001
# Validator runs: no CRITICAL findings.
#   INFO: C-001 is NUMERICAL with AN-001 linked — coverage is satisfied.
```

**Step 7: Researcher runs the experiment, result is p=0.02, mean yield=0.57. Transition prediction.**

```python
# First, record the observed value by updating the prediction.
gateway.set("prediction", "P-001", {
    "id":               "P-001",
    "observable":       "Mean yield in treated group relative to untreated control",
    "tier":             "fully_specified",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        0.55,
    "observed":         0.57,                    # recorded result
    "specification":    "mean(yield_treated) > 0.50 with p < 0.05",
    "derivation":       "C-001 directly states yield exceeds 0.50; A-001 ensures the "
                        "difference is attributable to the catalyst.",
    "claim_ids":         ["C-001"],
    "tests_assumptions": [],
    "independence_group": "IG-001",
    "free_params":       0,
    "falsifier":        "Mean yield ≤ 0.50 or p ≥ 0.05 would falsify.",
    "analysis":         "AN-001",
})
# → ok | P-001 updated

# Now transition status.
gateway.transition("prediction", "P-001", "CONFIRMED")
# → ok | P-001 → CONFIRMED
```

**Final web state — what the queries now return:**

```python
gateway.query("assumption_support_status", aid="A-001")
# data = {
#   "direct_claims":          {"C-001"},
#   "dependent_predictions":  {"P-001"},   # P-001's derivation chain includes A-001
#   "tested_by":              set(),       # nobody explicitly tests A-001
# }

gateway.query("refutation_impact", pid="P-001")
# data = {
#   "claim_ids":             {"C-001"},
#   "claim_ancestors":       set(),        # C-001 is FOUNDATIONAL — no ancestors
#   "implicit_assumptions":  {"A-001"},    # the full assumption set behind C-001
# }
```

The full chain is intact: one parameter, one assumption, one analysis, one claim, one prediction — confirmed by a single independent experiment.

---

### 1.2 — Claim DAG: Derived Claims and Dependency Traversal

**Scenario:** A materials scientist has three claims. Two are foundational observations; the third is derived from both. A prediction tests the derived claim.

**Claim dependency graph:**
```
C-001 (FOUNDATIONAL): alloy composition determines grain size
C-002 (FOUNDATIONAL): grain size determines tensile strength
    ↓ depends_on
C-003 (DERIVED):      alloy composition predicts tensile strength
    ↓ depends_on C-001 AND C-002
```

```python
gateway.register("claim", {
    "id":            "C-001",
    "statement":     "The ratio of chromium to nickel in the alloy determines "
                     "the average grain size after annealing.",
    "type":          "foundational",
    "scope":         "Cr-Ni alloy series, 800°C anneal",
    "falsifiability": "Different Cr:Ni ratios producing identical grain size distributions "
                      "would falsify this.",
    "category":      "qualitative",
})
# → ok

gateway.register("claim", {
    "id":            "C-002",
    "statement":     "Smaller grain size increases tensile strength through the "
                     "Hall-Petch mechanism.",
    "type":          "foundational",
    "scope":         "Polycrystalline metals, ambient temperature",
    "falsifiability": "A metal with smaller grains showing equivalent or lower tensile "
                      "strength than a coarser-grained sample would falsify this.",
    "category":      "numerical",
})
# → ok

gateway.register("claim", {
    "id":            "C-003",
    "statement":     "Increasing the chromium fraction in Cr-Ni alloys above 18% "
                     "increases tensile strength above 650 MPa after standard annealing.",
    "type":          "derived",
    "scope":         "Cr-Ni alloys, 18–25% Cr range, 800°C anneal",
    "falsifiability": "A Cr fraction above 18% producing tensile strength ≤ 650 MPa "
                      "under identical conditions would falsify this.",
    "category":      "numerical",
    "depends_on":    ["C-001", "C-002"],    # derives from both foundational claims
})
# → ok | C-003 registered
# Web validates: DFS from C-003 checks C-001 and C-002 — no cycle.
```

**What the traversal queries return:**

```python
gateway.query("claim_lineage", cid="C-003")
# data = {"lineage": {"C-001", "C-002"}}
# "C-003 rests on C-001 and C-002. Both must hold for C-003 to be valid."

gateway.query("claims_depending_on_claim", cid="C-001")
# data = {"depending": {"C-003"}}
# "If C-001 is retracted, C-003 is immediately downstream."
```

**Cycle detection: what happens if you try to create a cycle.**

After these three claims exist, this registration is attempted:

```python
gateway.register("claim", {
    "id":         "C-004",
    "statement":  "Tensile strength feeds back into grain size during work hardening.",
    "type":       "derived",
    "scope":      "...",
    "falsifiability": "...",
    "depends_on": ["C-002", "C-003"],
})
# → ok (C-004 is not a cycle — it depends on C-002 and C-003, but nothing depends on C-004 yet)

# Now attempt a problematic update that would make C-002 depend on C-004,
# which already transitively depends on C-002:
gateway.set("claim", "C-002", {
    "id":            "C-002",
    "statement":     "Smaller grain size increases tensile strength through the Hall-Petch mechanism.",
    "type":          "foundational",
    "scope":         "Polycrystalline metals, ambient temperature",
    "falsifiability": "...",
    "category":      "numerical",
    "depends_on":    ["C-004"],   # C-004 → C-003 → C-002: this would be a cycle
})
# → error | EpistemicError: cycle detected in depends_on graph for C-002
# GatewayResult(status="error", changed=False)
# The disk is untouched. C-002 still has no depends_on.
```

---

### 1.3 — Assumption Testability: `tests_assumptions` vs `conditional_on`

**Scenario:** A physicist has an empirical assumption about detector calibration. Two predictions correctly reference it in different ways. A third prediction (incorrectly) tries to put it in both roles at once.

```python
gateway.register("assumption", {
    "id":                      "A-001",
    "statement":               "The calorimeter energy scale is calibrated to within ±2% "
                               "across the full detection range.",
    "type":                    "E",               # AssumptionType.EMPIRICAL
    "scope":                   "LHC Run 3 dataset",
    "falsifiable_consequence": "Known-mass particle resonances reconstructed with a mean "
                               "energy offset > 2% would falsify this calibration claim.",
})
# → ok | A-001 registered. tested_by is empty — no predictions yet.
```

**P-001 is explicitly designed to test whether A-001 holds** (tests_assumptions):

```python
gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "Z boson mass reconstructed from calorimeter deposits",
    "tier":             "fully_specified",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        91.188,            # known Z mass in GeV
    "specification":    "Reconstructed Z mass within ±2% of 91.188 GeV",
    "claim_ids":        [],                # tests the assumption directly, not a downstream claim
    "tests_assumptions": ["A-001"],        # THIS prediction tests the calibration
    "free_params":      0,
    "falsifier":        "Reconstructed Z mass offset > 2% of nominal would falsify A-001.",
})
# → ok | P-001 registered
# Web auto-update: A-001.tested_by now includes P-001.
```

**P-002 takes A-001 as a given (conditional_on):**

```python
gateway.register("claim", {
    "id":            "C-001",
    "statement":     "The Higgs boson couples to the Z boson with strength predicted by the SM.",
    "type":          "foundational",
    "scope":         "Standard Model predictions",
    "falsifiability": "A measured HZZ coupling deviating > 3σ from SM prediction.",
    "assumptions":   ["A-001"],            # takes calibration as given
})

gateway.register("prediction", {
    "id":               "P-002",
    "observable":       "HZZ coupling strength κ_Z",
    "tier":             "conditional",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        1.0,               # SM predicts exactly 1.0
    "specification":    "κ_Z within 1.0 ± 0.15 (current experimental precision)",
    "claim_ids":        ["C-001"],
    "conditional_on":   ["A-001"],         # prediction only valid IF calibration holds
    "tests_assumptions": [],
    "free_params":      0,
    "falsifier":        "κ_Z deviating > 3σ from 1.0.",
})
# → ok | P-002 registered
# P-002 takes A-001 as a given. If A-001 is later falsified, P-002's results are suspect.
```

**P-003 (incorrect) tries to both test and condition on A-001:**

```python
gateway.register("prediction", {
    "id":               "P-003",
    "observable":       "Some other observable",
    "tier":             "conditional",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        42.0,
    "claim_ids":        ["C-001"],
    "conditional_on":   ["A-001"],         # takes A-001 as given...
    "tests_assumptions": ["A-001"],        # ...AND tests A-001 simultaneously — contradiction
    "free_params":      0,
})
# Step 4 (web mutation): register_prediction succeeds — this is a structural operation.
# Step 5 (validation): validate_tests_conditional_overlap fires.
#   → CRITICAL: Prediction P-003 has A-001 in both tests_assumptions and conditional_on.
#     A prediction cannot simultaneously test an assumption and depend on it being true.
# → GatewayResult(status="BLOCKED", changed=False,
#                 findings=[Finding(severity=CRITICAL, source="predictions/P-003", ...)])
# The disk is untouched. P-003 does not exist in the web.
```

**What `validate_web` returns at this point (no P-003 in the web):**

```python
gateway.query("validate_web")   # equivalent to running validate_project
# findings = [
#   Finding(INFO, "assumptions/A-001",
#           "Assumption A-001 has a falsifiable_consequence and a tested_by prediction (P-001)."
#           " Coverage satisfied."),
# ]
# overall: CLEAN — no critical or warning issues.
```

---

## Section 2: Complex Patterns and Edge Cases

### 2.1 — Parameter Update Cascade

**Scenario:** A computational biologist runs a gene expression analysis using a false-discovery-rate threshold. She later changes the threshold. This does not automatically invalidate any results — it creates a staleness signal that the blast-radius query surfaces.

**Initial state after registering all entities:**

```python
gateway.register("parameter", {
    "id":    "PAR-001",
    "name":  "fdr_threshold",
    "value": 0.05,
    "unit":  None,
    "notes": "Benjamini-Hochberg FDR threshold for differential expression calls",
})
# → ok

gateway.register("analysis", {
    "id":              "AN-001",
    "path":            "analyses/rna_seq_deg.py",
    "command":         "python rna_seq_deg.py --fdr 0.05",
    "uses_parameters": ["PAR-001"],
})
# → ok | PAR-001.used_in_analyses auto-updated to {AN-001}

gateway.register("claim", {
    "id":                    "C-001",
    "statement":             "BRCA1 expression is significantly downregulated in "
                             "triple-negative breast cancer samples relative to controls.",
    "type":                  "foundational",
    "scope":                 "TCGA BRCA cohort, n=120",
    "falsifiability":        "A well-powered study finding no significant differential "
                             "expression at FDR < 0.05 would falsify this.",
    "category":              "numerical",
    "analyses":              ["AN-001"],
    "parameter_constraints": {"PAR-001": "< 0.05"},  # this claim has a threshold on PAR-001
})
# → ok | AN-001.claims_covered auto-updated to {C-001}

gateway.register("claim", {
    "id":                    "C-002",
    "statement":             "ATM expression is significantly upregulated in "
                             "triple-negative breast cancer samples relative to controls.",
    "type":                  "foundational",
    "scope":                 "TCGA BRCA cohort, n=120",
    "falsifiability":        "...",
    "category":              "numerical",
    "analyses":              ["AN-001"],
    "parameter_constraints": {"PAR-001": "< 0.05"},
})
# → ok

gateway.register("independence_group", {
    "id":    "IG-001",
    "label": "TCGA BRCA RNA-seq differential expression analysis",
    "claim_lineage":      ["C-001", "C-002"],
    "assumption_lineage": [],
    "measurement_regime": "measured",
})

gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "BRCA1 log2 fold-change between TNBC and control",
    "tier":             "fully_specified",
    "status":           "CONFIRMED",
    "evidence_kind":    "retrodiction",
    "measurement_regime": "measured",
    "predicted":        -1.5,
    "observed":          -1.7,
    "claim_ids":        ["C-001"],
    "independence_group": "IG-001",
    "analysis":         "AN-001",
    "free_params":      0,
})
# → ok

gateway.register("prediction", {
    "id":               "P-002",
    "observable":       "ATM log2 fold-change between TNBC and control",
    "tier":             "fully_specified",
    "status":           "CONFIRMED",
    "evidence_kind":    "retrodiction",
    "measurement_regime": "measured",
    "predicted":        1.2,
    "observed":          1.1,
    "claim_ids":        ["C-002"],
    "independence_group": "IG-001",
    "analysis":         "AN-001",
    "free_params":      0,
})
# → ok
```

**Regulatory guidance changes the FDR standard to 0.01.**

```python
gateway.set("parameter", "PAR-001", {
    "id":    "PAR-001",
    "name":  "fdr_threshold",
    "value": 0.01,           # changed from 0.05 → 0.01
    "unit":  None,
    "notes": "Updated to 0.01 per journal submission requirements (Nature Methods 2024)",
})
# → ok | PAR-001 updated, changed=True
# The web stores the new value. That is all.
# P-001 and P-002 remain CONFIRMED. AN-001 is unchanged.
# Nothing is automatically invalidated. The web records what IS; it does not
# make judgments about what SHOULD be done.
```

**Now query the blast radius:**

```python
gateway.query("parameter_impact", pid="PAR-001")
# data = {
#   "stale_analyses":       {"AN-001"},         # AN-001 uses PAR-001
#   "constrained_claims":   {"C-001", "C-002"}, # both have parameter_constraints on PAR-001
#   "affected_claims":      {"C-001", "C-002"}, # union of stale_analyses coverage + constrained
#   "affected_predictions": {"P-001", "P-002"}, # all predictions downstream
# }
```

**What this means:** The analysis `AN-001` was run with `--fdr 0.05`. The threshold is now 0.01. Some genes that were called significant at 0.05 may not meet 0.01. The researcher needs to:
1. Re-run `AN-001` with `--fdr 0.01`.
2. Record the new result (via `ds record` once implemented).
3. Check whether P-001 and P-002's observed values still hold under the stricter threshold.
4. If BRCA1 no longer meets FDR < 0.01, transition P-001 to `STRESSED` or `REFUTED`.
5. Update `C-001.parameter_constraints` to reflect the new threshold.

The web has not made any of these decisions. It has surfaced the complete structural consequence of the parameter change and left the scientific judgment to the researcher.

**What `check_stale` will report:**

Once `check_stale` is implemented, it will compare the SHA fingerprint of the rendered views against the current web state. Because PAR-001 has changed, the rendered "parameters" view surface is stale and will be flagged. The analysis-staleness signal (AN-001 was run under different parameters) will be reported as a finding tied to the analysis record.

---

### 2.2 — Claim Retraction and the Downstream Block

**Scenario:** Three claims in a dependency chain. A foundational claim is found to be wrong. Naively retract it — get blocked. Understand why, then do it correctly.

```python
gateway.register("claim", {
    "id":            "C-001",
    "statement":     "Aspirin irreversibly inhibits COX-1 and COX-2 enzymes.",
    "type":          "foundational",
    "scope":         "In vitro and in vivo pharmacological studies",
    "falsifiability": "Reversal of platelet aggregation inhibition after aspirin "
                      "cessation within 24 hours would falsify irreversibility.",
    "category":      "qualitative",
})

gateway.register("claim", {
    "id":            "C-002",
    "statement":     "COX inhibition by aspirin reduces thromboxane A2 synthesis.",
    "type":          "derived",
    "scope":         "Platelet function studies",
    "falsifiability": "...",
    "category":      "qualitative",
    "depends_on":    ["C-001"],
})

gateway.register("claim", {
    "id":            "C-003",
    "statement":     "Low-dose aspirin reduces secondary cardiovascular event risk "
                     "through sustained platelet inhibition.",
    "type":          "derived",
    "scope":         "Secondary prevention population, 81mg daily",
    "falsifiability": "...",
    "category":      "qualitative",
    "depends_on":    ["C-002"],
})

gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "Relative risk of MI in aspirin vs. placebo group",
    "tier":             "fully_specified",
    "status":           "CONFIRMED",
    "evidence_kind":    "retrodiction",
    "measurement_regime": "measured",
    "predicted":        0.75,
    "observed":          0.72,
    "claim_ids":        ["C-001", "C-002", "C-003"],
    "free_params":      0,
})
```

**Suppose new research suggests COX-2 inhibition is actually reversible in endothelial tissue. The researcher wants to revise C-001 to "REVISED" first, then later retract it entirely.**

```python
# Step 1: Transition to REVISED — succeeds because no validator blocks status=REVISED.
gateway.transition("claim", "C-001", "REVISED")
# → ok | C-001 → REVISED

# Step 2: Attempt full retraction.
gateway.transition("claim", "C-001", "RETRACTED")
# Step 4: web.transition_claim("C-001", RETRACTED) → new_web where C-001.status = RETRACTED
# Step 5: validator.validate(new_web)
#   → validate_retracted_claim_citations fires.
#   → P-001.claim_ids contains C-001. C-001 is now RETRACTED.
#     CRITICAL: Prediction P-001 still cites retracted claim C-001.
#   → C-002.depends_on contains C-001. C-001 is now RETRACTED.
#     CRITICAL: Claim C-002 still depends on retracted claim C-001.
# → GatewayResult(status="BLOCKED", changed=False,
#                 findings=[
#                   Finding(CRITICAL, "predictions/P-001", "cites retracted C-001"),
#                   Finding(CRITICAL, "claims/C-002",      "depends on retracted C-001"),
#                 ])
```

**The correct sequence — clear the downstream first.**

```python
# First: update P-001 to remove C-001 from its claim_ids.
# (In practice this would also require updating derivation and specification.)
gateway.set("prediction", "P-001", {
    "id":               "P-001",
    "observable":       "Relative risk of MI in aspirin vs. placebo group",
    "tier":             "fully_specified",
    "status":           "CONFIRMED",
    "evidence_kind":    "retrodiction",
    "measurement_regime": "measured",
    "predicted":        0.75,
    "observed":          0.72,
    "claim_ids":        ["C-002", "C-003"],   # C-001 removed
    "derivation":       "Revised: rests on C-002 and C-003 only. The reversibility "
                        "of COX-1 inhibition (C-001) is now under review.",
    "free_params":      0,
})
# → ok

# Second: update C-002 to remove depends_on C-001.
gateway.set("claim", "C-002", {
    "id":            "C-002",
    "statement":     "COX inhibition by aspirin reduces thromboxane A2 synthesis.",
    "type":          "foundational",          # promoted to foundational since C-001 is gone
    "scope":         "Platelet function studies",
    "falsifiability": "...",
    "category":      "qualitative",
    "depends_on":    [],                      # C-001 removed
})
# → ok

# Now the retraction succeeds.
gateway.transition("claim", "C-001", "RETRACTED")
# → ok | C-001 → RETRACTED
# Validator re-runs: no references to C-001 remain in any active prediction or claim.
```

**Lesson:** The gateway enforces epistemic hygiene aggressively. You cannot silently break the derivation chain. Every entity that cited a retracted claim must be updated first. This forces the researcher to explicitly acknowledge that downstream conclusions are now ungrounded — the cascade is made visible and unbypassable.

---

### 2.3 — Independence Group Constraint: A Design Tension

**Scenario:** A researcher wants to register two independent experimental runs as separate independence groups, then document their separation. This exposes a structural constraint in the current design.

```python
# Step 1: Register the first group — succeeds.
gateway.register("independence_group", {
    "id":    "IG-001",
    "label": "Lab A: NMR experiment",
    "claim_lineage":    ["C-001"],
    "assumption_lineage": [],
    "measurement_regime": "measured",
})
# → ok | only 1 group in web, 0 pairs, 0 separations needed. Validator is satisfied.

# Step 2: Register the second group.
gateway.register("independence_group", {
    "id":    "IG-002",
    "label": "Lab B: independent NMR replication",
    "claim_lineage":    ["C-001"],
    "assumption_lineage": [],
    "measurement_regime": "measured",
})
# Step 4: web.register_independence_group(IG-002) → new_web (structural check passes)
# Step 5: validator.validate(new_web)
#   → validate_independence_semantics: 2 groups exist, need 1 pairwise separation, found 0.
#   → CRITICAL: Missing PairwiseSeparation between IG-001 and IG-002.
# → GatewayResult(status="BLOCKED", changed=False)
```

**The deadlock:** `PS-001` cannot be registered before `IG-002` exists (referential integrity would block it). But `IG-002` cannot be registered before `PS-001` exists (the validator blocks it). The gateway currently has no atomic multi-entity operation.

**Current workaround:** Bypass the pairwise separation requirement by using a single independence group until the design gap is addressed. If you need to capture that two experiments are independent, annotate the independence group's `notes` field temporarily.

**The clean fix (not yet implemented):** The `validate_independence_semantics` validator should only require pairwise separations for groups that have at least one member prediction. An empty group is a declaration of intent, not yet an evidentiary claim — requiring a separation before any predictions exist is premature. This is a genuine design gap discovered through these examples. The validator should read:

> *For every pair of independence groups where BOTH groups have at least one member prediction, a PairwiseSeparation record must exist.*

With this change, the registration sequence becomes:
1. Register IG-001 → ok
2. Register IG-002 → ok (neither group has predictions yet)
3. Register PS-001 → ok (both groups now exist)
4. Register P-001 into IG-001 → ok
5. Register P-002 into IG-002 → validator checks: 2 groups with predictions, 1 separation exists — ok

---

## Section 3: Real-World Full Chains

### 3.1 — Eddington 1919: Confirming General Relativity

**Context:** Einstein's General Relativity (1915) predicted that light passing near a massive body would be deflected. The predicted angle — 1.75 arcseconds at the solar limb — was exactly twice the Newtonian prediction. In May 1919, Arthur Eddington led expeditions to Sobral (Brazil) to photograph stars near the solar limb during a total eclipse. The Sobral result confirmed the GR prediction.

This example shows: foundational + derived claim chain, FULLY_SPECIFIED prediction from a pure theoretical deduction, NOVEL_PREDICTION evidence kind (prediction made in 1915, measured in 1919), and a parameter carrying the numerical forecast.

**Entities registered in order:**

```python
# --- Parameters ---

gateway.register("parameter", {
    "id":     "PAR-001",
    "name":   "gr_predicted_deflection_arcsec",
    "value":  1.75,
    "unit":   "arcsec",
    "source": "Einstein 1915, Annalen der Physik",
    "notes":  "Predicted angular deflection of starlight at the solar limb under GR. "
              "Newtonian prediction is exactly half this value (0.875 arcsec).",
})
# → ok

# --- Assumptions ---

gateway.register("assumption", {
    "id":                      "A-001",
    "statement":               "Photographic plate astrometry at the Sobral site achieved "
                               "positional accuracy sufficient to distinguish 1.75 arcsec "
                               "deflection from 0.875 arcsec.",
    "type":                    "E",            # EMPIRICAL
    "scope":                   "Sobral eclipse expedition, 29 May 1919",
    "falsifiable_consequence": "If calibration stars show systematic position errors "
                               "> 0.3 arcsec, the measurement precision is insufficient "
                               "to discriminate between the GR and Newtonian predictions.",
    "source":                  "Dyson, Eddington, Davidson 1920 MNRAS",
})
# → ok

gateway.register("assumption", {
    "id":       "A-002",
    "statement": "The reference star positions measured during the eclipse are not "
                 "themselves displaced by the solar gravitational field at the plate scale.",
    "type":     "M",            # METHODOLOGICAL — systematic control
    "scope":    "Sobral eclipse expedition, 29 May 1919",
    "notes":    "Reference stars were chosen sufficiently far from the solar limb to "
                "keep their own deflection below 0.05 arcsec.",
})
# → ok

# --- Theory ---

gateway.register("theory", {
    "id":     "T-001",
    "title":  "General Relativity",
    "status": "active",
    "summary": "Einstein's theory that gravity is the curvature of spacetime produced "
               "by mass-energy. Replaces Newtonian gravity at high mass/velocity regimes.",
    "source": "Einstein 1915",
})
# → ok

# --- Claims ---

gateway.register("claim", {
    "id":            "C-001",
    "statement":     "General Relativity describes gravity as spacetime curvature "
                     "proportional to the local mass-energy density.",
    "type":          "foundational",
    "scope":         "All physical regimes where GR has been tested",
    "falsifiability": "Any observation inconsistent with the Einstein field equations "
                      "at a statistically significant level would falsify this.",
    "category":      "qualitative",
    "source":        "Einstein 1915",
})
# → ok

gateway.register("claim", {
    "id":            "C-002",
    "statement":     "Electromagnetic radiation propagates along null geodesics in "
                     "curved spacetime.",
    "type":          "foundational",
    "scope":         "All physical regimes where GR has been tested",
    "falsifiability": "Detection of photons following paths inconsistent with null "
                      "geodesic equations in a known gravitational field.",
    "category":      "qualitative",
    "source":        "Einstein 1916",
})
# → ok

gateway.register("claim", {
    "id":            "C-003",
    "statement":     "The gravitational field of the Sun causes a measurable deflection "
                     "of light rays passing near the solar limb, equal to 1.75 arcsec.",
    "type":          "derived",
    "scope":         "Solar limb, passing starlight",
    "falsifiability": "Measured deflection outside the range 1.75 ± 0.3 arcsec would "
                      "falsify this claim (within 1919 measurement precision).",
    "category":      "numerical",
    "depends_on":    ["C-001", "C-002"],
    "assumptions":   ["A-001", "A-002"],
    "parameter_constraints": {"PAR-001": "== 1.75"},
})
# → ok
# C-001.used_in_claims, C-002... wait — claims do not use other claims as assumptions.
# The depends_on is between claims.
# A-001.used_in_claims auto-updated to {C-003}
# A-002.used_in_claims auto-updated to {C-003}

# --- Analysis ---

gateway.register("analysis", {
    "id":              "AN-001",
    "path":            "analyses/eddington_sobral_1919.py",
    "command":         "python eddington_sobral_1919.py --plates astrographic --stars 7",
    "uses_parameters": ["PAR-001"],
    "notes":           "Re-reduction of Sobral astrographic plates. "
                       "7 stars measured. Mean deflection derived by least squares.",
})
# → ok | PAR-001.used_in_analyses auto-updated to {AN-001}

# Update C-003 to link to the analysis.
# (We register the analysis first, then link C-003 to it.)
gateway.set("claim", "C-003", {
    "id":            "C-003",
    "statement":     "The gravitational field of the Sun causes a measurable deflection "
                     "of light rays passing near the solar limb, equal to 1.75 arcsec.",
    "type":          "derived",
    "scope":         "Solar limb, passing starlight",
    "falsifiability": "Measured deflection outside the range 1.75 ± 0.3 arcsec would "
                      "falsify this claim.",
    "category":      "numerical",
    "depends_on":    ["C-001", "C-002"],
    "assumptions":   ["A-001", "A-002"],
    "analyses":      ["AN-001"],
    "parameter_constraints": {"PAR-001": "== 1.75"},
})
# → ok | AN-001.claims_covered auto-updated to {C-003}

# --- Independence group ---

gateway.register("independence_group", {
    "id":               "IG-001",
    "label":            "Sobral 1919 eclipse expedition — astrographic telescope",
    "claim_lineage":    ["C-001", "C-002", "C-003"],
    "assumption_lineage": ["A-001", "A-002"],
    "measurement_regime": "measured",
    "notes":            "Four-inch astrographic refractor. 7 comparison stars. "
                        "Plates re-measured in Cambridge by Crommelin and Davidson.",
})
# → ok | only 1 group — no pairwise separation required.

# --- Prediction ---

gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "Mean angular displacement of Hyades stars near solar limb "
                        "relative to comparison positions taken 6 months prior",
    "tier":             "fully_specified",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",     # predicted in 1915; measured in 1919
    "measurement_regime": "measured",
    "predicted":        1.75,
    "specification":    "Mean deflection at mean distance from solar centre corresponding "
                        "to 1.75 × (solar radius / angular separation) arcsec",
    "derivation":       "C-001 gives the curvature of spacetime near the Sun. "
                        "C-002 requires light to follow null geodesics in that curvature. "
                        "C-003 quantifies the resulting deflection at the solar limb. "
                        "Together they make a unique numerical prediction requiring no "
                        "free parameter adjustments.",
    "claim_ids":        ["C-001", "C-002", "C-003"],
    "tests_assumptions": ["A-001"],    # confirmation tests whether the plates were accurate
    "conditional_on":   ["A-002"],     # takes reference star stability as given
    "independence_group": "IG-001",
    "analysis":         "AN-001",
    "free_params":      0,
    "falsifier":        "Mean deflection < 1.0 or > 2.5 arcsec at the 95% confidence "
                        "level would falsify the GR prediction.",
    "source":           "Einstein 1916 prediction; Dyson, Eddington, Davidson 1920 result",
})
# → ok
# Web auto-updates: IG-001.member_predictions = {P-001}
#                  A-001.tested_by = {P-001}
```

**Transition to CONFIRMED after the Sobral plates are measured.**

```python
# Record observed value.
gateway.set("prediction", "P-001", {
    # ... same fields as above, plus:
    "observed":  1.98,     # Sobral astrographic result (arcsec); within the error bars of 1.75
    "status":    "PENDING",
    # ... all other fields unchanged
})
# → ok

gateway.transition("prediction", "P-001", "CONFIRMED")
# → ok | P-001 → CONFIRMED

# Link the theory to its supporting entities.
gateway.set("theory", "T-001", {
    "id":                  "T-001",
    "title":               "General Relativity",
    "status":              "active",
    "summary":             "...",
    "related_claims":      ["C-001", "C-002", "C-003"],
    "related_predictions": ["P-001"],
    "source":              "Einstein 1915",
})
# → ok

# Register the discovery.
gateway.register("discovery", {
    "id":       "D-001",
    "title":    "First experimental confirmation of GR light bending",
    "date":     "1919-11-06",       # date of Royal Society announcement
    "summary":  "Sobral eclipse expedition measured a mean stellar deflection consistent "
                "with the GR prediction of 1.75 arcsec and inconsistent with the "
                "Newtonian prediction of 0.875 arcsec.",
    "impact":   "First direct observational test of general relativity beyond the "
                "solar system; established GR as the correct theory of gravity at "
                "macroscopic scales.",
    "status":   "integrated",
    "related_claims":      ["C-001", "C-002", "C-003"],
    "related_predictions": ["P-001"],
    "source":   "Dyson, Eddington, Davidson 1920 MNRAS",
})
# → ok
```

**What the queries reveal:**

```python
gateway.query("claim_lineage", cid="C-003")
# {"lineage": {"C-001", "C-002"}}
# C-003 rests on two foundational claims — both must hold.

gateway.query("assumption_lineage", cid="C-003")
# {"lineage": {"A-001", "A-002"}}
# C-003 takes both assumptions as given.

gateway.query("prediction_implicit_assumptions", pid="P-001")
# {"implicit_assumptions": {"A-001", "A-002"}}
# P-001 explicitly lists A-001 in tests_assumptions and A-002 in conditional_on.
# Both are surfaced here as the full implicit assumption set.

gateway.query("refutation_impact", pid="P-001")
# {
#   "claim_ids":             {"C-001", "C-002", "C-003"},
#   "claim_ancestors":       {"C-001", "C-002"},    # ancestors of C-003 (C-001 and C-002 are foundational)
#   "implicit_assumptions":  {"A-001", "A-002"},
# }
# If P-001 were refuted, ALL THREE claims and BOTH assumptions would be called into question.
```

**Note on the second expedition (Principe):** Eddington's Principe expedition also measured the deflection but with lower precision. It would ideally form a second independence group `IG-002` with a `PairwiseSeparation` documenting why the two sites constitute independent evidence (different telescopes, different locations, different observers). The current independence group deadlock described in Section 2.3 prevents registering `IG-002` cleanly. Once the validator fix is applied (only require separations when both groups have member predictions), the full two-site chain can be modeled.

---

### 3.2 — Michelson-Morley 1887: A Null Result That Broke an Assumption

**Context:** In 1887, Michelson and Morley used an interferometer to test whether the luminiferous ether — the hypothetical medium through which light was thought to propagate — was detectable through Earth's orbital motion. The experiment found no fringe shift. This null result falsified the prediction that ether wind would be detectable, placed the ether assumption under severe pressure, and ultimately contributed to the development of special relativity.

This example shows: a prediction that `tests_assumptions`, a `REFUTED` transition, the full `refutation_impact` and `assumption_support_status` traversals, and a `DeadEnd` registration documenting what was abandoned.

```python
# --- Parameters ---

gateway.register("parameter", {
    "id":     "PAR-001",
    "name":   "expected_fringe_shift",
    "value":  0.4,
    "unit":   "fringes",
    "source": "Michelson 1881 theoretical calculation",
    "notes":  "Expected shift at Earth orbital velocity ~30 km/s, arm length 11m, "
              "wavelength 590nm. Full calculation: 2vL/λc² ≈ 0.4 fringes.",
})
# → ok

# --- Assumptions ---

gateway.register("assumption", {
    "id":                      "A-001",
    "statement":               "Luminiferous ether exists as an absolute rest frame "
                               "through which electromagnetic radiation propagates.",
    "type":                    "E",                  # EMPIRICAL — central hypothesis under test
    "scope":                   "Electrodynamics, 1887",
    "falsifiable_consequence": "If ether exists, Earth's orbital velocity (~30 km/s) "
                               "would produce a detectable fringe shift of approximately "
                               "0.4 fringes in an 11-metre arm interferometer.",
    "source":                  "Maxwell 1878; Michelson 1881",
})
# → ok

gateway.register("assumption", {
    "id":       "A-002",
    "statement": "The interferometer apparatus does not drag ether locally (no ether drag).",
    "type":     "E",
    "scope":    "Michelson-Morley apparatus, 1887",
    "falsifiable_consequence": "Fresnel drag coefficient measurements with moving media "
                               "would reveal partial ether drag if present.",
    "source":   "Stokes 1845 ether drag theory (no drag variant)",
})
# → ok

# --- Claims ---

gateway.register("claim", {
    "id":            "C-001",
    "statement":     "Light requires a medium (ether) to propagate, and its speed is "
                     "measured relative to that medium.",
    "type":          "foundational",
    "scope":         "Classical wave mechanics of light",
    "falsifiability": "Detection of a constant speed of light in all inertial frames "
                      "would falsify the ether medium requirement.",
    "category":      "qualitative",
    "assumptions":   ["A-001"],
})
# → ok | A-001.used_in_claims → {C-001}

gateway.register("claim", {
    "id":            "C-002",
    "statement":     "Earth's orbital motion at ~30 km/s relative to the ether "
                     "produces a measurable ether wind detectable by interferometry.",
    "type":          "derived",
    "scope":         "Earth-based interferometry, 1887",
    "falsifiability": "An interferometer with sufficient sensitivity showing no fringe "
                      "shift through a full rotation would falsify ether wind detectability.",
    "category":      "numerical",
    "depends_on":    ["C-001"],
    "assumptions":   ["A-001", "A-002"],
    "parameter_constraints": {"PAR-001": "~= 0.4"},
})
# → ok | A-001.used_in_claims → {C-001, C-002}, A-002.used_in_claims → {C-002}

# --- Analysis ---

gateway.register("parameter", {
    "id":     "PAR-002",
    "name":   "interferometer_sensitivity",
    "value":  0.01,
    "unit":   "fringes",
    "notes":  "Minimum detectable fringe shift. Expected signal (0.4) is 40× the "
              "noise floor — sensitivity is not the limiting factor.",
})
# → ok

gateway.register("analysis", {
    "id":              "AN-001",
    "path":            "analyses/mm_interferometer_1887.py",
    "command":         "python mm_interferometer_1887.py --observations 36 --rotations full",
    "uses_parameters": ["PAR-001", "PAR-002"],
    "notes":           "36 observations over July 8-12 1887. "
                       "Interferometer on stone slab floating in mercury to allow full rotation. "
                       "Mean fringe shift measured: 0.01 fringes.",
})
# → ok

gateway.set("claim", "C-002", {
    # ... same as above with:
    "analyses": ["AN-001"],
})
# → ok | AN-001.claims_covered → {C-002}

# --- Independence group and prediction ---

gateway.register("independence_group", {
    "id":               "IG-001",
    "label":            "Michelson-Morley interferometer, Case Western Reserve, July 1887",
    "claim_lineage":    ["C-001", "C-002"],
    "assumption_lineage": ["A-001", "A-002"],
    "measurement_regime": "measured",
})
# → ok

gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "Fringe shift in Michelson interferometer during full rotation "
                        "of the apparatus",
    "tier":             "fully_specified",
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        0.4,
    "specification":    "Fringe shift amplitude ≈ 0.4 fringes across a full rotation, "
                        "peaking when one arm is aligned with Earth's orbital velocity vector",
    "derivation":       "C-001 requires light speed to depend on ether frame velocity. "
                        "C-002 quantifies the ether wind at Earth's orbital velocity. "
                        "Together they predict a specific and measurable fringe pattern.",
    "claim_ids":        ["C-001", "C-002"],
    "tests_assumptions": ["A-001", "A-002"],   # this prediction directly tests both
    "independence_group": "IG-001",
    "analysis":         "AN-001",
    "free_params":      0,
    "falsifier":        "Fringe shift < 0.02 fringes through a full rotation would be "
                        "inconsistent with ether wind at any Earth orbital phase.",
    "source":           "Michelson and Morley 1887 Am. J. Sci.",
})
# → ok
# A-001.tested_by → {P-001}, A-002.tested_by → {P-001}
```

**The measurement returns 0.01 fringes. The prediction is refuted.**

```python
# Record the observed value.
gateway.set("prediction", "P-001", {
    # ... same as above with:
    "observed": 0.01,    # measured; expected 0.4
    "status":   "PENDING",
})
# → ok

# Transition to STRESSED first — the result is anomalous but perhaps not conclusive alone.
gateway.transition("prediction", "P-001", "STRESSED")
# → ok | P-001 → STRESSED

# After replication and analysis, transition to REFUTED.
gateway.transition("prediction", "P-001", "REFUTED")
# → ok | P-001 → REFUTED
# Validator: validate_evidence_consistency checks that REFUTED predictions have an analysis.
# P-001.analysis = "AN-001" — satisfied.
```

**Query the consequences.**

```python
gateway.query("refutation_impact", pid="P-001")
# {
#   "claim_ids":            {"C-001", "C-002"},
#   "claim_ancestors":      {"C-001"},              # C-002 depends_on C-001
#   "implicit_assumptions": {"A-001", "A-002"},     # both assumptions are in the chain
# }
# The refutation of P-001 calls into question both claims and both assumptions.

gateway.query("assumption_support_status", aid="A-001")
# {
#   "direct_claims":         {"C-001", "C-002"},    # both claims reference A-001
#   "dependent_predictions": {"P-001"},             # P-001's chain includes A-001
#   "tested_by":             {"P-001"},             # P-001 was explicitly testing A-001
# }
# A-001 is now under direct pressure: the prediction that was testing it has been refuted.

gateway.query("assumption_support_status", aid="A-002")
# {
#   "direct_claims":         {"C-002"},
#   "dependent_predictions": {"P-001"},
#   "tested_by":             {"P-001"},
# }
```

**The researcher records the ether hypothesis as a dead end.**

```python
gateway.register("dead_end", {
    "id":          "DE-001",
    "title":       "Luminiferous ether as absolute rest frame",
    "description": "The Michelson-Morley experiment showed no detectable fringe shift "
                   "at 40× the apparatus sensitivity floor. Subsequent repetitions "
                   "(Morley and Miller 1902-1905, Miller 1925) produced similarly null "
                   "results. Attempts to salvage the ether via partial drag (Stokes) or "
                   "Lorentz contraction could not reconcile the full set of observations. "
                   "The concept was abandoned following Einstein's 1905 special relativity "
                   "paper, which explained all results without requiring an ether.",
    "status":      "resolved",
    "related_predictions": ["P-001"],
    "related_claims":      ["C-001", "C-002"],
    "references":  [
        "Michelson and Morley 1887 Am. J. Sci. 34:333",
        "Einstein 1905 Ann. Phys. 17:891",
    ],
})
# → ok
```

**What the web now shows — a complete epistemic record:**

The web records that:
- P-001 is REFUTED and was testing A-001 and A-002.
- A-001 is an empirical assumption with a known falsifiable consequence and has been tested — adversely.
- C-001 and C-002 have a refuted prediction in their derivation chain.
- DE-001 documents what was tried and why it was abandoned.

No inference has been drawn automatically. The web does not mark A-001 as "false" or C-001 as "retracted." That judgment belongs to the researcher. The web surfaces the structural consequences and waits.

---

### 3.3 — Fraud Detection Model: Parameter Drift and Compound Assumptions

**Context:** A machine learning team builds a fraud detection classifier. Two months after deployment, the data science team changes two parameters: a precision threshold (for business reporting) and the train-test split ratio (for model governance). One change is benign; the other makes an already-confirmed prediction suspect.

This example shows: a CONDITIONAL prediction (depends on distributional assumptions), a parameter update that stales an analysis, and the distinction between a prediction that is still structurally "CONFIRMED" but whose analytical basis is now stale.

```python
# --- Parameters ---

gateway.register("parameter", {
    "id":    "PAR-001",
    "name":  "test_split_ratio",
    "value": 0.20,
    "unit":  None,
    "notes": "Fraction of historical data held out as test set. Temporal split: "
             "most recent 20% of transactions.",
})
# → ok

gateway.register("parameter", {
    "id":    "PAR-002",
    "name":  "minimum_precision_threshold",
    "value": 0.85,
    "unit":  None,
    "notes": "Minimum acceptable precision for fraud alerts. Business requirement: "
             "false positive rate must stay below 15% of all alerts.",
})
# → ok

# --- Assumptions ---

gateway.register("assumption", {
    "id":                      "A-001",
    "statement":               "The statistical distribution of fraudulent transaction "
                               "patterns in the training period is representative of "
                               "the distribution during deployment.",
    "type":                    "E",               # EMPIRICAL
    "scope":                   "FraudNet v1.0, training window Jan–Dec 2023",
    "falsifiable_consequence": "A significant drop in model precision or recall on "
                               "fresh deployment data — not explained by volume changes "
                               "— would indicate distributional shift.",
})
# → ok

gateway.register("assumption", {
    "id":       "A-002",
    "statement": "The temporal 80/20 train-test split provides a stable and unbiased "
                 "estimate of out-of-sample performance.",
    "type":     "M",                # METHODOLOGICAL
    "scope":    "FraudNet v1.0 evaluation",
    "notes":    "Temporal split was chosen over random split to respect the sequential "
                "nature of fraud patterns.",
})
# → ok

# --- Claims ---

gateway.register("claim", {
    "id":            "C-001",
    "statement":     "FraudNet v1.0 has learned genuine fraud-indicative patterns "
                     "from the labeled training data.",
    "type":          "foundational",
    "scope":         "FraudNet v1.0, training window Jan–Dec 2023",
    "falsifiability": "Precision and recall significantly above a random baseline on "
                      "the held-out test set would confirm learning; at or below baseline "
                      "would falsify.",
    "category":      "qualitative",
    "assumptions":   ["A-001"],
})
# → ok

gateway.register("claim", {
    "id":            "C-002",
    "statement":     "The patterns learned by FraudNet v1.0 generalise to unseen "
                     "transactions at precision ≥ 0.85.",
    "type":          "derived",
    "scope":         "FraudNet v1.0, temporal test set from deployment window",
    "falsifiability": "Observed precision < 0.85 on the held-out test set would falsify.",
    "category":      "numerical",
    "depends_on":    ["C-001"],
    "assumptions":   ["A-001", "A-002"],
    "parameter_constraints": {"PAR-002": ">= 0.85"},   # claim threshold references PAR-002
})
# → ok

# --- Analysis ---

gateway.register("analysis", {
    "id":              "AN-001",
    "path":            "analyses/model_evaluation.py",
    "command":         "python model_evaluation.py --split 0.20 --threshold 0.85",
    "uses_parameters": ["PAR-001", "PAR-002"],
    "notes":           "Sklearn classification_report on temporal test split. "
                       "Result: precision=0.91, recall=0.78, f1=0.84.",
})
# → ok | PAR-001.used_in_analyses → {AN-001}, PAR-002.used_in_analyses → {AN-001}

gateway.set("claim", "C-002", {
    # ... same as above with:
    "analyses": ["AN-001"],
})
# → ok | AN-001.claims_covered → {C-002}

# --- Independence group and prediction ---

gateway.register("independence_group", {
    "id":    "IG-001",
    "label": "FraudNet v1.0 temporal test split evaluation",
    "claim_lineage":    ["C-001", "C-002"],
    "assumption_lineage": ["A-001", "A-002"],
    "measurement_regime": "measured",
})
# → ok

gateway.register("prediction", {
    "id":               "P-001",
    "observable":       "FraudNet v1.0 precision on temporal hold-out test set",
    "tier":             "conditional",          # CONDITIONAL — depends on distributional assumption
    "status":           "PENDING",
    "evidence_kind":    "novel_prediction",
    "measurement_regime": "measured",
    "predicted":        0.88,
    "specification":    "Precision ≥ 0.85 on the temporal test split (most recent 20% of data)",
    "derivation":       "C-001 asserts that genuine patterns were learned. C-002 asserts "
                        "those patterns generalise at ≥ 0.85 precision. Both require A-001 "
                        "to hold — if distribution has shifted, generalization may not hold.",
    "claim_ids":        ["C-001", "C-002"],
    "conditional_on":   ["A-001", "A-002"],     # prediction only valid if distribution is stable
    "tests_assumptions": [],                    # not explicitly designed to test distribution
    "independence_group": "IG-001",
    "analysis":         "AN-001",
    "free_params":      0,
    "falsifier":        "Precision < 0.85 on the test set.",
})
# → ok
# Validator: CONDITIONAL prediction must have conditional_on — it does. ok.
```

**Evaluation runs. Precision = 0.91. Prediction confirmed.**

```python
gateway.set("prediction", "P-001", {
    # ... same as above with:
    "observed": 0.91,
    "status":   "PENDING",
})
# → ok

gateway.transition("prediction", "P-001", "CONFIRMED")
# → ok | P-001 → CONFIRMED
```

**Two months later — regulatory governance change 1: precision threshold raised to 0.90.**

```python
gateway.set("parameter", "PAR-002", {
    "id":    "PAR-002",
    "name":  "minimum_precision_threshold",
    "value": 0.90,
    "unit":  None,
    "notes": "Raised from 0.85 to 0.90 per Q4 governance review. "
             "Regulatory guidance requires false positive rate below 10%.",
})
# → ok | PAR-002 updated

gateway.query("parameter_impact", pid="PAR-002")
# {
#   "stale_analyses":       {"AN-001"},
#   "constrained_claims":   {"C-002"},       # C-002 has parameter_constraints on PAR-002
#   "affected_claims":      {"C-002"},
#   "affected_predictions": {"P-001"},
# }
```

**This change is benign for the current result.** P-001.observed = 0.91 > 0.90, so the prediction still passes the new threshold. But C-002's `parameter_constraints` entry says `{"PAR-002": ">= 0.85"}` — this annotation is now stale. The researcher updates C-002's constraint to reflect the new threshold:

```python
gateway.set("claim", "C-002", {
    # ... same as above with:
    "parameter_constraints": {"PAR-002": ">= 0.90"},   # updated
})
# → ok
```

**Regulatory governance change 2: test split ratio changed from 0.20 to 0.30.**

```python
gateway.set("parameter", "PAR-001", {
    "id":    "PAR-001",
    "name":  "test_split_ratio",
    "value": 0.30,
    "unit":  None,
    "notes": "Increased from 0.20 to 0.30. Larger test window provides more stable "
             "precision estimates and includes Q3 seasonality in evaluation.",
})
# → ok

gateway.query("parameter_impact", pid="PAR-001")
# {
#   "stale_analyses":       {"AN-001"},       # AN-001 was run with --split 0.20
#   "constrained_claims":   set(),            # no claims annotate PAR-001 constraints
#   "affected_claims":      {"C-002"},        # C-002 is covered by the now-stale AN-001
#   "affected_predictions": {"P-001"},        # P-001 depends on C-002
# }
```

**This change is NOT benign.** `AN-001` was run with `--split 0.20`. The split is now 0.30. The test set has changed. The observed precision of 0.91 was measured on the 20% holdout, not the 30% holdout. P-001 is CONFIRMED based on a result produced under different parameters.

**The web does not automatically change P-001.status.** The CONFIRMED status remains. But the staleness signal is visible to anyone querying `parameter_impact`. The researcher must:

```python
# 1. Re-run AN-001 with the new split.
#    (ds record, once implemented, would capture the new result here.)

# 2. Suppose the new result returns precision = 0.87 (Q3 has seasonal fraud patterns
#    that weren't in the training window — A-001 is showing signs of strain).

# 3. Update the observed value.
gateway.set("prediction", "P-001", {
    # ... same fields as above with:
    "observed": 0.87,    # new result under 0.30 split
    "status":   "CONFIRMED",
})
# → ok

# 4. 0.87 > 0.90? No. Precision has dropped below the new threshold.
#    Transition to STRESSED — the evidence is under tension but not decisively refuted.
gateway.transition("prediction", "P-001", "STRESSED")
# → ok | P-001 → STRESSED
# Validator: validate_coverage will surface STRESSED predictions in its findings.
# This is a WARNING, not a CRITICAL — it calls for review, not a block.
```

**What the health check now shows:**

```python
gateway.query("health_check")
# findings = [
#   Finding(WARNING, "predictions/P-001",
#           "Prediction P-001 is STRESSED: observed precision 0.87 is below the "
#           "current threshold of 0.90. Review A-001 (distributional stability) "
#           "and consider whether a model retrain is warranted."),
#   Finding(INFO, "analyses/AN-001",
#           "AN-001 uses parameters PAR-001 (now 0.30) and PAR-002 (now 0.90). "
#           "Last recorded result was obtained under different parameter values."),
# ]

gateway.query("assumption_support_status", aid="A-001")
# {
#   "direct_claims":         {"C-001", "C-002"},
#   "dependent_predictions": {"P-001"},
#   "tested_by":             set(),     # nobody explicitly tests distribution stability
# }
# Note: A-001 (distributional stability) is an empirical assumption with a falsifiable
# consequence but NO prediction in tested_by. This means the team has identified the
# risk but has not set up a formal test for it.
# Validator: validate_assumption_testability will flag A-001 as WARNING.
```

**The web has revealed two structural gaps that pre-existed the parameter changes:**
1. A-001 has a `falsifiable_consequence` but no prediction in `tested_by`. The team never formally instrumented the distribution monitoring.
2. P-001 is CONDITIONAL on A-001 but A-001 is not being actively tested. The conditional dependency is a known risk that was never formally tracked.

These are not bugs introduced by the examples. They are real design gaps that the epistemic web makes visible.

---

## Summary: What These Examples Reveal

### Rules the gateway enforces that you cannot work around

| Situation | What happens |
|---|---|
| Register entity with reference to non-existent ID | `status="error"` immediately (web raises `BrokenReferenceError`) |
| Register claim with `depends_on` that creates a cycle | `status="error"` immediately |
| Register duplicate ID | `status="error"` immediately |
| Transition claim to RETRACTED while predictions still cite it | `status="BLOCKED"` (CRITICAL finding) |
| Prediction has same assumption in both `tests_assumptions` and `conditional_on` | `status="BLOCKED"` (CRITICAL finding) |
| `FULLY_SPECIFIED` prediction with `free_params != 0` | `status="BLOCKED"` (CRITICAL finding) |
| Register second independence group without a pairwise separation | `status="BLOCKED"` (CRITICAL finding) — see design gap below |

### Things the gateway does NOT do automatically

| Situation | What you must do manually |
|---|---|
| Parameter value changes | Query `parameter_impact`, re-run affected analyses, record results, decide whether to transition prediction status |
| Prediction refuted | Query `refutation_impact` to see blast radius; decide whether to retract upstream claims |
| Assumption under pressure from a refuted prediction | Explicitly review the assumption; the web flags it, it does not change the assumption's status |
| Analysis re-run with new parameters | Record the new result; transition the prediction status if warranted |

### Design gaps discovered

1. **Independence group registration deadlock.** The current `validate_independence_semantics` validator blocks the registration of a second independence group if no pairwise separation exists, but a pairwise separation cannot be registered before both groups exist. The fix: only require pairwise separations between groups that have at least one member prediction. Until this is resolved, use a single independence group for multi-site or multi-experiment evidence.

2. **No `record_result` operation yet.** The `Analysis` entity has `path` and `command` for provenance, but there is no implemented mechanism to record the result of running the analysis (including git SHA capture). `check_stale` and staleness-based findings depend on this. The `ds record` CLI command and `record_result` MCP tool are specified but not yet implemented.

3. **`conditional_on` predictions do not automatically surface as suspect when their condition assumption is under pressure.** If A-001 is tested by P-001 and P-001 is REFUTED, P-002 (which is `conditional_on` A-001) does not automatically become STRESSED. The researcher must query `assumption_support_status` to find P-002 and decide whether to transition it. A future health-check rule could surface all CONDITIONAL predictions whose `conditional_on` assumptions have active REFUTED predictions as tests as automatic WARNING findings.
