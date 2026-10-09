# EXP-03 Checkpoint 2B — Execution Report

## Implementation and inputs

- Added `src/analysis/exp03_checkpoint2b_spatial_heterogeneity.py`.
- Added `src/tests/analysis/test_exp03_checkpoint2b_spatial_heterogeneity.py`.
- Read existing Checkpoint 1/2 outputs, `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\matched_support_weight_details.csv`, `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02b\actual_vs_fixed_grid_residuals.csv`, the authoritative municipality bridge, and canonical monthly weather.
- Checkpoint 1 and Checkpoint 2 outputs were not overwritten.

## Influence method

For each problematic cell × disagreeing multi-municipality grid, the removed municipality is excluded from both the P50=10 yield-residual aggregate and the matching monthly weather aggregate. Remaining approved annual weights are renormalized. The calculation is reported only when every original paired year remains valid. `high_influence` is descriptive: sign flip, `|delta rho| >= 0.10`, or movement toward the pooled direction by at least 0.10.

## Outputs

`EXP_03_checkpoint2b_execution_report.md`, `EXP_03_checkpoint2b_spatial_heterogeneity_report.md`, `checkpoint2b_disagreeing_grid_municipalities.csv`, `checkpoint2b_disagreeing_grids.csv`, `checkpoint2b_geographic_concentration.csv`, `checkpoint2b_grid_disagreement_frequency.csv`, `checkpoint2b_high_influence_municipality_summary.csv`, `checkpoint2b_municipality_influence.csv`, `checkpoint2b_problematic_cells.csv`, `checkpoint2b_problematic_cells_by_month.csv`, `checkpoint2b_problematic_cells_by_variable.csv`.

## Tests

- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_checkpoint2b_spatial_heterogeneity.py -q` — **5 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **113 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Stop

The audit stops before feature engineering or modeling.
