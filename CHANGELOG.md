# Changelog

All notable changes to Operation Sugar are documented in this file.

This project follows **Semantic Versioning** and the general structure proposed by **Keep a Changelog**.

---

## [1.7.0] - 2026-10-09

### Annual-Yield Target, Weather–Yield Discovery, and EXP-03 Reproducibility

Operation Sugar v1.7.0 closes EXP-02 and EXP-03, establishing a reproducible adjusted-yield target and a compact downstream weather candidate universe for São Paulo annual sugarcane yield research.

### Added

- Completed municipality-first annual yield detrending with P50=10 as the primary historical specification and P50=12 as conservative robustness.
- Added annual harvested-area-weighted aggregation of municipality residuals to ERA5 0.5° grids.
- Added fixed common-support spatial-composition robustness.
- Added EXP-03 yield-stratified monthly weather analysis over the complete all-variable history.
- Added categorical, continuous, grouping, ranking-history, and spatial-heterogeneity robustness.
- Added March soil-moisture depth / regime reconstruction.
- Added bounded SoilGrids explanatory synthesis using native 0–200 cm source depths.
- Added EXP-03 representation and adjacent-month redundancy synthesis.
- Added a reproducible 38-representation downstream candidate universe.
- Added curated EXP-03 reports, summaries, and selected figures under `outputs/research/exp_03/`.
- Added dedicated EXP-03 analysis and validation modules.
- Added generated-data ignore rules for large reproducible EXP-03 intermediates and processed soil data.

### Changed

- Expanded the canonical all-variable weather history back to January 1981 while preserving EXP-01's approved 1990–2025 validation scope.
- Updated mixed historical NASA date parsing to support valid ISO date renderings.
- Reframed the active research sequence to run EXP-05 before EXP-04.
- Reduced clear representation duplication:
  - mean-daily solar is canonical over monthly total solar;
  - mean VPD is canonical over daily-max VPD;
  - 0–7 cm is canonical for the upper-soil-moisture family.
- Deferred dynamic Bayesian weather updating to a later Weather 2.0 phase.

### Research Findings

- The clearest late-weather relationship structure is Dec_(t-1) through Apr_t.
- Dec–Jan is strongest and most spatially broad.
- Feb–Mar contains materially greater cross-grid heterogeneity.
- April partially reconverges spatially.
- Relative humidity and deeper soil moisture are among the most spatially stable late-window signals.
- March soil-moisture response changes materially with depth, producing 42 positive-positive, 19 depth-recovery, 13 persistent-negative, and 2 reverse grids across the 76 usable grid-specific histories.
- SoilGrids differences across March depth regimes are suggestive but strongly entangled with latitude and production-support structure, so static soil remains explanatory-only.
- Only Dec–Jan relative humidity and Dec–Jan 28–100 cm soil moisture are promoted as multi-month candidate summaries.
- Temperature/VPD and rainfall/upper/deep-moisture conditional-information questions remain intentionally unresolved rather than collapsed by predictor correlation.

### Validation

- Focused analysis / weather-ETL / soil-ETL suite: **137 tests passing**.
- EXP-03 reproducibility closure reconstructs the frozen March regime counts and the 38-candidate downstream universe from data rather than hard-coded outputs.
- Large reconstructable intermediate tables remain local / ignored; curated reports and summaries are versioned.

### Next

The immediate next experiment is **EXP-05 — Conditional Temperature–VPD Yield Response**.

EXP-04 follows after EXP-05 and will focus on continuous relationship shape, magnitude, uncertainty, and target robustness without repeating the correlation screen already completed in EXP-03.

---

## [1.6.0] - 2026-09-27

### Weather Feature Structure, Spatial Weighting, and Annual-Yield Research Framework

Operation Sugar v1.6.0 completes the EXP-01 weather-structure research program and transitions the active research focus from harvest-block crushing prediction to annual agricultural sugarcane yield in São Paulo.

### Added

- Added combined NASA POWER and Open-Meteo / ERA5 monthly weather processing.
- Added municipality-level weather analysis covering 642 São Paulo municipalities from 1990 through 2025.
- Added EXP-01S harvested-area weight stability and observed-weight construction.
- Added EXP-01A municipality-level weather correlation and temporal-persistence analysis.
- Added EXP-01B harvested-area-weighted weather correlation analysis.
- Added EXP-01C matched-support sensitivity analysis separating support effects from harvested-area weighting effects.
- Added curated EXP-01 research outputs under `outputs/research/exp_01/`.
- Added finalized EXP-01S implementation and reproducibility tests.
- Added analysis tests for the EXP-01 research framework.
- Added the EXP-02A / EXP-02B / EXP-02C robustness sequence for annual-yield research.

### Changed

- Rebuilt and modularized parts of the weather and sugarcane ETL pipeline.
- Updated the primary research target from harvest-block crushing volume to annual agricultural sugarcane yield measured in tonnes of cane per hectare.
- Updated the README around the four-layer research framework and current annual-yield research program.
- Updated the roadmap to distinguish detrending uncertainty, spatial-composition sensitivity, and weather-relationship robustness.
- Separated generated working outputs from curated research artifacts committed to the repository.

### Research Findings

- Weather relationships are strongly dependent on calendar month.
- Pooled weather correlations can differ materially from within-calendar-month relationships.
- Surface soil moisture is substantially more persistent across months than precipitation.
- Harvested-area weighting changes the magnitude and persistence of core weather relationships more than matched-support exclusion does in the EXP-01 comparisons.
- São Paulo harvested-area shares are highly persistent from year to year but exhibit meaningful cumulative spatial change over longer horizons.
- EXP-01 establishes weather-feature structure and weighting sensitivity; it does not by itself determine which variables should enter the final annual-yield model.

### Validation

- `src/tests/analysis/`: 52 tests passing at the v1.6.0 release milestone.
- Focused combined-weather ETL tests passed before release.
- Curated EXP-01 outputs include research summaries, validation tables, and figures for EXP-01S, EXP-01A, EXP-01B, and EXP-01C.

### Notes

Version 1.6.0 marks the transition from the original harvest-block weather benchmark program to the annual-yield research program.

The next research step is EXP-02A, which tests whether annual yield anomalies remain stable across reasonable long-run trend specifications.

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