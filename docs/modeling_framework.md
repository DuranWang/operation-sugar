# Operation Sugar Modeling Framework

This document defines the statistical modeling framework used throughout Operation Sugar.

It begins after analytical variables have been constructed and validated under `docs/analytical_framework.md`. Its purpose is to define how those variables enter statistical experiments, how models are evaluated, and how results are interpreted.

Detailed experiment specifications and results are documented separately in:

- `docs/research/statistical_experiments.md`
- `docs/research/month_level_model_findings.md`
- `docs/research/negative_results.md`

---

## 1. Modeling Objective

Operation Sugar uses statistical models to test whether newly constructed variables provide explanatory or predictive value beyond an appropriate historical benchmark.

The objective is not to maximize predictive accuracy through unrestricted model expansion. Each model must answer a clearly defined research question and must be evaluated using a transparent, reproducible, and leakage-resistant procedure.

Statistical complexity is introduced only when simpler specifications have been evaluated first.

---

## 2. Modeling Workflow

Each statistical experiment follows the same general workflow.

```text
Research Question
        │
        ▼
Prediction Target
        │
        ▼
Predictor Representation
        │
        ▼
Benchmark Definition
        │
        ▼
Model Specification
        │
        ▼
Out-of-Sample Validation
        │
        ▼
Performance Comparison
        │
        ▼
Diagnostics
        │
        ▼
Research Interpretation
```

The research question, target, benchmark, and validation design must be defined before model performance is examined.

---

## 3. Prediction Tasks

A prediction task is defined by its observational unit and response variable.

Operation Sugar currently distinguishes between two principal task structures.

### Harvest-Block Prediction

The observational unit is a non-overlapping harvest block within a harvest season.

The response variable represents crushing volume within that block.

Because multiple observations occur within each season, the model may include harvest-block structure to represent the historical harvest calendar.

### Complete-Season Prediction

The observational unit is a complete harvest season.

The response variable represents total crushing across the full season.

Each season contributes one observation, so harvest-block fixed effects are not applicable.

### Future Prediction Tasks

Future targets may include cane yield, sugar yield, ATR, CCS, recoverable sugar, or harvest timing.

Each new target requires its own:

- observational unit;
- response definition;
- benchmark;
- validation design;
- interpretation boundary.

Benchmarks and model structures must not be transferred mechanically across prediction tasks.

---

## 4. Predictor Representations

Predictor representations determine how validated analytical variables are presented to a model.

Common representations include:

### Benchmark-Only Representation

Contains only the structural predictors required to represent the historical baseline.

Examples include harvest-block indicators for block-level prediction or an intercept for complete-season prediction.

### Aggregate Representation

Compresses a complete analytical window into a small number of summary variables.

Examples include total growing-season rainfall or average growing-season temperature.

Aggregate representations provide interpretable low-dimensional reference specifications.

### Temporally Structured Representation

Preserves variation across months, biological stages, or other defined time windows.

Examples include month-level weather variables or stage-specific weather summaries.

Temporally structured representations may capture information lost through complete-season aggregation, but they also increase estimation variance and model complexity.

### Combined Representation

Includes multiple predictor groups in the same model.

Combined models must be checked for:

- exact linear dependence;
- redundant aggregate and component variables;
- dimensionality relative to the number of independent seasons;
- unstable coefficient estimation.

The construction and scientific justification of predictors belong to `docs/analytical_framework.md`. The modeling framework evaluates whether those predictors generalize.

---

## 5. Benchmark Strategy

Every predictive model must be compared with a benchmark appropriate to the prediction unit.

### Harvest-Block Benchmark

The primary harvest-block benchmark represents the historical harvest profile using harvest-block fixed effects without weather predictors.

A weather or agronomic model provides incremental predictive value only if it improves out-of-sample performance beyond this benchmark.

### Complete-Season Benchmark

The primary complete-season benchmark is the historical mean estimated from the training seasons.

Because the complete-season dataset contains one observation per season, harvest-block fixed effects are neither meaningful nor identifiable.

### Benchmark Principles

A benchmark must:

- be defined before model comparison;
- use only information available in the training data;
- match the observational unit of the target;
- remain identical across models being compared;
- represent a credible alternative to the proposed predictors.

In-sample fit, nonzero coefficients, or improvement over an intercept-only model are not sufficient when a stronger domain-specific benchmark exists.

---

## 6. Model Classes

Operation Sugar introduces model classes progressively.

### Ordinary Least Squares

OLS provides the primary unregularized reference model.

It is used when the design matrix is identifiable and the sample size supports direct coefficient estimation.

OLS is valuable for:

- transparent coefficient interpretation;
- identifying overfitting in higher-dimensional representations;
- establishing an unregularized comparison for penalized models.

### Regularized Linear Models

Regularization is introduced when predictor dimensionality or coefficient instability makes unregularized estimation unreliable.

Penalty selection must occur entirely within the training data of each outer validation fold.

Where appropriate, structural predictors such as the intercept and harvest-block effects may remain unpenalized while weather or agronomic coefficients are penalized.

### Structured or Nonlinear Models

More complex models may be introduced only when they test a substantive research hypothesis that simpler models cannot represent.

Examples may include:

- structured penalties;
- nonlinear response functions;
- threshold models;
- biologically supported interactions;
- spatial or regional heterogeneity.

Additional complexity must be justified by the research question rather than by a search for improved fit alone.

---

## 7. Validation Framework

Validation is organized around complete harvest seasons.

### Leave-One-Season-Out Validation

Each outer fold holds out one complete season for evaluation and trains the model on all remaining seasons.

This design prevents observations from the same season from appearing in both the training and test sets.

It also evaluates the intended generalization problem: prediction for an unseen harvest season.

### Nested Model Selection

When a model contains tuning parameters, selection occurs through an inner validation procedure using only the outer training seasons.

The held-out outer season must not influence:

- penalty selection;
- feature scaling;
- imputation;
- variable screening;
- model specification changes.

### Fold-Specific Preprocessing

All learned preprocessing steps are fitted separately within each training fold and then applied to the held-out season.

This includes:

- centering;
- scaling;
- imputation;
- dimensionality reduction;
- data-driven transformations.

### Consistent Comparison Folds

Models compared within the same prediction task must use the same seasons, horizons, response definitions, and outer folds.

A performance difference is interpretable only when the comparison is based on the same held-out observations.

---

## 8. Evaluation Metrics

Operation Sugar evaluates predictive performance using multiple complementary metrics.

### Root Mean Squared Error

RMSE is the primary ranking metric when larger prediction errors should receive greater weight.

### Mean Absolute Error

MAE provides a more direct measure of typical absolute prediction error and is less sensitive to a small number of large misses.

### Out-of-Sample R-Squared

Out-of-sample \(R^2\) measures performance relative to the relevant training-data benchmark.

Negative values indicate that the model performs worse than the benchmark on held-out observations.

### Relative Performance

Model performance should also be reported relative to the primary benchmark.

For an error metric such as RMSE:

\[
\text{Improvement}_{m}
=
\frac{\text{RMSE}_{\text{benchmark}}-\text{RMSE}_{m}}
{\text{RMSE}_{\text{benchmark}}}
\times 100.
\]

Positive values indicate improvement over the benchmark. Negative values indicate worse performance.

No single metric should be interpreted without considering the others and the underlying prediction task.

---

## 9. Model Comparison

Model comparison is based primarily on out-of-sample performance.

A candidate model is evaluated by asking:

1. Does it improve on the appropriate benchmark?
2. Is the improvement consistent across aggregation horizons or related tasks?
3. Is the result stable across held-out seasons?
4. Does the model retain a plausible and identifiable level of complexity?
5. Does the added complexity provide incremental research value?

Model rankings should be reported together with absolute metrics, relative benchmark performance, and diagnostic evidence.

A model that improves substantially on a weaker specification but does not beat the primary benchmark is not considered a successful incremental prediction model.

---

## 10. Model Diagnostics

Predictive metrics alone are insufficient for evaluating statistical reliability.

Diagnostics may include:

### Design Diagnostics

- predictor count;
- matrix rank;
- condition number;
- exact linear dependence;
- observations and independent seasons relative to model dimension.

### Regularization Diagnostics

- selected penalty values;
- minimum- and maximum-grid selections;
- variation in selected penalties across outer folds;
- effective degrees of freedom;
- retained model complexity.

### Fold Diagnostics

- fold-level prediction errors;
- influential held-out seasons;
- changes in coefficients or tuning parameters when individual seasons are excluded;
- concentration of average performance in a small number of folds.

### Coefficient Diagnostics

- standardized coefficients;
- raw-unit coefficients;
- sign stability;
- magnitude stability;
- sensitivity to predictor representation.

Diagnostics are used to distinguish among:

- numerical identification problems;
- statistical overfitting;
- unstable relationships;
- weak incremental signal;
- genuine out-of-sample improvement.

---

## 11. Research Interpretation

Model conclusions must remain limited to the evaluated:

- sample;
- geographic scope;
- response variable;
- predictor definitions;
- model classes;
- validation procedure.

Failure to improve a benchmark does not imply that the underlying biological process is unimportant.

It means that the evaluated representation and model did not provide stable incremental predictive value for the specified task.

Likewise, a plausible coefficient or strong in-sample fit does not establish a generalizable relationship.

Negative and unstable results are retained because they:

- answer defined research questions;
- establish stronger future benchmarks;
- reveal limitations of current variables or models;
- prevent repeated investigation of unsupported specifications;
- guide the design of future experiments.

---

## 12. Modeling Principles

Operation Sugar follows six modeling principles.

### Benchmark Before Complexity

Every model must first be compared with a credible task-specific benchmark.

### Out-of-Sample Evidence First

Research conclusions are based primarily on held-out-season performance rather than complete-sample fit.

### Seasons Are the Independent Validation Unit

Training and test data are separated by complete harvest season.

### Prevent Information Leakage

All learned preprocessing and model selection occur within the relevant training fold.

### Diagnose, Do Not Only Rank

Performance rankings must be accompanied by model-complexity and fold-stability diagnostics.

### Preserve Narrow Interpretation

Conclusions must not extend beyond the target, data, variables, models, and validation design that were actually evaluated.

---

## 13. Relationship to Project Documentation

Operation Sugar separates variable construction, modeling methods, experimental records, and findings.

| Document | Responsibility |
|---|---|
| `docs/seasonal_framework.md` | Defines biological and operational stages of the sugarcane cycle |
| `docs/analytical_framework.md` | Defines and validates analytical variables |
| `docs/feature_dictionary.md` | Records implemented variable definitions |
| `docs/modeling_framework.md` | Defines how variables enter models and are statistically evaluated |
| `docs/research/research_decisions.md` | Records major research design decisions |
| `docs/research/statistical_experiments.md` | Records individual experiment specifications |
| `docs/research/month_level_model_findings.md` | Reports the Version 1.5.1 month-level study |
| `docs/research/negative_results.md` | Preserves unsuccessful and non-generalizing results |
| `ROADMAP.md` | Defines future research directions |
| `CHANGELOG.md` | Records release-level changes |

This separation prevents stable frameworks from becoming release-specific experiment reports.

---

## Summary

The Operation Sugar modeling framework defines how validated analytical variables are tested through statistical models.

Its central standard is incremental out-of-sample value beyond an appropriate historical benchmark.

Models are evaluated using season-level validation, fold-specific preprocessing, transparent metrics, consistent comparisons, and explicit diagnostics.

The framework does not determine whether a particular variable or model succeeds. It defines the procedure through which that question is answered.
