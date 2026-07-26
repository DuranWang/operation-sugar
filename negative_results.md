# Negative Results

This document records statistically unsuccessful or non-generalizing modeling results in Operation Sugar.

A negative result is not treated as a failed research effort.

Within Operation Sugar, negative results are retained when they:

- answer a clearly defined research question;
- are produced through reproducible datasets and validation procedures;
- reveal model instability, overfitting, or non-generalizing relationships;
- establish stronger benchmarks for future work;
- prevent repeated investigation of unsupported specifications.

The results documented here are based on the Version 1.5.0 and Version 1.5.1 modeling studies.

Detailed model definitions and complete results are documented in:

- `statistical_experiments.md`
- `modeling_framework.md`
- `month_level_model_findings.md`

---

# Research Context

The Version 1.5 modeling program evaluated two distinct prediction tasks.

## Harvest-Block Prediction

The harvest-block task tests whether weather information improves prediction of São Paulo crushing volumes within non-overlapping harvest aggregation blocks.

The primary benchmark is Block-Only OLS.

This model uses:

- an intercept;
- harvest-block fixed effects;
- no weather predictors.

The benchmark represents the historical harvest-calendar profile.

Harvest-block weather models are considered successful only if they improve leave-one-season-out predictive performance relative to Block-Only OLS.

## Complete-Season Prediction

The complete-season task tests whether aggregate weather improves prediction of total crushing over an entire harvest season.

Each season contributes one observation.

The benchmark is the training-season historical mean.

Complete-season models do **not** use harvest-block fixed effects because the target is already summed across all harvest blocks and the dataset contains no within-season block dimension.

The complete-season weather model is considered successful only if it improves leave-one-season-out predictive performance relative to the training-season mean benchmark.

## Scope

The reported conclusions are limited to:

- 16 complete matched harvest seasons;
- São Paulo harvest-block crushing volumes for the block-level models;
- São Paulo complete-season crushing totals for the season-total model;
- the evaluated aggregate and month-level weather variables;
- the evaluated linear and Ridge specifications;
- leave-one-season-out out-of-sample performance.

---

# Negative Result 1 — Harvest-Block Aggregate Weather OLS — Aggregate Weather OLS

## Research Question

> Do total growing-season rainfall and average growing-season temperature improve harvest-block crushing prediction beyond historical harvest timing?

---

## Specification

The Aggregate Weather OLS model includes:

- growing-season total rainfall;
- growing-season average temperature;
- harvest-block fixed effects.

The model is evaluated using leave-one-season-out cross-validation across five harvest aggregation horizons.

---

## Result

Aggregate Weather OLS underperformed Block-Only OLS at every horizon.

Average RMSE performance relative to Block-Only was:

\[
-2.45\%
\]

Negative values indicate worse out-of-sample RMSE than the benchmark.

---

## Diagnostic Interpretation

The aggregate weather variables were not sufficiently informative to improve held-out-season prediction.

Compressing the full September–April growing season into:

- one rainfall total; and
- one average temperature

removes the timing and distribution of weather conditions within the season.

The result also shows that statistically plausible complete-sample coefficients are not sufficient evidence of predictive value.

A relationship may appear reasonable in-sample while failing to generalize to unseen seasons.

---

## Research Value

This result established the first formal weather benchmark in Operation Sugar.

It showed that future weather models must improve on a strong historical harvest-profile baseline rather than merely demonstrate nonzero weather coefficients.

It also motivated the transition from aggregate weather summaries to month-level weather representations.

---

# Negative Result 2 — Complete-Season Aggregate Weather OLS

## Research Question

> Do aggregate growing-season rainfall and temperature improve prediction of complete-season crushing totals?

---

## Specification

The complete-season weather model includes:

- growing-season total rainfall;
- growing-season average temperature;
- an intercept.

It is compared with a training-season mean benchmark.

Each harvest season contributes one observation.

No harvest-block fixed effects are included.

This is intentional.

The complete-season target is:

\[
y_s
=
\sum_b y_{s,b}
\]

where all within-season harvest blocks have already been summed into one seasonal total.

Because the complete-season dataset contains no `harvest_block_order` dimension, block fixed effects are neither meaningful nor identifiable for this task.

The appropriate comparison is therefore:

1. a mean-only benchmark; and
2. an aggregate weather model using season-level rainfall and temperature.


---

## Result

The aggregate weather model did not outperform the training-season historical mean.

It produced:

- higher cross-validated RMSE;
- higher cross-validated MAE;
- lower cross-validated \(R^2\).

Positive complete-sample weather coefficients did not generalize to held-out seasons.

---

## Diagnostic Interpretation

The complete-season sample contains only 16 observations.

With such a small sample, coefficient estimates are highly sensitive to individual seasons.

Aggregate weather variables did not provide stable predictive structure beyond the historical average level of crushing.

This result should not be interpreted as a comparison against the harvest-calendar profile.

The harvest-calendar benchmark applies only to block-level prediction, where multiple within-season observations make harvest-block fixed effects meaningful.

For complete-season prediction, the relevant benchmark is the training-season mean because each season contributes only one total-crushing observation.

---

## Research Value

This result demonstrated that the failure of aggregate weather was not limited to the harvest-block prediction task.

Aggregate rainfall and temperature also failed to improve prediction of complete-season crushing totals relative to the training-season mean benchmark.

The two experiments use different benchmarks because they operate at different observational levels:

- harvest-block models compare against historical harvest timing;
- complete-season models compare against the historical mean level of total crushing.

The finding narrowed the research direction toward:

- more temporally structured weather variables;
- more biologically targeted outcomes;
- larger historical samples;
- stronger structural assumptions.

---

# Negative Result 3 — Rainfall Month-Level OLS

## Research Question

> Does preserving September–April monthly rainfall improve harvest-block prediction?

---

## Specification

Rainfall Month-Level OLS includes:

- `rainfall_sep`;
- `rainfall_oct`;
- `rainfall_nov`;
- `rainfall_dec`;
- `rainfall_jan`;
- `rainfall_feb`;
- `rainfall_mar`;
- `rainfall_apr`;
- growing-season average temperature control;
- harvest-block fixed effects.

The weather design has nine predictors.

Every outer fold is full rank, and the observed weather condition numbers are moderate.

---

## Result

Rainfall Month-Level OLS substantially underperformed Block-Only OLS at every horizon.

RMSE performance relative to Block-Only was:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -16.40% |
| 2 | -24.06% |
| 3 | -24.44% |
| 4 | -33.08% |
| 5 | -43.05% |

The model became progressively worse as the aggregation horizon increased.

---

## Diagnostic Interpretation

The model failure was not caused by:

- rank deficiency;
- an unidentified design matrix;
- extreme numerical ill-conditioning.

The weather design was estimable in every outer fold.

The failure therefore reflects statistical overfitting and unstable coefficient estimation rather than a linear-algebra error.

As the horizon increases:

- the number of observations decreases;
- the same nine weather coefficients must be estimated;
- coefficient variance becomes more damaging.

---

## Research Value

This result provides direct evidence that preserving monthly rainfall structure is not sufficient by itself.

More detailed temporal resolution can increase variance faster than it increases useful signal.

The result also justified the use of Ridge regularization.

---

# Negative Result 4 — Temperature Month-Level OLS

## Research Question

> Does preserving September–April monthly temperature improve harvest-block prediction?

---

## Specification

Temperature Month-Level OLS includes:

- `temperature_sep`;
- `temperature_oct`;
- `temperature_nov`;
- `temperature_dec`;
- `temperature_jan`;
- `temperature_feb`;
- `temperature_mar`;
- `temperature_apr`;
- growing-season total rainfall control;
- harvest-block fixed effects.

The weather design has nine predictors and remains full rank in every outer fold.

---

## Result

Temperature Month-Level OLS underperformed Block-Only OLS at every horizon.

RMSE performance relative to Block-Only was:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -8.94% |
| 2 | -13.30% |
| 3 | -13.51% |
| 4 | -18.56% |
| 5 | -19.37% |

Temperature OLS performed better than Rainfall OLS, but still failed to improve out-of-sample prediction.

---

## Diagnostic Interpretation

Temperature contains more stable structure than rainfall in the current sample.

However, the unregularized monthly temperature coefficients remain too variable to generalize reliably.

The model again becomes less competitive as the number of observations decreases at longer horizons.

---

## Research Value

This result separated two ideas that would otherwise be conflated:

1. temperature may contain more predictive structure than rainfall; and
2. unregularized temperature coefficients may still overfit.

The result motivated Temperature Month-Level Ridge rather than rejection of temperature as a research variable.

---

# Negative Result 5 — Rainfall Month-Level Ridge

## Research Question

> Can Ridge regularization stabilize the month-level rainfall model enough to outperform the historical harvest profile?

---

## Specification

Rainfall Month-Level Ridge uses the same weather variables as Rainfall Month-Level OLS.

The estimator applies:

- nested leave-one-season-out cross-validation;
- fold-specific weather standardization;
- unpenalized intercept;
- unpenalized harvest-block fixed effects;
- penalized weather coefficients;
- alpha grid from \(10^{-4}\) to \(10^8\).

---

## Result

Ridge substantially improved the rainfall model relative to OLS.

RMSE improvement relative to Rainfall Month-Level OLS was:

| Horizon | Ridge improvement versus OLS |
|---:|---:|
| 1 | 12.91% |
| 2 | 17.72% |
| 3 | 17.94% |
| 4 | 22.64% |
| 5 | 26.42% |

However, Rainfall Month-Level Ridge still underperformed Block-Only OLS:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -1.37% |
| 2 | -2.07% |
| 3 | -2.11% |
| 4 | -2.95% |
| 5 | -5.26% |

---

## Diagnostic Interpretation

Nested LOSO selected the maximum alpha in 75% of outer folds.

For those folds, effective weather degrees of freedom were numerically close to zero.

The median effective weather degrees of freedom was approximately zero.

This indicates that Ridge improved performance primarily by removing unstable rainfall contributions and collapsing the model toward Block-Only.

A small number of folds retained nonzero rainfall complexity, but this did not produce stable incremental predictive value.

---

## Research Value

Rainfall Ridge is a successful regularization experiment but an unsuccessful incremental prediction model.

It demonstrates that:

- Ridge can repair severe OLS overfitting;
- improved estimation does not imply that the weather variables add predictive value;
- a well-regularized model may legitimately conclude that the safest weather contribution is approximately zero.

---

# Negative Result 6 — Temperature Month-Level Ridge

## Research Question

> Can Ridge regularization convert the stronger temperature structure into stable incremental predictive value?

---

## Specification

Temperature Month-Level Ridge uses:

- September–April monthly temperatures;
- growing-season total rainfall control;
- harvest-block fixed effects;
- nested LOSO alpha selection;
- fold-specific scaling;
- partial Ridge regularization.

---

## Result

Temperature Month-Level Ridge was the strongest weather-based model and ranked second at every horizon.

It substantially improved on Temperature Month-Level OLS.

However, it still underperformed Block-Only OLS:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -0.56% |
| 2 | -0.85% |
| 3 | -0.86% |
| 4 | -1.21% |
| 5 | -1.49% |

---

## Diagnostic Interpretation

Nested LOSO selected the maximum alpha in 81.25% of outer folds.

Median effective weather degrees of freedom was approximately zero.

The nonzero mean effective degrees of freedom was driven primarily by a small number of influential folds.

The `21-22` held-out fold was especially influential.

When `21-22` was removed from the training sample, selected alpha decreased sharply and the model retained substantially more weather complexity.

This shows that the apparent temperature relationship among the remaining seasons was not stable to the inclusion of `21-22`.

---

## Research Value

Temperature Ridge is a near-benchmark result rather than a successful weather model.

It establishes that:

- temperature contains more stable structure than rainfall;
- regularization can recover most of the performance lost by OLS;
- the remaining temperature signal is still not sufficiently stable to beat the historical harvest profile.

This model should remain the strongest weather reference specification for future comparisons.

---

# Negative Result 7 — Joint Month-Level Ridge

## Research Question

> Do monthly rainfall and temperature provide complementary predictive information when modeled jointly?

---

## Specification

Joint Month-Level Ridge includes:

- eight monthly rainfall predictors;
- eight monthly temperature predictors;
- harvest-block fixed effects.

Aggregate controls are excluded because they are exact linear combinations of the monthly predictors.

Joint OLS is not estimated.

Each outer LOSO training fold contains 15 seasons.

After centering, the maximum weather rank is:

\[
15 - 1 = 14
\]

The joint model contains 16 weather predictors, so unregularized OLS is not uniquely identified.

Ridge provides a unique penalized solution.

---

## Result

Joint Month-Level Ridge underperformed:

- Block-Only OLS;
- Temperature Month-Level Ridge;
- Rainfall Month-Level Ridge

at every horizon.

RMSE performance relative to Block-Only was:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -6.75% |
| 2 | -10.09% |
| 3 | -10.26% |
| 4 | -14.16% |
| 5 | -17.54% |

The performance disadvantage widened as the aggregation horizon increased.

---

## Diagnostic Interpretation

The joint model displayed severe penalty-selection instability.

Across every horizon:

- 81.25% of outer folds selected the maximum alpha;
- 6.25% selected the minimum alpha;
- median effective weather degrees of freedom was approximately zero;
- maximum effective weather degrees of freedom was approximately 13.98.

The model therefore switched between two extremes:

1. removing almost all weather contribution; and
2. retaining almost every identifiable weather direction.

The `23-24` held-out fold was especially influential.

When `23-24` was held out:

- every horizon selected the minimum alpha;
- effective weather degrees of freedom rose to approximately 13.98;
- the near-unregularized relationship performed poorly on the held-out season.

The joint rainfall–temperature relationship learned from the remaining seasons did not generalize to `23-24`.

---

## Research Value

This result rejects the assumption that combining two weakly stable feature groups must improve prediction.

Adding rainfall to temperature:

- increased dimensionality;
- changed the most influential season;
- introduced extreme penalty instability;
- reduced out-of-sample performance.

The joint model shows that feature combination can create new instability rather than complementary signal.

---

# Cross-Experiment Lessons

## More Features Did Not Produce More Predictive Information

The progression from aggregate to monthly and joint weather representations increased feature count and temporal detail.

Out-of-sample performance did not improve.

The strongest model remained Block-Only OLS.

This demonstrates that feature expansion should be justified by incremental predictive value rather than by detail alone.

---

## Rank and Numerical Stability Are Not the Same as Generalization

Rainfall and Temperature Month-Level OLS were full rank in every outer fold.

Their failure was not a numerical identification problem.

A model can be:

- mathematically estimable;
- numerically stable;
- scientifically interpretable;

and still fail to generalize.

---

## Regularization Can Reveal the Absence of Stable Signal

Ridge materially improved every unregularized monthly model.

However, selected penalties frequently forced weather contributions toward zero.

The role of Ridge was therefore not only to estimate coefficients more efficiently.

It also provided evidence that the incremental weather signal was not stable across seasons.

---

## Mean Diagnostics Can Hide Fold Instability

Mean effective weather degrees of freedom was positive for all Ridge models.

Median effective weather degrees of freedom was approximately zero.

The difference occurred because a small number of influential folds retained large amounts of model complexity.

Future diagnostics should report:

- mean;
- median;
- minimum;
- maximum;
- alpha-boundary fractions;
- influential held-out seasons.

---

## Benchmarks Must Match the Prediction Unit

For harvest-block prediction, Block-Only OLS won every horizon.

Future block-level weather or agronomic models should not be evaluated only against:

- a mean benchmark;
- an intercept-only model;
- an in-sample fit.

They should demonstrate incremental value beyond the historical harvest-block profile.

For complete-season prediction, harvest-block fixed effects are not applicable because each season contributes one total observation.

The appropriate complete-season benchmark is therefore the training-season historical mean.

Benchmark design must match the observational unit and target definition.

---

# Interpretation Boundaries

The negative results do not establish that weather is unimportant to sugarcane.

They establish a narrower conclusion:

> Within the available 16-season historical sample and the evaluated linear specifications, aggregate and month-level growing-season weather variables do not provide stable incremental out-of-sample predictive value for São Paulo harvest-block crushing volumes beyond the historical harvest-block profile.

For the separate complete-season task, aggregate growing-season rainfall and temperature also fail to improve out-of-sample prediction relative to the training-season mean benchmark.

The experiments do not rule out:

- nonlinear weather responses;
- weather thresholds;
- interactions supported by stronger structural constraints;
- stage-specific weather windows;
- extreme-temperature effects;
- water-deficit duration;
- municipality-level heterogeneity;
- regional heterogeneity;
- harvest-timing targets;
- cane-yield targets;
- sugar-yield targets;
- ATR or CCS outcomes;
- satellite-derived crop indicators;
- relationships identifiable with a larger historical sample.

---

# Consequences for Future Research

The negative results change the Operation Sugar research roadmap.

Future work should avoid adding additional unconstrained month-level linear specifications without new information or stronger structure.

Priority should shift toward:

1. biologically defined stage-specific windows;
2. extreme-weather and persistence features;
3. nonlinear response functions;
4. spatial heterogeneity;
5. alternative agricultural outcomes;
6. larger historical samples;
7. structural regularization informed by agronomy.

The purpose of future work is not to search indefinitely for a specification that beats the benchmark.

The purpose is to test whether new data, targets, or structural assumptions provide information that the current models cannot capture.

---

# Terminology and Benchmark Distinction

Two aggregate weather models appear in the Version 1.5 research program.

## Harvest-Block Aggregate Weather OLS

Target:

```text
block_crush_tonnes
```

Predictors:

- harvest-block fixed effects;
- growing-season total rainfall;
- growing-season average temperature.

Benchmark:

```text
Block-Only OLS
```

## Complete-Season Aggregate Weather OLS

Target:

```text
season_total_crush_tonnes
```

Predictors:

- intercept;
- growing-season total rainfall;
- growing-season average temperature.

Benchmark:

```text
Training-season mean
```

The complete-season model does not include harvest-block fixed effects because all within-season blocks have already been aggregated into one seasonal total.

---

# Reproducibility

The Version 1.5.1 comparison can be reproduced with:

```bash
python -m src.modeling.month_level_model_comparison
python -m src.visualization.month_level_model_reporting
```

Primary comparison outputs are stored under:

```text
data/processed/modeling/month_level_baseline_results/
```

Primary reporting figures are stored under:

```text
docs/figures/
```

Detailed findings are documented in:

```text
docs/research/month_level_model_findings.md
```
