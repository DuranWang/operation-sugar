# EXP-03 Step 5 redundancy synthesis

## Scope and validation

This report formalizes the frozen Step-5 representation and temporal decisions. Adjacent-month correlations use exactly matched crop years within ERA5 grid and require at least 15 paired years. All **32 variable-pair summaries use 76 grids**. Existing yield and spatial summaries are read only; no candidate feature is constructed or optimized against yield.

## Approved representation reductions

| conceptual_family | canonical_variable | archived_robustness_variable | decision_basis |
| --- | --- | --- | --- |
| solar_energy | solar_radiation_mean_daily_mj_m2 | solar_radiation_total_mj_m2 | representation duplicate; mean-daily avoids month-length scaling |
| vpd | vpd_mean_kpa | vpd_mean_daily_max_kpa | near-duplicate predictor and yield behavior; not a temperature-VPD decision |
| upper_soil_moisture | soil_moisture_0_to_7cm_m3_m3 | soil_moisture_7_to_28cm_m3_m3 | one upper-state family; 0-7 cm preserves EXP-01 and March-audit continuity |

## Adjacent-month predictor redundancy

| conceptual_variable | month_pair | usable_grids | median_grid_spearman | q25_grid_spearman | q75_grid_spearman | modal_direction | modal_direction_fraction | pooled_within_grid_rank_rho |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rainfall_input | Dec-Jan | 76 | 0.3634 | 0.2945 | 0.4551 | positive | 0.9868 | 0.3839 |
| rainfall_input | Jan-Feb | 76 | 0.1293 | 0.0348 | 0.1719 | positive | 0.8026 | 0.1430 |
| rainfall_input | Feb-Mar | 76 | 0.3231 | 0.2462 | 0.3783 | positive | 0.9868 | 0.3247 |
| rainfall_input | Mar-Apr | 76 | 0.2382 | 0.1818 | 0.2812 | positive | 1.0000 | 0.2537 |
| temperature | Dec-Jan | 76 | 0.3999 | 0.3400 | 0.4678 | positive | 1.0000 | 0.4182 |
| temperature | Jan-Feb | 76 | 0.4092 | 0.3755 | 0.4731 | positive | 1.0000 | 0.4325 |
| temperature | Feb-Mar | 76 | 0.4517 | 0.3762 | 0.5316 | positive | 0.9868 | 0.4680 |
| temperature | Mar-Apr | 76 | 0.5935 | 0.5357 | 0.6633 | positive | 1.0000 | 0.6069 |
| relative_humidity | Dec-Jan | 76 | 0.4814 | 0.4403 | 0.5297 | positive | 1.0000 | 0.4978 |
| relative_humidity | Jan-Feb | 76 | 0.4984 | 0.3885 | 0.5486 | positive | 1.0000 | 0.4902 |
| relative_humidity | Feb-Mar | 76 | 0.5167 | 0.4450 | 0.5637 | positive | 1.0000 | 0.5241 |
| relative_humidity | Mar-Apr | 76 | 0.6304 | 0.5646 | 0.6647 | positive | 1.0000 | 0.6366 |
| mean_vpd | Dec-Jan | 76 | 0.3612 | 0.3072 | 0.4169 | positive | 1.0000 | 0.3794 |
| mean_vpd | Jan-Feb | 76 | 0.1185 | 0.0719 | 0.1766 | positive | 0.9079 | 0.1478 |
| mean_vpd | Feb-Mar | 76 | 0.4375 | 0.3744 | 0.4878 | positive | 1.0000 | 0.4306 |
| mean_vpd | Mar-Apr | 76 | 0.5488 | 0.4923 | 0.5987 | positive | 0.9868 | 0.5375 |
| upper_soil_moisture | Dec-Jan | 76 | 0.3856 | 0.3303 | 0.4411 | positive | 1.0000 | 0.4066 |
| upper_soil_moisture | Jan-Feb | 76 | 0.2344 | 0.1615 | 0.3423 | positive | 0.9868 | 0.2801 |
| upper_soil_moisture | Feb-Mar | 76 | 0.3718 | 0.3204 | 0.4293 | positive | 0.9868 | 0.3904 |
| upper_soil_moisture | Mar-Apr | 76 | 0.5808 | 0.5345 | 0.6288 | positive | 1.0000 | 0.5768 |
| deep_soil_moisture_28_100 | Dec-Jan | 76 | 0.6692 | 0.6015 | 0.7149 | positive | 1.0000 | 0.6514 |
| deep_soil_moisture_28_100 | Jan-Feb | 76 | 0.4748 | 0.3492 | 0.5997 | positive | 1.0000 | 0.4852 |
| deep_soil_moisture_28_100 | Feb-Mar | 76 | 0.5314 | 0.4562 | 0.6110 | positive | 1.0000 | 0.5483 |
| deep_soil_moisture_28_100 | Mar-Apr | 76 | 0.8085 | 0.7288 | 0.8415 | positive | 1.0000 | 0.7876 |
| deep_soil_moisture_100_255 | Dec-Jan | 76 | 0.8926 | 0.8613 | 0.9227 | positive | 1.0000 | 0.8877 |
| deep_soil_moisture_100_255 | Jan-Feb | 76 | 0.9237 | 0.8966 | 0.9415 | positive | 1.0000 | 0.9062 |
| deep_soil_moisture_100_255 | Feb-Mar | 76 | 0.9342 | 0.8783 | 0.9567 | positive | 1.0000 | 0.9028 |
| deep_soil_moisture_100_255 | Mar-Apr | 76 | 0.9502 | 0.9321 | 0.9698 | positive | 1.0000 | 0.9467 |
| solar_energy | Dec-Jan | 76 | 0.1457 | 0.1013 | 0.2029 | positive | 0.9737 | 0.1714 |
| solar_energy | Jan-Feb | 76 | -0.1490 | -0.1756 | -0.1220 | negative | 0.9868 | -0.1166 |
| solar_energy | Feb-Mar | 76 | -0.0903 | -0.1460 | -0.0090 | negative | 0.7763 | -0.0437 |
| solar_energy | Mar-Apr | 76 | 0.1664 | 0.1302 | 0.2215 | positive | 0.9868 | 0.2001 |

## Dec-Jan decision synthesis

| conceptual_variable | median_grid_spearman | q25_grid_spearman | q75_grid_spearman | modal_direction_fraction | start_standardized_high_minus_low | end_standardized_high_minus_low | start_grid_direction_agreement | end_grid_direction_agreement | decision_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rainfall_input | 0.3634 | 0.2945 | 0.4551 | 0.9868 | 0.2909 | 0.2781 | 0.8289 | 0.8026 | KEEP_MONTHLY |
| temperature | 0.3999 | 0.3400 | 0.4678 | 1.0000 | -0.3356 | -0.2810 | 0.8684 | 0.7368 | KEEP_MONTHLY |
| relative_humidity | 0.4814 | 0.4403 | 0.5297 | 1.0000 | 0.4887 | 0.4254 | 0.8816 | 0.8289 | DEC_JAN_AGGREGATION_CANDIDATE |
| mean_vpd | 0.3612 | 0.3072 | 0.4169 | 1.0000 | -0.3277 | -0.2615 | 0.7895 | 0.6974 | KEEP_MONTHLY |
| upper_soil_moisture | 0.3856 | 0.3303 | 0.4411 | 1.0000 | 0.3339 | 0.2729 | 0.8026 | 0.7105 | KEEP_MONTHLY |
| deep_soil_moisture_28_100 | 0.6692 | 0.6015 | 0.7149 | 1.0000 | 0.2666 | 0.3382 | 0.7105 | 0.7763 | DEC_JAN_AGGREGATION_CANDIDATE |
| deep_soil_moisture_100_255 | 0.8926 | 0.8613 | 0.9227 | 1.0000 | 0.0875 | 0.2008 | 0.6316 | 0.7632 | KEEP_MONTHLY |
| solar_energy | 0.1457 | 0.1013 | 0.2029 | 0.9737 | -0.3151 | -0.3112 | 0.7895 | 0.7237 | KEEP_MONTHLY |

Only Dec-Jan relative humidity and Dec-Jan 28-100 cm soil moisture are promoted as aggregation candidates. No Jan-Feb, Feb-Mar, or Mar-Apr aggregate is promoted.

## Frozen downstream universe

Candidate representations: **38**.

| candidate_id | raw_source_variable | source_months | candidate_status | spatial_status | conditional_information_flag |
| --- | --- | --- | --- | --- | --- |
| rainfall_input__m_-4 | nasa_total_rainfall_mm | Dec_(t-1) | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| rainfall_input__m_-3 | nasa_total_rainfall_mm | Jan_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| rainfall_input__m_-2 | nasa_total_rainfall_mm | Feb_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| rainfall_input__m_-1 | nasa_total_rainfall_mm | Mar_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| rainfall_input__m_0 | nasa_total_rainfall_mm | Apr_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| temperature__m_-4 | nasa_average_temperature_c | Dec_(t-1) | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| temperature__m_-3 | nasa_average_temperature_c | Jan_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| temperature__m_-2 | nasa_average_temperature_c | Feb_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| temperature__m_-1 | nasa_average_temperature_c | Mar_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| temperature__m_0 | nasa_average_temperature_c | Apr_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| relative_humidity__dec_jan | nasa_average_relative_humidity_pct | Dec_(t-1);Jan_t | DEC_JAN_AGGREGATION_CANDIDATE | STATEWIDE_COMMON | ATMOSPHERIC_SECONDARY |
| relative_humidity__m_-2 | nasa_average_relative_humidity_pct | Feb_t | KEEP_MONTHLY | STATEWIDE_COMMON | ATMOSPHERIC_SECONDARY |
| relative_humidity__m_-1 | nasa_average_relative_humidity_pct | Mar_t | KEEP_MONTHLY | STATEWIDE_COMMON | ATMOSPHERIC_SECONDARY |
| relative_humidity__m_0 | nasa_average_relative_humidity_pct | Apr_t | KEEP_MONTHLY | STATEWIDE_COMMON | ATMOSPHERIC_SECONDARY |
| mean_vpd__m_-4 | vpd_mean_kpa | Dec_(t-1) | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| mean_vpd__m_-3 | vpd_mean_kpa | Jan_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| mean_vpd__m_-2 | vpd_mean_kpa | Feb_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| mean_vpd__m_-1 | vpd_mean_kpa | Mar_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| mean_vpd__m_0 | vpd_mean_kpa | Apr_t | KEEP_SEPARATE_CONDITIONAL | MIXED_HETEROGENEOUS | EXP05_CONDITIONAL |
| upper_soil_moisture__m_-4 | soil_moisture_0_to_7cm_m3_m3 | Dec_(t-1) | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| upper_soil_moisture__m_-3 | soil_moisture_0_to_7cm_m3_m3 | Jan_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| upper_soil_moisture__m_-2 | soil_moisture_0_to_7cm_m3_m3 | Feb_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| upper_soil_moisture__m_-1 | soil_moisture_0_to_7cm_m3_m3 | Mar_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| upper_soil_moisture__m_0 | soil_moisture_0_to_7cm_m3_m3 | Apr_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | HYDRO_CONDITIONAL |
| deep_soil_moisture_28_100__dec_jan | soil_moisture_28_to_100cm_m3_m3 | Dec_(t-1);Jan_t | DEC_JAN_AGGREGATION_CANDIDATE | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_28_100__m_-2 | soil_moisture_28_to_100cm_m3_m3 | Feb_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_28_100__m_-1 | soil_moisture_28_to_100cm_m3_m3 | Mar_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_28_100__m_0 | soil_moisture_28_to_100cm_m3_m3 | Apr_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_100_255__m_-4 | soil_moisture_100_to_255cm_m3_m3 | Dec_(t-1) | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_100_255__m_-3 | soil_moisture_100_to_255cm_m3_m3 | Jan_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_100_255__m_-2 | soil_moisture_100_to_255cm_m3_m3 | Feb_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_100_255__m_-1 | soil_moisture_100_to_255cm_m3_m3 | Mar_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| deep_soil_moisture_100_255__m_0 | soil_moisture_100_to_255cm_m3_m3 | Apr_t | KEEP_SEPARATE_CONDITIONAL | DEFERRED_CONDITIONAL | HYDRO_CONDITIONAL |
| solar_energy__m_-4 | solar_radiation_mean_daily_mj_m2 | Dec_(t-1) | KEEP_MONTHLY | MIXED_HETEROGENEOUS | NONE |
| solar_energy__m_-3 | solar_radiation_mean_daily_mj_m2 | Jan_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | NONE |
| solar_energy__m_-2 | solar_radiation_mean_daily_mj_m2 | Feb_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | NONE |
| solar_energy__m_-1 | solar_radiation_mean_daily_mj_m2 | Mar_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | NONE |
| solar_energy__m_0 | solar_radiation_mean_daily_mj_m2 | Apr_t | KEEP_MONTHLY | MIXED_HETEROGENEOUS | NONE |

## Protected structure

- Temperature and mean VPD remain separate (`EXP05_CONDITIONAL`).
- Rainfall, upper moisture, and both deep-moisture layers remain distinct (`HYDRO_CONDITIONAL`).
- Static SoilGrids properties are not included.
- Total solar, daily-max VPD, and 7-28 cm moisture remain archived robustness representations rather than additional candidates.
