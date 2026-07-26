# Operation Sugar Architecture

Operation Sugar is organized as a modular quantitative research platform that processes heterogeneous public datasets through independent ETL pipelines before integrating them into unified research datasets for statistical modeling and downstream analytics.

---

# System Architecture

```text
                     IBGE
                      │
                      ▼
               Municipality Metadata

NASA POWER ───► Weather ETL ─────────────┐
                                         │
UNICA ───────► Harvest ETL ──────────────┼──────────────┐
                                         │              │
Seasonal Framework ──────────────────────┘              │
                                                        ▼
                                              Unified Research Dataset
                                                        │
                           ┌────────────────────────────┴────────────────────────────┐
                           ▼                                                         ▼
                  Statistical Modeling                                   Historical Analytics
                           │                                                         │
                           └────────────────────────────┬────────────────────────────┘
                                                        ▼
                                                 Research Outputs
```

The Unified Research Dataset serves as the common analytical foundation for statistical modeling, historical analytics, and future research workflows.

---

# Weather Pipeline

```text
NASA POWER
      │
      ▼
Weather Downloader
      │
      ▼
Validation
      │
      ▼
Monthly Aggregation
      │
      ▼
Feature Engineering
      │
      ▼
Weather Dataset
```

The weather pipeline transforms daily NASA POWER observations into validated analysis-ready weather datasets for downstream statistical modeling and analytics.

---

# Harvest Pipeline

```text
Historical Database
        │
        ▼
UNICA ETL
        │
        ▼
Validation
        │
        ▼
Harvest Analytics
        │
        ▼
Harvest Dataset
```

The harvest pipeline maintains a continuously updated historical harvest database and derives reproducible harvest analytics from official UNICA reports.

---

# Unified Research Dataset

Weather and harvest pipelines are processed independently before integration.

The resulting unified research dataset serves as the common input for:

- statistical modeling;
- weather analytics;
- harvest analytics;
- historical benchmark dashboards;
- future weather–harvest relationship analysis.

---

# Design Principles

## Modular Architecture

Weather processing, harvest processing, feature engineering, statistical modeling, and analytics are implemented as independent modules to improve maintainability and extensibility.

---

## Independent ETL Pipelines

Each public dataset is processed independently before integration, reducing coupling between heterogeneous data sources.

---

## Validation First

Every processing stage performs validation before downstream analysis to ensure reproducibility and data quality.

---

## Unified Research Dataset

Weather and harvest data remain independent during processing before being integrated into a unified research dataset for downstream statistical modeling and analytics.

---

## Reproducible Research

Research datasets are generated through reproducible ETL pipelines, ensuring that statistical experiments can be repeated using the same validated data sources.

---

# Relationship to Project Documentation

This document describes the software architecture of Operation Sugar.

The agronomic framework is documented in **seasonal_framework.md**.

The research and engineering decisions are documented in **research_design_decisions.md**.

The statistical modeling methodology is documented in **modeling_framework.md**.

Individual statistical experiments are documented in **statistical_experiments.md**.

---

# Future Development

Future architectural extensions are described in **ROADMAP.md**.