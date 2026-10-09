# EXP-03 Extended Checkpoint 1 — Execution Report

## Files changed

- `src/etl/weather/build_combined_monthly_weather.py`
- `src/analysis/exp01a_municipality_weather_correlation.py`
- `src/analysis/exp03_yield_stratified_monthly_weather.py`
- `src/tests/etl/weather/test_build_combined_monthly_weather.py`
- `src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py`
- Canonical combined-weather annual CSV and validation JSON files for 1981–1989.
- Extended audit and exploratory outputs under `D:\Desktop\Operation Sugar\outputs\research\exp_03\yield_stratified_monthly_weather\checkpoint1`.

## Commands and validation

- Rebuilt each 1981–1989 canonical annual file with the established municipality bridge.
- Reran EXP-03 Checkpoint 1 with the canonical 1981–2025 gate.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py -q` — **5 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **102 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/etl/weather/test_build_combined_monthly_weather.py src/tests/feature_engineering/test_month_level_weather.py -q` — **15 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Implementation issue resolved

The 1982 NASA source contains valid ISO dates in both `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS` form. The loader now explicitly accepts mixed ISO renderings while retaining strict filename-period, duplicate-key, and calendar-year validation. No observations or weather values were changed.

## Boundary

Grouping remains independent of weather availability. Only complete 16-month grid-year windows from 1982–2025 enter the exploratory contrasts. Earlier residuals remain part of rank construction and coverage diagnostics but are not imputed.
