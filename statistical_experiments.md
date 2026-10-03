# Statistical Experiments

This document records the major statistical experiments conducted in Operation Sugar.

It answers three questions:

1. What was tested?
2. How was it tested?
3. What did the experiment show?

Major methodological choices are documented in `research_decisions.md`.

Research-engineering problems and implementation lessons are documented in `research_engineering_challenges.md`.

Detailed tables, figures, execution reports, and diagnostics are stored under `outputs/research/`.

---

# Current Experiment Registry

| Experiment | Research Question | Status |
|---|---|---|
| EXP-01 | How should the weather feature space be characterized before yield modeling? | Completed |
| EXP-02 | How should long-run yield trends and changing production geography be separated from short-run yield anomalies? | Completed |
| EXP-03 | How do weather conditions differ across high-, medium-, and low-yield anomaly years? | Next |
| EXP-04 | What continuous relationships exist between weather variables and adjusted yield anomalies? | Proposed |
| EXP-05 | Does temperature response depend on atmospheric dryness such as VPD? | Proposed |
| EXP-06 | Can weather information be organized into biologically meaningful sugarcane growth stages? | Proposed |
| EXP-07 | Do weather features provide incremental predictive value out of sample? | Proposed |
| EXP-08 | How heterogeneous are weather–yield relationships across space? | Future |
| EXP-09 | Can yield forecasts be updated dynamically as weather information arrives? | Future |

---

# EXP-01 — Weather Feature Structure and Correlation Framework

## Status

Completed in Version 1.6.0.

## Research Question

> How should Operation Sugar characterize relationships among weather variables before deciding which features should enter agricultural yield models?

## Data

The primary São Paulo weather panel contains:

- 642 municipalities;
- 36 years;
- 12 calendar months;
- 277,344 municipality-month observations;
- 11 weather variables.

## EXP-01S — Harvested-Area Support Audit

### Purpose

Establish source semantics and harvested-area support before production weighting.

The agricultural source distinguishes:

- numeric reported observations;
- explicit zero values;
- unavailable observations.

Unavailable observations are not treated as zero.

This audit ensures that weighting does not create false geographic support.

---

## EXP-01A — Unweighted Weather Structure

### Analysis

Weather-variable relationships were evaluated:

- across pooled observations;
- separately by calendar month;
- through temporal-persistence diagnostics.

### Findings

Weather relationships are strongly month dependent.

Pooled correlations can obscure or reverse month-specific relationships.

Temporal persistence also varies by variable and month.

### Implication

Subsequent weather research should preserve temporal structure rather than assume one pooled annual relationship.

---

## EXP-01B — Harvested-Area-Weighted Weather Structure

### Analysis

Municipality observations were weighted by harvested area so that economically important sugarcane regions contribute more strongly.

### Finding

Production weighting changes estimated correlation magnitudes more than simple support exclusion in many comparisons.

### Implication

The weather environment experienced by major production areas can differ from the unweighted geographic average.

---

## EXP-01C — Matched-Support Decomposition

### Analysis

Weighted and unweighted relationships were compared on matched municipality support.

### Finding

Most of the difference between weighted and unweighted weather relationships is attributable to the weighting structure itself rather than merely to exclusion of municipalities with unavailable harvested-area data.

### Conclusion

EXP-01 established three working principles:

1. preserve month-level weather structure;
2. treat production weighting as analytically meaningful;
3. diagnose support effects separately from weighting effects.

EXP-01 did not select a predictive weather model.

Its purpose was to characterize the feature space before yield modeling.

## Outputs

`outputs/research/exp_01/`

---

# EXP-02 — Yield Detrending and Spatial Composition

## Status

Completed in Version 1.6.1.

## Research Questions

> How should long-run non-weather productivity trends be removed from municipality sugarcane yield while preserving shorter-run agricultural variation?

> How much does changing production composition within ERA5 weather grids affect the resulting adjusted-yield series?

## Objective

Construct the historical adjusted-yield representation used by subsequent weather experiments.

Conceptually:

\[
\text{observed yield}
=
\text{long-run municipality trend}
+
\text{short-run yield anomaly}.
\]

The municipality anomalies are then aligned to ERA5 weather grids.

---

# EXP-02 Phase 0 — Source and Support Audit

## Data

The annual São Paulo municipality panel covers:

- 1974–2025;
- 642 municipalities;
- 33,384 municipality-year rows;
- 21,822 valid yield observations before final eligibility filtering.

Municipality histories differ in valid-year count, calendar span, internal gaps, and endpoint coverage.

## Final Eligibility Rule

A municipality is retained when:

\[
N_{\text{valid}} \geq 15
\]

and:

\[
\text{calendar span} \geq 20\text{ years}.
\]

No hard maximum internal-gap threshold is imposed.

The final detrending sample contains:

- 511 municipalities;
- 20,931 observed municipality-year yield values.

Internal-gap length remains a diagnostic rather than an exclusion rule.

---

# EXP-02A — Municipality-Level Yield Detrending

## Research Question

> Which trend specification removes long-run agricultural productivity growth without excessively absorbing shorter-horizon variation that may contain weather signal?

## Model

For municipality \(i\):

\[
Y_{i,t}=m_i(t)+r_{i,t},
\]

where:

- \(Y_{i,t}\) is observed yield;
- \(m_i(t)\) is the estimated long-run trend;
- \(r_{i,t}\) is the adjusted yield residual.

The penalized smoother solves:

\[
\hat m_i
=
\arg\min_m
\left[
\sum_{t\in O_i}(Y_{i,t}-m_{i,t})^2
+
\lambda\sum_t(\Delta^2m_{i,t})^2
\right],
\]

with:

\[
\Delta^2m_t=m_{t+1}-2m_t+m_{t-1}.
\]

Its idealized frequency response is:

\[
H(P)
=
\frac{1}
{1+16\lambda\sin^4(\pi/P)}.
\]

`P50` denotes the period where the trend has a 50% amplitude response.

## Specifications

| Specification | Role |
|---|---|
| Linear | Rigid benchmark |
| P50 = 6 | Aggressive sensitivity |
| P50 = 10 | Primary |
| P50 = 12 | Conservative robustness |

## Cross-Specification Results

| Comparison | Pearson | Spearman | Sign Agreement | MAD |
|---|---:|---:|---:|---:|
| Linear vs P50 = 10 | 0.7259 | 0.6493 | 71.77% | 5.616 t/ha |
| Linear vs P50 = 12 | 0.7560 | 0.6849 | 73.56% | 5.336 t/ha |
| Linear vs P50 = 6 | 0.6437 | 0.5508 | 67.01% | 6.290 t/ha |
| P50 = 10 vs P50 = 12 | 0.9952 | 0.9912 | 95.46% | 0.567 t/ha |
| P50 = 10 vs P50 = 6 | 0.9635 | 0.9309 | 86.27% | 1.521 t/ha |
| P50 = 12 vs P50 = 6 | 0.9373 | 0.8886 | 82.47% | 2.016 t/ha |

Residual standard deviations:

| Specification | Residual SD |
|---|---:|
| Linear | 11.056 t/ha |
| P50 = 10 | 6.848 t/ha |
| P50 = 12 | 7.255 t/ha |
| P50 = 6 | 5.416 t/ha |

## Diagnostics

### Internal Gaps

Cross-specification disagreement is somewhat larger for municipalities with longer internal gaps, but the relationship is not monotonic.

The conservative P50 = 10 and P50 = 12 specifications remain highly stable.

Gap length is therefore retained as a sensitivity diagnostic rather than a hard gate.

### Endpoints

Cross-specification disagreement is largest near municipality-series boundaries and declines farther inside the series.

Endpoint proximity is retained for downstream sensitivity analysis.

## Conclusion

P50 = 10 and P50 = 12 form a stable conservative detrending region.

The final primary historical detrending specification is:

\[
\boxed{P50=10}.
\]

P50 = 12 remains the principal detrending robustness check.

Linear remains a rigid benchmark.

P50 = 6 remains an aggressive sensitivity specification.

---

# EXP-02B — Spatial Composition Sensitivity

## Research Question

> How much does changing municipality production composition within an ERA5 weather grid alter the grid-level adjusted-yield anomaly?

## Spatial Mapping

The 511 eligible municipalities map to:

- 78 ERA5 0.5° grids;
- 74 multi-municipality grids;
- 4 single-municipality grids.

Single-municipality grids are reported separately because actual and fixed composition are mechanically identical.

---

## Primary Aggregation

The primary grid-level anomaly uses annual harvested-area weights.

For municipality \(i\), grid \(g\), and year \(t\):

\[
w^{actual}_{i,g,t}
=
\frac{A_{i,t}}
{\sum_{j\in S_{g,t}}A_{j,t}}.
\]

The grid anomaly is:

\[
R^{actual}_{g,t}
=
\sum_{i\in S_{g,t}}
w^{actual}_{i,g,t}r_{i,t}.
\]

---

## Fixed-Composition Counterfactual

An initial candidate fixed-weight design averaged each municipality's historical production share over its own observation history.

That design was rejected after audit because different observation windows could produce an incoherent reference vector.

The approved fixed-composition design uses common historical support.

For grid \(g\):

\[
\bar w_{i,g}
=
\frac{1}{|C_g|}
\sum_{t\in C_g}
\frac{A_{i,t}}
{\sum_{j\in M_g}A_{j,t}},
\]

where \(C_g\) contains years with valid harvested-area support for the full grid municipality set.

When a particular grid-year contains only a subset of the reference municipalities with valid yield residuals, the approved reference vector is renormalized over that same matched support.

---

## Composition Effect

Define:

\[
\Delta_{g,t}
=
R^{actual}_{g,t}
-
R^{fixed}_{g,t}.
\]

\(\Delta\) measures the effect of changing within-grid production composition on the grid-level yield anomaly.

Weight movement is measured by total variation distance:

\[
TV_{g,t}
=
\frac12
\sum_i
\left|
w^{actual}_{i,g,t}
-
w^{fixed}_{i,g,t}
\right|.
\]

`TV` measures how far the production composition moved.

\(|\Delta|\) measures the consequence of that movement for the yield anomaly.

---

## Primary Results

Across 3,694 valid multi-municipality grid-years under P50 = 10:

| Metric | Result |
|---|---:|
| Pearson correlation, actual vs fixed | 0.9485 |
| Spearman correlation | 0.9410 |
| Mean absolute difference | 0.840 t/ha |
| RMSE | 1.668 t/ha |
| Sign agreement | 92.15% |

Relationship between composition movement and anomaly impact:

- Pearson correlation between \(TV\) and \(|\Delta|\): 0.5354;
- Spearman correlation: 0.6376.

The top 10% of grid-years account for 48.17% of total absolute composition effect.

## Interpretation

Changing within-grid production composition usually has a modest effect.

Large effects occur when two conditions coincide:

1. substantial harvested-area redistribution;
2. strongly different municipality residuals within the same grid.

The effect is therefore heterogeneous and concentrated in the tail.

---

# EXP-02B Top-Tail Diagnostic

The largest composition events were decomposed into municipality-level contributions.

The maximum observed event occurred in:

`era5_-20.50_-50.00`

in 1981, with:

\[
|\Delta|=19.272\text{ t/ha}.
\]

Contribution accounting reproduces the aggregate effect exactly.

Across the top 10 composition events:

- all weight vectors reconcile correctly;
- no unavailable-area artifact was identified;
- no normalization failure was identified;
- P50 = 12 preserves the sign of all top 10 events;
- the same events remain dominant under the conservative robustness specification.

The observed tail therefore represents real weighting sensitivity rather than an implementation artifact.

---

# EXP-02 Conclusion

EXP-02 defines the historical adjusted-yield representation used by subsequent weather research:

\[
\boxed{
\text{municipality raw yield}
\rightarrow
P50=10\text{ detrending}
\rightarrow
\text{municipality yield residual}
\rightarrow
\text{annual harvested-area-weighted ERA5 grid anomaly}
}
\]

Primary robustness checks retain:

- P50 = 12 detrending;
- common-support fixed composition;
- internal-gap diagnostics;
- endpoint diagnostics.

These full-history transformations are intended for historical research.

Any future out-of-sample forecasting system must reconstruct estimated transformations using training information only.

## Outputs

`outputs/research/exp_02/`

---

# EXP-03 — Yield-Stratified Weather Analysis

## Status

Next experiment.

## Research Question

> How do historical weather conditions differ between unusually high-, normal-, and unusually low-yield outcomes after removing long-run municipality productivity trends?

## Objective

Use the adjusted-yield representation established in EXP-02 to identify interpretable weather patterns associated with unusually strong or weak agricultural yield outcomes.

EXP-03 provides the first direct weather-to-adjusted-yield comparison before continuous response modeling.

## Design Questions Still Open

The following must be finalized before implementation:

- crop-season and weather-year alignment;
- grouping rule for high, medium, and low yield anomalies;
- whether grouping is global, year-relative, grid-relative, or quantile-based;
- minimum support within groups;
- statistical comparison procedure;
- endpoint and internal-gap sensitivity;
- presentation of actual-composition versus fixed-composition robustness.

EXP-03 will be designed before code development begins.

---

# Planned Experiments

The following experiments remain intentionally high-level until their research designs are formally approved.

| Experiment | Purpose | Status |
|---|---|---|
| EXP-04 | Estimate continuous weather–yield relationships | Proposed |
| EXP-05 | Test conditional temperature–VPD relationships | Proposed |
| EXP-06 | Evaluate growth-stage weather representation | Proposed |
| EXP-07 | Test incremental out-of-sample predictive value | Proposed |
| EXP-08 | Measure spatial heterogeneity in weather–yield response | Future |
| EXP-09 | Develop dynamic or sequential yield updating | Future |

No methodology in these experiments should be treated as finalized until its design is explicitly approved.

---

# Legacy Experiments — Harvest-Progress Modeling

Earlier Operation Sugar versions modeled São Paulo sugarcane crushing and harvest progress rather than annual agricultural yield.

These experiments remain part of the project history but are not part of the current EXP-01–EXP-09 numbering system.

## v1.5.0 — Aggregate Weather Baseline

Research question:

> Do aggregate growing-season rainfall and temperature improve prediction of historical sugarcane crushing?

The experiment evaluated harvest-block and complete-season crushing using aggregate rainfall and temperature with Leave-One-Season-Out validation.

It established the first weather-based predictive baseline.

## v1.5.1 — Month-Level Weather Models

Research question:

> Does preserving monthly weather structure improve out-of-sample prediction of historical sugarcane crushing?

The experiment evaluated month-level rainfall and temperature representations using OLS and Ridge specifications, with nested Leave-One-Season-Out validation for regularized models.

These experiments remain useful methodological and negative results but were superseded by the annual agricultural-yield research architecture introduced in v1.6.x.

Detailed legacy findings remain in:

- `month_level_model_findings.md`;
- `negative_results.md`.

---

# Current Research State

As of Version 1.6.1:

\[
\boxed{\text{EXP-01 completed}}
\]

\[
\boxed{\text{EXP-02 completed}}
\]

\[
\boxed{\text{EXP-03 next}}
\]

The adjusted-yield target is now established.

The immediate research objective is to determine which historical weather patterns are associated with unusually strong or weak sugarcane yield outcomes.
