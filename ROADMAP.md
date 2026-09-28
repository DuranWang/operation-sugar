# Operation Sugar Roadmap

Updated: September 27, 2026

Operation Sugar develops transparent, reproducible commodity research and forecast benchmarks, beginning with Brazilian sugarcane and sugar.

The current research target is **annual agricultural sugarcane yield (t/ha) in São Paulo**. The immediate priority is not to maximize model complexity; it is to establish a defensible adjusted-yield target and determine whether weather relationships survive reasonable changes in detrending and spatial aggregation.

Negative results remain part of the research record. An experiment is complete when its question has been evaluated credibly, including when no stable incremental relationship is found.

## Status and Priorities

| Status | Scope |
|---|---|
| **Completed** | v1.0–v1.6.0 research foundation; EXP-01S, EXP-01A, EXP-01B, EXP-01C |
| **Next** | EXP-02A — long-run trend specification and residual robustness |
| **After EXP-02A** | EXP-02B — spatial-composition sensitivity, subject to municipality-yield data gate |
| **After EXP-02A / 02B gate** | EXP-02C — weather-relationship robustness across retained anomaly definitions |
| **Later Layer 1** | EXP-03 through EXP-09: adjusted-yield exploration, growth-stage structure, incremental predictive value, spatial heterogeneity, dynamic probabilistic forecasting |
| **Long-term** | Layer 2: sugar / ethanol allocation and recovery; Layer 3: BRL/USD; Layer 4: supply chains |

## Four-Layer Research Architecture

| Layer | Research focus | Main questions |
|---|---|---|
| **1. Agricultural supply** | Weather → annual cane yield → cane production | Which weather variables contain stable explanatory and predictive information for TCH, and how should area be incorporated when moving from yield to production? |
| **2. Sugar production and energy** | Cane → sugar output; recovery / ATR; ethanol–sugar mix; energy links | How does available cane translate into sugar output, and how does allocation between sugar and ethanol vary? |
| **3. Currency** | BRL/USD and sugar prices | Does the exchange rate add information beyond agricultural and energy variables? |
| **4. Supply chains** | Ports, exports, inventories, transport, and physical availability | Do logistics and physical-flow indicators add information beyond the preceding layers? |

Cane yield, cane production, recoverable sugar, raw sugar, refined white sugar, and futures prices are distinct targets. They must not be treated as interchangeable.

---

## Layer 1 — Current Experiment Sequence

### EXP-01 — Basic vs Advanced Weather Feature Correlation

**Status: COMPLETED**

**Question**

How much information overlap exists between basic and advanced weather variables, and does that structure change when municipality observations are weighted by reported sugarcane harvested area?

#### EXP-01S — Harvested-Area Weight Stability

**Status: COMPLETED**

Measures year-to-year and long-horizon stability of municipality harvested-area shares under explicit IBGE missing-value semantics:

- numeric values are reported observations;
- `-` is explicit zero;
- `...` remains unavailable;
- unavailable values are not silently imputed as zero.

Main conclusion:

> São Paulo reported sugarcane harvested-area shares show strong year-to-year persistence but meaningful cumulative spatial change over multi-year horizons.

The result supports contemporaneous annual observed-only weights for historical descriptive sensitivity analysis, while leaving forecast-time weighting unresolved.

#### EXP-01A — Municipality-Level Weather Correlation

**Status: COMPLETED**

Validated panel:

- 1990–2025;
- 642 municipalities;
- 36 years;
- 12 months;
- 277,344 municipality-month observations;
- 11 verified weather variables;
- no missing weather observations in the validated panel.

Main conclusions:

- same-month weather relationships are strongly calendar-month dependent;
- temperature and VPD overlap substantially but not uniformly;
- surface soil moisture is much more temporally persistent than precipitation;
- pooled correlations can be materially misleading and can reverse sign relative to within-calendar-month relationships;
- variable-specific temporal aggregation is more defensible than imposing one common window on every weather feature.

#### EXP-01B — Harvested-Area-Weighted Weather Correlation

**Status: COMPLETED**

Repeats the EXP-01A structure while preserving municipality-level observations and weighting municipality-years by contemporaneous observed-only reported harvested-area share.

Main conclusion:

> The broad qualitative weather-correlation structure survives crop-area weighting, but correlation magnitude and temporal persistence are not invariant to the production footprint.

#### EXP-01C — Matched-Support Weighting-Sensitivity Comparison

**Status: COMPLETED**

Introduces:

```text
A   = original equal-weight support
A*  = equal-weight matched harvested-area-observed support
B   = matched support with harvested-area weights
```

This decomposes:

\[
\Delta_{support}=A^*-A
\]

\[
\Delta_{weight}=B-A^*
\]

\[
\Delta_{total}=B-A
\]

Across the 60 core pair × month comparisons:

- mean absolute Pearson support effect: 0.0066;
- mean absolute Pearson weighting effect: 0.0673;
- mean absolute Spearman support effect: 0.0086;
- mean absolute Spearman weighting effect: 0.0740.

Main conclusion:

> EXP-01A → EXP-01B differences are driven primarily by harvested-area weighting rather than by exclusion of the unavailable-area municipality-years.

The five pre-specified same-month relationship directions remain stable across A, A*, and B.

---

### EXP-02 — Non-Weather Baseline & Yield Detrending

**Status: APPROVED; EXP-02A NEXT**

**Overall question**

How robustly can OS define annual São Paulo yield anomalies before interpreting weather–yield relationships, given uncertainty about the true long-run non-weather process and possible changes in production geography?

EXP-02 does **not** attempt to model every determinant of sugarcane yield or to prove that a detrended residual is the weather component.

It treats the unknown long-run component as nuisance structure:

\[
Y_t = m(t) + u_t
\]

and asks whether substantive conclusions survive reasonable alternative treatments of \(m(t)\) and spatial composition.

#### EXP-02A — Long-Run Trend Specification & Residual Robustness

**Status: NEXT**

Compare:

1. linear trend;
2. limited smooth nonlinear trend, such as LOESS or spline;
3. piecewise / structural-break specification.

For each specification:

\[
r_t^{(k)} = Y_t - \hat m_k(t)
\]

Primary diagnostics:

- raw yield with fitted trends;
- residual series;
- residual correlation matrix;
- residual standard deviation / scale;
- sign agreement by year;
- ranking of large positive / negative anomaly years;
- remaining low-frequency structure;
- periods of material divergence.

Decision logic:

- **Case A:** residuals are highly similar → detrending uncertainty is small;
- **Case B:** disagreement is concentrated in a historical period → perform limited structural-break diagnosis;
- **Case C:** residuals are fundamentally different → retain multiple plausible anomaly definitions and treat the target as specification-sensitive.

Do not select a trend merely because it fits the historical sample best. Over-flexible trends can over-detrend; rigid trends can under-detrend.

#### EXP-02B — Spatial-Composition Sensitivity

**Status: APPROVED / AFTER EXP-02A**

**Data gate:** municipality-level annual yield and harvested area must be jointly usable.

Compare:

\[
Y_t^{annual}=\sum_i w_{i,t}Y_{i,t}
\]

with:

\[
Y_t^{fixed}=\sum_i \bar w_iY_{i,t}
\]

and inspect:

\[
\Delta r_t=r_t^{annual}-r_t^{fixed}
\]

This tests whether changing production geography materially changes the annual anomaly definition.

If municipality-level yield data do not pass validation, this experiment is reported as not executable rather than approximated by copying state yield across municipalities.

#### EXP-02C — Weather-Relationship Robustness

**Status: APPROVED / AFTER EXP-02A AND EXP-02B GATE**

Re-estimate the same pre-specified weather relationship across retained anomaly definitions and, if necessary, spatial-composition treatments.

Compare:

- sign;
- effect magnitude / standardized effect size;
- sensitive months or windows;
- uncertainty;
- later, time-respecting out-of-sample performance.

A weather relationship that appears only under one detrending choice is not sufficient evidence for a stable relationship.

#### EXP-02 Stop Rule

Do **not** automatically expand EXP-02 into separate historical models for fertilizer, varietal adoption, ratoon age, mechanization, capital investment, or every other non-weather driver.

If reasonable detrending and spatial-composition specifications produce stable conclusions, EXP-02 is complete.

Open a separate experiment for a structural factor only when there is concrete evidence that it materially destabilizes the anomaly definition or confounds the weather relationship.

---

### EXP-03 — Yield-Stratified Weather Analysis

**Status: PROPOSED**

Dependency: EXP-02 anomaly definition.

Question:

> How do weather conditions differ across historically high-, middle-, and low-adjusted-yield seasons?

This is exploratory grouping, not a causal estimate and not a detrending procedure.

### EXP-04 — Weather Features vs Annual Sugarcane Yield

**Status: PROPOSED**

Question:

> Which weather variables are associated with continuous adjusted annual yield in different months or candidate windows?

Required outputs include month × feature relationship maps, relationship curves, comparison with EXP-03 patterns, and candidate sensitive windows for later validation.

### EXP-05 — Conditional Temperature–VPD Yield Response

**Status: PROPOSED**

Question:

> Does VPD contain additional yield information after temperature is known, and does temperature contain additional information after VPD is known?

Conditional regression relationships are not automatically causal effects.

### EXP-06 — Growth-Stage Weather Feature Aggregation

**Status: PROPOSED**

Compare:

- month-level features;
- growth-stage aggregated features;
- hybrid representations.

All comparisons must use the same historical samples, forecast information set, and time-aware validation design.

### EXP-07 — Incremental Predictive Value of Advanced Weather Features

**Status: PROPOSED**

Candidate model ladder:

| Model | Feature set |
|---|---|
| M0 | Non-weather reference baseline |
| M1 | Basic weather |
| M2 | Basic + VPD |
| M3 | Basic + soil moisture |
| M4 | Basic + solar radiation |
| M5 | Basic + selected advanced features |

Feature selection and regularization tuning must occur inside each training sample.

### EXP-08 — Spatial Weather-Response Heterogeneity

**Status: PROPOSED / DATA-DEPENDENT**

Proceed only if yield resolution supports spatial analysis. State yield must not be copied across municipalities and treated as independent observations.

### EXP-09 — Bayesian Dynamic Yield Forecasting

**Status: CONCEPT**

Potential objective:

> Represent annual yield as a predictive distribution that updates through the crop season as new observed weather becomes available.

No prior, likelihood, dynamic architecture, or implementation has yet been selected.

---

## Layer 1 Completion Criteria

Layer 1 requires:

- a reproducible annual-yield target;
- documented crop-season alignment;
- robust anomaly definition;
- explicit handling of spatial composition;
- benchmarked weather experiments;
- time-aware evaluation for predictive claims;
- uncertainty and limitation reporting;
- preserved successful and unsuccessful specifications.

A null result is acceptable.

---

## Layer 2 — Cane-to-Sugar Conversion, Ethanol/Sugar Mix, and Energy

**Status: LONG-TERM PLANNED**

Key questions:

- How does available cane translate into actual sugar production?
- What information is needed on sugar content, recovery, ATR / CCS, and processing?
- How does allocation between sugar and ethanol vary?
- What role do crude oil and ethanol economics play?

Accounting relationships, correlations, predictive relationships, and causal hypotheses must be distinguished.

---

## Layer 3 — BRL/USD and Sugar Prices

**Status: LONG-TERM PLANNED**

Investigate whether currency adds information beyond agricultural and energy variables.

Any price study must define:

- quote convention;
- levels versus returns;
- forecast horizon;
- contemporaneous versus lagged information;
- contract-roll treatment where applicable.

---

## Layer 4 — Supply Chains and Sugar-Price Interactions

**Status: LONG-TERM PLANNED**

Candidate evidence:

- port activity;
- vessel lineups;
- export shipments;
- congestion;
- freight;
- storage / inventories;
- shipment destinations.

Distinguish sugar produced, available for export, loaded / shipped, and delivered.

---

## Cross-Layer Evaluation Principles

- Standardized targets, units, geographic scope, forecast issue dates, and horizons.
- Preserved forecasts and revision histories.
- Observation date separated from publication date.
- Historical data vintages where available.
- Target-appropriate public benchmarks.
- Matched evaluation samples.
- Training-fold preprocessing and nested tuning.
- Chronological expanding / rolling evaluation for historical forecasting claims.
- Explicit uncertainty propagation between layers.
- Reporting of negative results, instability, and specification changes.

The completed v1.5.1 leave-one-season-out study is a held-out-season evaluation, not a point-in-time historical trading backtest.

Better supply forecasts do not by themselves establish profitable trading strategies.

---

## Additional Research Options

ENSO / climate indicators, remote sensing, additional spatial heterogeneity, alternative forecast-safe weighting schemes, and interpretable nonlinear models remain optional extensions.

Introduce them only when they address a specific limitation and the available sample supports credible evaluation.

---

## v1.6.0 ✅

### Weather Feature Structure, Spatial Weighting, and Yield-Robustness Framework

#### Research Scope

Version 1.6.0 closes the EXP-01 research program and establishes the methodological starting point for annual-yield research.

#### Major Additions

- Rebuilt and modularized weather and sugarcane ETL components.
- Added combined NASA POWER and Open-Meteo / ERA5 monthly weather processing.
- Added validated municipality-level weather analysis across 642 São Paulo municipalities and 1990–2025.
- Completed EXP-01S harvested-area weight stability and observed-weight construction.
- Completed EXP-01A municipality-level weather correlation and temporal-persistence analysis.
- Completed EXP-01B harvested-area-weighted weather correlation analysis.
- Completed EXP-01C matched-support attribution separating support effects from weighting effects.
- Added curated research outputs under `outputs/research/exp_01/`.
- Added reproducible EXP-01 analysis tests; the analysis suite passes 52 tests at this release milestone.
- Defined EXP-02A / EXP-02B / EXP-02C as the next annual-yield robustness sequence.

#### Research Findings

- Weather relationships are strongly calendar-month dependent.
- Pooled correlations can materially differ from within-calendar-month relationships.
- Surface soil moisture is substantially more persistent than precipitation under fixed-calendar comparisons.
- Harvested-area weighting changes correlation magnitude and persistence more than matched-support exclusion does in the core EXP-01 comparisons.
- São Paulo harvested-area shares are locally persistent but exhibit meaningful long-horizon spatial change.
- EXP-01 does not select final yield-model features; it establishes predictor structure and weighting sensitivity before yield-based inference.

#### Result

Version 1.6.0 marks Operation Sugar's transition from the earlier harvest-block crushing benchmark program to a formal annual-yield research framework.

The immediate next step is EXP-02A: compare reasonable long-run yield trend specifications and test whether the resulting annual yield anomalies are robust to detrending choice.

---

## Completed Research Foundation — Version 1.x**

The retained release record below documents the development path through v1.6.0. Earlier v1.0–v1.5.1 findings concern the original harvest and crushing targets; v1.6.0 closes EXP-01 and transitions the project into the annual-yield research program.

## v1.5.1 ✅**

### Month-Level Weather Models**

#### Research Question**

> Does preserving September–April monthly weather structure improve harvest-block crushing prediction beyond the historical harvest profile?

#### Major Additions**

- September–April monthly rainfall features

- September–April monthly temperature features

- Rainfall Month-Level OLS

- Rainfall Month-Level Ridge

- Temperature Month-Level OLS

- Temperature Month-Level Ridge

- Joint Month-Level Ridge

- Nested leave-one-season-out alpha selection

- Fold-specific weather standardization

- Partially penalized Ridge regression

- Effective weather degrees-of-freedom diagnostics

- Alpha-grid boundary diagnostics

- Influential-season analysis

- Unified seven-model comparison

- Publication-style reporting figures

- Formal research findings and negative-results documentation

#### Model Comparison**

Seven harvest-block models were evaluated across five aggregation horizons:

1. Block-Only OLS

2. Temperature Month-Level Ridge

3. Aggregate Weather OLS

4. Rainfall Month-Level Ridge

5. Joint Month-Level Ridge

6. Temperature Month-Level OLS

7. Rainfall Month-Level OLS

The ranking was identical across all five horizons.

#### Research Findings**

- Block-Only OLS achieved the lowest LOSO RMSE at every horizon.

- Temperature Month-Level Ridge was the strongest weather-based model.

- Temperature Ridge remained approximately 0.56% to 1.49% worse than Block-Only.

- Rainfall Ridge remained approximately 1.37% to 5.26% worse than Block-Only.

- Ridge substantially reduced the overfitting of unregularized monthly models.

- Nested LOSO selected the maximum alpha in 75% to 81.25% of outer folds.

- Median effective weather degrees of freedom was approximately zero for every Ridge model and horizon.

- Joint Month-Level Ridge introduced penalty-selection instability rather than stable complementary information.

- Temperature Ridge was especially sensitive to the `21-22` season.

- Joint Ridge was especially sensitive to the `23-24` season.

#### Result**

Version 1.5.1 completed the first month-level weather modeling study in Operation Sugar.

Within the available 16-season sample and evaluated linear specifications, aggregate and month-level growing-season weather did not provide stable incremental out-of-sample predictive value for harvest-block crushing beyond the historical harvest-block profile.

The result does not imply that weather is unimportant to sugarcane production. It establishes that the current target, variables, sample, and model structures are insufficient to improve this specific prediction task.

---

---

## v1.5.0 ✅**

### Aggregate Weather Baselines**

#### Research Question**

> Do aggregate growing-season weather variables improve prediction of historical sugarcane crushing?

#### Major Additions**

- Weather–harvest modeling datasets

- Harvest-block baseline models

- Complete-season baseline models

- Leave-one-season-out cross-validation

- Fold-specific predictor standardization

- Aggregate weather dashboards

#### Research Findings**

At the harvest-block level:

- aggregate rainfall and temperature did not improve out-of-sample prediction;

- historical harvest-block position explained most of the predictable variation;

- Aggregate Weather OLS underperformed Block-Only OLS across all five aggregation horizons.

At the complete-season level:

- aggregate rainfall and temperature did not outperform the training-season historical mean;

- positive complete-sample coefficients did not generalize to held-out seasons.

#### Result**

Version 1.5.0 established the statistical benchmarks for future weather models and demonstrated the limitations of compressing the complete growing season into one rainfall total and one average temperature.

---

---

## v1.4.0 ✅**

### Harvest Intelligence**

#### Research Question**

> How does the current harvest compare with historical harvest behavior?

#### Major Additions**

- Historical percentile-band benchmarking

- Comparable harvest snapshots

- Harvest pace rankings

- Automated harvest research summaries

- Historical harvest dashboards

#### Result**

Version 1.4 established a quantitative historical benchmark for evaluating harvest progress using standardized UNICA reporting periods.

---

---

## v1.3.0 ✅**

### Harvest Calendar Analytics**

- Historical harvest calendar

- Harvest calendar heatmap

- Harvest timing metrics

- Data-driven harvest-stage inference

- Three-stage seasonal research framework

```text

Growing Stage

      ↓

Maturation Stage

      ↓

Harvest Stage

```

---

---

## v1.2.0 ✅**

### Historical Weather Intelligence**

- Historical weather archive

- Multi-season benchmark dashboards

- Literature-informed growing-season framework

- Historical weather benchmarking

---

---

## v1.1.0 ✅**

### Harvest Infrastructure**

- UNICA harvest ETL

- Historical harvest database

- Automated validation framework

- Static analytical dashboards

- Automated testing

---

---

## v1.0.0 ✅**

### Research Infrastructure**

- NASA POWER weather ETL

- Municipality metadata validation

- Monthly weather aggregation

- Growing-season feature engineering

- Modular project architecture

---

---
