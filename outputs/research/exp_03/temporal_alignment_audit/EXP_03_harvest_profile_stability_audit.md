# EXP-03 Harvest-Profile Structural Stability Audit

## Scope and data inventory

This is a pre-EXP-03 temporal-alignment audit only. It does not build yield strata, align weather, backcast profiles, or select a final temporal-alignment method.

- Canonical UNICA input: `D:\Desktop\Operation Sugar\data\processed\unica\crushing\unica_biweekly_crush.csv`.
- Source resolution: biweekly São Paulo crushing observations, aggregated to the repository's 13 crop-season-relative months (starting April and ending April remain separate).
- Comparable complete seasons: **16**, from **10-11** through **25-26**.
- Partial/incomparable seasons: **1** — 26-27; excluded and explicitly retained in the coverage audit.
- Each complete season has 24 reports, all 13 relative months, normalized shares summing to one, and totals reconciling both the source and existing cumulative-crush output.
- No trustworthy annual São Paulo mechanization series was found locally, so the optional mechanization context was not run.

Monthly quantiles use linear interpolation within the crossing relative-month bin, treating that month's crushing as uniformly distributed inside the bin. This avoids forcing every percentile to an integer month and is applied identically to every season.

## Season metrics

| season | harvest_center_month | median_harvest_month | harvest_window_80_months | harvest_window_50_months | hhi_concentration | tv_from_average_profile | wasserstein_from_average_months | yoy_tv_distance | yoy_wasserstein_months |
|---|---|---|---|---|---|---|---|---|---|
| 10-11 | 4.8706 | 4.7562 | 6.0589 | 3.4242 | 0.1247 | 0.0512 | 0.2000 |  |  |
| 11-12 | 4.8555 | 4.7771 | 5.1227 | 2.9827 | 0.1438 | 0.0785 | 0.2895 | 0.1083 | 0.2709 |
| 12-13 | 5.7231 | 5.6726 | 5.6797 | 3.2374 | 0.1314 | 0.1329 | 0.7039 | 0.1511 | 0.8676 |
| 13-14 | 5.3628 | 5.3269 | 6.2839 | 3.7426 | 0.1212 | 0.0862 | 0.3087 | 0.1011 | 0.4062 |
| 14-15 | 4.9504 | 4.8462 | 5.7479 | 3.2977 | 0.1296 | 0.0309 | 0.1163 | 0.0919 | 0.4124 |
| 15-16 | 5.6707 | 5.3961 | 6.5592 | 3.7671 | 0.1122 | 0.0987 | 0.6058 | 0.1260 | 0.7203 |
| 16-17 | 5.0721 | 4.9502 | 6.3938 | 3.5925 | 0.1184 | 0.0817 | 0.1715 | 0.1228 | 0.5986 |
| 17-18 | 5.1617 | 5.0009 | 5.9938 | 3.3107 | 0.1236 | 0.0370 | 0.1069 | 0.0643 | 0.1397 |
| 18-19 | 4.7885 | 4.5837 | 6.0404 | 3.3931 | 0.1261 | 0.0623 | 0.2863 | 0.0779 | 0.3732 |
| 19-20 | 4.9688 | 4.8775 | 5.6174 | 3.2973 | 0.1323 | 0.0382 | 0.1258 | 0.0824 | 0.2458 |
| 20-21 | 4.7017 | 4.6708 | 5.5290 | 3.3268 | 0.1335 | 0.0613 | 0.3633 | 0.0418 | 0.2671 |
| 21-22 | 4.5265 | 4.4844 | 4.9910 | 2.8796 | 0.1494 | 0.1103 | 0.5430 | 0.0836 | 0.2517 |
| 22-23 | 5.0985 | 4.9541 | 5.5932 | 3.1620 | 0.1353 | 0.0632 | 0.1108 | 0.1057 | 0.5720 |
| 23-24 | 5.3687 | 5.2415 | 6.1786 | 3.6415 | 0.1197 | 0.0582 | 0.3055 | 0.0841 | 0.3175 |
| 24-25 | 4.8434 | 4.7092 | 5.7606 | 3.3572 | 0.1290 | 0.0453 | 0.2216 | 0.0910 | 0.5253 |
| 25-26 | 5.0765 | 4.9953 | 5.6548 | 3.1705 | 0.1300 | 0.0348 | 0.0813 | 0.0610 | 0.2371 |

## Temporal drift summary

| metric_label | first_value | last_value | first_to_last_change | linear_slope_per_decade | linear_r_squared | spearman_rho_with_time | spearman_p_value |
|---|---|---|---|---|---|---|---|
| Weighted mean harvest month | 4.8706 | 5.0765 | 0.2059 | -0.1742 | 0.0628 | -0.1647 | 0.5421 |
| Median harvest month | 4.7562 | 4.9953 | 0.2391 | -0.1792 | 0.0717 | -0.1765 | 0.5133 |
| 10–90% harvest window | 6.0589 | 5.6548 | -0.4040 | -0.1651 | 0.0336 | -0.2441 | 0.3622 |
| 25–75% harvest window | 3.4242 | 3.1705 | -0.2538 | -0.0831 | 0.0254 | -0.1765 | 0.5133 |
| HHI concentration | 0.1247 | 0.1300 | 0.0053 | 0.0025 | 0.0167 | 0.1647 | 0.5421 |
| TV from observed-period average | 0.0512 | 0.0348 | -0.0164 | -0.0212 | 0.1189 | -0.3147 | 0.2352 |
| Wasserstein from observed-period average | 0.2000 | 0.0813 | -0.1187 | -0.1031 | 0.0677 | -0.2765 | 0.2999 |

Statistical significance is not used as proof of stability. The slopes, effect sizes, time-series shape, and early-versus-late profile overlap are interpreted together.

## Early versus late observed profiles

- First half: **10-11–17-18**; second half: **18-19–25-26**; **8 seasons per half**.
- Early-versus-late TV: **0.0500**.
- Early-versus-late Wasserstein distance: **0.2868 relative months**.
- Late-minus-early harvest-center shift: **-0.2868 months**.
- Late-minus-early HHI: **+0.0075**.

The most average-distant season is **12-13** (TV **0.1329**, Wasserstein **0.7039 months**). The largest year-to-year movement occurs in **12-13** (TV **0.1511**, Wasserstein **0.8676 months**).

## Plain-language audit findings

1. **Available history:** 16 comparable complete seasons are available; the ongoing 26-27 season is partial and excluded.
2. **Harvest center:** there is no consistent earlier-or-later drift. The first-to-last center change is **+0.206 months**, while the fitted trend is **-0.174 months per decade** and the late-half average is **-0.287 months** relative to the early half. The differing signs and oscillating series indicate episodic movement, not a persistent directional shift.
3. **Width and concentration:** the first-to-last 10–90% and 25–75% windows change by **-0.404** and **-0.254 months**; HHI changes by **+0.0053**. Variation is visible, but no persistent widening, narrowing, or concentration regime is evident.
4. **Distance from average:** median season-to-average TV is **0.0618** and median Wasserstein distance is **0.2540 months**. The maximum values are concentrated in specific seasons rather than sustained through the later sample.
5. **Movement pattern:** changes are chiefly episodic. The 12-13 profile is both the furthest from average and the largest year-to-year movement; it is not followed by a persistent separated regime.
6. **Does averaging hide structure?** averaging hides real season-specific deviations, particularly 12-13, 15-16, and 21-22, but the early and late mean profiles remain strongly overlapping and do not show an obvious regime split.
7. **EXP-03 implication:** within the observed modern period, a fixed average profile is a reasonable candidate, provided year-specific overlap-period profiles remain a robustness check. This is not yet a final alignment selection.
8. **Historical uncertainty:** the audit contains no comparable profile evidence for the 1970s–1990s, so stability in this sample cannot validate earlier decades.

## Methodological recommendation — Outcome A

Within the observed 2010–11 to 2025–26 period, the fixed-profile approximation appears defensible as an EXP-03 candidate: harvest-center movement is small and non-directional, window width and HHI fluctuate without a persistent regime change, most seasons remain close to the observed-period mean, and early-versus-late averages strongly overlap. The appropriate next design step is to evaluate a fixed harvest-relative alignment while retaining year-specific profiles as an overlap-period robustness check. This modern-period finding does not by itself authorize or validate backcasting the profile to 1974.

This recommendation concerns whether a fixed observed-period average profile is a candidate method. It does **not** select the final EXP-03 temporal alignment.

Even if the 2010–11 to 2025–26 modern sample is stable, that cannot establish that São Paulo's harvest profile was equally stable in the 1970s–1990s. No comparable profile observations cover those earlier IBGE decades, so full-history backcasting remains an untestable extrapolation.

## Validation and boundaries

- Unique season × crop-month keys, nonnegative shares, monotonic cumulative profiles, ordered quantiles, valid HHI/TV ranges, chronological season ordering, deterministic representative selection, and source-total reconciliation all passed.
- No causal mechanization inference or pre-specified structural break was imposed.
- No yield stratification, weather–yield analysis, profile backcast, or final temporal-alignment choice was performed.
- Work stops here for methodological review.
