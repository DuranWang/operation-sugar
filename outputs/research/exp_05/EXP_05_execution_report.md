# EXP-05 execution report

## Gate and frozen sources

Phase A passed; see `phase_a_gate_note.md`. No upstream source, prior experiment result, or authoritative research-state file was modified. Sources and field definitions are in `input_manifest.json`; the frozen targets are `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\actual_vs_fixed_grid_residuals.csv`, with municipality residual/weight lineage checked against `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\matched_support_weight_details.csv`. Canonical weather is read from `D:\Desktop\Operation Sugar\data\processed\combined_weather\annual`; T is `nasa_average_temperature_c` (°C), NASA POWER monthly mean of daily T2M, and VPD is `vpd_mean_kpa` (kPa), Open-Meteo ERA5 monthly mean of daily mean hourly VPD.

Upstream repository HEAD at execution: `d212073c331930c4f62a58a2099693ab64abde1e`. The newly written EXP-05 implementation is uncommitted in this working tree.

## Validation

- 64,896 grid × month-slot × yield-year rows: 78 grids × 16 slots × 52 target years. 52,548 primary paired observations, years 1981–2025; 0 rows lost on all-three-target year intersection.
- February pilot: 76 primary grids N≥20; 72 grids N≥30. Full run: 1216 of 1248 grid-slot series N≥20. N-tier limits are retained in all outputs.
- Missingness reasons: 7,820 rows outside the verified 1981–2025 weather source; 4,528 rows with invalid/missing primary target. There are no additional T/VPD partial-coverage losses once source year and target are valid. Eligible T/VPD covered weights sum to one. The primary analyzable grid-years represent at least 99.99986% of mapped, target-valid area-years under the stated denominator; this is not statewide area coverage.
- Target reconstruction max absolute error 1.24e-14 t/ha; municipality-to-grid overlap 0; target values are not replicated statewide. Shared annual shocks and adjacent weather remain non-independence caveats.
- Partial correlation squared versus partial-R² max discrepancy 1.04e-15; 1216 estimable linear series; 2304/2304 allowed restricted nonlinear fits; 16/16 pooled month models estimable.
- Stratified slopes fitted only when N≥10; empirical tertiles use average ranks for ties. No stratum is used as a primary conditional estimate. All linear, ranking, strata, and nonlinear comparisons use identical per-grid-slot primary paired rows.
- Cross-month sensitivity intersects paired years across all 16 slots within each grid; 1216 grid-slot common-year series retain N≥15. Its estimates never replace maximal-sample results.
- Year-synchronized bootstrap: 200 replicate draws for each of iid, consecutive 3-year, and consecutive 5-year blocks, seed 20261010. The same sampled yield-year labels are applied across grids and slots; missingness masks remain. Grid failures and effective counts are in the replicate table. HC3 coefficient intervals and leave-one-year-out influence are also retained.
- Pooled grid-intercept nonlinear models are additionally refitted under the same synchronized year draws, with within-grid scaling recomputed each replicate. Their per-slot interval diagnostics are in `pooled_nonlinear_synchronized_bootstrap.csv` and `monthly_spatial_synthesis.csv`.

## Principal empirical findings

The sustained negative VPD|T grid-median pattern is Aug–Nov_(t-1), with primary partial medians approximately −0.104, −0.099, −0.081, and −0.105; synchronized 3-year and 5-year block intervals are below zero for those four slots. The Feb_t pilot median VPD|T is about −0.080 but its 3-year interval spans zero. T|VPD has negative medians with 3-year intervals below zero in Dec_(t-1) and Mar_t, but no similarly sustained run. Magnitudes are modest: typical per-grid incremental R² values are near 0.01–0.02. These are month-level descriptive distributions, not independent grid discoveries or causal effects. Grid direction and year influence vary; candidate flags do not assign substantive importance.

P50=12 and fixed-composition median directions broadly agree for the Aug–Nov VPD|T pattern on identical years. The pooled common-slope nonlinear increments do not by themselves generalize to every grid. The common-year sensitivity changes at most one eligible year per grid-slot here and does not overturn the sustained pattern.

## Data products and methods

The output directory contains source manifest, month slots, sample and support audit, per-grid linear partials, strata, restricted per-grid and pooled common-slope nonlinear diagnostics, shared-year target robustness, common-year month sensitivity, leave-one-year-out sensitivity, synchronized bootstrap replicates, area coverage, directional evidence, monthly synthesis, figures, and this report. `grid_month_direction_evidence.csv` marks candidate directional consistency only; substantive magnitude is unadjudicated and **potential redundancy is not assigned**.

Principal machine-readable files: `sample_coverage.csv`, `grid_month_support.csv`, `linear_conditional_results.csv`, `stratification_diagnostics.csv`, `grid_restricted_nonlinear_diagnostics.csv`, `pooled_month_nonlinear_diagnostics.csv`, `all_target_shared_year_linear.csv`, `cross_month_common_year_linear.csv`, `leave_one_year_out.csv`, `synchronized_year_bootstrap_replicates.csv`, `pooled_nonlinear_synchronized_bootstrap.csv`, `monthly_area_coverage.csv`, `grid_month_direction_evidence.csv`, and `monthly_spatial_synthesis.csv`. February-only pilot diagnostics and maps/plots are retained alongside them.

Area coverage denominator is the sum of mapped, target-valid EXP-02B grid harvested-area denominators over weather-source-compatible yield years in each slot; it is not statewide area of all municipalities. Area-weighted directional shares use each grid's mean observed area over its own paired years and are supplemental. Grid-equal-weight summaries are primary.

Models use the existing monthly T and VPD values directly. Within one grid × slot, the existing grid/calendar-month anomaly convention would subtract a constant; intercept-inclusive OLS correlations, partials, and within-grid standardized pooled fits are invariant to that shift. No new weather transformation or upstream anomaly file was created.

## Limitations and unresolved research questions

Weather begins in 1981 and some grid targets are invalid. Restricted per-grid curvature and pooled common-slope curvature are descriptive, not causal. No year fixed effects are used because those would change the estimand. Spatially adjacent weather and shared annual shocks can reduce effective evidence diversity despite disjoint municipality outcome membership. The 3-/5-year block uncertainty is finite-sample sensitivity, not a guarantee of temporal dependence correction. An agreed smallest-important-effect margin and a subsequent forecasting comparison would be needed before considering simplification; neither is part of EXP-05. Project-wide research-state updates are proposed for Chat review, not applied.

## Reproducibility

`$env:PYTHONPATH='src'; python -m analysis.exp05_conditional_temperature_vpd --phase all`

Validation tests: `$env:PYTHONPATH='src'; python -m pytest src/tests/analysis/test_exp05_conditional_temperature_vpd.py src/tests/analysis/test_exp02b_composition_sensitivity.py src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py -q -p no:cacheprovider` — 22 passed (2026-10-10). New files: `src/analysis/exp05_conditional_temperature_vpd.py`, `src/tests/analysis/test_exp05_conditional_temperature_vpd.py`, and the isolated `outputs/research/exp_05/` tree. No tracked pre-existing file was changed.
