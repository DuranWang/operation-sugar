# EXP-02B Matched-Support Composition Sensitivity

## Status and scope

**EXP-02B-1 COMPLETED.** The approved common-support fixed weights were applied without further tuning. P50=10 is primary and P50=12 is the detrending robustness specification. Actual and fixed weighting use identical municipality-year residual support. No weather result was used, and EXP-03 / EXP-04 were not started.

## Validation

- Valid grid-years per specification: **3773**.
- Valid multi-municipality grid-years per specification: **3694**.
- Valid single-municipality grid-years per specification: **79**.
- Invalid grid-years per specification: **283**; all are retained with documented reasons.
- Actual and fixed weights sum to one on every valid grid-year.
- Fixed weights are renormalized only when matched residual support is a strict subset of full eligible grid membership.
- Full-membership grid-years per specification: **1880**; subset-support grid-years requiring fixed-weight renormalization: **1893**.
- P50=10 and P50=12 use identical matched support and identical weights.

## Primary multi-municipality-grid agreement

| specification | grid_years | grids | pearson_correlation | spearman_correlation | mean_absolute_difference | rmse_difference | sign_agreement | mean_delta | delta_standard_deviation | p05_delta | median_delta | p95_delta | median_absolute_delta | p90_absolute_delta | p95_absolute_delta | p99_absolute_delta | maximum_absolute_delta | mean_composition_tv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p50_10 | 3694 | 74 | 0.9485 | 0.9410 | 0.8398 | 1.6684 | 0.9215 | -0.0239 | 1.6685 | -2.1173 | 0.0000 | 2.0507 | 0.3751 | 2.0844 | 3.1220 | 6.9976 | 19.2720 | 0.1586 |
| p50_12 | 3694 | 74 | 0.9488 | 0.9402 | 0.8954 | 1.7706 | 0.9180 | -0.0266 | 1.7707 | -2.2038 | 0.0000 | 2.2102 | 0.4018 | 2.2058 | 3.3015 | 7.2943 | 20.6501 | 0.1586 |

These statistics describe representation sensitivity only. No materiality threshold or preferred weighting scheme is selected.

## Single-municipality grids

| specification | grid_years | grids | mean_absolute_difference | rmse_difference | sign_agreement | maximum_absolute_delta | mean_composition_tv |
|---|---|---|---|---|---|---|---|
| p50_10 | 79 | 4 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| p50_12 | 79 | 4 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

Their equality is mechanical and they are excluded from the primary composition statistics.

## Composition distance and concentration

| specification | grid_years | pearson_tv_vs_absolute_delta | spearman_tv_vs_absolute_delta |
|---|---|---|---|
| p50_10 | 3694 | 0.5354 | 0.6376 |
| p50_12 | 3694 | 0.5401 | 0.6421 |

| specification | concentration_set | items | share_of_total_absolute_delta |
|---|---|---|---|
| p50_10 | top_1_percent_grid_years | 37 | 0.1265 |
| p50_10 | top_5_percent_grid_years | 185 | 0.3319 |
| p50_10 | top_10_percent_grid_years | 370 | 0.4817 |
| p50_10 | top_5_grids | 5 | 0.1577 |
| p50_10 | top_10_grids | 10 | 0.2735 |
| p50_10 | top_5_years | 5 | 0.1566 |
| p50_10 | top_10_years | 10 | 0.2845 |
| p50_12 | top_1_percent_grid_years | 37 | 0.1264 |
| p50_12 | top_5_percent_grid_years | 185 | 0.3288 |
| p50_12 | top_10_percent_grid_years | 370 | 0.4780 |
| p50_12 | top_5_grids | 5 | 0.1570 |
| p50_12 | top_10_grids | 10 | 0.2720 |
| p50_12 | top_5_years | 5 | 0.1547 |
| p50_12 | top_10_years | 10 | 0.2819 |

The TV–absolute-delta relationship is descriptive, not causal.

## P50=10 versus P50=12 robustness

| metric | grid_years | pearson_correlation | spearman_correlation | sign_agreement | mean_absolute_difference | p95_absolute_difference | maximum_absolute_difference |
|---|---|---|---|---|---|---|---|
| actual_grid_residual_tch | 3694 | 0.9949 | 0.9912 | 0.9543 | 0.4339 | 1.2184 | 5.3147 |
| fixed_grid_residual_tch | 3694 | 0.9944 | 0.9906 | 0.9518 | 0.4208 | 1.1453 | 5.6930 |
| delta_actual_minus_fixed_tch | 3694 | 0.9960 | 0.9892 | 0.9691 | 0.1004 | 0.3765 | 1.9437 |

## Largest effects by grid

| specification | grid_id | grid_years | eligible_municipalities | mean_absolute_delta | p95_absolute_delta | maximum_absolute_delta | mean_composition_tv | mean_observed_state_area_share |
|---|---|---|---|---|---|---|---|---|
| p50_10 | era5_-21.00_-49.50 | 52 | 14 | 2.2074 | 6.8342 | 16.7504 | 0.2594 | 0.0132 |
| p50_10 | era5_-23.00_-49.00 | 52 | 5 | 2.1123 | 9.4451 | 18.1798 | 0.2468 | 0.0041 |
| p50_10 | era5_-21.50_-49.50 | 52 | 4 | 1.8417 | 8.3420 | 14.9820 | 0.1586 | 0.0028 |
| p50_10 | era5_-22.00_-49.50 | 52 | 7 | 1.6873 | 4.9443 | 11.6339 | 0.2940 | 0.0065 |
| p50_10 | era5_-20.50_-51.00 | 52 | 6 | 1.5598 | 5.6321 | 17.4647 | 0.1793 | 0.0058 |
| p50_10 | era5_-20.50_-50.00 | 52 | 11 | 1.5402 | 4.8817 | 19.2720 | 0.2425 | 0.0074 |
| p50_10 | era5_-22.50_-50.00 | 52 | 4 | 1.4959 | 4.2512 | 10.4559 | 0.1887 | 0.0029 |
| p50_10 | era5_-20.50_-49.50 | 47 | 7 | 1.4641 | 6.8115 | 9.6119 | 0.2596 | 0.0078 |
| p50_10 | era5_-23.50_-47.00 | 52 | 3 | 1.3440 | 7.2095 | 15.7955 | 0.1816 | 0.0002 |
| p50_10 | era5_-20.00_-50.50 | 44 | 9 | 1.3012 | 4.0661 | 4.9091 | 0.2492 | 0.0027 |
| p50_12 | era5_-21.00_-49.50 | 52 | 14 | 2.3347 | 7.1324 | 18.5427 | 0.2594 | 0.0132 |
| p50_12 | era5_-23.00_-49.00 | 52 | 5 | 2.2850 | 11.2589 | 19.3884 | 0.2468 | 0.0041 |
| p50_12 | era5_-21.50_-49.50 | 52 | 4 | 1.9279 | 8.7845 | 15.1846 | 0.1586 | 0.0028 |
| p50_12 | era5_-22.00_-49.50 | 52 | 7 | 1.7563 | 5.0270 | 12.2049 | 0.2940 | 0.0065 |
| p50_12 | era5_-20.50_-51.00 | 52 | 6 | 1.6822 | 5.7575 | 18.4815 | 0.1793 | 0.0058 |
| p50_12 | era5_-20.50_-50.00 | 52 | 11 | 1.6103 | 4.7843 | 20.6501 | 0.2425 | 0.0074 |
| p50_12 | era5_-22.50_-50.00 | 52 | 4 | 1.5612 | 4.2934 | 11.2466 | 0.1887 | 0.0029 |
| p50_12 | era5_-20.50_-49.50 | 47 | 7 | 1.5289 | 6.9855 | 10.1161 | 0.2596 | 0.0078 |
| p50_12 | era5_-23.50_-47.00 | 52 | 3 | 1.4682 | 7.6767 | 16.4263 | 0.1816 | 0.0002 |
| p50_12 | era5_-20.00_-50.50 | 44 | 9 | 1.4216 | 4.4113 | 4.9024 | 0.2492 | 0.0027 |

## Calendar years with largest mean absolute effects

| specification | year | grid_years | mean_absolute_delta | p95_absolute_delta | maximum_absolute_delta | mean_composition_tv |
|---|---|---|---|---|---|---|
| p50_10 | 1983 | 72 | 1.7335 | 5.8679 | 8.6550 | 0.1876 |
| p50_10 | 1975 | 61 | 1.6187 | 5.9443 | 11.6339 | 0.2148 |
| p50_10 | 1979 | 63 | 1.4299 | 4.9726 | 13.7371 | 0.2021 |
| p50_10 | 1981 | 69 | 1.2583 | 3.5849 | 19.2720 | 0.2007 |
| p50_10 | 1980 | 67 | 1.1786 | 3.2775 | 17.4647 | 0.2005 |
| p50_10 | 1984 | 73 | 1.1705 | 3.4179 | 6.9461 | 0.1838 |
| p50_10 | 1978 | 60 | 1.1481 | 3.8319 | 12.1590 | 0.2000 |
| p50_10 | 1982 | 69 | 1.1419 | 3.2521 | 18.1798 | 0.1748 |
| p50_10 | 1976 | 60 | 1.1183 | 3.6388 | 5.6351 | 0.2008 |
| p50_10 | 2007 | 72 | 1.1178 | 5.3707 | 12.6214 | 0.1358 |
| p50_12 | 1983 | 72 | 1.8160 | 5.9132 | 9.1775 | 0.1876 |
| p50_12 | 1975 | 61 | 1.6486 | 5.7373 | 12.2049 | 0.2148 |
| p50_12 | 1979 | 63 | 1.4837 | 5.8098 | 12.8864 | 0.2021 |
| p50_12 | 1981 | 69 | 1.3797 | 3.8279 | 20.6501 | 0.2007 |
| p50_12 | 1980 | 67 | 1.3161 | 3.5482 | 18.4815 | 0.2005 |
| p50_12 | 1978 | 60 | 1.2563 | 4.1003 | 13.0691 | 0.2000 |
| p50_12 | 1984 | 73 | 1.2548 | 3.7769 | 7.4061 | 0.1838 |
| p50_12 | 2007 | 72 | 1.1964 | 5.5805 | 12.9022 | 0.1358 |
| p50_12 | 1977 | 59 | 1.1928 | 3.3010 | 18.5427 | 0.2015 |
| p50_12 | 1982 | 69 | 1.1891 | 3.3576 | 19.3884 | 0.1748 |

## Largest individual grid-years

| specification | grid_id | year | matched_support_municipalities | absolute_delta_tch | composition_tv |
|---|---|---|---|---|---|
| p50_10 | era5_-20.50_-50.00 | 1981 | 2 | 19.2720 | 0.5235 |
| p50_10 | era5_-23.00_-49.00 | 1982 | 3 | 18.1798 | 0.5496 |
| p50_10 | era5_-20.50_-51.00 | 1980 | 2 | 17.4647 | 0.3625 |
| p50_10 | era5_-21.00_-49.50 | 1977 | 5 | 16.7504 | 0.6039 |
| p50_10 | era5_-23.50_-47.00 | 2018 | 2 | 15.7955 | 0.8498 |
| p50_10 | era5_-21.50_-49.50 | 2006 | 3 | 14.9820 | 0.2590 |
| p50_10 | era5_-23.00_-49.00 | 1979 | 2 | 13.7371 | 0.6054 |
| p50_10 | era5_-23.50_-45.50 | 2001 | 2 | 13.2922 | 0.4890 |
| p50_10 | era5_-21.50_-49.50 | 2007 | 4 | 12.6214 | 0.2627 |
| p50_10 | era5_-21.00_-49.50 | 1978 | 5 | 12.1590 | 0.5460 |
| p50_12 | era5_-20.50_-50.00 | 1981 | 2 | 20.6501 | 0.5235 |
| p50_12 | era5_-23.00_-49.00 | 1982 | 3 | 19.3884 | 0.5496 |
| p50_12 | era5_-21.00_-49.50 | 1977 | 5 | 18.5427 | 0.6039 |
| p50_12 | era5_-20.50_-51.00 | 1980 | 2 | 18.4815 | 0.3625 |
| p50_12 | era5_-23.50_-47.00 | 2018 | 2 | 16.4263 | 0.8498 |
| p50_12 | era5_-21.50_-49.50 | 2006 | 3 | 15.1846 | 0.2590 |
| p50_12 | era5_-23.50_-45.50 | 2001 | 2 | 14.7459 | 0.4890 |
| p50_12 | era5_-21.00_-49.50 | 1978 | 5 | 13.0691 | 0.5460 |
| p50_12 | era5_-21.50_-49.50 | 2007 | 4 | 12.9022 | 0.2627 |
| p50_12 | era5_-23.00_-49.00 | 1979 | 2 | 12.8864 | 0.6054 |

## Reproducible representative grids

| selection_reason | grid_id | eligible_municipalities | grid_years | mean_absolute_delta | mean_composition_tv | mean_observed_state_area_share |
|---|---|---|---|---|---|---|
| high_harvested_area | era5_-21.00_-48.00 | 8 | 52 | 0.4912 | 0.0925 | 0.0687 |
| low_composition_change | era5_-24.50_-49.00 | 2 | 31 | 0.1047 | 0.0357 | 0.0000 |
| high_composition_change | era5_-22.00_-49.50 | 7 | 52 | 1.6873 | 0.2940 | 0.0065 |
| large_composition_effect | era5_-21.00_-49.50 | 14 | 52 | 2.2074 | 0.2594 | 0.0132 |
| many_municipalities | era5_-21.00_-49.00 | 16 | 52 | 0.4882 | 0.1566 | 0.0343 |

## Interpretation boundaries

- Delta is a matched-support weighting difference, not a causal effect of westward expansion.
- The actual-weight series uses contemporaneous observed harvested area and is historical/descriptive, not automatically forecast-safe.
- The fixed series uses the approved common-reference construction; it was not tuned against residual or weather results.
- P50=10 is the primary detrending input only because Chat pre-specified it, not because it optimized these diagnostics.
- This report does not decide whether composition effects are practically material; that interpretation returns to Chat.
