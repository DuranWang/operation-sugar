![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.1-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

# Operation Sugar

An open-source agricultural data engineering platform for Brazilian sugarcane analytics.

Operation Sugar integrates official Brazilian sugarcane production statistics (IBGE), daily weather observations (NASA POWER), and harvest reports (UNICA) into reproducible weather–harvest datasets and analytics dashboards for Brazilian sugarcane research.

## Highlights

- 🌎 642 Brazilian sugar-producing municipalities
- 🌦️ NASA POWER + IBGE + UNICA data integration
- 🧪 167 automated unit tests (147 dedicated to the UNICA ETL pipeline)
- 📊 Automated weather–harvest analytics dashboards
- 🏗️ Modular ETL and feature engineering architecture

## Dashboard Preview

### Season Comparison Dashboard

![Comparison](docs/dashboard_season_comparison.png)

*Compare weather conditions and harvest progress across multiple Brazilian sugarcane seasons.*

### Single-season Dashboard

![Dashboard](docs/dashboard_v1.png)

*Detailed weather and harvest analytics for an individual growing season.*

## Architecture
```text
          IBGE
           │
           ▼
     Production Data
           │
           ▼

NASA POWER ──► Weather ETL ──┐
                             │
UNICA ───────► Harvest ETL ──┼──► Weather–Harvest Dataset
                             │
Growing-Season Features ─────┘
                 │
                 ▼
        Analytics Dashboard
```

## Features

- Automated NASA POWER weather ingestion
- UNICA harvest report ETL pipeline
- Historical harvest database updater
- Municipality-level weather aggregation
- Growing-season feature engineering
- Weather–harvest dataset construction
- Static analytics dashboards
- Comprehensive data validation
- 167 automated unit tests

## Project Goals

Operation Sugar aims to build a reproducible end-to-end pipeline that:

- Cleans and validates Brazilian sugarcane production data 
- Engineers weather features relevant to sugarcane growth 
- Prepares datasets for exploratory analysis, future statistical analysis, and forecasting models

## Current Version Limitations

Version 1.1 focuses on weather-driven biomass accumulation.

It does not currently model:

- Sugar price
- Sucrose concentration
- ATR
- Recoverable sugar
- Mill-level production

The scope is intentionally limited to establish a reproducible research pipeline before incorporating more advanced environmental variables.

## Project Structure

```text
Operation Sugar
│
├── data
│   ├── raw/
│   │   ├── nasa_power/
│   │   └── unica/
│   │
│   ├── processed/
│   └── metadata/
│
├── docs/
│
├── src/
│   ├── etl/
│   │   ├── unica/
│   │   ├── loader.py
│   │   ├── saver.py
│   │   ├── summary.py
│   │   ├── validator.py
│   │   ├── aggregate_monthly_weather.py
│   │   └── build_growing_season_features.py
│   │
│   ├── feature_engineering/
│   │   ├── rainfall.py
│   │   ├── temperature.py
│   │   ├── growing_season.py
│   │   └── pipeline.py
│   │
│   ├── pipelines/
│   │   └── build_weather_harvest_dataset.py
│   │
│   ├── visualization/
│   │   ├── build_dashboard.py
│   │   └── build_comparison_dashboard.py
│   │
│   └── schemas/
│
├── src/tests/
│   ├── etl/
│   │   └── unica/
│   └── feature_engineering/
│
├── LICENSE
├── README.md
└── requirements.txt
```

## Data Sources

| Source | Description | Website |
|---------|-------------|---------|
| **NASA POWER** | Daily gridded weather observations, including precipitation, air temperature, and relative humidity. | [NASA POWER](https://power.larc.nasa.gov/) |
| **IBGE** | Official Brazilian municipality metadata and sugarcane production statistics. | [IBGE](https://www.ibge.gov.br/) |
| **UNICA** | Harvest progress, sugarcane crushing, sugar production, and ethanol production statistics for Brazil's Center-South region. | [UNICA Data](https://unicadata.com.br/) |

The project integrates these independent data sources into a unified analysis-ready dataset through a reproducible ETL pipeline.

## Why this Project?

Public agricultural datasets are often fragmented across multiple organizations, formats, and temporal resolutions.

Operation Sugar integrates IBGE production statistics, NASA POWER weather observations, and UNICA harvest reports into a unified, reproducible analytics pipeline.

The resulting datasets support agricultural research, exploratory analysis, and future forecasting models.


## Project Statistics

Current Version (v1.1)

| Metric              | Value                                    |
| ------------------- | ---------------------------------------- |
| Municipalities      | 642                                      |
| Temporal Resolution | Daily                                    |
| Weather Variables   | Rainfall, Temperature, Relative Humidity |
| Input Years         | 2019–2021                                |
| Harvest Years       | 2020–2021                                |
| Automated Tests     | 167 (147 for UNICA ETL)                  |
| Python              | 3.12                                     |


The project is fully modularized, with dedicated ETL, feature engineering, validation, and testing components to ensure reproducibility and maintainability.


## Engineered Features

### Weather Features

- Growing-season rainfall
- Rainy days
- Dry days
- Average temperature
- Average humidity
- Maximum consecutive dry days
- Average maximum consecutive dry days

### Harvest Features

- Harvest season
- Latest report date
- Harvest period count
- Cumulative crushing


## Output

The pipeline produces analysis-ready datasets, including:

- Daily municipality weather observations
- Monthly aggregated weather summaries
- Growing-season weather features
- Historical UNICA harvest database
- Weather–harvest datasets
- Analytics dashboard outputs

Processed datasets are organized under:

```text
data/
├── raw/
│   ├── nasa_power/
│   └── unica/
│
└── processed/
    ├── monthly_weather/
    ├── growing_season/
    ├── unica/
    │   └── crushing/
    └── dashboard/
        └── weather_harvest_dataset.csv
```

The visualization pipeline exports dashboard images to:

```text
docs/
├── dashboard_v1.png
└── dashboard_season_comparison.png
```

All processed datasets are exported as CSV files, while dashboard outputs are exported as PNG images.

## Pipeline Workflow

```text
Metadata
    │
    ▼
NASA POWER ETL
    │
    ▼
UNICA ETL
    │
    ▼
Validation
    │
    ▼
Growing-Season Features
    │
    ▼
Weather-Harvest Dataset
    │
    ▼
Dashboard
```

## Testing

Run all tests

```bash
python -m pytest src/tests -v
```

Current status

```text
167 automated unit tests
100% passing
```

The UNICA ETL pipeline alone is covered by 147 automated unit tests spanning PDF parsing, table extraction, normalization, validation, and historical database updates.

## Quick Start

Clone the repository

```bash
git clone https://github.com/DuranWang/operation-sugar.git
cd operation-sugar
```

Install dependencies

```bash
pip install -r requirements.txt
```

Download NASA POWER weather observations

```bash
python -m src.download_nasa_power
```

Aggregate daily weather into monthly summaries

```bash
python -m src.etl.aggregate_monthly_weather
```

Generate growing-season weather features

```bash
python -m src.etl.build_growing_season_features
```

Build the weather–harvest dashboard dataset

```bash
python -m src.pipelines.build_weather_harvest_dataset
```

Generate the single-season dashboard

```bash
python -m src.visualization.build_dashboard
```

Generate the season-comparison dashboard

```bash
python -m src.visualization.build_comparison_dashboard
```

Run all automated tests

```bash
python -m pytest src/tests -v
```

The generated datasets and dashboard figures will be saved under the `data/processed/` and `docs/` directories.

## License

This project is released under the [MIT License](LICENSE).


## Contributing

Suggestions, bug reports, and feature requests are welcome.