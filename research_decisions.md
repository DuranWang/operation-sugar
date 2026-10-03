# Research Decisions

This document records the major analytical and statistical decisions that define the current Operation Sugar research architecture.

It answers one question:

> **What did the project choose, and why?**

Detailed experiment design, formulas, diagnostics, and numerical results are documented in `statistical_experiments.md`.

Research-engineering problems and implementation lessons are documented in `research_engineering_challenges.md`.

---

# Decision Principles

Operation Sugar follows a research-first workflow:

> Research questions determine statistical design, and statistical design determines engineering implementation.

Each decision below records the adopted choice, the rationale, and important alternatives where relevant.

---

# Section 1 — Research Architecture

## Decision 01 — Agricultural Yield Is the Primary v1.x Research Target

### Decision

Use annual sugarcane yield in tonnes per hectare as the primary agricultural target.

### Reason

Harvest progress and crushing volumes contain substantial operational variation from mill scheduling, logistics, industrial capacity, and harvest timing.

Annual agricultural yield provides a cleaner target for studying weather-driven crop productivity.

### Alternatives Considered

- biweekly crushing volume;
- harvest progress;
- total sugarcane production;
- sugar production.

### Scope

Earlier harvest-progress models remain part of the project history but no longer define the main research line.

---

## Decision 02 — Major Research Choices Must Remain Traceable

### Decision

Major methodological choices should be traceable to source data, experiment outputs, literature, or explicit statistical reasoning.

### Reason

Operation Sugar is intended to function as a reproducible research system rather than a collection of isolated models.

---

# Section 2 — Source Data and Support

## Decision 03 — Preserve IBGE Source Semantics

### Decision

Preserve the distinction between reported numeric values, explicit zeros, and unavailable observations in the IBGE source data.

Unavailable observations must not be converted to zero.

### Reason

Collapsing these categories can create false production, false harvested-area support, and invalid yield observations.

---

## Decision 04 — Define Yield Only from Valid Production and Harvested Area

### Decision

Municipality-year yield is defined only when the underlying production and harvested-area values produce a valid agricultural observation.

Undefined cases such as zero production divided by zero harvested area remain missing.

### Reason

An undefined observation is not equivalent to a true yield of zero.

---

# Section 3 — Municipality-Level Detrending

## Decision 05 — Detrend Before Spatial Aggregation

### Decision

Remove long-run yield trends separately for each municipality before aggregating yield anomalies to weather grids.

### Reason

Long-run productivity growth is not spatially uniform.

Municipalities differ in production history, technology adoption, cultivars, management, and structural development.

Detrending only after aggregation would mix those differences with short-run yield variation.

### Alternatives Considered

- statewide detrending;
- grid-level detrending;
- no detrending;
- one common linear trend.

---

## Decision 06 — Use a Smooth Long-Run Trend Rather Than Hard Structural Breaks

### Decision

Estimate municipality trends with a second-difference penalized smoother.

### Reason

The smoother allows productivity trends to evolve gradually without imposing arbitrary statewide break dates.

The available evidence did not justify treating deregulation, geographic expansion, or mechanization as one common yield break across São Paulo.

### Alternatives Considered

- linear trend;
- manually specified structural breaks;
- piecewise trends;
- short-window rolling means.

---

## Decision 07 — Use P50 = 10 as the Primary Historical Detrending Specification

### Decision

Use `P50 = 10` as the primary historical detrending specification.

### Reason

It provides a conservative compromise between allowing long-run productivity change and preserving shorter-horizon variation that may contain weather signal.

Nearby conservative specifications produce very similar adjusted-yield signals, supporting the stability of this choice.

### Alternatives Considered

- Linear — rigid benchmark;
- `P50 = 6` — aggressive sensitivity;
- `P50 = 12` — primary conservative robustness check.

### Scope

Detailed parameterization and cross-specification results are documented in `statistical_experiments.md`.

---

# Section 4 — Municipality Eligibility and Missing Histories

## Decision 08 — Require Sufficient History and Calendar Span

### Decision

Retain municipalities with:

- at least 15 valid yield observations;
- at least a 20-year calendar span.

### Reason

Trend estimation requires both enough observed yield values and enough time span to distinguish long-run movement from short-run variation.

---

## Decision 09 — Do Not Apply a Hard Internal-Gap Exclusion

### Decision

Treat internal missing-yield gaps as diagnostics rather than as automatic exclusion criteria.

### Reason

Hard gap restrictions remove meaningful production coverage while providing limited improvement in detrending stability.

### Alternatives Considered

- maximum five-year internal gap;
- maximum ten-year internal gap;
- complete-history requirement.

---

## Decision 10 — Do Not Invent Residuals for Missing Yield Years

### Decision

Allow the latent trend to remain defined across internal missing periods, but calculate yield residuals only where valid yield was actually observed.

### Reason

A continuous estimated trend does not imply that an agricultural observation exists in a missing year.

---

## Decision 11 — Treat Endpoint and Gap Proximity as Sensitivity Flags

### Decision

Retain endpoint proximity and internal-gap proximity as diagnostic information rather than primary exclusion rules.

### Reason

Trend estimates are less constrained near series boundaries and around sparse histories, but this does not imply that those observations are automatically invalid.

---

# Section 5 — Spatial Alignment and Weighting

## Decision 12 — Align Adjusted Yield to ERA5 0.5° Grids

### Decision

Map municipality-level adjusted yield to the ERA5 0.5° grid structure used by the weather data.

### Reason

Subsequent weather–yield analysis requires weather exposure and agricultural outcomes to share a common spatial unit.

---

## Decision 13 — Use Annual Harvested-Area Weights for the Primary Grid-Level Yield Anomaly

### Decision

Aggregate municipality yield residuals within each ERA5 grid using contemporaneous harvested-area weights.

### Reason

Municipalities contributing more sugarcane area should contribute more strongly to the grid-level agricultural anomaly.

Annual weights also preserve real historical changes in production geography.

### Alternatives Considered

- equal municipality weights;
- fixed harvested-area weights;
- statewide aggregation before weather alignment.

---

## Decision 14 — Evaluate Spatial Composition on Matched Support

### Decision

Compare actual annual composition with a fixed-composition counterfactual using the same municipality-year residual support.

### Reason

Differences between the two series should reflect weighting changes rather than missing-data differences.

---

## Decision 15 — Build Fixed Composition from Common Historical Support

### Decision

Construct fixed reference weights from years in which the full municipality set within a grid has valid harvested-area support.

When a grid-year contains only a subset of those municipalities with valid residuals, restrict and renormalize the approved reference vector over that same matched support.

### Reason

A previous candidate method averaged municipality shares over different historical windows and produced incoherent reference compositions.

Common support ensures that the fixed-weight counterfactual represents a valid grid composition.

### Rejected Alternative

Municipality-specific historical-average shares calculated over differential observation histories.

---

## Decision 16 — Use Actual Composition as Primary and Fixed Composition as Robustness

### Decision

Use annually changing harvested-area composition for the primary historical adjusted-yield series.

Use the common-support fixed-composition series as a robustness counterfactual.

### Reason

EXP-02B showed that changing within-grid production composition can matter, but the effect is generally limited enough that observed annual composition remains the more faithful primary historical representation.

Detailed diagnostics and effect sizes are documented in `statistical_experiments.md`.

---

# Section 6 — Final Historical Adjusted-Yield Representation

## Decision 17 — Primary Historical Adjusted-Yield Representation

### Decision

Subsequent historical weather–yield analysis will use:

> **P50 = 10 detrended municipality yield residuals, aggregated annually to ERA5 0.5° grids using observed harvested-area weights.**

### Reason

This representation removes municipality-specific long-run productivity change while preserving short-run yield variation and aligning the result with the weather grid.

### Primary Robustness Checks

- P50 = 12 detrending;
- common-support fixed composition;
- endpoint sensitivity;
- internal-gap proximity sensitivity.

---

## Decision 18 — Forecasting Transformations Must Be Reconstructed Training-Only

### Decision

Any detrending, weighting, scaling, feature selection, or other estimated transformation used in future out-of-sample forecasting must be reconstructed using the training information available at each forecast origin.

### Reason

The current EXP-02 transformations define a historical research representation.

Using full-history transformations inside a backtest would leak future information.

---

# Section 7 — Weather Research Decisions from EXP-01

## Decision 19 — Preserve Month-Level Weather Structure

### Decision

Evaluate weather relationships by month rather than relying only on pooled correlations.

### Reason

EXP-01 showed that relationships among weather variables can vary materially across the annual cycle.

Pooling months can obscure or reverse temporally specific relationships.

---

## Decision 20 — Separate Support Effects from Production-Weighting Effects

### Decision

Treat observational support and harvested-area weighting as distinct analytical issues.

### Reason

EXP-01 showed that changing weights and changing support can affect estimated weather relationships differently.

The two effects should therefore be diagnosed separately.

---

# Section 8 — Legacy Harvest-Progress Decisions

The following decisions belong to the earlier harvest-progress modeling architecture.

They are retained for historical continuity but do not define the current annual-yield research line.

## Legacy Decision A — Historical Harvest Profile Benchmark

Historical harvest-block profiles were used as the primary benchmark for weather-based crushing-volume models because recurring harvest timing explained substantial predictable variation.

## Legacy Decision B — Nested Leave-One-Season-Out Ridge Validation

Earlier month-level harvest-progress models used nested Leave-One-Season-Out validation to select Ridge regularization strength without tuning on the final held-out season.

## Legacy Decision C — Exclusion of Joint Month-Level OLS

Unregularized joint month-level rainfall-temperature OLS was excluded because the training folds did not provide enough identifiable rank for the full predictor set.

Ridge regularization was used instead.

---

# Summary

Operation Sugar's current historical agricultural-yield architecture is based on five core choices:

1. annual agricultural yield is the primary v1.x target;
2. long-run productivity trends are removed at the municipality level;
3. `P50 = 10` is the primary historical detrending specification;
4. adjusted yield is aligned to ERA5 grids using annual harvested-area weights;
5. fixed-composition and nearby detrending specifications are retained as robustness checks.

The resulting historical representation is:

> **P50 = 10 detrended municipality yield residuals aggregated annually to ERA5 0.5° grids using observed harvested-area weights.**

EXP-02 establishes this representation.

Subsequent experiments use it to study weather–yield relationships.
