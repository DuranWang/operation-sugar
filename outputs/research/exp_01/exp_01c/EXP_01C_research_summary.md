# EXP-01C Research Summary

EXP-01C adds A*, an equal-weight control restricted to the same 21,669 harvested-area-observed municipality-years as EXP-01B. It separates the A→B change into a support effect (A→A*) and a harvested-area weighting effect (A*→B). Observed zero-area rows remain equally weighted in A* and have zero contribution in B; 1,443 unavailable rows are excluded from both.

## Core cross-variable findings

Across the five pre-specified pairs and 12 months, mean absolute change across Pearson and Spearman is 0.008 for support, 0.071 for weighting, and 0.074 in total. Thus the typical support effect is about one-ninth the weighting effect; A→B changes are predominantly weighting-driven, although signed effects are decomposed coefficient by coefficient rather than treated as a variance share. The largest Pearson support effect is Precipitation ↔ VPD in month 12 (-0.022). The largest matched-support weighting effect is Temperature ↔ Surface soil moisture in month 8 for Pearson (+0.281) and Temperature ↔ Surface soil moisture in month 8 for Spearman (+0.287).

Strict sign reversals across all 120 core coefficients (60 monthly pairs × two methods) number 0 for A→A*, 0 for A*→B, and 0 for A→B. Month-specific coefficients remain the primary interpretation; no pooled correlation is used to override them.

## Temporal persistence

The values below are adjacent / approximately 3-month / 6-month mean Pearson correlations:

- Precipitation: A 0.140/0.026/0.074; A* 0.139/0.021/0.072; B 0.132/-0.012/0.066.
- Temperature: A 0.839/0.741/0.673; A* 0.835/0.736/0.667; B 0.755/0.601/0.490.
- VPD: A 0.725/0.623/0.545; A* 0.713/0.606/0.525; B 0.596/0.449/0.350.
- Surface soil moisture: A 0.844/0.749/0.740; A* 0.847/0.754/0.745; B 0.823/0.727/0.727.
- Solar radiation: A 0.425/0.364/0.316; A* 0.420/0.358/0.312; B 0.248/0.138/0.115.

The qualitative ordering is unchanged at all three horizons in A, A*, and B: surface soil moisture is most persistent, followed by temperature, VPD, solar radiation, and precipitation. Weighting nevertheless materially lowers temperature, VPD, and solar-radiation persistence, while soil-moisture persistence is largely preserved and precipitation remains weak. The largest absolute A*→B change among month-specific lag-1 results is 0.231 for VPD in destination month 11 (pearson, Δ=-0.231). Pooled precipitation lag-1 remains a secondary diagnostic.

## Interpretation for later work

A→A* quantifies sensitivity to excluding unavailable harvested-area municipality-years; A*→B is the clean matched-support estimate of the full weighting rule, including the shift of observed zero-area municipalities from equal contribution to zero contribution. A→B remains the total representation change. These descriptive differences can inform later EXP-01B/EXP-01C interpretation and eventual growth-stage aggregation, where calendar timing and crop footprint may matter, but they do not establish causality, predictive superiority, or a feature keep/drop decision. No yield modelling or EXP-02 analysis was performed.
