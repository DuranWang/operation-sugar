# EXP-01C Execution Report

## Status

**COMPLETED.** A* was implemented as an equal-weight matched-support control and compared with existing EXP-01A (A) and EXP-01B (B) outputs. EXP-01A and EXP-01B were not rerun. No statewide weather series, yield model, feature decision, or EXP-02 analysis was created.

## Files created or modified

- `src/analysis/exp01c_astar_matched_support_comparison.py`
- `src/tests/analysis/test_exp01c_astar_matched_support_comparison.py`
- EXP-01C tables, figures, research summary, and validation artifacts under `D:\Desktop\Operation Sugar\data\processed\analysis\exp_01c_astar_matched_support_comparison`
- this execution report under `outputs/experiments/exp_01c_astar_matched_support_comparison/`

## Validation gates

All 17 validation checks passed. Exact counts: A = 23,112 municipality-years; A* = B observed support = 21,669; positive area = 16,570; observed zero area retained in A* = 5,099; unavailable excluded = 1,443; A* month rows = 260,028. Every eligible key has all 12 months, canonical IBGE keys match exactly, and three non-blocking municipality-name metadata variants remain recorded by EXP-01B.

A* and B use identical observed-support keys. A* applies ordinary Pearson/Spearman with pandas average-tie ranks; it does not use area magnitude. For lag-1, weather lags are constructed on the complete panel before destination-year support filtering, exactly preserving EXP-01B's month and December→January alignment.

## Principal results

- Largest Pearson support effect: `nasa_total_rainfall_mm ↔ vpd_mean_kpa`, month 12, Δ = -0.0216.
- Largest Spearman support effect: `nasa_total_rainfall_mm ↔ vpd_mean_kpa`, month 12, Δ = -0.0250.
- Largest Pearson weighting effect: `nasa_average_temperature_c ↔ soil_moisture_0_to_7cm_m3_m3`, month 8, Δ = +0.2812.
- Largest Spearman weighting effect: `nasa_average_temperature_c ↔ soil_moisture_0_to_7cm_m3_m3`, month 8, Δ = +0.2868.
- Core-pair sign reversals across Pearson plus Spearman: support = 0, weighting = 0, total = 0.
- Cross-month persistence is compared for all five required variables at adjacent, ~3-month, and 6-month horizons in `exp_01c_temporal_persistence_comparison.csv`.
- Month-specific and overall lag-1 A/A*/B results are in their respective comparison files; pooled overall lag-1 remains secondary.

## Commands and tests

- Main execution: `py -3 -m analysis.exp01c_astar_matched_support_comparison --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-01C plus relevant EXP-01A/EXP-01B regression tests: **39 passed** (9 EXP-01C, 16 EXP-01A, 14 EXP-01B).
- A full-suite attempt reached **186 passed** with **34 setup errors** caused solely by the managed Windows environment denying pytest access to its temporary directory; no test assertion failed. Repointing `--basetemp` inside the workspace encountered the same environment-level ACL restriction.

## Primary outputs

- `validation/exp_01c_matched_support_validation.csv`
- `astar/astar_monthly_pair_correlations.csv`
- `astar/astar_core_pair_monthly_correlations.csv`
- `astar/astar_cross_month_dependence_summary.csv` and five 12×12 Pearson/Spearman/count matrix sets
- `astar/astar_lag1_persistence_by_month.csv` and `astar_lag1_persistence_overall.csv`
- `summary/exp_01c_core_pair_monthly_comparison.csv`
- `summary/exp_01c_core_pair_summary.csv`
- `summary/exp_01c_temporal_persistence_comparison.csv`
- `summary/exp_01c_lag1_by_month_comparison.csv`
- `summary/exp_01c_lag1_overall_comparison.csv`
- `summary/exp_01c_largest_changes.csv`
- `EXP_01C_research_summary.md`

## Warnings

Correlations are descriptive, not causal or predictive validation. A*→B includes the intended effect of giving observed zero-area municipalities zero statistical contribution in B. Month-specific results are primary; pooled lag-1 is only a diagnostic. The only execution warning is the unrelated full-suite pytest temporary-directory ACL issue described above; all relevant experiment tests passed. No unresolved method ambiguity or data failure remains.
