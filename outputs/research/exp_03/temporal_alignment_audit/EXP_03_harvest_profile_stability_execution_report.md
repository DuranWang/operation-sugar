# EXP-03 Harvest-Profile Stability Audit Execution Report

## Files created

- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\EXP_03_harvest_profile_stability_audit.md`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\season_coverage_audit.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\normalized_harvest_profiles.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\season_profile_metrics.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\profile_distance_summary.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\temporal_trend_summary.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\early_vs_late_profile_comparison.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\early_vs_late_summary.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\representative_season_selection.csv`
- Seven figures under `D:\Desktop\Operation Sugar\outputs\research\exp_03\temporal_alignment_audit\figures`.

## Command and validation

- Main command: `py -3 -m analysis.exp03_harvest_profile_stability_audit --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-03 audit tests: **5 passed**.
- Combined analysis and UNICA ETL regression suite: **244 passed**, with two pre-existing warnings.
- The first combined-suite attempt encountered Windows permission errors only while creating pytest temporary directories; it was rerun with an isolated approved temporary location and passed completely.
- Python compilation passed and all seven generated figures were visually inspected.
- All required structural, normalization, quantile-order, range, chronology, deterministic-selection, and source-reconciliation checks passed.

## Scope boundary

No mechanization causal analysis, yield stratification, weather alignment, weather–yield analysis, historical profile backcast, or final temporal-alignment selection was performed.
