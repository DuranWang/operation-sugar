# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by **Keep a Changelog**.
Versioning follows **Semantic Versioning**.

---

## [1.2.0] - 2026-07-23

### Added

- Historical weather archive supporting complete growing seasons from 2019–20 through 2026–27.
- Multi-season historical benchmark dashboard.
- Automatic generation of all research dashboards within the end-to-end pipeline.
- Historical weather–harvest benchmark dataset.

### Changed

- Introduced matched-cutoff harvest benchmarking methodology.
- Standardized cumulative harvest comparisons using identical UNICA reporting cutoffs.
- Expanded monthly weather aggregation to support multi-season historical analysis.
- Pipeline now generates all dashboard artifacts automatically.
- Simplified the Quick Start workflow to a single pipeline command.

### Highlights

- Historical benchmark framework for weather and harvest analysis.
- One-command end-to-end reproducible research pipeline.
- Seven-season historical benchmarking capability.

### Notes

This release marks the evolution of Operation Sugar
from a seasonal analytics project into a historical
research platform capable of reproducible multi-season
benchmarking.

## [1.1.1] - 2026-07-23

### Added

- Added `research_engineering_challenges.md`.
- Documented six major research engineering challenges encountered during platform development.
- Added a final reflection describing the evolution of Operation Sugar from a forecasting project into a research engineering platform.

### Documentation

- Explained the rationale behind the platform's modular ETL architecture.
- Documented engineering decisions related to:
  - heterogeneous data integration
  - large-scale API collection
  - temporal alignment
  - literature-driven feature engineering
  - automated data validation
  - reproducible research infrastructure

### Changed

- Expanded project documentation to emphasize research engineering principles rather than only technical implementation.

### Highlights

- Introduced comprehensive research engineering documentation.
- Expanded project architecture and design rationale.
- Improved reproducibility, maintainability, and developer experience.

### Notes

Although no new analytical features were introduced in this release, documenting the engineering decisions behind the platform is essential for reproducibility, maintainability, and future development.

This release marks the transition of Operation Sugar from a collection of analytical tools toward a documented research engineering platform.

---

## [1.1.0] - 2026-07-22

### Added

- UNICA harvest ETL pipeline
- Historical harvest database updater
- Weather–harvest dataset construction
- Static analytics dashboards
- Dashboard comparison visualization
- 147 automated unit tests for the UNICA ETL modules

### Changed

- Reorganized project structure
- Updated README documentation
- Improved project architecture

### Fixed

- Corrected cumulative harvest calculation.
- Improved UNICA data validation.
- Fixed duplicate harvest period handling.

---

## [1.0.0] - 2026-07-19

### Added

- NASA POWER weather downloader
- Municipality metadata validation
- Monthly weather aggregation
- Growing-season feature engineering
- Weather feature modules
- Initial automated testing
- Project documentation

### Changed

- Refactored ETL modules.
- Improved project folder structure.