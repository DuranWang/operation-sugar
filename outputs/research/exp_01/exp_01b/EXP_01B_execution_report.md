# EXP-01B Execution Report

## Status

**COMPLETED.** EXP-01B retained the municipality × year × calendar-month panel and applied contemporaneous annual observed-only harvested-area shares as observation weights. No statewide weather series was constructed. EXP-01C was not run.

## Files created or modified

- `src/analysis/exp01b_harvested_area_weighted_weather_correlation.py`
- `src/tests/analysis/test_exp01b_harvested_area_weighted_weather_correlation.py`
- validation, cross-variable, cross-month, summary, and figure artifacts under `data/processed/analysis/exp_01b_harvested_area_weighted_weather_correlation/`
- this report under `outputs/experiments/exp_01b_harvested_area_weighted_weather_correlation/`

Existing unrelated working-tree changes were preserved. NASA/ERA5 downloaders and ETL source were not modified.

## Data and variables

- Weather source: `D:\Desktop\Operation Sugar\data\processed\combined_weather\annual`; 1990–2025, 642 municipalities, 277,344 municipality-month rows, no weather missingness.
- Weight source: `D:\Desktop\Operation Sugar\data\processed\analysis\exp_01s_harvested_area_weight_stability\symbol_aware_harvested_area_1990_2025.csv`; 23,112 municipality-year rows.
- Included weather variables: `nasa_total_rainfall_mm`, `nasa_average_temperature_c`, `nasa_average_relative_humidity_pct`, `vpd_mean_kpa`, `vpd_mean_daily_max_kpa`, `soil_moisture_0_to_7cm_m3_m3`, `soil_moisture_7_to_28cm_m3_m3`, `soil_moisture_28_to_100cm_m3_m3`, `soil_moisture_100_to_255cm_m3_m3`, `solar_radiation_total_mj_m2`, `solar_radiation_mean_daily_mj_m2`.
- Canonical merge key: `ibge_code × year`; month remains part of the observation key after the merge.
- The same annual municipality weight is repeated across its 12 calendar months.

## Weighted Pearson and Spearman implementation

Weighted Pearson uses positive finite pairwise-complete observations, weighted means, weighted population covariance, and weighted population variances. Multiplying all weights by a constant leaves the coefficient unchanged.

Weighted Spearman first filters to pairwise-complete positive-weight observations, assigns ordinary average ranks (`rank(method="average")`) within the same analysis slice, and then applies the identical weighted-Pearson calculation to those ranks. Zero-weight observations cannot affect ranks or coefficients. No imputation is used.

Cross-month matrices reshape to one row per `ibge_code × year` and use that same year's annual municipality weight. Lag-1 rows use the destination observation's annual weight; a December→January pair therefore uses the January/destination year weight. Lags never cross municipalities or bridge a missing calendar month.

Reported support fields distinguish raw observed rows, positive-weight rows, zero-weight rows, weight sum, and Kish effective sample size `(sum w)^2 / sum(w^2)`.

## Merge and weighting validation

- Weather-area municipality-year keys: exact match; no weather-only or area-only keys.
- Panel rows after merge: 277,344; observation structure preserved.
- Positive-area municipality-years: 16,570; explicit/numeric-zero municipality-years: 5,099; unavailable municipality-years: 1,443.
- `-` remains explicit zero with analysis weight 0; `...` remains unavailable with missing analysis weight.
- Annual weight sums: 1.000000000000–1.000000000000; every month-year slice also sums to one.
- Positive stored EXP-01S weights agree with reconstructed weights within `1e-12`.
- Annual Kish effective sample size range: 113.4–233.0 municipalities.
- Every month-specific pair has 21,669 observed-weight rows, 16,570 positive-weight rows, 5,099 zero-weight rows, total weight 36, and Kish effective n 6,138.7; the 1,443 unavailable municipality-years are excluded.
- Every pooled same-month-variable pair has 260,028 observed-weight municipality-month rows, 198,840 positive-weight rows, 61,188 zero-weight rows, total weight 432, and Kish effective n 73,664.9.
- Three IBGE codes have municipality-name spelling/encoding differences across inputs; exact canonical codes match, so these are non-blocking metadata differences recorded in `municipality_name_mismatches.csv`.

The raw 642-municipality panel is retained. Unavailable weights are excluded from weighted coefficients rather than converted to zero; explicit zeros remain in validation counts but have no statistical contribution. Consequently, a later EXP-01C comparison must remember that the observed-only weighted view combines unequal weights with the approved exclusion of unavailable-area municipality-years.

## Main EXP-01B results

### Core month-specific relationships

- `nasa_total_rainfall_mm ↔ vpd_mean_kpa`: mean monthly weighted Pearson -0.561 (range -0.717 to -0.432); mean weighted Spearman -0.620.
- `nasa_total_rainfall_mm ↔ soil_moisture_0_to_7cm_m3_m3`: mean monthly weighted Pearson 0.411 (range 0.333 to 0.482); mean weighted Spearman 0.436.
- `nasa_average_temperature_c ↔ vpd_mean_kpa`: mean monthly weighted Pearson 0.694 (range 0.534 to 0.859); mean weighted Spearman 0.676.
- `nasa_average_temperature_c ↔ soil_moisture_0_to_7cm_m3_m3`: mean monthly weighted Pearson -0.508 (range -0.651 to -0.341); mean weighted Spearman -0.497.
- `nasa_average_temperature_c ↔ solar_radiation_mean_daily_mj_m2`: mean monthly weighted Pearson 0.451 (range 0.238 to 0.678); mean weighted Spearman 0.442.

### Weighted lag-1 persistence

- `nasa_total_rainfall_mm`: weighted Pearson 0.553; weighted Spearman 0.617; effective n 73572.8.
- `nasa_average_temperature_c`: weighted Pearson 0.783; weighted Spearman 0.783; effective n 73572.8.
- `vpd_mean_kpa`: weighted Pearson 0.632; weighted Spearman 0.645; effective n 73572.8.
- `soil_moisture_0_to_7cm_m3_m3`: weighted Pearson 0.829; weighted Spearman 0.819; effective n 73572.8.

### Weighted cross-month persistence

- `nasa_total_rainfall_mm`: adjacent / 3-month / 6-month weighted Pearson = 0.132 / -0.012 / 0.066.
- `nasa_average_temperature_c`: adjacent / 3-month / 6-month weighted Pearson = 0.755 / 0.601 / 0.490.
- `vpd_mean_kpa`: adjacent / 3-month / 6-month weighted Pearson = 0.596 / 0.449 / 0.350.
- `soil_moisture_0_to_7cm_m3_m3`: adjacent / 3-month / 6-month weighted Pearson = 0.823 / 0.727 / 0.727.
- `solar_radiation_mean_daily_mj_m2`: adjacent / 3-month / 6-month weighted Pearson = 0.248 / 0.138 / 0.115.

Calendar-month-specific results remain primary. Pooled weighted matrices are secondary because seasonal mixing can still distort signs and magnitudes.

## Tests and commands

- Focused EXP-01B tests: **14 passed**.
- Combined EXP-01B, EXP-01A, and related weather tests: **37 passed**.
- Full repository test suite: **211 passed, 3 pre-existing warnings**.
- Main command: `py -3 -m analysis.exp01b_harvested_area_weighted_weather_correlation --project-root <repository>` with `PYTHONPATH=src`.

## Main output files

- `validation/weight_merge_validation.csv`
- `validation/municipality_name_mismatches.csv`
- `cross variable/weighted_pooled_pearson_correlation.csv`
- `cross variable/weighted_pooled_spearman_correlation.csv`
- `cross variable/weighted_monthly_pair_correlations.csv`
- `summary/weighted_core_pair_monthly_correlations.csv`
- `summary/weighted_pearson_spearman_divergence.csv`
- `summary/weighted_lag1_persistence_overall.csv`
- `summary/weighted_lag1_persistence_by_month.csv`
- `summary/weighted_cross_month_dependence_summary.csv`
- `cross month/` 12×12 matrices and support diagnostics for five variables
- `figures/` pooled, core-pair, lag-1, and cross-month heatmaps

## Warnings and interpretation limits

- These are historical descriptive weights; finalized contemporaneous target-year area weights are not automatically forecast-safe.
- The 1,443 unavailable municipality-years remain unavailable, not zero.
- Zero-weight municipalities do not influence weighted coefficients or weighted ranks.
- Weighted correlations do not prove causality, predictive redundancy, or that weighting improves yield prediction.
- No feature keep/drop decision was made, and EXP-01C was not executed.
