# Operation Sugar Roadmap

Updated: October 9, 2026

Operation Sugar develops transparent, reproducible commodity-research and forecast benchmarks, beginning with Brazilian sugarcane and sugar.

The current Layer-1 target is **annual agricultural sugarcane yield (t/ha) in São Paulo**.

The immediate objective is not to maximize model complexity. It is to identify which weather relationships remain distinct, robust, interpretable, and eventually useful out of sample.

## Current Status

| Status | Scope |
|---|---|
| **Completed** | EXP-01 — weather feature structure |
| **Completed** | EXP-02 — yield detrending and spatial composition |
| **Completed** | EXP-03 — weather–yield discovery, robustness, spatial heterogeneity, and redundancy synthesis |
| **Next** | **EXP-05 — conditional temperature–VPD yield response** |
| **After EXP-05** | EXP-04 — focused continuous adjusted-yield characterization |
| **Later / separately approved** | Hydrological conditional-information follow-up |
| **Later Layer 1** | EXP-06, EXP-07, EXP-08 |
| **Deferred** | Dynamic Bayesian weather updating → Weather 2.0 |

Experiment numbers are historical identifiers. Execution order is intentionally **EXP-05 before EXP-04** because EXP-05 resolves the largest remaining atmospheric-demand redundancy question before the broader continuous-characterization stage.

---

## Four-Layer Research Architecture

| Layer | Research focus | Main question | Status |
|---|---|---|---|
| **1. Agricultural supply** | Weather → cane yield → cane production | Which weather information is robust and predictively useful for annual TCH? | Active |
| **2. Sugar production and energy** | Cane → sugar / ethanol | How does available cane translate into sugar output? | Planned |
| **3. Currency** | BRL/USD and sugar | Does currency add information beyond supply and energy? | Planned |
| **4. Supply chains** | Ports / exports / inventories | Do physical-flow indicators add information beyond upstream layers? | Planned |

Cane yield, cane production, recoverable sugar, sugar output, exports, and futures prices are distinct targets.

---

## Layer 1 — Experiment Sequence

### EXP-01 — Weather Feature Structure

**Status: COMPLETED**

Question:

> How much information overlap exists among weather variables, how does that overlap vary by month, and how does production-footprint weighting affect the estimated structure?

Established:

- strong calendar-month dependence;
- pooled-correlation failure modes;
- high soil-moisture persistence;
- transient rainfall behavior;
- substantial but incomplete temperature–VPD overlap;
- meaningful harvested-area weighting effects.

EXP-01 does not select final yield-model features.

---

### EXP-02 — Yield Detrending and Spatial Composition

**Status: COMPLETED**

Question:

> How should long-run productivity growth and changing production geography be separated from short-run annual yield variation before weather relationships are interpreted?

Approved historical representation:

§§§text
municipality annual yield
→ municipality-specific P50=10 detrending
→ municipality residual
→ annual ERA5-grid aggregation with observed harvested-area weights
§§§

Robustness:

- P50=12;
- common-support fixed composition;
- endpoint sensitivity;
- internal-gap proximity.

Any future forecasting system must reconstruct estimated transformations using training-period information only.

---

### EXP-03 — Yield-Stratified Weather Analysis

**Status: COMPLETED**

Question:

> Which monthly weather conditions differ across historically high-, middle-, and low-adjusted-yield outcomes, and how spatially stable are those relationships?

Main conclusions:

- primary late-weather structure: **Dec_(t-1) → Apr_t**;
- Dec–Jan: strongest and most spatially broad;
- Feb–Mar: materially more heterogeneous;
- Apr: partial spatial reconvergence;
- humidity and deeper soil moisture are among the most spatially stable late-window signals;
- March soil-moisture response varies with depth;
- static SoilGrids differences are suggestive but geography-confounded and remain explanatory-only.

Step-5 redundancy closure:

- mean-daily solar retained over monthly total solar;
- mean VPD retained over daily-max VPD;
- 0–7 cm retained as canonical upper-soil moisture;
- only Dec–Jan RH and Dec–Jan 28–100 cm soil moisture are promoted as temporal aggregation candidates;
- downstream universe: **38 candidate representations**.

Protected conditional questions:

- temperature ↔ VPD;
- rainfall ↔ upper moisture;
- rainfall/history ↔ deep moisture;
- upper ↔ deep moisture.

---

### EXP-05 — Conditional Temperature–VPD Yield Response

**Status: NEXT**

Question:

> Does VPD contain additional yield information after temperature is known, and does temperature contain additional information after VPD is known?

Primary empirical focus:

- February_t, where EXP-03 found relatively strong categorical atmospheric-demand contrasts but weaker pooled monotonic association and more spatial heterogeneity.

Initial design should remain transparent:

- inspect temperature–VPD overlap on matched support;
- evaluate yield–VPD relationships conditional on temperature;
- evaluate yield–temperature relationships conditional on VPD;
- assess whether conditioning improves spatial consistency.

Only if the simple conditional analysis supports it should parsimonious nonlinear or interaction terms be considered.

EXP-05 is a conditional-information experiment, not final feature selection.

---

### EXP-04 — Continuous Adjusted-Yield Characterization

**Status: PROPOSED — AFTER EXP-05**

Question:

> What are the magnitude and shape of the retained continuous weather–yield relationships, and which findings survive the approved target robustness specifications?

EXP-04 must not simply rerun the pooled-rank and grid-Spearman screen already completed in EXP-03.

It should focus on:

- relationship shape;
- effect magnitude;
- uncertainty;
- statewide-common versus heterogeneous structure;
- P50=12 robustness;
- fixed-composition robustness;
- fair comparison of the two approved Dec–Jan summaries against their constituent months.

The 38 Step-5 representations are a candidate universe, not a 38-variable regression.

EXP-05 may alter only the temperature/VPD portion before EXP-04.

---

### Hydrological Conditional-Information Follow-up

**Status: JUSTIFIED IN PRINCIPLE / UNNUMBERED**

Potential questions:

- does upper-soil moisture retain information after rainfall is known?
- what rainfall-history summary is appropriate for deep moisture?
- does deep moisture retain information after upper moisture is known?
- should the two deep layers remain separate?

This should be one coherent hydrological conditional design rather than several disconnected pairwise experiments.

It is not automatically next after EXP-05.

---

### EXP-06 — Growth-Stage Weather Aggregation

**Status: PROPOSED**

Compare:

- month-level features;
- biologically meaningful stage aggregates;
- hybrid representations.

Stage definitions must be supported by sugarcane agronomy and the empirical monthly evidence. They must not be outcome-optimized on the full historical sample.

---

### EXP-07 — Incremental Predictive Value

**Status: PROPOSED**

Question:

> Do retained advanced weather variables improve annual yield prediction beyond simpler weather benchmarks?

Use transparent model ladders first and chronological evaluation.

Feature selection, tuning, scaling, detrending, and other estimated transformations must be reconstructed inside training folds.

Candidate metrics include:

- RMSE;
- MAE;
- out-of-sample R²;
- held-out-season errors;
- stability across validation years.

---

### EXP-08 — Spatial Weather-Response Heterogeneity

**Status: LATER / CONDITIONAL**

EXP-03 already established real spatial heterogeneity.

Any future EXP-08 should build on that result rather than restart the question from scratch.

Possible extensions:

- long-run climate regimes;
- parsimonious response modifiers;
- regional interactions.

Correlated regional attributes must not be presented as causal without an identification design.

---

## Layer-1 Completion Criteria

Layer 1 requires:

- a reproducible adjusted-yield target;
- explicit spatial weighting;
- documented temporal alignment;
- robust weather–yield relationships;
- transparent feature-reduction logic;
- time-respecting predictive validation;
- uncertainty and limitation reporting;
- preserved negative results and specification sensitivity.

A null predictive result is acceptable.

---

## Deferred to Weather 2.0

Dynamic or sequential Bayesian yield updating is **not** part of the current v1.x experiment sequence.

It will be reconsidered only after the current weather-information problem is materially better resolved.

---

## Longer-Term Layers

### Layer 2 — Cane-to-Sugar Conversion and Energy

Questions include:

- recoverable sugar / ATR;
- processing recovery;
- sugar versus ethanol allocation;
- energy-market interactions.

### Layer 3 — BRL/USD

Any currency study must define quote convention, horizon, lag structure, and matched information sets.

### Layer 4 — Supply Chains

Candidate evidence includes ports, vessel lineups, exports, freight, congestion, storage, and inventories.

Distinguish sugar produced, available for export, loaded, shipped, and delivered.

---

## Cross-Layer Principles

- Standardize targets, issue dates, horizons, and information sets.
- Preserve forecast revisions and historical vintages where possible.
- Use matched evaluation samples.
- Keep training-fold preprocessing inside training folds.
- Prefer chronological expanding / rolling evaluation for historical forecast claims.
- Separate association, predictive information, and causal interpretation.
- Preserve failed specifications and negative results.
- Better supply forecasts do not by themselves establish profitable trading strategies.
