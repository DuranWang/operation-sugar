# Changelog

All notable changes to Operation Sugar are documented in this file.

This project follows **Semantic Versioning** and the general structure proposed by **Keep a Changelog**.

---
## [1.5.1] - 2026-07-26

### Month-Level Weather Modeling

Operation Sugar v1.5.1 extends the aggregate weather baseline framework with month-level weather representations, nested Ridge regularization, and a unified seven-model comparison framework for São Paulo harvest-block prediction.

### Added

- Added September–April month-level rainfall features.
- Added September–April month-level temperature features.
- Added Rainfall Month-Level OLS models.
- Added Rainfall Month-Level Ridge models.
- Added Temperature Month-Level OLS models.
- Added Temperature Month-Level Ridge models.
- Added Joint Month-Level Ridge models combining monthly rainfall and temperature predictors.
- Added nested leave-one-season-out cross-validation for Ridge hyperparameter selection.
- Added fold-specific weather standardization to all Ridge workflows.
- Added partially penalized Ridge regression with:
  - unpenalized intercept;
  - unpenalized harvest-block fixed effects;
  - penalized weather coefficients.
- Added effective weather degrees-of-freedom diagnostics.
- Added Ridge alpha-boundary diagnostics.
- Added fold-level alpha selection diagnostics.
- Added coefficient summaries and fold-level model diagnostics.
- Added unified seven-model comparison tables across all harvest aggregation horizons.
- Added publication-style reporting figures for:
  - model comparison;
  - RMSE improvement;
  - Ridge boundary selection;
  - effective weather degrees of freedom.
- Added `month_level_model_findings.md` documenting the complete Version 1.5 modeling study.

### Changed

- Refactored the month-level OLS engine to support generic weather feature specifications.
- Standardized model outputs across aggregate, rainfall, temperature, and joint weather models.
- Unified reporting pipelines for all seven evaluated models.
- Updated project documentation and README to reflect the completed month-level modeling framework.

### Notes

Version 1.5.1 completes the first month-level weather modeling framework in Operation Sugar.

The release adds nested Ridge regularization, unified seven-model evaluation, publication-style reporting figures, and accompanying research documentation.

See:

- `README.md`
- `docs/research/month_level_model_findings.md`

for the complete methodology, diagnostics, and research findings.


## [1.5.0] - 2026-07-26

### Aggregate Weather Baselines

Operation Sugar v1.5.0 introduces the project's first formal
out-of-sample statistical modeling framework for São Paulo
weather and sugarcane crushing.

### Added

- Expanded the São Paulo NASA POWER weather archive to cover
  September 2009 through April 2026.
- Extended growing-season weather features across 17 harvest years
  and 642 São Paulo municipalities.
- Constructed model-ready weather–harvest datasets for
  16 complete historical harvest seasons.
- Built five harvest-block aggregation datasets using
  aggregation horizons \(h = 1, 2, 3, 4, 5\).
- Implemented aggregate weather baseline models using:
  - total growing-season rainfall;
  - average growing-season temperature;
  - harvest-block position.
- Added harvest-block baseline models without weather predictors.
- Added complete-season baseline models comparing:
  - a training-season mean benchmark;
  - an aggregate weather model.
- Implemented leave-one-season-out cross-validation for all
  baseline models.
- Added standardized weather coefficients, prediction residuals,
  normalized error metrics, and incremental model comparisons.
- Added aggregate weather baseline dashboards for both
  harvest-block and complete-season prediction tasks.

### Changed

- Updated weather ingestion and aggregation workflows to
  automatically discover historical weather files rather than
  relying on manually maintained year lists.
- Updated the weather–harvest dataset to use the complete
  historical weather archive.
- Standardized weather predictors within each training fold
  to eliminate information leakage during cross-validation.
- Adopted complete harvest seasons as the unit of
  out-of-sample validation.

### Research Findings

Across 16 complete São Paulo harvest seasons, aggregate
growing-season rainfall and average temperature did not improve
out-of-sample crushing predictions.

At the harvest-block level:

- harvest-block position explained most of the predictable
  variation in seasonal crushing activity;
- adding aggregate rainfall and temperature slightly reduced
  predictive performance across all five aggregation horizons.

At the complete-season level:

- aggregate rainfall and temperature did not outperform a
  benchmark that predicted each held-out season using the
  average total crushing volume of the remaining training
  seasons;
- the aggregate weather model produced a lower
  cross-validated coefficient of determination and a higher
  normalized root mean squared error than the
  training-season mean benchmark.

Although rainfall and temperature coefficients were positive in
the complete-sample regressions, these relationships did not
generalize reliably to held-out harvest seasons.

### Research Interpretation

The results indicate that the strong predictive performance
observed at the harvest-block level is primarily driven by the
historical harvest calendar rather than aggregate weather
information.

The failure of aggregate weather variables at both the
harvest-block and complete-season levels suggests that
compressing the entire September–April growing season into one
rainfall total and one average temperature removes important
temporal information.

These findings establish the motivation for the next research
phase: month-level weather representations and temporally
structured statistical models.

---

## [1.4.0] - 2026-07-24

### Added

- Harvest Intelligence module
- Historical harvest calendar analytics
- Historical percentile-band benchmarking
- Comparable historical harvest snapshots
- Current season cumulative harvest rankings
- Automated harvest research summaries
- Harvest percentile-band visualization

### Improved

- Refactored harvest analytics into modular components
- Centralized pipeline logging
- Improved dashboard generation workflow

### Documentation

- Added Harvest Intelligence documentation
- Updated README with new dashboard previews
- Expanded analytical framework

## [1.3.0] - 2026-07-24

### Added

- Historical harvest calendar covering 16 completed Center-South Brazilian sugarcane seasons (2010–11 through 2025–26).
- Season-relative harvest timeline.
- Historical harvest calendar heatmap.
- Harvest timing metrics (start, end, and duration).
- Monthly harvest summary datasets.
- Dedicated harvest analytics workflow.
- Three-stage seasonal framework.
- Documentation for data-driven harvest analytics.

### Changed

- Introduced data-driven harvest-stage inference based on historical UNICA observations.
- Standardized historical harvest comparisons using season-relative months.
- Improved harvest outputs with both numeric indices and human-readable labels.
- Reorganized project documentation.

### Highlights

- Data-driven harvest analytics.
- Historical harvest calendar.
- Harvest timing metrics.
- Three-stage seasonal framework.

### Notes

Version 1.3 introduces the project's first data-driven harvest analytics layer, extending Operation Sugar beyond literature-informed growing-season analytics.

Historical UNICA crushing observations now provide an empirical benchmark for future weather–harvest relationship analysis.

---

## [1.2.0] - 2026-07-23

### Added

- Historical weather archive supporting complete growing seasons from 2019–20 through 2025–26.
- Multi-season historical benchmark dashboard.
- Automatic dashboard generation within the end-to-end pipeline.
- Historical weather–harvest benchmark dataset.

### Changed

- Introduced matched-cutoff harvest benchmarking.
- Standardized cumulative harvest comparisons using identical UNICA reporting cutoffs.
- Expanded monthly weather aggregation for multi-season analysis.
- Simplified the research pipeline to a single execution command.
- Established the literature-informed growing-season framework.

### Highlights

- Historical weather benchmarking.
- Automated end-to-end research pipeline.
- Multi-season benchmark dashboards.
- Literature-informed growing-season analytics.

### Notes

Version 1.2 established the literature-informed growing-season framework used throughout Operation Sugar for biomass-oriented weather analytics.

---

## [1.1.1] - 2026-07-23

### Added

- `research_engineering_challenges.md`.
- Documentation describing the platform's major research engineering challenges.
- Final reflection on the evolution of Operation Sugar into a research engineering platform.

### Changed

- Expanded documentation describing project architecture, engineering rationale, and reproducibility principles.

### Highlights

- Research engineering documentation.
- Improved project maintainability.
- Expanded design rationale.

### Notes

Although no analytical functionality was added, this release documents the engineering decisions supporting the platform's long-term reproducibility and maintainability.

---

## [1.1.0] - 2026-07-22

### Added

- UNICA harvest ETL pipeline.
- Historical harvest database updater.
- Weather–harvest dataset construction.
- Static analytics dashboards.
- Dashboard comparison visualization.
- 147 automated unit tests for the UNICA ETL pipeline.

### Changed

- Reorganized project structure.
- Improved project architecture.
- Updated project documentation.

### Fixed

- Corrected cumulative harvest calculations.
- Improved UNICA validation.
- Fixed duplicate harvest-period handling.

---

## [1.0.0] - 2026-07-19

### Added

- NASA POWER weather downloader.
- Municipality metadata validation.
- Monthly weather aggregation.
- Growing-season feature engineering.
- Weather feature modules.
- Initial automated testing.
- Initial project documentation.

### Changed

- Refactored ETL modules.
- Improved project structure.