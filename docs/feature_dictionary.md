# Feature Dictionary

This document defines the analytical variables currently implemented in Operation Sugar.

Each feature includes its definition, measurement unit, and analytical purpose.

Analytical methodology is documented in **analytical_framework.md**.

Future variables are documented in **ROADMAP.md**.

---

# Weather Features

## Baseline Weather Features

These variables summarize historical weather conditions over a specified analytical period.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `total_rainfall` | Sum of daily precipitation | mm | Measures total water supply |
| `average_temperature` | Mean daily temperature | °C | Measures general thermal conditions |
| `average_humidity` | Mean daily relative humidity | % | Measures atmospheric moisture |
| `rainy_days` | Number of days with precipitation greater than 1 mm | days | Measures rainfall frequency |
| `weather_observation_days` | Number of available daily observations | days | Data-quality indicator |

---

## Rainfall Distribution Features

These variables describe how rainfall is distributed through time rather than simply its total amount.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `dry_days` | Number of days with precipitation at or below 1 mm | days | Measures the frequency of dry conditions |
| `max_consecutive_dry_days` | Longest sequence of days with precipitation at or below 1 mm | days | Measures the persistence of dry conditions |

---

## Growing-Season Aggregate Features

These variables summarize weather over the complete September–April growing season.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `growing_season_total_rainfall` | Total rainfall accumulated during the growing season | mm | Aggregate water supply for statistical modeling |
| `growing_season_average_temperature` | Mean temperature during the growing season | °C | Aggregate thermal conditions for statistical modeling |

---

## Month-Level Rainfall Features

These variables preserve the temporal distribution of rainfall throughout the growing season.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `rainfall_sep` | Total September rainfall | mm | Month-level rainfall representation |
| `rainfall_oct` | Total October rainfall | mm | Month-level rainfall representation |
| `rainfall_nov` | Total November rainfall | mm | Month-level rainfall representation |
| `rainfall_dec` | Total December rainfall | mm | Month-level rainfall representation |
| `rainfall_jan` | Total January rainfall | mm | Month-level rainfall representation |
| `rainfall_feb` | Total February rainfall | mm | Month-level rainfall representation |
| `rainfall_mar` | Total March rainfall | mm | Month-level rainfall representation |
| `rainfall_apr` | Total April rainfall | mm | Month-level rainfall representation |

---

## Month-Level Temperature Features

These variables preserve the temporal distribution of temperature throughout the growing season.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `temperature_sep` | Mean September temperature | °C | Month-level temperature representation |
| `temperature_oct` | Mean October temperature | °C | Month-level temperature representation |
| `temperature_nov` | Mean November temperature | °C | Month-level temperature representation |
| `temperature_dec` | Mean December temperature | °C | Month-level temperature representation |
| `temperature_jan` | Mean January temperature | °C | Month-level temperature representation |
| `temperature_feb` | Mean February temperature | °C | Month-level temperature representation |
| `temperature_mar` | Mean March temperature | °C | Month-level temperature representation |
| `temperature_apr` | Mean April temperature | °C | Month-level temperature representation |

---

# Harvest Features

## Harvest Calendar Features

These variables describe the position of observations within the historical harvest calendar.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `harvest_block` | Sequential harvest aggregation block | index | Historical harvest timing |
| `harvest_season` | Harvest season identifier | categorical | Cross-validation grouping |
| `horizon` | Harvest aggregation horizon | blocks | Defines prediction window size |

---

# Data Quality Features

These variables monitor the completeness of weather observations.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `weather_observation_days` | Number of available daily observations | days | Measures observation completeness |

---

# Future Variables

Additional analytical variables are planned for future releases and are documented separately in:

- **ROADMAP.md**