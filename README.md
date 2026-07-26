![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.5-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

# Operation Sugar

An open-source research engineering platform for Brazilian sugarcane analytics.

Operation Sugar integrates official Brazilian sugarcane production statistics from IBGE, daily weather observations from NASA POWER, and harvest reports from UNICA into reproducible datasets, modular ETL pipelines, transparent statistical modeling workflows, and quantitative agricultural research.

Rather than focusing solely on predictive performance, the project emphasizes reproducible research infrastructure, biologically meaningful seasonal analytics, transparent engineering workflows, and rigorous out-of-sample model evaluation.

---

## Highlights

- 🌎 Weather analytics across 642 Brazilian sugar-producing municipalities
- 🌦️ Integrated NASA POWER, IBGE, and UNICA public datasets
- 📈 Historical harvest intelligence across 16 completed sugarcane seasons
- 📊 Aggregate weather baseline modeling with leave-one-season-out cross-validation
- 📉 Quantitative evaluation of weather predictors against historical benchmarks
- 🧪 167 automated unit tests, including 147 dedicated to the UNICA ETL pipeline
- 🏗️ Modular ETL, validation, analytics, modeling, and visualization architecture

---

## Dashboard Preview

### Weather & Harvest Benchmark

![Comparison](docs/dashboard_season_comparison.png)

*Compare historical weather conditions and matched-cutoff harvest progress across multiple São Paulo sugarcane seasons.*

### Historical Harvest Calendar

![Historical Harvest Calendar](docs/figures/harvest_heatmap.png)

*Visualize how annual sugarcane crushing is distributed across sixteen completed São Paulo harvest seasons.*

### Historical Percentile Benchmark

![Historical Percentile Bands](docs/figures/harvest_percentile_bands.png)

*Benchmark the current harvest against the historical distribution of completed seasons.*

### Harvest-Block Aggregate Weather Baseline

![Aggregate Baseline Dashboard](docs/figures/aggregate_baseline_dashboard.png)

*Evaluate whether aggregate growing-season rainfall and temperature improve out-of-sample prediction of harvest-block crushing beyond historical harvest timing.*

### Complete-Season Aggregate Weather Baseline

![Season Total Baseline Dashboard](docs/figures/season_total_baseline_dashboard.png)

*Compare aggregate weather predictors against a historical mean benchmark for complete-season crushing using leave-one-season-out cross-validation.*

Across both prediction tasks, aggregate growing-season weather did **not** improve out-of-sample predictive performance, motivating the transition toward month-level weather representations in future releases.

For a detailed explanation of the Harvest Intelligence methodology, see **docs/harvest_intelligence.md**.

---

## Why Operation Sugar?

Brazilian sugarcane data are publicly available but fragmented across multiple organizations, temporal resolutions, and geographic scales.

Operation Sugar integrates these heterogeneous datasets into a reproducible research platform for weather analytics, harvest intelligence, and statistical modeling.

---

## Seasonal Research Framework

Operation Sugar studies the annual sugarcane production cycle through three analytical stages.

```text
Growing Stage
        │
        ▼
Maturation Stage
        │
        ▼
Harvest Stage
```

---

## Core Capabilities

Operation Sugar provides a reproducible research engineering workflow for Brazilian sugarcane analytics, including:

- Automated NASA POWER weather ingestion
- UNICA harvest report ETL pipeline
- Historical harvest database updater
- Municipality-level weather aggregation
- Growing-season feature engineering
- Historical harvest calendar construction
- Monthly crushing distribution analysis
- Harvest timing metrics
- Historical percentile-band benchmarking
- Comparable historical harvest snapshots
- Automated harvest research summaries
- Weather–harvest dataset construction
- Statistical baseline modeling
- Leave-one-season-out cross-validation
- Historical benchmark dashboards
- Comprehensive data validation
- 167 automated unit tests

---

## Project Goals

Operation Sugar aims to build a reproducible end-to-end research platform that:

- integrates heterogeneous public agricultural datasets;
- engineers interpretable weather and harvest variables;
- produces analysis-ready datasets for statistical analysis;
- supports transparent and reproducible research workflows;
- establishes reliable data infrastructure before predictive modeling;
- evaluates new variables based on their incremental analytical value rather than simply increasing feature count.

---

## Current Version

Version **1.5** extends Operation Sugar beyond data engineering and historical analytics by introducing its first statistical modeling framework.

The current release evaluates aggregate growing-season weather variables using reproducible out-of-sample validation and establishes quantitative baselines for future month-level weather models.

See **CHANGELOG.md** for detailed release history.

---

## Current Limitations

Operation Sugar does **not** currently model:

- month-level weather effects;
- maturation-stage weather effects;
- soil moisture;
- vapor pressure deficit;
- solar radiation;
- evapotranspiration;
- sucrose concentration;
- ATR;
- recoverable sugar;
- mill-level production;
- satellite-derived crop conditions;
- sugar price forecasting.

These topics remain future research directions and are intentionally excluded from Version 1.5.

---

## Documentation

Detailed project documentation is available in the `docs/` directory.

| Document | Description |
|----------|-------------|
| **Architecture** | Overall platform architecture and system organization |
| **Seasonal Framework** | Definitions of growing, maturation, and harvest stages |
| **Analytical Framework** | Design of weather and harvest analytics |
| **Research Decisions** | Major analytical and research decisions |
| **Feature Dictionary** | Definitions of engineered variables |
| **Literature Registry** | Supporting agronomic literature |
| **Research Engineering Challenges** | Engineering challenges encountered during development |
| **ROADMAP** | Planned future development |
| **CHANGELOG** | Release history |

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Municipalities | 642 |
| Historical Weather Archive | September 2009 – April 2026 |
| Historical Harvest Seasons | 17 (16 completed) |
| Weather Variables | Rainfall, Temperature, Relative Humidity |
| Statistical Models | Aggregate Weather Baselines |
| Cross Validation | Leave-One-Season-Out |
| Automated Tests | 167 |
| UNICA ETL Tests | 147 |
| Python | 3.12 |

---

## Engineered Features

### Weather Analytics

- Baseline weather summaries
- Growing-season weather variables
- Drought indicators

### Harvest Analytics

Current harvest analytics include:

- Historical harvest calendar
- Historical percentile-band benchmarking
- Comparable historical harvest snapshots
- Cumulative harvest pace rankings
- Harvest timing metrics
- Automated harvest research summaries

### Statistical Modeling

Current statistical modeling includes:

- Aggregate weather baseline models
- Harvest-block prediction
- Complete-season prediction
- Leave-one-season-out cross-validation
- Historical benchmark comparison

### Planned Features

Future research will extend the platform with:

- Month-level weather modeling
- Maturation-stage weather analytics
- Soil moisture
- Vapor pressure deficit (VPD)
- Solar radiation
- Evapotranspiration
- Sugar quality metrics (ATR, sucrose)
- Satellite-derived crop indicators

---

## Data Sources

| Source | Description |
|---------|-------------|
| **NASA POWER** | Daily weather observations |
| **IBGE** | Municipality metadata and annual sugarcane production |
| **UNICA** | Harvest progress and crushing statistics |

These heterogeneous public datasets are integrated through reproducible ETL, validation, aggregation, analytics, and statistical modeling workflows.

---

## Output

The pipeline produces:

- processed weather datasets;
- harvest analytics datasets;
- statistical modeling datasets;
- benchmark dashboards;
- harvest intelligence datasets;
- automated research summaries;
- unified research datasets.

---

## Quick Start

```bash
git clone https://github.com/DuranWang/operation-sugar.git

cd operation-sugar

pip install -r requirements.txt

python -m src.pipelines.run_pipeline

python -m pytest src/tests -v
```

What happens?

✓ Download weather data

✓ Process harvest reports

✓ Build research datasets

✓ Train baseline statistical models

✓ Generate dashboards

---

## Testing

Run all tests:

```bash
python -m pytest src/tests -v
```

Current status:

```text
167 automated tests
100% passing
```

The automated test suite covers:

- ETL pipelines
- Validation
- Schema consistency
- Historical harvest processing
- Duplicate detection
- Temporal consistency

---

## Contributing

Suggestions, bug reports, feature requests, and research collaborations are welcome.

Contributions should prioritize:

- reproducibility;
- transparent assumptions;
- reliable validation;
- interpretable analytics;
- clear documentation.

---

## License

Released under the MIT License.

For research collaboration, commercial partnerships, or custom development related to Operation Sugar, please contact the author via LinkedIn:

https://www.linkedin.com/in/duranwang/