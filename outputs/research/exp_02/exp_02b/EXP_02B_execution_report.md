# EXP-02B Execution Report

## Status

EXP-02B completed using the approved common-support fixed weights, P50=10 primary residuals, and P50=12 robustness residuals. Work stopped before EXP-03 / EXP-04.

## Files created or modified

- `src/analysis/exp02b_composition_sensitivity.py`
- `src/tests/analysis/test_exp02b_composition_sensitivity.py`
- `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\actual_vs_fixed_grid_residuals.csv`
- `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\matched_support_weight_details.csv`
- Diagnostics: `composition_effect_diagnostics.csv`, `composition_effect_by_grid_ranked.csv`, `composition_effect_by_year_ranked.csv`, `composition_effect_grid_year_ranked.csv`, `composition_tv_relationship.csv`, `composition_effect_concentration.csv`, and `p50_10_vs_p50_12_robustness.csv` under `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b`.
- Reports, representative-grid selection, and eight figures under `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b`.

## Inputs and fixed-weight construction

- Source-aware annual yield/area panel: `data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv`.
- Municipality residuals: `data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv` (`P50=10` primary; `P50=12` robustness).
- Approved fixed weights: `outputs/research/exp_02/exp_02b/common_support_reference_weights.csv`, recomputed from the validated common-year sets during execution.
- Actual weights use contemporaneous observed harvested area on matched residual support. Approved fixed weights remain unchanged under full membership and are renormalized only over a strict matched-support subset.

## Validation boundaries

- Same municipality-year support for actual and fixed weighting.
- Same support and composition weights for P50=10 and P50=12.
- Actual and fixed weights normalized on all valid grid-years.
- Valid grid-years per specification: **3773** total, **3694** multi-municipality, and **79** single-municipality.
- **1880** full-membership grid-years used the approved fixed weights directly; **1893** subset-support grid-years used the authorized renormalization.
- **283** grid-years per specification had no matched residual support; none was fabricated.
- Four single-municipality grids reported separately.
- Explicit zero and unavailable source statuses retain their established meanings.
- No weather-based tuning or later experiment was performed.

## Commands and tests

- Main command: `py -3 -m analysis.exp02b_composition_sensitivity --stage full --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-02B test file: **11 passed**.
- Complete analysis regression suite, including EXP-02A and source-semantics checks: **88 passed**.
- Figure set visually inspected after generation.
