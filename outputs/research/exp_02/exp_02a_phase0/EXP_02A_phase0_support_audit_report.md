# EXP-02A Phase 0 Municipality Yield-Support Audit

## Status

**PHASE 0 COMPLETED.** This audit builds the source-aware 1974–2025 municipality annual-yield panel and compares candidate history-support gates. It does not choose a gate, fit a trend, create residuals, aggregate to weather grids, or run EXP-02B.

## Inputs and validity rule

- Raw authoritative source: `D:\Desktop\Operation Sugar\data\raw\tabela5457.xlsx`, sheets `Quantidade produzida` and `Área colhida`.
- Processed reconciliation source: `D:\Desktop\Operation Sugar\data\processed\sp_sugarcane_annual.csv`.
- Unit of observation: municipality × calendar year, 1974–2025.
- Raw numeric values remain numeric; `-` is explicit zero; `...` remains unavailable.
- Yield is valid only when harvested area is observed and strictly positive and production is observed. Numeric or explicit production zero is an observed zero, but 0/0 is undefined. No unavailable value is converted to zero.
- Harvested-area coverage uses the observed-only denominator: the sum of symbol-aware reported municipality area in that year. It is not latent true statewide coverage.

## Source validation

- Rows: 33,384; municipalities: 642; duplicate keys: 0.
- Valid yield rows: 21,822; numeric source rows: 21,825; explicit-zero rows: 8,857; unavailable rows: 2,702.
- Production/area status mismatches: 0.
- Numeric 0/0 rows excluded from valid yield: 3.
- No negative or infinite source-aware yield was introduced, and every valid source-aware yield matches the processed `yield_tch`.

## Municipality history support

- Municipalities with no valid yield: 33; municipalities with all 52 years valid: 146; municipalities with valid 2025 yield: 506.
- Valid-yield municipality count by year ranges from 271 to 530.
- `n_valid_years` 10th / median / 90th percentiles: 6.0 / 39.0 / 52.0.
- `calendar_span_years` 10th / median / 90th percentiles: 8.1 / 45.0 / 52.0.
- `max_internal_gap_years` 10th / median / 90th percentiles among defined histories: 0.0 / 0.0 / 13.0.

Municipalities with the largest internal gaps are listed in `municipality_support.csv`; the leading cases are:

| municipality | n_valid_years | calendar_span_years | max_internal_gap_years | mean_observed_area_share_1990_2025 |
|---|---|---|---|---|
| Caieiras | 10 | 52 | 42 | 0.000000 |
| São Paulo | 15 | 51 | 36 | 0.000001 |
| Barão de Antonina | 6 | 38 | 31 | 0.000001 |
| Ribeirão Branco | 7 | 52 | 31 | 0.000000 |
| Cananéia | 15 | 52 | 30 | 0.000000 |
| Álvares Florence | 23 | 52 | 29 | 0.000661 |
| Itaberá | 12 | 42 | 29 | 0.000021 |
| Sarapuí | 9 | 38 | 29 | 0.000013 |

## One-dimensional candidate trade-offs

Each row varies one dimension while applying only a minimal one-valid-year / one-year-span base for the other dimensions. The unrestricted gap row therefore describes municipalities with any valid yield, not all 642 municipalities.

| dimension | candidate_value | retained_municipalities | retained_valid_observation_share | mean_annual_area_coverage_1990_2025 | minimum_annual_area_coverage_1990_2025 |
|---|---|---|---|---|---|
| minimum_valid_years | 10 | 551 | 0.986 | 1.000 | 0.998 |
| minimum_valid_years | 15 | 533 | 0.977 | 1.000 | 0.998 |
| minimum_valid_years | 20 | 496 | 0.948 | 0.993 | 0.985 |
| minimum_valid_years | 25 | 456 | 0.907 | 0.976 | 0.947 |
| minimum_valid_years | 30 | 406 | 0.845 | 0.957 | 0.914 |
| minimum_valid_years | 35 | 352 | 0.765 | 0.897 | 0.837 |
| minimum_calendar_span_years | 15 | 557 | 0.987 | 1.000 | 0.999 |
| minimum_calendar_span_years | 20 | 525 | 0.965 | 0.994 | 0.987 |
| minimum_calendar_span_years | 25 | 507 | 0.949 | 0.987 | 0.971 |
| minimum_calendar_span_years | 30 | 482 | 0.921 | 0.975 | 0.953 |
| minimum_calendar_span_years | 35 | 435 | 0.860 | 0.927 | 0.894 |
| minimum_calendar_span_years | 40 | 409 | 0.830 | 0.912 | 0.867 |
| maximum_internal_gap_years | 1 | 395 | 0.717 | 0.891 | 0.825 |
| maximum_internal_gap_years | 2 | 425 | 0.764 | 0.918 | 0.858 |
| maximum_internal_gap_years | 3 | 440 | 0.790 | 0.924 | 0.864 |
| maximum_internal_gap_years | 5 | 468 | 0.835 | 0.942 | 0.897 |
| maximum_internal_gap_years | 10 | 531 | 0.919 | 0.975 | 0.951 |
| maximum_internal_gap_years | unrestricted | 609 | 1.000 | 1.000 | 1.000 |

## Representative combined gates

These gates are a reporting sequence, not a recommendation or optimization result.

| gate_id | retained_municipalities | retained_valid_municipality_years | retained_valid_observation_share | mean_annual_area_coverage_1990_2025 | minimum_annual_area_coverage_1990_2025 | area_coverage_2025 |
|---|---|---|---|---|---|---|
| G10_S15_GU | 544 | 21445 | 0.983 | 1.000 | 0.998 | 1.000 |
| G15_S20_G10 | 448 | 19291 | 0.884 | 0.969 | 0.938 | 0.939 |
| G20_S25_G5 | 380 | 17227 | 0.789 | 0.929 | 0.870 | 0.873 |
| G25_S30_G3 | 336 | 15767 | 0.723 | 0.902 | 0.823 | 0.824 |
| G30_S35_G2 | 293 | 14276 | 0.654 | 0.857 | 0.778 | 0.778 |
| G35_S40_G1 | 268 | 13203 | 0.605 | 0.822 | 0.730 | 0.730 |

The full 216-rule Cartesian grid is retained in `candidate_gate_summary_full_grid.csv`, and every gate-year result is in `candidate_gate_yearly_support_full_grid.csv`. This makes the three gate dimensions auditable without selecting the rule that maximizes city count or footprint.

## Geographic and support cautions

The available repository metadata contains municipality coordinates but no authoritative mesoregion labels. `municipality_history_support_map.png` provides a visual check for geographic concentration, but this audit does not invent regional classifications. Early-year gaps also reflect the constant current 642-municipality universe and the historical availability of municipalities, not only agricultural non-production.

Explicit-zero histories represent observed inactivity and must remain distinct from unavailable reporting. A retained municipality contributes a residual only in later Phase 1 years with valid observed yield; this audit does not bridge gaps or create yield values.

## Decisions returned to Chat

1. Select the minimum valid-yield years from the reported trade-off grid.
2. Select the minimum first-to-last valid calendar span.
3. Select the maximum internal gap that the future smoother may bridge.
4. Decide how strongly the gate should prioritize long 1974–2025 history versus preserving the 1990–2025 observed harvested-area footprint.
5. Decide whether municipalities with late starts but material recent footprint require a separately reported shorter-history stratum.

Formal detrending remains on hold pending those decisions.
