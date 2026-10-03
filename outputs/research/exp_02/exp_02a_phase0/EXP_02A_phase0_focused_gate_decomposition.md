# EXP-02A Phase 0 Focused Gate Decomposition

## Scope

This supplement applies each requested condition separately, then applies `N >= 15` and calendar span `>= 20` jointly with no gap restriction. “Separately” means the other dimensions use the minimal any-valid-history base (`N >= 1`, span `>= 1`, gap unrestricted). The comparison baseline contains 609 municipalities and 21822 valid municipality-year observations. No gate is selected and no trend is fitted.

## Summary

| case_label | retained_municipalities | municipalities_excluded_vs_any_valid | retained_valid_municipality_years | valid_observations_excluded_vs_any_valid | mean_area_coverage_1974_2025 | minimum_area_coverage_1974_2025 | minimum_coverage_year_1974_2025 | mean_area_coverage_1990_2025 | minimum_area_coverage_1990_2025 | minimum_coverage_year_1990_2025 |
|---|---|---|---|---|---|---|---|---|---|---|
| N >= 15 only | 533 | 76 | 21318 | 504 | 99.953% | 99.581% | 1975 | 99.963% | 99.834% | 1991 |
| Calendar span >= 20 only | 525 | 84 | 21063 | 759 | 99.580% | 98.678% | 2018 | 99.424% | 98.678% | 2018 |
| Maximum internal gap <= 10 only | 531 | 78 | 20051 | 1771 | 98.140% | 95.136% | 2019 | 97.488% | 95.136% | 2019 |
| N >= 15 + calendar span >= 20; gap unrestricted | 511 | 98 | 20931 | 891 | 99.570% | 98.676% | 2018 | 99.416% | 98.676% | 2018 |

## Early-period year-by-year observed-area coverage

| year | N15_only | S20_only | G10_only | N15_S20_GU |
|---|---|---|---|---|
| 1974 | 99.824% | 99.874% | 99.398% | 99.806% |
| 1975 | 99.581% | 99.624% | 99.029% | 99.564% |
| 1976 | 99.905% | 99.923% | 99.496% | 99.894% |
| 1977 | 99.861% | 99.881% | 99.358% | 99.847% |
| 1978 | 99.933% | 99.924% | 99.534% | 99.920% |
| 1979 | 99.946% | 99.945% | 99.545% | 99.934% |
| 1980 | 99.956% | 99.953% | 99.707% | 99.943% |
| 1981 | 99.969% | 99.968% | 99.703% | 99.959% |
| 1982 | 99.967% | 99.966% | 99.641% | 99.955% |
| 1983 | 99.995% | 99.982% | 99.752% | 99.982% |
| 1984 | 99.997% | 99.983% | 99.707% | 99.983% |
| 1985 | 99.987% | 99.974% | 99.722% | 99.973% |
| 1986 | 99.982% | 99.970% | 99.742% | 99.968% |
| 1987 | 99.984% | 99.968% | 99.772% | 99.968% |
| 1988 | 99.972% | 99.959% | 99.809% | 99.959% |
| 1989 | 99.996% | 99.988% | 99.820% | 99.988% |

The complete 1974–2025 year-by-year series, including retained valid municipality counts and area numerators/denominators, is in `focused_gate_decomposition_yearly_coverage.csv`.

## Interpretation without gate selection

- `N >= 15` has the smallest footprint effect: it removes short histories but retains nearly all observed harvested area in every year.
- Span `>= 20` is also almost neutral in 1974–2006, but its coverage declines gradually after 2007 because some materially active recent municipalities have shorter calendar histories.
- Gap `<= 10` has the largest independent effect. Its early-period coverage remains high, but it increasingly excludes observed area after the late 1990s, reaching the lowest coverage in 2019.
- Adding `N >= 15` to span `>= 20` changes the span-only footprint only slightly. Its main additional effect is excluding 14 municipalities and 132 valid observations relative to span `>= 20` alone.

These are descriptive support effects only. They do not establish the final eligibility gate.
