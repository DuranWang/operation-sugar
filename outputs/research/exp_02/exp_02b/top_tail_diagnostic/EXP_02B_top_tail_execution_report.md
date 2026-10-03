# EXP-02B Top-Tail Diagnostic Execution Report

## Completed work

- Selected the completed P50=10 top 10 multi-municipality grid-years by absolute Delta.
- Decomposed every event over its exact matched municipality support.
- Reconciled actual/fixed weights and municipality contributions.
- Audited endpoint, missing-gap, long-gap-history, residual-extremeness, source-status, and fixed-weight-renormalization conditions.
- Cross-checked the same event keys under completed P50=12 results.
- Created one stacked municipality-contribution plot for the maximum event.

## Outputs

- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\top10_event_summary.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\top10_municipality_contributions.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\top10_artifact_checks.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\top10_p50_12_crosscheck.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\maximum_event_municipality_contributions.png`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\top_tail_diagnostic\EXP_02B_top_tail_diagnostic_report.md`

## Boundaries

No residual, support, actual-weight, fixed-weight, or weather analysis was recomputed or redesigned. Work stopped before EXP-03 / EXP-04.

## Commands and tests

- Main command: `py -3 -m analysis.exp02b_top_tail_diagnostic --project-root <repository>` with `PYTHONPATH=src`.
- Focused top-tail diagnostic tests: **4 passed**.
- Complete analysis regression suite: **92 passed**.
- Python compilation check passed; the maximum-event contribution figure was visually inspected.
