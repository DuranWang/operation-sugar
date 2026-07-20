![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.0-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

```text
                 IBGE
                   \
                    \
NASA POWER ──► ETL ──► Monthly Weather ──► Growing Season ──► ML Models
                    /
                   /
               UNICA
```

# Operation Sugar

Operation Sugar is an open-source data engineering project for Brazilian sugarcane analytics.

The project integrates municipal sugarcane production statistics published by IBGE with daily weather observations from NASA POWER, producing analysis-ready datasets for agricultural analytics and statistical modeling.

Its long-term objective is to provide an extensible research platform for weather-driven sugarcane production analytics.

## Features

- Validate municipality metadata

- Download NASA POWER weather data

- Process agricultural production data

- Aggregate monthly weather

- Engineer weather features

- Generate growing-season features

- Export analysis-ready datasets

## Project Goals

Build a reproducible end-to-end pipeline that:
- Cleans and validates Brazilian sugarcane production data 
- Engineers weather features relevant to sugarcane growth 
- Prepares datasets for exploratory analysis and future forecasting models

## Current Version Limitations

Version 1.0 focuses on weather-driven biomass accumulation.

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
│   └── schemas/
│
├── src/tests/
│   ├── etl/
│   └── feature_engineering/
│
├── LICENSE
├── README.md
├── requirements.txt
└── RELEASE_CHECKLIST.md
```

## Data Sources

| Source | Description | Website |
|---------|-------------|---------|
| **NASA POWER** | Daily gridded weather observations, including precipitation, air temperature, and relative humidity. | [NASA POWER](https://power.larc.nasa.gov/) |
| **IBGE** | Official Brazilian municipality metadata and sugarcane production statistics. | [IBGE](https://www.ibge.gov.br/) |
| **UNICA** | Harvest progress, sugarcane crushing, sugar production, and ethanol production statistics for Brazil's Center-South region. | [UNICA Data](https://unicadata.com.br/) |

The project integrates these independent data sources into a unified analysis-ready dataset through a reproducible ETL pipeline.

## Why this Project?

Weather is one of the primary drivers of sugarcane growth and production. However, publicly available agricultural datasets are often fragmented across multiple sources with different formats and temporal resolutions.

Operation Sugar integrates official production statistics from IBGE, daily weather observations from NASA POWER, and harvest information from UNICA into a single reproducible analytics pipeline, providing analysis-ready datasets for agricultural research, exploratory analysis, and future predictive modeling.


## Project Statistics

Current Version (v1.0)

| Metric              | Value                                    |
| ------------------- | ---------------------------------------- |
| Municipalities      | 642                                      |
| Temporal Resolution | Daily                                    |
| Weather Variables   | Rainfall, Temperature, Relative Humidity |
| Input Years         | 2019–2021                                |
| Harvest Years       | 2020–2021                                |
| Automated Tests     | 20                                       |
| Python              | 3.12                                     |


The project is fully modularized, with dedicated ETL, feature engineering, validation, and testing components to ensure reproducibility and maintainability.


## Engineered Features

| Category | Features |
|----------|----------|
| Rainfall | Total rainfall, Rainy days, Dry day count, Maximum consecutive dry days |
| Temperature | Average temperature |
| Humidity | Average humidity |
| Growing Season | Growing-season total rainfall, Growing-season average temperature, Observation days, Start date, End date |

## Example Output

The growing-season feature pipeline produces one observation per municipality and harvest year.

Example (`data/processed/growing_season/SP/growing_season_features.csv`):

```csv
ibge_code,municipality,state,harvest_year,growing_season_total_rainfall,growing_season_average_temperature,growing_season_observation_days,growing_season_start,growing_season_end
3500105,Adamantina,SP,2020,884.76,26.94,243,2019-09-01,2020-04-30
3500105,Adamantina,SP,2021,538.19,27.83,242,2020-09-01,2021-04-30
3500204,Adolfo,SP,2020,948.71,26.18,243,2019-09-01,2020-04-30
3500204,Adolfo,SP,2021,648.53,27.03,242,2020-09-01,2021-04-30
3500303,Aguaí,SP,2020,1037.72,23.46,243,2019-09-01,2020-04-30
```

Each record summarizes the weather conditions experienced by one municipality during a single sugarcane growing season.

## Output

The pipeline produces analysis-ready datasets, including:

- Daily municipality weather observations
- Monthly aggregated weather summaries
- Growing-season feature tables

Processed datasets are organized under:

```text
data/processed/
├── sp_monthly_weather_2020.csv
└── growing_season/
    └── SP/
        └── growing_season_features.csv
```

All processed datasets are exported as CSV files.

## Pipeline Workflow

1. Download municipality metadata
2. Download NASA POWER weather observations
3. Validate raw datasets
4. Aggregate daily observations into monthly summaries
5. Engineer weather features
6. Build growing-season features
7. Export processed datasets

## Testing

Run all automated tests

```bash
python -m pytest src/tests -v
```

Current status

```text
20 automated tests
100% passing
```

## Quick Start

Clone the repository

```bash
git clone ...
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the weather downloader

```bash
python -m src.download_nasa_power
```

Run monthly aggregation

```bash
python -m src.etl.aggregate_monthly_weather
```

Generate growing-season features

```bash
python -m src.etl.build_growing_season_features
```

## License

This project is released under the [MIT License](LICENSE).

## Roadmap

### Version 1.0 ✅

- Weather download pipeline
- Monthly aggregation
- Weather feature engineering
- Growing-season summaries

### Version 1.1 🔄

- Additional weather variables
  - Soil moisture
  - Evapotranspiration
  - Vapor pressure deficit
- Climate indices
  - ENSO
- Remote sensing
  - Satellite products

## Contributing

Suggestions, bug reports, and feature requests are welcome.