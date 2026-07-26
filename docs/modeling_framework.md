# Modeling Framework

This document defines the statistical modeling framework used throughout Operation Sugar.

It describes how statistical models are designed, evaluated, and progressively extended across the project.

The research and engineering decisions that motivated this framework are documented in **research_design_decisions.md**.

The statistical experiments conducted under this framework are documented in **statistical_experiments.md**.

---

# Modeling Philosophy

Operation Sugar is designed as a quantitative research platform rather than a prediction competition.

The objective is not simply to maximize predictive accuracy, but to understand how weather information contributes to explaining historical sugarcane production through transparent, reproducible statistical experiments.

Statistical complexity is introduced only after simpler hypotheses have been rigorously evaluated.

---

# Modeling Workflow

Each statistical experiment follows the same workflow.

```text
Research Question
        │
        ▼
Response Variable
        │
        ▼
Weather Representation
        │
        ▼
Benchmark Model
        │
        ▼
Model Training
        │
        ▼
Out-of-Sample Validation
        │
        ▼
Performance Evaluation
        │
        ▼
Research Interpretation
```

This workflow ensures that every experiment is directly linked to a clearly defined scientific question.

---

# Response Variables

Operation Sugar currently considers two prediction tasks.

## Harvest-Block Prediction

Response variable:

- cumulative sugarcane crushing over one or more consecutive harvest blocks.

Purpose:

Evaluate whether weather information explains short-term harvest dynamics.

---

## Complete-Season Prediction

Response variable:

- total sugarcane crushing over one complete harvest season.

Purpose:

Evaluate whether weather information explains long-term seasonal production.

---

## Future Response Variables

Future releases may introduce additional prediction targets, including:

- sugar yield;
- ATR;
- recoverable sugar;
- sugar production.

---

# Predictor Hierarchy

Weather information is introduced progressively according to its temporal resolution and biological specificity.

```text
Aggregate Weather
        │
        ▼
Monthly Weather
        │
        ▼
Regularized Monthly Models
        │
        ▼
Advanced Agroclimatic Variables
        │
        ▼
Maturation Weather
        │
        ▼
Sugar Production Analytics
```

Each stage establishes the statistical baseline for the next stage.

---

# Benchmark Strategy

Every new weather representation is evaluated relative to an established statistical baseline.

Current benchmark models include:

| Prediction Task | Benchmark |
|-----------------|-----------|
| Harvest-block prediction | Harvest-block position |
| Complete-season prediction | Training-season historical mean |

Future weather representations are expected to demonstrate improvement relative to these benchmark models before additional model complexity is introduced.

---

# Validation Framework

All statistical models are evaluated using Leave-One-Season-Out Cross-Validation.

Each historical harvest season is treated once as an independent test season while all remaining seasons are used for model training.

This validation framework evaluates model generalization across historical harvest seasons while preventing information leakage between training and testing data.

---

# Evaluation Metrics

Primary evaluation metrics include:

- Cross-validated coefficient of determination;
- Cross-validated normalized root mean squared error.

Whenever benchmark models are available, incremental performance relative to the benchmark is also reported.

Operation Sugar emphasizes out-of-sample predictive performance rather than in-sample goodness of fit.

---

# Modeling Principles

Every statistical experiment follows the same principles.

## Principle 1

Each experiment answers one clearly defined research question.

---

## Principle 2

Introduce one major methodological advancement at a time.

This allows the contribution of each new weather representation to be evaluated independently.

---

## Principle 3

Every new model must be compared against an established statistical baseline.

Model complexity alone is not considered scientific progress.

---

## Principle 4

Prefer interpretable models before complex models.

Simple statistical models provide stronger scientific insight and clearer biological interpretation.

---

## Principle 5

Evaluate predictive performance using out-of-sample validation.

In-sample goodness of fit is not considered sufficient evidence of predictive value.

---

## Principle 6

Negative results are valuable research outcomes.

Demonstrating that a weather representation does not improve predictive performance establishes an important statistical baseline for future experiments.

---

# Relationship to Project Documentation

This document defines how statistical modeling is performed throughout Operation Sugar.

The research and engineering decisions underlying this framework are documented in **research_design_decisions.md**.

Individual statistical experiments—including research questions, experimental design, results, and interpretation—are documented in **statistical_experiments.md**.