# EXP-03 Checkpoint 2 — Robustness and Within-Grid Continuous Analysis

## Fixed inputs and validation

- Checkpoint 1 complete-window panel: **3267** grid-years, **78** grids, 1982–2025.
- Yield outcome: `actual_grid_residual_tch`; weather exposures: existing grid/calendar-month anomalies.
- Yield and weather ranks are calculated separately within ERA5 grid using deterministic average ranks.
- Grid-specific Spearman uses paired valid years only. Minimum reported paired years: **15**.
- Per-grid complete-weather histories: minimum **13**, median **44**, maximum **44** years. The threshold excludes only the two 13-year grids from grid-specific summaries; the pooled statistic retains all observations.
- Checkpoint 1 files were read only; all outputs are in a separate `checkpoint2` directory.

## Alternative groupings

20/60/20 complete-sample group counts:

| yield_group | grid_year_observations |
|---|---|
| Low | 582 |
| Medium | 2075 |
| High | 610 |

Within-grid z-score → pooled quartile counts (cut points -0.4638, 0.4850):

| yield_group | grid_year_observations |
|---|---|
| Low | 762 |
| Medium | 1703 |
| High | 802 |

High-level robustness:

| specification | sample_definition | effect_correlation_vs_primary | primary_window_correlation | late_window_correlation | sign_agreement_rate | sign_reversals | late_window_sign_agreement_rate | late_window_sign_reversals | maximum_absolute_effect_change | late_season_pattern |
|---|---|---|---|---|---|---|---|---|---|---|
| primary_within_grid_25_50_25 | 1974-2025 within-grid ranks; intersect complete 1982-2025 weather | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 1.0000 | 0 | 0.0000 | baseline |
| within_grid_20_60_20 | 1974-2025 within-grid 20/60/20; complete weather | 0.9836 | 0.9910 | 0.9948 | 0.9318 | 12 | 1.0000 | 0 | 0.1037 | broadly preserved |
| within_grid_zscore_pooled_25_50_25 | 1974-2025 within-grid z-score; pooled quartiles | 0.9928 | 0.9963 | 0.9973 | 0.9716 | 5 | 1.0000 | 0 | 0.0566 | broadly preserved |
| within_grid_25_50_25_rank_1982_2025_only | 1982-2025 within-grid 25/50/25 ranks | 0.9971 | 0.9975 | 0.9980 | 0.9886 | 2 | 1.0000 | 0 | 0.0438 | broadly preserved |

Both alternative groupings preserve the broad late-`t-1` / early-`t` moisture-versus-atmospheric-demand structure. Differences in individual cells are retained in the machine-readable comparison tables rather than treated as model-selection evidence.

## Continuous within-grid evidence

Across `m_-4 … m_0`, categorical and pooled within-grid-rank directions agree in **100.0%** of cells. The mean fraction of usable grids agreeing with the pooled direction is **70.7%**. Humidity and soil-moisture directions are generally positive, while temperature and VPD are generally negative, but cross-grid distributions are heterogeneous rather than unanimous.

Largest categorical/continuous sign disagreements:

| weather_variable | relative_month | standardized_high_minus_low | pooled_within_grid_rank_rho | median_grid_rho | pct_grids_agree_with_pooled_direction |
|---|---|---|---|---|---|
| soil_moisture_100_to_255cm_m3_m3 | m_-11 | -0.0194 | 0.0038 | -0.0127 | 0.4605 |
| nasa_average_relative_humidity_pct | m_-13 | -0.0161 | 0.0213 | 0.0201 | 0.5789 |
| soil_moisture_100_to_255cm_m3_m3 | m_-12 | -0.0132 | 0.0114 | -0.0133 | 0.4737 |
| soil_moisture_100_to_255cm_m3_m3 | m_-10 | -0.0080 | 0.0103 | -0.0021 | 0.5000 |
| nasa_average_temperature_c | m_-5 | -0.0058 | 0.0013 | -0.0170 | 0.4605 |
| nasa_average_temperature_c | m_-14 | -0.0041 | 0.0120 | 0.0270 | 0.5526 |

Descriptive possible threshold/gradual-response flags use upper/lower quartiles of absolute categorical and continuous magnitudes, not significance thresholds:

| weather_variable | relative_month | standardized_high_minus_low | pooled_within_grid_rank_rho | large_categorical_weak_continuous_flag | large_continuous_weak_categorical_flag |
|---|---|---|---|---|---|
| vpd_mean_kpa | m_-2 | -0.2382 | -0.0218 | True | False |

These cells are candidates for later nonlinear investigation only; no nonlinear model is fitted here.

## Primary 12-month versus extended 16-month window

| window_segment | cells | mean_absolute_primary_effect | mean_absolute_20_60_20_effect | mean_absolute_zscore_effect | mean_absolute_pooled_rank_rho | mean_absolute_median_grid_rho | mean_grid_direction_consistency | mean_evidence_sign_agreement_count | cells_all_five_directions_agree |
|---|---|---|---|---|---|---|---|---|---|
| extended_only_Jan_Apr_t_minus_1 | 44 | 0.0728 | 0.0580 | 0.0584 | 0.0248 | 0.0275 | 0.5786 | 4.4318 | 31 |
| primary_May_t_minus_1_Apr_t | 132 | 0.1782 | 0.2029 | 0.1908 | 0.0653 | 0.0682 | 0.6661 | 4.9242 | 124 |

The extra `m_-15 … m_-12` months have weaker average magnitude and less consistent cross-method evidence than the primary 12-month window. They should currently remain a robustness window rather than being promoted into the eventual main feature universe. The official window definitions are unchanged.

## Ranking-history sensitivity

- Complete-weather assignments changed: **116 / 3267 (3.55%)**.
- 1982–2025-only group counts:

| yield_group | grid_year_observations |
|---|---|
| Low | 818 |
| Medium | 1631 |
| High | 818 |

Transition matrix:

| full_history_group | Low | Medium | High |
|---|---|---|---|
| Low | 761 | 8 | 0 |
| Medium | 57 | 1602 | 30 |
| High | 0 | 21 | 788 |

The effect comparison is included in the robustness table. Full-history grouping remains primary and was not overwritten.

## Answers and decision

1. The December–March pattern survives 20/60/20 grouping.
2. It also survives within-grid z-score normalization followed by pooled quartiles.
3. Within-grid continuous directions broadly agree with the categorical pattern in the main coherent region.
4. Grid-specific results show moderate, not universal, directional consistency; the signal is not attributable to only one or two grids, but geographic heterogeneity is real.
5. Disagreements are concentrated in weaker cells and isolated months; flagged large/weak cases merit later nonlinear diagnostics.
6. `m_-15 … m_-12` do not show comparably coherent multi-method evidence and remain robustness-only.
7. Restricting ranking history to 1982–2025 does not erase the late-season structure.

### Classification: **B — Partially robust**

The broad humidity/soil-moisture versus temperature/VPD structure survives every grouping and ranking-history test, and continuous directions agree throughout the late window. However, 11 of 55 late-window cells have fewer than 60% of usable grids agreeing with the pooled direction, and at least one large categorical contrast has weak continuous support. Geographic and cell-level heterogeneity therefore make category A too strong.

## Stop boundary

No feature construction, PCA, variable reduction, lag selection, nonlinear or predictive modeling, train/test splitting, biological labels, causal claims, harvest-share weighting, or harvest-progress reconstruction was performed.
