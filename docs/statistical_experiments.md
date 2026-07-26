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

## Experimental Design

### Objective

Establish the first statistical baseline for evaluating weather information in historical sugarcane production.

This experiment evaluates whether simple aggregate growing-season weather variables contain predictive information before introducing more detailed temporal weather representations.

---

### Weather Predictors

The aggregate weather baseline uses only two predictors:

- Total growing-season rainfall
- Average growing-season temperature

No month-level weather information is included.

---

## Prediction Tasks

Two prediction tasks are evaluated.

### Harvest-Block Prediction

#### Response Variable

The response variable is cumulative sugarcane crushing over consecutive harvest blocks.

Each São Paulo harvest season consists of 24 approximately biweekly UNICA reporting periods.

Rather than predicting each reporting period individually, consecutive harvest blocks are aggregated into non-overlapping prediction windows.

Five aggregation horizons are evaluated.

| Aggregation Horizon | Response Variable |
| ------------------- | ----------------- |
| h = 1 | Crushing during one harvest block |
| h = 2 | Crushing summed over two consecutive harvest blocks |
| h = 3 | Crushing summed over three consecutive harvest blocks |
| h = 4 | Crushing summed over four consecutive harvest blocks |
| h = 5 | Crushing summed over five consecutive harvest blocks |

Increasing the aggregation horizon smooths short-term harvest variability while reducing the number of independent observations available for model estimation.

---

### Complete-Season Prediction

The response variable is total sugarcane crushing over one complete harvest season.

Each historical harvest season contributes one observation.

---

## Modeling Configuration

- Aggregate rainfall
- Aggregate temperature
- Harvest-block fixed effects
- Leave-One-Season-Out Cross-Validation
- Out-of-sample RMSE, MAE and \(R^2\)

---

## Findings

Aggregate growing-season rainfall and average temperature did not improve out-of-sample prediction for either harvest-block or complete-season crushing.

The aggregate weather model consistently underperformed the historical harvest-profile benchmark.

---

## Interpretation

Compressing the entire September–April growing season into one rainfall total and one average temperature removes potentially important temporal structure.

This experiment established the benchmark against which all subsequent weather models were evaluated.

---

# Experiment 2

## Month-Level Weather Models (Version 1.5.1)

### Research Question

> Does preserving the monthly structure of growing-season weather improve out-of-sample prediction of historical sugarcane crushing?

---

## Objective

Evaluate whether month-level weather representations provide stable incremental predictive value beyond the historical harvest-block profile.

---

## Weather Representations

Five weather specifications were evaluated.

| Model | Weather predictors |
|------|--------------------|
| Aggregate Weather OLS | Growing-season rainfall + temperature |
| Rainfall Month-Level OLS | September–April rainfall |
| Rainfall Month-Level Ridge | September–April rainfall |
| Temperature Month-Level OLS | September–April temperature |
| Temperature Month-Level Ridge | September–April temperature |
| Joint Month-Level Ridge | September–April rainfall + September–April temperature |

All month-level models included harvest-block fixed effects.

The Ridge models additionally employed:

- nested Leave-One-Season-Out cross-validation;
- fold-specific weather standardization;
- partially penalized Ridge regression;
- logarithmic alpha grid from \(10^{-4}\) to \(10^{8}\).

---

## Prediction Task

The response variable remained harvest-block crushing aggregated over five horizons:

| Horizon | Blocks per observation |
|---------|------------------------|
| h = 1 | 1 |
| h = 2 | 2 |
| h = 3 | 3 |
| h = 4 | 4 |
| h = 5 | 5 |

---

## Model Comparison

Seven models were ultimately compared:

1. Block-Only OLS
2. Temperature Month-Level Ridge
3. Aggregate Weather OLS
4. Rainfall Month-Level Ridge
5. Joint Month-Level Ridge
6. Temperature Month-Level OLS
7. Rainfall Month-Level OLS

The ranking was identical across every aggregation horizon.

---

## Findings

### Historical Harvest Profile

Block-Only OLS achieved the lowest out-of-sample RMSE across all five horizons.

Historical harvest timing therefore remained the strongest predictor of block-level crushing.

---

### Month-Level Temperature

Temperature Month-Level Ridge was the strongest weather model.

However, it remained between approximately 0.6% and 1.5% worse than Block-Only OLS across all horizons.

---

### Month-Level Rainfall

Rainfall Month-Level Ridge substantially outperformed Rainfall Month-Level OLS, demonstrating that Ridge effectively reduced overfitting.

Nevertheless, rainfall models remained consistently worse than both Block-Only OLS and Temperature Ridge.

---

### Joint Weather Representation

Combining rainfall and temperature into a single month-level model further reduced predictive performance.

The joint Ridge model consistently underperformed both single-weather-family Ridge models.

---

### Ridge Diagnostics

Nested LOSO selected the maximum alpha in approximately 75–81% of outer folds.

Median effective weather degrees of freedom remained approximately zero for every Ridge model.

Only a small number of influential seasons retained meaningful weather complexity after regularization.

---

## Interpretation

Preserving monthly weather structure substantially reduced overfitting compared with aggregate weather models.

Nevertheless, no evaluated month-level specification consistently outperformed the historical harvest-block profile.

Within the available 16 complete harvest seasons and the evaluated linear modeling framework, month-level growing-season weather did not provide stable incremental out-of-sample predictive value beyond historical harvest timing.

---

# Relationship to the Modeling Framework

This document records completed statistical experiments conducted under the Operation Sugar modeling framework.

General modeling principles, validation methodology, benchmark definitions, and evaluation philosophy are documented in **modeling_framework.md**.

Major research decisions are documented in **research/research_decisions.md**.

Detailed Version 1.5.1 model diagnostics, Ridge analyses, and full experimental results are documented in **month_level_model_findings.md**.