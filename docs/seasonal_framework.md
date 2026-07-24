# Assumptions

The seasonal framework establishes the analytical windows used throughout Operation Sugar.

It should be interpreted as a reproducible research framework rather than an exact biological description of every sugarcane field.

---

# Assumption A1 — Literature-Informed Growing Stage

For municipality-level weather aggregation in São Paulo, the growing stage is approximated as **September through April**, representing the primary period of regrowth (or establishment), tillering, and stalk growth.

This approximation follows the general crop calendar reported by Embrapa and other agronomic literature for south-central Brazil.

The objective of this assumption is not to define the exact biological development of every sugarcane field, but rather to establish a consistent and reproducible analytical window for weather-based feature engineering.

Consequently, weather observations are assigned to harvest seasons as follows:

- September through December observations are assigned to the following harvest year.
- January through April observations are assigned to the current harvest year.

This assumption supports biomass-oriented weather analysis throughout Version 1.x.

---

# Assumption A2 — Planned Maturation Stage

Operation Sugar distinguishes the maturation stage from the growing stage.

The maturation stage represents the period during which vegetative growth slows and sucrose accumulation becomes the dominant biological process.

Unlike the growing stage, maturation is expected to be analyzed using literature-supported pre-harvest weather windows rather than fixed calendar months.

The exact maturation window has **not yet been formally implemented** in Version 1.3 and remains part of future development.

---

# Assumption A3 — Data-Driven Harvest Stage

The harvest stage is inferred directly from historical UNICA crushing observations.

Harvest timing is defined empirically using cumulative seasonal crushing rather than predefined crop calendars.

Detailed methodology is documented in:

- seasonal_framework.md
- research_design_decisions.md

---

# Assumption A4 — Seasonal Interpretation

Operation Sugar distinguishes three analytical stages:

- Growing Stage
- Maturation Stage
- Harvest Stage

These stages represent different biological and operational processes.

They should **not** be interpreted as universally fixed or perfectly non-overlapping calendar periods.

Different planting dates, ratoon cycles, regional climates, and harvesting schedules may cause these stages to overlap across municipalities and production areas.

The purpose of these seasonal definitions is to provide reproducible analytical frameworks rather than exact biological boundaries for every sugarcane field.