# Research Decisions

This document records the major analytical and statistical decisions that define the current Operation Sugar research architecture.

It answers:

> **What did the project choose, and why?**

Detailed experiment methods and findings are documented in [`statistical_experiments.md`](statistical_experiments.md).

---

## Decision Principles

Operation Sugar follows a research-first workflow:

> research question → statistical design → engineering implementation

Major choices should remain traceable to source data, experiment outputs, literature, or explicit statistical reasoning.

---

# Target, Source, and Historical Outcome

## Decision 01 — Annual Agricultural Yield Is the Primary Layer-1 Target

Use annual sugarcane yield in tonnes per hectare as the primary agricultural target.

Harvest progress and crushing volumes mix agricultural and operational variation. Annual agricultural yield is a cleaner target for the current weather research.

---

## Decision 02 — Preserve IBGE Source Semantics

Keep numeric values, explicit zeros, and unavailable values distinct.

Unavailable observations are not silently converted to zero.

---

## Decision 03 — Define Yield Only from Valid Production and Harvested Area

Municipality-year yield is defined only when the source values produce a valid agricultural observation.

Undefined cases remain missing.

---

## Decision 04 — Detrend Before Spatial Aggregation

Remove long-run productivity trends separately by municipality before aggregating anomalies to weather grids.

Reason: long-run productivity growth is spatially heterogeneous.

---

## Decision 05 — Use a Smooth Long-Run Trend

Use a second-difference penalized smoother rather than impose common structural-break dates.

---

## Decision 06 — Use P50=10 as Primary Historical Detrending

Primary:

- **P50=10**

Robustness:

- P50=12 — conservative;
- P50=6 — aggressive;
- linear — rigid benchmark.

P50=10 and P50=12 form the stable conservative region.

---

## Decision 07 — Require Sufficient Yield History

Retain municipalities with:

- at least 15 valid annual yield observations;
- at least a 20-year calendar span.

---

## Decision 08 — Do Not Apply a Hard Internal-Gap Exclusion

Internal gaps remain diagnostics rather than automatic exclusion criteria.

---

## Decision 09 — Do Not Invent Residuals for Missing Yield Years

The latent trend may be defined across missing periods, but residuals are calculated only where observed yield exists.

---

## Decision 10 — Retain Endpoint and Gap-Proximity Flags

These are sensitivity diagnostics rather than primary exclusion rules.

---

# Spatial Alignment and Composition

## Decision 11 — Align Adjusted Yield to ERA5 0.5° Grids

Weather and adjusted yield must share a common spatial unit.

---

## Decision 12 — Use Annual Harvested-Area Weights as Primary

Aggregate municipality residuals within each ERA5 grid using contemporaneous observed harvested-area weights.

This preserves the historical production footprint.

---

## Decision 13 — Evaluate Fixed Composition on Matched Support

The actual-weight and fixed-weight series must use the same residual support when compared.

---

## Decision 14 — Build Fixed Composition from Common Historical Support

The fixed reference vector is constructed from common within-grid harvested-area support, then restricted and renormalized to matched residual support where necessary.

---

## Decision 15 — Use Actual Composition as Primary and Fixed Composition as Robustness

Observed annual composition is the primary historical representation.

Common-support fixed composition is the spatial-composition counterfactual.

---

# Forecasting Discipline

## Decision 16 — Reconstruct Estimated Transformations Training-Only

Any forecasting backtest must rebuild detrending, weighting, scaling, feature selection, window selection, and tuning using training information only.

Full-history historical transformations must not leak into held-out forecast periods.

---

## Decision 17 — Preserve Month-Level Weather Structure

Analyze weather relationships by calendar / relative month when pooling would obscure seasonal structure.

EXP-01 established that pooled relationships can be misleading.

---

## Decision 18 — Separate Predictor Overlap from Incremental Yield Information

High weather-to-weather correlation does not establish that one variable is redundant for yield.

Conditional-information questions require yield-based analysis.

---

# EXP-03 Decisions

## Decision 19 — Use Dec_(t-1) → Apr_t as the Main Late-Weather Discovery Window

EXP-03 identified Dec–Apr as the clearest coherent late-period relationship structure.

This is an empirical window, not yet a biological growth-stage label.

---

## Decision 20 — Preserve Feb–Mar Spatial Heterogeneity

February and March contain most weak-consistency late-window cells.

Do not average across these months merely to obtain smoother statewide relationships.

---

## Decision 21 — Preserve Upper and Deep Soil Moisture as Distinct Concepts

March response changes materially with depth.

Use the conceptual hydrological organization:

> rainfall input → upper-soil state → deeper stored-water state

This is an organizing framework, not a demonstrated causal chain.

---

## Decision 22 — Keep Static Soil Properties Explanatory-Only

SoilGrids differences are suggestive but strongly entangled with latitude and production-support structure.

Static soil is not an approved predictive input.

It may be revisited later only as a parsimonious modifier if it survives independent validation and time-respecting predictive testing.

---

## Decision 23 — Collapse Only Clear Representation Duplicates

Canonical downstream representations:

- mean-daily solar radiation;
- mean VPD;
- 0–7 cm upper-soil moisture.

Archived robustness representations:

- monthly total solar;
- daily-max VPD;
- 7–28 cm upper-soil moisture.

These choices are representation simplifications, not claims of zero information in the archived variants.

---

## Decision 24 — Protect Conditional-Information Pairs

Do not collapse these solely on predictor correlation:

- temperature ↔ VPD;
- rainfall ↔ upper soil moisture;
- rainfall/history ↔ deep soil moisture;
- upper ↔ deep soil moisture.

---

## Decision 25 — Promote Only Two Dec–Jan Aggregation Candidates

Approved candidate summaries:

- Dec–Jan relative humidity;
- Dec–Jan 28–100 cm soil moisture.

Do not promote Jan–Feb, Feb–Mar, or Mar–Apr aggregates at this stage.

The deepest 100–255 cm soil-moisture layer remains month-specific despite very high persistence because the relevant yield / spatial signatures are not fully interchangeable.

---

## Decision 26 — Freeze the Step-5 Downstream Universe at 38 Representations

The 38 representations are a transparent candidate universe.

They are not a 38-variable regression and are not final predictive feature selection.

---

# Experiment Sequencing

## Decision 27 — Run EXP-05 Before EXP-04

EXP-05 resolves the largest remaining atmospheric-demand conditional-information question before the broader continuous-characterization stage.

Experiment IDs are retained for historical continuity even though execution order is 05 → 04.

EXP-05 may revise only the temperature/VPD portion of the Step-5 candidate universe according to a pre-specified rule.

---

## Decision 28 — Keep the Hydrological Conditional Follow-up Separate

The rainfall ↔ upper ↔ deep moisture problem is scientifically justified but not yet an authorized numbered experiment.

Prefer one coherent hydrological conditional design rather than several disconnected pairwise tests.

---

## Decision 29 — Defer Dynamic Bayesian Updating to Weather 2.0

Dynamic or sequential probabilistic yield updating is not part of the current v1.x experiment sequence.

It should be reconsidered only after the current weather-information problem is materially better resolved.

---

# Summary

The current historical Layer-1 architecture is:

```text
IBGE municipality yield
→ municipality-specific P50=10 detrending
→ observed municipality residuals
→ annual harvested-area-weighted ERA5-grid anomalies
→ month-structured weather analysis
→ protected redundancy / conditional-information gates
→ later continuous and out-of-sample predictive evaluation
```

Current research sequence:

> **EXP-01 complete → EXP-02 complete → EXP-03 complete → EXP-05 next → EXP-04 → later conditional / growth-stage / predictive work**
