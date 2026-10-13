# EXP-05B — moisture-conditioned temperature/VPD synthesis

EXP-05B examined observational associations between frozen annual ERA5-grid sugarcane yield residuals and monthly temperature/VPD, conditional on **preselected antecedent 28–100 cm ERA5 soil moisture**. Every one of the 16 yield-relative month-slots was analyzed separately. The modifier is a candidate moisture-background proxy, not a measured drought threshold or verified crop water stress. All 76 original eligible grids were retained in every bootstrap fit.

## Conditional overlap versus response modification

Adding antecedent soil moisture as an additive covariate changes some grid-level T/VPD partial correlations, but not uniformly or dramatically. Across the primary grid-month series, median incremental R² for S beyond T+VPD is 0.0126 and the median absolute VPD partial-correlation shift is 0.0173. In Aug–Nov_(t−1), median VPD|T,S remains negative (−0.087, −0.098, −0.063, −0.080), with 64%–72% of grids negative in each slot. This is descriptive conditional overlap; it is neither proof of an independent moisture mechanism nor a variable-redundancy decision.

The response-modification question is less coherent. The primary pooled dry-minus-wet VPD slope contrast (t/ha per within-grid VPD SD) is:

| Month | Point | 3-year-block 95% pointwise interval | 5-year-block interval |
|---|---:|---:|---:|
| Aug_(t−1) | +0.348 | [−0.112, +0.871] | [−0.120, +0.797] |
| Sep_(t−1) | −0.300 | [−1.458, +0.284] | [−1.453, +0.162] |
| Oct_(t−1) | +0.321 | [−0.608, +1.025] | [−0.681, +0.982] |
| Nov_(t−1) | +0.113 | [−0.323, +0.525] | [−0.426, +0.439] |

Negative dry-minus-wet values match the preregistered stronger-negative-under-relatively-dry direction. Only September's *point* estimate has that sign within the previously flagged Aug–Nov window. All four intervals include zero; so do the primary T contrasts there. Across all 16 slots, nine VPD point contrasts are negative and seven positive, but none of the 3- or 5-year-block pointwise intervals for either atmospheric contrast exclude zero. This is **not** an equivalence finding; no smallest-important-effect margin was specified. The P2 interaction incremental R² over additive P1 is 0.00025–0.00181 in Aug–Nov, small descriptively, and its nonnegative interval is partly a nesting property rather than directional evidence.

The fixed Q2 curvature check, Q2′ including T×V, and the model allowing grid-specific *additive* T/V/S slopes all preserve a mixed Aug–Nov direction. P50=12 and fixed-composition target point estimates preserve the focal primary signs, while the m−1 soil-moisture, deeper-layer, and rainfall modifiers sometimes reverse them. Paired robustness intervals and all month estimates appear in `robustness_comparisons.csv` and `monthly_interaction_uncertainty.csv`. The alternate modifiers are comparisons, not a search for a preferred water proxy.

## Spatial and temporal caution

Grid-level VPD|T,S is negative in roughly two-thirds to three-quarters of the 76 grids during Aug–Nov, leaving substantial spatial heterogeneity. The pooled common interaction should not be assigned to every grid. No single left-out calendar year flips the four primary pooled VPD contrast signs, but the synchronized block intervals are broad. The fixed-grid resampling produced 1,000 valid attempts per scheme/slot/scenario with zero numerical failures; it therefore supports transparent uncertainty accounting, not a claim of precision or causal identification. Same-year Y is reused across different month-slots, and the focal window was outcome-informed by EXP-05. Multiple slot/model comparisons are not independent confirmatory tests.

**Descriptive classification: heterogeneous/mixed conditional pattern, without clear interval-supported moisture modification.** The data do not supply a consistently negative dry-minus-wet association across the Aug–Nov window. Do not tune the moisture layer or lag to make that pattern appear, infer physiological drought effects, or make feature keep/drop decisions here. Predictive relevance and any practical-effect threshold need separate preapproved work.
