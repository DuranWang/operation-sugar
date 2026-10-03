# EXP-02A Phase 1 Execution Report

## Scope

Phase 1 completed under the approved 511-municipality gate. No EXP-02B code or weather-based tuning was executed, and no winning detrending model was selected.

## Files created or modified

- `src/analysis/exp02a_detrending.py`
- `src/tests/analysis/test_exp02a_detrending.py`
- Reproducible model output under `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02a_phase1`.
- Diagnostics, reports, and plots under `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02a_phase1`.

No unrelated EXP-01 source file was modified.

## Commands and tests

- Main command: `py -3 -m analysis.exp02a_detrending --project-root <repository>` with `PYTHONPATH=src`.
- Focused Phase 1 unit and integration tests validate lambdas, normal equations, missing-year residual behavior, exact gate reconciliation, grid endpoints, source semantics, and output-key uniqueness.
- Phase 1, Phase 0, and relevant EXP-01S source-semantics regression tests passed: **38 passed**.
- Nine generated figures were visually inspected; residual lines correctly break across unobserved years while fitted trend lines retain the approved latent annual grid.

## Reconciliation

- Eligible municipalities: 511.
- Observed residual-bearing municipality-years: 20931.
- Latent annual-grid rows: 23166.
- Four specifications: linear, p50_10, p50_12, p50_6.
- Missing/unavailable/undefined yield years have no residual.

## Main diagnostic outputs

- `residual_pairwise_diagnostics.csv`
- `residual_scale_diagnostics.csv`
- `gap_stratum_summary.csv` and `gap_stratum_pairwise_diagnostics.csv`
- `internal_gap_inventory.csv` and `gap_proximity_diagnostics.csv`
- `endpoint_diagnostics.csv`
- `history_length_diagnostics.csv`
- `calendar_year_diagnostics.csv`
- ranked municipality and municipality-year disagreement tables
- deterministic representative-selection table and plots

## Warnings / interpretation

Latent trend values across missing years are consequences of the approved smoothness assumption, not reconstructed observed yields. The gap `>10` comparison is diagnostic and does not authorize automatic exclusion or history splitting. Residual-scale differences are not model-selection evidence.
