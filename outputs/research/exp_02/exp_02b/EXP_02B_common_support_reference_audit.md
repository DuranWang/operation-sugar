# EXP-02B Common-Support Reference-Weight Audit

## Scope

This audit implements only the Chat-approved common-support reference construction for the 74 multi-municipality grids. It does not calculate actual-weight or fixed-weight grid residuals and does not run the composition experiment.

For grid `g`, a common year requires every EXP-02A-eligible municipality assigned to the grid to have observed harvested-area status and the within-grid observed-area denominator to be positive. Candidate weights are the municipality's mean annual within-grid share over exactly those common years.

## Validation

- Multi-municipality grids audited: **74**.
- Grids with at least one common reference year: **74**.
- Grids with zero common reference years: **0**.
- Municipality fixed-weight rows created: **507**.
- Grids with common years whose candidate fixed weights fail to sum to one within numerical tolerance: **0**.
- Common reference years across grids: minimum **18**, median **43.5**, maximum **52**.

## Support distribution and observed-area footprint

The footprint column is the sum of each grid's mean annual share of statewide observed harvested area over 1974–2025. It is not a latent true-area share.

| support_group | grids | mean_common_reference_years | minimum_common_reference_years | maximum_common_reference_years | share_of_statewide_observed_area |
|---|---|---|---|---|---|
| <10 | 0 |  |  |  | 0.0000 |
| 10-14 | 0 |  |  |  | 0.0000 |
| 15-19 | 1 | 18.0000 | 18.0000 | 18.0000 | 0.2273 |
| >=20 | 73 | 40.7260 | 20.0000 | 52.0000 | 99.7467 |

The support groups jointly represent **99.9740%** of mean statewide observed harvested area. The remaining **0.0260%** belongs to the four single-municipality grids outside this multi-municipality reference audit.

The lowest-support grid is `era5_-23.00_-47.00`: 8 eligible municipalities, 18 common years, first/last common years 1993–2014, calendar span 22, and **0.2273%** mean observed statewide harvested-area footprint.

## Per-grid output

`common_support_grid_audit.csv` reports, for every multi-municipality grid, the eligible municipality count, number of common reference years, first and last common year, common-period calendar span, candidate-weight sum and reconciliation flag, and observed harvested-area footprint.

`common_support_reference_weights.csv` contains the municipality candidate weights and their common-year share ranges. No candidate weight is applied to a residual in this audit.

## Stop

The common-support audit is complete. EXP-02B stops here for Chat interpretation; the actual-vs-fixed residual experiment remains unexecuted.
