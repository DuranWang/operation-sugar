# EXP-01A Research Summary

## Scope

EXP-01A describes overlap and temporal dependence among municipality-level monthly weather predictors for São Paulo, 1990–2025. It uses 277,344 municipality-month observations without yield data or harvested-area weighting. Correlations are descriptive: they do not establish causality, predictive redundancy, or feature keep/drop decisions.

## Main cross-variable findings

- Temperature and mean VPD are consistently positively associated, but the monthly Pearson relationship varies materially (mean 0.73; range 0.55 to 0.88). They overlap, but are not interchangeable.
- Precipitation and 0–7 cm soil moisture are positively associated in every month (mean Pearson 0.40; range 0.25 to 0.48). Together with its cross-month persistence, this pattern is consistent with soil moisture carrying information beyond contemporaneous rainfall.
- Temperature and mean-daily solar radiation are positively related but distinctly month-dependent (mean Pearson 0.52; range 0.35 to 0.73).
- Temperature–surface-soil-moisture and precipitation–VPD relationships remain negative in every calendar month. None of the five core-pair Pearson or Spearman relationships changes sign across months.

## Month dependence and pooled-correlation pitfalls

Month-specific results are primary because pooled estimates can be dominated by the shared annual cycle. The strongest discrepancies include outright sign reversals:

- Precipitation ↔ Mean-daily solar radiation, month 9 (spearman): pooled 0.33 versus monthly -0.78.
- Precipitation ↔ Total solar radiation, month 9 (spearman): pooled 0.33 versus monthly -0.78.
- Precipitation ↔ Mean-daily solar radiation, month 7 (spearman): pooled 0.33 versus monthly -0.75.

For example, pooled precipitation–mean-daily-radiation Pearson correlation is positive even though the strongest monthly discrepancy is negative. This makes the pooled matrix useful as an overview, but unsafe as the sole description of predictor overlap.

## Temporal persistence

- Surface soil moisture is the most persistent variable: mean Pearson dependence is 0.84 for adjacent months and 0.74 six months apart.
- Temperature is also persistent (0.84 adjacent; 0.67 at six months).
- VPD is intermediate (0.73 adjacent; 0.54 at six months).
- Mean-daily solar radiation is weaker but still structured across months (0.42 adjacent; 0.32 at six months).
- Precipitation is short-lived (0.14 adjacent; 0.07 at six months). These labels are descriptive shorthand, not formal classifications.

## Implications for later experiments

EXP-01B should retain the same verified variables and definitions so harvested-area-weighted correlations remain directly comparable with EXP-01A. EXP-01C should compare the weighted and unweighted patterns, especially where seasonality or long persistence may change apparent overlap.

For later growth-stage aggregation, rainfall's short memory suggests that timing and episodic totals may matter more than broad multi-month averaging. Soil moisture and temperature carry substantial dependence across adjacent and distant months, so heavily overlapping stage windows could encode repeated information. VPD and radiation sit between these extremes. These observations motivate careful, pre-specified stage windows and multicollinearity checks; they do not by themselves justify selecting variables or stages.
