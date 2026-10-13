# EXP-05 conditional temperature–VPD synthesis

Exploratory grid/month-slot associations, not causal effects or forecasting feature selection.

## Main distribution

The primary estimand is the equal-grid median of per-grid two-sided partial correlations. Intervals below resample yield-year labels synchronously across grids in consecutive 3-year blocks (200 replicates).

| Slot | VPD\|T median [3-year interval] | T\|VPD median [3-year interval] | N primary grids |
|---|---:|---:|---:|
| Jan_(t-1) | 0.058 [-0.031, 0.115] | -0.049 [-0.163, 0.089] | 76 |
| Feb_(t-1) | 0.042 [-0.011, 0.124] | -0.049 [-0.103, 0.024] | 76 |
| Mar_(t-1) | 0.004 [-0.088, 0.098] | -0.004 [-0.061, 0.074] | 76 |
| Apr_(t-1) | 0.032 [-0.055, 0.123] | 0.017 [-0.090, 0.181] | 76 |
| May_(t-1) | -0.050 [-0.141, 0.025] | 0.021 [-0.046, 0.112] | 76 |
| Jun_(t-1) | -0.032 [-0.140, 0.073] | 0.024 [-0.112, 0.191] | 76 |
| Jul_(t-1) | -0.020 [-0.122, 0.051] | 0.082 [-0.030, 0.220] | 76 |
| Aug_(t-1) | -0.104 [-0.193, -0.029] | 0.062 [-0.013, 0.174] | 76 |
| Sep_(t-1) | -0.099 [-0.167, -0.009] | 0.027 [-0.058, 0.105] | 76 |
| Oct_(t-1) | -0.081 [-0.158, -0.013] | 0.029 [-0.043, 0.154] | 76 |
| Nov_(t-1) | -0.105 [-0.190, -0.002] | 0.030 [-0.036, 0.102] | 76 |
| Dec_(t-1) | -0.029 [-0.092, 0.046] | -0.087 [-0.169, -0.019] | 76 |
| Jan_(t) | -0.043 [-0.151, 0.089] | -0.055 [-0.160, 0.027] | 76 |
| Feb_(t) | -0.080 [-0.167, 0.059] | -0.005 [-0.096, 0.056] | 76 |
| Mar_(t) | 0.053 [-0.023, 0.149] | -0.071 [-0.190, -0.014] | 76 |
| Apr_(t) | -0.056 [-0.122, 0.078] | -0.047 [-0.210, 0.061] | 76 |

## Empirical reading

The clearest sustained conditional pattern is negative VPD|T over Aug–Nov_(t-1): equal-grid median partial correlations are approximately −0.10, −0.10, −0.08, and −0.11. The synchronized 3-year and 5-year block intervals for those spatial medians remain below zero, though individual grid directions vary. The February_t pilot median VPD|T is −0.08, but its block interval crosses zero. Temperature|VPD is weaker and changes sign across month-slots; Dec_(t-1) and Mar_t have negative medians with 3-year intervals below zero. These are descriptive signals, not isolated-month discoveries.

P50=12 and fixed-composition targets use the exact same paired-year support as primary in this run (zero rows lost). The Aug–Nov VPD|T medians retain their negative signs under both targets. The all-16-slot common-year sensitivity loses at most one year per grid-slot and preserves the broad pattern. Restricted per-grid quadratic conditioning generally leaves the Aug–Nov median VPD increment similar to its linear-control increment; pooled grid-intercept quadratic/interaction increments are small and are not evidence that all grids share one curvature.

Spatial heterogeneity and influence remain material: rank-partial signs agree with linear-partial signs for about 82% of N≥20 grid-slot-directions, while leave-one-year-out signs remain stable for about 59%. Do not equate a spatial median with a common response in every grid. February has no robust spatial-median direction after year-block uncertainty.

## Interpretation boundaries

Direction, magnitude, grid heterogeneity, rank robustness, target robustness, nonlinear controls, and common-year sensitivity are tabulated separately. The fixed-composition outcome tests yield weighting, not weather weighting. The grid-intercept pooled quadratic models impose common slopes and do not prove a common grid response. A year-synchronized bootstrap preserves common resampled calendar-year shocks but does not remove spatial dependence or establish causality.

No potential-redundancy label or feature keep/drop recommendation is made: no a priori smallest-important-effect margin exists. Directionally consistent candidates remain exploratory and their substantive importance is unadjudicated. See per-grid evidence flags and execution report for caveats.
