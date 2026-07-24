# Operation Sugar Roadmap

This document outlines the planned development roadmap for Operation Sugar.

Rather than continuously adding new variables, each release is designed to answer a distinct research question while maintaining a reproducible research engineering platform.

---

# Version 1.x — Baseline Research Platform

The Version 1.x series establishes the complete research infrastructure required for Brazilian sugarcane weather analytics.

Completed milestones include:

## v1.0.0

- NASA POWER weather ETL
- Municipality metadata validation
- Monthly weather aggregation
- Growing-season feature engineering
- Modular project architecture

---

## v1.1.0

- UNICA harvest ETL
- Historical harvest database
- Automated validation framework
- Static analytical dashboards
- Automated testing

---

## v1.2.0

- Historical weather archive
- Multi-season benchmark dashboards
- Literature-informed growing-season framework
- Historical weather benchmarking

---

## v1.3.0

- Historical harvest calendar
- Harvest calendar heatmap
- Harvest start metrics
- Harvest end metrics
- Harvest duration metrics
- Data-driven harvest-stage inference
- Three-stage seasonal research framework
  - Growing Stage
  - Maturation Stage
  - Harvest Stage

---

## v1.4.0 (Planned)

### Weather–Harvest Relationship

Objectives:

- Construct weather–harvest analytical datasets
- Correlation analysis between weather and harvest timing
- Regression analysis
- Historical weather–harvest visualization
- Baseline explanatory models

Version 1.4 establishes the baseline relationship between traditional weather variables and historical harvest behavior.

---

# Version 2.0 — Advanced Agroclimatic Features

Research Question

> Do advanced agroclimatic variables provide additional explanatory power beyond traditional weather variables?

Planned additions include:

- Soil moisture
- Vapor Pressure Deficit (VPD)
- Solar radiation
- Evapotranspiration (ET)

Rather than introducing these variables directly into predictive models, Version 2.0 will evaluate:

- correlation with existing weather features;
- multicollinearity;
- incremental explanatory value;
- model improvement relative to the baseline established in Version 1.x.

The objective is feature selection rather than feature accumulation.

---

# Version 3.0 — Maturation Analytics

Research Question

> Which environmental conditions govern sucrose accumulation before harvest?

Planned work:

- Maturation-window feature engineering
- Pre-harvest weather analytics
- Harvest-weighted weather variables
- Sugar accumulation indicators
- ATR-related environmental analysis

This stage extends Operation Sugar from biomass-oriented research toward sugar-production analytics.

---

# Future Research

Potential future extensions include:

## Climate

- ENSO indices
- Ocean-atmosphere oscillations
- Seasonal climate anomalies

## Remote Sensing

- Satellite-derived vegetation products
- Surface soil moisture
- Crop-condition monitoring

## Forecasting

- Yield prediction
- Sugar production forecasting
- Commodity-market research

## Explainable AI

- Feature importance
- Model interpretation
- Weather sensitivity analysis

---

# Long-Term Vision

Operation Sugar aims to become a reproducible research platform for Brazilian sugarcane analytics by integrating agronomic knowledge, observed harvest behavior, heterogeneous public datasets, transparent feature engineering, automated validation, and modular analytical workflows.

Rather than treating sugarcane production as a single "season", the platform studies the complete annual production cycle through three complementary analytical stages:

- Growing Stage
- Maturation Stage
- Harvest Stage

Future releases will continue expanding each stage while maintaining transparency, reproducibility, and scientific interpretability.