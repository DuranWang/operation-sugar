# EXP-04 — Continuous Weather–Yield Response Characterization

## Scope and sample

The frozen 38 candidates were analyzed separately, one X at a time, on 78 mapped ERA5 groups. Primary outcome is actual-composition P50=10 grid residual (t/ha), verified against municipality residuals. Candidate-specific paired weather spans 1981–2025 for Jan–Apr and 1982–2025 for Dec or Dec–Jan. No complete-window requirement was applied.
Linear fits: 2,888/2,964 candidate-grid rows (N≥20); restricted Q fits: 2,736/2,964 (N≥30, ≥10 distinct X, rank and conditioning). Two grids per candidate lack the linear threshold; four more per candidate lack the Q N/unique-X gate. These remain unresolved rather than classified as linear.

## Grid-level direction and magnitude

The CSVs report raw-unit slopes, a fixed familiar-unit increment, and each grid's observed IQR contrast. Direction varies across grids; no cross-variable effect-size ranking is inferred from these marginal models.

| Candidate family | Typical linear direction across the five-month window | Range of positive-grid counts (of 76) | Median grid IQR contrast range (t/ha) |
|---|---|---:|---:|
| rainfall_input | positive majority in every slot | 44–60 | +0.236 to +0.608 |
| temperature | negative majority in every slot | 11–27 | -0.591 to -0.245 |
| relative_humidity | positive majority in every slot | 63–66 | +0.328 to +0.789 |
| mean_vpd | negative majority in every slot | 15–31 | -0.540 to -0.134 |
| upper_soil_moisture | positive majority in every slot | 53–62 | +0.410 to +0.671 |
| deep_soil_moisture_28_100 | positive majority in every slot | 57–60 | +0.523 to +0.782 |
| deep_soil_moisture_100_255 | positive majority in every slot | 54–61 | +0.222 to +0.544 |
| solar_energy | negative majority in every slot | 15–34 | -0.680 to -0.039 |

## Restricted quadratic shape and spatial differences

Equal-grid pooled PQ curvature has block-3 and block-5 pointwise intervals both on the same side of zero for 1/38 candidates: rainfall_input__m_-2. This is evidence only within the prespecified quadratic family; 38 exploratory comparisons and shared year shocks preclude a discovery claim.
At grid level, both block intervals exclude zero for 123 of 2736 estimable Q fits. Candidate-specific counts and tail/LOYO diagnostics are in `candidate_response_summary.csv` and the detailed tables. A pooled curve can mask opposing grid curvatures; compare PL/PQ with HL/HQ on the same fixed 72-grid Q roster.
Nested Q−L in-sample R² is nonnegative by construction; its percentile bootstrap interval excluding zero is not evidence of meaningful curvature. Read c, local contrasts, tail support and year sensitivity together.

## December–January aggregation checks

The two frozen averages use A=(Dec+Jan)/2 in raw units, with D=(Jan−Dec)/2. Each ladder uses Y/Dec/Jan complete years. MAD is algebraically equivalent to separate linear Dec and Jan coefficients. QA/QAD checks whether A curvature changes the D diagnostic; the spatial sensitivity allows grid-specific A slopes.

| Aggregate | Pooled MA→MAD ΔR² | QA→QAD ΔR² | Block-5 MAD D coefficient CI | Block-5 QAD D coefficient CI |
|---|---:|---:|---:|---:|
| deep_soil_moisture_28_100__dec_jan | 0.00045 | 0.00031 | [-0.184, +0.475] | [-0.204, +0.393] |
| relative_humidity__dec_jan | 0.00083 | 0.00064 | [-0.538, +0.179] | [-0.529, +0.155] |

All four listed D intervals overlap zero. This does not establish practical equivalence of December and January. Fixed-A D contrasts use only grid pairs whose two proposed points lie in the observed A–D convex hull; hull inclusion does not guarantee dense local support. The observed joint-support figures should be inspected before substantive interpretation.

## Robustness and limits

The P50=12 actual and P50=10 fixed-composition targets were refit on both maximum and three-target common support, with primary weather exposure and primary X scaling fixed. Paired target intervals, synchronized-calendar LOYO rows, and 1,000-draw iid/block3/block5 intervals appear in the companion tables. All primary pooled bootstrap rosters remain fixed across draws; failures and provisional intervals are recorded separately.
All response curves describe historical within-grid associations. The models omit management, soils, year trends and other weather controls. They do not isolate causal effects or establish out-of-year forecasting value. ERA5 VPD/soil moisture/solar are shared point series within grid; NASA T/rain/RH follow municipality-series area aggregation. The prior spatial sampling audit found distance heterogeneity, but no exposure correction is made here. API 100–255 cm is retained as the source field name; its native ERA5 layer provenance is 100–289 cm.
No feature is recommended for deletion or addition on a significance rule. The EXP-03 candidate universe and EXP-02 target definitions remain frozen.
