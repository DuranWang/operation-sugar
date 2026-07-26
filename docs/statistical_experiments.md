# Statistical Experiments

This document records the statistical experiments conducted under the Operation Sugar modeling framework.

Each experiment addresses a specific research question using reproducible datasets, transparent statistical models, and rigorous out-of-sample evaluation.

The statistical modeling philosophy, predictor hierarchy, benchmark strategy, validation methodology, and evaluation principles are described in **modeling_framework.md**.

---

# Experiment 1

## Aggregate Weather Baselines (Version 1.5)

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

For example,

- **h = 1** predicts crushing during one harvest block.
- **h = 3** predicts cumulative crushing over three consecutive harvest blocks.
- **h = 5** predicts cumulative crushing over five consecutive harvest blocks.

Increasing the aggregation horizon smooths short-term harvest variability while reducing the number of independent observations available for model estimation.

---

### Complete-Season Prediction

#### Response Variable

The response variable is total sugarcane crushing over one complete harvest season.

Each historical harvest season contributes one observation.

---

## Modeling Configuration

This experiment follows the statistical modeling framework defined in **modeling_framework.md**.

Configuration:

- Aggregate weather predictors
- Benchmark models defined in the Modeling Framework
- Leave-One-Season-Out Cross-Validation
- Cross-validated evaluation metrics

---

## Research Findings

### Harvest-Block Prediction

#### Findings

Across all five aggregation horizons, aggregate weather variables failed to improve predictive performance relative to the harvest-calendar benchmark.

In several aggregation horizons, predictive performance was marginally lower than the benchmark model.

#### Conclusion

Aggregate growing-season rainfall and average temperature provided no additional predictive information beyond historical harvest timing.

---

### Complete-Season Prediction

#### Findings

Aggregate weather variables did not outperform the training-season historical mean benchmark under out-of-sample evaluation.

Although positive regression coefficients were observed when fitting the complete dataset, these relationships failed to generalize to unseen harvest seasons.

#### Conclusion

Aggregate growing-season weather failed to improve out-of-sample prediction of complete-season sugarcane crushing.

---

## Interpretation

The negative results are consistent across both prediction tasks.

Compressing the entire September–April growing season into a single rainfall total and a single average temperature removes important temporal information relevant to sugarcane production.

This experiment establishes the first statistical baseline within the Operation Sugar modeling framework.

Future experiments will determine whether preserving the temporal structure of weather observations improves predictive performance.

---

## Future Work

### Experiment 2 (Version 1.5.1)

### Research Question

> Which months of the growing season contain predictive weather information?

The next experiment will extend the aggregate weather baseline by preserving the temporal structure of weather observations.

Planned additions include:

- Month-level weather predictors
- Month-specific regression coefficients
- Regularized month weighting
- Temporal feature interpretation

The objective is to determine whether month-level weather representations improve out-of-sample predictive performance relative to aggregate growing-season weather.

---

# Relationship to the Modeling Framework

This document records the statistical experiments performed under the Operation Sugar modeling framework.

The statistical modeling philosophy, benchmark strategy, validation methodology, and evaluation principles are defined in **modeling_framework.md**.

The research and engineering decisions that motivated these experiments are documented in **research_design_decisions.md**.