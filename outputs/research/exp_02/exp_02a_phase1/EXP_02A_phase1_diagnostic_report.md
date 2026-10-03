# EXP-02A Phase 1 Detrending Diagnostics

## Status and scope

**PHASE 1 COMPLETED.** The approved gate was applied exactly: `n_valid_years >= 15`, calendar span `>= 20`, and no hard internal-gap exclusion. The run compares only Linear, P50=10, P50=12, and aggressive P50=6. It does not select a model, use weather results, split long gaps, or implement EXP-02B.

## Eligibility and output validation

- Eligible municipalities: **511**; expected: 511.
- Valid observed yield rows among eligible municipalities: **20931**.
- Annual smoother-grid rows: **23166**; specification-grid rows: **92664**.
- Residuals are present only on observed valid-yield years; latent fitted trends may exist on internal missing grid years.
- Grid endpoints equal each municipality's first and last valid years.
- Municipality × year × specification output keys are unique.

## Lambda validation

| specification | p50_years | lambda | response_at_p50 |
|---|---|---|---|
| p50_10 | 10.00000000 | 6.85410197 | 0.50000000 |
| p50_12 | 12.00000000 | 13.92820323 | 0.50000000 |
| p50_6 | 6.00000000 | 1.00000000 | 0.50000000 |

## Residual scale

| specification | n | residual_sd | residual_iqr | mean_absolute_residual | residual_rmse | mean_municipality_residual_sd |
|---|---|---|---|---|---|---|
| linear | 20931 | 11.0556 | 11.3580 | 7.8653 | 11.0554 | 10.7506 |
| p50_10 | 20931 | 6.8480 | 5.5489 | 4.4238 | 6.8479 | 6.6193 |
| p50_12 | 20931 | 7.2554 | 6.0429 | 4.7400 | 7.2553 | 7.0305 |
| p50_6 | 20931 | 5.4157 | 4.0257 | 3.3817 | 5.4156 | 5.1904 |

Residual scale is descriptive, not a model-selection score. A smaller residual variance under a more flexible trend is expected mechanically and is not evidence of superiority.

## Pairwise residual agreement

| specification_a | specification_b | pearson_correlation | spearman_correlation | sign_agreement | mean_absolute_difference | p95_difference | maximum_absolute_difference |
|---|---|---|---|---|---|---|---|
| linear | p50_10 | 0.7259 | 0.6493 | 0.7177 | 5.6159 | 12.2367 | 48.1387 |
| linear | p50_12 | 0.7560 | 0.6849 | 0.7356 | 5.3363 | 11.5921 | 47.0449 |
| linear | p50_6 | 0.6437 | 0.5508 | 0.6701 | 6.2895 | 14.0144 | 73.3440 |
| p50_10 | p50_12 | 0.9952 | 0.9912 | 0.9546 | 0.5665 | 1.2760 | 6.6193 |
| p50_10 | p50_6 | 0.9635 | 0.9309 | 0.8627 | 1.5207 | 3.4425 | 25.2053 |
| p50_12 | p50_6 | 0.9373 | 0.8886 | 0.8247 | 2.0158 | 4.5444 | 31.8246 |

Across Linear/P50=10/P50=12 comparisons, Pearson residual correlation ranges from **0.7259** to **0.9952**. Comparisons involving aggressive P50=6 range from **0.6437** to **0.9635**. This documents sensitivity without designating a winner.

## Internal-gap diagnostics

| stratum | municipalities | observations | mean_cross_spec_range | median_cross_spec_range | p95_cross_spec_range | maximum_cross_spec_range |
|---|---|---|---|---|---|---|
| 0 | 268 | 12313 | 6.2422 | 4.9342 | 16.0139 | 59.7046 |
| >10 | 63 | 1640 | 8.0543 | 6.2178 | 20.9827 | 60.3350 |
| 1-5 | 127 | 5229 | 7.2721 | 5.4741 | 20.2134 | 49.0937 |
| 6-10 | 53 | 1749 | 8.7074 | 6.5079 | 25.1638 | 73.3440 |

The `>10` group has mean cross-specification residual range **8.0543 t/ha**, versus **6.2422 t/ha** for `gap = 0` (difference **+1.8121 t/ha**, ratio **1.290**). This is a diagnostic comparison, not an automatic reason to split or exclude histories.

For Linear versus P50=10, residual correlation is **0.6672** in `gap >10` versus **0.7428** in `gap = 0`. For P50=10 versus P50=12 it remains **0.9943** versus **0.9955**, respectively.

Observed-year proximity to an internal gap:

| stratum | municipalities | observations | mean_cross_spec_range | p95_cross_spec_range | maximum_cross_spec_range |
|---|---|---|---|---|---|
| no_internal_gap | 268 | 12313 | 6.2422 | 16.0139 | 59.7046 |
| far_4plus_y | 243 | 6576 | 6.9799 | 18.8470 | 52.8452 |
| near_2_3y | 243 | 1217 | 9.5298 | 25.5879 | 73.3440 |
| adjacent_1y | 243 | 825 | 10.8680 | 28.6273 | 60.3350 |

Detailed pairwise results by gap stratum and an inventory of every internal gap are supplied as CSV outputs.

## Endpoint and history-length diagnostics

| stratum | municipalities | observations | mean_cross_spec_range | p95_cross_spec_range | maximum_cross_spec_range |
|---|---|---|---|---|---|
| endpoint | 511 | 1022 | 10.5436 | 29.3425 | 59.7046 |
| distance_1 | 510 | 980 | 7.8392 | 22.1184 | 37.8651 |
| distance_2 | 510 | 954 | 6.9801 | 17.8593 | 35.3593 |
| distance_3_5 | 510 | 2818 | 6.3318 | 16.0219 | 42.4143 |
| distance_6plus | 511 | 15157 | 6.6217 | 17.5852 | 73.3440 |

| stratum | municipalities | observations | mean_cross_spec_range | p95_cross_spec_range | maximum_cross_spec_range |
|---|---|---|---|---|---|
| 40-51 | 173 | 7889 | 6.8544 | 18.5265 | 49.0937 |
| 30-39 | 87 | 2962 | 7.4309 | 21.2014 | 73.3440 |
| 15-19 | 15 | 254 | 6.8243 | 18.3922 | 48.2389 |
| 52 | 146 | 7592 | 6.3829 | 16.3738 | 45.3027 |
| 20-29 | 90 | 2234 | 7.6308 | 20.5315 | 59.7046 |

## Calendar-year and unusually large disagreement

The calendar year with the highest mean cross-specification residual range is **1974** at **14.6439 t/ha**. Full year-by-year scale and disagreement diagnostics are provided in `calendar_year_diagnostics.csv`.

Municipalities with the largest mean cross-specification residual range:

| municipality | ibge_code | n_observed | gap_stratum | mean_cross_spec_range | p95_cross_spec_range | maximum_cross_spec_range |
|---|---|---|---|---|---|---|
| Pereira Barreto | 3537404 | 41 | 6-10 | 19.6277 | 32.9065 | 33.3915 |
| Irapuru | 3521606 | 39 | 6-10 | 18.7702 | 36.5579 | 39.6318 |
| Amparo | 3501905 | 52 | 0 | 18.2979 | 27.7282 | 28.0489 |
| Potirendaba | 3540804 | 51 | 0 | 17.8939 | 43.4094 | 47.8640 |
| Caçapava | 3508504 | 50 | 1-5 | 17.8077 | 40.3011 | 49.0937 |
| Uru | 3555901 | 19 | 1-5 | 16.8240 | 31.9830 | 33.1750 |
| Gastão Vidigal | 3516804 | 28 | 1-5 | 16.4923 | 35.5296 | 36.4804 |
| Jaci | 3524501 | 33 | 6-10 | 15.9031 | 49.1766 | 73.3440 |
| Dracena | 3514403 | 42 | 1-5 | 15.2183 | 29.6166 | 34.0946 |
| Fernando Prestes | 3515608 | 52 | 0 | 14.7205 | 29.4075 | 30.9646 |

The observation-level ranked file reports the municipality-years with the largest disagreement without imposing an unapproved materiality threshold.

## Representative plots

| selection_reason | municipality | ibge_code | n_valid_years | calendar_span_years | max_internal_gap_years | mean_cross_spec_range |
|---|---|---|---|---|---|---|
| long_complete_high_area | Morro Agudo | 3531902 | 52 | 52 | 0 | 4.4350 |
| shorter_eligible_history | São João do Pau d'Alho | 3549300 | 17 | 42 | 25 | 5.5050 |
| small_internal_gaps | Guaíra | 3517406 | 48 | 50 | 2 | 7.6038 |
| long_internal_gap | Murutinga do Sul | 3532108 | 26 | 52 | 22 | 14.0716 |
| high_harvested_area | Piracicaba | 3538709 | 52 | 52 | 0 | 7.1080 |
| large_cross_spec_disagreement | Pereira Barreto | 3537404 | 41 | 52 | 9 | 19.6277 |

Selection is deterministic and rule-based. The plots are diagnostics, not a basis for choosing the visually most attractive specification.

## Interpretation boundaries and questions for Chat

- A residual is a detrended yield anomaly, not a measured weather-caused component.
- P50=6 is an aggressive sensitivity case near the multi-year climate-variability band; lower residual scale is not evidence that it is preferable.
- Long gaps were bridged only by the stated smoothness assumption for latent fitted values. No residual was manufactured inside a gap.
- Chat should interpret whether the observed gap-stratum, endpoint, and aggressive-smoother disagreement is practically material. No quantitative materiality threshold was invented here.
- No choice between Linear, P50=10, and P50=12 is made in this report.
