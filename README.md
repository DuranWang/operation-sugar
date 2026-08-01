# Operation Sugar

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.5.1-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

**Open-source research and benchmarking infrastructure for commodity forecasts, beginning with Brazilian sugarcane.**

---

## Background

Operation Sugar (OS) began as an independent quantitative research project focused on Brazilian sugarcane.

The public information required to study sugarcane production and harvest activity is fragmented across institutions, geographic levels, temporal frequencies, and publication schedules. Weather observations, agricultural statistics, and harvest reports therefore require substantial engineering, validation, and alignment before they can be analyzed together.

## Goal

The long-term goal of OS is to develop transparent infrastructure for benchmarking commodity forecasts. Rather than treating one forecast as the universal standard, OS aims to compare statistical models, official outlooks, institutional research, and proprietary forecasts against clearly defined reference forecasts.

The central question is:

> How much incremental value does a forecast provide beyond information already available from transparent public sources and alternative public forecasts?

Brazilian sugarcane will serve as the first application. The project will use this domain to develop and test the data, target definitions, historical-vintage controls, and out-of-sample procedures required for fair forecast comparison.

## Problem

Commodity forecasts are widely produced, but they are rarely preserved and evaluated under consistent rules.

### Forecast records are incomplete

Forecasts are commonly distributed through emails, spreadsheets, presentations, reports, and internal systems. When a forecast is revised, the original version may be lost.

It may therefore be unclear when a forecast was made, what information was available, and which version should be evaluated. This creates opportunities for hindsight bias and selective reporting.

### Forecasts are not directly comparable

Forecasts may differ in target definition, geographic scope, units, aggregation period, publication date, horizon, and treatment of later revisions.

Comparing them without standardizing these differences can produce misleading conclusions.

### Historical evaluations may contain look-ahead bias

Agricultural and economic data are often revised after publication. A backtest using the latest dataset may therefore include information that was unavailable when the forecast would originally have been made.

Credible evaluation must distinguish among observation, publication, forecast, revision, and realization dates.

### Transparent reference forecasts are often missing

A forecast may appear accurate because it captures seasonality, persistence, partial-season observations, or other patterns already visible in public data.

Without relevant reference forecasts, it is difficult to determine whether the forecast contributes genuine incremental information.

## Proposed Solution

OS proposes an open framework that organizes forecasts around standardized records, multiple reference forecasts, historical data vintages, and consistent evaluation rules.

### 1. Standardized Forecast Records

Each forecast would be stored with a defined target, scope, horizon, publication timestamp, forecast value, information set, and revision history.

Original forecasts would remain preserved, while later updates would be recorded as separate revisions.

### 2. Multiple Reference Forecasts

OS would compare forecasts against several relevant alternatives, which may include:

- historical or seasonal baselines;
- persistence-based forecasts;
- reproducible public-information models;
- official industry or government outlooks;
- market consensus forecasts.

These references would distinguish basic predictive performance from incremental value beyond existing public information.

### 3. Vintage-Aligned Data

Evaluations would use, where possible, the information available at the time each forecast was produced.

Historical releases and revisions would be preserved or reconstructed. Where true historical vintages are unavailable, the limitation would be documented explicitly.

### 4. Standardized Evaluation

Forecasts would be compared using a common protocol covering:

- accuracy and bias;
- improvement relative to reference forecasts;
- stability across horizons and seasons;
- revision behavior;
- uncertainty, where available.

### 5. Reproducible Research Infrastructure

The framework would be supported by version-controlled code, documented data sources, transparent model specifications, preserved methodology versions, and reproducible historical results.

Changes to targets, data, models, or evaluation procedures would be recorded explicitly so that external researchers can reproduce and challenge the conclusions.

## Initial Application

Brazilian sugarcane will provide the first complete case study.

The initial implementation will define:

- a specific forecasting target;
- a historical information timeline;
- multiple reference forecasts;
- vintage-aware datasets;
- a standardized evaluation protocol;
- reproducible out-of-sample results.

The immediate objective is not to build a universal forecasting platform. It is to demonstrate that forecasts in one economically relevant commodity market can be preserved, aligned, and evaluated more transparently.

Expansion to other markets would be considered only after the methodology has been validated in Brazilian sugarcane.

---

## Current Research Foundation

The current repository is the research foundation for this longer-term benchmarking framework.

OS integrates official Brazilian sugarcane production statistics from IBGE, daily weather observations from NASA POWER, and harvest reports from UNICA into reproducible datasets, modular ETL pipelines, historical harvest intelligence, and statistically evaluated modeling workflows.

The project currently emphasizes strong reference models, transparent assumptions, reproducible experiments, and rigorous out-of-sample validation rather than model complexity alone.

### Highlights

- 🌎 Weather analytics across **642 São Paulo sugar-producing municipalities**
- 🌦️ Integrated **NASA POWER**, **IBGE**, and **UNICA** public datasets
- 📈 Historical harvest intelligence across **16 completed sugarcane seasons**
- 📊 **Seven statistical models** evaluated across **five harvest aggregation horizons**
- 🧠 Month-level rainfall and temperature modeling with **nested leave-one-season-out validation**
- 📉 Fold-specific feature standardization and **partially penalized Ridge regression**
- 🔍 Ridge stability and effective weather degrees-of-freedom diagnostics
- 🧪 **174 automated unit tests**, including **147 dedicated to the UNICA ETL pipeline**
- 🏗️ Modular ETL, validation, analytics, modeling, visualization, and research architecture

---

## Key Version 1.5.1 Findings

Seven statistical models were evaluated using identical leave-one-season-out cross-validation across five harvest aggregation horizons.

| Rank | Model | Relative RMSE vs. Block-Only |
|-----:|------------------------------|----------------:|
| 1 | Block-Only OLS | 0.00% |
| 2 | Temperature Month-Level Ridge | -1.00% |
| 3 | Aggregate Weather OLS | -2.45% |
| 4 | Rainfall Month-Level Ridge | -2.75% |
| 5 | Joint Month-Level Ridge | -11.76% |
| 6 | Temperature Month-Level OLS | -14.73% |
| 7 | Rainfall Month-Level OLS | -28.20% |

Negative values indicate worse out-of-sample RMSE than the historical Block-Only benchmark.

### Main Findings

- Historical harvest timing remained the strongest predictor across every aggregation horizon.
- Ridge regression substantially reduced overfitting relative to unregularized month-level models.
- Month-level temperature contained more stable predictive structure than month-level rainfall.
- Nested leave-one-season-out validation selected the maximum Ridge penalty in most outer folds, indicating that only a very small amount of weather complexity generalized across seasons.
- Within the available sixteen-season historical sample, growing-season weather variables did **not** provide stable incremental predictive value beyond the historical harvest profile for harvest-block crushing prediction.

This conclusion is intentionally narrow.

It does **not** imply that weather has no influence on sugarcane production. Instead, it indicates that the evaluated linear aggregate and month-level weather specifications do not outperform a simple historical harvest-calendar benchmark under rigorous out-of-sample validation.

This result illustrates the purpose of the broader OS framework: a model should be judged by the incremental value it provides beyond relevant reference forecasts, not by complexity or explanatory plausibility alone.

---

## Research Dashboard

### Weather & Harvest Benchmark

<p align="center">
  <img src="docs/figures/dashboard_season_comparison.png" width="900">
</p>

Compare historical weather conditions and matched-cutoff harvest progress across multiple São Paulo sugarcane seasons.

---

### Historical Harvest Calendar

<p align="center">
  <img src="docs/figures/harvest_heatmap.png" width="900">
</p>

Visualize how annual sugarcane crushing is distributed across sixteen completed São Paulo harvest seasons.

---

### Historical Percentile Benchmark

<p align="center">
  <img src="docs/figures/harvest_percentile_bands.png" width="900">
</p>

Benchmark the current harvest against the historical distribution of completed seasons.

---

### Harvest-Block Aggregate Weather Baseline

<p align="center">
  <img src="docs/figures/aggregate_baseline_dashboard.png" width="900">
</p>

Evaluate whether aggregate growing-season weather improves out-of-sample prediction of harvest-block crushing beyond historical harvest timing.

---

### Complete-Season Aggregate Weather Baseline

<p align="center">
  <img src="docs/figures/season_total_baseline_dashboard.png" width="900">
</p>

Compare aggregate weather predictors against a historical mean benchmark for complete-season crushing using leave-one-season-out cross-validation.

---

### Seven-Model Month-Level Comparison

<p align="center">
  <img src="docs/figures/month_level_model_rmse_comparison.png" width="900">
</p>

Compare seven statistical models across five harvest aggregation horizons under identical leave-one-season-out evaluation.

---

### Incremental Value Beyond the Historical Harvest Profile

<p align="center">
  <img src="docs/figures/month_level_model_improvement_vs_block.png" width="900">
</p>

Measure whether aggregate and month-level weather features provide additional predictive value beyond the historical harvest profile.

---

### Ridge Stability Diagnostics

<p align="center">
  <img src="docs/figures/month_level_ridge_boundary_diagnostics.png" width="900">
</p>

Visualize how frequently nested cross-validation selects boundary Ridge penalties across seasons and prediction horizons.

---

### Effective Weather Degrees of Freedom

<p align="center">
  <img src="docs/figures/month_level_ridge_effective_degrees_of_freedom.png" width="900">
</p>

Compare the typical amount of weather information retained by Ridge with the maximum retained in influential validation folds.

---

For the harvest methodology, see [`docs/harvest_intelligence.md`](docs/harvest_intelligence.md).

For the stable statistical methodology, see [`docs/modeling_framework.md`](docs/modeling_framework.md). For Version 1.5.1 results and diagnostics, see [`docs/research/month_level_model_findings.md`](docs/research/month_level_model_findings.md).

---

## Current Platform Capabilities

### Data Engineering

- Automated NASA POWER weather ingestion
- Municipality metadata integration
- UNICA harvest report ETL pipeline
- Historical harvest database updater
- Comprehensive schema validation

### Weather Analytics

- Municipality-level monthly weather aggregation
- Growing-season weather summaries
- September–April month-level rainfall features
- September–April month-level temperature features
- Weather–harvest dataset construction

### Harvest Intelligence

- Historical harvest calendar construction
- Monthly crushing distribution analysis
- Historical percentile-band benchmarking
- Comparable historical harvest snapshots
- Harvest timing metrics
- Automated harvest research summaries

### Statistical Modeling

- Block-Only historical benchmark
- Aggregate Weather OLS
- Complete-Season Aggregate Weather OLS
- Rainfall Month-Level OLS
- Temperature Month-Level OLS
- Rainfall Month-Level Ridge
- Temperature Month-Level Ridge
- Joint Rainfall–Temperature Ridge
- Seven-model comparison framework
- Leave-One-Season-Out cross-validation
- Nested Leave-One-Season-Out Ridge selection

### Research Infrastructure

- Modular project architecture
- Automated visualization pipeline
- Publication-style reporting figures
- Comprehensive validation framework
- Automated testing
- Reproducible research documentation

---

## Repository Statistics

| Metric | Value |
|---------|------:|
| Municipalities | 642 |
| Historical Weather Archive | September 2009 – April 2026 |
| Historical Harvest Seasons | 17 (16 completed) |
| Weather Variables | Rainfall, Temperature, Relative Humidity |
| Month-Level Weather Features | September–April Rainfall & Temperature |
| Statistical Models | 7 |
| Harvest Aggregation Horizons | 5 |
| Validation Strategy | Leave-One-Season-Out |
| Ridge Hyperparameter Selection | Nested Leave-One-Season-Out |
| Automated Tests | 174 |
| UNICA ETL Tests | 147 |
| Python | 3.12 |

---

## Documentation

Project documentation is organized into platform documentation, research documentation, and project management.

### Platform Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture.md`](docs/architecture.md) | Overall platform architecture and repository organization |
| [`docs/analytical_framework.md`](docs/analytical_framework.md) | Construction and validation of analytical variables |
| [`docs/modeling_framework.md`](docs/modeling_framework.md) | Stable statistical modeling and validation methodology |
| [`docs/seasonal_framework.md`](docs/seasonal_framework.md) | Biological and operational seasonal structure |
| [`docs/harvest_intelligence.md`](docs/harvest_intelligence.md) | Historical harvest benchmark methodology |
| [`docs/feature_dictionary.md`](docs/feature_dictionary.md) | Definitions of engineered variables |
| [`docs/literature_registry.md`](docs/literature_registry.md) | Supporting agronomic literature |

### Research Documentation

| Document | Description |
|----------|-------------|
| [`research_decisions.md`](research_decisions.md) | Major engineering and analytical decisions |
| [`statistical_experiments.md`](statistical_experiments.md) | Statistical experiment specifications and records |
| [`month_level_model_findings.md`](month_level_model_findings.md) | Version 1.5.1 modeling results and interpretation |
| [`negative_results.md`](negative_results.md) | Modeling approaches that did not generalize |

### Project Management

| Document | Description |
|----------|-------------|
| [`ROADMAP.md`](ROADMAP.md) | Planned future development |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

For readers interested in the complete modeling methodology, validation procedure, and experimental results, these documents provide substantially more detail than this repository overview.

---

## Quick Start

Clone the repository.

```bash
git clone https://github.com/DuranWang/operation-sugar.git

cd operation-sugar
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Run the complete research pipeline.

```bash
python -m src.pipelines.run_pipeline
```

Execute the automated test suite.

```bash
python -m pytest src/tests -v
```

---

## Reproducing the Version 1.5.1 Study

The complete month-level weather modeling workflow can be reproduced by executing the modeling modules in sequence.

```bash
python -m src.modeling.aggregate_baseline

python -m src.modeling.block_only_baseline

python -m src.modeling.month_level_baseline

python -m src.modeling.rainfall_month_level_ridge

python -m src.modeling.temperature_month_level_ols

python -m src.modeling.temperature_month_level_ridge

python -m src.modeling.joint_month_level_ridge

python -m src.modeling.month_level_model_comparison

python -m src.visualization.month_level_model_reporting
```

Primary modeling outputs are written to:

```text
data/processed/modeling/
```

Research figures are generated under:

```text
docs/figures/
```

The complete methodology and interpretation are documented in:

```text
docs/research/month_level_model_findings.md
```

---

## Testing

Run the complete automated test suite.

```bash
python -m pytest src/tests -v
```

Current status:

- ✅ 174 automated tests
- ✅ 100% passing

The test suite covers:

- ETL pipelines
- Schema validation
- Data validation
- Historical harvest processing
- Duplicate detection
- Temporal consistency
- Statistical modeling utilities

---

## Contributing

Suggestions, bug reports, feature requests, and research collaborations are welcome.

Contributions should prioritize:

- Reproducibility
- Transparent assumptions
- Reliable validation
- Interpretable statistical analysis
- Clear documentation
- Incremental analytical value

Please open an issue before submitting major architectural or modeling changes.

---

## License

Released under the MIT License.

For research collaboration, commercial partnerships, or custom development related to Operation Sugar, please contact the author via LinkedIn:

**LinkedIn**

> https://www.linkedin.com/in/duranwang/

or explore the repository discussions and issues on GitHub.

---
