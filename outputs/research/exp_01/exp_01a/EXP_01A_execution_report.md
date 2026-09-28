# EXP-01A execution report

## Status

**COMPLETED.** The mandatory validation gate passed on the authoritative combined-weather CSVs, and EXP-01A was executed through correlation, divergence, ranking, lag-1 persistence, figures, and verification. EXP-01B and EXP-01C were not run.

## Data validation

- Exact analysis source: `D:\Desktop\Operation Sugar\data\processed\combined_weather\annual` (`sp_municipality_monthly_weather_YYYY.csv`).
- Years analyzed: 1990–2025 inclusive (36 years).
- Observation unit and validated key: `ibge_code × calendar year × calendar month`.
- Coverage: 277,344 rows; 642 municipalities, 7,704 rows, and 12 calendar months in every year; no entering/leaving municipalities, missing municipality-month keys, or duplicate keys.
- Missingness: zero missing observations in every included weather variable, overall, by year, and by calendar month.
- Merge integrity: all 277,344 rows contain both NASA POWER basic data and Open-Meteo/ERA5 advanced data; zero basic-only, advanced-only, or neither-source rows.
- Municipality mapping: stable canonical seven-digit IBGE codes; 87 shared NASA weather groups and 83 sampled ERA5 grid points are retained as metadata, not analyzed as weather variables.
- Exact included variables: `nasa_total_rainfall_mm`, `nasa_average_temperature_c`, `nasa_average_relative_humidity_pct`, `vpd_mean_kpa`, `vpd_mean_daily_max_kpa`, `soil_moisture_0_to_7cm_m3_m3`, `soil_moisture_7_to_28cm_m3_m3`, `soil_moisture_28_to_100cm_m3_m3`, `soil_moisture_100_to_255cm_m3_m3`, `solar_radiation_total_mj_m2`, `solar_radiation_mean_daily_mj_m2`.
- Excluded metadata/QA fields: `municipality`, `ibge_code`, `month`, `year`, `calendar_month`, `date`, `nasa_weather_group_id`, `era5_grid_id`, `nasa_observed_days`, and `era5_observed_days`.
- Units, source, and code-verified aggregation definitions are recorded in `weather_variable_inventory.csv`. Separate VPD definitions, four soil depths, and monthly-total versus mean-daily radiation were preserved; no arbitrary averaging or unit conversion was applied.
- The official 2009 validation artifact was regenerated from `data/raw/nasa_power/daily_weather/SP/20090101_20091231.csv`: 365 dates, 234,330 valid NASA daily rows, 7,704 combined monthly rows, zero missing source rows, and a value-for-value match to the repaired annual CSV within pipeline tolerance (`pilot_comparison: passed`).

## Methods

- Pearson correlation describes linear association; Spearman correlation is Pearson correlation of within-pair ranks and describes monotonic association.
- Each coefficient uses pairwise-complete observations and carries its own `n`. No weather value was imputed or replaced with zero.
- Pooled matrices use every valid municipality-year-month row and may reflect the common seasonal cycle.
- Month-specific correlations use only municipality-year observations from the same calendar month across 1990–2025.
- Pearson–Spearman divergence is `|Spearman rho - Pearson r|` for each unordered pair and calendar month.
- Lag-1 values were created within IBGE municipality only when the prior record was exactly one calendar month earlier. December→January is allowed; missing months are never bridged.
- No significance tests, p-values, nonlinear models, yield data, harvested-area weights, or feature-selection thresholds were used.

## Results

### Strongest pooled basic/advanced overlap

- Pearson: `nasa_average_relative_humidity_pct ↔ vpd_mean_kpa` = -0.854 (n=277,344).
- Pearson: `nasa_average_relative_humidity_pct ↔ vpd_mean_daily_max_kpa` = -0.843 (n=277,344).
- Pearson: `nasa_average_temperature_c ↔ solar_radiation_mean_daily_mj_m2` = 0.790 (n=277,344).
- Pearson: `nasa_average_temperature_c ↔ solar_radiation_total_mj_m2` = 0.778 (n=277,344).
- Pearson: `nasa_average_relative_humidity_pct ↔ soil_moisture_0_to_7cm_m3_m3` = 0.649 (n=277,344).
- Spearman: `nasa_average_relative_humidity_pct ↔ vpd_mean_kpa` = -0.813 (n=277,344).
- Spearman: `nasa_average_relative_humidity_pct ↔ vpd_mean_daily_max_kpa` = -0.805 (n=277,344).
- Spearman: `nasa_average_temperature_c ↔ solar_radiation_mean_daily_mj_m2` = 0.788 (n=277,344).
- Spearman: `nasa_average_temperature_c ↔ solar_radiation_total_mj_m2` = 0.776 (n=277,344).
- Spearman: `nasa_average_relative_humidity_pct ↔ soil_moisture_7_to_28cm_m3_m3` = 0.667 (n=277,344).

These pooled results are descriptive and partly reflect the annual seasonal cycle. Month-specific results below are primary.

### Core relationships by calendar month

- `nasa_total_rainfall_mm ↔ vpd_mean_kpa`: weakest absolute Pearson in month 9 (r=-0.283, n=23,112); strongest in month 2 (r=-0.639, n=23,112).
- `nasa_total_rainfall_mm ↔ soil_moisture_0_to_7cm_m3_m3`: weakest absolute Pearson in month 9 (r=0.251, n=23,112); strongest in month 10 (r=0.484, n=23,112).
- `nasa_average_temperature_c ↔ vpd_mean_kpa`: weakest absolute Pearson in month 2 (r=0.548, n=23,112); strongest in month 9 (r=0.879, n=23,112).
- `nasa_average_temperature_c ↔ soil_moisture_0_to_7cm_m3_m3`: weakest absolute Pearson in month 5 (r=-0.449, n=23,112); strongest in month 10 (r=-0.677, n=23,112).
- `nasa_average_temperature_c ↔ solar_radiation_mean_daily_mj_m2`: weakest absolute Pearson in month 2 (r=0.348, n=23,112); strongest in month 9 (r=0.728, n=23,112).

- Temperature ↔ mean VPD is positive in every month, with Pearson r ranging from 0.548 to 0.879; it is consistently related but not interchangeable.
- Precipitation ↔ surface soil moisture is positive in every month, ranging from 0.251 to 0.484, with clear seasonal strength variation.
- Mean-daily solar radiation ↔ temperature ranges from 0.348 to 0.728; radiation retains visibly distinct within-month variation.

### Largest Pearson–Spearman divergences

- Month 9, `nasa_total_rainfall_mm ↔ solar_radiation_mean_daily_mj_m2`: Pearson=-0.304, Spearman=-0.778, |difference|=0.474.
- Month 9, `nasa_total_rainfall_mm ↔ solar_radiation_total_mj_m2`: Pearson=-0.304, Spearman=-0.778, |difference|=0.474.
- Month 9, `nasa_total_rainfall_mm ↔ vpd_mean_daily_max_kpa`: Pearson=-0.292, Spearman=-0.661, |difference|=0.369.
- Month 9, `nasa_total_rainfall_mm ↔ vpd_mean_kpa`: Pearson=-0.283, Spearman=-0.631, |difference|=0.348.
- Month 9, `nasa_total_rainfall_mm ↔ nasa_average_relative_humidity_pct`: Pearson=0.340, Spearman=0.666, |difference|=0.326.
- Month 9, `nasa_total_rainfall_mm ↔ soil_moisture_0_to_7cm_m3_m3`: Pearson=0.251, Spearman=0.567, |difference|=0.316.
- Month 9, `nasa_total_rainfall_mm ↔ soil_moisture_7_to_28cm_m3_m3`: Pearson=0.229, Spearman=0.486, |difference|=0.257.
- Month 9, `nasa_total_rainfall_mm ↔ nasa_average_temperature_c`: Pearson=-0.273, Spearman=-0.459, |difference|=0.186.
- Month 9, `nasa_total_rainfall_mm ↔ soil_moisture_28_to_100cm_m3_m3`: Pearson=0.157, Spearman=0.296, |difference|=0.138.
- Month 6, `nasa_total_rainfall_mm ↔ nasa_average_temperature_c`: Pearson=-0.320, Spearman=-0.452, |difference|=0.133.

These differences flag nonlinearity, rank structure, or influential extremes; EXP-01A does not fit nonlinear models.

### Lag-1 persistence

- `soil_moisture_0_to_7cm_m3_m3`: overall Pearson=0.842 and Spearman=0.835 (n=276,702); destination-month Pearson range 0.791 (month 10) to 0.877 (month 1).
- `nasa_average_temperature_c`: overall Pearson=0.826 and Spearman=0.826 (n=276,702); destination-month Pearson range 0.769 (month 7) to 0.891 (month 4).
- `vpd_mean_kpa`: overall Pearson=0.720 and Spearman=0.757 (n=276,702); destination-month Pearson range 0.516 (month 2) to 0.834 (month 6).
- `nasa_total_rainfall_mm`: overall Pearson=0.471 and Spearman=0.586 (n=276,702); destination-month Pearson range -0.038 (month 10) to 0.416 (month 1).

### Full cross-month temporal dependence

Each matrix compares the same variable in two calendar months after reshaping to one row per `ibge_code × year`. All 12×12 Pearson and Spearman matrices and their pairwise-count matrices use exact year alignment; no lag bridging or imputation occurs.

- `soil_moisture_0_to_7cm_m3_m3`: mean adjacent-month Pearson=0.844, three-month=0.749, and six-month=0.740; corresponding Spearman values are 0.837, 0.745, and 0.738 (pairwise n=23,112–23,112).
- `nasa_average_temperature_c`: mean adjacent-month Pearson=0.839, three-month=0.741, and six-month=0.673; corresponding Spearman values are 0.834, 0.738, and 0.679 (pairwise n=23,112–23,112).
- `vpd_mean_kpa`: mean adjacent-month Pearson=0.725, three-month=0.623, and six-month=0.545; corresponding Spearman values are 0.739, 0.662, and 0.591 (pairwise n=23,112–23,112).
- `solar_radiation_mean_daily_mj_m2`: mean adjacent-month Pearson=0.425, three-month=0.364, and six-month=0.316; corresponding Spearman values are 0.396, 0.334, and 0.311 (pairwise n=23,112–23,112).
- `nasa_total_rainfall_mm`: mean adjacent-month Pearson=0.140, three-month=0.026, and six-month=0.074; corresponding Spearman values are 0.164, 0.038, and 0.106 (pairwise n=23,112–23,112).

On a relative, descriptive basis, `soil_moisture_0_to_7cm_m3_m3`, `nasa_average_temperature_c` retain the strongest six-month dependence, while `solar_radiation_mean_daily_mj_m2`, `nasa_total_rainfall_mm` are the most short-lived of the five variables. This ranking describes temporal dependence only and is not a feature-selection rule.

### Pooled versus month-specific relationships

The following pairs have the largest gaps between pooled Pearson correlation and at least one calendar-month estimate:

- `nasa_total_rainfall_mm ↔ solar_radiation_mean_daily_mj_m2`: pooled r=0.244 versus month 2 r=-0.747 (absolute gap=0.990).
- `nasa_total_rainfall_mm ↔ solar_radiation_total_mj_m2`: pooled r=0.236 versus month 2 r=-0.747 (absolute gap=0.983).
- `nasa_total_rainfall_mm ↔ nasa_average_temperature_c`: pooled r=0.317 versus month 1 r=-0.410 (absolute gap=0.727).
- `soil_moisture_0_to_7cm_m3_m3 ↔ solar_radiation_mean_daily_mj_m2`: pooled r=-0.008 versus month 9 r=-0.732 (absolute gap=0.724).
- `soil_moisture_0_to_7cm_m3_m3 ↔ solar_radiation_total_mj_m2`: pooled r=-0.024 versus month 9 r=-0.732 (absolute gap=0.708).

Accordingly, pooled correlations should not be used alone to characterize weather-feature overlap.

## Answers for the next research step

1. The strongest observed cross-source overlaps are listed above; exact complete rankings are in `strongest_correlation_pairs.csv`.
2. The most month-dependent relationships are identified by the pooled/month gaps and the complete monthly table.
3. Temperature and mean VPD are positively related in every month, but the strength varies and does not establish redundancy.
4. Surface soil moisture is positively associated with precipitation in every month, with seasonal variation shown above.
5. Solar radiation tracks temperature only partially within months and retains distinct variation.
6. The lag table above ranks persistence across precipitation, temperature, VPD, and surface soil moisture.
7. Several pooled relationships differ materially from individual-month estimates; the listed largest gaps are the clearest examples.
8. No analyzed-CSV coverage, missingness, key, source-merge, or validation-artifact issue blocks EXP-01B.
9. EXP-01B should carry forward the same 11 included variables, unchanged, so weighted and unweighted results remain directly comparable.

## Interpretation limits

- Predictor correlation does not prove predictive redundancy or causation.
- Low correlation does not prove incremental yield-prediction value.
- EXP-01A does not select final yield-model features.
- Rows share 87 NASA weather groups and 83 sampled ERA5 grid points, so they are not independent spatial observations; no classical p-values or significance stars are reported.
- EXP-01B and EXP-01C are still required before deciding how crop-area weighting changes the picture.

## Engineering verification

- Created/modified: `src/analysis/exp01a_municipality_weather_correlation.py`, `src/tests/analysis/test_exp01a_municipality_weather_correlation.py`, the refreshed 2009 validation JSON, four validation CSVs, seven original correlation/persistence CSVs, sixteen cross-month CSVs, fifteen figures, and this report.
- Focused EXP-01A tests: **16 passed**.
- Related combined-weather ETL tests: **7 passed**.
- Full repository suite: **197 passed, 3 pre-existing warnings**.
- 2009 independent rebuild/pilot comparison: **passed** with 7,704 matched keys and no differing values within `1e-12` absolute/relative tolerance.
- Upstream downloader and ETL source code was not modified. Existing unrelated working-tree changes were preserved.
