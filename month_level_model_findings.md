# Operation Sugar v1.5 — Month-Level Weather Model Findings

## Research Objective

This study evaluates whether September–April monthly weather features provide stable incremental out-of-sample predictive value for São Paulo harvest-block crushing volumes beyond the historical harvest-block profile.

The dependent variable is the total tonnes crushed within harvest block \(b\) of season \(s\):

\[
y_{s,b}
=
\text{crush tonnes for season } s
\text{ in harvest block } b
\]

Five harvest aggregation horizons are evaluated:

| Horizon | Complete seasons | Observations | Blocks per season |
|---:|---:|---:|---:|
| 1 | 16 | 192 | 12 |
| 2 | 16 | 96 | 6 |
| 3 | 16 | 64 | 4 |
| 4 | 16 | 48 | 3 |
| 5 | 16 | 32 | 2 |

For `h=5`, only the first 10 base harvest periods are used. The final two base periods are excluded because they do not form a complete five-period block.

---

## Evaluation Design

All reported performance metrics are based on leave-one-season-out (LOSO) cross-validation.

### Ordinary least squares models

For each outer fold:

1. One complete harvest season is held out.
2. The model is fitted on the remaining 15 seasons.
3. Predictions are generated for every harvest block in the held-out season.
4. Predictions are combined across all 16 outer folds.

### Ridge models

Ridge models use nested leave-one-season-out cross-validation:

1. **Outer LOSO** estimates out-of-sample generalization performance.
2. **Inner LOSO** selects the Ridge penalty parameter.
3. `StandardScaler` is fitted separately within every training fold.
4. Weather scaling is performed at the season level because weather observations repeat across harvest blocks.
5. The intercept and harvest-block fixed effects are unpenalized.
6. Only weather coefficients receive the Ridge penalty.

The Ridge penalty grid is:

\[
\alpha
\in
10^{-4}, \ldots, 10^{8}
\]

with 49 logarithmically spaced values.

Primary metrics are:

- LOSO RMSE
- LOSO MAE
- LOSO \(R^2\)

---

## Models Evaluated

Seven models are compared.

### 1. Aggregate Weather OLS

Predictors:

- Growing-season total rainfall
- Growing-season average temperature
- Harvest-block fixed effects

### 2. Block-Only OLS

Predictors:

- Harvest-block fixed effects only

This model represents the historical harvest-calendar profile without weather information.

### 3. Rainfall Month-Level OLS

Predictors:

- September–April monthly rainfall
- Growing-season average temperature control
- Harvest-block fixed effects

### 4. Rainfall Month-Level Ridge

Same weather specification as Rainfall Month-Level OLS, estimated using nested LOSO Ridge.

### 5. Temperature Month-Level OLS

Predictors:

- September–April monthly temperature
- Growing-season total rainfall control
- Harvest-block fixed effects

### 6. Temperature Month-Level Ridge

Same weather specification as Temperature Month-Level OLS, estimated using nested LOSO Ridge.

### 7. Joint Month-Level Ridge

Predictors:

- September–April monthly rainfall
- September–April monthly temperature
- Harvest-block fixed effects

Aggregate rainfall and temperature controls are excluded because they are exact linear combinations of the monthly predictors.

Joint OLS is not estimated. With 15 training seasons in each outer fold, centering restricts the maximum weather rank to:

\[
15 - 1 = 14
\]

The joint model contains 16 weather predictors, so an unregularized joint design cannot be uniquely identified within outer LOSO folds.

---

## Seven-Model LOSO Results

The model ranking is identical across all five aggregation horizons.

| Rank | Model | Mean RMSE difference versus Block-Only |
|---:|---|---:|
| 1 | Block-Only OLS | 0.00% |
| 2 | Temperature Month-Level Ridge | -1.00% |
| 3 | Aggregate Weather OLS | -2.45% |
| 4 | Rainfall Month-Level Ridge | -2.75% |
| 5 | Joint Month-Level Ridge | -11.76% |
| 6 | Temperature Month-Level OLS | -14.73% |
| 7 | Rainfall Month-Level OLS | -28.20% |

Negative values indicate worse LOSO RMSE than Block-Only OLS.

### Horizon-level RMSE

| Model | h=1 | h=2 | h=3 | h=4 | h=5 |
|---|---:|---:|---:|---:|---:|
| Block-Only OLS | 5,913,106 | 9,595,373 | 14,269,552 | 16,046,071 | 19,462,955 |
| Temperature Month-Level Ridge | 5,946,166 | 9,676,748 | 14,392,661 | 16,240,365 | 19,753,791 |
| Aggregate Weather OLS | 5,992,356 | 9,790,057 | 14,564,054 | 16,509,769 | 20,230,519 |
| Rainfall Month-Level Ridge | 5,994,145 | 9,794,436 | 14,570,678 | 16,520,156 | 20,485,990 |
| Joint Month-Level Ridge | 6,312,283 | 10,563,692 | 15,733,436 | 18,318,241 | 22,876,934 |
| Temperature Month-Level OLS | 6,441,468 | 10,871,152 | 16,197,818 | 19,024,180 | 23,232,186 |
| Rainfall Month-Level OLS | 6,882,775 | 11,903,875 | 17,756,407 | 21,354,171 | 27,841,724 |

---

## Finding 1 — Historical Harvest-Block Shape Is the Strongest Predictor

Block-Only OLS achieves the lowest LOSO RMSE at every horizon.

The model uses no weather variables. Its predictive power comes entirely from the average historical crushing profile associated with each harvest-block position.

This indicates that the stable seasonal shape of the São Paulo harvest calendar explains most of the predictable block-level variation in crushing volumes.

The result should not be interpreted as evidence that weather has no effect on sugarcane production. It shows that, for the evaluated target and linear specifications, weather does not improve prediction beyond the historical block profile.

---

## Finding 2 — Temperature Contains More Stable Structure Than Rainfall

Temperature Month-Level Ridge is the strongest weather-based model and ranks second at every horizon.

Its RMSE remains close to Block-Only:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -0.56% |
| 2 | -0.85% |
| 3 | -0.86% |
| 4 | -1.21% |
| 5 | -1.49% |

Rainfall Month-Level Ridge performs worse:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -1.37% |
| 2 | -2.07% |
| 3 | -2.11% |
| 4 | -2.95% |
| 5 | -5.26% |

Therefore, monthly temperature features contain more stable predictive structure than monthly rainfall features in the current sample.

However, temperature still does not provide consistent incremental predictive value beyond Block-Only OLS.

---

## Finding 3 — Unregularized Monthly Models Overfit

Both month-level OLS models underperform their Ridge counterparts.

### Temperature

Ridge improves RMSE relative to Temperature Month-Level OLS by:

| Horizon | Ridge improvement versus OLS |
|---:|---:|
| 1 | 7.69% |
| 2 | 10.99% |
| 3 | 11.14% |
| 4 | 14.63% |
| 5 | 14.97% |

### Rainfall

Ridge improves RMSE relative to Rainfall Month-Level OLS by:

| Horizon | Ridge improvement versus OLS |
|---:|---:|
| 1 | 12.91% |
| 2 | 17.72% |
| 3 | 17.94% |
| 4 | 22.64% |
| 5 | 26.42% |

The increasing performance gap at longer horizons shows that the unregularized monthly specifications become increasingly unstable as the target blocks become larger and the number of observations decreases.

Ridge substantially reduces this overfitting.

---

## Finding 4 — Ridge Usually Chooses to Remove Weather

The typical Ridge fold has approximately zero effective weather degrees of freedom.

### Maximum-alpha boundary selection

| Model | Outer folds selecting maximum alpha |
|---|---:|
| Temperature Month-Level Ridge | 81.25% |
| Rainfall Month-Level Ridge | 75.00% |
| Joint Month-Level Ridge | 81.25% |

These fractions are identical across all five horizons.

When the maximum alpha of \(10^8\) is selected, the effective weather contribution is numerically close to zero. The model effectively collapses back toward the Block-Only specification.

### Median effective weather degrees of freedom

For every Ridge model and every horizon:

\[
\text{median effective weather df}
\approx 0
\]

The nonzero mean effective degrees of freedom are driven by a small number of influential folds rather than by a stable, modest weather effect across seasons.

---

## Finding 5 — The Joint Model Introduces Instability Instead of Complementarity

The Joint Month-Level Ridge model combines 16 monthly rainfall and temperature predictors.

It underperforms:

- Block-Only OLS
- Temperature Month-Level Ridge
- Rainfall Month-Level Ridge

at every horizon.

Its RMSE difference versus Block-Only becomes increasingly negative:

| Horizon | RMSE difference versus Block-Only |
|---:|---:|
| 1 | -6.75% |
| 2 | -10.09% |
| 3 | -10.26% |
| 4 | -14.16% |
| 5 | -17.54% |

The penalty diagnostics show extreme fold sensitivity:

- 13 of 16 folds select the maximum alpha.
- One fold selects the minimum alpha.
- The median effective weather degrees of freedom is approximately zero.
- The maximum effective weather degrees of freedom is approximately 13.98.

This means the joint model switches between:

1. removing nearly all weather contribution; and
2. retaining nearly all identifiable weather directions.

The combined rainfall–temperature specification therefore introduces instability rather than reliable complementary predictive information.

---

## Influential Seasons

### Temperature Month-Level Ridge

The selected penalty is especially sensitive to the `21-22` season.

When `21-22` is held out:

- `h=1` to `h=4` select \(\alpha \approx 0.316\)
- `h=5` selects \(\alpha = 0.1\)
- effective weather degrees of freedom rise to approximately 5.08–6.83

This indicates that the apparent temperature structure among the remaining seasons is not stable to the inclusion of `21-22`.

### Joint Month-Level Ridge

The selected penalty is especially sensitive to the `23-24` season.

When `23-24` is held out:

- every horizon selects the minimum alpha of \(10^{-4}\)
- effective weather degrees of freedom rise to approximately 13.98

The resulting relationship performs poorly when predicting the held-out `23-24` season.

This indicates that the high-dimensional rainfall–temperature relationship learned from the other seasons does not generalize consistently to `23-24`.

---

## Scientific Interpretation

The results support the following conclusion:

> Within the available 16-season historical sample and the evaluated linear specifications, growing-season weather variables do not provide stable incremental out-of-sample predictive value for harvest-block crushing volumes beyond the historical harvest-block profile.

This conclusion is narrower than stating that weather does not affect sugarcane production.

The analysis does not rule out:

- weather effects on full-season production totals;
- nonlinear weather responses;
- stage-specific weather effects;
- interactions between rainfall and temperature;
- effects on sugar concentration, ATR, or cane yield;
- effects of extreme weather rather than monthly averages;
- spatially heterogeneous municipality-level effects;
- relationships that require a larger historical sample.

---

## Practical Modeling Implication

For block-level crushing prediction under the current dataset:

1. **Block-Only OLS should remain the primary benchmark.**
2. **Temperature Month-Level Ridge is the strongest weather-based reference model.**
3. **Unregularized month-level OLS models should not be used for forecasting.**
4. **Joint monthly rainfall and temperature should not be added without stronger structural constraints or more data.**
5. **Future model development should prioritize new information and research design rather than additional unconstrained linear specifications.**

Potential next research directions include:

- stage-specific weather windows;
- extreme-temperature and water-deficit features;
- nonlinear response functions;
- municipality-level or region-level heterogeneity;
- harvest timing targets;
- cane yield, sugar yield, ATR, or CCS outcomes;
- additional complete historical seasons.

---

## Reporting Figures

The locked reporting outputs are:

- `docs/figures/month_level_model_rmse_comparison.png`
- `docs/figures/month_level_model_improvement_vs_block.png`
- `docs/figures/month_level_ridge_boundary_diagnostics.png`
- `docs/figures/month_level_ridge_effective_degrees_of_freedom.png`

The raw RMSE figure should be interpreted within each horizon. RMSE naturally increases with the aggregation horizon because each target block contains more tonnes.

---

## Reproducibility

Run the model-comparison layer:

```bash
python -m src.modeling.month_level_model_comparison
```

Generate the reporting figures:

```bash
python -m src.visualization.month_level_model_reporting
```

Primary tabular outputs are stored under:

```text
data/processed/modeling/month_level_baseline_results/
```

Primary reporting figures are stored under:

```text
docs/figures/
```
