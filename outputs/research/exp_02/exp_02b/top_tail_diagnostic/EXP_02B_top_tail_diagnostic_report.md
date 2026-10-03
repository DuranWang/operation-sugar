# EXP-02B Top-Tail Composition Diagnostic

## Scope and status

The completed P50=10 EXP-02B outputs were diagnosed without refitting residuals or changing the approved common-support weighting design. The top 10 multi-municipality grid-years were selected from the existing reproducible absolute-Delta ranking. P50=12 was used only as a cross-check. No weather-yield experiment was started.

## Top-10 event summary

| rank_absolute_delta_p50_10 | grid_id | year | delta_p50_10_tch | composition_tv | matched_support_municipalities | largest_positive_contributor | largest_positive_contribution_tch | largest_negative_contributor | largest_negative_contribution_tch | top2_abs_contribution_share_of_abs_delta |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | era5_-20.50_-50.00 | 1981 | -19.272 | 0.523 | 2 |  |  | Votuporanga | -12.456 | 1.000 |
| 2 | era5_-23.00_-49.00 | 1982 | -18.180 | 0.550 | 3 | Arandu | 0.007 | Cerqueira César | -9.449 | 1.000 |
| 3 | era5_-20.50_-51.00 | 1980 | 17.465 | 0.363 | 2 | Sud Mennucci | 11.349 |  |  | 1.000 |
| 4 | era5_-21.00_-49.50 | 1977 | 16.750 | 0.604 | 5 | Urupês | 12.404 | Nova Aliança | -0.089 | 0.944 |
| 5 | era5_-23.50_-47.00 | 2018 | 15.795 | 0.850 | 2 | Cabreúva | 10.982 |  |  | 1.000 |
| 6 | era5_-21.50_-49.50 | 2006 | -14.982 | 0.259 | 3 | Irapuã | 1.133 | Sabino | -16.682 | 1.189 |
| 7 | era5_-23.00_-49.00 | 1979 | 13.737 | 0.605 | 2 | Avaré | 14.952 | Cerqueira César | -1.215 | 1.177 |
| 8 | era5_-23.50_-45.50 | 2001 | -13.292 | 0.489 | 2 |  |  | Paraibuna | -7.143 | 1.000 |
| 9 | era5_-21.50_-49.50 | 2007 | 12.621 | 0.263 | 4 | Sabino | 13.288 | Irapuã | -0.416 | 1.086 |
| 10 | era5_-21.00_-49.50 | 1978 | 12.159 | 0.546 | 5 | José Bonifácio | 6.358 |  |  | 0.752 |

The contribution-share denominator is absolute event Delta. Shares can exceed one when large positive and negative municipality contributions cancel.

## Artifact checks

| rank_absolute_delta_p50_10 | grid_id | year | fixed_weight_renormalized | any_first_valid_yield_year | any_last_valid_yield_year | any_within_one_year_of_endpoint | any_immediately_adjacent_to_internal_missing_gap | any_long_internal_gap_history_gt10 | any_top_5pct_within_municipality_abs_residual | any_unusual_harvested_area_source_status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | era5_-20.50_-50.00 | 1981 | True | True | False | True | False | False | True | False |
| 2 | era5_-23.00_-49.00 | 1982 | True | False | False | False | True | False | True | False |
| 3 | era5_-20.50_-51.00 | 1980 | True | False | False | True | True | False | True | False |
| 4 | era5_-21.00_-49.50 | 1977 | True | False | False | False | False | True | True | False |
| 5 | era5_-23.50_-47.00 | 2018 | True | False | False | False | False | False | False | False |
| 6 | era5_-21.50_-49.50 | 2006 | True | False | False | False | False | False | True | False |
| 7 | era5_-23.00_-49.00 | 1979 | True | False | False | False | False | False | True | False |
| 8 | era5_-23.50_-45.50 | 2001 | True | False | False | False | True | False | False | False |
| 9 | era5_-21.50_-49.50 | 2007 | False | False | False | False | True | False | True | False |
| 10 | era5_-21.00_-49.50 | 1978 | True | False | False | False | True | True | False | False |

- Actual and fixed weights each sum to one for every event.
- Municipality contributions reproduce each signed Delta within numerical tolerance.
- Every contributing row has observed yield and usable harvested-area status; unavailable area never enters matched support.
- Endpoint, gap-history, and high-percentile residual indicators are diagnostic flags, not error labels or exclusion rules.
- Fixed-weight renormalization appears only because these selected years often have matched residual support smaller than full eligible grid membership.

## Diagnostic reading

- **9/10** events use the authorized subset-support fixed-weight renormalization; matched support ranges from **2 to 5 municipalities**. This is important tail context, but not a violation of the approved design.
- **2/10** events contain a municipality within one year of its observed-history endpoint, **5/10** are adjacent to an internal missing-yield gap, and **2/10** include a municipality from the established `>10`-year maximum-gap stratum.
- **7/10** include at least one residual in the municipality's upper 5% by absolute residual percentile. **0/10** contain an unusual harvested-area status; all contributing statuses are ordinary `numeric_positive` observations.
- The maximum event is exactly reconstructed from two contributions. It contains a first-valid-year municipality observation and upper-tail within-municipality residuals, so its endpoint context is explicit rather than hidden.
- P50=12 preserves the sign for **10/10** events. The P50=12/P50=10 absolute-Delta ratio ranges from **0.938 to 1.109**, and all ten remain within the P50=12 top ten.

The top tail is therefore algebraically reconciled and mechanically interpretable. No source-status conversion, weight-sum failure, contribution mismatch, or detrending-sign instability is evident. Frequent subset-support renormalization, sparse event-level support, endpoint/gap contexts, and extreme residuals remain substantive diagnostic context rather than grounds for an unapproved exclusion.

## P50=12 cross-check

| rank_absolute_delta_p50_10 | grid_id | year | delta_p50_10_tch | delta_p50_12_tch | rank_absolute_delta_p50_12 | same_sign | absolute_delta_change_tch | absolute_delta_ratio_p50_12_to_p50_10 |
|---|---|---|---|---|---|---|---|---|
| 1 | era5_-20.50_-50.00 | 1981 | -19.272 | -20.650 | 1 | True | 1.378 | 1.072 |
| 2 | era5_-23.00_-49.00 | 1982 | -18.180 | -19.388 | 2 | True | 1.209 | 1.066 |
| 3 | era5_-20.50_-51.00 | 1980 | 17.465 | 18.481 | 4 | True | 1.017 | 1.058 |
| 4 | era5_-21.00_-49.50 | 1977 | 16.750 | 18.543 | 3 | True | 1.792 | 1.107 |
| 5 | era5_-23.50_-47.00 | 2018 | 15.795 | 16.426 | 5 | True | 0.631 | 1.040 |
| 6 | era5_-21.50_-49.50 | 2006 | -14.982 | -15.185 | 6 | True | 0.203 | 1.014 |
| 7 | era5_-23.00_-49.00 | 1979 | 13.737 | 12.886 | 10 | True | -0.851 | 0.938 |
| 8 | era5_-23.50_-45.50 | 2001 | -13.292 | -14.746 | 7 | True | 1.454 | 1.109 |
| 9 | era5_-21.50_-49.50 | 2007 | 12.621 | 12.902 | 9 | True | 0.281 | 1.022 |
| 10 | era5_-21.00_-49.50 | 1978 | 12.159 | 13.069 | 8 | True | 0.910 | 1.075 |

All sign and magnitude comparisons above are descriptive. P50=12 does not redefine the P50=10 event selection.

## Maximum event decomposition

| municipality | ibge_code | harvested_area_ha | residual_p50_10 | actual_weight | approved_common_support_fixed_reference_weight | fixed_weight | weight_difference_actual_minus_fixed | contribution_p50_10_tch | within_municipality_abs_residual_percentile |
|---|---|---|---|---|---|---|---|---|---|
| Votuporanga | 3557105 | 89.000 | -23.796 | 0.873 | 0.068 | 0.349 | 0.523 | -12.456 | 0.957 |
| Nhandeara | 3532603 | 13.000 | 13.020 | 0.127 | 0.126 | 0.651 | -0.523 | -6.816 | 1.000 |

## Interpretation boundary

The decomposition is mechanical: large effects occur when large actual-versus-fixed weight shifts align with heterogeneous municipality residuals. Flags identify possible data-boundary contexts but are not treated as proof of artifacts. No causal historical interpretation, exclusion decision, or weighting redesign is made here.
