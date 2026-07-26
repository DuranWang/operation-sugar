# Research Decisions

This document records the major analytical, statistical, and engineering decisions made during the development of Operation Sugar.

Rather than describing implementation details, it explains why specific research and modeling choices were adopted and which alternatives were considered.

---

# Decision Principles

Each decision records:

- the decision;
- the rationale;
- the principal alternatives considered.

This structure improves transparency and documents the reasoning behind the project's analytical and statistical design.

---

# Section 1 — Research Decisions

## Decision 01 — Research Philosophy

### Decision

Research questions determine engineering implementation.

### Reason

Engineering should support scientific inquiry rather than define it.

---

## Decision 02 — Evidence Registry

### Decision

Assign a unique Paper ID to every major reference.

### Reason

Paper IDs improve traceability across documentation and reduce repetitive citations.

---

# Section 2 — Seasonal Decisions

## Decision 03 — Growing Stage Definition

### Decision

Treat vegetative development as a single analytical growing stage.

### Reason

Municipality-level phenological information is generally unavailable, making finer subdivisions difficult to support consistently.

### Alternatives Considered

- Separate developmental stages
- Calendar-year aggregation

---

## Decision 04 — Harvest Timing Definition

### Decision

Infer harvest timing directly from historical UNICA observations.

### Reason

Observed industrial activity provides a reproducible empirical definition of harvest timing.

### Alternatives Considered

- Fixed crop calendars
- Literature-defined harvest periods

---

# Section 3 — Weather Feature Decisions

## Decision 05 — Dry Day Definition

### Decision

Adopt the ETCCDI dry-day definition.

### Reason

It is internationally recognized and widely used in climate research.

### Alternatives Considered

- 0 mm
- 0.1 mm
- 2 mm

---

## Decision 06 — Maximum Consecutive Dry Days

### Decision

Use CDD as the primary drought indicator.

### Reason

Persistence better represents drought conditions than simple frequency.

### Alternatives Considered

- Dry-day count

---

## Decision 07 — Growing-Stage CDD

### Decision

Calculate CDD over the growing stage rather than the calendar year.

### Reason

Weather outside the biological growing period is less relevant to biomass accumulation.

### Alternatives Considered

- Annual CDD
- Ripening-stage CDD

---

## Decision 08 — Feature Selection Strategy

### Decision

Prioritize biologically meaningful variables.

### Reason

Variables should represent known biological or operational processes rather than arbitrary mathematical transformations.

---

## Decision 09 — Temperature Variable Selection

### Decision

Use average temperature as the primary thermal variable in Aggregate Baseline models.

### Reason

Sugarcane physiological responses are primarily driven by sustained thermal conditions rather than isolated daily temperature extremes.

Period-average temperature therefore provides a more biologically meaningful representation of the thermal environment than maximum or minimum temperature.

### Alternatives Considered

- Maximum temperature
- Minimum temperature
- Growing Degree Days (reserved for future agronomic models)
- Rolling mean temperature (reserved for future agronomic models)

### Notes

This decision applies only to the Aggregate Baseline models.

More biologically specialized thermal metrics—including Growing Degree Days, sustained warm or cool spell duration, rolling mean temperature, and stage-specific thermal accumulation—remain candidates for future agronomic feature engineering.

---

# Section 4 — Statistical Modeling Decisions

## Decision 10 — Aggregate Weather Before Month-Level Weather

### Decision

Evaluate aggregate growing-season weather before introducing month-level weather predictors.

### Reason

Aggregate weather provides the simplest representation of climatic conditions during the growing season.

Establishing its predictive performance creates a statistical baseline against which more detailed temporal weather representations can be evaluated.

### Alternatives Considered

- Develop month-level models immediately
- Introduce all weather features simultaneously

---

## Decision 11 — Incremental Modeling Strategy

### Decision

Introduce one major source of predictive information at a time.

### Reason

Adding multiple new predictors simultaneously makes it difficult to determine which variables contribute to any observed improvement in predictive performance.

An incremental strategy allows each experiment to isolate the value of a single methodological advancement.

### Alternatives Considered

- Simultaneous addition of multiple weather representations
- Comprehensive feature engineering before baseline evaluation

---

## Decision 12 — Out-of-Sample Evaluation

### Decision

Evaluate predictive performance exclusively using out-of-sample validation.

### Reason

Models may exhibit strong in-sample relationships that fail to generalize to unseen harvest seasons.

Out-of-sample evaluation provides a more reliable assessment of predictive value.

### Alternatives Considered

- In-sample goodness-of-fit only
- Random train-test splits

---

## Decision 13 — Historical Harvest Profile as the Primary Benchmark

### Decision

Use the historical harvest-block profile (Block-Only OLS) as the primary benchmark for evaluating weather-based prediction models.

### Reason

Historical harvest timing explains a substantial proportion of predictable variation in block-level crushing volumes.

Any weather representation should therefore be evaluated based on its incremental predictive value beyond the historical harvest profile rather than against a weather-free mean benchmark.

Using Block-Only OLS establishes a stronger and more operationally meaningful baseline for future model development.

### Alternatives Considered

- Training-season historical mean
- Aggregate weather baseline only

---

## Decision 14 — Nested Ridge Regularization

### Decision

Use nested Leave-One-Season-Out cross-validation to select Ridge regularization strength.

### Reason

Selecting the Ridge penalty on the same held-out season used for model evaluation would introduce optimistic bias.

Nested cross-validation separates hyperparameter selection from final model evaluation, providing an unbiased estimate of out-of-sample performance.

Weather predictors are standardized independently within each outer training fold to prevent information leakage.

### Alternatives Considered

- Fixed Ridge penalty
- Ordinary cross-validation
- Non-nested hyperparameter tuning

---

## Decision 15 — Exclusion of Joint Month-Level OLS

### Decision

Do not estimate an unregularized joint month-level rainfall–temperature OLS model.

### Reason

Each outer Leave-One-Season-Out training fold contains only 15 harvest seasons.

After centering the weather predictors, the maximum identifiable weather rank is therefore 14.

The joint month-level specification contains 16 monthly weather predictors, making the unregularized system non-identifiable within the training folds.

Ridge regularization produces a unique solution and therefore serves as the appropriate estimator for the joint specification.

### Alternatives Considered

- Joint Month-Level OLS
- Dimension reduction before OLS
- Principal component regression

# Summary

Operation Sugar records research, engineering, and statistical modeling decisions to make analytical assumptions explicit, reproducible, and transparent.

Each decision documents:

- what was chosen;
- why it was chosen;
- which alternatives were considered.

These decisions define the methodological foundation of the project and guide future feature engineering, statistical modeling, and experimental design.

The decisions documented here are implemented through the statistical modeling framework described in **modeling_framework.md**.

Their effectiveness is subsequently evaluated through the statistical experiments documented in **statistical_experiments.md**.
