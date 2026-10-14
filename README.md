# Operation Sugar

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Version](https://img.shields.io/badge/Version-1.7.1-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

**Independent quantitative research into Brazilian sugarcane and sugar markets, built on public data, explicit benchmarks, and reproducible experiments.**

Operation Sugar currently studies **annual agricultural sugarcane yield in São Paulo, Brazil**, measured in tonnes of cane per hectare. The active Layer-1 program combines municipality agricultural statistics, NASA POWER weather, Open-Meteo / ERA5 weather, and reproducible statistical experiments.

The project is deliberately benchmark-driven: new variables and model complexity are useful only when they add interpretable, reproducible information beyond simpler reference specifications.

## Research Snapshot

| Dimension | Current state |
|---|---|
| Primary target | Annual São Paulo sugarcane yield (t/ha) |
| Annual agricultural history | 1974–2025 |
| Municipality universe | 642 São Paulo municipalities |
| Detrending-eligible municipalities | 511 |
| Weather grouping | 0.5° analysis lattice; point-series ERA5 exposures |
| Grid support | 78 grids; 76 qualify for current grid-specific correlation summaries |
| Complete all-variable yield years | 1982–2025 |
| Main late-weather window | Dec_(t-1) → Apr_t |
| Weather sources | NASA POWER + Open-Meteo / ERA5 |
| Agricultural source | IBGE municipal agricultural statistics |
| Completed experiments | EXP-01, EXP-02, EXP-03, EXP-05, EXP-05B; EXP-04 reported complete and results reviewed |
| Immediate next step | **EXP-06 — representation and joint-description design** |
| Historical windows | Primary: May_(t-1)–Apr_t (12 months); extended: Jan_(t-1)–Apr_t (16 months) |
| v1.7.1 validation checkpoint (prior release) | **142 analysis tests; 329 full-suite tests passing (3 warnings)** |
| Current release checkpoint | **v1.7.1 — EXP-05/05B conditional weather–yield research** |

## Four-Layer Research Framework

```mermaid
flowchart LR
    A["Layer 1<br/>Agricultural Supply<br/>Weather → Cane Yield → Cane Production"]
    B["Layer 2<br/>Sugar Production & Energy<br/>Cane → Sugar / Ethanol Allocation"]
    C["Layer 3<br/>Currency<br/>BRL/USD → Sugar Market"]
    D["Layer 4<br/>Supply Chains<br/>Ports / Exports / Inventories"]

    A --> B --> C --> D
```

| Layer | Research focus | Status |
|---|---|---|
| **1. Agricultural supply** | Weather → annual cane yield → cane production | **Active** |
| **2. Sugar production and energy** | Cane → sugar output; recovery / ATR; ethanol–sugar allocation | Planned |
| **3. Currency** | BRL/USD and sugar prices | Planned |
| **4. Supply chains** | Ports, exports, transport, inventories, and physical availability | Planned |

The layers define a research sequence, not an established causal chain. Cane yield, cane production, sugar output, exports, and sugar prices are distinct targets.

---

## Current Layer-1 Pipeline

```text
IBGE annual municipality production + harvested area
                    │
                    ▼
         Municipality annual yield
                    │
                    ▼
     Municipality-first detrending
       P50=10 primary; P50=12 robustness
                    │
                    ▼
      Municipality yield residuals
                    │
                    ▼
ERA5-grid aggregation using annual harvested-area weights
                    │
                    ├──────────────┐
                    ▼              ▼
NASA POWER monthly weather   Open-Meteo / ERA5
                    │              │
                    └──────┬───────┘
                           ▼
                Aligned grid-year weather
                           │
                           ▼
                EXP-03 relationship discovery
                           │
                           ▼
          redundancy / conditional-information gates
                           │
                           ▼
            later continuous and predictive tests
```

Static SoilGrids properties are currently used only as **explanatory context** for spatial heterogeneity. They are not approved predictive inputs.

---

## Completed Research

### EXP-01 — Weather Feature Structure

EXP-01 characterized weather-to-weather overlap and temporal persistence before using yield.

Main conclusions:

- weather relationships are strongly calendar-month dependent;
- pooled all-month correlations can obscure or reverse month-specific structure;
- soil moisture is much more persistent than rainfall;
- temperature and VPD overlap substantially but correlation alone does not prove predictive redundancy;
- harvested-area weighting changes estimated weather relationships more than matched-support exclusion in the core comparisons.

Curated outputs: [`outputs/research/exp_01/`](outputs/research/exp_01/)

### EXP-02 — Yield Detrending and Spatial Composition

EXP-02 established the historical adjusted-yield target.

The approved primary representation is:

> **municipality yield → municipality-specific P50=10 detrending → residual → ERA5-grid aggregation with contemporaneous harvested-area weights**

Primary robustness checks:

- P50=12 detrending;
- common-support fixed composition;
- endpoint proximity;
- internal-gap proximity.

P50=10 and P50=12 residuals are highly similar. Changing within-grid production composition usually has a modest effect, but some grid-years show material differences.

Curated outputs: [`outputs/research/exp_02/`](outputs/research/exp_02/)

### EXP-03 — Yield-Stratified Weather Analysis

EXP-03 directly linked weather to the adjusted annual yield outcome.

Key findings:

1. **The clearest late-weather structure is Dec_(t-1) → Apr_t.**
2. **Dec–Jan is the strongest and most spatially coherent part of that window.**
3. **Feb–Mar is materially more heterogeneous across grids.**
4. **April partially reconverges spatially.**
5. Relative humidity and deeper soil moisture are among the most spatially stable late-window signals.
6. Rainfall, temperature, VPD, upper-soil moisture, and solar radiation remain informative but more heterogeneous.
7. March soil-moisture response changes materially with depth:
   - positive surface / positive deep: 42 grids;
   - negative surface / positive deep: 19 grids;
   - negative surface / negative deep: 13 grids;
   - positive surface / negative deep: 2 grids.
8. SoilGrids differences between March depth regimes are suggestive but strongly entangled with latitude and production-support structure; static soil remains explanatory-only.

Selected EXP-03 figure:

![EXP-03 directional consistency](outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2/figures/directional_consistency_heatmap.png)

Curated outputs: [`outputs/research/exp_03/`](outputs/research/exp_03/)

### EXP-05 — Conditional Temperature–VPD Yield Response

EXP-05 tested whether monthly mean VPD and temperature retain conditional yield information after accounting for the other atmospheric variable. Analyses covered 16 exploratory month-slots; the historical **primary 12-month window remains May_(t-1)–Apr_t**, with Jan–Apr_(t-1) as extended robustness.

- Aug–Nov_(t-1) median within-grid partial correlations `r(Y,VPD|T)` were approximately −0.104, −0.099, −0.081, and −0.105, respectively.
- These are modest historical associations, heterogeneous across grids; they are not evidence of causal effects or out-of-sample predictive improvement.
- Neither temperature nor VPD meets an approved feature-deletion standard. Both remain in the frozen downstream candidate universe.

Curated outputs: [`outputs/research/exp_05/`](outputs/research/exp_05/)

### EXP-05B — Moisture-Conditioned Temperature–VPD Yield Response

EXP-05B distinguished (1) additive conditional overlap with antecedent moisture from (2) modification of the temperature/VPD–yield slopes by antecedent moisture. The primary moisture proxy was the preceding three-month average of the nominal Open-Meteo 28–100 cm soil-moisture layer; preceding-month moisture, a deeper layer, and preceding three-month rainfall were bounded comparators.

- Conditioning on antecedent soil moisture did not remove the modest Aug–Nov negative VPD partial-correlation pattern.
- The Aug–Nov primary VPD dry-minus-wet slope contrasts were **+0.348, −0.300, +0.321, and +0.113 t/ha per within-grid VPD SD**, respectively. Every 3-year- and 5-year-block 95% pointwise interval included zero.
- Interaction directions were mixed across months and moisture definitions; no consistent interval-supported modification was established. This is **not** a practical-equivalence or causal finding.
- Fixed-grid synchronized bootstrap retained the original 76 eligible grids; numerical checks and paired inference completed. Rainfall showed more additive pooled in-sample information in some focal months, but no independently validated prediction advantage.
- No soil layer, rainfall variable, temperature, or VPD feature was dropped. Complex interactions are not required as default downstream features.

Curated outputs: [`outputs/research/exp_05b/`](outputs/research/exp_05b/)

---

### EXP-04 — Continuous Weather–Yield Response Characterization

**Completed as reported; supplied result tables reviewed on 2026-10-14.** The frozen 38 candidates were fit separately against the primary actual-composition P50=10 grid residual. There are 2,888 linear fits (76 grids per candidate) and 2,736 restricted quadratic fits (72 grids per candidate), with candidate-specific paired years rather than a complete-window exclusion.

Rainfall and soil moisture generally have positive slope point estimates; temperature and VPD generally have negative ones. Many individual-grid block intervals cross zero. February rainfall is the only pooled PQ candidate whose curvature intervals exclude zero under both block schemes; this is exploratory evidence within a prespecified quadratic family, not an independently validated discovery. Target sensitivities retain most slope signs. Linear LOYO was not present in the supplied review files.

These marginal models do not quantify joint seasonal explanatory power or forecast gains. No feature is added or removed on a significance rule. See the [reviewed results](outputs/research/exp_04/EXP_04_reviewed_results.md) for tables, sample rules, uncertainty, and the outstanding implementation/full-output synchronization gap.

## EXP-03 Redundancy Closure

Three representation duplicates were collapsed for downstream work:

| Concept | Canonical representation | Archived robustness representation |
|---|---|---|
| Solar | Mean-daily solar radiation | Monthly total solar |
| VPD | Mean VPD | Daily-max VPD |
| Upper soil moisture | 0–7 cm | 7–28 cm |

Only two multi-month summaries were promoted as candidate representations:

- **Dec–Jan relative humidity**
- **Dec–Jan 28–100 cm soil moisture**

No Jan–Feb, Feb–Mar, or Mar–Apr aggregate was promoted.

The resulting downstream universe contains **38 candidate representations**.

Protected feature-information distinctions (EXP-05 tested T/VPD without authorizing predictive feature deletion):

- temperature ↔ VPD;
- rainfall ↔ upper-soil moisture;
- rainfall/history ↔ deep-soil moisture;
- upper ↔ deep-soil moisture.

See the reproducible Step-5 report:

[`outputs/research/exp_03/redundancy/EXP_03_redundancy_synthesis_report.md`](outputs/research/exp_03/redundancy/EXP_03_redundancy_synthesis_report.md)

---

## Current Research Sequence

The experiment IDs are historical identifiers; execution order may differ.

```text
EXP-01  Weather feature structure                     COMPLETE
EXP-02  Yield detrending / spatial composition        COMPLETE
EXP-03  Weather–yield discovery / heterogeneity       COMPLETE
EXP-05  Temperature–VPD conditional information      COMPLETE
EXP-05B Moisture-conditioned T/VPD response           COMPLETE
EXP-04  Continuous weather–yield characterization      COMPLETE / RESULTS REVIEWED
         Hydrological conditional follow-up            UNNUMBERED / LATER
EXP-06  Time/stage weather representations            NEXT DESIGN
EXP-07  Incremental out-of-sample predictive value    PROPOSED
EXP-08  Spatial response heterogeneity                 LATER / CONDITIONAL
```

Dynamic Bayesian updating is intentionally deferred to a later **Weather 2.0** research phase rather than kept in the current v1.x experiment sequence.

See [`ROADMAP.md`](ROADMAP.md) for the current sequence and stop boundaries.

---

## Reproducibility

### Setup

```bash
git clone https://github.com/DuranWang/operation-sugar.git
cd operation-sugar
python -m pip install -r requirements.txt
```

The project targets Python 3.12. Large source archives and generated processed datasets are intentionally excluded from version control; curated research outputs are retained under `outputs/research/`.

### Current research analysis modules

```text
src/analysis/exp03_yield_stratified_monthly_weather.py
src/analysis/exp03_checkpoint2_robustness.py
src/analysis/exp03_checkpoint2b_spatial_heterogeneity.py
src/analysis/exp03_harvest_profile_stability_audit.py
src/analysis/exp03_march_soil_moisture_depth.py
src/analysis/exp03_soil_regime_synthesis.py
src/analysis/exp03_redundancy_synthesis.py
```

Added conditional-research modules:

```text
src/analysis/exp05_conditional_temperature_vpd.py
src/analysis/exp05b_fixed_grid_bootstrap.py
src/analysis/exp05b_moisture_conditioning.py
src/analysis/exp05b_summarize.py
```

### Focused test suite

```bash
python -m pytest src/tests/analysis src/tests/etl/weather src/tests/etl/soil -q
```

At the v1.7.1 checkpoint, `python -m pytest src/tests/analysis -q` passes **142 tests**, and `python -m pytest -q` passes **329 tests with 3 warnings** on the release-preparation machine.

---

## Prior Negative Benchmark

Before the annual-yield program, OS tested whether September–April rainfall and temperature improved **harvest-block crushing-volume** prediction beyond a historical harvest-profile benchmark.

They did not: the historical harvest-profile benchmark had the lowest held-out-season RMSE across the evaluated scales.

That negative result helped motivate the shift from operational crushing-volume prediction toward the cleaner agricultural-yield target.

See:

- [`month_level_model_findings.md`](month_level_model_findings.md)
- [`negative_results.md`](negative_results.md)

---

## Methodology Principles

- **Benchmark discipline:** compare new information against a relevant reference.
- **Matched samples:** separate support changes from modeling effects.
- **Temporal structure:** preserve month-specific relationships when pooling would be misleading.
- **Specification robustness:** retain reasonable alternative target definitions when conclusions depend on them.
- **Time-aware evaluation:** predictive claims require chronological validation and forecast-date information sets.
- **Training-only preprocessing:** estimated transformations and feature selection belong inside the training sample.
- **Negative results:** failed specifications remain part of the research record.
- **Interpretation discipline:** association, prediction, and causality are separate claims.

---

## Documentation

| Document | Purpose |
|---|---|
| [`ROADMAP.md`](ROADMAP.md) | Current experiment sequencing and research priorities |
| [`statistical_experiments.md`](statistical_experiments.md) | Experiment questions, methods, and findings |
| [`research_decisions.md`](research_decisions.md) | Major methodological choices and rationale |
| [`docs/architecture.md`](docs/architecture.md) | Current software and research-data architecture |
| [`docs/modeling_framework.md`](docs/modeling_framework.md) | Modeling and evaluation framework |
| [`docs/analytical_framework.md`](docs/analytical_framework.md) | Analytical-variable construction |
| [`docs/seasonal_framework.md`](docs/seasonal_framework.md) | Seasonal definitions and historical context |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

## Contributing and Contact

Suggestions, bug reports, and research collaborations are welcome. Contributions should prioritize explicit assumptions, reproducibility, appropriate benchmarks, and demonstrable incremental value.

Contact: [Duran Wang on LinkedIn](https://www.linkedin.com/in/duranwang/)

Released under the [MIT License](LICENSE).
