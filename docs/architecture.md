# Operation Sugar Architecture

Operation Sugar is a modular research-engineering platform for public-data agricultural and commodity research.

The current architecture is centered on **annual São Paulo sugarcane yield**, not the earlier harvest-progress target.

---

## Current Layer-1 Research Architecture

```text
                         IBGE
          annual production + harvested area
                           │
                           ▼
                 Municipality yield
                           │
                           ▼
              Municipality detrending
             P50=10 primary / P50=12 robustness
                           │
                           ▼
                Municipality residuals
                           │
                           ▼
          Annual ERA5-grid yield anomalies
        observed harvested-area weights primary
                           │
                           ├──────────────────────┐
                           │                      │
                           ▼                      ▼
                    NASA POWER            Open-Meteo / ERA5
                    basic weather          advanced weather
                           │                      │
                           └──────────┬───────────┘
                                      ▼
                           Monthly weather alignment
                                      │
                                      ▼
                         EXP-03 relationship analysis
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                  ▼
              robustness       spatial heterogeneity   redundancy
                    │                 │                  │
                    └─────────────────┴──────────────────┘
                                      ▼
                            downstream candidates
                                      │
                                      ▼
                       conditional / continuous tests
                                      │
                                      ▼
                       later time-aware prediction
```

---

## Agricultural Outcome Pipeline

### Source

IBGE municipality agricultural statistics.

### Transformation

1. validate production and harvested-area source semantics;
2. calculate valid municipality annual yield;
3. enforce minimum historical support;
4. fit municipality-specific long-run trend;
5. retain residuals only for observed yield years;
6. map eligible municipalities to ERA5 0.5° grids;
7. aggregate residuals using annual harvested-area weights.

Primary historical detrending:

- P50=10.

Primary robustness:

- P50=12.

Primary spatial composition:

- actual annual harvested-area weights.

Spatial robustness:

- common-support fixed composition.

---

## Weather Pipeline

### NASA POWER

Provides the basic monthly weather layer, including rainfall, temperature, and relative humidity.

### Open-Meteo / ERA5

Provides advanced weather states including:

- VPD;
- solar radiation;
- depth-resolved soil moisture.

The combined monthly-weather ETL preserves source-specific validation before downstream alignment.

The all-variable EXP-03 history begins in January 1981.

---

## Static Soil Explanatory Layer

SoilGrids is processed separately from the dynamic weather pipeline.

Current use:

> explanatory context for spatial response regimes only.

Retained native depth structure extends to 200 cm.

No 200–255 cm static-soil layer is fabricated to match the deepest dynamic soil-moisture variable.

Static soil is not part of the current predictive weather candidate universe.

---

## EXP-03 Analysis Layer

Formal modules:

```text
src/analysis/exp03_yield_stratified_monthly_weather.py
src/analysis/exp03_checkpoint2_robustness.py
src/analysis/exp03_checkpoint2b_spatial_heterogeneity.py
src/analysis/exp03_harvest_profile_stability_audit.py
src/analysis/exp03_march_soil_moisture_depth.py
src/analysis/exp03_soil_regime_synthesis.py
src/analysis/exp03_redundancy_synthesis.py
```

Responsibilities:

- temporal alignment;
- yield stratification;
- continuous robustness;
- grid-specific spatial diagnostics;
- March soil-moisture depth analysis;
- bounded SoilGrids explanatory synthesis;
- representation and adjacent-month redundancy synthesis.

Curated outputs are stored under:

```text
outputs/research/exp_03/
```

Large reconstructable intermediate tables are excluded from version control.

---

## Current Downstream Candidate Layer

Step 5 reduces clear representation duplication while protecting unresolved conditional information.

Canonical families:

- rainfall;
- temperature;
- relative humidity;
- mean VPD;
- upper soil moisture 0–7 cm;
- deep soil moisture 28–100 cm;
- deep soil moisture 100–255 cm;
- mean-daily solar radiation.

Only two temporal summaries are promoted as multi-month candidates:

- Dec–Jan RH;
- Dec–Jan 28–100 cm soil moisture.

The resulting universe contains 38 candidate representations.

This is a research candidate layer, not a production model schema.

---

## Conditional-Information Layer

Immediate next experiment:

- EXP-05 temperature ↔ VPD.

Separately justified later hydrological questions:

- rainfall ↔ upper moisture;
- rainfall/history ↔ deep moisture;
- upper ↔ deep moisture.

The architecture intentionally keeps predictor correlation and incremental yield information as separate analytical problems.

---

## Forecasting Architecture

Historical descriptive work may use complete observed seasons.

Formal forecasting requires a stricter architecture:

```text
forecast origin
     │
     ▼
training-period data only
     │
     ├── detrending
     ├── weighting / forecast-safe footprint treatment
     ├── feature construction
     ├── feature selection
     ├── scaling
     └── tuning
     │
     ▼
held-out future period
```

No estimated full-history transformation should leak into a historical forecast backtest.

---

## Legacy Harvest / UNICA Pipeline

UNICA harvest and crushing workflows remain in the repository as historical research infrastructure.

They support:

- historical harvest timing;
- crushing benchmarks;
- prior harvest-progress studies.

They no longer define the primary Layer-1 target.

The earlier harvest-profile benchmark remains a retained negative-result reference.

---

## Reporting Architecture

```text
experiment code
     │
     ▼
machine-readable summaries
     │
     ▼
curated reports / selected figures
     │
     ▼
README / roadmap / experiment registry
```

Repository policy:

- commit source code and tests;
- commit concise curated research outputs;
- ignore large reconstructable intermediate datasets;
- preserve negative results;
- keep research decisions separate from execution logs.

---

## Validation

Focused v1.7.0 research suite:

```bash
python -m pytest src/tests/analysis src/tests/etl/weather src/tests/etl/soil -q
```

Checkpoint result:

> **137 passed**

---

## Design Principles

- **Modular ETL:** source-specific ingestion and validation remain separate.
- **Validation first:** downstream analysis uses explicitly validated support.
- **Spatial alignment:** weather and yield share the ERA5 grid before relationship analysis.
- **Research traceability:** formal conclusions map to scripts, tests, and curated outputs.
- **Reproducibility:** generated intermediate data are rebuildable from the pipeline.
- **Time-aware prediction:** forecast claims require historical information sets and training-only transformations.
- **Interpretation discipline:** association, predictive value, and causality remain distinct.

---

## Related Documentation

- [`README.md`](../README.md) — public project overview
- [`ROADMAP.md`](../ROADMAP.md) — current research sequence
- [`research_decisions.md`](../research_decisions.md) — adopted methodological choices
- [`statistical_experiments.md`](../statistical_experiments.md) — experiment methods and findings
- [`modeling_framework.md`](modeling_framework.md) — modeling and evaluation framework
- [`analytical_framework.md`](analytical_framework.md) — analytical-variable construction
