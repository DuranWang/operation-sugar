# EXP-02A Phase 0 Execution Report

## Scope and status

Phase 0 is complete. The run reconstructed and validated the source-aware 1974–2025 municipality annual-yield panel, measured history support, evaluated the full candidate-gate grid, and produced the requested tables and figures. It did **not** select a final eligibility gate, fit trends, create residuals, run EXP-02B, or alter EXP-01 outputs.

## Files created

- `D:\Desktop\Operation Sugar\src\analysis\exp02a_yield_support_audit.py`
- `D:\Desktop\Operation Sugar\src\tests\analysis\test_exp02a_yield_support_audit.py`
- `D:\Desktop\Operation Sugar\data\processed\analysis\exp_02a_yield_support_audit\source_aware_annual_yield_panel_1974_2025.csv`
- All Phase 0 tables, figures, and reports under `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02a_phase0`.

No pre-existing tracked source or data file was modified.

## Commands and validation

- Main run: `py -3 -m analysis.exp02a_yield_support_audit --project-root "D:\Desktop\Operation Sugar"` with `PYTHONPATH=src`.
- Focused Phase 0 tests cover source-symbol parsing, yield validity, 0/0 exclusion, support spans and gaps, gate boundaries, observed-area denominators, annual reconciliation, and gate-summary reconciliation.
- The focused Phase 0 tests plus the relevant EXP-01S source-aware harvested-area regression tests passed: **27 passed**.
- Four generated figures were visually inspected for readable labels, legends, ranges, and plotted content.

## Data and source-semantics validation

- Raw authoritative workbook: `data/raw/tabela5457.xlsx`; sheets `Quantidade produzida` and `Área colhida`.
- Processed reconciliation input: `data/processed/sp_sugarcane_annual.csv`.
- Panel: 642 municipalities × 52 calendar years = 33,384 unique municipality-year rows.
- Both variables contain 21,822 numeric-positive rows, 3 numeric-zero rows, 8,857 explicit-zero (`-`) rows, and 2,702 unavailable (`...`) rows.
- Production and harvested-area status disagree in 0 rows.
- There are 21,822 valid yield rows. All three numeric 0/0 rows are excluded. No unavailable value is converted to zero.
- Every valid source-aware yield matches the processed `yield_tch` value.

## Outputs and cautions

The full Cartesian grid contains 216 gates, with yearly support retained for every gate. A six-row representative tightening sequence is included only to make the trade-off readable; it is not a recommendation. Harvested-area coverage is the retained share of the observed-only municipality area total for each year, not coverage of latent true statewide production.

The current 642-municipality universe includes places that did not exist as independent municipalities throughout the early period. Therefore, early missing histories may reflect municipality formation and reporting availability as well as agricultural inactivity. The repository provides coordinates but no authoritative historical region classification, so no region labels were invented.

## Decisions returned to Chat

1. Minimum valid-yield years.
2. Minimum first-to-last valid calendar span.
3. Maximum permitted internal gap.
4. The desired balance between long historical support and retention of the 1990–2025 observed harvested-area footprint.
5. Whether a separately reported recent/shorter-history stratum is needed.
