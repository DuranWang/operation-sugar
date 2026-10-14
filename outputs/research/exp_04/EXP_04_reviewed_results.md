# EXP-04 — Continuous Weather–Yield Response Characterization

Reviewed: 2026-10-14. Execution was reported complete by the implementing Work; this update reviews supplied result tables without rerunning the experiment.

## Scope and estimation

The frozen EXP-03 universe contains 38 candidates, analyzed separately, one weather representation at a time. Primary Y is the actual-composition P50=10 grid yield residual (t/ha), constructed from municipality residuals and observed harvested-area weights. These are marginal historical associations, not a joint annual weather model.

There are 78 mapped weather groups and 2,964 candidate-grid rows. Linear fits require N >= 20: 2,888 fits (76 grids per candidate). Restricted quadratic fits require N >= 30, at least 10 distinct X values, and rank/conditioning checks: 2,736 fits (72 grids per candidate). Failed gates remain unresolved. All pooled PL/PQ/HL/HQ models use the same fixed 72-grid quadratic roster for their candidate; the 76-grid linear summaries have a different denominator.

Candidate-specific paired weather spans 1981–2025 for Jan–Apr and 1982–2025 for Dec and Dec–Jan. No complete 16-month weather-window requirement was imposed. The execution report records 143,374 candidate-grid-year rows and target reconstruction error no larger than 1.2e-14 t/ha.

## Linear results

See `linear_response_review_summary.csv` for all 38 candidates. Its positive-grid counts describe original fitted slope signs. Separate columns count grids with both 3- and 5-year block intervals entirely positive or entirely negative. Neither the sign count nor the median IQR contrast is an uncertainty interval.

Rainfall has a positive majority in all five month slots (44–60 of 76 grids); its grid median fitted IQR contrast ranges from +0.236 to +0.608 t/ha. The 28–100 cm SM candidates have 57–60 positive grids and median IQR contrasts of +0.523 to +0.782 t/ha. Temperature and VPD have negative majorities. These spatial direction patterns coexist with substantial uncertainty for individual grids. Grids share calendar shocks and are not independent replications.

An IQR contrast is the fitted change between a grid's observed weather P25 and P75. Different variables have different units, distributions, and correlated exposures; these marginal contrasts do not rank their independent contributions. Small single-month linear R² values do not test how much a jointly specified seasonal representation can explain annual yield anomalies. That question requires a separate design.

## Restricted quadratic evidence

Only February rainfall (`rainfall_input__m_-2`) has pooled PQ curvature intervals excluding zero with the same sign under both block schemes: c = -0.2271, block-3 [-0.4339, -0.0257], block-5 [-0.4038, -0.0238]. The heterogeneous-slope HQ sensitivity is also negative under both schemes. This is an exploratory quadratic-family signal among 38 outcome-informed candidates, not an independently validated nonlinear discovery. Lack of interval support for other pooled candidates does not establish linearity or exclude opposing grid curvatures or other shapes.

At grid level, 123 of 2,736 estimable quadratic fits have both block intervals excluding zero with the same sign. All 123 retain curvature sign under leave-one-year-out (LOYO), but 35 have a maximum absolute curvature change exceeding 50% of the original magnitude, including nine exceeding 100%. Direction retention does not establish stable amplitude. February pooled PQ LOYO curvature ranges from -0.2621 to -0.1984.

The supplied LOYO files contain Q/PQ/HQ diagnostics, not L/PL diagnostics. Linear year-sensitivity has not been verified in this review. Nested Q-minus-L in-sample R² is nonnegative by construction; a positive percentile interval for that increment is not sufficient curvature evidence.

## December–January aggregation

The two frozen averages are raw-unit A = (Dec + Jan)/2, with D = (Jan - Dec)/2. MA/MAD and QA/QAD use Y/Dec/Jan complete years. MAD is algebraically equivalent to separate linear Dec and Jan coefficients. Spatial sensitivity allows grid-specific A slopes.

| Aggregate | MA→MAD ΔR² | QA→QAD ΔR² | Block-5 MAD D interval | Block-5 QAD D interval |
|---|---:|---:|---|---|
| 28–100 cm SM | 0.00045 | 0.00031 | [-0.184, +0.475] | [-0.204, +0.393] |
| Relative humidity | 0.00083 | 0.00064 | [-0.538, +0.179] | [-0.529, +0.155] |

These execution-report intervals include zero; they do not establish practical equivalence of December and January. Fixed-A contrasts require observed A–D convex-hull support, which alone does not ensure dense local support. RH is an atmospheric humidity descriptor, not a soil-water-stress indicator.

## Targets and uncertainty

The primary target remains actual-composition P50=10. Robustness refits substitute actual-composition P50=12 or P50=10 fixed composition while holding the primary weather exposure and X scaling fixed. Maximum and three-target common sample counts coincide in every supplied comparison row. Linear slope signs agree with primary in 2,831/2,888 P50=12 fits (98.0%) and 2,688/2,888 fixed-composition fits (93.1%). Quadratic signs agree in 2,650/2,736 (96.9%) and 2,446/2,736 (89.4%), respectively. These comparisons do not establish target equivalence.

The execution report records independent 50-attempt smoke checks followed by 1,000 attempts each for synchronized iid calendar years and noncircular overlapping 3-/5-year moving blocks. Roster, scaling, and anchors remain fixed within draws. Six of 19,824 full-bootstrap estimand rows have one invalid attempt, all from the same block-5 draw for pooled Dec–Jan models, leaving 999 valid estimates. Intervals with fewer than 800 valid draws are provisional. Bootstrap draws are not new independent data and do not correct candidate selection, source exposure error, or detrending uncertainty.

## Interpretation and next step

These are exploratory within-grid historical associations. No causal effects, out-of-year forecast gains, or significance-based feature additions/deletions are claimed. Common year shocks, management, soils, trends, and other weather may influence the associations. ERA5 VPD/SM/solar use shared point series within groups; NASA T/rain/RH use municipality-series area aggregation. The earlier spatial audit found distance heterogeneity; no exposure correction was applied. API 100–255 cm remains the source field name, with native ERA5 layer provenance reported as 100–289 cm.

EXP-04 is complete as reported and its supplied results have been reviewed. EXP-06 is next for design: limited time/stage representations and a separately agreed descriptive joint-weather specification. Neither a new joint model nor stage boundaries are frozen by this update. Chronological predictive evaluation belongs to EXP-07.

## Repository synchronization and validation

This directory contains the supplied candidate summary, a compact linear review derived from supplied grid estimates, and SHA-256 provenance for the reviewed files. The experiment implementation, processed panel, complete bootstrap archive, figures, and input manifests remain in the implementing Work environment and have not been synchronized here. The execution report lists 17 focused tests passing; those tests and the full experiment were not rerun in this documentation update. The existing v1.7.1 release/test checkpoint remains historical.
