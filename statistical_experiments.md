# Statistical Experiments

This document records the major statistical experiments conducted in Operation Sugar.

It answers:

1. What was tested?
2. How was it tested?
3. What did the experiment show?

Major methodological choices are summarized in [`research_decisions.md`](research_decisions.md).

Detailed curated reports, tables, figures, and execution records are stored under `outputs/research/`.

---

## Current Experiment Registry

| Experiment | Research question | Status |
|---|---|---|
| EXP-01 | How should the weather feature space be characterized before yield modeling? | Completed |
| EXP-02 | How should long-run yield trends and changing production geography be separated from short-run yield anomalies? | Completed |
| EXP-03 | How do weather conditions differ across adjusted-yield outcomes, and how spatially stable are those relationships? | Completed |
| EXP-05 | Does temperature or VPD retain yield information after conditioning on the other? | **Next** |
| EXP-04 | What continuous relationships remain among the post-EXP-05 candidate weather representations and adjusted yield? | After EXP-05 |
| Hydrological follow-up | How should rainfall, upper moisture, and deep moisture be separated conditionally? | Unnumbered / later |
| EXP-06 | Can weather information be organized into biologically meaningful sugarcane growth stages? | Proposed |
| EXP-07 | Do retained weather features provide incremental predictive value out of sample? | Proposed |
| EXP-08 | How heterogeneous are weather–yield responses across space? | Later / conditional |

Dynamic Bayesian updating has been removed from the current v1.x numbering and deferred to Weather 2.0.

---

# EXP-01 — Weather Feature Structure and Correlation Framework

## Status

Completed.

## Research Question

> How should Operation Sugar characterize relationships among weather variables before deciding which features should enter agricultural yield models?

## Primary Data

Validated municipality weather panel:

- 642 São Paulo municipalities;
- 1990–2025;
- 36 years;
- 12 months;
- 277,344 municipality-month observations;
- 11 verified monthly weather variables.

## Design

EXP-01 included:

- harvested-area support and missing-value semantics;
- unweighted month-specific weather correlation;
- harvested-area-weighted weather correlation;
- matched-support decomposition;
- adjacent-month persistence diagnostics.

## Findings

- Weather relationships are strongly month dependent.
- Pooled correlations can obscure or reverse month-specific relationships.
- Soil moisture is highly persistent relative to rainfall.
- Rainfall behaves as a comparatively transient input.
- Temperature and VPD overlap strongly but not uniformly.
- Production-footprint weighting changes relationship magnitudes more than matched-support exclusion in the core comparisons.

Qualitative persistence ordering:

> soil moisture > temperature > VPD > solar radiation > rainfall

## Interpretation Boundary

EXP-01 measures predictor overlap and persistence.

It does not establish which variables provide incremental yield information.

## Outputs

`outputs/research/exp_01/`

---

# EXP-02 — Yield Detrending and Spatial Composition

## Status

Completed.

## Research Questions

> How should long-run non-weather productivity growth be removed from municipality yield while preserving shorter-run variation?

> How much does changing production composition within an ERA5 weather grid alter the adjusted-yield representation?

## Source Support

Annual São Paulo municipality panel:

- 1974–2025;
- 642 municipalities;
- 511 municipalities pass the current history gate;
- 20,931 residual-bearing municipality-years;
- 78 ERA5 0.5° grids.

Eligibility:

\[
N_{\text{valid}} \ge 15
\]

and calendar span ≥20 years.

No hard internal-gap exclusion is used.

## Municipality-Level Detrending

For municipality \(i\):

\[
Y_{i,t}=m_i(t)+r_{i,t}.
\]

The approved trend estimator is a second-difference penalized smoother.

Retained specifications:

| Specification | Role |
|---|---|
| Linear | Rigid benchmark |
| P50=6 | Aggressive sensitivity |
| **P50=10** | **Primary** |
| P50=12 | Conservative robustness |

P50=10 and P50=12 residuals are nearly identical under the completed audit, establishing a stable conservative detrending region.

Residuals are calculated only where valid annual yield is observed. The latent smoother is not treated as an observed agricultural outcome during missing years.

## Grid Aggregation

Primary historical grid anomaly:

\[
R^{actual}_{g,t}
=
\sum_{i \in S_{g,t}}
w^{actual}_{i,g,t}r_{i,t}.
\]

Primary weighting:

- contemporaneous observed harvested-area composition.

Robustness:

- common-support fixed composition.

The fixed-composition counterfactual is evaluated on matched municipality-year residual support.

## Findings

Actual and fixed composition are broadly similar overall.

Composition effects become large when:

1. within-grid harvested-area weights move substantially; and
2. municipality residuals within the same grid differ strongly.

The effect is therefore heterogeneous and concentrated in a minority of grid-years.

## Final Historical Target

```text
municipality raw yield
→ P50=10 municipality detrending
→ municipality residual
→ annual harvested-area-weighted ERA5-grid anomaly
```

Primary robustness:

- P50=12;
- fixed composition;
- endpoint sensitivity;
- internal-gap proximity.

## Forecasting Boundary

These full-history transformations define a historical research representation.

Any formal out-of-sample forecast must reconstruct estimated transformations using training information only.

## Outputs

`outputs/research/exp_02/`

---

# EXP-03 — Yield-Stratified Weather Analysis

## Status

Completed.

## Research Question

> Which monthly weather conditions are associated with unusually high or low adjusted annual sugarcane yield, and how stable are those relationships across alternative grouping rules, time windows, and ERA5 grids?

## Canonical Support

Complete all-variable weather support begins in January 1981.

Complete all-variable yield years:

- 1982–2025.

Aligned support:

- 3,267 complete grid-years;
- 78 grids represented;
- 76 grids meet the ≥15 paired-year requirement for grid-specific correlation summaries.

Primary weather window:

- May_(t-1) → Apr_t.

Extended robustness:

- Jan_(t-1) → Apr_t.

## Primary Grouping

The primary descriptive grouping uses within-grid historical yield-anomaly ranks.

The categorical analysis is not a causal design and is not final predictive feature selection.

## Robustness

The broad late-window pattern survives:

- 20/60/20 grouping;
- within-grid z-score normalization followed by pooled quartiles;
- restriction of ranking history to the complete-weather era;
- continuous within-grid rank associations.

In the main Dec–Apr window, categorical and pooled continuous directions agree throughout the analyzed cells.

The extended-only early months are materially weaker than the primary window.

## Temporal Structure

Main coherent late window:

> **Dec_(t-1) → Apr_t**

Summary:

| Period | Empirical characterization |
|---|---|
| Dec–Jan | strongest and most spatially broad |
| Feb–Mar | weaker pooled monotonic evidence and more spatial heterogeneity |
| Apr | partial spatial reconvergence |

This pattern is descriptive. It is not yet a biological growth-stage definition.

## Variable-Level Structure

Most spatially stable late-window families:

- relative humidity;
- deeper soil moisture.

Mixed / heterogeneous but informative:

- rainfall;
- temperature;
- VPD;
- upper soil moisture;
- solar radiation.

## Spatial-Heterogeneity Audit

The weak-consistency late-window cells are concentrated entirely in February and March.

Disagreement is spread across many grids rather than explained by one statewide outlier.

This supports the overall EXP-03 classification:

> **B — Partially robust**

The broad humidity / deeper-moisture versus atmospheric-demand structure survives, but several variable-month cells are not spatially uniform enough to justify one statewide mechanistic interpretation.

## March Soil-Moisture Depth Analysis

Usable grids: 76.

Surface:

- March 0–7 cm grid-specific Spearman rho.

Deep:

- arithmetic mean of March 28–100 and 100–255 cm grid-specific Spearman rho.

Reconstructed regimes:

| Regime | Count |
|---|---:|
| surface positive / deep positive | 42 |
| surface negative / deep positive — depth recovery | 19 |
| surface negative / deep negative — persistent negative | 13 |
| surface positive / deep negative — reverse | 2 |

The result supports preserving upper and deep soil moisture as distinct hydrological concepts.

## SoilGrids Explanatory Synthesis

SoilGrids was used only as static explanatory context.

Native depths were preserved through 200 cm; no 200–255 cm soil property layer was fabricated.

Thickness-weighted summaries:

- upper: 0–30 cm;
- deep: 30–200 cm;
- profile contrast: deep minus upper.

The depth-recovery and persistent-negative regimes show suggestive differences in texture, bulk density, coarse fragments, and modeled water-retention profile.

However, the strongest soil contrasts also co-vary strongly with latitude and production-support structure.

Conclusion:

> **Suggestive / partial explanatory evidence only.**

Static soil is not promoted into the predictive weather feature set.

## Step-5 Representation Reduction

Approved canonical representations:

| Family | Canonical | Archived robustness |
|---|---|---|
| Solar | mean-daily solar radiation | monthly total solar |
| VPD | mean VPD | daily-max VPD |
| Upper soil moisture | 0–7 cm | 7–28 cm |

These are representation decisions, not proof that archived variants contain zero information.

## Step-5 Temporal Redundancy

Grid-specific matched-year adjacent-month Spearman correlations were calculated for:

- Dec–Jan;
- Jan–Feb;
- Feb–Mar;
- Mar–Apr.

Only two multi-month summaries passed the combined redundancy + existing-yield-signature + spatial-compatibility gate:

- Dec–Jan relative humidity;
- Dec–Jan 28–100 cm soil moisture.

No Jan–Feb, Feb–Mar, or Mar–Apr aggregate was promoted.

The 100–255 cm layer is extremely persistent but remains month-specific because its yield / spatial behavior is not sufficiently interchangeable across the relevant months.

## Frozen Downstream Universe

Step 5 produces **38 candidate representations**.

The candidate universe preserves:

- rainfall input;
- temperature;
- relative humidity;
- mean VPD;
- upper soil moisture;
- 28–100 cm deep moisture;
- 100–255 cm deep moisture;
- mean-daily solar radiation.

Protected conditional-information questions:

- temperature ↔ VPD;
- rainfall ↔ upper soil moisture;
- rainfall/history ↔ deep soil moisture;
- upper ↔ deep soil moisture.

## Outputs

- `outputs/research/exp_03/yield_stratified_monthly_weather/`
- `outputs/research/exp_03/march_soil_moisture_depth/`
- `outputs/research/exp_03/soil_regime_synthesis/`
- `outputs/research/exp_03/redundancy/`

---

# EXP-05 — Conditional Temperature–VPD Yield Response

## Status

**NEXT**

## Why EXP-05 Runs Before EXP-04

Step 5 intentionally preserved temperature and VPD because their incremental information remains unresolved.

Resolving this question before EXP-04 avoids carrying two overlapping atmospheric-demand families into the broader continuous-characterization stage without first testing whether both matter conditionally.

## Research Question

> Does VPD contain additional yield information after temperature is known, and does temperature contain additional information after VPD is known?

## Primary Focus

February_t.

EXP-03 found:

- meaningful negative categorical atmospheric-demand contrasts;
- weaker pooled monotonic relationships;
- greater spatial heterogeneity.

## Candidate Analysis

Start with transparent conditional diagnostics:

- matched-support temperature–VPD overlap;
- yield–VPD within narrow temperature conditions;
- yield–temperature within narrow VPD conditions;
- spatial-direction consistency before and after conditioning.

Only if warranted should a parsimonious nonlinear or interaction specification be considered.

## Boundary

EXP-05 is not final feature selection.

RH and solar remain secondary atmospheric context unless later evidence justifies expanding the conditional program.

---

# EXP-04 — Continuous Adjusted-Yield Characterization

## Status

Proposed — after EXP-05.

## Research Question

> What are the magnitude and shape of the retained continuous weather–yield relationships, and which relationships survive the approved target robustness checks?

## Scope

EXP-03 already computed pooled within-grid continuous associations and grid-specific Spearman diagnostics.

Therefore EXP-04 must add information rather than repeat that screen.

Focus areas:

- relationship shape;
- effect magnitude;
- uncertainty;
- statewide-common versus heterogeneous behavior;
- P50=12 robustness;
- fixed-composition robustness;
- comparison of the two approved Dec–Jan summaries with their constituent months.

The 38 Step-5 representations are a candidate universe, not a multivariate regression specification.

---

# Hydrological Conditional-Information Follow-up

## Status

Justified in principle / unnumbered / not yet designed.

Potential questions:

- rainfall versus upper-soil moisture;
- rainfall history versus deep moisture;
- upper versus deep moisture;
- 28–100 versus 100–255 cm deep-state representation.

Prefer one coherent hydrological design rather than disconnected pairwise experiments.

---

# EXP-06 — Growth-Stage Weather Aggregation

## Status

Proposed.

Question:

> Can weather variables be aggregated into biologically meaningful São Paulo sugarcane growth stages without discarding useful information?

Compare month-level, stage-level, and hybrid representations.

Stage boundaries must not be outcome-optimized on the full sample.

---

# EXP-07 — Incremental Predictive Value

## Status

Proposed.

Question:

> Do advanced weather variables improve annual yield prediction beyond simpler benchmarks?

Use chronological validation and transparent model ladders.

Feature selection, scaling, detrending, weighting, and tuning must occur within training samples.

---

# EXP-08 — Spatial Weather-Response Heterogeneity

## Status

Later / conditional.

EXP-03 already established meaningful spatial heterogeneity.

Future work should test parsimonious response modifiers or regional structure rather than simply repeat grid-by-grid correlation maps.

---

# Legacy Harvest-Progress Experiments

Earlier Operation Sugar versions modeled sugarcane crushing and harvest timing rather than annual agricultural yield.

The historical harvest-profile benchmark outperformed the evaluated aggregate and month-level weather models for that target.

Those negative results remain part of the research record:

- `month_level_model_findings.md`
- `negative_results.md`

They do not imply that weather is irrelevant to agricultural yield.
