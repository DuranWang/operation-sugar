# Operation Sugar Roadmap

Updated: September 17, 2026

Operation Sugar develops transparent, reproducible commodity research and forecast benchmarks, beginning with Brazilian sugarcane and sugar. Its research agenda connects agricultural supply, production allocation, currency, and supply-chain conditions through four layers.

New methods must be evaluated against relevant public-information benchmarks. Negative results remain part of the research record. A layer is complete when its question has been evaluated credibly, including when no stable incremental predictive relationship is found.

## Status and Priorities

| Status | Scope |
|---|---|
| Completed | v1.0–v1.5.1 data engineering, harvest analytics, and weather–crushing model comparisons; release details below |
| Current research direction | Layer 1: transition from harvest-block crushing volume to annual cane yield; design the staged experiments below |
| Planned within Layer 1 | Expanded weather windows, advanced weather variables, and uncertainty analysis; implementation and results are not claimed here |
| Long-term planned | Layer 2: sugar/ethanol allocation and energy links; Layer 3: BRL/USD; Layer 4: supply chains |

The four layers describe research scope and sequencing, not a completed causal model or a claim of profitable trading performance. Work proceeds from Layer 1 to Layer 4; later layers can interact with earlier ones.

## Four-Layer Research Architecture

| Layer | Research focus | Main questions and intended outputs |
|---|---|---|
| 1. Weather and cane supply | Weather → annual cane yield → cane production | Do weather features add predictive information for annual tonnes of cane per hectare (TCH)? Combine yield with an explicitly defined area measure when estimating production. |
| 2. Sugar production and energy allocation | Cane → sugar output; ethanol/sugar mix; crude oil and sugar prices | How do cane availability, sugar content/recovery, and allocation between sugar and ethanol relate to sugar output? How are crude oil, ethanol economics, and sugar prices connected? |
| 3. Currency | Brazilian real versus US dollar and sugar prices | Does the exchange rate add information beyond agricultural and energy variables? Investigate timing, feedback, and possible shared drivers. |
| 4. Supply chains | Logistics, exports, inventories, and sugar-price interactions | Do supply-chain conditions add information about available supply, delivery timing, and sugar prices beyond the preceding layers? |

Sugar-output definitions and price instruments must be specified separately. Cane tonnage, recoverable sugar, raw sugar, refined white sugar, and futures prices are not interchangeable targets. For any ICE No. 11 study, explicitly identify the raw-sugar contract and pricing convention; a white-sugar study requires its own target specification.

## Layer 1 — Weather, Annual Cane Yield, and Cane Production

### Why Change the Target?

The completed study predicts harvest-block crushing tonnes, summarized more broadly as harvest progress. Across the evaluated specifications, weather models did not consistently improve on the historical harvest-block profile.

A working hypothesis is that block-level crushing combines crop conditions with harvest scheduling and processing activity, making growing-season weather an indirect predictor of this target. The existing negative result does not establish which omitted factors caused the underperformance.

The next study therefore asks whether annual cane yield is a more informative target for weather research. A change of target is a new experiment, not a guarantee of improved performance.

### Target and Information Set

- Define annual cane yield as TCH using a documented geographic scope, season convention, source, denominator, and treatment of revisions.
- Keep cane yield distinct from total cane production. Any production estimate additionally requires a compatible area series and its own uncertainty assessment.
- Define the forecast issue date and data availability before constructing predictors.
- Treat full-year observed weather as an ex-post or late-season information set unless it was available at the forecast issue date.
- Do not compare absolute RMSE across crushing-tonnage and TCH targets as evidence that one task improved; compare each task with its own benchmark.

### Sequential Experiments

| Step | Experiment | Purpose |
|---|---|---|
| 1 | Annual cane-yield baselines, starting with training-sample mean and appropriate trend/persistence alternatives | Establish target-specific reference performance |
| 2 | Original eight-month growing-period rainfall and temperature features → annual cane yield | Evaluate the new target using the original weather information set |
| 3 | Extend to eight growing months plus four maturation months | Test the incremental information in the additional window |
| 4 | Add VPD, soil moisture, and solar radiation separately, then assess combinations | Attribute incremental value to each variable group rather than changing everything simultaneously |

Use matched seasons, outer evaluation folds, model families, and information cutoffs for comparisons within the yield study. Record any sample reductions caused by new data coverage and rerun the comparator on the matched sample.

### Weather Windows and Agricultural Mechanisms

The proposed twelve-month design contains eight growing months plus four maturation months. Exact calendar dates, season alignment, and applicability across locations must be justified before implementation. Validate this working division against crop-cycle and harvest evidence rather than assuming every field follows one common schedule.

The following are candidate mechanisms to substantiate with agronomic literature, not findings of Operation Sugar:

| Variable group | Mechanism hypothesis to investigate | Required design work |
|---|---|---|
| VPD | Atmospheric moisture demand, crop water stress, and associated growth responses | Verify derivation, units, temporal aggregation, and additional information beyond temperature/humidity |
| Soil moisture | Water availability and persistence of deficits beyond rainfall totals | Justify depth/root-zone relevance, source limitations, seasonal anomalies, and lag windows |
| Solar radiation | Radiation availability and biomass accumulation | Distinguish the available radiation product from PAR; justify units and stage-specific exposure measures |
| Maturation-period weather | Later-stage conditions may affect cane yield and sugar accumulation differently | Separate hypotheses about cane mass from hypotheses about sugar content/recovery; connect the latter to Layer 2 |

Before model inclusion, document coverage, measurement consistency, missingness, spatial aggregation, redundancy with existing features, publication availability, and the supporting mechanism. Supporting papers and decisions belong in the literature registry and research-decision log.

### Model Development and Uncertainty

Start with parsimonious models suitable for the effective number of seasons. Retain the completed regularization experiments as methodological evidence.

Planned Bayesian work should address parameter uncertainty, prior sensitivity, and posterior predictive uncertainty in the small-season sample. Compare Bayesian regression with existing regularized references under the same information set. Bayesian implementation is not yet claimed.

The existing partially penalized Ridge estimator already provides an optimization application. More elaborate nonlinear, threshold, stage-specific, spatial, or structurally constrained models require explicit hypotheses and adequate data.

### Completion Criteria

Produce a reproducible target dataset, documented weather windows, benchmark comparisons, uncertainty/limitations, and a record of successful and unsuccessful specifications. A null result is an acceptable outcome. Later layers must propagate uncertainty rather than treat weather-derived cane forecasts as known quantities.

## Layer 2 — Cane-to-Sugar Conversion, Ethanol/Sugar Mix, and Energy

Status: long-term planned, following the Layer 1 study.

### Research Questions

- How does available cane translate into actual sugar production under clearly defined output units and product categories?
- What additional information is needed on sugar content, recovery, processing, and allocation between sugar and ethanol?
- How does the ethanol/sugar production mix vary, and can it be predicted against appropriate historical references?
- What is the relationship between crude oil and sugar prices, and what role might ethanol economics play?

### Proposed Work

1. Build aligned cane, sugar, ethanol, and production-mix records, with explicit conversion definitions and publication dates.
2. Evaluate sugar-content/recovery and allocation components before combining them into a sugar-output estimate.
3. Examine crude-oil, ethanol, and sugar-price relationships using documented instruments and observation frequencies.
4. Separate accounting relationships, empirical correlations, predictive relationships, and causal hypotheses.
5. Compare integrated output estimates with simple allocation/conversion baselines and available public outlooks.

Maturation and sugar-quality research, including relevant ATR/CCS measures, belongs at the boundary of Layers 1 and 2. Measures must be defined and checked for compatibility before use. Energy prices alone are not assumed to determine mill allocation.

## Layer 3 — BRL/USD and Sugar Prices

Status: long-term planned, after establishing the agricultural and allocation framework.

Investigate whether Brazilian currency movements add information about sugar prices beyond the preceding layers. Potential channels to evaluate include export incentives, local-currency revenues/costs, and production or selling decisions; these are hypotheses requiring evidence.

Define the exchange-rate quote convention explicitly. Distinguish contemporaneous association from lagged predictive information, test stability across periods, and account for potential shared drivers and feedback. Any price analysis must specify returns versus levels, forecast horizons, and contract-roll treatment where applicable.

Deliverables: an aligned currency/commodity dataset, benchmarked experiments, sensitivity analysis, and documented interpretation limits.

## Layer 4 — Supply Chains and Sugar-Price Interactions

Status: long-term planned, after the preceding research layers.

Evaluate the interaction between physical supply-chain conditions and sugar prices. Candidate evidence includes port activity, vessel lineups, export shipments, congestion, freight, storage/inventories, and shipment destinations, subject to access and historical coverage.

Distinguish sugar produced, sugar available for export, sugar loaded/shipped, and sugar delivered. Test whether these observations improve supply or price estimates at clearly defined lead times. Investigate both directions of interaction: logistics may affect available supply, while prices and incentives may affect shipment decisions.

Deliverables: documented logistics indicators, point-in-time availability checks, and incremental comparisons with the preceding layers. Public-data feasibility must be established before promising individual indicators.

## Cross-Layer Evaluation and Benchmark Infrastructure

The long-term benchmark infrastructure supports every layer:

- Standardized targets, units, geographic scope, forecast issue dates, and horizons.
- Preserved forecasts and revision histories; observation dates distinguished from publication dates.
- Historical data vintages where available, with limitations recorded where unavailable.
- Target-appropriate public reference forecasts and matched evaluation samples.
- Training-fold preprocessing and nested tuning where needed.
- Chronological expanding/rolling evaluations for historical forecasting claims.
- Explicit uncertainty propagation between layers and ablation tests for added inputs.
- Reporting of negative results, instability, and specification changes.

The completed leave-one-season-out study is a held-out-season evaluation: training can include seasons later than the held-out season. It is not a point-in-time historical trading backtest. Its five aggregation scales describe block sizes, not automatically one-to-five-month forecast lead times.

Later price models must define their own baselines and evaluation protocols. Better supply forecasts do not by themselves establish profitable trading strategies.

## Additional Research Options

ENSO/climate indicators, remote sensing, spatial heterogeneity, production-weighted weather exposure, and interpretable nonlinear models remain optional extensions within the relevant layer. Introduce them only when they address an identified limitation and data/sample size support credible evaluation.

## Completed Research Foundation — Version 1.x

The historical release record below is retained from the repository. Completed findings concern the original targets and validation design, not the planned four-layer system.

## v1.5.1 ✅

### Month-Level Weather Models

#### Research Question

> Does preserving September–April monthly weather structure improve harvest-block crushing prediction beyond the historical harvest profile?

#### Major Additions

- September–April monthly rainfall features
- September–April monthly temperature features
- Rainfall Month-Level OLS
- Rainfall Month-Level Ridge
- Temperature Month-Level OLS
- Temperature Month-Level Ridge
- Joint Month-Level Ridge
- Nested leave-one-season-out alpha selection
- Fold-specific weather standardization
- Partially penalized Ridge regression
- Effective weather degrees-of-freedom diagnostics
- Alpha-grid boundary diagnostics
- Influential-season analysis
- Unified seven-model comparison
- Publication-style reporting figures
- Formal research findings and negative-results documentation

#### Model Comparison

Seven harvest-block models were evaluated across five aggregation horizons:

1. Block-Only OLS
2. Temperature Month-Level Ridge
3. Aggregate Weather OLS
4. Rainfall Month-Level Ridge
5. Joint Month-Level Ridge
6. Temperature Month-Level OLS
7. Rainfall Month-Level OLS

The ranking was identical across all five horizons.

#### Research Findings

- Block-Only OLS achieved the lowest LOSO RMSE at every horizon.
- Temperature Month-Level Ridge was the strongest weather-based model.
- Temperature Ridge remained approximately 0.56% to 1.49% worse than Block-Only.
- Rainfall Ridge remained approximately 1.37% to 5.26% worse than Block-Only.
- Ridge substantially reduced the overfitting of unregularized monthly models.
- Nested LOSO selected the maximum alpha in 75% to 81.25% of outer folds.
- Median effective weather degrees of freedom was approximately zero for every Ridge model and horizon.
- Joint Month-Level Ridge introduced penalty-selection instability rather than stable complementary information.
- Temperature Ridge was especially sensitive to the `21-22` season.
- Joint Ridge was especially sensitive to the `23-24` season.

#### Result

Version 1.5.1 completed the first month-level weather modeling study in Operation Sugar.

Within the available 16-season sample and evaluated linear specifications, aggregate and month-level growing-season weather did not provide stable incremental out-of-sample predictive value for harvest-block crushing beyond the historical harvest-block profile.

The result does not imply that weather is unimportant to sugarcane production. It establishes that the current target, variables, sample, and model structures are insufficient to improve this specific prediction task.

---

---

## v1.5.0 ✅

### Aggregate Weather Baselines

#### Research Question

> Do aggregate growing-season weather variables improve prediction of historical sugarcane crushing?

#### Major Additions

- Weather–harvest modeling datasets
- Harvest-block baseline models
- Complete-season baseline models
- Leave-one-season-out cross-validation
- Fold-specific predictor standardization
- Aggregate weather dashboards

#### Research Findings

At the harvest-block level:

- aggregate rainfall and temperature did not improve out-of-sample prediction;
- historical harvest-block position explained most of the predictable variation;
- Aggregate Weather OLS underperformed Block-Only OLS across all five aggregation horizons.

At the complete-season level:

- aggregate rainfall and temperature did not outperform the training-season historical mean;
- positive complete-sample coefficients did not generalize to held-out seasons.

#### Result

Version 1.5.0 established the statistical benchmarks for future weather models and demonstrated the limitations of compressing the complete growing season into one rainfall total and one average temperature.

---

---

## v1.4.0 ✅

### Harvest Intelligence

#### Research Question

> How does the current harvest compare with historical harvest behavior?

#### Major Additions

- Historical percentile-band benchmarking
- Comparable harvest snapshots
- Harvest pace rankings
- Automated harvest research summaries
- Historical harvest dashboards

#### Result

Version 1.4 established a quantitative historical benchmark for evaluating harvest progress using standardized UNICA reporting periods.

---

---

## v1.3.0 ✅

### Harvest Calendar Analytics

- Historical harvest calendar
- Harvest calendar heatmap
- Harvest timing metrics
- Data-driven harvest-stage inference
- Three-stage seasonal research framework

```text
Growing Stage
      ↓
Maturation Stage
      ↓
Harvest Stage
```

---

---

## v1.2.0 ✅

### Historical Weather Intelligence

- Historical weather archive
- Multi-season benchmark dashboards
- Literature-informed growing-season framework
- Historical weather benchmarking

---

---

## v1.1.0 ✅

### Harvest Infrastructure

- UNICA harvest ETL
- Historical harvest database
- Automated validation framework
- Static analytical dashboards
- Automated testing

---

---

## v1.0.0 ✅

### Research Infrastructure

- NASA POWER weather ETL
- Municipality metadata validation
- Monthly weather aggregation
- Growing-season feature engineering
- Modular project architecture

---

---
