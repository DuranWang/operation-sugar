# EXP-02B Fixed-Reference Weight Audit

## Construction checked

For each eligible municipality, the raw fixed reference weight is the time-average of its observed within-grid harvested-area share over usable-status years with a positive observed grid denominator. Grid-year matched-support normalization is not yet applied in this audit.

## History support

- Eligible municipalities represented: **511**.
- Reference observed-year minimum / 10th percentile / median / 90th percentile / maximum: **15 / 33 / 52 / 52 / 52**.
- Municipalities with fewer than 15 reference years: **0**.

## Differential-support reconciliation

- Multi-municipality grids: **74**.
- Raw fixed-weight sums across multi-municipality grids: minimum **1.000000**, median **1.000376**, maximum **1.149543**.
- Absolute deviation from one: median **0.000376**, maximum **0.149543**.
- Multi-municipality grids with absolute deviation above 5%: **16**, representing **14.538%** of mean observed statewide harvested area when grid shares are summed.
- Multi-municipality grids with absolute deviation above 10%: **5**, representing **5.254%** of mean observed statewide harvested area.

The grid-normalized reference weight is retained for audit readability, but the final grid-year calculation follows the handover exactly by renormalizing the raw municipality reference weights over the contemporaneous matched support.

Largest fixed shares in multi-municipality grids:

| grid_id | municipality | ibge_code | eligible_municipalities | reference_observed_years | reference_positive_area_years | fixed_reference_weight_grid_normalized |
|---|---|---|---|---|---|---|
| era5_-24.50_-49.00 | Ribeira | 3542800 | 2 | 31 | 31 | 0.9233 |
| era5_-22.50_-52.50 | Teodoro Sampaio | 3554300 | 2 | 48 | 48 | 0.8982 |
| era5_-23.50_-49.00 | Itaí | 3521804 | 2 | 52 | 52 | 0.8374 |
| era5_-24.00_-49.00 | Itapeva | 3522406 | 2 | 51 | 47 | 0.8260 |
| era5_-23.00_-45.50 | Caçapava | 3508504 | 5 | 52 | 50 | 0.8247 |
| era5_-20.00_-50.00 | Pedranópolis | 3536901 | 2 | 45 | 44 | 0.7581 |
| era5_-23.50_-47.00 | Cabreúva | 3508405 | 3 | 52 | 52 | 0.7345 |
| era5_-23.00_-45.00 | Guaratinguetá | 3518404 | 2 | 34 | 26 | 0.7087 |
| era5_-22.00_-50.50 | Quatá | 3541703 | 7 | 52 | 52 | 0.6919 |
| era5_-23.50_-47.50 | Boituva | 3507001 | 8 | 52 | 51 | 0.6681 |
| era5_-23.00_-48.50 | Botucatu | 3507506 | 4 | 52 | 52 | 0.6274 |
| era5_-21.50_-47.00 | Mococa | 3530508 | 7 | 52 | 52 | 0.6266 |
| era5_-22.50_-49.50 | São Pedro do Turvo | 3550506 | 6 | 52 | 52 | 0.6042 |
| era5_-23.50_-48.50 | Paranapanema | 3535804 | 2 | 42 | 32 | 0.6014 |
| era5_-20.00_-51.00 | Três Fronteiras | 3554904 | 2 | 34 | 25 | 0.5634 |
| era5_-24.50_-48.00 | Pariquera-Açu | 3536208 | 3 | 45 | 41 | 0.5619 |
| era5_-20.50_-49.00 | Olímpia | 3533908 | 4 | 52 | 52 | 0.5570 |
| era5_-20.00_-47.50 | Igarapava | 3520103 | 4 | 52 | 52 | 0.5520 |
| era5_-21.50_-49.50 | Irapuã | 3521507 | 4 | 52 | 52 | 0.5395 |
| era5_-23.00_-48.00 | Cesário Lange | 3511607 | 7 | 52 | 52 | 0.4966 |

This audit does not use weather outcomes and does not tune the reference weights.

## Required stop

The maximum raw reference-weight reconciliation deviation is 14.95%, and the issue is not confined to negligible-footprint grids. It arises because municipality-specific means use differential observed histories; for example, later-observed municipalities can receive a post-entry mean share while longer-history municipalities' means also include earlier years in which those municipalities were absent.

The handover requires returning materially poor differential-support reconciliation to Chat rather than inventing a replacement. EXP-02B therefore stops here before actual-vs-fixed aggregation. Chat must decide whether to accept the specified matched-support renormalization despite this diagnostic, or approve a revised fixed-reference construction such as a common-support/reference-period rule. No alternative is selected in this audit.
