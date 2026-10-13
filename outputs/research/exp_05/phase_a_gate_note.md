# EXP-05 Phase A gate — February_t

Status: **PASS**.

- Frozen target lineage reconstructs all three grid outcomes with maximum absolute error 1.24e-14 t/ha; 511 municipalities map uniquely to 78 grids. Within-year grid target values are not replicated statewide. Shared yearly shocks and weather-source groups remain possible spatial dependence.
- February_t is month slot -2, yield-year February, from the existing 16-slot alignment. No 16-month completeness filter is applied.
- 3336 paired primary grid-years; 76 grids have N≥20, 72 have N≥30, 2 have N<15. All-three-target paired rows: 3336.
- Partial-correlation/partial-R² identity maximum error 1.04e-15; all 144 allowed per-grid restricted nonlinear fits and the pooled grid-intercept diagnostic are estimable. Synchronized year bootstraps produced estimable spatial medians and pooled nonlinear refits; failed-grid counts remain in the outputs.
- Protocol frozen for Phase B: same per-grid-slot Y/T/VPD complete-case sample; 15/20/30-year tiers; two-sided linear and rank partials; HC3; average-rank empirical thirds; restricted quadratic controls; pooled common-slope grid-intercept L/Q/I; shared-year target comparison; synchronized i.i.d./3-year/5-year year draws (200 replicates, seed 20261010); no year fixed effects or additional covariates.
- Known limitations: weather begins in 1981; some target grid-years are invalid; adjacent grid weather and shared annual shocks can correlate. No smallest-important-effect margin is approved, so potential redundancy is not assigned. Pooled nonlinear fits are diagnostics, not grid-universal effects.

No material methodological ambiguity was found in the pilot; proceed to Phase B under the frozen rules.
