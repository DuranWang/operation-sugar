# Operation Sugar

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.5.1-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

**Independent quantitative research into Brazilian sugarcane and sugar markets, built on public data and transparent forecast benchmarks.**

Operation Sugar (OS) combines weather observations, agricultural statistics, and harvest reports to investigate commodity supply. Its central research question is: **does additional information improve prediction beyond a relevant public-information benchmark?**

The repository contains data pipelines, harvest analytics, and a completed weather–crushing modeling study. Current research is moving toward annual cane yield, expanded weather windows, and agronomically motivated variables. The long-term goal is a reproducible framework for comparing commodity forecasts under consistent targets, information sets, and evaluation rules.

## Research Snapshot

| Dimension | Completed research foundation |
|---|---|
| Geographic scope | São Paulo, Brazil; weather analytics covering 642 municipalities |
| Public data | NASA POWER weather, IBGE agricultural statistics, and UNICA harvest reports |
| Historical modeling sample | 16 completed harvest seasons |
| Model comparison | Seven harvest-block models across five aggregation scales |
| Methods | OLS, partially penalized Ridge, nested leave-one-season-out tuning |
| Diagnostics | Coefficient stability, penalty-boundary selection, effective weather degrees of freedom |
| Engineering | Modular Python ETL, validation, feature engineering, modeling, reporting, and automated tests |

## Completed Study — Does Weather Improve Crushing Predictions?

### Question and Design

The v1.5.1 study tests whether September–April rainfall and temperature improve prediction of **harvest-block sugarcane crushing volume** beyond the historical harvest profile.

The reference model, **Block-Only OLS**, uses harvest-block fixed effects. Weather models add aggregate or month-level predictors. All seven models use the same outer leave-one-season-out (LOSO) folds; Ridge penalties are selected with an inner LOSO procedure.

### Results

| Rank | Model | Mean RMSE increase vs. Block-Only |
|---:|---|---:|
| 1 | Block-Only OLS | 0.00% |
| 2 | Temperature Month-Level Ridge | 1.00% |
| 3 | Aggregate Weather OLS | 2.45% |
| 4 | Rainfall Month-Level Ridge | 2.75% |
| 5 | Joint Month-Level Ridge | 11.76% |
| 6 | Temperature Month-Level OLS | 14.73% |
| 7 | Rainfall Month-Level OLS | 28.20% |

Values are the arithmetic mean of percentage RMSE increases across the five aggregation scales. Positive values indicate worse performance than the benchmark. The RMSE ranking is identical across all five scales.

![Seven-model RMSE comparison across harvest aggregation scales](docs/figures/month_level_model_rmse_comparison.png)

**The historical harvest-profile benchmark achieved the lowest held-out-season RMSE at every scale.** Ridge substantially reduced the error of unregularized monthly models, but weather features did not deliver stable incremental predictive value in this sample and model family.

Nested tuning frequently selected the maximum Ridge penalty, and median effective weather degrees of freedom was approximately zero. Fold-level diagnostics also identified seasons associated with unstable penalty selection and retained model complexity.

These results concern the evaluated linear specifications and crushing-volume target; they do not establish that weather is irrelevant to cane production. OS retains the negative results to guide subsequent experiments and make the limits of the evidence explicit.

See the [full findings](month_level_model_findings.md), [negative-results record](negative_results.md), and [saved comparison outputs](data/processed/modeling/month_level_baseline_results/).

## Current Research — From Crushing Volume to Annual Cane Yield

The next study will test whether weather is more informative for **annual cane yield, measured in tonnes of cane per hectare (TCH)**.

The motivation is that block-level crushing may combine crop conditions with harvest scheduling and processing activity. Annual yield offers a different target for studying agricultural productivity. This is a research hypothesis: the completed study did not identify the causes of its underperformance, and changing targets does not guarantee better predictions.

### Planned Experiment Sequence

| Step | Experiment | Question |
|---|---|---|
| 1 | Establish annual cane-yield benchmarks | How well do simple historical references predict TCH? |
| 2 | Apply the original eight-month rainfall and temperature information set | Does weather add information for the new target? |
| 3 | Extend to eight growing months plus four maturation months | Does the additional weather window improve prediction? |
| 4 | Add VPD, soil moisture, and solar radiation separately, then in combination | Which variable groups contribute incremental information? |

The proposed eight-plus-four-month division requires explicit calendar alignment and agronomic justification. Comparisons will use matched samples and information cutoffs so that changes in coverage are not mistaken for improvements from new features.

### Mechanism-Driven Variable Selection

| Candidate variable | Agricultural hypothesis to investigate |
|---|---|
| Vapor pressure deficit (VPD) | Atmospheric moisture demand and associated crop water-stress responses |
| Soil moisture | Water availability and persistence of deficits beyond rainfall totals |
| Solar radiation | Radiation availability and biomass accumulation |

These mechanisms will be supported with agronomic literature before model inclusion. Source definitions, soil depth, radiation measures, aggregation windows, and redundancy with existing predictors must be documented. Effects on cane biomass will be distinguished from effects on sugar content and recovery.

Small-sample uncertainty is another planned research focus, including Bayesian regression and posterior predictive analysis against regularized reference models. These extensions are **planned work**, not completed capabilities.

## Four-Layer Research Roadmap

| Layer | Research focus | Status |
|---|---|---|
| **1. Agricultural supply** | Weather → annual cane yield; compatible area data → cane production | Initial weather–crushing study completed; yield study is the next priority |
| **2. Sugar production and energy** | Cane → sugar output; sugar content/recovery, ethanol/sugar mix, and crude-oil–sugar-price relationships | Planned |
| **3. Currency** | BRL/USD and sugar prices; incremental information beyond agricultural and energy variables | Planned |
| **4. Supply chains** | Port activity, exports, transport, inventories, and interactions with sugar prices | Planned |

These layers define a research agenda, not an established causal chain. Later studies will distinguish association, predictive information, and causal hypotheses. Cane yield, total cane production, sugar output, and sugar prices require separate target definitions and benchmarks.

The roadmap also distinguishes raw sugar from refined white sugar. Any ICE No. 11 price study will specify the raw-sugar contract, forecast horizon, and contract-roll convention.

See [ROADMAP.md](ROADMAP.md) for experiment sequencing, completion criteria, and the retained release history.

## Methodology and Interpretation

- **Season-level evaluation:** complete seasons are held out together, avoiding random splits of blocks from the same season.
- **Nested tuning:** Ridge penalties are selected using only the outer training seasons.
- **Training-fold preprocessing:** weather standardization is fitted within each training fold, using one weather observation per season.
- **Partial regularization:** weather coefficients are penalized; the intercept and harvest-block effects remain unpenalized. The implementation uses residualization and linear-system solves.
- **Benchmark discipline:** model comparisons use matching targets, samples, and outer folds; unstable and negative results are documented.

### Evaluation Boundaries

LOSO evaluates generalization to a held-out season, but its training set can include later seasons. It is **not a chronological, point-in-time forecasting backtest**. Historical-vintage controls and expanding/rolling evaluations remain development goals.

The five aggregation scales combine base harvest periods into different block sizes; they are **not automatically one-to-five-month forecast lead times**. Full-period observed weather also constrains when a prediction could have been issued. Future studies will define forecast dates and publication availability before selecting features.

The effective weather sample is small: repeated harvest blocks do not create additional independent seasons. Findings should be interpreted within this sample, target, and specification set.

## Reproducibility

### Inspect Existing Results

The repository includes [model results](data/processed/modeling/), [research figures](docs/figures/), and detailed experiment records. These can be inspected without downloading the raw weather archive.

Additional visualizations include the [weather–harvest comparison](docs/figures/dashboard_season_comparison.png), [harvest calendar](docs/figures/harvest_heatmap.png), [historical percentile bands](docs/figures/harvest_percentile_bands.png), [penalty diagnostics](docs/figures/month_level_ridge_boundary_diagnostics.png), and [effective degrees of freedom](docs/figures/month_level_ridge_effective_degrees_of_freedom.png).

### Set Up

```bash
git clone https://github.com/DuranWang/operation-sugar.git
cd operation-sugar
python -m pip install -r requirements.txt
```

The project targets Python 3.12. Data ingestion and local preparation are required for a rebuild from source; cloning alone does not provide the raw weather archive.

### Run Analytics from Prepared Inputs

The analytics runner expects São Paulo daily weather CSVs under `data/raw/nasa_power/daily_weather/SP/`, together with the harvest inputs required by its modules. Consult the [architecture](docs/architecture.md) and module input paths before running.

```bash
python -m src.pipelines.run_pipeline
```

This runner performs weather aggregation, feature construction, dashboards, and harvest intelligence. Statistical model estimation is a separate workflow.

When rebuilding model-ready datasets, ensure harvest directory casing matches the code: the supplied snapshot contains `data/processed/unica/Crushing/`, while dataset builders reference `data/processed/unica/crushing/`. These differ on case-sensitive filesystems.

### Rerun the v1.5.1 Models

With the included model-ready CSVs under `data/processed/modeling/aggregate_baseline/` and `data/processed/modeling/month_level_baseline/`, the modeling sequence is:

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

To rebuild those input tables after preparing upstream weather–harvest data, use `src.modeling.aggregate_baseline_data` and `src.modeling.month_level_baseline_data`. The separate complete-season crushing experiment is implemented in `src.modeling.season_total_baseline`.

Model outputs are written under `data/processed/modeling/`; figures are written under `docs/figures/`.

### Run Tests

```bash
python -m pytest src/tests -v
```

The repository includes automated tests for ETL, validation, harvest processing, and weather feature engineering. Run the suite in the configured environment to determine the current collected-test count and pass status.

## Documentation

| Document | Purpose |
|---|---|
| [Architecture](docs/architecture.md) | Modules, data flow, and repository organization |
| [Modeling framework](docs/modeling_framework.md) | Model specifications and evaluation methodology |
| [Analytical framework](docs/analytical_framework.md) | Construction and validation of analytical variables |
| [Seasonal framework](docs/seasonal_framework.md) | Biological and operational seasonal definitions |
| [Harvest intelligence](docs/harvest_intelligence.md) | Historical harvest benchmarks |
| [Feature dictionary](docs/feature_dictionary.md) | Engineered-variable definitions |
| [Literature registry](docs/literature_registry.md) | Supporting agronomic literature |
| [Research decisions](research_decisions.md) | Engineering and analytical decisions |
| [Statistical experiments](statistical_experiments.md) | Experiment specifications and records |
| [v1.5.1 findings](month_level_model_findings.md) | Results and diagnostics |
| [Negative results](negative_results.md) | Specifications that did not generalize |
| [Roadmap](ROADMAP.md) / [Changelog](CHANGELOG.md) | Planned research and release history |

## Long-Term Benchmarking Goal

OS aims to make commodity forecasts easier to preserve, reproduce, and compare. Planned infrastructure includes standardized forecast records, preserved revisions, historical data vintages where available, and evaluation against multiple public reference forecasts. Brazilian sugar is the first application; broader expansion depends on validating the approach in this domain.

## Contributing and Contact

Suggestions, bug reports, and research collaborations are welcome. Contributions should prioritize clear assumptions, reproducibility, appropriate benchmarks, and demonstrable incremental value. Please open an issue before major architectural or modeling changes.

Contact: [Duran Wang on LinkedIn](https://www.linkedin.com/in/duranwang/).

Released under the [MIT License](LICENSE).
