# Statistical Experiments

This document records the statistical experiments conducted under the Operation Sugar modeling framework.

Each experiment addresses a specific research question using reproducible datasets, transparent statistical models, and rigorous out-of-sample evaluation.

The statistical modeling philosophy, predictor hierarchy, benchmark strategy, validation methodology, and evaluation principles are described in **modeling_framework.md**.

---

# Experiment 1

## Aggregate Weather Baselines (Version 1.5.0)

### Research Question

> Do aggregate growing-season weather variables improve prediction of historical sugarcane crushing?

---

## Objective

Establish the first statistical baseline for evaluating weather information in historical sugarcane production.

This experiment evaluates whether simple aggregate growing-season weather variables contain predictive information before introducing more detailed temporal weather representations.

---

## Predictors

The aggregate weather baseline uses two weather predictors:

- Total growing-season rainfall
- Average growing-season temperature

No month-level weather information is included.

---

## Prediction Tasks

Two prediction tasks are evaluated.

### Harvest-Block Prediction

The response variable is cumulative sugarcane crushing over consecutive harvest blocks.

Each São Paulo harvest season consists of twenty-four approximately biweekly UNICA reporting periods. Consecutive harvest blocks are aggregated into non-overlapping prediction windows.

| Aggregation Horizon | Response Variable |
|--------------------|-------------------|
| h = 1 | One harvest block |
| h = 2 | Two consecutive harvest blocks |
| h = 3 | Three consecutive harvest blocks |
| h = 4 | Four consecutive harvest blocks |
| h = 5 | Five consecutive harvest blocks |

Increasing the aggregation horizon smooths short-term harvest variability while reducing the number of independent observations available for model estimation.

### Complete-Season Prediction

The response variable is total sugarcane crushing over one complete harvest season.

Each historical harvest season contributes one observation.

---

## Experimental Design

Harvest-block models include:

- Aggregate rainfall
- Aggregate temperature
- Harvest-block fixed effects

Complete-season models include aggregate growing-season weather predictors only.

Both prediction tasks employ:

- Leave-One-Season-Out cross-validation
- Out-of-sample RMSE
- Out-of-sample MAE
- Out-of-sample \(R^2\)

---

## Models Evaluated

### Harvest-Block Prediction

- Block-Only OLS
- Aggregate Weather OLS

### Complete-Season Prediction

- Historical Mean Baseline
- Aggregate Weather OLS

---

## Status

Completed in Version 1.5.0.

---

## Related Documents

- `modeling_framework.md` — statistical methodology
- `month_level_model_findings.md` — subsequent month-level experiments
- `negative_results.md` — approaches that did not generalize

---

# Experiment 2

## Month-Level Weather Models (Version 1.5.1)

### Research Question

> Does preserving the monthly structure of growing-season weather improve out-of-sample prediction of historical sugarcane crushing?

---

## Objective

Evaluate whether month-level weather representations provide stable incremental predictive value beyond the historical harvest profile.

---

## Predictors

Five weather representations were evaluated.

| Model | Weather Predictors |
|------|--------------------|
| Aggregate Weather OLS | Growing-season rainfall + temperature |
| Rainfall Month-Level OLS | September–April rainfall |
| Rainfall Month-Level Ridge | September–April rainfall |
| Temperature Month-Level OLS | September–April temperature |
| Temperature Month-Level Ridge | September–April temperature |
| Joint Month-Level Ridge | September–April rainfall + September–April temperature |

All models additionally include harvest-block fixed effects.

---

## Response Variable

The response variable is harvest-block sugarcane crushing aggregated over five non-overlapping prediction horizons.

| Horizon | Blocks per Observation |
|---------|-----------------------:|
| h = 1 | 1 |
| h = 2 | 2 |
| h = 3 | 3 |
| h = 4 | 4 |
| h = 5 | 5 |

---

## Experimental Design

The month-level experiments employ:

- Leave-One-Season-Out outer validation
- Nested Leave-One-Season-Out Ridge hyperparameter selection
- Fold-specific weather standardization
- Partially penalized Ridge regression
- Logarithmic Ridge alpha grid from \(10^{-4}\) to \(10^{8}\)

---

## Models Evaluated

Seven models were compared.

1. Block-Only OLS
2. Aggregate Weather OLS
3. Rainfall Month-Level OLS
4. Rainfall Month-Level Ridge
5. Temperature Month-Level OLS
6. Temperature Month-Level Ridge
7. Joint Month-Level Ridge

The Complete-Season Aggregate Weather OLS model remains a separate prediction task and is not included in the seven-model harvest-block comparison.

---

## Evaluation

Models were compared using out-of-sample:

- RMSE
- MAE
- \(R^2\)

Performance was evaluated independently across all five aggregation horizons.

---

## Status

Completed in Version 1.5.1.

---

## Related Documents

- `modeling_framework.md` — statistical methodology
- `month_level_model_findings.md` — complete Version 1.5.1 results and interpretation
- `negative_results.md` — unsuccessful and non-generalizing approaches

---

# Relationship to the Modeling Framework

This document records the statistical experiments conducted under the Operation Sugar modeling framework.

It specifies the research questions, predictor representations, response variables, model configurations, and evaluation protocols used in each completed experiment.

General statistical methodology, validation principles, benchmark strategy, and evaluation philosophy are documented in **modeling_framework.md**.

Major engineering and research design decisions are documented in **research_decisions.md**.

Experimental results, diagnostics, interpretation, and conclusions are documented separately in the corresponding research reports, including **month_level_model_findings.md** and **negative_results.md**.