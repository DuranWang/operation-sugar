# Operation Sugar v1.0 Release Checklist

## Objective

Build a reproducible end-to-end agricultural analytics pipeline for Brazilian sugarcane weather research.

Operation Sugar v1.0 is a research platform, not a production-grade sugar price or sugarcane production forecasting system.

## Scope Rules

Every v1.0 task must contribute directly to making the project:

- Understandable
- Reproducible
- Runnable
- Extensible

The following topics are deferred to v1.1:

- Soil moisture
- Evapotranspiration
- Vapour pressure deficit
- ENSO indicators
- Satellite data
- Advanced harvest-progress weighting
- Advanced forecasting models

## Milestone 1: Data Pipeline

- [x] NASA POWER downloader
- [x] Municipality metadata
- [x] Data validation
- [x] Monthly aggregation
- [x] Folder structure
- [ ] Confirm end-to-end pipeline execution

No new pipeline functionality will be added unless a bug prevents the v1.0 workflow from running.

## Milestone 2: Feature Engineering

### General Weather Features

- [x] Total rainfall
- [x] Rainy-day count
- [x] Average temperature
- [x] Average relative humidity

### Dryness Features

- [x] Maximum consecutive dry days
- [ ] Dry-day count

### Agricultural Window Features

- [ ] Define fixed growing-season window
- [ ] Growing-season rainfall
- [ ] Growing-season temperature
- [ ] Define fixed maturation window
- [ ] Maturation-window rainfall
- [ ] Maturation-window temperature

### Feature Dataset

- [ ] Combine weather features into one municipality-level dataset
- [ ] Validate feature dataset
- [ ] Document feature definitions

Feature engineering stops when these items are complete.

## Milestone 3: Exploratory Data Analysis

- [ ] Create EDA notebook
- [ ] Rainfall distribution figure
- [ ] Temperature seasonality figure
- [ ] Dry-day distribution figure
- [ ] Municipality comparison figure
- [ ] Weather-feature relationship figure
- [ ] Summarize key observations

EDA stops after five publication-ready figures and a concise interpretation.

## Milestone 4: Baseline Modeling

- [ ] Define modeling unit and target variable
- [ ] Create train/test workflow
- [ ] Linear regression baseline
- [ ] Elastic Net baseline
- [ ] Random Forest baseline (optional)
- [ ] Report baseline metrics
- [ ] Document modeling limitations

The baseline demonstrates that the pipeline can supply a model. It is not presented as a production forecasting system.

## Milestone 5: Repository Release

- [x] Initial README
- [x] `.gitignore`
- [x] Initial `requirements.txt`
- [ ] Finalize README
- [ ] Add pipeline architecture diagram
- [ ] Add example notebook
- [ ] Add sample dataset
- [ ] Add license
- [ ] Clean repository structure
- [ ] Remove temporary and duplicate files
- [ ] Test installation from a clean environment
- [ ] Test documented commands
- [ ] Create GitHub repository
- [ ] Publish v1.0

## Post-Release

- [ ] Add GitHub link to resume
- [ ] Update project description on resume
- [ ] Publish LinkedIn project post