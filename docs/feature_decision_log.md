# Feature Decision Log

This document records the major feature engineering decisions made during
the development of Operation Sugar.

Each decision documents not only what was chosen,
but also why alternatives were rejected.
===============================================================================================
Decision 01: 

## Project Scope Freeze (GitHub v1.0)

### Decision

Freeze the scope of GitHub v1.0.

### Included

- Total Rainfall
- Rainy Days
- Average Temperature
- Average Humidity
- Dry Day
- Dry Day Count
- Maximum Consecutive Dry Days
- Growing Season Rainfall
- Maturation Window Rainfall
- Maturation Window Temperature

### Deferred

- Soil Moisture
- Water Deficit
- ET / ET₀
- VPD
- ENSO
- Satellite Features

### Reason

The objective of GitHub v1.0 is to build a reproducible
weather-based feature engineering pipeline rather than an exhaustive
crop physiology model.

Keeping the scope limited improves maintainability,
reproducibility and project completeness.
======================================================================================================
Decision 02:

## Dry Day Definition

### Decision

Adopt the ETCCDI definition.

### Definition

A Dry Day is defined as daily precipitation < 1 mm.

### Scientific Motivation

The ETCCDI definition is the internationally accepted standard
used by climate science and drought monitoring communities.

### Alternatives Considered

- 0 mm
- 0.1 mm
- 2 mm

Rejected because they are either less common
or region-specific.
======================================================================================
Decision 03:

## Maximum Consecutive Dry Days (CDD)

### Decision

Include in GitHub v1.0.

### Scientific Motivation

CDD measures the persistence of rainfall deficits rather than
their frequency.

Persistent dry periods are more likely to cause
continuous soil moisture depletion and water stress.

### Interpretation

CDD is a rainfall-based climate proxy.

It is not a direct measure of

- soil moisture

or

- physiological water stress.

### Alternatives Considered

Dry Day Count

Rejected as the primary feature because it measures
frequency rather than persistence.
==================================================================================================
## Growing Season Maximum Consecutive Dry Days

### Decision

Calculate CDD during the growing season rather than
over the entire calendar year.

### Reason

The current project predicts sugarcane production,
which primarily reflects biomass accumulation.

Water stress during vegetative growth is therefore
more biologically relevant than water stress occurring
outside the growing season.

### Alternatives Considered

Annual CDD

Rejected because it includes periods outside
biologically relevant crop development.

Ripening-window CDD

Deferred because it is expected to be more relevant
for sugar accumulation than biomass production.
========================================================================================
Decision 05

## Literature-driven Feature Engineering

### Decision

Every feature included in Operation Sugar
must have scientific evidence.

### Workflow

Literature

↓

Literature Registry

↓

Feature Decision

↓

Feature Definition

↓

Python Implementation

### Reason

This ensures every engineered feature
has traceable scientific justification.

Features are added because literature supports them,
not because they are easy to compute.
=========================================================================================================
Decision 06:

## Evidence Registry

### Decision

Assign a unique Paper ID
to every core publication.

### Example

P01

Cardozo & Sentelhas

P02

ETCCDI

P03

Nature (2024)

...

### Reason

Paper IDs simplify documentation,
avoid repeated citations,
and improve traceability.
===========================================================================================
Decision 07:

## Feature Selection Strategy

### Decision

Prioritize biologically meaningful variables
over statistically convenient variables.

### Principle

Every feature should represent
a known agronomic or physiological process.

### Examples

Rainfall

↓

Water availability

CDD

↓

Persistence of rainfall deficit

Temperature

↓

Thermal accumulation

rather than arbitrary statistical transformations.

====================================================================================================
Decision 08:

## Growing Season Stage Definition

### Decision

For GitHub v1.0, the sugarcane growing season combines:

- plant establishment or ratoon regrowth;
- tillering;
- stalk elongation or grand growth.

The maturation period is treated as a separate biological window.

### Reason

Operation Sugar currently models sugarcane production rather than sugar
content or recoverable sugar output. Establishment, tillering, and stalk
elongation collectively represent the main period of canopy development,
stalk formation, and biomass accumulation.

Combining these stages provides a biologically meaningful and reproducible
window without requiring an excessively detailed crop-development model.

### Ratoon-Cane Consideration

The term "establishment or regrowth" is used instead of only "planting"
because ratoon sugarcane begins a new production cycle through regrowth
following harvest rather than through replanting.

### Alternatives Considered

- Treat each development stage as a separate feature window:
  deferred because it would substantially increase feature complexity and
  require more precise municipality-level phenological data.

- Include maturation in the growing season:
  rejected because maturation is more directly associated with ripening and
  sucrose accumulation than with primary biomass formation.

- Use the full calendar year:
  rejected because it includes periods that may not contribute meaningfully
  to crop development.
=========================================================================================
Decision 09

## Maturation-Window Features

### Decision

Maturation-window rainfall and temperature features are excluded
from Operation Sugar v1.0 and deferred to a future release.

### Rationale

Operation Sugar v1.0 focuses on weather conditions associated with
sugarcane biomass accumulation and cane production. The primary
biological window is therefore the growing season, approximated for
São Paulo as September through April.

Weather conditions during maturation are particularly relevant to
sucrose accumulation, cane quality, ATR, and recoverable sugar.
These outcomes are outside the primary scope of v1.0.

### Planned Extension

A future release may introduce:

- maturation-window total rainfall
- maturation-window average temperature
- harvest-date-based biological windows
- sugar-quality and recoverable-sugar targets

### July 21: Implemented a fully automated ETL pipeline for UNICA biweekly crushing reports.

Pipeline:

PDF
→ Page Detection
→ Table Extraction
→ Data Normalization
→ Validation
→ CSV Export

The pipeline successfully converts UNICA PDF reports into analysis-ready datasets
without manual intervention.