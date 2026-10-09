# EXP-03 Checkpoint 2 — Execution Report

## Implementation

- Added `src/analysis/exp03_checkpoint2_robustness.py`.
- Added `src/tests/analysis/test_exp03_checkpoint2_robustness.py`.
- Read Checkpoint 1 outputs without modifying them.
- Grid-specific Spearman safeguard: at least 15 paired years, chosen from the observed 13–44-year support distribution; 76 of 78 grids qualify.

## Outputs

CSV/report files: `EXP_03_checkpoint2_execution_report.md`, `EXP_03_checkpoint2_report.md`, `categorical_vs_continuous_comparison.csv`, `checkpoint2_robustness_summary.csv`, `cross_grid_spearman_summaries.csv`, `effect_comparison_20_60_20_vs_primary.csv`, `effect_comparison_zscore_vs_primary.csv`, `grid_specific_spearman_correlations.csv`, `grid_year_support_distribution.csv`, `monthly_effects_20_60_20.csv`, `monthly_effects_zscore_pooled.csv`, `monthly_group_summary_20_60_20.csv`, `monthly_group_summary_zscore_pooled.csv`, `pooled_within_grid_rank_associations.csv`, `ranking_history_assignment_sensitivity.csv`, `ranking_history_effect_comparison.csv`, `ranking_history_group_counts.csv`, `ranking_history_monthly_effects.csv`, `ranking_history_monthly_group_summary.csv`, `ranking_history_transition_matrix.csv`, `window_12_vs_16_comparison.csv`, `window_12_vs_16_summary.csv`, `yield_group_assignments_20_60_20.csv`, `yield_group_assignments_zscore_pooled.csv`, `yield_group_counts_20_60_20.csv`, `yield_group_counts_zscore_pooled.csv`.

Figures: `figures/directional_consistency_heatmap.png`, `figures/median_grid_spearman_heatmap.png`, `figures/pooled_within_grid_rank_heatmap.png`, `figures/primary_high_minus_low_heatmap.png`, `figures/robustness_20_60_20_heatmap.png`, `figures/robustness_zscore_pooled_heatmap.png`.

## Tests

- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_checkpoint2_robustness.py -q` — **6 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **108 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Stop

Checkpoint 2 completed without entering feature engineering or modeling.
