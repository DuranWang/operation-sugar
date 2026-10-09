# EXP-03 Checkpoint 1 — Extended 1982–2025 Rerun

## Scope and exact inputs

- EXP-02 grid residuals: `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\actual_vs_fixed_grid_residuals.csv`.
- Exact outcome: valid `p50_10` rows, residual column **`actual_grid_residual_tch`**.
- Exact EXP-02 support/weights: `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\matched_support_weight_details.csv`; target-year `actual_weight` is unchanged.
- Canonical municipality-month weather: `D:\Desktop\Operation Sugar\data\processed\combined_weather\annual`, extended and validated for 1981–2025.
- Weather columns: `nasa_total_rainfall_mm`, `nasa_average_temperature_c`, `nasa_average_relative_humidity_pct`, `vpd_mean_kpa`, `vpd_mean_daily_max_kpa`, `soil_moisture_0_to_7cm_m3_m3`, `soil_moisture_7_to_28cm_m3_m3`, `soil_moisture_28_to_100cm_m3_m3`, `soil_moisture_100_to_255cm_m3_m3`, `solar_radiation_total_mj_m2`, `solar_radiation_mean_daily_mj_m2`.

These are annual harvested-area weights from EXP-02, not monthly harvest shares. No harvest calendar, interpolation, or monthly harvest weighting was constructed.

## Outcome, alignment, and grouping

- Full residual sample: **3773** grid-years, **78** grids, yield years **1974–2025**.
- Complete-window analysis: **3267** grid-years and **52272** aligned rows.
- Earliest scientifically valid all-variable yield year: **1982**.
- Extended window remains `m_-15` Jan_(t-1) through `m_0` Apr_t; primary remains `m_-11` May_(t-1) through `m_0` Apr_t.
- Partial within-month actual-weight coverage issues: **0**.

| yield_group | grid_year_observations | unique_grids | unique_years | minimum_residual | median_residual | maximum_residual |
|---|---|---|---|---|---|---|
| Low | 948 | 78 | 52 | -48.8381 | -4.2887 | -0.6387 |
| Medium | 1877 | 78 | 52 | -6.0880 | 0.0313 | 5.6917 |
| High | 948 | 78 | 52 | 0.6029 | 4.1266 | 44.6848 |

Grouping uses average within-grid ranks over the full residual history before weather availability. Rows in exact within-grid residual ties: **0**. Complete-weather group counts are:

| yield_group | complete_grid_years |
|---|---|
| High | 809 |
| Low | 769 |
| Medium | 1689 |

## Temporal source-coverage gate

| weather_variable | source | earliest_available_month | latest_available_month | n_missing_calendar_months | missing_municipality_month_rows | mapped_municipalities | sufficient_for_complete_1982_window |
|---|---|---|---|---|---|---|---|
| nasa_total_rainfall_mm | NASA POWER | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| nasa_average_temperature_c | NASA POWER | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| nasa_average_relative_humidity_pct | NASA POWER | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| vpd_mean_kpa | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| vpd_mean_daily_max_kpa | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| soil_moisture_0_to_7cm_m3_m3 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| soil_moisture_7_to_28cm_m3_m3 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| soil_moisture_28_to_100cm_m3_m3 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| soil_moisture_100_to_255cm_m3_m3 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| solar_radiation_total_mj_m2 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |
| solar_radiation_mean_daily_mj_m2 | ERA5 | 1981-01 | 2025-12 | 0 | 0 | 642 | True |

For every year 1981–1989, the canonical panel contains 7,704 rows, 642 municipalities, 12 months, no duplicate keys, no missing NASA or ERA5 source rows, and no missing required-variable values. The complete year-by-year audit is `annual_source_coverage_1981_2025.csv`.

Grid-year window coverage over the full residual history is:

| window_status | grid_year_observations | first_yield_year | last_yield_year |
|---|---|---|---|
| complete_16_months | 3267 | 1982 | 2025 |
| missing_window | 437 | 1974 | 1980 |
| partial_window | 69 | 1981 | 1981 |

## Spatial reconciliation gate

| Diagnostic | Value |
|---|---:|
| Eligible EXP-02 municipalities | 511 |
| Represented ERA5 grids | 78 |
| NASA weather groups | 76 |
| NASA groups spanning multiple ERA5 grids | 49 |
| Duplicate municipality-month keys | 0 |
| All valid grid-year weight sums equal one | True |
| Residual and weight-detail support identical | True |
| NASA and ERA5 municipality-month support identical | True |

NASA is attached at municipality-month level through `nasa_weather_group_id`; ERA5 is attached through `era5_grid_id`; sources merge on municipality plus month before ERA5-grid aggregation. NASA groups spanning multiple ERA5 grids are expected bridge behavior, not a direct grid join. All **78** grid audit rows have no mapping anomaly.

## Strongest preliminary coherent three-month patterns

| weather_variable | start_relative_month | end_relative_month | window_in_primary | direction | mean_standardized_high_minus_low | mean_absolute_standardized_effect | minimum_absolute_standardized_effect |
|---|---|---|---|---|---|---|---|
| nasa_average_relative_humidity_pct | m_-4 | m_-2 | True | positive | 0.4453 | 0.4453 | 0.4216 |
| nasa_average_relative_humidity_pct | m_-3 | m_-1 | True | positive | 0.3922 | 0.3922 | 0.3297 |
| nasa_average_relative_humidity_pct | m_-5 | m_-3 | True | positive | 0.3911 | 0.3911 | 0.2591 |
| nasa_average_relative_humidity_pct | m_-2 | m_0 | True | positive | 0.3818 | 0.3818 | 0.3297 |
| nasa_average_relative_humidity_pct | m_-6 | m_-4 | True | positive | 0.3224 | 0.3224 | 0.2195 |
| soil_moisture_7_to_28cm_m3_m3 | m_-4 | m_-2 | True | positive | 0.2988 | 0.2988 | 0.2701 |
| soil_moisture_0_to_7cm_m3_m3 | m_-4 | m_-2 | True | positive | 0.2919 | 0.2919 | 0.2689 |
| soil_moisture_28_to_100cm_m3_m3 | m_-4 | m_-2 | True | positive | 0.2914 | 0.2914 | 0.2666 |
| soil_moisture_28_to_100cm_m3_m3 | m_-3 | m_-1 | True | positive | 0.2892 | 0.2892 | 0.2601 |
| vpd_mean_kpa | m_-4 | m_-2 | True | negative | -0.2758 | 0.2758 | 0.2382 |
| vpd_mean_kpa | m_-5 | m_-3 | True | negative | -0.2739 | 0.2739 | 0.2323 |
| nasa_average_temperature_c | m_-4 | m_-2 | True | negative | -0.2623 | 0.2623 | 0.1702 |

These are descriptive adjacent-month contrasts, not constructed features, formal hypothesis tests, biological stage labels, or selection decisions. The Spearman companion remains supporting evidence only.

## Comparison with the former 1991–2025 checkpoint

- Correlation across the 176 old and new standardized High-minus-Low cells: **0.9432**.
- Sign reversals across all cells: **11**; within `m_-4` through `m_0`: **2**.
- Largest absolute standardized-effect change: **0.1937**, `nasa_average_temperature_c` at `m_-10`.

The late-`t-1` / early-`t` exploratory pattern remains visible: higher-yield observations are comparatively more humid and soil-moist, with lower temperature and VPD across adjacent months. Individual magnitudes changed after adding 1982–1990, so no month or window is treated as finalized.

## Stop boundary

No final features, seasonal collapse, biological labels, predictive model, optimized weights, harvest-share weights, or reconstructed harvest profiles were produced. This remains Checkpoint 1 only.
