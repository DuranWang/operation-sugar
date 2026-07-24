# Operation Sugar Architecture

Operation Sugar is organized as a modular research engineering platform that processes heterogeneous public datasets through independent ETL pipelines before integrating them into unified research datasets for downstream analytics.

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
                Weather Analytics                                      Harvest Analytics
                           │                                                         │
                           └────────────────────────────┬────────────────────────────┘
                                                        ▼
                                             Historical Benchmark
                                                   Dashboards
```

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

The weather pipeline transforms daily NASA POWER observations into validated analysis-ready weather datasets.

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

The weather and harvest pipelines are processed independently before integration.

The unified dataset serves as the foundation for:

- weather analytics;
- harvest analytics;
- historical benchmark dashboards;
- future weather–harvest relationship analysis.

---

# Design Principles

## Modular Architecture

Weather processing, harvest processing, validation, and analytics are implemented as independent modules to improve maintainability and extensibility.

---

## Independent ETL Pipelines

Each public dataset is processed independently before integration, reducing coupling between heterogeneous data sources.

---

## Validation First

Every processing stage performs validation before downstream analysis to ensure reproducibility and data quality.

---

## Unified Analytics Layer

Weather and harvest data remain independent during processing but are combined into a unified analytical dataset for downstream research.

---

# Related Documentation

For analytical methodology, see:

- `seasonal_framework.md`
- `analytical_framework.md`
- `research_design_decisions.md`

For future development, see:

- `ROADMAP.md`