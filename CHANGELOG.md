# Changelog

All notable changes to Operation Sugar are documented in this file.

This project follows **Semantic Versioning** and the general structure proposed by **Keep a Changelog**.

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