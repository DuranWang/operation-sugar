# Operation Sugar Roadmap

Updated: October 14, 2026

Operation Sugar develops transparent, reproducible commodity-research and forecast benchmarks, beginning with Brazilian sugarcane and sugar.

The current Layer-1 target is **annual agricultural sugarcane yield (t/ha) in São Paulo**.

The immediate objective is not to maximize model complexity. It is to identify which weather relationships remain distinct, robust, interpretable, and eventually useful out of sample.

## Current Status

| Status | Scope |
|---|---|
| **Completed** | EXP-01 — weather feature structure |
| **Completed** | EXP-02 — yield detrending and spatial composition |
| **Completed** | EXP-03 — weather–yield discovery, robustness, spatial heterogeneity, and redundancy synthesis |
| **Completed** | EXP-05 — temperature–VPD conditional information |
| **Completed** | EXP-05B — antecedent moisture and rainfall conditional-response analysis |
| **Completed as reported; results reviewed** | EXP-04 — continuous weather–yield characterization |
| **Next — design** | EXP-06 — time/stage representations and descriptive joint-weather specification |
| **Later / separately approved** | Hydrological conditional-information follow-up |
| **Later Layer 1** | EXP-07, EXP-08 |
| **Deferred** | Dynamic Bayesian weather updating → Weather 2.0 |

Experiment numbers are historical identifiers. The completed research sequence placed **EXP-05 and EXP-05B before EXP-04** to characterize atmospheric conditional information; neither experiment made final predictive feature keep/drop decisions.

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

**Status: COMPLETED**

Question:

> Does VPD contain additional yield information after temperature is known, and does temperature contain additional information after VPD is known?

EXP-05 tested 16 separate monthly exploratory slots, preserving May_(t-1)–Apr_t as the 12-month primary historical window and Jan_(t-1)–Apr_t as extended robustness.

- Aug–Nov_(t-1) median within-grid `r(Y,VPD|T)` was approximately −0.104, −0.099, −0.081, and −0.105.
- Directional patterns are modest and spatially heterogeneous; February_t was not a uniformly robust VPD signal.
- Conditioning does not establish independent causality or prospective predictive value.
- **Decision:** retain both temperature and mean VPD as exploratory candidates. No approved evidence supports deleting either one.

Outputs: `outputs/research/exp_05/`.

---

### EXP-05B — Moisture-Conditioned Temperature–VPD Yield Response

**Status: COMPLETED**

Question:

> Do the temperature/VPD–yield conditional slopes differ systematically between relatively dry and wet antecedent soil-moisture conditions?

- Primary modifier: mean antecedent 28–100 cm soil moisture over months m−3 to m−1. Comparators: month m−1 moisture, nominal 100–255 cm deeper moisture, and three-month rainfall total.
- The primary Aug–Nov VPD dry-minus-wet slope contrasts were +0.348, −0.300, +0.321, +0.113 t/ha per within-grid VPD SD. The prespecified 3-/5-year synchronized-block intervals all crossed zero.
- Adding moisture as an additive covariate did not eliminate the earlier modest negative VPD partial-correlation pattern.
- Results were mixed across months, grids, and modifiers; there is **no clear interval-supported moisture modification**, not proof of no effect.
- Fixed-grid bootstrap retained 76 eligible grids. Do not use the mixed interaction results to justify causal claims, practical equivalence, or feature deletion.
- The physical depth/source mapping of the nominal Open-Meteo 100–255 cm field versus ERA5 layer 4 (100–289 cm) requires clear provenance when interpreting the deep-layer comparator.

Outputs: `outputs/research/exp_05b/`.

---

### EXP-04 — Continuous Weather–Yield Response Characterization

**Completed as reported; supplied result tables reviewed on 2026-10-14.** The frozen 38 candidates were fit separately against the primary actual-composition P50=10 grid residual. There are 2,888 linear fits (76 grids per candidate) and 2,736 restricted quadratic fits (72 grids per candidate), with candidate-specific paired years rather than a complete-window exclusion.

Rainfall and soil moisture generally have positive slope point estimates; temperature and VPD generally have negative ones. Many individual-grid block intervals cross zero. February rainfall is the only pooled PQ candidate whose curvature intervals exclude zero under both block schemes; this is exploratory evidence within a prespecified quadratic family, not an independently validated discovery. Target sensitivities retain most slope signs. Linear LOYO was not present in the supplied review files.

These marginal models do not quantify joint seasonal explanatory power or forecast gains. No feature is added or removed on a significance rule. See the [reviewed results](outputs/research/exp_04/EXP_04_reviewed_results.md) for tables, sample rules, uncertainty, and the outstanding implementation/full-output synchronization gap.

---

### Hydrological Conditional-Information Follow-up

**Status: JUSTIFIED IN PRINCIPLE / UNNUMBERED**

Potential questions:

- does upper-soil moisture retain information after rainfall is known?
- what rainfall-history summary is appropriate for deep moisture?
- does deep moisture retain information after upper moisture is known?
- should the two deep layers remain separate?

This should be one coherent hydrological conditional design rather than several disconnected pairwise experiments.

It is not automatically next after EXP-05B or EXP-04; it requires separate approval.

---

### EXP-06 — Growth-Stage Weather Aggregation

**Status: NEXT — DESIGN**

Consider limited time/stage representations and a separately agreed descriptive joint-weather specification. Single-month marginal R² from EXP-04 is not a test of seasonal joint explanatory power. No new joint model is frozen here; predictive value remains EXP-07.

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
